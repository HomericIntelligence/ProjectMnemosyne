---
name: architecture-crosshost-nats-compose-deployment
description: "Deploy HomericIntelligence ecosystem across two Tailscale hosts using Docker Compose overlays and direct NATS connections. Use when: (1) splitting the E2E stack across multiple machines, (2) configuring NATS leafnode or direct connections over Tailscale, (3) debugging cross-host service communication, (4) setting up NATS-to-Loki log forwarding bridges."
category: architecture
date: 2026-04-06
version: "1.1.0"
user-invocable: false
verification: verified-local
tags:
  - cross-host
  - deployment
  - compose
  - tailscale
  - nats
  - leafnode
  - podman
  - e2e
  - homeric-intelligence
  - loki
  - native-binary
  - pythonpath
---

# Cross-Host NATS Compose Deployment

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-06 |
| **Objective** | Deploy HomericIntelligence ecosystem across two Tailscale hosts for E2E agent evaluation |
| **Outcome** | Two-host deployment with worker host running full compose stack and control host running native Nestor + odysseus-console. Direct NATS over Tailscale, no leaf node needed. Full 6-phase cross-host validation PASS confirmed 2026-04-06. |
| **Verification** | verified-local |

## When to Use

- Splitting the HomericIntelligence E2E compose stack across multiple physical machines
- Configuring NATS connections (direct or leafnode) over Tailscale mesh networking
- Debugging cross-host service communication issues (DNS, ports, connectivity)
- Setting up NATS-to-Loki log forwarding for distributed observability
- Understanding when NATS leaf nodes add value vs. when direct connections suffice
- Running NATS as a native binary when rootlessport is absent (slirp4netns port remapping issue)
- Diagnosing `No module named 'hermes'` when starting Hermes with uvicorn

## Verified Workflow

### Quick Reference

```bash
# Worker host (epimetheus 100.92.173.32) — start the compose stack
CONTROL_HOST_IP=100.73.61.56 just crosshost-up $CONTROL_HOST_IP

# Control host (100.73.61.56) — start Nestor native binary
NATS_URL=nats://100.92.173.32:4222 ./build/ProjectNestor/ProjectNestor_server

# Control host — apply agent manifests via Agamemnon
AGAMEMNON_URL=http://100.92.173.32:8080 ./scripts/apply.sh

# Control host — run E2E validation (8-phase)
WORKER_HOST_IP=100.92.173.32 just crosshost-test $WORKER_HOST_IP

# Control host — start event viewer
just odysseus-console nats://100.92.173.32:4222
```

### Native Binary Startup Pattern (when rootlessport absent)

When `rootlessport` is not available on the worker host, podman's slirp4netns network stack remaps container ports to ephemeral ports invisible to external hosts. In this case, run all services as native binaries:

```bash
# Worker host: start all services as native binaries (when rootlessport absent)

# NATS — must use native binary when rootlessport missing
~/.local/bin/nats-server -js -p 4222 -m 8222 > /tmp/nats-crosshost.log &
sleep 2 && curl http://localhost:4222/varz | python3 -c "import sys,json; d=json.load(sys.stdin); print('NATS OK:', d['server_id'][:12])"

# Agamemnon
NATS_URL=nats://localhost:4222 ./control/ProjectAgamemnon/build/debug/ProjectAgamemnon_server > /tmp/agamemnon-crosshost.log &

# Hermes — PYTHONPATH=src required
cd infrastructure/ProjectHermes
PYTHONPATH=src pixi run python -m uvicorn hermes.main:app --host 0.0.0.0 --port 8085 > /tmp/hermes-crosshost.log &
cd -

# hello-myrmidon Python worker
python3 provisioning/Myrmidons/hello-world/main.py > /tmp/myrmidon-crosshost.log &
```

**Important:** If NATS port changes mid-session (e.g., switching from container to native binary), restart both Agamemnon and Hermes — they do not automatically reconnect to the new NATS address.

### Deployment Topology

