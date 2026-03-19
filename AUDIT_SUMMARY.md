# 🔍 Sardis Repository Audit — Summary for Hackathon Team

**Completed:** March 19, 2026
**Audit Scope:** Sardis core → Hackathon demo feature parity
**Full Audit:** See `docs/sardis_repo_audit.md` (2,500+ lines)

---

## 🎯 Quick Answer: What Can We Steal?

We found **5 high-impact features** from production that we can port to the hackathon demo in **5–25 hours** total.

### Top 5 Features (Priority Order)

| # | Feature | Effort | Impact | Status |
|---|---------|--------|--------|--------|
| 1️⃣ | **Kill Switch** (global circuit breaker) | 2–3h | ⭐⭐⭐⭐⭐ | Can port 80% from code |
| 2️⃣ | **AnomalyDashboard UI** (real-time feed) | 1–2h | ⭐⭐⭐⭐⭐ | Copy TSX directly, adapt endpoints |
| 3️⃣ | **Trust Tiers** (KYA → auto spending limits) | 1–2h | ⭐⭐⭐⭐⭐ | Mostly data mapping |
| 4️⃣ | **Goal Drift** (behavioral anomaly detection) | 4–6h | ⭐⭐⭐⭐⭐ | Port statistical detector |
| 5️⃣ | **KillSwitch UI** (control panel) | 1–2h | ⭐⭐⭐⭐⭐ | Copy TSX, simplify UI |

**Total to "wow" investors:** ~5–6 hours (top 3 features)
**Total for production-ready demo:** ~20–25 hours (all 5 + supporting features)

---

## 📊 Production vs. Hackathon: Gate Comparison

### Sardis Production: 12 Security Gates
```
Gate 1:  Kill Switch              ← MISSING (we have no circuit breaker)
Gate 2:  Amount validation
Gate 3:  Scope check              ← PARTIAL (we only check networks)
Gate 4:  MCC category check       ← MISSING
Gate 5:  Per-tx limit             ✅ We have this
Gate 6:  Total lifetime limit     ← MISSING
Gate 7:  Time-window limits       ← MISSING
Gate 8:  On-chain balance         ← N/A (we're off-chain)
Gate 9:  Merchant rules           ✅ We have this (partial)
Gate 10: Goal drift               ← MISSING
Gate 11: Merchant trust           ← MISSING
Gate 12: Approval threshold       ← MISSING
```

### Hackathon Current: 8 Gates
```
✅ Amount positive
✅ Merchant allowlist/blocklist
✅ Category blocklist
✅ Per-tx limit
✅ Daily limit
✅ Network check
✅ Currency check
✅ (Optional) Gas price
```

**Gap:** We're missing the sophisticated gates (kill switch, goal drift, trust escalation, approval routing, merchant intelligence).

---

## 🚀 Implementation Roadmap

### Phase 1: Quick Wins (5–6 hours) → "Wow" Investors

```python
# 1. Kill Switch (2–3h)
# - Add Redis-backed global circuit breaker
# - Can activate by rail (A2A, AP2, checkout) or chain (Base, Polygon, etc.)
# - Demo: "Flip this switch and all payments block globally, instantly"

# 2. Trust Tiers (1–2h)
# - UNTRUSTED → LOW → MEDIUM → HIGH → SOVEREIGN
# - Auto-escalate as agent gets verified (iDenfy)
# - Demo: "Agent starts with $10/tx limit, graduates to $50k/tx"

# 3. AnomalyDashboard UI (1–2h)
# - Real-time feed of anomaly alerts
# - Severity color-coding (low=green, critical=red)
# - Demo: "Monitor behavioral anomalies in real-time"
```

### Phase 2: Impressive Features (10–14 hours) → Deep Technical Demo

```python
# 4. Goal Drift Detection (4–6h)
# - Statistical baseline → compare current transactions
# - Detects merchant shift, amount anomaly, velocity spike
# - Demo: "Agent suddenly tries to buy gambling (drift HIGH). Block & alert."

# 5. Cumulative Spending Limits (2–3h)
# - Track total/monthly spend against policy
# - Prevents limit overrun via concurrent transactions

# 6. Time-Window Limits (2–3h)
# - Daily/weekly/monthly rolling windows with auto-reset
# - More sophisticated than hardcoded daily limit

# 7. Approval Routing (2–3h)
# - Amount OK but needs human sign-off
# - Separates "auto-approve" from "requires review"
```

