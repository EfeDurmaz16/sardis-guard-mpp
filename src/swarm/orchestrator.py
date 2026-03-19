"""Sardis Guard — Swarm Orchestrator.

Runs multi-agent research scenarios through the Sardis Guard evaluation
pipeline, demonstrating mandate delegation, budget enforcement, and
attack detection.

Usage:
    from src.swarm.orchestrator import SwarmOrchestrator

    orch = SwarmOrchestrator()
    results = orch.run_benign_warmup()
    attack_results = orch.run_attack_scenario()
    orch.print_summary()
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.guard_client import SardisGuardClient, GuardedResponse, TempoError
from src.services.wrappers import (
    BrowserbaseService,
    PerplexityService,
    ServiceResult,
    StableEnrichService,
    TempoRPCService,
)
from src.services.registry import ServiceRegistry, default_registry
from src.swarm.scenarios import (
    ATTACK_SCENARIO,
    BENIGN_SCENARIO,
    ScenarioStep,
    get_scenario_summary,
)
from src.types import Action, MandateNode, MandateStatus, PaymentIntentEvent

logger = logging.getLogger("sardis_guard.swarm")

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class StepResult:
    """Result of executing a single scenario step."""

    step_index: int
    step: ScenarioStep
    # Guard evaluation
    guard_verdict: dict | None = None
    guard_allowed: bool = False
    guard_error: str | None = None
    # Downstream service call
    service_result: ServiceResult | None = None
    # Mandate state
    mandate_id: str = ""
    mandate_remaining: str = "0"
    # Timing
    total_latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "agent_role": self.step.agent_role,
            "service_id": self.step.service_id,
            "action": self.step.action,
            "description": self.step.description,
            "guard_allowed": self.guard_allowed,
            "guard_error": self.guard_error,
            "service_success": self.service_result.success if self.service_result else None,
            "cost": self.step.expected_cost,
            "mandate_id": self.mandate_id,
            "mandate_remaining": self.mandate_remaining,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "is_malicious": self.step.is_malicious,
            "attack_type": self.step.attack_type,
        }


class SwarmOrchestrator:
    """Orchestrates multi-agent scenarios through the Sardis Guard pipeline.

    Creates a mandate delegation tree:
        root_mandate (principal)
         +-- planner_mandate (child)
         +-- researcher_mandate (child)
         +-- scraper_mandate (child)
         +-- analyst_mandate (child)

    Each child mandate has its own budget, allowed services, and constraints.
    The orchestrator routes scenario steps to the appropriate child mandate
    and calls Guard.evaluate() before invoking the downstream service.
    """

    def __init__(
        self,
        guard_client: SardisGuardClient | None = None,
        registry: ServiceRegistry | None = None,
        principal_id: str = "principal_demo",
        root_budget: Decimal = Decimal("5.00"),
    ):
        # Guard client for policy evaluation
        try:
            self.guard = guard_client or SardisGuardClient()
        except TempoError:
            logger.warning("tempo CLI not found — orchestrator will run in dry-run mode")
            self.guard = None

        self.registry = registry or default_registry

        # Service wrappers
        self._services: dict[str, Any] = {}
        self._init_services()

        # Mandate tree
        self.principal_id = principal_id
        self.root_budget = root_budget
        self.mandates: dict[str, MandateNode] = {}
        self.agent_to_mandate: dict[str, str] = {}

        # Results
        self.results: list[StepResult] = []
        self.frozen_agents: set[str] = set()
        self.total_cost: float = 0.0

    def _init_services(self):
        """Initialize service wrappers (lazy — only tempo RPC is always available)."""
        try:
            self._services["stableenrich"] = StableEnrichService()
        except RuntimeError:
            logger.warning("tempo CLI not found — StableEnrich unavailable")
        try:
            self._services["browserbase"] = BrowserbaseService()
        except RuntimeError:
            logger.warning("tempo CLI not found — Browserbase unavailable")
        try:
            self._services["perplexity"] = PerplexityService()
        except RuntimeError:
            logger.warning("tempo CLI not found — Perplexity unavailable")

        # Tempo RPC always works (no MPP required)
        self._services["tempo-rpc"] = TempoRPCService()

    # ------------------------------------------------------------------
    # Mandate tree setup
    # ------------------------------------------------------------------

    def _create_mandate_tree(self):
        """Create root mandate + 4 child mandates for the swarm agents."""
        # Root mandate — owned by the principal
        root = MandateNode(
            mandate_id=f"mnd_root_{uuid.uuid4().hex[:8]}",
            parent_id=None,
            principal_id=self.principal_id,
            agent_id="swarm_root",
            max_total=self.root_budget,
            max_per_tx=Decimal("1.00"),
            remaining=self.root_budget,
            allowed_services=[],  # root can access everything
            allowed_chains=["tempo", "base"],
            allowed_currencies=["USDC", "pathUSD"],
            max_delegation_depth=3,
        )
        self.mandates[root.mandate_id] = root

        # Child mandates
        children = {
            "planner": {
                "max_total": Decimal("0.50"),
                "max_per_tx": Decimal("0.10"),
                "allowed_services": ["sardis-guard"],
                "description": "Planning and coordination",
            },
            "researcher": {
                "max_total": Decimal("2.00"),
                "max_per_tx": Decimal("0.10"),
                "allowed_services": ["stableenrich", "perplexity"],
                "description": "Web research and data gathering",
            },
            "scraper": {
                "max_total": Decimal("1.00"),
                "max_per_tx": Decimal("0.05"),
                "allowed_services": ["stableenrich", "browserbase"],
                "description": "Page scraping and data extraction",
            },
            "analyst": {
                "max_total": Decimal("1.50"),
                "max_per_tx": Decimal("0.10"),
                "allowed_services": ["tempo-rpc", "stableenrich"],
                "description": "On-chain analysis and data synthesis",
            },
        }

        for role, config in children.items():
            child = MandateNode(
                mandate_id=f"mnd_{role}_{uuid.uuid4().hex[:8]}",
                parent_id=root.mandate_id,
                principal_id=self.principal_id,
                agent_id=f"agent_{role}",
                max_total=config["max_total"],
                max_per_tx=config["max_per_tx"],
                remaining=config["max_total"],
                allowed_services=config["allowed_services"],
                allowed_chains=["tempo", "base"],
                allowed_currencies=["USDC", "pathUSD"],
                delegation_depth=1,
                max_delegation_depth=2,
            )
            self.mandates[child.mandate_id] = child
            self.agent_to_mandate[role] = child.mandate_id

        logger.info(
            "Created mandate tree: root (%s) + %d children",
            root.mandate_id,
            len(children),
        )

    def _get_mandate_for_agent(self, agent_role: str) -> MandateNode | None:
        """Get the mandate assigned to an agent role."""
        mandate_id = self.agent_to_mandate.get(agent_role)
        if mandate_id:
            return self.mandates.get(mandate_id)
        return None

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    def _execute_step(self, index: int, step: ScenarioStep) -> StepResult:
        """Execute a single scenario step through Guard + downstream service."""
        t0 = time.monotonic()

        # Get mandate for this agent
        mandate = self._get_mandate_for_agent(step.agent_role)
        mandate_id = mandate.mandate_id if mandate else "none"

        # Check if agent is frozen
        if step.agent_role in self.frozen_agents:
            return StepResult(
                step_index=index,
                step=step,
                guard_allowed=False,
                guard_error=f"Agent '{step.agent_role}' is frozen — all actions denied",
                mandate_id=mandate_id,
                mandate_remaining=str(mandate.remaining) if mandate else "0",
                total_latency_ms=(time.monotonic() - t0) * 1000,
            )

        # Check mandate budget locally first
        if mandate:
            amount = Decimal(str(step.expected_cost))
            can_spend, reason = mandate.can_spend(amount)
            if not can_spend:
                return StepResult(
                    step_index=index,
                    step=step,
                    guard_allowed=False,
                    guard_error=f"Mandate denied: {reason}",
                    mandate_id=mandate_id,
                    mandate_remaining=str(mandate.remaining),
                    total_latency_ms=(time.monotonic() - t0) * 1000,
                )

            # Check if service is in the child's allowed list
            if mandate.allowed_services and step.service_id not in mandate.allowed_services:
                return StepResult(
                    step_index=index,
                    step=step,
                    guard_allowed=False,
                    guard_error=f"Service '{step.service_id}' not in mandate allowed_services: {mandate.allowed_services}",
                    mandate_id=mandate_id,
                    mandate_remaining=str(mandate.remaining),
                    total_latency_ms=(time.monotonic() - t0) * 1000,
                )

        # Call Sardis Guard /evaluate (if available)
        guard_verdict = None
        guard_allowed = True
        guard_error = None

        if self.guard and step.expected_cost > 0:
            try:
                # Derive merchant from service registry
                meta = self.registry.get_or_unknown(step.service_id)
                merchant = meta.base_url or step.service_id

                verdict = self.guard.evaluate(
                    amount=str(step.expected_cost),
                    merchant=merchant,
                    currency="USDC",
                    network="tempo",
                    category=meta.category.value if hasattr(meta.category, "value") else "general",
                    memo=step.description,
                )
                guard_verdict = {
                    "allowed": verdict.allowed,
                    "summary": verdict.summary,
                    "checks_count": len(verdict.checks),
                    "latency_ms": verdict.latency_ms,
                }
                guard_allowed = verdict.allowed
                if not verdict.allowed:
                    guard_error = verdict.summary
            except TempoError as e:
                guard_error = f"Guard evaluation failed: {e}"
                # In production, fail-closed; for demo, allow to proceed
                guard_allowed = True
                logger.warning("Guard eval failed, proceeding anyway: %s", e)

        # If Guard denied, stop here
        if not guard_allowed:
            return StepResult(
                step_index=index,
                step=step,
                guard_verdict=guard_verdict,
                guard_allowed=False,
                guard_error=guard_error,
                mandate_id=mandate_id,
                mandate_remaining=str(mandate.remaining) if mandate else "0",
                total_latency_ms=(time.monotonic() - t0) * 1000,
            )

        # Execute the downstream service call
        service_result = self._call_service(step)

        # Record spend on mandate
        if mandate and step.expected_cost > 0:
            mandate.record_spend(Decimal(str(step.expected_cost)))
        self.total_cost += step.expected_cost

        return StepResult(
            step_index=index,
            step=step,
            guard_verdict=guard_verdict,
            guard_allowed=True,
            service_result=service_result,
            mandate_id=mandate_id,
            mandate_remaining=str(mandate.remaining) if mandate else "0",
            total_latency_ms=(time.monotonic() - t0) * 1000,
        )

    def _call_service(self, step: ScenarioStep) -> ServiceResult | None:
        """Call the actual downstream service."""
        svc = self._services.get(step.service_id)
        if svc is None:
            # Unknown service — return a synthetic failure
            return ServiceResult(
                service_id=step.service_id,
                action=step.action,
                success=False,
                error=f"Service '{step.service_id}' not available (not in wrapper registry)",
                cost=step.expected_cost,
            )

        try:
            if step.service_id == "stableenrich":
                if step.action == "exa_search":
                    return svc.exa_search(**step.params)
                elif step.action == "firecrawl_scrape":
                    return svc.firecrawl_scrape(**step.params)
                elif step.action == "apollo_people_search":
                    return svc.apollo_people_search(**step.params)
            elif step.service_id == "browserbase":
                if step.action == "search":
                    return svc.search(**step.params)
                elif step.action == "fetch":
                    return svc.fetch(**step.params)
            elif step.service_id == "perplexity":
                return svc.search(**step.params)
            elif step.service_id == "tempo-rpc":
                if step.action == "get_balance":
                    return svc.get_balance(**step.params)
                elif step.action == "get_block_number":
                    return svc.get_block_number()
                elif step.action == "get_tx_count":
                    return svc.get_tx_count(**step.params)
                elif step.action == "get_chain_id":
                    return svc.get_chain_id()

            return ServiceResult(
                service_id=step.service_id,
                action=step.action,
                success=False,
                error=f"Unknown action '{step.action}' for service '{step.service_id}'",
            )
        except Exception as e:
            return ServiceResult(
                service_id=step.service_id,
                action=step.action,
                success=False,
                error=str(e),
                cost=step.expected_cost,
            )

    # ------------------------------------------------------------------
    # Scenario runners
    # ------------------------------------------------------------------

    def run_benign_warmup(self, skip_expensive: bool = True) -> list[StepResult]:
        """Run the benign research scenario.

        Creates a mandate tree and executes normal research calls through Guard.

        Args:
            skip_expensive: If True, skip Perplexity calls ($0.05 each).

        Returns:
            List of StepResult for each step.
        """
        print(f"\n{BOLD}{CYAN}{'='*60}")
        print("  Sardis Guard — Benign Swarm Warmup")
        print(f"{'='*60}{RESET}\n")

        # Create mandate tree
        self._create_mandate_tree()
        self._print_mandate_tree()

        scenario = BENIGN_SCENARIO
        if skip_expensive:
            scenario = [s for s in scenario if s.service_id != "perplexity"]
            print(f"{DIM}(Skipping Perplexity calls — use skip_expensive=False to include){RESET}\n")

        summary = get_scenario_summary(scenario)
        print(f"  Steps: {summary['total_steps']}")
        print(f"  Agents: {', '.join(summary['agents'])}")
        print(f"  Services: {', '.join(summary['services'])}")
        print(f"  Estimated cost: ${summary['estimated_total_cost']:.4f}")
        print()

        results = []
        for i, step in enumerate(scenario):
            print(f"{BOLD}[Step {i+1}/{len(scenario)}]{RESET} "
                  f"{MAGENTA}{step.agent_role}{RESET} -> "
                  f"{CYAN}{step.service_id}/{step.action}{RESET}")
            print(f"  {DIM}{step.description}{RESET}")

            result = self._execute_step(i, step)
            results.append(result)

            if result.guard_allowed:
                svc_status = ""
                if result.service_result:
                    svc_status = f" | Service: {'OK' if result.service_result.success else 'FAIL'}"
                print(f"  {GREEN}ALLOWED{RESET} (mandate remaining: ${result.mandate_remaining}){svc_status}")
                if result.service_result and result.service_result.success:
                    data = result.service_result.data
                    if isinstance(data, dict):
                        preview = str(data)[:150]
                        print(f"  {DIM}Data: {preview}...{RESET}")
                    elif isinstance(data, str) and len(data) > 2:
                        print(f"  {DIM}Data: {data[:150]}...{RESET}")
            else:
                print(f"  {RED}DENIED{RESET} — {result.guard_error}")
            print()

        self.results.extend(results)
        self._print_benign_summary(results)
        return results

    def run_attack_scenario(self) -> list[StepResult]:
        """Run the attack scenario with a compromised agent.

        Simulates:
          1. Normal warmup call (blend in)
          2. Rapid burst of calls (velocity anomaly)
          3. Novel/unknown service access (novelty anomaly)
          4. Sanctioned address lookup (sanctions hit)
          5. Budget violation attempt

        Returns:
            List of StepResult for each step.
        """
        print(f"\n{BOLD}{RED}{'='*60}")
        print("  Sardis Guard — Attack Scenario")
        print(f"{'='*60}{RESET}\n")

        # Ensure mandate tree exists
        if not self.mandates:
            self._create_mandate_tree()
            self._print_mandate_tree()

        scenario = ATTACK_SCENARIO
        summary = get_scenario_summary(scenario)
        print(f"  Steps: {summary['total_steps']} ({summary['malicious_steps']} malicious)")
        print(f"  Agents: {', '.join(summary['agents'])}")
        print(f"  Attack types: burst, novel_service, sanctions, budget_violation")
        print()

        results = []
        for i, step in enumerate(scenario):
            marker = f"{RED}[ATTACK]{RESET} " if step.is_malicious else ""
            print(f"{BOLD}[Step {i+1}/{len(scenario)}]{RESET} {marker}"
                  f"{MAGENTA}{step.agent_role}{RESET} -> "
                  f"{CYAN}{step.service_id}/{step.action}{RESET}")
            print(f"  {DIM}{step.description}{RESET}")

            if step.is_malicious:
                print(f"  {YELLOW}Attack type: {step.attack_type}{RESET}")

            result = self._execute_step(i, step)
            results.append(result)

            if result.guard_allowed:
                svc_status = ""
                if result.service_result:
                    svc_status = f" | Service: {'OK' if result.service_result.success else 'FAIL'}"
                print(f"  {GREEN}ALLOWED{RESET} (remaining: ${result.mandate_remaining}){svc_status}")
            else:
                print(f"  {RED}DENIED{RESET} — {result.guard_error}")
                # Check if this is a sanctions/freeze action
                if step.attack_type == "sanctions":
                    self.frozen_agents.add(step.agent_role)
                    print(f"  {RED}{BOLD}AGENT FROZEN: {step.agent_role}{RESET}")
            print()

            # Small delay between burst calls for realism (but fast)
            if step.attack_type == "burst":
                import time as _t
                _t.sleep(0.1)  # 100ms between burst calls — still fast

        self.results.extend(results)
        self._print_attack_summary(results)
        return results

    # ------------------------------------------------------------------
    # Pretty printing
    # ------------------------------------------------------------------

    def _print_mandate_tree(self):
        """Print the mandate delegation tree."""
        print(f"{BOLD}Mandate Delegation Tree:{RESET}")
        root = next((m for m in self.mandates.values() if m.parent_id is None), None)
        if not root:
            print("  (no root mandate)")
            return

        print(f"  {CYAN}{root.mandate_id}{RESET} (root)")
        print(f"    Budget: ${root.max_total} | Per-tx: ${root.max_per_tx}")
        print(f"    Agent: {root.agent_id}")

        for mandate in self.mandates.values():
            if mandate.parent_id == root.mandate_id:
                role = mandate.agent_id.replace("agent_", "")
                print(f"  +-- {MAGENTA}{mandate.mandate_id}{RESET} ({role})")
                print(f"      Budget: ${mandate.max_total} | Per-tx: ${mandate.max_per_tx}")
                svcs = ", ".join(mandate.allowed_services) if mandate.allowed_services else "all"
                print(f"      Services: {svcs}")
        print()

    def _print_benign_summary(self, results: list[StepResult]):
        """Print summary of benign scenario."""
        allowed = sum(1 for r in results if r.guard_allowed)
        denied = sum(1 for r in results if not r.guard_allowed)
        svc_ok = sum(1 for r in results if r.service_result and r.service_result.success)
        svc_fail = sum(1 for r in results if r.service_result and not r.service_result.success)
        cost = sum(r.step.expected_cost for r in results if r.guard_allowed)

        print(f"{BOLD}{CYAN}{'─'*60}")
        print(f"  Benign Scenario Summary")
        print(f"{'─'*60}{RESET}")
        print(f"  Guard:    {GREEN}{allowed} allowed{RESET}, {RED}{denied} denied{RESET}")
        print(f"  Services: {GREEN}{svc_ok} succeeded{RESET}, {RED}{svc_fail} failed{RESET}")
        print(f"  Cost:     ${cost:.4f}")
        print(f"  Mandates: {len(self.mandates)} active")
        print()

    def _print_attack_summary(self, results: list[StepResult]):
        """Print summary of attack scenario."""
        allowed = sum(1 for r in results if r.guard_allowed)
        denied = sum(1 for r in results if not r.guard_allowed)
        malicious_allowed = sum(1 for r in results if r.step.is_malicious and r.guard_allowed)
        malicious_denied = sum(1 for r in results if r.step.is_malicious and not r.guard_allowed)

        print(f"{BOLD}{RED}{'─'*60}")
        print(f"  Attack Scenario Summary")
        print(f"{'─'*60}{RESET}")
        print(f"  Total:     {GREEN}{allowed} allowed{RESET}, {RED}{denied} denied{RESET}")
        print(f"  Malicious: {RED}{malicious_allowed} slipped through{RESET}, "
              f"{GREEN}{malicious_denied} caught{RESET}")
        print(f"  Frozen agents: {', '.join(self.frozen_agents) or 'none'}")

        # Breakdown by attack type
        attack_types: dict[str, dict] = {}
        for r in results:
            if r.step.is_malicious:
                at = r.step.attack_type
                if at not in attack_types:
                    attack_types[at] = {"allowed": 0, "denied": 0}
                if r.guard_allowed:
                    attack_types[at]["allowed"] += 1
                else:
                    attack_types[at]["denied"] += 1

        if attack_types:
            print(f"\n  {BOLD}Attack type breakdown:{RESET}")
            for at, counts in attack_types.items():
                status = f"{GREEN}CAUGHT{RESET}" if counts["denied"] > 0 else f"{RED}MISSED{RESET}"
                print(f"    {at}: {counts['allowed']} allowed, {counts['denied']} denied — {status}")
        print()

    def print_summary(self):
        """Print overall orchestrator summary."""
        print(f"\n{BOLD}{'='*60}")
        print(f"  Swarm Orchestrator — Overall Summary")
        print(f"{'='*60}{RESET}")
        print(f"  Total steps executed: {len(self.results)}")
        print(f"  Total cost: ${self.total_cost:.4f}")
        print(f"  Mandates created: {len(self.mandates)}")
        print(f"  Frozen agents: {', '.join(self.frozen_agents) or 'none'}")

        # Mandate budget usage
        print(f"\n  {BOLD}Mandate Budget Usage:{RESET}")
        for mandate in self.mandates.values():
            if mandate.parent_id is not None:  # only children
                role = mandate.agent_id.replace("agent_", "")
                pct = (mandate.spent / mandate.max_total * 100) if mandate.max_total > 0 else 0
                bar_len = int(pct / 5)
                bar = f"{'#' * bar_len}{'.' * (20 - bar_len)}"
                status = mandate.status.value
                print(f"    {role:12s} [{bar}] ${str(mandate.spent):>6s}/{mandate.max_total} ({pct:.0f}%) [{status}]")
        print()

    def get_results_dict(self) -> dict:
        """Return all results as a serializable dict."""
        return {
            "total_steps": len(self.results),
            "total_cost": round(self.total_cost, 4),
            "frozen_agents": list(self.frozen_agents),
            "mandates": {
                mid: m.to_dict() for mid, m in self.mandates.items()
            },
            "results": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    orch = SwarmOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1] == "--attack":
        orch.run_benign_warmup(skip_expensive=True)
        orch.run_attack_scenario()
    elif len(sys.argv) > 1 and sys.argv[1] == "--attack-only":
        orch.run_attack_scenario()
    else:
        orch.run_benign_warmup(skip_expensive=True)

    orch.print_summary()
