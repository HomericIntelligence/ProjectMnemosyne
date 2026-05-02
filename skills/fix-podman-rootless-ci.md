---
name: fix-podman-rootless-ci
description: 'Fix rootless Podman CI failures: Dockerfile ARG scoping, workspace UID
  mapping, compose provider compatibility. Use when: container builds fail with empty
  ARG values across FROM boundaries, bind-mounted files have Permission denied, or
  docker-compose doesn''t support Podman extensions.'
category: ci-cd
date: 2026-03-20
version: 1.0.0
user-invocable: false
---
# Fix Podman Rootless CI

## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Rootless Podman on GitHub Actions introduces multiple failure modes not seen with Docker or rootful Podman |
| **Scope** | Multi-stage Dockerfiles, docker-compose.yml, CI composite actions, justfile build recipes |
| **Environment** | GitHub Actions `ubuntu-latest` runners with rootless Podman + docker-compose CLI plugin |
| **Impact** | All container-dependent CI jobs fail (builds, tests, SBOM generation) |

## When to Use

- Container builds fail with `can't find uid for user :` or empty `${VAR}` in COPY --chown
- `Permission denied` when creating files/dirs inside bind-mounted workspace in CI containers
- `podman compose` delegates to docker-compose CLI plugin and Podman-specific compose options are ignored
- SBOM tools (Syft/anchore) fail to authenticate to GHCR to scan pushed images
- Justfile recipes create directories on the host that are then non-writable inside the container

## Verified Workflow

### Quick Reference

| Issue | Root Cause | Fix |
| ------- | ----------- | ----- |
| `can't find uid for user :` | Docker ARGs don't persist across FROM | Re-declare `ARG` in each stage |
| `Permission denied` on workspace files | Rootless Podman UID namespace mapping | `chmod -R a+rwX .` on host before container use |
| docker-compose ignores `userns_mode` | docker-compose CLI plugin, not Podman compose | Don't use Podman-specific compose extensions |
| SBOM scan auth failure | Syft can't authenticate to GHCR | Export image to tarball, scan locally |
| Build mode always "debug" | Justfile `$1` vs `{{mode}}` parameter | Use `{{mode}}` template substitution |
| Host-created dirs non-writable in container | `_ensure_build_dir` runs on host, not in container | Remove host-side mkdir; inner recipes already do it |

### Step 1: Dockerfile ARG Scoping

Docker/Podman `ARG` declarations are scoped to a single build stage. They do NOT persist across `FROM` boundaries.

**Symptom**: `COPY --chown=${USER_NAME}:${USER_NAME}` fails with `can't find uid for user :`

**Fix**: Re-declare the ARG in every stage that uses it:

```dockerfile
# Stage 1
FROM ubuntu:24.04 AS base
ARG USER_NAME=dev
# ... uses USER_NAME ...

# Stage 2 - MUST re-declare
FROM base AS development
ARG USER_NAME=dev          # <-- Required! Without this, USER_NAME is empty
USER ${USER_NAME}
COPY --chown=${USER_NAME}:${USER_NAME} . .

# Stage 3 inheriting from development - ARG inherited
FROM development AS ci
# USER_NAME is available (inherited from development)

# Stage 4 - from base, MUST re-declare
FROM base AS production
ARG USER_NAME=dev          # <-- Required again
COPY --from=development /home/${USER_NAME}/.pixi /home/${USER_NAME}/.pixi
```

### Step 2: Rootless Podman Workspace Permissions

In rootless Podman, the user namespace maps UIDs:
- Container UID 0 (root) -> Host user (e.g., UID 1001)
- Container UID 1001 -> Host subuid range (e.g., 101001)

Bind-mounted host files (owned by host UID 1001) appear as owned by container root (UID 0). The container application user (UID 1001) cannot write to them.

**Fix**: Make the workspace world-writable on the host before the container uses it:

```yaml
# In CI composite action, after starting container:
- name: Fix workspace permissions
  shell: bash
  run: |
    chmod -R a+rwX . || true
```

This is safe because CI runners are ephemeral single-use VMs.

**Do NOT try**:
- `userns_mode: keep-id` in docker-compose.yml (docker-compose CLI plugin ignores it)
- `PODMAN_USERNS=keep-id` env var (unreliable through docker-compose API)
- `chown` inside the container (overcomplicated and may not work with UID mapping)

