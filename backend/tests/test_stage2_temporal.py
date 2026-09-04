"""Stage 2 · Temporal detection tests."""

from datetime import datetime, timedelta, timezone

from app.stage2.temporal_detection import TemporalAnalyzer

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


def dt(days: float) -> datetime:
    return NOW - timedelta(days=days)


class TestBurst:
    def test_three_claims_in_48h_is_burst(self) -> None:
        p = TemporalAnalyzer().analyze(
            [dt(1.0), dt(1.5), dt(2.0)])
        score, flags = p.as_tuple()
        assert score >= 0.8
        assert any(f.startswith("coordinated_burst") for f in flags)

    def test_two_claims_are_not_burst(self) -> None:
        p = TemporalAnalyzer().analyze([dt(1.0), dt(2.0)])
        score, flags = p.as_tuple()
        assert score == 0.0
        assert flags == []


class TestStaggered:
    def test_claims_over_three_weeks_flag_stagger(self) -> None:
        dates = [dt(1), dt(5), dt(11), dt(17), dt(23)]
        p = TemporalAnalyzer().analyze(dates)
        score, flags = p.as_tuple()
        assert 0.4 <= score < 0.8
        assert any(f.startswith("staggered_pattern") for f in flags)

    def test_scattered_claims_stay_quiet(self) -> None:
        dates = [dt(2), dt(40), dt(95)]
        p = TemporalAnalyzer().analyze(dates)
        score, flags = p.as_tuple()
        assert score == 0.0
        assert flags == []


class TestRegularity:
    def test_machine_like_spacing_is_flagged(self) -> None:
        dates = [dt(30.0), dt(25.0), dt(20.0), dt(15.0), dt(10.0)]
        p = TemporalAnalyzer().analyze(dates)
        score, flags = p.as_tuple()
        assert p.gap_cv is not None and p.gap_cv < 0.35
        assert any(f.startswith("regular_spacing") for f in flags)
        assert score >= 0.6


class TestEdgeCases:
    def test_single_claim(self) -> None:
        p = TemporalAnalyzer().analyze([dt(1)])
        assert p.as_tuple() == (0.0, [])

    def test_empty(self) -> None:
        assert TemporalAnalyzer().analyze([]).as_tuple() == (0.0, [])

    def test_unsorted_input_is_sorted(self) -> None:
        p1 = TemporalAnalyzer().analyze([dt(3), dt(1), dt(2)])
        p2 = TemporalAnalyzer().analyze([dt(1), dt(2), dt(3)])
        assert p1.span_days == p2.span_days
        assert p1.as_tuple() == p2.as_tuple()
