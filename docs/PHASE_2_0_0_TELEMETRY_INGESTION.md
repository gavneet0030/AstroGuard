# AstroGuard Phase 2.0.0
# Telemetry Data Engineering Foundation

## Purpose

Establish a mission-independent historical telemetry ingestion engine.

This is a research prototype. It is not an operational spacecraft
flight-safety system and is not affiliated with NASA.

## Supported formats

- CSV
- JSON array
- JSON object containing a records array

## Canonical telemetry schema

| Field | Type | Requirement |
|---|---|---|
| timestamp | ISO-8601 string | Required, timezone-aware |
| channel | string | Required |
| value | finite float | Required |
| unit | string | Optional |
| quality | enum | Optional |
| source | string | Optional |

Quality values:

- GOOD
- SUSPECT
- BAD
- UNKNOWN

## Data flow

1. Validate source file and extension.
2. Calculate source SHA-256.
3. Preserve original source in data/raw/archive.
4. Check for an existing completed batch.
5. Parse and validate telemetry records.
6. Deduplicate records within the batch.
7. Write accepted records to JSONL.
8. Write rejected records to quarantine JSONL.
9. Write a batch provenance manifest.

## Data directories

- `data/raw/archive/`: Original source files.
- `data/processed/batches/`: Accepted records and manifests.
- `data/quarantine/`: Invalid records and validation reasons.
- `data/sample/`: Explicitly labelled local fixtures.

## Idempotency

The SHA-256 of the source file is the batch identifier.

Re-ingesting an unchanged file returns `already_processed`.

This version performs duplicate detection within a batch. It does not
yet provide global cross-batch deduplication.

## Resource limits

- Maximum source file size: 512 MiB.
- Maximum JSON input size: 64 MiB.
- CSV records are processed incrementally.
- JSON input is parsed into memory.

## Important provenance boundary

A source label is descriptive metadata, not proof of authenticity.

A NASA mission archive adapter must be implemented only after the
exact public dataset, its license, mission, schema, and provenance
are identified.

The local tests use synthetic fixtures and are not NASA observations.

## CLI

`python -m astroguard_api.telemetry.cli ingest data/sample/file.csv`

## Validation

`python -m pytest -q backend/tests/test_telemetry_pipeline.py`

`python -m pytest -q backend/tests`
