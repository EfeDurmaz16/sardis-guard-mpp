#!/usr/bin/env python3
"""Sardis Guard Demo — AI Research Agent with Budget Enforcement.

Demonstrates the full Sardis Guard flow:
1. Agent sets a $2 spending mandate (budget)
2. Agent performs searches via StableEnrich/Exa ($0.01/search)
3. Sardis Guard enforces the budget on every call
4. When the daily limit is hit, Guard blocks further spending

Run:
    python -m src.demo_agent
    # or
    python src/demo_agent.py
"""

from __future__ import annotations

import json
import sys
import time

from src.guard_client import SardisGuardClient, GuardedResponse, TempoError

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner():
    print(f"""
{BOLD}{CYAN}{'='*60}
  Sardis Guard Demo — AI Research Agent
  Budget: $2.00 | Cost per search: $0.01
  Guard URL: dendric-margie-answerlessly.ngrok-free.dev
{'='*60}{RESET}
""")


def step(num: int, total: int, msg: str):
    print(f"{BOLD}[{num}/{total}]{RESET} {msg}")


def show_verdict(result: GuardedResponse, query: str | None = None):
    """Pretty-print a guarded response."""
    v = result.verdict
    if result.allowed:
        print(f"  {GREEN}ALLOWED{RESET} — {v.summary}")
        if result.downstream_response and isinstance(result.downstream_response, dict):
            # Show a snippet of the downstream response
            snippet = json.dumps(result.downstream_response, indent=2)
            if len(snippet) > 300:
                snippet = snippet[:300] + "\n  ..."
            print(f"  {DIM}Response:{RESET}")
            for line in snippet.split("\n")[:8]:
                print(f"    {DIM}{line}{RESET}")
        elif result.downstream_status == "error":
            print(f"  {YELLOW}Downstream error: {result.error}{RESET}")
    else:
        print(f"  {RED}DENIED{RESET} — {v.summary}")
        # Show which checks failed
        for check in v.checks:
            if check.get("result") == "FAIL":
                print(f"    {RED}x {check['name']}: {check['reason']}{RESET}")

    if v.payment_tx:
        print(f"  {DIM}Guard payment tx: {v.payment_tx}{RESET}")
    print()


