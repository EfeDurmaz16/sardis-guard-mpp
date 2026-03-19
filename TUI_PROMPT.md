# Sardis Guard TUI — Complete Build Specification

## Context

Sardis Guard is an MPP (Machine Payments Protocol) policy firewall for AI agent payments. It runs a FastAPI server with a rich API surface. Build a **production-quality Terminal User Interface** that connects to the **REAL API** at the URLs below.

**CRITICAL RULES:**
- NO mocks. NO fake data. NO hardcoded demo content. Every pixel of data comes from real API calls.
- If an endpoint returns empty data, show a styled empty state with the endpoint URL.
- If an endpoint returns 402, show "MPP payment required" with the cost and a `tempo request` command the user can copy.

## API URLs

| Environment | URL |
|-------------|-----|
| Production | `https://guard.sardis.sh` |
| Local dev | `http://localhost:8402` |

Default to production. Override with `SARDIS_API_URL` env var.

```go
apiURL := os.Getenv("SARDIS_API_URL")
if apiURL == "" {
    apiURL = "https://guard.sardis.sh"
}
```

## Tech Stack

| Package | Version | Role |
|---------|---------|------|
| `github.com/charmbracelet/bubbletea` | latest | TUI framework (Elm architecture) |
| `github.com/charmbracelet/lipgloss` | v2+ | Terminal styling — colors, borders, layout |
| `github.com/charmbracelet/bubbles` | latest | Pre-built components: table, viewport, spinner, textinput, list, progress |
| `github.com/charmbracelet/huh` | latest | Form/input components for policy builder |
| `github.com/r3labs/sse/v2` | latest | SSE client for `/stream` |
| `github.com/spf13/cobra` | latest | CLI command structure |

## Directory Structure

```
sardis-tui/
├── main.go
├── go.mod
├── cmd/
│   └── root.go              # Cobra root, launches TUI
├── internal/
│   ├── api/
│   │   ├── client.go         # HTTP client for ALL endpoints
│   │   ├── sse.go            # SSE stream consumer with auto-reconnect
│   │   └── types.go          # Go structs matching API JSON responses
│   ├── ui/
│   │   ├── app.go            # Main Bubble Tea model, tab routing, layout
│   │   ├── theme.go          # Lip Gloss color tokens + shared styles
│   │   ├── header.go         # Persistent top bar (service name, tabs, status)
│   │   ├── statusbar.go      # Bottom status bar (API URL, event count, latency)
│   │   ├── views/
│   │   │   ├── overview.go   # Tab 1: Dashboard overview
│   │   │   ├── feed.go       # Tab 2: Live SSE event feed
│   │   │   ├── policy.go     # Tab 3: Policy simulator (Huh forms)
│   │   │   ├── mandates.go   # Tab 4: Mandate tree + CRUD
│   │   │   ├── screening.go  # Tab 5: OFAC/sanctions screening
│   │   │   └── audit.go      # Tab 6: Audit trail + evidence packs
│   │   └── components/
│   │       ├── badge.go       # Status badges (ALLOW, DENY, FROZEN, etc.)
│   │       ├── gauge.go       # Budget progress bars
│   │       ├── tree.go        # Tree renderer for mandates
│   │       └── sparkline.go   # Inline sparkline for risk scores
```

## Complete API Surface (Verified Against Real Server)

### FREE Endpoints (no payment required)

#### `GET /` — Service Info
```json
{
  "service": "Sardis Guard Intelligence Plane",
  "version": "0.2.0",
  "modules": {
    "risk_engine": true,
    "event_store": true,
    "sanctions_screener": true,
    "mandate_store": true,
    "governance_engine": true
  },
  "endpoints": { ... }
}
```

#### `GET /health` — Health Check
```json
{"status": "ok", "agents_tracked": 3, "mandates_active": 2}
```

