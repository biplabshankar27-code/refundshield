"""Ring detection endpoints (Stage 2)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.audit import AuditTrail
from app.core.deps import get_audit, get_claim_analyzer, get_ring_service
from app.core.models import RingDetectionResult
from app.stage1.claim_analyzer import ClaimAnalyzer
from app.stage2.ring_detection import RingDetectionService

router = APIRouter(prefix="/api/rings", tags=["stage2"])


@router.post("/detect", response_model=RingDetectionResult)
def detect_rings(
    analyzer: ClaimAnalyzer = Depends(get_claim_analyzer),
    service: RingDetectionService = Depends(get_ring_service),
    audit: AuditTrail = Depends(get_audit),
) -> RingDetectionResult:
    """Run the full Stage 2 pipeline (Stage 1 backfill + graph + Louvain)."""
    return service.run(claim_analyzer=analyzer)


@router.get("/latest", response_model=RingDetectionResult | None)
def latest_run(service: RingDetectionService = Depends(get_ring_service)) -> dict | None:
    """Return the most recent stored ring detection run, if any."""
    import datetime as _dt

    db = service.db
    with db.connect() as conn:
        row = conn.execute(
            "SELECT run_id, payload_json, created_at FROM ring_runs "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload_json"])
    return payload
