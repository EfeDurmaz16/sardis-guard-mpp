# Sardis Guard Intelligence Plane | CLAUDE.md

## TL;DR

**Sardis Guard** is an MPP-native financial intelligence platform for AI agent payments. It sits between any AI agent and any MPP service, enforcing spending mandates, running ML anomaly detection, screening against OFAC sanctions, managing hierarchical mandate delegation, and producing evidence-grade audit trails -- all charged at $0.001 per evaluation via the Machine Payments Protocol.

**One-liner:** "MPP solves how agents pay. Sardis Guard solves whether agents should pay."

This is a hackathon demo of the full **Sardis protocol** -- the Internet's Financial Operating System for Machine Commerce.

---

## The Sardis Protocol (Full Context)

### What Problem Does Sardis Solve?

AI agents can reason, but they cannot be trusted with money. The existing agentic payment stack has a critical gap:

| Question | Standard | What It Does |
|----------|----------|-------------|
| What does the agent want? | **Google AP2** | Intent + mandate VDCs |
| Who is the agent? | **Visa TAP** | Agent identity + HTTP signatures |
| **How is spending authorized?** | **GAP** | No existing standard |
| **Is delivery verified?** | **GAP** | No existing standard |
| How does money move? | **Coinbase x402** | HTTP-native stablecoin |
| How does money move? | **Mastercard Agent Pay** | Agentic tokens + network |

Sardis fills the gap between identity (TAP) and settlement (x402/card/bank). It answers: "Given who this agent is, is this specific payment authorized, safe, and compliant?"

### Protocol Architecture (6 Layers)

```
                    Principal (human)
                         |
                    Agent (AI)  <------>  Merchant
                         |
               +---------v----------+
               |   Identity Layer   |   Agent certificates, trust tiers,
               |                    |   TAP-compatible Ed25519 signatures
               +--------+---------+
                         |
               +---------v----------+
               |   Protocol Core    |   Mandate engine, token minter,
               |                    |   22-state machine, policy evaluator
               +---+----------+----+
                   |          |
          +--------v---+  +--v-----------+
          | Funding    |  | Privacy      |   Groth16 circuits,
          | (UTXO)     |  | (ZKP)        |   3 privacy tiers
          | Cells,     |  |              |
          | split/merge|  |              |
          +------+-----+  +------+-------+
                 |               |
               +-v---------------v---+
               | Escrow + Dispute    |   Timelock holds, delivery ACK,
               |                     |   arbitration node
               +--------+-----------+
                         |
               +---------v----------+
               | Settlement Layer   |   Rail selection, FX bridge,
               | (Liquidity Router) |   clearance lock
               +--+-+-+--+---------+
                  | | |  |
               x402 Card Bank FX
```

### Dual-Rail Architecture (v1.1)

Sardis uses an **internal ledger as primary rail** (like PayPal). Money enters Sardis via on-ramps (bank transfer, card, USDC, stablecoin, credit). Once inside:

- **Payer vault** (FundingCells/UTXO) -> **Atomic ledger transfer** -> **Merchant account** (Sardis balance)
- Transfer is ~1ms, ~$0 fee, zero external API calls
- External rails (x402, card/Stripe, bank/ACH, FX bridge, wire) are **off-ramp/fallback only**

### Payment Object Lifecycle (22 States)

The Sardis payment object follows a 22-state lifecycle:

```
ISSUED -> PRESENTED -> VERIFIED
                         |
                    +----+----+
                    |         |
              (direct)    (escrow)
                    |         |
                 LOCKED   ESCROWED -> CONFIRMING -> RELEASED
                    |                                  |
                    +----------+  +--------------------+
                               |  |
                         SETTLING (+FX)
                          |         |
                   PARTIAL_SETTLED  SETTLED -> FULFILLED
                   (UNLOCK, cells                |
                    RETURNED)              DISPUTING -> ARBITRATING -> RESOLVED

Side transitions: ISSUED -> REVOKED, ISSUED -> EXPIRED
```

