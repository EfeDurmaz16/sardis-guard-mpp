# Sardis Repository Audit — Security Features & Components to Port

**Date:** March 19, 2026
**Audit Scope:** Sardis main repository (`/Users/efebarandurmaz/sardis`) → Hackathon project (`~/sardis-mpp-hackathon`)
**Focus:** Security features, infrastructure, and dashboard components we can bring into the demo

---

## Executive Summary

The Sardis core repository has **12+ security gates** that our current 8-gate hackathon pipeline doesn't implement. This audit identifies:

1. **4 major missing security features** (Kill Switch, Goal Drift, Trust Tiers, Anomaly Detection)
2. **Gaps in policy enforcement** compared to production
3. **Reusable dashboard components** for visualization
4. **MCP server architecture** we can adapt for the demo

### Most Impactful to Port (High ROI for Demo)
- **Kill Switch** (Gate 1) — global circuit breaker (easy, high impact)
- **Goal Drift Detection** (Gate 9) — behavioral anomaly (medium effort, impressive demo)
- **Trust Tiers** (implicit in all gates) — dynamic spending limits (medium effort)
- **AnomalyDashboard component** — visualize anomaly signals real-time

---

## 1. Security Features NOT in Hackathon

### 1.1 Kill Switch (Gate 1 — Currently Missing)

#### Source Code
- **Dashboard UI:** `/Users/efebarandurmaz/sardis/dashboard/src/pages/KillSwitch.tsx` (lines 1–300)
- **API Hooks:** `dashboard/src/hooks/useApi.ts` (look for `useKillSwitchStatus`, etc.)
- **Control Plane:** `packages/sardis-core/src/sardis_v2_core/control_plane.py` (lines 1–100)
- **Implementation Details:** `packages/sardis-core/src/sardis_v2_core/execution_intent.py`

#### What It Does
- **Scope:** Global, per-rail (A2A, AP2, checkout), per-chain
- **Redis-backed:** Instant activation/deactivation across fleet
- **Auto-reactivation:** Optional TTL (e.g., "auto-reactivate in 1 hour")
- **Audit trail:** Records who activated, when, and why (reason + notes)
- **Fail-closed:** If kill switch is on, ALL payments on that rail/chain are blocked immediately

#### Current Implementation in Hackathon
**None.** No kill switch exists. We only have 8 gates; kill switch would be Gate 0 (before policy).

#### How to Port It
1. Add Redis key: `sardis:killswitch:{rail}:{chain}` with TTL
2. In policy engine (`src/policy.py`), add **first check**:
   ```python
   async def check_kill_switch(rail: str, chain: str) -> PolicyCheck:
       """Check if kill switch is active for this rail/chain."""
       key = f"sardis:killswitch:{rail}:{chain}"
       active = await redis.get(key)
       return PolicyCheck(
           name="kill_switch",
           result=CheckResult.FAIL if active else CheckResult.PASS,
           reason="Kill switch activated" if active else "OK",
       )
   ```
3. Add API endpoints to activate/deactivate (see KillSwitch.tsx for UI expectations)

#### Effort
**Easy** — ~2–3 hours (if Redis is already configured)

#### Impact for Demo
**High** — Shows "circuit breaker" narrative; impressive when you flip a switch and all payments block globally

---

### 1.2 Goal Drift Detection (Gate 9)

#### Source Code
- **Core Engine:** `packages/sardis-core/src/sardis_v2_core/goal_drift_detector.py` (150+ lines)
- **Integrator:** `packages/sardis-core/src/sardis_v2_core/drift_policy_integrator.py`
- **Policy Call:** `packages/sardis-core/src/sardis_v2_core/spending_policy.py` (lines 401–406)
- **Dashboard:** `dashboard/src/pages/GoalDrift.tsx`
- **Tests:** `packages/sardis-core/tests/test_goal_drift.py`

#### What It Does
- **Statistical Drift Detection** using chi-squared and K-S tests (no ML)
- **5 drift types:**
  - `MERCHANT_SHIFT` — spending with different merchants than baseline
  - `AMOUNT_ANOMALY` — transaction amounts deviate from distribution
  - `VELOCITY_CHANGE` — transactions-per-day spike
  - `CATEGORY_DRIFT` — category distribution shift (e.g., suddenly buying gambling)
  - `TIME_PATTERN_CHANGE` — transacting at unusual times of day

