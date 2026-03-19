"""Sardis Guard — Merchant Intelligence.

Enriches merchant/service names with risk context using Exa search
via `tempo request` (MPP-gated StableEnrich). Caches results in SQLite.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MERCHANT_DB = DATA_DIR / "merchant_cache.db"

# High-risk merchant categories
HIGH_RISK_CATEGORIES: set[str] = {
    "gambling",
    "adult",
    "crypto_mixer",
    "darknet",
    "weapons",
    "sanctions_evasion",
    "money_service_business",
    "ransomware",
    "unregistered_exchange",
}

# Known merchant risk labels (curated)
KNOWN_MERCHANT_RISK: dict[str, list[str]] = {
    "tornado cash": ["mixer", "sanctioned", "ofac"],
    "garantex": ["exchange", "sanctioned", "ofac", "russia"],
    "blender.io": ["mixer", "sanctioned", "ofac", "dprk"],
    "sinbad": ["mixer", "sanctioned", "ofac", "dprk"],
    "hydra": ["darknet", "marketplace", "sanctioned"],
    "chatex": ["exchange", "sanctioned", "ofac"],
    "binance": ["exchange", "regulated"],
    "coinbase": ["exchange", "regulated", "us_licensed"],
    "uniswap": ["dex", "defi", "regulated"],
    "aave": ["defi", "lending", "regulated"],
    "opensea": ["nft", "marketplace"],
    "stripe": ["payment_processor", "regulated"],
    "amazon": ["ecommerce", "regulated"],
    "openai": ["ai", "saas", "regulated"],
    "anthropic": ["ai", "saas", "regulated"],
}


# ---------------------------------------------------------------------------
# MerchantProfile dataclass
# ---------------------------------------------------------------------------

@dataclass
class MerchantProfile:
    """Enriched merchant/service profile."""
    name: str = ""
    domain: str = ""
    category: str = "unknown"
    risk_labels: list[str] = field(default_factory=list)
    description: str = ""
    first_seen: float = 0.0
    enriched_at: float = 0.0
    source: str = ""  # "cache", "tempo", "heuristic"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "category": self.category,
            "risk_labels": self.risk_labels,
            "description": self.description,
            "first_seen": self.first_seen,
            "enriched_at": self.enriched_at,
            "source": self.source,
        }

    @property
    def is_high_risk(self) -> bool:
        return bool(set(self.risk_labels) & HIGH_RISK_CATEGORIES) or \
               any(lbl in ("sanctioned", "ofac") for lbl in self.risk_labels)


# ---------------------------------------------------------------------------
# MerchantIntel
# ---------------------------------------------------------------------------

class MerchantIntel:
    """Merchant enrichment engine.

    Uses `tempo request` CLI for MPP-gated StableEnrich / Exa search.
    Caches results in SQLite to avoid repeated expensive lookups.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or MERCHANT_DB
        self._init_db()

    def _init_db(self):
        """Initialize SQLite cache database."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                name TEXT PRIMARY KEY,
                domain TEXT DEFAULT '',
                category TEXT DEFAULT 'unknown',
                risk_labels TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                first_seen REAL DEFAULT 0,
                enriched_at REAL DEFAULT 0,
                source TEXT DEFAULT '',
                raw_response TEXT DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()

    def enrich_merchant(self, merchant: str) -> MerchantProfile:
        """Enrich a merchant name with risk context.

        Priority:
        1. SQLite cache
        2. Known merchant risk labels
        3. Tempo StableEnrich (via `tempo request`)
        4. Heuristic fallback
        """
        if not merchant:
            return MerchantProfile(name="unknown", category="unknown")

        normalized = merchant.strip().lower()

        # 1. Check cache
        cached = self._get_cached(normalized)
        if cached:
            return cached

        # 2. Check known merchants
        if normalized in KNOWN_MERCHANT_RISK:
            profile = MerchantProfile(
                name=merchant,
                category=self._infer_category(KNOWN_MERCHANT_RISK[normalized]),
                risk_labels=KNOWN_MERCHANT_RISK[normalized],
                description=f"Known merchant: {merchant}",
                first_seen=time.time(),
                enriched_at=time.time(),
                source="known_list",
            )
            self._cache_profile(normalized, profile)
            return profile

        # 3. Try Tempo StableEnrich
        tempo_profile = self._enrich_via_tempo(merchant)
        if tempo_profile:
            self._cache_profile(normalized, tempo_profile)
            return tempo_profile

        # 4. Heuristic fallback
        profile = self._heuristic_enrich(merchant)
        self._cache_profile(normalized, profile)
        return profile

    # ----- Cache -----

    def _get_cached(self, name: str) -> MerchantProfile | None:
        """Look up cached merchant profile."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            row = conn.execute(
                "SELECT name, domain, category, risk_labels, description, first_seen, enriched_at, source "
                "FROM merchants WHERE name = ?",
                (name,),
            ).fetchone()
            conn.close()

            if row:
                return MerchantProfile(
                    name=row[0],
                    domain=row[1],
                    category=row[2],
                    risk_labels=json.loads(row[3]),
                    description=row[4],
                    first_seen=row[5],
                    enriched_at=row[6],
                    source="cache",
                )
            return None
        except Exception:
            return None

    def _cache_profile(self, name: str, profile: MerchantProfile):
        """Store merchant profile in SQLite cache."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT OR REPLACE INTO merchants "
                "(name, domain, category, risk_labels, description, first_seen, enriched_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    profile.domain,
                    profile.category,
                    json.dumps(profile.risk_labels),
                    profile.description,
                    profile.first_seen or time.time(),
                    time.time(),
                    profile.source,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    # ----- Tempo StableEnrich -----

    def _enrich_via_tempo(self, merchant: str) -> MerchantProfile | None:
        """Use `tempo request` to call StableEnrich / Exa for merchant info."""
        try:
            # Build the request payload for StableEnrich via Exa
            search_query = f"{merchant} company service category risk"

            result = subprocess.run(
                [
                    "tempo", "request",
                    "exa",  # StableEnrich Exa search service
                    "--method", "POST",
                    "--path", "/search",
                    "--data", json.dumps({
                        "query": search_query,
                        "num_results": 3,
                        "use_autoprompt": True,
                        "type": "neural",
                    }),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                return None

            response = json.loads(result.stdout)
            results = response.get("results", [])

            if not results:
                return None

            # Parse top result
            top = results[0]
            domain = top.get("url", "")
            title = top.get("title", merchant)
            snippet = top.get("text", "")[:500]

            # Extract domain from URL
            if domain:
                from urllib.parse import urlparse
                parsed = urlparse(domain)
                domain = parsed.netloc or domain

            # Infer category and risk labels from content
            risk_labels = self._infer_risk_labels(merchant, snippet)
            category = self._infer_category(risk_labels) if risk_labels else self._guess_category(merchant, snippet)

            return MerchantProfile(
                name=merchant,
                domain=domain,
                category=category,
                risk_labels=risk_labels,
                description=snippet[:300],
                first_seen=time.time(),
                enriched_at=time.time(),
                source="tempo_exa",
            )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return None
        except Exception:
            return None

    # ----- Heuristics -----

    def _heuristic_enrich(self, merchant: str) -> MerchantProfile:
        """Fallback enrichment using name-based heuristics."""
        normalized = merchant.strip().lower()
        risk_labels: list[str] = []
        category = "unknown"

        # Keyword-based category inference
        if any(kw in normalized for kw in ("exchange", "swap", "dex", "trade")):
            category = "exchange"
            risk_labels.append("exchange")
        elif any(kw in normalized for kw in ("mix", "tumbl", "blend", "tornado")):
            category = "crypto_mixer"
            risk_labels.extend(["mixer", "high_risk"])
        elif any(kw in normalized for kw in ("casino", "bet", "gambl", "poker")):
            category = "gambling"
            risk_labels.append("gambling")
        elif any(kw in normalized for kw in ("lend", "borrow", "yield", "stake")):
            category = "defi"
            risk_labels.append("defi")
        elif any(kw in normalized for kw in ("nft", "opensea", "blur", "magic eden")):
            category = "nft"
            risk_labels.append("nft")
        elif any(kw in normalized for kw in ("ai", "gpt", "claude", "llm")):
            category = "ai"
            risk_labels.append("ai")
        elif any(kw in normalized for kw in ("shop", "store", "market", "buy")):
            category = "ecommerce"
            risk_labels.append("ecommerce")
        elif any(kw in normalized for kw in ("pay", "stripe", "square")):
            category = "payment_processor"
            risk_labels.append("payment")

        return MerchantProfile(
            name=merchant,
            category=category,
            risk_labels=risk_labels,
            description=f"Heuristic enrichment for: {merchant}",
            first_seen=time.time(),
            enriched_at=time.time(),
            source="heuristic",
        )

    @staticmethod
    def _infer_risk_labels(merchant: str, text: str) -> list[str]:
        """Infer risk labels from merchant name and search text."""
        combined = f"{merchant} {text}".lower()
        labels: list[str] = []

        risk_keywords = {
            "sanctioned": ["sanction", "ofac", "sdn list", "designated"],
            "mixer": ["mixer", "tumbler", "mixing service", "privacy"],
            "gambling": ["casino", "gambling", "betting", "wager"],
            "darknet": ["darknet", "dark web", "tor hidden", "onion"],
            "ransomware": ["ransomware", "ransom", "malware"],
            "exchange": ["exchange", "trading platform", "crypto exchange"],
            "defi": ["defi", "decentralized finance", "lending protocol", "yield"],
            "regulated": ["regulated", "licensed", "sec registered", "finra"],
        }

        for label, keywords in risk_keywords.items():
            if any(kw in combined for kw in keywords):
                labels.append(label)

        return labels

    @staticmethod
    def _infer_category(labels: list[str]) -> str:
        """Infer category from risk labels."""
        priority = [
            "crypto_mixer", "darknet", "gambling", "ransomware",
            "exchange", "defi", "nft", "payment_processor",
            "ai", "ecommerce", "saas",
        ]
        for cat in priority:
            if cat in labels:
                return cat
        # Check broader matches
        if "mixer" in labels:
            return "crypto_mixer"
        if "exchange" in labels:
            return "exchange"
        if "regulated" in labels:
            return "regulated_service"
        return "unknown"

    @staticmethod
    def _guess_category(merchant: str, text: str) -> str:
        """Last-resort category guess from text content."""
        combined = f"{merchant} {text}".lower()
        if "exchange" in combined:
            return "exchange"
        if "payment" in combined:
            return "payment_processor"
        if "defi" in combined or "protocol" in combined:
            return "defi"
        return "unknown"
