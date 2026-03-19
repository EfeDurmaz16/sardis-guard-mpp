"""Sardis Guard Intelligence Plane — Core Types.

These are the four canonical types shared across all modules.
Every module imports from here, never defines its own versions.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


# --- Actions ---

class Action(str, Enum):
    ALLOW = "ALLOW"
    FLAG = "FLAG"
    HOLD = "HOLD"
    FREEZE_CHILD = "FREEZE_CHILD"
    FREEZE_TREE = "FREEZE_TREE"
    DENY = "DENY"


class MandateStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


class TrustTier(str, Enum):
    """Agent trust tiers with preset spending limits.

    From Sardis Protocol Spec v1.1:
      UNTRUSTED:  $10/tx,     $25/day    — new/unknown agents
      LOW:        $50/tx,    $100/day    — basic KYA
      MEDIUM:    $500/tx,  $1,000/day   — verified KYA
      HIGH:    $5,000/tx, $10,000/day   — attested KYA
      SOVEREIGN:$50,000/tx (unlimited)  — full sovereign agent
    """
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SOVEREIGN = "sovereign"


# Preset limits per trust tier (from Sardis production)
TRUST_TIER_LIMITS: dict[TrustTier, dict] = {
    TrustTier.UNTRUSTED: {"per_tx": Decimal("10"), "daily": Decimal("25"), "total": Decimal("100")},
    TrustTier.LOW: {"per_tx": Decimal("50"), "daily": Decimal("100"), "total": Decimal("5000")},
    TrustTier.MEDIUM: {"per_tx": Decimal("500"), "daily": Decimal("1000"), "total": Decimal("50000")},
    TrustTier.HIGH: {"per_tx": Decimal("5000"), "daily": Decimal("10000"), "total": Decimal("500000")},
    TrustTier.SOVEREIGN: {"per_tx": Decimal("50000"), "daily": Decimal("999999999"), "total": Decimal("999999999")},
}


# --- PaymentIntentEvent ---

@dataclass
class PaymentIntentEvent:
    """Source-of-truth event for every payment evaluation."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    # Identity
    agent_id: str = ""
    principal_id: str = ""
    mandate_id: str = ""
    parent_mandate_id: str | None = None

    # Payment details
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    network: str = "tempo"
    merchant: str = ""
    category: str = "general"

    # Service context
    service_id: str = ""
    service_path: str = ""
    purpose: str = ""
    destination_address: str = ""
    prompt_hash: str = ""

    # Session binding (T3: anti-relay)
    session_hash: str = ""  # SHA-256(merchant + service_id + timestamp_bucket)

    # Results (filled by pipeline)
    policy_verdict: dict = field(default_factory=dict)
    governance_result: dict = field(default_factory=dict)
    risk_assessment: dict = field(default_factory=dict)
    aml_result: dict = field(default_factory=dict)
    action: Action = Action.ALLOW
    evidence_refs: list[str] = field(default_factory=list)
    downstream_allowed: bool = True

    # Hash chain
    prev_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self, prev: str = "") -> str:
        """Compute SHA-256 hash for tamper-evident chain."""
        payload = f"{self.event_id}|{self.timestamp}|{self.agent_id}|{self.amount}|{self.merchant}|{self.action.value}|{prev}"
        self.prev_hash = prev
        self.entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.entry_hash

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "principal_id": self.principal_id,
            "mandate_id": self.mandate_id,
            "parent_mandate_id": self.parent_mandate_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "network": self.network,
            "merchant": self.merchant,
            "category": self.category,
            "service_id": self.service_id,
            "service_path": self.service_path,
            "purpose": self.purpose,
            "destination_address": self.destination_address,
            "policy_verdict": self.policy_verdict,
            "governance_result": self.governance_result,
            "risk_assessment": self.risk_assessment,
            "aml_result": self.aml_result,
            "action": self.action.value,
            "evidence_refs": self.evidence_refs,
            "downstream_allowed": self.downstream_allowed,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }


# --- MandateNode ---