### Mandate Signing Flow

1. **Principal defines policy** -- merchant scope, limits, FX, expiry
2. **Canonical serialization** -- JSON deterministic byte order
3. **SHA-256 hash** -- payload to 32-byte digest
4. **Ed25519 sign** -- hash + private key (never leaves device) = 64-byte sig
5. **JWS compact serialization** -- header.payload.signature (RFC 7515)

The signed mandate is verified by: Issuer (stores), Merchant (verifies claims), Arbitration (dispute evidence), Agent (reads bounds). Anyone with the public key can verify -- only the principal can sign.

---

## Hackathon Context

- **Event:** Tempo MPP Hackathon, March 19 2026
- **Team:** Efe Baran Durmaz (solo, using Claude Code with parallel agents)
- **Wallet:** `0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c` (Tempo mainnet, chain 4217)
- **Server:** FastAPI on port 8402, tunneled via ngrok
- **Revenue model:** $0.001 per policy evaluation via MPP. Every agent payment in the ecosystem = revenue.

---

## What We Built (Architecture)

```
AI Agent -> Sardis Guard (MPP, $0.001) -> 8-Gate Intelligence Pipeline -> ALLOW/FLAG/HOLD/FREEZE/DENY
                                                                             |
                                                                      if ALLOWED
                                                                             |
                                                                             v
                                                            MPP Service (Perplexity, Alchemy, etc.)
```

### The 8-Gate Security Pipeline

Every payment evaluation passes through 8 sequential gates. A failure at any gate stops the payment:

| Gate | Module | What It Does | Hackathon Status |
|------|--------|-------------|-----------------|
| **Gate 0** | `DedupStore` | Idempotency keys, nonce tracking, fingerprint dedup. Rejects replays before any state mutation. | IMPLEMENTED |
| **Gate 1** | `GovernanceEngine` | 10-point mandate check: active status, per-tx limit, remaining budget, service allowed, merchant not blocked, chain allowed, currency allowed, delegation depth, parent chain active, approval threshold. | IMPLEMENTED |
| **Gate 2** | `SanctionsScreener` | OFAC SDN address screening (exact match) + entity name screening (exact, substring, Levenshtein fuzzy match). Downloads live from Treasury or falls back to fixture of ~20 known sanctioned addresses. | IMPLEMENTED |
| **Gate 3** | `RiskEngine` | ML anomaly detection (IsolationForest, 12-feature vector), Markov-chain service transition surprisal, cross-agent Jaccard correlation. | IMPLEMENTED |
| **Gate 4** | `PolicyEngine` | 12-check policy pipeline (mandate active, per-tx limit, daily limit, merchant allow/block, category allow/block, chain allowlist, currency allowlist, memo requirement, gas price check, cooldown). | IMPLEMENTED |
| **Gate 5** | Action Resolution | Composite scoring: sanctions=FREEZE_TREE, governance fail=DENY, risk score thresholds (0.45=ALLOW, 0.70=FLAG, 0.85=HOLD, else=FREEZE_CHILD). | IMPLEMENTED |
| **Gate 6** | `MandateStore` | Spend recording with upward propagation through delegation tree. Budget exhaustion triggers EXHAUSTED status. | IMPLEMENTED |
| **Gate 7** | `EventStore` | Hash-chained append-only audit trail (SHA-256 chain). SQLite WAL for writes, DuckDB for analytics. Evidence pack generation. | IMPLEMENTED |

### Action Severity Ladder

```
ALLOW       -> Payment proceeds normally
FLAG        -> Payment proceeds, flagged for review
HOLD        -> Payment paused, requires manual release
FREEZE_CHILD -> Target mandate frozen, all future payments denied
FREEZE_TREE  -> Target mandate + all descendants frozen (sanctions response)
DENY         -> Payment blocked, no state mutation
```

---

## Project Structure

