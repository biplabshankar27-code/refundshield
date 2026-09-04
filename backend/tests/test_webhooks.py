"""Tests for webhook-style event simulation (real HMAC path)."""

from app.config import get_settings
from app.data.webhooks import (
    build_webhook_event,
    payment_captured_payload,
    refund_processed_payload,
    sign_body,
    verify_webhook,
)
from app.razorpay_client import RazorpayTestClient


def real_client() -> RazorpayTestClient:
    # Uses .env test credentials; Client construction performs no network I/O.
    return RazorpayTestClient(get_settings())


def test_roundtrip_signature_verification() -> None:
    secret = "whsec_test_secret"
    body, sig = build_webhook_event(
        "payment.captured",
        payment_captured_payload("pay_1", "order_1", 100000),
        secret,
    )
    assert verify_webhook(body, sig, secret, client=real_client()) is True


def test_tampered_body_fails() -> None:
    secret = "whsec_test_secret"
    body, sig = build_webhook_event(
        "refund.processed",
        refund_processed_payload("rfnd_1", "pay_1", 50000),
        secret,
    )
    tampered = body.replace("processed", "failed")
    assert verify_webhook(tampered, sig, secret, client=real_client()) is False


def test_wrong_secret_fails() -> None:
    body, sig = build_webhook_event(
        "payment.captured", payment_captured_payload("pay_2", "order_2", 1), "s1"
    )
    assert verify_webhook(body, sig, "s2", client=real_client()) is False


def test_sign_body_is_deterministic() -> None:
    assert sign_body("hello", "k") == sign_body("hello", "k")
    assert sign_body("hello", "k") != sign_body("hellO", "k")
