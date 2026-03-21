# Session Notes: Podman From Source Install

**Date**: 2026-03-19
**Project**: ProjectOdyssey (add-podman-support branch)

## Context

PureOS 10 (Byzantium) host with GLIBC 2.31. Mojo requires GLIBC 2.32+, so all Mojo
commands must run inside a container. The justfile `_run` helper routes mojo recipes
through Docker compose, Podman, or native (CI=true/NATIVE=1).

## Problem Chain

1. Host podman was 3.0.1 (system package)
2. Kubic unstable repo for Debian_11 returns 404; stable caps at 3.4.2
3. GitHub releases for podman only ship `podman-remote-static-linux_amd64.tar.gz`
   — this is a remote client, not a container runtime
4. `podman-remote` reports version 5.8.1 and lists subcommands like `run`,
   but fails immediately with socket error when actually invoked
5. Justfile `_run` only checked version number (≥4), not whether podman actually works
6. Script was run with `sudo`, installing to `/root/.local/bin` instead of `/usr/local/bin`
7. `libseccomp-dev` was missing from build deps, causing pkg-config failure mid-build

## Resolution

- Build full podman 5.8.1 from source using Go 1.24.2
- Script detects root vs user and installs to appropriate global vs local path
- Script checks `$INSTALL_DIR/podman info` (not `which podman`) for early-exit
- Justfile `_run` adds `&& podman info &>/dev/null` to podman detection

## Files Modified

- `scripts/install-podman.sh` — complete rewrite (3 iterations)
- `justfile` — _run/_run_interactive: add podman info check, CI=true detection,
  docker run fallback, docker-build-dev recipe
- `scripts/build_mojo.sh`, `scripts/run_test_group.sh`, `scripts/run_test_mojo.sh` — new
- `pixi.toml` — add `just = "*"` so `pixi run just` works
- `README.md` — Container Setup section with Podman/Docker/Native options