package views

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"sardis-tui/internal/api"
	t "sardis-tui/internal/theme"
)

// PolicyState tracks the policy simulator form state
type PolicyState struct {
	Fields      []PolicyField
	ActiveField int
	Submitted   bool
	Result      *api.Verdict
	Error       string
}

type PolicyField struct {
	Label       string
	Value       string
	Placeholder string
	Options     []string // if non-empty, this is a select field
	OptionIdx   int
}

// NewPolicyState creates a fresh policy form
func NewPolicyState() *PolicyState {
	return &PolicyState{
		Fields: []PolicyField{
			{Label: "Amount", Value: "", Placeholder: "1.50"},
			{Label: "Merchant", Value: "", Placeholder: "perplexity.ai"},
			{Label: "Currency", Value: "USDC", Options: []string{"USDC", "pathUSD", "EURC", "USDT"}},
			{Label: "Network", Value: "tempo", Options: []string{"tempo", "base", "ethereum", "polygon", "arbitrum", "optimism"}},
			{Label: "Category", Value: "", Placeholder: "research"},
			{Label: "Memo", Value: "", Placeholder: "(optional)"},
		},
	}
}

// HandleKey handles keyboard input for the policy form
func (ps *PolicyState) HandleKey(key string) {
	if ps.Submitted {
		if key == "esc" || key == "enter" {
			ps.Submitted = false
			ps.Result = nil
			ps.Error = ""
		}
		return
	}

	field := &ps.Fields[ps.ActiveField]

	switch key {
	case "tab", "down":
		ps.ActiveField = (ps.ActiveField + 1) % len(ps.Fields)
	case "shift+tab", "up":
		ps.ActiveField = (ps.ActiveField - 1 + len(ps.Fields)) % len(ps.Fields)
	case "left":
		if len(field.Options) > 0 {
			field.OptionIdx = (field.OptionIdx - 1 + len(field.Options)) % len(field.Options)
			field.Value = field.Options[field.OptionIdx]
		}
	case "right":
		if len(field.Options) > 0 {
			field.OptionIdx = (field.OptionIdx + 1) % len(field.Options)
			field.Value = field.Options[field.OptionIdx]
		}
	case "backspace":
		if len(field.Options) == 0 && len(field.Value) > 0 {
			field.Value = field.Value[:len(field.Value)-1]
		}
	case "enter":
		if ps.ActiveField == len(ps.Fields)-1 {
			ps.Submitted = true
		} else {
			ps.ActiveField = (ps.ActiveField + 1) % len(ps.Fields)
		}
	default:
		if len(field.Options) == 0 && len(key) == 1 {
			field.Value += key
		}
	}
}

// GetValues returns the form values as a map
func (ps *PolicyState) GetValues() map[string]string {
	vals := make(map[string]string)
	for _, f := range ps.Fields {
		v := f.Value
		if v == "" {
			v = f.Placeholder
		}
		vals[f.Label] = v
	}
	return vals
}

// RenderPolicy renders the policy simulator tab
func RenderPolicy(ps *PolicyState, width, height int) string {
	if ps.Submitted && ps.Result != nil {
		return renderPolicyResult(ps, width, height)
	}
	if ps.Submitted && ps.Error != "" {
		return renderPolicyError(ps, width)
	}

	return renderPolicyForm(ps, width, height)
}

func renderPolicyForm(ps *PolicyState, width, height int) string {
	title := t.TextSecondary.Render("Policy Simulator")
	subtitle := t.TextMuted.Render("Simulate a payment evaluation against the 12-check policy engine")

	var lines []string
	lines = append(lines, title)
	lines = append(lines, subtitle)
	lines = append(lines, "")

	fieldWidth := width - 12
	if fieldWidth > 60 {
		fieldWidth = 60
	}

	for i, field := range ps.Fields {
		isActive := i == ps.ActiveField

		label := lipgloss.NewStyle().Width(12).Foreground(t.ColorText70).Render(field.Label)
		if isActive {
			label = lipgloss.NewStyle().Width(12).Foreground(t.ColorAmber).Bold(true).Render(field.Label)
		}

		var value string
		if len(field.Options) > 0 {
			var opts []string
			for j, opt := range field.Options {
				if j == field.OptionIdx {
					opts = append(opts, lipgloss.NewStyle().Foreground(t.ColorAmber).Bold(true).Render("["+opt+"]"))
				} else {
					opts = append(opts, lipgloss.NewStyle().Foreground(t.ColorText30).Render(" "+opt+" "))
				}
			}
			value = strings.Join(opts, " ")
		} else {
			displayVal := field.Value
			if displayVal == "" {
				displayVal = lipgloss.NewStyle().Foreground(t.ColorText30).Render(field.Placeholder)
			} else {
				displayVal = lipgloss.NewStyle().Foreground(t.ColorText).Render(displayVal)
			}
			if isActive {
				displayVal += lipgloss.NewStyle().Foreground(t.ColorAmber).Render("▎")
			}

			inputStyle := lipgloss.NewStyle().
				Width(fieldWidth).
				Padding(0, 1)
			if isActive {
				inputStyle = inputStyle.
					Border(lipgloss.RoundedBorder(), false, false, true, false).
					BorderForeground(t.ColorAmber)
			}
			value = inputStyle.Render(displayVal)
		}

		lines = append(lines, "  "+label+value)
		lines = append(lines, "")
	}

	lines = append(lines, "")
	lines = append(lines, "  "+t.TextMuted.Render("Enter: submit   Tab: next field   Esc: cancel"))

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderPolicyResult(ps *PolicyState, width, height int) string {
	v := ps.Result
	vals := ps.GetValues()

	var verdictStr string
	if v.Allowed {
		verdictStr = t.BadgeAllow.Render(" ALLOWED ")
	} else {
		verdictStr = t.BadgeDeny.Render(" DENIED ")
	}

	title := t.TextSecondary.Render(fmt.Sprintf("Policy Evaluation: $%s -> %s", vals["Amount"], vals["Merchant"]))
	latency := t.TextMuted.Render(fmt.Sprintf("%.1fms", v.TotalLatency))

	var lines []string
	lines = append(lines, title)
	lines = append(lines, "")
	lines = append(lines, "  VERDICT: "+verdictStr+"    "+latency)
	lines = append(lines, "")

	hdrNum := lipgloss.NewStyle().Width(4).Foreground(t.ColorText30).Render("#")
	hdrCheck := lipgloss.NewStyle().Width(22).Foreground(t.ColorText30).Render("CHECK")
	hdrResult := lipgloss.NewStyle().Width(10).Foreground(t.ColorText30).Render("RESULT")
	hdrReason := lipgloss.NewStyle().Foreground(t.ColorText30).Render("REASON")
	lines = append(lines, "  "+hdrNum+hdrCheck+hdrResult+hdrReason)

	sep := lipgloss.NewStyle().Foreground(t.ColorText30).Render(
		"  " + strings.Repeat("─", 4) + strings.Repeat("─", 22) + strings.Repeat("─", 10) + strings.Repeat("─", 30))
	lines = append(lines, sep)

	for i, check := range v.Checks {
		num := lipgloss.NewStyle().Width(4).Foreground(t.ColorText30).Render(fmt.Sprintf("%2d", i+1))
		name := lipgloss.NewStyle().Width(22).Foreground(t.ColorText70).Render(check.Name)

		var result string
		if check.Result == "PASS" {
			result = lipgloss.NewStyle().Width(10).Foreground(t.ColorGreen).Render("PASS")
		} else {
			result = lipgloss.NewStyle().Width(10).Foreground(t.ColorRed).Bold(true).Render("FAIL")
		}

		reason := t.TextMuted.Render(check.Reason)
		lines = append(lines, "  "+num+name+result+reason)
	}

	lines = append(lines, "")
	lines = append(lines, "  "+t.TextMuted.Render("Press Esc or Enter to return to form"))

	content := strings.Join(lines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorBorder).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}

func renderPolicyError(ps *PolicyState, width int) string {
	title := t.TextRed.Render("Evaluation Error")
	msg := t.TextSecondary.Render(ps.Error)

	content := title + "\n\n  " + msg + "\n\n  " + t.TextMuted.Render("Press Esc to return")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(t.ColorRed).
		Padding(1, 2).
		Width(width - 2).
		Render(content)
}