```
sardis-mpp-hackathon/
+-- CLAUDE.md              <- You are here
+-- PLAN.md                <- Full hackathon timeline
+-- pyproject.toml          <- Python project config
+-- src/
|   +-- server.py           <- FastAPI + MPP server, 8 endpoints (v1), lazy-loads intelligence modules
|   +-- routes_v2.py        <- V2 routes: mandates, screening, dashboard, reports, full pipeline
|   +-- policy.py           <- 12-check policy engine (Gate 4)
|   +-- types.py            <- 4 canonical types: PaymentIntentEvent, MandateNode, RiskAssessment, AuditEvidencePack
|   +-- guard_client.py     <- Client SDK for agents (wraps tempo CLI)
|   +-- cli.py              <- CLI tool for policy checks
|   +-- demo_agent.py       <- AI agent demo
|   +-- mandates/
|   |   +-- mandate_store.py <- Delegation tree, scope narrowing, spend propagation, freeze/resume (Gate 6)
|   +-- governance/
|   |   +-- engine.py       <- 10-point governance evaluation, action application (Gate 1)
|   |   +-- signatures.py   <- Signature verification helpers
|   +-- risk/
|   |   +-- engine.py       <- IsolationForest + Markov + cross-agent correlation (Gate 3)
|   |   +-- features.py     <- 12-feature extraction: amount_vs_p50, velocity, novelty, delegation_depth, etc.
|   +-- compliance/
|   |   +-- sanctions.py    <- OFAC SDN screening: address exact match, entity fuzzy match (Gate 2)
|   |   +-- address_risk.py <- On-chain address risk analysis
|   +-- security/
|   |   +-- dedup.py        <- Idempotency keys, nonce tracking, fingerprint dedup (Gate 0)
|   +-- storage/
|   |   +-- event_store.py  <- SQLite WAL + DuckDB analytics, hash-chain integrity (Gate 7)
|   +-- services/
|   |   +-- wrappers.py     <- Typed wrappers for MPP services (Perplexity, StableEnrich, Browserbase, Tempo RPC)
|   |   +-- registry.py     <- Service metadata registry
|   +-- swarm/
|   |   +-- orchestrator.py <- Multi-agent scenario runner with mandate delegation
|   |   +-- scenarios.py    <- Benign + attack scenario definitions
|   +-- intel/
|       +-- merchant.py     <- Merchant intelligence
|       +-- onchain.py      <- On-chain intelligence
+-- data/                   <- SQLite databases (sardis_guard.db, dedup.db), OFAC cache
+-- tests/
```

---

## Core Types (src/types.py)

Four canonical types shared across all modules:

### PaymentIntentEvent

The source-of-truth event for every evaluation. Contains identity fields (agent_id, principal_id, mandate_id), payment details (amount, currency, network, merchant, category), service context (service_id, service_path, purpose), and result fields filled by the pipeline (policy_verdict, governance_result, risk_assessment, aml_result, action). Includes SHA-256 hash chain (prev_hash, entry_hash) for tamper-evident audit.

```json
{
  "event_id": "uuid",
  "timestamp": 1710864000.0,
  "agent_id": "agent_researcher",
  "principal_id": "principal_demo",
  "mandate_id": "mnd_abc123",
  "amount": "0.05",
  "currency": "USDC",
  "network": "tempo",
  "merchant": "perplexity.mpp.paywithlocus.com",
  "category": "research",
  "service_id": "perplexity",
  "action": "ALLOW",
  "downstream_allowed": true,
  "governance_result": { "allowed": true, "checks": [...] },
  "risk_assessment": { "ml_score": 0.12, "final_score": 0.08, "action": "ALLOW" },
  "aml_result": { "hit": false },
  "prev_hash": "abc...",
  "entry_hash": "def..."
}
```

### MandateNode

A node in the mandate delegation tree. Enforces hierarchical budget constraints where each child further constrains (never expands) its parent's bounds.

