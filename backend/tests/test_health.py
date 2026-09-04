"""Smoke tests for the Phase 0 skeleton."""


def test_health() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "database" in body


def test_root_reports_test_mode() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get("/")
    body = resp.json()
    assert resp.status_code == 200
    assert body["service"] == "RefundShield"
    assert body["mode"] == "razorpay-test-only"
