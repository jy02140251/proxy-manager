"""
Utility Functions for Proxy Manager.

Common helper functions for proxy parsing, validation,
and formatting used across the application.
"""

import re
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Regex pattern for proxy URL validation
PROXY_URL_PATTERN = re.compile(
    r"^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$"
)


def parse_proxy_url(url: str) -> Tuple[str, int, str, Optional[str], Optional[str]]:
    """
    Parse a proxy URL into its components.

    Args:
        url: Proxy URL (e.g., "socks5://user:pass@1.2.3.4:1080")

    Returns:
        Tuple of (address, port, protocol, username, password)

    Raises:
        ValueError: If the URL format is invalid.
    """
    match = PROXY_URL_PATTERN.match(url)
    if not match:
        raise ValueError(f"Invalid proxy URL format: {url}")

    protocol, username, password, address, port = match.groups()
    return address, int(port), protocol, username, password


def validate_ip_address(address: str) -> bool:
    """Validate an IPv4 address format."""
    parts = address.split(".")
    if len(parts) != 4:
        return False
    return all(
        part.isdigit() and 0 <= int(part) <= 255
        for part in parts
    )


def validate_port(port: int) -> bool:
    """Validate a port number is within valid range."""
    return 1 <= port <= 65535


def format_proxy_list(proxies: list, include_auth: bool = False) -> str:
    """
    Format a list of proxies as a human-readable string.

    Args:
        proxies: List of Proxy objects.
        include_auth: Whether to include authentication details.

    Returns:
        Formatted string with proxy details.
    """
    lines = []
    for i, proxy in enumerate(proxies, 1):
        status_icon = "+" if proxy.status.value == "active" else "-"
        line = f"  [{status_icon}] {proxy.address}:{proxy.port} ({proxy.protocol.value})"
        if proxy.latency_ms > 0:
            line += f" - {proxy.latency_ms:.0f}ms"
        if include_auth and proxy.username:
            line += f" [auth: {proxy.username}]"
        lines.append(line)
    return "\n".join(lines) if lines else "  (no proxies)"


def load_proxies_from_file(filepath: str) -> list:
    """
    Load proxy URLs from a text file (one per line).

    Args:
        filepath: Path to the proxy list file.

    Returns:
        List of parsed proxy tuples.
    """
    proxies = []
    try:
        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    proxy_data = parse_proxy_url(line)
                    proxies.append(proxy_data)
                except ValueError as e:
                    logger.warning("Line %d: %s", line_num, e)
    except FileNotFoundError:
        logger.error("Proxy file not found: %s", filepath)
    return proxies


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure application logging."""
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )