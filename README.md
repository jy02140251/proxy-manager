# Proxy Manager

A high-performance proxy IP management tool with automatic health checking, intelligent rotation, and REST API interface. Supports HTTP, HTTPS, and SOCKS5 proxies.

## Features

- **Multi-Protocol Support**: HTTP, HTTPS, SOCKS5 proxy management
- **Health Checking**: Automatic periodic proxy health verification with configurable intervals
- **Smart Rotation**: Round-robin, random, and latency-based proxy rotation strategies
- **REST API**: Full-featured API for proxy CRUD operations and statistics
- **Persistence**: SQLite-backed storage with in-memory caching
- **Docker Ready**: Containerized deployment with Docker

## Installation

```bash
git clone https://github.com/jy02140251/proxy-manager.git
cd proxy-manager
pip install -r requirements.txt
```

## Quick Start

```python
from proxy_manager import ProxyManager

manager = ProxyManager()

# Add proxies
manager.add_proxy("http://1.2.3.4:8080", protocol="http")
manager.add_proxy("socks5://5.6.7.8:1080", protocol="socks5")

# Get next available proxy (auto health-checked)
proxy = manager.get_proxy(strategy="latency")
print(f"Using proxy: {proxy.address}")

# Run health check
results = await manager.check_all()
print(f"Healthy: {results.healthy}/{results.total}")
```

## API Usage

```bash
# Start the API server
python api.py

# Add a proxy
curl -X POST http://localhost:8080/api/proxies \
  -H "Content-Type: application/json" \
  -d '{"address": "http://1.2.3.4:8080", "protocol": "http"}'

# Get a proxy with rotation
curl http://localhost:8080/api/proxies/next?strategy=random
```

## Configuration

Edit `config.py` or use environment variables. See the configuration section for details.

## License

MIT License