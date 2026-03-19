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
}

export interface HealthData {
  status: string;
  agents_tracked: number;
  mandates_active: number;
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
}
