"""Sardis Guard MCP Server — Model Context Protocol interface for AI agent policy evaluation.

Exposes Sardis Guard's 8-gate security pipeline, OFAC sanctions screening, mandate
governance, and emergency controls as MCP tools for Claude Desktop, Cursor, and
other MCP-compatible clients.

Usage:
    python src/mcp_server.py

Configure in Claude Desktop / Cursor:
    {
      "mcpServers": {
        "sardis-guard": {
          "command": "python",
          "args": ["src/mcp_server.py"],
          "cwd": "/path/to/sardis-mpp-hackathon"
        }
      }
    }
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("sardis_guard_mcp")

# Guard API base URL (Cloud Run deployment)
GUARD_BASE_URL = os.environ.get(
    "SARDIS_GUARD_URL",
    "https://sardis-guard-482463483786.us-central1.run.app",
).rstrip("/")

# Tempo CLI path (needed for MPP-gated endpoints like /evaluate/v2)
TEMPO_PATH = os.environ.get("TEMPO_PATH") or shutil.which("tempo")

# HTTP client for free endpoints
_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    """Lazy-init a shared httpx client for free Guard endpoints."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            base_url=GUARD_BASE_URL,
            timeout=15.0,
            headers={"User-Agent": "sardis-guard-mcp/1.0"},
        )
    return _http_client


def _tempo_request(method: str, url: str, data: dict | None = None) -> dict | str:
    """Call an MPP-gated endpoint via the tempo CLI.

    The tempo CLI handles wallet key management and the 402 payment flow
    transparently, so the MCP server does not need to manage keys.

    Args:
        method: HTTP method (GET, POST).
        url: Full URL to call.
        data: JSON body for POST requests.

    Returns:
        Parsed JSON dict, or raw string on parse failure.

    Raises:
        RuntimeError: If tempo CLI is not found or the request fails.
    """
    if not TEMPO_PATH:
        raise RuntimeError(
            "tempo CLI not found. Install from https://docs.tempo.xyz/cli "
            "or set TEMPO_PATH env var."
        )

    cmd = [TEMPO_PATH, "request", "-j", "-X", method.upper()]

    if data is not None and method.upper() in ("POST", "PUT", "PATCH"):
        cmd.extend(["--json", json.dumps(data)])

    cmd.extend(["-m", "30"])
    cmd.append(url)

    logger.debug("tempo command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=40,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("tempo request timed out after 40s")
    except FileNotFoundError:
        raise RuntimeError(f"tempo CLI not found at {TEMPO_PATH}")

    output = result.stdout.strip()

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"tempo request failed (exit {result.returncode}): {stderr or output}"
        )

    # Parse JSON from output (tempo may prepend payment info lines)
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Try to extract the last JSON object from mixed output
        for line in reversed(output.split("\n")):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return output


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "sardis-guard",
    instructions=(
        "Sardis Guard is the financial intelligence and governance platform for AI agent payments. "
        "Use these tools to evaluate payments against an 8-gate security pipeline, screen wallets "
        "and entities for OFAC sanctions, manage hierarchical spending mandates, and activate "
        "emergency kill switches. All screening and mandate tools are free. The evaluate_payment "
        "tool requires a funded tempo wallet for MPP micropayments ($0.001/call)."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: evaluate_payment
# ---------------------------------------------------------------------------

@mcp.tool()
def evaluate_payment(
    amount: str,
    merchant: str,
    currency: str = "USDC",
    network: str = "tempo",
    category: str = "general",
    agent_id: str = "",
    mandate_id: str = "",
) -> str:
    """Evaluate a payment against Sardis Guard's 8-gate security pipeline.

    Runs the full intelligence pipeline: kill-switch check, dedup/replay protection,
    governance (mandate chain), OFAC sanctions screening, ML anomaly detection
    (IsolationForest + Markov + cross-agent correlation), and risk scoring.

    This is an MPP-gated endpoint -- requires a funded tempo wallet ($0.001/call).

    Args:
        amount: Payment amount as a string, e.g. "1.50".
        merchant: Merchant URL or identifier, e.g. "stableenrich.dev".
        currency: Payment currency (default "USDC"). Also supports "pathUSD", "EURC", "USDT".
        network: Blockchain network (default "tempo"). Also supports "base", "ethereum", "polygon", etc.
        category: Spending category, e.g. "general", "search", "api_call", "compute".
        agent_id: Optional agent identifier for governance tracking.
        mandate_id: Optional mandate ID to evaluate against a specific spending mandate.

    Returns:
        JSON with action (ALLOW/FLAG/HOLD/FREEZE/DENY), risk scores, governance result,
        AML screening, and payment receipt.
    """
    payload = {
        "amount": amount,
        "merchant": merchant,
        "currency": currency,
        "network": network,
        "category": category,
    }
    if agent_id:
        payload["agent_id"] = agent_id
    if mandate_id:
        payload["mandate_id"] = mandate_id

    try:
        result = _tempo_request("POST", f"{GUARD_BASE_URL}/evaluate/v2", data=payload)
        return json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
    except RuntimeError as e:
        return json.dumps({"error": str(e), "hint": "Ensure tempo CLI is installed and wallet is funded."})


# ---------------------------------------------------------------------------
# Tool 2: screen_address
# ---------------------------------------------------------------------------

@mcp.tool()
def screen_address(address: str) -> str:
    """Screen a wallet address against OFAC sanctions lists.

    Checks the address against the US Treasury OFAC SDN list and other sanctions
    databases. Returns whether the address is sanctioned, with match details and
    confidence score.

    This is a free endpoint -- no MPP payment required.

    Args:
        address: Blockchain wallet address to screen (e.g. "0x1234...abcd").

    Returns:
        JSON with hit (bool), matched_entry, match_type, list_source, and confidence.
    """
    client = _get_http_client()
    try:
        resp = client.post("/screen/address", json={"address": address})
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}", "address": address})