```json
{
  "mandate_id": "mnd_abc123",
  "parent_id": "mnd_root_xyz",
  "principal_id": "principal_demo",
  "agent_id": "agent_researcher",
  "max_total": "50.00",
  "max_per_tx": "5.00",
  "spent": "12.50",
  "remaining": "37.50",
  "allowed_services": ["perplexity", "stableenrich"],
  "allowed_merchants": [],
  "blocked_merchants": ["gambling.com"],
  "allowed_chains": ["tempo", "base"],
  "allowed_currencies": ["USDC", "pathUSD"],
  "status": "active",
  "approval_threshold": "10.00",
  "delegation_depth": 1,
  "max_delegation_depth": 3,
  "is_active": true
}
```

### RiskAssessment

Output of the ML risk engine. Composite of 4 sub-scores with fixed action thresholds.

```json
{
  "ml_score": 0.23,
  "sequence_score": 0.0,
  "correlation_score": 0.0,
  "sanctions_score": 0.0,
  "final_score": 0.08,
  "action": "ALLOW",
  "features": {
    "amount_usd": 0.05,
    "amount_vs_agent_p50": 1.0,
    "velocity_5m": 2.0,
    "velocity_1h": 5.0,
    "merchant_novelty": 0.5,
    "service_novelty": 0.3,
    "delegation_depth": 1.0,
    "budget_utilization": 0.25,
    "sanctions_exact_hit": 0.0
  },
  "reasons": []
}
```

### AuditEvidencePack

Self-contained compliance evidence for a session. Includes all events, mandate chain, risk assessments, sanctions results, and hash chain integrity validation.

---

## API Endpoints

### V1 Endpoints (MPP-gated)

| Endpoint | Method | Price | Description |
|----------|--------|-------|-------------|
| `GET /` | GET | Free | Service info + module status |
| `GET /health` | GET | Free | Health check |
| `POST /evaluate` | POST | $0.001 | 12-check policy evaluation |
| `POST /simulate` | POST | $0.0005 | Dry-run policy (no state mutation) |
| `GET /mandate` | GET | $0.0001 | View spending mandate |
| `PUT /mandate` | PUT | $0.001 | Update spending mandate |
| `GET /stats` | GET | $0.0001 | Spending statistics |
| `GET /audit` | GET | $0.001 | Full audit trail |
| `GET /stream` | GET | Free | SSE live evaluation feed |

### V2 Endpoints (Full Intelligence Pipeline)

| Endpoint | Method | Price | Description |
|----------|--------|-------|-------------|
| `POST /evaluate/v2` | POST | $0.001 | Full 8-gate intelligence pipeline with governance, sanctions, ML risk |
| `POST /mandates/root` | POST | Free | Create root mandate |
| `POST /mandates/delegate` | POST | Free | Delegate child mandate (enforces scope narrowing) |
| `POST /mandates/freeze` | POST | Free | Freeze mandate (optionally with all descendants) |
| `POST /mandates/resume` | POST | Free | Resume frozen mandate (requires active parent) |
| `GET /mandates` | GET | Free | List all mandates |
| `GET /mandates/{id}` | GET | Free | Mandate detail with children and tree size |
| `POST /screen/entity` | POST | Free | Screen entity name against OFAC sanctions |
| `POST /screen/address` | POST | Free | Screen wallet address against OFAC sanctions |
| `GET /dashboard/summary` | GET | Free | Aggregate stats (events, agents, volume, denials) |
| `GET /dashboard/graph` | GET | Free | Service transition graph for visualization |
| `GET /agents/{id}/risk` | GET | Free | Agent risk timeline and summary |
| `GET /reports/session/{id}` | GET | Free | Compliance evidence pack with hash chain validation |

---

## Enterprise Feature Map: Implemented vs. Aspirational

### IMPLEMENTED in Hackathon

