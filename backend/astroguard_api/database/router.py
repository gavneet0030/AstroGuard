
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from astroguard_api.database.base import get_db
from astroguard_api.database import repository, service

from astroguard_api.database.schemas import (
    TelemetryRecordCreate,
    TelemetryRecordRead,
    ExperimentCreate,
    ExperimentRead,
    ModelArtifactCreate,
    ModelArtifactRead,
    InferenceEventCreate,
    InferenceEventRead,
)


router = APIRouter(tags=["database"])


def _database_failure(db: Session, detail: str):
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


@router.get("/system/database/health")
def database_health(db: Session = Depends(get_db)):
    try:
        return service.database_health(db)
    except SQLAlchemyError:
        _database_failure(db, "Database unavailable.")


@router.post(
    "/telemetry/records",
    response_model=TelemetryRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_telemetry(
    payload: TelemetryRecordCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.save_telemetry(db, payload.model_dump())
    except SQLAlchemyError:
        _database_failure(db, "Unable to persist telemetry.")


@router.get(
    "/telemetry/records",
    response_model=list[TelemetryRecordRead],
)
def get_telemetry(
    channel: str | None = Query(default=None, pattern=r"^(a-1|p-1)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return repository.list_telemetry_records(db, channel, limit)


@router.post(
    "/experiments",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.save_experiment(db, payload.model_dump())
    except SQLAlchemyError:
        _database_failure(db, "Unable to persist experiment.")


@router.get(
    "/experiments",
    response_model=list[ExperimentRead],
)
def get_experiments(
    channel: str | None = Query(default=None, pattern=r"^(a-1|p-1)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return repository.list_experiments(db, channel, limit)


@router.post(
    "/models/register",
    response_model=ModelArtifactRead,
    status_code=status.HTTP_201_CREATED,
)
def register_model(
    payload: ModelArtifactCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.save_model_artifact(db, payload.model_dump())
    except service.DatabaseConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError:
        _database_failure(db, "Unable to register model.")


@router.get(
    "/models/registry",
    response_model=list[ModelArtifactRead],
)
def get_model_registry(
    channel: str | None = Query(default=None, pattern=r"^(a-1|p-1)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return repository.list_model_artifacts(db, channel, limit)


@router.post(
    "/inference/events",
    response_model=InferenceEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inference_event(
    payload: InferenceEventCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.save_inference_event(db, payload.model_dump())
    except SQLAlchemyError:
        _database_failure(db, "Unable to persist inference event.")


@router.get(
    "/inference/events",
    response_model=list[InferenceEventRead],
)
def get_inference_events(
    channel: str | None = Query(default=None, pattern=r"^(a-1|p-1)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return repository.list_inference_events(db, channel, limit)
