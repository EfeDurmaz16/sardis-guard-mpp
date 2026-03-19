package ui

import (
	"github.com/charmbracelet/lipgloss"
	t "sardis-tui/internal/theme"
)

var tabs = []string{"Overview", "Feed", "Policy", "Mandates", "Screening", "Audit"}

// RenderHeader renders the top bar with tabs and connection status
func RenderHeader(activeTab int, connected bool, width int) string {
	// Logo
	logo := lipgloss.NewStyle().
		Bold(true).
		Foreground(t.ColorText).
		Render("SARDIS GUARD")

	// Tab bar
	var tabItems string
	for i, tab := range tabs {
		if i == activeTab {
			tabItems += t.ActiveTabStyle.Render(tab)
		} else {
			tabItems += t.InactiveTabStyle.Render(tab)
		}
	}

	// Connection indicator
	var connStatus string
	if connected {
		connStatus = lipgloss.NewStyle().Foreground(t.ColorGreen).Render("● ") +
			lipgloss.NewStyle().Foreground(t.ColorText50).Render("CONNECTED")
	} else {
		connStatus = lipgloss.NewStyle().Foreground(t.ColorRed).Render("● ") +
			lipgloss.NewStyle().Foreground(t.ColorText50).Render("DISCONNECTED")
	}

	// Layout: logo + tabs on left, connection status on right
	left := logo + "  " + tabItems
	leftWidth := lipgloss.Width(left)
	connWidth := lipgloss.Width(connStatus)

	gap := width - leftWidth - connWidth - 2
	if gap < 1 {
		gap = 1
	}

	headerContent := left + lipgloss.NewStyle().Width(gap).Render("") + connStatus

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(0, 1).
		Width(width - 2).
		Render(headerContent)
}
