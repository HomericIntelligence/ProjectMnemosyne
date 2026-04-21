---
name: e2e-homeric-compose-cpp-pipeline
description: "Wire HomericIntelligence C++20 services into a podman/docker compose E2E stack with NATS JetStream, Prometheus, Grafana. Use when: (1) setting up the full E2E pipeline, (2) adding new C++20 services to the compose stack, (3) debugging multi-container C++ service orchestration, (4) troubleshooting podman vs docker runtime differences, (5) running on hosts without rootlessport or external internet access, (6) debugging Hermes webhook event type mapping (only task.updated/completed/failed/agent.* supported), (7) writing healthchecks compatible with podman-compose 1.5.0 and Docker Compose v2+v5 (use YAML string form — no array; Docker Compose v5 splits array elements on spaces)."
category: architecture
date: 2026-04-21
version: "1.6.0"
history: e2e-homeric-compose-cpp-pipeline.history
user-invocable: false
verification: verified-local
tags:
  - e2e
  - compose
  - podman
  - docker
  - cpp20
  - nats
  - prometheus
  - grafana
  - homeric-intelligence
  - dual-runtime
  - wsl2
  - host-network
  - grafana-analytics
---

# HomericIntelligence E2E Compose Pipeline (C++20 + NATS)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-21 |
| **Objective** | Wire all HomericIntelligence services into a dual-runtime (podman + docker) compose E2E stack for testing |
| **Outcome** | 10-container stack running on both podman compose and docker compose: NATS, Agamemnon (C++), Nestor (C++), Hermes (Python), hello-myrmidon (C++), Prometheus, Loki, Promtail, Grafana, argus-exporter. All 7 E2E phases passing on both runtimes. Host-network workaround documented for rootlessport-absent hosts. |
| **Verification** | verified-local |

## When to Use

- Setting up the HomericIntelligence E2E pipeline from scratch
- Adding a new C++20 service to the compose stack
- Debugging service-to-service communication in the HomericIntelligence mesh
- Understanding the architecture: what connects to what, on which ports
- Troubleshooting podman vs docker runtime differences
- Fixing WSL2-specific DNS or container networking issues
- Running on hosts without rootlessport (use host-network workaround below)
- Diagnosing Grafana startup hangs on low-IO or air-gapped hosts

## Verified Workflow

### Quick Reference

```bash
# WSL2 podman: kill stale aardvark-dns before fresh start
kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true

# Start the stack — works with both runtimes (from Odysseus root)
podman compose -f docker-compose.e2e.yml up -d --build
# OR
docker compose -f docker-compose.e2e.yml up -d --build

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
NATS (nats:alpine, :4222/:8222)  ← NOT nats:latest (distroless, no shell)
  ├── Agamemnon (C++20, :8080) — REST API, NATS pub/sub
  ├── Nestor (C++20, :8081) — Research stats, NATS pub
  ├── Hermes (Python/FastAPI, :8085) — Webhook→NATS bridge
  ├── hello-myrmidon (C++20) — NATS pull consumer
  └── argus-exporter (Python, :9100) — Scrapes Agamemnon + Nestor → Prometheus
          Uses AGAMEMNON_URL/NESTOR_URL (NOT MAESTRO_URL — ai-maestro removed per ADR-006)

Prometheus (:19090) ← scrapes argus-exporter
Loki (:13100) ← log aggregation
Promtail ← scrapes container logs → ships to Loki
Grafana (:13001) ← dashboards from Prometheus + Loki
```

### Host-Network Workaround (rootlessport absent)

When `rootlessport` is not installed on the host, bridge-networked containers start but never bind ports on the host — `start-stack.sh` will hang at `podman wait --condition=healthy`. Use `--network=host` for all containers instead:

