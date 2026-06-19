---
name: homeric-crosshost-deployment-and-mesh-topology
description: "Deploy and operate the HomericIntelligence mesh across multiple Tailscale hosts using NATS JetStream, compose overlays, and justfile launchers. Use when: (1) splitting the E2E stack across multiple physical hosts via compose overlay or per-component launchers, (2) bringing up Agamemnon/Nestor/Hermes natively or via containers on any new Tailnet host from cold state, (3) running hub+remote-worker topology for cross-host myrmidon dispatch, (4) configuring NATS connections (direct or leafnode) over Tailscale, (5) implementing NATS JetStream publish retry with exponential backoff, (6) debugging Hermes webhook event types, compose healthchecks, or podman rootlessport/DNS quirks, (7) PLANNING credential-based authentication for a credential-less NATS leaf/server config and scrutinizing the uncertain assumptions a reviewer must verify in such a plan."
category: architecture
date: 2026-06-19
version: "1.2.0"
user-invocable: false
verification: unverified
history: homeric-crosshost-deployment-and-mesh-topology.history
tags:
  - cross-host
  - deployment
  - compose
  - tailscale
  - nats
  - jetstream
  - podman
  - docker
  - justfile
  - per-component
  - launcher
  - mesh
  - hermes
  - agamemnon
  - nestor
  - myrmidon
  - atlas
  - cold-start
  - retry
  - backoff
  - e2e
  - cpp20
  - homeric-intelligence
  - auth
  - authorization
  - credentials
  - leafnode
  - leaf-conf
  - server-conf
  - security
  - planning
  - reviewer-risks
  - adr
---

# HomericIntelligence Cross-Host Deployment and Mesh Topology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Deploy and operate the HomericIntelligence mesh across multiple Tailscale hosts using NATS JetStream, compose overlays, justfile launchers, and resilient publish patterns; and plan credential-based authentication for the credential-less NATS leaf/server config |
| **Outcome** | Deployment patterns verified-local (two-host + 6-host). The NATS leaf/server auth fix is still an UNVERIFIED PLAN for issue #176 (R1, post-NOGO) — the full plan was not run end-to-end and no CI passed. BUT the config-block-presence validator was PROTOTYPED this session (verified-local: exit 0 on the fixed fixture, exit 1 on the repo's current configs). The plan's highest-value content remains its catalogue of uncertain assumptions a reviewer must verify, now sharpened by concrete NOGO causes. |
| **Verification** | unverified OVERALL for the NATS auth-planning section (the full plan was not exercised end-to-end); the brace-depth config-block validator specifically is verified-local (prototyped 2026-06-19 against fixed + current fixtures). Verified-local for all prior deployment content (Odysseus sessions 2026-04-03 to 2026-05-03). |
| **History** | [changelog](./homeric-crosshost-deployment-and-mesh-topology.history) |

## When to Use

