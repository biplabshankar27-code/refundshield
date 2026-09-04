"""API tests: Stage 1 endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db, get_claim_analyzer, get_audit
from app.main import app
from app.core.audit import AuditTrail
from app.core.db import Database
from app.data.generator import DatasetGenerator, GeneratorConfig, load_claims, load_orders
from app.stage1.claim_analyzer import ClaimAnalyzer, build_claim_input


@pytest.fixture()
def world(tmp_path):
    db = Database(str(tmp_path / "api1.db"))
    audit = AuditTrail(db)
    analyzer = ClaimAnalyzer(db, audit, enable_razorpay=False)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_audit] = lambda: audit
    app.dependency_overrides[get_claim_analyzer] = lambda: analyzer
    yield db, analyzer
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(world, tmp_path):
    db, analyzer = world
    DatasetGenerator(db, GeneratorConfig(
        seed=21, n_normal=8, n_fraudsters=2, n_rings=1, ring_size=3,
        n_adversarial_rings=0, image_dir=str(tmp_path / "img"),
    )).generate()
    return db, analyzer


def test_analyze_single_claim(seeded):
    db, _ = seeded
    claims = load_claims(db)
    orders = {o["order_id"]: o for o in load_orders(db)}
    row = claims[0]

    with TestClient(app) as c:
        resp = c.post("/api/claims/analyze", json={
            "claim_id": row["claim_id"],
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "claim_text": row["text"],
            "amount_claimed_inr": row["amount_paise"] / 100.0,
            "image_path": row["image_path"],
            "use_razorpay_enrichment": False,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_band"] in {"low", "medium", "high", "critical"}
    assert data["recommended_action"] in {
        "approve_normally", "manual_review", "manual_review_urgent"}
    assert len(data["signals"]) == 4
    assert data["review_priority"] in {
        "P0_now", "P1_today", "P2_this_week", "P3_backlog"}


def test_analyze_unknown_order_still_works(world):
    with TestClient(app) as c:
        resp = c.post("/api/claims/analyze", json={
            "claim_id": "CLM-MANUAL-1",
            "order_id": "ORD-DOES-NOT-EXIST",
            "customer_id": "CUST-00001",
            "claim_text": "Item arrived damaged, requesting a refund please.",
            "amount_claimed_inr": 999.0,
            "use_razorpay_enrichment": False,
        })
    assert resp.status_code == 200
    assert resp.json()["risk_score"] >= 0.0


def test_list_and_get_results(seeded):
    db, analyzer = seeded
    claims = load_claims(db)
    orders = {o["order_id"]: o for o in load_orders(db)}
    for row in claims[:3]:
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    with TestClient(app) as c:
        listing = c.get("/api/claims/results").json()
        one = c.get(f"/api/claims/{claims[0]['claim_id']}").json()
        missing = c.get("/api/claims/NOPE")
        payload = c.get("/api/claims/results").json()[0]

    assert len(listing) == 3
    assert one["claim_id"] == claims[0]["claim_id"]
    assert "result" in one
    assert missing.status_code == 404
    assert payload["risk_band"] in {"low", "medium", "high", "critical"}


def test_audit_endpoint_records_stage1(seeded):
    db, analyzer = seeded
    claims = load_claims(db)
    orders = {o["order_id"]: o for o in load_orders(db)}
    analyzer.analyze(build_claim_input(claims[0], orders.get(claims[0]["order_id"])))

    with TestClient(app) as c:
        events = c.get("/api/audit", params={"event_type": "stage1.analysis"}).json()
        count = c.get("/api/audit/count").json()
    assert len(events) == 1
    assert events[0]["subject_id"] == claims[0]["claim_id"]
    assert count["events"] >= 2  # stage1 + persistence are both audited
