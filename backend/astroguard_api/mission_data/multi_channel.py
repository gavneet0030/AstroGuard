from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPOSITORY = "appleparan/telemanom"
BASE_URL = "https://huggingface.co/datasets/appleparan/telemanom/resolve/main"
ALLOWED_HOSTS = {
                    "cas-bridge.xethub.hf.co",
                    "cas-server.xethub-eu.hf.co",
                    "cas-server.xethub.hf.co",
                    "cdn-lfs-eu-1.hf.co",
                    "cdn-lfs-us-1.hf.co",
                    "cdn-lfs.huggingface.co",
                    "huggingface.co",
                    "transfer.xethub-eu.hf.co",
                    "transfer.xethub.hf.co",
                    "us.aws.cdn.hf.co",
                    "us.gcp.cdn.hf.co",
                }
MAX_FILE_BYTES = 32 * 1024 * 1024
CHANNEL_PATTERN = re.compile(r"^[A-Z]-[0-9]{1,2}$")


class AcquisitionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urllib.parse.urlparse(newurl).hostname
        if host not in ALLOWED_HOSTS:
            raise AcquisitionError(f"Redirect host is not allowlisted: {host}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_atomic(url: str, destination: Path) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise AcquisitionError("URL rejected by HTTPS host allowlist")

    destination.parent.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AstroGuard-Research/1.0"},
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=".astroguard-", suffix=".part", dir=str(destination.parent)
    )
    os.close(fd)
    temporary = Path(temporary_name)
    total = 0

    try:
        with opener.open(request, timeout=45) as response:
            final_host = urllib.parse.urlparse(response.geturl()).hostname
            if final_host not in ALLOWED_HOSTS:
                raise AcquisitionError(f"Final host is not allowlisted: {final_host}")

            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_FILE_BYTES:
                raise AcquisitionError("Remote file exceeds the configured size limit")

            with temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise AcquisitionError("Download exceeded the configured size limit")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())

        if total == 0:
            raise AcquisitionError("Remote file was empty")

        os.replace(temporary, destination)
        return {"bytes": total, "sha256": sha256_file(destination), "url": url}

    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def read_label_record(labels_path: Path, channel: str) -> dict[str, Any]:
    if not labels_path.is_file():
        raise AcquisitionError(f"Label metadata not found: {labels_path}")

    with labels_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"chan_id", "spacecraft", "num_values", "anomaly_sequences"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise AcquisitionError("Label CSV is missing required columns")

        matches = [row for row in reader if row["chan_id"].strip() == channel]

    if len(matches) != 1:
        raise AcquisitionError(
            f"Expected exactly one label record for {channel}; found {len(matches)}"
        )

    row = matches[0]
    spacecraft = row["spacecraft"].strip().upper()
    if spacecraft not in {"SMAP", "MSL"}:
        raise AcquisitionError("Invalid spacecraft value")

    try:
        expected_rows = int(row["num_values"])
        intervals = ast.literal_eval(row["anomaly_sequences"])
    except (ValueError, SyntaxError, TypeError) as exc:
        raise AcquisitionError("Malformed label metadata") from exc

    if expected_rows <= 0 or not isinstance(intervals, list):
        raise AcquisitionError("Invalid label sample count or anomaly intervals")

    clean_intervals = []
    for interval in intervals:
        if (
            not isinstance(interval, (list, tuple))
            or len(interval) != 2
            or any(type(value) is not int for value in interval)
        ):
            raise AcquisitionError("Malformed anomaly interval")
        start, end = interval
        if start < 0 or end < start or end >= expected_rows:
            raise AcquisitionError("Anomaly interval outside the declared test stream")
        clean_intervals.append([start, end])

    return {
        "channel_id": channel,
        "spacecraft": spacecraft,
        "expected_test_rows": expected_rows,
        "anomaly_sequences": clean_intervals,
    }


