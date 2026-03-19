---
name: docker-pixi-isolation
description: "Fix Docker container Mojo stdlib failures caused by host .pixi/ bind-mount contamination. Use when: CI tests fail with 'unable to locate module std' inside Docker containers."
category: ci-cd
date: 2026-03-18
user-invocable: false
---

# Docker Pixi Isolation

## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | CI test jobs inside Docker fail with `error: unable to locate module 'std'` |
| **Root Cause** | Host `.pixi/` directory (with native Mojo binaries) bind-mounted into container shadows container's own Mojo installation |
| **Solution** | Named Docker volume at `/workspace/.pixi` + entrypoint script + remove `setup-pixi` from Docker-routed CI jobs |
| **Scope** | Docker-compose services, CI workflow files, justfile `_run` recipe |

## When to Use

- CI test jobs fail with `unable to locate module 'std'` inside Docker containers
- Host environment tools (pixi, Mojo) leak into Docker containers via bind mounts
- `docker-compose.yml` bind-mounts the entire workspace (`.:/workspace`) and host has `.pixi/` installed
- CI workflows use `setup-pixi` action but route commands through Docker via justfile

## Verified Workflow

### Quick Reference

1. **Add named volume** to `docker-compose.yml` that shadows the bind-mounted `.pixi/`:

```yaml
services:
  myservice:
    volumes:
      - .:/workspace:delegated
      - workspace-pixi:/workspace/.pixi  # Shadows host .pixi/

volumes:
  workspace-pixi:
    driver: local
```

2. **Create entrypoint script** (`docker/entrypoint.sh`) that initializes pixi if needed:

```bash
#!/usr/bin/env bash
set -e
if [ ! -x ".pixi/envs/default/bin/mojo" ]; then
    echo "Initializing pixi environment inside container..."
    pixi install
fi
exec "$@"
```

3. **Add entrypoint to Dockerfile** (before `CMD`):

```dockerfile
COPY --chown=${USER_NAME}:${USER_NAME} docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
```

4. **Add entrypoint to docker-compose services**:

```yaml
entrypoint: ["/usr/local/bin/entrypoint.sh"]
```

5. **Remove `setup-pixi` from CI workflows** that route through Docker:
   - If a workflow calls `just build`, `just test-group`, etc. (which route through Docker via `_run` recipe), it does NOT need `setup-pixi`
   - Remove `NATIVE=1` prefixes that bypass Docker
   - Remove direct `pixi run mojo` calls that won't work without host pixi

### Why Named Volumes Work

Docker named volumes take precedence over bind mount subdirectories. When you have:
- Bind mount: `.:/workspace` (brings host `.pixi/` into container)
- Named volume: `workspace-pixi:/workspace/.pixi` (empty initially)

The named volume wins at `/workspace/.pixi`, effectively hiding the host's incompatible `.pixi/` directory. The entrypoint script then populates it with `pixi install` on first run.

### Identifying Affected CI Jobs

A CI job needs this fix if it:
1. Uses `setup-pixi` (installs pixi on the host, creating `.pixi/`)
2. Routes commands through Docker (via justfile `_run` recipe or `docker compose exec`)
3. The justfile `_run` recipe checks `NATIVE` env var — without `NATIVE=1`, commands run in Docker

Check with: `grep -l "setup-pixi" .github/workflows/*.yml` cross-referenced with `grep -l "just " .github/workflows/*.yml`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `NATIVE=1` to CI jobs | Force all Mojo commands to run natively on the runner | Defeats the purpose of Docker isolation; inconsistent with other jobs that use Docker | All CI jobs should use the same execution environment (Docker) |
| Keep `setup-pixi` alongside Docker volume fix | Let pixi install on host but shadow with volume | Wastes CI time installing pixi on host when it's not used; `.pixi/` still created on host | Remove unnecessary setup steps entirely, don't just work around them |
| Use absolute imports in Mojo (`from shared.core.shape import ...`) | Import functions using full package path | Creates different type identity when module is also imported via `__init__.mojo`, causing `cannot be converted from 'ExTensor' to 'ExTensor'` errors | Always use relative imports (`from .shape import ...`) within a package to avoid type identity splits |

## Results & Parameters

### docker-compose.yml Configuration

```yaml
services:
  projectodyssey-dev:
    volumes:
      - .:/workspace:delegated
      - workspace-pixi:/workspace/.pixi
      - pixi-cache:${HOME}/.pixi
    entrypoint: ["/usr/local/bin/entrypoint.sh"]

  projectodyssey-ci:
    volumes:
      - .:/workspace
      - workspace-pixi:/workspace/.pixi
      - pixi-cache:${HOME}/.pixi
    entrypoint: ["/usr/local/bin/entrypoint.sh"]

volumes:
  workspace-pixi:
    driver: local
```

### CI Workflow Pattern (After Fix)

```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@v6

  # NO setup-pixi step — Mojo runs inside Docker

  - name: Install Just
    uses: extractions/setup-just@v3

  - name: Build
    run: just build  # Routes through Docker via _run recipe
```

### Related Mojo Import Fix

When a Mojo package has circular references (e.g., `extensor.mojo` importing from `shape.mojo` which imports `ExTensor`), always use relative imports:

```mojo
# WRONG — creates separate type identity
from shared.core.shape import split as split_fn

# CORRECT — same type identity
from .shape import split as split_fn
```
