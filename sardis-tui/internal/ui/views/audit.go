package views

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// AuditState tracks audit view state
type AuditState struct {
	Events       []api.EvalEvent
	Selected     int
	ShowDetail   bool
	Filter       string
	FilterActive bool
}

func NewAuditState() *AuditState {
	return &AuditState{}
}

// HandleKey handles keyboard input for audit view
func (as *AuditState) HandleKey(key string) string {
	if as.FilterActive {
		switch key {
		case "enter", "esc":
			as.FilterActive = false
		case "backspace":
			if len(as.Filter) > 0 {
				as.Filter = as.Filter[:len(as.Filter)-1]
			}
		default:
			if len(key) == 1 {
				as.Filter += key
			}
		}
		return ""
	}

	if as.ShowDetail {
		if key == "esc" || key == "enter" {
			as.ShowDetail = false
		}
		return ""
	}

	switch key {
	case "up", "k":
		if as.Selected > 0 {
			as.Selected--
		}
	case "down", "j":
		if as.Selected < len(as.filteredEvents())-1 {
			as.Selected++
		}
	case "enter":
		if len(as.filteredEvents()) > 0 {
			as.ShowDetail = true
		}
	case "/":
		as.FilterActive = true
	case "e", "E":
		return "export_evidence"
	}
	return ""
}

func (as *AuditState) filteredEvents() []api.EvalEvent {
	if as.Filter == "" {
		return as.Events
	}
	filter := strings.ToLower(as.Filter)
	var filtered []api.EvalEvent
	for _, e := range as.Events {
		agent := strings.ToLower(e.GetAgentName())
		merchant := strings.ToLower(e.Merchant)
		action := strings.ToLower(e.GetAction())
		if strings.Contains(agent, filter) || strings.Contains(merchant, filter) || strings.Contains(action, filter) {
			filtered = append(filtered, e)
		}
	}
	return filtered
}

