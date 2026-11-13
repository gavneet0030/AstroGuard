from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


SOURCE_ID = "NASA_SMAP_MSL_TELEMANOM"
REPOSITORY_ID = "appleparan/telemanom"

BASE_URL = (
    "https://huggingface.co/datasets/"
    "appleparan/telemanom/resolve/main"
)

ALLOWED_REDIRECT_HOSTS = {
    "huggingface.co",
    "hf.co",
    "xethub.hf.co",
}

DEFAULT_MAX_FILE_BYTES = 32 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 45

CHANNEL_PATTERN = re.compile(r"^[A-Z]-[0-9]+$")


class ChannelAcquisitionError(RuntimeError):
    """Raised when channel acquisition or validation fails."""


@dataclass(frozen=True)
class LabelRecord:
    source_row_number: int
    spacecraft: str
    channel_id: str
    num_values: int
    anomaly_sequences: list[list[int]]

    @property
    def record_id(self) -> str:
        return (
            f"{self.spacecraft}:"
            f"{self.channel_id}:"
            f"row-{self.source_row_number}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def parse_anomaly_sequences(value: str) -> list[list[int]]:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError) as exc:
        raise ChannelAcquisitionError(
            "Could not parse anomaly_sequences safely"
        ) from exc

    if not isinstance(parsed, (list, tuple)):
        raise ChannelAcquisitionError(
            "Anomaly sequences must be a list"
        )

    result: list[list[int]] = []

    for interval in parsed:
        if not isinstance(interval, (list, tuple)):
            raise ChannelAcquisitionError(
                "Anomaly interval must be a list or tuple"
            )

        if len(interval) != 2:
            raise ChannelAcquisitionError(
                "Anomaly interval must contain exactly two indices"
            )

        start, end = interval

        if type(start) is not int or type(end) is not int:
            raise ChannelAcquisitionError(
                "Anomaly interval indices must be integers"
            )

        if start < 0 or end < start:
            raise ChannelAcquisitionError(
                "Invalid anomaly interval bounds"
            )

        result.append([start, end])

    return result


def load_label_records(labels_path: Path) -> list[LabelRecord]:
    if not labels_path.is_file():
        raise ChannelAcquisitionError(
            f"Labels CSV does not exist: {labels_path}"
        )

    records: list[LabelRecord] = []

    with labels_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:

        reader = csv.DictReader(stream)

        required_columns = {
            "chan_id",
            "spacecraft",
            "num_values",
            "anomaly_sequences",
        }

        if not reader.fieldnames:
            raise ChannelAcquisitionError(
                "Labels CSV has no header"
            )

        if not required_columns.issubset(set(reader.fieldnames)):
            raise ChannelAcquisitionError(
                f"Missing label columns: {required_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            channel = str(row["chan_id"]).strip().upper()
            spacecraft = str(row["spacecraft"]).strip().upper()

            if not CHANNEL_PATTERN.fullmatch(channel):
                raise ChannelAcquisitionError(
                    f"Invalid channel ID at row {row_number}"
                )

            if spacecraft not in {"SMAP", "MSL"}:
                raise ChannelAcquisitionError(
                    f"Invalid spacecraft at row {row_number}"
                )

            try:
                num_values = int(row["num_values"])
            except (ValueError, TypeError) as exc:
                raise ChannelAcquisitionError(
                    f"Invalid num_values at row {row_number}"
                ) from exc

            if num_values <= 0:
                raise ChannelAcquisitionError(
                    "num_values must be positive"
                )

            sequences = parse_anomaly_sequences(
                row["anomaly_sequences"]
            )

            for start, end in sequences:
                if end >= num_values:
                    raise ChannelAcquisitionError(
                        f"Anomaly interval exceeds stream at row {row_number}"
                    )

            records.append(
                LabelRecord(
                    source_row_number=row_number,
                    spacecraft=spacecraft,
                    channel_id=channel,
                    num_values=num_values,
                    anomaly_sequences=sequences,
                )
            )

    return records


def inventory(labels_path: Path) -> dict[str, Any]:
    records = load_label_records(labels_path)

    channels: dict[str, list[dict[str, Any]]] = {}

    for record in records:
        channels.setdefault(
            record.channel_id,
            [],
        ).append(asdict(record))

    return {
        "source_id": SOURCE_ID,
        "repository_id": REPOSITORY_ID,
        "source_record_count": len(records),
        "unique_channel_count": len(channels),
        "channels": channels,
        "pilot_candidates": sorted(channels),
        "duplicate_channel_records": {
            channel: len(rows)
            for channel, rows in channels.items()
            if len(rows) > 1
        },
        "note": (
            "Source label rows are preserved independently. "
            "Repeated channel IDs are not merged."
        ),
    }


def find_channel_records(
    labels_path: Path,
    channel_id: str,
    spacecraft: str | None = None,
) -> list[LabelRecord]:

    channel_id = channel_id.strip().upper()

    if not CHANNEL_PATTERN.fullmatch(channel_id):
        raise ChannelAcquisitionError(
            "Invalid channel identifier"
        )

    normalized_spacecraft = (
        spacecraft.strip().upper()
        if spacecraft
        else None
    )

    if normalized_spacecraft not in {None, "SMAP", "MSL"}:
        raise ChannelAcquisitionError(
            "Spacecraft must be SMAP or MSL"
        )

    return [
        record
        for record in load_label_records(labels_path)
        if record.channel_id == channel_id
        and (
            normalized_spacecraft is None
            or record.spacecraft == normalized_spacecraft
        )
    ]


def is_approved_redirect(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme != "https":
        return False

    if not parsed.hostname:
        return False

    host = parsed.hostname.lower()

    return any(
        host == approved
        or host.endswith("." + approved)
        for approved in ALLOWED_REDIRECT_HOSTS
    )


def download_bounded(
    url: str,
    destination: Path,
    max_bytes: int = DEFAULT_MAX_FILE_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:

    if not url.startswith(
        "https://huggingface.co/datasets/"
    ):
        raise ChannelAcquisitionError(
            "Only the configured Hugging Face dataset host is allowed"
        )

    if max_bytes <= 0:
        raise ChannelAcquisitionError(
            "Maximum file size must be positive"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AstroGuard-Research-Prototype/2.2.0"
        },
        method="GET",
    )

    temporary_path: Path | None = None

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            final_url = response.geturl()

            if not is_approved_redirect(final_url):
                raise ChannelAcquisitionError(
                    "Redirected to an unapproved host"
                )

            declared_size = response.headers.get(
                "Content-Length"
            )

            if declared_size:
                try:
                    declared_size_int = int(declared_size)
                except ValueError as exc:
                    raise ChannelAcquisitionError(
                        "Invalid Content-Length header"
                    ) from exc

                if (
                    declared_size_int <= 0
                    or declared_size_int > max_bytes
                ):
                    raise ChannelAcquisitionError(
                        "Remote file exceeds configured size limit"
                    )

            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=destination.name + ".",
                suffix=".partial",
                dir=str(destination.parent),
            )

            os.close(file_descriptor)

            temporary_path = Path(temporary_name)

            total_bytes = 0
            digest = hashlib.sha256()

            with temporary_path.open("wb") as output:
                while True:
                    chunk = response.read(64 * 1024)

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > max_bytes:
                        raise ChannelAcquisitionError(
                            "Download exceeded configured size limit"
                        )

                    digest.update(chunk)
                    output.write(chunk)

                output.flush()
                os.fsync(output.fileno())

            if total_bytes == 0:
                raise ChannelAcquisitionError(
                    "Downloaded file is empty"
                )

            if (
                declared_size
                and total_bytes != int(declared_size)
            ):
                raise ChannelAcquisitionError(
                    "Downloaded size does not match Content-Length"
                )

            os.replace(
                temporary_path,
                destination,
            )

            temporary_path = None

            return {
                "url": url,
                "final_url": final_url,
                "size_bytes": total_bytes,
                "sha256": digest.hexdigest(),
            }

    except ChannelAcquisitionError:
        raise

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
    ) as exc:

        raise ChannelAcquisitionError(
            f"Download failed: {exc}"
        ) from exc

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink(missing_ok=True)


def validate_npy(
    path: Path,
    expected_rows: int | None = None,
) -> dict[str, Any]:

    if not path.is_file():
        raise ChannelAcquisitionError(
            f"Array file missing: {path}"
        )

    try:
        array = np.load(
            path,
            mmap_mode="r",
            allow_pickle=False,
        )
    except Exception as exc:
        raise ChannelAcquisitionError(
            f"Invalid NumPy file: {path.name}"
        ) from exc

    if array.ndim != 2:
        raise ChannelAcquisitionError(
            f"Expected 2D array; received {array.ndim}D"
        )

    if array.shape[0] <= 0 or array.shape[1] <= 0:
        raise ChannelAcquisitionError(
            "Array dimensions must be positive"
        )

    if array.dtype.kind not in {"i", "u", "f"}:
        raise ChannelAcquisitionError(
            "Array must have a numeric dtype"
        )

    if (
        expected_rows is not None
        and int(array.shape[0]) != expected_rows
    ):
        raise ChannelAcquisitionError(
            f"Expected {expected_rows} rows; "
            f"received {array.shape[0]}"
        )

    rows_per_chunk = 8192

    for start in range(
        0,
        array.shape[0],
        rows_per_chunk,
    ):
        block = np.asarray(
            array[start:start + rows_per_chunk]
        )

        if not np.isfinite(block).all():
            raise ChannelAcquisitionError(
                "NaN or infinite values detected"
            )

    return {
        "file": path.name,
        "shape": [
            int(array.shape[0]),
            int(array.shape[1]),
        ],
        "dtype": str(array.dtype),
        "target_feature_index": 0,
        "command_feature_count": int(array.shape[1] - 1),
        "finite_values": True,
        "expected_rows": expected_rows,
        "expected_rows_match": (
            None
            if expected_rows is None
            else int(array.shape[0]) == expected_rows
        ),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def acquire_channel(
    labels_path: Path,
    output_root: Path,
    channel_id: str,
    spacecraft: str | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict[str, Any]:

    records = find_channel_records(
        labels_path,
        channel_id,
        spacecraft,
    )

    if len(records) == 0:
        raise ChannelAcquisitionError(
            f"No label record found for {channel_id}"
        )

    if len(records) > 1:
        identifiers = [
            record.record_id
            for record in records
        ]

        raise ChannelAcquisitionError(
            "Multiple label rows exist for this channel. "
            "Explicit record selection is required. "
            f"Found: {identifiers}"
        )

    record = records[0]

    channel_directory = (
        output_root
        / record.spacecraft.lower()
        / record.channel_id.lower()
    )

    channel_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    results: dict[str, Any] = {}

    for split in ("train", "test"):

        relative_path = (
            f"data/data/{split}/"
            f"{record.channel_id}.npy"
        )

        encoded_path = urllib.parse.quote(
            relative_path,
            safe="/",
        )

        url = (
            f"{BASE_URL}/"
            f"{encoded_path}"
        )

        destination = (
            channel_directory
            / f"{split}.npy"
        )

        download_result = download_bounded(
            url=url,
            destination=destination,
            max_bytes=max_file_bytes,
        )

        expected_rows = (
            record.num_values
            if split == "test"
            else None
        )

        validation_result = validate_npy(
            destination,
            expected_rows=expected_rows,
        )

        results[split] = {
            "download": download_result,
            "validation": validation_result,
        }

    train_shape = results["train"]["validation"]["shape"]
    test_shape = results["test"]["validation"]["shape"]

    if train_shape[1] != test_shape[1]:
        raise ChannelAcquisitionError(
            "Train/test feature count mismatch"
        )

    manifest = {
        "schema_version": "1.0",
        "phase": "2.2.0",
        "source_id": SOURCE_ID,
        "repository_id": REPOSITORY_ID,
        "channel_id": record.channel_id,
        "spacecraft": record.spacecraft,
        "label_record": asdict(record),
        "label_record_id": record.record_id,
        "train": results["train"],
        "test": results["test"],
        "features": {
            "target_feature_index": 0,
            "command_feature_count": train_shape[1] - 1,
            "feature_count": train_shape[1],
        },
        "anomaly_sequences": record.anomaly_sequences,
        "data_limitations": {
            "timestamps_reconstructed": False,
            "physical_units_inferred": False,
            "telemetry_values_anonymized": True,
            "values_pre_scaled": True,
            "source_is_nasa_api": False,
            "source_is_telemanom_dataset_mirror": True,
        },
    }

    manifest_path = (
        channel_directory
        / "channel_manifest.json"
    )

    temporary_manifest = (
        channel_directory
        / "channel_manifest.json.partial"
    )

    temporary_manifest.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    os.replace(
        temporary_manifest,
        manifest_path,
    )

    return {
        "status": "PASS",
        "channel_id": record.channel_id,
        "spacecraft": record.spacecraft,
        "train_shape": train_shape,
        "test_shape": test_shape,
        "manifest_path": str(manifest_path),
        "train_sha256": results["train"]["validation"]["sha256"],
        "test_sha256": results["test"]["validation"]["sha256"],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "AstroGuard bounded Telemanom channel acquisition"
        )
    )

    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--channel")
    parser.add_argument("--spacecraft")
    parser.add_argument("--max-file-mb", type=int, default=32)
    parser.add_argument("--inventory", action="store_true")

    args = parser.parse_args()

    labels_path = Path(args.labels).resolve()
    output_root = Path(args.output).resolve()

    if args.inventory:
        print(
            json.dumps(
                inventory(labels_path),
                indent=2,
            )
        )
        return 0

    if not args.channel:
        parser.error(
            "--channel is required unless --inventory is used"
        )

    if not 1 <= args.max_file_mb <= 128:
        parser.error(
            "--max-file-mb must be between 1 and 128"
        )

    result = acquire_channel(
        labels_path=labels_path,
        output_root=output_root,
        channel_id=args.channel,
        spacecraft=args.spacecraft,
        max_file_bytes=args.max_file_mb * 1024 * 1024,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
