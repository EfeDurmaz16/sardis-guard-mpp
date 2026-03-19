"""Sardis Guard — Address Risk Scoring.

Heuristic-based risk scoring for crypto addresses.
Uses known mixer/sanctioned address lists, contract vs EOA detection,
and address pattern analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.types import Action


# ---------------------------------------------------------------------------
# Known high-risk address sets (lowercase)
# ---------------------------------------------------------------------------

# Known mixer/tumbler contract addresses
KNOWN_MIXERS: set[str] = {
    # Tornado Cash contracts
    "0x8589427373d6d84e98730d7795d8f6f8731fda16",
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
    "0xd96f2b1c14db8458374d9aca76e26c3d18364307",
    "0x4736dcf1b7a3d580672cce6e7c65cd5cc9cfbfa9",
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384",
    "0x722122df12d4e14e13ac3b6895a86e84145b6967",
    "0x905b63fff465b9ffbf41dea908ceb12cd76acf9b",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291",
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
    # Railgun (privacy)
    "0xfa7093cdd9ee6932b4eb2c9e1cce4ce7a7586306",
}

# Known bridge exploiter / attack addresses
KNOWN_EXPLOITERS: set[str] = {
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96",  # Lazarus / Ronin
    "0xa7e5d5a720f06526557c513402f2e6b5fa20b008",  # Lazarus
    "0x3cbded43efdaf0fc77b9c55f6fc9988fcc9b757d",  # Lazarus
}

# Known phishing addresses
KNOWN_PHISHING: set[str] = {
    "0x0000000000000000000000000000000000000000",  # null address (burn)
}

# Known legitimate high-volume addresses (to avoid false positives)
KNOWN_SAFE: set[str] = {
    # Circle USDC treasury
    "0x55fe002aeff02f77364de339a1292923a15844b8",
    # Coinbase
    "0x503828976d22510aad0201ac7ec88293211d23da",
    # Uniswap v3 Router
    "0xe592427a0aece92de3edee1f18e0157c05861564",
}


# ---------------------------------------------------------------------------
# AddressRisk dataclass
# ---------------------------------------------------------------------------

@dataclass
class AddressRisk:
    """Risk assessment for a single address."""
    score: float = 0.0          # 0.0 (safe) to 1.0 (critical)
    labels: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "labels": self.labels,
            "reasons": self.reasons,
        }


# ---------------------------------------------------------------------------
# AddressRiskScorer
# ---------------------------------------------------------------------------

class AddressRiskScorer:
    """Heuristic-based risk scorer for crypto addresses.

    Checks:
    - Known mixer addresses
    - Known exploit/hack addresses
    - Known phishing addresses
    - Address format anomalies
    - Null/burn address patterns
    - Known safe addresses (reduces score)
    """

    def __init__(self):
        self.mixers = KNOWN_MIXERS
        self.exploiters = KNOWN_EXPLOITERS
        self.phishing = KNOWN_PHISHING
        self.safe = KNOWN_SAFE

    def score_address(self, address: str) -> AddressRisk:
        """Score an address for risk using heuristics.

        Returns AddressRisk with score 0.0 (safe) - 1.0 (critical).
        """
        if not address:
            return AddressRisk(
                score=0.5,
                labels=["invalid"],
                reasons=["Empty address provided"],
            )

        normalized = address.strip().lower()
        risk = AddressRisk()

        # ---- Check known sets ----

        if normalized in self.safe:
            risk.score = 0.05
            risk.labels.append("known_safe")
            risk.reasons.append(f"Address is a known safe/institutional address")
            return risk

        if normalized in self.mixers:
            risk.score = 0.95
            risk.labels.extend(["mixer", "high_risk", "privacy_tool"])
            risk.reasons.append("Address belongs to a known mixer/tumbler service")
            return risk

        if normalized in self.exploiters:
            risk.score = 1.0
            risk.labels.extend(["exploiter", "critical", "state_actor"])
            risk.reasons.append("Address associated with known exploit/state-sponsored attack")
            return risk

        if normalized in self.phishing:
            risk.score = 0.9
            risk.labels.extend(["phishing", "high_risk"])
            risk.reasons.append("Address flagged for phishing activity")
            return risk

        # ---- Heuristic checks ----

        scores: list[float] = []

        # Check 1: Null/burn address patterns
        if self._is_null_like(normalized):
            risk.labels.append("null_pattern")
            risk.reasons.append("Address resembles a null/burn address pattern")
            scores.append(0.7)

        # Check 2: Vanity address (many repeating characters)
        vanity_score = self._vanity_score(normalized)
        if vanity_score > 0:
            risk.labels.append("vanity_address")
            risk.reasons.append(f"Vanity address pattern detected (score: {vanity_score:.2f})")
            scores.append(vanity_score * 0.3)  # Mild risk signal

        # Check 3: Recently created address pattern (low nonce proxy)
        # Without on-chain data, we check if it looks like a freshly generated address
        # (no particular pattern — all random hex addresses look the same)
        # This is a placeholder for on-chain enrichment

        # Check 4: Contract-like address (starts with specific patterns)
        # CREATE2 addresses often have leading zeros
        if self._has_create2_pattern(normalized):
            risk.labels.append("create2_pattern")
            risk.reasons.append("Address has CREATE2-like pattern (possible disposable contract)")
            scores.append(0.2)

        # Check 5: Valid ETH address format
        if not self._is_valid_eth_address(normalized):
            risk.labels.append("invalid_format")
            risk.reasons.append("Address is not a valid Ethereum address format")
            scores.append(0.6)

        # Aggregate
        if scores:
            risk.score = min(max(scores), 1.0)
        else:
            # Unknown address, no signals
            risk.score = 0.1
            risk.labels.append("unknown")
            risk.reasons.append("No risk signals detected; address is unknown")

        return risk

    # ----- Heuristic helpers -----

    @staticmethod
    def _is_valid_eth_address(addr: str) -> bool:
        """Check if address matches 0x + 40 hex chars."""
        return bool(re.match(r"^0x[0-9a-f]{40}$", addr))

    @staticmethod
    def _is_null_like(addr: str) -> bool:
        """Check for null/burn-like addresses."""
        if not addr.startswith("0x"):
            return False
        hex_part = addr[2:]
        # All zeros
        if hex_part == "0" * 40:
            return True
        # All same character
        if len(set(hex_part)) <= 2:
            return True
        # Dead address patterns
        if hex_part.startswith("dead") or hex_part.startswith("0000000000"):
            return True
        return False

    @staticmethod
    def _vanity_score(addr: str) -> float:
        """Score how 'vanity' an address looks (repeating patterns)."""
        if not addr.startswith("0x") or len(addr) != 42:
            return 0.0
        hex_part = addr[2:]
        unique_chars = len(set(hex_part))
        # Normal addresses have ~14-16 unique hex chars
        # Vanity addresses have far fewer
        if unique_chars <= 4:
            return 0.8
        if unique_chars <= 6:
            return 0.4
        if unique_chars <= 8:
            return 0.1
        return 0.0

    @staticmethod
    def _has_create2_pattern(addr: str) -> bool:
        """Check for CREATE2-style leading zeros."""
        if not addr.startswith("0x"):
            return False
        hex_part = addr[2:]
        # CREATE2 addresses often start with multiple zeros
        leading_zeros = len(hex_part) - len(hex_part.lstrip("0"))
        return leading_zeros >= 6