### What to Skip (Low ROI)

- ❌ **MCC Service** (merchant category codes) — requires huge lookup table
- ❌ **Merchant Trust Scoring** — requires merchant database
- ❌ **On-chain Balance Check** — we're off-chain for Tempo
- ❌ **Trust Network** (agent-to-agent) — out of scope for single-agent policy demo

---

## 📁 Code We Can Copy/Fork

### 1. Dashboard Components (Copy-Paste, 30 min–1h each)

| Component | Path | What It Does | Effort |
|-----------|------|-------------|--------|
| **KillSwitch.tsx** | `dashboard/src/pages/KillSwitch.tsx` | Status grid + activate/deactivate modal | 1h (simplify UI) |
| **AnomalyDashboard.tsx** | `dashboard/src/pages/AnomalyDashboard.tsx` | Real-time anomaly event feed | 1h (endpoint mapping) |
| **PolicyBuilder.tsx** | `dashboard/src/components/PolicyBuilder.tsx` | NL → policy parser + tester | 1h (endpoint mapping) |
| **AlertFeed.tsx** | `dashboard/src/components/AlertFeed.tsx` | Timeline of alerts/blocks | 30m (endpoint mapping) |
| **Charts** | `dashboard/src/components/charts/` | SpendingChart, CategoryPie, etc. | 30m (data mapping) |

### 2. Core Backend Code (Port & Adapt, 1–5h each)

| Feature | Source File | Lines | Can Port | Effort |
|---------|------------|-------|----------|--------|
| **Kill Switch** | `control_plane.py` | 60–90 | 80% | 2–3h |
| **Trust Tiers** | `kya_trust_scoring.py` | 46–80 | 90% | 1–2h |
| **Goal Drift** | `goal_drift_detector.py` | 1–150 | 70% | 4–6h |
| **Anomaly Detection** | `anomaly_detection.py` | 1–150 | 90% | 1–2h |
| **Time Windows** | `spending_policy.py:101–145` | 50 | 95% | 2–3h |
| **Orchestrator Pattern** | `orchestrator.py` | 1000+ | 60% | Reference only |

All code has detailed docstrings and is in Python (our stack).

---

## 🎬 Demo Narrative (With These Features)

**Before:** "Our policy engine checks 8 things"

**After:** "Our policy engine has 12+ gates + behavioral anomaly detection:
1. **Kill Switch** — Global circuit breaker (instant, fleet-wide)
2. **Trust Tiers** — Agents start untrusted ($10/tx), graduate with verification
3. **Goal Drift** — Detects behavioral shifts (merchant changes, velocity spikes)
4. **Cumulative Limits** — Total + monthly caps prevent burst attacks
5. **Time Windows** — Daily/weekly/monthly rolling windows
6. **Approval Routing** — Large payments require human review
7. **Merchant Intelligence** — First-seen merchants get tighter scrutiny
8. **Compliance** — KYC + sanctions + AML (iDenfy + Elliptic)

Plus: Real-time dashboard visualization of all enforcement"

**Investor reaction:** 🤯 "That's production-grade. How'd you build this in a hackathon?"

---

## 📋 Implementation Checklist

### ✅ Phase 1: Must-Have (5–6 hours)

- [ ] **Kill Switch Backend** (2h)
  - [ ] Create `src/guardrails/kill_switch.py` with Redis integration
  - [ ] Add `check_kill_switch()` as Gate 0 in `src/policy.py`
  - [ ] Add endpoints: POST `/api/guardrails/kill-switch/activate`, DELETE `...deactivate`
  - [ ] Test: Activation blocks all payments on specified rail/chain

- [ ] **Trust Tiers Backend** (1h)
  - [ ] Create `src/trust/scorer.py` with TrustTier enum + limits
  - [ ] Add `apply_trust_tier_limits()` to policy engine
  - [ ] Test: Agent escalates UNTRUSTED → LOW → MEDIUM as KYA improves

