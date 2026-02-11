"""
Proxy Rotation Module.

Implements multiple rotation strategies for selecting
the next proxy from the active pool.
"""

import random
import logging
from typing import List, Optional

from models import Proxy, ProxyStatus

logger = logging.getLogger(__name__)


class ProxyRotator:
    """
    Proxy rotation engine supporting multiple strategies.
    
    Strategies:
        - round_robin: Sequential rotation through active proxies
        - random: Random selection from active proxies
        - latency: Select the proxy with lowest latency
        - weighted: Weighted selection based on success rate
    """

    def __init__(self):
        self._index: int = 0

    def get_next(
        self, proxies: List[Proxy], strategy: str = "round_robin"
    ) -> Optional[Proxy]:
        """
        Get the next proxy based on the specified strategy.

        Args:
            proxies: List of all proxies in the pool.
            strategy: Rotation strategy to use.

        Returns:
            Selected Proxy or None if no active proxies available.
        """
        active = [p for p in proxies if p.status == ProxyStatus.ACTIVE]

        if not active:
            logger.warning("No active proxies available for rotation")
            return None

        strategy_map = {
            "round_robin": self._round_robin,
            "random": self._random,
            "latency": self._lowest_latency,
            "weighted": self._weighted_random,
        }

        strategy_fn = strategy_map.get(strategy, self._round_robin)
        selected = strategy_fn(active)

        if selected:
            logger.debug(
                "Selected proxy %s:%d via %s strategy",
                selected.address,
                selected.port,
                strategy,
            )
        return selected

    def _round_robin(self, proxies: List[Proxy]) -> Proxy:
        """Select proxies in sequential order."""
        self._index = self._index % len(proxies)
        proxy = proxies[self._index]
        self._index += 1
        return proxy

    def _random(self, proxies: List[Proxy]) -> Proxy:
        """Select a random proxy from the pool."""
        return random.choice(proxies)

    def _lowest_latency(self, proxies: List[Proxy]) -> Proxy:
        """Select the proxy with the lowest latency."""
        return min(proxies, key=lambda p: p.latency_ms if p.latency_ms > 0 else float("inf"))

    def _weighted_random(self, proxies: List[Proxy]) -> Proxy:
        """Select proxy weighted by success rate."""
        weights = [max(p.success_rate, 1.0) for p in proxies]
        return random.choices(proxies, weights=weights, k=1)[0]