- Splitting the HomericIntelligence E2E compose stack across multiple physical machines
- Configuring NATS connections (direct or leafnode) over Tailscale mesh networking
- Bringing up Agamemnon, Nestor, or Hermes natively (binary/uvicorn) or via podman on any Tailnet host from cold state
- Launching myrmidon Python workers across Tailnet hosts (fan-out or hub+remote-worker pattern)
- Adding justfile recipes that launch C++ binaries or delegate to submodule justfiles
- Choosing between compose overlay vs native binary vs per-component launcher deployment
- Implementing NATS JetStream publish retry with exponential backoff and jitter in Python
- Debugging cross-host service communication, NATS leafnode config, or podman networking issues
- Planning credential-based authentication for the canonical credential-less `configs/nats/leaf.conf` + `server.conf` (issue #176) and reviewing such a plan for unverified assumptions

## Verified Workflow

### Quick Reference

```bash
# Compose overlay — start worker host
CONTROL_HOST_IP=<control-tailscale-ip> just crosshost-up $CONTROL_HOST_IP

# Compose overlay — start control host (Nestor native binary)
NATS_URL=nats://<worker-ip>:4222 <build-root>/ProjectNestor/ProjectNestor_server

# Per-component launchers (any host, any service)
just install-worker                                   # Worker: podman + tools
just install-control                                  # Control: C++ build chain + compile
just start-nats
just start-agamemnon NATS_URL=nats://worker-ip:4222
just start-nestor    NATS_URL=nats://worker-ip:4222
just start-hermes    NATS_URL=nats://worker-ip:4222
just start-myrmidon  NATS_URL=nats://worker-ip:4222 AGAMEMNON_URL=http://worker-ip:8080
just start-argus
just start-console   NATS_URL=nats://worker-ip:4222

# Hub+remote-worker topology (hermes=hub, epimetheus=remote worker)
just hermes-hub-up && just hermes-hub-test

# Single-host full E2E stack
podman compose -f docker-compose.e2e.yml up -d --build
just e2e-test

# Cross-host E2E validation (8 phases)
WORKER_HOST_IP=<worker-ip> just crosshost-test $WORKER_HOST_IP

# Verify NATS health
curl http://localhost:8222/varz    # monitoring (NOT port 4222)
curl http://localhost:8222/connz   # active connections
```

### Critical Binary Names and Paths

```
CORRECT:  control/ProjectAgamemnon/build/debug/ProjectAgamemnon_server
WRONG:    control/ProjectAgamemnon/build/debug/agamemnon

CORRECT:  control/ProjectNestor/build/debug/ProjectNestor_server
WRONG:    control/ProjectNestor/build/debug/nestor

CORRECT:  PYTHONPATH=src uvicorn hermes.server:app
WRONG:    uvicorn hermes.server:app     (no PYTHONPATH — module not found)
WRONG:    uvicorn hermes.main:app       (module does not exist)

CORRECT:  ~/.local/bin/nats-server -js  (use full path — not in PATH by default)
WRONG:    nats-server -js               (bare name, command not found on most hosts)

NATS:     port 4222 = client pub/sub;  port 8222 = HTTP monitoring
```

### Native Mesh Bringup (single host, pixi available)

```bash
# 1. NATS (binary NOT in PATH — use full path)
~/.local/bin/nats-server -js &

# 2. Agamemnon — build inside pixi for correct conda toolchain
pixi run bash -c "
  cd control/ProjectAgamemnon
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug \
    -DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF
  cmake --build build/debug
  ./build/debug/ProjectAgamemnon_server &
"

# 3. Nestor
pixi run bash -c "
  cd control/ProjectNestor
  cmake -B build/debug -DCMAKE_BUILD_TYPE=Debug
  cmake --build build/debug
  ./build/debug/ProjectNestor_server &
"

# 4. Hermes — src layout requires PYTHONPATH
cd infrastructure/ProjectHermes
pixi run bash -c "PYTHONPATH=src uvicorn hermes.server:app --host 0.0.0.0 --port 8085" &

# 5. Verify
curl -s http://localhost:8080/health    # {"service":"ProjectAgamemnon","status":"ok"}
curl -s http://localhost:8081/v1/health
curl -s http://localhost:8085/health
curl -s http://localhost:8222/varz | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('connections:', d['connections'])"
```

### Multi-Host Cold-Start Strategy (up to 6 Tailnet Hosts)

| Host | Odysseus Present | Strategy | Special Notes |
| ------ | ---------------- | -------- | ------------- |
| titan, aeolus, athena | No | `gh repo clone` + podman containers | Agamemnon build ~5-10 min (Conan C++ deps) |
| artemis | Yes, pixi available | Native build inside `pixi run bash -c "..."` | Must use `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` |
| hephaestus | No | Clone fresh, native build | Nestor needs `-DCMAKE_EXE_LINKER_FLAGS='-lz'` |
| apollo | No | Python 3.7 — too old for Hermes | Use `docker run --network=host` for all services |

**Pre-check**: `ls ~/<project-root>` — clone via `gh repo clone` if missing.

```bash
# Podman container build (hosts without native toolchain)
gh repo clone HomericIntelligence/Odysseus ~/<project-root>
cd ~/<project-root> && git submodule update --init --recursive
podman build -t agamemnon control/ProjectAgamemnon/
podman run -d --name agamemnon --network=host agamemnon
```

**Hermes Dockerfile**: requires `prometheus_client` in pip install; use `HERMES_PORT=8085` (not 8080 — conflicts with Agamemnon). Fixed in PR #415.

### Compose Overlay Pattern for Cross-Host Splits

```yaml
# docker-compose.crosshost.yml (overlay on docker-compose.e2e.yml)
services:
  nestor:
    profiles: ["disabled"]     # runs on control host as native binary
  argus-exporter:
    environment:
      - NESTOR_URL=http://${CONTROL_HOST_IP}:8081
```

```bash
podman compose -f docker-compose.e2e.yml -f docker-compose.crosshost.yml up -d
```

**Disable-via-overlay pattern**: `profiles: ["disabled"]` is the correct way to exclude a service from an overlay without removing it from the base compose file.

### NATS Connection Strategy: Direct vs. Leaf Node

| Topology | Recommended | Reason |
| ---------- | ------------- | -------- |
| 2 hosts, 1 remote client | Direct connection | Zero additional complexity; Tailscale handles routing |
| 2+ hosts, multiple remote clients | Leaf node | Reduces WAN connections; local pub/sub for co-located services |
| Hub-and-spoke (many remotes) | Leaf nodes per spoke | Each spoke gets local NATS; leaf auto-reconnects |

**Leafnode config — critical**: leaf.conf must connect to port **7422** (leafnode listen port), **NOT** port 4222 (client port).

```hcl
# server.conf (hub)
leafnodes { port = 7422 }

# leaf.conf (spoke)
leafnodes {
  remotes [{ url: "nats-leaf://<hub-ip>:7422" }]
}
```

## Proposed Workflow — Planning NATS Leaf/Server Auth (UNVERIFIED, issue #176)

> **Warning:** This section is an UNVERIFIED PLAN. No code was run, no CI passed,
> and the NATS version behaviors below were not exercised. Treat every step as a
> hypothesis until CI confirms. The highest-value content here is the
> reviewer-risk catalogue in **Results & Parameters** — read it before trusting any step.

The canonical `configs/nats/leaf.conf` and `configs/nats/server.conf` ship with NO
authentication: the `leafnodes {}` listener accepts anonymous leaf connections, so any
host that can reach port 7422 can join the mesh and relay traffic. This is the plan for
closing that hole. `configs/` is canonical — fixing it propagates to every host that
copies the config.

### Proposed Steps

1. **Add `authorization {}` to BOTH the client listener AND the `leafnodes {}` listener
   in `server.conf`.** A leafnode listener without its own authorization stays open even
   if the client listener is authed — they are independent. Do not assume top-level
   `authorization {}` covers the leafnode listener.
2. **Add a credential to each `leaf.conf` `remotes` entry.** Prefer
   `credentials = ".../leaf.creds"` (NKey/JWT, per-leaf, individually revocable). A
   `token = "$NATS_LEAF_TOKEN"` is an acceptable bootstrap fallback only. **Keep the URL
   on port 7422 — never 4222** (4222 is the client port; leaf remotes pointed at 4222
   silently fail to connect).
3. **Reference secrets via NATS env substitution** (`$NATS_LEAF_TOKEN`), mirroring the
   existing `$NATS_MONITORING_PASSWORD` pattern already in the configs. Never commit
   secret values.
4. **Treat `configs/` as canonical** — the fix lands once and propagates to every host
   that copies or symlinks the config.
5. **Enforce with a fail-closed lint wired into the EXISTING runner/CI gate.** This repo
   is `just` / `pixi`, **NOT** pytest. Add a shell validator invoked by
   `just validate-configs` (which CI must call). The gate **must strip comments before
   grepping** so a commented-out example does not satisfy the check, and it must assert
   per-block (the leafnode block has its own authorization) rather than file-wide.
6. **Auth is a NEW architectural decision → write a NEW append-only ADR (ADR-009).**
   Never edit an accepted ADR.

```hcl
# server.conf — PROPOSED (both listeners authed)
authorization {
  user = "$NATS_CLIENT_USER"
  password = "$NATS_CLIENT_PASSWORD"
}
leafnodes {
  port = 7422
  authorization {                 # leafnode listener needs its OWN block
    token = "$NATS_LEAF_TOKEN"     # or per-leaf user/account + .creds
  }
  tls { ... }                     # NOTE: nested block — see awk-parser risk below
}
```

```hcl
# leaf.conf — PROPOSED (authed remote, still port 7422)
leafnodes {
  remotes [
    {
      url: "nats-leaf://<hub-ip>:7422"
      credentials: "/etc/nats/creds/leaf.creds"   # preferred; revocable per-leaf
      # token: "$NATS_LEAF_TOKEN"                  # bootstrap fallback only
    }
  ]
}
```

### Canonical Config-Block-Presence Check — Brace-Depth Validator (verified-local, R1)

**This is the validated heart of the R1 plan.** The NOGO killed the first plan because its
validator stopped at the first `}` — which closes the nested `tls {}`, not the `leafnodes {}`
block. A config-block validator MUST track brace DEPTH (count `{` vs `}`), never stop at the
first close brace. Prototyped this session: exit 0 on the fixed fixture, exit 1 on the repo's
current (unauthed) `configs/nats/server.conf`.

```bash
#!/usr/bin/env bash
# validate-configs (wired into `just validate-configs`; CI must invoke it explicitly).
# Extract a named brace-block by DEPTH, stripping comments first, then assert auth inside it.
set -euo pipefail

# block FILE BLOCKNAME -> prints the contents of the first top-level BLOCKNAME { ... },
# tracking nested braces by depth so nested tls{}/jetstream{} do NOT close it early.
block() {
  local file="$1" name="$2"
  sed 's/#.*//' "$file" | awk -v blk="$name" '
    $0 ~ blk"[[:space:]]*\\{" && depth==0 { inblk=1 }
    inblk {
      n=gsub(/\{/,"{"); m=gsub(/\}/,"}");
      depth += n - m;
      print;
      if (depth<=0 && started) { inblk=0 }
      if (n>0) started=1
    }
  '
}

# Assert the leafnodes{} listener carries its OWN authorization{} (per-block, not file-wide).
if ! block configs/nats/server.conf leafnodes | grep -q 'authorization'; then
  echo "FAIL: server.conf leafnodes{} listener has no authorization{} block" >&2
  exit 1
fi
echo "OK: leafnodes listener is authenticated"
```

Verification discipline that makes this gate real (all learned from the NOGO):

```bash
# Assert BOTH directions — a validator that always exits 1 "passes" the bad-case check
# for the WRONG reason and silently rejects the FIX too.
./validate-configs                 # MUST exit 0 on the fixed config
git stash && ! ./validate-configs  # MUST exit 1 on the unfixed config
git stash pop

# Fail-closed must be TESTED, not asserted: render the config with the token UNSET and
# grep for the leaked literal. Install a pinned nats-server in CI and run it unconditionally
# — never gate the check on `command -v nats-server` (that turns it into a silent no-op).
NATS_LEAF_TOKEN= nats-server -t -c configs/nats/server.conf 2>&1 \
  | grep -q '\$NATS_LEAF_TOKEN' && { echo "FAIL: unset token leaked as literal"; exit 1; }
```

### Agamemnon API Shape (Confirmed)

```bash
# Health
curl -s http://localhost:8080/health
# Returns: {"service":"ProjectAgamemnon","status":"ok"}

# Create team — response wraps ID under .team.id
TEAM_ID=$(curl -s -X POST http://localhost:8080/v1/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"my-team","description":"..."}' \
  | jq -r '.team.id')   # NOT .id

# Create task — team-scoped path (NOT /v1/tasks)
curl -s -X POST "http://localhost:8080/v1/teams/$TEAM_ID/tasks" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-task","type":"echo","params":{}}'

# Complete task — echo tasks require external PATCH (no autonomous executor)
curl -s -X PATCH "http://localhost:8080/v1/teams/$TEAM_ID/tasks/<task_id>" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}'
```

### Multi-Host Myrmidon Fan-Out

```bash
# On each reachable remote host — always use main.py (Python), NOT main.cpp
NATS_URL=nats://<controller-tailscale-ip>:4222 \
  nohup python3 provisioning/Myrmidons/hello-world/main.py \
  > /tmp/hello-myrmidon.log 2>&1 &

# Verify cross-host NATS connection count
curl -s http://<hub-ip>:8222/varz | jq .connections
```

### NATS JetStream Publish Retry with Exponential Backoff

```python
import asyncio, json, random, time, nats

_RETRYABLE_PUBLISH_ERRORS = (
    nats.errors.TimeoutError,
    nats.errors.NoRespondersError,
    nats.errors.DrainTimeoutError,
    nats.errors.ConnectionReconnectingError,
    nats.errors.StaleConnectionError,
)

async def publish_with_retry(js, subject, message, retries=3, base_delay=0.1, timeout=5.0):
    last_exc = None
    for attempt in range(retries):
        try:
            return await js.publish(subject, message, timeout=timeout)
        except _RETRYABLE_PUBLISH_ERRORS as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = min(base_delay * (2 ** attempt), 2.0) * random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
    raise last_exc
```

Retry budget defaults (`retries=3`, `base_delay=0.1s`, `timeout=5.0s`): ~15.3s worst case.
Non-retryable errors (`AuthorizationError`, `BadSubjectError`, generic `Exception`) propagate immediately.

### Host-Network Workaround (rootlessport absent)

```bash
# SYMPTOM: start-stack.sh hangs at `podman wait --condition=healthy`
# ROOT CAUSE: rootlessport absent — bridge networking never binds host ports
kill $(cat /run/user/$(id -u)/containers/networks/aardvark-dns/aardvark.pid 2>/dev/null) 2>/dev/null || true
podman run -d --name hi-nats --network=host nats:alpine -js -m 8222
# When using --network=host, Grafana datasources must use localhost, not service names
```

**Grafana on air-gapped hosts** — add to grafana service to prevent startup hang:

```yaml
environment:
  - GF_ANALYTICS_REPORTING_ENABLED=false
  - GF_ANALYTICS_CHECK_FOR_UPDATES=false
  - GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false
```

### Compose Healthchecks (Dual-Runtime: podman-compose 1.5.0 + Docker Compose v2/v5)

```yaml
# CORRECT — YAML string form; Docker Compose v2 and v5 both treat it as CMD-SHELL
healthcheck:
  test: "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"
  interval: 5s
  timeout: 3s
  retries: 10
  start_period: 10s

# For nats:alpine (BusyBox wget rejects combined -qO- flag)
healthcheck:
  test: "wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"
```

### After NATS Restart

Agamemnon and Nestor do NOT auto-reconnect after NATS restarts. Always kill and restart them:

```bash
pkill -f ProjectAgamemnon_server || kill $(pgrep -f ProjectAgamemnon_server)
pkill -f ProjectNestor_server    || kill $(pgrep -f ProjectNestor_server)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Leaf.conf to port 4222 | Connected leaf node to NATS client port | Leaf nodes require dedicated leafnode listener port 7422 | Always use port 7422 for leafnode remotes, not 4222 |
| `agamemnon` as binary name | Called `./build/debug/agamemnon` | Binary is `ProjectAgamemnon_server` — exact CMake target name | Check `ls build/debug/` to confirm binary name |
| `nestor` as binary name | Called `./build/debug/nestor` | Binary is `ProjectNestor_server` — exact CMake target name | Always use `ProjectNestor_server` |
| Hermes without PYTHONPATH | `uvicorn hermes.server:app` with no env prefix | src layout — Python cannot find `hermes` module | Always prefix `PYTHONPATH=src` |
| `uvicorn hermes.main:app` | Used `hermes.main:app` entry point | Module is `hermes.server:app`; `hermes.main` does not exist | Always use `hermes.server:app` |
| `nats-server` without full path | Called bare `nats-server` | `~/.local/bin` not in PATH on most remote hosts | Always use `~/.local/bin/nats-server` |
| NATS monitoring on port 4222 | `curl localhost:4222/varz` | Port 4222 is client port; monitoring HTTP is on 8222 | NATS monitoring: port 8222; client pub/sub: port 4222 |
| NATS via podman (slirp4netns) | Podman container NATS without rootlessport | slirp4netns remaps 4222 to ephemeral port invisible to external clients | Run NATS as native binary when rootlessport absent |
| cmake without pixi on artemis | Ran cmake directly without `pixi run bash -c` | pixi conda toolchain not activated; wrong sysroot | Run cmake inside `pixi run bash -c "..."` |
| cmake without `_ENABLE_CLANG_TIDY=OFF` | Default cmake on artemis | clang-tidy sysroot mismatch causes build failure | Always pass `-DProjectAgamemnon_ENABLE_CLANG_TIDY=OFF` on conda sysroot hosts |
| Nestor without `-lz` on hephaestus | Standard cmake for Nestor | OpenSSL zlib dep not automatically linked | Pass `-DCMAKE_EXE_LINKER_FLAGS='-lz'` on hephaestus |
| `POST /v1/tasks` Agamemnon | Used flat `/v1/tasks` path | Returns 404 — endpoint is team-scoped only | Correct: `POST /v1/teams/<teamId>/tasks` |
| `POST .../complete` task completion | Used POST complete endpoint | Returns 404 — endpoint does not exist | Use `PATCH /v1/teams/<id>/tasks/<id>` with `{"status":"completed"}` |
| `jq -r '.id'` on team response | Extracted `.id` directly | Team ID is nested: `{"team": {"id": "..."}}` | Always use `.team.id` |
| Hermes with `HERMES_PORT=8080` | Default port for Hermes container | Conflicts with Agamemnon on 8080 | Set `HERMES_PORT=8085`; Agamemnon owns 8080 |
| Hermes Dockerfile without `prometheus_client` | Built without prometheus_client | Hermes imports it at startup; container crashes | Add `prometheus_client` to pip install (PR #415) |
| hello-myrmidon `main.cpp` | Used C++ file in hello-world | Requires build step; Python `main.py` is the worker | Always use `main.py`; it subscribes via JetStream push consumer |
| `worker.py` in start-myrmidon recipe | Referenced non-existent worker.py | File does not exist — correct file is `main.py` | Use `main.py`; subscribes to `hi.myrmidon.hello.>` |
| `task.created` to Hermes webhook | Sent `task.created` event | Hermes `_TASK_EVENTS` allowlist: `task.updated`, `task.completed`, `task.failed`, `agent.*` only — silently dropped | Always use `task.updated` for test webhook validation |
| Submodule scripts as-is | Used provisioning/Myrmidons scripts | Submodule pinned to old commit with `aim_*` functions targeting ai-maestro | Verify submodule pins match standalone checkouts after migrations |
| Monolithic e2e-all launcher | Single `just e2e-all` starts everything | Defeats multi-machine flexibility; per-component granularity needed | Individual launchers compose better for distributed deployment |
| `nats:latest` for healthchecks | Used `nats:latest` container | `nats:latest` is distroless — no shell, wget, or curl | Use `nats:alpine` for compose healthchecks |
| CMD-SHELL array healthcheck on podman-compose 1.5.0 | `["CMD-SHELL", "wget ..."]` format | podman-compose 1.5.0 rejects this array format | Use `["CMD", "sh", "-c", "wget ..."]` or YAML string form |
| CMD/CMD-SHELL array on Docker Compose v5 | JSON array `["CMD","sh","-c","full cmd"]` | Docker Compose v5 splits 4th element on spaces — `sh -c wget` runs wget alone | Use YAML string `test: "cmd"` — both v2 and v5 treat it as CMD-SHELL without splitting |
| `wget -qO-` in nats:alpine | Combined short flag with BusyBox wget | BusyBox wget rejects `-qO-`; prints usage and exits 1 | Use `-q -O /dev/stdout` (space-separated, explicit path) |
| Sleeping after final retry attempt | `if attempt < retries` guard | Adds unnecessary latency after retries exhausted | Guard with `if attempt < retries - 1` |
| Catching bare `Exception` in retry | Catch-all in retry loop | Hides non-retryable bugs as transient failures; burns retry budget | Only catch explicit `_RETRYABLE_PUBLISH_ERRORS` tuple |
| No restart after NATS port change | Left Agamemnon/Hermes running | Processes lose NATS connection and do not auto-reconnect | Restart both services after NATS is stable |
| Assuming Odysseus present on all hosts | Skipped `gh repo clone` step | Only some hosts had a clone; others needed fresh clone | Pre-check `ls ~/<project-root>` — clone if missing |
| `podman cp` to overwrite read-only bind-mount | Tried `podman cp` on `:ro` Prometheus config | Volume is `:ro` — copy fails with "device or resource busy" | Write resolved-IP config to host bind-mount source, then `/-/reload` |
| Forking Atlas branch from feature branch | Created feat branch from `feat/issue-22-ci-hardening` | Picked up 12 extra CI commits; PR not rebased to main | Always fork from `main`; check base before `git worktree add` |
| Leaf remote on port 4222 (auth fix) | Pointing `remotes.url` at the client port while adding creds | Leaf nodes silently never connect | Leaf remotes MUST use 7422, even when adding auth |
| Auth only on client listener | Adding `authorization{}` only at the top level of `server.conf` | The `leafnodes{}` listener stays open — anonymous leaf relay still works | The leafnode listener needs its OWN `authorization` block |
| `sensitive = true` in Nomad var | Terraform-ism to hide NATS creds in a Nomad variable | Nomad parse error: "argument named 'sensitive' is not expected" | Don't secure NATS creds via Nomad `sensitive` vars |
| Naive grep gate | `grep` for `token` without stripping comments | A commented-out example passes the check (false-negative) | Strip comments before asserting presence; assert per-block, not file-wide |
| Assuming pytest exists | Planning a pytest-based regression test for the config | Odysseus has no pytest; tasks are `just`-backed | Wire gates into the existing `just` / CI runner |
| awk parser that ends block on first `}` | Validate leafnodes auth by scanning until the first `}` | Nested `tls{}` inside `leafnodes{}` closes first — parser declared a CORRECTLY-authed config unauthenticated; exited 1 on BOTH fixed and broken configs | A config-block validator MUST track brace DEPTH (count `{` vs `}`), not stop at the first `}`. Nested blocks are the norm in NATS/HCL-style configs |
| Verification that only checks the broken case | `git stash && ! validator && echo PASS` | A validator that always exits 1 "passes" this check for the wrong reason — masks that it also rejects the FIX | Always assert BOTH directions: exit 1 on the unfixed config AND exit 0 on the fixed config. A regression gate that can't accept the fix is broken |
| Assuming a recipe wired into justfile runs in CI | Claimed validator "already runs on pull_request via ci.yml" | `ci.yml`'s validate job inlines its own steps and never invokes `just validate-configs`/`pixi run validate` | Don't assume CI calls your `just` recipe — READ the workflow. Add an explicit CI step (or confirm the recipe is invoked) or the gate doesn't exist |
| Parse check gated on `command -v nats-server` | `command -v nats-server && nats-server -t ... \|\| echo skipped` | The tool is absent in CI, so the check silently skips — the fail-closed assumption is never actually tested | If a verification matters, INSTALL the tool in CI (pinned release) and run it unconditionally; a `command -v ... \|\|` guard turns the check into a no-op |
| Asserting `.gitignore` coverage from a pattern | Claimed `/etc/nats/certs/` was already git-ignored | `grep -n "certs\|creds\|nats" .gitignore` → no matches; the claim was fabricated from the certs convention | Grep the actual file before claiming a path is ignored. "It follows the convention" is not evidence the entry exists |

## Results & Parameters

```yaml
# Service ports
services:
  nats:    client=4222, monitoring=8222
  agamemnon: 8080
  nestor:    8081
  hermes:    8085  # NOT 8080 -- conflicts with Agamemnon
  prometheus: 9090 (or 19090 if conflicting)
  grafana:   3001 (or 13001)
  loki:      3100 (or 13100)
  argus-exporter: 9100