- **Baseline profile** built from 30-day rolling history
- **Severity levels:** LOW / MEDIUM / HIGH / CRITICAL
- **Confidence score** (0.0–1.0) based on p-values

#### Current Implementation in Hackathon
**None.** Our `src/risk/engine.py` has basic anomaly detection but no goal drift.

#### How to Port It
1. Port `goal_drift_detector.py` class to Python or simplify for Tempo demo
2. Build lightweight baseline on first 5–10 transactions per agent
3. In policy engine, add check before compliance:
   ```python
   async def check_goal_drift(agent_id: str, txns: list, current: dict) -> PolicyCheck:
       detector = GoalDriftDetector()
       baseline = await detector.get_agent_baseline(agent_id, txns)
       alert = await detector.detect_drift(agent_id, [current], baseline)

       if alert.severity in ["HIGH", "CRITICAL"]:
           return PolicyCheck(
               name="goal_drift",
               result=CheckResult.FAIL,
               reason=f"{alert.severity} drift: {alert.details}",
           )
       return PolicyCheck(name="goal_drift", result=CheckResult.PASS, reason="OK")
   ```

#### Effort
**Medium** — ~4–6 hours (includes writing minimal baseline builder and drift detector)

#### Impact for Demo
**High** — "Agent spent $500 at gambling merchant (first-time, HIGH severity drift)" is a compelling story

---

### 1.3 Trust Tiers (Implicit in All Gates)

#### Source Code
- **Core Scoring:** `packages/sardis-core/src/sardis_v2_core/kya_trust_scoring.py` (150+ lines)
- **Trust Levels:** Lines 46–80 (enums, thresholds, limits)
- **Policy Integration:** `spending_policy.py` (lines 340–346 use trust override)

#### What It Does
5 trust tiers with automatic spending limits:

| Tier | Score | Per-Tx | Per-Day | How to Reach |
|------|-------|--------|---------|--------------|
| **UNTRUSTED** | 0.0–0.3 | $10 | $25 | New agent, no history |
| **LOW** | 0.3–0.5 | $50 | $100 | Basic KYA (iDenfy verify) |
| **MEDIUM** | 0.5–0.7 | $500 | $1k | Full KYC + some transactions |
| **HIGH** | 0.7–0.9 | $5k | $10k | iDenfy verified + code audit |
| **SOVEREIGN** | 0.9–1.0 | $50k | $100k | Attestation + high history |

Trust score calculated from 5 signals:
1. KYA level (25% weight)
2. Transaction history (20%)
3. Compliance status (20%)
4. Reputation (10%)
5. Behavioral consistency (10%)
6. Transitive trust (15%)

#### Current Implementation in Hackathon
**Partial.** We have spending limits in `SpendingMandate`, but no automatic trust-tier-based escalation.

#### How to Port It
1. Add `TrustTier` enum and `DEFAULT_LIMITS` to `policy.py`
2. Implement lightweight trust scorer (just KYA level → tier; can skip signals for demo):
   ```python
   class TrustScorer:
       def get_tier(kya_level: str) -> TrustTier:
           return {
               "none": TrustTier.UNTRUSTED,
               "basic": TrustTier.LOW,
               "verified": TrustTier.MEDIUM,
               "attested": TrustTier.HIGH,
           }.get(kya_level, TrustTier.UNTRUSTED)
   ```
3. In policy evaluation, apply trust-tier limits as overrides:
   ```python
   def apply_trust_limits(amount: Decimal, tier: TrustTier) -> PolicyCheck:
       max_tx = DEFAULT_LIMITS[tier]["max_per_tx"]
       if amount > max_tx:
           return PolicyCheck(
               name="trust_tier_limit",
               result=CheckResult.FAIL,
               reason=f"Amount ${amount} exceeds {tier} tier limit of ${max_tx}",
           )
       return PolicyCheck(name="trust_tier_limit", result=CheckResult.PASS, reason="OK")
   ```

#### Effort
**Easy** — ~1–2 hours (mostly copy-paste from Sardis + lightweight scorer)

