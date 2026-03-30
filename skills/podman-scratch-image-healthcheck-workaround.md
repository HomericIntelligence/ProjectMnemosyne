---
name: podman-scratch-image-healthcheck-workaround
description: "Work around healthcheck failures for scratch/distroless container images in podman compose. Use when: (1) NATS or other scratch images fail CMD-SHELL healthchecks, (2) depends_on service_healthy blocks container startup, (3) minimal images have no shell or utilities."
category: debugging
date: 2026-03-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - podman
  - healthcheck
  - scratch
  - distroless
  - nats
  - compose
---

# Podman Scratch Image Healthcheck Workaround

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Fix compose startup blocked by healthcheck failures on scratch/distroless images |
| **Outcome** | Successful — remove healthchecks for scratch images, use simple depends_on |
| **Verification** | verified-local |

## When to Use

- `podman compose up` hangs because a dependency's healthcheck keeps failing
- Container logs show: `exec: "sh": executable file not found` or `exec: "wget": executable file not found`
- The failing container is a minimal/scratch/distroless image (NATS, etcd, CoreDNS, etc.)
- Services that `depends_on: condition: service_healthy` never start

## Verified Workflow

### Quick Reference

```yaml
# WRONG — fails for scratch images:
services:
  nats:
    image: nats:latest
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:8222/healthz"]
  app:
    depends_on:
      nats:
        condition: service_healthy  # blocks forever

# CORRECT — simple ordering for scratch images:
services:
  nats:
    image: nats:latest
    # No healthcheck — scratch image has no shell/tools
  app:
    depends_on:
      - nats  # start-order only, no health condition
```

### Detailed Steps

1. Identify if the image is scratch/distroless: `podman exec <container> sh -c "true"` → `executable file not found`
2. Remove the `healthcheck:` block entirely from that service
3. Change all `depends_on: condition: service_healthy` to simple `depends_on: - name`
4. Add retry logic in the dependent service (connection retry loop) instead of relying on compose health

### What scratch images lack

| Tool | Available? | Used by |
|------|-----------|---------|
| `/bin/sh` | No | CMD-SHELL healthchecks |
| `wget` | No | HTTP healthchecks |
| `curl` | No | HTTP healthchecks |
| `true` | No | Trivial healthchecks |
| `which` | No | Tool detection |
| The service binary | Yes | Only thing present |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `CMD-SHELL "wget ..."` | Shell-based HTTP healthcheck | No shell in scratch image | Scratch = no shell at all |
| `CMD-SHELL "true"` | Simplest possible shell command | Still requires a shell to interpret "true" | Even `true` needs `/bin/sh` |
| `CMD ["nats-server", "--help"]` | Use existing binary as health proxy | `nats-server --help` exits with code 1 (not 0) when already running | Binary help commands often return non-zero |
| `CMD-SHELL "nats-server --help > /dev/null 2>&1"` | Redirect stderr/stdout | No shell to do the redirection | Same shell issue |

## Results & Parameters

```yaml
# Known scratch/distroless images affected:
scratch_images:
  - nats:latest (NATS server)
  - nats:2.10 (NATS server)
  - gcr.io/distroless/* (Google distroless)
  - cgr.dev/chainguard/* (Chainguard images)

# Workaround pattern for compose:
pattern: |
  Remove healthcheck from scratch image service.
  Use simple depends_on (start-order only).
  Add connection retry loop in dependent services.

# Example retry in C++ (nats.c):
cpp_retry: |
  for (int i = 0; i < 30 && !connected; ++i) {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    s = natsConnection_ConnectTo(&conn, url.c_str());
  }
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | E2E compose with NATS | nats:latest scratch image caused compose deadlock |
