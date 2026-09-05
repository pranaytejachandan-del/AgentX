export type ExecutionStage =
  | 'REQUEST_CREATED'
  | 'PARSING'
  | 'DISCOVERING'
  | 'NEGOTIATING'
  | 'POLICY_CHECK'
  | 'APPROVAL_REQUIRED'
  | 'READY_FOR_PAYMENT'
  | 'PAYMENT_PENDING'
  | 'PAID'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type ApprovalStatus = 'NOT_REQUIRED' | 'PENDING' | 'APPROVED' | 'REJECTED';

export type PaymentStatus =
  | 'NOT_STARTED'
  | 'PAYMENT_PENDING'
  | 'PAID'
  | 'FAILED'
  | 'EXPIRED'
  | 'CANCELLED';

export interface ProcurementConstraints {
  category?: string | null;
  item_description: string;
  quantity?: number | null;
  target_unit_price?: number | null;
  max_unit_price?: number | null;
  currency: string;
  max_lead_time_days?: number | null;
  required_certifications: string[];
  additional_requirements: string[];
  missing_required_fields: string[];
  ambiguous_fields: string[];
  needs_clarification: boolean;
}

export interface ScoreBreakdown {
  price_score: number;
  lead_time_score: number;
  rating_score: number;
  gst_score: number;
}

export interface OfferCandidate {
  offer_id?: string;
  product_id: number;
  product_name: string;       // backend field
  product_title?: string;     // alias used in some views
  vendor_id: number;
  vendor_name: string;
  vendor_rating: number;
  sku?: string;
  gst_verified: boolean;      // backend field
  gst_status?: string;        // alias
  base_price: number;         // backend field (pre-negotiation)
  unit_price?: number;        // alias
  min_allowable_price?: number;
  lead_time_days: number;
  certifications: string[];
  semantic_similarity?: number;
  price_score?: number;
  lead_time_score?: number;
  rating_score?: number;
  gst_score?: number;
  overall_score: number;
  eligibility_status: string; // backend field: 'ELIGIBLE' | 'INELIGIBLE' | 'NEAR_MATCH'
  is_eligible?: boolean;      // alias
  eligibility_reasons?: string[];
  rejection_reasons?: string[];
  deterministic_score_breakdown?: ScoreBreakdown;
}

export interface NegotiationTrace {
  id: number;
  turn_number: number;
  buyer_agent_message?: string | null;
  supplier_agent_message?: string | null;
  proposed_price?: number | null;
  counter_price?: number | null;
  negotiation_status: string;
  timestamp: string;
  decision_summary?: string | null;
}

export interface NegotiationSummary {
  initial_price: number;
  final_price: number;
  quantity: number;
  total_amount: number;
  unit_savings: number;
  total_savings: number;
  status: string;
}

export interface GuardrailRuleResult {
  rule_name: string;
  passed: boolean;
  message: string;
  actual_value?: any;
  expected_threshold?: any;
}

export interface GuardrailResult {
  request_id: number;
  order_id?: number | null;
  passed_all: boolean;
  requires_human_approval: boolean;
  approval_threshold?: number;
  total_amount?: number;
  deal_snapshot?: Record<string, any> | null;
  rules: GuardrailRuleResult[];
  error?: string;
}

export interface OrderSummary {
  id: number;
  request_id?: number;
  vendor_id: number;
  vendor_name?: string | null;
  product_id: number;
  product_title?: string | null;
  quantity: number;
  negotiated_unit_price: number;
  total_amount: number;
  currency: string;
  approval_status: ApprovalStatus;
  payment_status: PaymentStatus;
  razorpay_order_id?: string | null;
  razorpay_payment_link_id?: string | null;
  razorpay_payment_link_url?: string | null;
  razorpay_payment_id?: string | null;
  payment_failure_reason?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProcurementRequestSummary {
  id: number;
  user_id: number;
  raw_prompt: string;
  extracted_constraints?: ProcurementConstraints | null;
  execution_status: ExecutionStage;
  max_budget?: number | null;
  created_at?: string;
  updated_at?: string;
  order?: OrderSummary | null;
}

export interface DashboardMetrics {
  total: number;
  active: number;
  awaiting_approval: number;
  payment_pending: number;
  completed: number;
  failed: number;
}

export interface ProcurementListResponse {
  items: ProcurementRequestSummary[];
  total: number;
  metrics: DashboardMetrics;
}

export interface ExecutionTraceEvent {
  stage: ExecutionStage;
  title: string;
  timestamp?: string | null;
  actor: string;
  summary: string;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  actor: string;
  event_data?: Record<string, any> | null;
  timestamp: string;
}

export interface ProcurementDetailResponse {
  request: ProcurementRequestSummary;
  order?: OrderSummary | null;
  discovered_offers: OfferCandidate[];
  negotiation_traces: NegotiationTrace[];
  negotiation_summary?: NegotiationSummary | null;
  guardrail_result?: GuardrailResult | null;
  execution_trace: ExecutionTraceEvent[];
  audit_events: AuditEvent[];
}
