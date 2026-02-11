"""
Proxy Health Checker Module.

Performs concurrent health checks on proxy servers using
async HTTP requests with configurable timeout and targets.
"""

import asyncio
import time
import logging
from typing import List

import aiohttp

from models import Proxy, ProxyStatus, HealthCheckResult
from config import config

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Asynchronous proxy health checker.
    
    Verifies proxy connectivity by making HTTP requests through
    each proxy to a configurable health check URL.
    """

    def __init__(
        self,
        check_url: str = None,
        timeout: int = None,
        max_failures: int = None,
    ):
        self.check_url = check_url or config.health_check_url
        self.timeout = timeout or config.health_check_timeout
        self.max_failures = max_failures or config.max_consecutive_failures

    async def check_single(self, proxy: Proxy) -> bool:
        """
        Check a single proxy's health.

        Args:
            proxy: The proxy to check.

        Returns:
            True if proxy is healthy, False otherwise.
        """
        proxy.status = ProxyStatus.CHECKING
        start_time = time.time()

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)

            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout_config
            ) as session:
                async with session.get(
                    self.check_url,
                    proxy=proxy.url,
                ) as response:
                    if response.status == 200:
                        latency = (time.time() - start_time) * 1000
                        proxy.record_success(latency)
                        logger.debug(
                            "Proxy %s:%d healthy (%.0fms)",
                            proxy.address,
                            proxy.port,
                            latency,
                        )
                        return True

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.debug(
                "Proxy %s:%d failed: %s", proxy.address, proxy.port, str(e)
            )

        proxy.record_failure()

        # Ban proxy if too many consecutive failures
        if proxy.consecutive_failures >= self.max_failures:
            proxy.status = ProxyStatus.BANNED
            logger.warning(
                "Proxy %s:%d banned after %d consecutive failures",
                proxy.address,
                proxy.port,
                proxy.consecutive_failures,
            )

        return False

    async def check_batch(
        self, proxies: List[Proxy], concurrency: int = 20
    ) -> HealthCheckResult:
        """
        Check multiple proxies concurrently.

        Args:
            proxies: List of proxies to check.
            concurrency: Max concurrent checks.

        Returns:
            HealthCheckResult with aggregated statistics.
        """
        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_check(proxy: Proxy) -> bool:
            async with semaphore:
                return await self.check_single(proxy)

        results = await asyncio.gather(
            *[bounded_check(p) for p in proxies],
            return_exceptions=True,
        )

        healthy = sum(1 for r in results if r is True)
        unhealthy = len(proxies) - healthy
        active_proxies = [p for p in proxies if p.status == ProxyStatus.ACTIVE]
        avg_latency = (
            sum(p.latency_ms for p in active_proxies) / len(active_proxies)
            if active_proxies
            else 0
        )

        result = HealthCheckResult(
            total=len(proxies),
            healthy=healthy,
            unhealthy=unhealthy,
            avg_latency_ms=round(avg_latency, 2),
            check_duration_s=round(time.time() - start_time, 2),
        )

        logger.info(
            "Health check complete: %d/%d healthy (%.2fs)",
            healthy,
            len(proxies),
            result.check_duration_s,
        )
        return result