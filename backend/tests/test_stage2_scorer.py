"""Stage 2 · Ring scorer tests — strict formula & explanation contract."""

import networkx as nx
import pytest

from app.stage2.ring_scorer import RingScorer


def build_clique(members: list[str], risk: float) -> nx.Graph:
    G = nx.Graph()
    for m in members:
        G.add_node(m, avg_stage1_risk=risk, claims=2,
                   total_claimed_inr=1000.0)
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            G.add_edge(members[i], members[j], weight=1,
                       shared_types=["vpa"],
                       shared_entities=[f"vpa:x@upi"])
    return G


@pytest.fixture()
def scorer() -> RingScorer:
    return RingScorer()


def test_formula_is_exact(scorer: RingScorer) -> None:
    members = ["m1", "m2", "m3"]
    sub = build_clique(members, risk=0.5)
    ring = scorer.score(
        ring_id="R1", subgraph=sub, member_ids=members,
        avg_stage1_risk=0.5, temporal_score=0.9,
        adversarial_flags=[], exposure_inr=3000.0,
        shared_entities={"vpa": ["x@upi"]},
    )
    expected = round(0.6 * 0.5 + 0.4 * 1.0, 3)  # clique density = 1.0
    assert ring.ring_score == expected == 0.7
    assert ring.ring_score == pytest.approx(
        0.6 * ring.avg_stage1_risk + 0.4 * ring.graph_density, abs=1e-6)


def test_density_of_complete_graph_is_one(scorer: RingScorer) -> None:
    members = ["m1", "m2", "m3", "m4"]
    sub = build_clique(members, 0.6)
    ring = scorer.score(
        ring_id="R2", subgraph=sub, member_ids=members,
        avg_stage1_risk=0.6, temporal_score=0.0, adversarial_flags=[],
        exposure_inr=0.0, shared_entities={},
    )
    assert ring.graph_density == 1.0


def test_band_mapping(scorer: RingScorer) -> None:
    members = ["a", "b"]
    sub = build_clique(members, 0.9)
    assert scorer.score(
        ring_id="R", subgraph=sub, member_ids=members, avg_stage1_risk=0.9,
        temporal_score=0, adversarial_flags=[], exposure_inr=0,
        shared_entities={},
    ).risk_band == "critical"


def test_members_and_exposure(scorer: RingScorer) -> None:
    members = ["m1", "m2", "m3"]
    sub = build_clique(members, 0.5)
    ring = scorer.score(
        ring_id="R3", subgraph=sub, member_ids=members,
        avg_stage1_risk=0.5, temporal_score=0.0, adversarial_flags=[],
        exposure_inr=3000.0, shared_entities={"vpa": ["x@upi"]},
    )
    assert ring.size == 3
    assert set(ring.member_ids) == set(members)
    assert ring.estimated_exposure_inr == 3000.0
    assert len(ring.members) == 3
    assert ring.members[0].shared_entities == ["x@upi"]


def test_explanation_mentions_formula_and_defense_only(scorer: RingScorer) -> None:
    members = ["m1", "m2", "m3"]
    sub = build_clique(members, 0.7)
    ring = scorer.score(
        ring_id="R4", subgraph=sub, member_ids=members,
        avg_stage1_risk=0.7, temporal_score=0.9,
        adversarial_flags=["staggered_pattern → evasion-aware timing"],
        exposure_inr=12500.0, shared_entities={"vpa": ["x@upi"]},
    )
    assert "0.6" in ring.explanation and "0.4" in ring.explanation
    assert "never" in ring.explanation and "automatically" in ring.explanation
    assert "₹12,500" in ring.explanation
    assert ring.adversarial_flags
