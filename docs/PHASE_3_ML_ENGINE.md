# AstroGuard Phase 3.0–3.5

## 3.0 — Architecture

Modular ML engine with:
- Experiment configuration
- Dataset contracts
- Dataset fingerprints
- Reproducible experiments

## 3.1 — Statistical detection

- Z-score
- Robust Z-score
- Causal rolling robust deviation

All thresholds are calibrated using training data only.

## 3.2 — Unsupervised detection

Isolation Forest:
- 100 estimators by default
- random_state 42
- n_jobs 1
- train-only fitting
- train-derived anomaly threshold

## 3.3 — Supervised classification

Random Forest:
- balanced class weights
- stratified training-only validation
- validation-only threshold selection

Supervised training requires a genuine row-aligned train_labels.npy.
Test labels are never used to train the model.

## 3.4 — Evaluation

- Precision
- Recall
- F1
- Average precision (PR-AUC)
- ROC-AUC
- False alarm rate
- Specificity
- Confusion matrix

## 3.5 — Model persistence and inference

- Joblib persistence
- SHA-256 checksum
- Model manifest
- Feature count validation
- FastAPI inference router

## Limitations

The rolling detector uses feature column zero from the existing
processed feature matrices. These matrices are already engineered
and scaled; its scores are not in raw physical telemetry units.

This is a research and portfolio prototype, not an operational
spacecraft flight-safety system.