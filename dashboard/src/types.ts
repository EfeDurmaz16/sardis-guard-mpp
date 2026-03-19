export type Action = "ALLOW" | "FLAG" | "HOLD" | "FREEZE_CHILD" | "FREEZE_TREE" | "DENY";

export interface PolicyCheck {
  name: string;
  result: "PASS" | "FAIL" | "SKIP";
  reason: string;
  latency_ms: number;
}

export interface Verdict {
  allowed: boolean;
  summary: string;
  total_latency_ms: number;
  checks: PolicyCheck[];
}

export interface AuditEvent {
  timestamp: number;
  agent: string;
  merchant: string;
  amount: string;
  currency: string;
  network: string;
  category: string;
  verdict: Verdict;
  type: "evaluate" | "simulate";
  // V2 fields
  event_id?: string;
  agent_id?: string;
  action?: Action;
  downstream_allowed?: boolean;
  risk_assessment?: RiskAssessment;
  governance_result?: GovernanceResult;
  aml_result?: AmlResult;
  entry_hash?: string;
  prev_hash?: string;
}

export interface RiskAssessment {
  ml_score: number;
  sequence_score: number;
  correlation_score: number;
  sanctions_score: number;
  final_score: number;
  action: Action;
  features?: Record<string, number>;
  reasons?: string[];
}

export interface AmlResult {
  hit: boolean;
  match_type?: string;
  matched_entry?: string;
  confidence?: number;
}

export interface GovernanceResult {
  allowed: boolean;
  checks?: unknown[];
  action?: string;
}

export interface MandateNode {
  mandate_id: string;
  parent_id: string | null;
  principal_id: string;
  agent_id: string;
  max_total: string;
  max_per_tx: string;
  spent: string;
  remaining: string;
  allowed_services: string[];
  allowed_merchants: string[];
  blocked_merchants: string[];
  allowed_chains: string[];
  allowed_currencies: string[];
  status: "active" | "frozen" | "expired" | "exhausted";
  approval_threshold: string;
  delegation_depth: number;
  max_delegation_depth: number;
  created_at: number;
  expires_at: number;
  frozen_at: number;
  frozen_reason: string;
  is_active: boolean;
}

export interface DashboardSummary {
  total_events: number;
  active_agents: number;
  total_volume: number;
  unique_merchants: number;
  denied_count: number;
  flagged_count: number;
  held_count: number;
  frozen_count: number;
  mandates_active: number;
  mandates_frozen: number;
  mandates_total: number;
}

export interface ServiceInfo {
  service: string;
  version: string;
  modules: Record<string, boolean>;
  endpoints: Record<string, string>;
}

export interface HealthData {
  status: string;
  agents_tracked: number;
  mandates_active: number;
}

export interface KillSwitchState {
  scope: string;
  target: string;
  reason: string;
  activated_at: number;
  auto_lift_at: number | null;
  activated_by: string;
}

export interface ScreeningResult {
  entity?: string;
  address?: string;
  hit: boolean;
  match_type: string;
  matched_entry: string;
  list_source: string;
  confidence: number;
}

export interface EvidencePack {
  session_id: string;
  generated_at: number;
  event_count: number;
  chain_valid: boolean;
  first_hash: string;
  last_hash: string;
  events: unknown[];
  mandate_chain: unknown[];
}

export interface RiskDataPoint {
  time: number;
  timeLabel: string;
  score: number;
  action: Action;
  agent: string;
}

export interface ActionBreakdown {
  ALLOW: number;
  FLAG: number;
  HOLD: number;
  FREEZE: number;
  DENY: number;
}

export interface DashboardStats {
  totalEvents: number;
  activeMandates: number;
  frozenMandates: number;
  avgRiskScore: number;
  actions: ActionBreakdown;
  agentsTracked: number;
  totalVolume: number;
  uniqueMerchants: number;
}

export type ViewId = "overview" | "feed" | "policy" | "mandates" | "screening" | "killswitch" | "audit";
