"""FastAPI dependency wiring (singletons cached per process)."""

from functools import lru_cache

from fastapi import Depends, HTTPException

from app.config import Settings, get_settings
from app.core.audit import AuditTrail
from app.core.db import Database
from app.razorpay_client import RazorpayConfigError, RazorpayTestClient
from app.stage1.claim_analyzer import ClaimAnalyzer
from app.stage2.ring_detection import RingDetectionService


@lru_cache
def get_db() -> Database:
    return Database(get_settings().sqlite_path)


def get_audit(db: Database = Depends(get_db)) -> AuditTrail:
    return AuditTrail(db)


def get_razorpay(settings: Settings = Depends(get_settings)) -> RazorpayTestClient | None:
    """Optional: None when credentials are absent (demo runs fully offline)."""
    if not settings.credentials_configured:
        return None
    try:
        return RazorpayTestClient(settings)
    except RazorpayConfigError:
        return None


def get_claim_analyzer(
    db: Database = Depends(get_db),
    audit: AuditTrail = Depends(get_audit),
    razorpay: RazorpayTestClient | None = Depends(get_razorpay),
) -> ClaimAnalyzer:
    return ClaimAnalyzer(db, audit, razorpay=razorpay, enable_razorpay=True)


def get_ring_service(
    db: Database = Depends(get_db),
    audit: AuditTrail = Depends(get_audit),
) -> RingDetectionService:
    return RingDetectionService(db, audit)


def get_db_or_503(db: Database = Depends(get_db)) -> Database:
    if db is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    return db
