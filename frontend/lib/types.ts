/** Backend API types — mirror app/core/models.py */

export type RiskBand = "low" | "medium" | "high" | "critical";
export type ReviewPriority = "P0_now" | "P1_today" | "P2_this_week" | "P3_backlog";
export type AllowedAction =
  | "approve_normally"
  | "manual_review"
  | "manual_review_urgent";

export interface Signal {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  detail: string;
}

export interface ImageEvidence {
  provided: boolean;
  perceptual_hash: string | null;
  is_reused: boolean;
  reused_of_order_id: string | null;
  similarity_to_prior_claim: number | null;
  ai_generated_suspected: boolean;
  ai_generated_score: number;
  metadata_inconsistent: boolean;
  notes: string[];
}

export interface Stage1Result {
  claim_id: string;
  order_id: string;
  customer_id: string;
  risk_score: number;
  risk_band: RiskBand;
  review_priority: ReviewPriority;
  recommended_action: AllowedAction;
  signals: Signal[];
  image_evidence: ImageEvidence;
  reason: string;
  created_at: string;
}

export interface RingMember {
  customer_id: string;
  avg_stage1_risk: number;
  claims: number;
  total_claimed_inr: number;
  shared_entities: string[];
}

export interface Ring {
  ring_id: string;
  member_ids: string[];
  size: number;
  avg_stage1_risk: number;
  graph_density: number;
  temporal_coordination_score: number;
  ring_score: number;
  risk_band: RiskBand;
  estimated_exposure_inr: number;
  shared_entities: Record<string, string[]>;
  adversarial_flags: string[];
  explanation: string;
  members: RingMember[];
}

export interface CostOfDelay {
  daily_exposure_inr: number;
  scenarios: Record<string, number>;
  note: string;
}

export interface GraphSummary {
  nodes: number;
  edges: number;
  communities_detected: number;
  modularity: number | null;
}

export interface RingDetectionResult {
  run_id: string;
  generated_at: string;
  graph: GraphSummary;
  rings: Ring[];
  baseline_daily_burn_inr: number;
  cost_of_delay: CostOfDelay;
}

export interface AuditEvent {
  id: number | null;
  created_at: string;
  event_type: string;
  actor: string;
  subject_type: string;
  subject_id: string;
  summary: string;
  payload: Record<string, unknown>;
}

export interface ClaimResultRow {
  claim_id: string;
  order_id: string;
  customer_id: string;
  risk_score: number;
  risk_band: RiskBand;
  review_priority: string;
  recommended_action: string;
  reason: string;
  created_at: string;
  payload: Stage1Result;
}

export interface ClaimMetrics {
  n_claims?: number;
  threshold?: number;
  confusion_matrix?: { tp: number; fp: number; fn: number; tn: number };
  precision?: number;
  recall?: number;
  f1?: number;
  auc?: number | null;
  mean_risk_fraud?: number | null;
  mean_risk_legit?: number | null;
  unavailable?: string;
  note?: string;
}

export interface RingMetrics {
  synthetic_ring_members?: number;
  detected_members?: number;
  member_precision?: number;
  member_recall?: number;
  false_positives?: number;
  unavailable?: string;
}

export interface BootstrapResponse {
  generated: Record<string, unknown>;
  claims_analyzed: number;
  claims_newly_analyzed: number;
  ring_run_id: string;
  rings_detected: number;
  cost_of_delay: CostOfDelay;
  metrics: { claims: ClaimMetrics; rings: RingMetrics };
}
