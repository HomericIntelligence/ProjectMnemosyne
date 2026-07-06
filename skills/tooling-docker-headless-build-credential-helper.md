---
name: tooling-docker-headless-build-credential-helper
description: "Docker build/pull over SSH, or 'docker compose pull'/'up' under sudo (or any headless/non-desktop shell), fails with 'Cannot autolaunch D-Bus without X11 $DISPLAY' because a credential helper needs a desktop keyring. Use when: (1) docker build fails getting credentials in a headless/SSH session, (2) docker compose pull/up fails with the same D-Bus/X11 error under sudo even though plain docker pull just worked in the same shell, (3) error mentions D-Bus/X11/$DISPLAY during an image pull, (4) a build or compose pull works on a desktop login but not over SSH/CI/sudo/cron."
category: tooling
date: 2026-07-06
version: "1.1.0"
user-invocable: false
history: tooling-docker-headless-build-credential-helper.history
verification: verified-local
tags:
  - docker
  - credentials
  - headless
  - ci
  - ssh
  - docker-compose
  - sudo
  - dbus
  - credsstore
---

# Tooling: Docker Headless Build Credential Helper

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-07-06 |
| Objective | Build/pull Docker images, and run `docker compose pull`/`up`, in a headless session (SSH/CI/cron, or a `sudo`-spawned shell with no desktop login) when a credential helper can't reach a desktop keyring. |
| Root cause | Docker's credential store (`credsStore` / a `docker-credential-*` helper such as the secretservice helper) tries to talk to a desktop keyring over D-Bus. In a headless or sudo'd session there's no working `DBUS_SESSION_BUS_ADDRESS`, so it errors: `error getting credentials - err: exit status 1, out: Cannot autolaunch D-Bus without X11 $DISPLAY`. Critically, this is NOT limited to sessions where `credsStore` is explicitly configured: whenever NO `~/.docker/config.json` exists at all for a user, Docker auto-detects and invokes the first `docker-credential-*` binary it finds anywhere in `PATH` — so a desktop machine with GNOME-keyring packages installed will trip this for every registry pull, even fully public/anonymous images, for any user/UID that has no docker config of its own. `sudo` does not forward `DBUS_SESSION_BUS_ADDRESS`, so a freshly sudo'd shell (even `sudo -u otheruser bash -c '...'` invoked from inside an already-root script) has no D-Bus session regardless of which UID it runs as. `docker compose` (the separate Go CLI plugin) has its own credential-resolution path independent of plain `docker pull` — fixing one does not prove the other is fixed for the same user. |
| Outcome | Build/pull and `docker compose pull` succeed in the headless/sudo session by neutralizing the credential helper (per-context, persisted config) and/or pre-caching the base image. |
| Verification | verified-local |

## When to Use

- A `docker build` fails getting credentials while running in a headless/SSH session (no desktop, no `$DISPLAY`).
- `docker compose pull` or `docker compose up` fails with the same D-Bus/X11 credential error under `sudo` (or any non-desktop shell context), even when plain `docker pull` just succeeded in that exact same shell.
- The failure occurs even though there is NO `~/.docker/config.json` file at all for the user running the command — absence of a config file does not mean no credential helper will be invoked.
- The error mentions D-Bus, X11, or `$DISPLAY` during an image pull, even for a public base image that needs no authentication.
- A build or compose pull works fine on a desktop login but fails the moment it runs over SSH, in CI, from a cron job, or via `sudo`.

## Verified Workflow

The credential helper only fails because Docker invokes it during the registry round-trip. Remove that invocation (no helper configured, for the correct user/UID context) or remove the round-trip (image already cached) and the pull proceeds.

1. For a one-off build/pull (e.g. CI job), point Docker at a credential-helper-free config: create a temp dir with a `config.json` of `{}` and export `DOCKER_CONFIG` to it. With no `credsStore` configured, the helper is never invoked for that invocation.
2. For a persistent context that will repeatedly run `docker` and/or `docker compose` under `sudo` or headlessly (e.g. a homelab upgrade script), write an explicit `~/.docker/config.json` with `"credsStore": ""` for EVERY distinct user/UID context that actually invokes docker/compose — root (if commands run via plain `sudo`), any other user reached via `sudo -u someuser ...` from within a root script, and the original interactive user if they also run docker/compose directly. Do not rely on simply leaving the file absent or `credsStore` unset — explicitly setting it to an empty string is what reliably suppresses the auto-detected helper for both `docker pull` and `docker compose pull`.
3. `docker compose` is a separate binary/code path from plain `docker pull` (the `cli-plugins/docker-compose` Go plugin) with its own credential resolution. A passing `docker pull` in a given user/shell context does NOT prove `docker compose pull` will also pass in that same context — verify both, directly, in the exact invocation context (e.g. inside the same `sudo -u someuser bash -c '...'` the real script uses), not just once with the top-level `sudo` user.
4. Pre-pull/cache the needed base image so the build/pull hits the local cache and avoids the registry round-trip that triggers the helper. Docker shares one image cache per daemon, so pulling as any user that can reach the daemon makes the image available to a later build/pull run by a different user.
5. If a build "skip if image exists" guard is in place, force a rebuild (remove the old tagged image) when you actually changed the Dockerfile, otherwise the rebuild is a no-op.

