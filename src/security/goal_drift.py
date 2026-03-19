"""Sardis Guard — Goal Drift Detection (Sardis Protocol).

Detects when an agent's spending behavior shifts from its stated purpose.
Compares recent spending patterns against the agent's historical baseline
using lightweight statistical methods (no heavy ML).

If drift exceeds threshold -> FLAG or HOLD the payment.
"""

from __future__ import annotations

import collections
import math
import time
from dataclasses import dataclass, field


@dataclass
class DriftScore:
    """Result of a goal drift computation."""

    category_drift: float = 0.0   # 0-1, category frequency distribution shift
    service_drift: float = 0.0    # 0-1, Jaccard distance between service sets
    amount_drift: float = 0.0     # 0-1, mean/std shift in recent vs. historical
    composite: float = 0.0        # 0-1, weighted combination
    is_drifting: bool = False     # True if composite exceeds threshold

    def to_dict(self) -> dict:
        return {
            "category_drift": round(self.category_drift, 4),
            "service_drift": round(self.service_drift, 4),
            "amount_drift": round(self.amount_drift, 4),
            "composite": round(self.composite, 4),
            "is_drifting": self.is_drifting,
        }


@dataclass
class _SpendingEvent:
    """Internal record for a single spending event."""

    merchant: str
    category: str
    service_id: str
    amount: float
    timestamp: float


