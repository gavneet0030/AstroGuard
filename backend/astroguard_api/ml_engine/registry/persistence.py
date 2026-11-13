import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
import sklearn

from ..fingerprints import sha256_file


class ModelRegistry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model,
        channel,
        model_name,
        feature_count,
        feature_names,
        fingerprint,
        threshold,
        config
    ):
        if channel not in ("a-1", "p-1"):
            raise ValueError("Invalid channel.")

        if model_name not in ("isolation_forest", "random_forest"):
            raise ValueError("Invalid model name.")

        folder = self.root / channel / model_name / "v1"
        folder.mkdir(parents=True, exist_ok=True)

        target = folder / "model.joblib"

        descriptor, temporary = tempfile.mkstemp(
            prefix="model_",
            suffix=".tmp",
            dir=str(folder)
        )

        os.close(descriptor)

        try:
            joblib.dump(model, temporary, compress=3)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        manifest = {
            "schema_version": 1,
            "model_name": model_name,
            "channel": channel,
            "model_version": "v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "feature_count": int(feature_count),
            "feature_names": feature_names,
            "dataset_fingerprint": fingerprint,
            "threshold": float(threshold),
            "config": config,
            "versions": {
                "numpy": np.__version__,
                "scikit_learn": sklearn.__version__,
                "joblib": joblib.__version__
            },
            "artifact_sha256": sha256_file(target)
        }

        manifest_path = folder / "manifest.json"
        temporary_manifest = folder / "manifest.json.tmp"

        temporary_manifest.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        os.replace(temporary_manifest, manifest_path)

        return folder

    def load(self, channel, model_name):
        if channel not in ("a-1", "p-1"):
            raise ValueError("Invalid channel.")

        if model_name not in ("isolation_forest", "random_forest"):
            raise ValueError("Invalid model name.")

        folder = (
            self.root / channel / model_name / "v1"
        ).resolve()

        if self.root not in folder.parents:
            raise ValueError("Invalid model path.")

        manifest_path = folder / "manifest.json"
        model_path = folder / "model.joblib"

        if not manifest_path.is_file() or not model_path.is_file():
            raise FileNotFoundError("Model artifact not found.")

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        if sha256_file(model_path) != manifest["artifact_sha256"]:
            raise ValueError("Model checksum verification failed.")

        return joblib.load(model_path), manifest