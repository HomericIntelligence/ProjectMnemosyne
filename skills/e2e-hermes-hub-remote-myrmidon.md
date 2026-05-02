---
name: e2e-hermes-hub-remote-myrmidon
description: "Hub+remote-worker topology for HomericIntelligence E2E: hermes runs full stack (NATS JetStream, Agamemnon, Nestor, Hermes bridge, observability), epimetheus runs only the hello-myrmidon Python worker over Tailscale. Use when: (1) validating cross-host myrmidon dispatch end-to-end, (2) setting up a hub+single-remote-worker topology distinct from the symmetric crosshost split, (3) troubleshooting remote myrmidon NATS connectivity, (4) excluding a compose service via overlay profiles."
category: architecture
date: 2026-04-20
version: "1.1.0"
user-invocable: false
verification: verified-local
tags:
  - e2e
  - cross-host
  - hermes-hub
  - myrmidon
  - tailscale
  - nats
  - compose-overlay
  - podman
  - homeric-intelligence
  - remote-worker
---

# E2E Hermes-Hub Remote Myrmidon Topology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-20 |
| **Objective** | Validate cross-host myrmidon dispatch with hermes as the hub (full stack) and epimetheus as a single remote Python worker |
| **Outcome** | Scripts written and reviewed; not yet executed end-to-end (SSH to hermes refused from local machine during planning) |
| **Verification** | unverified — scripts are ready to run but have not been tested yet |

> **Update 2026-04-27:** Validated end-to-end in the Atlas first-run session. apollo (100.68.51.128) and hermes (100.73.61.56) both accepted SSH and had nats-py installed. 3-host fan-out (epimetheus + apollo + hermes) reached 6 NATS connections. Hermes module name confirmed: `hermes.server:app` (NOT `hermes.main:app`).

## When to Use

- Running the HomericIntelligence E2E stack with hermes as the hub (all services) and a separate remote worker host
- Validating that a Python myrmidon worker can subscribe to NATS on a remote hub over Tailscale
- Using compose overlays to disable a service on the hub side (so the remote worker is the sole subscriber)
- Debugging NATS cross-host connection count after a remote myrmidon starts
- Distinguishing the hub+remote-worker topology from the symmetric crosshost split (`architecture-crosshost-nats-compose-deployment`)

## Verified Workflow

### Quick Reference

```bash
# Start hub stack on hermes + launch remote myrmidon on epimetheus
just hermes-hub-up

# Run 8-phase E2E validator
just hermes-hub-test

# Tear down
just hermes-hub-down

# View hub logs
just hermes-hub-logs SERVICE=agamemnon
```

### Detailed Steps

1. **Hermes hub setup** — SSH to hermes (100.73.61.56):
   ```bash
   just doctor --role worker --install
   # Add tailscale0 to firewalld trusted zone so remote myrmidon can reach NATS
   sudo firewall-cmd --zone=trusted --add-interface=tailscale0 --permanent
   sudo firewall-cmd --reload
   # Resolve symlinks (rootless podman requirement)
   # Run compose with overlay that disables hello-myrmidon
   podman compose -f docker-compose.e2e.yml -f e2e/docker-compose.hermes-hub.yml up -d --build
   # Apply podman DNS workaround: inspect NATS container IP, restart NATS-dependent containers with direct IPs
   ```

2. **Compose overlay** — `e2e/docker-compose.hermes-hub.yml` disables hello-myrmidon on the hub:
   ```yaml
   services:
     hello-myrmidon:
       profiles:
         - disabled
   ```
   The `profiles: ["disabled"]` pattern is the correct way to exclude a service via overlay without removing it.

3. **Epimetheus remote worker setup** — SSH to epimetheus (100.92.173.32):
   ```bash
   # Clone Odysseus if absent (only provisioning/Myrmidons submodule needed)
   git clone https://github.com/HomericIntelligence/Odysseus.git
   git submodule update --init provisioning/Myrmidons
   # Launch myrmidon pointing at hermes NATS
   # Always use main.py (Python) — main.cpp also exists but should be ignored
   NATS_URL=nats://100.73.61.56:4222 nohup python3 provisioning/Myrmidons/hello-world/main.py \
     > /tmp/hello-myrmidon.log 2>&1 &
   ```

4. **Verify cross-host NATS connection**:
   ```bash
   # Should show connections >= 2 (Agamemnon + remote myrmidon)
   curl -s http://hermes:8222/varz | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['connections'] >= 2, d['connections']"
   ```

5. **Run 8-phase E2E validator** (`e2e/run-hermes-hub-e2e.sh`):
   - Phase 1: Hub health (all services responding)
   - Phase 2: NATS JetStream stream exists
   - Phase 3: Remote myrmidon NATS connection confirmed
   - Phase 4: Dispatch task via Agamemnon REST
   - Phase 5: Task routes to remote myrmidon (subject `hi.myrmidon.hello.>`)
   - Phase 6: Completion event published back on `hi.tasks.{team_id}.{task_id}.completed`
   - Phase 7: Agamemnon marks task complete
   - Phase 8: Observability stack captures the full trace