# Key environment variables
env_vars:
  NATS_URL:         "nats://<worker_ip>:4222"
  AGAMEMNON_URL:    "http://<worker_ip>:8080"
  NESTOR_URL:       "http://<control_ip>:8081"
  CONTROL_HOST_IP:  "<Tailscale IP of the control host>"
  WORKER_HOST_IP:   "<Tailscale IP of the worker host>"
  PYTHONPATH:       "src"   # required for Hermes

# NATS publish retry defaults (Python/nats-py)
nats_publish_retry:
  retries: 3
  base_delay: 0.1s          # doubles each attempt; cap at 2.0s
  jitter: "uniform(0.5, 1.5)"
  publish_timeout: 5.0s
  worst_case_total: ~15.3s

# Hermes supported webhook event types (_TASK_EVENTS allowlist)
hermes_event_types:
  - task.updated
  - task.completed
  - task.failed
  - "agent.*"
  # NOT supported (silently dropped): task.created

# Justfile recipes (per-component launchers)
recipes:
  install-worker:   "e2e/doctor.sh --role worker --install + submodule init"
  install-control:  "e2e/doctor.sh --role control --install + build Agamemnon/Nestor"
  start-nats:       "podman run -d --replace nats:alpine -js -m 8222"
  start-agamemnon:  "NATS_URL=... <build-root>/ProjectAgamemnon/ProjectAgamemnon_server"
  start-nestor:     "NATS_URL=... <build-root>/ProjectNestor/ProjectNestor_server"
  start-hermes:     "delegates to infrastructure/ProjectHermes justfile"
  start-myrmidon:   "NATS_URL=... python3 provisioning/Myrmidons/hello-world/main.py"
  start-argus:      "delegates to infrastructure/ProjectArgus justfile"
  start-console:    "python3 tools/odysseus-console.py"
