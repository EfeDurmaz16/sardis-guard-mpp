"""Sardis Guard — Pure feature extraction functions.

All functions are stateless and operate on event data + history.
"""

from __future__ import annotations

import math
import statistics
import time
from decimal import Decimal
from typing import Any

from src.types import MandateNode, PaymentIntentEvent


def extract_features(
    event: PaymentIntentEvent,
    history: list[dict[str, Any]],
    mandate: MandateNode | None = None,
    sanctions_hit: bool = False,
    wallet_age_days: float = 30.0,
) -> dict[str, float]:
    """Extract the full feature vector for a payment event.

    Args:
        event: The current payment event being evaluated.
        history: Previous events for the same agent (newest first, dicts).
        mandate: The mandate governing this payment, if any.
        sanctions_hit: Whether the compliance module flagged a sanctions match.
        wallet_age_days: Age of the wallet in days (placeholder from intel).

    Returns:
        Dictionary of feature name -> float value.
    """
    features: dict[str, float] = {}

    features["amount_usd"] = float(event.amount)
    features["amount_vs_agent_p50"] = _amount_vs_p50(event, history)
    features["velocity_5m"] = _velocity(history, minutes=5)
    features["velocity_1h"] = _velocity(history, minutes=60)
    features["merchant_novelty"] = _novelty(event.merchant, history, field="merchant")
    features["service_novelty"] = _novelty(event.service_id, history, field="service_id")
    features["service_transition_surprisal"] = 0.0  # Computed by engine's Markov table
    features["delegation_depth"] = _delegation_depth(mandate)
    features["budget_utilization"] = _budget_utilization(mandate)
    features["wallet_age_days"] = wallet_age_days
    features["counterparty_count_24h"] = _counterparty_count_24h(history)
    features["sanctions_exact_hit"] = 1.0 if sanctions_hit else 0.0

    return features


# ------------------------------------------------------------------
# Individual feature functions
# ------------------------------------------------------------------


def _amount_vs_p50(event: PaymentIntentEvent, history: list[dict[str, Any]]) -> float:
    """Ratio of current amount to the median amount in agent history.

    Returns 1.0 if no history (neutral).
    """
    if not history:
        return 1.0

    amounts = []
    for h in history:
        try:
            a = float(h.get("amount", 0))
            if a > 0:
                amounts.append(a)
        except (ValueError, TypeError):
            continue

    if not amounts:
        return 1.0

    median = statistics.median(amounts)
    if median == 0:
        return 1.0

    return float(event.amount) / median


def _velocity(history: list[dict[str, Any]], minutes: int) -> float:
    """Count of events in the last N minutes."""
    cutoff = time.time() - (minutes * 60)
    count = 0
    for h in history:
        ts = h.get("timestamp", 0)
        if isinstance(ts, (int, float)) and ts >= cutoff:
            count += 1
        elif isinstance(ts, (int, float)) and ts < cutoff:
            # History is newest-first, so once we pass the cutoff we can stop
            break
    return float(count)


def _novelty(value: str, history: list[dict[str, Any]], field: str) -> float:
    """1.0 if never seen, decays with repeated occurrences.

    Formula: 1.0 / (1 + occurrences)  ->  first time = 0.5, never = 1.0
    For truly never seen: return 1.0
    """
    if not value:
        return 0.0
    if not history:
        return 1.0

    occurrences = sum(1 for h in history if h.get(field) == value)
    if occurrences == 0:
        return 1.0

    # Exponential decay: e^(-0.3 * occurrences) gives smooth decay
    return math.exp(-0.3 * occurrences)


def _delegation_depth(mandate: MandateNode | None) -> float:
    """Delegation depth from mandate, normalized."""
    if mandate is None:
        return 0.0
    return float(mandate.delegation_depth)


def _budget_utilization(mandate: MandateNode | None) -> float:
    """Fraction of total budget already spent."""
    if mandate is None:
        return 0.0
    max_total = float(mandate.max_total)
    if max_total <= 0:
        return 1.0
    spent = float(mandate.spent)
    return min(spent / max_total, 1.0)


def _counterparty_count_24h(history: list[dict[str, Any]]) -> float:
    """Number of unique merchants in the last 24 hours."""
    cutoff = time.time() - (24 * 60 * 60)
    merchants: set[str] = set()
    for h in history:
        ts = h.get("timestamp", 0)
        if isinstance(ts, (int, float)) and ts >= cutoff:
            m = h.get("merchant", "")
            if m:
                merchants.add(m)
        elif isinstance(ts, (int, float)) and ts < cutoff:
            break
    return float(len(merchants))
