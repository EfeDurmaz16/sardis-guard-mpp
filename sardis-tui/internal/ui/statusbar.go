package ui

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// RenderStatusBar renders the bottom status bar
func RenderStatusBar(summary *api.DashboardSummary, eventCount int, width int) string {
	sep := lipgloss.NewStyle().Foreground(t.ColorText30).Render(" │ ")

	logo := lipgloss.NewStyle().Foreground(t.ColorText30).Render("sardis guard")

	events := lipgloss.NewStyle().Foreground(t.ColorText70).Render(fmt.Sprintf("%d events", eventCount))

	var agents, volume, merchants string
	if summary != nil {
		agents = lipgloss.NewStyle().Foreground(t.ColorText70).Render(fmt.Sprintf("%d agents", summary.ActiveAgents))
		volume = lipgloss.NewStyle().Foreground(t.ColorAmber).Bold(true).Render(fmt.Sprintf("$%.2f volume", summary.TotalVolume))
		merchants = lipgloss.NewStyle().Foreground(t.ColorText70).Render(fmt.Sprintf("%d merchants", summary.UniqueMerchants))
	} else {
		agents = lipgloss.NewStyle().Foreground(t.ColorText30).Render("-- agents")
		volume = lipgloss.NewStyle().Foreground(t.ColorText30).Render("$--")
		merchants = lipgloss.NewStyle().Foreground(t.ColorText30).Render("-- merchants")
	}

	help := lipgloss.NewStyle().Foreground(t.ColorText30).Render("? help")

	left := logo + sep + events + sep + agents + sep + merchants + sep + volume
	leftWidth := lipgloss.Width(left)
	helpWidth := lipgloss.Width(help)
	gap := width - leftWidth - helpWidth - 4
	if gap < 1 {
		gap = 1
	}

	content := left + lipgloss.NewStyle().Width(gap).Render("") + help

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(0, 1).
		Width(width - 2).
		Render(content)
}