# ---------------------------------------------------------------------------
# Tool 3: screen_entity
# ---------------------------------------------------------------------------

@mcp.tool()
def screen_entity(name: str) -> str:
    """Screen an entity name against sanctions and watchlists.

    Performs fuzzy matching against OFAC SDN, EU consolidated sanctions, and UN
    sanctions lists. Useful for checking merchant names, organization names, or
    individual names before transacting.

    This is a free endpoint -- no MPP payment required.

    Args:
        name: Entity name to screen (e.g. "Tornado Cash", "Lazarus Group").

    Returns:
        JSON with hit (bool), match_type (exact/fuzzy/none), matched_entry,
        list_source, and confidence score.
    """
    client = _get_http_client()
    try:
        resp = client.post("/screen/entity", json={"name": name})
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}", "name": name})


# ---------------------------------------------------------------------------
# Tool 4: create_mandate
# ---------------------------------------------------------------------------

@mcp.tool()
def create_mandate(
    principal_id: str,
    agent_id: str,
    max_total: str = "100",
    max_per_tx: str = "10",
    allowed_services: list[str] | None = None,
) -> str:
    """Create a root spending mandate for an AI agent.

    A mandate defines the spending authority envelope: how much the agent can spend
    in total, per transaction, which services/merchants it can access, and on which
    chains/currencies. The mandate is the core governance primitive in Sardis.

    This is a free endpoint -- no MPP payment required.

    Args:
        principal_id: The human principal granting spending authority (e.g. "user_123").
        agent_id: The AI agent receiving spending authority (e.g. "agent_research_001").
        max_total: Maximum total budget in USD (default "100").
        max_per_tx: Maximum per-transaction limit in USD (default "10").
        allowed_services: Optional list of allowed service identifiers (empty = all allowed).

    Returns:
        JSON with the created mandate details including mandate_id, status, and full config.
    """
    payload = {
        "principal_id": principal_id,
        "agent_id": agent_id,
        "max_total": max_total,
        "max_per_tx": max_per_tx,
        "allowed_services": allowed_services or [],
    }
    client = _get_http_client()
    try:
        resp = client.post("/mandates/root", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}"})


# ---------------------------------------------------------------------------
# Tool 5: delegate_mandate
# ---------------------------------------------------------------------------

