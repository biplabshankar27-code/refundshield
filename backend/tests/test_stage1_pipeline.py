"""Stage 1 end-to-end pipeline tests on the generated dataset."""

from datetime import datetime, timezone

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.models import ClaimInput
from app.data.generator import DatasetGenerator, GeneratorConfig, load_claims, load_orders
from app.stage1.claim_analyzer import ClaimAnalyzer


def build_world(tmp_path):
    db = Database(str(tmp_path / "s1.db"))
    cfg = GeneratorConfig(
        seed=99, n_normal=25, n_fraudsters=6, n_rings=1, ring_size=4,
        n_adversarial_rings=1, adversarial_ring_size=4,
        image_dir=str(tmp_path / "img"),
    )
    DatasetGenerator(db, cfg).generate()
    audit = AuditTrail(db)
    analyzer = ClaimAnalyzer(db, audit, enable_razorpay=False)
    return db, analyzer, audit


def to_claim_input(row: dict, orders: dict) -> ClaimInput:
    order = orders[row["order_id"]]
    delivered = order["delivered_at"]
    return ClaimInput(
        claim_id=row["claim_id"],
        order_id=row["order_id"],
        customer_id=row["customer_id"],
        claim_text=row["text"],
        amount_claimed_inr=row["amount_paise"] / 100.0,
        image_path=row["image_path"],
        delivery_status="delivered" if delivered else "in_transit",
        delivered_at=datetime.fromisoformat(delivered) if delivered else None,
        claim_created_at=datetime.fromisoformat(row["created_at"]),
        use_razorpay_enrichment=False,
    )


def run_all(db, analyzer):
    orders = {o["order_id"]: o for o in load_orders(db)}
    claims = load_claims(db)
    results = {}
    for row in claims:
        results[row["claim_id"]] = (row, analyzer.analyze(to_claim_input(row, orders)))
    return results


def test_pipeline_scores_all_claims(tmp_path) -> None:
    db, analyzer, audit = build_world(tmp_path)
    results = run_all(db, analyzer)

    claims = load_claims(db)
    assert len(results) == len(claims)
    for row, res in results.values():
        assert 0.0 <= res.risk_score <= 1.0
        assert res.recommended_action in {
            "approve_normally", "manual_review", "manual_review_urgent"}
        assert res.reason
        assert len(res.signals) == 4
        # results are persisted
        with db.connect() as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM claim_results WHERE claim_id = ?",
                (res.claim_id,)).fetchone()["n"]
        assert n == 1
    # one audit event per claim
    assert audit.list_events(event_type="stage1.analysis",
                             limit=10_000).__len__() == len(claims)


def test_fraudulent_claims_score_higher_than_legit(tmp_path) -> None:
    db, analyzer, _ = build_world(tmp_path)
    results = run_all(db, analyzer)

    fraud = [res.risk_score for row, res in results.values()
             if row["ground_truth"] == 1]
    legit = [res.risk_score for row, res in results.values()
             if row["ground_truth"] == 0]

    assert fraud and legit
    mean_f, mean_l = sum(fraud) / len(fraud), sum(legit) / len(legit)
    assert mean_f > mean_l + 0.15, (
        f"separation too small: fraud={mean_f:.2f} legit={mean_l:.2f}")
    assert mean_f >= 0.45, f"fraud mean too low: {mean_f:.2f}"


def test_reused_images_flagged_for_fraudsters(tmp_path) -> None:
    db, analyzer, _ = build_world(tmp_path)
    results = run_all(db, analyzer)
    fraud_reuse = [res for row, res in results.values()
                   if row["ground_truth"] == 1
                   and res.image_evidence.is_reused]
    assert fraud_reuse, "expected some fraudster image reuse to be caught"


def test_stage1_never_sees_ground_truth(tmp_path) -> None:
    """The analyzer must never receive ground-truth labels as input."""
    import inspect

    from app.core.models import ClaimInput

    fields = set(ClaimInput.model_fields)
    assert "ground_truth" not in fields
    db, analyzer, _ = build_world(tmp_path)
    src = inspect.getsource(type(analyzer))
    assert "ground_truth" not in src
