"""Session-Bound Anti-Relay Protection (Threat T3).

From Sardis Protocol Spec v1.1, Section 22:

Every payment evaluation includes a session_hash that binds it to a specific
merchant interaction. Even if an attacker intercepts the evaluation, they
cannot relay it to a different merchant or session.

    session_hash = SHA-256(merchant_id + service_id + timestamp_bucket)

Verification:
1. Compute expected session_hash from request data
2. Compare with provided session_hash
3. Reject if mismatch (relay detected)
"""

from __future__ import annotations

import hashlib
import time


def compute_session_hash(
    merchant: str,
    service_id: str,
    timestamp: float | None = None,
    bucket_seconds: int = 300,  # 5 minute window
) -> str:
    """Compute session-bound hash for anti-relay protection.

    The hash binds a payment to a specific merchant + service + time window.
    A relay attacker cannot reuse this for a different merchant.
    """
    ts = timestamp or time.time()
    bucket = int(ts / bucket_seconds) * bucket_seconds
    payload = f"{merchant}|{service_id}|{bucket}"
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_session_hash(
    provided_hash: str,
    merchant: str,
    service_id: str,
    timestamp: float | None = None,
    bucket_seconds: int = 300,
    tolerance_buckets: int = 1,  # also check prev bucket
) -> tuple[bool, str]:
    """Verify session hash matches expected value.

    Checks current bucket and one previous to handle boundary conditions.
    Returns (valid, reason).
    """
    if not provided_hash:
        return True, "No session_hash provided (transparent mode)"

    ts = timestamp or time.time()

    # Check current and adjacent buckets
    for offset in range(tolerance_buckets + 1):
        check_ts = ts - (offset * bucket_seconds)
        expected = compute_session_hash(merchant, service_id, check_ts, bucket_seconds)
        if provided_hash == expected:
            return True, "Session hash verified"

    return False, (
        f"Session hash mismatch — possible relay attack. "
        f"Hash does not match merchant={merchant}, service={service_id} "
        f"in any valid time window."
    )
