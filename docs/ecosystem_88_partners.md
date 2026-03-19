# MPP Ecosystem: 54 Services x Sardis Guard Analysis

> Research date: 2026-03-19
> Source: `tempo wallet -t services` (live directory query)
> Context: The Synthesis Hackathon at Paradigm, March 19-22, 2026

**Note:** The directory currently lists **54 services** (not 88 -- the "88" figure likely counted individual endpoints). This document covers all 54 with full Sardis Guard analysis.

---

## Table of Contents

1. [Full Categorized Service List](#1-full-categorized-service-list)
2. [Sardis Guard Relevance Assessment](#2-sardis-guard-relevance-assessment)
3. [Top 10 Integration Opportunities](#3-top-10-integration-opportunities)
4. [Multi-Service Compositions](#4-multi-service-compositions)
5. [Recommended Compositions per Hackathon Session](#5-recommended-compositions-per-hackathon-session)
6. [PR #383 Update Recommendations](#6-pr-383-update-recommendations)
7. [Hosting Topology (Who Runs What)](#7-hosting-topology-who-runs-what)

---

## 1. Full Categorized Service List

### 1.1 AI / LLM Services (8)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 1 | Anthropic (Claude) | `anthropic` | 2 | Per-model token pricing | HIGH -- token spend can explode; budget caps essential |
| 2 | OpenAI (GPT-4o, DALL-E, Whisper) | `openai` | 6 | Per-model token pricing | HIGH -- most expensive AI service; anomaly detection critical |
| 3 | Google Gemini (Veo, Imagen) | `gemini` | 10 | Per-model pricing | HIGH -- video generation is costly |
| 4 | OpenRouter (100+ LLMs) | `openrouter` | 1 | Per-model routing | HIGH -- unified gateway means Guard sees all LLM spend |
| 5 | Perplexity (Sonar) | `perplexity` | 4 | Per-request | MEDIUM -- search + chat, moderate cost |
| 6 | Replicate (open-source models) | `replicate` | 4 | Per-model inference | HIGH -- GPU costs vary wildly by model |
| 7 | Mathpix (math OCR) | `mathpix` | 2 | Per-request | LOW -- niche, low cost |
| 8 | Stability AI (SD, 3D, audio) | `stability-ai` | 23 | Per-generation | MEDIUM -- 23 endpoints, many generation types |

### 1.2 Media Generation Services (3)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 9 | fal.ai (Flux, SD, Grok, video) | `fal` | 16 | Per-generation | HIGH -- 600+ models, video gen is expensive |
| 10 | StableStudio (Nano Banana, Sora, Veo) | `stablestudio` | 28 | Per-generation | HIGH -- Sora/Veo video = high cost per generation |
| 11 | Suno (AI music) | `suno` | 5 | Per-song | MEDIUM -- creative output, moderate cost |

### 1.3 Search & Research Services (4)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 12 | Exa (AI search) | `exa` | 4 | Per-request | MEDIUM -- research agent staple |
| 13 | Parallel (multi-hop research) | `parallel` | 3 | Per-task | HIGH -- multi-hop tasks can chain costs |
| 14 | SerpApi (Google Flights) | `serpapi` | 1 | Per-search | LOW -- single endpoint |
| 15 | SpyFu (SEO/PPC research) | `spyfu` | 9 | Per-request | MEDIUM -- competitor intel, 18yr data |

### 1.4 Web Scraping & Automation (6)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 16 | Browserbase (headless browser) | `browserbase` | 6 | Per-session + time | HIGH -- sessions accumulate cost over time |
| 17 | Firecrawl (scraping/crawling) | `firecrawl` | 5 | Per-request | MEDIUM -- crawl jobs can fan out |
| 18 | Oxylabs (geo-targeted scraping) | `oxylabs` | 1 | Per-request | MEDIUM -- geo-targeting adds cost |
| 19 | Browser Use (AI browser agent) | `browser-use` | 4 | Per-task | HIGH -- autonomous browser = unpredictable spend |
| 20 | 2Captcha (CAPTCHA solving) | `twocaptcha` | 2 | Per-solve | MEDIUM -- enables automation chains |
| 21 | Diffbot (extraction + KG) | `diffbot` | 12 | Per-request | MEDIUM -- KG queries can be expensive |

### 1.5 Data Enrichment & Intelligence (6)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 22 | StableEnrich (Apollo, Exa, etc.) | `stableenrich` | 27 | Per-request | HIGH -- 27 endpoints across multiple providers; cost aggregation |
| 23 | Clado (LinkedIn, people search) | `clado` | 12 | Per-request | HIGH -- deep research can chain many calls |
| 24 | Hunter (email finding/verification) | `hunter` | 8 | Per-request | MEDIUM -- lead gen, moderate cost |
| 25 | BuiltWith (tech detection) | `builtwith` | 14 | Per-request | LOW -- informational, low cost |
| 26 | EDGAR (SEC filings) | `edgar` | 3 | Per-request | LOW -- public data, low cost |
| 27 | EDGAR Search (full-text SEC search) | `edgar-search` | 1 | Per-request | LOW -- public data, low cost |

### 1.6 Social Media & Communication (4)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 28 | AgentMail (email inboxes) | `agentmail` | 83 | Per-action | MEDIUM -- many endpoints, inbox management |
| 29 | StableEmail (pay-per-send) | `stableemail` | 24 | Per-email | HIGH -- outbound email needs content policy |
| 30 | StablePhone (AI calls, numbers) | `stablephone` | 7 | Per-call/number | HIGH -- phone calls = real-world impact; policy critical |
| 31 | StableSocial (TikTok, IG, FB, Reddit) | `stablesocial` | 37 | Per-request | MEDIUM -- data scraping, moderate cost |

### 1.7 Blockchain & On-Chain Data (5)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 32 | Allium (on-chain finance) | `allium` | 15 | Per-request | HIGH -- wallet analysis feeds into Guard's risk scoring |
| 33 | Alchemy (100+ chains RPC) | `alchemy` | 3 | Per-call | HIGH -- raw RPC = can execute transactions; must govern |
| 34 | Codex (token data, 80+ networks) | `codex` | 1 | Per-query | MEDIUM -- GraphQL, data-only |
| 35 | Dune (SQL analytics) | `dune` | 3 | Per-query | MEDIUM -- SQL execution, moderate cost |
| 36 | Tempo RPC | `rpc` | 1 | $0.001/call | LOW -- infrastructure, low per-call |

### 1.8 Travel & Aviation (5)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 37 | StableTravel (flights, hotels, activities) | `stabletravel` | 68 | Per-request | CRITICAL -- booking flights/hotels = high-value transactions |
| 38 | AviationStack (flight tracking) | `aviationstack` | 11 | Per-request | LOW -- read-only data |
| 39 | FlightAPI (flight prices/tracking) | `flightapi` | 7 | Per-request | LOW -- read-only data |
| 40 | GoFlightLabs (flight data) | `goflightlabs` | 15 | Per-request | LOW -- read-only data |
| 41 | SerpApi (Google Flights) | `serpapi` | 1 | Per-search | LOW -- search only |

### 1.9 Maps & Geospatial (2)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 42 | Google Maps (full platform) | `googlemaps` | 43 | Per-request | MEDIUM -- 43 endpoints, moderate cost |
| 43 | Mapbox (geocoding, routing) | `mapbox` | 8 | Per-request | LOW -- cheaper alternative |

### 1.10 Storage & Hosting (3)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 44 | Object Storage (S3/R2) | `storage` | 5 | Per-MB | MEDIUM -- upload size = cost driver |
| 45 | StableUpload (file hosting) | `stableupload` | 7 | Per-upload tier | MEDIUM -- file size tiers |
| 46 | Code Storage (Git repos) | `codestorage` | 2 | Per-repo | LOW -- one-time cost |

### 1.11 Finance & Payments (2)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 47 | Laso Finance (virtual cards, Venmo/PayPal) | `laso` | 10 | Per-transaction | CRITICAL -- real money movement; sanctions/policy essential |
| 48 | Stripe Climate (carbon credits) | `stripe-climate` | 1 | Per-contribution | MEDIUM -- ESG spend tracking |

### 1.12 Compute & Code Execution (2)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 49 | Modal (serverless GPU) | `modal` | 4 | Per-compute | HIGH -- GPU time = expensive; runaway jobs |
| 50 | Judge0 (code execution, 70+ langs) | `judge0` | 5 | Per-execution | MEDIUM -- sandboxed, but volume matters |

### 1.13 Specialty Data (4)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 51 | RentCast (real estate data) | `rentcast` | 10 | Per-request | LOW -- informational |
| 52 | KicksDB (sneaker market data) | `kicksdb` | 29 | Per-request | LOW -- niche market data |
| 53 | OpenWeather (weather data) | `openweather` | 7 | Per-request | LOW -- utility data |
| 54 | PostalForm (print & mail letters) | `postalform` | 3 | Per-order | HIGH -- physical world action; irreversible |

### 1.14 Novelty (1)

| # | Service | ID | Endpoints | Pricing Model | Guard Relevance |
|---|---------|----|-----------:|--------------|-----------------|
| 55 | Prospect Butcher (sandwich ordering) | `prospect-butcher` | 1 | Per-sandwich | HIGH (for demo!) -- physical purchase, irreversible |

---

## 2. Sardis Guard Relevance Assessment

### Tier 1: CRITICAL -- Guard is Essential (5 services)

These services involve **real money movement** or **irreversible physical actions**. An unguarded agent using these is genuinely dangerous.

| Service | Why Guard is Critical |
|---------|----------------------|
| **Laso Finance** | Virtual debit cards, Venmo/PayPal payments. Real money leaves the system. OFAC screening, spend limits, and fraud detection are non-negotiable. |
| **StableTravel** | Books flights and hotels with real money. A rogue agent could book $5,000 in flights. Mandate governance (approved destinations, price caps) is essential. |
| **Alchemy RPC** | Raw JSON-RPC access to 100+ chains. An agent could submit arbitrary transactions. Guard must validate transaction intent before execution. |
| **PostalForm** | Prints and mails physical letters. Irreversible. Content policy + recipient screening needed. |
| **StablePhone** | Makes real AI phone calls. Irreversible voice interaction. Must validate call recipients, content policies, and per-call budgets. |

### Tier 2: HIGH -- Guard Adds Major Value (14 services)

These services have **high cost variance**, **unpredictable spend patterns**, or **sensitive data access**.

| Service | Why Guard Matters |
|---------|-------------------|
| **OpenAI** | GPT-4o/o1 token costs vary 10-100x by model. A single long conversation can cost $5+. |
| **Anthropic** | Opus is 15x more expensive than Haiku. Model selection policy matters. |
| **fal.ai** | 600+ models; video generation can be 50x more expensive than image gen. |
| **StableStudio** | Sora 2 Pro and Veo 3.1 are the most expensive generation services in MPP. |
| **Replicate** | Open-source model costs are completely unpredictable per model. |
| **Google Gemini** | Veo video generation can cost $5+ per clip. |
| **OpenRouter** | Routes to 100+ models; cost depends on which model agent selects. |
| **Browserbase** | Sessions accumulate cost over time; an agent could leave sessions running. |
| **Browser Use** | Fully autonomous browser agent; unpredictable number of actions/cost. |
| **StableEnrich** | 27 endpoints across multiple providers; easy for bulk enrichment to explode cost. |
| **Clado** | Deep research jobs can chain many API calls; bulk contact enrichment is expensive. |
| **StableEmail** | Outbound email at scale could create spam/abuse liability. Content governance needed. |
| **Modal** | GPU compute can cost $2-4/hour; a long training job can drain a wallet. |
| **Parallel** | Multi-hop research tasks chain multiple sub-queries, each costing money. |
| **Allium** | On-chain finance data can feed into Guard's own risk scoring (complementary). |

### Tier 3: MEDIUM -- Guard Adds Value (15 services)

Standard API services where budget tracking and anomaly detection are useful but not critical.

AgentMail, Firecrawl, Oxylabs, Diffbot, SpyFu, Suno, Stability AI, 2Captcha, Google Maps, StableSocial, Object Storage, StableUpload, Judge0, Dune, Stripe Climate, Mathpix, Codex, Hunter, Perplexity (when used for search only)

### Tier 4: LOW -- Guard is Nice-to-Have (16 services)

Read-only data services or low-cost utilities where Guard provides audit trail value but limited policy enforcement value.

AviationStack, FlightAPI, GoFlightLabs, SerpApi, Mapbox, Code Storage, RentCast, KicksDB, OpenWeather, Tempo RPC, EDGAR, EDGAR Search, BuiltWith, Prospect Butcher (low cost but fun for demos)

---

## 3. Top 10 Integration Opportunities

### #1: Laso Finance + Guard = Governed Virtual Cards

**What:** Sardis Guard evaluates every Laso Finance action (card provisioning, Venmo/PayPal sends) through the 8-gate pipeline before execution.

**Why it matters:** This is the most direct "Sardis Guard prevents real financial harm" demo. An agent trying to send $500 via Venmo to a sanctioned entity gets blocked.

**Composition:**
```
Agent -> Guard /evaluate/v2 -> Laso /send-payment -> Guard /audit
```

**Demo value:** 10/10 -- this is the money shot for investors.

---

### #2: StableTravel + Guard = Controlled Travel Booking

**What:** Agent books flights/hotels with spending mandates: "Book flights under $300, only domestic US, no first class."

**Why it matters:** 68 endpoints, $100-5000 transactions. The highest dollar-value service in MPP. Policy enforcement here is obvious.

**Composition:**
```
Agent -> Guard /evaluate (policy: domestic, economy, <$300)
     -> StableTravel /flights/search
     -> Guard /evaluate (verify selected flight matches policy)
     -> StableTravel /flights/book
     -> Guard /audit (log booking confirmation)
```

**Demo value:** 9/10 -- enterprise travel policy is immediately understandable.

---

### #3: OpenAI/Anthropic/OpenRouter + Guard = LLM Cost Governance

**What:** Guard enforces model selection policies and per-conversation budget caps across all LLM providers.

**Why it matters:** Most agent frameworks use LLMs as their reasoning engine. A policy like "use Haiku for routine tasks, Sonnet for complex tasks, never use Opus without approval" could save 10-50x on LLM costs.

**Composition:**
```
Agent -> Guard /evaluate (check model selection + budget)
     -> OpenRouter /chat/completions
     -> Guard /spend (decrement conversation budget)
```

**Demo value:** 8/10 -- every AI company has this problem.

---

### #4: Multi-Provider Research Pipeline + Guard Budget Envelope

**What:** Research agent uses Perplexity + StableEnrich + Browserbase + Exa in a chain, with Guard enforcing a total budget envelope across all services.

**Why it matters:** Cross-service budget tracking is impossible without a governance layer. Agent could spend $0.05 on Perplexity, $0.50 on StableEnrich enrichment, $0.30 on Browserbase sessions, and blow past its $0.50 budget because no single service knows about the others.

**Composition:**
```
Agent -> Guard /mandate/create ($0.50 research budget)
     -> Guard /evaluate -> Perplexity /search ($0.05)
     -> Guard /evaluate -> StableEnrich /apollo/people-search ($0.10)
     -> Guard /evaluate -> Browserbase /session/create ($0.15)
     -> Guard /evaluate -> Exa /search ($0.05)
     -> Guard: remaining budget $0.15
     -> Guard /evaluate -> StableEnrich /apollo/people-enrich ($0.20)
     -> Guard: DENIED -- would exceed budget
```

**Demo value:** 9/10 -- shows the cross-service problem that only Guard solves.

---

### #5: Alchemy RPC + Guard = Transaction Firewall

**What:** Guard sits in front of Alchemy's JSON-RPC endpoint and validates transaction intent before allowing `eth_sendRawTransaction` calls.

**Why it matters:** Raw RPC access to 100+ blockchains is the most dangerous capability in MPP. An agent with RPC access could drain a wallet, interact with malicious contracts, or send funds to sanctioned addresses.

**Composition:**
```
Agent -> Guard /evaluate/v2 (parse tx, check recipient against OFAC, validate amount vs. mandate)
     -> IF APPROVED: Alchemy /eth_sendRawTransaction
     -> Guard /audit (log tx hash, chain, amount)
```

**Demo value:** 8/10 -- technically impressive; shows Guard can parse on-chain transactions.

---

### #6: Creative Pipeline + Guard = Production Asset Governance

**What:** Agent generates images (fal.ai/StableStudio), uploads them (StableUpload), and emails them (StableEmail), with Guard enforcing content budgets and preventing overspend on expensive video generation.

**Why it matters:** Video generation (Sora, Veo) costs 50-100x more than image generation. Without Guard, an agent might choose Sora when FLUX would suffice.

**Composition:**
```
Agent -> Guard /evaluate (policy: images only, no video, max $0.50)
     -> fal.ai /flux/dev (generate logo, $0.05)
     -> Guard /evaluate
     -> StableUpload /upload (host image, $0.02)
     -> Guard /evaluate
     -> StableEmail /send (email with image link, $0.01)
     -> Agent tries: fal.ai /minimax/video-01 ($0.50)
     -> Guard: DENIED -- video generation not in mandate
```

**Demo value:** 7/10 -- visual, fun, shows content-type policy.

---

### #7: StablePhone + Guard = Call Governance

**What:** Guard screens phone call recipients against blocklists and enforces per-call budget limits before allowing AI phone calls.

**Why it matters:** AI phone calls have real-world consequences. An unguarded agent could call anyone, say anything, and spend unlimited money. This is a liability nightmare.

**Composition:**
```
Agent -> Guard /evaluate (screen recipient phone number, check call budget)
     -> IF APPROVED: StablePhone /call
     -> Guard /audit (log call ID, duration, cost)
```

**Demo value:** 7/10 -- dramatic; "what if an AI called a senator?"

---

### #8: EDGAR + Allium + Perplexity + Guard = Financial Due Diligence Agent

**What:** Agent performs financial due diligence on a company using SEC filings (EDGAR), on-chain wallet analysis (Allium), and web research (Perplexity), with Guard enforcing research scope and budget.

**Why it matters:** Financial research agents are a major use case. Guard ensures the agent stays within scope (approved companies, approved data sources) and budget.

**Composition:**
```
Agent -> Guard /mandate/create ("research ACME Corp financials, max $1")
     -> EDGAR /company-facts (XBRL data, $0.01)
     -> Allium /wallet/balances (on-chain treasury, $0.01)
     -> Perplexity /search ("ACME Corp financial health", $0.05)
     -> Guard: all within scope and budget
```

**Demo value:** 8/10 -- institutional finance use case.

---

### #9: Clado + Hunter + AgentMail + Guard = Governed Outreach Agent

**What:** Agent finds leads (Clado), verifies emails (Hunter), and sends outreach (AgentMail), with Guard enforcing anti-spam policies and recipient screening.

**Why it matters:** Automated outreach without governance is spam. Guard enforces: max 50 emails/day, approved templates only, no outreach to competitors, CAN-SPAM compliance.

**Composition:**
```
Agent -> Guard /mandate/delegate (outreach agent, $0.50 budget, 50 email limit)
     -> Clado /search (find prospects)
     -> Hunter /email-verifier (verify addresses)
     -> AgentMail /messages/send (send outreach)
     -> Guard: enforces daily limit, template compliance
```

**Demo value:** 7/10 -- sales teams immediately understand this.

---

### #10: PostalForm + Guard = Physical Mail Governance

**What:** Guard screens postal mail recipients and content before allowing PostalForm to print and mail physical letters.

**Why it matters:** Physical mail is completely irreversible. An agent could send threatening letters, impersonate someone, or mail to restricted addresses. Guard must validate content and recipients.

**Composition:**
```
Agent -> Guard /evaluate (screen recipient, validate content policy)
     -> PostalForm /orders/validate (get quote)
     -> Guard /evaluate (approve quoted amount)
     -> PostalForm /orders (create order)
```

**Demo value:** 8/10 -- "physical world consequences" is very compelling.

---

## 4. Multi-Service Compositions

### 4.1 "Company Builder" Flow (Session 2)

The canonical demo: an AI agent "starts a company" using real MPP services.

```
Step 1: Market Research
  Perplexity /search ("AI payments market size") ............... $0.05
  StableEnrich /exa/search ("competitor landscape") ............ $0.007
  Browserbase /fetch (scrape competitor pricing page) .......... $0.01

Step 2: Brand Creation
  fal.ai /flux/dev (generate company logo) ..................... $0.05
  StableUpload /upload (host logo) ............................. $0.02

Step 3: Communications Setup
  AgentMail /inboxes (create company email) .................... $0.01
  StableEmail /send (send intro email to prospect) ............. $0.01

Step 4: Financial Setup
  Laso Finance /get-card (provision virtual debit card) ........ $?
  Stripe Climate /contribute (carbon offset) ................... $0.01

Step 5: Lead Generation
  StableEnrich /apollo/people-search (find prospects) .......... $0.01
  Hunter /email-verifier (verify prospect emails) .............. $0.01

Step 6: On-Chain Verification
  Allium /wallet/balances (check treasury wallet) .............. $0.01

Guard gates: 12 transactions, 8 services, ~$0.20 total
Guard catches: off-scope purchases, budget overruns, sanctioned entities
```

### 4.2 "Research Swarm" Flow (Session 3)

5 agents with different mandates, all researching the same topic, Guard enforcing boundaries.

```
Agent Alpha (Researcher) -- $0.15 budget
  Perplexity /search + /chat
  Exa /search + /findSimilar
  Firecrawl /scrape

Agent Beta (Data Analyst) -- $0.10 budget
  Dune /sql/execute
  Allium /wallet/pnl
  Codex /graphql

Agent Gamma (Competitive Intel) -- $0.10 budget
  StableEnrich /apollo/org-search
  BuiltWith /domain
  SpyFu /domain_stats

Agent Delta (Financial Analyst) -- $0.08 budget
  EDGAR /company-facts
  EDGAR Search /search

Agent Epsilon (ROGUE -- will be caught) -- $0.05 budget
  Tries: StableTravel /flights/book -- DENIED (not in mandate)
  Tries: Laso /send-payment -- DENIED (not in mandate)
  Tries: sanctioned address lookup -- FREEZE_TREE

Guard dashboard: real-time spending across all 5 agents
Guard action: freezes Epsilon's mandate, other agents continue
```

### 4.3 "Pay-per-Token LLM" Flow (Session 3 alternative)

Guard enforces token-level spending on streamed LLM conversations.

```
User sets mandate: "Max $0.50 for this conversation"

Each streamed token:
  Guard /evaluate (check remaining budget) -> $0.0001/token
  OpenRouter /chat/completions (stream response)
  Guard /spend (decrement budget)

At $0.48 spent:
  Guard: WARNING -- 96% budget consumed
  Agent receives low-budget signal

At $0.50:
  Guard: DENIED -- budget exhausted
  Conversation ends gracefully with summary
```

### 4.4 "Agent Hiring Agent" Flow (Session 3 alternative)

Demonstrates mandate delegation -- Agent A hires Agent B for a sub-task.

```
Agent A (Project Manager):
  Guard /mandate/create (root: "Build landing page, $1.00")
  Guard /mandate/delegate (child: "Design assets, $0.30" -> Agent B)
  Guard /mandate/delegate (child: "Write copy, $0.20" -> Agent C)

Agent B (Designer):
  fal.ai /flux/dev (generate hero image) ..................... $0.05
  StableStudio /nano-banana (generate illustrations) ......... $0.03
  StableUpload /upload (host assets) ......................... $0.04

Agent C (Copywriter):
  Perplexity /chat (research topic) .......................... $0.05
  OpenRouter /chat/completions (write copy) .................. $0.03

Agent A reviews, sub-mandates expire automatically.
Guard: shows delegation tree with per-agent spend visualization.
```

---

## 5. Recommended Compositions per Hackathon Session

### Session 2: Agent Company Builder

**Primary services (already planned):**
- Perplexity, StableEnrich, Browserbase, fal.ai, AgentMail, StableEmail, Laso Finance, Stripe Climate, Allium

**Add these for richer demo:**
- **Hunter** -- verify prospect emails before sending (adds realism)
- **StableUpload** -- host the generated logo (completes the asset pipeline)
- **OpenRouter** -- use for "business plan generation" step (shows LLM governance)

**Total services in demo:** 12
**Estimated cost:** $0.20-0.30
**Guard gates:** ~15 evaluate calls

### Session 3: Research Swarm OR Pay-per-Token

**If Research Swarm:**
- Perplexity, Exa, Firecrawl, Dune, Allium, Codex, StableEnrich, BuiltWith, SpyFu, EDGAR
- **10 services, 5 agents, ~$0.15**
- Best for: "governance at scale" narrative

**If Pay-per-Token:**
- OpenRouter (or Anthropic/OpenAI directly)
- **1 service, but deeply instrumented with Guard**
- Best for: "micropayment governance" narrative
- More technically novel but less visually impressive

**Recommendation:** Research Swarm (Session 3 option C from SESSIONS.md). It uses more services, shows cross-agent governance, and the "rogue agent gets frozen" moment is dramatic.

---

## 6. PR #383 Update Recommendations

### Current Status
- **State:** OPEN
- **Title:** "feat(services): add Sardis Guard intelligence plane"
- **URL:** https://github.com/tempoxyz/mpp/pull/383

### What Needs Updating

**The PR is solid as-is for the hackathon.** However, after the hackathon, consider these improvements:

1. **Add composition examples** -- Show how Guard composes with other MPP services (the multi-service flows above would make excellent documentation in the PR description or service metadata).

2. **Add `llmsTxt` URL** -- The service entry should include `llmsTxt: "https://guard.sardis.sh/llms.txt"` so AI coding agents can discover Guard's capabilities. Many top services (Exa, fal.ai, Firecrawl, StableUpload, etc.) have this.

3. **Add `openapi` or `apiReference` URL** -- Currently null. An OpenAPI spec would make Guard auto-discoverable by agent frameworks.

4. **Consider renaming to differentiate** -- Current name "Sardis Guard intelligence plane" is descriptive but long. The directory uses short names (e.g., "Exa", "Modal", "Allium"). Consider just "Sardis Guard" or "Sardis" for the `name` field.

5. **Verify endpoint pricing** -- The PR lists `$0.001` per evaluate and `$0.0005` per simulate. These are very cheap (good for adoption) but verify they're sustainable for production.

6. **No code changes needed right now** -- The PR content is appropriate for the hackathon submission. Post-hackathon, update with production URLs.

---

## 7. Hosting Topology (Who Runs What)

An important observation: the 54 services are hosted by different infrastructure providers, revealing the ecosystem's structure.

### Tempo-Hosted (First-Party Proxies)
Services at `*.mpp.tempo.xyz` -- Tempo wraps third-party APIs with MPP payment gating:
- `anthropic.mpp.tempo.xyz` -- Anthropic
- `exa.mpp.tempo.xyz` -- Exa
- `fal.mpp.tempo.xyz` -- fal.ai
- `firecrawl.mpp.tempo.xyz` -- Firecrawl
- `gemini.mpp.tempo.xyz` -- Google Gemini
- `modal.mpp.tempo.xyz` -- Modal
- `openai.mpp.tempo.xyz` -- OpenAI
- `openrouter.mpp.tempo.xyz` -- OpenRouter
- `rpc.mpp.tempo.xyz` -- Tempo RPC
- `storage.mpp.tempo.xyz` -- Object Storage

### Stable* Suite (Independent Developer -- "stuxf")
Services at `stable*.dev` -- A single prolific developer building MPP-native services:
- `stableemail.dev` -- Email
- `stableenrich.dev` -- Data enrichment (27 endpoints!)
- `stabletravel.dev` -- Travel (68 endpoints!)
- `stablephone.dev` -- Phone calls
- `stablesocial.dev` -- Social media data
- `stablestudio.dev` -- AI generation (28 endpoints!)
- `stableupload.dev` -- File hosting

**Implication for Sardis:** The Stable* suite is the most prolific service builder in MPP. Partnering with stuxf or building Guard specifically to govern Stable* services would cover 7 services and 200+ endpoints.

### Locus-Hosted (YC F25 Competitor)
Services at `*.mpp.paywithlocus.com` -- Locus wraps third-party APIs:
- Mapbox, RentCast, Stability AI, Hunter, Replicate, BuiltWith, Suno, OpenWeather, Perplexity, Diffbot, Mathpix, Judge0, Browser Use, Clado, EDGAR, EDGAR Search, Laso Finance, Stripe Climate

**18 services hosted by Locus!** This makes Locus the largest service aggregator in MPP by count (vs. Tempo's 10). Notable because Locus is a YC-backed competitor in the "agent payments" space.

**Implication for Sardis:** Locus controls the hosting for 18/54 services (33%). If Sardis Guard sits in front of Locus-hosted services, it creates an interesting dynamic -- Guard governs spending that flows through a competitor's infrastructure.

### First-Party MPP Services
Services that run their own MPP endpoints:
- `mpp.api.agentmail.to` -- AgentMail
- `agents.allium.so` -- Allium
- `mpp.browserbase.com` -- Browserbase
- `graph.codex.io` -- Codex
- `api.dune.com` -- Dune (custom integration)
- `parallelmpp.dev` -- Parallel
- `mpp.alchemy.com` -- Alchemy
- `postalform.com` -- PostalForm
- `agents.prospectbutcher.shop` -- Prospect Butcher
- `climate.stripe.dev` -- Stripe Climate

### Third-Party Proxies (via Tempo proxy infrastructure)
Services at `*.mpp.tempo.xyz`:
- AviationStack, Code Storage, FlightAPI, GoFlightLabs, Oxylabs, SpyFu, SerpApi, Google Maps, KicksDB, 2Captcha

---

## Key Takeaways

1. **54 services, not 88.** The "88" number likely referred to the early partner list or counted endpoints. The live directory has 54 services with 700+ total endpoints.

2. **Guard is essential for 5 services** (Laso Finance, StableTravel, Alchemy RPC, PostalForm, StablePhone) and highly valuable for 14 more. That is 19 out of 54 services (35%) where Guard adds clear, immediate value.

3. **Cross-service budget tracking is Guard's killer feature.** No single MPP service knows about spending at other services. Only Guard can enforce a total budget across Perplexity + StableEnrich + Browserbase + fal.ai.

4. **The Stable* suite (7 services, 200+ endpoints) is the single best integration target** for demonstrating Guard's breadth. One partnership covers the most prolific builder in the ecosystem.

5. **Locus hosts 33% of all services.** This creates both an opportunity (Guard governs spending that flows through Locus) and a risk (Locus could build their own governance layer).

6. **The Company Builder demo (Session 2) should use 12 services** to maximize the "composability" narrative. The Research Swarm (Session 3) should use 10 services with 5 agents.

7. **PR #383 is good as-is** for the hackathon. Post-hackathon, add `llmsTxt`, `openapi`, and composition examples.