#### `GET /stream` — SSE Event Stream
Events: `connected` (empty data), `evaluation` (full event payload).
SSE event data shape for `evaluation`:
```json
{
  "timestamp": 1710864000.123,
  "agent": "agent-id",
  "merchant": "perplexity.ai",
  "amount": "1.50",
  "currency": "USDC",
  "network": "tempo",
  "category": "research",
  "verdict": {
    "allowed": true,
    "summary": "ALLOWED — 12 checks passed in 0ms",
    "total_latency_ms": 0.3,
    "checks": [
      {"name": "mandate_active", "result": "PASS", "reason": "Mandate is active", "latency_ms": 0.0},
      {"name": "per_tx_limit", "result": "PASS", "reason": "$1.50 <= $5.00 limit", "latency_ms": 0.0},
      {"name": "daily_limit", "result": "PASS", "reason": "$1.50 <= $50.00 daily limit", "latency_ms": 0.0},
      {"name": "merchant_allowlist", "result": "PASS", "reason": "Merchant allowed", "latency_ms": 0.0},
      {"name": "merchant_blocklist", "result": "PASS", "reason": "Merchant not blocked", "latency_ms": 0.0},
      {"name": "category_allowlist", "result": "PASS", "reason": "Category allowed", "latency_ms": 0.0},
      {"name": "category_blocklist", "result": "PASS", "reason": "Category not blocked", "latency_ms": 0.0},
      {"name": "chain_allowlist", "result": "PASS", "reason": "Chain tempo allowed", "latency_ms": 0.0},
      {"name": "currency_allowlist", "result": "PASS", "reason": "Currency USDC allowed", "latency_ms": 0.0},
      {"name": "memo_requirement", "result": "PASS", "reason": "Memo provided or not required", "latency_ms": 0.0},
      {"name": "gas_price", "result": "PASS", "reason": "Gas price acceptable", "latency_ms": 0.0},
      {"name": "cooldown", "result": "PASS", "reason": "Cooldown satisfied", "latency_ms": 0.0}
    ]
  },
  "type": "evaluate"
}
```

V2 SSE events have additional fields:
```json
{
  "event_id": "uuid",
  "agent_id": "agent-name",
  "principal_id": "principal",
  "mandate_id": "mnd_xxxx",
  "amount": "1.50",
  "merchant": "perplexity.ai",
  "action": "ALLOW",
  "downstream_allowed": true,
  "risk_assessment": {
    "ml_score": 0.12,
    "sequence_score": 0.05,
    "correlation_score": 0.08,
    "sanctions_score": 0.0,
    "final_score": 0.09,
    "action": "ALLOW",
    "reasons": []
  },
  "governance_result": {"allowed": true, "checks": []},
  "aml_result": {"hit": false, "match_type": "none"},
  "entry_hash": "sha256hex...",
  "prev_hash": "sha256hex..."
}
```

#### `GET /dashboard/summary` — Aggregate Stats
```json
{
  "total_events": 5,
  "active_agents": 2,
  "total_volume": 9.5,
  "unique_merchants": 1,
  "denied_count": 0,
  "flagged_count": 0,
  "held_count": 0,
  "frozen_count": 1,
  "mandates_active": 0,
  "mandates_frozen": 0,
  "mandates_total": 0
}
```

#### `GET /dashboard/graph` — Service Transition Graph
```json
{
  "graph": {
    "edges": [{"from": "perplexity", "to": "perplexity", "weight": 2}]
  }
}
```

#### `GET /agents/{agent_id}/risk` — Agent Risk Timeline
```json
{
  "agent_id": "agent-x",
  "summary": {},
  "risk_timeline": []
}
```

