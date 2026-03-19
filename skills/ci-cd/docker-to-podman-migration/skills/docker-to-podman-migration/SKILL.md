---
name: docker-to-podman-migration
description: "Migrate CI/CD from Docker to Podman for container builds, test execution, and GHCR publishing. Use when: replacing Docker with Podman in GitHub Actions, eliminating NATIVE=1 workarounds, rewriting GHCR publish workflows."
category: ci-cd
date: 2026-03-19
user-invocable: false
---

# Docker to Podman CI/CD Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-19 |
| **Objective** | Replace Docker with Podman as the sole container engine for local dev, CI test execution, and GHCR publishing |
| **Outcome** | Successfully migrated 17 CI jobs across 10 workflow files, eliminated all NATIVE=1 workarounds |
| **Scope** | GitHub Actions workflows, justfile recipes, docker-compose.yml, GHCR publishing, documentation |

## When to Use

Invoke this skill when:

1. **Migrating from Docker to Podman** in a project's CI/CD infrastructure
2. **Eliminating `NATIVE=1` workarounds** that bypass container-based test execution
3. **Rewriting GHCR publish workflows** from `docker/*` GitHub Actions to raw `podman` commands
4. **Creating a `setup-container` composite action** for Podman compose in CI
5. **Ubuntu-latest runners** already have Podman pre-installed and you want to leverage it

## Verified Workflow

### Quick Reference

```yaml
# Composite action: .github/actions/setup-container/action.yml
# 1. touch $HOME/.gitconfig (prevents bind-mount failure on CI)
# 2. Export USER_ID/GROUP_ID to GITHUB_ENV
# 3. actions/cache on ~/.local/share/containers
# 4. podman compose build <service>
# 5. podman compose up -d <service>
# 6. Wait + verify with podman compose exec -T <service> pixi run mojo --version
```

### Step 1: Create setup-container composite action

```yaml
name: Set Up Podman Container
runs:
  using: composite
  steps:
    - name: Ensure .gitconfig exists
      shell: bash
      run: touch "$HOME/.gitconfig"

    - name: Export runner UID/GID
      shell: bash
      run: |
        echo "USER_ID=$(id -u)" >> "$GITHUB_ENV"
        echo "GROUP_ID=$(id -g)" >> "$GITHUB_ENV"

    - name: Cache Podman storage
      uses: actions/cache@v5
      with:
        path: ~/.local/share/containers
        key: podman-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
        restore-keys: podman-

    - name: Build and start container
      shell: bash
      run: |
        podman compose build projectodyssey-dev
        podman compose up -d projectodyssey-dev
```

### Step 2: Migrate workflow jobs

For each job that runs Mojo commands:

1. Replace `uses: ./.github/actions/setup-pixi` with `uses: ./.github/actions/setup-container`
2. Remove `NATIVE=1` prefix from all `just` calls
3. Wrap direct `pixi run mojo ...` calls:

```yaml
# Before (native execution)
- run: pixi run mojo test -I . tests/

# After (container execution via justfile _run helper)
- run: just test-group "tests/shared/core" "test_*.mojo"

# After (direct container execution for non-justfile commands)
- run: |
    podman compose exec -T projectodyssey-dev bash -c \
      'pixi run mojo test -I . tests/'
```

### Step 3: Rewrite GHCR publish workflows

Replace Docker-specific GitHub Actions with raw Podman commands:

```yaml
# Login
- run: echo "${{ secrets.GITHUB_TOKEN }}" | podman login ghcr.io --username "${{ github.actor }}" --password-stdin

# Build (--format docker is critical for GHCR compatibility)
- run: |
    podman build --format docker -f Dockerfile.ci --target production \
      -t ghcr.io/$IMAGE_NAME:$VERSION .

# Push
- run: podman push ghcr.io/$IMAGE_NAME:$VERSION

# Cache (replaces type=gha Docker cache)
- uses: actions/cache@v5
  with:
    path: ~/.local/share/containers
    key: podman-ci-${{ hashFiles('Dockerfile.ci') }}
```

### Step 4: Update docker-compose.yml for Podman

