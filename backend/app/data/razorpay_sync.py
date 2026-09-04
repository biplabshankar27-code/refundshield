"""Two-way sync between RefundShield's local dataset and Razorpay Test Mode.

- ``pull_orders_and_payments`` : Test account -> local tables
- ``push_generated_orders``    : local simulated orders -> real Razorpay TEST
  orders (via ``order.create``), storing the id mapping
- ``enrich_orders``            : attach payment facts (method, captured,
  amount) to local orders so Stage 1 has real payment signals

Every call is audit-logged. All network operations are Test Mode only by
construction (RazorpayTestClient refuses live keys).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.core.audit import AuditTrail
from app.core.db import Database
from app.core.models import RazorpayOrder, RazorpayPayment
from app.razorpay_client import RazorpayAPIError, RazorpayTestClient

logger = logging.getLogger("refundshield.sync")


class SyncReport(BaseModel):
    pulled_orders: int = 0
    pulled_payments: int = 0
    pushed_orders: int = 0
    enriched_orders: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RazorpaySync:
    def __init__(self, client: RazorpayTestClient, db: Database) -> None:
        self.client = client
        self.db = db
        self.audit = AuditTrail(db)

    # ---------------------------------------------------------------- pull
    def pull_orders_and_payments(self, count: int = 100) -> SyncReport:
        """Fetch Test Mode orders & payments into local mirror tables."""
        report = SyncReport()
        try:
            orders = self.client.fetch_orders(count=count)
        except RazorpayAPIError as exc:
            report.errors.append(f"orders pull failed: {exc}")
            orders = []
        try:
            payments = self.client.fetch_payments(count=count)
        except RazorpayAPIError as exc:
            report.errors.append(f"payments pull failed: {exc}")
            payments = []

        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            for o in orders:
                conn.execute(
                    """
                    INSERT INTO razorpay_orders (local_order_id,
                        razorpay_order_id, synced_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(local_order_id) DO UPDATE SET
                        razorpay_order_id=excluded.razorpay_order_id,
                        synced_at=excluded.synced_at
                    """,
                    (o.receipt or o.id, o.id, now),
                )
            for p in payments:
                conn.execute(
                    """
                    INSERT INTO razorpay_payments (razorpay_payment_id,
                        razorpay_order_id, method, amount_paise, status,
                        captured, created_at, payload_json, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(razorpay_payment_id) DO UPDATE SET
                        status=excluded.status,
                        captured=excluded.captured,
                        payload_json=excluded.payload_json,
                        synced_at=excluded.synced_at
                    """,
                    (
                        p.id, p.order_id, p.method, p.amount, p.status,
                        int(p.captured), p.created_at,
                        json.dumps(p.model_dump(mode="json"), default=str), now,
                    ),
                )
        report.pulled_orders = len(orders)
        report.pulled_payments = len(payments)
        self.audit.record(
            event_type="razorpay.pull",
            actor="sync",
            subject_type="razorpay_account",
            subject_id="test-mode",
            summary=(f"Pulled {report.pulled_orders} orders / "
                     f"{report.pulled_payments} payments from Test Mode"),
            payload=report.model_dump(mode="json"),
        )
        return report

    # ---------------------------------------------------------------- push
    def push_generated_orders(self, limit: int = 25) -> SyncReport:
        """Create real Razorpay TEST orders for local simulated orders."""
        report = SyncReport()
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT o.order_id, o.amount_paise, c.customer_id
                   FROM orders o JOIN customers c USING (customer_id)
                   WHERE o.source = 'simulated'
                   ORDER BY o.created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            receipt = row["order_id"]
            try:
                rp_order: RazorpayOrder = self._create_order(
                    amount_paise=row["amount_paise"],
                    receipt=receipt,
                    notes={"customer_id": row["customer_id"],
                           "system": "refundshield-test"},
                )
            except RazorpayAPIError as exc:
                report.errors.append(f"{receipt}: {exc}")
                continue
            with self.db.connect() as conn:
                conn.execute(
                    """INSERT INTO razorpay_orders
                       (local_order_id, razorpay_order_id, synced_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(local_order_id) DO UPDATE SET
                           razorpay_order_id=excluded.razorpay_order_id,
                           synced_at=excluded.synced_at""",
                    (receipt, rp_order.id, now),
                )
                conn.execute(
                    "UPDATE orders SET source = 'razorpay' WHERE order_id = ?",
                    (receipt,),
                )
            report.pushed_orders += 1

        self.audit.record(
            event_type="razorpay.push",
            actor="sync",
            subject_type="razorpay_account",
            subject_id="test-mode",
            summary=f"Created {report.pushed_orders} TEST orders in Razorpay",
            payload=report.model_dump(mode="json"),
        )
        return report

    def _create_order(self, *, amount_paise: int, receipt: str,
                      notes: dict) -> RazorpayOrder:
        data = self.client._call(lambda: self.client._client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes,
        }))
        return RazorpayOrder.model_validate(data)

    # -------------------------------------------------------------- enrich
    def enrich_orders(self) -> SyncReport:
        """Join Razorpay payment facts onto local orders."""
        report = SyncReport()
        with self.db.connect() as conn:
            mappings = conn.execute(
                "SELECT local_order_id, razorpay_order_id FROM razorpay_orders"
            ).fetchall()
            for m in mappings:
                pay = conn.execute(
                    """SELECT * FROM razorpay_payments
                       WHERE razorpay_order_id = ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (m["razorpay_order_id"],),
                ).fetchone()
                if pay is None:
                    continue
                conn.execute(
                    """UPDATE orders SET payment_id = ?, source = 'razorpay'
                       WHERE order_id = ? AND payment_id IS NULL""",
                    (pay["razorpay_payment_id"], m["local_order_id"]),
                )
                report.enriched_orders += 1
        self.audit.record(
            event_type="razorpay.enrich",
            actor="sync",
            subject_type="orders",
            subject_id="local",
            summary=f"Enriched {report.enriched_orders} orders with payment facts",
            payload=report.model_dump(mode="json"),
        )
        return report
