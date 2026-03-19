# MPP Hackathon — 3 Session Plan

## Session 1: Sardis Guard Intelligence Plane (SUPPLY SIDE) ✅ DONE

**What:** MPP-native financial intelligence platform for AI agent payments.
**Status:** Çalışıyor, 17 modül, 7000+ satır, 8-gate security pipeline.

Built:
- 8-gate security pipeline (dedup, governance, sanctions, ML risk, policy, action, spend, audit)
- 6 security layers (T1-T4, T9, AML) — all tested
- IsolationForest + Markov chain + cross-agent correlation
- OFAC sanctions screening (real Treasury data)
- Mandate delegation tree with freeze propagation
- Hash-chained audit trail (SHA-256)
- Session-hash anti-relay (T3) + in-flight limit (T4)
- React dashboard (dark theme, SSE, risk timeline)
- CLI (7 commands), swarm orchestrator (benign + attack)

---

## Session 2: Agent Company Builder (CONSUMER SIDE)

**What:** An AI agent that "starts a company" using real MPP services, with Sardis Guard enforcing every payment.

**Pitch:** "We gave an AI agent $5 and said 'start a company.' Watch what happens — and watch what Sardis catches."

### Demo Flow:

1. **Create root mandate** — "Research AI payments market, max $5 budget"
2. **Delegate child mandates:**
   - `agent_researcher` — Perplexity + StableEnrich ($2 budget)
   - `agent_designer` — fal.ai image gen ($1 budget)
   - `agent_comms` — AgentMail + StableEmail ($1 budget)
   - `agent_finance` — Laso Finance + Stripe Climate ($1 budget)

3. **Company building steps (real MPP calls):**
   | Step | Agent | Service | Action | Cost |
   |------|-------|---------|--------|------|
   | 1 | researcher | Perplexity | Market research: "AI agent payments TAM" | ~$0.05 |
   | 2 | researcher | StableEnrich/Exa | Competitor analysis | ~$0.007 |
   | 3 | researcher | Browserbase | Scrape competitor pricing | ~$0.01 |
   | 4 | designer | fal.ai | Generate company logo (FLUX) | ~$0.05 |
   | 5 | comms | AgentMail | Create company email inbox | ~$0.01 |
   | 6 | comms | StableEmail | Send intro email to potential customer | ~$0.01 |
   | 7 | finance | Laso Finance | Get virtual debit card | ~$? |
   | 8 | finance | Stripe Climate | Carbon offset ($0.01) | ~$0.01 |
   | 9 | researcher | StableEnrich/Apollo | Find leads | ~$0.01 |
   | 10 | researcher | Allium | Check wallet activity | ~$0.01 |

4. **Attack/drift detection:**
   - Agent tries to buy something off-scope → DENIED
   - Agent tries to exceed budget → DENIED
   - Agent sends to sanctioned address → FREEZE_TREE
   - Show mandate tree: 3 agents green, 1 frozen

5. **Evidence pack:**
   - Download compliance report
   - Show hash chain integrity
   - Show mandate delegation tree with spend visualization

### Tech:
- Python script orchestrating real MPP calls
- Each call goes through Guard evaluate/v2
- Dashboard shows real-time activity
- CLI shows colored output

### Budget: ~$0.20-0.50 total

---

## Session 3: Unhinged Composition (COMPOSE + FUN)

**What:** Creative, wild, entertaining demos that compose MPP services in unexpected ways.

### Idea Pool:

**A. Agent Poker / Agent Economy** 🎰
- 3-4 agents with different budgets and mandates
- Each agent buys "intel" on the others via Perplexity/StableEnrich
- Agents bid on shared resources (compute, data)
- Sardis Guard enforces rules: no collusion, budget limits, sanctions
- Dashboard shows real-time spending war
- *Vibe: "AI agents playing economic games with real money"*

**B. MPP Service Chain Race** 🏁
- Build the longest possible service chain
- Agent → Guard → Perplexity → Guard → StableEnrich → Guard → Browserbase → Guard → fal.ai → Guard → AgentMail
- Each hop is a real MPP payment
- Race: which chain completes fastest?
- Dashboard shows the chain progressing
- *Vibe: "How many services can you chain before you run out of budget?"*

**C. AI Research Swarm with Live Dashboard** 🧠
- 5 agents, each with different roles
- All researching "How will AI agents change payments?"
- Real-time dashboard shows spending, discoveries, risk scores
- One agent "goes rogue" — starts researching gambling/dark markets
- Sardis catches it, freezes mandate, other agents continue
- *Vibe: "The future of autonomous research with financial guardrails"*

**D. Pay-per-Token LLM Through Guard** 💬
- Use MPP streamed payments (SSE sessions)
- Each token from Claude/GPT costs micropayment
- Sardis Guard monitors token spend in real-time
- Budget cap: "max $1 for this conversation"
- Show conversation being cut off when budget exhausted
- *Vibe: "What if every AI thought cost real money?"*

**E. Agent Hiring Agent** 🤝
- Agent A has a task but not the right mandate for some services
- Agent A "hires" Agent B by delegating a sub-mandate
- Agent B does the work, spends within delegate budget
- Agent A reviews results, sub-mandate expires
- *Vibe: "AI agents with delegation of financial authority"*

**F. Sardis Guard as MCP Tool** 🔧
- Sardis Guard as a Claude Desktop / Cursor tool
- User says "Research competitors" in Claude
- Claude calls Guard MCP tool → gets mandate → uses MPP services
- Real-time spending visible in dashboard
- *Vibe: "Every Claude conversation can spend real money — safely"*

### Recommended Pick: C (Research Swarm) or D (Pay-per-Token)
- C is most impressive for Paradigm (shows governance at scale)
- D is most technically novel (MPP streamed payments + Guard)
- Both are achievable in 2 hours

---

## Budget Plan

| Session | Est. Cost | What |
|---------|-----------|------|
| Session 1 | $0.52 spent | Intelligence Plane (done) |
| Session 2 | ~$0.20 | Company Builder |
| Session 3 | ~$0.15 | Unhinged Composition |
| Buffer | ~$0.10 | Retries, debugging |
| **Total** | **~$0.97** | **Stays under $1 USDC** |

Current balance: ~$0.48 USDC → enough for Sessions 2+3 if careful.
