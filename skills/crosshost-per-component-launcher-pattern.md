---
name: crosshost-per-component-launcher-pattern
description: "Per-component install and launch commands for cross-host HomericIntelligence deployment. Use when: (1) deploying individual services on separate Tailscale hosts, (2) adding justfile recipes that launch C++ binaries or delegate to submodule justfiles, (3) connecting services via NATS_URL across a mesh, (4) deciding between compose-based vs native binary deployment."
category: architecture
date: 2026-04-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - cross-host
  - deployment
  - launcher
  - justfile
  - nats
  - tailscale
  - per-component
  - podman
  - homeric-intelligence
---

# Cross-Host Per-Component Launcher Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-04 |
| **Objective** | Create per-component install and launch commands so each HomericIntelligence service can run independently on any Tailscale host, connected via NATS_URL |
| **Outcome** | 9 new justfile recipes (2 install + 7 launchers) enabling flexible multi-machine deployment where any component runs on any host |
| **Verification** | verified-local |

## When to Use

- Deploying individual HomericIntelligence services on separate Tailscale hosts (not using compose)
- Adding justfile recipes that launch C++ binaries from BUILD_ROOT or delegate to submodule justfiles
- Connecting distributed services via NATS_URL as the universal connector parameter
- Deciding between compose-based deployment (see `architecture-crosshost-nats-compose-deployment`) and native binary launchers
- Setting up a new host to participate in the HomericIntelligence mesh with minimal ceremony

## Verified Workflow

### Quick Reference

```bash
# --- Worker host setup ---
just install-worker                   # podman + tools + submodule init

# --- Control host setup ---
just install-control                  # C++ build chain + build agamemnon/nestor

# --- Start NATS (on any host, typically the worker) ---
just start-nats
# Outputs: NATS running at nats://<ip>:4222

# --- Start individual components (on any host, point at NATS) ---
just start-agamemnon NATS_URL=nats://worker-ip:4222
just start-nestor    NATS_URL=nats://worker-ip:4222
just start-hermes    NATS_URL=nats://worker-ip:4222
just start-myrmidon  NATS_URL=nats://worker-ip:4222 AGAMEMNON_URL=http://worker-ip:8080
just start-argus                      # delegates to ProjectArgus docker-compose
just start-console   NATS_URL=nats://worker-ip:4222
```

### Two-Role Install Pattern

Install recipes are split by host role to avoid pulling unnecessary dependencies:

```just
# Worker: podman + tools (no C++ compiler needed)
install-worker:
    bash e2e/doctor.sh --role worker --install
    git submodule update --init --recursive

# Control: full C++ build chain + compile binaries
install-control:
    bash e2e/doctor.sh --role control --install
    git submodule update --init --recursive
    just _build-agamemnon _build-nestor
```

### NATS as Standalone Podman Container

NATS runs as a standalone podman container (not inside compose) for maximum deployment flexibility. The `--replace` flag makes the command idempotent:

```just
start-nats:
    podman run -d --replace --name hi-nats \
      -p 4222:4222 -p 8222:8222 \
      nats:alpine -js -m 8222
```

Key details:
- Uses `nats:alpine` (not `nats:latest`) for healthcheck compatibility
- `-js` enables JetStream (required for pull consumers)
- `-m 8222` enables HTTP monitoring endpoint
- Port 4222 = client connections, port 8222 = monitoring API

### C++ Binary Launchers

C++ services launch directly from BUILD_ROOT, receiving NATS_URL as an environment variable:

```just
start-agamemnon NATS_URL="nats://localhost:4222":
    NATS_URL={{ NATS_URL }} "{{BUILD_ROOT}}/ProjectAgamemnon/ProjectAgamemnon_server"

start-nestor NATS_URL="nats://localhost:4222":
    NATS_URL={{ NATS_URL }} "{{BUILD_ROOT}}/ProjectNestor/ProjectNestor_server"
```

Binaries are compiled by `just build` (or `just install-control`), which runs CMake with Ninja and places artifacts under `build/<ProjectName>/`.

### Delegation to Submodule Justfiles

Components with their own build/run infrastructure delegate to the submodule's justfile, passing NATS_URL through the environment:

```just
# Hermes has its own Python/FastAPI setup
start-hermes NATS_URL="nats://localhost:4222":
    cd infrastructure/ProjectHermes && NATS_URL={{ NATS_URL }} just start

# Argus has its own docker-compose stack (Prometheus + Loki + Grafana)
start-argus:
    cd infrastructure/ProjectArgus && just start
```

### Python Fallback for Non-Compiled Components

hello-myrmidon does not have a C++ build target in `just build`. The Python `worker.py` serves as the runtime:

```just
start-myrmidon NATS_URL="nats://localhost:4222" AGAMEMNON_URL="http://localhost:8080":
    NATS_URL={{ NATS_URL }} AGAMEMNON_URL={{ AGAMEMNON_URL }} \
      python3 provisioning/Myrmidons/hello-world/worker.py
```

