"""Evaluation metrics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.db import Database
from app.core.deps import get_db
from app.evaluation.metrics import EvaluationService

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/metrics")
def metrics(
    threshold: float = Query(default=0.6, ge=0.0, le=1.0),
    db: Database = Depends(get_db),
) -> dict:
    svc = EvaluationService(db)
    out: dict = {}
    try:
        out["claims"] = svc.claim_metrics(threshold)
    except LookupError as exc:
        out["claims"] = {"unavailable": str(exc)}
    try:
        out["rings"] = svc.ring_metrics()
    except LookupError as exc:
        out["rings"] = {"unavailable": str(exc)}
    return out
