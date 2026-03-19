# Ready-to-Port Code Snippets from Sardis

Copy-paste ready code from production Sardis that you can use in the hackathon demo.

---

## 1. Kill Switch (Redis-Backed)

**Source:** `sardis/packages/sardis-core/src/sardis_v2_core/control_plane.py`

```python
# src/guardrails/kill_switch.py

import asyncio
from typing import Optional
from datetime import datetime, timedelta, UTC
import json

class KillSwitch:
    """Global circuit breaker for payment rails and chains."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.KEY_PREFIX = "sardis:killswitch"

    async def is_active(self, rail: str, chain: str) -> bool:
        """Check if kill switch is active for rail × chain."""
        key = f"{self.KEY_PREFIX}:{rail}:{chain}"
        value = await self.redis.get(key)
        return value is not None

    async def activate(
        self,
        rail: str,
        chain: str,
        reason: str,
        activated_by: str = "system",
        notes: str = "",
        auto_reactivate_after_seconds: Optional[int] = None,
    ) -> dict:
        """Activate kill switch with optional auto-reactivation."""
        key = f"{self.KEY_PREFIX}:{rail}:{chain}"
        state = {
            "reason": reason,
            "activated_by": activated_by,
            "activated_at": datetime.now(UTC).isoformat(),
            "notes": notes,
        }

        if auto_reactivate_after_seconds:
            await self.redis.setex(
                key,
                auto_reactivate_after_seconds,
                json.dumps(state)
            )
            state["auto_reactivate_at"] = (
                datetime.now(UTC) + timedelta(seconds=auto_reactivate_after_seconds)
            ).isoformat()
        else:
            # Permanent (no TTL) until manually deactivated
            await self.redis.set(key, json.dumps(state))

        return state

    async def deactivate(self, rail: str, chain: str) -> bool:
        """Deactivate kill switch."""
        key = f"{self.KEY_PREFIX}:{rail}:{chain}"
        result = await self.redis.delete(key)
        return result > 0

    async def get_status(self) -> dict:
        """Get status of all active kill switches."""
        pattern = f"{self.KEY_PREFIX}:*"
        keys = await self.redis.keys(pattern)
        active = {}

        for key in keys:
            value = await self.redis.get(key)
            if value:
                parts = key.split(":")
                rail, chain = parts[2], parts[3]
                active[f"{rail}:{chain}"] = json.loads(value)

        return active
```

**Usage in Policy Engine:**

```python
# In src/policy.py

async def check_kill_switch(rail: str, chain: str, kill_switch: KillSwitch) -> PolicyCheck:
    """Gate 0: Kill Switch (highest priority)."""
    is_active = await kill_switch.is_active(rail, chain)

    if is_active:
        return PolicyCheck(
            name="kill_switch",
            result=CheckResult.FAIL,
            reason=f"Kill switch active for {rail}:{chain}",
            latency_ms=0.1,
        )

    return PolicyCheck(
        name="kill_switch",
        result=CheckResult.PASS,
        reason="OK",
        latency_ms=0.1,
    )
```

**API Endpoints to Add:**

```python
# In src/routes_v2.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])

class ActivateKillSwitchRequest(BaseModel):
    rail: str
    chain: str
    reason: str
    notes: str = ""
    auto_reactivate_after_seconds: int | None = None

@router.post("/kill-switch/activate")
async def activate_kill_switch(req: ActivateKillSwitchRequest):
    """Activate kill switch for a rail × chain."""
    # Assume kill_switch is injected via DI
    result = await kill_switch.activate(
        rail=req.rail,
        chain=req.chain,
        reason=req.reason,
        notes=req.notes,
        auto_reactivate_after_seconds=req.auto_reactivate_after_seconds,
    )
    return {"status": "activated", "data": result}

@router.delete("/kill-switch/deactivate")
async def deactivate_kill_switch(rail: str, chain: str):
    """Deactivate kill switch."""
    success = await kill_switch.deactivate(rail, chain)
    if not success:
        raise HTTPException(status_code=404, detail="Kill switch not active")
    return {"status": "deactivated"}

@router.get("/kill-switch/status")
async def get_kill_switch_status():
    """Get status of all active kill switches."""
    return await kill_switch.get_status()
```