```bash
# Kill stale aardvark-dns first (always safe to run)
kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true

# Start all services with host networking
podman run -d --name odysseus-nats-1 --network=host nats:alpine -js -m 8222
podman run -d --name odysseus-agamemnon-1 --network=host \
  -e NATS_URL=nats://localhost:4222 \
  localhost/odysseus-agamemnon:latest
# ... repeat for all services

# Grafana: MUST disable analytics to prevent startup hang on air-gapped/slow hosts
# (Grafana blocks at usagestats.collector HTTP call to grafana.net after ~16m of SQLite migrations)
podman run -d --name odysseus-grafana-1 --network=host \
  -e GF_ANALYTICS_REPORTING_ENABLED=false \
  -e GF_ANALYTICS_CHECK_FOR_UPDATES=false \
  -e GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  grafana/grafana:latest
```

**Important:** When using `--network=host`, provisioned datasources in Grafana must reference `localhost` rather than service names:
- `http://prometheus:9090` → `http://localhost:9090`
- `http://loki:3100` → `http://localhost:3100`

Add these env vars to the grafana service in `docker-compose.e2e.yml` for compose-based deployments on any host:
```yaml
environment:
  - GF_ANALYTICS_REPORTING_ENABLED=false
  - GF_ANALYTICS_CHECK_FOR_UPDATES=false
  - GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false
```

### Detailed Steps

1. C++20 services use multi-stage Dockerfiles: `ubuntu:24.04` builder → slim runtime
2. NATS uses `nats:alpine` (NOT `nats:latest` which is distroless) with `-js -m 8222` flags (JetStream + monitoring)
3. All services on `homeric-mesh` bridge network
4. Symlinked submodules need absolute paths in compose build contexts
5. argus-exporter needs a standalone Dockerfile (inline `dockerfile_inline` not supported by podman compose)
6. Port remapping needed if host ports are already bound (observability → 19090, 13001, 13100, 19100)
7. On WSL2 rootless podman: kill aardvark-dns PID before starting a fresh stack to avoid stale DNS mappings
8. Docker builds require `make` in apt-get install (gtest CMake recipe uses Unix Makefiles) and `conan profile detect --force` before `conan install`
9. argus-exporter uses `AGAMEMNON_URL`/`NESTOR_URL` with `/v1/agents`, `/v1/tasks`, `/v1/health` endpoints and `hi_*` metric prefix (ai-maestro removed per ADR-006)
10. Both `podman compose` and `docker compose` work with the same `docker-compose.e2e.yml` — no compose-file changes needed between runtimes

### C++20 Dockerfile Pattern

