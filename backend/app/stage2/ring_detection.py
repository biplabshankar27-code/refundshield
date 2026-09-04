"""Stage 2 orchestrator — from many Stage 1 results to abuse rings.

Pipeline:
    ensure Stage 1 results → graph_builder → Louvain communities →
    connected components → temporal analysis → ring_scorer →
    cost-of-delay simulation → persistence + audit
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import networkx as nx

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.models import (
    GraphSummary,
    Ring,
    RingDetectionResult,
)
from app.stage1.claim_analyzer import ClaimAnalyzer, build_claim_input
from app.stage2.community_detection import CommunityDetector
from app.stage2.counterfactual import CostOfDelaySimulator
from app.stage2.graph_builder import GraphBuilder
from app.stage2.ring_scorer import RingScorer
from app.stage2.temporal_detection import TemporalAnalyzer

logger = logging.getLogger("refundshield.stage2")

NOISE_FLOOR = 0.15  # rings scoring below this are not reported


class RingDetectionService:
    def __init__(self, db: Database, audit: AuditTrail, seed: int = 42) -> None:
        self.db = db
        self.audit = audit
        self.builder = GraphBuilder(db)
        self.detector = CommunityDetector(seed=seed)
        self.scorer = RingScorer()
        self.temporal = TemporalAnalyzer()
        self.simulator = CostOfDelaySimulator()

    # ------------------------------------------------------------------ API
    def run(
        self,
        claim_analyzer: ClaimAnalyzer | None = None,
        min_size: int = 2,
    ) -> RingDetectionResult:
        run_id = uuid.uuid4().hex[:12]

        if claim_analyzer is not None:
            self._ensure_stage1(claim_analyzer)

        G = self.builder.build()
        communities, modularity = self.detector.detect(G)

        claim_dates = self._claim_dates_by_customer()
        rings: list[Ring] = []
        for members in communities:
            if len(members) < min_size:
                continue
            sub = G.subgraph(members)
            if sub.number_of_edges() == 0:
                continue

            avg_risk = self._avg_risk(sub, members)
            exposure = sum(
                sub.nodes[m].get("total_claimed_inr", 0.0) for m in members)
            dates = [d for m in members for d in claim_dates.get(m, [])]
            profile = self.temporal.analyze(dates)
            t_score, t_flags = profile.as_tuple()

            adversarial_flags = [
                f"{flag} → evasion-aware timing" for flag in t_flags
                if flag.startswith(("staggered", "regular"))
            ]

            ring = self.scorer.score(
                ring_id=f"RING-{run_id[:6]}-{len(rings) + 1:02d}",
                subgraph=sub,
                member_ids=members,
                avg_stage1_risk=avg_risk,
                temporal_score=t_score,
                adversarial_flags=adversarial_flags,
                exposure_inr=exposure,
                shared_entities=self._shared_entities(sub),
            )
            if ring.ring_score >= NOISE_FLOOR:
                rings.append(ring)

        rings.sort(key=lambda r: r.ring_score, reverse=True)
        cost_of_delay, daily_burn = self.simulator.simulate(rings)

        result = RingDetectionResult(
            run_id=run_id,
            graph=GraphSummary(
                nodes=G.number_of_nodes(),
                edges=G.number_of_edges(),
                communities_detected=len(rings),
                modularity=round(modularity, 4) if modularity is not None else None,
            ),
            rings=rings,
            baseline_daily_burn_inr=daily_burn,
            cost_of_delay=cost_of_delay,
        )

        self._persist(result)
        self.audit.record(
            event_type="stage2.detection",
            actor="stage2",
            subject_type="ring_run",
            subject_id=run_id,
            summary=(
                f"Detected {len(rings)} ring(s) across "
                f"{G.number_of_nodes()} customers / {G.number_of_edges()} edges"
            ),
            payload=result.model_dump(mode="json"),
        )
        return result

    # -------------------------------------------------------------- helpers
    def _ensure_stage1(self, analyzer: ClaimAnalyzer) -> None:
        with self.db.connect() as conn:
            done = {r["claim_id"] for r in conn.execute(
                "SELECT claim_id FROM claim_results").fetchall()}
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM claims").fetchall()]
            orders = {o["order_id"]: dict(o) for o in conn.execute(
                "SELECT * FROM orders").fetchall()}
        pending = [r for r in rows if r["claim_id"] not in done]
        for row in pending:
            analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))
        if pending:
            logger.info("Stage 1 ran for %d pending claims", len(pending))

    def _avg_risk(self, sub: nx.Graph, members: list[str]) -> float:
        risks = [sub.nodes[m].get("avg_stage1_risk", 0.0) for m in members]
        weights = [max(1, sub.nodes[m].get("claims", 1)) for m in members]
        weighted = sum(r * w for r, w in zip(risks, weights))
        return weighted / max(1, sum(weights))

    def _claim_dates_by_customer(self) -> dict[str, list[datetime]]:
        out: dict[str, list[datetime]] = defaultdict(list)
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT customer_id, created_at FROM claims").fetchall()
        for r in rows:
            try:
                out[r["customer_id"]].append(
                    datetime.fromisoformat(r["created_at"]))
            except (ValueError, TypeError):
                continue
        return out

    def _shared_entities(self, sub: nx.Graph) -> dict[str, list[str]]:
        by_kind: dict[str, set[str]] = defaultdict(set)
        for _, _, data in sub.edges(data=True):
            for pair in data.get("shared_entities", []):
                kind, _, entity = pair.partition(":")
                by_kind[kind].add(entity)
        return {k: sorted(v) for k, v in by_kind.items()}

    def _persist(self, result: RingDetectionResult) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO ring_runs (run_id, payload_json, created_at)
                   VALUES (?, ?, ?)""",
                (result.run_id,
                 json.dumps(result.model_dump(mode="json"), default=str), now),
            )
            for ring in result.rings:
                conn.execute(
                    """INSERT INTO ring_results (run_id, ring_id, member_ids,
                       ring_score, avg_risk, density, temporal_score,
                       exposure_inr, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.run_id, ring.ring_id,
                        json.dumps(ring.member_ids),
                        ring.ring_score, ring.avg_stage1_risk,
                        ring.graph_density, ring.temporal_coordination_score,
                        ring.estimated_exposure_inr,
                        json.dumps(ring.model_dump(mode="json"), default=str),
                        now,
                    ),
                )
