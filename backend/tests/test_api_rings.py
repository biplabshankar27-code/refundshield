"""API tests: Stage 2 endpoints, evaluation, demo bootstrap, defense-only."""

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db, get_claim_analyzer, get_audit, get_ring_service
from app.main import app
from app.core.audit import AuditTrail
from app.core.db import Database
from app.data.generator import DatasetGenerator, GeneratorConfig
from app.stage1.claim_analyzer import ClaimAnalyzer
from app.stage2.ring_detection import RingDetectionService


@pytest.fixture()
def world(tmp_path):
    db = Database(str(tmp_path / "api2.db"))
    audit = AuditTrail(db)
    analyzer = ClaimAnalyzer(db, audit, enable_razorpay=False)
    service = RingDetectionService(db, audit)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_audit] = lambda: audit
    app.dependency_overrides[get_claim_analyzer] = lambda: analyzer
    app.dependency_overrides[get_ring_service] = lambda: service
    yield db, analyzer, service
    app.dependency_overrides.clear()


def test_detect_and_fetch_latest(world, tmp_path):
    db, _, _ = world
    DatasetGenerator(db, GeneratorConfig(
        seed=31, n_normal=10, n_fraudsters=2, n_rings=1, ring_size=4,
        n_adversarial_rings=0, image_dir=str(tmp_path / "img"),
    )).generate()

    with TestClient(app) as c:
        resp = c.post("/api/rings/detect")
        assert resp.status_code == 200
        run = resp.json()

        latest = c.get("/api/rings/latest")
    assert run["graph"]["nodes"] > 0
    assert run["cost_of_delay"]["scenarios"]
    assert latest.status_code == 200
    assert latest.json()["run_id"] == run["run_id"]


def test_latest_returns_none_before_any_run(world):
    with TestClient(app) as c:
        resp = c.get("/api/rings/latest")
    assert resp.status_code == 200
    assert resp.json() is None


def test_evaluation_metrics_flow(world, tmp_path):
    db, _, _ = world
    DatasetGenerator(db, GeneratorConfig(
        seed=41, n_normal=12, n_fraudsters=3, n_rings=1, ring_size=4,
        n_adversarial_rings=0, image_dir=str(tmp_path / "img"),
    )).generate()

    with TestClient(app) as c:
        empty = c.get("/api/evaluation/metrics")
        c.post("/api/rings/detect")
        full = c.get("/api/evaluation/metrics")

    assert empty.status_code == 200
    assert "unavailable" in empty.json()["claims"]
    m = full.json()
    cm = m["claims"]
    assert cm["n_claims"] > 0
    assert cm["auc"] is None or 0.0 <= cm["auc"] <= 1.0
    assert 0.0 <= cm["precision"] <= 1.0
    assert 0.0 <= cm["recall"] <= 1.0
    assert m["rings"]["synthetic_ring_members"] > 0


def test_demo_bootstrap_and_cost_of_delay(world):
    db, _, _ = world
    with TestClient(app) as c:
        boot = c.post("/api/demo/bootstrap", json={
            "seed": 77, "n_normal": 10, "n_fraudsters": 2,
            "n_rings": 1, "ring_size": 3, "n_adversarial_rings": 0,
        }).json()
        cod = c.get("/api/demo/cost-of-delay").json()
        # idempotent second run
        boot2 = c.post("/api/demo/bootstrap", json={
            "seed": 77, "n_normal": 10, "n_fraudsters": 2,
            "n_rings": 1, "ring_size": 3, "n_adversarial_rings": 0,
        }).json()

    assert boot["claims_analyzed"] > 0
    assert boot["rings_detected"] >= 1
    assert cod["run_id"] == boot["ring_run_id"]
    assert cod["cost_of_delay"]["scenarios"]
    assert boot2["generated"].get("skipped") is True
    assert boot2["claims_newly_analyzed"] == 0


def test_simulated_webhook_roundtrip(world):
    with TestClient(app) as c:
        resp = c.post("/api/demo/simulate-webhook", json={
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_1"}}},
            "secret": "whsec_demo_secret",
        })
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


def test_defense_only_surface(world):
    """No endpoint may expose a block/enforce action."""
    with TestClient(app) as c:
        openapi = c.get("/openapi.json").json()
    paths = list(openapi["paths"].keys())
    assert paths
    for p in paths:
        assert "block" not in p.lower()
        assert "enforce" not in p.lower()
        assert "ban" not in p.lower()
