"""Tests for the Razorpay Test Mode wrapper (network fully mocked)."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.razorpay_client import RazorpayAPIError, RazorpayConfigError, RazorpayTestClient


def make_client(underlying: MagicMock | None = None) -> RazorpayTestClient:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.razorpay_client.Client", MagicMock(return_value=underlying or MagicMock()))
        return RazorpayTestClient(
            Settings(
                razorpay_key_id="rzp_test_testkey123",
                razorpay_key_secret="secret",
                _env_file=None,
            )
        )


def test_rejects_missing_credentials() -> None:
    with pytest.raises(RazorpayConfigError, match="not configured"):
        RazorpayTestClient(Settings(razorpay_key_id="", razorpay_key_secret="", _env_file=None))


def test_live_key_rejected_at_config_level() -> None:
    # Config layer is the first guard: pydantic refuses LIVE keys outright.
    with pytest.raises(ValidationError):
        Settings(
            razorpay_key_id="rzp_live_badkey",
            razorpay_key_secret="s",
            _env_file=None,
        )


def test_live_key_rejected_at_client_level() -> None:
    # Defense in depth: even if a live key sneaks past config (e.g. mutated
    # in memory), the client refuses to initialise.
    cfg = Settings(
        razorpay_key_id="rzp_test_ok",
        razorpay_key_secret="s",
        _env_file=None,
    )
    cfg.razorpay_key_id = "rzp_live_badkey"
    with pytest.raises(RazorpayConfigError, match="TEST MODE only"):
        RazorpayTestClient(cfg)


def test_fetch_orders_parses_payload() -> None:
    sdk = MagicMock()
    sdk.order.all.return_value = {
        "entity": "collection",
        "count": 1,
        "items": [
            {
                "id": "order_A1",
                "amount": 129900,
                "currency": "INR",
                "status": "paid",
                "receipt": "rcpt-7",
                "notes": {"channel": "web"},
            }
        ],
    }
    client = make_client(sdk)
    orders = client.fetch_orders()
    assert len(orders) == 1
    o = orders[0]
    assert o.id == "order_A1"
    assert o.amount == 129900
    assert o.status == "paid"


def test_fetch_payments_parses_payload() -> None:
    sdk = MagicMock()
    sdk.payment.all.return_value = {
        "items": [
            {
                "id": "pay_X1",
                "order_id": "order_A1",
                "method": "upi",
                "amount": 129900,
                "status": "captured",
                "captured": True,
                "email": "a@b.c",
                "notes": {},
            }
        ]
    }
    client = make_client(sdk)
    payments = client.fetch_payments()
    assert payments[0].captured is True
    assert payments[0].method == "upi"


def test_api_error_is_wrapped() -> None:
    from razorpay.errors import BadRequestError

    sdk = MagicMock()
    sdk.order.all.side_effect = BadRequestError("bad", "Bad request")
    client = make_client(sdk)
    with pytest.raises(RazorpayAPIError):
        client.fetch_orders()


def test_refund_creation_passes_amount_and_notes() -> None:
    sdk = MagicMock()
    sdk.payment.refund.return_value = {
        "id": "rfnd_1",
        "payment_id": "pay_X1",
        "amount": 50000,
        "currency": "INR",
        "status": "processed",
    }
    client = make_client(sdk)
    r = client.create_test_refund("pay_X1", 50000, {"reason": "test"})
    sdk.payment.refund.assert_called_once_with("pay_X1", {"amount": 50000, "notes": {"reason": "test"}})
    assert r.status == "processed"


def test_webhook_signature_rejects_bad_hmac() -> None:
    from razorpay.errors import SignatureVerificationError

    sdk = MagicMock()
    sdk.utility.verify_webhook_signature.side_effect = SignatureVerificationError(
        "bad signature"
    )
    client = make_client(sdk)
    assert client.verify_webhook_signature("body", "deadbeef", "whsec_test") is False
