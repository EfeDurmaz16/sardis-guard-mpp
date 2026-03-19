"""Sardis Guard — MPP Service Wrappers.

Thin wrappers around real MPP services. Each wrapper:
  - Calls `tempo request -t -X POST --json '...' URL` for MPP services
  - Uses httpx for direct JSON-RPC (Tempo RPC)
  - Parses JSON response
  - Returns structured result
  - Tracks cumulative cost

Usage:
    from src.services.wrappers import StableEnrichService
    svc = StableEnrichService()
    result = svc.exa_search("AI agent payments")
    print(result)
    print(f"Total cost: ${svc.total_cost:.4f}")
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("sardis_guard.services")


# ---------------------------------------------------------------------------
# Base result type
# ---------------------------------------------------------------------------

@dataclass
class ServiceResult:
    """Structured result from an MPP service call."""

    service_id: str
    action: str
    success: bool
    data: dict | list | str | None = None
    error: str | None = None
    cost: float = 0.0
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "action": self.action,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "cost": self.cost,
            "latency_ms": round(self.latency_ms, 1),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Base wrapper with shared tempo CLI logic
# ---------------------------------------------------------------------------

class _MPPServiceBase:
    """Base class for MPP service wrappers using the tempo CLI."""

    SERVICE_ID: str = ""
    BASE_URL: str = ""

    def __init__(self, tempo_path: str | None = None, timeout: int = 30):
        if tempo_path:
            self.tempo_path = tempo_path
        else:
            found = shutil.which("tempo")
            if not found:
                raise RuntimeError(
                    "tempo CLI not found in PATH. Install: https://docs.tempo.xyz/cli"
                )
            self.tempo_path = found
        self.timeout = timeout
        self.total_cost: float = 0.0
        self.call_count: int = 0
        self.call_log: list[ServiceResult] = []

    def _tempo_post(self, url: str, data: dict, cost: float = 0.0) -> ServiceResult:
        """Execute a POST via tempo request and return a ServiceResult."""
        action = url.rsplit("/", 1)[-1] if "/" in url else url
        t0 = time.monotonic()

        cmd = [
            self.tempo_path, "request", "-t",
            "-X", "POST",
            "--json", json.dumps(data),
            "-m", str(self.timeout),
            "--retries", "2",
            url,
        ]

        logger.debug("tempo POST %s | payload=%s", url, json.dumps(data)[:200])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
            )
        except subprocess.TimeoutExpired:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=f"Timeout after {self.timeout}s",
                cost=cost,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result
        except FileNotFoundError:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=f"tempo CLI not found at {self.tempo_path}",
                cost=0.0,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result

        latency = (time.monotonic() - t0) * 1000
        output = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=stderr or output or f"Exit code {proc.returncode}",
                cost=cost,
                latency_ms=latency,
            )
            self._record(result)
            return result

        # Parse JSON from potentially mixed output (tempo prints payment info lines)
        parsed = self._parse_output(output)
        result = ServiceResult(
            service_id=self.SERVICE_ID,
            action=action,
            success=True,
            data=parsed,
            cost=cost,
            latency_ms=latency,
        )
        self._record(result)
        return result

    def _tempo_get(self, url: str, cost: float = 0.0) -> ServiceResult:
        """Execute a GET via tempo request."""
        action = url.rsplit("/", 1)[-1] if "/" in url else url
        t0 = time.monotonic()

        cmd = [
            self.tempo_path, "request", "-t",
            "-X", "GET",
            "-m", str(self.timeout),
            "--retries", "2",
            url,
        ]

        logger.debug("tempo GET %s", url)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout + 10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=str(e),
                cost=cost,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result

        latency = (time.monotonic() - t0) * 1000
        output = proc.stdout.strip()

        if proc.returncode != 0:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=proc.stderr.strip() or output,
                cost=cost,
                latency_ms=latency,
            )
            self._record(result)
            return result

        parsed = self._parse_output(output)
        result = ServiceResult(
            service_id=self.SERVICE_ID,
            action=action,
            success=True,
            data=parsed,
            cost=cost,
            latency_ms=latency,
        )
        self._record(result)
        return result

    def _record(self, result: ServiceResult):
        """Track cost and log the call."""
        self.total_cost += result.cost
        self.call_count += 1
        self.call_log.append(result)
        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level,
            "[%s] %s — %s (%.0fms, $%.4f)",
            self.SERVICE_ID,
            result.action,
            "OK" if result.success else result.error,
            result.latency_ms,
            result.cost,
        )

    @staticmethod
    def _parse_output(output: str) -> dict | list | str:
        """Parse tempo CLI output, extracting JSON from potentially mixed output."""
        if not output:
            return {}

        # Try direct JSON parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # tempo may output payment info lines before the JSON body.
        # Find the last JSON block in the output.
        lines = output.split("\n")

        # Try to find a JSON object/array starting from the end
        for i in range(len(lines) - 1, -1, -1):
            candidate = "\n".join(lines[i:])
            stripped = candidate.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    continue

        # Try each line individually
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return output


# ---------------------------------------------------------------------------
# Perplexity
# ---------------------------------------------------------------------------

class PerplexityService(_MPPServiceBase):
    """Wrapper for Perplexity AI search via MPP.

    Endpoint: POST https://perplexity.mpp.paywithlocus.com/perplexity/search
    Cost: ~$0.05 per search (expensive — use sparingly)
    """

    SERVICE_ID = "perplexity"
    BASE_URL = "https://perplexity.mpp.paywithlocus.com"
    COST_PER_SEARCH = 0.05

    def search(self, query: str) -> ServiceResult:
        """Search using Perplexity AI via MPP.

        Args:
            query: Natural language search query.

        Returns:
            ServiceResult with search results in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/perplexity/search",
            data={"query": query},
            cost=self.COST_PER_SEARCH,
        )