```

### Uncertain Assumptions a Reviewer MUST Verify (NATS auth plan, issue #176)

This is the core value of the planning learning. A plan for NATS leaf/server auth in this
ecosystem is only as trustworthy as these unverified claims. A reviewer should treat each as
a blocking question, not a settled fact.

1. **Env-var substitution in `authorization { token = "$NATS_LEAF_TOKEN" }` — fail-closed is now
   TESTED, not assumed (R1 downgrade).** Previously the HIGHEST-RISK untested assumption; R1 adds a
   pinned `nats-server -t -c server.conf` run with the var UNSET that greps the rendered config for
   the leaked literal `$NATS_LEAF_TOKEN`. With that CI step the fail-closed behavior is verified, not
   hoped for. The residual risk is keeping that pinned check unconditional (never gate it on
   `command -v nats-server`) so it can't silently skip.
2. **Whether one shared token across client + all leaf nodes is acceptable** vs per-leaf
   `.creds`. A shared token is a shared secret with no per-leaf revocation. The plan documents
   `.creds` as recommended but ships a token fallback; the reviewer must confirm the bootstrap
   token is not silently becoming the permanent posture.
3. **The awk leafnode-block parser brittleness is RESOLVED in R1 by the brace-depth validator.**
   The original NOGO cause: a parser that ends the block on the first `}` closes the nested
   `tls {}`, not `leafnodes {}`, mis-declaring auth. R1 replaces it with the depth-tracking
   `block()` helper (counts `{` vs `}`, strips comments) prototyped this session — exit 0 on the
   fixed fixture, exit 1 on the current configs. Reviewer residual: confirm the validator is run in
   BOTH directions (rejects the bad config AND accepts the fix), never just the bad case.
4. **Cited line numbers may have drifted.** `server.conf:27-34`, `leaf.conf:34-37`,
   `justfile:258-266`, `ci.yml:11-55`, `deployment.md:152-161` were read once. Re-confirm each
   before editing.
5. **ADR-008 Status is "Proposed", not "Accepted".** The plan builds ADR-009 on top of an
   unaccepted ADR. Confirm the sequencing/numbering is still valid.
6. **`.gitignore` coverage of `.creds`/`certs` was FABRICATED in R0 — confirmed absent in R1.**
   `grep -n "certs\|creds\|nats" .gitignore` returns no matches; the R0 claim that the convention
   already ignored these paths was invented. The plan must ADD the `.gitignore` entries, not assume
   them. Lesson: grep the actual file before claiming a path is ignored.
7. **`just validate-configs` running in CI on `pull_request` was FALSE — confirmed in R1.**
   `ci.yml`'s validate job inlines its own steps and never invokes `just validate-configs` /
   `pixi run validate`. The gate does not exist until an explicit CI step is added (or the workflow
   is changed to call the recipe). Read `ci.yml` end-to-end; do not infer the invocation graph.
8. **Shared-token-vs-per-leaf-`.creds` posture risk REMAINS (R1, unresolved).** The plan still
   ships a `token` bootstrap fallback alongside the recommended per-leaf `.creds`. A shared token is
   a shared secret with no per-leaf revocation; the reviewer must confirm the bootstrap token is not
   silently becoming the permanent posture. This is the one reviewer-risk item the R1 prototype did
   NOT retire.

### Reviewer-risk + Meta-Lessons (planning learnings from the NOGO, R1)

These are the durable PLANNING lessons the NOGO cycle taught — independent of NATS specifics.

- **The single most valuable planning move was PROTOTYPING the validator before shipping the
  plan.** Running the brace-depth `block()` extractor against fixed + current fixtures turned "I
  think this works" into "exit 0 vs exit 1, verified." Plans that ship unvalidated shell/awk get
  NOGO'd on latent traps (here: the nested-`tls{}` brace).
- **Verify the CI invocation graph, not just file existence.** A gate wired into a `just` recipe is
  invisible to CI unless the workflow actually calls that recipe. Read `ci.yml` end-to-end.
- **Every line-number citation drifts.** The NOGO flagged `:27-39` vs the actual `:27-40`. Re-grep
  before citing; precision claims invite precision checks.
- **Fail-closed must be TESTED, not asserted.** The highest-risk assumption (unset
  `$NATS_LEAF_TOKEN` resolves empty, not to the literal string) only became believable once a pinned
  `nats-server -t` run was added that greps the rendered config for a leaked literal.
- **Negative-path verification needs BOTH directions.** Asserting only "rejects the bad config"
  hides a validator that rejects everything — including the fix. Assert exit 1 on broken AND exit 0
  on fixed.

```yaml
# PROPOSED NATS auth env vars (mirror existing $NATS_MONITORING_PASSWORD pattern)
nats_auth_env_vars:
  NATS_LEAF_TOKEN:        "$ENV — bootstrap fallback only; MUST fail closed if unset"
  NATS_CLIENT_USER:       "$ENV"
  NATS_CLIENT_PASSWORD:   "$ENV"
  # Preferred over token: per-leaf NKey/JWT .creds at /etc/nats/creds/leaf.creds (revocable)

