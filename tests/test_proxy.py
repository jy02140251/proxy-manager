"""
Proxy Manager Unit Tests.

Tests for proxy CRUD operations, validation utilities,
and rotation strategies.
"""

import os
import pytest

from proxy_manager import ProxyManager
from models import Proxy, ProxyProtocol, ProxyStatus
from rotator import ProxyRotator
from utils import parse_proxy_url, validate_ip_address, validate_port


@pytest.fixture
def manager(tmp_path):
    """Create a ProxyManager with a temporary database."""
    db_path = str(tmp_path / "test_proxies.db")
    return ProxyManager(db_path=db_path)


class TestProxyManager:
    """Tests for ProxyManager class."""

    def test_add_proxy(self, manager):
        """Test adding a proxy to the pool."""
        proxy = manager.add_proxy("1.2.3.4", 8080, "http")
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8080
        assert proxy.protocol == ProxyProtocol.HTTP
        assert manager.pool_size == 1

    def test_add_duplicate_proxy_raises(self, manager):
        """Test that adding a duplicate proxy raises ValueError."""
        manager.add_proxy("1.2.3.4", 8080)
        with pytest.raises(ValueError, match="already exists"):
            manager.add_proxy("1.2.3.4", 8080)

    def test_add_invalid_protocol_raises(self, manager):
        """Test that an invalid protocol raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported protocol"):
            manager.add_proxy("1.2.3.4", 8080, "ftp")

    def test_remove_proxy(self, manager):
        """Test removing a proxy from the pool."""
        manager.add_proxy("1.2.3.4", 8080)
        assert manager.remove_proxy("1.2.3.4", 8080) is True
        assert manager.pool_size == 0

    def test_remove_nonexistent_proxy(self, manager):
        """Test removing a proxy that does not exist."""
        assert manager.remove_proxy("9.9.9.9", 1234) is False

    def test_get_active_proxies(self, manager):
        """Test filtering active proxies."""
        p1 = manager.add_proxy("1.1.1.1", 8080)
        p2 = manager.add_proxy("2.2.2.2", 8080)
        p1.status = ProxyStatus.ACTIVE
        assert len(manager.get_active_proxies()) == 1


class TestProxyRotator:
    """Tests for proxy rotation strategies."""

    def test_round_robin(self):
        """Test round-robin rotation returns proxies sequentially."""
        rotator = ProxyRotator()
        proxies = [
            Proxy(address="1.1.1.1", port=8080, status=ProxyStatus.ACTIVE),
            Proxy(address="2.2.2.2", port=8080, status=ProxyStatus.ACTIVE),
        ]
        first = rotator.get_next(proxies, "round_robin")
        second = rotator.get_next(proxies, "round_robin")
        assert first.address == "1.1.1.1"
        assert second.address == "2.2.2.2"

    def test_no_active_proxies_returns_none(self):
        """Test that rotation returns None when no proxies are active."""
        rotator = ProxyRotator()
        proxies = [
            Proxy(address="1.1.1.1", port=8080, status=ProxyStatus.INACTIVE),
        ]
        assert rotator.get_next(proxies, "random") is None


class TestUtils:
    """Tests for utility functions."""

    def test_parse_proxy_url(self):
        """Test parsing a valid proxy URL."""
        addr, port, proto, user, pwd = parse_proxy_url("socks5://user:pass@1.2.3.4:1080")
        assert addr == "1.2.3.4"
        assert port == 1080
        assert proto == "socks5"
        assert user == "user"
        assert pwd == "pass"

    def test_parse_proxy_url_no_auth(self):
        """Test parsing a proxy URL without authentication."""
        addr, port, proto, user, pwd = parse_proxy_url("http://5.6.7.8:3128")
        assert addr == "5.6.7.8"
        assert port == 3128
        assert user is None

    def test_validate_ip_address(self):
        """Test IP address validation."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("999.1.1.1") is False
        assert validate_ip_address("abc") is False

    def test_validate_port(self):
        """Test port validation."""
        assert validate_port(8080) is True
        assert validate_port(0) is False
        assert validate_port(70000) is False