| Feature | Enterprise Map Category | What We Built |
|---------|------------------------|---------------|
| **Mandate delegation tree** | Governance (1) | Root mandate -> child mandates with scope narrowing. Child can never exceed parent's budget or scope. |
| **Budget enforcement** | Governance (1) | Per-tx limits, total budget caps, spend propagation up the tree, EXHAUSTED auto-status. |
| **Approval thresholds** | Governance (1) | Amount-based approval gates on mandates. |
| **Policy engine (12 checks)** | Governance (1) | Merchant allow/block, category allow/block, chain/currency allowlists, cooldown, gas price, memo requirement. |
| **OFAC sanctions screening** | Compliance (3) | Real OFAC SDN list download + parsing. Address exact match + entity fuzzy match (Levenshtein). |
| **Immutable audit trail** | Compliance (3) | SHA-256 hash-chained event store. SQLite WAL for writes. Evidence pack generation with chain validation. |
| **Real-time analytics** | Compliance (3) | DuckDB analytics: per-agent summaries, risk timelines, service transition graphs, dashboard aggregates. |
| **ML anomaly detection** | Security (5) | IsolationForest on 12-feature vector. Markov-chain service transition surprisal. Cross-agent Jaccard correlation. |
| **Auto-freeze (FREEZE_CHILD/TREE)** | Security (5) | Sanctions hit -> FREEZE_TREE (mandate + all descendants). High risk -> FREEZE_CHILD. |
| **Dedup / replay protection** | Security (5) | Idempotency keys (24h TTL), monotonic nonces, request fingerprint dedup. Fail-closed. |
| **SSE event streaming** | Integration (6) | Real-time Server-Sent Events for all evaluations. |
| **Agent fleet tracking** | Identity (2) | Per-agent state tracking, risk trends (rising/falling/stable), multi-agent correlation detection. |
| **Role-based agent scoping** | Identity (2) | Mandates scope agents to specific services (planner, researcher, scraper, analyst roles). |
| **Swarm orchestration** | Identity (2) | Multi-agent scenario runner with benign warmup + attack detection demo. |

### Could Be Added During Hackathon

| Feature | Effort | Impact for Demo |
|---------|--------|----------------|
| **Dashboard UI** (React + Vite) | 1-2 hours | High -- visual demo of mandate tree, risk timeline, live evaluations |
| **Natural language mandates** | 30 min | High -- "spend max $10/day on research, no gambling" -> policy rules |
| **MCP Server** | 1 hour | High -- Sardis Guard as a tool in Claude Desktop/Cursor |
| **Multi-sig mandates** | 45 min | Medium -- N-of-M signature requirement on high-value mandates |
| **Webhook delivery** | 30 min | Medium -- POST to callback URL on state transitions |

### Aspirational (Enterprise Roadmap)

| Feature | Phase | Why It Matters for Paradigm |
|---------|-------|-----------------------------|
| Multi-signature mandates (N-of-M Ed25519) | Phase 2 | Enterprise treasury won't use single-signer authorization |
| Hierarchical delegation (CFO -> VP -> team lead) | Phase 3 | Maps to how enterprise budgets actually work |
| Configurable approval workflows (Slack/Teams) | Phase 2 | Approval outside Sardis dashboard = zero adoption |
| Spending policies as code (OPA/Rego) | Phase 3 | "Set rules once, enforce everywhere" |
| SSO + SCIM integration (Okta, Azure AD) | Phase 2 | Enterprise security requirement #1 |
| Full ZKP verification (3 privacy tiers) | Phase 3 | Prevents competitive intelligence leaks between merchants |
| HSM key management (FIPS 140-2 Level 3) | Phase 3 | Enterprise policy mandates HSM for financial authorization |
| Accounting integration (QuickBooks, Xero, NetSuite) | Phase 3 | Invisible agent spend = CFO blocks it |
| Terraform/IaC provider | Phase 3 | Enterprise DevOps manages everything via code |
| ERP connectors (SAP Ariba, Coupa) | Phase 4 | Enterprise procurement lives inside ERP workflows |
| Multi-vault treasury with yield | Phase 2-3 | Department isolation + yield on idle balances |
| Dedicated infrastructure + 99.99% SLA | Phase 3 | Procurement checklist items |

### Most Impressive for Paradigm Investors