#### Impact for Demo
**Medium** — Shows progression: agents start UNTRUSTED, graduate through tiers as they get verified

---

### 1.4 Anomaly Detection (Already Partially Implemented)

#### Source Code
- **Anomaly Engine:** `packages/sardis-core/src/sardis_v2_core/anomaly_detection.py` (150 lines)
- **Dashboard:** `dashboard/src/pages/AnomalyDashboard.tsx` (300+ lines)
- **MCP Tool:** `packages/sardis-mcp-server/src/tools/guardrails.ts` (lines 1–100+)

#### What It Does (Currently in Hackathon)
- Z-score analysis (transactions > 3 std devs from mean = anomaly)
- Percentile thresholds (top 5% of transactions flagged)
- Frequency analysis (new merchants = higher scrutiny)
- Velocity checks (rapid successive transactions)

#### Current Implementation in Hackathon
**Mostly done.** `src/risk/engine.py` has anomaly detection. Missing:
- Dashboard visualization (AnomalyDashboard.tsx clone)
- Real-time signal scoring
- Baseline statistics persistence
- Merchant reputation tracking

#### How to Port It
1. Copy `AnomalyDashboard.tsx` to `dashboard/src/pages/` — already structured for our API
2. Enhance `src/risk/engine.py` to return structured signals (compatible with Sardis format):
   ```python
   @dataclass
   class AnomalySignal:
       name: str        # e.g., "z_score_3.5", "merchant_first_seen"
       score: float     # 0.0–1.0
       weight: float    # how much to count this in overall score
   ```
3. Expose `/api/anomalies` endpoint to return recent detections

#### Effort
**Easy** — ~1–2 hours (mostly copy UI, minimal backend changes)

#### Impact for Demo
**Medium** — Real-time anomaly feed looks impressive; shows "behavioral monitoring"

---

## 2. Comparison: Hackathon vs. Production Policy Pipeline

### Sardis Production (12 Gates)

From `spending_policy.py`, lines 271–285:

```
1. Amount validation       — amount > 0, fee >= 0
2. Scope check            — is spending category allowed?
3. MCC check              — is merchant category code blocked?
4. Per-tx limit           — amount + fee vs. cap
5. Total limit            — cumulative spending vs. lifetime cap
6. Time-window limits     — daily / weekly / monthly caps
7. On-chain balance       — wallet has funds?
8. Merchant rules         — allowlist / blocklist / per-merchant caps
9. Goal drift             — agent staying on task?
10. Merchant trust        — first-seen / low-trust merchant scrutiny
11. Approval threshold    — needs human sign-off?
12. KYA attestation       — on-chain identity verified?
```

### Hackathon Current (8 Gates)

From `src/policy.py`, `evaluate_policy()`:

```
1. Amount positive check
2. Merchant allowlist/blocklist
3. Category blocklist
4. Per-tx limit
5. Daily limit
6. Network check (allowed chains)
7. Currency check (allowed tokens)
8. (Optional) Gas price check
```

### Gap Analysis

| Gate | Production | Hackathon | Gap | Effort |
|------|-----------|-----------|-----|--------|
| Kill Switch (0) | Yes | No | Missing entire gate | Easy |
| Amount validation | Yes | Yes | ✓ |  |
| Scope | Yes | Partial (network only) | Missing category scopes | Easy |
| MCC check | Yes | No | Missing MCC service | Hard |
| Per-tx limit | Yes | Yes | ✓ |  |
| Total limit | Yes | No | Missing cumulative tracking | Medium |
| Time-window limits | Yes | No | Missing daily/weekly/monthly | Medium |
| On-chain balance | No (hackathon is off-chain) | No | N/A for Tempo |  |
| Merchant rules | Yes | Yes (partial) | Limited to allow/block | Easy |
| Goal drift | Yes | No | Missing entirely | Medium |
| Merchant trust | Yes | No | Missing merchant profiles | Hard |
| Approval threshold | Yes | No | Missing | Hard |
| KYA attestation | Yes | Partial | Only basic KYA check | Medium |

---

## 3. Missing Implementations We Should Add (Priority Order)

### Priority 1 — High Impact, Low Effort