@dataclass
class MandateNode:
    """A node in the mandate delegation tree."""

    mandate_id: str = field(default_factory=lambda: f"mnd_{uuid.uuid4().hex[:12]}")
    parent_id: str | None = None
    principal_id: str = ""
    agent_id: str = ""

    # Budget
    max_total: Decimal = Decimal("100")
    max_per_tx: Decimal = Decimal("10")
    spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("100")
    in_flight_limit: int = 5  # T4: max concurrent outstanding payment objects
    in_flight_count: int = 0  # current outstanding

    # Scope restrictions
    allowed_services: list[str] = field(default_factory=list)
    allowed_merchants: list[str] = field(default_factory=list)
    blocked_merchants: list[str] = field(default_factory=list)
    allowed_chains: list[str] = field(default_factory=lambda: ["tempo"])
    allowed_currencies: list[str] = field(default_factory=lambda: ["USDC", "pathUSD"])
    allowed_categories: list[str] = field(default_factory=list)

    # Governance
    trust_tier: TrustTier = TrustTier.LOW
    status: MandateStatus = MandateStatus.ACTIVE
    approval_threshold: Decimal = Decimal("0")  # above this, needs approval
    delegation_depth: int = 0
    max_delegation_depth: int = 3

    # Time
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    frozen_at: float = 0.0
    frozen_reason: str = ""

    # Signature (simplified for hackathon)
    signature: str = ""

    @property
    def is_active(self) -> bool:
        if self.status != MandateStatus.ACTIVE:
            return False
        if self.expires_at > 0 and time.time() > self.expires_at:
            return False
        if self.remaining <= 0:
            return False
        return True

    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        if not self.is_active:
            return False, f"Mandate {self.mandate_id} is {self.status.value}"
        if amount > self.max_per_tx:
            return False, f"${amount} exceeds per-tx limit ${self.max_per_tx}"
        if amount > self.remaining:
            return False, f"${amount} exceeds remaining budget ${self.remaining}"
        if self.approval_threshold > 0 and amount > self.approval_threshold:
            return False, f"${amount} exceeds approval threshold ${self.approval_threshold}"
        return True, "Budget check passed"

    def record_spend(self, amount: Decimal):
        self.spent += amount
        self.remaining = self.max_total - self.spent

    def freeze(self, reason: str = ""):
        self.status = MandateStatus.FROZEN
        self.frozen_at = time.time()
        self.frozen_reason = reason

    def resume(self):
        self.status = MandateStatus.ACTIVE
        self.frozen_at = 0.0
        self.frozen_reason = ""

    def to_dict(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "parent_id": self.parent_id,
            "principal_id": self.principal_id,
            "agent_id": self.agent_id,
            "max_total": str(self.max_total),
            "max_per_tx": str(self.max_per_tx),
            "spent": str(self.spent),
            "remaining": str(self.remaining),
            "allowed_services": self.allowed_services,
            "allowed_merchants": self.allowed_merchants,
            "blocked_merchants": self.blocked_merchants,
            "allowed_chains": self.allowed_chains,
            "allowed_currencies": self.allowed_currencies,
            "status": self.status.value,
            "approval_threshold": str(self.approval_threshold),
            "delegation_depth": self.delegation_depth,
            "max_delegation_depth": self.max_delegation_depth,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "frozen_at": self.frozen_at,
            "frozen_reason": self.frozen_reason,
            "is_active": self.is_active,
        }


# --- RiskAssessment ---

@dataclass
class RiskAssessment:
    """Output of the risk engine for a single event."""

    # Individual scores (0.0 - 1.0)
    ml_score: float = 0.0           # IsolationForest anomaly
    sequence_score: float = 0.0     # Service transition surprisal
    correlation_score: float = 0.0  # Cross-agent correlation
    sanctions_score: float = 0.0    # AML/sanctions hit

    # Final composite
    final_score: float = 0.0
    action: Action = Action.ALLOW

    # Feature vector used
    features: dict[str, float] = field(default_factory=dict)

    # Explanations
    reasons: list[str] = field(default_factory=list)

    def resolve_action(self) -> Action:
        """Determine action from final_score with fixed thresholds."""
        if self.sanctions_score >= 1.0:
            self.action = Action.FREEZE_TREE
            self.reasons.append("Sanctions exact match → FREEZE_TREE")
            return self.action

        # Composite score
        self.final_score = max(
            self.ml_score * 0.35 +
            self.sequence_score * 0.25 +
            self.correlation_score * 0.20 +
            self.sanctions_score * 0.20,
            self.sanctions_score,  # sanctions floor
        )

        if self.final_score < 0.45:
            self.action = Action.ALLOW
        elif self.final_score < 0.70:
            self.action = Action.FLAG
            self.reasons.append(f"Elevated risk ({self.final_score:.2f}) → FLAG")
        elif self.final_score < 0.85:
            self.action = Action.HOLD
            self.reasons.append(f"High risk ({self.final_score:.2f}) → HOLD")
        else:
            self.action = Action.FREEZE_CHILD
            self.reasons.append(f"Critical risk ({self.final_score:.2f}) → FREEZE_CHILD")

        return self.action

    def to_dict(self) -> dict:
        return {
            "ml_score": round(self.ml_score, 4),
            "sequence_score": round(self.sequence_score, 4),
            "correlation_score": round(self.correlation_score, 4),
            "sanctions_score": round(self.sanctions_score, 4),
            "final_score": round(self.final_score, 4),
            "action": self.action.value,
            "features": {k: round(v, 4) for k, v in self.features.items()},
            "reasons": self.reasons,
        }


# --- AuditEvidencePack ---

@dataclass
class AuditEvidencePack:
    """Self-contained compliance evidence for a session."""

    session_id: str = field(default_factory=lambda: f"ses_{uuid.uuid4().hex[:12]}")
    generated_at: float = field(default_factory=time.time)

    # Content
    events: list[dict] = field(default_factory=list)
    mandate_chain: list[dict] = field(default_factory=list)
    risk_assessments: list[dict] = field(default_factory=list)
    sanctions_results: list[dict] = field(default_factory=list)
    freeze_actions: list[dict] = field(default_factory=list)
    operator_actions: list[dict] = field(default_factory=list)

    # Integrity
    event_count: int = 0
    chain_valid: bool = True
    first_hash: str = ""
    last_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "generated_at": self.generated_at,
            "event_count": self.event_count,
            "chain_valid": self.chain_valid,
            "first_hash": self.first_hash,
            "last_hash": self.last_hash,
            "events": self.events,
            "mandate_chain": self.mandate_chain,
            "risk_assessments": self.risk_assessments,
            "sanctions_results": self.sanctions_results,
            "freeze_actions": self.freeze_actions,
            "operator_actions": self.operator_actions,
        }