# ---------------------------------------------------------------------------
# StableEnrich
# ---------------------------------------------------------------------------

class StableEnrichService(_MPPServiceBase):
    """Wrapper for StableEnrich enrichment APIs via MPP.

    Provides: Exa search, Firecrawl scraping, Apollo people search.
    Base URL: https://stableenrich.dev
    Cost: ~$0.007-0.01 per call (cheap — good for demos)
    """

    SERVICE_ID = "stableenrich"
    BASE_URL = "https://stableenrich.dev"
    COST_PER_EXA = 0.007
    COST_PER_FIRECRAWL = 0.01
    COST_PER_APOLLO = 0.01

    def exa_search(self, query: str, num_results: int = 3) -> ServiceResult:
        """Search the web using Exa via StableEnrich.

        Args:
            query: Search query string.
            num_results: Number of results to return (default 3).

        Returns:
            ServiceResult with search results in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/api/exa/search",
            data={"query": query, "num_results": num_results},
            cost=self.COST_PER_EXA,
        )

    def firecrawl_scrape(self, url: str) -> ServiceResult:
        """Scrape a URL using Firecrawl via StableEnrich.

        Args:
            url: The URL to scrape.

        Returns:
            ServiceResult with scraped content in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/api/firecrawl/scrape",
            data={"url": url},
            cost=self.COST_PER_FIRECRAWL,
        )

    def apollo_people_search(self, **filters: Any) -> ServiceResult:
        """Search for people using Apollo via StableEnrich.

        Keyword Args:
            person_titles: list[str] — Job titles to search.
            organization_domains: list[str] — Company domains.
            person_locations: list[str] — Locations.
            per_page: int — Results per page.

        Returns:
            ServiceResult with people data in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/api/apollo/people-search",
            data=filters,
            cost=self.COST_PER_APOLLO,
        )


# ---------------------------------------------------------------------------
# Browserbase
# ---------------------------------------------------------------------------

class BrowserbaseService(_MPPServiceBase):
    """Wrapper for Browserbase browser automation via MPP.

    Provides: search and fetch (headless browser).
    Base URL: https://mpp.browserbase.com
    Cost: ~$0.01 per call
    """

    SERVICE_ID = "browserbase"
    BASE_URL = "https://mpp.browserbase.com"
    COST_PER_CALL = 0.01

    def search(self, query: str) -> ServiceResult:
        """Search the web using a headless browser.

        Args:
            query: Search query string.

        Returns:
            ServiceResult with search results in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/search",
            data={"query": query},
            cost=self.COST_PER_CALL,
        )

    def fetch(self, url: str) -> ServiceResult:
        """Fetch a URL using a headless browser.

        Args:
            url: The URL to fetch.

        Returns:
            ServiceResult with page content in .data
        """
        return self._tempo_post(
            url=f"{self.BASE_URL}/fetch",
            data={"url": url},
            cost=self.COST_PER_CALL,
        )


