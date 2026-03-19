"""Sardis Guard — Swarm Orchestration.

Multi-agent orchestration with mandate delegation and risk detection.
Demonstrates both benign (research) and adversarial (attack) scenarios.
"""

from src.swarm.orchestrator import SwarmOrchestrator
from src.swarm.scenarios import BENIGN_SCENARIO, ATTACK_SCENARIO, ScenarioStep

__all__ = [
    "SwarmOrchestrator",
    "BENIGN_SCENARIO",
    "ATTACK_SCENARIO",
    "ScenarioStep",
]
