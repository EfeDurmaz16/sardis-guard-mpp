"""Kill Switch — Emergency Payment Halt (Gate 1).

From Sardis Protocol Spec v1.1:
  "Global / Org / Agent / Chain scope. Redis-backed, multi-instance safe.
   Auto-reactivation timer. Active → IMMEDIATE REJECT."

The kill switch is the FIRST gate in the pipeline — before dedup, governance,
sanctions, or any other check. If active, all payments are rejected instantly.

Four scopes (checked in order, most general first):
  1. GLOBAL  — stops ALL payments across all agents/orgs
  2. ORG     — stops all payments for a specific principal/organization
  3. AGENT   — stops all payments for a specific agent
  4. CHAIN   — stops all payments on a specific chain/network

Each kill switch has:
  - activated_at: when it was triggered
  - reason: why (sanctions alert, anomaly detection, manual, etc.)
  - auto_reactivate_at: when to auto-lift (0 = manual lift only)
  - activated_by: who triggered it (system, operator, anomaly_detector)

In production: Redis-backed for multi-instance safety.
In hackathon: SQLite-backed (same DB as events).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class KillSwitchScope(str, Enum):
    GLOBAL = "global"
    ORG = "org"
    AGENT = "agent"
    CHAIN = "chain"


@dataclass
class KillSwitchState:
    """Current state of a kill switch."""
    active: bool
    scope: KillSwitchScope
    target: str  # "" for global, org_id/agent_id/chain for others
    reason: str
    activated_at: float
    auto_reactivate_at: float  # 0 = manual only
    activated_by: str


@dataclass
class KillSwitchCheckResult:
    """Result of checking all kill switches."""
    blocked: bool
    active_switches: list[KillSwitchState]
    reason: str

    @property
    def summary(self) -> str:
        if not self.blocked:
            return "No active kill switches"
        scopes = [s.scope.value for s in self.active_switches]
        return f"BLOCKED by kill switch(es): {', '.join(scopes)} — {self.reason}"


class KillSwitchManager:
    """Manages kill switches across all scopes.

    SQLite-backed for hackathon. In production, this would be Redis
    with pub/sub for multi-instance propagation.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "kill_switch.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kill_switches (
                scope TEXT NOT NULL,
                target TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL,
                activated_at REAL NOT NULL,
                auto_reactivate_at REAL NOT NULL DEFAULT 0,
                activated_by TEXT NOT NULL DEFAULT 'system',
                PRIMARY KEY (scope, target)
            )
        """)
        conn.commit()

    def activate(
        self,
        scope: KillSwitchScope,
        target: str = "",
        reason: str = "Manual activation",
        auto_lift_seconds: int = 0,
        activated_by: str = "operator",
    ) -> KillSwitchState:
        """Activate a kill switch."""
        now = time.time()
        auto_reactivate = (now + auto_lift_seconds) if auto_lift_seconds > 0 else 0.0

        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO kill_switches VALUES (?, ?, ?, ?, ?, ?)",
            (scope.value, target, reason, now, auto_reactivate, activated_by),
        )
        conn.commit()

        return KillSwitchState(
            active=True,
            scope=scope,
            target=target,
            reason=reason,
            activated_at=now,
            auto_reactivate_at=auto_reactivate,
            activated_by=activated_by,
        )

    def deactivate(self, scope: KillSwitchScope, target: str = "") -> bool:
        """Deactivate a kill switch. Returns True if it was active."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM kill_switches WHERE scope = ? AND target = ?",
            (scope.value, target),
        )
        conn.commit()
        return cursor.rowcount > 0

    def check(
        self,
        agent_id: str = "",
        principal_id: str = "",
        chain: str = "",
    ) -> KillSwitchCheckResult:
        """Check all kill switches for a payment. Returns immediately if any are active.

        Check order: GLOBAL → ORG → AGENT → CHAIN (most general first).
        """
        now = time.time()
        conn = self._get_conn()

        # Auto-lift expired switches
        conn.execute(
            "DELETE FROM kill_switches WHERE auto_reactivate_at > 0 AND auto_reactivate_at < ?",
            (now,),
        )
        conn.commit()

        active = []

        # Check GLOBAL
        row = conn.execute(
            "SELECT * FROM kill_switches WHERE scope = 'global'",
        ).fetchone()
        if row:
            active.append(self._row_to_state(row))

        # Check ORG
        if principal_id:
            row = conn.execute(
                "SELECT * FROM kill_switches WHERE scope = 'org' AND target = ?",
                (principal_id,),
            ).fetchone()
            if row:
                active.append(self._row_to_state(row))

        # Check AGENT
        if agent_id:
            row = conn.execute(
                "SELECT * FROM kill_switches WHERE scope = 'agent' AND target = ?",
                (agent_id,),
            ).fetchone()
            if row:
                active.append(self._row_to_state(row))

        # Check CHAIN
        if chain:
            row = conn.execute(
                "SELECT * FROM kill_switches WHERE scope = 'chain' AND target = ?",
                (chain,),
            ).fetchone()
            if row:
                active.append(self._row_to_state(row))

        if active:
            reasons = [f"[{s.scope.value}] {s.reason}" for s in active]
            return KillSwitchCheckResult(
                blocked=True,
                active_switches=active,
                reason="; ".join(reasons),
            )

        return KillSwitchCheckResult(blocked=False, active_switches=[], reason="")

    def list_active(self) -> list[KillSwitchState]:
        """List all active kill switches."""
        now = time.time()
        conn = self._get_conn()

        # Auto-lift expired
        conn.execute(
            "DELETE FROM kill_switches WHERE auto_reactivate_at > 0 AND auto_reactivate_at < ?",
            (now,),
        )
        conn.commit()

        rows = conn.execute("SELECT * FROM kill_switches").fetchall()
        return [self._row_to_state(r) for r in rows]

    def _row_to_state(self, row) -> KillSwitchState:
        return KillSwitchState(
            active=True,
            scope=KillSwitchScope(row[0]),
            target=row[1],
            reason=row[2],
            activated_at=row[3],
            auto_reactivate_at=row[4],
            activated_by=row[5],
        )
