package ui

import (
	"github.com/charmbracelet/lipgloss"
	t "sardis-tui/internal/theme"
)

type helpEntry struct {
	Key  string
	Desc string
}

var tabHelp = map[int][]helpEntry{
	TabOverview: {
		{"r", "refresh"},
		{"1-6", "tabs"},
		{"?", "help"},
		{"q", "quit"},
	},
	TabFeed: {
		{"j/k", "scroll"},
		{"r", "refresh"},
		{"1-6", "tabs"},
		{"q", "quit"},
	},
	TabPolicy: {
		{"tab", "next field"},
		{"shift+tab", "prev"},
		{"←/→", "select option"},
		{"enter", "submit"},
		{"esc", "back"},
	},
	TabMandates: {
		{"j/k", "navigate"},
		{"enter", "detail"},
		{"n", "new root"},
		{"f", "freeze"},
		{"r", "resume"},
		{"esc", "back"},
	},
	TabScreening: {
		{"tab", "entity/address"},
		{"enter", "screen"},
		{"esc", "clear"},
	},
	TabAudit: {
		{"j/k", "navigate"},
		{"/", "filter"},
		{"enter", "detail"},
		{"e", "export"},
		{"esc", "back"},
	},
}

// RenderHelpBar renders a context-sensitive keyboard shortcut bar for the active tab
func RenderHelpBar(activeTab, width int) string {
	entries := tabHelp[activeTab]
	if entries == nil {
		return ""
	}

	sep := lipgloss.NewStyle().Foreground(t.ColorText30).Render(" │ ")

	keyStyle := lipgloss.NewStyle().Foreground(t.ColorAmber).Bold(true)
	descStyle := lipgloss.NewStyle().Foreground(t.ColorText50)

	var bar string
	for i, e := range entries {
		if i > 0 {
			bar += sep
		}
		bar += keyStyle.Render(e.Key) + " " + descStyle.Render(e.Desc)
	}

	return lipgloss.NewStyle().
		Padding(0, 1).
		Width(width - 2).
		Render(bar)
}