### Example: 3-Host Deployment

```
Host A (NATS hub):
  just start-nats

Host B (control plane):
  just install-control
  just start-agamemnon NATS_URL=nats://hostA:4222
  just start-nestor    NATS_URL=nats://hostA:4222

Host C (worker):
  just install-worker
  just start-hermes    NATS_URL=nats://hostA:4222
  just start-myrmidon  NATS_URL=nats://hostA:4222 AGAMEMNON_URL=http://hostB:8080
  just start-argus
  just start-console   NATS_URL=nats://hostA:4222
```

All hosts must be on the same Tailscale mesh. Replace hostnames with Tailscale IPs if DNS is not configured.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| hello-myrmidon C++ binary | Tried to include hello-myrmidon in `just build` targets | hello-myrmidon has no CMakeLists.txt; only Agamemnon, Nestor, Charybdis, Keystone, and Odyssey are compiled by `just build` | Use the Python worker.py fallback instead of adding a build step for simple myrmidon agents |
| Monolithic e2e-all launcher | Considered a single `just e2e-all` that starts everything | User explicitly wanted per-component granularity for multi-machine flexibility; a monolithic command defeats the purpose | Individual launchers compose better than monolithic scripts for distributed deployment |
| nats:latest image | Initially used `nats:latest` for the standalone container | `nats:latest` lacks shell utilities needed for container healthchecks | Always use `nats:alpine` which includes the necessary healthcheck tooling |

## Results & Parameters

### Justfile Recipes Added

```yaml
recipes:
  install-worker:
    purpose: "Install prerequisites for worker host"
    delegates_to: "e2e/doctor.sh --role worker --install"
    also_runs: "git submodule update --init --recursive"

  install-control:
    purpose: "Install prerequisites + build C++ binaries for control host"
    delegates_to: "e2e/doctor.sh --role control --install"
    also_runs: "submodule init + _build-agamemnon + _build-nestor"

  start-nats:
    purpose: "NATS JetStream server (standalone podman container)"
    image: "nats:alpine"
    ports: "4222 (client), 8222 (monitoring)"
    flags: "-js -m 8222"

  start-agamemnon:
    purpose: "ProjectAgamemnon C++ binary"
    binary: "build/ProjectAgamemnon/ProjectAgamemnon_server"
    params: "NATS_URL (default: nats://localhost:4222)"

  start-nestor:
    purpose: "ProjectNestor C++ binary"
    binary: "build/ProjectNestor/ProjectNestor_server"
    params: "NATS_URL (default: nats://localhost:4222)"

  start-hermes:
    purpose: "ProjectHermes webhook-to-NATS bridge"
    delegates_to: "infrastructure/ProjectHermes justfile"
    params: "NATS_URL (default: nats://localhost:4222)"

  start-myrmidon:
    purpose: "hello-myrmidon Python worker"
    runtime: "python3 provisioning/Myrmidons/hello-world/worker.py"
    params: "NATS_URL, AGAMEMNON_URL"

  start-argus:
    purpose: "Prometheus + Loki + Grafana observability stack"
    delegates_to: "infrastructure/ProjectArgus justfile"

  start-console:
    purpose: "Real-time NATS event viewer"
    runtime: "python3 tools/odysseus-console.py"
    params: "NATS_URL (default: nats://localhost:4222)"
```

### Design Decisions

| Decision | Rationale |
| ---------- | ----------- |
| NATS_URL as universal connector | Every component takes one parameter to join the mesh; no service discovery needed |
| Default NATS_URL=localhost | Allows single-machine development without any flags |
| `--replace` on podman run | Makes start-nats idempotent; re-running replaces the container |
| Two install roles | Worker hosts need only podman; control hosts need cmake/ninja/gcc for C++ compilation |
| Python fallback for myrmidons | Avoids requiring a C++ build for simple agent workers |

### Compose vs. Per-Component: When to Use Which

| Approach | Best For | Skill Reference |
| ---------- | ---------- | ----------------- |
| Compose overlay (`docker-compose.crosshost.yml`) | Single-command deployment, CI/CD, reproducible environments | `architecture-crosshost-nats-compose-deployment` |
| Per-component launchers (`just start-*`) | Multi-machine flexibility, development, debugging individual services | This skill |
| Both together | Worker host uses compose, control host uses native binaries | Combine both skills |

## Related Skills

| Skill | Relationship |
| ------- | ------------- |
| `architecture-crosshost-nats-compose-deployment` | Compose overlay approach to cross-host deployment; complementary to this per-component approach |
| `e2e-crosshost-doctor-prerequisite-checker` | The doctor.sh tool used by install-worker and install-control recipes |
| `e2e-homeric-compose-cpp-pipeline` | Base single-host E2E pipeline that this skill extends to multi-host per-component |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | Per-component launcher recipes | Commit 82742b7 on feat/crosshost-e2e-pipeline branch; dry-run tested, recipes parse correctly, binary paths confirmed |
