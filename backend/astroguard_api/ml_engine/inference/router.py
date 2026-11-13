from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import InferenceService


def create_ml_router(project_root):
    router = APIRouter(
        prefix="/api/v1/ml",
        tags=["ML Inference"]
    )

    root = Path(project_root).resolve()

    service = InferenceService(
        root / "artifacts" / "models" / "phase3"
    )

    class PredictionRequest(BaseModel):
        channel: str
        model: str
        features: list[list[float]] = Field(min_length=1)

    @router.get("/status")
    def status():
        return {
            "status": "available",
            "models": [
                "isolation_forest",
                "random_forest"
            ]
        }

    @router.get("/models")
    def models():
        results = []

        for channel in ("a-1", "p-1"):
            for model_name in (
                "isolation_forest",
                "random_forest"
            ):
                path = (
                    service.registry.root /
                    channel / model_name / "v1" / "manifest.json"
                )

                if path.is_file():
                    import json
                    results.append(
                        json.loads(path.read_text(encoding="utf-8"))
                    )

        return {"count": len(results), "items": results}

    @router.post("/predict")
    def predict(request: PredictionRequest):
        try:
            return service.predict(
                request.channel,
                request.model,
                request.features
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Model not found."
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc)
            )

    return router