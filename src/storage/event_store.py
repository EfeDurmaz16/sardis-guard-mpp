"""Sardis Guard — Event Store.

SQLite WAL-mode for source-of-truth event storage with hash chain integrity.
DuckDB read model attached for analytics queries.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
from pathlib import Path
from typing import Any

import duckdb

from src.types import PaymentIntentEvent

_DEFAULT_DB = Path.home() / "sardis-mpp-hackathon" / "data" / "sardis_guard.db"


class EventStore:
    """Append-only event store with hash-chain integrity and analytics."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = str(db_path or _DEFAULT_DB)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection helpers (one connection per thread for SQLite safety)
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id           TEXT PRIMARY KEY,
                timestamp          REAL NOT NULL,
                agent_id           TEXT NOT NULL,
                principal_id       TEXT NOT NULL DEFAULT '',
                mandate_id         TEXT NOT NULL DEFAULT '',
                parent_mandate_id  TEXT,
                amount             TEXT NOT NULL DEFAULT '0',
                currency           TEXT NOT NULL DEFAULT 'USDC',
                network            TEXT NOT NULL DEFAULT 'tempo',
                merchant           TEXT NOT NULL DEFAULT '',
                category           TEXT NOT NULL DEFAULT 'general',
                service_id         TEXT NOT NULL DEFAULT '',
                service_path       TEXT NOT NULL DEFAULT '',
                purpose            TEXT NOT NULL DEFAULT '',
                destination_address TEXT NOT NULL DEFAULT '',
                prompt_hash        TEXT NOT NULL DEFAULT '',
                policy_verdict     TEXT NOT NULL DEFAULT '{}',
                governance_result  TEXT NOT NULL DEFAULT '{}',
                risk_assessment    TEXT NOT NULL DEFAULT '{}',
                aml_result         TEXT NOT NULL DEFAULT '{}',
                action             TEXT NOT NULL DEFAULT 'ALLOW',
                evidence_refs      TEXT NOT NULL DEFAULT '[]',
                downstream_allowed INTEGER NOT NULL DEFAULT 1,
                prev_hash          TEXT NOT NULL DEFAULT '',
                entry_hash         TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_mandate_id ON events(mandate_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_principal_id ON events(principal_id)
        """)
        conn.commit()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def insert_event(self, event: PaymentIntentEvent) -> str:
        """Insert event into the store, auto-computing hash chain."""
        prev_hash = self.get_last_hash()
        event.compute_hash(prev_hash)

        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO events (
                event_id, timestamp, agent_id, principal_id, mandate_id,
                parent_mandate_id, amount, currency, network, merchant,
                category, service_id, service_path, purpose,
                destination_address, prompt_hash,
                policy_verdict, governance_result, risk_assessment,
                aml_result, action, evidence_refs, downstream_allowed,
                prev_hash, entry_hash
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                event.event_id,
                event.timestamp,
                event.agent_id,
                event.principal_id,
                event.mandate_id,
                event.parent_mandate_id,
                str(event.amount),
                event.currency,
                event.network,
                event.merchant,
                event.category,
                event.service_id,
                event.service_path,
                event.purpose,
                event.destination_address,
                event.prompt_hash,
                json.dumps(event.policy_verdict),
                json.dumps(event.governance_result),
                json.dumps(event.risk_assessment),
                json.dumps(event.aml_result),
                event.action.value,
                json.dumps(event.evidence_refs),
                1 if event.downstream_allowed else 0,
                event.prev_hash,
                event.entry_hash,
            ),
        )
        conn.commit()
        return event.entry_hash

    # ------------------------------------------------------------------
    # Read path (SQLite)
    # ------------------------------------------------------------------

    def get_events(
        self,
        agent_id: str | None = None,
        mandate_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve events with optional filters, oldest first (ASC).

        Hash chain validation requires oldest-to-newest ordering:
        events[i].prev_hash must equal events[i-1].entry_hash.
        """
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []

        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if mandate_id is not None:
            clauses.append("mandate_id = ?")
            params.append(mandate_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM events {where} ORDER BY timestamp ASC, rowid ASC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_event_count(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) AS cnt FROM events").fetchone()
        return row["cnt"] if row else 0

    def get_last_hash(self) -> str:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT entry_hash FROM events ORDER BY timestamp DESC, rowid DESC LIMIT 1"
        ).fetchone()
        return row["entry_hash"] if row else ""

    # ------------------------------------------------------------------
    # Analytics read model (DuckDB)
    # ------------------------------------------------------------------

    def _duck(self) -> duckdb.DuckDBPyConnection:
        """Create a transient DuckDB connection that reads from SQLite."""
        duck = duckdb.connect("")
        duck.execute("INSTALL sqlite; LOAD sqlite;")
        duck.execute(
            f"ATTACH '{self._db_path}' AS sdb (TYPE sqlite, READ_ONLY)"
        )
        return duck

    def get_agent_summary(self, agent_id: str) -> dict[str, Any]:
        """Per-agent aggregate: total_spent, tx_count, unique_merchants, risk_trend."""
        duck = self._duck()
        row = duck.execute(
            """
            SELECT
                COALESCE(SUM(CAST(amount AS DOUBLE)), 0)  AS total_spent,
                COUNT(*)                                   AS tx_count,
                COUNT(DISTINCT merchant)                   AS unique_merchants
            FROM sdb.events
            WHERE agent_id = ?
            """,
            [agent_id],
        ).fetchone()

        total_spent, tx_count, unique_merchants = row if row else (0, 0, 0)

        # Risk trend: slope of final_score over last 20 events
        trend_rows = duck.execute(
            """
            SELECT
                risk_assessment
            FROM sdb.events
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            [agent_id],
        ).fetchall()

        risk_trend = self._compute_risk_trend(trend_rows)
        duck.close()

        return {
            "agent_id": agent_id,
            "total_spent": round(total_spent, 2),
            "tx_count": tx_count,
            "unique_merchants": unique_merchants,
            "risk_trend": risk_trend,
        }

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Aggregate stats across all agents for dashboard."""
        duck = self._duck()
        row = duck.execute(
            """
            SELECT
                COUNT(*)                                   AS total_events,
                COUNT(DISTINCT agent_id)                   AS active_agents,
                COALESCE(SUM(CAST(amount AS DOUBLE)), 0)  AS total_volume,
                COUNT(DISTINCT merchant)                   AS unique_merchants,
                COUNT(CASE WHEN action = 'DENY' THEN 1 END) AS denied_count,
                COUNT(CASE WHEN action = 'FLAG' THEN 1 END) AS flagged_count,
                COUNT(CASE WHEN action = 'HOLD' THEN 1 END) AS held_count,
                COUNT(CASE WHEN action IN ('FREEZE_CHILD', 'FREEZE_TREE') THEN 1 END) AS frozen_count
            FROM sdb.events
            """
        ).fetchone()

        duck.close()

        if not row:
            return {
                "total_events": 0,
                "active_agents": 0,
                "total_volume": 0.0,
                "unique_merchants": 0,
                "denied_count": 0,
                "flagged_count": 0,
                "held_count": 0,
                "frozen_count": 0,
            }

        return {
            "total_events": row[0],
            "active_agents": row[1],
            "total_volume": round(row[2], 2),
            "unique_merchants": row[3],
            "denied_count": row[4],
            "flagged_count": row[5],
            "held_count": row[6],
            "frozen_count": row[7],
        }

    def get_risk_timeline(self, agent_id: str) -> list[dict[str, Any]]:
        """List of (timestamp, final_score) for charting risk over time."""
        duck = self._duck()
        rows = duck.execute(
            """
            SELECT timestamp, risk_assessment
            FROM sdb.events
            WHERE agent_id = ?
            ORDER BY timestamp ASC
            """,
            [agent_id],
        ).fetchall()
        duck.close()

        timeline = []
        for ts, ra_json in rows:
            score = self._extract_final_score(ra_json)
            timeline.append({"timestamp": ts, "final_score": score})
        return timeline

    def get_service_graph(self) -> dict[str, list[dict[str, Any]]]:
        """Adjacency list of service transitions for graph visualization.

        Returns: { "edges": [ {"from": svc_a, "to": svc_b, "weight": count}, ... ] }
        """
        duck = self._duck()
        rows = duck.execute(
            """
            WITH ordered AS (
                SELECT
                    agent_id,
                    service_id,
                    LAG(service_id) OVER (PARTITION BY agent_id ORDER BY timestamp) AS prev_service
                FROM sdb.events
                WHERE service_id != ''
            )
            SELECT prev_service, service_id, COUNT(*) AS weight
            FROM ordered
            WHERE prev_service IS NOT NULL AND prev_service != ''
            GROUP BY prev_service, service_id
            ORDER BY weight DESC
            """
        ).fetchall()
        duck.close()

        edges = [
            {"from": r[0], "to": r[1], "weight": r[2]} for r in rows
        ]
        return {"edges": edges}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        # Parse JSON fields back
        for field in (
            "policy_verdict",
            "governance_result",
            "risk_assessment",
            "aml_result",
            "evidence_refs",
        ):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        d["downstream_allowed"] = bool(d.get("downstream_allowed", 1))
        return d

    @staticmethod
    def _extract_final_score(ra_json: str) -> float:
        if not ra_json:
            return 0.0
        try:
            ra = json.loads(ra_json) if isinstance(ra_json, str) else ra_json
            return float(ra.get("final_score", 0.0))
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _compute_risk_trend(trend_rows: list) -> str:
        """Compute risk trend from last N risk_assessment JSON blobs.

        Returns 'rising', 'falling', or 'stable'.
        """
        if len(trend_rows) < 3:
            return "stable"

        scores = []
        for (ra_json,) in trend_rows:
            scores.append(EventStore._extract_final_score(ra_json))

        # Reverse so oldest is first (rows come newest-first)
        scores.reverse()

        n = len(scores)
        if n < 3:
            return "stable"

        # Simple linear regression slope
        x_mean = (n - 1) / 2.0
        y_mean = sum(scores) / n
        num = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
        den = sum((i - x_mean) ** 2 for i in range(n))

        if den == 0:
            return "stable"

        slope = num / den

        if slope > 0.01:
            return "rising"
        elif slope < -0.01:
            return "falling"
        else:
            return "stable"

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None
