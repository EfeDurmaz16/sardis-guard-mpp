"""Sardis Guard Client SDK — Compose policy checks with downstream MPP services.

Usage:
    guard = SardisGuardClient()
    result = guard.guarded_request(
        method="POST",
        url="https://stableenrich.dev/api/exa/search",
        data={"query": "AI agent payments"},
        amount="0.01",
        merchant="stableenrich.dev",
    )

Flow:
    1. Agent wants to call a paid API (Perplexity, StableEnrich, etc.)
    2. Client calls Sardis Guard /evaluate via MPP to check policy
    3. If ALLOWED → proceed to call the downstream service via MPP
    4. If DENIED → return denial reason, never call downstream (save money)
"""

from __future__ import annotations

import json
import logging
import subprocess
import shutil
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("sardis_guard")

GUARD_URL = "https://dendric-margie-answerlessly.ngrok-free.dev"

# Well-known MPP service URLs
MPP_SERVICES = {
    "perplexity": "https://perplexity.mpp.paywithlocus.com/perplexity/search",
    "exa": "https://stableenrich.dev/api/exa/search",
    "stableenrich": "https://stableenrich.dev/api/exa/search",
}


class TempoError(Exception):
    """Raised when the tempo CLI fails."""


class PolicyDeniedError(Exception):
    """Raised when Sardis Guard denies a payment."""

    def __init__(self, verdict: dict):
        self.verdict = verdict
        summary = verdict.get("summary", "Policy denied")
        super().__init__(summary)


@dataclass
class GuardVerdict:
    """Result of a Sardis Guard policy evaluation."""

    allowed: bool
    summary: str
    checks: list[dict]
    latency_ms: float
    agent_id: str
    payment_tx: str | None = None
    raw: dict | None = None

    @classmethod
    def from_response(cls, data: dict) -> GuardVerdict:
        verdict = data.get("verdict", {})
        payment = data.get("payment", {})
        return cls(
            allowed=verdict.get("allowed", False),
            summary=verdict.get("summary", "Unknown"),
            checks=verdict.get("checks", []),
            latency_ms=verdict.get("total_latency_ms", 0),
            agent_id=data.get("agent", "unknown"),
            payment_tx=payment.get("tx"),
            raw=data,
        )


@dataclass
class GuardedResponse:
    """Result of a guarded request: policy verdict + optional downstream response."""

    verdict: GuardVerdict
    allowed: bool
    downstream_response: dict | str | None = None
    downstream_status: str | None = None
    error: str | None = None