# ---------------------------------------------------------------------------
# Tempo RPC (direct JSON-RPC, NOT MPP)
# ---------------------------------------------------------------------------

class TempoRPCService:
    """Direct JSON-RPC client for the Tempo blockchain.

    This does NOT use MPP — Tempo RPC is a free public endpoint.
    Uses httpx for direct HTTP requests.
    """

    SERVICE_ID = "tempo-rpc"
    RPC_URL = "https://rpc.tempo.xyz"

    def __init__(self, rpc_url: str | None = None, timeout: int = 15):
        self.rpc_url = rpc_url or self.RPC_URL
        self.timeout = timeout
        self.total_cost: float = 0.0  # RPC is free but we track for consistency
        self.call_count: int = 0
        self.call_log: list[ServiceResult] = []
        self._request_id = 0

    def _rpc_call(self, method: str, params: list) -> ServiceResult:
        """Execute a JSON-RPC call to the Tempo node."""
        self._request_id += 1
        action = method
        t0 = time.monotonic()

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=f"RPC timeout after {self.timeout}s",
                cost=0.0,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result
        except httpx.HTTPStatusError as e:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                cost=0.0,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result
        except Exception as e:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=str(e),
                cost=0.0,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result

        latency = (time.monotonic() - t0) * 1000

        if "error" in data:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=False,
                error=json.dumps(data["error"]),
                cost=0.0,
                latency_ms=latency,
            )
        else:
            result = ServiceResult(
                service_id=self.SERVICE_ID,
                action=action,
                success=True,
                data=data.get("result"),
                cost=0.0,
                latency_ms=latency,
            )
        self._record(result)
        return result

    def _record(self, result: ServiceResult):
        self.call_count += 1
        self.call_log.append(result)
        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level,
            "[%s] %s — %s (%.0fms)",
            self.SERVICE_ID,
            result.action,
            "OK" if result.success else result.error,
            result.latency_ms,
        )

    def get_balance(self, address: str) -> ServiceResult:
        """Get the ETH balance of an address on Tempo.

        Args:
            address: Ethereum-style hex address (0x...).

        Returns:
            ServiceResult with balance (hex wei) in .data
        """
        return self._rpc_call("eth_getBalance", [address, "latest"])

    def get_tx_count(self, address: str) -> ServiceResult:
        """Get the transaction count (nonce) for an address.

        Args:
            address: Ethereum-style hex address (0x...).

        Returns:
            ServiceResult with tx count (hex) in .data
        """
        return self._rpc_call("eth_getTransactionCount", [address, "latest"])

    def get_block_number(self) -> ServiceResult:
        """Get the latest block number on Tempo."""
        return self._rpc_call("eth_blockNumber", [])

    def get_chain_id(self) -> ServiceResult:
        """Get the chain ID."""
        return self._rpc_call("eth_chainId", [])


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    print("\n=== Sardis Guard — Service Wrapper Tests ===\n")

    # Test 1: Tempo RPC (free, always works)
    print("[1] Tempo RPC — get_balance...")
    rpc = TempoRPCService()
    bal = rpc.get_balance("0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c")
    print(f"    Success: {bal.success}")
    print(f"    Data: {bal.data}")
    print(f"    Latency: {bal.latency_ms:.0f}ms")
    print()

    print("[2] Tempo RPC — get_block_number...")
    block = rpc.get_block_number()
    print(f"    Success: {block.success}")
    if block.success and isinstance(block.data, str):
        print(f"    Block: {int(block.data, 16)}")
    print(f"    Latency: {block.latency_ms:.0f}ms")
    print()

    print("[3] Tempo RPC — get_chain_id...")
    chain = rpc.get_chain_id()
    print(f"    Success: {chain.success}")
    if chain.success and isinstance(chain.data, str):
        print(f"    Chain ID: {int(chain.data, 16)}")
    print(f"    Latency: {chain.latency_ms:.0f}ms")
    print()

    print(f"Total RPC calls: {rpc.call_count}, Cost: ${rpc.total_cost:.4f}")
    print("\nDone. (MPP service tests require tempo wallet with balance)")
