"""MandateStore — in-memory mandate delegation tree.

Manages root mandates, delegation with scope narrowing,
spend propagation, and freeze/resume operations.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Optional

from src.types import MandateNode, MandateStatus


class MandateStore:
    """Thread-safe in-memory store for MandateNode objects."""

    def __init__(self) -> None:
        self._mandates: dict[str, MandateNode] = {}
        self._agent_index: dict[str, str] = {}  # agent_id -> mandate_id
        self._lock = threading.Lock()

    def list_all(self) -> list[MandateNode]:
        """Return all mandates."""
        return list(self._mandates.values())

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_root(
        self,
        principal_id: str,
        agent_id: str,
        max_total: Decimal | float | int = 100,
        max_per_tx: Decimal | float | int = 10,
        allowed_services: list[str] | None = None,
        allowed_merchants: list[str] | None = None,
        blocked_merchants: list[str] | None = None,
        allowed_chains: list[str] | None = None,
        allowed_currencies: list[str] | None = None,
        allowed_categories: list[str] | None = None,
        approval_threshold: Decimal | float | int = 0,
        max_delegation_depth: int = 3,
        expires_at: float = 0.0,
    ) -> MandateNode:
        """Create a root mandate issued by a principal to an agent."""
        max_total = Decimal(str(max_total))
        max_per_tx = Decimal(str(max_per_tx))
        approval_threshold = Decimal(str(approval_threshold))

        node = MandateNode(
            parent_id=None,
            principal_id=principal_id,
            agent_id=agent_id,
            max_total=max_total,
            max_per_tx=max_per_tx,
            spent=Decimal("0"),
            remaining=max_total,
            allowed_services=allowed_services or [],
            allowed_merchants=allowed_merchants or [],
            blocked_merchants=blocked_merchants or [],
            allowed_chains=allowed_chains or ["tempo"],
            allowed_currencies=allowed_currencies or ["USDC", "pathUSD"],
            allowed_categories=allowed_categories or [],
            approval_threshold=approval_threshold,
            delegation_depth=0,
            max_delegation_depth=max_delegation_depth,
            expires_at=expires_at,
        )

        with self._lock:
            self._mandates[node.mandate_id] = node
            self._agent_index[agent_id] = node.mandate_id
        return node

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def delegate(
        self,
        parent_id: str,
        agent_id: str,
        max_total: Decimal | float | int,
        max_per_tx: Decimal | float | int,
        allowed_services: list[str] | None = None,
        allowed_merchants: list[str] | None = None,
        blocked_merchants: list[str] | None = None,
        allowed_chains: list[str] | None = None,
        allowed_currencies: list[str] | None = None,
        allowed_categories: list[str] | None = None,
        approval_threshold: Decimal | float | int = 0,
        expires_at: float = 0.0,
    ) -> MandateNode:
        """Delegate a child mandate from a parent.

        Enforces:
          - Child budget cannot exceed parent remaining budget.
          - Child per-tx cannot exceed parent per-tx.
          - Child scope must be a subset of parent scope (when parent has restrictions).
          - Delegation depth must not exceed max_delegation_depth.
          - Parent must be active.
        """
        max_total = Decimal(str(max_total))
        max_per_tx = Decimal(str(max_per_tx))
        approval_threshold = Decimal(str(approval_threshold))

        with self._lock:
            parent = self._mandates.get(parent_id)
            if parent is None:
                raise ValueError(f"Parent mandate {parent_id} not found")
            if not parent.is_active:
                raise ValueError(f"Parent mandate {parent_id} is not active ({parent.status.value})")

            # --- depth check ---
            new_depth = parent.delegation_depth + 1
            if new_depth > parent.max_delegation_depth:
                raise ValueError(
                    f"Delegation depth {new_depth} exceeds max {parent.max_delegation_depth}"
                )

            # --- budget check ---
            if max_total > parent.remaining:
                raise ValueError(
                    f"Child max_total ${max_total} exceeds parent remaining ${parent.remaining}"
                )
            if max_per_tx > parent.max_per_tx:
                raise ValueError(
                    f"Child max_per_tx ${max_per_tx} exceeds parent max_per_tx ${parent.max_per_tx}"
                )

            # --- scope narrowing ---
            child_services = self._narrow_scope(
                parent.allowed_services, allowed_services, "services"
            )
            child_merchants = self._narrow_scope(
                parent.allowed_merchants, allowed_merchants, "merchants"
            )
            child_chains = self._narrow_scope(
                parent.allowed_chains, allowed_chains, "chains"
            )
            child_currencies = self._narrow_scope(
                parent.allowed_currencies, allowed_currencies, "currencies"
            )
            child_categories = self._narrow_scope(
                parent.allowed_categories, allowed_categories, "categories"
            )

            # Blocked merchants: union of parent + child
            child_blocked = list(
                set(parent.blocked_merchants) | set(blocked_merchants or [])
            )

            node = MandateNode(
                parent_id=parent_id,
                principal_id=parent.principal_id,
                agent_id=agent_id,
                max_total=max_total,
                max_per_tx=max_per_tx,
                spent=Decimal("0"),
                remaining=max_total,
                allowed_services=child_services,
                allowed_merchants=child_merchants,
                blocked_merchants=child_blocked,
                allowed_chains=child_chains,
                allowed_currencies=child_currencies,
                allowed_categories=child_categories,
                approval_threshold=approval_threshold,
                delegation_depth=new_depth,
                max_delegation_depth=parent.max_delegation_depth,
                expires_at=expires_at,
            )

            self._mandates[node.mandate_id] = node
            self._agent_index[agent_id] = node.mandate_id
        return node

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, mandate_id: str) -> MandateNode | None:
        """Get a mandate by ID."""
        return self._mandates.get(mandate_id)

    def get_by_agent(self, agent_id: str) -> MandateNode | None:
        """Get a mandate by agent ID."""
        mid = self._agent_index.get(agent_id)
        if mid is None:
            return None
        return self._mandates.get(mid)

    def get_children(self, mandate_id: str) -> list[MandateNode]:
        """Get direct children of a mandate."""
        return [
            m for m in self._mandates.values() if m.parent_id == mandate_id
        ]

    def get_tree(self, root_id: str) -> list[MandateNode]:
        """Get full tree from a root mandate (BFS)."""
        root = self._mandates.get(root_id)
        if root is None:
            return []

        result: list[MandateNode] = [root]
        queue = [root_id]
        while queue:
            current_id = queue.pop(0)
            children = self.get_children(current_id)
            for child in children:
                result.append(child)
                queue.append(child.mandate_id)
        return result

    # ------------------------------------------------------------------
    # Spend tracking
    # ------------------------------------------------------------------

    def record_spend(self, mandate_id: str, amount: Decimal | float | int) -> None:
        """Record spend on a mandate and propagate up to root.

        Updates spent/remaining on the target mandate and every
        ancestor in the delegation chain.
        """
        amount = Decimal(str(amount))
        node = self._mandates.get(mandate_id)
        if node is None:
            raise ValueError(f"Mandate {mandate_id} not found")

        # Walk up the chain and record on each ancestor
        current: MandateNode | None = node
        while current is not None:
            current.record_spend(amount)
            if current.remaining <= 0:
                current.status = MandateStatus.EXHAUSTED
            if current.parent_id:
                current = self._mandates.get(current.parent_id)
            else:
                current = None

    # ------------------------------------------------------------------
    # Freeze / Resume
    # ------------------------------------------------------------------

    def freeze(self, mandate_id: str, reason: str = "") -> None:
        """Freeze a single mandate."""
        node = self._mandates.get(mandate_id)
        if node is None:
            raise ValueError(f"Mandate {mandate_id} not found")
        node.freeze(reason)

    def freeze_children(self, mandate_id: str, reason: str = "") -> None:
        """Freeze all children of a mandate recursively (not the mandate itself)."""
        children = self.get_children(mandate_id)
        for child in children:
            child.freeze(reason)
            self.freeze_children(child.mandate_id, reason)

    def freeze_tree(self, mandate_id: str, reason: str = "") -> None:
        """Freeze a mandate and all its descendants."""
        self.freeze(mandate_id, reason)
        self.freeze_children(mandate_id, reason)

    def resume(self, mandate_id: str) -> None:
        """Resume a frozen mandate. Only succeeds if parent is active."""
        node = self._mandates.get(mandate_id)
        if node is None:
            raise ValueError(f"Mandate {mandate_id} not found")

        # Check parent is active (if parent exists)
        if node.parent_id:
            parent = self._mandates.get(node.parent_id)
            if parent is not None and not parent.is_active:
                raise ValueError(
                    f"Cannot resume: parent {node.parent_id} is {parent.status.value}"
                )

        node.resume()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _narrow_scope(
        parent_scope: list[str],
        child_scope: list[str] | None,
        label: str,
    ) -> list[str]:
        """Ensure child scope is a subset of parent scope.

        If parent has no restrictions (empty list), child can set any.
        If parent has restrictions, child must be a subset or default to parent's.
        """
        if not parent_scope:
            # Parent has no restrictions — child can define freely
            return child_scope or []

        if not child_scope:
            # Child didn't specify — inherit parent scope
            return list(parent_scope)

        # Validate subset
        invalid = set(child_scope) - set(parent_scope)
        if invalid:
            raise ValueError(
                f"Child {label} {invalid} not in parent scope {parent_scope}"
            )
        return child_scope
