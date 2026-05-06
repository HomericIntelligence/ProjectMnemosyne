---
name: podman-scratch-image-healthcheck-workaround
description: "Distroless / scratch / minimal-base container images cannot run shell-based HEALTHCHECK directives — no shell, no wget, no curl, no busybox. Use when: (1) switching a service to distroless / scratch / minimal base, (2) adding a HEALTHCHECK to a Dockerfile, (3) writing a docker-compose or podman-compose healthcheck: block, (4) a container reports unhealthy forever but the process is clearly running, (5) `docker exec <c> sh` returns 'exec format error' or 'no such file', (6) k8s exec-style livenessProbe/readinessProbe silently fails."
category: tooling
date: 2026-05-05
version: "1.1.0"
user-invocable: false
verification: verified-local
history: podman-scratch-image-healthcheck-workaround.history
tags:
  - distroless
  - scratch
  - healthcheck
  - dockerfile
  - docker-compose
  - podman
  - kubernetes
  - liveness
  - readiness
  - nats
---

# Distroless / Scratch Image Healthcheck — Shell Required But Absent

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-05 |
| **Objective** | Stop shipping in-container healthchecks that silently fail forever on distroless / scratch / minimal-base images, and audit every place a shell-based probe might still be lurking when a service migrates to a minimal base. |
| **Outcome** | Successful — drop the in-container healthcheck, rely on external HTTP probes (`/livez`, `/readyz`), or build a `-healthcheck` flag into the binary. |
| **Verification** | verified-local — confirmed under both podman compose (NATS scratch) and docker compose (Atlas v0.2.0, `gcr.io/distroless/static-debian12:nonroot`). |
| **History** | [changelog](./podman-scratch-image-healthcheck-workaround.history) |

## When to Use

- You are switching any service to `gcr.io/distroless/*`, `cgr.dev/chainguard/*`, `scratch`, or any `FROM scratch`-style minimal base.
- You are adding a `HEALTHCHECK` instruction to a Dockerfile.
- You are writing a `healthcheck:` block in `docker-compose.yml` or `podman-compose.yml`.
- A container shows `up (unhealthy)` in `docker compose ps` / `podman ps` but the process is clearly running and external probes against the port return 200.
- `docker exec <container> sh` returns `OCI runtime exec failed: ... executable file not found in $PATH` or "no such file or directory".
- Kubernetes pods stay `NotReady` forever even though the app is healthy — and the probe is `exec:`-style.
- `podman compose up` hangs because a dependency's healthcheck never goes healthy.
- Service binaries log `exec: "wget": executable file not found` or `exec: "sh": executable file not found`.

## Verified Workflow

### Quick Reference — the four-way audit

Whenever you switch a service to distroless / scratch / minimal (or any base without busybox), audit **all four** places a shell-based probe could be hiding. Every one of them breaks silently if you miss it.

```text
[ ] 1. Dockerfile          — `HEALTHCHECK CMD wget|curl|sh ...`     → remove or replace with binary-built probe
[ ] 2. docker-compose.yml  — `healthcheck: test: ["CMD", "wget"...]` → remove the healthcheck: block
[ ] 3. k8s manifests       — `livenessProbe:` / `readinessProbe:`    → switch `exec:` to `httpGet:` /
                              with `exec: command: [sh|wget|curl]`     `tcpSocket:` / `grpc:`, OR build a
                                                                        `-healthcheck` flag into the binary
[ ] 4. operator runbooks   — "exec into the container and run X"      → rewrite to use external HTTP probe or
                                                                         `kubectl debug` ephemeral container
```

### Recommended fix (taken on Atlas v0.2.0)

```yaml
# WRONG — silently fails forever on distroless:
services:
  atlas:
    image: ghcr.io/homericintelligence/atlas:v0.2.0  # gcr.io/distroless/static-debian12:nonroot
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3002/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

# CORRECT — no in-container probe; rely on external HTTP probes:
services:
  atlas:
    image: ghcr.io/homericintelligence/atlas:v0.2.0
    # No healthcheck: block. The binary is the only thing in the image.
    # Liveness / readiness are checked from outside via:
    #   curl http://localhost:3002/livez   → 200 if process is up
    #   curl http://localhost:3002/readyz  → 200 only when every component is loaded,
    #                                        enabled, and reporting valid results
```

### Detailed Steps

1. **Confirm the image is shell-less.** Run `docker exec <container> sh -c "true"` or `podman exec <c> sh -c "true"`. If you see `exec: "sh": executable file not found in $PATH`, the image has no shell and every CMD-SHELL / wget / curl probe is broken.
2. **Remove the in-container probe at the source.** Delete `HEALTHCHECK` from the Dockerfile and `healthcheck:` from compose. Do not try to "fix" the probe with a different shell command — none of them work without a shell.
3. **Replace `depends_on: condition: service_healthy` with plain `depends_on: - name`.** Health-conditional ordering deadlocks because the dependency never becomes healthy. Use start-order only and add a connection-retry loop in the dependent service.
4. **Move probes outside the container.** Have the orchestrator (k8s, Nomad, an external monitor) hit `http://<host>:<port>/livez` and `/readyz` from outside. The probe runs in the orchestrator's environment, where `wget`/`curl`/HTTP libraries exist.
5. **For k8s, switch `exec:` probes to `httpGet:` / `tcpSocket:` / `grpc:`.** These are evaluated by the kubelet, not inside the container — they don't need a shell.
6. **(Optional, cleanest long-term)** Build a `-healthcheck` flag into the binary itself: `myapp -healthcheck` calls the same handler in-process and exits 0/1. The image stays minimal and `HEALTHCHECK CMD ["/myapp", "-healthcheck"]` works on distroless because it invokes the binary directly, not a shell.
7. **Update operator runbooks.** Any step that says "exec into the container and run X" must be rewritten to use external HTTP probes or `kubectl debug` ephemeral containers (which inject a debug image alongside the target).