#### `GET /mandates` — List All Mandates
```json
{
  "mandates": [
    {
      "mandate_id": "mnd_abc123",
      "parent_id": null,
      "principal_id": "admin",
      "agent_id": "research-bot",
      "max_total": "100",
      "max_per_tx": "10",
      "spent": "42.30",
      "remaining": "57.70",
      "allowed_services": ["exa", "stableenrich"],
      "allowed_merchants": ["stableenrich.dev"],
      "blocked_merchants": [],
      "allowed_chains": ["tempo"],
      "allowed_currencies": ["USDC", "pathUSD"],
      "status": "active",
      "approval_threshold": "0",
      "delegation_depth": 0,
      "max_delegation_depth": 3,
      "created_at": 1710860000.0,
      "expires_at": 0,
      "frozen_at": 0,
      "frozen_reason": "",
      "is_active": true
    }
  ]
}
```

#### `GET /mandates/{mandate_id}` — Mandate Detail + Children
```json
{
  "mandate": { "...same shape as above..." },
  "children": [ "...array of mandate objects..." ],
  "tree_size": 3
}
```

#### `POST /mandates/root` — Create Root Mandate
Request:
```json
{
  "principal_id": "admin",
  "agent_id": "research-bot",
  "max_total": "100",
  "max_per_tx": "10",
  "allowed_services": [],
  "allowed_merchants": [],
  "blocked_merchants": [],
  "allowed_chains": ["tempo"],
  "allowed_currencies": ["USDC", "pathUSD"],
  "approval_threshold": "0",
  "expires_in_seconds": 0
}
```

#### `POST /mandates/delegate` — Delegate Child Mandate
Request:
```json
{
  "parent_mandate_id": "mnd_abc123",
  "agent_id": "sub-agent",
  "max_total": "25",
  "max_per_tx": "5",
  "allowed_services": [],
  "allowed_merchants": [],
  "blocked_merchants": [],
  "allowed_chains": ["tempo"],
  "allowed_currencies": ["USDC", "pathUSD"],
  "expires_in_seconds": 0
}
```

#### `POST /mandates/freeze` — Freeze Mandate
```json
{"mandate_id": "mnd_abc123", "reason": "Suspicious activity", "freeze_children": true}
```

#### `POST /mandates/resume` — Resume Mandate
```json
{"mandate_id": "mnd_abc123"}
```

#### `POST /screen/entity` — OFAC Entity Screening
Request: `{"name": "Tornado Cash"}`
Response:
```json
{
  "entity": "Tornado Cash",
  "hit": true,
  "match_type": "exact",
  "matched_entry": "Tornado Cash",
  "list_source": "ofac_sdn",
  "confidence": 1.0
}
```

#### `POST /screen/address` — OFAC Address Screening
Request: `{"address": "0x..."}`
Response: Same shape as entity screening.

#### `GET /kill-switch/status` — Kill Switch Status
```json
{
  "active_count": 0,
  "switches": [
    {
      "scope": "global",
      "target": "",
      "reason": "Emergency halt",
      "activated_at": 1710860000.0,
      "auto_lift_at": null,
      "activated_by": "operator"
    }
  ]
}
```

#### `POST /kill-switch/activate` — Activate Kill Switch
```json
{"scope": "global", "target": "", "reason": "Emergency halt", "auto_lift_seconds": 300}
```

#### `POST /kill-switch/deactivate` — Deactivate Kill Switch
```json
{"scope": "global", "target": ""}
```

#### `GET /reports/session/{session_id}` — Evidence Pack
```json
{
  "session_id": "ses_abc123",
  "generated_at": 1710864000.0,
  "event_count": 42,
  "chain_valid": true,
  "first_hash": "abc...",
  "last_hash": "xyz...",
  "events": [],
  "mandate_chain": [],
  "risk_assessments": [],
  "sanctions_results": [],
  "freeze_actions": [],
  "operator_actions": []
}
```

### MPP-GATED Endpoints (return 402 without payment)

| Endpoint | Method | Cost | Description |
|----------|--------|------|-------------|
| `/evaluate` | POST | $0.001 | 12-check policy evaluation |
| `/evaluate/v2` | POST | $0.001 | Full intelligence pipeline |
| `/simulate` | POST | $0.0005 | Dry-run policy evaluation |
| `/mandate` | GET | $0.0001 | View legacy mandate |
| `/stats` | GET | $0.0001 | Agent spending stats |
| `/audit` | GET | $0.001 | Full audit trail |