// RenderAudit renders the audit trail tab
func RenderAudit(as *AuditState, width, height int) string {
	events := as.filteredEvents()

	if as.ShowDetail && as.Selected < len(events) {
		return renderAuditDetail(events[as.Selected], width)
	}

	title := t.TextSecondary.Render("Audit Trail")
	count := t.TextMuted.Render(fmt.Sprintf("%d events", len(events)))

	chainValid := "chain valid " + t.TextGreen.Render("✓")
	if len(events) == 0 {
		chainValid = ""
	}

	var lines []string
	lines = append(lines, title+"  "+count+"  "+chainValid)
	lines = append(lines, "")

	// Filter bar
	if as.FilterActive {
		filterInput := as.Filter + lipgloss.NewStyle().Foreground(t.ColorAmber).Render("▎")
		lines = append(lines, "  "+t.TextAmber.Render("/ ")+lipgloss.NewStyle().Foreground(t.ColorText).Render(filterInput))
		lines = append(lines, "")
	} else if as.Filter != "" {
		lines = append(lines, "  "+t.TextMuted.Render("filter: ")+t.TextAmber.Render(as.Filter)+"  "+t.TextMuted.Render("(/ to edit)"))
		lines = append(lines, "")
	}

	// Table header
	hdrTime := lipgloss.NewStyle().Width(10).Foreground(t.ColorText30).Render("TIME")
	hdrAgent := lipgloss.NewStyle().Width(15).Foreground(t.ColorText30).Render("AGENT")
	hdrMerchant := lipgloss.NewStyle().Width(20).Foreground(t.ColorText30).Render("MERCHANT")
	hdrAmount := lipgloss.NewStyle().Width(10).Foreground(t.ColorText30).Render("AMOUNT")
	hdrAction := lipgloss.NewStyle().Width(12).Foreground(t.ColorText30).Render("ACTION")
	hdrRisk := lipgloss.NewStyle().Foreground(t.ColorText30).Render("RISK")
	lines = append(lines, "  "+hdrTime+hdrAgent+hdrMerchant+hdrAmount+hdrAction+hdrRisk)

	sep := lipgloss.NewStyle().Foreground(t.ColorText30).
		Render("  " + strings.Repeat("─", 10) + strings.Repeat("─", 15) + strings.Repeat("─", 20) + strings.Repeat("─", 10) + strings.Repeat("─", 12) + strings.Repeat("─", 8))
	lines = append(lines, sep)

	if len(events) == 0 {
		lines = append(lines, "  "+t.TextMuted.Render("No events recorded"))
	} else {
		availableLines := height - len(lines) - 6
		if availableLines < 3 {
			availableLines = 3
		}

		start := 0
		if len(events) > availableLines {
			start = len(events) - availableLines
		}

		for i := start; i < len(events); i++ {
			isSelected := i == as.Selected
			e := events[i]

			ts := time.Unix(int64(e.Timestamp), 0).Format("15:04:05")
			agent := e.GetAgentName()
			if len(agent) > 14 {
				agent = agent[:14]
			}

			sel := "  "
			if isSelected {
				sel = lipgloss.NewStyle().Foreground(t.ColorAmber).Render("▸ ")
			}

			tsStr := t.TextMuted.Width(10).Render(ts)

			agentStyle := t.TextCyan
			if isSelected {
				agentStyle = lipgloss.NewStyle().Foreground(t.ColorAmber)
			}
			agentStr := agentStyle.Width(15).Render(agent)

			merchantStr := t.TextSecondary.Width(20).Render(truncate(e.Merchant, 19))
			amountStr := t.TextPrimary.Width(10).Render("$" + e.Amount)
			badge := t.ActionBadge(e.GetAction())

			risk := ""
			if e.RiskAssessment != nil {
				risk = t.TextMuted.Render(fmt.Sprintf("%.2f", e.RiskAssessment.FinalScore))
			}

			lines = append(lines, sel+tsStr+agentStr+merchantStr+amountStr+lipgloss.NewStyle().Width(12).Render(badge)+risk)
		}
	}

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderAuditDetail(e api.EvalEvent, width int) string {
	title := t.TextSecondary.Render("Event Detail")

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")

	ts := time.Unix(int64(e.Timestamp), 0).Format("2006-01-02 15:04:05")

	fields := []struct {
		Label string
		Value string
	}{
		{"Event ID", e.EventID},
		{"Time", ts},
		{"Agent", e.GetAgentName()},
		{"Principal", e.PrincipalID},
		{"Merchant", e.Merchant},
		{"Amount", "$" + e.Amount + " " + e.Currency},
		{"Network", e.Network},
		{"Action", e.GetAction()},
	}

	for _, f := range fields {
		if f.Value == "" {
			continue
		}
		label := lipgloss.NewStyle().Width(14).Foreground(t.ColorText50).Render(f.Label)
		lines = append(lines, "  "+label+t.TextPrimary.Render(f.Value))
	}

	// Policy checks
	if e.Verdict != nil {
		lines = append(lines, "")
		lines = append(lines, "  "+t.TextSecondary.Render("Policy Checks"))
		for _, c := range e.Verdict.Checks {
			var icon string
			if c.Result == "PASS" {
				icon = t.TextGreen.Render("✓")
			} else {
				icon = t.TextRed.Render("✗")
			}
			name := t.TextMuted.Width(22).Render(c.Name)
			lines = append(lines, "    "+icon+" "+name+t.TextMuted.Render(c.Reason))
		}
	}

	// Risk assessment
	if e.RiskAssessment != nil {
		r := e.RiskAssessment
		lines = append(lines, "")
		lines = append(lines, "  "+t.TextSecondary.Render("Risk Assessment"))
		riskFields := []struct {
			Label string
			Value string
		}{
			{"Final Score", fmt.Sprintf("%.4f", r.FinalScore)},
			{"ML Score", fmt.Sprintf("%.4f", r.MLScore)},
			{"Sequence", fmt.Sprintf("%.4f", r.SequenceScore)},
			{"Correlation", fmt.Sprintf("%.4f", r.CorrelationScore)},
			{"Sanctions", fmt.Sprintf("%.4f", r.SanctionsScore)},
			{"Action", r.Action},
		}
		for _, f := range riskFields {
			label := lipgloss.NewStyle().Width(14).Foreground(t.ColorText50).Render(f.Label)
			lines = append(lines, "    "+label+t.TextPrimary.Render(f.Value))
		}
	}

	// Hash chain
	if e.EntryHash != "" {
		lines = append(lines, "")
		lines = append(lines, "  "+t.TextSecondary.Render("Hash Chain"))
		hashLabel := lipgloss.NewStyle().Width(14).Foreground(t.ColorText50)
		if e.PrevHash != "" {
			lines = append(lines, "    "+hashLabel.Render("Prev Hash")+t.TextMuted.Render(truncate(e.PrevHash, 40)))
		}
		lines = append(lines, "    "+hashLabel.Render("Entry Hash")+t.TextMuted.Render(truncate(e.EntryHash, 40)))
	}

	lines = append(lines, "")
	lines = append(lines, "  "+t.TextMuted.Render("Press Esc to return"))

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorderHi).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}
