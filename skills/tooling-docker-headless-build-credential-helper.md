---
name: tooling-docker-headless-build-credential-helper
description: "Docker build/pull over SSH fails with 'Cannot autolaunch D-Bus without X11 $DISPLAY' because the credential helper needs a desktop keyring. Use when: (1) docker build fails getting credentials in a headless/SSH session, (2) error mentions D-Bus/X11/$DISPLAY during image pull, (3) a build works on a desktop but not over SSH/CI."
category: tooling
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker
  - credentials
  - headless
  - ci
  - ssh
---

# Tooling: Docker Headless Build Credential Helper

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-22 |
| Objective | Build/pull Docker images in a headless (SSH/CI/cron) session when a configured credential helper can't reach a desktop keyring. |
| Root cause | Docker's credential store (`credsStore` / a `docker-credential-*` helper such as the secretservice helper) tries to talk to a desktop keyring over D-Bus. In a headless session there's no X11/D-Bus, so it errors: `error getting credentials - err: exit status 1, out: Cannot autolaunch D-Bus without X11 $DISPLAY`. This fires during an image pull (e.g. pulling a public base image) even though no auth is actually needed. |
| Outcome | Build/pull succeeds in the headless session by neutralizing the credential helper and/or pre-caching the base image. |
| Verification | verified-local |

## When to Use

- A `docker build` fails getting credentials while running in a headless/SSH session (no desktop, no `$DISPLAY`).
- The error mentions D-Bus, X11, or `$DISPLAY` during an image pull, even for a public base image that needs no authentication.
- A build works fine on a desktop login but fails the moment it runs over SSH, in CI, or from a cron job.

## Verified Workflow

The credential helper only fails because Docker invokes it during the registry round-trip. Remove that invocation (no helper configured) or remove the round-trip (image already cached) and the build proceeds.

1. Point Docker at a credential-helper-free config for the build: create a temp dir with a `config.json` of `{}` and export `DOCKER_CONFIG` to it. With no `credsStore` configured, the helper is never invoked.
2. Pre-pull/cache the needed base image so the build hits the local cache and avoids the registry round-trip that triggers the helper. Docker shares one image cache per daemon, so pulling as any user that can reach the daemon makes the image available to a later build run by a different user.
3. If a build "skip if image exists" guard is in place, force a rebuild (remove the old tagged image) when you actually changed the Dockerfile, otherwise the rebuild is a no-op.

### Quick Reference

```sh
# 1. Headless-safe build prep: neutralize the credential helper + pre-cache the base image
mkdir -p "$CLEAN_CFG"
printf '{}\n' > "$CLEAN_CFG/config.json"
export DOCKER_CONFIG="$CLEAN_CFG"
docker image inspect <base-image> >/dev/null 2>&1 || docker pull <base-image>

# 2. Force a rebuild after a Dockerfile change (defeat a "skip if exists" guard)
docker rmi -f <image>:<tag>
```

Note: the image cache is per-daemon and shared across users; a pull by one user benefits a build by another on the same host.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Re-ran the build as-is in the headless session | Same D-Bus/X11 credential error on the base-image pull | Must neutralize the credential helper (`DOCKER_CONFIG` override) or pre-cache the image; re-running changes nothing. |
| 2 | Looked for the helper in the invoking user's `~/.docker/config.json` | The build actually ran as a DIFFERENT user whose docker config had the `credsStore` | Check the config of the user that runs the build, not your interactive user. |

## Results & Parameters

- **Headless-safe build prep** (neutralize helper + warm cache):
  ```sh
  mkdir -p "$CLEAN_CFG"
  printf '{}\n' > "$CLEAN_CFG/config.json"
  export DOCKER_CONFIG="$CLEAN_CFG"
  docker image inspect <base-image> >/dev/null 2>&1 || docker pull <base-image>
  ```
- **Force rebuild after a Dockerfile change** (defeat a "skip if image exists" guard):
  ```sh
  docker rmi -f <image>:<tag>
  ```
- **Note:** the image cache is per-daemon and shared across users; a pull by one user benefits a build by another on the same host.
