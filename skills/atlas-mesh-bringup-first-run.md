---
name: atlas-mesh-bringup-first-run
description: "Patterns for bringing up the HomericIntelligence mesh natively or via containers across single or multiple Tailnet hosts from a cold state. Use when: (1) bringing up Agamemnon/Nestor/Hermes natively or via podman on any new host, (2) launching myrmidon workers across Tailnet hosts, (3) running the Atlas epic, (4) troubleshooting Agamemnon task completion API, (5) cold-starting the full 6-host Tailnet mesh."
category: architecture
date: 2026-05-03
version: "2.0.0"
user-invocable: false
verification: verified-local
history: atlas-mesh-bringup-first-run.history
tags:
  - atlas
  - mesh
  - bringup
  - nats
  - agamemnon
  - nestor
  - hermes
  - myrmidon
  - tailscale
  - multi-host
  - review-wave
  - binary-paths
  - podman
  - cold-start
  - pixi
---

# Atlas Mesh Bringup: First Run Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Bring up HomericIntelligence mesh natively or via containers across up to 6 Tailnet hosts from cold state; correct binary names, build flags, Hermes src-layout, and Agamemnon API shape |
| **Outcome** | Full 6-host mesh reachable at peak; Agamemnon API shape confirmed (team-scoped task path); echo-type task completion requires external PATCH |
| **Verification** | verified-local — executed end-to-end across 6 Tailnet hosts 2026-05-03 |
| **History** | [changelog](./atlas-mesh-bringup-first-run.history) |

## When to Use

