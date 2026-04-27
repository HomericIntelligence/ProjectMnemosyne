---
name: docker-to-podman-migration
description: 'Migrate a project from Docker to Podman, removing NATIVE=1 escape hatches.
  Use when: (1) replacing Docker with Podman in GitHub Actions or Makefile/justfile
  ecosystems, (2) eliminating NATIVE=1 workarounds that bypass container-based builds,
  (3) rewriting GHCR publish workflows, (4) adopting Containerfile over Dockerfile in
  C++/CMake or Mojo/Python projects.'
category: ci-cd
date: 2026-04-26
version: 1.1.0
user-invocable: false
verification: verified-local
history: docker-to-podman-migration.history
tags: [podman, docker, containerfile, makefile, justfile, native, migration, cmake, cpp]
---
# Docker to Podman Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 (amended; original 2026-03-19) |
| **Objective** | Replace Docker with Podman as the sole container engine for local dev, CI test execution, GHCR publishing, and Makefile/justfile build systems |
| **Outcome** | Successfully migrated ProjectOdyssey (17 CI jobs, GHCR publishing) and ProjectKeystone (Makefile+justfile, NATIVE=1 removal, Containerfile adoption) |
| **Verification** | verified-local (ProjectKeystone PR #499); verified-ci (ProjectOdyssey PR #4991) |
| **History** | [changelog](./docker-to-podman-migration.history) |

## When to Use

Invoke this skill when:

1. **Migrating from Docker to Podman** in a project's CI/CD infrastructure (GitHub Actions or local Makefile)
2. **Eliminating `NATIVE=1` workarounds** that bypass container-based test/build execution
3. **Rewriting GHCR publish workflows** from `docker/*` GitHub Actions to raw `podman` commands
4. **Creating a `setup-container` composite action** for Podman compose in CI
5. **Ubuntu-latest runners** already have Podman pre-installed and you want to leverage it
6. **Adopting `Containerfile`** (Podman-native name) over `Dockerfile` in a C++/CMake project
7. **Replacing `docker-compose` CLI** with `podman compose` in a Makefile or justfile

## Verified Workflow

### Quick Reference

```bash
# --- GitHub Actions / Mojo / Python projects ---
# Composite action: .github/actions/setup-container/action.yml
# 1. touch $HOME/.gitconfig (prevents bind-mount failure on CI)
# 2. Export USER_ID/GROUP_ID to GITHUB_ENV
# 3. actions/cache on ~/.local/share/containers
# 4. podman compose build <service>
# 5. podman compose up -d <service>
# 6. Verify: podman compose exec -T <service> pixi run mojo --version

# --- C++/CMake / Makefile / justfile projects ---
# 1. Rename Dockerfile → Containerfile
# 2. Copy .dockerignore → .containerignore
# 3. Replace Makefile DOCKER_CHECK/DOCKER_PREFIX vars with CONTAINER_CHECK/CONTAINER_PREFIX
# 4. Remove ifeq ($(NATIVE),1) block entirely
# 5. Remove %.native pattern rule
# 6. Rename docker.* targets → container.*
# 7. Strip NATIVE=1 from all justfile make calls
# 8. Update docker-compose → podman compose in justfile
```

### Step 1: Create setup-container composite action (GitHub Actions / Mojo projects)

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

### Step 2: Migrate workflow jobs (GitHub Actions)

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

### Step 5: Update justfile _run helper (Mojo/Python projects)

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

### Step 7: C++/CMake Makefile migration (remove NATIVE=1 escape hatch)

This pattern applies to C++/CMake projects (e.g., ProjectKeystone) that use a
Makefile+justfile build system with a Docker/Podman prefix variable pattern.

```makefile
# BEFORE: ifeq block with NATIVE=1 escape hatch
ifeq ($(NATIVE),1)
    DOCKER_CHECK :=
    DOCKER_PREFIX :=
else
    DOCKER_CHECK := docker-compose up -d dev >/dev/null 2>&1 || true;
    DOCKER_PREFIX := docker-compose exec -T dev
endif

# AFTER: unconditional podman compose (no escape hatch)
CONTAINER_CHECK := podman compose up -d dev >/dev/null 2>&1 || true;
CONTAINER_PREFIX := podman compose exec -T dev
```

Makefile target body pattern (no change needed besides variable rename):

```makefile
compile:
	@$(CONTAINER_CHECK) $(CONTAINER_PREFIX) cmake --build --preset $(PRESET) -- -j$(NPROC)

test:
	@$(CONTAINER_CHECK) $(CONTAINER_PREFIX) ctest --preset $(PRESET) --output-on-failure
```

Also remove the `%.native` pattern rule (the escape hatch entry point):

```makefile
# DELETE this rule entirely:
# %.native:
#     @$(MAKE) $* NATIVE=1
```

Rename Docker management targets:

```makefile
# BEFORE                    AFTER
docker.build:               container.build:
docker.up:                  container.up:
docker.down:                container.down:
docker.shell:               container.shell:
```

### Step 8: justfile for C++/CMake projects

```bash
# Remove NATIVE=1 from all make calls:
# BEFORE: make compile NATIVE=1
# AFTER:  make compile

# Update docker-compose references:
sed -i 's/docker-compose/podman compose/g' justfile

# Update management target names:
# BEFORE: make docker.up
# AFTER:  make container.up
```

### Step 9: Adopt Containerfile (C++/CMake projects)

```bash
# Rename Dockerfile → Containerfile (podman looks for this first)
cp Dockerfile Containerfile
git rm Dockerfile
git add Containerfile

# Copy .dockerignore → .containerignore (podman reads this preferentially)
cp .dockerignore .containerignore
git add .containerignore

# Update CODEOWNERS: Dockerfile → Containerfile
# docker-compose.yml files do NOT need renaming — podman compose reads them natively
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Migrating only the 3 main test workflows | Assumed comprehensive-tests, build-validation, training-weekly were the only Mojo-executing workflows | 9 additional jobs across 6 other workflows also ran `pixi run mojo` (release, benchmark, paper-validation, etc.) | Always audit ALL workflows with `grep -r 'pixi run mojo'` before declaring migration complete |
| Using `docker/login-action` with Podman | Docker-specific GitHub Actions don't work with Podman | These actions assume Docker daemon is running | Use raw `podman login` via shell `run:` steps instead |
| Using `type=gha` Docker cache with Podman | Docker buildx cache strategies are Docker-specific | Podman doesn't support buildx or GHA cache type | Use `actions/cache` on `~/.local/share/containers` keyed by Dockerfile hash |
| Keeping `:delegated` volume mount | Docker-only volume consistency option | Podman ignores `:delegated` and may warn | Use `:Z` for SELinux label (no-op without SELinux) |
| Single grep for unwrapped `pixi run mojo` | Grepped individual lines for `pixi run mojo` not inside `podman compose exec` | False positives: heredoc templates and multi-line `podman compose exec` blocks where the `pixi run` is on a separate line | Verify in context — check surrounding lines, not just the matching line |
| Renaming docker-compose.yml to podman-compose.yml | Considered renaming to match Podman naming conventions | Not needed — both `podman compose` and `podman-compose` read `docker-compose.yml` natively | Keep compose YAML filenames as-is; only the CLI changes, not the file format |
| Using symlink Dockerfile → Containerfile | Considered keeping `Dockerfile` with a symlink to `Containerfile` | Unnecessary complexity | Rename directly to `Containerfile`; Podman finds it first and docker-compose/podman-compose fall back correctly |
| Post-migration: pre-commit reverts on older branches | After merging the Podman PR, branches created before the merge had `NATIVE=1` reverted by pre-commit linter | The branch's justfile/Makefile were at the pre-migration state; checking them out caused linter to revert them | After this migration, any older branches need `git rebase origin/main` before the linter runs; rebase, not cherry-pick |

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

### C++/CMake Makefile Variables

```bash
# Verify podman is available
which podman
podman --version        # tested with 4.9.3
podman compose version  # uses Docker Compose v2.x engine

# Build the dev image
podman compose build dev

# Start dev container
podman compose up -d dev

# Run a command inside the container
podman compose exec -T dev cmake --preset debug

# All just targets now route through container (no NATIVE=1 needed)
just build    # → make compile → podman compose exec -T dev cmake ...
just test     # → make test   → podman compose exec -T dev ctest ...
just lint     # → make lint   → podman compose exec -T dev ./scripts/run_static_analysis.sh
just format   # → make format → podman compose exec -T dev bash -c "find ... | xargs clang-format"
```

### Files Typically Modified

| File | Change |
|------|--------|
| `.github/actions/setup-container/action.yml` | **NEW** — Podman compose setup for CI |
| `.github/workflows/*.yml` | `setup-pixi` → `setup-container` for Mojo jobs |
| `justfile` | `docker-*` → `podman-*` / `container-*` recipes, remove `NATIVE=1` |
| `docker-compose.yml` | `:delegated` → `:Z`, gitconfig mount fix |
| `Makefile` | `DOCKER_CHECK/PREFIX` → `CONTAINER_CHECK/PREFIX`, remove `%.native` rule |
| `Dockerfile` → `Containerfile` | Rename (Podman prefers `Containerfile`) |
| `.containerignore` | **NEW** — copy of `.dockerignore` for Podman |
| `CODEOWNERS` | `Dockerfile` → `Containerfile` |
| `scripts/run_mojo.sh` | Remove Docker fallback |
| `CLAUDE.md` / docs | Docker → Podman references |

### ubuntu-latest Podman Availability

- Ubuntu 24.04 (ubuntu-latest as of 2026): Podman 4.x pre-installed
- No need to install Podman in CI
- `podman compose` available (uses podman-compose or docker-compose backend)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4991 | Full Docker→Podman migration, 17 CI jobs, GHCR publishing; verified-ci |
| ProjectKeystone | PR #499 (2026-04-26) | Makefile+justfile migration, NATIVE=1 removal, Containerfile adoption; verified-local |
