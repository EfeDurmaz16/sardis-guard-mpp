"""Simple mandate signing for tamper evidence.

Uses HMAC-SHA256 over canonical mandate fields to produce
a signature that can be verified later. This is not a full
PKI system — it's a lightweight integrity check for the hackathon.
"""

from __future__ import annotations

import hashlib
import hmac

from src.types import MandateNode


def _canonical_payload(mandate: MandateNode) -> str:
    """Build a deterministic string from mandate fields for signing."""
    parts = [
        mandate.mandate_id,
        mandate.parent_id or "",
        mandate.principal_id,
        mandate.agent_id,
        str(mandate.max_total),
        str(mandate.max_per_tx),
        ",".join(sorted(mandate.allowed_services)),
        ",".join(sorted(mandate.allowed_merchants)),
        ",".join(sorted(mandate.blocked_merchants)),
        ",".join(sorted(mandate.allowed_chains)),
        ",".join(sorted(mandate.allowed_currencies)),
        str(mandate.delegation_depth),
        str(mandate.max_delegation_depth),
        str(mandate.created_at),
        str(mandate.expires_at),
    ]
    return "|".join(parts)


def sign_mandate(mandate: MandateNode, secret: str) -> str:
    """Produce an HMAC-SHA256 signature for a mandate.

    The signature covers immutable fields (IDs, budget caps, scope,
    depth, timestamps) — not mutable state like spent/remaining/status.
    """
    payload = _canonical_payload(mandate)
    sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    mandate.signature = sig
    return sig


def verify_mandate(mandate: MandateNode, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature against a mandate's canonical fields."""
    payload = _canonical_payload(mandate)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