- [ ] **Dashboard: AnomalyDashboard** (1h)
  - [ ] Copy `dashboard/src/pages/AnomalyDashboard.tsx`
  - [ ] Adapt `/api/anomalies` endpoint mapping
  - [ ] Wire into routes

- [ ] **Dashboard: KillSwitch** (1h)
  - [ ] Copy `dashboard/src/pages/KillSwitch.tsx`
  - [ ] Simplify rails/chains, adapt endpoints
  - [ ] Wire into routes

### 📊 Phase 2: Nice-to-Have (10–14 hours, If Time Permits)

- [ ] **Goal Drift Detection** (5h)
  - [ ] Port `GoalDriftDetector` to `src/risk/goal_drift.py`
  - [ ] Implement baseline builder + drift detector
  - [ ] Add `check_goal_drift()` as Gate 9 in policy.py
  - [ ] Expose `/api/risk/baseline` and `/api/risk/drift` endpoints

- [ ] **Cumulative Spending Limits** (3h)
  - [ ] Track `spent_today` + `spent_this_month` in agent state
  - [ ] Add `check_cumulative_limit()` to policy.py
  - [ ] Database: Add spend_state table/column

- [ ] **Time-Window Limits** (3h)
  - [ ] Create `src/policy/time_windows.py` with auto-reset logic
  - [ ] Add `check_time_windows()` to policy.py
  - [ ] Database: Persist window state with TTL

- [ ] **Approval Threshold** (2h)
  - [ ] Return "requires_approval" instead of deny for large amounts
  - [ ] Add approval status to PaymentResult
  - [ ] Expose in `/api/policy/check` response

---

## 🔗 Key Files to Reference

**Full Audit Document:** `~/sardis-mpp-hackathon/docs/sardis_repo_audit.md` (2,500 lines)
- Implementation checklists for every feature
- Code snippets ready to copy
- Effort estimates and ROI analysis
- FAQ on what to skip

**Production Code References:**
- Kill Switch: `sardis/packages/sardis-core/src/sardis_v2_core/control_plane.py` (lines 1–100)
- Trust Tiers: `sardis/packages/sardis-core/src/sardis_v2_core/kya_trust_scoring.py` (lines 46–150)
- Goal Drift: `sardis/packages/sardis-core/src/sardis_v2_core/goal_drift_detector.py` (lines 1–150)
- Dashboard: `sardis/dashboard/src/pages/{KillSwitch,AnomalyDashboard,GoalDrift}.tsx`
- MCP Tools: `sardis/packages/sardis-mcp-server/src/tools/guardrails.ts` (lines 1–200+)

---

## 💡 Quick Decision Guide

**If you have 5–6 hours:** Port Kill Switch + Trust Tiers + AnomalyDashboard UI
→ Result: "Wow" investors with circuit breaker + agent progression

**If you have 10–14 hours:** Add Goal Drift Detection + Cumulative Limits
→ Result: Production-grade policy engine in a hackathon

**If you have 20+ hours:** Add all features + Approval Routing + Polish
→ Result: Hardcore demo; beats most Series A companies

---

## 🎓 Key Learnings

1. **Production Sardis is sophisticated but portable.** Most features are non-ML (statistical tests, simple rules), so they port easily.

2. **Kill Switch is the biggest bang for buck.** 2–3 hours of work, instantly impressive in a demo.

3. **Dashboard is 80% reusable.** We can copy Sardis TSX files almost directly; mostly just endpoint mapping.

4. **Trust Tiers enable a powerful narrative.** "Agents start untrusted, graduate with verification" is a compelling story.

5. **Goal Drift is production-grade** but only if you spend 5+ hours on it. If time is tight, skip for Phase 2.

---

## 🎯 Recommendation

**Start with Phase 1 (5–6h).** You'll immediately:
- ✅ Add Kill Switch (circuit breaker narrative)
- ✅ Add Trust Tiers (agent progression story)
- ✅ Add AnomalyDashboard (real-time visualization)
- ✅ Add KillSwitch UI (operational control)

Then, **if iterations allow, add Goal Drift (4–6h more).** That's the feature that truly differentiates you from competitors.

---

**Questions?** See full audit in `docs/sardis_repo_audit.md` for detailed implementation guides, code snippets, and ROI analysis.
