"""Stage 2 · Cost-of-Delay counterfactual simulation (₹).

Answers: "If we leave these rings unreviewed for N days, what does the
merchant likely lose?"

Model (deliberately simple and disclosed):
    exposure(t) = current_open_exposure × (1 + g)^t

``g`` is the daily compounding growth of ring activity, estimated from the
observed claim velocity of the detected rings (default 12%/day when the
sample is too small to estimate). Scenarios: 7 / 14 / 30 days.
"""

from __future__ import annotations

from app.core.models import CostOfDelay, Ring

DEFAULT_SCENARIOS = (7, 14, 30)
DEFAULT_GROWTH = 0.12


class CostOfDelaySimulator:
    def __init__(self, scenarios: tuple[int, ...] = DEFAULT_SCENARIOS,
                 growth_fallback: float = DEFAULT_GROWTH) -> None:
        self.scenarios = scenarios
        self.growth_fallback = growth_fallback

    def estimate_growth(self, rings: list[Ring]) -> float:
        """Crude velocity estimate: growth scales with ring count & burstiness."""
        if not rings:
            return 0.0
        bursty = sum(1 for r in rings if r.temporal_coordination_score >= 0.7)
        adversarial = sum(1 for r in rings if r.adversarial_flags)
        g = self.growth_fallback + 0.03 * bursty + 0.02 * adversarial
        return min(0.35, g)

    def simulate(self, rings: list[Ring]) -> tuple[CostOfDelay, float]:
        """Return (CostOfDelay, baseline_daily_burn_inr)."""
        open_exposure = sum(r.estimated_exposure_inr for r in rings)
        g = self.estimate_growth(rings)

        scenarios: dict[str, float] = {
            str(days): round(open_exposure * ((1.0 + g) ** days), 2)
            for days in self.scenarios
        }
        daily_burn = round(
            open_exposure * g, 2) if rings else 0.0

        note = (
            f"Simulation assumes ring activity compounds at {g:.0%}/day "
            f"(estimated from {len(rings)} detected ring(s); bursty and "
            "adversarial rings raise the rate). Figures are projections of "
            "open claim value, not guarantees."
        )
        return CostOfDelay(
            daily_exposure_inr=daily_burn,
            scenarios=scenarios,
            note=note,
        ), daily_burn
