"""Stage 1 orchestrator — turns one refund/return claim into a Stage1Result.

Pipeline:
    image_analyzer → history_analyzer → text_analyzer →
    payment_delivery_signals → scorer → Stage1Result (+ persistence/audit)

Razorpay enrichment is mirror-first (local SQLite mirror populated by the
sync service) with an optional live Test Mode fetch as fallback. The
service degrades gracefully to simulated facts when Razorpay is absent —
Stage 1 never depends on the network to stay testable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.models import (
    ClaimInput,
    SignalName,
    Stage1Result,
)
from app.razorpay_client import RazorpayAPIError, RazorpayTestClient
from app.stage1.history_analyzer import HistoryAnalyzer
from app.stage1.image_analyzer import ImageAnalyzer
from app.stage1.payment_delivery_signals import PaymentDeliveryAnalyzer
from app.stage1.scorer import ClaimScorer
from app.stage1.text_analyzer import TextAnalyzer

logger = logging.getLogger("refundshield.stage1")


class ClaimAnalyzer:
    def __init__(
        self,
        db: Database,
        audit: AuditTrail,
        razorpay: RazorpayTestClient | None = None,
        enable_razorpay: bool = True,
    ) -> None:
        self.db = db
        self.audit = audit
        self.razorpay = razorpay if enable_razorpay else None
        self.image_analyzer = ImageAnalyzer()
        self.history_analyzer = HistoryAnalyzer()
        self.text_analyzer = TextAnalyzer()
        self.payment_analyzer = PaymentDeliveryAnalyzer()
        self.scorer = ClaimScorer()

    # ------------------------------------------------------------------ API
    def analyze(self, claim: ClaimInput) -> Stage1Result:
        order = self._load_order(claim.order_id)
        customer = self._load_customer(claim.customer_id)
        payment = self._load_payment_facts(order, claim.use_razorpay_enrichment)

        # ---- 1. image evidence ------------------------------------------
        prior_images = self._prior_claim_images(
            claim.customer_id, exclude_claim_id=claim.claim_id
        )
        image_ev = self.image_analyzer.analyze(
            image_base64=claim.image_base64,
            image_path=claim.image_path,
            prior_images=prior_images,
        )

        # ---- 2. history evidence ----------------------------------------
        history = self._history_facts(claim.customer_id, claim.claim_id)
        history_ev = self.history_analyzer.analyze(**history)

        # ---- 3. text evidence -------------------------------------------
        text_ev = self.text_analyzer.analyze(claim.claim_text)

        # ---- 4. payment & delivery evidence ------------------------------
        claim_created_at = claim.claim_created_at or datetime.now(timezone.utc)
        delivered_at = (
            (claim.delivered_at or self._parse(order["delivered_at"]))
            if order else claim.delivered_at
        )
        pd_ev = self.payment_analyzer.analyze(
            amount_claimed_paise=int(claim.amount_claimed_inr * 100),
            order_amount_paise=order["amount_paise"] if order else None,
            order_status=order["status"] if order else None,
            payment_method=payment.get("method"),
            payment_captured=payment.get("captured"),
            delivery_status=claim.delivery_status,
            delivered_at=delivered_at,
            claim_created_at=claim_created_at,
            address_changed_after_order=claim.address_changed_after_order,
            razorpay_enriched=bool(payment.get("razorpay_enriched")),
            payment_id=payment.get("payment_id"),
        )

        # ---- 5. score & explain ------------------------------------------
        scores: dict[SignalName, float] = {
            "image_evidence": self.image_analyzer.score(image_ev),
            "history_evidence": self.history_analyzer.score(history_ev),
            "payment_delivery_evidence": self.payment_analyzer.score(pd_ev),
            "text_evidence": self.text_analyzer.score(text_ev),
        }
        details: dict[SignalName, str] = {
            "image_evidence": self._image_detail(image_ev),
            "history_evidence": "; ".join(history_ev.notes) or "no notable history",
            "payment_delivery_evidence": "; ".join(pd_ev.notes) or "payment & delivery consistent",
            "text_evidence": "; ".join(text_ev.notes) or "text reads normally",
        }
        signals = self.scorer.build_signals(scores, details)
        risk_score = self.scorer.score(signals)
        band = self.scorer.band(risk_score)
        priority = self.scorer.priority(band)
        action = self.scorer.action(band)
        reason = self.scorer.explain(signals, risk_score, band, action)

        result = Stage1Result(
            claim_id=claim.claim_id,
            order_id=claim.order_id,
            customer_id=claim.customer_id,
            risk_score=risk_score,
            risk_band=band,
            review_priority=priority,
            recommended_action=action,  # type: ignore[arg-type]
            signals=signals,
            image_evidence=image_ev,
            history_evidence=history_ev,
            payment_delivery_evidence=pd_ev,
            text_evidence=text_ev,
            reason=reason,
        )

        self._persist(result)
        self.audit.record(
            event_type="stage1.analysis",
            actor="stage1",
            subject_type="claim",
            subject_id=claim.claim_id,
            summary=(
                f"Claim {claim.claim_id} scored {risk_score:.2f} ({band}) — "
                f"{action}"
            ),
            payload=result.model_dump(mode="json"),
        )
        return result

    # -------------------------------------------------------------- loaders
    def _load_order(self, order_id: str) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE order_id = ?", (order_id,)
            ).fetchone()
        return dict(row) if row else None

    def _load_customer(self, customer_id: str) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
            ).fetchone()
        return dict(row) if row else None

    def _load_payment_facts(self, order: dict | None,
                            enabled: bool) -> dict:
        """Mirror-first payment facts with live Test Mode fallback."""
        facts: dict = {"method": None, "captured": None,
                       "payment_id": None, "razorpay_enriched": False}
        if not order:
            return facts
        payment_id = order.get("payment_id")
        if payment_id:
            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT * FROM razorpay_payments WHERE razorpay_payment_id = ?",
                    (payment_id,),
                ).fetchone()
            if row:
                facts.update(method=row["method"], captured=bool(row["captured"]),
                             payment_id=payment_id, razorpay_enriched=True)
                return facts
            if self.razorpay and enabled:
                try:
                    p = self.razorpay.fetch_payment(payment_id)
                    facts.update(method=p.method, captured=p.captured,
                                 payment_id=payment_id, razorpay_enriched=True)
                    return facts
                except RazorpayAPIError as exc:
                    logger.warning("Razorpay enrichment failed for %s: %s",
                                   payment_id, exc)
        return facts

    def _history_facts(self, customer_id: str, current_claim_id: str) -> dict:
        with self.db.connect() as conn:
            cust = conn.execute(
                "SELECT created_at FROM customers WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
            orders = conn.execute(
                "SELECT COUNT(*) AS n FROM orders WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()["n"]
            claims = conn.execute(
                """SELECT claim_id, image_path FROM claims
                   WHERE customer_id = ? AND claim_id != ?""",
                (customer_id, current_claim_id),
            ).fetchall()
            recent = conn.execute(
                """SELECT COUNT(*) AS n FROM orders
                   WHERE customer_id = ? AND created_at >= datetime('now', '-1 day')""",
                (customer_id,),
            ).fetchone()["n"]

        created = self._parse(cust["created_at"]) if cust else None
        age_days = (datetime.now(timezone.utc) - created).days if created else 0
        return {
            "customer_age_days": max(0, age_days),
            "total_orders": int(orders),
            "total_prior_claims": len(claims),
            "prior_fraudulent_flags": 0,   # stage1 never sees ground truth
            "chargeback_count": 0,         # would come from disputes API in prod
            "velocity_24h": int(recent),
        }

    def _prior_claim_images(self, customer_id: str,
                            exclude_claim_id: str) -> list[tuple[str, str]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT order_id, image_path FROM claims
                   WHERE customer_id = ? AND claim_id != ? AND image_path IS NOT NULL""",
                (customer_id, exclude_claim_id),
            ).fetchall()
        return [(r["order_id"], r["image_path"]) for r in rows]

    # ------------------------------------------------------------ persistence
    def _persist(self, result: Stage1Result) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO claim_results (claim_id, order_id, customer_id,
                   risk_score, risk_band, priority, action, reason,
                   payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.claim_id, result.order_id, result.customer_id,
                    result.risk_score, result.risk_band, result.review_priority,
                    result.recommended_action, result.reason,
                    json.dumps(result.model_dump(mode="json"), default=str),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.execute(
                "UPDATE claims SET status = 'analyzed' WHERE claim_id = ?",
                (result.claim_id,),
            )

    @staticmethod
    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _image_detail(ev) -> str:
        bits: list[str] = []
        if ev.is_reused and ev.reused_of_order_id:
            bits.append(f"reused from order {ev.reused_of_order_id}")
        elif ev.similarity_to_prior_claim is not None:
            bits.append(f"{ev.similarity_to_prior_claim:.0%} similar to a prior claim")
        if ev.ai_generated_suspected:
            bits.append("AI-generation suspected")
        if ev.metadata_inconsistent:
            bits.append("missing metadata")
        if not ev.provided:
            bits.append("no image provided")
        return ", ".join(bits) or "image looks original"


def build_claim_input(row: dict, order: dict | None) -> ClaimInput:
    """Assemble a ClaimInput from the local claims/orders tables."""
    delivered_at = None
    if order and order.get("delivered_at"):
        try:
            delivered_at = datetime.fromisoformat(order["delivered_at"])
        except ValueError:
            delivered_at = None
    delivered = delivered_at is not None and delivered_at <= datetime.now(timezone.utc)
    created_at = None
    if row.get("created_at"):
        try:
            created_at = datetime.fromisoformat(row["created_at"])
        except ValueError:
            created_at = None
    return ClaimInput(
        claim_id=row["claim_id"],
        order_id=row["order_id"],
        customer_id=row["customer_id"],
        claim_text=row.get("text", ""),
        amount_claimed_inr=row["amount_paise"] / 100.0,
        image_path=row.get("image_path"),
        delivery_status="delivered" if delivered else "in_transit",
        delivered_at=delivered_at,
        claim_created_at=created_at,
        use_razorpay_enrichment=False,
    )
