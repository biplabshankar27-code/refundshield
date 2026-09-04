"""Append-only audit trail.

Every scoring decision, Razorpay interaction, and ring detection run is
recorded here. The trail is write-append: nothing is ever updated or
deleted through this module.
"""

import json
import logging
from datetime import datetime, timezone

from app.core.db import Database
from app.core.models import AuditEvent

logger = logging.getLogger("refundshield.audit")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditTrail:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record(
        self,
        *,
        event_type: str,
        actor: str,
        subject_type: str,
        subject_id: str,
        summary: str,
        payload: dict | None = None,
    ) -> int:
        event = AuditEvent(
            created_at=datetime.now(timezone.utc),
            event_type=event_type,
            actor=actor,
            subject_type=subject_type,
            subject_id=subject_id,
            summary=summary,
            payload=payload or {},
        )
        with self.db.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_events
                    (created_at, event_type, actor, subject_type, subject_id,
                     summary, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.created_at.isoformat(),
                    event.event_type,
                    event.actor,
                    event.subject_type,
                    event.subject_id,
                    event.summary,
                    json.dumps(event.payload, default=str),
                ),
            )
            row_id = int(cur.lastrowid or 0)
        logger.info("AUDIT %s %s/%s — %s", event_type, subject_type, subject_id, summary)
        return row_id

    def list_events(
        self,
        *,
        event_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: list = []
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if subject_id:
            query += " AND subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            AuditEvent(
                id=r["id"],
                created_at=datetime.fromisoformat(r["created_at"]),
                event_type=r["event_type"],
                actor=r["actor"],
                subject_type=r["subject_type"],
                subject_id=r["subject_id"],
                summary=r["summary"],
                payload=json.loads(r["payload_json"]),
            )
            for r in rows
        ]

    def count(self) -> int:
        with self.db.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM audit_events").fetchone()
        return int(row["n"])
