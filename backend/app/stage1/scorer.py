"""Stage 1 · Risk scoring & explanation.

Fixed, inspectable weights — no black box. The output is deliberately
defense-only: `approve_normally` | `manual_review` | `manual_review_urgent`.
There is no "block" action anywhere in this system.
"""

from __future__ import annotations

from app.core.models import (
    RiskBand,
    ReviewPriority,
    Signal,
    SignalName,
)

WEIGHTS: dict[SignalName, float] = {
    "image_evidence": 0.30,
    "history_evidence": 0.20,
    "payment_delivery_evidence": 0.30,
    "text_evidence": 0.20,
}

BANDS: list[tuple[float, RiskBand, ReviewPriority]] = [
    (0.85, "critical", "P0_now"),
    (0.60, "high", "P1_today"),
    (0.35, "medium", "P2_this_week"),
    (0.00, "low", "P3_backlog"),
]

# Defense-only action ladder — there is intentionally no "block".
ACTIONS: dict[RiskBand, str] = {
    "critical": "manual_review_urgent",
    "high": "manual_review_urgent",
    "medium": "manual_review",
    "low": "approve_normally",
}


class ClaimScorer:
    def band(self, risk_score: float) -> RiskBand:
        for threshold, band, _ in BANDS:
            if risk_score >= threshold:
                return band
        return "low"

    def priority(self, band: RiskBand) -> ReviewPriority:
        return dict((b, p) for _, b, p in BANDS)[band]

    def action(self, band: RiskBand) -> str:
        return ACTIONS[band]

    def build_signals(self, scores: dict[SignalName, float],
                      details: dict[SignalName, str]) -> list[Signal]:
        signals: list[Signal] = []
        for name in ("image_evidence", "history_evidence",
                     "payment_delivery_evidence", "text_evidence"):
            score = round(min(1.0, max(0.0, scores.get(name, 0.0))), 3)
            weight = WEIGHTS[name]
            signals.append(Signal(
                name=name, score=score, weight=weight,
                contribution=round(score * weight, 4),
                detail=details.get(name, ""),
            ))
        return signals

    def score(self, signals: list[Signal]) -> float:
        total = sum(s.contribution for s in signals)
        return round(min(1.0, max(0.0, total)), 3)

    def explain(self, signals: list[Signal], risk_score: float,
                band: RiskBand, action: str) -> str:
        """Plain-English reason, driven by the top contributing signals."""
        ranked = sorted(signals, key=lambda s: s.contribution, reverse=True)
        drivers = [s for s in ranked if s.contribution >= 0.06][:3]

        if not drivers:
            reason = (
                f"This claim looks routine: all signals are quiet and the "
                f"overall risk is {risk_score:.2f} ({band})."
            )
        else:
            parts: list[str] = []
            for s in drivers:
                parts.append(f"{_human(s.name)} ({s.score:.2f} — {s.detail})")
            reason = (
                f"Risk {risk_score:.2f} ({band}), driven mainly by: "
                + "; ".join(parts) + "."
            )

        if action == "approve_normally":
            reason += (
                " Recommended action: process the refund normally — no review "
                "needed. RefundShield never blocks customers."
            )
        else:
            urgency = "immediately" if action == "manual_review_urgent" else "in the normal review queue"
            reason += (
                f" Recommended action: a human should review this claim "
                f"{urgency}. RefundShield only flags and explains — it never "
                f"blocks accounts or takes enforcement action."
            )
        return reason


def _human(name: str) -> str:
    return {
        "image_evidence": "Image evidence",
        "history_evidence": "Customer history",
        "payment_delivery_evidence": "Payment & delivery facts",
        "text_evidence": "Claim text",
    }.get(name, name.replace("_", " ").title())
