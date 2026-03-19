package theme

import "github.com/charmbracelet/lipgloss"

// 5-step monochrome surface scale
var (
	ColorBg       = lipgloss.Color("#09090b")
	ColorSurface1 = lipgloss.Color("#111113")
	ColorSurface2 = lipgloss.Color("#1a1a1f")
	ColorSurface3 = lipgloss.Color("#252530")
	ColorSurface4 = lipgloss.Color("#30303d")
)

// Borders
var (
	ColorBorder   = lipgloss.Color("#1f1f28")
	ColorBorderHi = lipgloss.Color("#2a2a38")
)

// Text hierarchy
var (
	ColorText   = lipgloss.Color("#e4e4e7")
	ColorText70 = lipgloss.Color("#a1a1aa")
	ColorText50 = lipgloss.Color("#71717a")
	ColorText30 = lipgloss.Color("#3f3f46")
)

// Accent: Amber — active tab, key values, warnings
var (
	ColorAmber      = lipgloss.Color("#f59e0b")
	ColorAmberMuted = lipgloss.Color("#92400e")
)

// Accent: Red — deny/freeze, errors, kill switch
var (
	ColorRed      = lipgloss.Color("#ef4444")
	ColorRedMuted = lipgloss.Color("#7f1d1d")
)

// Accent: Green — allow, connected, success
var (
	ColorGreen      = lipgloss.Color("#22c55e")
	ColorGreenMuted = lipgloss.Color("#14532d")
)

// Accent: Cyan — agent IDs, links, info
var ColorCyan = lipgloss.Color("#06b6d4")

// Base styles
var (
	TextPrimary   = lipgloss.NewStyle().Foreground(ColorText)
	TextSecondary = lipgloss.NewStyle().Foreground(ColorText70)
	TextMuted     = lipgloss.NewStyle().Foreground(ColorText50)
	TextDisabled  = lipgloss.NewStyle().Foreground(ColorText30)
	TextBold      = lipgloss.NewStyle().Foreground(ColorText).Bold(true)
	TextAmber     = lipgloss.NewStyle().Foreground(ColorAmber).Bold(true)
	TextCyan      = lipgloss.NewStyle().Foreground(ColorCyan)
	TextGreen     = lipgloss.NewStyle().Foreground(ColorGreen)
	TextRed       = lipgloss.NewStyle().Foreground(ColorRed)
)

// Panel style
var PanelStyle = lipgloss.NewStyle().
	Border(lipgloss.RoundedBorder()).
	BorderForeground(ColorBorder).
	Padding(1, 2)

// Tab styles
var (
	ActiveTabStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorAmber).
			Padding(0, 2)

	InactiveTabStyle = lipgloss.NewStyle().
				Foreground(ColorText50).
				Padding(0, 2)
)

// Badge styles
var (
	BadgeAllow = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorGreen).
			Background(ColorGreenMuted).
			Padding(0, 1)

	BadgeDeny = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorRed).
			Background(ColorRedMuted).
			Padding(0, 1)

	BadgeFlag = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorAmber).
			Background(ColorAmberMuted).
			Padding(0, 1)

	BadgeFrozen = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorRed).
			Background(ColorRedMuted).
			Padding(0, 1)

	BadgeHold = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorAmber).
			Background(ColorAmberMuted).
			Padding(0, 1)

	BadgeActive = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorGreen)

	BadgeExhausted = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorText50)
)

// ActionBadge returns a styled badge for an action string
func ActionBadge(action string) string {
	switch action {
	case "ALLOW":
		return BadgeAllow.Render(" ALLOW ")
	case "DENY":
		return BadgeDeny.Render(" DENY ")
	case "FLAG":
		return BadgeFlag.Render(" FLAG ")
	case "HOLD":
		return BadgeHold.Render(" HOLD ")
	case "FREEZE_CHILD":
		return BadgeFrozen.Render(" FREEZE ")
	case "FREEZE_TREE":
		return BadgeFrozen.Render(" FREEZE_TREE ")
	default:
		return TextMuted.Render(action)
	}
}

// StatusBadge returns a styled badge for mandate status
func StatusBadge(status string) string {
	switch status {
	case "active":
		return BadgeActive.Render("ACTIVE")
	case "frozen":
		return BadgeFrozen.Render("FROZEN")
	case "expired":
		return TextMuted.Render("EXPIRED")
	case "exhausted":
		return BadgeExhausted.Render("EXHAUSTED")
	default:
		return TextMuted.Render(status)
	}
}

// ModuleDot returns a colored dot for module status
func ModuleDot(active bool) string {
	if active {
		return TextGreen.Render("●")
	}
	return TextRed.Render("●")
}
