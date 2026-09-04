"""Stage 2 · Temporal coordination detection.

Separates two abuse styles:
- **burst rings**   — many claims in a 48–72 h window (naive coordination)
- **staggered rings** — claims deliberately spread over weeks (adversarial)

The output is an explainable profile; it feeds adversarial flags but does
not alter the strict ring-score formula.
"""

from __future__ import annotations

import statistics
from datetime import datetime

BURST_WINDOW_HOURS = 72
STAGGER_MIN_DAYS = 7
STAGGER_MAX_DAYS = 60
MIN_CLAIMS = 3


class TemporalProfile:
    def __init__(self) -> None:
        self.coordination_score: float = 0.0
        self.flags: list[str] = []
        self.span_days: float = 0.0
        self.mean_gap_days: float | None = None
        self.gap_cv: float | None = None  # coefficient of variation of gaps
        self.n_claims: int = 0

    def as_tuple(self) -> tuple[float, list[str]]:
        return round(self.coordination_score, 3), self.flags


class TemporalAnalyzer:
    def analyze(self, claim_dates: list[datetime]) -> TemporalProfile:
        profile = TemporalProfile()
        profile.n_claims = len(claim_dates)
        if len(claim_dates) < 2:
            return profile

        dates = sorted(claim_dates)
        span = (dates[-1] - dates[0]).total_seconds()
        profile.span_days = round(span / 86400.0, 2)

        gaps = [
            (dates[i + 1] - dates[i]).total_seconds() / 86400.0
            for i in range(len(dates) - 1)
        ]
        profile.mean_gap_days = round(statistics.mean(gaps), 2) if gaps else None
        if len(gaps) >= 2 and statistics.mean(gaps) > 0:
            profile.gap_cv = round(statistics.pstdev(gaps) / statistics.mean(gaps), 2)

        # ---- burst detection -------------------------------------------
        if span <= BURST_WINDOW_HOURS * 3600 and len(dates) >= MIN_CLAIMS:
            profile.coordination_score = max(
                profile.coordination_score,
                0.9 if len(dates) >= 3 else 0.6,
            )
            profile.flags.append(
                f"coordinated_burst: {len(dates)} claims within "
                f"{profile.span_days:.1f} days"
            )

        # ---- staggered / adversarial detection --------------------------
        elif (STAGGER_MIN_DAYS * 86400 <= span <= STAGGER_MAX_DAYS * 86400
              and len(dates) >= MIN_CLAIMS):
            profile.coordination_score = max(profile.coordination_score, 0.55)
            profile.flags.append(
                f"staggered_pattern: {len(dates)} claims spread over "
                f"{profile.span_days:.0f} days"
            )

        # ---- machine-like regularity ------------------------------------
        if profile.gap_cv is not None and len(gaps) >= 3 and profile.gap_cv < 0.35:
            profile.coordination_score = max(profile.coordination_score, 0.6)
            profile.flags.append(
                f"regular_spacing: gap CV {profile.gap_cv} suggests "
                "scheduled submissions"
            )

        return profile