#### 1. Kill Switch (Gate 0)
- **Why:** Global circuit breaker narrative is compelling
- **How:** 1 Redis key check
- **Effort:** 2–3 hours
- **Files to create:** `src/guardrails/kill_switch.py`
- **Files to modify:** `src/policy.py` (add check), `src/routes_v2.py` (add endpoints)

#### 2. Trust Tiers (Policy Override)
- **Why:** Shows agent progression and risk-based limits
- **How:** Map KYA level → TrustTier → spending limits
- **Effort:** 1–2 hours
- **Files to create:** `src/trust/scorer.py`
- **Files to modify:** `src/policy.py` (apply tier limits)

#### 3. Cumulative Spending Limits
- **Why:** Production critical; we skip this entirely
- **How:** Track spent_today + spent_this_month in DB
- **Effort:** 2–3 hours
- **Files to modify:** `src/policy.py` (add check), mandate store (track spend)

### Priority 2 — Medium Impact, Medium Effort

#### 4. Goal Drift Detection
- **Why:** Behavioral anomaly detection is impressive
- **How:** Build baseline from first 5–10 txns, detect shifts in merchant/amount distributions
- **Effort:** 4–6 hours
- **Files to create:** `src/risk/goal_drift.py`
- **Files to modify:** `src/policy.py` (add check), `src/routes_v2.py` (expose baseline endpoint)

#### 5. Time-Window Limits (Daily/Weekly/Monthly)
- **Why:** Real-world spending policies always have rolling windows
- **How:** Track window state in DB with auto-reset logic
- **Effort:** 3–4 hours
- **Files to create:** `src/policy/time_windows.py`
- **Files to modify:** `src/policy.py` (add check), mandate store (persist windows)

#### 6. Approval Threshold
- **Why:** Separates auto-approve from human review
- **How:** If amount > threshold, return "requires_approval" instead of deny
- **Effort:** 1–2 hours
- **Files to modify:** `src/policy.py` (check and return code), `src/types.py` (add approval status)

### Priority 3 — Lower ROI or Hard

#### 7. MCC (Merchant Category Code) Blocking
- **Why:** Blocks entire categories (gambling, adult, etc.)
- **How:** Map MCC to category, check blocklist
- **Effort:** Medium (need MCC lookup table)
- **Files to create:** `src/compliance/mcc_service.py` (with MCC→category mapping)

#### 8. Merchant Trust Scoring
- **Why:** Sophisticated but lower for demo
- **How:** Track merchant interactions, boost approval threshold for known good merchants
- **Effort:** Hard (requires merchant DB)

#### 9. On-Chain Balance Check
- **Why:** Sardis is non-custodial; we're off-chain for Tempo
- **How:** Query Tempo RPC for wallet balance
- **Effort:** Medium (RPC integration)

---

## 4. Dashboard Components We Can Fork

### 4.1 PolicyBuilder.tsx
**Path:** `dashboard/src/components/PolicyBuilder.tsx`

**What it does:**
- Natural language → parsed policy (calls `/api/v2/policies/parse`)
- Shows spending limits, category restrictions, approval thresholds
- Template selection (LOW/MEDIUM/HIGH trust presets)
- Test mode (simulate payment against policy)

**Can we use it?**
**Yes, partially.** Modify to:
1. Use our `/api/policy/parse` endpoint (adapt endpoint names)
2. Remove KYA/compliance fields (keep only spending limits)
3. Simplify templates to match our `SpendingMandate`

**Effort:** 1–2 hours (mostly find-replace on endpoint names)

---

### 4.2 AnomalyDashboard.tsx
**Path:** `dashboard/src/pages/AnomalyDashboard.tsx`

**What it does:**
- Real-time anomaly event feed
- Severity color-coding (low/medium/high/critical)
- Signal breakdown (which checks triggered anomaly)
- Anomaly config panel (adjust sensitivity, thresholds)
- Assessment tool (test if a hypothetical payment would trigger anomaly)

**Can we use it?**
**Yes, with minor changes.** The UI is generic enough. Adapt to:
1. Map our anomaly signals to the `AnomalySignal` interface (name, score, weight)
2. Use our `/api/anomalies` endpoint for event feed
3. Simplify config (just z-score threshold + percentile for demo)

