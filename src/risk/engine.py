"""Sardis Guard — Risk Engine.

IsolationForest anomaly detection, Markov sequence novelty,
cross-agent correlation, and composite risk scoring.
"""

from __future__ import annotations

import collections
import math
import threading
import time
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

from src.risk.features import extract_features
from src.storage.event_store import EventStore
from src.types import Action, MandateNode, PaymentIntentEvent, RiskAssessment


class RiskEngine:
    """Real-time risk scoring for payment events.

    Components:
      1. Feature extraction (pure functions from features.py)
      2. IsolationForest anomaly detection (retrained periodically)
      3. Markov-chain service transition surprisal
      4. Cross-agent correlation within the same principal
    """

    # Feature ordering for the ML model (must be consistent)
    _FEATURE_KEYS = [
        "amount_usd",
        "amount_vs_agent_p50",
        "velocity_5m",
        "velocity_1h",
        "merchant_novelty",
        "service_novelty",
        "service_transition_surprisal",
        "delegation_depth",
        "budget_utilization",
        "wallet_age_days",
        "counterparty_count_24h",
        "sanctions_exact_hit",
    ]

    def __init__(self, event_store: EventStore):
        self._store = event_store
        self._lock = threading.Lock()

        # --- IsolationForest ---
        self._model: IsolationForest | None = None
        self._training_data: list[list[float]] = []
        self._event_count_at_last_train = 0
        self._last_train_time = 0.0
        self._min_events_for_ml = 5  # cold-start threshold
        self._retrain_event_interval = 20
        self._retrain_time_interval = 60.0  # seconds

        # --- Markov transition table ---
        # Key: (prev_service, current_service), Value: count
        self._transitions: dict[tuple[str, str], int] = collections.defaultdict(int)
        # Key: prev_service, Value: total outgoing count
        self._transition_totals: dict[str, int] = collections.defaultdict(int)
        # Track last service per agent for transition computation
        self._agent_last_service: dict[str, str] = {}

        # --- Cross-agent correlation ---
        # Key: principal_id, Value: list of (timestamp, agent_id, service_id)
        self._principal_activity: dict[str, list[tuple[float, str, str]]] = (
            collections.defaultdict(list)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(
        self,
        event: PaymentIntentEvent,
        mandate: MandateNode | None = None,
        sanctions_hit: bool = False,
    ) -> RiskAssessment:
        """Full risk assessment for a payment event.

        1. Extract features from event + agent history
        2. Score with IsolationForest (anomaly detection)
        3. Score service transition surprisal (Markov chain)
        4. Score cross-agent correlation
        5. Compose final score and resolve action
        """
        # Get agent history from event store
        history = self._store.get_events(agent_id=event.agent_id, limit=200)

        # 1. Extract features
        features = extract_features(
            event=event,
            history=history,
            mandate=mandate,
            sanctions_hit=sanctions_hit,
        )

        # 2. Compute service transition surprisal and inject into features
        surprisal = self._compute_transition_surprisal(event)
        features["service_transition_surprisal"] = surprisal

        # 3. ML anomaly score
        ml_score = self._score_ml(features)

        # 4. Cross-agent correlation
        correlation_score = self._score_correlation(event)

        # 5. Build RiskAssessment
        assessment = RiskAssessment(
            ml_score=ml_score,
            sequence_score=surprisal,
            correlation_score=correlation_score,
            sanctions_score=features["sanctions_exact_hit"],
            features=features,
        )

        # 6. Resolve action based on composite score
        assessment.resolve_action()

        # Add explanatory reasons
        if ml_score > 0.6:
            assessment.reasons.append(
                f"ML anomaly score high ({ml_score:.2f})"
            )
        if surprisal > 0.7:
            assessment.reasons.append(
                f"Unusual service transition (surprisal={surprisal:.2f})"
            )
        if correlation_score > 0.5:
            assessment.reasons.append(
                f"Cross-agent correlation detected ({correlation_score:.2f})"
            )
        if features["velocity_5m"] > 5:
            assessment.reasons.append(
                f"High velocity: {int(features['velocity_5m'])} events in 5min"
            )
        if features["amount_vs_agent_p50"] > 5.0:
            assessment.reasons.append(
                f"Amount {features['amount_vs_agent_p50']:.1f}x agent median"
            )
        if features["budget_utilization"] > 0.9:
            assessment.reasons.append(
                f"Budget {features['budget_utilization']:.0%} utilized"
            )

        # 7. Update internal state for future scoring
        self._update_state(event, features)

        return assessment

    # ------------------------------------------------------------------
    # IsolationForest ML scoring
    # ------------------------------------------------------------------

    def _score_ml(self, features: dict[str, float]) -> float:
        """Score event using IsolationForest. Returns 0-1 (higher = more anomalous).

        Cold start: returns 0.0 until we have >= _min_events_for_ml data points.
        """
        feature_vec = [features.get(k, 0.0) for k in self._FEATURE_KEYS]

        with self._lock:
            total_events = len(self._training_data)

            # Cold start guard
            if total_events < self._min_events_for_ml:
                return 0.0

            # Check if retrain is needed
            events_since_train = total_events - self._event_count_at_last_train
            time_since_train = time.time() - self._last_train_time
            if (
                self._model is None
                or events_since_train >= self._retrain_event_interval
                or time_since_train >= self._retrain_time_interval
            ):
                self._retrain()

            if self._model is None:
                return 0.0

            # IsolationForest.score_samples returns negative anomaly scores
            # More negative = more anomalous
            # We normalize to 0-1 where 1 = most anomalous
            try:
                raw_score = self._model.score_samples(
                    np.array([feature_vec])
                )[0]
                # Typical range is roughly [-0.7, 0.3] but can vary
                # Map so that score_samples < -0.5 -> anomaly_score near 1.0
                # and score_samples > 0 -> anomaly_score near 0.0
                anomaly_score = max(0.0, min(1.0, -raw_score * 1.5 + 0.25))
                return anomaly_score
            except Exception:
                return 0.0

    def _retrain(self) -> None:
        """Retrain IsolationForest on accumulated training data. Must hold _lock."""
        if len(self._training_data) < self._min_events_for_ml:
            return

        X = np.array(self._training_data)
        self._model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42,
            n_jobs=1,
        )
        self._model.fit(X)
        self._event_count_at_last_train = len(self._training_data)
        self._last_train_time = time.time()

    # ------------------------------------------------------------------
    # Markov transition surprisal
    # ------------------------------------------------------------------

    def _compute_transition_surprisal(self, event: PaymentIntentEvent) -> float:
        """Compute -log(P(current_service | prev_service)) normalized to [0, 1].

        Novel transitions (never seen before) get score 0.9.
        No previous service for this agent -> 0.0 (can't compute transition).
        """
        current_service = event.service_id
        if not current_service:
            return 0.0

        prev_service = self._agent_last_service.get(event.agent_id)
        if not prev_service:
            return 0.0  # First event for this agent, no transition to score

        pair = (prev_service, current_service)
        total = self._transition_totals.get(prev_service, 0)

        if total == 0:
            # No data for this source service at all
            return 0.9

        count = self._transitions.get(pair, 0)
        if count == 0:
            # Never seen this transition
            return 0.9

        probability = count / total
        # -log(p) / normalization_factor to get 0-1 range
        # max surprisal happens at p close to 0, min at p=1
        surprisal = -math.log(probability)
        # Normalize: -log(1/total) is max surprisal for uniform distribution
        max_surprisal = math.log(max(total, 2))
        if max_surprisal == 0:
            return 0.0

        normalized = min(surprisal / max_surprisal, 1.0)
        return normalized

    # ------------------------------------------------------------------
    # Cross-agent correlation
    # ------------------------------------------------------------------

    def _score_correlation(self, event: PaymentIntentEvent) -> float:
        """Find agents under the same principal with similar service sequences
        in a 10-minute window.

        Score = jaccard_similarity(service_paths) * num_correlated_agents
        Capped at 1.0.
        """
        if not event.principal_id or not event.service_id:
            return 0.0

        now = event.timestamp
        window_start = now - 600  # 10 minutes

        activity = self._principal_activity.get(event.principal_id, [])

        # Collect service sets per other agent in window
        agent_services: dict[str, set[str]] = collections.defaultdict(set)
        for ts, aid, svc in activity:
            if ts >= window_start and aid != event.agent_id and svc:
                agent_services[aid].add(svc)

        if not agent_services:
            return 0.0

        # Get current agent's recent services in window
        current_services: set[str] = {event.service_id}
        for ts, aid, svc in activity:
            if ts >= window_start and aid == event.agent_id and svc:
                current_services.add(svc)

        # Compute jaccard similarity with each other agent
        correlated_count = 0
        total_similarity = 0.0

        for other_agent, other_services in agent_services.items():
            intersection = len(current_services & other_services)
            union = len(current_services | other_services)
            if union > 0:
                jaccard = intersection / union
                if jaccard > 0.3:  # threshold for "similar"
                    correlated_count += 1
                    total_similarity += jaccard

        if correlated_count == 0:
            return 0.0

        # Score = avg_similarity * num_correlated, capped at 1.0
        avg_sim = total_similarity / correlated_count
        score = avg_sim * correlated_count
        return min(score, 1.0)

    # ------------------------------------------------------------------
    # State updates (called after scoring)
    # ------------------------------------------------------------------

    def _update_state(
        self, event: PaymentIntentEvent, features: dict[str, float]
    ) -> None:
        """Update ML training data, Markov table, and correlation tracking."""
        feature_vec = [features.get(k, 0.0) for k in self._FEATURE_KEYS]

        with self._lock:
            self._training_data.append(feature_vec)

        # Update Markov transitions
        current_service = event.service_id
        if current_service:
            prev_service = self._agent_last_service.get(event.agent_id)
            if prev_service:
                pair = (prev_service, current_service)
                self._transitions[pair] += 1
                self._transition_totals[prev_service] += 1
            self._agent_last_service[event.agent_id] = current_service

        # Update cross-agent correlation tracking
        if event.principal_id:
            self._principal_activity[event.principal_id].append(
                (event.timestamp, event.agent_id, event.service_id)
            )
            # Prune old entries (> 30 min) to bound memory
            cutoff = event.timestamp - 1800
            self._principal_activity[event.principal_id] = [
                entry
                for entry in self._principal_activity[event.principal_id]
                if entry[0] >= cutoff
            ]