```
Worker Host (epimetheus 100.92.173.32):
  NATS (:4222/:8222)
  ├── Agamemnon (:8080) — REST API, NATS pub/sub
  ├── Hermes (:8085) — Webhook→NATS bridge
  ├── hello-myrmidon — NATS pull consumer
  └── argus-exporter (:9100) — Scrapes all services + remote Nestor
  Prometheus (:9090) ← scrapes argus-exporter
  Grafana (:3001) ← dashboards
  Loki (:3100) ← log aggregation

        ┌─── Tailscale mesh ───┐

Control Host (100.73.61.56):
  Nestor (:8081) — native binary, connects to worker NATS
  odysseus-console — NATS event viewer
```

### Compose Overlay Pattern for Cross-Host Splits

The key pattern is using `docker-compose.crosshost.yml` as an overlay on the base `docker-compose.e2e.yml`. Services that run on other hosts are disabled via `profiles: ["disabled"]`, and dependent services are reconfigured to scrape remote endpoints.

```yaml
# docker-compose.crosshost.yml (overlay)
services:
  # Disable services that run on the control host
  nestor:
    profiles: ["disabled"]

  # Reconfigure argus-exporter to scrape remote Nestor
  argus-exporter:
    environment:
      - NESTOR_URL=http://${CONTROL_HOST_IP}:8081
```

Usage:
```bash
podman compose -f docker-compose.e2e.yml -f docker-compose.crosshost.yml up -d
```

### NATS Connection Strategy: Direct vs. Leaf Node

**Direct NATS connection over Tailscale** is the correct choice for simple topologies (2 hosts, 1 remote client). Leaf nodes are an optimization for when multiple local services need NATS access on the remote host.

| Topology | Recommended | Reason |
| ---------- | ------------- | -------- |
| 2 hosts, 1 remote client | Direct connection | Zero additional complexity, Tailscale handles routing |
| 2+ hosts, multiple remote clients | Leaf node | Reduces WAN connections, local pub/sub for co-located services |
| Hub-and-spoke (many remotes) | Leaf nodes per spoke | Each spoke gets local NATS, leaf auto-reconnects |

### NATS Leafnode Port Configuration (Critical)

**NATS leaf.conf must connect to port 7422 (leafnode listen port), NOT port 4222 (client port).**

