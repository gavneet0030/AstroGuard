# Phase 2.3.0 — Telemetry Preprocessing and Feature Engineering

## Objective

Convert verified SMAP telemetry arrays into reproducible, model-ready
features while preserving the original source arrays.

## Inputs

- Verified Telemanom channel train.npy.
- Verified Telemanom channel test.npy.
- Source label metadata.
- Dataset registry and unified loader validation.

## Feature schema

For the current 25-column input:

1. 25 original input features.
2. 25 first-order differences.
3. Target-channel rolling mean for windows 5 and 30.
4. Target-channel rolling standard deviation for windows 5 and 30.

Total: 54 features.

## Temporal policy

- Rolling features are trailing and causal.
- The current observation is included.
- No future observation contributes to a feature.
- Rolling state resets independently at the train/test boundary.
- The first difference in each split is zero.
- Train and test are processed independently.

## Normalization

- Standardization statistics are fitted only on training features.
- Training means and standard deviations are stored in the manifest.
- The same training statistics transform the test features.
- Constant features use scale 1 to avoid division by zero.
- Output features are float32.

## Labels

- Test anomaly labels are uint8.
- Source anomaly intervals use inclusive start and end indices.
- Overlapping intervals are represented as a binary union.
- Labels are aligned to test rows.

## Output

data/processed/telemetry_features/<spacecraft>/<channel>/

- train_features.npy
- test_features.npy
- test_labels.npy
- preprocessing_manifest.json

## Safety and provenance

- Original raw files are read-only inputs.
- Source checksums are validated before processing.
- Output files are written atomically.
- Existing processed output is not overwritten unless explicitly requested.
- Source timestamps are not reconstructed.
- Physical units are not inferred.
- Test data is not used to fit normalization statistics.

## Limitations

- The dataset values are anonymized and pre-scaled.
- Rolling features use only the target telemetry column.
- This phase does not train an anomaly detector.
- This phase does not claim operational spacecraft safety capability.
- This project is an independent research/portfolio prototype and is not
  affiliated with NASA.

## CLI

From the AstroGuard project root:

python -m astroguard_api.mission_data.preprocessing_cli --root . --channel A-1 --spacecraft SMAP

python -m astroguard_api.mission_data.preprocessing_cli --root . --channel P-1 --spacecraft SMAP

Use --overwrite only when intentionally regenerating an existing output.
