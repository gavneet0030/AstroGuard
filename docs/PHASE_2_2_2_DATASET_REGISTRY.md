# Phase 2.2.2 — Multi-Channel Dataset Registry and Unified Loader

## Objective

Provide a single manifest-driven interface for discovering, inspecting,
validating and loading explicitly acquired Telemanom channels.

## Implemented modules

- `astroguard_api.mission_data.registry`
- `astroguard_api.mission_data.unified_loader`

## Registry responsibilities

1. Discover channel directories under:
   `data/raw/mission_sources/telemanom_channels/`
2. Read `channel_manifest.json`.
3. Validate manifest schema version.
4. Validate source repository identity.
5. Validate spacecraft and channel identity.
6. Resolve duplicate channel IDs using spacecraft identity.
7. Validate train/test metadata.
8. Read matching source-label records.
9. Validate expected test row counts.
10. Validate anomaly intervals.
11. Verify array shape, dtype, byte size and SHA-256.

## Loader responsibilities

- Select `train` or `test`.
- Load NumPy arrays with `mmap_mode="r"` by default.
- Disable pickle loading.
- Expose channel and spacecraft identity.
- Return a metadata object alongside the array.
- Support explicit spacecraft selection.
- Refuse ambiguous channel IDs.
- Verify hashes by default.

## CLI

List acquired channels:

```powershell
$env:PYTHONPATH = Join-Path $Root "backend"

.\.venv\Scripts\python.exe -m astroguard_api.mission_data.unified_loader `
    --project-root $Root list
```

Inspect a channel:

```powershell
.\.venv\Scripts\python.exe -m astroguard_api.mission_data.unified_loader `
    --project-root $Root inspect `
    --channel A-1 `
    --spacecraft SMAP
```

Load test split:

```powershell
.\.venv\Scripts\python.exe -m astroguard_api.mission_data.unified_loader `
    --project-root $Root load `
    --channel A-1 `
    --spacecraft SMAP `
    --split test
```

Load train split:

```powershell
.\.venv\Scripts\python.exe -m astroguard_api.mission_data.unified_loader `
    --project-root $Root load `
    --channel P-1 `
    --spacecraft SMAP `
    --split train
```

## Python usage

```python
from pathlib import Path

from astroguard_api.mission_data.unified_loader import load_channel

loaded = load_channel(
    project_root=Path("."),
    channel_id="A-1",
    spacecraft="SMAP",
    split="test",
)

print(loaded.shape)
print(loaded.feature_count)
print(loaded.metadata)
```

## Memory behavior

The default loader uses read-only NumPy memory mapping:

`mmap_mode="r"`

This avoids eagerly copying the full array into Python-managed memory.

The loader does not promise that every downstream operation is zero-copy.
Operations such as advanced indexing, conversion, concatenation or
materialization may allocate additional memory.

## Data interpretation limitations

The acquired benchmark arrays are anonymized and pre-scaled.

This phase does not:

- reconstruct timestamps;
- infer physical engineering units;
- infer spacecraft operating state;
- download the complete Telemanom archive;
- claim NASA affiliation;
- provide operational flight-safety decisions.

## Validation

Run targeted tests:

```powershell
$env:PYTHONPATH = Join-Path $Root "backend"

.\.venv\Scripts\python.exe -m pytest `
    backend/tests/test_dataset_registry.py -q
```

Run the full backend suite:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## Acceptance criteria

- P-1 and A-1 are discovered.
- Channel identity includes spacecraft.
- Manifest metadata is validated.
- Label metadata is cross-checked.
- Train/test shapes and dtypes match manifests.
- SHA-256 verification works.
- Non-finite values are rejected.
- Read-only memory mapping works.
- Ambiguous or unknown channels are rejected.
- Existing telemetry artifacts remain unchanged.
- Full backend regression passes.