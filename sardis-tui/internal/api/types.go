package api

// ServiceInfo from GET /
type ServiceInfo struct {
	Service     string            `json:"service"`
	Version     string            `json:"version"`
	Description string            `json:"description"`
	Modules     map[string]bool   `json:"modules"`
	Endpoints   map[string]string `json:"endpoints"`
	Protocol    string            `json:"protocol"`
}

// HealthCheck from GET /health
type HealthCheck struct {
	Status         string `json:"status"`
	AgentsTracked  int    `json:"agents_tracked"`
	MandatesActive int    `json:"mandates_active"`
}

// DashboardSummary from GET /dashboard/summary
type DashboardSummary struct {
	TotalEvents     int     `json:"total_events"`
	ActiveAgents    int     `json:"active_agents"`
	TotalVolume     float64 `json:"total_volume"`
	UniqueMerchants int     `json:"unique_merchants"`
	DeniedCount     int     `json:"denied_count"`
	FlaggedCount    int     `json:"flagged_count"`
	HeldCount       int     `json:"held_count"`
	FrozenCount     int     `json:"frozen_count"`
	MandatesActive  int     `json:"mandates_active"`
	MandatesFrozen  int     `json:"mandates_frozen"`
	MandatesTotal   int     `json:"mandates_total"`
}

// KillSwitchStatus from GET /kill-switch/status
type KillSwitchStatus struct {
	ActiveCount int          `json:"active_count"`
	Switches    []KillSwitch `json:"switches"`
}

type KillSwitch struct {
	Scope       string   `json:"scope"`
	Target      string   `json:"target"`
	Reason      string   `json:"reason"`
	ActivatedAt float64  `json:"activated_at"`
	AutoLiftAt  *float64 `json:"auto_lift_at"`
	ActivatedBy string   `json:"activated_by"`
}

// Mandate from GET /mandates
type MandateList struct {
	Mandates []Mandate `json:"mandates"`
}

type Mandate struct {
	MandateID          string   `json:"mandate_id"`
	ParentID           *string  `json:"parent_id"`
	PrincipalID        string   `json:"principal_id"`
	AgentID            string   `json:"agent_id"`
	MaxTotal           string   `json:"max_total"`
	MaxPerTx           string   `json:"max_per_tx"`
	Spent              string   `json:"spent"`
	Remaining          string   `json:"remaining"`
	AllowedServices    []string `json:"allowed_services"`
	AllowedMerchants   []string `json:"allowed_merchants"`
	BlockedMerchants   []string `json:"blocked_merchants"`
	AllowedChains      []string `json:"allowed_chains"`
	AllowedCurrencies  []string `json:"allowed_currencies"`
	Status             string   `json:"status"`
	ApprovalThreshold  string   `json:"approval_threshold"`
	DelegationDepth    int      `json:"delegation_depth"`
	MaxDelegationDepth int      `json:"max_delegation_depth"`
	CreatedAt          float64  `json:"created_at"`
	ExpiresAt          float64  `json:"expires_at"`
	FrozenAt           float64  `json:"frozen_at"`
	FrozenReason       string   `json:"frozen_reason"`
	IsActive           bool     `json:"is_active"`
}

type MandateDetail struct {
	Mandate  Mandate   `json:"mandate"`
	Children []Mandate `json:"children"`
	TreeSize int       `json:"tree_size"`
}

// Screening from POST /screen/entity and POST /screen/address
type ScreenResult struct {
	Entity       string  `json:"entity,omitempty"`
	Address      string  `json:"address,omitempty"`
	Hit          bool    `json:"hit"`
	MatchType    string  `json:"match_type"`
	MatchedEntry string  `json:"matched_entry"`
	ListSource   string  `json:"list_source"`
	Confidence   float64 `json:"confidence"`
}

// EvalEvent is the canonical event shape from /reports/session/current
type EvalEvent struct {
	EventID            string            `json:"event_id"`
	Timestamp          float64           `json:"timestamp"`
	AgentID            string            `json:"agent_id"`
	PrincipalID        string            `json:"principal_id"`
	MandateID          string            `json:"mandate_id"`
	Amount             string            `json:"amount"`
	Currency           string            `json:"currency"`
	Network            string            `json:"network"`
	Merchant           string            `json:"merchant"`
	Category           string            `json:"category"`
	ServiceID          string            `json:"service_id"`
	DestinationAddress string            `json:"destination_address"`
	Action             string            `json:"action"`
	RiskAssessment     *RiskAssessment   `json:"risk_assessment,omitempty"`
	GovernanceResult   *GovernanceResult `json:"governance_result,omitempty"`
	AMLResult          *AMLResult        `json:"aml_result,omitempty"`
	EntryHash          string            `json:"entry_hash,omitempty"`
	PrevHash           string            `json:"prev_hash,omitempty"`

	// SSE-only fields
	Agent   string   `json:"agent,omitempty"`
	Verdict *Verdict `json:"verdict,omitempty"`
}

// GetAgentName returns the agent identifier
func (e *EvalEvent) GetAgentName() string {
	if e.AgentID != "" {
		return e.AgentID
	}
	return e.Agent
}

// GetAction returns the action
func (e *EvalEvent) GetAction() string {
	if e.Action != "" {
		return e.Action
	}
	if e.Verdict != nil {
		if e.Verdict.Allowed {
			return "ALLOW"
		}
		return "DENY"
	}
	return "UNKNOWN"
}

type Verdict struct {
	Allowed      bool          `json:"allowed"`
	Summary      string        `json:"summary"`
	TotalLatency float64       `json:"total_latency_ms"`
	Checks       []PolicyCheck `json:"checks"`
}

type PolicyCheck struct {
	Name    string  `json:"name"`
	Result  string  `json:"result"`
	Reason  string  `json:"reason"`
	Latency float64 `json:"latency_ms"`
}

type RiskAssessment struct {
	MLScore          float64            `json:"ml_score"`
	SequenceScore    float64            `json:"sequence_score"`
	CorrelationScore float64            `json:"correlation_score"`
	SanctionsScore   float64            `json:"sanctions_score"`
	FinalScore       float64            `json:"final_score"`
	Action           string             `json:"action"`
	Features         map[string]float64 `json:"features,omitempty"`
	Reasons          []string           `json:"reasons"`
}

type GovernanceResult struct {
	Allowed bool              `json:"allowed"`
	Action  string            `json:"action"`
	Reason  string            `json:"reason"`
	Checks  []GovernanceCheck `json:"checks"`
}

type GovernanceCheck struct {
	Check  string `json:"check"`
	Passed bool   `json:"passed"`
	Detail string `json:"detail"`
}

type AMLResult struct {
	Hit          bool    `json:"hit"`
	MatchType    string  `json:"match_type"`
	MatchedEntry string  `json:"matched_entry"`
	Confidence   float64 `json:"confidence"`
}

// ServiceGraph from GET /dashboard/graph
type ServiceGraph struct {
	Graph struct {
		Edges []GraphEdge `json:"edges"`
	} `json:"graph"`
}

type GraphEdge struct {
	From   string `json:"from"`
	To     string `json:"to"`
	Weight int    `json:"weight"`
}

// AgentRisk from GET /agents/{id}/risk
type AgentRisk struct {
	AgentID      string          `json:"agent_id"`
	Summary      AgentSummary    `json:"summary"`
	RiskTimeline []RiskTimepoint `json:"risk_timeline"`
}

type AgentSummary struct {
	AgentID         string  `json:"agent_id"`
	TotalSpent      float64 `json:"total_spent"`
	TxCount         int     `json:"tx_count"`
	UniqueMerchants int     `json:"unique_merchants"`
	RiskTrend       string  `json:"risk_trend"`
}

type RiskTimepoint struct {
	Timestamp  float64 `json:"timestamp"`
	FinalScore float64 `json:"final_score"`
}

// EvidencePack from GET /reports/session/{id}
type EvidencePack struct {
	SessionID        string      `json:"session_id"`
	GeneratedAt      float64     `json:"generated_at"`
	EventCount       int         `json:"event_count"`
	ChainValid       bool        `json:"chain_valid"`
	FirstHash        string      `json:"first_hash"`
	LastHash         string      `json:"last_hash"`
	Events           []EvalEvent `json:"events"`
	MandateChain     []Mandate   `json:"mandate_chain"`
	RiskAssessments  []interface{} `json:"risk_assessments"`
	SanctionsResults []interface{} `json:"sanctions_results"`
	FreezeActions    []interface{} `json:"freeze_actions"`
	OperatorActions  []interface{} `json:"operator_actions"`
}
