"""Stage 2 · Ring scoring & explanation.

    ring_score = 0.6 * avg_stage1_risk + 0.4 * graph_density

Strict formula per spec. The temporal coordination score and adversarial
flags inform the narrative but do NOT enter the formula.
"""

from __future__ import annotations

import networkx as nx

from app.core.models import Ring, RingMember

W_RISK = 0.6
W_DENSITY = 0.4


class RingScorer:
    def score(
        self,
        *,
        ring_id: str,
        subgraph: nx.Graph,
        member_ids: list[str],
        avg_stage1_risk: float,
        temporal_score: float,
        adversarial_flags: list[str],
        exposure_inr: float,
        shared_entities: dict[str, list[str]],
    ) -> Ring:
        density = round(nx.density(subgraph), 3) if subgraph.number_of_nodes() > 1 else 0.0
        ring_score = round(
            min(1.0, W_RISK * avg_stage1_risk + W_DENSITY * density), 3)

        members = [
            RingMember(
                customer_id=m,
                avg_stage1_risk=round(
                    subgraph.nodes[m].get("avg_stage1_risk", 0.0), 3),
                claims=int(subgraph.nodes[m].get("claims", 1)),
                total_claimed_inr=round(
                    subgraph.nodes[m].get("total_claimed_inr", 0.0), 2),
                shared_entities=self._entities_for(subgraph, m),
            )
            for m in member_ids
        ]

        return Ring(
            ring_id=ring_id,
            member_ids=member_ids,
            size=len(member_ids),
            avg_stage1_risk=round(avg_stage1_risk, 3),
            graph_density=density,
            temporal_coordination_score=round(temporal_score, 3),
            ring_score=ring_score,
            risk_band=self._band(ring_score),
            estimated_exposure_inr=round(exposure_inr, 2),
            shared_entities=shared_entities,
            adversarial_flags=adversarial_flags,
            explanation=self._explain(
                ring_score, avg_stage1_risk, density, temporal_score,
                shared_entities, adversarial_flags, exposure_inr,
            ),
            members=members,
        )

    @staticmethod
    def _band(score: float) -> str:
        if score >= 0.85:
            return "critical"
        if score >= 0.60:
            return "high"
        if score >= 0.35:
            return "medium"
        return "low"

    @staticmethod
    def _entities_for(subgraph: nx.Graph, node: str) -> list[str]:
        out: set[str] = set()
        for _, _, data in subgraph.edges(node, data=True):
            for pair in data.get("shared_entities", []):
                _, _, entity = pair.partition(":")
                if entity:
                    out.add(entity)
        return sorted(out)

    def _explain(
        self,
        ring_score: float,
        avg_risk: float,
        density: float,
        temporal: float,
        shared: dict[str, list[str]],
        flags: list[str],
        exposure: float,
    ) -> str:
        entity_bits = [f"{len(v)} shared {k}(s)" for k, v in shared.items() if v]
        entity_txt = ", ".join(entity_bits) if entity_bits else "no shared entities"
        parts = [
            f"Ring score {ring_score:.2f} = 0.6 × avg claim risk "
            f"({avg_risk:.2f}) + 0.4 × graph density ({density:.2f}).",
            f"Members are linked via {entity_txt}.",
        ]
        if temporal >= 0.7:
            parts.append("Claims cluster tightly in time — consistent with "
                         "coordinated activity.")
        elif temporal >= 0.4:
            parts.append("Claim timing shows a staggered, evasion-aware "
                         "pattern rather than a single burst.")
        if flags:
            parts.append("Adversarial indicators: " + "; ".join(flags) + ".")
        parts.append(
            f"Estimated exposure if all open claims are paid: "
            f"₹{exposure:,.0f}.")
        parts.append(
            "RefundShield only surfaces and explains this ring — it never "
            "takes account action automatically; enforcement is a human "
            "decision.")
        return " ".join(parts)