# PROPOSED fail-closed lint (shell, wired into `just validate-configs`, NOT pytest)
config_auth_gate:
  runner: "just validate-configs — MUST be invoked by an EXPLICIT ci.yml step"
  ci_invocation: "ci.yml inlines its own steps; it does NOT call the recipe today — add the step"
  must_strip_comments_before_grep: true     # else a commented example passes
  brace_depth_extraction: true              # block() counts {/} — nested tls{} must not close early
  assert_per_block: true                    # leafnodes{} needs its own authorization{}
  assert_both_directions: true              # exit 1 on broken config AND exit 0 on the fix
  fail_closed_test: "NATS_LEAF_TOKEN= nats-server -t -c server.conf | grep -q '$NATS_LEAF_TOKEN'"
  nats_server_in_ci: "pinned release, run UNCONDITIONALLY (never `command -v` guard)"
  ports:
    leaf_remote: 7422                        # never 4222
  adr: "new ADR-009 (append-only); never edit accepted ADRs"
  validator_status: "prototyped verified-local: exit 0 on fixed fixture, exit 1 on current configs"
```

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | 2026-04-03 Cross-host compose overlay | Two-host deployment: epimetheus (worker) + control host; full 6-phase validation PASS 2026-04-06 |
| HomericIntelligence/Odysseus | 2026-04-04 Per-component launchers | 9 justfile recipes; commit 82742b7 on feat/crosshost-e2e-pipeline |
| HomericIntelligence/Odysseus | 2026-04-20 Hermes-hub topology | Hub+remote-worker scripts written; validated 2026-04-27 in Atlas session |
| HomericIntelligence/Odysseus | 2026-04-21 E2E compose pipeline | 10-container stack; all 7 phases passing on podman + docker; PR #117 |
| HomericIntelligence/Odysseus | 2026-04-24 NATS publish retry | Full retry loop with jitter verified in CI (ProjectHermes) |
| HomericIntelligence/Odysseus | 2026-05-03 Atlas 6-host cold-start | 6 hosts started (4 podman, 1 pixi native, 1 docker); Agamemnon API confirmed |
| Odysseus | Plan for issue #176 (NATS leaf auth) | unverified plan — no code run, no CI; value is the reviewer-risk catalogue of uncertain assumptions |
| Odysseus | Plan R1 for issue #176 (NATS leaf auth, post-NOGO) | validator prototyped verified-local (brace-depth `block()`: exit 0 on fixed fixture, exit 1 on current configs); full plan still unverified |