class SardisGuardClient:
    """Client SDK that composes Sardis Guard policy checks with downstream MPP services.

    Uses the tempo CLI for all MPP requests (wallet key is managed by tempo CLI).
    """

    def __init__(
        self,
        guard_url: str = GUARD_URL,
        tempo_path: str | None = None,
        timeout: int = 30,
        retries: int = 2,
    ):
        self.guard_url = guard_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

        # Find tempo CLI
        if tempo_path:
            self.tempo_path = tempo_path
        else:
            found = shutil.which("tempo")
            if not found:
                raise TempoError(
                    "tempo CLI not found. Install it: https://docs.tempo.xyz/cli"
                )
            self.tempo_path = found

    # --- Core tempo CLI wrapper ---

    def _tempo_request(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict | str:
        """Execute a tempo request and return the parsed response.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            url: Full URL to request.
            data: JSON body for POST/PUT requests.
            extra_headers: Additional headers to include.

        Returns:
            Parsed JSON dict or raw string if not JSON.

        Raises:
            TempoError: If the tempo CLI fails or returns an error.
        """
        cmd = [self.tempo_path, "request", "-t"]
        cmd.extend(["-X", method.upper()])

        if extra_headers:
            for key, value in extra_headers.items():
                cmd.extend(["-H", f"{key}: {value}"])

        if data is not None and method.upper() in ("POST", "PUT", "PATCH"):
            cmd.extend(["--json", json.dumps(data)])

        if self.timeout:
            cmd.extend(["-m", str(self.timeout)])

        if self.retries:
            cmd.extend(["--retries", str(self.retries)])

        cmd.append(url)

        logger.debug("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,  # extra buffer over HTTP timeout
            )
        except subprocess.TimeoutExpired:
            raise TempoError(f"tempo request timed out after {self.timeout}s")
        except FileNotFoundError:
            raise TempoError(f"tempo CLI not found at {self.tempo_path}")

        output = result.stdout.strip()

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Check if it's a payment-related error (402) — these contain useful info
            if "402" in stderr or "Payment Required" in stderr:
                raise TempoError(
                    f"Payment required but tempo could not complete payment: {stderr}"
                )
            raise TempoError(
                f"tempo request failed (exit {result.returncode}): {stderr or output}"
            )

        # Parse response — tempo outputs the HTTP response body
        return self._parse_output(output)

    def _parse_output(self, output: str) -> dict | str:
        """Parse tempo CLI output, extracting JSON from potentially mixed output."""
        if not output:
            return {}

        # Try direct JSON parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # tempo may output payment info lines before the JSON body.
        # Look for the last JSON object/array in the output.
        lines = output.split("\n")
        json_lines: list[str] = []
        in_json = False

        for line in reversed(lines):
            stripped = line.strip()
            if not in_json and (stripped.startswith("{") or stripped.startswith("[")):
                in_json = True
            if in_json:
                json_lines.insert(0, line)
            if in_json and (stripped.endswith("}") or stripped.endswith("]")):
                break

        if json_lines:
            try:
                return json.loads("\n".join(json_lines))
            except json.JSONDecodeError:
                pass

        # Fall back: try each line individually (some APIs return single-line JSON)
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        # Return raw output if nothing parses
        return output

    # --- Guard API Methods ---

    def evaluate(
        self,
        amount: str,
        merchant: str,
        currency: str = "USDC",
        network: str = "tempo",
        category: str = "general",
        memo: str | None = None,
    ) -> GuardVerdict:
        """Evaluate a payment against Sardis Guard's 12-check policy engine.

        Args:
            amount: Payment amount as string (e.g. "0.01").
            merchant: Merchant URL or identifier.
            currency: Payment currency (default: USDC).
            network: Blockchain network (default: tempo).
            category: Spending category (default: general).
            memo: Optional memo/description.

        Returns:
            GuardVerdict with the policy decision.

        Raises:
            TempoError: If the tempo request fails.
            PolicyDeniedError: Never raised here — check verdict.allowed instead.
        """
        payload: dict[str, Any] = {
            "amount": amount,
            "merchant": merchant,
            "currency": currency,
            "network": network,
            "category": category,
        }
        if memo:
            payload["memo"] = memo

        logger.info("Evaluating: $%s to %s", amount, merchant)

        response = self._tempo_request(
            method="POST",
            url=f"{self.guard_url}/evaluate",
            data=payload,
        )

        if isinstance(response, str):
            raise TempoError(f"Unexpected Guard response: {response}")

        verdict = GuardVerdict.from_response(response)
        logger.info("Verdict: %s", verdict.summary)
        return verdict

    def guarded_request(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        amount: str = "0.01",
        merchant: str | None = None,
        currency: str = "USDC",
        network: str = "tempo",
        category: str = "api_call",
        memo: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> GuardedResponse:
        """Evaluate policy via Sardis Guard, then call downstream service if allowed.

        This is the main method for composing Guard with any MPP service.

        Args:
            method: HTTP method for the downstream call.
            url: Downstream service URL.
            data: Request body for downstream call.
            amount: Expected cost of the downstream call.
            merchant: Merchant identifier (derived from URL if not provided).
            currency: Payment currency.
            network: Blockchain network.
            category: Spending category.
            memo: Optional memo.
            extra_headers: Additional headers for the downstream call.

        Returns:
            GuardedResponse with verdict and optional downstream response.
        """
        # Derive merchant from URL if not provided
        if not merchant:
            from urllib.parse import urlparse
            merchant = urlparse(url).netloc

        # Step 1: Evaluate policy via Sardis Guard
        try:
            verdict = self.evaluate(
                amount=amount,
                merchant=merchant,
                currency=currency,
                network=network,
                category=category,
                memo=memo,
            )
        except TempoError as e:
            return GuardedResponse(
                verdict=GuardVerdict(
                    allowed=False,
                    summary=f"Guard evaluation failed: {e}",
                    checks=[],
                    latency_ms=0,
                    agent_id="unknown",
                ),
                allowed=False,
                error=str(e),
            )

        # Step 2: If DENIED, return immediately without calling downstream
        if not verdict.allowed:
            logger.warning("DENIED by Guard: %s", verdict.summary)
            return GuardedResponse(
                verdict=verdict,
                allowed=False,
                error=verdict.summary,
            )

        # Step 3: ALLOWED — call the downstream service via MPP
        logger.info("ALLOWED — calling downstream: %s %s", method, url)
        try:
            downstream = self._tempo_request(
                method=method,
                url=url,
                data=data,
                extra_headers=extra_headers,
            )
            return GuardedResponse(
                verdict=verdict,
                allowed=True,
                downstream_response=downstream,
                downstream_status="success",
            )
        except TempoError as e:
            logger.error("Downstream call failed: %s", e)
            return GuardedResponse(
                verdict=verdict,
                allowed=True,  # Guard allowed it, but downstream failed
                downstream_response=None,
                downstream_status="error",
                error=f"Downstream call failed: {e}",
            )

    def get_mandate(self) -> dict:
        """View the current spending mandate for this agent.

        Returns:
            Dict with mandate details (max_per_tx, max_daily, allowed_merchants, etc.)
        """
        response = self._tempo_request(
            method="GET",
            url=f"{self.guard_url}/mandate",
        )
        if isinstance(response, str):
            raise TempoError(f"Unexpected mandate response: {response}")
        return response

    def update_mandate(self, **kwargs) -> dict:
        """Update the spending mandate for this agent.

        Keyword Args:
            max_per_tx: Max amount per transaction (str).
            max_daily: Max daily spending (str).
            allowed_merchants: List of allowed merchant identifiers.
            blocked_merchants: List of blocked merchant identifiers.
            allowed_categories: List of allowed categories.
            blocked_categories: List of blocked categories.
            allowed_chains: List of allowed blockchain networks.
            allowed_currencies: List of allowed currencies.
            require_memo: Whether memo is required (bool).
            cooldown_seconds: Min seconds between payments (int).

        Returns:
            Dict with update confirmation.
        """
        # Filter out None values
        payload = {k: v for k, v in kwargs.items() if v is not None}

        if not payload:
            raise ValueError("No mandate fields to update")

        response = self._tempo_request(
            method="PUT",
            url=f"{self.guard_url}/mandate",
            data=payload,
        )
        if isinstance(response, str):
            raise TempoError(f"Unexpected mandate update response: {response}")
        return response

    def get_stats(self) -> dict:
        """Get spending statistics for this agent.

        Returns:
            Dict with stats (spent_today, tx_count_today, last_payment_ts).
        """
        response = self._tempo_request(
            method="GET",
            url=f"{self.guard_url}/stats",
        )
        if isinstance(response, str):
            raise TempoError(f"Unexpected stats response: {response}")
        return response

    def health(self) -> dict:
        """Check Guard service health (free, no MPP payment required).

        This calls the health endpoint directly via subprocess/curl since
        it doesn't require MPP payment.
        """
        # Health endpoint is free — still use tempo for consistency
        # but it won't trigger payment
        try:
            result = subprocess.run(
                ["curl", "-s", "-m", "5", f"{self.guard_url}/health"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return self._parse_output(result.stdout.strip())
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    # --- Convenience Methods for Known Services ---

    def search_exa(self, query: str, amount: str = "0.01") -> GuardedResponse:
        """Search via StableEnrich/Exa with Guard policy check.

        Args:
            query: Search query string.
            amount: Cost per search (default: $0.01).

        Returns:
            GuardedResponse with search results if allowed.
        """
        return self.guarded_request(
            method="POST",
            url=MPP_SERVICES["exa"],
            data={"query": query},
            amount=amount,
            merchant="stableenrich.dev",
            category="search",
            memo=f"Exa search: {query[:50]}",
        )

    def search_perplexity(self, query: str, amount: str = "0.05") -> GuardedResponse:
        """Search via Perplexity with Guard policy check.

        Args:
            query: Search query string.
            amount: Cost per search (default: $0.05).

        Returns:
            GuardedResponse with search results if allowed.
        """
        return self.guarded_request(
            method="POST",
            url=MPP_SERVICES["perplexity"],
            data={"query": query},
            amount=amount,
            merchant="perplexity.mpp.paywithlocus.com",
            category="search",
            memo=f"Perplexity search: {query[:50]}",
        )


# --- CLI Quick Test ---

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    guard = SardisGuardClient()

    print("\n=== Sardis Guard Client ===\n")

    # Health check (free)
    print("[1] Health check...")
    health = guard.health()
    print(f"    Status: {health}\n")

    # Evaluate a small payment
    print("[2] Evaluating $0.01 payment to stableenrich.dev...")
    verdict = guard.evaluate(
        amount="0.01",
        merchant="stableenrich.dev",
        category="search",
    )
    print(f"    Allowed: {verdict.allowed}")
    print(f"    Summary: {verdict.summary}")
    print(f"    Checks:  {len(verdict.checks)} run, {len([c for c in verdict.checks if c['result'] == 'FAIL'])} failed\n")

    # Get stats
    print("[3] Getting spending stats...")
    stats = guard.get_stats()
    print(f"    Stats: {json.dumps(stats, indent=2)}\n")

    print("Done.")