1. **8-gate pipeline is real, not vaporware** -- every gate has working code with sub-millisecond evaluation
2. **ML anomaly detection** -- IsolationForest + Markov + cross-agent correlation is a genuine moat
3. **OFAC sanctions screening** -- downloads real OFAC SDN list from Treasury, not a mock
4. **Mandate delegation tree** -- hierarchical budget constraints that mirror enterprise org charts
5. **Hash-chained audit trail** -- tamper-evident, evidence-grade, SOC 2-compatible from day one
6. **Revenue from day one** -- $0.001/eval via MPP, not waiting for enterprise contracts
7. **Protocol-level positioning** -- fills the gap between AP2/TAP (identity) and x402 (settlement) that no one else occupies

---

## Ecosystem Positioning

### Where Sardis Fits

```
Existing Standards (left)                    Sardis Protocol (right, fills the gap)
---------------------------------------     -----------------------------------------
Google AP2 (Intent + mandates)        ----> Extends AP2 mandate model
Visa TAP (Agent identity)             ----> TAP-compatible certificates
                                             UTXO cells + one-time objects
    [GAP: How is spending authorized?]       ZKP privacy (3 tiers)
    [GAP: Is delivery verified?]             Escrow + arbitration
                                             Recurring mandate trees
                                             22-state lifecycle engine
Coinbase x402 (Stablecoin)            ----> Multi-rail settlement + FX
Mastercard Agent Pay (Network)               Internal ledger (primary rail)
                                             x402 / card / bank adapters
```

### Competitive Positioning

| Player | What They Do | How Sardis Differs |
|--------|-------------|-------------------|
| **Locus** (YC F25) | Agent payment infrastructure | Sardis is the governance/firewall layer -- composable with Locus, not competing |
| **Orthogonal** (YC W26) | Pivoted to API marketplace | No longer a payments competitor |
| **Coinbase x402** | HTTP-native stablecoin transfer | Settlement rail only -- no policy, no governance, no compliance |
| **Mastercard Agent Pay** | Agentic tokens + card network | Card-rail specific -- Sardis is rail-agnostic |
| **Stripe MPP** | Payment method for machine commerce | Payment processing -- Sardis adds the trust/governance layer on top |

### Key Insight

Everyone else is building **pipes** (how money moves). Sardis builds **valves** (whether money should move). Valves are more defensible than pipes because:
- Compliance requirements only increase over time
- Policy complexity grows with agent fleet size
- ML models improve with more data (network effect)
- Enterprise procurement requires governance, not just payment processing

---

## Tech Stack

| Technology | Why |
|-----------|-----|
| **Python 3.12+** | pympp SDK is Python-first, fastest iteration |
| **FastAPI** | Async, automatic OpenAPI docs, pympp server integration |
| **pympp[tempo,server]** | Official MPP SDK -- handles 402 challenge/credential/receipt flow |
| **scikit-learn** | IsolationForest for anomaly detection |
| **SQLite WAL** | Append-only event store with hash chain integrity |
| **DuckDB** | Analytics read model attached to SQLite for aggregation queries |
| **Tempo mainnet (chain 4217)** | Wallet configured for mainnet USDC payments |
| **ngrok** | Quick public URL for demo |
| **dataclasses** | Zero-dep domain models, sub-1ms evaluation |

---

## MPP Protocol Quick Reference

The Machine Payments Protocol uses HTTP 402 for machine payments:

1. Client requests a paid endpoint -> Server returns **402** with `WWW-Authenticate` header
2. Header contains a **Challenge** (amount, currency, recipient, method)
3. Client signs a payment transaction and retries with `Authorization` header containing a **Credential**
4. Server **verifies** payment on-chain, returns **200** with `Payment-Receipt` header

pympp handles all of this automatically:
- **Server side:** `Mpp.create()` + `mpp_server.charge()` -- generates challenges, verifies credentials
- **Client side:** `tempo request` CLI -- auto-handles 402 -> pay -> retry

---

## CLI Tools

