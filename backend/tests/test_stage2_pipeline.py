"""Stage 2 · End-to-end ring detection pipeline on the generated dataset."""

from app.core.audit import AuditTrail
from app.core.db import Database
from app.data.generator import (
    DatasetGenerator,
    GeneratorConfig,
    load_claims,
    load_customers,
)
from app.stage1.claim_analyzer import ClaimAnalyzer
from app.stage2.ring_detection import RingDetectionService


def build_world(tmp_path):
    db = Database(str(tmp_path / "s2.db"))
    cfg = GeneratorConfig(
        seed=11, n_normal=30, n_fraudsters=5, n_rings=2, ring_size=5,
        n_adversarial_rings=1, adversarial_ring_size=5,
        image_dir=str(tmp_path / "img"),
    )
    DatasetGenerator(db, cfg).generate()
    audit = AuditTrail(db)
    analyzer = ClaimAnalyzer(db, audit, enable_razorpay=False)
    service = RingDetectionService(db, audit)
    return db, analyzer, service, audit


def test_pipeline_detects_seeded_rings(tmp_path) -> None:
    db, analyzer, service, _ = build_world(tmp_path)
    result = service.run(claim_analyzer=analyzer)

    customers = {c["customer_id"]: c for c in load_customers(db)}
    persona_of = {cid: c["persona"] for cid, c in customers.items()}

    detected_members = [set(r.member_ids) for r in result.rings]

    # 1. coordinated rings are found (>=3 of their members together)
    ring_personas = [cid for cid, p in persona_of.items() if p == "ring"]
    found_coordinated = any(
        len(set(ring_personas) & members) >= 3 for members in detected_members)
    assert found_coordinated, "coordinated ring missed"

    # 2. adversarial rings are found via the bank-only link
    adv_personas = [cid for cid, p in persona_of.items()
                    if p == "adversarial_ring"]
    found_adversarial = any(
        len(set(adv_personas) & members) >= 3 for members in detected_members)
    assert found_adversarial, "adversarial ring missed"

    # 3. normal customers are not dragged into rings
    normal_ids = {cid for cid, p in persona_of.items() if p == "normal"}
    normal_in_rings = sum(
        len(members & normal_ids) for members in detected_members)
    assert normal_in_rings <= 1, f"{normal_in_rings} normals pulled into rings"


def test_ring_score_formula_holds_for_every_ring(tmp_path) -> None:
    db, analyzer, service, _ = build_world(tmp_path)
    result = service.run(claim_analyzer=analyzer)
    assert result.rings, "expected at least one ring"
    for ring in result.rings:
        expected = round(0.6 * ring.avg_stage1_risk + 0.4 * ring.graph_density, 3)
        assert ring.ring_score == expected


def test_adversarial_rings_carry_evasion_flags(tmp_path) -> None:
    db, analyzer, service, _ = build_world(tmp_path)
    result = service.run(claim_analyzer=analyzer)
    customers = {c["customer_id"]: c for c in load_customers(db)}
    adv = {cid for cid, c in customers.items()
           if c["persona"] == "adversarial_ring"}
    adv_rings = [r for r in result.rings if len(set(r.member_ids) & adv) >= 3]
    assert adv_rings
    assert any("evasion" in f.lower()
               for r in adv_rings for f in r.adversarial_flags)


def test_results_persist_and_audit(tmp_path) -> None:
    db, analyzer, service, audit = build_world(tmp_path)
    result = service.run(claim_analyzer=analyzer)

    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM ring_results").fetchone()["n"]
    assert n == len(result.rings)

    events = audit.list_events(event_type="stage2.detection")
    assert len(events) == 1
    assert events[0].subject_id == result.run_id


def test_graph_summary_and_cost_of_delay(tmp_path) -> None:
    db, analyzer, service, _ = build_world(tmp_path)
    result = service.run(claim_analyzer=analyzer)

    assert result.graph.nodes > 0
    assert result.graph.edges > 0
    assert result.graph.communities_detected == len(result.rings)
    if result.rings:
        assert result.cost_of_delay.daily_exposure_inr > 0
        assert set(result.cost_of_delay.scenarios) == {"7", "14", "30"}
        assert result.baseline_daily_burn_inr > 0


def test_detection_is_deterministic(tmp_path) -> None:
    db, analyzer, service, _ = build_world(tmp_path)
    r1 = service.run(claim_analyzer=analyzer)
    r2 = service.run(claim_analyzer=analyzer)
    # ring_id embeds a fresh run uuid, so compare stable fields
    key = lambda r: (tuple(sorted(r.member_ids)), r.ring_score,
                     r.avg_stage1_risk, r.graph_density)
    assert [key(r) for r in r1.rings] == [key(r) for r in r2.rings]