When hitting these, the TUI should show:
```
┌─ PAYMENT REQUIRED ─────────────────────────────────┐
│                                                     │
│  This endpoint requires MPP payment: $0.001         │
│                                                     │
│  Run this command to access:                        │
│  tempo request -t -X POST \                         │
│    --json '{"amount":"1.50","merchant":"test.com"}' \│
│    https://guard.sardis.sh/evaluate                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Color Theme — Premium Monochrome + Warm Accents

Design principles from Linear, Vercel, Stripe research:
- Near-black backgrounds (never pure #000)
- 5-step gray scale for surface elevation
- Off-white text (never pure #fff)
- Low-contrast borders (rgba(255,255,255,0.08) equivalent)
- Amber/red accents ONLY on active states, important values, danger indicators
- Everything else is strictly grayscale
- Text hierarchy through weight and opacity, not color

```go
// theme.go

// 5-step monochrome surface scale
ColorBg         = lipgloss.Color("#09090b")   // base background
ColorSurface1   = lipgloss.Color("#111113")   // raised (cards)
ColorSurface2   = lipgloss.Color("#1a1a1f")   // elevated (selected)
ColorSurface3   = lipgloss.Color("#252530")   // hover/active
ColorSurface4   = lipgloss.Color("#30303d")   // highlighted

// Borders — must be subtle (10-15% lighter than bg)
ColorBorder     = lipgloss.Color("#1f1f28")   // default border
ColorBorderHi   = lipgloss.Color("#2a2a38")   // hover border

// Text hierarchy — opacity simulated via gray shades
ColorText       = lipgloss.Color("#e4e4e7")   // primary (100%)
ColorText70     = lipgloss.Color("#a1a1aa")   // secondary (70%)
ColorText50     = lipgloss.Color("#71717a")   // tertiary (50%)
ColorText30     = lipgloss.Color("#3f3f46")   // disabled (30%)

// Accent: Amber — used ONLY for: active tab, key values, warnings
ColorAmber      = lipgloss.Color("#f59e0b")
ColorAmberMuted = lipgloss.Color("#92400e")   // amber bg tint

// Accent: Red — used ONLY for: deny/freeze, errors, kill switch
ColorRed        = lipgloss.Color("#ef4444")
ColorRedMuted   = lipgloss.Color("#7f1d1d")

// Accent: Green — used ONLY for: allow, connected, success
ColorGreen      = lipgloss.Color("#22c55e")
ColorGreenMuted = lipgloss.Color("#14532d")

// Accent: Cyan — used ONLY for: agent IDs, links, info
ColorCyan       = lipgloss.Color("#06b6d4")

// Common styles
PanelStyle = lipgloss.NewStyle().
    Border(lipgloss.RoundedBorder()).
    BorderForeground(ColorBorder).
    Background(ColorSurface1).
    Padding(1, 2)

ActiveTabStyle = lipgloss.NewStyle().
    Bold(true).
    Foreground(ColorAmber).
    Border(lipgloss.ThickBorder(), false, false, true, false).
    BorderForeground(ColorAmber).
    Padding(0, 2)

InactiveTabStyle = lipgloss.NewStyle().
    Foreground(ColorText50).
    Padding(0, 2)