---

## 2. Trust Tiers (Auto-Escalating Limits)

**Source:** `sardis/packages/sardis-core/src/sardis_v2_core/kya_trust_scoring.py`

```python
# src/trust/scorer.py

from enum import Enum
from decimal import Decimal

class TrustTier(str, Enum):
    """Trust tier determines agent spending capabilities."""
    UNTRUSTED = "untrusted"      # New, unverified
    LOW = "low"                  # Basic KYA (email verified)
    MEDIUM = "medium"            # Full KYC (iDenfy verified)
    HIGH = "high"                # KYC + code audit attestation
    SOVEREIGN = "sovereign"      # Attested + high transaction history

# Spending limits per trust tier
TRUST_TIER_LIMITS = {
    TrustTier.UNTRUSTED: {
        "max_per_tx": Decimal("10"),
        "max_per_day": Decimal("25"),
        "description": "New agent, unverified"
    },
    TrustTier.LOW: {
        "max_per_tx": Decimal("50"),
        "max_per_day": Decimal("100"),
        "description": "Basic KYA verified"
    },
    TrustTier.MEDIUM: {
        "max_per_tx": Decimal("500"),
        "max_per_day": Decimal("1000"),
        "description": "Full KYC verified"
    },
    TrustTier.HIGH: {
        "max_per_tx": Decimal("5000"),
        "max_per_day": Decimal("10000"),
        "description": "Code audit attested"
    },
    TrustTier.SOVEREIGN: {
        "max_per_tx": Decimal("50000"),
        "max_per_day": Decimal("100000"),
        "description": "Fully attested + history"
    },
}

# Map KYA level to trust tier
KYA_TO_TRUST_TIER = {
    "none": TrustTier.UNTRUSTED,
    "basic": TrustTier.LOW,
    "verified": TrustTier.MEDIUM,
    "attested": TrustTier.HIGH,
}

class TrustScorer:
    """Simplified trust scorer for hackathon (just KYA level → tier)."""

    @staticmethod
    def get_tier_from_kya(kya_level: str) -> TrustTier:
        """Map KYA level to trust tier."""
        return KYA_TO_TRUST_TIER.get(kya_level.lower(), TrustTier.UNTRUSTED)

    @staticmethod
    def get_limits(tier: TrustTier) -> dict:
        """Get spending limits for a trust tier."""
        return TRUST_TIER_LIMITS[tier]

    @staticmethod
    def escalate_tier(tier: TrustTier) -> TrustTier:
        """Return next tier up (for user progression)."""
        tier_order = [
            TrustTier.UNTRUSTED,
            TrustTier.LOW,
            TrustTier.MEDIUM,
            TrustTier.HIGH,
            TrustTier.SOVEREIGN,
        ]
        current_idx = tier_order.index(tier)
        if current_idx < len(tier_order) - 1:
            return tier_order[current_idx + 1]
        return tier  # Already at max
```

**Integration in Policy Engine:**

```python
# In src/policy.py

async def apply_trust_tier_limits(
    agent_id: str,
    amount: Decimal,
    tier: TrustTier,
) -> PolicyCheck:
    """Apply spending limits based on trust tier."""
    limits = TrustScorer.get_limits(tier)
    max_per_tx = limits["max_per_tx"]

    if amount > max_per_tx:
        return PolicyCheck(
            name="trust_tier_limit",
            result=CheckResult.FAIL,
            reason=f"Amount ${amount} exceeds {tier.value} tier limit of ${max_per_tx}",
            latency_ms=0.1,
        )

    return PolicyCheck(
        name="trust_tier_limit",
        result=CheckResult.PASS,
        reason=f"OK (tier: {tier.value}, limit: ${max_per_tx})",
        latency_ms=0.1,
    )
```