class GoalDriftDetector:
    """Detects behavioral drift from agent's stated purpose.

    Compares recent spending patterns against the agent's historical baseline:
    - Merchant category distribution shift (chi-squared-inspired ratio test)
    - Service usage pattern change (Jaccard distance)
    - Amount distribution shift (mean + std deviation comparison)

    If drift exceeds threshold -> FLAG or HOLD the payment.

    All state is in-memory (dict-based) for hackathon speed.
    """

    # Number of recent events to compare against baseline
    RECENT_WINDOW = 10

    # Composite threshold for flagging drift
    DRIFT_THRESHOLD = 0.60

    # Weights for composite score
    WEIGHT_CATEGORY = 0.40
    WEIGHT_SERVICE = 0.30
    WEIGHT_AMOUNT = 0.30

    def __init__(self) -> None:
        # Key: agent_id -> list of _SpendingEvent (append order)
        self._history: dict[str, list[_SpendingEvent]] = collections.defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_event(
        self,
        agent_id: str,
        merchant: str,
        category: str,
        service_id: str,
        amount: float,
        timestamp: float | None = None,
    ) -> None:
        """Record a spending event for future drift analysis."""
        self._history[agent_id].append(
            _SpendingEvent(
                merchant=merchant,
                category=category,
                service_id=service_id,
                amount=amount,
                timestamp=timestamp or time.time(),
            )
        )

    def compute_drift(self, agent_id: str) -> DriftScore:
        """Compare the last RECENT_WINDOW events against the full baseline.

        Returns a DriftScore with per-dimension and composite scores.
        If the agent has fewer than RECENT_WINDOW + 1 events, drift
        cannot be meaningfully computed and all scores return 0.
        """
        events = self._history.get(agent_id, [])

        # Need at least RECENT_WINDOW + 1 events to have a baseline
        if len(events) <= self.RECENT_WINDOW:
            return DriftScore()

        recent = events[-self.RECENT_WINDOW :]
        baseline = events[: -self.RECENT_WINDOW]

        cat_drift = self._category_drift(recent, baseline)
        svc_drift = self._service_drift(recent, baseline)
        amt_drift = self._amount_drift(recent, baseline)

        composite = (
            self.WEIGHT_CATEGORY * cat_drift
            + self.WEIGHT_SERVICE * svc_drift
            + self.WEIGHT_AMOUNT * amt_drift
        )

        return DriftScore(
            category_drift=cat_drift,
            service_drift=svc_drift,
            amount_drift=amt_drift,
            composite=composite,
            is_drifting=composite >= self.DRIFT_THRESHOLD,
        )

    # ------------------------------------------------------------------
    # Internal scoring functions
    # ------------------------------------------------------------------

    @staticmethod
    def _category_drift(
        recent: list[_SpendingEvent], baseline: list[_SpendingEvent]
    ) -> float:
        """Compare category frequency distributions.

        Uses a chi-squared-inspired ratio test:
        For each category, compute |p_recent - p_baseline| / max(p_baseline, epsilon).
        Average across all categories, capped at 1.0.

        A score of 0 means identical distributions; 1 means completely different.
        """
        epsilon = 1e-6

        # Build frequency distributions
        baseline_counts: dict[str, int] = collections.Counter(
            e.category for e in baseline
        )
        recent_counts: dict[str, int] = collections.Counter(
            e.category for e in recent
        )

        all_categories = set(baseline_counts.keys()) | set(recent_counts.keys())
        if not all_categories:
            return 0.0

        baseline_total = len(baseline)
        recent_total = len(recent)

        divergence_sum = 0.0
        for cat in all_categories:
            p_baseline = baseline_counts.get(cat, 0) / max(baseline_total, 1)
            p_recent = recent_counts.get(cat, 0) / max(recent_total, 1)
            # Normalized absolute difference
            divergence_sum += abs(p_recent - p_baseline) / max(p_baseline, epsilon)

        # Normalize by number of categories; cap at 1.0
        raw = divergence_sum / max(len(all_categories), 1)
        return min(raw, 1.0)

    @staticmethod
    def _service_drift(
        recent: list[_SpendingEvent], baseline: list[_SpendingEvent]
    ) -> float:
        """Jaccard distance between recent and baseline service sets.

        Jaccard distance = 1 - |A intersection B| / |A union B|
        Score of 0 = same services; 1 = completely different services.
        """
        baseline_services = {e.service_id for e in baseline if e.service_id}
        recent_services = {e.service_id for e in recent if e.service_id}

        if not baseline_services and not recent_services:
            return 0.0

        union = baseline_services | recent_services
        intersection = baseline_services & recent_services

        if not union:
            return 0.0

        jaccard_similarity = len(intersection) / len(union)
        return 1.0 - jaccard_similarity

    @staticmethod
    def _amount_drift(
        recent: list[_SpendingEvent], baseline: list[_SpendingEvent]
    ) -> float:
        """Compare mean and std of recent vs. historical amounts.

        Combined score:
        - mean_shift: |mean_recent - mean_baseline| / max(mean_baseline, 1)
        - std_shift: |std_recent - std_baseline| / max(std_baseline, 1)
        - Score = 0.6 * sigmoid(mean_shift) + 0.4 * sigmoid(std_shift)

        Uses a sigmoid to smoothly map unbounded ratios to [0, 1].
        """
        baseline_amounts = [e.amount for e in baseline]
        recent_amounts = [e.amount for e in recent]

        if not baseline_amounts or not recent_amounts:
            return 0.0

        mean_b = sum(baseline_amounts) / len(baseline_amounts)
        mean_r = sum(recent_amounts) / len(recent_amounts)

        # Standard deviation (population)
        std_b = _std(baseline_amounts, mean_b)
        std_r = _std(recent_amounts, mean_r)

        # Normalized shifts
        mean_shift = abs(mean_r - mean_b) / max(mean_b, 1.0)
        std_shift = abs(std_r - std_b) / max(std_b, 1.0)

        # Sigmoid mapping: 2 / (1 + e^(-2x)) - 1  maps [0, inf) -> [0, 1)
        def sigmoid01(x: float) -> float:
            return 2.0 / (1.0 + math.exp(-2.0 * x)) - 1.0

        return 0.6 * sigmoid01(mean_shift) + 0.4 * sigmoid01(std_shift)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _std(values: list[float], mean: float) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)
