---
name: architecture-homeric-ecosystem-ground-truth
description: "Map the actual implementation state of every HomericIntelligence component against documentation claims. Use when: (1) verifying what's real code vs aspirational docs, (2) planning deployment of the agent mesh, (3) assessing component readiness, (4) checking submodule pin freshness, (5) onboarding to the ecosystem."
category: architecture
date: 2026-04-03
version: 1.1.0
user-invocable: false
tags:
  - architecture
  - ecosystem
  - ground-truth
  - component-inventory
  - deployment-readiness
---

# Architecture: HomericIntelligence Ecosystem Ground Truth

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-03 |
| **Objective** | Map the actual state of every HomericIntelligence component — what's real code vs documentation claims |
| **Outcome** | Complete component readiness matrix distinguishing production-ready, needs-work, not-started, and not-relevant components |
| **Verification** | verified-local — verified by reading source code of every component |

## When to Use

- You need to know which HomericIntelligence components are real, deployable services vs libraries vs meta-repos
- Planning a deployment and need to know what actually works end-to-end
- Onboarding to the ecosystem and need ground truth, not aspirational architecture docs
- Checking whether a submodule pin in Odysseus matches the standalone checkout
- Assessing which components have NATS/REST integration vs which are standalone

## Component Ground Truth

### Agamemnon — Real C++20 Service

