package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	t "sardis-tui/internal/theme"
)

// Gauge renders a horizontal progress bar
func Gauge(ratio float64, width int, fg lipgloss.Color) string {
	if ratio < 0 {
		ratio = 0
	}
	if ratio > 1 {
		ratio = 1
	}
	filled := int(ratio * float64(width))
	if filled > width {
		filled = width
	}
	empty := width - filled

	bar := lipgloss.NewStyle().Foreground(fg).Render(strings.Repeat("█", filled))
	bar += lipgloss.NewStyle().Foreground(t.ColorSurface3).Render(strings.Repeat("░", empty))
	return bar
}

// GaugeWithLabel renders a progress bar with a percentage label
func GaugeWithLabel(ratio float64, width int, fg lipgloss.Color) string {
	barWidth := width - 5
	if barWidth < 4 {
		barWidth = 4
	}
	pct := fmt.Sprintf("%3d%%", int(ratio*100))
	return Gauge(ratio, barWidth, fg) + " " + lipgloss.NewStyle().Foreground(t.ColorText50).Render(pct)
}

// Sparkline renders a tiny inline sparkline from values
func Sparkline(values []float64, width int) string {
	if len(values) == 0 {
		return strings.Repeat("·", width)
	}

	blocks := []rune{'▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'}

	min, max := values[0], values[0]
	for _, v := range values {
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}

	rng := max - min
	if rng == 0 {
		rng = 1
	}

	start := 0
	if len(values) > width {
		start = len(values) - width
	}
	vals := values[start:]

	var result strings.Builder
	for _, v := range vals {
		idx := int((v - min) / rng * float64(len(blocks)-1))
		if idx >= len(blocks) {
			idx = len(blocks) - 1
		}
		result.WriteRune(blocks[idx])
	}

	for i := len(vals); i < width; i++ {
		result.WriteRune('·')
	}

	return lipgloss.NewStyle().Foreground(t.ColorAmber).Render(result.String())
}

// TreePrefix generates box-drawing characters for tree rendering
func TreePrefix(isLast bool, depth int) string {
	if depth == 0 {
		return "◆ "
	}
	prefix := ""
	for i := 0; i < depth-1; i++ {
		prefix += "│   "
	}
	if isLast {
		prefix += "└── ◇ "
	} else {
		prefix += "├── ◇ "
	}
	return lipgloss.NewStyle().Foreground(t.ColorText30).Render(prefix)
}

// StatBox renders a small stat with label and value
func StatBox(label, value string) string {
	l := lipgloss.NewStyle().Foreground(t.ColorText50).Render(label)
	v := lipgloss.NewStyle().Foreground(t.ColorText).Bold(true).Render(value)
	return l + "\n" + v
}
