package ui

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// RenderStatusBar renders the bottom status bar
func RenderStatusBar(apiURL string, summary *api.DashboardSummary, eventCount int, width int) string {
	sep := lipgloss.NewStyle().Foreground(t.ColorText30).Render(" │ ")

	url := lipgloss.NewStyle().Foreground(t.ColorText50).Render(apiURL)

	events := lipgloss.NewStyle().Foreground(t.ColorText70).Render(fmt.Sprintf("%d events", eventCount))

	var agents, volume string
	if summary != nil {
		agents = lipgloss.NewStyle().Foreground(t.ColorText70).Render(fmt.Sprintf("%d agents", summary.ActiveAgents))
		volume = lipgloss.NewStyle().Foreground(t.ColorAmber).Bold(true).Render(fmt.Sprintf("$%.2f", summary.TotalVolume))
	} else {
		agents = lipgloss.NewStyle().Foreground(t.ColorText30).Render("-- agents")
		volume = lipgloss.NewStyle().Foreground(t.ColorText30).Render("$--")
	}

	help := lipgloss.NewStyle().Foreground(t.ColorText30).Render("? help")

	left := url + sep + events + sep + agents + sep + volume
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
