# Sardis Guard Intelligence Plane

**Financial intelligence and governance for AI agent payments via MPP.**

Built at the [Tempo MPP Hackathon](https://hackathon.tempo.xyz) (March 19, 2026).

## What is this?

Every AI agent in the MPP ecosystem can spend money. But nobody asks: **should this agent be allowed to spend?**

Sardis Guard is the answer. It sits between any AI agent and any MPP service, enforcing an 8-gate security pipeline before every payment clears:

```
AI Agent → Sardis Guard ($0.001/eval) → 8 Security Gates → ALLOW / DENY
                                                              ↓
                                                      MPP Service
                                                  (Perplexity, Alchemy, etc.)
```

## The 8-Gate Security Pipeline

| Gate | What | How |
|------|------|-----|
| **0. Dedup** | Replay/double-spend prevention | Idempotency keys, monotonic nonces, request fingerprinting |
| **1. Governance** | Mandate chain validation | 10-point check: budget, scope, delegation depth, parent chain |
| **2. Sanctions** | OFAC/AML screening | Real Treasury SDN list, address exact match, entity fuzzy match |
| **3. Risk** | ML anomaly detection | IsolationForest, Markov transition surprisal, cross-agent correlation |
| **4. Policy** | Spending rules | 12-check pipeline: limits, merchants, categories, chains, cooldowns |
| **5. Action** | Composite scoring | Thresholds: ALLOW < 0.45 < FLAG < 0.70 < HOLD < 0.85 < FREEZE |
| **6. Spend** | Budget enforcement | Hierarchical spend propagation through mandate delegation tree |
| **7. Audit** | Evidence trail | SHA-256 hash-chained append-only log, evidence pack generation |

Plus **session-hash anti-relay** (T3) and **in-flight limit anti-shadow-lock** (T4) from the [Sardis Protocol Spec](https://sardis.sh).

## Quick Start

```bash
# Install
git clone https://github.com/EfeDurmaz16/sardis-guard-mpp
cd sardis-guard-mpp
uv venv && uv pip install "pympp[tempo,server]" fastapi uvicorn scikit-learn numpy duckdb

# Run
source .venv/bin/activate
uvicorn src.server:app --host 0.0.0.0 --port 8402

# Test (free endpoint)
curl http://localhost:8402/health

# Test (MPP-gated — requires tempo wallet)
tempo request -t -X POST --json '{"amount":"1.50","merchant":"perplexity.ai"}' \
  http://localhost:8402/evaluate
```

## Live Demo Results

**Benign swarm** (6 real MPP calls):
```
researcher → StableEnrich/Exa: "AI agent payments market" → ALLOWED
researcher → StableEnrich/Exa: "MPP ecosystem"            → ALLOWED
scraper    → Browserbase: "Tempo blockchain"               → ALLOWED
analyst    → Tempo RPC: wallet balance                     → ALLOWED
analyst    → Tempo RPC: block number                       → ALLOWED
researcher → StableEnrich/Exa: "competitor wallets"        → ALLOWED
```

**Attack scenario** (8 steps, 3 caught):
```
burst calls (4x rapid)  → 3 allowed, 1 DENIED (budget)
novel service (darkweb)  → DENIED (service not in mandate)
sanctions (Tornado Cash) → balance check allowed (not a payment)
budget violation ($5)    → DENIED (exceeds $0.10 per-tx limit)
```

**Replay protection**:
```
Call 1: idempotency_key=test123, nonce=1 → ALLOW
Call 2: same key, same nonce             → 409 REJECTED (duplicate)
Call 3: nonce=2                          → ALLOW
Call 4: nonce=1 (backwards!)             → REJECTED (replay attack)
```

## Architecture

```
sardis-guard-mpp/
├── src/
│   ├── server.py              # FastAPI + MPP server (9 endpoints)
│   ├── routes_v2.py           # V2: mandates, screening, dashboard, reports (13 endpoints)
│   ├── types.py               # 4 canonical types
│   ├── policy.py              # 12-check policy engine
│   ├── mandates/              # Delegation tree, scope narrowing, freeze/resume
│   ├── governance/            # 10-point evaluation, HMAC signatures
│   ├── risk/                  # IsolationForest + Markov + cross-agent correlation
│   ├── compliance/            # OFAC sanctions, address risk scoring
│   ├── security/              # Dedup, session binding (T3), in-flight limit (T4)
│   ├── storage/               # SQLite WAL + DuckDB analytics, hash chain
│   ├── services/              # MPP service wrappers (Perplexity, StableEnrich, Browserbase, Tempo RPC)
│   ├── swarm/                 # Multi-agent orchestrator with benign + attack scenarios
│   └── intel/                 # Merchant + onchain intelligence
├── dashboard/                 # React + Vite + Tailwind dashboard
├── docs/                      # Protocol summary, MPP research
└── CLAUDE.md                  # Full context (554 lines)
```

## Key Numbers

- **17 Python modules**, all import cleanly
- **16,000+ lines** of working code
- **22 API endpoints** (9 v1 + 13 v2)
- **8 security gates** in the evaluation pipeline
- **6 threat mitigations** (T1-T4, T9, AML)
- **12 ML features** for anomaly detection
- **19 sanctioned addresses** from real OFAC SDN list
- **14 real MPP payments** processed during development

## Sardis Protocol

This hackathon project is a focused demo of the [Sardis Protocol](https://sardis.sh) — the Internet's Financial Operating System for Machine Commerce. The full protocol spec covers UTXO funding, zero-knowledge proofs, escrow/arbitration, FX bridging, recurring mandate trees, and a 22-state payment lifecycle.

## Built With

- [pympp](https://pypi.org/project/pympp/) — Machine Payments Protocol SDK
- [Tempo](https://tempo.xyz) — Stablecoin blockchain (chain 4217)
- [FastAPI](https://fastapi.tiangolo.com/) — Python web framework
- [scikit-learn](https://scikit-learn.org/) — IsolationForest anomaly detection
- [DuckDB](https://duckdb.org/) — Analytics engine
- [React](https://react.dev/) + [Vite](https://vite.dev/) + [Tailwind](https://tailwindcss.com/) — Dashboard

## License

MIT
