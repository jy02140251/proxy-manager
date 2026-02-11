"""Proxy rotation scheduler with configurable strategies."""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RotationStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    WEIGHTED = "weighted"
    FAILOVER = "failover"


@dataclass
class SchedulerConfig:
    strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN
    health_check_interval: int = 60
    max_failures: int = 3
    cooldown_seconds: int = 300
    auto_remove_dead: bool = False


@dataclass
class ProxyStats:
    proxy_url: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    avg_response_time: float = 0.0
    last_used: float = 0.0
    last_success: float = 0.0
    is_cooling_down: bool = False
    cooldown_until: float = 0.0


class ProxyScheduler:
    """Manages proxy rotation with multiple strategies."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self._proxies: Dict[str, ProxyStats] = {}
        self._rr_index = 0
        self._lock = asyncio.Lock()

    def add_proxy(self, proxy_url: str, weight: int = 1) -> None:
        if proxy_url not in self._proxies:
            self._proxies[proxy_url] = ProxyStats(proxy_url=proxy_url)
            logger.info(f"Added proxy: {proxy_url}")

    def remove_proxy(self, proxy_url: str) -> None:
        self._proxies.pop(proxy_url, None)
        logger.info(f"Removed proxy: {proxy_url}")

    async def get_next(self) -> Optional[str]:
        async with self._lock:
            available = self._get_available_proxies()
            if not available:
                logger.warning("No available proxies")
                return None

            if self.config.strategy == RotationStrategy.ROUND_ROBIN:
                return self._round_robin(available)
            elif self.config.strategy == RotationStrategy.LEAST_USED:
                return self._least_used(available)
            elif self.config.strategy == RotationStrategy.FAILOVER:
                return self._failover(available)
            else:
                return self._round_robin(available)

    def _get_available_proxies(self) -> List[ProxyStats]:
        now = time.time()
        available = []
        for stats in self._proxies.values():
            if stats.is_cooling_down and now > stats.cooldown_until:
                stats.is_cooling_down = False
                stats.consecutive_failures = 0
            if not stats.is_cooling_down:
                available.append(stats)
        return available

    def _round_robin(self, proxies: List[ProxyStats]) -> str:
        self._rr_index = self._rr_index % len(proxies)
        proxy = proxies[self._rr_index]
        self._rr_index += 1
        proxy.last_used = time.time()
        proxy.total_requests += 1
        return proxy.proxy_url

    def _least_used(self, proxies: List[ProxyStats]) -> str:
        proxy = min(proxies, key=lambda p: p.total_requests)
        proxy.last_used = time.time()
        proxy.total_requests += 1
        return proxy.proxy_url

    def _failover(self, proxies: List[ProxyStats]) -> str:
        proxy = max(proxies, key=lambda p: p.successful_requests / max(p.total_requests, 1))
        proxy.last_used = time.time()
        proxy.total_requests += 1
        return proxy.proxy_url

    def report_success(self, proxy_url: str, response_time: float = 0) -> None:
        if proxy_url in self._proxies:
            stats = self._proxies[proxy_url]
            stats.successful_requests += 1
            stats.consecutive_failures = 0
            stats.last_success = time.time()
            n = stats.successful_requests
            stats.avg_response_time = (stats.avg_response_time * (n - 1) + response_time) / n

    def report_failure(self, proxy_url: str) -> None:
        if proxy_url in self._proxies:
            stats = self._proxies[proxy_url]
            stats.failed_requests += 1
            stats.consecutive_failures += 1
            if stats.consecutive_failures >= self.config.max_failures:
                stats.is_cooling_down = True
                stats.cooldown_until = time.time() + self.config.cooldown_seconds
                logger.warning(f"Proxy {proxy_url} cooling down for {self.config.cooldown_seconds}s")

    def get_stats(self) -> List[Dict]:
        return [
            {
                "url": s.proxy_url,
                "total": s.total_requests,
                "success": s.successful_requests,
                "failed": s.failed_requests,
                "avg_response_time": round(s.avg_response_time, 3),
                "cooling_down": s.is_cooling_down,
            }
            for s in self._proxies.values()
        ]

    @property
    def proxy_count(self) -> int:
        return len(self._proxies)

    @property
    def available_count(self) -> int:
        return len(self._get_available_proxies())