package ui

import (
	"fmt"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
	"sardis-tui/internal/ui/views"
)

// Tab indices
const (
	TabOverview  = 0
	TabFeed      = 1
	TabPolicy    = 2
	TabMandates  = 3
	TabScreening = 4
	TabAudit     = 5
)

// Messages
type (
	tickMsg         struct{}
	sseEventMsg     api.EvalEvent
	sseConnectedMsg bool
	sseErrorMsg     error
	healthMsg       *api.HealthCheck
	summaryMsg      *api.DashboardSummary
	serviceInfoMsg  *api.ServiceInfo
	killSwitchMsg   *api.KillSwitchStatus
	mandatesMsg     *api.MandateList
	screenMsg       struct {
		Query  string
		Type   string
		Result *api.ScreenResult
		Err    error
	}
	apiErrorMsg struct {
		Source string
		Err    error
	}
)

// App is the main Bubble Tea model
type App struct {
	client    *api.Client
	stream    *api.SSEStream
	width     int
	height    int
	activeTab int
	connected bool
	showHelp  bool

	// Data
	health     *api.HealthCheck
	summary    *api.DashboardSummary
	info       *api.ServiceInfo
	killSwitch *api.KillSwitchStatus
	events     []api.EvalEvent
	eventCount int

	// View states
	feedScroll   int
	policyState  *views.PolicyState
	mandateState *views.MandateState
	screenState  *views.ScreeningState
	auditState   *views.AuditState
}

// NewApp creates the main application model
func NewApp() *App {
	client := api.NewClient()
	stream := api.NewSSEStream(client.BaseURL)

	return &App{
		client:       client,
		stream:       stream,
		policyState:  views.NewPolicyState(),
		mandateState: views.NewMandateState(),
		screenState:  views.NewScreeningState(),
		auditState:   views.NewAuditState(),
	}
}

func (a *App) Init() tea.Cmd {
	a.stream.Start()
	return tea.Batch(
		a.pollSSE(),
		a.fetchInitialData(),
		a.tick(),
	)
}

func (a *App) tick() tea.Cmd {
	return tea.Tick(5*time.Second, func(t time.Time) tea.Msg {
		return tickMsg{}
	})
}

func (a *App) pollSSE() tea.Cmd {
	return func() tea.Msg {
		select {
		case event := <-a.stream.Events:
			return sseEventMsg(event)
		case connected := <-a.stream.Connected:
			return sseConnectedMsg(connected)
		case err := <-a.stream.Errors:
			return sseErrorMsg(err)
		}
	}
}

func (a *App) fetchInitialData() tea.Cmd {
	return tea.Batch(
		a.fetchHealth(),
		a.fetchSummary(),
		a.fetchServiceInfo(),
		a.fetchKillSwitch(),
		a.fetchMandates(),
	)
}

func (a *App) fetchHealth() tea.Cmd {
	return func() tea.Msg {
		h, err := a.client.GetHealth()
		if err != nil {
			return apiErrorMsg{"health", err}
		}
		return healthMsg(h)
	}
}

func (a *App) fetchSummary() tea.Cmd {
	return func() tea.Msg {
		s, err := a.client.GetDashboardSummary()
		if err != nil {
			return apiErrorMsg{"summary", err}
		}
		return summaryMsg(s)
	}
}

func (a *App) fetchServiceInfo() tea.Cmd {
	return func() tea.Msg {
		i, err := a.client.GetServiceInfo()
		if err != nil {
			return apiErrorMsg{"info", err}
		}
		return serviceInfoMsg(i)
	}
}

func (a *App) fetchKillSwitch() tea.Cmd {
	return func() tea.Msg {
		ks, err := a.client.GetKillSwitchStatus()
		if err != nil {
			return apiErrorMsg{"killswitch", err}
		}
		return killSwitchMsg(ks)
	}
}

func (a *App) fetchMandates() tea.Cmd {
	return func() tea.Msg {
		ml, err := a.client.GetMandates()
		if err != nil {
			return apiErrorMsg{"mandates", err}
		}
		return mandatesMsg(ml)
	}
}