This was a blocking bug (issues #5, #16). The server must explicitly declare the leafnode listener:

```hcl
# server.conf — worker host
leafnodes {
  port = 7422
}
```

```hcl
# leaf.conf — remote host (if using leaf nodes)
leafnodes {
  remotes [
    {
      url: "nats-leaf://100.92.173.32:7422"
    }
  ]
}
```

**Common mistake:** Connecting leaf.conf to port 4222 produces a cryptic handshake error. Always use the dedicated leafnode port.

### Podman DNS Workaround

Podman rootless networking does not resolve container hostnames reliably. The `start-stack.sh` pattern discovers container IPs via `podman inspect` and restarts NATS-dependent services with direct IPs:

```bash
# Discover container IP
NATS_IP=$(podman inspect --format '{{.NetworkSettings.Networks.homeric-mesh.IPAddress}}' nats)

# Restart services with direct IP
podman compose -f docker-compose.e2e.yml -f docker-compose.crosshost.yml \
  run -d -e NATS_URL=nats://${NATS_IP}:4222 agamemnon
```

### NATS-to-Loki Bridge Pattern

Loki does not natively subscribe to NATS. A small Python bridge (~100 lines) using `nats-py` pull subscribers and Loki's `/loki/api/v1/push` HTTP API bridges the gap with batching:

```python
# Simplified bridge pattern
async def bridge():
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()
    sub = await js.pull_subscribe("hi.logs.>", "loki-bridge")
    while True:
        msgs = await sub.fetch(batch=100, timeout=5)
        entries = [format_loki_entry(m) for m in msgs]
        requests.post(f"{LOKI_URL}/loki/api/v1/push", json={"streams": entries})
        for m in msgs:
            await m.ack()
```

### Submodule Pin Staleness Detection

Always verify submodule pins match the expected branch head, especially after migrations:

```bash
# Check if submodule pin matches remote HEAD
cd provisioning/Myrmidons
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "WARNING: Myrmidons submodule is stale ($LOCAL vs $REMOTE)"
fi
```

The Myrmidons submodule was pinned to an old commit still targeting `ai-maestro` while the standalone checkout had been migrated to Agamemnon. This caused `aim_*` function calls to fail silently.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct leaf.conf to port 4222 | Connected leaf node to NATS client port | Leaf nodes require dedicated leafnode listener port (7422) | Always use the leafnode-specific port (7422), not the client port (4222) |
| Submodule scripts as-is | Tried to use provisioning/Myrmidons scripts | Submodule pinned to old commit with `aim_*` functions targeting ai-maestro | Verify submodule pins match standalone checkouts after migrations |
| Keystone as transport daemon | Planned to use Keystone to bridge BlazingMQ to NATS | Keystone is a C++ library with MessageBus abstraction, not a deployable service. No BlazingMQ binary exists. | Components connect to NATS directly; Keystone transport abstraction is aspirational |
| NATS via podman container with slirp4netns | `podman run -d --network=host` for NATS | slirp4netns (rootless network stack when rootlessport absent) remaps port 4222 to an ephemeral port (e.g., 14222) invisible to external clients; cross-host `curl http://<worker-ip>:4222/varz` gets "Connection refused" | Start NATS as a native binary (`~/.local/bin/nats-server -js -p 4222 -m 8222`) when rootlessport is absent |
| Hermes started without PYTHONPATH | `pixi run python -m uvicorn hermes.main:app` | `src/` directory is not on PYTHONPATH by default; fails with `No module named 'hermes'` | Always prefix with `PYTHONPATH=src`: `PYTHONPATH=src pixi run python -m uvicorn hermes.main:app --host 0.0.0.0 --port 8085` |
| No restart after NATS port change | Left Agamemnon and Hermes running when switching NATS from container to native binary | Running processes lose their NATS connection and do not automatically reconnect to the new address | Restart both services after NATS is stable on the correct port |

## Results & Parameters

```yaml
# Deployment topology
worker_host:
  name: epimetheus
  tailscale_ip: 100.92.173.32
  services:
    - nats:4222/:8222
    - agamemnon:8080
    - hermes:8085
    - hello-myrmidon
    - prometheus:9090
    - grafana:3001
    - loki:3100
    - argus-exporter:9100

control_host:
  tailscale_ip: 100.73.61.56
  services:
    - nestor:8081 (native binary)
    - odysseus-console (NATS subscriber)

# Files created
files:
  - docker-compose.crosshost.yml       # Compose overlay for cross-host splits
  - e2e/start-crosshost.sh             # Launcher with podman DNS workarounds
  - e2e/run-crosshost-e2e.sh           # 8-phase cross-host validation
  - e2e/prometheus.crosshost.yml       # Remote Nestor scrape config
  - tools/odysseus-console.py          # NATS event viewer
  - infrastructure/ProjectArgus/nats-loki-bridge/  # NATS-to-Loki bridge
  - .env.example                       # Env var documentation

# Key environment variables
env_vars:
  CONTROL_HOST_IP: "Tailscale IP of the control host"
  WORKER_HOST_IP: "Tailscale IP of the worker host"
  NATS_URL: "nats://<worker_ip>:4222"
  AGAMEMNON_URL: "http://<worker_ip>:8080"
  NESTOR_URL: "http://<control_ip>:8081"
```

## Related Skills

| Skill | Relationship |
| ------- | ------------- |
| `e2e-homeric-compose-cpp-pipeline` | Base single-host E2E pipeline; this skill extends it to multi-host |
| `tailscale-agamemnon-setup` | Tailscale installation and Agamemnon cross-host connectivity |
| `natsc-fetchcontent-cpp20-integration` | NATS C client integration for C++20 services |

## Verified On

| Project | Date | Details |
| --------- | ------ | --------- |
| Odysseus | 2026-04-03 | Cross-host E2E deployment — 2-host topology: worker (epimetheus) + control host over Tailscale mesh |
| Odysseus | 2026-04-06 | Full cross-host validation PASS after firewalld fix; all 6 checks: NATS reachable, Agamemnon health, Hermes webhook, task lifecycle, observability metrics |
