"""Demo bootstrap + cost-of-delay + webhook simulation endpoints."""

import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.deps import get_audit, get_claim_analyzer, get_db
from app.data.generator import DatasetGenerator, GeneratorConfig, load_claims
from app.evaluation.metrics import EvaluationService
from app.stage1.claim_analyzer import ClaimAnalyzer, build_claim_input
from app.stage2.ring_detection import RingDetectionService

logger = logging.getLogger("refundshield.api.demo")

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _default_image_dir() -> str:
    """Where generated evidence images go (volume on Modal, repo locally)."""
    return os.environ.get("REFUNDSHIELD_IMAGE_DIR", "./synthetic_images")


class BootstrapConfig(BaseModel):
    seed: int = 42
    n_normal: int = 40
    n_fraudsters: int = 6
    n_rings: int = 2
    ring_size: int = 4
    n_adversarial_rings: int = 1
    adversarial_ring_size: int = 4
    force_regenerate: bool = False


@router.post("/bootstrap")
def bootstrap(
    cfg: BootstrapConfig | None = None,
    db: Database = Depends(get_db),
    audit: AuditTrail = Depends(get_audit),
    analyzer: ClaimAnalyzer = Depends(get_claim_analyzer),
) -> dict:
    """One-shot demo: generate data → Stage 1 → Stage 2. Idempotent unless forced."""
    cfg = cfg or BootstrapConfig()

    with db.connect() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"]

    if existing and not cfg.force_regenerate:
        gen_summary = {"skipped": True, "existing_claims": existing}
    else:
        gen = DatasetGenerator(db, GeneratorConfig(
            seed=cfg.seed,
            n_normal=cfg.n_normal,
            n_fraudsters=cfg.n_fraudsters,
            n_rings=cfg.n_rings,
            ring_size=cfg.ring_size,
            n_adversarial_rings=cfg.n_adversarial_rings,
            adversarial_ring_size=cfg.adversarial_ring_size,
            image_dir=_default_image_dir(),
        ))
        gen_summary = gen.generate().model_dump(mode="json")

    # Stage 1 for all pending claims
    with db.connect() as conn:
        done = {r["claim_id"] for r in conn.execute(
            "SELECT claim_id FROM claim_results").fetchall()}
        rows = [dict(r) for r in conn.execute("SELECT * FROM claims").fetchall()]
        orders = {o["order_id"]: dict(o) for o in conn.execute(
            "SELECT * FROM orders").fetchall()}
    pending = [r for r in rows if r["claim_id"] not in done]
    for row in pending:
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    # Stage 2
    service = RingDetectionService(db, audit)
    ring_result = service.run()
    service  # keep reference for clarity

    metrics = {}
    try:
        metrics["claims"] = EvaluationService(db).claim_metrics()
    except LookupError as exc:
        metrics["claims"] = {"unavailable": str(exc)}
    try:
        metrics["rings"] = EvaluationService(db).ring_metrics()
    except LookupError as exc:
        metrics["rings"] = {"unavailable": str(exc)}

    return {
        "generated": gen_summary,
        "claims_analyzed": len(rows),
        "claims_newly_analyzed": len(pending),
        "ring_run_id": ring_result.run_id,
        "rings_detected": len(ring_result.rings),
        "cost_of_delay": ring_result.cost_of_delay.model_dump(),
        "metrics": metrics,
    }


@router.get("/cost-of-delay")
def cost_of_delay(db: Database = Depends(get_db)) -> dict:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT payload_json, created_at FROM ring_runs "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no ring detection run yet")
    payload = json.loads(row["payload_json"])
    return {
        "run_id": payload["run_id"],
        "generated_at": row["created_at"],
        "baseline_daily_burn_inr": payload.get("baseline_daily_burn_inr", 0.0),
        "cost_of_delay": payload.get("cost_of_delay"),
        "rings": [
            {"ring_id": r["ring_id"], "ring_score": r["ring_score"],
             "size": r["size"], "estimated_exposure_inr": r["estimated_exposure_inr"]}
            for r in payload.get("rings", [])
        ],
    }


class SimulatedWebhook(BaseModel):
    event: str = Field(default="payment.captured")
    payload: dict = Field(default_factory=dict)
    secret: str = Field(default="", description="webhook secret used to sign")


@router.post("/simulate-webhook")
def simulate_webhook(
    wh: SimulatedWebhook,
    db: Database = Depends(get_db),
    audit: AuditTrail = Depends(get_audit),
) -> dict:
    """Build a Razorpay-shaped webhook, sign it, verify it, and log it."""
    from app.data.webhooks import build_webhook_event, verify_webhook
    from app.config import get_settings
    from app.razorpay_client import RazorpayConfigError, RazorpayTestClient

    body, signature = build_webhook_event(wh.event, wh.payload, wh.secret)
    try:
        client = RazorpayTestClient(get_settings())
        verified = verify_webhook(body, signature, wh.secret, client=client)
    except RazorpayConfigError:
        # verification needs test keys; fall back to local HMAC comparison
        import hashlib
        import hmac
        expected = hmac.new(wh.secret.encode(), body.encode(),
                            hashlib.sha256).hexdigest()
        verified = hmac.compare_digest(expected, signature)

    audit.record(
        event_type="webhook.simulated",
        actor="demo",
        subject_type="webhook",
        subject_id=wh.event,
        summary=f"Simulated webhook {wh.event} verified={verified}",
        payload={"event": wh.event, "verified": verified},
    )
    return {"event": wh.event, "signature": signature, "verified": verified}
