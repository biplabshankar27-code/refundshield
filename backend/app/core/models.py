"""Pydantic domain models for RefundShield.

All scores are floats in [0, 1]. Money is always integer paise from
Razorpay, with explicit `_inr` float helpers where we present rupees.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RiskBand = Literal["low", "medium", "high", "critical"]
ReviewPriority = Literal["P0_now", "P1_today", "P2_this_week", "P3_backlog"]

# Defense-only: the only actions this system may ever recommend.
AllowedAction = Literal["approve_normally", "manual_review", "manual_review_urgent"]

SignalName = Literal[
    "image_evidence",
    "history_evidence",
    "payment_delivery_evidence",
    "text_evidence",
]


# ---------------------------------------------------------------- Stage 1
class Signal(BaseModel):
    """One explainable scoring signal."""

    name: SignalName
    score: float = Field(ge=0.0, le=1.0, description="Signal risk in [0,1]")
    weight: float = Field(ge=0.0, le=1.0)
    contribution: float = Field(ge=0.0, le=1.0, description="score * weight")
    detail: str = ""


class ImageEvidence(BaseModel):
    provided: bool = False
    perceptual_hash: str | None = None
    is_reused: bool = False
    reused_of_order_id: str | None = None
    similarity_to_prior_claim: float | None = Field(
        default=None, ge=0.0, le=1.0
    )
    ai_generated_suspected: bool = False
    ai_generated_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata_inconsistent: bool = False
    notes: list[str] = Field(default_factory=list)


class HistoryEvidence(BaseModel):
    customer_age_days: int = Field(ge=0)
    total_orders: int = Field(ge=0)
    total_refunds: int = Field(ge=0)
    refund_ratio: float = Field(ge=0.0, le=1.0, default=0.0)
    chargeback_count: int = Field(ge=0, default=0)
    prior_claim_images_reused: int = Field(ge=0, default=0)
    is_new_account: bool = False
    velocity_24h: int = Field(ge=0, default=0, description="Orders in last 24h")
    notes: list[str] = Field(default_factory=list)


class PaymentDeliveryEvidence(BaseModel):
    payment_id: str | None = None
    payment_method: str | None = None
    payment_captured: bool = False
    amount_paid_inr: float = 0.0
    amount_claimed_inr: float = 0.0
    amount_mismatch: bool = False
    order_status: str | None = None
    delivery_status: Literal["unknown", "in_transit", "delivered", "failed"] = (
        "unknown"
    )
    delivered_at: datetime | None = None
    claim_created_at: datetime | None = None
    days_between_delivery_and_claim: float | None = None
    claimed_before_delivery: bool = False
    address_changed_after_order: bool = False
    razorpay_enriched: bool = False
    notes: list[str] = Field(default_factory=list)


class TextEvidence(BaseModel):
    urgency_score: float = Field(ge=0.0, le=1.0, default=0.0)
    threat_score: float = Field(ge=0.0, le=1.0, default=0.0)
    negativity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    vagueness_score: float = Field(ge=0.0, le=1.0, default=0.0)
    matched_patterns: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Stage1Result(BaseModel):
    """Output of Stage 1: individual claim intelligence."""

    claim_id: str
    order_id: str
    customer_id: str

    risk_score: float = Field(ge=0.0, le=1.0)
    risk_band: RiskBand
    review_priority: ReviewPriority
    recommended_action: AllowedAction

    signals: list[Signal]
    image_evidence: ImageEvidence
    history_evidence: HistoryEvidence
    payment_delivery_evidence: PaymentDeliveryEvidence
    text_evidence: TextEvidence

    reason: str = Field(description="Plain-English explanation of the score")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    @field_validator("risk_band", mode="before")
    @classmethod
    def derive_band(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        score = info.data.get("risk_score", 0.0)
        if score >= 0.85:
            return "critical"
        if score >= 0.6:
            return "high"
        if score >= 0.35:
            return "medium"
        return "low"


class ClaimInput(BaseModel):
    """A single refund/return request entering Stage 1."""

    claim_id: str
    order_id: str
    customer_id: str
    claim_text: str = ""
    amount_claimed_inr: float = Field(ge=0.0, default=0.0)
    image_base64: str | None = Field(
        default=None, description="Customer-submitted evidence image (base64)"
    )
    image_path: str | None = Field(
        default=None, description="Optional local path to the evidence image"
    )
    delivery_status: Literal[
        "unknown", "in_transit", "delivered", "failed"
    ] = "unknown"
    delivered_at: datetime | None = None
    claim_created_at: datetime | None = None
    address_changed_after_order: bool = False
    use_razorpay_enrichment: bool = True


# ---------------------------------------------------------------- Stage 2
class RingMember(BaseModel):
    customer_id: str
    avg_stage1_risk: float = Field(ge=0.0, le=1.0)
    claims: int = Field(ge=1)
    total_claimed_inr: float = Field(ge=0.0)
    shared_entities: list[str] = Field(
        default_factory=list, description="e.g. device:abc, addr:xyz, bank:uhi"
    )


class Ring(BaseModel):
    ring_id: str
    member_ids: list[str]
    size: int = Field(ge=1)
    avg_stage1_risk: float = Field(ge=0.0, le=1.0)
    graph_density: float = Field(ge=0.0, le=1.0)
    temporal_coordination_score: float = Field(ge=0.0, le=1.0)
    ring_score: float = Field(ge=0.0, le=1.0, description="0.6*avg_risk + 0.4*density")
    risk_band: RiskBand
    estimated_exposure_inr: float = Field(ge=0.0)
    shared_entities: dict[str, list[str]] = Field(default_factory=dict)
    adversarial_flags: list[str] = Field(default_factory=list)
    explanation: str
    members: list[RingMember] = Field(default_factory=list)


class GraphSummary(BaseModel):
    nodes: int
    edges: int
    communities_detected: int
    modularity: float | None = None


class RingDetectionResult(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
    graph: GraphSummary
    rings: list[Ring]
    baseline_daily_burn_inr: float = Field(ge=0.0)
    cost_of_delay: "CostOfDelay"


class CostOfDelay(BaseModel):
    """Money at risk if review is postponed — simulation output in ₹."""

    daily_exposure_inr: float
    scenarios: dict[str, float] = Field(
        description="days -> projected exposure in ₹, e.g. {'7': 41250.0}"
    )
    note: str = ""


# ---------------------------------------------------------------- Razorpay
class RazorpayOrder(BaseModel):
    id: str
    amount: int = Field(description="Integer paise")
    currency: str = "INR"
    status: str
    receipt: str | None = None
    customer_id: str | None = None
    created_at: int | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class RazorpayPayment(BaseModel):
    id: str
    order_id: str | None = None
    method: str | None = None
    amount: int = Field(description="Integer paise")
    currency: str = "INR"
    status: str
    captured: bool = False
    email: str | None = None
    contact: str | None = None
    created_at: int | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class RazorpayRefund(BaseModel):
    id: str
    payment_id: str | None = None
    amount: int = Field(description="Integer paise")
    currency: str = "INR"
    status: str
    speed: str | None = None
    created_at: int | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- Audit
class AuditEvent(BaseModel):
    id: int | None = None
    created_at: datetime
    event_type: str
    actor: str
    subject_type: str
    subject_id: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


RingDetectionResult.model_rebuild()
