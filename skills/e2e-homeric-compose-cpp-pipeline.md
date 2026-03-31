---
name: e2e-homeric-compose-cpp-pipeline
description: "Wire HomericIntelligence C++20 services into a podman compose E2E stack with NATS JetStream, Prometheus, Grafana. Use when: (1) setting up the full E2E pipeline, (2) adding new C++20 services to the compose stack, (3) debugging multi-container C++ service orchestration."
category: architecture
date: 2026-03-30
version: "1.2.0"
history: e2e-homeric-compose-cpp-pipeline.history
user-invocable: false
verification: verified-local
tags:
  - e2e
  - compose
  - podman
  - cpp20
  - nats
  - prometheus
  - grafana
  - homeric-intelligence
---

# HomericIntelligence E2E Compose Pipeline (C++20 + NATS)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Wire all HomericIntelligence services into a single podman compose stack for E2E testing |
| **Outcome** | 9-container stack running: NATS, Agamemnon (C++), Nestor (C++), Hermes (Python), hello-myrmidon (C++), Prometheus, Loki, Grafana, argus-exporter. 14/18 E2E checks passing. |
| **Verification** | verified-local |

## When to Use

- Setting up the HomericIntelligence E2E pipeline from scratch
- Adding a new C++20 service to the compose stack
- Debugging service-to-service communication in the HomericIntelligence mesh
- Understanding the architecture: what connects to what, on which ports

## Verified Workflow

### Quick Reference

```bash
# Start the stack (from Odysseus root)
podman compose -f docker-compose.e2e.yml up -d --build

# Run E2E test
just e2e-test

# Tear down
just e2e-down

# Check service health
curl localhost:8080/v1/health  # Agamemnon (C++)
curl localhost:8081/v1/health  # Nestor (C++)
curl localhost:8085/health     # Hermes (Python)
curl localhost:8222/healthz    # NATS
```

### Service Topology (10 containers)

```
NATS (nats:latest, :4222/:8222)
  ├── Agamemnon (C++20, :8080) — REST API, NATS pub/sub
  ├── Nestor (C++20, :8081) — Research stats, NATS pub
  ├── Hermes (Python/FastAPI, :8085) — Webhook→NATS bridge
  ├── hello-myrmidon (C++20) — NATS pull consumer
  └── argus-exporter (Python, :9100) — Scrapes all services → Prometheus

Prometheus (:19090) ← scrapes argus-exporter
Loki (:13100) ← log aggregation
Promtail ← scrapes container logs → ships to Loki
Grafana (:13001) ← dashboards from Prometheus + Loki
```

### Detailed Steps

1. C++20 services use multi-stage Dockerfiles: `ubuntu:24.04` builder → slim runtime
2. NATS uses official `nats:latest` image with `-js -m 8222` flags (JetStream + monitoring)
3. All services on `homeric-mesh` bridge network
4. Symlinked submodules need absolute paths in compose build contexts
5. argus-exporter needs a standalone Dockerfile (inline `dockerfile_inline` not supported by podman compose)
6. Port remapping needed if host ports are already bound (observability → 19090, 13001, 13100, 19100)

### C++20 Dockerfile Pattern