### Tempo CLI (wallet/payments)
```bash
source ~/.tempo/env
tempo wallet -t whoami                    # Check wallet
tempo wallet -t services --search "..."   # Discover MPP services
tempo request -t -X POST --json '{}' URL  # Make MPP request
```

### Sardis Guard CLI
```bash
cd ~/sardis-mpp-hackathon && source .venv/bin/activate
python src/cli.py evaluate --amount 1.50 --merchant perplexity.ai
python src/cli.py simulate --amount 100 --merchant gambling.com
python src/cli.py mandate
python src/cli.py stats
python src/cli.py audit
python src/cli.py health
```

### Server Management
```bash
cd ~/sardis-mpp-hackathon && source .venv/bin/activate
uvicorn src.server:app --host 0.0.0.0 --port 8402   # Start server
kill $(lsof -ti:8402)                                 # Kill server
```

### Swarm Demo
```bash
cd ~/sardis-mpp-hackathon && source .venv/bin/activate
python -m src.swarm.orchestrator                      # Benign warmup
python -m src.swarm.orchestrator --attack              # Benign + attack
python -m src.swarm.orchestrator --attack-only         # Attack only
```

---

## Development Rules

1. **Work in `~/sardis-mpp-hackathon/`** -- do not pollute the main sardis repo
2. **Always use the venv** -- `source .venv/bin/activate` before running Python
3. **Always source tempo** -- `source ~/.tempo/env` before tempo CLI commands
4. **Commit atomically** -- each feature/fix gets its own commit
5. **Test with real payments** -- use `tempo request` to verify MPP flow works
6. **Keep server running** -- port 8402 should always be up for demos
7. **Balance awareness** -- wallet has limited USDC, evaluations cost $0.001
8. **All types in src/types.py** -- never define domain types in other modules
9. **Fail-closed** -- if any security module is unavailable, DENY the payment (except in dev)

---

## Key URLs

| What | URL |
|------|-----|
| Server (local) | http://localhost:8402 |
| Server (public) | Via ngrok (check `http://localhost:4040/api/tunnels`) |
| SSE stream | http://localhost:8402/stream |
| Tempo mainnet RPC | https://rpc.tempo.xyz |
| Chain ID | 4217 (mainnet) |
| USDC token | `0x20C000000000000000000000b9537d11c60E8b50` |
| MPP spec | https://mpp.dev |
| Hackathon | https://hackathon.tempo.xyz |

---

## MPP Ecosystem Services

| Service | URL | What It Does |
|---------|-----|-------------|
| Perplexity | `perplexity.mpp.paywithlocus.com` | AI search |
| StableEnrich | `stableenrich.dev` | People/company enrichment, Exa search, Firecrawl |
| Alchemy | `mpp.alchemy.com` | Blockchain data |
| Browserbase | `mpp.browserbase.com` | Headless browser |

---

## Parent Project (Sardis)

This hackathon project demonstrates a focused subset of the full Sardis platform at `~/sardis/`:

| Sardis Component | Hackathon Equivalent |
|-----------------|---------------------|
| `sardis-core/spending_policy.py` | `src/policy.py` (12-check engine) |
| `sardis-protocol/ap2.py` | `src/governance/engine.py` (mandate verification) |
| `sardis-compliance/` | `src/compliance/sanctions.py` (OFAC screening) |
| `sardis-ledger/` | `src/storage/event_store.py` (hash-chained audit) |
| `sardis-chain/executor.py` | MPP settlement via pympp/Tempo |
| `sardis-wallet/` | Tempo wallet (0xa4df...) |
| `sardis-mpp/client.py` | `src/guard_client.py` |

The full Sardis platform has 12+ monorepo packages, 50+ DB tables, 47+ API routers, Solidity smart contracts, a React dashboard, and integrations with CrewAI, AutoGPT, OpenClaw, Composio, n8n, and more. This hackathon project proves the core thesis: **policy enforcement as a service is viable, valuable, and monetizable from day one via MPP.**
