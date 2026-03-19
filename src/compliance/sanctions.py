"""Sardis Guard — OFAC Sanctions Screening.

Downloads and parses the OFAC SDN list for crypto addresses.
Falls back to a local fixture of ~20 known sanctioned addresses if download fails.
No Docker/Watchman required.
"""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.types import Action


# ---------------------------------------------------------------------------
# Data directory for cached OFAC data
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OFAC_CACHE_FILE = DATA_DIR / "ofac_addresses.json"
OFAC_NAMES_CACHE_FILE = DATA_DIR / "ofac_names.json"

# OFAC SDN Advanced XML (contains digital-currency addresses)
OFAC_SDN_XML_URL = "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml"
# Simpler CSV fallback
OFAC_SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

# XML namespace
OFAC_NS = {"ns": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"}


# ---------------------------------------------------------------------------
# Known sanctioned crypto addresses (fixture / demo fallback)
# ---------------------------------------------------------------------------

KNOWN_SANCTIONED_ADDRESSES: dict[str, dict] = {
    # Tornado Cash (OFAC designated Aug 2022)
    "0x8589427373D6D84E98730D7795D8f6f8731FDA16": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0xd96f2B1c14Db8458374d9Aca76E26c3D18364307": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0x4736dCf1b7A3d580672CcE6E7c65cd5cc9cFBfA9": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0xDD4c48C0B24039969fC16D1cdF626eaB821d3384": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0x722122dF12D4e14e13Ac3b6895a86e84145b6967": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0x905b63Fff465B9fFBF41DeA908CEb12cd76aCf9B": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0xA160cdAB225685dA1d56aa342Ad8841c3b53f291": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    # Garantex (OFAC designated Apr 2022)
    "0x6F1cA141A28907F78Ebaa64f83D078e15B9eF413": {
        "entity": "Garantex Europe OU",
        "list": "OFAC SDN",
        "program": "RUSSIA-EO14024",
    },
    "0x2f389cE8bD8ff92De3402FFCe4691d17fC4f6535": {
        "entity": "Garantex Europe OU",
        "list": "OFAC SDN",
        "program": "RUSSIA-EO14024",
    },
    # Blender.io (OFAC designated May 2022)
    "0x3Cffd56B47B7b41c56B9d548F3f467851F3B5f95": {
        "entity": "Blender.io",
        "list": "OFAC SDN",
        "program": "DPRK",
    },
    # Sinbad.io (OFAC designated Nov 2023)
    "0x72a5843cc08275C8171E582972Aa4fDa8C397B2A": {
        "entity": "Sinbad.io",
        "list": "OFAC SDN",
        "program": "DPRK",
    },
    # Chatex (OFAC designated Nov 2021)
    "0x24dDBa35bc781e3Ce4b32232456E3fB55b1D58F2": {
        "entity": "Chatex",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    # Lazarus Group wallets (DPRK)
    "0x098B716B8Aaf21512996dC57EB0615e2383E2f96": {
        "entity": "Lazarus Group",
        "list": "OFAC SDN",
        "program": "DPRK",
    },
    "0xa7e5d5A720f06526557c513402f2e6B5fA20b008": {
        "entity": "Lazarus Group",
        "list": "OFAC SDN",
        "program": "DPRK",
    },
    "0x3CBdeD43EFdAf0FC77b9C55F6fC9988fCC9b757d": {
        "entity": "Lazarus Group",
        "list": "OFAC SDN",
        "program": "DPRK",
    },
    # Suex OTC (OFAC designated Sep 2021)
    "0x2F65390476747a0271E7B0e6026fEB3F6ae9eE0F": {
        "entity": "SUEX OTC, s.r.o.",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    # Additional Tornado Cash Router
    "0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
    "0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936": {
        "entity": "Tornado Cash",
        "list": "OFAC SDN",
        "program": "CYBER2",
    },
}

# Known sanctioned entity names for name screening
KNOWN_SANCTIONED_NAMES: dict[str, dict] = {
    "tornado cash": {"list": "OFAC SDN", "program": "CYBER2"},
    "garantex": {"list": "OFAC SDN", "program": "RUSSIA-EO14024"},
    "garantex europe ou": {"list": "OFAC SDN", "program": "RUSSIA-EO14024"},
    "blender.io": {"list": "OFAC SDN", "program": "DPRK"},
    "sinbad.io": {"list": "OFAC SDN", "program": "DPRK"},
    "sinbad": {"list": "OFAC SDN", "program": "DPRK"},
    "chatex": {"list": "OFAC SDN", "program": "CYBER2"},
    "lazarus group": {"list": "OFAC SDN", "program": "DPRK"},
    "suex otc": {"list": "OFAC SDN", "program": "CYBER2"},
    "hydra market": {"list": "OFAC SDN", "program": "RUSSIA-EO14024"},
    "task force rusich": {"list": "OFAC SDN", "program": "RUSSIA-EO14024"},
    "conti ransomware": {"list": "OFAC SDN", "program": "CYBER2"},
    "trickbot": {"list": "OFAC SDN", "program": "CYBER2"},
}


# ---------------------------------------------------------------------------
# SanctionsResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class SanctionsResult:
    """Result of a sanctions screening check."""
    hit: bool = False
    match_type: str = ""          # "exact_address", "fuzzy_name", "none"
    matched_entry: str = ""       # Entity name that matched
    list_source: str = ""         # e.g. "OFAC SDN"
    confidence: float = 0.0       # 0.0 - 1.0
    program: str = ""             # Sanctions program
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "hit": self.hit,
            "match_type": self.match_type,
            "matched_entry": self.matched_entry,
            "list_source": self.list_source,
            "confidence": self.confidence,
            "program": self.program,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# SanctionsScreener
# ---------------------------------------------------------------------------

class SanctionsScreener:
    """OFAC sanctions screener for crypto addresses and entity names.

    On init, loads cached OFAC data or downloads fresh from Treasury.
    Falls back to a built-in fixture of ~20 known sanctioned addresses.
    """

    def __init__(self, auto_load: bool = True):
        # address -> metadata (lowercased for matching)
        self.addresses: dict[str, dict] = {}
        # name (lowercased) -> metadata
        self.names: dict[str, dict] = {}
        self._loaded_from: str = "none"
        self._last_updated: float = 0.0

        if auto_load:
            self.load_ofac_addresses()

    # ----- Loading -----

    def load_ofac_addresses(self) -> int:
        """Load OFAC sanctioned addresses. Priority:
        1. Fresh download from Treasury (XML)
        2. Local cache file
        3. Built-in fixture
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Try downloading fresh data
        if self._try_download_ofac():
            self._loaded_from = "ofac_download"
            self._last_updated = time.time()
            self._save_cache()
            return len(self.addresses)

        # Try loading from cache
        if self._try_load_cache():
            self._loaded_from = "cache"
            return len(self.addresses)

        # Fall back to built-in fixture
        self._load_fixture()
        self._loaded_from = "fixture"
        self._save_cache()  # save fixture to cache for next time
        return len(self.addresses)

    def _try_download_ofac(self) -> bool:
        """Download and parse OFAC SDN Advanced XML for crypto addresses."""
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(OFAC_SDN_XML_URL)
                resp.raise_for_status()

            root = ET.fromstring(resp.content)

            # Try multiple namespace strategies since OFAC changes these
            addresses_found: dict[str, dict] = {}
            names_found: dict[str, dict] = {}

            # Strategy 1: Look for Digital Currency Address features
            # The XML uses nested structures: sdnEntry -> id -> ... -> feature
            # We need to handle the namespace flexibly
            xml_text = resp.text

            # Extract addresses using regex (more robust than namespace-dependent XML parsing)
            # OFAC lists digital currency addresses with type "Digital Currency Address"
            addr_pattern = re.compile(
                r"Digital Currency Address\s*-\s*(\w+)\s*</.*?>(0x[0-9a-fA-F]{40})",
                re.DOTALL | re.IGNORECASE,
            )
            # Simpler: just find all Ethereum-like addresses in the XML
            eth_addr_pattern = re.compile(r"\b(0x[0-9a-fA-F]{40})\b")

            found_eth = set(eth_addr_pattern.findall(xml_text))

            # Also extract SDN entity names
            name_pattern = re.compile(
                r"<lastName>([^<]+)</lastName>",
                re.IGNORECASE,
            )
            first_name_pattern = re.compile(
                r"<firstName>([^<]+)</firstName>",
                re.IGNORECASE,
            )

            for addr in found_eth:
                addr_lower = addr.lower()
                addresses_found[addr_lower] = {
                    "entity": "OFAC SDN Entry",
                    "list": "OFAC SDN",
                    "program": "UNKNOWN",
                }

            # Parse names from XML
            for match in name_pattern.finditer(xml_text):
                name = match.group(1).strip().lower()
                if len(name) > 2:
                    names_found[name] = {"list": "OFAC SDN", "program": "SDN"}

            if addresses_found:
                self.addresses = addresses_found
                self.names = {**KNOWN_SANCTIONED_NAMES, **names_found}
                # Merge in our known addresses (with better metadata)
                for addr, meta in KNOWN_SANCTIONED_ADDRESSES.items():
                    self.addresses[addr.lower()] = meta
                return True

            return False

        except Exception:
            return False

    def _try_download_ofac_csv(self) -> bool:
        """Fallback: download and parse SDN CSV."""
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(OFAC_SDN_CSV_URL)
                resp.raise_for_status()

            csv_text = resp.text
            eth_pattern = re.compile(r"\b(0x[0-9a-fA-F]{40})\b")
            found = set(eth_pattern.findall(csv_text))

            if found:
                for addr in found:
                    self.addresses[addr.lower()] = {
                        "entity": "OFAC SDN Entry",
                        "list": "OFAC SDN",
                        "program": "UNKNOWN",
                    }
                # Merge known addresses
                for addr, meta in KNOWN_SANCTIONED_ADDRESSES.items():
                    self.addresses[addr.lower()] = meta
                self.names = dict(KNOWN_SANCTIONED_NAMES)
                return True
            return False
        except Exception:
            return False

    def _try_load_cache(self) -> bool:
        """Load from local JSON cache."""
        try:
            if OFAC_CACHE_FILE.exists():
                data = json.loads(OFAC_CACHE_FILE.read_text())
                self.addresses = data.get("addresses", {})
                self._last_updated = data.get("updated_at", 0)

            if OFAC_NAMES_CACHE_FILE.exists():
                self.names = json.loads(OFAC_NAMES_CACHE_FILE.read_text())
            else:
                self.names = dict(KNOWN_SANCTIONED_NAMES)

            return bool(self.addresses)
        except Exception:
            return False

    def _load_fixture(self):
        """Load built-in fixture of known sanctioned addresses."""
        self.addresses = {
            addr.lower(): meta
            for addr, meta in KNOWN_SANCTIONED_ADDRESSES.items()
        }
        self.names = dict(KNOWN_SANCTIONED_NAMES)

    def _save_cache(self):
        """Persist current data to local cache files."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "addresses": self.addresses,
                "updated_at": time.time(),
                "count": len(self.addresses),
            }
            OFAC_CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
            OFAC_NAMES_CACHE_FILE.write_text(json.dumps(self.names, indent=2))
        except Exception:
            pass  # Non-fatal

    # ----- Screening -----

    def screen_address(self, address: str) -> SanctionsResult:
        """Screen a crypto address against the OFAC sanctions list.

        Exact match (case-insensitive) against known sanctioned addresses.
        """
        if not address:
            return SanctionsResult(hit=False, match_type="none")

        normalized = address.strip().lower()
        entry = self.addresses.get(normalized)

        if entry:
            return SanctionsResult(
                hit=True,
                match_type="exact_address",
                matched_entry=entry.get("entity", "Unknown SDN"),
                list_source=entry.get("list", "OFAC SDN"),
                confidence=1.0,
                program=entry.get("program", ""),
                details={"address": address, "source": self._loaded_from},
            )

        return SanctionsResult(
            hit=False,
            match_type="none",
            confidence=0.0,
            details={"address": address, "checked_against": len(self.addresses)},
        )

    def screen_entity(self, name: str) -> SanctionsResult:
        """Screen an entity name against the OFAC sanctions list.

        Uses substring matching and simple edit-distance for fuzzy matching.
        """
        if not name:
            return SanctionsResult(hit=False, match_type="none")

        query = name.strip().lower()

        # 1. Exact name match
        if query in self.names:
            meta = self.names[query]
            return SanctionsResult(
                hit=True,
                match_type="exact_name",
                matched_entry=query,
                list_source=meta.get("list", "OFAC SDN"),
                confidence=1.0,
                program=meta.get("program", ""),
            )

        # 2. Substring match (query is contained in a sanctioned name or vice versa)
        best_match: str | None = None
        best_confidence: float = 0.0

        for sanctioned_name, meta in self.names.items():
            # Substring containment
            if query in sanctioned_name or sanctioned_name in query:
                # Confidence based on length ratio
                shorter = min(len(query), len(sanctioned_name))
                longer = max(len(query), len(sanctioned_name))
                conf = shorter / longer if longer > 0 else 0.0
                if conf > best_confidence:
                    best_confidence = conf
                    best_match = sanctioned_name

            # Simple token overlap
            query_tokens = set(query.split())
            name_tokens = set(sanctioned_name.split())
            if query_tokens and name_tokens:
                overlap = len(query_tokens & name_tokens)
                total = len(query_tokens | name_tokens)
                token_conf = overlap / total if total > 0 else 0.0
                if token_conf > best_confidence:
                    best_confidence = token_conf
                    best_match = sanctioned_name

        # Threshold for fuzzy match
        if best_match and best_confidence >= 0.5:
            meta = self.names[best_match]
            return SanctionsResult(
                hit=True,
                match_type="fuzzy_name",
                matched_entry=best_match,
                list_source=meta.get("list", "OFAC SDN"),
                confidence=round(best_confidence, 3),
                program=meta.get("program", ""),
            )

        # 3. Edit distance for short names (Levenshtein-like)
        if len(query) <= 30:
            for sanctioned_name, meta in self.names.items():
                dist = _levenshtein(query, sanctioned_name)
                max_len = max(len(query), len(sanctioned_name))
                if max_len > 0:
                    similarity = 1.0 - (dist / max_len)
                    if similarity >= 0.75 and similarity > best_confidence:
                        best_confidence = similarity
                        best_match = sanctioned_name

            if best_match and best_confidence >= 0.75:
                meta = self.names[best_match]
                return SanctionsResult(
                    hit=True,
                    match_type="fuzzy_name",
                    matched_entry=best_match,
                    list_source=meta.get("list", "OFAC SDN"),
                    confidence=round(best_confidence, 3),
                    program=meta.get("program", ""),
                )

        return SanctionsResult(
            hit=False,
            match_type="none",
            confidence=0.0,
            details={"query": name, "checked_against": len(self.names)},
        )

    # ----- Info -----

    @property
    def stats(self) -> dict:
        return {
            "address_count": len(self.addresses),
            "name_count": len(self.names),
            "loaded_from": self._loaded_from,
            "last_updated": self._last_updated,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _levenshtein(s1: str, s2: str) -> int:
    """Simple Levenshtein edit distance."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]