**Effort:** 1–2 hours (mostly endpoint mapping)

---

### 4.3 KillSwitch.tsx
**Path:** `dashboard/src/pages/KillSwitch.tsx`

**What it does:**
- Status grid: rails (A2A, AP2, checkout) × chains (Base, Polygon, etc.)
- Each cell shows: active/inactive + activation time + who activated
- Activate modal: reason + notes + auto-reactivate TTL
- Real-time refresh (1s polling or WebSocket)

**Can we use it?**
**Yes, mostly as-is.** Adapt to:
1. Simplify rails to match our payment types (MPP direct, vouchers, etc.)
2. Simplify chains to match Tempo + testnet
3. Change auto-reactivation default from "none" to "1 hour"

**Effort:** 1–2 hours (mostly UI simplification)

---

### 4.4 AlertFeed.tsx
**Path:** `dashboard/src/components/AlertFeed.tsx`

**What it does:**
- Timeline of alerts (policy violations, compliance blocks, etc.)
- Each alert shows: timestamp, alert type, reason, details
- Filter by severity or type
- Search bar

**Can we use it?**
**Yes, directly.** Just map to our alert/event schema.

**Effort:** 30 minutes (just endpoint mapping)

---

### 4.5 SpendingChart.tsx, AgentSpendingBar.tsx, CategoryPie.tsx
**Path:** `dashboard/src/components/charts/`

**What they do:**
- Bar chart: agent spending over time
- Pie chart: spending by category
- Timeline: daily spending with limits

**Can we use them?**
**Yes, directly.** They're Recharts components with minimal Sardis-specific logic.

**Effort:** 30 minutes (just data format mapping)

---

## 5. MCP Server Patterns We Should Adapt

### 5.1 Guardrails Tools
**Path:** `packages/sardis-mcp-server/src/tools/guardrails.ts`

**Tools exposed:**
- `sardis_check_circuit_breaker` — circuit breaker + kill switch status
- `sardis_activate_kill_switch` — toggle kill switch for a wallet/rail/chain
- `sardis_deactivate_kill_switch` — reset kill switch
- `sardis_check_rate_limits` — current rate limit usage
- `sardis_get_behavioral_alerts` — fetch recent anomaly alerts

**Can we adapt for hackathon?**
**Yes.** These are thin wrappers around REST endpoints. We could create:
```typescript
// src/mcp/tools/guardrails.ts
export const guardrailsTools = {
  check_kill_switch: async (rail: string, chain: string) =>
    GET `/api/guardrails/kill-switch?rail=${rail}&chain=${chain}`,

  activate_kill_switch: async (rail: string, chain: string, reason: string) =>
    POST `/api/guardrails/kill-switch/activate`, { rail, chain, reason },

  check_anomalies: async (limit: number = 10) =>
    GET `/api/anomalies?limit=${limit}`,
};
```

**Effort:** 2–3 hours to create MCP tool wrapper + test

---

### 5.2 Policy Tools
**Path:** `packages/sardis-mcp-server/src/tools/policy.ts`

**Tools exposed:**
- `sardis_check_policy` — validate payment against policy
- `sardis_build_policy` — create/update policy from natural language
- `sardis_get_policy` — fetch current policy for agent

**Can we adapt?**
**Yes, directly.** Our `/api/policy/check` endpoint is basically the same interface.

**Effort:** 1–2 hours

---

## 6. Trust Infrastructure (Advanced, Optional)

### Source Code
**Path:** `packages/sardis-core/src/sardis_v2_core/trust_infrastructure.py`

### What It Does
- **Agent Registry:** Register agent with trust profile
- **Trust Evaluation:** Evaluate trust between two agents (for A2A payments)
- **Attestation Management:** Issue/verify verifiable credentials
- **Trust Network:** Graph of trust relationships between agents

### Current Implementation in Hackathon
**None.** We focus on single-agent spending policies.

### Worth Porting?
**Low priority for hackathon.** This is for agent-to-agent trust, which is out of scope for the demo. Skip it.

---

## 7. Implementation Checklist (Recommended Order)

