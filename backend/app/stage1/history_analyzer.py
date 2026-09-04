"""Stage 1 · Customer & order history signals."""

from __future__ import annotations

import logging

from app.core.models import HistoryEvidence

logger = logging.getLogger("refundshield.stage1.history")

NEW_ACCOUNT_DAYS = 30


class HistoryAnalyzer:
    def analyze(
        self,
        *,
        customer_age_days: int,
        total_orders: int,
        total_prior_claims: int,
        prior_fraudulent_flags: int,
        chargeback_count: int,
        velocity_24h: int,
    ) -> HistoryEvidence:
        refund_ratio = (total_prior_claims / total_orders) if total_orders else 0.0
        ev = HistoryEvidence(
            customer_age_days=customer_age_days,
            total_orders=total_orders,
            total_refunds=total_prior_claims,
            refund_ratio=round(min(1.0, refund_ratio), 3),
            chargeback_count=chargeback_count,
            prior_claim_images_reused=prior_fraudulent_flags,
            is_new_account=customer_age_days < NEW_ACCOUNT_DAYS,
            velocity_24h=velocity_24h,
        )

        if ev.is_new_account:
            ev.notes.append(f"Account only {customer_age_days} days old.")
        if ev.refund_ratio >= 0.5 and total_orders >= 3:
            ev.notes.append(
                f"{ev.total_refunds} refunds on {total_orders} orders "
                f"({ev.refund_ratio:.0%} refund rate)."
            )
        if chargeback_count:
            ev.notes.append(f"{chargeback_count} prior chargeback(s) on file.")
        if velocity_24h >= 3:
            ev.notes.append(f"{velocity_24h} orders in the last 24 hours.")
        return ev

    def score(self, ev: HistoryEvidence) -> float:
        s = 0.10  # baseline: history alone is never conclusive
        if ev.is_new_account:
            s += 0.20
        s += 0.35 * min(1.0, ev.refund_ratio)
        s += 0.30 * min(1.0, ev.chargeback_count / 2.0)
        if ev.velocity_24h >= 3:
            s += 0.20
        if ev.prior_claim_images_reused:
            s += 0.10 * min(1.0, ev.prior_claim_images_reused / 2.0)
        return round(min(1.0, s), 3)