```dockerfile
FROM ubuntu:24.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build g++ git ca-certificates libssl-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt cmake/ include/ src/ test/ ./
RUN cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DProjectFoo_BUILD_TESTING=OFF \
    -DProjectFoo_ENABLE_CLANG_TIDY=OFF \
    -DProjectFoo_ENABLE_CPPCHECK=OFF \
    && cmake --build build --target ProjectFoo_server

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 wget && rm -rf /var/lib/apt/lists/*
COPY --from=builder /src/build/ProjectFoo_server /usr/local/bin/
EXPOSE 8080
ENV NATS_URL=nats://localhost:4222
CMD ["ProjectFoo_server"]
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Symlink build contexts | `context: ./infrastructure/ProjectHermes/` (symlink) | Podman compose can't follow symlinks for build contexts | Use absolute paths: `context: /home/user/ProjectHermes/` |
| `dockerfile_inline` in compose | Inline Dockerfile for argus-exporter | Podman's external compose provider doesn't support `dockerfile_inline` | Create a standalone Dockerfile and reference via `dockerfile:` key |
| CMD-SHELL healthcheck on NATS | `test: ["CMD-SHELL", "wget ..."]` | NATS official image is scratch — no shell, no wget, no curl | Remove healthchecks for scratch images; use simple `depends_on` |
| `depends_on: condition: service_healthy` | Wait for healthy NATS before starting services | Combined with NATS healthcheck failure, blocks all dependent containers | Use simple `depends_on` (start-order only) for scratch images |
| Same host ports as existing services | Ports 9090, 3100, 3001, 9100 | Zombie `rootlessport` processes from crashed containers hold ports | Remap to non-conflicting ports (19090, 13100, 13001, 19100) |
| Python stubs for Agamemnon/Nestor | FastAPI Python services as temporary implementation | Violates architecture constraint: all services must be C++/Mojo | Implement in C++20 with cpp-httplib + nlohmann-json + nats.c |
| Promtail docker_sd without socket | Promtail config uses `docker_sd_configs` but no socket mounted | "Cannot connect to the Docker daemon at unix:///var/run/podman/podman.sock" | Mount podman socket: `- /run/user/1000/podman/podman.sock:/var/run/podman/podman.sock:ro` |
| Using `podman compose up` alone | Expected DNS to work after compose up | Podman rootless DNS gateway mismatch — services can't resolve each other | Use `start-stack.sh` launcher: compose up → discover IPs → restart services with direct IPs |
| Hardcoded `/home/user/` paths in compose | Absolute paths for symlink build contexts | Breaks for any other developer or CI | Use `${PROJECT_ROOT}` env vars + `.env` file generated by `start-stack.sh` via `readlink -f` |
| Running containers as root | No `USER` directive in Dockerfiles | Security review flagged this as P1 | Add `RUN useradd -r -s /usr/sbin/nologin <service>` + `USER <service>` before CMD |
| Mixed `docker compose` / `podman compose` | Some justfile recipes used `docker compose` | Inconsistent — podman is the standard per ADR-001 | Use `podman compose` everywhere, remove all `docker compose` references |
| Hardcoded UID in podman socket path | `/run/user/1000/podman/podman.sock` | Breaks for non-1000 UIDs | Use `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock` via `.env` variable |
| Lambda `[&store]` capture in cpp-httplib | Reference to function parameter in route handler | cpp-httplib copies lambdas — reference dangles after `register_routes()` returns | Use `Store* sp = &store; [sp]` pointer capture pattern |

## Results & Parameters

```yaml
# E2E test results (28/28 passing)
passing:
  - All 4 service health checks (Agamemnon, Nestor, Hermes, NATS)
  - Webhook → Hermes → NATS accepted
  - Agent CRUD (create, by-name lookup, docker agent, start, list)
  - Team + Task + PUT update + Workflows endpoints
  - Myrmidon pull → process → publish completion → task marked completed
  - Nestor research POST + stats
  - 5 Prometheus hi_* metrics (agamemnon_health, nestor_health, agents, tasks, tasks_by_status)
  - NATS JetStream (3 connections, 480+ messages)
  - Grafana + Loki API responding
  - Chaos inject + list + remove (3 checks)

# Portability pattern (v1.2.0)
env_generation: |
  # In start-stack.sh / run-hello-world.sh — resolve symlinks for podman
  PROJECT_ROOT="$ODYSSEUS_ROOT"
  HERMES_DIR="$(readlink -f "$ODYSSEUS_ROOT/infrastructure/ProjectHermes")"
  ARGUS_DIR="$(readlink -f "$ODYSSEUS_ROOT/infrastructure/ProjectArgus")"
  MYRMIDONS_DIR="$(readlink -f "$ODYSSEUS_ROOT/provisioning/Myrmidons")"
  PODMAN_SOCK="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
  cat > "$ODYSSEUS_ROOT/.env" <<EOF
  PROJECT_ROOT=$PROJECT_ROOT
  HERMES_DIR=$HERMES_DIR
  ...
  EOF

# Non-root Dockerfile pattern
dockerfile_nonroot: |
  FROM ubuntu:24.04
  RUN useradd -r -s /usr/sbin/nologin myservice
  COPY --from=builder /src/build/myservice /usr/local/bin/
  USER myservice
  CMD ["myservice"]

# Container build times
agamemnon_build: ~90s (94 cmake targets)
nestor_build: ~70s (48 cmake targets)
myrmidon_build: ~60s (89 cmake targets)
hermes_build: ~15s (pip install)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Full E2E pipeline on feat/cpp-skeleton branch | 9-container stack with C++20 Agamemnon, Nestor, hello-myrmidon |
