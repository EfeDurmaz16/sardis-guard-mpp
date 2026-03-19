"""Sardis Guard — MPP Service Registry.

Metadata about known MPP services. Used by:
  - Risk engine for service_novelty scoring (unknown services = higher risk)
  - Orchestrator for routing decisions
  - Dashboard for service directory display

The registry is append-only at runtime — services can be discovered
and registered dynamically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Risk classification for MPP services."""
    LOW = "low"         # Well-known, audited, cheap (e.g., Tempo RPC)
    MEDIUM = "medium"   # Established services with moderate cost (e.g., StableEnrich)
    HIGH = "high"       # Expensive or data-sensitive (e.g., Perplexity, Apollo)
    UNKNOWN = "unknown" # Not in registry — highest risk score


class ServiceCategory(str, Enum):
    """Functional category for MPP services."""
    SEARCH = "search"
    ENRICHMENT = "enrichment"
    SCRAPING = "scraping"
    BLOCKCHAIN = "blockchain"
    AI = "ai"
    BROWSER = "browser"
    IDENTITY = "identity"
    PAYMENTS = "payments"
    OTHER = "other"


@dataclass
class ServiceMeta:
    """Metadata for a single MPP service."""

    service_id: str
    name: str
    base_url: str
    category: ServiceCategory
    risk_level: RiskLevel
    typical_cost: float  # USD per call (average)
    description: str = ""
    endpoints: list[str] = field(default_factory=list)
    requires_mpp: bool = True  # False for direct RPC
    tags: list[str] = field(default_factory=list)

    @property
    def risk_score(self) -> float:
        """Numeric risk score (0.0 - 1.0) for use in risk engine."""
        return {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.3,
            RiskLevel.HIGH: 0.6,
            RiskLevel.UNKNOWN: 0.9,
        }[self.risk_level]

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "base_url": self.base_url,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "typical_cost": self.typical_cost,
            "description": self.description,
            "endpoints": self.endpoints,
            "requires_mpp": self.requires_mpp,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Built-in registry of known MPP services
# ---------------------------------------------------------------------------

_BUILTIN_SERVICES: list[ServiceMeta] = [
    ServiceMeta(
        service_id="perplexity",
        name="Perplexity AI",
        base_url="https://perplexity.mpp.paywithlocus.com",
        category=ServiceCategory.SEARCH,
        risk_level=RiskLevel.HIGH,
        typical_cost=0.05,
        description="AI-powered web search with citations",
        endpoints=["/perplexity/search"],
        tags=["ai", "search", "research"],
    ),
    ServiceMeta(
        service_id="stableenrich",
        name="StableEnrich",
        base_url="https://stableenrich.dev",
        category=ServiceCategory.ENRICHMENT,
        risk_level=RiskLevel.MEDIUM,
        typical_cost=0.007,
        description="Company and people enrichment (Exa, Firecrawl, Apollo)",
        endpoints=[
            "/api/exa/search",
            "/api/firecrawl/scrape",
            "/api/apollo/people-search",
        ],
        tags=["enrichment", "search", "scraping", "people"],
    ),
    ServiceMeta(
        service_id="browserbase",
        name="Browserbase",
        base_url="https://mpp.browserbase.com",
        category=ServiceCategory.BROWSER,
        risk_level=RiskLevel.MEDIUM,
        typical_cost=0.01,
        description="Headless browser automation — search and fetch",
        endpoints=["/search", "/fetch"],
        tags=["browser", "scraping", "automation"],
    ),
    ServiceMeta(
        service_id="tempo-rpc",
        name="Tempo RPC",
        base_url="https://rpc.tempo.xyz",
        category=ServiceCategory.BLOCKCHAIN,
        risk_level=RiskLevel.LOW,
        typical_cost=0.0,
        description="Tempo blockchain JSON-RPC (free, no MPP required)",
        endpoints=["/"],
        requires_mpp=False,
        tags=["blockchain", "rpc", "tempo", "free"],
    ),
    ServiceMeta(
        service_id="sardis-guard",
        name="Sardis Guard",
        base_url="https://dendric-margie-answerlessly.ngrok-free.dev",
        category=ServiceCategory.PAYMENTS,
        risk_level=RiskLevel.LOW,
        typical_cost=0.001,
        description="12-check policy firewall for AI agent payments",
        endpoints=[
            "/evaluate",
            "/simulate",
            "/mandate",
            "/stats",
            "/audit",
            "/stream",
        ],
        tags=["policy", "guard", "payments", "governance"],
    ),
]


class ServiceRegistry:
    """Registry of known MPP services with metadata.

    Used by the risk engine to score service_novelty:
      - Known service → low novelty score
      - Unknown service → high novelty score (suspicious)

    Thread-safe for reads; writes are rare (only during discovery).
    """

    def __init__(self):
        self._services: dict[str, ServiceMeta] = {}
        # Load built-in services
        for svc in _BUILTIN_SERVICES:
            self._services[svc.service_id] = svc

    def get(self, service_id: str) -> ServiceMeta | None:
        """Get metadata for a service by ID."""
        return self._services.get(service_id)

    def get_or_unknown(self, service_id: str) -> ServiceMeta:
        """Get metadata, returning a synthetic UNKNOWN entry if not found."""
        existing = self._services.get(service_id)
        if existing:
            return existing
        return ServiceMeta(
            service_id=service_id,
            name=f"Unknown ({service_id})",
            base_url="",
            category=ServiceCategory.OTHER,
            risk_level=RiskLevel.UNKNOWN,
            typical_cost=0.0,
            description="Unregistered service — elevated risk",
        )

    def register(self, meta: ServiceMeta):
        """Register or update a service in the registry."""
        self._services[meta.service_id] = meta

    def list_all(self) -> list[ServiceMeta]:
        """Return all registered services."""
        return list(self._services.values())

    def list_by_category(self, category: ServiceCategory) -> list[ServiceMeta]:
        """Return services filtered by category."""
        return [s for s in self._services.values() if s.category == category]

    def list_by_risk(self, risk_level: RiskLevel) -> list[ServiceMeta]:
        """Return services filtered by risk level."""
        return [s for s in self._services.values() if s.risk_level == risk_level]

    def is_known(self, service_id: str) -> bool:
        """Check if a service is registered (known)."""
        return service_id in self._services

    def novelty_score(self, service_id: str) -> float:
        """Return a novelty score for a service (0.0 = well-known, 1.0 = unknown).

        Used by the risk engine's service_novelty feature.
        """
        meta = self._services.get(service_id)
        if meta is None:
            return 1.0  # Unknown service
        return meta.risk_score

    def __len__(self) -> int:
        return len(self._services)

    def __contains__(self, service_id: str) -> bool:
        return service_id in self._services

    def to_dict(self) -> dict:
        return {
            "total_services": len(self._services),
            "services": [s.to_dict() for s in self._services.values()],
        }


# Singleton instance for convenience
default_registry = ServiceRegistry()