- Bringing up Agamemnon, Nestor, or Hermes natively (binary/uvicorn) on any Tailnet host
- Building services via podman on hosts where Odysseus is not present
- Launching myrmidon Python workers on multiple Tailnet hosts (fan-out pattern)
- Running the Atlas epic implementation (issue #152) without the myrmidon-multi pipeline
- Troubleshooting Agamemnon review wave task completion API calls
- Cold-starting the full Tailnet mesh (all 6 hosts at once)
- Checking which Tailnet hosts are online/reachable before dispatch

## Verified Workflow

### Quick Reference — Native Mesh Bringup (single host with pixi)

```bash
# 1. Start NATS (binary NOT in PATH by default — use full path)
~/.local/bin/nats-server -js &
# Monitor at http://localhost:8222/varz (NOT port 4222)

# 2. Start Agamemnon — binary is ProjectAgamemnon_server (NOT agamemnon)
# Must build inside pixi to get correct compiler environment
pixi run bash -c "
  cd control/ProjectAgamemnon
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug \
    -DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF
  cmake --build build/debug
  ./build/debug/ProjectAgamemnon_server &
"

# 3. Start Nestor — binary is ProjectNestor_server (NOT nestor)
pixi run bash -c "
  cd control/ProjectNestor
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug
  cmake --build build/debug
  ./build/debug/ProjectNestor_server &
"

# 4. Start Hermes — src layout; must set PYTHONPATH=src
cd infrastructure/ProjectHermes
pixi run bash -c "PYTHONPATH=src uvicorn hermes.server:app --host 0.0.0.0 --port 8085" &

# 5. Verify all services respond
curl -s http://localhost:8080/health            # Agamemnon: {"service":"ProjectAgamemnon","status":"ok"}
curl -s http://localhost:8081/v1/health         # Nestor
curl -s http://localhost:8085/health            # Hermes
curl -s http://localhost:8222/varz | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('connections:', d['connections'])"
```

### Critical Binary Name Facts

```
CORRECT:  control/ProjectAgamemnon/build/debug/ProjectAgamemnon_server
WRONG:    control/ProjectAgamemnon/build/debug/agamemnon
WRONG:    control/ProjectAgamemnon/build/agamemnon

CORRECT:  control/ProjectNestor/build/debug/ProjectNestor_server
WRONG:    control/ProjectNestor/build/debug/nestor
WRONG:    control/ProjectNestor/build/nestor

CORRECT:  PYTHONPATH=src uvicorn hermes.server:app
WRONG:    uvicorn hermes.server:app  (no PYTHONPATH -- module not found)
WRONG:    uvicorn hermes.main:app    (module does not exist)
```

### NATS Binary Path and Ports

```bash
# NATS binary is NOT in PATH on most hosts
~/.local/bin/nats-server -js &     # Correct -- use full path

# NATS monitoring is on port 8222 (not 4222)
# 4222 is the client port for pub/sub
curl http://localhost:8222/varz     # server stats including connection count
curl http://localhost:8222/connz    # active connections
curl http://localhost:8222/jsz      # JetStream stats
```

### Multi-Host Cold-Start Strategy (6 Tailnet Hosts)

Before starting services, determine the correct method for each host:

| Host | Odysseus Present | Strategy | Special Notes |
| ------ | ---------------- | -------- | ------------- |
| titan, aeolus | No | Clone fresh via `gh repo clone`, build podman containers | Agamemnon container build ~5-10 min (Conan C++ deps) |
| artemis | Yes, pixi available | Native build inside `pixi run bash -c "..."` | Must use `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF`; Hermes needs `PYTHONPATH=src` |
| athena | No | Clone fresh, build via podman | Standard podman flow |
| hephaestus | No | Clone fresh, build natively | Nestor needs manual `-lz` link flag for OpenSSL zlib dep |
| apollo | No | Python 3.7 -- too old for Hermes (>=3.10) | Use docker with `--network=host` for all services |
| hermes, cleopatra | N/A | Tailscale-offline (not SSH-reachable) | Skip gracefully |

#### Podman Container Build (for hosts without Odysseus)

```bash
# Clone Odysseus first
gh repo clone HomericIntelligence/Odysseus ~/Odysseus
cd ~/Odysseus
git submodule update --init --recursive

# Build and start services as containers
podman build -t agamemnon control/ProjectAgamemnon/
podman build -t nestor control/ProjectNestor/
podman build -t hermes infrastructure/ProjectHermes/

podman run -d --name agamemnon --network=host agamemnon
podman run -d --name nestor --network=host nestor
podman run -d -e HERMES_PORT=8085 --name hermes --network=host hermes
```

**Hermes Dockerfile**: requires `prometheus_client` in pip install and `HERMES_PORT` defaulting to `8085` (not `8080` -- conflicts with Agamemnon). Fixed in PR #415.

#### Native Build on artemis (pixi available, clang-tidy sysroot issue)

```bash
# Must run cmake INSIDE pixi to get correct conda toolchain
pixi run bash -c "
  cd control/ProjectAgamemnon
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug \
    -DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF
  cmake --build build/debug -j$(nproc)
"
# Then start binary (exact name):
./control/ProjectAgamemnon/build/debug/ProjectAgamemnon_server
```

#### Native Build on hephaestus (OpenSSL zlib dep)

```bash
# Nestor requires explicit -lz for OpenSSL zlib dependency
pixi run bash -c "
  cd control/ProjectNestor
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_EXE_LINKER_FLAGS='-lz'
  cmake --build build/debug -j$(nproc)
"
```

### Agamemnon API Shape (Confirmed)

```bash
# Health check
curl -s http://localhost:8080/health
# Returns: {"service":"ProjectAgamemnon","status":"ok"}

# Create team (nested under "team" key)
TEAM_ID=$(curl -s -X POST http://localhost:8080/v1/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"my-team","description":"..."}' \
  | jq -r '.team.id')   # <-- .team.id, NOT .id

# Create task (team-scoped path -- NOT /v1/tasks)
curl -s -X POST "http://localhost:8080/v1/teams/$TEAM_ID/tasks" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-task","type":"echo","params":{}}'

# Transition task to completed (echo tasks need external PATCH)
curl -s -X PATCH "http://localhost:8080/v1/teams/$TEAM_ID/tasks/<task_id>" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}'
```

**Critical**: `echo`-type tasks have no autonomous executor -- they require an external PATCH to
transition to `completed`. The old `POST .../complete` endpoint returns 404.

### After NATS Restart: Restart Agamemnon and Nestor

Agamemnon and Nestor do NOT auto-reconnect to NATS reliably after a restart. Always kill and
restart them:

```bash
pkill -f ProjectAgamemnon_server || kill $(pgrep -f ProjectAgamemnon_server)
pkill -f ProjectNestor_server    || kill $(pgrep -f ProjectNestor_server)
# pkill may return exit code 144 in some environments -- use kill <pid> if needed
```

### Multi-Host Myrmidon Fan-Out

Launch hello-myrmidon Python workers on remote Tailnet hosts. Always use `main.py` (Python), not
`main.cpp` (C++).

```bash
# On each reachable remote host:
NATS_URL=nats://<controller-tailscale-ip>:4222 \
  nohup python3 provisioning/Myrmidons/hello-world/main.py \
  > /tmp/hello-myrmidon.log 2>&1 &
```

### Atlas Implementation: Use Direct Worktree (Not myrmidon-multi)

The `claude-myrmidon-multi.py` pipeline is NOT suitable for Atlas scaffold work. For Atlas epic
implementation:

1. Create a worktree directly from `main` (not from a feature branch)
2. Implement the scaffold with one agent in the worktree
3. Ensure `go.mod` uses `go 1.23.0` (not 1.22) -- templ v0.3.1001 requires Go 1.23
4. toolchain directive is `go1.24.2`

**Branch base rule**: Always fork from `main`. If the wrong base was used, cherry-pick the commit:

```bash
git checkout -b feat/issue-152-atlas-bootstrap-clean main
git cherry-pick <atlas-commit-sha>
git push --force-with-lease origin feat/issue-152-atlas-bootstrap-clean
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `agamemnon` as binary name | Called `./build/debug/agamemnon` | Binary is `ProjectAgamemnon_server` -- exact CMake target name | Always use `ProjectAgamemnon_server`; check `ls build/debug/` to confirm |
| `nestor` as binary name | Called `./build/debug/nestor` | Binary is `ProjectNestor_server` -- exact CMake target name | Always use `ProjectNestor_server` |
| `uvicorn hermes.server:app` without PYTHONPATH | Started Hermes without `PYTHONPATH=src` | Repo uses src layout -- Python cannot find `hermes` module | Always set `PYTHONPATH=src` before uvicorn in src-layout repos |
| `uvicorn hermes.main:app` | Used `hermes.main:app` as entry point | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` |
| cmake without pixi on artemis | Ran cmake directly without `pixi run bash -c` | pixi conda toolchain not activated; wrong sysroot used | Must run cmake inside `pixi run bash -c "..."` to get correct conda-managed compiler |
| cmake without `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` | Default cmake build on artemis | clang-tidy sysroot mismatch in pixi conda toolchain causes build failure | Always pass `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` on hosts with conda sysroot |
| `nats-server` without full path | Called bare `nats-server` on remote hosts | `~/.local/bin` not in PATH on most remote hosts | Always use `~/.local/bin/nats-server` with full path |
| NATS monitoring on port 4222 | Tried `curl localhost:4222/varz` | Port 4222 is the client port; monitoring HTTP is on 8222 | NATS monitoring: port 8222. Client pub/sub: port 4222 |
| `POST /v1/tasks` Agamemnon endpoint | Used flat `/v1/tasks` path | Returns 404 -- endpoint is team-scoped only | Correct endpoint: `POST /v1/teams/<teamId>/tasks` |
| `POST .../complete` task completion | Used `POST /v1/teams/<id>/tasks/<id>/complete` | Returns 404 -- endpoint does not exist | Use `PATCH /v1/teams/<id>/tasks/<id>` with `{"status":"completed"}` |
| `jq -r '.id'` on team create response | Extracted `.id` directly from team creation response | Team ID nested: `{"team": {"id": "..."}}` -- must use `.team.id` | Always use `.team.id`, not `.id` |
| `HERMES_PORT=8080` (default) | Used default port for Hermes container | Conflicts with Agamemnon on 8080 | Set `HERMES_PORT=8085` explicitly; Agamemnon owns 8080 |
| Hermes Dockerfile without `prometheus_client` | Built Hermes container without prometheus_client | Hermes imports it at startup; container crashes immediately | Fixed in PR #415: add `prometheus_client` to pip install in Dockerfile |
| docker uvicorn directly on apollo | Tried uvicorn directly on Python 3.7 host | Python 3.7 too old for Hermes (requires >=3.10) | Use `docker run --network=host` on hosts with Python <3.10 |
| Assuming Odysseus present on all hosts | Skipped `gh repo clone` step | Only 3/6 hosts had Odysseus; 3 needed fresh clone | Pre-check: `ls ~/Odysseus` -- clone if missing |
| Nestor without `-lz` on hephaestus | Standard cmake build for Nestor on hephaestus | OpenSSL zlib dep not automatically linked | Pass `-DCMAKE_EXE_LINKER_FLAGS='-lz'` explicitly on hephaestus |
| myrmidon-multi for Atlas scaffold | Tried `claude-myrmidon-multi.py` for Atlas file creation | Formula-driven pipeline; Atlas scaffold needs exact file content | Use direct worktree with single agent for precision scaffold work |
| Forking Atlas branch from feature branch | Created feat branch from `feat/issue-22-ci-hardening` | Picked up 12 extra CI commits; PR not rebased to main | Always fork from `main`; check base before `git worktree add` |
| `pkill -f "nats-server"` | Used pkill to stop NATS | Returns exit code 144 in some environments | Use `kill $(pgrep nats-server)` with explicit PID |

## Results & Parameters

### Host Reachability Matrix (2026-05-03 Cold-Start Session)

| Host | Tailscale Online | SSH | Odysseus Present | Method | Result |
| ------ | ---------------- | --- | ----------------- | ------ | ------ |
| titan | yes | yes | No | gh clone + podman | RUNNING |
| aeolus | yes | yes | No | gh clone + podman | RUNNING |
| artemis | yes | yes | Yes (pixi available) | native pixi build | RUNNING |
| athena | yes | yes | No | gh clone + podman | RUNNING |
| hephaestus | yes | yes | No | gh clone + native build (-lz) | RUNNING |
| apollo | yes | yes | No | docker (Python 3.7 host) | RUNNING |
| hermes | no | no | -- | Tailscale-offline | SKIPPED |
| cleopatra | no | no | -- | Tailscale-offline | SKIPPED |

### NATS Connection Count at 6-Service Peak

```
Agamemnon         -> 1 connection
Nestor            -> 1 connection
Hermes            -> 1 connection
titan myrmidon    -> 1 connection
aeolus myrmidon   -> 1 connection
artemis myrmidon  -> 1 connection
Total: 6 connections
```

Verify: `curl -s http://localhost:8222/varz | jq .connections`

### Agamemnon Health Response

```json
{"service": "ProjectAgamemnon", "status": "ok"}
```

### go.mod Requirements for Atlas (templ v0.3.1001)

```
go 1.23.0          # templ v0.3.1001 requires Go >= 1.23; "go 1.22" is rejected
toolchain go1.24.2 # matches the toolchain installed on the build host
```

### Session Metrics (2026-05-03 Cold-Start)

| Metric | Value |
| -------- | ------- |
| Hosts attempted | 8 |
| Hosts online (Tailscale) | 6 |
| Hosts successfully started | 6 |
| Hosts skipped (Tailscale-offline) | 2 (hermes, cleopatra) |
| Agamemnon container build time | ~5-10 min (Conan C++ deps) |
| Hermes PR #415 | Fixed prometheus_client + HERMES_PORT=8085 |

### Session Metrics (2026-04-27 First Run on epimetheus)

| Metric | Value |
| -------- | ------- |
| NATS connections at peak | 6 |
| Myrmidon workers launched | 3 (epimetheus local, apollo, hermes) |
| Hosts SSH-failed | 4 (titan, athena, cleopatra, artemis -- sshd disabled at time) |
| Review dimensions run | 6/6 |
| Review dimensions approved | 6/6 |
| Task completion via Agamemnon | 1/6 (5/6 returned 404 -- now fixed via PATCH) |
| Atlas PR | #173 on HomericIntelligence/Odysseus |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | Atlas epic implementation session 2026-04-27 | Native mesh bringup on epimetheus; 3-host myrmidon fan-out; PR #173 |
| HomericIntelligence/Odysseus | Full 6-host Tailnet cold-start session 2026-05-03 | 6 hosts started (4 podman, 1 native pixi, 1 docker); Agamemnon API shape confirmed; Hermes PR #415 |
