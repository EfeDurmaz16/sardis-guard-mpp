"""Sardis Guard Intelligence Plane — V2 Routes.

New endpoints for mandate governance, screening, dashboard, and reports.
These are mounted onto the main FastAPI app from server.py.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.types import (
    Action,
    AuditEvidencePack,
    MandateNode,
    MandateStatus,
    PaymentIntentEvent,
    RiskAssessment,
)

from src.security.dedup import DedupStore
from src.security.session_binding import compute_session_hash, verify_session_hash
from src.security.in_flight import InFlightTracker, InFlightEntry
from src.security.kill_switch import KillSwitchManager, KillSwitchScope

router = APIRouter()

# Security modules
in_flight_tracker = InFlightTracker()
kill_switch_mgr = KillSwitchManager()

# These will be set by server.py at startup
mandate_store = None
governance_engine = None
risk_engine = None
sanctions_screener = None
dedup_store = DedupStore()
event_store = None
mpp_server = None
sse_queue = None
REALM = ""
ACTIVE_CHAIN_ID = 0


def _init(
    _mandate_store,
    _governance_engine,
    _risk_engine,
    _sanctions_screener,
    _event_store,
    _mpp_server,
    _sse_queue,
    _realm,
    _chain_id,
):
    """Called by server.py to inject dependencies."""
    global mandate_store, governance_engine, risk_engine, sanctions_screener
    global event_store, mpp_server, sse_queue, REALM, ACTIVE_CHAIN_ID
    mandate_store = _mandate_store
    governance_engine = _governance_engine
    risk_engine = _risk_engine
    sanctions_screener = _sanctions_screener
    event_store = _event_store
    mpp_server = _mpp_server
    sse_queue = _sse_queue
    REALM = _realm
    ACTIVE_CHAIN_ID = _chain_id


# ── Request Models ──────────────────────────────────────────────────────────


class CreateRootMandateRequest(BaseModel):
    principal_id: str
    agent_id: str
    max_total: str = "100"
    max_per_tx: str = "10"
    allowed_services: list[str] = []
    allowed_merchants: list[str] = []
    blocked_merchants: list[str] = []
    allowed_chains: list[str] = ["tempo"]
    allowed_currencies: list[str] = ["USDC", "pathUSD"]
    approval_threshold: str = "0"
    expires_in_seconds: int = 0  # 0 = no expiry


class DelegateMandateRequest(BaseModel):
    parent_mandate_id: str
    agent_id: str
    max_total: str = "25"
    max_per_tx: str = "5"
    allowed_services: list[str] = []
    allowed_merchants: list[str] = []
    blocked_merchants: list[str] = []
    allowed_chains: list[str] = ["tempo"]
    allowed_currencies: list[str] = ["USDC", "pathUSD"]
    expires_in_seconds: int = 0


class FreezeMandateRequest(BaseModel):
    mandate_id: str
    reason: str = "Manual freeze"
    freeze_children: bool = False


class ResumeMandateRequest(BaseModel):
    mandate_id: str


class ScreenEntityRequest(BaseModel):
    name: str


class ScreenAddressRequest(BaseModel):
    address: str


class EvaluateV2Request(BaseModel):
    """Extended evaluation request with governance context."""
    amount: str
    merchant: str
    currency: str = "USDC"
    network: str = "tempo"
    category: str = "general"
    agent_id: str = ""
    principal_id: str = ""
    mandate_id: str = ""
    service_id: str = ""
    service_path: str = ""
    purpose: str = ""
    destination_address: str = ""
    memo: str | None = None
    session_hash: str = ""  # T3: anti-relay binding
    idempotency_key: str = ""
    nonce: int = -1


# ── Mandate Routes ──────────────────────────────────────────────────────────


@router.post("/mandates/root")
async def create_root_mandate(body: CreateRootMandateRequest):
    """Create a root mandate for a principal. Free endpoint."""
    expires_at = (time.time() + body.expires_in_seconds) if body.expires_in_seconds > 0 else 0.0

    node = mandate_store.create_root(
        principal_id=body.principal_id,
        agent_id=body.agent_id,
        max_total=Decimal(body.max_total),
        max_per_tx=Decimal(body.max_per_tx),
        allowed_services=body.allowed_services,
        allowed_merchants=body.allowed_merchants,
        blocked_merchants=body.blocked_merchants,
        allowed_chains=body.allowed_chains,
        allowed_currencies=body.allowed_currencies,
        approval_threshold=Decimal(body.approval_threshold),
        expires_at=expires_at,
    )

    return {"mandate": node.to_dict()}


@router.post("/mandates/delegate")
async def delegate_mandate(body: DelegateMandateRequest):
    """Delegate a child mandate from an existing parent. Free endpoint."""
    expires_at = (time.time() + body.expires_in_seconds) if body.expires_in_seconds > 0 else 0.0

    try:
        child = mandate_store.delegate(
            parent_id=body.parent_mandate_id,
            agent_id=body.agent_id,
            max_total=Decimal(body.max_total),
            max_per_tx=Decimal(body.max_per_tx),
            allowed_services=body.allowed_services,
            allowed_merchants=body.allowed_merchants,
            blocked_merchants=body.blocked_merchants,
            allowed_chains=body.allowed_chains,
            allowed_currencies=body.allowed_currencies,
            expires_at=expires_at,
        )
    except (ValueError, KeyError) as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return {"mandate": child.to_dict()}


@router.post("/mandates/freeze")
async def freeze_mandate(body: FreezeMandateRequest):
    """Freeze a mandate (and optionally its children). Free endpoint."""
    node = mandate_store.get(body.mandate_id)
    if not node:
        return JSONResponse(status_code=404, content={"error": "Mandate not found"})

    if body.freeze_children:
        mandate_store.freeze_tree(body.mandate_id, body.reason)
    else:
        mandate_store.freeze(body.mandate_id, body.reason)

    return {"frozen": True, "mandate": mandate_store.get(body.mandate_id).to_dict()}


@router.post("/mandates/resume")
async def resume_mandate(body: ResumeMandateRequest):
    """Resume a frozen mandate. Free endpoint."""
    try:
        mandate_store.resume(body.mandate_id)
    except (ValueError, KeyError) as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return {"resumed": True, "mandate": mandate_store.get(body.mandate_id).to_dict()}


@router.get("/mandates")
async def list_mandates(wallet: str = ""):
    """List mandates, optionally filtered by wallet address. Free endpoint."""
    all_mandates = mandate_store.list_all() if hasattr(mandate_store, 'list_all') else []
    if wallet:
        w = wallet.lower()
        all_mandates = [
            m for m in all_mandates
            if w in m.principal_id.lower() or w in m.agent_id.lower()
        ]
    return {"mandates": [m.to_dict() for m in all_mandates]}


@router.get("/mandates/{mandate_id}")
async def get_mandate_detail(mandate_id: str):
    """Get mandate details including children. Free endpoint."""
    node = mandate_store.get(mandate_id)
    if not node:
        return JSONResponse(status_code=404, content={"error": "Mandate not found"})

    children = mandate_store.get_children(mandate_id)
    tree = mandate_store.get_tree(mandate_id)

    return {
        "mandate": node.to_dict(),
        "children": [c.to_dict() for c in children],
        "tree_size": len(tree),
    }


# ── Screening Routes ───────────────────────────────────────────────────────


@router.post("/screen/entity")
async def screen_entity(body: ScreenEntityRequest):
    """Screen an entity name against sanctions lists. Free endpoint."""
    if not sanctions_screener:
        return {"error": "Sanctions screener not available", "hit": False}

    result = sanctions_screener.screen_entity(body.name)
    return {
        "entity": body.name,
        "hit": result.hit,
        "match_type": result.match_type,
        "matched_entry": result.matched_entry,
        "list_source": result.list_source,
        "confidence": result.confidence,
    }


@router.post("/screen/address")
async def screen_address(body: ScreenAddressRequest):
    """Screen a wallet address against sanctions lists. Free endpoint."""
    if not sanctions_screener:
        return {"error": "Sanctions screener not available", "hit": False}

    result = sanctions_screener.screen_address(body.address)
    return {
        "address": body.address,
        "hit": result.hit,
        "match_type": result.match_type,
        "matched_entry": result.matched_entry,
        "list_source": result.list_source,
        "confidence": result.confidence,
    }


# ── Kill Switch Routes ──────────────────────────────────────────────────────


class KillSwitchActivateRequest(BaseModel):
    scope: str  # "global", "org", "agent", "chain"
    target: str = ""  # org_id, agent_id, or chain name
    reason: str = "Manual activation"
    auto_lift_seconds: int = 0  # 0 = manual lift only


class KillSwitchDeactivateRequest(BaseModel):
    scope: str
    target: str = ""


@router.post("/kill-switch/activate")
async def activate_kill_switch(body: KillSwitchActivateRequest):
    """Activate a kill switch. Free endpoint (emergency action)."""
    scope = KillSwitchScope(body.scope)
    state = kill_switch_mgr.activate(
        scope=scope,
        target=body.target,
        reason=body.reason,
        auto_lift_seconds=body.auto_lift_seconds,
        activated_by="operator",
    )
    return {
        "activated": True,
        "scope": state.scope.value,
        "target": state.target,
        "reason": state.reason,
        "auto_lift_at": state.auto_reactivate_at if state.auto_reactivate_at > 0 else None,
    }


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(body: KillSwitchDeactivateRequest):
    """Deactivate a kill switch. Free endpoint."""
    scope = KillSwitchScope(body.scope)
    was_active = kill_switch_mgr.deactivate(scope, body.target)
    return {"deactivated": was_active, "scope": body.scope, "target": body.target}


@router.get("/kill-switch/status")
async def kill_switch_status():
    """List all active kill switches. Free endpoint."""
    active = kill_switch_mgr.list_active()
    return {
        "active_count": len(active),
        "switches": [
            {
                "scope": s.scope.value,
                "target": s.target,
                "reason": s.reason,
                "activated_at": s.activated_at,
                "auto_lift_at": s.auto_reactivate_at if s.auto_reactivate_at > 0 else None,
                "activated_by": s.activated_by,
            }
            for s in active
        ],
    }


# ── Dashboard Routes ────────────────────────────────────────────────────────


@router.get("/dashboard/summary")
async def dashboard_summary():
    """Aggregate dashboard stats. Free endpoint."""
    if event_store and hasattr(event_store, 'get_dashboard_summary'):
        summary = event_store.get_dashboard_summary()
    else:
        summary = {}

    # Add mandate stats
    all_mandates = mandate_store.list_all() if mandate_store and hasattr(mandate_store, 'list_all') else []
    active_count = sum(1 for m in all_mandates if m.status == MandateStatus.ACTIVE)
    frozen_count = sum(1 for m in all_mandates if m.status == MandateStatus.FROZEN)

    return {
        **summary,
        "mandates_active": active_count,
        "mandates_frozen": frozen_count,
        "mandates_total": len(all_mandates),
    }


@router.get("/dashboard/graph")
async def dashboard_graph():
    """Service transition graph for visualization. Free endpoint."""
    if event_store and hasattr(event_store, 'get_service_graph'):
        return {"graph": event_store.get_service_graph()}
    return {"graph": {"nodes": [], "edges": []}}


@router.get("/agents/{agent_id}/risk")
async def agent_risk(agent_id: str):
    """Risk timeline for a specific agent. Free endpoint."""
    if event_store and hasattr(event_store, 'get_risk_timeline'):
        timeline = event_store.get_risk_timeline(agent_id)
    else:
        timeline = []

    if event_store and hasattr(event_store, 'get_agent_summary'):
        summary = event_store.get_agent_summary(agent_id)
    else:
        summary = {}

    return {
        "agent_id": agent_id,
        "summary": summary,
        "risk_timeline": timeline,
    }


# ── Report Routes ───────────────────────────────────────────────────────────


@router.get("/reports/session/{session_id}")
async def session_report(session_id: str):
    """Generate a compliance evidence pack for a session. Free endpoint."""
    if not event_store:
        return JSONResponse(status_code=503, content={"error": "Event store not available"})

    events = event_store.get_events(limit=1000)
    # Filter to session if needed (for now, return all)

    pack = AuditEvidencePack(session_id=session_id)
    pack.events = [e if isinstance(e, dict) else e.to_dict() for e in events]
    pack.event_count = len(pack.events)

    if pack.events:
        pack.first_hash = pack.events[0].get("entry_hash", "")
        pack.last_hash = pack.events[-1].get("entry_hash", "")

    # Add mandate chain
    if mandate_store and hasattr(mandate_store, 'list_all'):
        pack.mandate_chain = [m.to_dict() for m in mandate_store.list_all()]

    # Validate hash chain
    pack.chain_valid = True
    for i in range(1, len(pack.events)):
        if pack.events[i].get("prev_hash") != pack.events[i - 1].get("entry_hash"):
            pack.chain_valid = False
            break

    return pack.to_dict()


# ── Extended Evaluate (V2) ──────────────────────────────────────────────────


@router.post("/evaluate/v2")
async def evaluate_v2(request: Request, body: EvaluateV2Request):
    """Full intelligence pipeline evaluation. Costs $0.001 per call."""
    from mpp import Challenge

    result = await mpp_server.charge(
        authorization=request.headers.get("Authorization"),
        amount="0.001",
        chain_id=ACTIVE_CHAIN_ID,
        description="Sardis Guard intelligence evaluation",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://sardis.sh/errors/payment-required",
                "title": "Payment Required",
                "detail": "Intelligence evaluation costs $0.001 via MPP",
            },
            headers={"WWW-Authenticate": result.to_www_authenticate(REALM)},
        )

    credential, receipt = result
    caller_id = credential.source or "anonymous"
    agent_id = body.agent_id or caller_id

    # GATE 1: Kill Switch — FIRST check, before everything else
    ks_result = kill_switch_mgr.check(
        agent_id=agent_id,
        principal_id=body.principal_id,
        chain=body.network,
    )
    if ks_result.blocked:
        return JSONResponse(
            status_code=503,
            content={
                "error": "kill_switch_active",
                "detail": ks_result.summary,
                "active_switches": [
                    {"scope": s.scope.value, "target": s.target, "reason": s.reason}
                    for s in ks_result.active_switches
                ],
                "action": "IMMEDIATE_REJECT",
                "payment": {"tx": receipt.reference},
            },
            headers={"Payment-Receipt": receipt.reference},
        )

    # GATE 2: Dedup / replay protection (BEFORE any state mutation)
    dedup_result = dedup_store.check_all(
        agent_id=agent_id,
        amount=body.amount,
        merchant=body.merchant,
        idempotency_key=body.idempotency_key,
        nonce=body.nonce,
    )
    if dedup_result.is_duplicate:
        return JSONResponse(
            status_code=409,
            content={
                "error": "duplicate_request",
                "detail": dedup_result.reason,
                "original_event_id": dedup_result.original_event_id,
                "action": "REJECT",
                "payment": {"tx": receipt.reference},
            },
            headers={"Payment-Receipt": receipt.reference},
        )

    # 0b. Session-hash anti-relay check (T3)
    if body.session_hash:
        sh_valid, sh_reason = verify_session_hash(
            body.session_hash, body.merchant, body.service_id,
        )
        if not sh_valid:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "relay_detected",
                    "detail": sh_reason,
                    "threat": "T3",
                    "action": "REJECT",
                    "payment": {"tx": receipt.reference},
                },
                headers={"Payment-Receipt": receipt.reference},
            )

    # 0c. In-flight limit check (T4)
    if body.mandate_id and mandate_store:
        mandate_for_flight = mandate_store.get(body.mandate_id)
        if mandate_for_flight:
            flight_ok, flight_reason, flight_count = in_flight_tracker.check(
                body.mandate_id, mandate_for_flight.in_flight_limit,
            )
            if not flight_ok:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "in_flight_limit_exceeded",
                        "detail": flight_reason,
                        "threat": "T4",
                        "current_in_flight": flight_count,
                        "limit": mandate_for_flight.in_flight_limit,
                        "action": "REJECT",
                        "payment": {"tx": receipt.reference},
                    },
                    headers={"Payment-Receipt": receipt.reference},
                )

    # Build event
    event = PaymentIntentEvent(
        agent_id=agent_id,
        principal_id=body.principal_id,
        mandate_id=body.mandate_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        network=body.network,
        merchant=body.merchant,
        category=body.category,
        service_id=body.service_id,
        service_path=body.service_path,
        purpose=body.purpose,
        destination_address=body.destination_address,
        session_hash=body.session_hash or compute_session_hash(body.merchant, body.service_id),
    )

    # 1. Governance check
    gov_result = {"allowed": True, "checks": [], "reason": "No mandate specified"}
    mandate = None
    if body.mandate_id and mandate_store:
        mandate = mandate_store.get(body.mandate_id)
        if mandate and governance_engine:
            gov_result = governance_engine.evaluate(event, mandate).to_dict()

    event.governance_result = gov_result

    # 2. Sanctions screening
    aml_result = {"hit": False, "match_type": "none"}
    if body.destination_address and sanctions_screener:
        scr = sanctions_screener.screen_address(body.destination_address)
        aml_result = {
            "hit": scr.hit,
            "match_type": scr.match_type,
            "matched_entry": scr.matched_entry,
            "confidence": scr.confidence,
        }
    event.aml_result = aml_result

    # 3. Risk assessment
    risk = RiskAssessment()
    if risk_engine:
        sanctions_hit = aml_result.get("hit", False)
        risk = risk_engine.assess(event, mandate, sanctions_hit)
    else:
        risk.resolve_action()
    event.risk_assessment = risk.to_dict()

    # 4. Resolve final action
    if aml_result.get("hit"):
        event.action = Action.FREEZE_TREE
        event.downstream_allowed = False
    elif not gov_result.get("allowed", True):
        event.action = Action.DENY
        event.downstream_allowed = False
    else:
        event.action = risk.action
        event.downstream_allowed = event.action in (Action.ALLOW, Action.FLAG)

    # 5. Apply action to mandate
    if mandate and governance_engine:
        governance_engine.apply_action(event.action, body.mandate_id, risk.reasons[0] if risk.reasons else "Risk threshold")

    # 6. Record spend if allowed + track in-flight
    if event.downstream_allowed and mandate:
        mandate_store.record_spend(body.mandate_id, Decimal(body.amount))
        in_flight_tracker.record(InFlightEntry(
            event_id=event.event_id,
            agent_id=event.agent_id,
            mandate_id=body.mandate_id,
            amount=body.amount,
            merchant=body.merchant,
        ))

    # 7. Store event
    if event_store:
        last_hash = event_store.get_last_hash() if hasattr(event_store, 'get_last_hash') else ""
        event.compute_hash(last_hash)
        event_store.insert_event(event)

    # 8. Record dedup markers
    import json as _json
    dedup_store.record_all(
        agent_id=event.agent_id,
        amount=body.amount,
        merchant=body.merchant,
        event_id=event.event_id,
        idempotency_key=body.idempotency_key,
        nonce=body.nonce,
        result_json=_json.dumps({"event_id": event.event_id, "action": event.action.value}),
    )

    # 9. Broadcast to SSE
    if sse_queue:
        await sse_queue.put(event.to_dict())

    return JSONResponse(
        content={
            "event_id": event.event_id,
            "action": event.action.value,
            "downstream_allowed": event.downstream_allowed,
            "governance": gov_result,
            "risk": risk.to_dict(),
            "aml": aml_result,
            "policy_verdict": event.policy_verdict,
            "agent": event.agent_id,
            "mandate_id": event.mandate_id,
            "evidence_refs": [event.entry_hash],
            "payment": {
                "tx": receipt.reference,
                "method": "tempo",
                "amount_charged": "0.001",
            },
        },
        headers={"Payment-Receipt": receipt.reference},
    )
