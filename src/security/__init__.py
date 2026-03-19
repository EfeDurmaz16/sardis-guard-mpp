"""Sardis Guard — Security modules."""

from src.security.dedup import DedupResult, DedupStore
from src.security.goal_drift import DriftScore, GoalDriftDetector
from src.security.in_flight import InFlightEntry, InFlightTracker
from src.security.kill_switch import KillSwitchManager
from src.security.price_creep import CreepResult, PriceCreepDetector
from src.security.session_binding import compute_session_hash, verify_session_hash

__all__ = [
    "CreepResult",
    "DedupResult",
    "DedupStore",
    "DriftScore",
    "GoalDriftDetector",
    "InFlightEntry",
    "InFlightTracker",
    "KillSwitchManager",
    "PriceCreepDetector",
    "compute_session_hash",
    "verify_session_hash",
]
