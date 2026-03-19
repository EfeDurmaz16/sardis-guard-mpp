"""Sardis Guard Intelligence Plane — Financial Intelligence for AI Agent Payments.

An MPP-native service that combines:
- 12-check policy evaluation
- ML-based anomaly detection (IsolationForest + Markov + cross-agent correlation)
- OFAC sanctions screening
- Mandate-chain governance with delegation + freeze propagation
- Hash-chained audit trail with evidence packs

Flow: Agent → HTTP 402 → Sardis Guard (pay $0.001) → Intelligence Pipeline → ALLOW/FLAG/HOLD/FREEZE/DENY
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from mpp import Challenge, Credential, Receipt
from mpp.methods.tempo import ChargeIntent, tempo
from mpp.methods.tempo._defaults import CHAIN_ID, TESTNET_CHAIN_ID, USDC, PATH_USD
from mpp.server import Mpp
from mpp.store import MemoryStore

# fastapi-mpp: decorator-based MPP integration (proof of concept)
try:
    from mpp_fastapi import MPP as FastAPIMPP
    from mpp_fastapi.dependencies import WalletConfig
    _HAS_FASTAPI_MPP = True
except ImportError:
    _HAS_FASTAPI_MPP = False
    FastAPIMPP = None
    WalletConfig = None

# Use mainnet by default (wallet is on mainnet), testnet if SARDIS_TESTNET=1
USE_TESTNET = os.environ.get("SARDIS_TESTNET", "0") == "1"
ACTIVE_CHAIN_ID = TESTNET_CHAIN_ID if USE_TESTNET else CHAIN_ID
ACTIVE_CURRENCY = PATH_USD if USE_TESTNET else USDC

from src.policy import (
    AgentState,
    PolicyVerdict,
    SpendingMandate,
    evaluate_policy,
)

logger = logging.getLogger("sardis_guard")

# --- Config ---
WALLET_ADDRESS = os.environ.get(
    "SARDIS_WALLET", "0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c"
)
MPP_SECRET = os.environ.get("MPP_SECRET_KEY", secrets.token_hex(32))
REALM = os.environ.get("MPP_REALM", "guard.sardis.sh")

# --- App ---
app = FastAPI(
    title="Sardis Guard Intelligence Plane",
    description="Financial intelligence and governance platform for AI agent payments. "
    "ML anomaly detection, OFAC sanctions screening, mandate-chain governance, "
    "and evidence-grade audit trails — all via MPP.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MPP Server ---
mpp_server = Mpp.create(
    method=tempo(
        chain_id=ACTIVE_CHAIN_ID,
        currency=ACTIVE_CURRENCY,
        recipient=WALLET_ADDRESS,
        intents={"charge": ChargeIntent(store=MemoryStore())},
    ),
    realm=REALM,
    secret_key=MPP_SECRET,
)

# --- fastapi-mpp decorator instance (proof of concept for /evaluate) ---
mpp_decorator = None
if _HAS_FASTAPI_MPP and FastAPIMPP and WalletConfig:
    mpp_decorator = FastAPIMPP(
        wallet_config=WalletConfig(
        tempo_wallet_url=WALLET_ADDRESS,
        session_secret=MPP_SECRET,
    ),
    realm=REALM,
    debug_mode=True,
    weak_debug_validation=True,
)

# --- Intelligence Modules ---
# Initialize on startup to avoid import errors if modules aren't ready yet
_risk_engine = None
_event_store = None
_sanctions_screener = None
_mandate_store = None
_governance_engine = None


def _init_intelligence():
    """Lazy-init intelligence modules. Called on first request or startup."""
    global _risk_engine, _event_store, _sanctions_screener, _mandate_store, _governance_engine

    if _event_store is not None:
        return  # already initialized

    try:
        from src.storage.event_store import EventStore
        _event_store = EventStore()
        logger.info("EventStore initialized (SQLite + DuckDB)")
    except Exception as e:
        logger.warning("EventStore not available: %s", e)

    try:
        from src.risk.engine import RiskEngine
        _risk_engine = RiskEngine(event_store=_event_store)
        logger.info("RiskEngine initialized (IsolationForest + Markov)")
    except Exception as e:
        logger.warning("RiskEngine not available: %s", e)

    try:
        from src.compliance.sanctions import SanctionsScreener
        _sanctions_screener = SanctionsScreener()
        logger.info("SanctionsScreener initialized (%d addresses)", len(_sanctions_screener.addresses))
    except Exception as e:
        logger.warning("SanctionsScreener not available: %s", e)

    try:
        from src.mandates.mandate_store import MandateStore
        _mandate_store = MandateStore()
        logger.info("MandateStore initialized")
    except Exception as e:
        logger.warning("MandateStore not available: %s", e)

    try:
        from src.governance.engine import GovernanceEngine
        _governance_engine = GovernanceEngine(store=_mandate_store)
        logger.info("GovernanceEngine initialized")
    except Exception as e:
        logger.warning("GovernanceEngine not available: %s", e)

    # Mount V2 routes
    try:
        from src.routes_v2 import router as v2_router, _init as v2_init
        v2_init(
            _mandate_store, _governance_engine, _risk_engine,
            _sanctions_screener, _event_store, mpp_server,
            sse_queue, REALM, ACTIVE_CHAIN_ID,
        )
        app.include_router(v2_router)
        logger.info("V2 routes mounted")
    except Exception as e:
        logger.warning("V2 routes not available: %s", e)


@app.on_event("startup")
async def startup():
    _init_intelligence()


# --- In-memory agent state (per-agent spending tracker) ---
agent_states: dict[str, AgentState] = {}
agent_mandates: dict[str, SpendingMandate] = {}

# --- Audit log & SSE broadcasting ---
audit_log: list[dict] = []
sse_queue: asyncio.Queue[dict] = asyncio.Queue()

# Default mandate for unregistered agents
DEFAULT_MANDATE = SpendingMandate(
    max_per_tx=Decimal("5.00"),
    max_daily=Decimal("50.00"),
    allowed_chains=["tempo", "base", "ethereum", "polygon", "arbitrum", "optimism"],
    allowed_currencies=["USDC", "pathUSD", "EURC", "USDT"],
)


# --- Request Models ---
class PolicyRequest(BaseModel):
    """Request to evaluate a payment against the policy engine."""

    amount: str  # e.g. "1.50"
    merchant: str  # merchant URL or identifier
    currency: str = "USDC"
    network: str = "tempo"
    category: str = "general"
    memo: str | None = None
    gas_price_gwei: str | None = None


class MandateUpdate(BaseModel):
    """Update a spending mandate for an agent."""

    max_per_tx: str | None = None
    max_daily: str | None = None
    allowed_merchants: list[str] | None = None
    blocked_merchants: list[str] | None = None
    allowed_categories: list[str] | None = None
    blocked_categories: list[str] | None = None
    allowed_chains: list[str] | None = None
    allowed_currencies: list[str] | None = None
    require_memo: bool | None = None
    cooldown_seconds: int | None = None


# --- Free Endpoints ---


@app.get("/")
async def root():
    modules = {
        "risk_engine": _risk_engine is not None,
        "event_store": _event_store is not None,
        "sanctions_screener": _sanctions_screener is not None,
        "mandate_store": _mandate_store is not None,
        "governance_engine": _governance_engine is not None,
    }
    return {
        "service": "Sardis Guard Intelligence Plane",
        "version": "0.2.0",
        "description": "Financial intelligence and governance for AI agent payments — "
        "ML anomaly detection, OFAC sanctions, mandate chains, evidence-grade audit trails",
        "modules": modules,
        "endpoints": {
            "--- Policy (MPP-gated) ---": "",
            "/evaluate": "POST — 12-check policy evaluation ($0.001/call)",
            "/evaluate/v2": "POST — Full intelligence pipeline ($0.001/call)",
            "/simulate": "POST — Dry-run policy ($0.0005/call)",
            "--- Governance (free) ---": "",
            "/mandates/root": "POST — Create root mandate",
            "/mandates/delegate": "POST — Delegate child mandate",
            "/mandates/freeze": "POST — Freeze mandate",
            "/mandates/resume": "POST — Resume mandate",
            "/mandates": "GET — List all mandates",
            "--- Screening (free) ---": "",
            "/screen/entity": "POST — Screen entity against sanctions",
            "/screen/address": "POST — Screen address against OFAC",
            "--- Dashboard (free) ---": "",
            "/dashboard/summary": "GET — Aggregate stats",
            "/dashboard/graph": "GET — Service transition graph",
            "/agents/{id}/risk": "GET — Agent risk timeline",
            "/reports/session/{id}": "GET — Evidence pack",
            "--- Legacy (MPP-gated) ---": "",
            "/mandate": "GET — View mandate ($0.0001/call)",
            "/stats": "GET — Spending stats ($0.0001/call)",
            "/audit": "GET — Audit trail ($0.001/call)",
            "/stream": "GET — SSE live feed (free)",
            "/health": "GET — Health check (free)",
        },
        "protocol": "MPP (Machine Payments Protocol)",
        "payment_method": "Tempo pathUSD (testnet)",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents_tracked": len(agent_states),
        "mandates_active": len(agent_mandates),
    }


# --- Paid Endpoints (MPP-gated) ---


@app.post("/evaluate")
async def evaluate(request: Request, body: PolicyRequest):
    """Evaluate a payment against the 12-check policy engine. Costs $0.001 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.001",
        chain_id=ACTIVE_CHAIN_ID,
        description="Sardis Guard policy evaluation",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Policy evaluation costs $0.001 per call via MPP",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"
    receipt_ref = receipt.reference

    # Get or create agent state + mandate
    state = agent_states.setdefault(agent_id, AgentState())
    mandate = agent_mandates.get(agent_id, DEFAULT_MANDATE)

    # Run 12-check policy
    verdict = evaluate_policy(
        amount=Decimal(body.amount),
        merchant=body.merchant,
        currency=body.currency,
        network=body.network,
        category=body.category,
        memo=body.memo,
        gas_price_gwei=Decimal(body.gas_price_gwei) if body.gas_price_gwei else None,
        mandate=mandate,
        agent_state=state,
    )

    # Update agent state if allowed
    if verdict.allowed:
        state.spent_today += Decimal(body.amount)
        state.tx_count_today += 1
        state.last_payment_ts = time.time()

    # Record audit entry and broadcast to SSE listeners
    entry = {
        "timestamp": time.time(),
        "agent": agent_id,
        "merchant": body.merchant,
        "amount": body.amount,
        "currency": body.currency,
        "network": body.network,
        "category": body.category,
        "verdict": verdict.to_dict(),
        "type": "evaluate",
    }
    audit_log.append(entry)
    await sse_queue.put(entry)

    return {
        "verdict": verdict.to_dict(),
        "agent": agent_id,
        "payment": {
            "tx": receipt_ref,
            "method": "tempo",
            "amount_charged": "0.001",
            "currency": "pathUSD",
        },
    }


