"""
AstroGuard telemetry ingestion engine.

Input formats:
- CSV
- JSON array
- JSON object with a records array

Pipeline:
1. Validate source file.
2. Compute SHA-256.
3. Preserve original raw source.
4. Check batch idempotency.
5. Parse and validate records.
6. Deduplicate valid records within the batch.
7. Write accepted JSONL.
8. Write rejected JSONL with reasons.
9. Atomically publish output files.
10. Write provenance manifest last.

The raw archive is never modified by this module after copying.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from astroguard_api.telemetry.models import (
    TelemetryRecord,
    TelemetryValidationError,
)


MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_SOURCE_BYTES = 512 * 1024 * 1024

SUPPORTED_SUFFIXES = {
    ".csv",
    ".json",
}


class IngestionError(RuntimeError):
    """Raised when a telemetry batch cannot be ingested."""


@dataclass(frozen=True)
class IngestionResult:
    batch_id: str
    source_name: str
    source_sha256: str
    status: str
    total_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    raw_archive_path: str
    processed_path: str
    quarantine_path: str
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def _write_json_line(stream, payload: dict[str, Any]) -> None:
    stream.write(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    stream.write("\n")


def _iter_csv(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:

        reader = csv.DictReader(stream)

        if reader.fieldnames is None:
            raise IngestionError(
                "CSV file has no header row"
            )

        normalized_headers = {
            str(name).strip().lower()
            for name in reader.fieldnames
            if name is not None
        }

        required = {
            "timestamp",
            "channel",
            "value",
        }

        missing = required - normalized_headers

        if missing:
            raise IngestionError(
                "CSV missing required columns: "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            normalized = {
                str(key).strip().lower(): value
                for key, value in row.items()
                if key is not None
            }

            yield normalized


def _iter_json(path: Path) -> Iterator[dict[str, Any]]:
    size = path.stat().st_size

    if size > MAX_JSON_BYTES:
        raise IngestionError(
            "JSON input exceeds the 64 MiB ingestion limit"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as stream:
            payload = json.load(stream)
    except json.JSONDecodeError as exc:
        raise IngestionError(
            "JSON input is malformed"
        ) from exc

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("records")
    else:
        records = None

    if not isinstance(records, list):
        raise IngestionError(
            "JSON must be an array or an object containing a records array"
        )

    for row in records:
        if not isinstance(row, dict):
            yield {"__invalid_record__": row}
        else:
            yield row


def _iter_records(path: Path) -> Iterator[dict[str, Any]]:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        yield from _iter_csv(path)
        return

    if suffix == ".json":
        yield from _iter_json(path)
        return

    raise IngestionError(
        "Unsupported input format. Supported formats: CSV and JSON."
    )


class TelemetryIngestor:
    def __init__(
        self,
        project_root: Path,
        *,
        max_source_bytes: int = MAX_SOURCE_BYTES,
    ) -> None:

        self.project_root = Path(project_root).resolve()

        self.raw_root = (
            self.project_root
            / "data"
            / "raw"
            / "archive"
        )

        self.processed_root = (
            self.project_root
            / "data"
            / "processed"
            / "batches"
        )

        self.quarantine_root = (
            self.project_root
            / "data"
            / "quarantine"
        )

        self.max_source_bytes = max_source_bytes

        for directory in (
            self.raw_root,
            self.processed_root,
            self.quarantine_root,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def _validate_source(self, source: Path) -> Path:
        source = Path(source).resolve()

        if not source.exists():
            raise IngestionError(
                "Source file does not exist"
            )

        if not source.is_file():
            raise IngestionError(
                "Source path must reference a file"
            )

        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise IngestionError(
                "Unsupported telemetry file extension"
            )

        if source.stat().st_size > self.max_source_bytes:
            raise IngestionError(
                "Source file exceeds configured size limit"
            )

        if source.stat().st_size == 0:
            raise IngestionError(
                "Source file is empty"
            )

        return source

    def _archive_raw(
        self,
        source: Path,
        digest: str,
    ) -> Path:

        destination = (
            self.raw_root
            / f"{digest}{source.suffix.lower()}"
        )

        if destination.exists():
            if sha256_file(destination) != digest:
                raise IngestionError(
                    "Existing raw archive hash mismatch"
                )

            return destination

        temporary = destination.with_suffix(
            destination.suffix + ".tmp"
        )

        try:
            shutil.copyfile(source, temporary)

            if sha256_file(temporary) != digest:
                raise IngestionError(
                    "Raw archive checksum verification failed"
                )

            os.replace(
                temporary,
                destination,
            )
        finally:
            if temporary.exists():
                temporary.unlink()

        return destination

    def _batch_paths(self, digest: str) -> dict[str, Path]:
        return {
            "processed": (
                self.processed_root
                / f"{digest}.jsonl"
            ),
            "quarantine": (
                self.quarantine_root
                / f"{digest}.jsonl"
            ),
            "manifest": (
                self.processed_root
                / f"{digest}.manifest.json"
            ),
        }

    def _load_existing_result(
        self,
        digest: str,
        source_name: str,
        raw_archive: Path,
        paths: dict[str, Path],
    ) -> Optional[IngestionResult]:

        manifest_path = paths["manifest"]

        if not manifest_path.exists():
            return None

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            raise IngestionError(
                "Existing batch manifest is unreadable"
            )

        if manifest.get("source_sha256") != digest:
            raise IngestionError(
                "Existing batch manifest checksum mismatch"
            )

        if not paths["processed"].exists():
            raise IngestionError(
                "Existing processed output is missing"
            )

        if not paths["quarantine"].exists():
            raise IngestionError(
                "Existing quarantine output is missing"
            )

        return IngestionResult(
            batch_id=digest,
            source_name=source_name,
            source_sha256=digest,
            status="already_processed",
            total_records=manifest["total_records"],
            accepted_records=manifest["accepted_records"],
            rejected_records=manifest["rejected_records"],
            duplicate_records=manifest["duplicate_records"],
            raw_archive_path=str(raw_archive),
            processed_path=str(paths["processed"]),
            quarantine_path=str(paths["quarantine"]),
            manifest_path=str(manifest_path),
        )

    def ingest_file(
        self,
        source: Path,
        *,
        source_label: str = "LOCAL_FILE",
    ) -> IngestionResult:

        source = self._validate_source(source)

        digest = sha256_file(source)

        raw_archive = self._archive_raw(
            source,
            digest,
        )

        paths = self._batch_paths(digest)

        existing = self._load_existing_result(
            digest,
            source.name,
            raw_archive,
            paths,
        )

        if existing is not None:
            return existing

        processed_fd, processed_temp_name = tempfile.mkstemp(
            prefix=digest + ".",
            suffix=".tmp",
            dir=str(self.processed_root),
        )

        quarantine_fd, quarantine_temp_name = tempfile.mkstemp(
            prefix=digest + ".",
            suffix=".tmp",
            dir=str(self.quarantine_root),
        )

        processed_temp = Path(processed_temp_name)
        quarantine_temp = Path(quarantine_temp_name)

        os.close(processed_fd)
        os.close(quarantine_fd)

        total = 0
        accepted = 0
        rejected = 0
        duplicates = 0

        seen_fingerprints: set[str] = set()

        try:
            with (
                processed_temp.open(
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as processed_stream,
                quarantine_temp.open(
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as quarantine_stream,
            ):

                for row_number, row in enumerate(
                    _iter_records(source),
                    start=1,
                ):
                    total += 1

                    try:
                        if "__invalid_record__" in row:
                            raise TelemetryValidationError(
                                "JSON record must be an object"
                            )

                        record = TelemetryRecord.from_mapping(
                            row,
                            default_source=source_label,
                        )

                        fingerprint = record.fingerprint()

                        if fingerprint in seen_fingerprints:
                            duplicates += 1
                            continue

                        seen_fingerprints.add(
                            fingerprint
                        )

                        _write_json_line(
                            processed_stream,
                            record.to_dict(),
                        )

                        accepted += 1

                    except TelemetryValidationError as exc:
                        _write_json_line(
                            quarantine_stream,
                            {
                                "row_number": row_number,
                                "reason": str(exc),
                                "record": row,
                            },
                        )

                        rejected += 1

                processed_stream.flush()
                os.fsync(processed_stream.fileno())

                quarantine_stream.flush()
                os.fsync(quarantine_stream.fileno())

            os.replace(
                processed_temp,
                paths["processed"],
            )

            os.replace(
                quarantine_temp,
                paths["quarantine"],
            )

            manifest = {
                "schema_version": "1.0",
                "pipeline": "astroguard-telemetry-ingestion",
                "batch_id": digest,
                "source_name": source.name,
                "source_label": source_label,
                "source_sha256": digest,
                "source_size_bytes": source.stat().st_size,
                "total_records": total,
                "accepted_records": accepted,
                "rejected_records": rejected,
                "duplicate_records": duplicates,
                "status": "completed",
                "raw_archive_path": str(raw_archive),
                "processed_path": str(paths["processed"]),
                "quarantine_path": str(paths["quarantine"]),
            }

            manifest_temp = paths["manifest"].with_suffix(
                ".manifest.json.tmp"
            )

            manifest_temp.write_text(
                json.dumps(
                    manifest,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            os.replace(
                manifest_temp,
                paths["manifest"],
            )

        except Exception:
            for temporary in (
                processed_temp,
                quarantine_temp,
            ):
                if temporary.exists():
                    temporary.unlink()

            raise

        return IngestionResult(
            batch_id=digest,
            source_name=source.name,
            source_sha256=digest,
            status="completed",
            total_records=total,
            accepted_records=accepted,
            rejected_records=rejected,
            duplicate_records=duplicates,
            raw_archive_path=str(raw_archive),
            processed_path=str(paths["processed"]),
            quarantine_path=str(paths["quarantine"]),
            manifest_path=str(paths["manifest"]),
        )
