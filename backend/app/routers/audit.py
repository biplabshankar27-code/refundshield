"""Audit trail endpoints."""

from fastapi import APIRouter, Depends, Query

from app.core.audit import AuditTrail
from app.core.deps import get_audit
from app.core.models import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEvent])
def list_audit(
    event_type: str | None = None,
    subject_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    audit: AuditTrail = Depends(get_audit),
) -> list[AuditEvent]:
    return audit.list_events(
        event_type=event_type, subject_id=subject_id,
        limit=limit, offset=offset,
    )


@router.get("/count")
def audit_count(audit: AuditTrail = Depends(get_audit)) -> dict:
    return {"events": audit.count()}
