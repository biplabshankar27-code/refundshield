"""Stage 1 scorer contract tests — including the defense-only guarantee."""

import pytest

from app.stage1.scorer import ACTIONS, WEIGHTS, ClaimScorer


@pytest.fixture()
def scorer() -> ClaimScorer:
    return ClaimScorer()


def _signals(scores: dict[str, float]) -> list:
    return scorer_signals(scores)


def scorer_signals(scores: dict[str, float]) -> list:
    s = ClaimScorer()
    return s.build_signals(scores, {k: "detail" for k in scores})


class TestWeights:
    def test_weights_sum_to_one(self) -> None:
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_signals_carry_contribution(self) -> None:
        signals = scorer_signals({"image_evidence": 0.8, "text_evidence": 0.5})
        img = next(s for s in signals if s.name == "image_evidence")
        assert img.contribution == pytest.approx(0.8 * WEIGHTS["image_evidence"])


class TestBands:
    def test_band_thresholds(self, scorer: ClaimScorer) -> None:
        assert scorer.band(0.10) == "low"
        assert scorer.band(0.40) == "medium"
        assert scorer.band(0.65) == "high"
        assert scorer.band(0.90) == "critical"

    def test_priority_follows_band(self, scorer: ClaimScorer) -> None:
        assert scorer.priority("critical") == "P0_now"
        assert scorer.priority("low") == "P3_backlog"

    def test_score_monotonic(self, scorer: ClaimScorer) -> None:
        low = scorer.score(scorer_signals({k: 0.1 for k in WEIGHTS}))
        high = scorer.score(scorer_signals({k: 0.9 for k in WEIGHTS}))
        assert high > low


class TestDefenseOnly:
    def test_no_block_action_exists(self) -> None:
        for band, action in ACTIONS.items():
            assert action in {"approve_normally", "manual_review",
                              "manual_review_urgent"}
            assert "block" not in action

    def test_all_bands_map_to_actions(self, scorer: ClaimScorer) -> None:
        for band in ("low", "medium", "high", "critical"):
            assert scorer.action(band) in ACTIONS.values()


class TestExplanation:
    def test_high_risk_reason_mentions_review(self, scorer: ClaimScorer) -> None:
        signals = scorer_signals({
            "image_evidence": 0.9, "text_evidence": 0.7,
            "payment_delivery_evidence": 0.2, "history_evidence": 0.3,
        })
        score = scorer.score(signals)
        reason = scorer.explain(signals, score, scorer.band(score),
                                scorer.action(scorer.band(score)))
        assert "review" in reason.lower()
        assert "never blocks" in reason
        assert str(round(score, 2)) in reason

    def test_low_risk_reason_mentions_normal_processing(self, scorer: ClaimScorer) -> None:
        signals = scorer_signals({k: 0.05 for k in WEIGHTS})
        score = scorer.score(signals)
        reason = scorer.explain(signals, score, "low", "approve_normally")
        assert "normally" in reason.lower()