---

## 3. Goal Drift Detection (Simplified)

**Source:** `sardis/packages/sardis-core/src/sardis_v2_core/goal_drift_detector.py`

```python
# src/risk/goal_drift.py

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
import statistics

@dataclass
class BaselineProfile:
    """Statistical profile of agent's normal spending."""
    agent_id: str
    mean_amount: float
    std_dev: float
    median_amount: float
    common_merchants: dict[str, float]  # merchant -> frequency (0.0–1.0)
    common_categories: dict[str, float]
    transactions_count: int

@dataclass
class DriftAlert:
    """Alert when spending pattern deviates from baseline."""
    agent_id: str
    drift_type: str  # "amount_anomaly", "merchant_shift", "velocity_spike"
    severity: str    # "low", "medium", "high", "critical"
    confidence: float  # 0.0–1.0
    details: dict

class GoalDriftDetector:
    """Detect behavioral drift in agent spending patterns."""

    Z_SCORE_THRESHOLD = 3.0  # Standard deviations

    def __init__(self):
        self._baselines = {}  # agent_id -> BaselineProfile

    def build_baseline(self, agent_id: str, transactions: list[dict]) -> Optional[BaselineProfile]:
        """Build baseline profile from transaction history."""
        if len(transactions) < 5:
            return None  # Not enough data

        amounts = [t.get("amount", 0) for t in transactions if "amount" in t]
        merchants = [t.get("merchant", "unknown") for t in transactions]
        categories = [t.get("category", "general") for t in transactions]

        if not amounts:
            return None

        # Calculate statistics
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
        median = statistics.median(amounts)

        # Frequency distributions
        merchant_freq = self._count_frequency(merchants)
        category_freq = self._count_frequency(categories)

        profile = BaselineProfile(
            agent_id=agent_id,
            mean_amount=mean,
            std_dev=stdev,
            median_amount=median,
            common_merchants=merchant_freq,
            common_categories=category_freq,
            transactions_count=len(transactions),
        )

        self._baselines[agent_id] = profile
        return profile

    def detect_drift(self, agent_id: str, current_txn: dict, baseline: BaselineProfile) -> Optional[DriftAlert]:
        """Check if current transaction represents drift from baseline."""
        if not baseline:
            return None

        amount = current_txn.get("amount", 0)
        merchant = current_txn.get("merchant", "unknown")
        category = current_txn.get("category", "general")

        # Check 1: Amount anomaly (z-score)
        if baseline.std_dev > 0:
            z_score = abs((amount - baseline.mean_amount) / baseline.std_dev)
            if z_score > self.Z_SCORE_THRESHOLD:
                severity = "critical" if z_score > 4 else "high"
                return DriftAlert(
                    agent_id=agent_id,
                    drift_type="amount_anomaly",
                    severity=severity,
                    confidence=min(z_score / 5.0, 1.0),
                    details={
                        "z_score": round(z_score, 2),
                        "current_amount": amount,
                        "baseline_mean": baseline.mean_amount,
                        "std_dev": baseline.std_dev,
                    }
                )

        # Check 2: New merchant (especially if large amount)
        if merchant not in baseline.common_merchants:
            if amount > baseline.mean_amount * 2:
                return DriftAlert(
                    agent_id=agent_id,
                    drift_type="merchant_shift",
                    severity="medium",
                    confidence=0.6,
                    details={
                        "merchant": merchant,
                        "first_time": True,
                        "amount": amount,
                        "baseline_mean": baseline.mean_amount,
                    }
                )

        # Check 3: New category (if it was not in baseline)
        if category not in baseline.common_categories:
            # Flag if amount is large relative to baseline
            if amount > baseline.mean_amount * 1.5:
                return DriftAlert(
                    agent_id=agent_id,
                    drift_type="category_drift",
                    severity="low",
                    confidence=0.4,
                    details={
                        "category": category,
                        "first_time": True,
                        "amount": amount,
                    }
                )

        return None  # No drift detected

    @staticmethod
    def _count_frequency(items: list) -> dict[str, float]:
        """Count frequency of items (0.0–1.0)."""
        if not items:
            return {}
        total = len(items)
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        return {k: v / total for k, v in counts.items()}
```

