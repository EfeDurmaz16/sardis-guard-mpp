"""GovernanceEngine — evaluates payment intents against mandate constraints.

Runs a 10-point check sequence and produces a GovernanceResult
indicating whether the payment is allowed, with full audit trail.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from src.types import Action, MandateNode, MandateStatus, PaymentIntentEvent
from src.mandates.mandate_store import MandateStore


@dataclass
class GovernanceResult:
    """Result of governance evaluation."""

    allowed: bool = True
    checks: list[dict] = field(default_factory=list)
    mandate_snapshot: dict = field(default_factory=dict)
    action: Action = Action.ALLOW
    reason: str = ""
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "reason": self.reason,
            "checks": self.checks,
            "mandate_snapshot": self.mandate_snapshot,
            "evaluated_at": self.evaluated_at,
        }


class GovernanceEngine:
    """Evaluates PaymentIntentEvents against MandateNode constraints."""

    def __init__(self, store: MandateStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        event: PaymentIntentEvent,
        mandate: MandateNode,
    ) -> GovernanceResult:
        """Run all governance checks and return a result.

        Checks (in order):
          1. Mandate is active (not frozen/expired/exhausted)
          2. Amount within per-tx limit
          3. Amount within remaining budget
          4. Service in allowed_services (if specified)
          5. Merchant not in blocked_merchants
          6. Chain in allowed_chains
          7. Currency in allowed_currencies
          8. Delegation depth within bounds
          9. Parent mandate is also active (recursive)
          10. Approval threshold check
        """
        result = GovernanceResult(
            mandate_snapshot=mandate.to_dict(),
        )

        # 1. Active status
        self._check(
            result,
            name="mandate_active",
            passed=mandate.is_active,
            detail=f"Status: {mandate.status.value}",
            deny_reason=f"Mandate {mandate.mandate_id} is {mandate.status.value}",
        )

        # 2. Per-tx limit
        self._check(
            result,
            name="per_tx_limit",
            passed=event.amount <= mandate.max_per_tx,
            detail=f"Amount ${event.amount} vs limit ${mandate.max_per_tx}",
            deny_reason=f"Amount ${event.amount} exceeds per-tx limit ${mandate.max_per_tx}",
        )

        # 3. Remaining budget
        self._check(
            result,
            name="remaining_budget",
            passed=event.amount <= mandate.remaining,
            detail=f"Amount ${event.amount} vs remaining ${mandate.remaining}",
            deny_reason=f"Amount ${event.amount} exceeds remaining budget ${mandate.remaining}",
        )

        # 4. Service allowed
        service_ok = (
            not mandate.allowed_services
            or event.service_id in mandate.allowed_services
        )
        self._check(
            result,
            name="service_allowed",
            passed=service_ok,
            detail=f"Service '{event.service_id}' vs allowed {mandate.allowed_services or ['*']}",
            deny_reason=f"Service '{event.service_id}' not in allowed services",
        )

        # 5. Merchant not blocked
        merchant_ok = event.merchant not in mandate.blocked_merchants
        self._check(
            result,
            name="merchant_not_blocked",
            passed=merchant_ok,
            detail=f"Merchant '{event.merchant}' vs blocked {mandate.blocked_merchants}",
            deny_reason=f"Merchant '{event.merchant}' is blocked",
        )

        # 6. Chain allowed
        chain_ok = (
            not mandate.allowed_chains
            or event.network in mandate.allowed_chains
        )
        self._check(
            result,
            name="chain_allowed",
            passed=chain_ok,
            detail=f"Chain '{event.network}' vs allowed {mandate.allowed_chains or ['*']}",
            deny_reason=f"Chain '{event.network}' not in allowed chains",
        )

        # 7. Currency allowed
        currency_ok = (
            not mandate.allowed_currencies
            or event.currency in mandate.allowed_currencies
        )
        self._check(
            result,
            name="currency_allowed",
            passed=currency_ok,
            detail=f"Currency '{event.currency}' vs allowed {mandate.allowed_currencies or ['*']}",
            deny_reason=f"Currency '{event.currency}' not in allowed currencies",
        )

        # 8. Delegation depth
        depth_ok = mandate.delegation_depth <= mandate.max_delegation_depth
        self._check(
            result,
            name="delegation_depth",
            passed=depth_ok,
            detail=f"Depth {mandate.delegation_depth} vs max {mandate.max_delegation_depth}",
            deny_reason=f"Delegation depth {mandate.delegation_depth} exceeds max {mandate.max_delegation_depth}",
        )

        # 9. Parent chain active (recursive)
        parent_ok, parent_detail = self._check_parent_chain(mandate)
        self._check(
            result,
            name="parent_chain_active",
            passed=parent_ok,
            detail=parent_detail,
            deny_reason=parent_detail if not parent_ok else "",
        )

        # 10. Approval threshold
        threshold_ok = (
            mandate.approval_threshold <= 0
            or event.amount <= mandate.approval_threshold
        )
        self._check(
            result,
            name="approval_threshold",
            passed=threshold_ok,
            detail=f"Amount ${event.amount} vs threshold ${mandate.approval_threshold}",
            deny_reason=f"Amount ${event.amount} exceeds approval threshold ${mandate.approval_threshold}",
        )

        # Determine final action
        if not result.allowed:
            result.action = Action.DENY
        else:
            result.action = Action.ALLOW

        return result

    # ------------------------------------------------------------------
    # Action application
    # ------------------------------------------------------------------

    def apply_action(
        self,
        action: Action,
        mandate_id: str,
        reason: str = "",
    ) -> dict:
        """Apply a governance action to a mandate.

        Returns a summary dict of what was done.
        """
        summary = {
            "action": action.value,
            "mandate_id": mandate_id,
            "reason": reason,
            "applied_at": time.time(),
            "effect": "none",
        }

        if action == Action.ALLOW:
            summary["effect"] = "no_change"

        elif action == Action.FLAG:
            summary["effect"] = "flagged_for_review"

        elif action == Action.HOLD:
            summary["effect"] = "held_for_manual_review"

        elif action == Action.FREEZE_CHILD:
            self._store.freeze(mandate_id, reason)
            summary["effect"] = "mandate_frozen"

        elif action == Action.FREEZE_TREE:
            self._store.freeze_tree(mandate_id, reason)
            summary["effect"] = "tree_frozen"

        elif action == Action.DENY:
            summary["effect"] = "transaction_blocked"

        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check(
        self,
        result: GovernanceResult,
        name: str,
        passed: bool,
        detail: str,
        deny_reason: str,
    ) -> None:
        """Record a single check result."""
        result.checks.append({
            "check": name,
            "passed": passed,
            "detail": detail,
        })
        if not passed:
            result.allowed = False
            if not result.reason:
                result.reason = deny_reason

    def _check_parent_chain(self, mandate: MandateNode) -> tuple[bool, str]:
        """Walk up the parent chain and verify all ancestors are active."""
        if mandate.parent_id is None:
            return True, "Root mandate — no parent to check"

        current_id: str | None = mandate.parent_id
        depth = 0
        while current_id is not None:
            parent = self._store.get(current_id)
            if parent is None:
                return False, f"Parent mandate {current_id} not found in store"
            if not parent.is_active:
                return False, f"Parent {current_id} is {parent.status.value}"
            current_id = parent.parent_id
            depth += 1
            if depth > 20:
                return False, "Parent chain too deep (possible cycle)"

        return True, f"All {depth} ancestors active"
