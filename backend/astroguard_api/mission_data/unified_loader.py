from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .registry import (
    ChannelRecord,
    RegistryError,
    discover_channels,
    get_channel,
    validate_channel,
)


SplitName = Literal["train", "test"]


class TelemetryLoadError(RuntimeError):
    """Raised when a telemetry split cannot be loaded safely."""


@dataclass(frozen=True)
class LoadedTelemetry:
    spacecraft: str
    channel_id: str
    split: str
    values: np.ndarray
    metadata: dict[str, Any]
    manifest_path: Path

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(self.values.shape)

    @property
    def feature_count(self) -> int:
        return int(self.values.shape[1])

    @property
    def is_memory_mapped(self) -> bool:
        return isinstance(self.values, np.memmap)


def load_channel(
    project_root: Path,
    channel_id: str,
    split: SplitName = "test",
    spacecraft: str | None = None,
    verify_hashes: bool = True,
    mmap_mode: str | None = "r",
) -> LoadedTelemetry:
    project_root = Path(project_root).resolve()

    if split not in ("train", "test"):
        raise TelemetryLoadError(
            f"Unsupported split {split!r}; use 'train' or 'test'"
        )

    # Phase 2.2.2.1:
    # The unified loader must never expose writable dataset mappings.
    if mmap_mode != "r":
        raise TelemetryLoadError(
            "Only mmap_mode='r' is permitted; writable or non-mapped "
            "loading is disabled."
        )

    try:
        record = get_channel(
            project_root,
            channel_id,
            spacecraft=spacecraft,
        )

        validation = validate_channel(
            project_root,
            record,
            verify_hashes=verify_hashes,
        )

    except RegistryError as exc:
        raise TelemetryLoadError(str(exc)) from exc

    path = (
        record.train_path if split == "train"
        else record.test_path
    )

    try:
        values = np.load(
            path,
            mmap_mode=mmap_mode,
            allow_pickle=False,
        )
    except (OSError, ValueError) as exc:
        raise TelemetryLoadError(
            f"Unable to load {record.key} {split} array"
        ) from exc

    if values.ndim != 2:
        raise TelemetryLoadError("Loaded telemetry must be two-dimensional")

    metadata = {
        **validation,
        "split": split,
        "selected_path": str(path),
        "memory_mapped": isinstance(values, np.memmap),
        "mmap_mode": mmap_mode,
        "manifest_path": str(record.manifest_path),
    }

    return LoadedTelemetry(
        spacecraft=record.spacecraft,
        channel_id=record.channel_id,
        split=split,
        values=values,
        metadata=metadata,
        manifest_path=record.manifest_path,
    )


def list_channels(project_root: Path) -> list[dict[str, Any]]:
    try:
        records = discover_channels(project_root)
    except RegistryError as exc:
        raise TelemetryLoadError(str(exc)) from exc

    output = []

    for record in records:
        output.append({
            "key": record.key,
            "spacecraft": record.spacecraft,
            "channel_id": record.channel_id,
            "train_shape": list(record.train_shape),
            "test_shape": list(record.test_shape),
            "manifest_path": str(record.manifest_path),
            "source_repository": record.source_repository,
        })

    return output


def inspect_channel(
    project_root: Path,
    channel_id: str,
    spacecraft: str | None = None,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    try:
        record = get_channel(
            project_root,
            channel_id,
            spacecraft=spacecraft,
        )

        return validate_channel(
            project_root,
            record,
            verify_hashes=verify_hashes,
        )

    except RegistryError as exc:
        raise TelemetryLoadError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AstroGuard unified telemetry loader"
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("list")

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--channel", required=True)
    inspect_parser.add_argument("--spacecraft", choices=["SMAP", "MSL"])

    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("--channel", required=True)
    load_parser.add_argument("--spacecraft", choices=["SMAP", "MSL"])
    load_parser.add_argument("--split", choices=["train", "test"], default="test")

    args = parser.parse_args()

    try:
        if args.command == "list":
            result = {
                "status": "PASS",
                "channels": list_channels(args.project_root),
            }

        elif args.command == "inspect":
            result = {
                "status": "PASS",
                "channel": inspect_channel(
                    args.project_root,
                    args.channel,
                    spacecraft=args.spacecraft,
                ),
            }

        else:
            loaded = load_channel(
                args.project_root,
                args.channel,
                split=args.split,
                spacecraft=args.spacecraft,
                verify_hashes=True,
                mmap_mode="r",
            )

            result = {
                "status": "PASS",
                "channel": loaded.channel_id,
                "spacecraft": loaded.spacecraft,
                "split": loaded.split,
                "shape": list(loaded.shape),
                "feature_count": loaded.feature_count,
                "dtype": str(loaded.values.dtype),
                "memory_mapped": loaded.is_memory_mapped,
                "metadata": loaded.metadata,
            }

        print(json.dumps(result, indent=2, default=str))
        return 0

    except (TelemetryLoadError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "error": str(exc),
        }, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())