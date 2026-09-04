"""Stage 1 · Claim text analysis.

Lexicon + regex based (no external model): transparent, fast, and every
match is listed for the explainability layer.
"""

from __future__ import annotations

import re

from app.core.models import TextEvidence

URGENCY_TERMS = [
    "immediately", "right now", "now", "asap", "urgent", "today",
    "24 hours", "within an hour", "instantly",
]
THREAT_TERMS = [
    "chargeback", "consumer court", "consumer case", "police complaint",
    "lawyer", "legal action", "escalate", "social media", "press",
    "dispute the payment", "call my bank", "report you",
    "formal complaint", "face a complaint",
]
DELIVERY_MISS_PATTERNS = [
    r"never arrived", r"not received", r"did(n't| not) (get|receive|arrive)",
    r"empty box", r"missing from delivery", r"gone missing", r"theft",
    r"no package",
]
NEGATIVE_TERMS = [
    "worst", "scam", "fraud", "useless", "terrible", "unacceptable",
    "angry", "pathetic", "cheat", "horrible",
]
VAGUE_MARKERS = ["it", "thing", "stuff", "some", "maybe", "kind of"]

_WORD_RE = re.compile(r"[a-z']+")


def _hit_count(text_lower: str, terms: list[str]) -> list[str]:
    return [t for t in terms if t in text_lower]


class TextAnalyzer:
    def analyze(self, claim_text: str) -> TextEvidence:
        text = (claim_text or "").strip()
        low = text.lower()
        words = _WORD_RE.findall(low)

        ev = TextEvidence()
        if not text:
            ev.notes.append("Claim text is empty — nothing to analyze.")
            return ev

        ev.matched_patterns = (
            _hit_count(low, URGENCY_TERMS)
            + _hit_count(low, THREAT_TERMS)
            + _hit_count(low, NEGATIVE_TERMS)
            + [p for p in DELIVERY_MISS_PATTERNS if re.search(p, low)]
        )

        ev.urgency_score = self._graded(low, URGENCY_TERMS)
        ev.threat_score = self._graded(low, THREAT_TERMS)
        neg_hits = len(_hit_count(low, NEGATIVE_TERMS))
        ev.negativity_score = round(min(1.0, neg_hits / 3.0), 3)

        # vagueness: very short, or non-specific
        vagueness = 0.0
        if len(words) < 6:
            vagueness += 0.4
        if len(_hit_count(low, VAGUE_MARKERS)) >= 2 and len(words) < 12:
            vagueness += 0.3
        if not any(w.isdigit() for w in words):
            vagueness += 0.1          # no numbers / specifics at all
        ev.vagueness_score = round(min(1.0, vagueness), 3)

        if ev.threat_score >= 0.5:
            ev.notes.append("Threatening / escalation language detected.")
        if ev.urgency_score >= 0.5:
            ev.notes.append("Artificial urgency pressure detected.")
        if ev.vagueness_score >= 0.5:
            ev.notes.append("Claim text is unusually vague for a refund case.")
        return ev

    def score(self, ev: TextEvidence) -> float:
        s = (
            0.45 * ev.threat_score
            + 0.25 * ev.urgency_score
            + 0.10 * ev.negativity_score
            + 0.20 * ev.vagueness_score
        )
        # a "never arrived" pattern while claiming a damaged-product refund
        # is a common inconsistency; presence of any miss-pattern adds a nudge
        if any(re.search(p, " ".join(ev.matched_patterns)) for p in DELIVERY_MISS_PATTERNS):
            s += 0.05
        return round(min(1.0, s), 3)

    def _graded(self, low: str, terms: list[str]) -> float:
        hits = len(_hit_count(low, terms))
        if hits == 0:
            return 0.0
        return round(min(1.0, 0.45 + 0.25 * (hits - 1)), 3)
