# Phase 2.3.1 — Advanced Temporal and Statistical Features

## Purpose

Extend the verified 54-column Phase 2.3.0 baseline into a separate
69-column advanced dataset for the acquired SMAP A-1 and P-1 channels.

The original baseline dataset is preserved.

## Feature contract

15 additional features are generated from target telemetry column 0.

1. First difference
2. Absolute first difference
3. Percentage change
4. Rolling mean, window 5
5. Rolling population standard deviation, window 5
6. Rolling minimum, window 5
7. Rolling maximum, window 5
8. Rolling median, window 5
9. Rolling median absolute deviation, window 5
10. Rolling mean, window 30
11. Rolling population standard deviation, window 30
12. Rolling minimum, window 30
13. Rolling maximum, window 30
14. EWMA alpha 0.1
15. EWMA alpha 0.3

## Causality

All rolling windows are trailing windows. The feature at index t uses
only observations at or before t.

At the beginning of a split, the calculation uses the available prefix.
Train and test windows are reset independently.

## Scaling

The advanced feature scaler is fitted only on the training split.
The same training mean and scale are applied to test features.

Constant training columns use scale 1.0.

## Dataset contract

Baseline features: 54
Advanced features: 15
Total features: 69

Feature dtype: float32
Label dtype: uint8

## Outputs

data/processed/advanced_telemetry_features/smap/a-1/
data/processed/advanced_telemetry_features/smap/p-1/

Files:
- train_features_advanced.npy
- test_features_advanced.npy
- test_labels.npy
- advanced_feature_manifest.json

## Safety

- Raw telemetry is read-only.
- Phase 2.3.0 outputs are read-only.
- Source labels are copied, not reconstructed.
- No timestamps are invented.
- No physical units are inferred.
- No full archive downloads are performed.
- No cloud services or Docker are required.

## Limitations

These features are a research and portfolio feature-engineering layer.
They are not a validated spacecraft flight-safety system.