### Quick Reference

```sh
# 1. One-off build/pull: neutralize the credential helper via a temp DOCKER_CONFIG override
mkdir -p "$CLEAN_CFG"
printf '{}\n' > "$CLEAN_CFG/config.json"
export DOCKER_CONFIG="$CLEAN_CFG"
docker image inspect <base-image> >/dev/null 2>&1 || docker pull <base-image>

# 2. Persistent fix for sudo/headless/service contexts (docker AND docker compose):
#    write for EVERY user/UID context that actually runs docker or docker compose
#    (root, any `sudo -u someuser` target, the interactive user if applicable)
mkdir -p ~/.docker
cat > ~/.docker/config.json <<'EOF'
{
  "credsStore": "",
  "auths": {}
}
EOF

# 3. Verify per-context -- docker pull passing does NOT prove docker compose pull passes
docker pull hello-world && docker rmi hello-world
cd /path/to/a/docker-compose-project && docker compose pull <any-service>

# 4. Force a rebuild after a Dockerfile change (defeat a "skip if exists" guard)
docker rmi -f <image>:<tag>
```

Note: the image cache is per-daemon and shared across users; a pull by one user benefits a build/pull by another on the same host. The credential-helper fix, unlike the image cache, is NOT shared — it must be applied per user/UID `~/.docker/config.json`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Re-ran the build as-is in the headless session | Same D-Bus/X11 credential error on the base-image pull | Must neutralize the credential helper (`DOCKER_CONFIG` override) or pre-cache the image; re-running changes nothing. |
| 2 | Looked for the helper in the invoking user's `~/.docker/config.json` | The build actually ran as a DIFFERENT user whose docker config had the `credsStore` | Check the config of the user that runs the build, not your interactive user. |
| 3 | Assumed root had no `~/.docker/config.json` and thus no credential-helper problem | Absence of a config file is exactly what triggers Docker's auto-detection of any `docker-credential-*` helper found in `PATH`, even for anonymous/public pulls | Absence of config does NOT mean "no credential helper used" \| it can mean "auto-detect and use whichever helper is on `PATH`". |
| 4 | Fixed root's `~/.docker/config.json` (`credsStore: ""`), confirmed `docker pull hello-world` worked as root | `docker compose pull` from the same root-owned script STILL failed identically, because compose is a separate binary/code path not proven to honor the same fix without direct testing | `docker pull` succeeding does not prove `docker compose pull` will succeed — they have separate credential-resolution code paths and must be verified independently. |
| 5 | Rewrote scripts to run docker commands via `sudo -u originaluser bash -c '...'`, reasoning that user's interactive shell has a working D-Bus session | Still failed: `sudo -u someuser bash -c '...'` invoked from within an already-`sudo`'d root script does not inherit that user's interactive D-Bus session — it's a fresh, sessionless shell for that user too | `sudo` does not forward `DBUS_SESSION_BUS_ADDRESS` regardless of target UID; only directly testing (not assuming) `docker compose pull` in the EXACT invocation context reveals whether that user's config is actually fixed. |
| 6 | Assumed one working fix (e.g. root's config) generalized to all contexts in the script | Each distinct user/UID context that invokes docker/compose needs its OWN `~/.docker/config.json` with `credsStore: ""`; a fix for one does not propagate to another | Apply and verify the fix per user/UID context — root, any `sudo -u` target, and the interactive user — not just once. |

## Results & Parameters

- **One-off build/pull** (temp `DOCKER_CONFIG` override, e.g. CI):
  ```sh
  mkdir -p "$CLEAN_CFG"
  printf '{}\n' > "$CLEAN_CFG/config.json"
  export DOCKER_CONFIG="$CLEAN_CFG"
  docker image inspect <base-image> >/dev/null 2>&1 || docker pull <base-image>
  ```
- **Persistent fix for sudo/headless/service contexts** (docker AND docker compose), apply per user/UID:
  ```json
  {
    "credsStore": "",
    "auths": {}
  }
  ```
  written to that user's `~/.docker/config.json`.
- **Verification commands** (run per context, both required):
  ```sh
  docker pull hello-world && docker rmi hello-world          # tests plain docker CLI
  cd /path/to/a/docker-compose-project && docker compose pull <any-service>   # tests the SEPARATE compose plugin path
  ```
- **Force rebuild after a Dockerfile change** (defeat a "skip if image exists" guard):
  ```sh
  docker rmi -f <image>:<tag>
  ```
- **Note:** the image cache is per-daemon and shared across users; a pull by one user benefits a build/pull by another on the same host. The credential-helper config fix is NOT shared across users — apply it per user/UID context that actually runs docker/compose.