- **Type**: REST API server on port 8080
- **Endpoints**: `/v1/agents`, `/v1/teams`, `/v1/tasks`, `/v1/chaos/*`
- **Tech stack**: cpp-httplib, nats.c v3.9.1, nlohmann_json
- **Storage**: In-memory only (no persistence yet — issue #71)
- **NATS**: Creates 6 JetStream streams on startup: `homeric-agents`, `homeric-tasks`, `homeric-myrmidon`, `homeric-research`, `homeric-pipeline`, `homeric-logs`
- **Binary path**: `control/ProjectAgamemnon/build/debug/agamemnon` — NOT `build/agamemnon`
- **NATS reconnect**: Does NOT auto-reconnect after NATS restart — kill and restart Agamemnon
- **Status**: Production ready

### Nestor — Real C++20 Service

- **Type**: REST API server on port 8081
- **Endpoints**: `/v1/health`, `/v1/research/stats`, `POST /v1/research`
- **Tech stack**: Same as Agamemnon (cpp-httplib, nats.c, nlohmann_json)
- **Binary path**: `control/ProjectNestor/build/debug/nestor` — NOT `build/nestor`
- **NATS reconnect**: Does NOT auto-reconnect after NATS restart — kill and restart Nestor
- **Status**: Production ready

### Hermes — Production Python FastAPI

- **Type**: FastAPI service on port 8085
- **Endpoints**: `/health`, `POST /webhook`, `GET /subjects`
- **Security**: HMAC-SHA256 webhook validation
- **NATS**: Auto-creates JetStream streams
- **uvicorn entry point**: `hermes.server:app` — NOT `hermes.main:app` (that module does not exist)
- **Status**: Production ready

### Keystone — Library, NOT a Service

- **Type**: C++20 library providing MessageBus + ThreadPool + coroutines
- **Phases 1-3 complete**: 4-layer HMAS architecture
- **Phase 8 (gRPC)**: Optional, not required
- **Critical misconception**: Architecture docs describe Keystone as an invisible transport daemon. It is actually a library. Components connect to NATS directly via nats.c — Keystone's transport abstraction is aspirational.
- **BlazingMQ**: No binary exists anywhere in the ecosystem
- **Status**: Needs work (library exists, daemon does not)

### Odysseus — Meta-Repo, NOT a Service

- **Type**: Coordination repo with justfile commands + configs + ADRs
- **No HTTP server, no daemon**
- **The "user interface" role** is fulfilled by CLI commands and the odysseus-console NATS subscriber
- **Status**: Production ready (for what it is)

### Myrmidons — Two States

- **Submodule pin in Odysseus**: Was stale (targeting ai-maestro)
- **Standalone checkout**: Already migrated to Agamemnon
- **hello-myrmidon**: Python NATS pull consumer demonstrating the worker pattern
- **Status**: Needs work (submodule pin alignment)

### ProjectOdyssey — NOT Part of the Agent Mesh

- **Type**: Standalone Mojo ML training framework (~198K lines)
- **Zero NATS/REST integration**
- **"Agents" in that repo** refers to Claude Code automation, not distributed services
- **Critical misconception**: Architecture docs say "research sandbox graduates to AchaeanFleet" — but Odyssey has nothing to do with the agent mesh
- **Status**: Not relevant to mesh deployment

## Verified Workflow

### Auditing a Component

1. **Read actual source code**, not architecture docs or CLAUDE.md descriptions
2. **Check for HTTP server bindings** (cpp-httplib, FastAPI, etc.) to determine if it's a service
3. **Check for NATS connections** (nats.c, nats.py) to determine mesh integration
4. **Compare submodule pin** against standalone checkout (they can diverge after migrations)
5. **Verify port bindings** and endpoint paths against what other components expect

### Verifying Submodule Freshness

```bash
# Compare submodule pin in Odysseus vs standalone checkout
git -C ~/Odysseus/provisioning/Myrmidons log -1 --oneline
git -C ~/Myrmidons log -1 --oneline
# If they differ, the submodule pin is stale
```

### Checking What's Actually Deployed

```bash
# Check which services respond
curl -s http://localhost:8080/v1/agents  # Agamemnon
curl -s http://localhost:8081/v1/health  # Nestor
curl -s http://localhost:8085/health     # Hermes

# Check NATS streams
nats stream ls  # Should show homeric-agents, homeric-tasks, etc.

# Check NATS monitoring (port 8222, NOT 4222)
# 4222 = client pub/sub port; 8222 = HTTP monitoring port
curl -s http://localhost:8222/varz | jq '{connections, routes, num_subscriptions}'
curl -s http://localhost:8222/jsz   # JetStream stats
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assumed Myrmidons scripts target ai-maestro | Read submodule version of api.sh | Submodule was stale; standalone checkout was already migrated | Always check both submodule pin AND standalone checkout |
| Planned Keystone as transport daemon | Architecture docs describe Keystone as invisible transport | Keystone is a library with MessageBus, not a deployable service | Read actual source, not just architecture docs |
| Expected Odyssey to integrate with mesh | Architecture calls it "research sandbox graduates to AchaeanFleet" | It's a pure ML framework with zero NATS/REST code | ProjectOdyssey has nothing to do with the agent mesh |
| `uvicorn hermes.main:app` | Used `hermes.main:app` as Hermes entry point (2026-04-27) | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` for Hermes uvicorn launch |
| Binary at `build/agamemnon` | Looked for Agamemnon at `build/agamemnon` (2026-04-27) | Debug build lands in `build/debug/agamemnon` | C++ debug builds are in `build/debug/`, not `build/` root |
| NATS monitoring on port 4222 | `curl localhost:4222/varz` (2026-04-27) | Port 4222 is client port; monitoring is on 8222 | NATS monitoring: 8222. Client: 4222 |
| Agamemnon survives NATS restart | Expected Agamemnon to reconnect after NATS restart (2026-04-27) | Agamemnon and Nestor do not auto-reconnect reliably | After NATS restart, kill and restart Agamemnon + Nestor |

## Results & Parameters

### Component Readiness Matrix

```yaml
PRODUCTION_READY:
  - Agamemnon    # C++20 REST API, 6 JetStream streams, port 8080
  - Nestor       # C++20 REST API, port 8081
  - Hermes       # Python FastAPI, HMAC webhooks, port 8085
  - hello-myrmidon  # Python NATS pull consumer
  - Argus        # Observability stack
  - E2E compose  # Full pipeline validation

NEEDS_WORK:
  - Myrmidons          # Submodule pin stale after ai-maestro migration
  - NATS configs       # Leafnode port configuration
  - hi.logs.> pipeline # Only hello-myrmidon publishes

NOT_STARTED:
  - Keystone daemon    # Library exists, daemon does not
  - BlazingMQ          # No binary anywhere in ecosystem
  - Peer discovery     # Tailscale integration not implemented
  - GitHub Issues store # Agamemnon is in-memory only (issue #71)
  - Chaos injection    # API stubs only in Agamemnon /v1/chaos/*
  - Nomad scheduling   # Configs exist but not used

NOT_RELEVANT:
  - ProjectOdyssey     # Standalone Mojo ML framework, zero mesh integration
```

### Key Technical Facts

```yaml
ports:
  agamemnon: 8080
  nestor: 8081
  hermes: 8085

jetstream_streams:
  - homeric-agents
  - homeric-tasks
  - homeric-myrmidon
  - homeric-research
  - homeric-pipeline
  - homeric-logs

tech_stacks:
  agamemnon: [cpp-httplib, "nats.c v3.9.1", nlohmann_json]
  nestor: [cpp-httplib, "nats.c", nlohmann_json]
  hermes: [FastAPI, "nats.py", HMAC-SHA256]
  keystone: [MessageBus, ThreadPool, coroutines]
  hello-myrmidon: [Python, "nats.py", pull-consumer]
```

### Cross-Reference Commands

```bash
# Find all HTTP server bindings across ecosystem
grep -r "httplib\|FastAPI\|uvicorn\|app\.run" ~/Project*/src/ ~/Odysseus/

# Find all NATS connection strings
grep -r "nats://\|nats_connect\|NATS_URL\|nats.connect" ~/Project*/src/

# Find all JetStream stream creation
grep -r "JetStreamManager\|js_add_stream\|add_stream" ~/Project*/src/

# Verify port assignments don't conflict
grep -r "8080\|8081\|8085\|4222" ~/Project*/src/ ~/Odysseus/configs/
```
