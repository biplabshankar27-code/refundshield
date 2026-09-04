"""Tests for the synthetic dataset generator."""

from pathlib import Path

from app.core.db import Database
from app.data.generator import (
    DatasetGenerator,
    GeneratorConfig,
    load_bank_accounts,
    load_claims,
    load_customers,
    load_orders,
)


def make_db(tmp_path: Path) -> Database:
    return Database(str(tmp_path / "data.db"))


def small_config(tmp_path: Path) -> GeneratorConfig:
    return GeneratorConfig(
        seed=123,
        n_normal=20,
        n_fraudsters=5,
        n_rings=2,
        ring_size=4,
        n_adversarial_rings=1,
        adversarial_ring_size=4,
        image_dir=str(tmp_path / "images"),
    )


def test_generator_produces_expected_populations(tmp_path: Path) -> None:
    db = make_db(tmp_path)
    summary = DatasetGenerator(db, small_config(tmp_path)).generate()

    assert summary.customers_by_persona["normal"] == 20
    assert summary.customers_by_persona["fraudster"] == 5
    assert summary.customers_by_persona["ring"] == 8
    assert summary.customers_by_persona["adversarial_ring"] == 4
    assert summary.total_claims == summary.fraudulent_claims + summary.legit_claims
    assert summary.fraudulent_claims > 0 and summary.legit_claims > 0


def test_generator_is_deterministic(tmp_path: Path) -> None:
    s1 = DatasetGenerator(make_db(tmp_path), small_config(tmp_path)).generate()
    s2 = DatasetGenerator(
        Database(str(tmp_path / "data2.db")), small_config(tmp_path)
    ).generate()
    assert s1.total_claims == s2.total_claims
    assert s1.fraudulent_claims == s2.fraudulent_claims
    c1 = [c["text"] for c in load_claims(Database(str(tmp_path / "data.db")))]
    c2 = [c["text"] for c in load_claims(Database(str(tmp_path / "data2.db")))]
    assert c1 == c2


def test_ring_members_share_bank_account(tmp_path: Path) -> None:
    db = make_db(tmp_path)
    DatasetGenerator(db, small_config(tmp_path)).generate()

    customers = {c["customer_id"]: c for c in load_customers(db)}
    vpas = load_bank_accounts(db)
    ring_customers = [c for c in customers.values() if c["persona"] == "ring"]
    assert len(ring_customers) == 8

    # all members of each ring label share exactly one VPA
    by_label: dict[str, set[str]] = {}
    for c in ring_customers:
        label = c["ring_label"]
        by_label.setdefault(label, set()).update(vpas[c["customer_id"]])
    for label, vpa_set in by_label.items():
        assert len(vpa_set) == 1, f"{label} VPA not shared"


def test_adversarial_rings_link_only_via_bank(tmp_path: Path) -> None:
    db = make_db(tmp_path)
    DatasetGenerator(db, small_config(tmp_path)).generate()

    orders = load_orders(db)
    customers = {c["customer_id"]: c for c in load_customers(db)}
    adv = [c for c in customers.values() if c["persona"] == "adversarial_ring"]
    adv_ids = {c["customer_id"] for c in adv}
    adv_orders = [o for o in orders if o["customer_id"] in adv_ids]

    devices = {o["device_id"] for o in adv_orders}
    addresses = {o["address_id"] for o in adv_orders}
    # evasion: device + address are all distinct
    assert len(devices) == len(adv_orders)
    assert len(addresses) == len(adv_orders)


def test_claims_reference_valid_orders_and_images(tmp_path: Path) -> None:
    db = make_db(tmp_path)
    DatasetGenerator(db, small_config(tmp_path)).generate()

    order_ids = {o["order_id"] for o in load_orders(db)}
    for c in load_claims(db):
        assert c["order_id"] in order_ids
        assert Path(c["image_path"]).exists(), f"missing image {c['image_path']}"
        assert c["amount_paise"] > 0
        assert c["ground_truth"] in (0, 1)


def test_generator_writes_audit_event(tmp_path: Path) -> None:
    from app.core.audit import AuditTrail

    db = make_db(tmp_path)
    DatasetGenerator(db, small_config(tmp_path)).generate()
    events = AuditTrail(db).list_events(event_type="data.generate")
    assert len(events) == 1
    assert events[0].payload["total_claims"] > 0