```dockerfile
FROM ubuntu:24.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build g++ git ca-certificates libssl-dev make python3-pip \
    && pip3 install --break-system-packages conan \
    && rm -rf /var/lib/apt/lists/*
# make is required — gtest's CMake recipe uses Unix Makefiles generator
# conan profile detect is required in fresh containers (no default profile exists)
RUN conan profile detect --force
WORKDIR /src
COPY CMakeLists.txt cmake/ include/ src/ test/ conanfile.py ./
RUN conan install . --output-folder=build --build=missing
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
| CMD-SHELL healthcheck on NATS (v1.0) | `test: ["CMD-SHELL", "wget ..."]` on `nats:latest` | NATS official `nats:latest` is scratch — no shell, no wget, no curl | Remove healthchecks for scratch images; use simple `depends_on` |
| nats:latest healthcheck (v1.3) | Used wget in CMD-SHELL healthcheck with `nats:latest` | `nats:latest` is distroless, no wget/shell available | Use `nats:alpine` for compose healthchecks — includes shell and wget |
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
| podman compose up after down (WSL2) | Ran `podman compose down && up` on WSL2 | aardvark-dns retained stale container-to-IP DNS records across runs | Kill aardvark-dns PID before fresh start: `kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid)` |
| Docker build without make | Built C++ Dockerfile in Docker | gtest CMake recipe needs `make` (Unix Makefiles generator) | Add `make` to `apt-get install` in Dockerfiles |
| Docker build without conan profile | Ran `conan install` in fresh Docker container | No Conan default profile exists in fresh containers | Run `conan profile detect --force` before `conan install` |
| argus-exporter with MAESTRO_URL | Started exporter pointing to ai-maestro on port 23000 | ai-maestro removed per ADR-006 — service doesn't exist | Migrate to `AGAMEMNON_URL`/`NESTOR_URL` with `/v1/agents`, `/v1/tasks`, `/v1/health` and `hi_*` prefix |
| Port mapping mismatch in start-stack.sh | start-stack.sh mapped argus-exporter to `-p 19100:9100` | Test script expected `:9100` matching compose file definition | Ensure start-stack.sh port mappings match compose file: `-p 9100:9100` |
| `start-stack.sh` hang at `podman wait --condition=healthy` (v1.4) | Called `podman wait --condition=healthy odysseus_nats_1` in start-stack.sh | rootlessport absent → NATS starts but never binds bridge-network ports → healthy condition never reached, wait blocks forever | Kill wait PID from a separate SSH session; switch all containers to `--network=host` |
| Grafana startup hang at `usagestats.collector` (v1.4) | Started Grafana without analytics env vars on epimetheus | After ~16m SQLite schema migrations, Grafana makes an external HTTP call to grafana.net; hosts without internet access or with slow links block indefinitely | Add `GF_ANALYTICS_REPORTING_ENABLED=false`, `GF_ANALYTICS_CHECK_FOR_UPDATES=false`, `GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false` to grafana service in `docker-compose.e2e.yml` |
| `run-hello-world.sh` Phase 3 event type `task.created` (v1.4) | Phase 3 sends `event: task.created` to Hermes webhook | Hermes `_TASK_EVENTS` only maps `task.updated`, `task.completed`, `task.failed`, `agent.*` — `task.created` is silently dropped, no NATS message published | Change Phase 3 test event to `task.updated` |
| IPC test runner T4 port override (v1.4) | `run-ipc-tests.sh --topology t4` used without patching process.sh | `process.sh` sourced unconditionally overwrites T4 ports with T1 non-standard ports (`AGAMEMNON_PORT=18080`, `NATS_MONITOR_PORT=18222`) — tests time out or target wrong ports | Topology-aware port selection: T4 must override to standard ports (8080, 8222) after sourcing `process.sh` |
| Grafana datasource hostnames in host-network mode (v1.4) | Provisioned datasources used service names (`http://prometheus:9090`, `http://loki:3100`) | With `--network=host`, service-name DNS does not resolve (no compose-managed bridge network) | Change datasource URLs to `http://localhost:9090` and `http://localhost:3100` for host-network deployments |
| `task.created` event to Hermes (v1.5) | Sent `task.created` webhook event to Hermes for Phase 3 test validation | Hermes `_TASK_EVENTS` only maps `task.updated`, `task.completed`, `task.failed`, `agent.*` — `task.created` is silently dropped with zero error and zero NATS message published | Always use `task.updated` for test webhook validation calls |
| `worker.py` in `start-myrmidon` recipe (v1.5) | Referenced `provisioning/Myrmidons/hello-world/worker.py` in justfile `start-myrmidon` recipe | File does not exist — the Python NATS JetStream subscriber worker is `main.py` | Use `main.py`; it subscribes to `hi.myrmidon.hello.>` via JetStream push consumer and publishes completion to `hi.tasks.{team_id}.{task_id}.completed` via core NATS |
| CMD-SHELL array in healthcheck (podman-compose 1.5.0) (v1.5) | Used `["CMD-SHELL", "wget ..."]` in `docker-compose.yml` healthcheck definitions | podman-compose 1.5.0 rejects the CMD-SHELL array format (Docker Compose accepts it) with a parse error | Use `["CMD", "sh", "-c", "wget ..."]` for dual-runtime compatibility |
| `["CMD","sh","-c","full cmd"]` healthcheck on Docker Compose v5 (v1.6) | Used JSON array form `["CMD", "sh", "-c", "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"]` for all service healthchecks | Docker Compose v5.x splits the 4th array element on spaces into separate exec args — `sh -c wget` runs wget binary alone (prints help, exit 1); does not pass the full string to `-c` | Switch all healthcheck `test:` values to YAML string form (no array); string form is treated as CMD-SHELL and passed verbatim to `sh -c`. Works on both v2 and v5. |
| `["CMD-SHELL","full cmd"]` array form on Docker Compose v5 (v1.6) | Tried CMD-SHELL array form as alternative to CMD array | Docker Compose v5 also splits CMD-SHELL array elements on spaces — confirmed via `podman inspect .Config.Healthcheck` showing tokenized args | Use plain string `test: "cmd"` (no array at all); Docker Compose treats it as CMD-SHELL without splitting |
| `wget -qO-` in nats:alpine healthcheck (v1.6) | Used combined short flag `-qO-` (stdout redirect) with BusyBox wget in nats:alpine | BusyBox wget does not support combined `-qO-`; prints usage text and exits 1 | Use `-q -O /dev/stdout` (space-separated, explicit path) for BusyBox wget |
| Prometheus scraping argus-exporter by hostname (v1.6) | `prometheus.yml` static config used `argus-exporter:9100` as scrape target | `start-stack.sh` restarts argus-exporter via `podman run --replace` (not compose), giving it a dynamic IP not registered in compose-managed DNS; Prometheus gets "no such host" | Generate `prometheus.runtime.yml` with resolved argus-exporter IP before compose up; after exporter starts, update runtime config with actual IP and reload Prometheus via `/-/reload` (requires `--web.enable-lifecycle` flag on Prometheus) |
| `podman cp` to overwrite read-only bind-mounted Prometheus config (v1.6) | Tried `podman cp prometheus.runtime.yml odysseus-prometheus-1:/etc/prometheus/prometheus.yml` | Volume is mounted `:ro` — copy fails with "device or resource busy"; also the bind source file on the host is authoritative anyway | Write the resolved-IP config to the host bind-mount source file (`prometheus.runtime.yml`), then trigger `/-/reload`; Prometheus re-reads from the host path |
| `just e2e-test` calling `start-stack.sh` while stack already up (v1.6) | Added `bash e2e/start-stack.sh` as first step of `e2e-test` recipe for DNS workaround; `start-stack.sh` ran `compose up -d` which tried to recreate containers already started by `podman run --replace` in a prior `e2e-up` | Docker Compose sees name conflicts on containers it no longer tracks (they were replaced by `podman run --replace`); `compose up` fails with "container name already in use" | Add idempotency guard at top of both `start-stack.sh` and Phase 1 of `run-hello-world.sh`: `if curl -sf http://localhost:8080/v1/health; then exit 0; fi` — skip bring-up if Agamemnon already healthy |