### Phase 1: Foundational (2–3 hours) — Must Have for Demo
- [ ] **Kill Switch:** Add Redis circuit breaker
  - [ ] `src/guardrails/kill_switch.py` — KillSwitch class
  - [ ] `src/policy.py` — add `check_kill_switch()` as Gate 0
  - [ ] `src/routes_v2.py` — add `/api/guardrails/kill-switch/*` endpoints
  - [ ] Test: Can activate/deactivate, blocks payments when active

- [ ] **Trust Tiers:** Add automatic spending limits by KYA level
  - [ ] `src/trust/scorer.py` — TrustTier enum, DEFAULT_LIMITS mapping
  - [ ] `src/policy.py` — add `apply_trust_tier_limits()` check
  - [ ] Test: Agents escalate from UNTRUSTED → LOW → MEDIUM as KYA improves

### Phase 2: Impact (4–6 hours) — Nice to Have, High Wow Factor
- [ ] **Goal Drift Detection:** Behavioral anomaly detection
  - [ ] `src/risk/goal_drift.py` — GoalDriftDetector with baseline builder
  - [ ] `src/policy.py` — add `check_goal_drift()` as Gate 9
  - [ ] `src/routes_v2.py` — add `/api/risk/baseline` and `/api/risk/drift` endpoints
  - [ ] Test: Can detect merchant shift, amount anomaly, velocity spike

- [ ] **Cumulative Spending Limits:** Track total/monthly spend
  - [ ] `src/policy.py` — add `check_cumulative_limit()` check
  - [ ] Database: Add `agent_spend_state` table (or column in agents)
  - [ ] Test: Can track spend, blocks when limit exceeded

- [ ] **Time-Window Limits:** Daily/weekly/monthly rolling windows
  - [ ] `src/policy/time_windows.py` — TimeWindowLimit class with auto-reset
  - [ ] Database: Persist window state with TTL
  - [ ] `src/policy.py` — add `check_time_windows()` check
  - [ ] Test: Can reset windows on schedule, blocks when exhausted

### Phase 3: UI/Dashboard (2–3 hours) — Makes It Visible
- [ ] Copy `AnomalyDashboard.tsx` to `dashboard/src/pages/`
- [ ] Copy `KillSwitch.tsx` to `dashboard/src/pages/`
- [ ] Copy chart components: `SpendingChart.tsx`, `CategoryPie.tsx`, etc.
- [ ] Update dashboard routes to include new pages
- [ ] Wire up endpoints (search/replace Sardis API paths with our paths)

### Phase 4: Polish (1–2 hours) — Demo Ready
- [ ] Add MCP tool wrappers (guardrails, policy, risk)
- [ ] Create `/api/docs` OpenAPI schema with all new endpoints
- [ ] Add example scenarios to README
- [ ] Record demo walkthrough: Kill switch → Goal drift → Trust escalation

---

## 8. File Mapping Summary

### Files We Should Copy/Fork
| Source | Target | Changes | Effort |
|--------|--------|---------|--------|
| `dashboard/src/pages/KillSwitch.tsx` | `dashboard/src/pages/KillSwitch.tsx` | Simplify rails/chains | 1h |
| `dashboard/src/pages/AnomalyDashboard.tsx` | `dashboard/src/pages/AnomalyDashboard.tsx` | Endpoint mapping | 1h |
| `dashboard/src/components/PolicyBuilder.tsx` | `dashboard/src/components/PolicyBuilder.tsx` | Endpoint mapping | 1h |
| `dashboard/src/components/AlertFeed.tsx` | `dashboard/src/components/AlertFeed.tsx` | Endpoint mapping | 0.5h |
| `dashboard/src/components/charts/*` | `dashboard/src/components/charts/*` | None | 0.5h |

### Files We Should Create/Adapt
| Source | Target | Purpose | Effort |
|--------|--------|---------|--------|
| `kya_trust_scoring.py` | `src/trust/scorer.py` | Trust tier calculation | 2h |
| `goal_drift_detector.py` | `src/risk/goal_drift.py` | Behavioral drift detection | 5h |
| `spending_policy.py` | `src/policy.py` (enhance) | Add 4 new gates | 4h |
| `guardrails.ts` | `src/mcp/tools/guardrails.ts` | MCP guardrails interface | 2h |

