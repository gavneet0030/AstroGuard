# Phase 2.2.1 — Multi-channel telemetry acquisition

## Objective
Generalize the Phase 2.2.0 single-channel acquisition pattern into an explicit
channel-selectable acquisition command.

## Source
Hugging Face dataset: appleparan/telemanom.
Original NumPy layout: data/data/train/{CHANNEL}.npy and
data/data/test/{CHANNEL}.npy.

## Integrity controls
- HTTPS-only allowlisted hosts and redirect validation
- 32 MiB maximum per file
- Temporary download followed by atomic replacement
- NumPy loading with allow_pickle=False
- Numeric, two-dimensional, finite-value validation
- Test sample count checked against source label metadata
- Train/test feature-count consistency
- SHA-256 checksums in a per-channel manifest
- No fabricated timestamps or physical units

## Scope
This phase acquires only the explicitly selected channel A-1.
It must not overwrite the previously acquired P-1 channel.

## Known data limitations
Telemetry values are anonymized and pre-scaled. Channel identifiers are
anonymized. Sample indices are not UTC timestamps. The dataset is a
research benchmark, not operational flight telemetry.
