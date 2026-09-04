"""Honest evaluation metrics.

Ground truth comes from the synthetic dataset's ``ground_truth`` column
and exists ONLY for offline evaluation. It never reaches any scorer —
these metrics simply measure how well the defense performs.
"""

from __future__ import annotations

from typing import Any

from app.core.db import Database


def _auc(scores: list[float], labels: list[int]) -> float | None:
    """Rank-based AUC (Mann–Whitney). None when a class is missing."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = sum(
        1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 4)


class EvaluationService:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------- claims
    def claim_metrics(self, threshold: float = 0.6) -> dict[str, Any]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT c.claim_id, c.ground_truth, r.risk_score
                   FROM claims c JOIN claim_results r USING (claim_id)"""
            ).fetchall()
        if not rows:
            raise LookupError("no analyzed claims with ground truth available")

        scores = [r["risk_score"] for r in rows]
        labels = [int(r["ground_truth"]) for r in rows]

        tp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 1)
        fp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 0)
        fn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 1)
        tn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 0)

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)

        fraud = [s for s, y in zip(scores, labels) if y == 1]
        legit = [s for s, y in zip(scores, labels) if y == 0]

        return {
            "n_claims": len(rows),
            "threshold": threshold,
            "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "auc": _auc(scores, labels),
            "mean_risk_fraud": round(sum(fraud) / len(fraud), 4) if fraud else None,
            "mean_risk_legit": round(sum(legit) / len(legit), 4) if legit else None,
            "note": (
                "Metrics compare Stage 1 scores against synthetic ground-truth "
                "labels. Ground truth is never visible to any scorer."
            ),
        }

    # -------------------------------------------------------------- rings
    def ring_metrics(self) -> dict[str, Any]:
        with self.db.connect() as conn:
            synthetic_ring_members = {
                r["customer_id"] for r in conn.execute(
                    "SELECT customer_id FROM customers WHERE ring_label IS NOT NULL"
                ).fetchall()
            }
            rows = conn.execute(
                """SELECT member_ids, created_at FROM ring_results
                   ORDER BY created_at DESC LIMIT 200"""
            ).fetchall()
        if not rows:
            raise LookupError("no ring detection runs available")

        latest_run_created = rows[0]["created_at"]
        detected: set[str] = set()
        for r in rows:
            if r["created_at"] != latest_run_created:
                continue
            import json
            detected.update(json.loads(r["member_ids"]))

        tp = len(detected & synthetic_ring_members)
        fp = len(detected - synthetic_ring_members)
        fn = len(synthetic_ring_members - detected)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        return {
            "synthetic_ring_members": len(synthetic_ring_members),
            "detected_members": len(detected),
            "member_precision": round(precision, 4),
            "member_recall": round(recall, 4),
            "false_positives": fp,
            "note": (
                "Member-level comparison of detected ring membership against "
                "synthetic ring labels (evaluation only)."
            ),
        }
