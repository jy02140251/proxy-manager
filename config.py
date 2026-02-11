"""
Proxy Manager Configuration.

Centralized configuration with environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class ProxyConfig:
    """Configuration for the proxy manager."""

    # Database
    db_path: str = os.getenv("PROXY_DB_PATH", "proxies.db")

    # Health Check Settings
    health_check_url: str = os.getenv("HEALTH_CHECK_URL", "https://httpbin.org/ip")
    health_check_timeout: int = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
    health_check_interval: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))
    max_consecutive_failures: int = int(os.getenv("MAX_FAILURES", "3"))

    # Rotation Settings
    default_strategy: str = os.getenv("ROTATION_STRATEGY", "round_robin")
    min_pool_size: int = int(os.getenv("MIN_POOL_SIZE", "1"))

    # API Settings
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8080"))
    api_key: str = os.getenv("API_KEY", "")

    # Supported protocols
    supported_protocols: List[str] = field(
        default_factory=lambda: ["http", "https", "socks5"]
    )

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "proxy_manager.log")


config = ProxyConfig()