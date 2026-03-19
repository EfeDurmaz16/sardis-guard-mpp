package views

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
	"sardis-tui/internal/ui/components"
)

// RenderOverview renders the main dashboard overview tab
func RenderOverview(summary *api.DashboardSummary, info *api.ServiceInfo, ks *api.KillSwitchStatus, events []api.EvalEvent, width, height int) string {
	if width < 40 {
		return t.TextMuted.Render("Terminal too narrow")
	}

	var sections []string

	// Stats row
	sections = append(sections, renderStatRow(summary, ks, width))

	// Two-column: Action Breakdown + System Modules
	leftW := (width - 6) / 2
	rightW := width - leftW - 6

	leftPanel := renderActionBreakdown(summary, leftW)
	rightPanel := renderSystemModules(info, rightW)

	twoCol := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, "  ", rightPanel)
	sections = append(sections, twoCol)

	// Recent Activity
	sections = append(sections, renderRecentActivity(events, width))

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

func renderStatRow(summary *api.DashboardSummary, ks *api.KillSwitchStatus, width int) string {
	var stats []string

	if summary != nil {
		stats = append(stats, components.StatBox("EVENTS", fmt.Sprintf("%d", summary.TotalEvents)))
		stats = append(stats, components.StatBox("AGENTS", fmt.Sprintf("%d", summary.ActiveAgents)))
		stats = append(stats, components.StatBox("VOLUME", fmt.Sprintf("$%.2f", summary.TotalVolume)))
		stats = append(stats, components.StatBox("MERCHANTS", fmt.Sprintf("%d", summary.UniqueMerchants)))
	} else {
		stats = append(stats, components.StatBox("EVENTS", "--"))
		stats = append(stats, components.StatBox("AGENTS", "--"))
		stats = append(stats, components.StatBox("VOLUME", "$--"))
		stats = append(stats, components.StatBox("MERCHANTS", "--"))
	}

	killCount := 0
	if ks != nil {
		killCount = ks.ActiveCount
	}
	killLabel := fmt.Sprintf("%d active", killCount)
	if killCount > 0 {
		killLabel = t.TextRed.Render(killLabel)
	}
	stats = append(stats, components.StatBox("KILL SW", killLabel))

	statWidth := (width - 4) / len(stats)
	var rendered []string
	for _, s := range stats {
		rendered = append(rendered, lipgloss.NewStyle().Width(statWidth).Render(s))
	}

	content := lipgloss.JoinHorizontal(lipgloss.Top, rendered...)
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderActionBreakdown(summary *api.DashboardSummary, width int) string {
	title := t.TextSecondary.Render("Action Breakdown")

	total := 0
	actions := map[string]int{
		"ALLOW":  0,
		"FLAG":   0,
		"HOLD":   0,
		"FREEZE": 0,
		"DENY":   0,
	}
	if summary != nil {
		actions["DENY"] = summary.DeniedCount
		actions["FLAG"] = summary.FlaggedCount
		actions["HOLD"] = summary.HeldCount
		actions["FREEZE"] = summary.FrozenCount
		nonAllow := summary.DeniedCount + summary.FlaggedCount + summary.HeldCount + summary.FrozenCount
		actions["ALLOW"] = summary.TotalEvents - nonAllow
		if actions["ALLOW"] < 0 {
			actions["ALLOW"] = 0
		}
		total = summary.TotalEvents
	}

	barWidth := width - 22
	if barWidth < 8 {
		barWidth = 8
	}

	order := []string{"ALLOW", "FLAG", "HOLD", "FREEZE", "DENY"}
	colors := map[string]lipgloss.Color{
		"ALLOW":  t.ColorGreen,
		"FLAG":   t.ColorAmber,
		"HOLD":   t.ColorAmber,
		"FREEZE": t.ColorRed,
		"DENY":   t.ColorRed,
	}

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")

	for _, action := range order {
		count := actions[action]
		ratio := 0.0
		if total > 0 {
			ratio = float64(count) / float64(total)
		}
		label := lipgloss.NewStyle().Width(8).Foreground(t.ColorText70).Render(action)
		bar := components.Gauge(ratio, barWidth, colors[action])
		pct := lipgloss.NewStyle().Width(5).Align(lipgloss.Right).Foreground(t.ColorText50).
			Render(fmt.Sprintf("%d%%", int(ratio*100)))
		lines = append(lines, "  "+label+" "+bar+" "+pct)
	}

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width).
		Render(content)
}

func renderSystemModules(info *api.ServiceInfo, width int) string {
	title := t.TextSecondary.Render("System Modules")

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")

	if info != nil && len(info.Modules) > 0 {
		var names []string
		for name := range info.Modules {
			names = append(names, name)
		}
		sort.Strings(names)

		for _, name := range names {
			active := info.Modules[name]
			dot := t.ModuleDot(active)
			status := "active"
			statusStyle := t.TextGreen
			if !active {
				status = "down"
				statusStyle = t.TextRed
			}

			label := lipgloss.NewStyle().Width(22).Foreground(t.ColorText70).Render(name)
			lines = append(lines, "  "+label+" "+dot+" "+statusStyle.Render(status))
		}
	} else {
		lines = append(lines, t.TextMuted.Render("  No module data"))
	}

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width).
		Render(content)
}

func renderRecentActivity(events []api.EvalEvent, width int) string {
	title := t.TextSecondary.Render("Recent Activity")

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")

	if len(events) == 0 {
		lines = append(lines, t.TextMuted.Render("  No events yet. Waiting for evaluations..."))
	} else {
		count := 5
		if len(events) < count {
			count = len(events)
		}
		for i := len(events) - 1; i >= len(events)-count; i-- {
			e := events[i]
			ts := time.Unix(int64(e.Timestamp), 0).Format("15:04:05")
			agent := e.GetAgentName()
			if len(agent) > 14 {
				agent = agent[:14]
			}

			tsStr := t.TextMuted.Render(ts)
			agentStr := t.TextCyan.Width(15).Render(agent)
			merchantStr := t.TextSecondary.Width(20).Render(truncate(e.Merchant, 20))
			amountStr := t.TextAmber.Width(12).Render(fmt.Sprintf("$%s %s", e.Amount, e.Currency))
			badge := t.ActionBadge(e.GetAction())

			latency := ""
			if e.Verdict != nil {
				latency = t.TextMuted.Render(fmt.Sprintf("%.1fms", e.Verdict.TotalLatency))
			} else if e.RiskAssessment != nil {
				latency = t.TextMuted.Render(fmt.Sprintf("risk:%.2f", e.RiskAssessment.FinalScore))
			}

			lines = append(lines, "  "+tsStr+"  "+agentStr+" "+merchantStr+" "+amountStr+" "+badge+" "+latency)
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

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max-1] + "…"
}
