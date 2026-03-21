# Session Notes: Fix All Failing CI Workflows on Main

## Date: 2026-03-20

## Context

All 3 CI workflows on ProjectOdyssey's `main` branch were failing since commit `59fa92b`.
The project uses rootless Podman with docker-compose CLI plugin on GitHub Actions ubuntu-latest runners.

## Failures Encountered

### 1. Pre-commit Checks — pixi lockfile channel mismatch
- `pixi.lock` was generated against `https://conda.modular.com/max-nightly/`
- `pixi.toml` specifies `https://conda.modular.com/max`
- `pixi install --locked` requires exact channel match
- **Fix**: `pixi install` to regenerate lockfile

### 2. Comprehensive Tests — Container build failure
- **Layer 1**: Podman socket not started on GH Actions → `systemctl --user start podman.socket`
- **Layer 2**: `USER_NAME` ARG empty in development/production Dockerfile stages
  - Error: `can't find uid for user :`
  - Root cause: ARGs don't persist across FROM boundaries in Docker/Podman
  - Fix: Re-declare `ARG USER_NAME=dev` in each stage
- **Layer 3**: `Permission denied` writing to bind-mounted workspace
  - Root cause: Rootless Podman UID namespace mapping
  - Container UID 1001 maps to host subuid ~101001, not host UID 1001
  - Host files (owned by host UID 1001) appear as root-owned inside container
  - Fix: `chmod -R a+rwX .` on host before container use
- **Layer 4**: `_ensure_build_dir` created dirs on host that container couldn't write to
  - Fix: Removed host-side mkdir; `_build-inner` already does `mkdir -p` inside container
- **Layer 5**: `_build-inner` always used "debug" mode regardless of argument
  - Root cause: `MODE="${1:-debug}"` uses bash `$1` which is empty in justfile
  - Fix: `MODE="{{mode}}"` uses just template substitution

### 3. Container Build and Publish — SBOM auth failure
- `anchore/sbom-action` tried to pull image from GHCR to scan it
- Syft couldn't authenticate (doesn't inherit Podman login credentials)
- **Fix**: Export image to tarball with `podman save`, scan the tarball

## Key Debugging Observations

- `podman compose` on GH Actions ubuntu-latest delegates to `/usr/libexec/docker/cli-plugins/docker-compose`
- This means Podman-specific compose extensions (userns_mode, etc.) are NOT supported
- The docker-compose plugin connects to Podman via the Docker API socket
- Multiple failures were layered — fixing one revealed the next
- Pre-existing Mojo test failures were hidden by the container build failure

## Timeline

1. Commit 1: pixi.lock + Podman socket + SBOM tarball → Pre-commit & Container Publish fixed
2. Commit 2: Dockerfile ARG re-declaration → Container build fixed
3. Commit 3: chmod workspace + remove host mkdir + fix justfile mode → Build Validation & Package Compilation fixed

## Approaches That Failed

1. `userns_mode: keep-id` in docker-compose.yml — docker-compose CLI plugin ignores it
2. `PODMAN_USERNS=keep-id` env var — unreliable through docker-compose API
3. `chown` inside container — overcomplicated for CI use case