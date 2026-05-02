---
name: docker-compose-v5-healthcheck-array-split
description: "Docker Compose v5 (v2.39+) splits healthcheck test: arrays on spaces, breaking all pipe-based shell healthchecks. Use when: (1) healthchecks fail with CMD array format on Docker Compose v5, (2) containers become unhealthy despite service being responsive, (3) migrating compose files to Docker Compose v5, (4) diagnosing 'sh -c wget' help text in healthcheck logs."
category: tooling
date: 2026-04-21
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker-compose
  - docker-compose-v5
  - healthcheck
  - busybox
  - wget
  - podman
  - wsl2
  - regression
---

# Docker Compose v5 Healthcheck Array Splitting Regression

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-21 |
| **Objective** | Fix all-unhealthy containers in Odysseus E2E stack after upgrading to Docker Compose v5.0.2 |
| **Outcome** | Successful — all 9 containers healthy, 8/8 E2E phases pass after switching to string form |
| **Verification** | verified-local |

## When to Use

- All or many containers become `unhealthy` after upgrading to Docker Compose v5 (v2.39+)
- `podman inspect` or `docker inspect` shows the healthcheck was split: e.g. `["CMD","sh","-c","wget","-qO-","http://..."]` instead of `["CMD","sh","-c","wget -qO- http://..."]`
- Healthcheck logs show `wget --help` text or usage output (indicating `wget` ran without arguments)
- Services with `depends_on: condition: service_healthy` never start because dependencies stay unhealthy
- Migrating a compose file from Docker Compose v2.x to v5.x
- Diagnosing `sh -c wget` or similar partial-command execution in healthcheck output

## Verified Workflow

### Quick Reference

```yaml
# BROKEN on Docker Compose v5 (splits the 4th element on spaces):
healthcheck:
  test: ["CMD", "sh", "-c", "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"]

# WORKS on all versions (string = CMD-SHELL, passed verbatim to sh -c):
healthcheck:
  test: "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"

# For nats:alpine (BusyBox wget — does NOT support -O- combined flag):
# BROKEN:
healthcheck:
  test: "wget -qO- http://localhost:8222/healthz 2>/dev/null | grep -q ok"

# WORKS (BusyBox requires space-separated -O /dev/stdout):
healthcheck:
  test: "wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"
```

### Detailed Steps

1. **Diagnose the split**: Run `podman inspect <container-name> --format '{{json .Config.Healthcheck}}'` (or `docker inspect`). If you see the command string split into individual words, you have the v5 regression.

2. **Identify affected services**: Any service using `test: ["CMD", "sh", "-c", "..."]` or `test: ["CMD-SHELL", "..."]` with a multi-word shell command is affected.

3. **Apply the string fix**: Replace all YAML array `test:` values with plain string form. Docker Compose treats a string value as `CMD-SHELL` and passes it verbatim to `sh -c`.

4. **Handle BusyBox wget for Alpine-based images**: If the image uses BusyBox wget (e.g. `nats:alpine`, any Alpine image), replace `-qO-` (GNU wget combined flag) with `-q -O /dev/stdout` (BusyBox requires space-separated `-O` with explicit path).

5. **Verify fix**: After restarting with `podman compose down && podman compose up -d`, re-inspect the container — the healthcheck field should now show a single string for the command.

6. **Check all `depends_on: condition: service_healthy`**: Once the healthchecks pass, dependent services will start automatically.

### Diagnostic Commands

```bash
# Check serialized healthcheck (shows whether split occurred):
podman inspect <container-name> --format '{{json .Config.Healthcheck}}'

# Check live healthcheck status:
podman inspect <container-name> --format '{{json .State.Health}}'

# View raw healthcheck log:
podman inspect <container-name> --format '{{range .State.Health.Log}}{{.Output}}{{end}}'

# Detect Docker Compose version:
docker-compose --version
# or via snap:
/snap/bin/docker-compose --version
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `["CMD-SHELL", "cmd"]` array form | Used `["CMD-SHELL", "wget -qO- http://localhost:8080/v1/health"]` — single-element payload | Docker Compose v5 still splits this; confirmed via `podman inspect .Config.Healthcheck` showing `["CMD-SHELL","wget","-qO-","http://..."]` | `CMD-SHELL` array form is also split — only the string form is safe |
| `["CMD", "sh", "-c", "wget -q -O /dev/stdout ... \| grep -q ok"]` array form | Attempted to use the BusyBox-compatible `-O /dev/stdout` syntax inside the array | Array still split; `sh` received `-c` then `wget` as separate args, ignoring `-c` | Array splitting is unconditional in v5 regardless of flag style |
| `["CMD", "sh", "-c", "wget -qO- ... \| grep -q ok"]` array form | GNU wget combined `-qO-` flag inside CMD array | Two failures: (1) v5 splits the array so only `wget` ran; (2) even if unsplit, BusyBox in `nats:alpine` rejects `-qO-` as invalid combined flag | Combined `-qO-` is GNU wget only; always use `-q -O /dev/stdout` for BusyBox |
| `wget -q --spider <url>` inside array | BusyBox `wget --spider` exits 0 on success; used as lightweight HTTP probe | Array splitting meant only `wget` ran (printed help, exited 1) — the `--spider` argument was never seen | Fix the array split first; `--spider` itself is valid for BusyBox healthchecks |

## Results & Parameters

After applying the string-form fix across all services (NATS, Agamemnon, Nestor, Hermes):

```yaml
# Agamemnon / Nestor / Hermes (GNU wget in non-Alpine images):
healthcheck:
  test: "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s

# NATS (nats:alpine — BusyBox wget, explicit -O path required):
healthcheck:
  test: "wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 15s
```

**Expected outcomes after fix:**

```
podman ps --format "table {{.Names}}\t{{.Status}}"
# All containers should show "(healthy)" in Status column

podman inspect nats --format '{{json .Config.Healthcheck}}'
# Should show single-element string, NOT split words:
# {"Test":["CMD-SHELL","wget -q -O /dev/stdout http://localhost:8222/healthz 2>/dev/null | grep -q ok"],...}
```

**Root cause summary:** Docker Compose v5 changed how it serializes the `test:` field when the value is a YAML sequence. It now passes each element of the YAML array as a separate exec argument rather than treating element [3] as a single shell string. This worked correctly in Docker Compose v2.x. The string form of `test:` is immune because Docker Compose has always serialized strings as `CMD-SHELL` with the entire string as a single argument.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | E2E stack (`docker-compose.e2e.yml`) with Docker Compose v5.0.2 via `/snap/bin/docker-compose`, podman 4.9.3, WSL2 Ubuntu 24.04 | All 9 containers healthy, 8/8 E2E phases passed after fix |
