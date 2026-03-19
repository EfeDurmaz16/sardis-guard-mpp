"""Sardis Guard — On-chain Intelligence.

Wallet profiling via Tempo RPC (JSON-RPC) and heuristic analysis.
Uses httpx for direct RPC calls (non-MPP-gated).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Tempo mainnet RPC
TEMPO_RPC_URL = "https://rpc.tempo.xyz"

# Fallback RPCs for other chains
CHAIN_RPC_URLS: dict[str, str] = {
    "tempo": TEMPO_RPC_URL,
    "base": "https://mainnet.base.org",
    "base_sepolia": "https://sepolia.base.org",
    "ethereum": "https://eth.llamarpc.com",
    "polygon": "https://polygon-rpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
}

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
WALLET_CACHE_FILE = DATA_DIR / "wallet_cache.json"


# ---------------------------------------------------------------------------
# WalletProfile dataclass
# ---------------------------------------------------------------------------

@dataclass
class WalletProfile:
    """On-chain profile of a wallet address."""
    address: str = ""
    balance: float = 0.0          # Balance in native token (ETH)
    balance_wei: int = 0
    tx_count: int = 0
    estimated_age_days: int = 0
    is_contract: bool = False
    chain: str = "tempo"
    risk_score: float = 0.0       # 0.0 (safe) - 1.0 (critical)
    risk_reasons: list[str] = field(default_factory=list)
    queried_at: float = 0.0
    source: str = ""              # "rpc", "cache", "partial"

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "balance": round(self.balance, 6),
            "balance_wei": self.balance_wei,
            "tx_count": self.tx_count,
            "estimated_age_days": self.estimated_age_days,
            "is_contract": self.is_contract,
            "chain": self.chain,
            "risk_score": round(self.risk_score, 4),
            "risk_reasons": self.risk_reasons,
            "queried_at": self.queried_at,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# OnchainIntel
# ---------------------------------------------------------------------------

class OnchainIntel:
    """On-chain wallet intelligence via JSON-RPC.

    Uses Tempo RPC (https://rpc.tempo.xyz) and fallback chain RPCs
    for wallet profiling. Caches results locally.
    """

    def __init__(self, default_chain: str = "tempo"):
        self.default_chain = default_chain
        self._cache: dict[str, WalletProfile] = {}
        self._load_cache()

    def get_wallet_info(
        self,
        address: str,
        chain: str | None = None,
    ) -> WalletProfile:
        """Get wallet profile for an address.

        Queries:
        - eth_getBalance for balance
        - eth_getTransactionCount for nonce/activity
        - eth_getCode to check if contract

        Then applies heuristic risk scoring.
        """
        if not address:
            return WalletProfile(
                address="",
                risk_score=0.5,
                risk_reasons=["Empty address"],
                source="error",
            )

        chain = chain or self.default_chain
        cache_key = f"{chain}:{address.lower()}"

        # Check cache (valid for 5 minutes)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.queried_at < 300:
                cached.source = "cache"
                return cached

        rpc_url = CHAIN_RPC_URLS.get(chain, TEMPO_RPC_URL)
        profile = WalletProfile(
            address=address,
            chain=chain,
            queried_at=time.time(),
        )

        # Query RPC
        balance_ok = self._fetch_balance(rpc_url, address, profile)
        nonce_ok = self._fetch_tx_count(rpc_url, address, profile)
        code_ok = self._fetch_code(rpc_url, address, profile)

        if balance_ok or nonce_ok or code_ok:
            profile.source = "rpc"
        else:
            profile.source = "partial"
            profile.risk_reasons.append("Could not reach RPC — partial data only")

        # Estimate age from tx count
        profile.estimated_age_days = self._estimate_age(profile.tx_count)

        # Risk scoring
        profile.risk_score = self._compute_risk(profile)

        # Cache
        self._cache[cache_key] = profile
        self._save_cache()

        return profile

    # ----- RPC calls -----

    def _fetch_balance(self, rpc_url: str, address: str, profile: WalletProfile) -> bool:
        """Fetch ETH balance via eth_getBalance."""
        try:
            resp = self._rpc_call(rpc_url, "eth_getBalance", [address, "latest"])
            if resp is not None:
                balance_wei = int(resp, 16)
                profile.balance_wei = balance_wei
                profile.balance = balance_wei / 1e18
                return True
        except Exception:
            pass
        return False

    def _fetch_tx_count(self, rpc_url: str, address: str, profile: WalletProfile) -> bool:
        """Fetch transaction count via eth_getTransactionCount."""
        try:
            resp = self._rpc_call(rpc_url, "eth_getTransactionCount", [address, "latest"])
            if resp is not None:
                profile.tx_count = int(resp, 16)
                return True
        except Exception:
            pass
        return False

    def _fetch_code(self, rpc_url: str, address: str, profile: WalletProfile) -> bool:
        """Check if address is a contract via eth_getCode."""
        try:
            resp = self._rpc_call(rpc_url, "eth_getCode", [address, "latest"])
            if resp is not None:
                # "0x" means EOA, anything longer is contract bytecode
                profile.is_contract = len(resp) > 2
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _rpc_call(rpc_url: str, method: str, params: list) -> str | None:
        """Make a JSON-RPC call and return the result field."""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": 1,
                    },
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                if "result" in data:
                    return data["result"]
                return None
        except Exception:
            return None

    # ----- Risk scoring -----

    @staticmethod
    def _estimate_age(tx_count: int) -> int:
        """Rough age estimate from tx count (assumes ~1-3 tx/day for active wallets)."""
        if tx_count == 0:
            return 0
        if tx_count < 5:
            return 1
        if tx_count < 50:
            return max(1, tx_count // 3)
        if tx_count < 500:
            return max(30, tx_count // 5)
        return max(180, tx_count // 10)

    @staticmethod
    def _compute_risk(profile: WalletProfile) -> float:
        """Compute risk score from wallet profile heuristics."""
        risk = 0.0
        reasons = profile.risk_reasons

        # New wallet (0 transactions) — moderate risk
        if profile.tx_count == 0:
            risk = max(risk, 0.4)
            reasons.append("New wallet with zero transactions")

        # Very few transactions — mild risk
        elif profile.tx_count < 3:
            risk = max(risk, 0.3)
            reasons.append(f"Low activity wallet ({profile.tx_count} tx)")

        # High transaction count — usually legitimate
        elif profile.tx_count > 1000:
            risk = max(risk, 0.05)
            reasons.append(f"High activity wallet ({profile.tx_count} tx)")

        # Contract with no balance — could be a proxy/disposable
        if profile.is_contract and profile.balance == 0.0:
            risk = max(risk, 0.3)
            reasons.append("Contract address with zero balance")

        # Contract — generally neutral but noted
        elif profile.is_contract:
            reasons.append("Address is a smart contract")

        # Very high balance (whale) — low risk but notable
        if profile.balance > 100.0:
            reasons.append(f"High balance wallet ({profile.balance:.2f} ETH)")

        # Empty wallet with some history — could be drained
        if profile.tx_count > 10 and profile.balance == 0.0:
            risk = max(risk, 0.25)
            reasons.append("Active wallet with zero balance (possibly drained)")

        return min(risk, 1.0)

    # ----- Cache persistence -----

    def _load_cache(self):
        """Load wallet cache from disk."""
        try:
            if WALLET_CACHE_FILE.exists():
                data = json.loads(WALLET_CACHE_FILE.read_text())
                for key, val in data.items():
                    self._cache[key] = WalletProfile(**val)
        except Exception:
            self._cache = {}

    def _save_cache(self):
        """Save wallet cache to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self._cache.items()}
            WALLET_CACHE_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass
