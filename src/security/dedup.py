"""Deduplication and replay protection for Sardis Guard.

Three layers of protection:
1. Idempotency keys — client provides a key, same key = same response
2. Nonce tracking — per-agent monotonic nonce, rejects out-of-order or replayed
3. Challenge binding — each MPP challenge ID is single-use (handled by pympp MemoryStore)

Fail-closed: if the dedup store is unavailable, REJECT the payment.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    """Result of dedup check."""
    is_duplicate: bool
    original_event_id: str | None = None
    original_timestamp: float | None = None
    reason: str = ""


class DedupStore:
    """SQLite-backed deduplication store.

    Tracks:
    - Idempotency keys (24h TTL) — same key returns cached result
    - Agent nonces — monotonically increasing per agent
    - Request fingerprints — SHA-256 of (agent_id, amount, merchant, timestamp_bucket)
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "dedup.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idempotency_key TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_nonces (
                agent_id TEXT PRIMARY KEY,
                last_nonce INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS request_fingerprints (
                fingerprint TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_idem_expires ON idempotency_keys(expires_at);
            CREATE INDEX IF NOT EXISTS idx_fp_expires ON request_fingerprints(expires_at);
        """)
        conn.commit()

    def check_idempotency(self, key: str) -> DedupResult:
        """Check if an idempotency key has been seen before."""
        if not key:
            return DedupResult(is_duplicate=False)

        conn = self._get_conn()
        now = time.time()

        # Clean expired
        conn.execute("DELETE FROM idempotency_keys WHERE expires_at < ?", (now,))

        row = conn.execute(
            "SELECT event_id, created_at FROM idempotency_keys WHERE idempotency_key = ?",
            (key,),
        ).fetchone()

        if row:
            return DedupResult(
                is_duplicate=True,
                original_event_id=row[0],
                original_timestamp=row[1],
                reason=f"Idempotency key '{key}' already used at {row[1]:.0f}",
            )

        return DedupResult(is_duplicate=False)

    def record_idempotency(self, key: str, event_id: str, result_json: str, ttl: int = 86400):
        """Record an idempotency key after successful processing."""
        if not key:
            return
        conn = self._get_conn()
        now = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO idempotency_keys VALUES (?, ?, ?, ?, ?)",
            (key, event_id, result_json, now, now + ttl),
        )
        conn.commit()

    def check_nonce(self, agent_id: str, nonce: int) -> DedupResult:
        """Check agent nonce is strictly increasing. Prevents replay attacks."""
        if nonce < 0:
            return DedupResult(is_duplicate=False)  # nonce not provided

        conn = self._get_conn()
        row = conn.execute(
            "SELECT last_nonce FROM agent_nonces WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()

        if row:
            last_nonce = row[0]
            if nonce <= last_nonce:
                return DedupResult(
                    is_duplicate=True,
                    reason=f"Nonce {nonce} <= last seen {last_nonce} for agent {agent_id}. "
                    f"Possible replay attack.",
                )

        return DedupResult(is_duplicate=False)

    def record_nonce(self, agent_id: str, nonce: int):
        """Record the latest nonce for an agent."""
        if nonce < 0:
            return
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO agent_nonces VALUES (?, ?, ?) "
            "ON CONFLICT(agent_id) DO UPDATE SET last_nonce = ?, updated_at = ?",
            (agent_id, nonce, time.time(), nonce, time.time()),
        )
        conn.commit()

    def check_fingerprint(self, agent_id: str, amount: str, merchant: str,
                          window_seconds: int = 5) -> DedupResult:
        """Detect near-duplicate requests within a time window.

        Creates a fingerprint from (agent_id, amount, merchant, time_bucket).
        If the same fingerprint appears within window_seconds, it's a duplicate.
        """
        # Time bucket = current time rounded to window_seconds
        now = time.time()
        time_bucket = int(now / window_seconds) * window_seconds

        payload = f"{agent_id}|{amount}|{merchant}|{time_bucket}"
        fingerprint = hashlib.sha256(payload.encode()).hexdigest()

        conn = self._get_conn()

        # Clean expired
        conn.execute("DELETE FROM request_fingerprints WHERE expires_at < ?", (now,))

        row = conn.execute(
            "SELECT event_id, created_at FROM request_fingerprints WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()

        if row:
            return DedupResult(
                is_duplicate=True,
                original_event_id=row[0],
                original_timestamp=row[1],
                reason=f"Near-duplicate request detected within {window_seconds}s window. "
                f"Same agent ({agent_id}), amount ({amount}), merchant ({merchant}).",
            )

        return DedupResult(is_duplicate=False)

    def record_fingerprint(self, fingerprint_input: str, agent_id: str, amount: str,
                           merchant: str, event_id: str, window_seconds: int = 5):
        """Record a request fingerprint."""
        now = time.time()
        time_bucket = int(now / window_seconds) * window_seconds
        payload = f"{agent_id}|{amount}|{merchant}|{time_bucket}"
        fingerprint = hashlib.sha256(payload.encode()).hexdigest()

        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO request_fingerprints VALUES (?, ?, ?, ?, ?)",
            (fingerprint, event_id, agent_id, now, now + window_seconds * 2),
        )
        conn.commit()

    def check_all(self, agent_id: str, amount: str, merchant: str,
                  idempotency_key: str = "", nonce: int = -1) -> DedupResult:
        """Run all dedup checks. Returns first failure or success."""
        # 1. Idempotency key
        result = self.check_idempotency(idempotency_key)
        if result.is_duplicate:
            return result

        # 2. Nonce
        result = self.check_nonce(agent_id, nonce)
        if result.is_duplicate:
            return result

        # 3. Fingerprint (near-duplicate detection)
        result = self.check_fingerprint(agent_id, amount, merchant)
        if result.is_duplicate:
            return result

        return DedupResult(is_duplicate=False)

    def record_all(self, agent_id: str, amount: str, merchant: str,
                   event_id: str, idempotency_key: str = "", nonce: int = -1,
                   result_json: str = ""):
        """Record all dedup markers after successful processing."""
        self.record_idempotency(idempotency_key, event_id, result_json)
        self.record_nonce(agent_id, nonce)
        self.record_fingerprint("", agent_id, amount, merchant, event_id)
