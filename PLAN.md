# Sardis Guard — Intelligence Plane | Hackathon Plan

**Event:** Tempo MPP Hackathon, March 19 2026, 9:30 AM - 6:30 PM PT (started ~12:00 PT for us)
**Project:** Sardis Guard — pay-per-evaluation policy firewall for AI agent payments
**Team:** Efe Baran Durmaz (solo, Claude Code parallel agents)
**Wallet:** `0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c` (1 USDC, mainnet Tempo chain 4217)

---

## Vision

**"Before any AI agent spends money through MPP, it passes through Sardis Guard — a 12-check policy firewall that charges $0.001 per evaluation and earns revenue on every agent payment in the ecosystem."**

Every MPP service charges agents for access. But **no one controls what the agent is allowed to spend.** Sardis Guard is the policy middleware — we make money every time an agent's money moves.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Claude, GPT)                │
│                                                          │
│  "Research competitors, buy data, pay for API calls"     │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    Sardis Guard (MPP)        │  $0.001/eval
        │                              │
        │  12-check policy pipeline:   │
        │  ┌─ mandate_active          │
        │  ├─ per_tx_limit            │
        │  ├─ daily_limit             │
        │  ├─ merchant_allow/block    │
        │  ├─ category_allow/block    │
        │  ├─ chain_allowlist         │
        │  ├─ currency_allowlist      │
        │  ├─ memo_requirement        │
        │  ├─ gas_price_check         │
        │  └─ cooldown_period         │
        │                              │
        │  → ALLOW or DENY            │
        └──────┬────────┬─────────────┘
               │        │
      ALLOWED  │        │  DENIED → stop
               ▼        │
  ┌────────────────────┐│  ┌────────────────────┐
  │ Perplexity ($0.05) ││  │ Alchemy ($0.001)   │
  │ AI search results  ││  │ Blockchain data    │
  └────────────────────┘│  └────────────────────┘
  ┌────────────────────┐│  ┌────────────────────┐
  │ StableEnrich       ││  │ Any MPP Service    │
  │ Company data       ││  │ Future services... │
  └────────────────────┘│  └────────────────────┘
```

---

## Current Status (Updated Live)

### ✅ COMPLETED
- [x] Tempo CLI installed (v1.4.3)
- [x] Wallet connected (1 USDC mainnet)
- [x] Policy engine (12 checks, `src/policy.py`)
- [x] FastAPI MPP server (`src/server.py`)
- [x] pympp[tempo,server] installed
- [x] Server running on port 8402
- [x] ngrok tunnel: `https://dendric-margie-answerlessly.ngrok-free.dev`
- [x] **2 real MPP payments processed** (ALLOW + DENY scenarios)
- [x] Per-agent state tracking (cumulative daily spend)

### 🔲 TODO
- [ ] Test with multiple MPP services (Perplexity, Alchemy, StableEnrich)
- [ ] Agent client that composes Guard + downstream services
- [ ] CLI tool for quick policy checks
- [ ] Real-time dashboard (React)
- [ ] Policy builder UI
- [ ] Service directory PR
- [ ] Demo video

---

## Saat-Saat Detaylı Plan

### Phase 1: DONE — MPP Server (12:00 - 13:30 PT / 22:00 - 23:30 TR)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Tempo CLI + wallet setup | ✅ | v1.4.3, 1 USDC |
| 1.2 | pympp SDK install | ✅ | pympp[tempo,server] 0.4.1 |
| 1.3 | Policy engine (12 checks) | ✅ | `src/policy.py` |
| 1.4 | FastAPI server w/ MPP paid endpoints | ✅ | `src/server.py` |
| 1.5 | ngrok public URL | ✅ | Working |
| 1.6 | Verify with `tempo request` | ✅ | 2 real payments |

### Phase 2: NOW — Consumer Side + Compose (13:30 - 16:00 PT / 23:30 - 02:00 TR)