```yaml
volumes:
  - .:/workspace:Z          # :Z for SELinux (was :delegated for Docker)
  - ${HOME:-.}/.gitconfig:/home/dev/.gitconfig:ro  # ${HOME:-.} fallback for CI
```

### Step 5: Update justfile _run helper

```just
_run cmd:
    #!/usr/bin/env bash
    set -e
    if [[ "${NATIVE:-}" == "1" ]]; then
        eval "{{cmd}}"
    elif command -v podman &>/dev/null && \
        podman compose ps -q {{podman_service}} 2>/dev/null \
        | xargs -r podman inspect -f '{{.State.Running}}' 2>/dev/null \
        | grep -q true; then
        podman compose exec -T {{podman_service}} bash -c "{{cmd}}"
    else
        echo "Error: Podman compose container not running."
        exit 1
    fi
```

### Step 6: Audit ALL workflows for completeness

```bash
# Find ALL jobs that still use setup-pixi
grep -rn 'setup-pixi' .github/workflows/*.yml

# Verify ZERO NATIVE=1 in any workflow
grep -r 'NATIVE=1' .github/workflows/*.yml

# For each setup-pixi job, classify: does it run Mojo?
# If yes → migrate to setup-container
# If no (Python-only, shell-only) → keep setup-pixi
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Migrating only the 3 main test workflows | Assumed comprehensive-tests, build-validation, training-weekly were the only Mojo-executing workflows | 9 additional jobs across 6 other workflows also ran `pixi run mojo` (release, benchmark, paper-validation, etc.) | Always audit ALL workflows with `grep -r 'pixi run mojo'` before declaring migration complete |
| Using `docker/login-action` with Podman | Docker-specific GitHub Actions don't work with Podman | These actions assume Docker daemon is running | Use raw `podman login` via shell `run:` steps instead |
| Using `type=gha` Docker cache with Podman | Docker buildx cache strategies are Docker-specific | Podman doesn't support buildx or GHA cache type | Use `actions/cache` on `~/.local/share/containers` keyed by Dockerfile hash |
| Keeping `:delegated` volume mount | Docker-only volume consistency option | Podman ignores `:delegated` and may warn | Use `:Z` for SELinux label (no-op without SELinux) |
| Single grep for unwrapped `pixi run mojo` | Grepped individual lines for `pixi run mojo` not inside `podman compose exec` | False positives: heredoc templates and multi-line `podman compose exec` blocks where the `pixi run` is on a separate line | Verify in context — check surrounding lines, not just the matching line |

## Results & Parameters

### Key Podman CI Parameters

```yaml
# Podman build for GHCR (MUST use --format docker)
podman build --format docker -f Dockerfile.ci --target <target> -t <tag> .

# Podman login
echo "$TOKEN" | podman login ghcr.io --username "$ACTOR" --password-stdin

# Cache path for Podman storage
~/.local/share/containers

# Cache key pattern
podman-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}

# Container exec pattern (non-interactive for CI)
podman compose exec -T <service> bash -c '<command>'

# Volume mount for rootless Podman
.:/workspace:Z

# docker-compose.yml filename: keep as-is (podman compose reads it natively)
```

### Files Typically Modified

| File | Change |
|------|--------|
| `.github/actions/setup-container/action.yml` | **NEW** — Podman compose setup for CI |
| `.github/workflows/*.yml` | `setup-pixi` → `setup-container` for Mojo jobs |
| `justfile` | `docker-*` → `podman-*` recipes, `_run` helper |
| `docker-compose.yml` | `:delegated` → `:Z`, gitconfig mount fix |
| `scripts/run_mojo.sh` | Remove Docker fallback |
| `CLAUDE.md` / docs | Docker → Podman references |

### ubuntu-latest Podman Availability

- Ubuntu 24.04 (ubuntu-latest as of 2026): Podman 4.x pre-installed
- No need to install Podman in CI
- `podman compose` available (uses podman-compose or docker-compose backend)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4991 | Full Docker→Podman migration, 17 CI jobs, GHCR publishing |
