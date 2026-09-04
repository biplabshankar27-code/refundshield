"""Stage 1 unit tests: image / history / text / payment-delivery analyzers."""

from datetime import datetime, timedelta, timezone

from PIL import Image

from app.data.images import generate_evidence_image
from app.stage1.history_analyzer import HistoryAnalyzer
from app.stage1.image_analyzer import ImageAnalyzer
from app.stage1.payment_delivery_signals import PaymentDeliveryAnalyzer
from app.stage1.text_analyzer import TextAnalyzer


# ---------------------------------------------------------------- image
class TestImageAnalyzer:
    def setup_method(self) -> None:
        self.an = ImageAnalyzer()

    def test_reused_image_is_detected(self, tmp_path) -> None:
        src = tmp_path / "orig.png"
        dup = tmp_path / "dup.png"
        generate_evidence_image(src, seed=1, kind="unique")
        generate_evidence_image(dup, seed=2, kind="copy", source_path=src)

        ev = self.an.analyze(
            image_base64=None, image_path=str(dup),
            prior_images=[("ORD-OLD", str(src))],
        )
        assert ev.is_reused
        assert ev.reused_of_order_id == "ORD-OLD"
        assert self.an.score(ev) >= 0.9

    def test_noisy_reuse_is_detected(self, tmp_path) -> None:
        src = tmp_path / "orig.png"
        noisy = tmp_path / "noisy.png"
        generate_evidence_image(src, seed=3, kind="unique")
        generate_evidence_image(noisy, seed=4, kind="noise", source_path=src)

        ev = self.an.analyze(
            image_base64=None, image_path=str(noisy),
            prior_images=[("ORD-X", str(src))],
        )
        assert ev.is_reused, "noisy near-duplicate should be flagged"

    def test_unique_image_is_not_flagged(self, tmp_path) -> None:
        a = tmp_path / "a.png"
        b = tmp_path / "b.png"
        generate_evidence_image(a, seed=5, kind="unique")
        generate_evidence_image(b, seed=6, kind="unique")

        ev = self.an.analyze(
            image_base64=None, image_path=str(a),
            prior_images=[("ORD-Y", str(b))],
        )
        assert not ev.is_reused
        assert not ev.ai_generated_suspected
        assert self.an.score(ev) <= 0.5  # metadata note only

    def test_ai_image_is_suspected(self, tmp_path) -> None:
        p = tmp_path / "ai.png"
        generate_evidence_image(p, seed=7, kind="ai")
        ev = self.an.analyze(image_base64=None, image_path=str(p), prior_images=[])
        assert ev.ai_generated_suspected
        assert ev.ai_generated_score >= 0.65

    def test_missing_image_is_mildly_risky(self) -> None:
        ev = self.an.analyze(image_base64=None, image_path=None, prior_images=[])
        assert not ev.provided
        assert self.an.score(ev) == 0.25

    def test_corrupt_image_does_not_crash(self, tmp_path) -> None:
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"not-an-image")
        ev = self.an.analyze(image_base64=None, image_path=str(bad), prior_images=[])
        assert not ev.provided


# ---------------------------------------------------------------- history
class TestHistoryAnalyzer:
    def setup_method(self) -> None:
        self.an = HistoryAnalyzer()

    def _hist(self, **kw) -> dict:
        base = dict(customer_age_days=400, total_orders=10,
                    total_prior_claims=1, prior_fraudulent_flags=0,
                    chargeback_count=0, velocity_24h=0)
        base.update(kw)
        return base

    def test_clean_veteran_scores_low(self) -> None:
        ev = self.an.analyze(**self._hist())
        assert self.an.score(ev) <= 0.2

    def test_new_account_with_many_refunds_scores_high(self) -> None:
        ev = self.an.analyze(**self._hist(
            customer_age_days=10, total_orders=6, total_prior_claims=5))
        s = self.an.score(ev)
        assert s >= 0.55
        assert ev.is_new_account
        assert any("refund rate" in n for n in ev.notes)

    def test_chargebacks_raise_score(self) -> None:
        ev = self.an.analyze(**self._hist(chargeback_count=3))
        assert self.an.score(ev) >= 0.4

    def test_velocity_flagged(self) -> None:
        ev = self.an.analyze(**self._hist(velocity_24h=5))
        assert self.an.score(ev) >= 0.3


# ---------------------------------------------------------------- text
class TestTextAnalyzer:
    def setup_method(self) -> None:
        self.an = TextAnalyzer()

    def test_threat_text_scores_high(self) -> None:
        ev = self.an.analyze(
            "Refund my money NOW or I will file a chargeback and a consumer "
            "court case today itself.")
        assert self.an.score(ev) >= 0.5
        assert ev.threat_score >= 0.5
        assert any("chargeback" in p for p in ev.matched_patterns)

    def test_polite_text_scores_low(self) -> None:
        ev = self.an.analyze(
            "The earbuds arrived with a small crack. Packaging was fine, "
            "would like a refund please.")
        assert self.an.score(ev) <= 0.15

    def test_empty_text_is_neutral(self) -> None:
        ev = self.an.analyze("")
        assert self.an.score(ev) == 0.0

    def test_delivery_miss_pattern_detected(self) -> None:
        ev = self.an.analyze("The package never arrived at all.")
        assert any("never arrived" in p for p in ev.matched_patterns)


# ------------------------------------------------- payment & delivery
class TestPaymentDelivery:
    def setup_method(self) -> None:
        self.an = PaymentDeliveryAnalyzer()

    def _kw(self, **kw) -> dict:
        base = dict(
            amount_claimed_paise=100000, order_amount_paise=100000,
            order_status="paid", payment_method="upi", payment_captured=True,
            delivery_status="delivered",
            delivered_at=datetime.now(timezone.utc) - timedelta(days=4),
            claim_created_at=datetime.now(timezone.utc),
            address_changed_after_order=False,
        )
        base.update(kw)
        return base

    def test_clean_claim_scores_low(self) -> None:
        ev = self.an.analyze(**self._kw())
        assert self.an.score(ev) <= 0.15

    def test_inflated_claim_strong_signal(self) -> None:
        ev = self.an.analyze(**self._kw(amount_claimed_paise=160000))
        assert ev.amount_mismatch
        assert self.an.score(ev) >= 0.7

    def test_claim_before_delivery(self) -> None:
        ev = self.an.analyze(**self._kw(
            delivery_status="in_transit",
            delivered_at=datetime.now(timezone.utc) + timedelta(days=2),
        ))
        assert ev.claimed_before_delivery
        assert self.an.score(ev) >= 0.7

    def test_reflex_claim_after_delivery(self) -> None:
        delivered = datetime.now(timezone.utc) - timedelta(hours=2)
        ev = self.an.analyze(**self._kw(delivered_at=delivered))
        assert ev.days_between_delivery_and_claim is not None
        assert ev.days_between_delivery_and_claim < 1
        assert self.an.score(ev) >= 0.4

    def test_address_change_adds_risk(self) -> None:
        ev = self.an.analyze(**self._kw(address_changed_after_order=True))
        assert self.an.score(ev) > self.an.score(self.an.analyze(**self._kw()))
