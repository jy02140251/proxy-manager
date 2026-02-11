"""
Data Models for Proxy Manager.

Defines proxy entity, health check results, and
statistics data structures.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProxyProtocol(str, Enum):
    """Supported proxy protocols."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyStatus(str, Enum):
    """Proxy health status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHECKING = "checking"
    BANNED = "banned"


@dataclass
class Proxy:
    """Represents a single proxy server."""

    address: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    status: ProxyStatus = ProxyStatus.INACTIVE
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_check_time: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def url(self) -> str:
        """Get the full proxy URL with authentication if available."""
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.address}:{self.port}"
        return f"{self.protocol.value}://{self.address}:{self.port}"

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0

    def record_success(self, latency: float) -> None:
        """Record a successful health check."""
        self.success_count += 1
        self.consecutive_failures = 0
        self.latency_ms = latency
        self.status = ProxyStatus.ACTIVE
        self.last_check_time = time.time()

    def record_failure(self) -> None:
        """Record a failed health check."""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_check_time = time.time()


@dataclass
class HealthCheckResult:
    """Result of a batch health check operation."""
    total: int = 0
    healthy: int = 0
    unhealthy: int = 0
    avg_latency_ms: float = 0.0
    check_duration_s: float = 0.0