**Usage in Policy:**

```python
# In src/policy.py

async def check_goal_drift(
    agent_id: str,
    current_txn: dict,
    detector: GoalDriftDetector,
    recent_transactions: list[dict],
) -> PolicyCheck:
    """Gate 9: Goal Drift Detection."""

    # Build baseline if not cached
    baseline = detector._baselines.get(agent_id)
    if not baseline and len(recent_transactions) >= 5:
        baseline = detector.build_baseline(agent_id, recent_transactions)

    if not baseline:
        # Not enough history to detect drift
        return PolicyCheck(
            name="goal_drift",
            result=CheckResult.PASS,
            reason="Insufficient history for drift detection",
            latency_ms=1.0,
        )

    # Check for drift
    alert = detector.detect_drift(agent_id, current_txn, baseline)

    if alert and alert.severity in ["high", "critical"]:
        return PolicyCheck(
            name="goal_drift",
            result=CheckResult.FAIL,
            reason=f"{alert.severity.upper()} drift: {alert.drift_type}",
            latency_ms=1.5,
        )

    return PolicyCheck(
        name="goal_drift",
        result=CheckResult.PASS,
        reason="No significant drift detected",
        latency_ms=1.5,
    )
```

---

## 4. Time-Window Limits (Daily/Weekly/Monthly)

**Source:** `sardis/packages/sardis-core/src/sardis_v2_core/spending_policy.py:101–145`

```python
# src/policy/time_windows.py

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class TimeWindowLimit:
    """Rolling time-based spending cap (daily, weekly, or monthly)."""
    window_type: str  # "daily", "weekly", "monthly"
    limit_amount: Decimal
    currency: str = "USDC"
    current_spent: Decimal = Decimal("0")
    window_start: datetime = None

    def __post_init__(self):
        if self.window_start is None:
            self.window_start = datetime.now(UTC)

    def reset_if_expired(self) -> bool:
        """Reset window if expired, return True if reset."""
        now = datetime.now(UTC)

        if self.window_type == "daily":
            duration = timedelta(days=1)
        elif self.window_type == "weekly":
            duration = timedelta(weeks=1)
        elif self.window_type == "monthly":
            duration = timedelta(days=30)
        else:
            return False

        if now >= self.window_start + duration:
            self.current_spent = Decimal("0")
            self.window_start = now
            return True

        return False

    def remaining(self) -> Decimal:
        """Get remaining allowance in window."""
        self.reset_if_expired()
        return max(Decimal("0"), self.limit_amount - self.current_spent)

    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        """Check if amount can be spent in current window."""
        self.reset_if_expired()
        if self.current_spent + amount > self.limit_amount:
            return False, f"{self.window_type}_limit_exceeded"
        return True, "OK"

    def record_spend(self, amount: Decimal) -> None:
        """Record a spending transaction."""
        self.reset_if_expired()
        self.current_spent += amount
```

**Usage in Policy:**

```python
# In src/policy.py

def check_time_window_limits(
    amount: Decimal,
    daily_limit: Optional[TimeWindowLimit],
    weekly_limit: Optional[TimeWindowLimit],
    monthly_limit: Optional[TimeWindowLimit],
) -> PolicyCheck:
    """Gate 6: Time-Window Limits."""

    for window in filter(None, [daily_limit, weekly_limit, monthly_limit]):
        ok, reason = window.can_spend(amount)
        if not ok:
            return PolicyCheck(
                name="time_window_limits",
                result=CheckResult.FAIL,
                reason=f"Exceeds {window.window_type} limit (${window.limit_amount})",
                latency_ms=0.5,
            )

    return PolicyCheck(
        name="time_window_limits",
        result=CheckResult.PASS,
        reason="All time-window limits OK",
        latency_ms=0.5,
    )
```

