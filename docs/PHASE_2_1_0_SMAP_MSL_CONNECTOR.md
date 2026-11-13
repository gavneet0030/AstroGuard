# AstroGuard Phase 2.1.0
## SMAP / MSL Mission Source Connector

### Objective

Register and retrieve the anomaly-label metadata associated with the
published SMAP and Mars Science Laboratory spacecraft anomaly benchmark.

### Source

Original research repository:

https://github.com/khundman/telemanom

Original label file:

https://raw.githubusercontent.com/khundman/telemanom/master/labeled_anomalies.csv

Research paper:

https://arxiv.org/abs/1802.04431

### Dataset characteristics

- SMAP: 55 telemetry channels.
- MSL: 27 telemetry channels.
- Total: 82 channels.
- Published anomaly sequences: 105.
- Values are pre-scaled.
- Channel identifiers are anonymized.
- Timestamps are anonymized.
- Anomaly labels refer to sample-index intervals.

### Provenance

This is a NASA-mission-derived research benchmark distributed through
the Telemanom research repository. The repository documents the
underlying SMAP and MSL data and its research use.

It is not a live NASA telemetry endpoint and is not an operational
spacecraft feed.

### Timestamp policy

AstroGuard must not convert sample indices into fabricated UTC
timestamps. Sample indices are retained as the temporal reference
until an independently verified time mapping is available.

### Unit policy

Pre-scaled values must not be assigned invented engineering units.

### Commands

Discover source:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m astroguard_api.mission_sources.cli discover
```

Fetch anomaly labels:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m astroguard_api.mission_sources.cli fetch-labels --project-root "$PWD"
```

Force refresh:

```powershell
.\.venv\Scripts\python.exe -m astroguard_api.mission_sources.cli --project-root "$PWD" fetch-labels --force
```

### Storage

Raw label file:

`data/raw/mission_sources/smap_msl/labeled_anomalies.csv`

Processed source manifest:

`data/processed/mission_metadata/smap_msl_source_manifest.json`

### Security

- HTTPS only.
- Fixed source URL allowlist.
- Maximum label file size: 5 MiB.
- Temporary download followed by validation and atomic replacement.
- No `eval()` or `exec()` on downloaded data.
- No API keys required.
- No secrets stored in source files.

### Phase boundary

This phase downloads and validates anomaly metadata only.

The full telemetry archive and channel-level array ingestion are
separate implementation steps. The current connector does not claim
that the raw telemetry archive has been downloaded.