## Results & Parameters

```yaml
# E2E test results (28/28 passing, both runtimes)
# Verified: podman compose AND docker compose pass all 7 E2E phases
dual_runtime: true
runtimes_verified:
  - podman compose (rootless, WSL2)
  - docker compose (Docker Desktop / Docker CE)
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

# NATS image selection (v1.3.0)
nats_image: "nats:alpine"  # NOT nats:latest (distroless, no shell/wget/curl)
nats_healthcheck: |
  # Works with nats:alpine (has shell + wget)
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz || exit 1"]
    interval: 5s
    timeout: 3s
    retries: 5

# WSL2 podman aardvark-dns fix (v1.3.0)
aardvark_dns_fix: |
  # Kill stale aardvark-dns before starting a fresh stack on WSL2
  # aardvark-dns accumulates stale container-to-IP mappings across down/up cycles
  kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true

# Docker build requirements (v1.3.0)
docker_build_prereqs: |
  # In Dockerfile builder stage:
  # 1. Install make (gtest CMake recipe uses Unix Makefiles generator)
  RUN apt-get install -y make
  # 2. Create Conan default profile (doesn't exist in fresh containers)
  RUN conan profile detect --force
  # 3. Then run conan install
  RUN conan install . --output-folder=build --build=missing

# argus-exporter migration (v1.3.0 — ai-maestro removed per ADR-006)
argus_exporter: |
  # OLD (broken): MAESTRO_URL=http://ai-maestro:23000, /api/agents
  # NEW: AGAMEMNON_URL=http://agamemnon:8080, NESTOR_URL=http://nestor:8081
  # Endpoints: /v1/agents, /v1/tasks, /v1/health
  # Metric prefix: hi_* (e.g., hi_agamemnon_health, hi_nestor_health)

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

# Host-network workaround (v1.4.0 — rootlessport absent)
host_network_workaround: |
  # SYMPTOM: start-stack.sh hangs at `podman wait --condition=healthy`
  # ROOT CAUSE: rootlessport absent → bridge networking never binds host ports
  # FIX: use --network=host for ALL containers
  kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true
  podman run -d --name odysseus-nats-1 --network=host nats:alpine -js -m 8222
  # Add GF_ANALYTICS_* env vars to prevent Grafana blocking at usagestats.collector

# Grafana analytics env vars (v1.4.0)
grafana_analytics_fix: |
  # Add to grafana service in docker-compose.e2e.yml to prevent startup hang on air-gapped hosts
  # Grafana blocks ~indefinitely after SQLite migrations when grafana.net call times out
  environment:
    - GF_ANALYTICS_REPORTING_ENABLED=false
    - GF_ANALYTICS_CHECK_FOR_UPDATES=false
    - GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false

# Hermes event type mapping (v1.4.0, confirmed v1.5.0)
hermes_event_types: |
  # _TASK_EVENTS supported by Hermes webhook→NATS bridge (strict allowlist):
  #   task.updated, task.completed, task.failed, agent.*
  # NOT supported (silently dropped — no error, no NATS message): task.created
  # run-hello-world.sh Phase 3 must use event: task.updated
  # Valid event types: task.updated | task.completed | task.failed | agent.*

# hello-world myrmidon worker entrypoint (v1.5.0)
hello_world_myrmidon_worker: |
  # File: provisioning/Myrmidons/hello-world/main.py  (NOT worker.py — does not exist)
  # Subscribes to: hi.myrmidon.hello.>  (JetStream push consumer)
  # Publishes completion to: hi.tasks.{team_id}.{task_id}.completed  (core NATS)
  # justfile start-myrmidon recipe must reference main.py

# CMD array format for dual-runtime healthchecks (v1.5.0)
healthcheck_cmd_array: |
  # podman-compose 1.5.0 REJECTS CMD-SHELL array format; Docker Compose accepts it.
  # For dual-runtime compatibility, always use CMD+sh+-c form:
  #
  # WRONG (Docker only):
  #   test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz || exit 1"]
  #
  # CORRECT (dual-runtime):
  #   test: ["CMD", "sh", "-c", "wget -qO- http://localhost:8222/healthz || exit 1"]
  healthcheck:
    test: ["CMD", "sh", "-c", "wget -qO- http://localhost:PORT/healthz || exit 1"]
    interval: 5s
    timeout: 3s
    retries: 5

# IPC topology port selection (v1.4.0)
ipc_topology_ports: |
  # process.sh sets T1 non-standard ports (AGAMEMNON_PORT=18080, NATS_MONITOR_PORT=18222)
  # T4 topology requires standard ports — override AFTER sourcing process.sh:
  source process.sh
  if [ "$TOPOLOGY" = "t4" ]; then
    AGAMEMNON_PORT=8080
    NATS_MONITOR_PORT=8222
  fi

# Healthcheck string form — Docker Compose v2 + v5 compatible (v1.6.0)
healthcheck_string_form: |
  # Use YAML string (no array) — Docker Compose treats it as CMD-SHELL, passes verbatim to sh -c
  # Works on Docker Compose v2.x AND v5.x (v5 array splitting regression workaround)
  #
  # BROKEN on Docker Compose v5 (splits on spaces):
  #   test: ["CMD", "sh", "-c", "wget -qO- http://localhost:8080/v1/health || exit 1"]
  #   test: ["CMD-SHELL", "wget -qO- http://localhost:8080/v1/health || exit 1"]
  #
  # CORRECT (both versions):
  healthcheck:
    test: "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"
    interval: 5s
    timeout: 3s
    retries: 10
    start_period: 10s

# BusyBox wget for nats:alpine (v1.6.0)
busybox_wget_healthcheck: |
  # BusyBox wget (nats:alpine) rejects combined -qO- flag
  # Use -q -O /dev/stdout (space-separated, explicit path)
  healthcheck:
    test: "wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"
    interval: 5s
    timeout: 3s
    retries: 10
    start_period: 5s

# Prometheus IP patch for podman run --replace services (v1.6.0)
prometheus_ip_patch: |
  # start-stack.sh generates prometheus.runtime.yml before compose up,
  # then after argus-exporter starts via podman run --replace, resolves its IP
  # and hot-reloads Prometheus (requires --web.enable-lifecycle in compose)
  #
  # In docker-compose.e2e.yml:
  #   prometheus:
  #     command: ["--config.file=/etc/prometheus/prometheus.yml", "--web.enable-lifecycle"]
  #     volumes:
  #       - ${PROJECT_ROOT}/e2e/prometheus.runtime.yml:/etc/prometheus/prometheus.yml:ro
  #
  # In start-stack.sh (after podman run argus-exporter):
  cp "$ODYSSEUS_ROOT/e2e/prometheus.yml" "$ODYSSEUS_ROOT/e2e/prometheus.runtime.yml"
  # ... (compose up) ...
  ARGUS_IP=$(get_ip odysseus-argus-exporter-1)
  sed "s/argus-exporter:9100/${ARGUS_IP}:9100/g" \
    "$ODYSSEUS_ROOT/e2e/prometheus.yml" > "$ODYSSEUS_ROOT/e2e/prometheus.runtime.yml"
  curl -sf -X POST http://localhost:9090/-/reload

# Idempotency guard (v1.6.0)
idempotency_guard: |
  # Add to top of start-stack.sh and Phase 1 of run-hello-world.sh to prevent
  # double bring-up when e2e-test calls start-stack.sh while stack is already up
  if curl -sf http://localhost:8080/v1/health >/dev/null 2>&1; then
    echo "Stack already running — skipping bring-up."
    exit 0
  fi

# teardown orphan cleanup (v1.6.0)
teardown_orphan_cleanup: |
  # compose down does not track containers started by podman run --replace
  # teardown.sh must explicitly remove them:
  podman ps -a --filter name=odysseus --format '{{.Names}}' 2>/dev/null \
    | xargs -r podman rm -f 2>/dev/null || true
  podman network rm odysseus_homeric-mesh 2>/dev/null || true
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Full E2E pipeline on feat/cpp-skeleton branch | 9-container stack with C++20 Agamemnon, Nestor, hello-myrmidon |
| Odysseus | Dual-runtime E2E on fix/governance-compliance-files branch | 10-container stack passing all 7 phases on both podman compose and docker compose. WSL2 aardvark-dns workaround verified. |
| Odysseus | Host-network validation on epimetheus (SSH) | Validated host-network workaround on rootlessport-absent host. Grafana analytics hang, Hermes task.created drop, IPC T4 port override, and datasource hostname issues all confirmed and resolved. |
| Odysseus | 2026-04-21 | Full 8-phase E2E pass on Docker Compose v5.0.2 (snap) + podman 4.9.3, WSL2. PR #117. Healthcheck string form, BusyBox wget, Prometheus IP patch, and idempotency guards all verified. |