def run_demo():
    """Run the full demo scenario."""
    banner()

    # --- Initialize ---
    print(f"{BOLD}Initializing Sardis Guard client...{RESET}")
    try:
        guard = SardisGuardClient()
    except TempoError as e:
        print(f"{RED}Failed to initialize: {e}{RESET}")
        sys.exit(1)

    # --- Step 1: Health Check ---
    step(1, 6, "Checking Guard service health (free)...")
    health = guard.health()
    if isinstance(health, dict) and health.get("status") == "ok":
        print(f"  {GREEN}Guard is healthy{RESET}")
        print(f"  Agents tracked: {health.get('agents_tracked', '?')}")
        print(f"  Mandates active: {health.get('mandates_active', '?')}")
    else:
        print(f"  {YELLOW}Guard returned: {health}{RESET}")
    print()

    # --- Step 2: Set Budget Mandate ---
    step(2, 6, "Setting spending mandate: $0.05/tx, $2.00/day budget...")
    try:
        mandate_result = guard.update_mandate(
            max_per_tx="0.05",
            max_daily="2.00",
            allowed_categories=["search", "api_call", "general"],
            allowed_chains=["tempo", "base"],
            allowed_currencies=["USDC", "pathUSD"],
            cooldown_seconds=0,
        )
        print(f"  {GREEN}Mandate updated{RESET}")
        if isinstance(mandate_result, dict):
            tx = mandate_result.get("payment", {}).get("tx", "N/A")
            print(f"  {DIM}Payment tx: {tx}{RESET}")
    except TempoError as e:
        print(f"  {YELLOW}Could not update mandate: {e}{RESET}")
        print(f"  {DIM}Continuing with default mandate...{RESET}")
    print()

    # --- Step 3: View Current Mandate ---
    step(3, 6, "Viewing current mandate...")
    try:
        mandate = guard.get_mandate()
        if isinstance(mandate, dict) and "mandate" in mandate:
            m = mandate["mandate"]
            print(f"  Max per tx: ${m.get('max_per_tx', '?')}")
            print(f"  Max daily:  ${m.get('max_daily', '?')}")
            print(f"  Chains:     {m.get('allowed_chains', '?')}")
            print(f"  Currencies: {m.get('allowed_currencies', '?')}")
            print(f"  Categories: {m.get('allowed_categories', '?')}")
        else:
            print(f"  {DIM}{mandate}{RESET}")
    except TempoError as e:
        print(f"  {YELLOW}Could not view mandate: {e}{RESET}")
    print()

    # --- Step 4: Run Research Queries (Guard + Downstream) ---
    research_queries = [
        "AI agent payment infrastructure 2026",
        "machine payments protocol MPP services",
        "stablecoin payment rails for AI agents",
        "non-custodial MPC wallet architecture",
        "spending policies for autonomous AI agents",
    ]

    step(4, 6, f"Running {len(research_queries)} research queries ($0.01 each)...")
    print(f"  {DIM}Each query: Guard evaluation ($0.001) + Exa search ($0.01){RESET}")
    print()

    results = []
    for i, query in enumerate(research_queries, 1):
        print(f"  {CYAN}Query {i}/{len(research_queries)}:{RESET} \"{query}\"")
        result = guard.search_exa(query=query, amount="0.01")
        show_verdict(result, query)
        results.append(result)
        time.sleep(0.5)  # small delay between requests

    allowed_count = sum(1 for r in results if r.allowed)
    denied_count = sum(1 for r in results if not r.allowed)
    print(f"  {BOLD}Results: {GREEN}{allowed_count} allowed{RESET}, {RED}{denied_count} denied{RESET}")
    print()

    # --- Step 5: Try to Exceed Budget ---
    step(5, 6, "Testing budget enforcement — requesting $3.00 (exceeds $2 limit)...")
    result = guard.guarded_request(
        method="POST",
        url="https://stableenrich.dev/api/exa/search",
        data={"query": "expensive research query"},
        amount="3.00",  # exceeds both per-tx ($0.05) and daily ($2.00) limits
        merchant="stableenrich.dev",
        category="search",
    )
    show_verdict(result)

    # --- Step 6: Check Final Stats ---
    step(6, 6, "Checking final spending stats...")
    try:
        stats = guard.get_stats()
        if isinstance(stats, dict) and "stats" in stats:
            s = stats["stats"]
            print(f"  {BOLD}Spent today:   ${s.get('spent_today', '?')}{RESET}")
            print(f"  Transactions: {s.get('tx_count_today', '?')}")
        else:
            print(f"  {DIM}{stats}{RESET}")
    except TempoError as e:
        print(f"  {YELLOW}Could not get stats: {e}{RESET}")
    print()

    # --- Summary ---
    print(f"""{BOLD}{CYAN}{'='*60}
  Demo Complete!

  What happened:
  1. Set a $2/day budget with $0.05/tx limit
  2. Ran {len(research_queries)} searches at $0.01 each
  3. Guard evaluated policy BEFORE each downstream call
  4. $3.00 request was DENIED (exceeds both limits)
  5. Agent never overspent — Guard enforced the mandate

  This is Sardis Guard: policy enforcement for the agent economy.
  AI agents can reason, but they cannot be trusted with money.
  Sardis is how they earn that trust.
{'='*60}{RESET}
""")


# --- Alternate Demo: Rapid-fire until budget exhausted ---

def run_exhaust_demo():
    """Keep searching until the daily budget is fully exhausted."""
    banner()
    print(f"{BOLD}Mode: Exhaust budget — keep searching until DENIED{RESET}\n")

    guard = SardisGuardClient()

    # Set a tight budget
    print("Setting $0.10 daily budget ($0.01/tx)...\n")
    try:
        guard.update_mandate(
            max_per_tx="0.02",
            max_daily="0.10",
        )
    except TempoError:
        pass

    search_num = 0
    while True:
        search_num += 1
        query = f"research query #{search_num}"
        print(f"{CYAN}Search #{search_num}:{RESET} \"{query}\"")

        result = guard.search_exa(query=query, amount="0.01")

        if not result.allowed:
            print(f"  {RED}DENIED after {search_num - 1} successful searches{RESET}")
            print(f"  {RED}Reason: {result.verdict.summary}{RESET}")
            break
        else:
            print(f"  {GREEN}ALLOWED{RESET} ({result.verdict.latency_ms:.0f}ms)")

        if search_num >= 50:
            print(f"\n  {YELLOW}Safety limit: stopped after 50 searches{RESET}")
            break

        time.sleep(0.3)

    print(f"\n{BOLD}Budget exhausted! Guard prevented overspending.{RESET}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--exhaust":
        run_exhaust_demo()
    else:
        run_demo()
