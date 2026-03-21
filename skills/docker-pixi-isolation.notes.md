# Session Notes: Docker Pixi Isolation Fix

## Date: 2026-03-18

## Context

Main branch had 2 failing CI workflows after PR #4927 (workflow fixes) and #4928 (alias to comptime):

1. **Comprehensive Tests** — ALL 20 test jobs failed with `error: unable to locate module 'std'` inside Docker
2. **Build Validation** — `ExTensor.split()` type conversion error: `cannot be converted from 'ExTensor' to 'ExTensor'`

## Root Cause Analysis

### Docker Stdlib Failure

The CI pipeline uses `setup-pixi` action which installs pixi on the **runner host**, creating `.pixi/envs/default/` with native Mojo binaries. The `docker-compose.yml` bind-mounts `.:/workspace:delegated`, which brings the runner's `.pixi/` into the container. The runner's native Mojo binaries can't find their stdlib inside the container's filesystem, resulting in `unable to locate module 'std'`.

### ExTensor Type Identity Split

`extensor.mojo` lines 3441/3475 used absolute imports (`from shared.core.shape import split`), while `shape.mojo` imports `ExTensor` via `from .extensor import ExTensor`. The absolute path resolves through `shared/core/__init__.mojo`, creating a different `ExTensor` type identity than the one resolved via relative imports. This caused the Mojo compiler to treat them as different types.

## Changes Made

### PR #4929: fix-docker-mojo-stdlib

**Commit 1: Docker fix + import fix**
- Created `docker/entrypoint.sh` — ensures pixi env exists inside container
- Modified `Dockerfile` — copies entrypoint into image
- Modified `docker-compose.yml` — added `workspace-pixi` named volume to dev and ci services, added entrypoint
- Fixed `shared/core/extensor.mojo` — changed absolute imports to relative imports on lines 3441 and 3475

**Commit 2: Remove native execution from CI**
- Removed `setup-pixi` from comprehensive-tests.yml (7 occurrences), build-validation.yml (1), training-tests-weekly.yml (1)
- Removed `NATIVE=1` from comprehensive-tests.yml mojo-compilation job
- Removed direct `pixi run mojo --version` call from data-utilities test job
- Replaced direct `pixi run mojo package` compilation step with `just package` (routes through Docker)

## Key Insight

The user's feedback was clear: "I don't want ANY CI/CD workflows to use native, they all must use container." Initially I only removed the explicit `NATIVE=1` but kept `setup-pixi` in some workflows. The user's directive required removing `setup-pixi` from ALL workflows that route through Docker, not just the ones with `NATIVE=1`.

## Files Modified

- `docker/entrypoint.sh` (NEW)
- `Dockerfile`
- `docker-compose.yml`
- `shared/core/extensor.mojo`
- `.github/workflows/comprehensive-tests.yml`
- `.github/workflows/build-validation.yml`
- `.github/workflows/training-tests-weekly.yml`