BadgeAllow  = lipgloss.NewStyle().Bold(true).Foreground(ColorGreen).Background(ColorGreenMuted).Padding(0, 1)
BadgeDeny   = lipgloss.NewStyle().Bold(true).Foreground(ColorRed).Background(ColorRedMuted).Padding(0, 1)
BadgeFlag   = lipgloss.NewStyle().Bold(true).Foreground(ColorAmber).Background(ColorAmberMuted).Padding(0, 1)
BadgeFrozen = lipgloss.NewStyle().Bold(true).Foreground(ColorRed).Background(ColorRedMuted).Padding(0, 1)
```

## Views (6 Tabs)

### Tab 1: Overview (default)
Data sources: `GET /health`, `GET /dashboard/summary`, `GET /kill-switch/status`, SSE `/stream` (last 5)

```
╭─ SARDIS GUARD INTELLIGENCE PLANE ────────────────── guard.sardis.sh ─╮
│  Overview   Feed   Policy   Mandates   Screening   Audit            │
╰──────────────────────────────────────────────────────── ● CONNECTED ─╯

  EVENTS          AGENTS          VOLUME          MERCHANTS       KILL SW
  5               2               $9.50           1               0 active

╭─ Action Breakdown ────────╮  ╭─ System Modules ─────────────────────╮
│                           │  │                                      │
│  ALLOW   ████████░░  80%  │  │  risk_engine        ● active         │
│  FLAG    ░░░░░░░░░░   0%  │  │  event_store        ● active         │
│  HOLD    ░░░░░░░░░░   0%  │  │  sanctions_screener ● active         │
│  FREEZE  ██░░░░░░░░  20%  │  │  mandate_store      ● active         │
│  DENY    ░░░░░░░░░░   0%  │  │  governance_engine  ● active         │
│                           │  │                                      │
╰───────────────────────────╯  ╰──────────────────────────────────────╯

╭─ Recent Activity ────────────────────────────────────────────────────╮
│  14:23:01  agent-x     perplexity.ai   $1.50 USDC   ALLOW   0.3ms  │
│  14:22:58  agent-y     alchemy.com     $0.50 USDC   ALLOW   0.2ms  │
│  14:22:45  agent-x     perplexity.ai   $2.00 USDC   ALLOW   0.1ms  │
│  ...                                                                │
╰──────────────────────────────────────────────────────────────────────╯
```

### Tab 2: Live Feed
Data source: SSE `/stream` (real-time, accumulating)

Full-height scrollable viewport. Each event row:
```
  14:23:01  agent-x     perplexity.ai   $1.50 USDC  tempo   ALLOW   12/12 passed  0.3ms
```

For denied events, show failed checks on a second line:
```
  14:23:01  agent-y     gambling.com    $100  USDC  darknet  DENY   3/12 failed   0.1ms
            ↳ per_tx_limit, merchant_blocklist, chain_allowlist
```

For V2 events, show risk score:
```
  14:23:01  agent-x     perplexity.ai   $1.50 USDC  ALLOW   risk:0.09  ml:0.12  seq:0.05
```

- Auto-scroll to newest events
- Counter in header: "142 events"
- Color the verdict badge: green ALLOW, red DENY, amber FLAG, etc.

### Tab 3: Policy Simulator
Uses `huh` forms to build a request, then either:
1. Calls the free local 12-check engine (no payment needed) OR
2. Generates a `tempo request` command for `/simulate`

Form fields:
- Amount (textinput, required, placeholder: "1.50")
- Merchant (textinput, required, placeholder: "perplexity.ai")
- Currency (select: USDC, pathUSD, EURC, USDT)
- Network (select: tempo, base, ethereum, polygon, arbitrum, optimism)
- Category (textinput, default: "general")
- Memo (textinput, optional)
- Gas Price Gwei (textinput, optional)

After submission, show 12-check table:
```
╭─ Policy Evaluation: $1.50 → perplexity.ai ──────────────────────────╮
│                                                                      │
│  VERDICT: ALLOWED                                          0.3ms     │
│                                                                      │
│  #   CHECK              RESULT    REASON                             │
│  ─── ────────────────── ──────── ────────────────────────────────    │
│   1  mandate_active      PASS    Mandate is active                   │
│   2  per_tx_limit        PASS    $1.50 <= $5.00 limit               │
│   3  daily_limit         PASS    $1.50 <= $50.00 daily limit        │
│   4  merchant_allowlist  PASS    Merchant allowed                    │
│   5  merchant_blocklist  PASS    Merchant not blocked               │
│   6  category_allowlist  PASS    Category allowed                    │
│   7  category_blocklist  PASS    Category not blocked               │
│   8  chain_allowlist     PASS    Chain tempo allowed                 │
│   9  currency_allowlist  PASS    Currency USDC allowed              │
│  10  memo_requirement    PASS    Memo provided or not required      │
│  11  gas_price           PASS    Gas price acceptable               │
│  12  cooldown            PASS    Cooldown satisfied                  │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