def validate_array(path: Path) -> dict[str, Any]:
    try:
        array = np.load(path, allow_pickle=False, mmap_mode="r")
    except Exception as exc:
        raise AcquisitionError(f"Invalid NumPy array: {path.name}") from exc

    if array.ndim != 2 or array.shape[0] <= 0 or array.shape[1] <= 0:
        raise AcquisitionError(f"Unexpected array dimensions: {array.shape}")

    if array.dtype.kind not in {"f", "i", "u"}:
        raise AcquisitionError(f"Non-numeric array dtype: {array.dtype}")

    # Validate in bounded row chunks to avoid loading the complete array into RAM.
    for start in range(0, array.shape[0], 512):
        chunk = np.asarray(array[start:start + 512])
        if not np.isfinite(chunk).all():
            raise AcquisitionError("Array contains non-finite values")

    return {
        "shape": [int(array.shape[0]), int(array.shape[1])],
        "dtype": str(array.dtype),
    }


def acquire_channel(
    project_root: Path,
    channel: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    channel = channel.strip().upper()
    if not CHANNEL_PATTERN.fullmatch(channel):
        raise AcquisitionError("Invalid channel identifier")

    labels_path = (
        project_root / "data" / "raw" / "mission_sources"
        / "smap_msl" / "labeled_anomalies.csv"
    )
    label = read_label_record(labels_path, channel)
    spacecraft = label["spacecraft"].lower()
    channel_dir = (
        project_root / "data" / "raw" / "mission_sources"
        / "telemanom_channels" / spacecraft / channel.lower()
    )

    train_path = channel_dir / "train.npy"
    test_path = channel_dir / "test.npy"
    manifest_path = channel_dir / "channel_manifest.json"

    if channel_dir.exists() and not force:
        if manifest_path.exists() and train_path.exists() and test_path.exists():
            try:
                previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                if previous.get("channel_id") == channel:
                    if (
                        previous.get("train_sha256") == sha256_file(train_path)
                        and previous.get("test_sha256") == sha256_file(test_path)
                    ):
                        return {
                            "status": "SKIPPED_ALREADY_VERIFIED",
                            "channel_id": channel,
                            "manifest_path": str(manifest_path),
                        }
            except (OSError, ValueError):
                pass
        raise AcquisitionError(
            f"Existing channel directory is not a verified matching acquisition: {channel_dir}. "
            "Inspect it or use --force after taking a backup."
        )

    channel_dir.mkdir(parents=True, exist_ok=True)
    train_url = f"{BASE_URL}/data/data/train/{channel}.npy"
    test_url = f"{BASE_URL}/data/data/test/{channel}.npy"

    train_info = download_atomic(train_url, train_path)
    test_info = download_atomic(test_url, test_path)

    train_meta = validate_array(train_path)
    test_meta = validate_array(test_path)

    if train_meta["shape"][1] != test_meta["shape"][1]:
        raise AcquisitionError("Train/test feature counts differ")
    if test_meta["shape"][0] != label["expected_test_rows"]:
        raise AcquisitionError(
            f"Test rows {test_meta['shape'][0]} do not match labels "
            f"{label['expected_test_rows']}"
        )

    manifest = {
        "schema_version": 1,
        "source_repository": REPOSITORY,
        "channel_id": channel,
        "spacecraft": label["spacecraft"],
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "train": train_meta,
        "test": test_meta,
        "expected_test_rows_from_labels": label["expected_test_rows"],
        "anomaly_sequences": label["anomaly_sequences"],
        "train_sha256": train_info["sha256"],
        "test_sha256": test_info["sha256"],
        "train_bytes": train_info["bytes"],
        "test_bytes": test_info["bytes"],
        "train_url": train_url,
        "test_url": test_url,
        "timestamps_reconstructed": False,
        "physical_units_inferred": False,
        "values_are_anonymized_and_pre_scaled": True,
        "validation": {
            "test_rows_match_labels": True,
            "train_test_feature_counts_match": True,
            "all_values_finite": True,
            "sha256_recorded": True,
        },
    }

    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    os.replace(temporary_manifest, manifest_path)

    return {
        "status": "PASS",
        "channel_id": channel,
        "spacecraft": label["spacecraft"],
        "train_shape": train_meta["shape"],
        "test_shape": test_meta["shape"],
        "manifest_path": str(manifest_path),
        "train_sha256": train_info["sha256"],
        "test_sha256": test_info["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AstroGuard multi-channel acquisition")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        result = acquire_channel(args.project_root.resolve(), args.channel, force=args.force)
        print(json.dumps(result, indent=2))
        return 0
    except (AcquisitionError, OSError, urllib.error.URLError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