| # | Task | Agent | Tech | Est |
|---|------|-------|------|-----|
| 2.1 | **Discover existing MPP services** | Main | `tempo wallet services --search` | 10 min |
| 2.2 | **Sardis Guard Client SDK** — Python wrapper that calls Guard → downstream service | Agent A | Python, pympp client | 30 min |
| 2.3 | **AI Agent Demo** — Claude agent that researches + buys data, Guard enforces limits | Agent B | Claude API + Guard client | 45 min |
| 2.4 | **Multi-service composition** — Agent calls Guard, then Perplexity OR Alchemy | Agent B | MPP chaining | 30 min |
| 2.5 | **CLI tool** — `sardis-guard check/evaluate/mandate` commands | Agent C | Typer | 20 min |
| 2.6 | **Simulate endpoint** — dry-run policy check (no state mutation) | Agent A | FastAPI | 10 min |
| 2.7 | **Audit trail endpoint** — get payment history | Agent A | FastAPI | 10 min |
| 2.8 | **Payment-Receipt header** — fix the missing header warning | Agent A | pympp | 5 min |

**Demo 2 deliverable:** AI agent autonomously researches competitors using Perplexity + Alchemy, Sardis Guard enforces $5/tx and $50/day limits, agent adapts when DENIED.

### Phase 3: Dashboard + Polish (16:00 - 18:00 PT / 02:00 - 04:00 TR)

| # | Task | Agent | Tech | Est |
|---|------|-------|------|-----|
| 3.1 | **Real-time dashboard** — spending chart, policy hit/miss, agent activity | Agent D | React + Vite + Tailwind | 45 min |
| 3.2 | **Policy builder UI** — fork from Sardis dashboard PolicyBuilder.tsx | Agent D | React | 30 min |
| 3.3 | **WebSocket/SSE stream** — live policy evaluation feed | Agent A | FastAPI + SSE | 15 min |
| 3.4 | **Multi-agent scenario** — 3 agents with different mandates, same Guard | Agent B | Python | 20 min |
| 3.5 | **Service directory PR** — register Sardis Guard in tempoxyz/mpp | Agent E | GitHub PR | 15 min |
| 3.6 | **Demo video** — 2-3 min screen recording | Me | Screen rec | 15 min |

**Demo 3 deliverable:** Full stack — dashboard with real-time policy enforcement visualization, multi-agent multi-service demo, PR submitted.

### Phase 4: BONUS — Wild Ideas (if time permits)

