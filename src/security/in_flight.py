"""In-Flight Limit Anti-Shadow-Lock (Threat T4).

From Sardis Protocol Spec v1.1, Section 23:

A malfunctioning agent (hallucinating, stuck in retry loop) could request
hundreds of payment objects without presenting any to merchants. Each object
claims a FundingCell, effectively freezing all funds until expiry.

The in_flight_limit prevents this by capping concurrent outstanding objects.

    // Before minting new payment object:
    pending_count = COUNT(*) FROM payment_objects
      WHERE mandate_id = mandate.id
      AND state IN ('ISSUED', 'PRESENTED', 'VERIFIED', 'LOCKED', 'ESCROWED', 'SETTLING')

    IF pending_count >= mandate.in_flight_limit:
      RETURN ERROR("in_flight_limit_exceeded")
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class InFlightEntry:
    """A tracked in-flight payment evaluation."""
    event_id: str
    agent_id: str
    mandate_id: str
    amount: str
    merchant: str
    created_at: float = field(default_factory=time.time)
    ttl: float = 300.0  # 5 min default expiry


class InFlightTracker:
    """Tracks outstanding (in-flight) payment evaluations per mandate.

    Prevents T4 shadow-lock attacks by enforcing a maximum number of
    concurrent outstanding evaluations per mandate.
    """

    def __init__(self):
        self._entries: dict[str, list[InFlightEntry]] = {}  # mandate_id -> entries
        self._lock = threading.Lock()

    def check(self, mandate_id: str, limit: int = 5) -> tuple[bool, str, int]:
        """Check if a new evaluation can proceed.

        Returns (allowed, reason, current_count).
        """
        with self._lock:
            self._cleanup_expired(mandate_id)
            entries = self._entries.get(mandate_id, [])
            count = len(entries)

            if count >= limit:
                return (
                    False,
                    f"IN_FLIGHT_LIMIT_EXCEEDED: {count} outstanding evaluations "
                    f"(limit: {limit}). Settle or cancel existing before requesting new.",
                    count,
                )

            return True, f"In-flight check passed ({count}/{limit})", count

    def record(self, entry: InFlightEntry):
        """Record a new in-flight evaluation."""
        with self._lock:
            if entry.mandate_id not in self._entries:
                self._entries[entry.mandate_id] = []
            self._entries[entry.mandate_id].append(entry)

    def resolve(self, mandate_id: str, event_id: str):
        """Remove an entry when it's been settled/fulfilled/cancelled."""
        with self._lock:
            entries = self._entries.get(mandate_id, [])
            self._entries[mandate_id] = [e for e in entries if e.event_id != event_id]

    def get_count(self, mandate_id: str) -> int:
        """Get current in-flight count for a mandate."""
        with self._lock:
            self._cleanup_expired(mandate_id)
            return len(self._entries.get(mandate_id, []))

    def get_all(self, mandate_id: str) -> list[dict]:
        """Get all in-flight entries for a mandate."""
        with self._lock:
            self._cleanup_expired(mandate_id)
            return [
                {
                    "event_id": e.event_id,
                    "agent_id": e.agent_id,
                    "amount": e.amount,
                    "merchant": e.merchant,
                    "created_at": e.created_at,
                    "age_seconds": round(time.time() - e.created_at, 1),
                }
                for e in self._entries.get(mandate_id, [])
            ]

    def _cleanup_expired(self, mandate_id: str):
        """Remove entries past their TTL."""
        now = time.time()
        entries = self._entries.get(mandate_id, [])
        self._entries[mandate_id] = [
            e for e in entries if (now - e.created_at) < e.ttl
        ]