@app.get("/mandate")
async def get_mandate(request: Request):
    """View the current spending mandate. Costs $0.0001 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.0001",
        chain_id=ACTIVE_CHAIN_ID,
        description="View spending mandate",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Viewing mandate costs $0.0001 via MPP",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"
    mandate = agent_mandates.get(agent_id, DEFAULT_MANDATE)

    return JSONResponse(
        content={
            "agent": agent_id,
            "mandate": {
                "max_per_tx": str(mandate.max_per_tx),
                "max_daily": str(mandate.max_daily),
                "allowed_merchants": mandate.allowed_merchants,
                "blocked_merchants": mandate.blocked_merchants,
                "allowed_categories": mandate.allowed_categories,
                "blocked_categories": mandate.blocked_categories,
                "allowed_chains": mandate.allowed_chains,
                "allowed_currencies": mandate.allowed_currencies,
                "require_memo": mandate.require_memo,
                "cooldown_seconds": mandate.cooldown_seconds,
                "active": mandate.active,
            },
            "payment": {"tx": receipt.reference},
        },
        headers={"Payment-Receipt": receipt.reference},
    )


@app.put("/mandate")
async def update_mandate(request: Request, body: MandateUpdate):
    """Update the spending mandate. Costs $0.001 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.001",
        chain_id=ACTIVE_CHAIN_ID,
        description="Update spending mandate",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Updating mandate costs $0.001 via MPP",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"
    mandate = agent_mandates.get(agent_id, SpendingMandate())

    # Apply updates
    if body.max_per_tx is not None:
        mandate.max_per_tx = Decimal(body.max_per_tx)
    if body.max_daily is not None:
        mandate.max_daily = Decimal(body.max_daily)
    if body.allowed_merchants is not None:
        mandate.allowed_merchants = body.allowed_merchants
    if body.blocked_merchants is not None:
        mandate.blocked_merchants = body.blocked_merchants
    if body.allowed_categories is not None:
        mandate.allowed_categories = body.allowed_categories
    if body.blocked_categories is not None:
        mandate.blocked_categories = body.blocked_categories
    if body.allowed_chains is not None:
        mandate.allowed_chains = body.allowed_chains
    if body.allowed_currencies is not None:
        mandate.allowed_currencies = body.allowed_currencies
    if body.require_memo is not None:
        mandate.require_memo = body.require_memo
    if body.cooldown_seconds is not None:
        mandate.cooldown_seconds = body.cooldown_seconds

    agent_mandates[agent_id] = mandate

    return JSONResponse(
        content={
            "agent": agent_id,
            "mandate_updated": True,
            "payment": {"tx": receipt.reference},
        },
        headers={"Payment-Receipt": receipt.reference},
    )


@app.get("/stats")
async def get_stats(request: Request):
    """Get agent spending stats. Costs $0.0001 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.0001",
        chain_id=ACTIVE_CHAIN_ID,
        description="View spending stats",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Stats costs $0.0001 via MPP",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"
    state = agent_states.get(agent_id, AgentState())

    return JSONResponse(
        content={
            "agent": agent_id,
            "stats": {
                "spent_today": str(state.spent_today),
                "tx_count_today": state.tx_count_today,
                "last_payment_ts": state.last_payment_ts,
            },
            "payment": {"tx": receipt.reference},
        },
        headers={"Payment-Receipt": receipt.reference},
    )


# --- New Endpoints ---


@app.post("/simulate")
async def simulate(request: Request, body: PolicyRequest):
    """Dry-run policy evaluation — no state mutation. Costs $0.0005 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.0005",
        chain_id=ACTIVE_CHAIN_ID,
        description="Sardis Guard policy simulation (dry-run)",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Policy simulation costs $0.0005 per call via MPP",
                "service": "sardis-guard",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"

    # Read state without mutating — use a snapshot for evaluation
    state = agent_states.get(agent_id, AgentState())
    mandate = agent_mandates.get(agent_id, DEFAULT_MANDATE)

    verdict = evaluate_policy(
        amount=Decimal(body.amount),
        merchant=body.merchant,
        currency=body.currency,
        network=body.network,
        category=body.category,
        memo=body.memo,
        gas_price_gwei=Decimal(body.gas_price_gwei) if body.gas_price_gwei else None,
        mandate=mandate,
        agent_state=state,
    )

    # Record audit entry for simulations too
    entry = {
        "timestamp": time.time(),
        "agent": agent_id,
        "merchant": body.merchant,
        "amount": body.amount,
        "currency": body.currency,
        "network": body.network,
        "category": body.category,
        "verdict": verdict.to_dict(),
        "type": "simulate",
    }
    audit_log.append(entry)
    await sse_queue.put(entry)

    return JSONResponse(
        content={
            "verdict": verdict.to_dict(),
            "agent": agent_id,
            "simulated": True,
            "payment": {
                "tx": receipt.reference,
                "method": "tempo",
                "amount_charged": "0.0005",
                "currency": "pathUSD",
            },
        },
        headers={"Payment-Receipt": receipt.reference},
    )


@app.get("/audit")
async def audit(request: Request):
    """Full audit trail for the requesting agent. Costs $0.001 per call."""
    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.001",
        chain_id=ACTIVE_CHAIN_ID,
        description="Sardis Guard audit trail",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Audit trail costs $0.001 per call via MPP",
                "service": "sardis-guard",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    agent_id = credential.source or "anonymous"

    # Filter audit entries for this agent
    agent_entries = [e for e in audit_log if e["agent"] == agent_id]

    return JSONResponse(
        content={
            "agent": agent_id,
            "total_evaluations": len(agent_entries),
            "entries": agent_entries,
            "payment": {
                "tx": receipt.reference,
                "method": "tempo",
                "amount_charged": "0.001",
                "currency": "pathUSD",
            },
        },
        headers={"Payment-Receipt": receipt.reference},
    )


@app.get("/stream")
async def stream():
    """SSE stream of live policy evaluations. Free — no payment required."""

    async def event_generator():
        import json

        # Send initial keepalive
        yield f"event: connected\ndata: {{}}\n\n"
        while True:
            try:
                entry = await asyncio.wait_for(sse_queue.get(), timeout=30.0)
                yield f"event: evaluation\ndata: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive to prevent connection timeout
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8402)