---

## 9. Specific Code Snippets to Port

### 9.1 Kill Switch Check (Copy from Control Plane)
```python
# From: packages/sardis-core/src/sardis_v2_core/control_plane.py
# Adapted for hackathon

async def check_kill_switch(rail: str, chain: str) -> tuple[bool, str]:
    """Check if kill switch is active."""
    key = f"sardis:killswitch:{rail}:{chain}"
    active = await redis.get(key)
    if active:
        auto_reactivate_at = await redis.ttl(key)  # -1 = no TTL (permanent)
        return False, f"Kill switch active (auto-reactivate in {auto_reactivate_at}s)"
    return True, "OK"
```

### 9.2 Trust Tier Mapping (Simplified from kya_trust_scoring.py)
```python
# From: packages/sardis-core/src/sardis_v2_core/kya_trust_scoring.py
# Simplified for hackathon

from enum import Enum
from decimal import Decimal

class TrustTier(str, Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SOVEREIGN = "sovereign"

TRUST_TIER_LIMITS = {
    TrustTier.UNTRUSTED: {"max_per_tx": Decimal("10"), "max_per_day": Decimal("25")},
    TrustTier.LOW: {"max_per_tx": Decimal("50"), "max_per_day": Decimal("100")},
    TrustTier.MEDIUM: {"max_per_tx": Decimal("500"), "max_per_day": Decimal("1000")},
    TrustTier.HIGH: {"max_per_tx": Decimal("5000"), "max_per_day": Decimal("10000")},
    TrustTier.SOVEREIGN: {"max_per_tx": Decimal("50000"), "max_per_day": Decimal("100000")},
}

def get_tier_from_kya(kya_level: str) -> TrustTier:
    mapping = {
        "none": TrustTier.UNTRUSTED,
        "basic": TrustTier.LOW,
        "verified": TrustTier.MEDIUM,
        "attested": TrustTier.HIGH,
    }
    return mapping.get(kya_level, TrustTier.UNTRUSTED)
```

### 9.3 Goal Drift Detector Skeleton
```python
# From: packages/sardis-core/src/sardis_v2_core/goal_drift_detector.py
# Simplified for hackathon

class GoalDriftDetector:
    def __init__(self, sensitivity: float = 0.05):
        self.sensitivity = sensitivity
        # For hackathon: use in-memory cache instead of Redis
        self._baselines = {}

    async def build_profile(self, agent_id: str, txns: list) -> dict:
        """Build baseline spending profile from transaction history."""
        if not txns or len(txns) < 5:
            return None  # Not enough data

        merchants = [t.get("merchant") for t in txns]
        amounts = [t.get("amount") for t in txns]
        categories = [t.get("category") for t in txns]

        import statistics
        return {
            "agent_id": agent_id,
            "merchant_distribution": self._count_freq(merchants),
            "amount_distribution": {
                "mean": statistics.mean(amounts),
                "stdev": statistics.stdev(amounts) if len(amounts) > 1 else 0,
            },
            "category_distribution": self._count_freq(categories),
            "transaction_count": len(txns),
        }

    async def detect_drift(self, agent_id: str, current_txn: dict, baseline: dict) -> dict | None:
        """Detect if current transaction represents drift from baseline."""
        if not baseline:
            return None  # No baseline, can't detect drift

        import math
        amount = current_txn.get("amount")
        merchant = current_txn.get("merchant")

        # Z-score check
        mean = baseline["amount_distribution"]["mean"]
        stdev = baseline["amount_distribution"]["stdev"]
        if stdev > 0:
            z_score = abs((amount - mean) / stdev)
            if z_score > 3.0:
                return {
                    "agent_id": agent_id,
                    "drift_type": "AMOUNT_ANOMALY",
                    "severity": "HIGH" if z_score > 4 else "MEDIUM",
                    "confidence": min(z_score / 5.0, 1.0),
                    "details": {"z_score": z_score, "mean": mean},
                }

        # Merchant novelty check
        if merchant not in baseline["merchant_distribution"]:
            if amount > mean * 2:  # Large amount to new merchant
                return {
                    "agent_id": agent_id,
                    "drift_type": "MERCHANT_SHIFT",
                    "severity": "MEDIUM",
                    "confidence": 0.6,
                    "details": {"merchant": merchant, "first_time": True},
                }

        return None  # No drift detected

    @staticmethod
    def _count_freq(items: list) -> dict:
        """Count frequency of items as percentage."""
        if not items:
            return {}
        total = len(items)
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        return {k: v / total for k, v in counts.items()}
```