### Alternatives considered

| Option | Image cost | Trade-off | Recommendation |
| -------- | ----------- | --------- | --------------- |
| Drop in-container healthcheck (taken) | 0 | Honest about distroless constraints; relies on external probes; orchestrator must do liveness/readiness checks. | **Default.** Pair with `/livez` + `/readyz` HTTP endpoints. |
| Switch to `gcr.io/distroless/static:debug-nonroot` | +~5 MB | Restores busybox shell + wget; expands attack surface; defeats some of the distroless rationale. | Use for debugging only — not production. |
| Build `-healthcheck` flag into the binary | 0 | Needs source code change; cleanest long-term solution; image stays minimal; works for HEALTHCHECK + k8s exec probes alike. | **Best long-term** when you own the binary. |
| Sidecar container with curl | +sidecar | Adds infra complexity; defeats single-container-per-pod simplicity; multiplies pods. | Reject unless already running a sidecar mesh. |

### What scratch / distroless images lack

| Tool | `scratch` | `distroless/static:nonroot` | `distroless/static:debug-nonroot` | Used by |
| ------ | ---------- | ----------------------------- | ----------------------------------- | --------- |
| `/bin/sh` | No | No | Yes (busybox) | CMD-SHELL healthchecks, k8s `exec:` probes |
| `wget` | No | No | Yes (busybox) | HTTP healthchecks |
| `curl` | No | No | No | HTTP healthchecks |
| `true` | No | No | Yes (builtin) | Trivial healthchecks |
| `which` | No | No | Yes | Tool detection in scripts |
| The service binary | Yes | Yes | Yes | Only thing reliably present |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `CMD-SHELL "wget ..."` on `nats:latest` (podman compose) | Shell-based HTTP healthcheck | No shell in scratch image | Scratch = no shell at all |
| `CMD-SHELL "true"` | Simplest possible shell command | Still requires `/bin/sh` to interpret `true` | Even `true` needs a shell |
| `CMD ["nats-server", "--help"]` | Use existing binary as health proxy | `nats-server --help` exits with code 1 (not 0) when already running | Binary `--help` commands often return non-zero |
| `CMD-SHELL "nats-server --help > /dev/null 2>&1"` | Redirect stderr/stdout | No shell to do the redirection | Same shell issue |
| `CMD ["wget", "-qO-", "http://localhost:3002/healthz"]` against `gcr.io/distroless/static-debian12:nonroot` (Atlas v0.2.0, docker compose) | HTTP healthcheck via wget on distroless | `OCI runtime exec failed: exec failed: unable to start container process: exec: "wget": executable file not found in $PATH`. Container reported `unhealthy` forever; orchestrator never sent traffic. | distroless/static has no busybox — there is **no** wget, no curl, no shell. Either drop the healthcheck or switch to `:debug-nonroot` (busybox) or build a `-healthcheck` flag into the binary. |

## Results & Parameters

```yaml
# Known shell-less images affected:
shell_less_images:
  - nats:latest                                # NATS server (scratch base)
  - nats:2.10                                  # NATS server (scratch base)
  - gcr.io/distroless/static-debian12:nonroot  # Atlas v0.2.0
  - gcr.io/distroless/base-debian12:nonroot
  - gcr.io/distroless/cc-debian12:nonroot
  - cgr.dev/chainguard/static                  # Chainguard static
  - scratch                                    # FROM scratch

# Verified-local fix (Atlas v0.2.0):
broken_state: |
  $ docker compose up -d atlas
  $ docker compose ps
  NAME    STATE          STATUS
  atlas   running        Up 12 seconds (unhealthy)
  $ docker logs atlas | grep -i exec
  OCI runtime exec failed: exec failed: unable to start container process:
  exec: "wget": executable file not found in $PATH

fixed_state: |
  # docker-compose.yml: removed healthcheck: block entirely
  $ docker compose up -d atlas
  $ docker compose ps
  NAME    STATE          STATUS
  atlas   running        Up 8 seconds
  $ curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3002/livez
  200
  $ curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3002/readyz
  200

# External probe pattern (recommended):
liveness:  GET http://<host>:<port>/livez   → 200 iff the process is up
readiness: GET http://<host>:<port>/readyz  → 200 iff every component is loaded,
                                              enabled, and reporting valid results

# Example connection retry in C++ (nats.c):
cpp_retry: |
  for (int i = 0; i < 30 && !connected; ++i) {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    s = natsConnection_ConnectTo(&conn, url.c_str());
  }
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | E2E compose with NATS (podman compose) | `nats:latest` scratch image caused compose deadlock under `service_healthy` |
| Atlas v0.2.0 | `ghcr.io/homericintelligence/atlas:v0.2.0` (~14.9 MB, `gcr.io/distroless/static-debian12:nonroot`), docker compose | Pre-existing `wget`-based healthcheck failed with `exec: "wget": executable file not found`; fix was to drop the in-container healthcheck and rely on external `/livez` + `/readyz` probes |