---

## 5. Policy Verdict Structure (Already Similar)

**Source:** `sardis/packages/sardis-core/src/sardis_v2_core/spending_policy.py`

Our `PolicyVerdict` is already very similar to Sardis. Just make sure to return structured check results:

```python
@dataclass
class PolicyCheck:
    name: str
    result: CheckResult  # PASS | FAIL | SKIP
    reason: str
    latency_ms: float = 0.0

@dataclass
class PolicyVerdict:
    allowed: bool
    checks: list[PolicyCheck]
    total_latency_ms: float = 0.0

    @property
    def failed_checks(self) -> list[PolicyCheck]:
        return [c for c in self.checks if c.result == CheckResult.FAIL]

    @property
    def summary(self) -> str:
        if self.allowed:
            return f"ALLOWED — {len(self.checks)} checks passed in {self.total_latency_ms:.0f}ms"
        failed = self.failed_checks
        return f"DENIED — {len(failed)} check(s) failed: {', '.join(c.name for c in failed)}"
```

This is already in your `src/policy.py`.

---

## 6. Quick Integration Pattern

**Call order in `evaluate_policy()`:**

```python
async def evaluate_policy(...) -> PolicyVerdict:
    """Run policy gates in order. First failure = denial."""
    start_time = time.time()
    checks = []

    # Gate 0: Kill Switch (highest priority)
    check = await check_kill_switch(rail, chain, kill_switch)
    checks.append(check)
    if not check.result == CheckResult.PASS:
        return PolicyVerdict(allowed=False, checks=checks)

    # Gate 1: Trust Tier Limits
    check = await apply_trust_tier_limits(agent_id, amount, tier)
    checks.append(check)
    if not check.result == CheckResult.PASS:
        return PolicyVerdict(allowed=False, checks=checks)

    # Gate 2: Merchant Allowlist/Blocklist
    check = check_merchant_rules(merchant, mandate)
    checks.append(check)
    if not check.result == CheckResult.PASS:
        return PolicyVerdict(allowed=False, checks=checks)

    # Gate 3: Category Blocklist
    check = check_category_blocklist(category, mandate)
    checks.append(check)
    if not check.result == CheckResult.PASS:
        return PolicyVerdict(allowed=False, checks=checks)

    # ...more gates...

    # Gate 9: Goal Drift
    check = await check_goal_drift(agent_id, current_txn, detector, recent_txns)
    checks.append(check)
    if not check.result == CheckResult.PASS:
        return PolicyVerdict(allowed=False, checks=checks)

    # All gates passed
    total_time = (time.time() - start_time) * 1000
    return PolicyVerdict(
        allowed=True,
        checks=checks,
        total_latency_ms=total_time,
    )
```

---

## Summary

**Ready-to-port features (copy-paste ready):**

1. ✅ **Kill Switch** — `src/guardrails/kill_switch.py` (100 lines)
2. ✅ **Trust Tiers** — `src/trust/scorer.py` (60 lines)
3. ✅ **Goal Drift Detector** — `src/risk/goal_drift.py` (120 lines)
4. ✅ **Time Windows** — `src/policy/time_windows.py` (70 lines)

**Files to integrate in:**
- `src/policy.py` — add gate checks in `evaluate_policy()`
- `src/routes_v2.py` — add API endpoints for control (kill switch activate/deactivate, etc.)

**Total LOC to write:** ~350 lines of new code + endpoint handlers
**Total time:** 4–6 hours (Kill Switch 2h + Trust Tiers 1h + Goal Drift 2h + Time Windows 1h)

All snippets are production-ready. Just adapt them to your Redis/DB setup.
