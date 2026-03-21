---
name: prometheus-json-api-exporter-sidecar
description: 'Deploy a Python sidecar that converts JSON REST APIs to Prometheus text
  format. Use when: upstream services expose JSON (not /metrics), all Prometheus targets
  show up=0, or bridging Docker-networked services.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Prometheus JSON API Exporter Sidecar

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Get Prometheus metrics from services that only expose JSON REST APIs |
| Outcome | ✅ Operational — both `homeric-exporter` and `prometheus` targets show `up=1` |
| Stack | Python 3.11-slim + urllib (stdlib only), Docker Compose, Prometheus |
| Context | HomericIntelligence/ProjectArgus — ai-maestro and NATS expose JSON, not Prometheus format |

## When to Use

1. Service exposes JSON endpoints (e.g. `/api/diagnostics`, `/varz`) instead of `/metrics`
2. All Prometheus targets show `up=0` after pointing scrape configs at JSON endpoints
3. You need to bridge metrics from a Docker-networked service to Prometheus
4. You want metrics without modifying the upstream service (treat it as a black box)
5. Host services need to be reached from inside Docker containers (gateway IP problem)

## Verified Workflow

### Quick Reference

```python
# Minimal stdlib exporter skeleton
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request, json, time

def collect() -> str:
    lines = []
    def gauge(name, value, labels={}):
        lstr = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name}{{{lstr}}} {value}")

    d = json.loads(urllib.request.urlopen("http://UPSTREAM/api/status", timeout=5).read())
    gauge("myservice_up", 1 if d.get("status") == "ok" else 0)
    return "\n".join(lines) + "\n"
```

```yaml
# docker-compose.yml sidecar entry
argus-exporter:
  image: python:3.11-slim
  restart: unless-stopped
  ports:
    - "9100:9100"
  volumes:
    - ./exporter/exporter.py:/exporter.py:ro
  command: python /exporter.py
  environment:
    MAESTRO_URL: "http://172.20.0.1:23000"   # host gateway from this network
    NATS_URL: "http://172.24.0.1:8222"        # different network = different gateway
  networks:
    - argus
```

```yaml
# prometheus.yml — point at sidecar, not the JSON service
scrape_configs:
  - job_name: 'homeric-exporter'
    static_configs:
      - targets: ['argus-exporter:9100']   # sidecar hostname on Docker network
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Step 1 — Diagnose the root cause of `up=0`

Before writing any code, confirm why targets are down. Check what the upstream service actually returns:

```bash
# Does it return Prometheus text format?
curl -s http://HOST:PORT/metrics | head -5
# Expected: "# HELP ..." / "# TYPE ..." lines
# If you see JSON, you need a sidecar.

# What does Prometheus see inside its container?
docker exec argus-prometheus cat /etc/prometheus/prometheus.yml
# Verify it matches what's on disk — config reload doesn't always take
```

**Key insight**: `docker compose restart prometheus` is more reliable than `POST /-/reload` when the file on disk differs from what the container has cached.

### Step 2 — Find the correct host gateway IP

Services in a Docker network reach the host at the network's gateway IP, NOT `localhost`.

```bash
# Find the gateway for a running Docker network
docker network inspect projectargus_argus | python3 -c \
  "import sys,json; d=json.load(sys.stdin); \
   print(d[0]['IPAM']['Config'][0]['Gateway'])"
# e.g. 172.24.0.1

# Verify from inside the container
docker exec argus-exporter python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://172.24.0.1:8222/varz', timeout=3).read()[:100])"
```

Different Docker networks have different gateway IPs. If ai-maestro lives on one subnet and NATS on another, use each network's gateway.

### Step 3 — Write the exporter

Use stdlib only (`urllib.request`, `json`, `http.server`) — no dependencies to install in the container:

```python
#!/usr/bin/env python3
import os, time, urllib.request, json, logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("exporter")

UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "http://host:port")
PORT = int(os.environ.get("EXPORTER_PORT", "9100"))

def _fetch(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read())
    except Exception as e:
        log.warning("fetch %s failed: %s", url, e)
        return None

