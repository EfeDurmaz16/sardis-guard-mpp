package views

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// ScreeningState tracks screening view state
type ScreeningState struct {
	Mode    int // 0 = entity, 1 = address
	Input   string
	Results []ScreeningResult
	Loading bool
	Error   string
}

type ScreeningResult struct {
	Query  string
	Type   string // "entity" or "address"
	Result *api.ScreenResult
}

func NewScreeningState() *ScreeningState {
	return &ScreeningState{}
}

// HandleKey handles keyboard input for screening view
func (ss *ScreeningState) HandleKey(key string) string {
	switch key {
	case "tab":
		ss.Mode = (ss.Mode + 1) % 2
		ss.Input = ""
	case "backspace":
		if len(ss.Input) > 0 {
			ss.Input = ss.Input[:len(ss.Input)-1]
		}
	case "enter":
		if ss.Input != "" {
			query := ss.Input
			ss.Input = ""
			if ss.Mode == 0 {
				return "screen_entity:" + query
			}
			return "screen_address:" + query
		}
	case "esc":
		ss.Input = ""
		ss.Error = ""
	default:
		if len(key) == 1 {
			ss.Input += key
		}
	}
	return ""
}

// RenderScreening renders the OFAC screening tab
func RenderScreening(ss *ScreeningState, width, height int) string {
	title := t.TextSecondary.Render("OFAC Sanctions Screening")
	subtitle := t.TextMuted.Render("Screen entities and wallet addresses against the OFAC SDN list")

	var sections []string
	sections = append(sections, title)
	sections = append(sections, subtitle)
	sections = append(sections, "")

	// Mode tabs
	var modeTabs string
	if ss.Mode == 0 {
		modeTabs = t.ActiveTabStyle.Render("Entity") + "  " + t.InactiveTabStyle.Render("Address")
	} else {
		modeTabs = t.InactiveTabStyle.Render("Entity") + "  " + t.ActiveTabStyle.Render("Address")
	}
	sections = append(sections, "  "+modeTabs)
	sections = append(sections, "")

	// Input field
	var placeholder string
	if ss.Mode == 0 {
		placeholder = "Enter entity name (e.g. Tornado Cash)"
	} else {
		placeholder = "Enter wallet address (0x...)"
	}

	inputVal := ss.Input
	if inputVal == "" {
		inputVal = lipgloss.NewStyle().Foreground(t.ColorText30).Render(placeholder)
	} else {
		inputVal = lipgloss.NewStyle().Foreground(t.ColorText).Render(inputVal)
	}
	inputVal += lipgloss.NewStyle().Foreground(t.ColorAmber).Render("▎")

	inputField := lipgloss.NewStyle().
		Width(width - 12).
		Border(lipgloss.RoundedBorder(), false, false, true, false).
		BorderForeground(t.ColorAmber).
		Padding(0, 1).
		Render(inputVal)

	sections = append(sections, "  "+inputField)
	sections = append(sections, "")

	// Error
	if ss.Error != "" {
		sections = append(sections, "  "+t.TextRed.Render(ss.Error))
		sections = append(sections, "")
	}

	// Results (most recent first)
	if len(ss.Results) > 0 {
		for i := len(ss.Results) - 1; i >= 0; i-- {
			r := ss.Results[i]
			sections = append(sections, renderScreeningResult(r, width-8))
			sections = append(sections, "")
		}
	}

	content := strings.Join(sections, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderScreeningResult(r ScreeningResult, width int) string {
	queryLabel := "Entity"
	if r.Type == "address" {
		queryLabel = "Address"
	}

	queryDisplay := r.Query
	if len(queryDisplay) > 50 {
		queryDisplay = queryDisplay[:20] + "..." + queryDisplay[len(queryDisplay)-10:]
	}

	header := t.TextSecondary.Render(fmt.Sprintf("Screening: %s \"%s\"", queryLabel, queryDisplay))

	if r.Result == nil {
		return header + "\n  " + t.TextRed.Render("Error fetching result")
	}

	var lines []string
	lines = append(lines, header)
	lines = append(lines, "")

	if r.Result.Hit {
		lines = append(lines, "  RESULT:   "+t.BadgeDeny.Render(" HIT "))
		lines = append(lines, "  Type:     "+t.TextPrimary.Render(r.Result.MatchType))
		if r.Result.MatchedEntry != "" {
			lines = append(lines, "  Match:    "+t.TextPrimary.Render(r.Result.MatchedEntry))
		}
		lines = append(lines, "  Source:   "+t.TextMuted.Render(r.Result.ListSource))
		lines = append(lines, "  Conf:     "+t.TextAmber.Render(fmt.Sprintf("%.3f", r.Result.Confidence)))
	} else {
		lines = append(lines, "  RESULT:   "+t.BadgeAllow.Render(" CLEAR "))
	}

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorderHi).
		Padding(1, 2).
		Width(width).
		Render(content)
}
