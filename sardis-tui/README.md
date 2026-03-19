# sardis-tui

Terminal UI for **Sardis Guard** — the financial intelligence plane for AI agent payments.

```
╭─ SARDIS GUARD ── Overview  Feed  Policy  Mandates  Screening  Audit ── ● CONNECTED ─╮
│                                                                                       │
│  EVENTS     AGENTS     VOLUME      MERCHANTS    KILL SW                               │
│  6          3          $51.12      5            0 active                               │
│                                                                                       │
│  ╭─ Action Breakdown ─────────╮  ╭─ System Modules ──────────────────╮                │
│  │  ALLOW   ████████░░  67%   │  │  risk_engine        ● active      │                │
│  │  FREEZE  ██░░░░░░░░  17%   │  │  sanctions_screener ● active      │                │
│  │  DENY    ██░░░░░░░░  17%   │  │  governance_engine  ● active      │                │
│  ╰────────────────────────────╯  ╰───────────────────────────────────╯                │
╰───────────────────────────────────────────────────────────────────────────────────────╯
```

## Install

**Homebrew** (macOS/Linux):
```bash
brew tap efebarandurmaz/tap
brew install sardis-tui
```

**Go install**:
```bash
go install github.com/efebarandurmaz/sardis-mpp-hackathon/sardis-tui@latest
```

**Binary download**: See [Releases](https://github.com/efebarandurmaz/sardis-mpp-hackathon/releases).

## Usage

```bash
# Connect to production API (default)
sardis-tui

# Connect to local dev server
SARDIS_API_URL=http://localhost:8402 sardis-tui
```

## Tabs

| Key | Tab | Description |
|-----|-----|-------------|
| `1` | **Overview** | Dashboard stats, action breakdown, system modules, recent events |
| `2` | **Feed** | Live SSE event stream with real-time evaluations |
| `3` | **Policy** | Simulate payment evaluations against the 12-check policy engine |
| `4` | **Mandates** | Mandate delegation tree with freeze/resume actions |
| `5` | **Screening** | OFAC SDN sanctions screening (entity + address) |
| `6` | **Audit** | Audit trail with filtering, event detail, evidence packs |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`-`6` | Switch tabs |
| `q` / `Ctrl+C` | Quit |
| `?` | Help overlay |
| `r` | Refresh data |
| `j`/`k` / arrows | Navigate |
| `Enter` | Select / expand |
| `Esc` | Back / close |
| `/` | Filter (audit tab) |

## API

Connects to the Sardis Guard Intelligence Plane API. All dashboard data comes from free endpoints — no MPP payment required for the TUI.

| Endpoint | What TUI Uses It For |
|----------|---------------------|
| `GET /health` | Connection status |
| `GET /` | Service info + module status |
| `GET /dashboard/summary` | Stats row |
| `GET /kill-switch/status` | Kill switch indicator |
| `GET /stream` | Live event feed (SSE) |
| `GET /mandates` | Mandate tree |
| `POST /screen/entity` | OFAC entity screening |
| `POST /screen/address` | OFAC address screening |

## Theme

Monochrome with strategic accent colors:

- **Amber** `#f59e0b` — active tab, key values, warnings
- **Red** `#ef4444` — DENY/FREEZE, errors, kill switch
- **Green** `#22c55e` — ALLOW, connected, success
- **Cyan** `#06b6d4` — agent IDs, references

## Build from Source

```bash
cd sardis-tui
go build -o sardis-tui .
./sardis-tui
```
