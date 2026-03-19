package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

// Client talks to the Sardis Guard API
type Client struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewClient creates a new API client, using SARDIS_API_URL env var or default
func NewClient() *Client {
	base := os.Getenv("SARDIS_API_URL")
	if base == "" {
		base = "https://sardis-guard-482463483786.us-central1.run.app"
	}
	return &Client{
		BaseURL: base,
		HTTPClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (c *Client) get(path string, target interface{}) error {
	resp, err := c.HTTPClient.Get(c.BaseURL + path)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 402 {
		return fmt.Errorf("MPP payment required (402)")
	}
	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	return json.NewDecoder(resp.Body).Decode(target)
}

func (c *Client) post(path string, payload interface{}, target interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal error: %w", err)
	}

	resp, err := c.HTTPClient.Post(c.BaseURL+path, "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 402 {
		return fmt.Errorf("MPP payment required (402)")
	}
	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	if target != nil {
		return json.NewDecoder(resp.Body).Decode(target)
	}
	return nil
}

// GetServiceInfo returns GET /
func (c *Client) GetServiceInfo() (*ServiceInfo, error) {
	var info ServiceInfo
	err := c.get("/", &info)
	return &info, err
}

// GetHealth returns GET /health
func (c *Client) GetHealth() (*HealthCheck, error) {
	var h HealthCheck
	err := c.get("/health", &h)
	return &h, err
}

// GetDashboardSummary returns GET /dashboard/summary
func (c *Client) GetDashboardSummary() (*DashboardSummary, error) {
	var s DashboardSummary
	err := c.get("/dashboard/summary", &s)
	return &s, err
}

// GetKillSwitchStatus returns GET /kill-switch/status
func (c *Client) GetKillSwitchStatus() (*KillSwitchStatus, error) {
	var ks KillSwitchStatus
	err := c.get("/kill-switch/status", &ks)
	return &ks, err
}

// GetMandates returns GET /mandates
func (c *Client) GetMandates() (*MandateList, error) {
	var ml MandateList
	err := c.get("/mandates", &ml)
	return &ml, err
}

// GetMandateDetail returns GET /mandates/{id}
func (c *Client) GetMandateDetail(id string) (*MandateDetail, error) {
	var md MandateDetail
	err := c.get("/mandates/"+id, &md)
	return &md, err
}

// ScreenEntity returns POST /screen/entity
func (c *Client) ScreenEntity(name string) (*ScreenResult, error) {
	var sr ScreenResult
	err := c.post("/screen/entity", map[string]string{"name": name}, &sr)
	return &sr, err
}

// ScreenAddress returns POST /screen/address
func (c *Client) ScreenAddress(address string) (*ScreenResult, error) {
	var sr ScreenResult
	err := c.post("/screen/address", map[string]string{"address": address}, &sr)
	return &sr, err
}

// GetServiceGraph returns GET /dashboard/graph
func (c *Client) GetServiceGraph() (*ServiceGraph, error) {
	var sg ServiceGraph
	err := c.get("/dashboard/graph", &sg)
	return &sg, err
}

// CreateRootMandate creates POST /mandates/root
func (c *Client) CreateRootMandate(req map[string]interface{}) (*Mandate, error) {
	var m Mandate
	err := c.post("/mandates/root", req, &m)
	return &m, err
}

// DelegateMandate creates POST /mandates/delegate
func (c *Client) DelegateMandate(req map[string]interface{}) (*Mandate, error) {
	var m Mandate
	err := c.post("/mandates/delegate", req, &m)
	return &m, err
}

// FreezeMandate sends POST /mandates/freeze
func (c *Client) FreezeMandate(id, reason string, freezeChildren bool) error {
	return c.post("/mandates/freeze", map[string]interface{}{
		"mandate_id":      id,
		"reason":          reason,
		"freeze_children": freezeChildren,
	}, nil)
}

// ResumeMandate sends POST /mandates/resume
func (c *Client) ResumeMandate(id string) error {
	return c.post("/mandates/resume", map[string]string{
		"mandate_id": id,
	}, nil)
}

// ActivateKillSwitch sends POST /kill-switch/activate
func (c *Client) ActivateKillSwitch(scope, target, reason string, autoLiftSeconds int) error {
	req := map[string]interface{}{
		"scope":  scope,
		"target": target,
		"reason": reason,
	}
	if autoLiftSeconds > 0 {
		req["auto_lift_seconds"] = autoLiftSeconds
	}
	return c.post("/kill-switch/activate", req, nil)
}

// DeactivateKillSwitch sends POST /kill-switch/deactivate
func (c *Client) DeactivateKillSwitch(scope, target string) error {
	return c.post("/kill-switch/deactivate", map[string]string{
		"scope":  scope,
		"target": target,
	}, nil)
}

// GetEvidencePack returns GET /reports/session/{id}
func (c *Client) GetEvidencePack(sessionID string) (*EvidencePack, error) {
	var ep EvidencePack
	err := c.get("/reports/session/"+sessionID, &ep)
	return &ep, err
}

// GetEvents fetches all events from the evidence pack (free endpoint)
func (c *Client) GetEvents() ([]EvalEvent, error) {
	ep, err := c.GetEvidencePack("current")
	if err != nil {
		return nil, err
	}
	return ep.Events, nil
}

// GetAgentRisk returns GET /agents/{id}/risk
func (c *Client) GetAgentRisk(agentID string) (*AgentRisk, error) {
	var ar AgentRisk
	err := c.get("/agents/"+agentID+"/risk", &ar)
	return &ar, err
}
