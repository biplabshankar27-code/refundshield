"""Stage 1 · Payment & delivery signals.

Combines the claim's assertions with facts from the order record and the
Razorpay Test Mode payment mirror (method, captured status, amounts).
"""

from __future__ import annotations

from datetime import datetime

from app.core.models import PaymentDeliveryEvidence


class PaymentDeliveryAnalyzer:
    def analyze(
        self,
        *,
        amount_claimed_paise: int,
        order_amount_paise: int | None,
        order_status: str | None,
        payment_method: str | None,
        payment_captured: bool | None,
        delivery_status: str,
        delivered_at: datetime | None,
        claim_created_at: datetime | None,
        address_changed_after_order: bool,
        razorpay_enriched: bool = False,
        payment_id: str | None = None,
    ) -> PaymentDeliveryEvidence:
        ev = PaymentDeliveryEvidence(
            payment_id=payment_id,
            payment_method=payment_method,
            payment_captured=bool(payment_captured),
            amount_paid_inr=round((order_amount_paise or 0) / 100.0, 2),
            amount_claimed_inr=round(amount_claimed_paise / 100.0, 2),
            order_status=order_status,
            delivery_status=delivery_status,  # type: ignore[arg-type]
            delivered_at=delivered_at,
            claim_created_at=claim_created_at,
            address_changed_after_order=address_changed_after_order,
            razorpay_enriched=razorpay_enriched,
        )

        if order_amount_paise and amount_claimed_paise > order_amount_paise:
            over = amount_claimed_paise / max(1, order_amount_paise) - 1.0
            ev.amount_mismatch = True
            ev.notes.append(
                f"Claimed ₹{ev.amount_claimed_inr:,.0f} exceeds paid "
                f"₹{ev.amount_paid_inr:,.0f} (+{over:.0%})."
            )

        if delivered_at and claim_created_at:
            days = (claim_created_at - delivered_at).total_seconds() / 86400.0
            ev.days_between_delivery_and_claim = round(days, 2)
            if days < 0:
                ev.claimed_before_delivery = True
                ev.notes.append("Claim filed BEFORE the order was delivered.")

        if ev.claimed_before_delivery:
            ev.notes.append("Claim precedes delivery — impossible for damage claims.")
        if address_changed_after_order:
            ev.notes.append("Shipping address changed after the order was placed.")
        if payment_captured is False and payment_id:
            ev.notes.append("Underlying payment is not captured at Razorpay.")
        return ev

    def score(self, ev: PaymentDeliveryEvidence) -> float:
        factors: list[float] = []
        if ev.amount_mismatch:
            over = ev.amount_claimed_inr - ev.amount_paid_inr
            over_ratio = over / ev.amount_paid_inr if ev.amount_paid_inr else 1.0
            factors.append(1.0 if over_ratio > 0.10 else 0.6)
        if ev.claimed_before_delivery:
            factors.append(0.85)
        elif ev.days_between_delivery_and_claim is not None:
            days = ev.days_between_delivery_and_claim
            if days < 1:
                factors.append(0.45)   # reflex claim seconds after delivery
            elif days < 2:
                factors.append(0.25)
        if ev.address_changed_after_order:
            factors.append(0.4)
        if ev.payment_id and not ev.payment_captured:
            factors.append(0.4)
        if ev.delivery_status == "failed":
            factors.append(0.35)

        if not factors:
            return 0.08  # nothing unusual — near-neutral signal
        return round(min(1.0, sum(factors) / len(factors) + 0.1 * (len(factors) - 1)), 3)