### Tab 4: Mandates
Data source: `GET /mandates` (FREE)

Tree visualization with box-drawing:
```
╭─ Mandate Tree ────────────────────────────── 3 nodes · 1 frozen ─────╮
│                                                                      │
│  ◆ root-orchestrator          ACTIVE     $127/$500    ████░░░░ 26%   │
│  ├── ◇ research-agent         ACTIVE     $42/$100     ████░░░░ 42%   │
│  ├── ◇ trading-agent          ACTIVE     $85/$200     ████░░░░ 43%   │
│  │   └── ◇ sub-trader-alpha   FROZEN     $12/$50      ██░░░░░░ 24%   │
│  └── ◇ outreach-agent         EXHAUST    $50/$50      ████████ 100%  │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

When a node is selected (arrow keys + enter), show detail panel:
```
╭─ research-agent ─────────────────────────────────────────────────────╮
│  Mandate ID:     mnd_abc123                                          │
│  Principal:      admin                                               │
│  Budget:         $42.30 / $100.00 ($57.70 remaining)                │
│  Per-TX Limit:   $10.00                                              │
│  Depth:          1 / 3                                               │
│  Chains:         tempo, base                                         │
│  Currencies:     USDC, pathUSD                                       │
│  Merchants:      stableenrich.dev, exa.ai                           │
│  Blocked:        (none)                                              │
│  Status:         ACTIVE                                              │
│                                                                      │
│  [F] Freeze   [D] Delegate   [R] Resume   [Esc] Back                │
╰──────────────────────────────────────────────────────────────────────╯
```

Actions:
- **F** → `POST /mandates/freeze` (with confirmation)
- **D** → Opens Huh form to `POST /mandates/delegate`
- **R** → `POST /mandates/resume`
- **N** → Opens Huh form to `POST /mandates/root` (create new root)

### Tab 5: Screening
Data source: `POST /screen/entity`, `POST /screen/address` (both FREE)

Two input modes:
1. **Entity screen**: Text input for name → `POST /screen/entity`
2. **Address screen**: Text input for 0x address → `POST /screen/address`

Results:
```
╭─ Screening: "Tornado Cash" ──────────────────────────────────────────╮
│                                                                      │
│  RESULT:   HIT                                                       │
│  Type:     exact                                                     │
│  Match:    Tornado Cash                                              │
│  Source:   ofac_sdn                                                  │
│  Conf:     1.000                                                     │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯

╭─ Screening: "0xd90e2f925DA726b50C4Ed8D0Fb90Ad05..." ────────────────╮
│                                                                      │
│  RESULT:   CLEAR                                                     │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

### Tab 6: Audit Trail
Data sources: SSE events (accumulated) + `GET /reports/session/{id}` (FREE)

Table view of all events:
```
╭─ Audit Trail ──────────────────────── 42 events · chain valid ✓ ─────╮
│                                                                      │
│  TIME      AGENT        MERCHANT         AMOUNT   ACTION   RISK      │
│  ──────── ──────────── ──────────────── ──────── ──────── ───────    │
│  14:23:01  agent-x     perplexity.ai    $1.50    ALLOW    0.09      │
│  14:22:58  agent-y     alchemy.com      $0.50    ALLOW    0.12      │
│  14:22:45  agent-x     perplexity.ai    $2.00    FLAG     0.55      │
│  14:22:30  agent-z     gambling.xyz     $100     DENY     0.92      │
│                                                                      │
│  [E] Export evidence pack   [S] Sort by column   [/] Filter          │
╰──────────────────────────────────────────────────────────────────────╯
```