@mcp.tool()
def delegate_mandate(
    parent_mandate_id: str,
    agent_id: str,
    max_total: str = "25",
    max_per_tx: str = "5",
) -> str:
    """Delegate a child mandate from an existing parent mandate.

    Creates a sub-mandate with reduced authority. The child mandate's budget
    cannot exceed the parent's remaining budget, and restrictions are inherited
    (intersection of parent and child scopes). Supports up to 3 levels of
    delegation depth.

    This is a free endpoint -- no MPP payment required.

    Args:
        parent_mandate_id: The parent mandate ID to delegate from (e.g. "mnd_abc123def456").
        agent_id: The sub-agent receiving delegated authority (e.g. "agent_sub_task_002").
        max_total: Maximum total budget for the child (default "25").
        max_per_tx: Maximum per-transaction limit for the child (default "5").

    Returns:
        JSON with the child mandate details including mandate_id and full config.
    """
    payload = {
        "parent_mandate_id": parent_mandate_id,
        "agent_id": agent_id,
        "max_total": max_total,
        "max_per_tx": max_per_tx,
    }
    client = _get_http_client()
    try:
        resp = client.post("/mandates/delegate", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}"})


# ---------------------------------------------------------------------------
# Tool 6: freeze_mandate
# ---------------------------------------------------------------------------

@mcp.tool()
def freeze_mandate(
    mandate_id: str,
    reason: str = "Manual freeze",
    freeze_children: bool = False,
) -> str:
    """Freeze a spending mandate (emergency governance action).

    Immediately halts all spending under the mandate. If freeze_children is True,
    all child mandates in the delegation tree are also frozen (cascade freeze).
    Frozen mandates can be resumed later with the resume endpoint.

    This is a free endpoint -- no MPP payment required.

    Args:
        mandate_id: The mandate ID to freeze (e.g. "mnd_abc123def456").
        reason: Human-readable reason for the freeze (e.g. "Suspicious activity detected").
        freeze_children: If True, freeze all child mandates in the delegation tree.

    Returns:
        JSON confirming the freeze with updated mandate details.
    """
    payload = {
        "mandate_id": mandate_id,
        "reason": reason,
        "freeze_children": freeze_children,
    }
    client = _get_http_client()
    try:
        resp = client.post("/mandates/freeze", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}"})


# ---------------------------------------------------------------------------
# Tool 7: check_health
# ---------------------------------------------------------------------------

@mcp.tool()
def check_health() -> str:
    """Check Sardis Guard service health and status.

    Returns the operational status of the Guard service, number of tracked agents,
    and active mandates. Use this to verify the service is reachable before making
    other calls.

    This is a free endpoint -- no MPP payment required.

    Returns:
        JSON with status ("ok"/"error"), agents_tracked count, and mandates_active count.
    """
    client = _get_http_client()
    try:
        resp = client.get("/health")
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"status": "error", "detail": str(e)})


# ---------------------------------------------------------------------------
# Tool 8: activate_kill_switch
# ---------------------------------------------------------------------------

@mcp.tool()
def activate_kill_switch(
    scope: str,
    target: str = "",
    reason: str = "Emergency activation",
) -> str:
    """Activate an emergency kill switch to immediately halt payments.

    This is the nuclear option -- use only in genuine emergencies (compromised agent,
    detected exploit, sanctions hit, etc.). Kill switches take priority over all other
    checks in the evaluation pipeline (Gate 1).

    Scopes:
    - "global": Halts ALL payments across the entire platform.
    - "org": Halts all payments for a specific organization.
    - "agent": Halts all payments for a specific agent.
    - "chain": Halts all payments on a specific blockchain network.

    This is a free endpoint -- no MPP payment required.

    Args:
        scope: Kill switch scope -- one of "global", "org", "agent", "chain".
        target: The target identifier (org_id, agent_id, or chain name). Required for
            non-global scopes, ignored for "global".
        reason: Human-readable reason for activation (logged in audit trail).

    Returns:
        JSON confirming activation with scope, target, reason, and optional auto-lift time.
    """
    if scope not in ("global", "org", "agent", "chain"):
        return json.dumps({"error": f"Invalid scope '{scope}'. Must be one of: global, org, agent, chain."})

    payload = {
        "scope": scope,
        "target": target,
        "reason": reason,
    }
    client = _get_http_client()
    try:
        resp = client.post("/kill-switch/activate", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except httpx.HTTPError as e:
        return json.dumps({"error": f"HTTP error: {e}"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Starting Sardis Guard MCP server...")
    logger.info("Guard API: %s", GUARD_BASE_URL)
    logger.info("Tempo CLI: %s", TEMPO_PATH or "NOT FOUND (MPP-gated tools will fail)")
    mcp.run()
