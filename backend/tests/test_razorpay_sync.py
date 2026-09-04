"""Tests for Razorpay Test Mode sync (network mocked)."""

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.core.db import Database
from app.data.generator import DatasetGenerator, GeneratorConfig, load_orders
from app.data.razorpay_sync import RazorpaySync
from app.razorpay_client import RazorpayTestClient


def make_sync(db: Database, sdk: MagicMock) -> RazorpaySync:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.razorpay_client.Client", MagicMock(return_value=sdk))
        client = RazorpayTestClient(
            Settings(razorpay_key_id="rzp_test_k", razorpay_key_secret="s",
                     _env_file=None)
        )
    return RazorpaySync(client, db)


def seeded_db(tmp_path) -> tuple[Database, int]:
    db = Database(str(tmp_path / "sync.db"))
    summary = DatasetGenerator(db, GeneratorConfig(
        seed=7, n_normal=6, n_fraudsters=2, n_rings=1, ring_size=3,
        n_adversarial_rings=0, image_dir=str(tmp_path / "img"),
    )).generate()
    return db, summary.total_orders


def test_push_creates_test_orders_and_mapping(tmp_path) -> None:
    db, n_orders = seeded_db(tmp_path)
    sdk = MagicMock()
    sdk.order.create.side_effect = [
        {"id": f"order_RP{i:03d}", "amount": 99900, "currency": "INR",
         "status": "created", "receipt": f"ORD-{10001 + i:05d}", "notes": {}}
        for i in range(n_orders)
    ]
    sync = make_sync(db, sdk)
    report = sync.push_generated_orders(limit=n_orders)

    assert report.pushed_orders == n_orders
    assert sdk.order.create.call_count == n_orders
    # every pushed order is now marked as razorpay-sourced
    assert all(o["source"] == "razorpay" for o in load_orders(db))


def test_enrich_attaches_payment_facts(tmp_path) -> None:
    db, n_orders = seeded_db(tmp_path)
    sdk = MagicMock()
    sdk.order.create.side_effect = [
        {"id": f"order_RP{i:03d}", "amount": 99900, "currency": "INR",
         "status": "created", "receipt": f"ORD-{10001 + i:05d}", "notes": {}}
        for i in range(n_orders)
    ]
    sync = make_sync(db, sdk)
    sync.push_generated_orders(limit=n_orders)

    # simulate a pulled payment for the first razorpay order
    with db.connect() as conn:
        mapping = conn.execute(
            "SELECT local_order_id, razorpay_order_id FROM razorpay_orders LIMIT 1"
        ).fetchone()
        conn.execute(
            """INSERT INTO razorpay_payments (razorpay_payment_id,
               razorpay_order_id, method, amount_paise, status, captured,
               created_at, payload_json, synced_at)
               VALUES ('pay_OK1', ?, 'upi', 99900, 'captured', 1, 1, '{}', 'now')""",
            (mapping["razorpay_order_id"],),
        )

    report = sync.enrich_orders()
    assert report.enriched_orders >= 1
    row = conn_row(db, mapping["local_order_id"])
    assert row["payment_id"] == "pay_OK1"
    assert row["source"] == "razorpay"


def conn_row(db: Database, order_id: str) -> dict:
    with db.connect() as conn:
        return dict(conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone())


def test_pull_stores_orders_and_payments(tmp_path) -> None:
    db, _ = seeded_db(tmp_path)
    sdk = MagicMock()
    sdk.order.all.return_value = {"items": [
        {"id": "order_PP1", "amount": 50000, "currency": "INR",
         "status": "paid", "receipt": "rcpt-1", "notes": {}}
    ]}
    sdk.payment.all.return_value = {"items": [
        {"id": "pay_PP1", "order_id": "order_PP1", "method": "card",
         "amount": 50000, "status": "captured", "captured": True,
         "email": "x@y.z", "notes": {}}
    ]}
    sync = make_sync(db, sdk)
    report = sync.pull_orders_and_payments()

    assert report.pulled_orders == 1
    assert report.pulled_payments == 1
    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM razorpay_payments").fetchone()["n"]
        assert n == 1


def test_push_survives_partial_api_errors(tmp_path) -> None:
    from razorpay.errors import BadRequestError

    db, n_orders = seeded_db(tmp_path)
    sdk = MagicMock()

    responses = [
        {"id": "order_OK1", "amount": 99900, "currency": "INR",
         "status": "created", "receipt": f"ORD-{10001:05d}", "notes": {}}
    ]
    call_state = {"i": 0}

    def flaky_create(*args, **kwargs):
        i = call_state["i"]
        call_state["i"] += 1
        if i == 0:
            return responses[0]
        raise BadRequestError("bad", "Bad request")

    sdk.order.create.side_effect = flaky_create
    sync = make_sync(db, sdk)
    report = sync.push_generated_orders(limit=3)

    assert report.pushed_orders == 1
    assert len(report.errors) >= 1
