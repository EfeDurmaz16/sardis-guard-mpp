"""Sardis Guard — 12-Check Policy Engine for MPP payments.

Each check returns (pass: bool, reason: str). A payment is DENIED if any check fails.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class CheckResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class PolicyCheck:
    name: str
    result: CheckResult
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

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "summary": self.summary,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "checks": [
                {
                    "name": c.name,
                    "result": c.result.value,
                    "reason": c.reason,
                    "latency_ms": round(c.latency_ms, 1),
                }
                for c in self.checks
            ],
        }


@dataclass
class SpendingMandate:
    """Spending mandate defining what an agent is allowed to do."""
    max_per_tx: Decimal = Decimal("10.00")
    max_daily: Decimal = Decimal("100.00")
    allowed_merchants: list[str] = field(default_factory=list)  # empty = all allowed
    blocked_merchants: list[str] = field(default_factory=list)
    allowed_categories: list[str] = field(default_factory=list)  # empty = all allowed
    blocked_categories: list[str] = field(default_factory=list)
    allowed_chains: list[str] = field(default_factory=lambda: ["tempo", "base", "ethereum"])
    allowed_currencies: list[str] = field(default_factory=lambda: ["USDC", "pathUSD", "EURC"])
    require_memo: bool = False
    max_gas_price_gwei: Decimal = Decimal("50")
    cooldown_seconds: int = 0  # min seconds between payments
    active: bool = True


@dataclass
class AgentState:
    """Mutable state tracking for an agent's spending."""
    spent_today: Decimal = Decimal("0")
    tx_count_today: int = 0
    last_payment_ts: float = 0.0


def evaluate_policy(
    amount: Decimal,
    merchant: str,
    currency: str,
    network: str,
    category: str = "general",
    memo: str | None = None,
    gas_price_gwei: Decimal | None = None,
    mandate: SpendingMandate | None = None,
    agent_state: AgentState | None = None,
) -> PolicyVerdict:
    """Run the 12-check policy pipeline. Returns verdict with per-check details."""
    mandate = mandate or SpendingMandate()
    agent_state = agent_state or AgentState()
    checks: list[PolicyCheck] = []
    start = time.monotonic()

    def _check(name: str, fn):
        t0 = time.monotonic()
        try:
            passed, reason = fn()
            result = CheckResult.PASS if passed else CheckResult.FAIL
        except Exception as e:
            result = CheckResult.FAIL
            reason = f"Check error: {e}"
        checks.append(PolicyCheck(name=name, result=result, reason=reason, latency_ms=(time.monotonic() - t0) * 1000))

    # 1. Mandate active
    _check("mandate_active", lambda: (mandate.active, "Mandate is active" if mandate.active else "Mandate is suspended"))

    # 2. Per-transaction limit
    _check("per_tx_limit", lambda: (
        amount <= mandate.max_per_tx,
        f"${amount} <= ${mandate.max_per_tx} limit" if amount <= mandate.max_per_tx else f"${amount} exceeds ${mandate.max_per_tx} per-tx limit"
    ))

    # 3. Daily spending limit
    projected = agent_state.spent_today + amount
    _check("daily_limit", lambda: (
        projected <= mandate.max_daily,
        f"${projected} <= ${mandate.max_daily} daily limit" if projected <= mandate.max_daily else f"${projected} would exceed ${mandate.max_daily} daily limit"
    ))

    # 4. Merchant allowlist
    _check("merchant_allowlist", lambda: (
        not mandate.allowed_merchants or merchant in mandate.allowed_merchants,
        "Merchant allowed" if not mandate.allowed_merchants or merchant in mandate.allowed_merchants else f"Merchant {merchant} not in allowlist"
    ))

    # 5. Merchant blocklist
    _check("merchant_blocklist", lambda: (
        merchant not in mandate.blocked_merchants,
        "Merchant not blocked" if merchant not in mandate.blocked_merchants else f"Merchant {merchant} is blocked"
    ))

    # 6. Category allowlist
    _check("category_allowlist", lambda: (
        not mandate.allowed_categories or category in mandate.allowed_categories,
        "Category allowed" if not mandate.allowed_categories or category in mandate.allowed_categories else f"Category {category} not allowed"
    ))

    # 7. Category blocklist
    _check("category_blocklist", lambda: (
        category not in mandate.blocked_categories,
        "Category not blocked" if category not in mandate.blocked_categories else f"Category {category} is blocked"
    ))

    # 8. Chain allowlist
    _check("chain_allowlist", lambda: (
        network in mandate.allowed_chains,
        f"Chain {network} allowed" if network in mandate.allowed_chains else f"Chain {network} not in allowed chains"
    ))

    # 9. Currency allowlist
    _check("currency_allowlist", lambda: (
        currency in mandate.allowed_currencies,
        f"Currency {currency} allowed" if currency in mandate.allowed_currencies else f"Currency {currency} not allowed"
    ))

    # 10. Memo requirement
    _check("memo_requirement", lambda: (
        not mandate.require_memo or bool(memo),
        "Memo provided or not required" if not mandate.require_memo or bool(memo) else "Memo required but not provided"
    ))

    # 11. Gas price check
    _check("gas_price", lambda: (
        gas_price_gwei is None or gas_price_gwei <= mandate.max_gas_price_gwei,
        "Gas price acceptable" if gas_price_gwei is None or gas_price_gwei <= mandate.max_gas_price_gwei else f"Gas {gas_price_gwei} gwei exceeds {mandate.max_gas_price_gwei} gwei limit"
    ))

    # 12. Cooldown
    now = time.time()
    elapsed = now - agent_state.last_payment_ts if agent_state.last_payment_ts > 0 else float("inf")
    _check("cooldown", lambda: (
        elapsed >= mandate.cooldown_seconds,
        "Cooldown satisfied" if elapsed >= mandate.cooldown_seconds else f"Cooldown: {mandate.cooldown_seconds - elapsed:.0f}s remaining"
    ))

    total_ms = (time.monotonic() - start) * 1000
    all_passed = all(c.result == CheckResult.PASS for c in checks)

    return PolicyVerdict(allowed=all_passed, checks=checks, total_latency_ms=total_ms)
