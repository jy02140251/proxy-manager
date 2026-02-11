"""Tests for the proxy rotation scheduler."""

import pytest
import asyncio
from scheduler import ProxyScheduler, SchedulerConfig, RotationStrategy


class TestProxyScheduler:
    @pytest.fixture
    def scheduler(self):
        config = SchedulerConfig(strategy=RotationStrategy.ROUND_ROBIN)
        s = ProxyScheduler(config)
        s.add_proxy("http://proxy1:8080")
        s.add_proxy("http://proxy2:8080")
        s.add_proxy("http://proxy3:8080")
        return s

    def test_add_proxy(self, scheduler):
        assert scheduler.proxy_count == 3

    def test_remove_proxy(self, scheduler):
        scheduler.remove_proxy("http://proxy1:8080")
        assert scheduler.proxy_count == 2

    @pytest.mark.asyncio
    async def test_round_robin(self, scheduler):
        p1 = await scheduler.get_next()
        p2 = await scheduler.get_next()
        p3 = await scheduler.get_next()
        p4 = await scheduler.get_next()
        assert p1 != p2
        assert p1 == p4  # wraps around

    def test_report_success(self, scheduler):
        scheduler.report_success("http://proxy1:8080", response_time=0.5)
        stats = scheduler.get_stats()
        proxy1 = next(s for s in stats if s["url"] == "http://proxy1:8080")
        assert proxy1["success"] == 1

    def test_report_failure_cooldown(self):
        config = SchedulerConfig(max_failures=2, cooldown_seconds=10)
        s = ProxyScheduler(config)
        s.add_proxy("http://proxy1:8080")
        s.report_failure("http://proxy1:8080")
        s.report_failure("http://proxy1:8080")
        stats = s.get_stats()
        assert stats[0]["cooling_down"] is True

    @pytest.mark.asyncio
    async def test_no_proxies_returns_none(self):
        s = ProxyScheduler()
        result = await s.get_next()
        assert result is None

    def test_get_stats(self, scheduler):
        stats = scheduler.get_stats()
        assert len(stats) == 3
        assert all("url" in s for s in stats)

    @pytest.mark.asyncio
    async def test_least_used_strategy(self):
        config = SchedulerConfig(strategy=RotationStrategy.LEAST_USED)
        s = ProxyScheduler(config)
        s.add_proxy("http://proxy1:8080")
        s.add_proxy("http://proxy2:8080")
        p1 = await s.get_next()
        p2 = await s.get_next()
        assert p1 != p2  # should alternate since both start at 0