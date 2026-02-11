"""
Proxy Manager Core Module.

Provides the main ProxyManager class for adding, removing,
and managing proxy pools with SQLite persistence.
"""

import sqlite3
import logging
from typing import List, Optional

from models import Proxy, ProxyProtocol, ProxyStatus
from config import config

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Core proxy pool manager with SQLite persistence.
    
    Manages a pool of proxy servers, providing CRUD operations,
    filtering, and integration with health checking and rotation.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        self._pool: List[Proxy] = []
        self._init_database()
        self._load_proxies()

    def _init_database(self) -> None:
        """Initialize SQLite database and create tables if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT DEFAULT 'http',
                    status TEXT DEFAULT 'inactive',
                    username TEXT,
                    password TEXT,
                    country TEXT,
                    latency_ms REAL DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    consecutive_failures INTEGER DEFAULT 0,
                    last_check_time REAL DEFAULT 0,
                    created_at REAL,
                    PRIMARY KEY (address, port)
                )
            """)
            conn.commit()
        logger.info("Database initialized at %s", self.db_path)

    def _load_proxies(self) -> None:
        """Load all proxies from database into memory pool."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM proxies").fetchall()
            self._pool = [
                Proxy(
                    address=row["address"],
                    port=row["port"],
                    protocol=ProxyProtocol(row["protocol"]),
                    status=ProxyStatus(row["status"]),
                    username=row["username"],
                    password=row["password"],
                    country=row["country"],
                    latency_ms=row["latency_ms"],
                    success_count=row["success_count"],
                    failure_count=row["failure_count"],
                    consecutive_failures=row["consecutive_failures"],
                    last_check_time=row["last_check_time"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        logger.info("Loaded %d proxies from database", len(self._pool))

    def add_proxy(
        self,
        address: str,
        port: int,
        protocol: str = "http",
        username: Optional[str] = None,
        password: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Proxy:
        """
        Add a new proxy to the pool.

        Args:
            address: Proxy IP address or hostname.
            port: Proxy port number.
            protocol: Protocol type (http, https, socks5).
            username: Optional authentication username.
            password: Optional authentication password.
            country: Optional country code.

        Returns:
            The created Proxy object.

        Raises:
            ValueError: If the proxy already exists or protocol is invalid.
        """
        if protocol not in config.supported_protocols:
            raise ValueError(f"Unsupported protocol: {protocol}")

        # Check for duplicates
        for p in self._pool:
            if p.address == address and p.port == port:
                raise ValueError(f"Proxy {address}:{port} already exists")

        proxy = Proxy(
            address=address,
            port=port,
            protocol=ProxyProtocol(protocol),
            username=username,
            password=password,
            country=country,
        )

        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO proxies (address, port, protocol, username, password, country, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (address, port, protocol, username, password, country, proxy.created_at),
            )
            conn.commit()

        self._pool.append(proxy)
        logger.info("Added proxy %s:%d (%s)", address, port, protocol)
        return proxy

    def remove_proxy(self, address: str, port: int) -> bool:
        """Remove a proxy from the pool and database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM proxies WHERE address = ? AND port = ?",
                (address, port),
            )
            conn.commit()
            removed = cursor.rowcount > 0

        if removed:
            self._pool = [p for p in self._pool if not (p.address == address and p.port == port)]
            logger.info("Removed proxy %s:%d", address, port)
        return removed

    def get_active_proxies(self) -> List[Proxy]:
        """Get all proxies with active status."""
        return [p for p in self._pool if p.status == ProxyStatus.ACTIVE]

    def get_all_proxies(self) -> List[Proxy]:
        """Get all proxies regardless of status."""
        return list(self._pool)

    @property
    def pool_size(self) -> int:
        """Get total number of proxies in pool."""
        return len(self._pool)

    @property
    def active_count(self) -> int:
        """Get number of active proxies."""
        return len(self.get_active_proxies())