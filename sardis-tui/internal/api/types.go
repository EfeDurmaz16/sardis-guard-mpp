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

// SSE evaluation event
type EvalEvent struct {
	// V1 fields
	Timestamp float64   `json:"timestamp"`
	Agent     string    `json:"agent"`
	Merchant  string    `json:"merchant"`
	Amount    string    `json:"amount"`
	Currency  string    `json:"currency"`
	Network   string    `json:"network"`
	Category  string    `json:"category"`
	Type      string    `json:"type"`
	Verdict   *Verdict  `json:"verdict,omitempty"`

	// V2 fields
	EventID          string            `json:"event_id,omitempty"`
	AgentID          string            `json:"agent_id,omitempty"`
	PrincipalID      string            `json:"principal_id,omitempty"`
	MandateID        string            `json:"mandate_id,omitempty"`
	Action           string            `json:"action,omitempty"`
	DownstreamAllowed bool             `json:"downstream_allowed,omitempty"`
	RiskAssessment   *RiskAssessment   `json:"risk_assessment,omitempty"`
	GovernanceResult *GovernanceResult `json:"governance_result,omitempty"`
	AMLResult        *AMLResult        `json:"aml_result,omitempty"`
	EntryHash        string            `json:"entry_hash,omitempty"`
	PrevHash         string            `json:"prev_hash,omitempty"`
}

// GetAgentName returns the agent identifier from either V1 or V2 fields
func (e *EvalEvent) GetAgentName() string {
	if e.AgentID != "" {
		return e.AgentID
	}
	return e.Agent
}

// GetAction returns the action from either V1 verdict or V2 action field
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
	Allowed      bool           `json:"allowed"`
	Summary      string         `json:"summary"`
	TotalLatency float64        `json:"total_latency_ms"`
	Checks       []PolicyCheck  `json:"checks"`
}

type PolicyCheck struct {
	Name    string  `json:"name"`
	Result  string  `json:"result"`
	Reason  string  `json:"reason"`
	Latency float64 `json:"latency_ms"`
}

type RiskAssessment struct {
	MLScore          float64 `json:"ml_score"`
	SequenceScore    float64 `json:"sequence_score"`
	CorrelationScore float64 `json:"correlation_score"`
	SanctionsScore   float64 `json:"sanctions_score"`
	FinalScore       float64 `json:"final_score"`
	Action           string  `json:"action"`
	Reasons          []string `json:"reasons"`
}

type GovernanceResult struct {
	Allowed bool     `json:"allowed"`
	Checks  []string `json:"checks"`
}

type AMLResult struct {
	Hit       bool   `json:"hit"`
	MatchType string `json:"match_type"`
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
	AgentID       string        `json:"agent_id"`
	Summary       interface{}   `json:"summary"`
	RiskTimeline  []interface{} `json:"risk_timeline"`
}

// EvidencePack from GET /reports/session/{id}
type EvidencePack struct {
	SessionID         string        `json:"session_id"`
	GeneratedAt       float64       `json:"generated_at"`
	EventCount        int           `json:"event_count"`
	ChainValid        bool          `json:"chain_valid"`
	FirstHash         string        `json:"first_hash"`
	LastHash          string        `json:"last_hash"`
	Events            []interface{} `json:"events"`
	MandateChain      []interface{} `json:"mandate_chain"`
	RiskAssessments   []interface{} `json:"risk_assessments"`
	SanctionsResults  []interface{} `json:"sanctions_results"`
	FreezeActions     []interface{} `json:"freeze_actions"`
	OperatorActions   []interface{} `json:"operator_actions"`
}