| # | Wild Idea | Impact | Difficulty |
|---|-----------|--------|------------|
| 4.1 | **MCP Server** — Sardis Guard as MCP tool for Claude Desktop | 🔥🔥🔥 | Medium |
| 4.2 | **Rust MPP Proxy** — high-perf policy proxy using mpp-rs + axum | 🔥🔥🔥 | Hard |
| 4.3 | **mppx Proxy** — TypeScript payment proxy wrapping OpenAI/Anthropic APIs | 🔥🔥 | Medium |
| 4.4 | **New MPP Service PR** — add a new service to the registry (like Alchemy PR #380) | 🔥🔥 | Easy |
| 4.5 | **Natural language mandate** — "spend max $10/day on research, no gambling" → policy rules | 🔥🔥🔥 | Medium |
| 4.6 | **Cross-agent delegation** — Agent A gives Agent B a sub-mandate | 🔥 | Hard |

---

## Tech Stack Decision

| Layer | Technology | Why |
|-------|-----------|-----|
| **MPP Server** | Python + FastAPI + pympp[tempo,server] | ✅ Already working, fastest path |
| **Policy Engine** | Pure Python (dataclasses) | Zero deps, sub-1ms evaluation |
| **Client SDK** | Python + pympp[tempo] + httpx | Consumer side for agents |
| **Agent** | Claude API (anthropic SDK) | Natural language reasoning |
| **Dashboard** | React + Vite + Tailwind | Fork from Sardis dashboard |
| **CLI** | Typer + tempo CLI | Quick testing |
| **Tunnel** | ngrok | Already running |
| **Chain** | Tempo mainnet (4217, USDC) | Wallet is on mainnet |

**Considered but skipped:**
- Rust (mpp-rs + axum): More impressive but takes 2x longer. Could be Phase 4 bonus.
- TypeScript (mppx + Next.js): Good for dashboard API but adds complexity.
- Fly.io deploy: ngrok is sufficient for hackathon.

---

## MPP Ecosystem Context

### Existing Services (from directory)
- **Alchemy** — Blockchain data APIs (JSON-RPC, NFT API), session-based pricing
- **Perplexity** — AI search, per-query pricing
- **StableEnrich** — Company/people enrichment
- **StableStudio** — Image generation
- **StableSocial** — Social media data
- **Locus** — Agent payment infra (YC F25, competitor)

### Gap We Fill
Nobody in the MPP ecosystem does **policy enforcement**. Services charge, agents pay — but there's no governance layer. Sardis Guard is that layer.

### Competitive Angle vs Locus
Locus does agent payments. Sardis Guard does **agent payment governance** — we're the firewall, not the pipe. We're composable with everything, including Locus.

---

## Endpoints (Final API Design)

| Endpoint | Method | Price | Description |
|----------|--------|-------|-------------|
| `GET /` | GET | Free | Service info + endpoint listing |
| `GET /health` | GET | Free | Health check |
| `POST /evaluate` | POST | $0.001 | Run 12-check policy, record result |
| `POST /simulate` | POST | $0.0005 | Dry-run policy (no state mutation) |
| `GET /mandate` | GET | $0.0001 | View current spending mandate |
| `PUT /mandate` | PUT | $0.001 | Update spending mandate |
| `GET /stats` | GET | $0.0001 | Agent spending statistics |
| `GET /audit` | GET | $0.001 | Full audit trail |
| `GET /stream` | GET | Free | SSE stream of policy evaluations |

---

## Reusable Sardis Assets

| Asset | File | What We Take |
|-------|------|-------------|
| SpendingPolicy engine | `sardis-core/spending_policy.py` | Logic reference (simplified) |
| SardisMPPClient | `sardis-mpp/client.py` | Direct use for agent client |
| PolicyBuilder UI | `dashboard/components/PolicyBuilder.tsx` | Fork for dashboard |
| Policy DSL | `sardis-core/policy_dsl.py` | JSON policy structure |
| Spending analytics | `sardis-cli/commands/spending.py` | CLI reference |

---

## Parallel Agent Strategy

```
Main Thread          Agent A (Backend)     Agent B (Agent/Demo)    Agent C (CLI)      Agent D (Dashboard)
────────────        ─────────────────     ──────────────────     ─────────────      ─────────────────
Phase 1 ✅
Phase 2 ──────────▶ Guard SDK + API       Claude agent demo      CLI tool
                     simulate endpoint     Multi-service flow
                     audit endpoint        Multi-agent scenario
Phase 3 ──────────▶ SSE stream            Polish demos           Service PR          React dashboard
                                                                                     Policy builder
Phase 4 ──────────▶ Wild ideas...
```

---

## Key Links

| What | URL |
|------|-----|
| Wallet | `0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c` |
| Server (local) | `http://localhost:8402` |
| Server (public) | `https://dendric-margie-answerlessly.ngrok-free.dev` |
| Tempo mainnet RPC | `https://rpc.tempo.xyz` |
| Chain ID | 4217 (mainnet) |
| USDC token | `0x20C000000000000000000000b9537d11c60E8b50` |
| pympp SDK | https://pypi.org/project/pympp/ |
| mpp-rs (Rust) | https://github.com/tempoxyz/mpp-rs |
| mppx (TypeScript) | https://www.npmjs.com/package/mppx |
| MPP spec | https://mpp.dev |
| Alchemy PR ref | https://github.com/tempoxyz/mpp/pull/380 |
| Hackathon | https://hackathon.tempo.xyz |

---

## Revenue Model (For Demo Pitch)

```
Agent ecosystem:
  1000 agents × 100 payments/day × $0.001/eval = $100/day = $36,500/year

At scale:
  100,000 agents × 50 payments/day × $0.001/eval = $5,000/day = $1.8M/year

+ Premium features:
  - Custom mandates: $0.01/update
  - Audit reports: $0.01/report
  - Real-time streaming: $0.005/min
  - Multi-agent delegation: $0.005/delegation
```

---

## Risk & Mitigations

| Risk | Mitigation |
|------|-----------|
| Low balance (1 USDC) | Evaluations cost $0.001 — we can do ~1000 evals |
| ngrok instability | Have fly.io Dockerfile ready as backup |
| pympp SDK bugs | We have the source, can patch locally |
| No other services to compose with | Use `tempo wallet services` to discover, or mock |
| Time pressure | Parallel agents, pre-built Sardis assets |
