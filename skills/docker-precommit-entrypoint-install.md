---
name: docker-precommit-entrypoint-install
description: "Pre-commit git hooks must be installed in entrypoint.sh (container startup), not Dockerfile RUN (image build), because .git/ is only accessible after bind-mount volumes are active. Use when: (1) setting up pre-commit in Docker/Podman with a bind-mounted workspace, (2) debugging why git hooks are not running inside containers, (3) pre-commit install appears to succeed during Docker build but hooks don't fire at runtime, (4) `core.hooksPath` git config blocks hook installation with a 'Cowardly refusing' error."
category: tooling
date: 2026-04-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [docker, podman, pre-commit, git-hooks, bind-mount, entrypoint, container]
---
# Pre-Commit Hook Installation in Bind-Mounted Containers

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Objective** | Ensure pre-commit git hooks are installed and run inside a Docker/Podman container where the project workspace is bind-mounted at runtime (not COPY'd at image build time) |
| **Outcome** | Success — hooks fire correctly on `git commit` inside the container; CI validates them on every push |
| **Verification** | verified-ci |

## When to Use

- Your project workspace is bind-mounted into the container (e.g., `-v $(pwd):/workspace`) rather than `COPY`'d during build
- `pixi run pre-commit install` is in your `Dockerfile` but hooks are not running at commit time
- Pre-commit install in `Dockerfile` appears to succeed but `.git/hooks/pre-commit` is missing at runtime
- `git commit` inside the container skips all hooks silently
- `pixi run pre-commit install` fails with: `Cowardly refusing to install hooks with 'core.hooksPath' set`
- Setting up a new project that uses Docker/Podman for development with a shared host workspace

## Verified Workflow

### Quick Reference

```bash
# In docker/entrypoint.sh — install hooks at container startup, not in Dockerfile
if [ -d ".git" ] && [ ! -f ".git/hooks/pre-commit" ]; then
    echo "Installing pre-commit git hooks..."
    pixi run pre-commit install --install-hooks 2>/dev/null || true
fi

# If core.hooksPath is set and blocking install, unset it first:
git config --unset-all core.hooksPath
```

### Step 1: Identify the Problem

Symptoms of Dockerfile-based install silently failing:

```bash
# Inside the running container:
ls -la .git/hooks/pre-commit   # missing or stub
git commit -m "test"           # no hooks fire
```

Root cause: `Dockerfile RUN` executes at IMAGE BUILD time before the bind-mount exists.
At that point, `/workspace/.git/` is either empty or from a stale base image layer.
When the volume is mounted at `podman run` / `docker run` time, the host `.git/`
directory shadows the filesystem layer, and the hooks installed during build are gone.

### Step 2: Remove the Dockerfile install

Delete any pre-commit install line from your `Dockerfile`:

```diff
-RUN pixi run pre-commit install --install-hooks
```

Removing it prevents confusion — it never worked in a bind-mount setup anyway.

### Step 3: Add install to entrypoint.sh

Add the following block to `docker/entrypoint.sh`, before the main `exec` call:

```bash
# Install pre-commit hooks into the git repo if not already installed.
# This must run at container startup (not Dockerfile build) because the
# workspace is bind-mounted at runtime and .git/hooks is inside the mount.
if [ -d ".git" ] && [ ! -f ".git/hooks/pre-commit" ]; then
    echo "Installing pre-commit git hooks..."
    pixi run pre-commit install --install-hooks 2>/dev/null || true
fi
```

Key properties of this block:
- **Idempotent**: The `[ ! -f ".git/hooks/pre-commit" ]` guard means already-installed
  hooks are never reinstalled (fast container restarts).
- **Non-blocking**: `|| true` prevents entrypoint failure if pre-commit is temporarily
  unavailable (e.g., first-time pixi env bootstrap).
- **Scoped**: The `[ -d ".git" ]` guard skips installation in CI runners or ephemeral
  containers where no git repo is present.

### Step 4: Handle core.hooksPath (if needed)

If `pixi run pre-commit install` fails with:

```
Cowardly refusing to install hooks with 'core.hooksPath' set
```

This means `core.hooksPath` was set to a non-standard path (e.g., by a previous automation run). Clear it:

```bash
git config --unset-all core.hooksPath
```

Then retry install. Verify:

```bash
git config --get core.hooksPath   # should return nothing
ls -la .git/hooks/pre-commit      # should exist now
```

### Step 5: Verify hooks fire

```bash
# Inside the container:
just podman-up   # or: docker compose up -d / podman compose up -d
just shell       # open container shell

# Verify hook is installed:
ls -la .git/hooks/pre-commit

# Test by staging and committing a trivial change:
git commit --allow-empty -m "test: verify pre-commit hooks fire in container"
# Expected: pre-commit runs and passes (or shows actual hook output)
```

### Step 6: CI verification

In CI (GitHub Actions / Podman-based workflows), the same `entrypoint.sh` runs before
each test job. Pre-commit hooks installed by it are validated by the pre-commit CI workflow:

```yaml
# .github/workflows/pre-commit.yml
- name: Run pre-commit hooks
  run: |
    podman compose exec -T <service> pixi run pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `RUN pixi run pre-commit install` in Dockerfile | Added install command to the image build | At build time the workspace bind-mount does not exist; `.git/` is absent or a stale base-image layer. The bind-mount at `podman run` time shadows the layer, erasing the installed hooks. | `RUN` in Dockerfile is image-build time; volume mounts are container-start time. Never install hooks into a bind-mounted path during image build. |
| `RUN pixi run pre-commit install --install-hooks` silently "succeeds" | Command returned exit 0 during build | pre-commit found and used a temporary `.git/` stub from the base image layer. Hooks were written to a layer that got shadowed at runtime. | Exit 0 does not mean hooks are usable — verify with `ls .git/hooks/pre-commit` inside a running container after the mount is active. |
| `COPY . /workspace` at build time + Dockerfile install | Copied the entire repo to avoid the bind-mount problem | Makes the image embed a snapshot of the repo, breaking live development workflows; `.git/` is still read-only at build time. | For development containers, bind-mount is the correct pattern; Dockerfile install is not the right fix. |
| Calling `git config core.hooksPath .git/hooks` | Tried to explicitly set hooks path to avoid issues | If `core.hooksPath` is set to a path pre-commit does not recognise as the default, pre-commit refuses to install. | Do not set `core.hooksPath` unless you have a specific alternate-hooks-directory use case. If it is set, unset it before running `pre-commit install`. |

## Results & Parameters

### Verified entrypoint.sh Snippet

```bash
#!/usr/bin/env bash
set -euo pipefail

# Install pre-commit hooks into the git repo if not already installed.
# This must run at container startup (not Dockerfile build) because the
# workspace is bind-mounted at runtime and .git/hooks is inside the mount.
if [ -d ".git" ] && [ ! -f ".git/hooks/pre-commit" ]; then
    echo "Installing pre-commit git hooks..."
    pixi run pre-commit install --install-hooks 2>/dev/null || true
fi

exec "$@"
```

### Expected Output on First Container Start

```
Installing pre-commit git hooks...
pre-commit installed at .git/hooks/pre-commit
pre-commit installed at .git/hooks/pre-push
```

### Expected Output on Subsequent Container Starts

(silent — the guard `[ ! -f ".git/hooks/pre-commit" ]` prevents reinstall)

### core.hooksPath Diagnosis & Fix

| Symptom | Diagnosis Command | Fix |
|---------|-------------------|-----|
| `Cowardly refusing to install hooks with 'core.hooksPath' set` | `git config --get core.hooksPath` | `git config --unset-all core.hooksPath` |
| Hooks not firing after install | `ls -la .git/hooks/pre-commit` | Re-run `pixi run pre-commit install` |
| Hook exists but container startup is slow | Check `--install-hooks` flag | Drop `--install-hooks` for faster cold start; hooks download on first `git commit` instead |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Commit `0d6b2272` — `fix(docker): install pre-commit git hooks at container startup` | Fixed dev-container workflow where `docker/entrypoint.sh` was missing the install block; hooks now fire on every `git commit` inside the Podman dev container |

## References

- [Pre-commit documentation — installation](https://pre-commit.com/#installation)
- [docker-to-podman-migration.md](docker-to-podman-migration.md) — related skill for Podman CI/CD migration
- [document-hook-glibc-incompatibility.md](document-hook-glibc-incompatibility.md) — GLIBC-aware mojo-format hook wrapper