func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		return a.handleKey(msg)

	case tea.WindowSizeMsg:
		a.width = msg.Width
		a.height = msg.Height
		return a, nil

	case tickMsg:
		return a, tea.Batch(
			a.fetchHealth(),
			a.fetchSummary(),
			a.fetchKillSwitch(),
			a.tick(),
		)

	case sseEventMsg:
		event := api.EvalEvent(msg)
		a.events = append(a.events, event)
		a.eventCount++
		a.auditState.Events = a.events
		return a, a.pollSSE()

	case sseConnectedMsg:
		a.connected = bool(msg)
		return a, a.pollSSE()

	case sseErrorMsg:
		a.connected = false
		return a, a.pollSSE()

	case healthMsg:
		a.health = (*api.HealthCheck)(msg)
		if msg != nil {
			a.connected = true
		}
		return a, nil

	case summaryMsg:
		a.summary = (*api.DashboardSummary)(msg)
		return a, nil

	case serviceInfoMsg:
		a.info = (*api.ServiceInfo)(msg)
		return a, nil

	case killSwitchMsg:
		a.killSwitch = (*api.KillSwitchStatus)(msg)
		return a, nil

	case mandatesMsg:
		if msg != nil {
			a.mandateState.Mandates = msg.Mandates
		}
		return a, nil

	case screenMsg:
		a.screenState.Loading = false
		if msg.Err != nil {
			a.screenState.Error = msg.Err.Error()
		} else {
			a.screenState.Results = append(a.screenState.Results, views.ScreeningResult{
				Query:  msg.Query,
				Type:   msg.Type,
				Result: msg.Result,
			})
		}
		return a, nil

	case apiErrorMsg:
		return a, nil
	}

	return a, nil
}

func (a *App) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	// Don't intercept keys in text-input tabs
	inTextInput := false
	switch a.activeTab {
	case TabPolicy:
		if !a.policyState.Submitted {
			inTextInput = true
		}
	case TabScreening:
		inTextInput = true
	case TabAudit:
		if a.auditState.FilterActive {
			inTextInput = true
		}
	}

	// Global keys that always work — even in text input
	switch key {
	case "ctrl+c":
		a.stream.Stop()
		return a, tea.Quit
	case "esc":
		// Esc always returns to overview (escape from any view)
		if inTextInput {
			// Let the view handle esc first for internal state
			switch a.activeTab {
			case TabPolicy:
				if a.policyState.Submitted {
					a.policyState.Submitted = false
					a.policyState.Result = nil
					a.policyState.Error = ""
					return a, nil
				}
				// Not submitted — switch to overview
				a.activeTab = TabOverview
				return a, nil
			case TabScreening:
				if a.screenState.Input != "" {
					a.screenState.Input = ""
					return a, nil
				}
				a.activeTab = TabOverview
				return a, nil
			case TabAudit:
				if a.auditState.FilterActive {
					a.auditState.FilterActive = false
					return a, nil
				}
			}
		}
	}

	// Global keys that only work outside text input
	if !inTextInput {
		switch key {
		case "q":
			a.stream.Stop()
			return a, tea.Quit
		case "?":
			a.showHelp = !a.showHelp
			return a, nil
		case "1":
			a.activeTab = TabOverview
			return a, nil
		case "2":
			a.activeTab = TabFeed
			return a, nil
		case "3":
			a.activeTab = TabPolicy
			return a, nil
		case "4":
			a.activeTab = TabMandates
			return a, a.fetchMandates()
		case "5":
			a.activeTab = TabScreening
			return a, nil
		case "6":
			a.activeTab = TabAudit
			return a, nil
		case "r":
			return a, a.fetchInitialData()
		}
	}

	// Tab-specific keys
	switch a.activeTab {
	case TabPolicy:
		a.policyState.HandleKey(key)
		if a.policyState.Submitted && a.policyState.Result == nil && a.policyState.Error == "" {
			return a, a.evaluatePolicy()
		}

	case TabMandates:
		action := a.mandateState.HandleKey(key)
		return a, a.handleMandateAction(action)

	case TabScreening:
		action := a.screenState.HandleKey(key)
		return a, a.handleScreenAction(action)

	case TabAudit:
		action := a.auditState.HandleKey(key)
		return a, a.handleAuditAction(action)

	case TabFeed:
		switch key {
		case "up", "k":
			if a.feedScroll < len(a.events)-1 {
				a.feedScroll++
			}
		case "down", "j":
			if a.feedScroll > 0 {
				a.feedScroll--
			}
		}
	}

	return a, nil
}

func (a *App) evaluatePolicy() tea.Cmd {
	return func() tea.Msg {
		vals := a.policyState.GetValues()

		reqBody := map[string]interface{}{
			"amount":   vals["Amount"],
			"merchant": vals["Merchant"],
			"currency": vals["Currency"],
			"network":  vals["Network"],
			"category": vals["Category"],
		}
		if vals["Memo"] != "" && vals["Memo"] != "(optional)" {
			reqBody["memo"] = vals["Memo"]
		}

		// simulate is MPP-gated, show the command to run
		a.policyState.Error = fmt.Sprintf(
			"Policy simulation requires MPP payment ($0.0005).\n\n"+
				"  Run this command:\n"+
				"  tempo request -t -X POST \\\n"+
				"    --json '{\"amount\":\"%s\",\"merchant\":\"%s\",\"currency\":\"%s\",\"network\":\"%s\"}' \\\n"+
				"    <server>/simulate",
			vals["Amount"], vals["Merchant"], vals["Currency"], vals["Network"])
		return nil
	}
}

