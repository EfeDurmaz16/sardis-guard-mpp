package views

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
	"sardis-tui/internal/ui/components"
)

// MandateState tracks mandate view state
type MandateState struct {
	Mandates   []api.Mandate
	Selected   int
	ShowDetail bool
	Error      string
}

// NewMandateState creates a fresh mandate state
func NewMandateState() *MandateState {
	return &MandateState{}
}

// HandleKey handles keyboard input for mandate view
func (ms *MandateState) HandleKey(key string) string {
	if ms.ShowDetail {
		switch key {
		case "esc":
			ms.ShowDetail = false
		case "f", "F":
			if ms.Selected < len(ms.Mandates) {
				return "freeze:" + ms.Mandates[ms.Selected].MandateID
			}
		case "r", "R":
			if ms.Selected < len(ms.Mandates) {
				return "resume:" + ms.Mandates[ms.Selected].MandateID
			}
		}
		return ""
	}

	switch key {
	case "up", "k":
		if ms.Selected > 0 {
			ms.Selected--
		}
	case "down", "j":
		if ms.Selected < len(ms.Mandates)-1 {
			ms.Selected++
		}
	case "enter":
		if len(ms.Mandates) > 0 {
			ms.ShowDetail = true
		}
	case "n", "N":
		return "create_root"
	}
	return ""
}

// RenderMandates renders the mandate tree tab
func RenderMandates(ms *MandateState, width, height int) string {
	if ms.ShowDetail && ms.Selected < len(ms.Mandates) {
		return renderMandateDetail(ms.Mandates[ms.Selected], width)
	}

	return renderMandateTree(ms, width, height)
}

func renderMandateTree(ms *MandateState, width, height int) string {
	frozenCount := 0
	for _, m := range ms.Mandates {
		if m.Status == "frozen" {
			frozenCount++
		}
	}

	title := t.TextSecondary.Render("Mandate Tree")
	stats := t.TextMuted.Render(fmt.Sprintf("%d nodes", len(ms.Mandates)))
	if frozenCount > 0 {
		stats += t.TextRed.Render(fmt.Sprintf(" · %d frozen", frozenCount))
	}

	var lines []string
	lines = append(lines, title+"  "+stats)
	lines = append(lines, "")

	if len(ms.Mandates) == 0 {
		lines = append(lines, t.TextMuted.Render("  No mandates configured."))
		lines = append(lines, t.TextMuted.Render("  Press N to create a root mandate."))
	} else {
		children := make(map[string][]int)
		var roots []int
		for i, m := range ms.Mandates {
			if m.ParentID == nil || *m.ParentID == "" {
				roots = append(roots, i)
			} else {
				children[*m.ParentID] = append(children[*m.ParentID], i)
			}
		}

		for ri, rootIdx := range roots {
			isLastRoot := ri == len(roots)-1
			lines = append(lines, renderMandateNode(ms, rootIdx, 0, isLastRoot, children, width)...)
		}
	}

	lines = append(lines, "")
	lines = append(lines, "  "+t.TextMuted.Render("[N] New root   [Enter] Detail   [F] Freeze   [R] Resume"))

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderMandateNode(ms *MandateState, idx, depth int, isLast bool, children map[string][]int, width int) []string {
	m := ms.Mandates[idx]
	isSelected := idx == ms.Selected

	prefix := components.TreePrefix(isLast, depth)

	agentName := m.AgentID
	if len(agentName) > 22 {
		agentName = agentName[:22]
	}
	nameStyle := t.TextCyan
	if isSelected {
		nameStyle = lipgloss.NewStyle().Foreground(t.ColorAmber).Bold(true)
	}
	name := nameStyle.Width(23).Render(agentName)

	status := t.StatusBadge(m.Status)

	maxTotal, _ := strconv.ParseFloat(m.MaxTotal, 64)
	spent, _ := strconv.ParseFloat(m.Spent, 64)
	ratio := 0.0
	if maxTotal > 0 {
		ratio = spent / maxTotal
	}

	budgetStr := t.TextSecondary.Render(fmt.Sprintf("$%.0f/$%.0f", spent, maxTotal))
	gaugeColor := t.ColorGreen
	if ratio > 0.8 {
		gaugeColor = t.ColorRed
	} else if ratio > 0.5 {
		gaugeColor = t.ColorAmber
	}
	gauge := components.GaugeWithLabel(ratio, 16, gaugeColor)

	sel := "  "
	if isSelected {
		sel = lipgloss.NewStyle().Foreground(t.ColorAmber).Render("▸ ")
	}

	line := sel + prefix + name + " " + status + "  " + budgetStr + "  " + gauge

	var lines []string
	lines = append(lines, line)

	childIdxs := children[m.MandateID]
	for ci, childIdx := range childIdxs {
		isLastChild := ci == len(childIdxs)-1
		lines = append(lines, renderMandateNode(ms, childIdx, depth+1, isLastChild, children, width)...)
	}

	return lines
}

func renderMandateDetail(m api.Mandate, width int) string {
	title := t.TextCyan.Bold(true).Render(m.AgentID)

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")

	maxTotal, _ := strconv.ParseFloat(m.MaxTotal, 64)
	spent, _ := strconv.ParseFloat(m.Spent, 64)
	remaining, _ := strconv.ParseFloat(m.Remaining, 64)

	fields := []struct {
		Label string
		Value string
	}{
		{"Mandate ID", m.MandateID},
		{"Principal", m.PrincipalID},
		{"Budget", fmt.Sprintf("$%.2f / $%.2f ($%.2f remaining)", spent, maxTotal, remaining)},
		{"Per-TX Limit", "$" + m.MaxPerTx},
		{"Depth", fmt.Sprintf("%d / %d", m.DelegationDepth, m.MaxDelegationDepth)},
		{"Chains", joinOrNone(m.AllowedChains)},
		{"Currencies", joinOrNone(m.AllowedCurrencies)},
		{"Services", joinOrNone(m.AllowedServices)},
		{"Merchants", joinOrNone(m.AllowedMerchants)},
		{"Blocked", joinOrNone(m.BlockedMerchants)},
		{"Status", m.Status},
	}

	if m.FrozenReason != "" {
		fields = append(fields, struct {
			Label string
			Value string
		}{"Freeze Reason", m.FrozenReason})
	}

	for _, f := range fields {
		label := lipgloss.NewStyle().Width(16).Foreground(t.ColorText50).Render(f.Label)
		value := t.TextPrimary.Render(f.Value)
		lines = append(lines, "  "+label+value)
	}

	lines = append(lines, "")
	lines = append(lines, "  "+t.TextMuted.Render("[F] Freeze   [D] Delegate   [R] Resume   [Esc] Back"))

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorderHi).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func joinOrNone(items []string) string {
	if len(items) == 0 {
		return "(any)"
	}
	return strings.Join(items, ", ")
}
