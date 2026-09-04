"""Razorpay webhook receiver (Test Mode).

Verifies the X-Razorpay-Signature HMAC before accepting an event; then
records it in the audit trail. RefundShield remains defense-only: a
webhook never triggers account or payment actions — it only enriches the
log.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import get_settings
from app.core.audit import AuditTrail
from app.core.deps import get_audit

logger = logging.getLogger("refundshield.api.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    audit: AuditTrail = Depends(get_audit),
) -> dict:
    settings = get_settings()
    secret = getattr(settings, "razorpay_webhook_secret", None) or \
        request.headers.get("x-webhook-secret", "")
    if not secret:
        raise HTTPException(
            status_code=400,
            detail="Webhook secret not configured; refusing unsigned payload.")

    body = (await request.body()).decode("utf-8", errors="replace")
    signature = request.headers.get("x-razorpay-signature", "")

    from app.data.webhooks import verify_webhook
    from app.razorpay_client import RazorpayConfigError, RazorpayTestClient

    try:
        client = RazorpayTestClient(settings)
        verified = verify_webhook(body, signature, secret, client=client)
    except RazorpayConfigError:
        verified = False

    if not verified:
        audit.record(
            event_type="webhook.rejected",
            actor="razorpay-webhook",
            subject_type="webhook",
            subject_id="unknown",
            summary="Webhook signature verification failed",
        )
        raise HTTPException(status_code=400, detail="invalid signature")

    try:
        event = await request.json()
        event_name = event.get("event", "unknown")
    except Exception:
        event_name = "unparseable"

    audit.record(
        event_type="webhook.razorpay",
        actor="razorpay-webhook",
        subject_type="webhook",
        subject_id=event_name,
        summary=f"Verified webhook event '{event_name}'",
        payload={"event": event_name},
    )
    return {"status": "logged", "event": event_name}
