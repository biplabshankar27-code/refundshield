"""Webhook-style event simulation for Razorpay Test Mode.

Real Razorpay webhooks sign the raw request body with HMAC-SHA256 using
the webhook secret. We produce the same shape so signature verification
(code path included) is exercised end-to-end without a public endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.razorpay_client import RazorpayTestClient


def sign_body(body: str, secret: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def build_webhook_event(event: str, payload: dict[str, Any],
                        secret: str) -> tuple[str, str]:
    """Return ``(body_json, signature)`` for a simulated Razorpay webhook."""
    body = json.dumps({"event": event, "payload": payload}, default=str)
    return body, sign_body(body, secret)


def verify_webhook(body: str, signature: str, secret: str,
                   client: RazorpayTestClient | None = None) -> bool:
    """Verify via the SDK's utility to exercise the real code path."""
    if client is None:
        client = RazorpayTestClient()
    return client.verify_webhook_signature(body, signature, secret)


def payment_captured_payload(payment_id: str, order_id: str,
                             amount_paise: int) -> dict:
    return {
        "payment": {
            "entity": {
                "id": payment_id,
                "order_id": order_id,
                "amount": amount_paise,
                "currency": "INR",
                "status": "captured",
                "method": "upi",
            }
        }
    }


def refund_processed_payload(refund_id: str, payment_id: str,
                             amount_paise: int) -> dict:
    return {
        "refund": {
            "entity": {
                "id": refund_id,
                "payment_id": payment_id,
                "amount": amount_paise,
                "currency": "INR",
                "status": "processed",
            }
        }
    }