### Step 3: SBOM Generation Without Registry Auth

SBOM tools like Syft/anchore need to read the container image. If the image was pushed to GHCR, Syft may not inherit Podman login credentials.

**Fix**: Export the image to a tarball and scan locally:

```yaml
- name: Export image for SBOM
  run: |
    podman save -o /tmp/image.tar "$REGISTRY/$IMAGE:$TAG"

- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    image: /tmp/image.tar
```

### Step 4: Justfile Parameter Passing

In justfile, recipe parameters are template-substituted with `{{param}}`. They are NOT passed as bash positional parameters (`$1`, `$2`).

```just
# WRONG - $1 is always empty in justfile bash blocks
_build-inner mode="debug":
    #!/usr/bin/env bash
    MODE="${1:-debug}"    # Always "debug"!

# CORRECT - use just template substitution
_build-inner mode="debug":
    #!/usr/bin/env bash
    MODE="{{mode}}"       # Correctly receives the argument
```

### Step 5: Host vs Container Directory Creation

When using `podman compose exec` to run builds inside a container with bind-mounted workspace:

- Directories created on the **host** (before exec) are owned by the host user
- In rootless Podman, these appear as root-owned inside the container
- The container application user cannot write to them

**Fix**: Don't create build output directories on the host. Let the inner build script create them inside the container where the user has appropriate permissions.

### Step 6: Podman Socket on GitHub Actions

GitHub Actions `ubuntu-latest` runners have Podman installed but the socket is not activated by default. `podman compose` delegates to docker-compose which needs the socket.

```yaml
- name: Start Podman socket
  shell: bash
  run: |
    systemctl --user start podman.socket || true
    echo "DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock" >> "$GITHUB_ENV"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `userns_mode: keep-id` in docker-compose.yml | Add Podman-specific user namespace mapping to compose file | `podman compose` on GH Actions delegates to `docker-compose` CLI plugin, which doesn't understand Podman extensions | Check what compose provider is actually used (`/usr/libexec/docker/cli-plugins/docker-compose`) before using Podman-specific features |
| `PODMAN_USERNS=keep-id` env var | Set env var so Podman applies keep-id to all containers | Unreliable when containers are created through the Docker API by docker-compose, not directly by Podman CLI | Podman CLI env vars may not be honored when docker-compose creates containers via the API |
| `chown` inside container as root | Run `podman compose exec -u 0 -T` to chown workspace to container user | Overcomplicated; in rootless Podman, root inside container IS the host user, but chown to non-root UID involves subuid mapping complexities | Prefer simpler host-side solutions (`chmod`) over in-container ownership changes |
| Initial plan missing Dockerfile ARG issue | Original CI fix plan addressed 3 issues but missed the ARG scoping bug | The Dockerfile's `USER_NAME` ARG was only declared in the `base` stage; development/production stages silently used empty string | Always check `ARG` declarations across ALL stages in multi-stage Dockerfiles — empty ARGs cause silent failures, not build errors |
| Assuming CI test failures were new regressions | 4 test groups failed after container fixes | These tests were previously **skipped** because the container build itself failed; fixing infrastructure made pre-existing test bugs visible | When fixing infrastructure, expect to uncover pre-existing failures that were hidden by earlier-stage breaks |

## Results & Parameters

### Configuration

```yaml
# GitHub Actions runner
runner: ubuntu-latest (Ubuntu 24.04, GLIBC 2.39)
podman_version: rootless (default on ubuntu-latest)
compose_provider: /usr/libexec/docker/cli-plugins/docker-compose
container_user: dev (UID 1001)
runner_user: runner (UID 1001)

# Key files modified
files:
  - Dockerfile                                    # ARG re-declaration
  - .github/actions/setup-container/action.yml    # Socket + chmod
  - .github/workflows/container-publish.yml       # SBOM tarball
  - justfile                                      # {{mode}} fix
  - pixi.lock                                     # Channel regeneration
```

### Verification Commands

```bash
# Check Podman compose provider
podman compose version

# Check if rootless
podman info --format '{{.Host.Security.Rootless}}'

# Test bind-mount permissions
podman compose exec -T service ls -la /workspace

# Verify ARG values in build
podman build --build-arg USER_NAME=dev -f Dockerfile --target development . 2>&1 | grep "STEP.*COPY.*chown"
```