def collect() -> str:
    lines = []
    def gauge(name, value, labels={}):
        lstr = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name}{{{lstr}}} {value}")

    d = _fetch(f"{UPSTREAM_URL}/api/status")
    if d:
        gauge("myservice_up", 1 if d.get("status") == "ok" else 0)
        gauge("myservice_items_total", d.get("count", 0))

    gauge("exporter_scrape_timestamp", time.time())
    return "\n".join(lines) + "\n"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = collect().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, fmt, *args): pass  # suppress access log noise

if __name__ == "__main__":
    log.info("exporter starting on port %d", PORT)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
```

### Step 4 — Add to docker-compose and bring up

```bash
# Add the service (see Quick Reference above), then:
docker compose up -d argus-exporter

# Verify it's producing metrics
curl -s http://localhost:9100/metrics | head -20

# Restart Prometheus to pick up updated prometheus.yml
docker compose restart prometheus
sleep 8

# Verify targets
curl -s "http://localhost:9090/api/v1/targets" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  [print(t['labels']['job'], t['health']) for t in d['data']['activeTargets']]"
```

### Step 5 — Add per-entity metrics with labels

For services returning lists (e.g. agent arrays), emit one metric per entity with labels:

```python
for entry in d.get("agents", []):
    ag = entry["agent"]
    online = 1 if ag.get("session", {}).get("status") == "online" else 0
    gauge("myservice_agent_online", online, {
        "name": ag["name"],
        "host": ag.get("hostId", "unknown"),
    })
```

This enables per-agent dashboards and alerting in Grafana.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Point Prometheus at ai-maestro `/api/diagnostics` directly | Added scrape job with `metrics_path: /api/diagnostics` | Endpoint returns JSON, not Prometheus text format — all targets showed `up=0` | Always verify upstream returns `# TYPE` lines before adding as scrape target |
| Point Prometheus at NATS `/metrics` | Added NATS scrape job targeting `localhost:8222/metrics` | NATS exposes `/varz` and `/jsz` JSON, not `/metrics`; also `localhost` inside container ≠ host | Check NATS docs — monitoring endpoints are JSON only; need sidecar |
| Use `POST /-/reload` to apply new prometheus.yml | Called `curl -X POST http://localhost:9090/-/reload` | Container still showed old config (`docker exec ... cat`) — volume mount may have been cached | Use `docker compose restart prometheus` for reliable config reload |
| Use `localhost` for host services in Docker | Set `NATS_URL=http://localhost:8222` in exporter container | `localhost` inside container = container itself, not the host | Find gateway IP with `docker network inspect`; different networks have different gateway IPs |
| `pixi run pip install -e .` in pixi env | Tried to install editable package via pip | `pip` not installed in pixi env by default; system pip refused due to externally-managed env | Add `package = { path = ".", editable = true }` to `[pypi-dependencies]` in pixi.toml |
| `python -m keystone.daemon` without package install | Ran daemon directly with pixi run | `ModuleNotFoundError: No module named 'keystone'` — src-layout not importable by default | Add editable install to pixi.toml `[pypi-dependencies]`; requires `pixi install` to re-solve |

## Results & Parameters

**Live metrics produced** (HomericIntelligence/ProjectArgus):

```
maestro_agents_total{} 7
maestro_agents_online{} 2
maestro_agent_online{name="laptop-mnemosyne-devops",host="hermes",program="claude-code"} 1
maestro_diagnostics_ok{} 1
maestro_check_ok{check="tmux"} 1
nats_connections{} 3
nats_jetstream_streams{} 2
nats_jetstream_messages{} 47
homeric_exporter_scrape_timestamp{} 1742082481.234
```

**Prometheus targets after fix:**
```
homeric-exporter  up
prometheus        up
```

**docker-compose.yml sidecar (production-ready):**
```yaml
argus-exporter:
  image: python:3.11-slim
  container_name: argus-exporter
  restart: unless-stopped
  ports:
    - "9100:9100"
  volumes:
    - ./exporter/exporter.py:/exporter.py:ro
  command: python /exporter.py
  environment:
    MAESTRO_URL: "http://172.20.0.1:23000"
    NATS_URL: "http://172.24.0.1:8222"
  networks:
    - argus
```

**pixi.toml fix for src-layout editable package:**
```toml
[pypi-dependencies]
mypackage = { path = ".", editable = true }
```
Run `pixi install` after adding this, then `pixi run python -m mypackage.daemon` works.
