"""
REST API for Proxy Manager.

Provides HTTP endpoints for proxy CRUD operations,
health checking, and pool statistics.
"""

import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from proxy_manager import ProxyManager
from health_checker import HealthChecker
from rotator import ProxyRotator
from config import config

app = FastAPI(
    title="Proxy Manager API",
    description="RESTful API for managing proxy pools",
    version="1.0.0",
)

manager = ProxyManager()
checker = HealthChecker()
rotator = ProxyRotator()


class ProxyCreate(BaseModel):
    """Schema for creating a new proxy."""
    address: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None


class ProxyResponse(BaseModel):
    """Schema for proxy response data."""
    address: str
    port: int
    protocol: str
    status: str
    latency_ms: float
    success_rate: float


@app.get("/api/proxies")
async def list_proxies(
    status: Optional[str] = Query(None, description="Filter by status"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
):
    """List all proxies with optional filtering."""
    proxies = manager.get_all_proxies()

    if status:
        proxies = [p for p in proxies if p.status.value == status]
    if protocol:
        proxies = [p for p in proxies if p.protocol.value == protocol]

    return {
        "proxies": [
            ProxyResponse(
                address=p.address,
                port=p.port,
                protocol=p.protocol.value,
                status=p.status.value,
                latency_ms=p.latency_ms,
                success_rate=p.success_rate,
            )
            for p in proxies
        ],
        "total": len(proxies),
    }


@app.post("/api/proxies", status_code=201)
async def add_proxy(data: ProxyCreate):
    """Add a new proxy to the pool."""
    try:
        proxy = manager.add_proxy(
            address=data.address,
            port=data.port,
            protocol=data.protocol,
            username=data.username,
            password=data.password,
            country=data.country,
        )
        return {"message": "Proxy added", "proxy": proxy.url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/proxies/{address}/{port}")
async def remove_proxy(address: str, port: int):
    """Remove a proxy from the pool."""
    if manager.remove_proxy(address, port):
        return {"message": f"Proxy {address}:{port} removed"}
    raise HTTPException(status_code=404, detail="Proxy not found")


@app.get("/api/proxies/next")
async def get_next_proxy(
    strategy: str = Query("round_robin", description="Rotation strategy"),
):
    """Get the next available proxy using specified rotation strategy."""
    proxy = rotator.get_next(manager.get_all_proxies(), strategy)
    if not proxy:
        raise HTTPException(status_code=503, detail="No active proxies available")
    return ProxyResponse(
        address=proxy.address,
        port=proxy.port,
        protocol=proxy.protocol.value,
        status=proxy.status.value,
        latency_ms=proxy.latency_ms,
        success_rate=proxy.success_rate,
    )


@app.post("/api/health-check")
async def run_health_check():
    """Run health check on all proxies."""
    proxies = manager.get_all_proxies()
    result = await checker.check_batch(proxies)
    return {
        "total": result.total,
        "healthy": result.healthy,
        "unhealthy": result.unhealthy,
        "avg_latency_ms": result.avg_latency_ms,
        "duration_s": result.check_duration_s,
    }


@app.get("/api/stats")
async def get_stats():
    """Get proxy pool statistics."""
    return {
        "pool_size": manager.pool_size,
        "active_count": manager.active_count,
        "protocols": {
            proto: len([p for p in manager.get_all_proxies() if p.protocol.value == proto])
            for proto in ["http", "https", "socks5"]
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.api_host, port=config.api_port)