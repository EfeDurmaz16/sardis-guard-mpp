package cmd

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"
	"sardis-tui/internal/ui"
)

var rootCmd = &cobra.Command{
	Use:   "sardis-tui",
	Short: "Sardis Guard Terminal UI",
	Long:  "Terminal interface for the Sardis Guard Intelligence Plane — policy firewall for AI agent payments",
	RunE: func(cmd *cobra.Command, args []string) error {
		app := ui.NewApp()
		p := tea.NewProgram(app, tea.WithAltScreen())
		_, err := p.Run()
		return err
	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
