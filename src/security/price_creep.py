"""Sardis Guard — Price Creep Protection (Threat T10).

From Sardis Protocol Spec Section 30:

A SaaS vendor might apply micro-increases each billing cycle,
staying under per-cycle thresholds but drifting significantly
over time. This detector tracks cumulative drift and consecutive
increases to catch slow price manipulation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CreepResult:
    """Result of a price creep check."""

    drifted: bool = False              # True if any threshold was breached
    drift_pct: float = 0.0            # Cumulative drift from first recorded price (%)
    consecutive_increases: int = 0     # Number of consecutive price increases
    reason: str = ""                   # Human-readable explanation

    def to_dict(self) -> dict:
        return {
            "drifted": self.drifted,
            "drift_pct": round(self.drift_pct, 2),
            "consecutive_increases": self.consecutive_increases,
            "reason": self.reason,
        }


@dataclass
class _PriceRecord:
    """A single price observation."""

    amount: float
    timestamp: float


class PriceCreepDetector:
    """Detects slow merchant price increases (Threat T10).

    A SaaS vendor might apply micro-increases each billing cycle,
    staying under per-cycle thresholds but drifting significantly
    over time. This detector tracks:
    - max_price_increase_pct: Max single-cycle increase (default 10%)
    - cumulative_drift_cap_pct: Max total drift over window (default 25%)
    - consecutive_trueup_escalation: After N consecutive increases, auto-escalate (default 3)

    All state is in-memory (dict-based) for hackathon speed.
    """

    def __init__(
        self,
        max_price_increase_pct: float = 10.0,
        cumulative_drift_cap_pct: float = 25.0,
        consecutive_trueup_escalation: int = 3,
    ) -> None:
        self.max_price_increase_pct = max_price_increase_pct
        self.cumulative_drift_cap_pct = cumulative_drift_cap_pct
        self.consecutive_trueup_escalation = consecutive_trueup_escalation

        # Key: (merchant, service_id) -> list of _PriceRecord (append order)
        self._prices: dict[tuple[str, str], list[_PriceRecord]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_price(
        self,
        merchant: str,
        service_id: str,
        amount: float,
        timestamp: float | None = None,
    ) -> None:
        """Record a price observation for a merchant+service pair."""
        key = (merchant, service_id)
        if key not in self._prices:
            self._prices[key] = []
        self._prices[key].append(
            _PriceRecord(amount=amount, timestamp=timestamp or time.time())
        )

    def check_creep(
        self,
        merchant: str,
        service_id: str,
        current_amount: float,
    ) -> CreepResult:
        """Check whether the current price shows signs of creep.

        Evaluates three conditions (any triggers a flag):
        1. Single-cycle increase exceeds max_price_increase_pct
        2. Cumulative drift from first price exceeds cumulative_drift_cap_pct
        3. Consecutive increases >= consecutive_trueup_escalation

        Returns CreepResult with detailed reasoning.
        """
        key = (merchant, service_id)
        history = self._prices.get(key, [])

        # No history — nothing to compare against
        if not history:
            return CreepResult(reason="No price history — first observation")

        reasons: list[str] = []
        drifted = False

        # --- 1. Single-cycle increase check ---
        last_price = history[-1].amount
        if last_price > 0:
            cycle_change_pct = ((current_amount - last_price) / last_price) * 100.0
        else:
            cycle_change_pct = 0.0

        if cycle_change_pct > self.max_price_increase_pct:
            drifted = True
            reasons.append(
                f"Single-cycle increase {cycle_change_pct:.1f}% exceeds "
                f"{self.max_price_increase_pct}% threshold"
            )

        # --- 2. Cumulative drift from first recorded price ---
        first_price = history[0].amount
        if first_price > 0:
            cumulative_pct = ((current_amount - first_price) / first_price) * 100.0
        else:
            cumulative_pct = 0.0

        if cumulative_pct > self.cumulative_drift_cap_pct:
            drifted = True
            reasons.append(
                f"Cumulative drift {cumulative_pct:.1f}% exceeds "
                f"{self.cumulative_drift_cap_pct}% cap"
            )

        # --- 3. Consecutive increases ---
        # Count backwards from the end of history, including current_amount
        consecutive = 0
        prices_with_current = [r.amount for r in history] + [current_amount]
        for i in range(len(prices_with_current) - 1, 0, -1):
            if prices_with_current[i] > prices_with_current[i - 1]:
                consecutive += 1
            else:
                break

        if consecutive >= self.consecutive_trueup_escalation:
            drifted = True
            reasons.append(
                f"{consecutive} consecutive price increases "
                f"(threshold: {self.consecutive_trueup_escalation}) — auto-escalate FLAG"
            )

        # Build reason string
        if not reasons:
            reason = (
                f"Price OK — cycle change {cycle_change_pct:+.1f}%, "
                f"cumulative {cumulative_pct:+.1f}%, "
                f"{consecutive} consecutive increase(s)"
            )
        else:
            reason = "; ".join(reasons)

        return CreepResult(
            drifted=drifted,
            drift_pct=cumulative_pct,
            consecutive_increases=consecutive,
            reason=reason,
        )
