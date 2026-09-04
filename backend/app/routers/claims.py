"""Claim intelligence endpoints (Stage 1)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.deps import get_audit, get_claim_analyzer, get_db
from app.core.models import ClaimInput, Stage1Result
from app.stage1.claim_analyzer import ClaimAnalyzer

router = APIRouter(prefix="/api/claims", tags=["stage1"])


@router.post("/analyze", response_model=Stage1Result)
def analyze_claim(
    claim: ClaimInput,
    analyzer: ClaimAnalyzer = Depends(get_claim_analyzer),
    audit: AuditTrail = Depends(get_audit),
) -> Stage1Result:
    """Score a single refund/return request (Stage 1). Defense-only."""
    result = analyzer.analyze(claim)
    return result


@router.get("/results")
def list_results(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Database = Depends(get_db),
) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT claim_id, order_id, customer_id, risk_score, risk_band,
               priority, action, reason, payload_json, created_at
               FROM claim_results ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "claim_id": r["claim_id"],
            "order_id": r["order_id"],
            "customer_id": r["customer_id"],
            "risk_score": r["risk_score"],
            "risk_band": r["risk_band"],
            "review_priority": r["priority"],
            "recommended_action": r["action"],
            "reason": r["reason"],
            "created_at": r["created_at"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


@router.get("/{claim_id}")
def get_result(
    claim_id: str,
    db: Database = Depends(get_db),
) -> dict:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT payload_json, created_at FROM claim_results WHERE claim_id = ?",
            (claim_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"claim {claim_id} not analyzed")
    return {"claim_id": claim_id, "created_at": row["created_at"],
            "result": json.loads(row["payload_json"])}