func (a *App) handleMandateAction(action string) tea.Cmd {
	if action == "" {
		return nil
	}

	switch {
	case len(action) > 7 && action[:7] == "freeze:":
		id := action[7:]
		return func() tea.Msg {
			_ = a.client.FreezeMandate(id, "Frozen via TUI", true)
			ml, _ := a.client.GetMandates()
			if ml != nil {
				return mandatesMsg(ml)
			}
			return nil
		}

	case len(action) > 7 && action[:7] == "resume:":
		id := action[7:]
		return func() tea.Msg {
			_ = a.client.ResumeMandate(id)
			ml, _ := a.client.GetMandates()
			if ml != nil {
				return mandatesMsg(ml)
			}
			return nil
		}
	}

	return nil
}

func (a *App) handleScreenAction(action string) tea.Cmd {
	if action == "" {
		return nil
	}

	switch {
	case len(action) > 14 && action[:14] == "screen_entity:":
		query := action[14:]
		a.screenState.Loading = true
		return func() tea.Msg {
			result, err := a.client.ScreenEntity(query)
			return screenMsg{Query: query, Type: "entity", Result: result, Err: err}
		}

	case len(action) > 15 && action[:15] == "screen_address:":
		query := action[15:]
		a.screenState.Loading = true
		return func() tea.Msg {
			result, err := a.client.ScreenAddress(query)
			return screenMsg{Query: query, Type: "address", Result: result, Err: err}
		}
	}

	return nil
}

func (a *App) handleAuditAction(action string) tea.Cmd {
	if action == "export_evidence" {
		return func() tea.Msg {
			_, _ = a.client.GetEvidencePack("current")
			return nil
		}
	}
	return nil
}

func (a *App) View() string {
	if a.width == 0 {
		return "Loading..."
	}

	if a.showHelp {
		return a.renderHelp()
	}

	// Header
	header := RenderHeader(a.activeTab, a.connected, a.width)

	// Content area (header=3 + helpbar=1 + statusbar=3 + gaps=2)
	contentHeight := a.height - 9
	var content string

	switch a.activeTab {
	case TabOverview:
		content = views.RenderOverview(a.summary, a.info, a.killSwitch, a.events, a.width, contentHeight)
	case TabFeed:
		content = views.RenderFeed(a.events, a.feedScroll, a.width, contentHeight)
	case TabPolicy:
		content = views.RenderPolicy(a.policyState, a.width, contentHeight)
	case TabMandates:
		content = views.RenderMandates(a.mandateState, a.width, contentHeight)
	case TabScreening:
		content = views.RenderScreening(a.screenState, a.width, contentHeight)
	case TabAudit:
		content = views.RenderAudit(a.auditState, a.width, contentHeight)
	}

	// Context help bar
	helpbar := RenderHelpBar(a.activeTab, a.width)

	// Status bar
	statusbar := RenderStatusBar(a.summary, a.eventCount, a.width)

	return header + "\n" + content + "\n" + helpbar + "\n" + statusbar
}

func (a *App) renderHelp() string {
	title := t.TextAmber.Render("SARDIS GUARD — Keyboard Shortcuts")

	keys := []struct {
		Key  string
		Desc string
	}{
		{"1-6", "Switch tabs"},
		{"Tab", "Next field (in forms)"},
		{"q / Ctrl+C", "Quit"},
		{"?", "Toggle this help"},
		{"r", "Refresh data"},
		{"j/k / up/down", "Navigate lists"},
		{"Enter", "Select / expand"},
		{"Esc", "Back / close"},
		{"", ""},
		{"", "Mandates:"},
		{"N", "New root mandate"},
		{"F", "Freeze mandate"},
		{"R", "Resume mandate"},
		{"", ""},
		{"", "Screening:"},
		{"Tab", "Switch entity/address"},
		{"Enter", "Screen"},
		{"", ""},
		{"", "Audit:"},
		{"E", "Export evidence pack"},
		{"/", "Filter events"},
	}

	var lines string
	for _, k := range keys {
		if k.Key == "" {
			lines += "\n  " + t.TextSecondary.Render(k.Desc)
		} else {
			keyStr := t.TextAmber.Width(16).Render(k.Key)
			lines += "\n  " + keyStr + t.TextSecondary.Render(k.Desc)
		}
	}

	return t.PanelStyle.Width(a.width - 4).Render(title + "\n" + lines + "\n\n  " + t.TextMuted.Render("Press ? to close"))
}