- **E** → Calls `GET /reports/session/current` and displays the evidence pack
- **/** → Filter by agent ID, merchant, action
- Arrow keys to scroll
- Enter to expand event details (show all 12 checks + risk breakdown)

## Navigation & Keybindings

| Key | Action |
|-----|--------|
| `1`-`6` or `Tab` | Switch between views |
| `q`, `Ctrl+C` | Quit |
| `?` | Help overlay |
| `r` | Refresh current view's data |
| `j`/`k` or arrows | Navigate lists |
| `Enter` | Select/expand item |
| `Esc` | Back/close detail panel |
| `/` | Search/filter (in feed + audit) |

## Header & Status Bar

**Header** (always visible, top):
```
 SARDIS GUARD   Overview  Feed  Policy  Mandates  Screening  Audit     ● CONNECTED
```
- Active tab: amber color + underline
- Connected: green dot + "CONNECTED" / red dot + "DISCONNECTED"

**Status Bar** (always visible, bottom):
```
 guard.sardis.sh   142 events   5 agents   $9.50 volume   0.3ms avg   Press ? for help
```

## Connection & Resilience

1. **Startup**: Hit `GET /health` first. If fails, show large "CONNECTING..." with retry.
2. **SSE**: Connect to `GET /stream`. On `connected` event, set status to CONNECTED. On error, set DISCONNECTED and retry every 3 seconds. Show reconnect attempt count.
3. **Polling**: Every 5 seconds, refresh `GET /health` and `GET /dashboard/summary` for stats.
4. **Graceful degradation**: If any endpoint fails, show the error in-place. Never crash.

## Quality Bar

- Consistent padding on all panels: 1 line vertical, 2 chars horizontal
- Rounded borders everywhere (`lipgloss.RoundedBorder()`)
- Amber accent ONLY on: active tab, important numeric values, warning states
- Red ONLY on: DENY/FREEZE badges, errors, kill switch active
- Green ONLY on: ALLOW badges, connected status, success states
- Cyan ONLY on: agent IDs, clickable references
- Everything else: strict grayscale hierarchy
- Numbers: always bold
- Labels: always dimmed (70% text)
- Timestamps: always muted (50% text)
- Terminal responsive: adapt to `tea.WindowSizeMsg`, min 80x24
- No Unicode symbols beyond box-drawing and ◆◇●. No emojis.

## Build & Run

```bash
cd ~/sardis-mpp-hackathon/sardis-tui
go mod init sardis-tui
go mod tidy
go run .

# With custom API URL
SARDIS_API_URL=http://localhost:8402 go run .
```

## Action Types Reference

The system uses these action levels (from `src/types.py`):
```
ALLOW       — Payment approved, proceed to downstream service
FLAG        — Payment approved but flagged for review (risk 0.45-0.70)
HOLD        — Payment paused, requires manual approval (risk 0.70-0.85)
FREEZE_CHILD — Freeze this mandate only (risk 0.85+)
FREEZE_TREE  — Freeze entire mandate tree (sanctions hit or critical risk)
DENY        — Payment rejected by policy checks
```

Risk score thresholds:
```
< 0.45  → ALLOW  (green)
< 0.70  → FLAG   (amber)
< 0.85  → HOLD   (amber, brighter)
< 1.00  → FREEZE (red)
```

## Trust Tiers (from Sardis Protocol)

```
UNTRUSTED:   $10/tx,     $25/day     — new/unknown agents
LOW:         $50/tx,    $100/day     — basic KYA
MEDIUM:     $500/tx,  $1,000/day    — verified KYA
HIGH:     $5,000/tx, $10,000/day    — attested KYA
SOVEREIGN: $50,000/tx (unlimited)   — full sovereign agent
```