### Remote Myrmidon Dependencies

The hello-myrmidon Python worker requires **only**:
- `NATS_URL` environment variable pointing to hermes
- `nats-py >= 2.14.0` installed on the remote host
- No `AGAMEMNON_URL` needed — the worker only subscribes to NATS and publishes back via core NATS

epimetheus already had `nats-py 2.14.0` installed. Only the `provisioning/Myrmidons` submodule is needed — not the full recursive submodule tree.

### NATS Subject Flow

```
Agamemnon (hermes:8080)
  → publishes task to JetStream: hi.myrmidon.hello.<team_id>.<task_id>
  → remote myrmidon on epimetheus subscribes via push consumer: hi.myrmidon.hello.>
  → myrmidon completes task
  → publishes back via core NATS: hi.tasks.<team_id>.<task_id>.completed
  → Agamemnon receives completion, marks task done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | SSH to hermes from local machine during planning session | SSH refused (connection refused from local; Tailscale not active on dev machine) | Scripts are complete and correct but must be run from a Tailscale-connected machine or directly on hermes |
| Attempt 2 | Considered using AGAMEMNON_URL in the remote myrmidon launch command | Unnecessary — the Python worker communicates only via NATS subjects, not Agamemnon REST | Always check the myrmidon source first; NATS_URL is the sole required config |
| Attempt 3 | Considered full recursive `git submodule update --init --recursive` on epimetheus | Would pull all submodules including C++ build deps, heavy and slow | Use sparse init: `git submodule update --init provisioning/Myrmidons` |
| `uvicorn hermes.main:app` | Used `hermes.main:app` as the Hermes entry point (2026-04-27) | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` for Hermes uvicorn launch |
| Launching main.cpp instead of main.py | Agent got confused by C++ file in hello-world/ (2026-04-27) | Both main.py (Python) and main.cpp (C++) coexist; C++ requires build step | Always specify "use main.py (Python), not main.cpp" explicitly in agent prompts |

## Results & Parameters

### Host Assignments

| Host | IP | Role | Services |
| ------ | ---- | ------ | ---------- |
| hermes | 100.73.61.56 | Hub | NATS JetStream, Agamemnon (C++), Nestor (C++), Hermes bridge (Python), Prometheus, Loki, Grafana, argus-exporter |
| epimetheus | 100.92.173.32 | Remote worker | hello-myrmidon Python worker only |

### Topology Comparison

| Dimension | Old crosshost (`docker-compose.crosshost.yml`) | New hub+worker (`docker-compose.hermes-hub.yml`) |
| ----------- | ----------------------------------------------- | -------------------------------------------------- |
| epimetheus | Worker host (NATS, Agamemnon, most services) | Single remote worker (myrmidon only) |
| hermes | Control host (Nestor native binary) | Hub host (ALL services in compose) |
| NATS location | epimetheus | hermes |
| Nestor | Native binary on hermes | In compose on hermes |
| Primary use | Full distributed deployment | Validate worker dispatch specifically |

### Key Files

- `e2e/docker-compose.hermes-hub.yml` — compose overlay: disables hello-myrmidon via `profiles: ["disabled"]`
- `e2e/start-hermes-hub.sh` — SSH-driven launcher (hermes hub setup + epimetheus remote worker)
- `e2e/run-hermes-hub-e2e.sh` — 8-phase E2E validator
- `justfile` recipes: `hermes-hub-up`, `hermes-hub-test`, `hermes-hub-down`, `hermes-hub-logs`

### NATS Connection Validation Command

```bash
# From hermes or any Tailscale-connected host:
curl -s http://100.73.61.56:8222/varz | python3 -c "
import sys, json
d = json.load(sys.stdin)
conns = d.get('connections', 0)
print(f'NATS connections: {conns}')
assert conns >= 2, f'Expected >= 2 connections (Agamemnon + remote myrmidon), got {conns}'
print('OK: cross-host myrmidon connection confirmed')
"
```

### Related Skills

- `architecture-crosshost-nats-compose-deployment` — symmetric split: epimetheus=worker, hermes=Nestor native
- `crosshost-per-component-launcher-pattern` — per-component justfile launchers, any service on any host
- `e2e-crosshost-doctor-prerequisite-checker` — `just doctor` role-based prerequisite checker including firewalld/tailscale0 check
- `e2e-homeric-compose-cpp-pipeline` — base single-host compose E2E pipeline (v1.5.0)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | 2026-04-20 session implementing hermes-hub topology | Scripts written, reviewed, not yet executed end-to-end |
| Odysseus | 2026-04-27 Atlas first-run session on epimetheus | End-to-end validated: epimetheus + apollo + hermes myrmidon workers, 6 NATS connections at peak |
