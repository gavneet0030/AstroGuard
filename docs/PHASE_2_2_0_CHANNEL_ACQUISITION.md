# AstroGuard Phase 2.2.0 — Channel-Level Telemetry Acquisition

## Scope

This phase introduces a bounded, per-channel acquisition client for the
Telemanom SMAP/MSL research benchmark.

It does not download the full dataset.

## Source

Hugging Face dataset mirror:

https://huggingface.co/datasets/appleparan/telemanom

Original NumPy file layout:

- data/data/train/{CHANNEL}.npy
- data/data/test/{CHANNEL}.npy

## Array structure

Each NumPy array must be two-dimensional:

(timesteps, features)

The first feature is the target telemetry value. Remaining features
encode command information.

The train and test arrays must have the same feature count.

The test row count must match the selected label record's num_values.

## Acquisition controls

- HTTPS only.
- Redirect host validation.
- 32 MiB default maximum per file.
- Temporary file downloads.
- Atomic replacement.
- SHA-256 checksums.
- NumPy memory mapping.
- Chunked finite-value validation.
- No automatic dependency upgrades.

## Label handling

Duplicate label rows are preserved independently.

A channel with multiple label rows cannot be acquired through this
single-record interface. The connector raises an explicit error rather
than silently choosing or merging a label record.

## Data limitations

- Telemetry values are anonymized.
- Values are pre-scaled.
- Timestamps are not reconstructed.
- Physical units are not inferred.
- Channel identifiers do not disclose engineering semantics.
- This is a research dataset mirror, not a NASA API.

## Storage

data/raw/mission_sources/telemanom_channels/
    smap/
        p-1/
            train.npy
            test.npy
            channel_manifest.json

## CLI

Inventory:

python -m astroguard_api.mission_data.telemanom_channel --labels PATH --output PATH --inventory

Acquire:

python -m astroguard_api.mission_data.telemanom_channel --labels PATH --output PATH --channel P-1 --spacecraft SMAP

## Safety

- Existing label metadata is not modified.
- Existing source connector is not overwritten.
- No notebook is created.
- Native C++ build files are not modified.