---

## 10. What NOT to Port

### Things We Should Skip (Out of Scope for Demo)

1. **Trust Network (trust_infrastructure.py)**
   - Agent-to-agent trust for payments
   - Out of scope; we focus on single-agent policies
   - Effort: Hard, impact: Low

2. **Merchant Trust Service**
   - Requires merchant database and reputation scoring
   - Complex; skip for hackathon
   - Effort: Hard, impact: Medium

3. **On-Chain Balance Checking**
   - Sardis is non-custodial; we're off-chain for Tempo
   - Can add later if time permits
   - Effort: Medium, impact: Medium

4. **MCC (Merchant Category Code) Service**
   - Requires MCC lookup table (thousands of codes)
   - Nice to have but heavy for demo
   - Effort: Medium, impact: Medium

5. **Approval Routing (Human Review)**
   - Complex workflow (requires admin UI + email)
   - Can simplify to just returning "requires_approval" flag
   - Effort: Hard, impact: Low

6. **Compliance Integration (KYC/AML/Sanctions)**
   - Already done (iDenfy, Elliptic)
   - Just reuse current implementation
   - Effort: None (already in place)

---

## 11. Dashboard: What's Already Done vs. Missing

### Already Implemented in Dashboard
- ✅ Policy Manager (CRUD policies)
- ✅ Transactions (list + filter)
- ✅ Agents (list, status)
- ✅ Mandates (spending control)
- ✅ Approvals (flow UI)
- ✅ Analytics (basic charts)

### Missing (Worth Adding for Demo)
- ❌ KillSwitch page (control + status grid)
- ❌ AnomalyDashboard (real-time anomaly feed)
- ❌ GoalDrift page (drift detection + baseline viewer)
- ❌ TrustTiers page (agent KYA level + auto-escalation demo)
- ❌ PolicyPlayground (test "what if" scenarios)

---

## 12. Summary: ROI by Feature

| Feature | Effort | Impact | ROI | Recommendation |
|---------|--------|--------|-----|---|
| Kill Switch | Easy (2h) | High | ⭐⭐⭐⭐⭐ | **MUST HAVE** |
| Trust Tiers | Easy (1h) | High | ⭐⭐⭐⭐⭐ | **MUST HAVE** |
| Cumulative Limits | Medium (3h) | High | ⭐⭐⭐⭐ | **Should have** |
| Goal Drift | Medium (5h) | Very High | ⭐⭐⭐⭐⭐ | **Nice to have** (impressive) |
| Time Windows | Medium (3h) | High | ⭐⭐⭐⭐ | **Should have** |
| AnomalyDashboard | Easy (1h) | High | ⭐⭐⭐⭐⭐ | **MUST HAVE** |
| KillSwitch UI | Easy (1h) | High | ⭐⭐⭐⭐⭐ | **MUST HAVE** |
| Approval Threshold | Easy (1h) | Medium | ⭐⭐⭐ | **Nice to have** |
| MCC Service | Medium (4h) | Medium | ⭐⭐ | **Skip** |
| Merchant Trust | Hard (8h) | Medium | ⭐⭐ | **Skip** |
| Trust Network | Hard (6h) | Low | ⭐ | **Skip** |

---

## Conclusion

**Top 5 features to port (in order):**
1. **Kill Switch** (2h) — global circuit breaker, huge demo impact
2. **AnomalyDashboard UI** (1h) — real-time visualization
3. **Trust Tiers** (1h) — shows agent progression
4. **Goal Drift Detection** (5h) — behavioral anomaly, very impressive
5. **KillSwitch UI** (1h) — control plane visibility

**Total time to "wow" demo:** ~10 hours
**Total time for production-ready implementation:** ~20–25 hours

This audit provides a roadmap to bring Sardis's sophisticated security architecture into the hackathon demo while staying focused on the highest-impact features.
