# Sardis Guard Intelligence Plane - Ecosystem Research

> Research conducted: 2026-03-19
> Purpose: Inform hackathon strategy for Sardis Guard — an MPP-native financial intelligence service

---

## Table of Contents

1. [GitHub Open Source Landscape](#1-github-open-source-landscape)
2. [MPP Ecosystem Analysis](#2-mpp-ecosystem-analysis)
3. [Domain/DNS APIs for Company Builder](#3-domaindns-apis-for-company-builder)
4. [What the MPP Ecosystem Needs](#4-what-the-mpp-ecosystem-needs)
5. [Competitor Analysis](#5-competitor-analysis)
6. [Strategic Recommendations](#6-strategic-recommendations)

---

## 1. GitHub Open Source Landscape

### 1.1 "Machine Payments Protocol" Search Results

| Project | Stars | Description | Relevance |
|---------|-------|-------------|-----------|
| [wevm/mppx](https://github.com/wevm/mppx) | 44 | Official TypeScript SDK for MPP | **Core SDK** — client/server, proxy, Stripe, MCP support |
| [tempoxyz/mpp-rs](https://github.com/tempoxyz/mpp-rs) | 38 | Official Rust SDK for MPP | Reference implementation |
| [tempoxyz/mpp-specs](https://github.com/tempoxyz/mpp-specs) | 30 | IETF specification for MPP | Protocol spec — HTTP 402 + Payment auth scheme |
| [solana-foundation/solana-mpp-sdk](https://github.com/solana-foundation/solana-mpp-sdk) | 30 | Solana payment method for MPP | Shows cross-chain interest |
| [tempoxyz/pympp](https://github.com/tempoxyz/pympp) | 11 | Official Python SDK for MPP | What we're building on |
| [SylvainCostes/fastapi-mpp](https://github.com/SylvainCostes/fastapi-mpp) | 1 | FastAPI middleware for MPP | **Directly relevant** — 402 challenges + receipt validation for FastAPI |
| [Kenny50/onlygate-tempo-mpp-wrapper](https://github.com/Kenny50/onlygate-tempo-mpp-wrapper) | 0 | Zero-trust HITL wrapper for MPP | **Direct competitor** — see Section 5 |
| [teckedd-code2save/agentmart](https://github.com/teckedd-code2save/agentmart) | 1 | Agent-to-agent economy on MPP | Interesting pattern: agents hiring agents |
| [cloudflare/mpp-proxy](https://github.com/cloudflare/mpp-proxy) | 38 | Cloudflare Worker MPP payment-gated proxy | **Key pattern** — the canonical way to wrap existing APIs with MPP |

**Key Hackathon Projects (from recent PRs to tempoxyz/mpp):**

| PR # | Project | What it does |
|------|---------|-------------|
| #381 | StableDomains | Domain registration as MPP service |
| #379 | Soulink | On-chain identity/trust for AI agents (Base, ERC-721 .agent names) |
| #378 | GovLaws | U.S. federal regulation lookup via MPP |
| #377 | Palm | Polymarket analytics + meme data |
| #374 | mppx-solana | Solana payment method docs |
| #373 | ClawdMarket | Agent-to-agent marketplace |

### 1.2 "Agent Payments" Search Results

| Project | Stars | Description | Relevance |
|---------|-------|-------------|-----------|
| [xpaysh/agentic-economy-boilerplate](https://github.com/xpaysh/agentic-economy-boilerplate) | 7 | "Rosetta Stone" for agentic payments — 5+ protocols | Shows protocol fragmentation |
| [ChaosChain/chaoschain-x402](https://github.com/ChaosChain/chaoschain-x402) | 17 | Decentralized facilitator for x402 | x402 alternative ecosystem |
| [beep-it/beep-sdk](https://github.com/beep-it/beep-sdk) | 17 | Agent-to-agent payments on SUI | Cross-chain competition |
| [worldliberty/agentpay-sdk](https://github.com/worldliberty/agentpay-sdk) | 10 | Open SDK: agents pay, hold funds, move money with policy enforcement | **Conceptually close to Sardis** |
| [bitrefill/awesome-agentic-payments](https://github.com/bitrefill/awesome-agentic-payments) | 3 | Curated list of agentic payment protocols | Good reference list |
| [matverach/paysentry](https://github.com/matverach/paysentry) | 4 | Authorization gateway for AI agent payments | **Direct competitor concept** — see Section 5 |
| [mkmkkkkk/paysentry](https://github.com/mkmkkkkk/paysentry) | 4 | Payment control plane for AI agents (x402 focused) | **Direct competitor concept** — spending limits, circuit breakers, audit trails |
| [sentient-agi/agentic-payments-bot](https://github.com/sentient-agi/agentic-payments-bot) | 4 | Agentic payment service for Open Agent Skills | Sentient AGI interest |

### 1.3 "AI Agent Wallet" Search Results

| Project | Stars | Description | Relevance |
|---------|-------|-------------|-----------|
| [EmblemCompany/EmblemAi-AgentWallet](https://github.com/EmblemCompany/EmblemAi-AgentWallet) | 6 | Multi-chain wallet for AI agents | Generic solution |
| [francis-codex/seedless-agent-wallet](https://github.com/francis-codex/seedless-agent-wallet) | 2 | Autonomous agent wallet on Solana with on-chain policy | Solana-focused policy enforcement |

### 1.4 Sanctions/Compliance Screening Tools

| Project | Stars | Description | Relevance |
|---------|-------|-------------|-----------|
| [moov-io/watchman](https://github.com/moov-io/watchman) | **440** | AML/CTF/KYC/OFAC watchlist search | **Best open source option** — Go-based, well-maintained |
| [opensanctions/yente](https://github.com/opensanctions/yente) | 126 | OpenSanctions API with entity search + bulk matching | **Python-friendly**, Reconciliation API spec |
| [0xB10C/ofac-sanctioned-digital-currency-addresses](https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses) | 156 | Extract sanctioned crypto addresses from SDN list | Direct wallet address screening |
| [ultrasoundmoney/ofac-ethereum-addresses](https://github.com/ultrasoundmoney/ofac-ethereum-addresses) | 54 | Ethereum addresses on OFAC SDN list | Quick lookup table |

**Key Insight:** No one has built an MPP-native compliance/screening service. This is a gap.

### 1.5 "Payment Firewall" and "Anomaly Detection" Results

Almost nothing exists in open source. The `Recurring_Payment_Firewall` by vortex-m focuses on subscription abuse detection but has 0 stars. There is no open-source payment anomaly detection tool designed for agent payments.

**Key Insight:** "Payment firewall" as a category does not exist yet. Sardis Guard would be first.

---

## 2. MPP Ecosystem Analysis

### 2.1 Tempo Organization (tempoxyz) — Complete Repo Inventory

| Repo | Stars | Category | Notes |
|------|-------|----------|-------|
| [tempo](https://github.com/tempoxyz/tempo) | 870 | Core blockchain | The Tempo L1 node (Rust, reth-based) |
| [tempo-apps](https://github.com/tempoxyz/tempo-apps) | 180 | Applications | Monorepo for Tempo apps |
| [tempo-ts](https://github.com/tempoxyz/tempo-ts) | 71 | SDK | TypeScript tooling for Tempo |
| [tempo-foundry](https://github.com/tempoxyz/tempo-foundry) | 72 | Tooling | Fork of Foundry with Tempo support |
| [tempo-std](https://github.com/tempoxyz/tempo-std) | 63 | Tooling | Foundry contracts/libraries for Tempo |
| [tempo-go](https://github.com/tempoxyz/tempo-go) | 62 | SDK | Go SDK |
| [mpp-rs](https://github.com/tempoxyz/mpp-rs) | 38 | SDK | Rust MPP SDK |
| [mpp-specs](https://github.com/tempoxyz/mpp-specs) | 30 | Spec | IETF specification |
| [metrics-derive](https://github.com/tempoxyz/metrics-derive) | 24 | Tooling | Rust metrics macro |
| [mpp](https://github.com/tempoxyz/mpp) | 21 | Docs | mpp.dev documentation site + service directory |
| [agent-skills](https://github.com/tempoxyz/agent-skills) | 17 | Agent | Skills for AI coding agents (Claude/Amp/Codex) |
| [rpc-tester](https://github.com/tempoxyz/rpc-tester) | 15 | Tooling | RPC testing tool |
| [pytempo](https://github.com/tempoxyz/pytempo) | 13 | SDK | PoC Python client for Tempo |
| [pympp](https://github.com/tempoxyz/pympp) | 11 | SDK | Python MPP SDK |
| [docs](https://github.com/tempoxyz/docs) | 11 | Docs | Documentation |
| [.github](https://github.com/tempoxyz/.github) | 10 | Meta | Org-level config |
| [tempo-support](https://github.com/tempoxyz/tempo-support) | 10 | Support | Issues/support |
| [changelogs](https://github.com/tempoxyz/changelogs) | 8 | Docs | Changelogs |
| [chains](https://github.com/tempoxyz/chains) | 7 | Config | Chain metadata |
| [examples](https://github.com/tempoxyz/examples) | 6 | Examples | TypeScript examples |
| [wallet](https://github.com/tempoxyz/wallet) | 5 | Wallet | Tempo wallet |
| [incur-rs](https://github.com/tempoxyz/incur-rs) | 3 | Tooling | Rust CLI framework for agents |
| [mpp-proxy-cf](https://github.com/tempoxyz/mpp-proxy-cf) | 0 | Proxy | Cloudflare proxy template (empty README) |
| [cf-template-proxy](https://github.com/tempoxyz/cf-template-proxy) | 0 | Proxy | CF template |
| [ledger-app-tempo](https://github.com/tempoxyz/ledger-app-tempo) | 2 | Hardware | Ledger hardware wallet plugin |

### 2.2 wevm/mppx — TypeScript SDK Deep Dive

**Architecture:**
```
src/
  BodyDigest.ts       - Content hash verification
  Challenge.ts        - 402 challenge parsing
  Credential.ts       - Payment credential handling
  Errors.ts           - Error types
  Expires.ts          - Expiration handling
  Mcp.ts              - MCP integration
  Method.ts           - Payment method abstraction
  PaymentRequest.ts   - Request construction
  Receipt.ts          - Receipt verification
  Store.ts            - Session/credential storage
  client/             - Client-side SDK
  server/             - Server-side SDK
  proxy/              - MPP proxy implementation
  middlewares/         - Express/Hono middleware
  stripe/             - Stripe SPT integration
  tempo/              - Tempo chain integration
  viem/               - Viem integration
  mcp-sdk/            - MCP SDK integration
  cli/                - CLI tool
```

**Examples:**
- `charge` — Payment-gated photo generation API
- `charge-wagmi` — Payment-gated charge with Wagmi + React
- `session/multi-fetch` — Multiple paid requests over a single payment channel
- `session/sse` — Pay-per-token LLM streaming with SSE
- `stripe` — Stripe SPT charge with automatic client

**Key Pattern: cloudflare/mpp-proxy (38 stars)**
- Cloudflare Worker acting as transparent reverse proxy
- Payment-gated access via HTTP 402 + `WWW-Authenticate: Payment`
- JWT cookie after successful payment (1-hour session)
- Ships with Tempo production defaults
- One-click "Deploy to Cloudflare" button
- **This is the canonical pattern for wrapping any API with MPP payments**

### 2.3 MPP Service Directory — Complete List (54+ services)

**Categories defined:** ai, blockchain, compute, data, media, search, social, storage, web

**All services in directory:**

| Service | Category | Integration | Description |
|---------|----------|-------------|-------------|
| AgentMail | ai, social | first-party | Email inboxes for AI agents |
| Allium | blockchain, data | first-party | On-chain finance data, token prices, SQL explorer |
| Anthropic | ai | third-party | Claude chat completions |
| Browserbase | web, compute, search | first-party | Headless browser sessions |
| Codex | blockchain, data | first-party | On-chain data API, 80+ networks |
| Dune | data, blockchain | first-party | SQL analytics on blockchain data |
| Exa | search, ai | third-party | AI-powered web search |
| fal.ai | ai, media | third-party | Image/video/audio generation (600+ models) |
| Firecrawl | web, data | third-party | Web scraping/crawling |
| Google Gemini | ai, media | third-party | Gemini, Veo, Imagen |
| Modal | compute | third-party | Serverless GPU compute |
| OpenAI | ai, media | third-party | GPT-4o, DALL-E, Whisper |
| OpenRouter | ai | third-party | Unified API for 100+ LLMs |
| Parallel | search, ai | first-party | Web search + multi-hop research |
| Alchemy | blockchain, data | first-party | Blockchain data APIs, 100+ chains |
| Tempo RPC | blockchain | first-party | Tempo JSON-RPC access |
| Object Storage | storage | first-party | S3/R2-compatible storage |
| StableEmail | social | first-party | Pay-per-send email |
| StableEnrich | data, search, social | first-party | Research APIs (Apollo, Exa, Firecrawl, Google Maps) |
| StableTravel | data, web | first-party | Flights, hotels, activities (Amadeus, FlightAware) |
| StablePhone | ai, social | first-party | AI phone calls, phone numbers |
| StableSocial | social, data | first-party | TikTok, Instagram, Facebook, Reddit data |
| StableStudio | ai, media | first-party | AI image/video generation |
| StableUpload | storage | first-party | File hosting + static sites |
| AviationStack | data | third-party | Flight tracking |
| Code Storage | storage | third-party | Paid Git repos |
| FlightAPI | data | third-party | Flight prices/tracking |
| GoFlightLabs | data | third-party | Flight data |
| Oxylabs | web, data | third-party | Web scraping with geo-targeting |
| SpyFu | data, search | third-party | SEO/PPC competitor research |
| SerpApi | search, data | third-party | Google Flights search |
| Google Maps | data | third-party | Geocoding, directions, places |
| KicksDB | data | ? | Sneaker database |
| 2Captcha | web | ? | CAPTCHA solving |
| PostalForm | social | ? | Physical mail API |
| Prospect Butcher Co | data | ? | Business data |
| Mapbox | data | third-party | Maps and geocoding |
| RentCast | data | ? | Real estate data |
| Stability AI | ai, media | third-party | Stable Diffusion models |
| Hunter | data | ? | Email verification |
| Replicate | ai, compute | third-party | ML model hosting |
| BuiltWith | data | third-party | Technology lookup |
| Suno | ai, media | ? | AI music generation |
| OpenWeather | data | third-party | Weather data |
| Perplexity | ai, search | third-party | AI search |
| Diffbot | data, ai | third-party | Knowledge Graph |
| Mathpix | ai | third-party | Math OCR |
| Judge0 | compute | ? | Code execution |
| Browser Use | web | ? | Browser automation |
| Clado | data | ? | Contact enrichment |
| EDGAR | data | ? | SEC filings |
| EDGAR Search | data | ? | SEC filings search |
| Laso Finance | blockchain | ? | DeFi data |
| Stripe Climate | ? | ? | Carbon removal credits |

### 2.4 MPP Protocol Architecture

The MPP protocol is built on:
- **HTTP 402 Payment Required** — standardized via IETF spec
- **`WWW-Authenticate: Payment`** header — server challenges client with payment requirements
- **`Authorization: Payment`** header — client responds with payment proof
- **`Payment-Receipt`** header — server confirms payment
- **Two intents:** `charge` (per-request) and `session` (multi-request payment channel)
- **Payment methods:** Tempo (primary), Stripe (secondary), Solana (new)
- **USDC as primary currency** on Tempo chain

---

## 3. Domain/DNS APIs for Company Builder

### 3.1 Vercel Domains API (BEST OPTION)

- **Endpoint:** `POST /v1/registrar/domains/{domain}/buy`
- **Features:** Search, price check, purchase, renew, transfer
- **Pricing:** At-cost domain registration
- **Auth:** Bearer token (Vercel API token)
- **SDK:** `@vercel/sdk` package
- **Docs:** https://vercel.com/docs/domains/registrar-api
- **Verdict:** Best option for MPP proxy wrapping — clean REST API, instant setup

### 3.2 Namecheap API

- **Endpoint:** `namecheap.domains.create` (HTTP GET with query params)
- **Features:** Search, register, renew, transfer, DNS management
- **Pricing:** Competitive (.com ~$10-13)
- **Auth:** API key + whitelisted IP
- **Response:** XML format
- **Python libraries:** `PyNamecheap`, `namecheap-python`, `namecheapapi`
- **Limitations:** Requires IP whitelisting, XML responses
- **Verdict:** Good but XML response format is annoying; IP whitelist makes proxying harder

### 3.3 Cloudflare Registrar API

- **Status:** Domain PURCHASE not available via API for standard accounts
- **API only supports:** Listing domains, updating settings (auto-renew), DNS management
- **Registration:** Dashboard-only for non-Enterprise
- **Pricing:** At-cost (cheapest guaranteed)
- **Verdict:** Cannot be used for programmatic purchase unless Enterprise tier

### 3.4 Other Options

| Provider | API Available | Domain Purchase | Pricing | Notes |
|----------|--------------|-----------------|---------|-------|
| DNSimple | Yes, REST | Yes | Mid-range | Has sandbox, clean API |
| NameSilo | Yes, REST | Yes | Very cheap ($8.99 .com) | Has sandbox |
| DomainNameAPI | Yes, REST | Yes (reseller) | Wholesale | Free reseller program, no minimum |
| Domainr/Fastly | Search only | No (redirect to registrar) | Free | Domain search API only |

### 3.5 Existing MPP Domain Service

**StableDomains** was just submitted as PR #381 to the MPP service directory by @stuxf. This means someone is already building a domain purchase service for MPP. Consider:
- Partnering/integrating rather than competing
- Or building a differentiated offering (e.g., domain + DNS + hosting bundle)

---

## 4. What the MPP Ecosystem Needs

### 4.1 Missing Categories

Based on analysis of the 54+ services in the directory:

| Missing Category | Description | Why It Matters |
|-----------------|-------------|----------------|
| **Security / Compliance** | OFAC screening, fraud detection, wallet reputation | **No security services exist** — agents pay blindly |
| **Financial Intelligence** | Spending analytics, anomaly detection, policy enforcement | Zero governance layer for agent spending |
| **Identity / KYC** | Agent identity verification, attestation | Soulink (PR #379) just appeared but is basic |
| **Payments Infrastructure** | Payment orchestration, multi-chain routing, escrow | Only raw chain access exists |
| **Legal / Regulatory** | Contract generation, compliance checking | GovLaws (PR #378) is first legal service |
| **DevOps / Monitoring** | Service uptime monitoring, cost tracking | Agents can't monitor their own spending |
| **Communication** | SMS, WhatsApp, push notifications | Only email exists (StableEmail, AgentMail) |
| **E-commerce** | Product catalogs, checkout, inventory | ClawdMarket (PR #373) is first marketplace |
| **Finance / Banking** | Fiat on/off ramp, invoicing, accounting | No traditional finance integration |

### 4.2 What Would Make MPP Useful for Enterprises

1. **Spending Governance Layer** — Enterprises need to control agent budgets, set policies, get approvals
2. **Compliance / OFAC Screening** — Before any payment, check counterparty against sanctions lists
3. **Audit Trail / Reporting** — Exportable logs of all agent spending for finance teams
4. **Cost Allocation** — Tag spending to projects, departments, cost centers
5. **Anomaly Detection** — Alert when spending patterns change unexpectedly
6. **Rate Limiting / Circuit Breakers** — Prevent runaway agents from draining wallets
7. **Multi-Agent Policy** — Different policies for different agents in the same org

### 4.3 Composability Patterns Not Yet Built

1. **Pre-transaction Intelligence** — Screen every payment before it settles (OFAC, fraud, policy)
2. **Payment Middleware Chain** — Plug-in architecture: policy -> compliance -> execution -> audit
3. **Cross-Service Analytics** — Aggregate spending across all MPP services an agent uses
4. **Smart Routing** — Route to cheapest/fastest provider for equivalent services
5. **Subscription/Budget Management** — Convert per-request to budgeted spending pools
6. **Multi-Agent Coordination** — Shared budgets with per-agent sub-limits

### 4.4 What Would Paradigm Find Interesting

Paradigm (Tempo's backer, Matt Huang CEO) cares about:
1. **Protocol-level infrastructure** — Things that become standard layers
2. **Network effects** — Services that get more valuable with more users
3. **Programmable money primitives** — New financial building blocks
4. **Security infrastructure** — Essential plumbing that everyone needs

**Sardis Guard as a "financial intelligence plane" maps perfectly:**
- It's protocol-level (sits between every agent and every payment)
- Network effects (more data = better anomaly detection)
- Programmable policies (natural language -> enforcement rules)
- Security infrastructure (compliance is non-optional for enterprises)

---

## 5. Competitor Analysis

### 5.1 Locus (YC F25) — paywithlocus.com

**Status:** Active YC company, funded, shipping product

**What they do:**
- Payment infrastructure for AI agents
- USDC payments with spending limits, escrow, policy enforcement, audit trails
- Agent identities, budgets, permissions

**Founders:**
- Cole Dermott — ex-Coinbase (B2B payment products)
- Eliot — ex-Scale AI

**Open Source:**
- [agentic-commerce-protocol-demo](https://github.com/locus-technologies/agentic-commerce-protocol-demo) (39 stars) — Reference implementation of OpenAI's Agentic Commerce Protocol (ACP)
- [smart-contracts-locus](https://github.com/locus-technologies/smart-contracts-locus) — Solidity contracts

**Technical Architecture (from smart contracts):**
- `LocusSmartWallet` — ERC-4337 smart wallet with permissioned keys + virtual subwallets
- `Subwallet` — Minimal proxy for temporary token holding with disbursement deadlines
- `LocusFactory` — Wallet deployment factory
- `Paymaster` — Gas sponsorship
- Uses Solady (gas-optimized) + OpenZeppelin
- USDC-focused, ERC-4337 account abstraction

**Traction:**
- Hosted agentic payments hackathon at YC HQ
- OpenClaw skills marketplace integration
- $10 USDC beta credits for new users

**Differentiation from Sardis Guard:**
- Locus = wallet + payment infrastructure (execution layer)
- Sardis Guard = intelligence + governance layer (sits on top of wallets/payments)
- **Non-competing** — Sardis Guard could govern Locus wallets

### 5.2 OnlyGate — Kenny50/onlygate-tempo-mpp-wrapper

**Status:** Hackathon project (0 stars)

**What they claim:**
- "Zero-trust Enterprise Guardrails for Tempo MPP"
- "Tempo's Access Keys control How Much and To Whom. OnlyGate controls What and Why."
- Pre-transaction decision gateway with ABAC policy

**Architecture:**
- CLI wrapper that intercepts `tempo request` commands
- Tier 1: Auto-approve micro-transactions (<$1), log everything
- Tier 2: HITL escalation for high-value/unknown endpoints (Telegram/Slack)
- Thread suspension until human approval

**Strengths:**
- Good narrative ("Blind Agent Vulnerability")
- Zero-integration approach (CLI hijacking)
- Mobile-first HITL via Telegram

**Weaknesses:**
- CLI-only (won't work for SDK-based agents)
- No intelligence/ML — just rules and thresholds
- No sanctions screening
- No cross-agent analytics
- Hack-level implementation quality

**How Sardis Guard Wins:**
- API-native (works with any client, not just CLI)
- Machine learning anomaly detection vs. static rules
- OFAC/sanctions screening built in
- Natural language policy engine vs. hard-coded tiers
- Cross-agent analytics dashboard
- Production-grade (not a CLI wrapper hack)

### 5.3 PaySentry (Two Implementations)

**PaySentry by matverach (4 stars):**
- "OAuth but for money" — policies define limits, categories, merchants
- Architecture design phase only (no implementation)
- PostgreSQL data model with policies, agents, authorizations, event log
- 5 Architecture Decision Records written

**PaySentry by mkmkkkkk (4 stars):**
- "Missing control plane for AI agent payments"
- Supports x402, ACP, AP2, Visa TAP
- Has npm packages: `@paysentry/core`, `@paysentry/control`, `@paysentry/observe`
- Features: spending limits, circuit breakers, audit trails, rate limiting
- Has working demo (`npx paysentry-demo`)

**How Sardis Guard Wins:**
- MPP-native (not x402/ACP-focused)
- Compliance built-in (OFAC, not just spending limits)
- Intelligence layer (anomaly detection, not just rules)
- Listed in MPP service directory (distribution advantage)
- Full-stack (API + dashboard, not just npm library)

### 5.4 Other Relevant Projects

| Project | What It Is | Threat Level |
|---------|-----------|--------------|
| [beep-it/beep-sdk](https://github.com/beep-it/beep-sdk) | Agent payments on SUI (a402 protocol) | Low — different chain/protocol |
| [worldliberty/agentpay-sdk](https://github.com/worldliberty/agentpay-sdk) | Open SDK with policy enforcement | Medium — but no MPP integration |
| [AgentPayy/agentpayy-python-sdk](https://github.com/AgentPayy/agentpayy-python-sdk) | Python SDK with x402 auto-pay | Low — x402 focused |
| Soulink (PR #379) | On-chain identity for agents | Complementary — identity is an input to our scoring |

### 5.5 Competitive Landscape Summary

```
                        INTELLIGENCE
                            ^
                            |
                   Sardis Guard  (us)
                            |
                   PaySentry (mkmkkkkk)
    PROTOCOL-NATIVE --------+-------- PROTOCOL-AGNOSTIC
                   OnlyGate  |
                            |
                     Locus   |
                            v
                        EXECUTION
```

**Sardis Guard occupies a unique position:** MPP-native + intelligence-focused. No other project is in this quadrant.

---

## 6. Strategic Recommendations

### 6.1 Build This for the Hackathon

**Sardis Guard Intelligence Plane** should be:

1. **An MPP-native service** listed in the directory at `guard.sardis.sh`
2. **Pre-transaction screening:** Every payment checked against OFAC + anomaly detection + policy engine
3. **Post-transaction analytics:** Dashboard showing all agent spending across MPP services
4. **Natural language policies:** "Max $50/day on AI services, require approval above $25"

### 6.2 Key Differentiators to Emphasize

1. **Only compliance service in MPP** — no one else screens for OFAC/sanctions
2. **Intelligence, not just rules** — ML anomaly detection vs. static thresholds
3. **Natural language policies** — vs. JSON config files
4. **API-native** — works with any MPP client (not just CLI)
5. **Network effects** — more agents = better anomaly detection

### 6.3 Integration Strategy

- Use `cloudflare/mpp-proxy` pattern as base architecture
- Integrate `moov-io/watchman` (440 stars) or `opensanctions/yente` (126 stars) for OFAC screening
- Use `0xB10C/ofac-sanctioned-digital-currency-addresses` for direct wallet screening
- Build on `tempoxyz/pympp` for Python SDK integration
- Consider `SylvainCostes/fastapi-mpp` patterns for the FastAPI middleware

### 6.4 Domain Purchase API (if needed)

- **Best option:** Vercel Domains API — clean REST, instant purchase, good pricing
- **Budget option:** NameSilo API — cheapest domains, has sandbox
- **Note:** StableDomains (PR #381) is already being built — consider using it instead of building our own

### 6.5 What NOT to Build

- Don't build a wallet (Locus does this)
- Don't build a CLI wrapper (OnlyGate does this poorly)
- Don't build just spending limits (PaySentry does this)
- Don't compete on execution layer — compete on intelligence layer

### 6.6 Narrative for Judges

> "54 services in the MPP directory. Zero security services. Every agent is paying blind — no OFAC screening, no anomaly detection, no spending governance. Sardis Guard is the financial intelligence plane that makes MPP enterprise-ready. If MPP is Visa's network, Sardis Guard is Visa's fraud detection."

---

## Appendix: Data Sources

- GitHub API (gh CLI) — repo searches, org listings, PR analysis
- MPP Service Directory: `tempoxyz/mpp/schemas/services.ts`
- Web searches for competitor intelligence
- Direct README analysis of 15+ repositories
- PR analysis of recent submissions to tempoxyz/mpp
