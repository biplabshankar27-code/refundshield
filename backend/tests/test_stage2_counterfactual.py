"""Stage 2 · Cost-of-delay simulation tests."""

import pytest

from app.core.models import Ring
from app.stage2.counterfactual import CostOfDelaySimulator


def make_ring(score: float, exposure: float, temporal: float = 0.0,
              flags: list[str] | None = None) -> Ring:
    return Ring(
        ring_id=f"R-{score}-{exposure}", member_ids=["a", "b", "c"], size=3,
        avg_stage1_risk=score, graph_density=1.0,
        temporal_coordination_score=temporal, ring_score=score,
        risk_band="high", estimated_exposure_inr=exposure,
        shared_entities={}, adversarial_flags=flags or [],
        explanation="x", members=[],
    )


def test_no_rings_means_no_exposure() -> None:
    cod, burn = CostOfDelaySimulator().simulate([])
    assert cod.daily_exposure_inr == 0.0
    assert all(v == 0.0 for v in cod.scenarios.values())
    assert burn == 0.0


def test_scenarios_compound_monotonically() -> None:
    cod, _ = CostOfDelaySimulator().simulate([make_ring(0.7, 10_000)])
    vals = [cod.scenarios[k] for k in ("7", "14", "30")]
    assert vals == sorted(vals)
    assert vals[0] > 10_000


def test_exact_compounding_math() -> None:
    sim = CostOfDelaySimulator(growth_fallback=0.12)
    cod, burn = sim.simulate([make_ring(0.7, 10_000)])
    assert cod.scenarios["7"] == pytest.approx(round(10_000 * 1.12 ** 7, 2))
    assert cod.scenarios["30"] == pytest.approx(round(10_000 * 1.12 ** 30, 2))
    assert burn == pytest.approx(round(10_000 * 0.12, 2))


def test_bursty_and_adversarial_rings_raise_growth() -> None:
    sim = CostOfDelaySimulator()
    calm = sim.estimate_growth([make_ring(0.5, 100)])
    hot = sim.estimate_growth([
        make_ring(0.5, 100, temporal=0.9),
        make_ring(0.5, 100, flags=["staggered"]),
    ])
    assert hot > calm
    assert hot <= 0.35


def test_note_discloses_assumptions() -> None:
    cod, _ = CostOfDelaySimulator().simulate([make_ring(0.7, 100)])
    assert "%" in cod.note
    assert "projections" in cod.note
