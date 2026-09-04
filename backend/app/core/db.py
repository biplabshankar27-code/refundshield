"""SQLite plumbing: connections, schema, and lifecycle."""

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("refundshield.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL,
    event_type    TEXT    NOT NULL,
    actor         TEXT    NOT NULL,
    subject_type  TEXT    NOT NULL,
    subject_id    TEXT    NOT NULL,
    summary       TEXT    NOT NULL,
    payload_json  TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_subject    ON audit_events (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_events (created_at);

CREATE TABLE IF NOT EXISTS claim_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id       TEXT NOT NULL,
    order_id       TEXT,
    customer_id    TEXT,
    risk_score     REAL NOT NULL,
    risk_band      TEXT NOT NULL,
    priority       TEXT NOT NULL,
    action         TEXT NOT NULL,
    reason         TEXT NOT NULL,
    payload_json   TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claim_customer ON claim_results (customer_id);
CREATE INDEX IF NOT EXISTS idx_claim_created  ON claim_results (created_at);

CREATE TABLE IF NOT EXISTS ring_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL,
    ring_id        TEXT NOT NULL,
    member_ids     TEXT NOT NULL,
    ring_score     REAL NOT NULL,
    avg_risk       REAL NOT NULL,
    density        REAL NOT NULL,
    temporal_score REAL NOT NULL,
    exposure_inr   REAL NOT NULL,
    payload_json   TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ring_run ON ring_results (run_id);

CREATE TABLE IF NOT EXISTS ring_runs (
    run_id        TEXT PRIMARY KEY,
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id  TEXT PRIMARY KEY,
    persona      TEXT NOT NULL,           -- normal | fraudster | ring | adversarial_ring
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    ring_label   TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id       TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL,
    amount_paise   INTEGER NOT NULL,
    status         TEXT NOT NULL,         -- paid | created | attempted
    device_id      TEXT NOT NULL,
    address_id     TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    delivered_at   TEXT,
    payment_id     TEXT,
    source         TEXT NOT NULL DEFAULT 'simulated',  -- simulated | razorpay
    notes_json     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id);

CREATE TABLE IF NOT EXISTS claims (
    claim_id      TEXT PRIMARY KEY,
    order_id      TEXT NOT NULL,
    customer_id   TEXT NOT NULL,
    text          TEXT NOT NULL,
    amount_paise  INTEGER NOT NULL,
    image_path    TEXT,
    created_at    TEXT NOT NULL,
    persona       TEXT NOT NULL,
    ring_label    TEXT,
    ground_truth  INTEGER NOT NULL,       -- 1 = fraudulent (evaluation ONLY, never a signal)
    status        TEXT NOT NULL DEFAULT 'open'
);
CREATE INDEX IF NOT EXISTS idx_claims_customer ON claims (customer_id);
CREATE INDEX IF NOT EXISTS idx_claims_order    ON claims (order_id);

CREATE TABLE IF NOT EXISTS bank_accounts (
    customer_id TEXT NOT NULL,
    vpa         TEXT NOT NULL,
    PRIMARY KEY (customer_id, vpa)
);

CREATE TABLE IF NOT EXISTS razorpay_orders (
    local_order_id    TEXT PRIMARY KEY,
    razorpay_order_id TEXT NOT NULL,
    synced_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS razorpay_payments (
    razorpay_payment_id TEXT PRIMARY KEY,
    razorpay_order_id   TEXT,
    method              TEXT,
    amount_paise        INTEGER,
    status              TEXT,
    captured            INTEGER,
    created_at          INTEGER,
    payload_json        TEXT NOT NULL,
    synced_at           TEXT NOT NULL
);
"""


class Database:
    """Thin wrapper around sqlite3 with per-call connections (WAL mode)."""

    def __init__(self, sqlite_path: str) -> None:
        self.path = sqlite_path
        parent = Path(sqlite_path).parent
        if str(parent) not in ("", "."):
            os.makedirs(parent, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        logger.debug("Database ready at %s", self.path)
