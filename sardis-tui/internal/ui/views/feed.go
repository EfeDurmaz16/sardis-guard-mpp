package views

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// RenderFeed renders the live event feed tab
func RenderFeed(events []api.EvalEvent, scrollOffset, width, height int) string {
	title := t.TextSecondary.Render("Live Event Feed")
	count := t.TextMuted.Render(fmt.Sprintf("%d events", len(events)))
	header := title + "  " + count

	availableHeight := height - 6
	if availableHeight < 3 {
		availableHeight = 3
	}

	var lines []string

	if len(events) == 0 {
		lines = append(lines, "")
		lines = append(lines, t.TextMuted.Render("  Waiting for evaluations..."))
		lines = append(lines, t.TextMuted.Render("  Events will appear here in real-time as the SSE stream receives them."))
	} else {
		maxLines := availableHeight
		start := len(events) - 1 - scrollOffset
		if start < 0 {
			start = 0
		}
		end := start - maxLines
		if end < -1 {
			end = -1
		}

		for i := start; i > end; i-- {
			e := events[i]
			line := renderFeedLine(e, width-8)
			lines = append(lines, line)

			if e.GetAction() == "DENY" && e.Verdict != nil {
				failedChecks := renderFailedChecks(e.Verdict)
				if failedChecks != "" {
					lines = append(lines, failedChecks)
				}
			}
		}
	}

	content := header + "\n\n" + strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Height(availableHeight + 4).
		Render(content)
}

func renderFeedLine(e api.EvalEvent, width int) string {
	ts := time.Unix(int64(e.Timestamp), 0).Format("15:04:05")

	agent := e.GetAgentName()
	if len(agent) > 14 {
		agent = agent[:14]
	}

	tsStr := t.TextMuted.Render(ts)
	agentStr := t.TextCyan.Width(15).Render(agent)
	merchantStr := t.TextSecondary.Width(20).Render(truncate(e.Merchant, 20))
	amountStr := t.TextAmber.Width(12).Render(fmt.Sprintf("$%s %s", e.Amount, e.Currency))
	networkStr := t.TextMuted.Width(8).Render(e.Network)
	badge := t.ActionBadge(e.GetAction())

	var extra string
	if e.Verdict != nil {
		passed := 0
		for _, c := range e.Verdict.Checks {
			if c.Result == "PASS" {
				passed++
			}
		}
		total := len(e.Verdict.Checks)
		if total > 0 {
			extra = t.TextMuted.Render(fmt.Sprintf("%d/%d passed", passed, total))
		}
		extra += "  " + t.TextMuted.Render(fmt.Sprintf("%.1fms", e.Verdict.TotalLatency))
	} else if e.RiskAssessment != nil {
		r := e.RiskAssessment
		extra = t.TextMuted.Render(fmt.Sprintf("risk:%.2f  ml:%.2f  seq:%.2f", r.FinalScore, r.MLScore, r.SequenceScore))
	}

	return "  " + tsStr + "  " + agentStr + " " + merchantStr + " " + amountStr + " " + networkStr + " " + badge + "  " + extra
}

func renderFailedChecks(v *api.Verdict) string {
	var failed []string
	for _, c := range v.Checks {
		if c.Result != "PASS" {
			failed = append(failed, c.Name)
		}
	}
	if len(failed) == 0 {
		return ""
	}
	arrow := t.TextRed.Render("            ↳ ")
	checks := t.TextRed.Render(strings.Join(failed, ", "))
	return arrow + checks
}
