"""Tests for the append-only SQLite audit trail."""

from app.core.audit import AuditTrail


def test_record_and_list_roundtrip(audit: AuditTrail) -> None:
    row_id = audit.record(
        event_type="stage1.analysis",
        actor="system",
        subject_type="claim",
        subject_id="CLM-001",
        summary="Analyzed claim CLM-001: risk 0.82 (high)",
        payload={"risk_score": 0.82},
    )
    assert row_id > 0

    events = audit.list_events(subject_id="CLM-001")
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "stage1.analysis"
    assert ev.payload["risk_score"] == 0.82
    assert ev.summary.startswith("Analyzed claim")


def test_filters(audit: AuditTrail) -> None:
    for i in range(3):
        audit.record(
            event_type="stage1.analysis",
            actor="system",
            subject_type="claim",
            subject_id=f"CLM-{i:03d}",
            summary=f"claim {i}",
        )
    audit.record(
        event_type="stage2.detection",
        actor="system",
        subject_type="ring_run",
        subject_id="RUN-1",
        summary="ring run",
    )

    assert len(audit.list_events(event_type="stage2.detection")) == 1
    assert len(audit.list_events(subject_id="CLM-002")) == 1
    assert audit.count() == 4


def test_limit_and_ordering(audit: AuditTrail) -> None:
    for i in range(5):
        audit.record(
            event_type="x",
            actor="system",
            subject_type="t",
            subject_id=f"s{i}",
            summary="ev",
        )
    page = audit.list_events(limit=2)
    assert len(page) == 2
    # DESC ordering — newest first
    assert page[0].subject_id == "s4"


def test_payload_json_survives(audit: AuditTrail) -> None:
    audit.record(
        event_type="razorpay.fetch",
        actor="system",
        subject_type="payment",
        subject_id="pay_1",
        summary="fetched",
        payload={"amount": 150000, "nested": {"ok": True}},
    )
    ev = audit.list_events()[0]
    assert ev.payload["amount"] == 150000
    assert ev.payload["nested"]["ok"] is True
