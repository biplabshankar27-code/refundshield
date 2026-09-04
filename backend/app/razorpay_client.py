"""Razorpay Test Mode client wrapper.

Rules enforced here:
- Credentials come ONLY from Settings (environment / .env) — never hardcoded.
- LIVE keys are refused at construction time (belt & braces on top of config).
- Every API error is logged and re-raised as RazorpayAPIError.
- This wrapper never creates refunds unless explicitly asked; when it does,
  the action is Test Mode by construction and logged.
"""

import logging
from typing import Any

from razorpay import Client
from razorpay.errors import (
    BadRequestError,
    GatewayError,
    ServerError,
    SignatureVerificationError,
)

from app.config import Settings, get_settings
from app.core.models import RazorpayOrder, RazorpayPayment, RazorpayRefund

logger = logging.getLogger("refundshield.razorpay")


class RazorpayConfigError(RuntimeError):
    """Raised when credentials are missing or not Test Mode."""


class RazorpayAPIError(RuntimeError):
    """Raised when a Razorpay API call fails."""


class RazorpayTestClient:
    """Thin, typed wrapper over the official Razorpay Python SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        key_id, key_secret = cfg.razorpay_key_id, cfg.razorpay_key_secret

        if not key_id or not key_secret:
            raise RazorpayConfigError(
                "Razorpay credentials not configured. Set RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET in the environment (.env) — never in code."
            )
        if not key_id.startswith("rzp_test_"):
            raise RazorpayConfigError(
                "RefundShield integrates with Razorpay TEST MODE only. "
                f"Refusing key '{key_id[:12]}...'."
            )

        self._client: Client = Client(auth=(key_id, key_secret))
        logger.info("Razorpay TEST MODE client initialised (%s...)", key_id[:12])

    # ------------------------------------------------------------- Orders
    def fetch_orders(self, count: int = 100) -> list[RazorpayOrder]:
        data = self._call(lambda: self._client.order.all({"count": count}))
        items = data.get("items", []) if isinstance(data, dict) else data
        return [RazorpayOrder.model_validate(o) for o in items]

    def fetch_order(self, order_id: str) -> RazorpayOrder:
        data = self._call(lambda: self._client.order.fetch(order_id))
        return RazorpayOrder.model_validate(data)

    # ----------------------------------------------------------- Payments
    def fetch_payments(self, count: int = 100) -> list[RazorpayPayment]:
        data = self._call(lambda: self._client.payment.all({"count": count}))
        items = data.get("items", []) if isinstance(data, dict) else data
        return [RazorpayPayment.model_validate(p) for p in items]

    def fetch_payment(self, payment_id: str) -> RazorpayPayment:
        data = self._call(lambda: self._client.payment.fetch(payment_id))
        return RazorpayPayment.model_validate(data)

    # ------------------------------------------------------------ Refunds
    def fetch_refunds_for_payment(self, payment_id: str) -> list[RazorpayRefund]:
        data = self._call(lambda: self._client.payment.fetch_multiple_refund(payment_id))
        items = data.get("items", []) if isinstance(data, dict) else data
        return [RazorpayRefund.model_validate(r) for r in items]

    def fetch_refunds(self, count: int = 100) -> list[RazorpayRefund]:
        data = self._call(lambda: self._client.refund.all({"count": count}))
        items = data.get("items", []) if isinstance(data, dict) else data
        return [RazorpayRefund.model_validate(r) for r in items]

    def create_test_refund(
        self, payment_id: str, amount_paise: int, notes: dict[str, Any] | None = None
    ) -> RazorpayRefund:
        """Create a refund. Test Mode only (enforced at construction)."""
        logger.warning(
            "Creating TEST MODE refund of %d paise on payment %s", amount_paise, payment_id
        )
        data = self._call(
            lambda: self._client.payment.refund(
                payment_id, {"amount": amount_paise, "notes": notes or {}}
            )
        )
        return RazorpayRefund.model_validate(data)

    # ------------------------------------------------------ Webhook utils
    def verify_webhook_signature(self, body: str, signature: str, secret: str) -> bool:
        try:
            self._client.utility.verify_webhook_signature(body, signature, secret)
            return True
        except SignatureVerificationError:
            logger.warning("Webhook signature verification FAILED")
            return False

    # ------------------------------------------------------------ Internals
    def _call(self, fn):
        try:
            return fn()
        except (BadRequestError, GatewayError, ServerError) as exc:
            logger.error("Razorpay API error: %s", exc)
            raise RazorpayAPIError(str(exc)) from exc
        except Exception as exc:  # network errors, auth errors, etc.
            logger.error("Unexpected Razorpay client error: %s", exc)
            raise RazorpayAPIError(str(exc)) from exc
