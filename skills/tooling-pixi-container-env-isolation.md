---
name: tooling-pixi-container-env-isolation
description: "Fix host/container pixi environment collision and pixi binary shadowing in Docker/Podman.
  Use when: (1) just build fails with Permission denied reading .pixi/envs/default inside a Podman
  container, (2) rootless Podman UID mapping (host UID 1000 -> container UID 0) corrupts pixi env
  ownership, (3) a named Docker volume was used to isolate .pixi/ but ownership still breaks after
  restarts, (4) container fails with 'pixi: command not found' after moving pixi-cache volume
  mountpoint to ~/.pixi/ (which shadows the pixi binary installed during image build)."
category: tooling
date: 2026-05-03
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: tooling-pixi-container-env-isolation.history
tags:
  - pixi
  - podman
  - docker
  - container
  - env-isolation
  - uid-mapping
  - workspace-collision
  - detached-environments
  - volume-shadowing
---

# Tooling: Pixi Container Environment Isolation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Fix `just build` failing with `Permission denied (os error 13)` when the pixi env at `.pixi/envs/default` is shared between host and rootless Podman container; also fix `pixi: command not found` when the pixi-cache volume is mounted at the wrong path |
| **Outcome** | Successful — CI passed (AddressSanitizer Tests, Build Validation, Mojo Package Compilation) after both fixes |
| **Verification** | verified-ci (PR #5347, PR #5348) |
| **Root Cause 1** | Host and container share the same pixi env path (`<workspace>/.pixi/envs/default`). Rootless Podman UID mapping corrupts ownership. |
| **Root Cause 2** | After enabling `detached-environments` and removing `workspace-pixi`, the `pixi-cache` volume was still mounted at `~/.pixi/` — shadowing the pixi binary installed at `~/.pixi/bin/pixi` during image build. |
| **History** | [changelog](./tooling-pixi-container-env-isolation.history) |

## When to Use

- `just build` (or any pixi command inside the container) fails with `Permission denied (os error 13)`
  and the path in the error points to `.pixi/envs/default/`
- Rootless Podman maps the host user (UID 1000) to container root (UID 0), or vice-versa
- The workspace is bind-mounted into the container (e.g., `.:/workspace`) and both host and
  container run `pixi install` pointing at the same `.pixi/envs/default/`
- A named Docker/Podman volume was previously used to shadow `.pixi/` but ownership corruption
  resurfaces after container restarts or volume recreation
- Container fails with `pixi: command not found` even though pixi was installed during image build
- The `pixi-cache` named volume is mounted at `~/.pixi/` (wrong) instead of `~/.cache/pixi` (correct)
- You want to permanently eliminate the path collision rather than work around it

## Verified Workflow

### Quick Reference

1. **Create `.pixi/config.toml`** in the workspace root (commit to repo):

```toml
[detached-environments]
# Relocates pixi envs from <workspace>/.pixi/envs/ to per-user cache dirs.
# Host: ~/.cache/pixi/envs/<hash>/
# Container: /home/dev/.cache/pixi/envs/<hash>/
# A convenience symlink is left at <workspace>/.pixi/envs -> <cache>/envs.
detached-environments = true
```

2. **Remove the `workspace-pixi` named volume** AND correct the `pixi-cache` mountpoint:

```yaml
# BEFORE (broken — two problems):
services:
  myservice:
    volumes:
      - .:/workspace:delegated
      - workspace-pixi:/workspace/.pixi   # Problem 1: shadows host .pixi/
      - pixi-cache:/home/dev/.pixi        # Problem 2: shadows pixi binary!

volumes:
  workspace-pixi:
    driver: local
  pixi-cache:
    driver: local

# AFTER (correct):
services:
  myservice:
    volumes:
      - .:/workspace:delegated
      - pixi-cache:/home/dev/.cache/pixi  # CORRECT: mount at PIXI_CACHE_DIR, not ~/.pixi/

volumes:
  pixi-cache:
    driver: local
```

**Critical**: Mount `pixi-cache` at `~/.cache/pixi` (the `PIXI_CACHE_DIR`), NOT at `~/.pixi/`.
Mounting at `~/.pixi/` shadows the pixi binary installed at `~/.pixi/bin/pixi` during image
build, causing `pixi: command not found` at container startup.

3. **Update `docker/entrypoint.sh`** — replace the mojo binary path check with `pixi info`:

```bash
# BEFORE (brittle: hardcodes .pixi/envs/default path):
if [ ! -f .pixi/envs/default/bin/mojo ]; then
    echo "Initializing pixi environment inside container..."
    pixi install
fi

# AFTER (works with detached-environments; resolves the real env path):
MOJO_BIN=$(pixi info --json 2>/dev/null | python3 -c \
    "import sys, json; d=json.load(sys.stdin); \
     print(d.get('environments_info',[{}])[0].get('env_location','') + '/bin/mojo')" 2>/dev/null)
if [ -z "$MOJO_BIN" ] || [ ! -f "$MOJO_BIN" ]; then
    echo "Initializing pixi environment inside container..."
    pixi install
fi
exec "$@"
```

4. **Add a pre-commit guard hook** in `.pre-commit-config.yaml` to prevent regression
   (detect if `.pixi/envs` is a real directory instead of the expected symlink):

```yaml
- id: no-pixi-env-in-workspace
  name: Ensure .pixi/envs is a symlink (detached-environments)
  entry: >-
    bash -c
    'if [ -d .pixi/envs ] && [ ! -L .pixi/envs ]; then
    echo "ERROR .pixi/envs/ is a real directory (not a symlink).";
    echo "Run: pixi config set detached-environments true --local";
    exit 1; fi'
  language: system
  pass_filenames: false
  always_run: true
```

5. **Tear down volumes and rebuild**:

```bash
podman compose down -v     # Remove old named volumes including workspace-pixi
podman compose build --no-cache
podman compose up -d
just build                  # Should succeed
```

### Detailed Steps

1. **Diagnose the collision** — confirm both host and container resolve the same path:

   ```bash
   # On host:
   ls -la .pixi/envs/default/  # Shows env owned by UID 1000

   # Inside container:
   podman compose exec myservice bash -c "ls -la /workspace/.pixi/envs/default/"
   # Same path, now owned by UID 0 (root inside container) or shows EPERM
   ```

2. **Diagnose pixi binary shadowing** — check if pixi-cache is mounted at the wrong path:

   ```bash
   # Check docker-compose.yml for the wrong mount:
   grep "pixi-cache" docker-compose.yml
   # If it shows ~/.pixi  (not ~/.cache/pixi), that's the bug

   # Confirm the binary exists in the image (before volume mount shadows it):
   podman run --rm <image> ls /home/dev/.pixi/bin/pixi   # Should exist
   # With the wrong volume mount, it becomes invisible at runtime
   ```

3. **Enable `detached-environments`** — create `.pixi/config.toml`:

   ```bash
   mkdir -p .pixi
   cat > .pixi/config.toml <<'EOF'
   [detached-environments]
   detached-environments = true
   EOF
   git add .pixi/config.toml
   ```

   After this, `pixi install` on the **host** will store the env in
   `~/.cache/pixi/envs/<hash>/` and leave a symlink at `.pixi/envs → ~/.cache/pixi/envs`.
   The bind-mounted workspace still contains `.pixi/envs`, but it is now a **symlink** —
   the container cannot follow it to the host's cache dir, so it installs its own env
   under `/home/dev/.cache/pixi/envs/<hash>/` (inside the container's pixi-cache volume).

4. **Remove the `workspace-pixi` named volume** and fix the `pixi-cache` mountpoint —
   edit `docker-compose.yml` as shown above. The volume must target `~/.cache/pixi`
   (the `PIXI_CACHE_DIR`), which covers both the pixi package cache and the detached env
   storage — without hiding the pixi binary.

5. **Update entrypoint.sh** — the old check `[ ! -f .pixi/envs/default/bin/mojo ]` no longer
   works because the env is no longer at that path. Use `pixi info --json` to locate the
   real env path dynamically.

6. **Add the pre-commit guard** — prevents future contributors from accidentally breaking
   the detached-environments config. Note the YAML `>-` block scalar is required when the
   `entry:` value contains a colon (e.g., `echo "ERROR: ..."`); a double-quoted string will
   cause `yaml.scanner.ScannerError: mapping values are not allowed here`.

7. **Handle rebase conflicts** — if workflow files have conflicts over `actions/checkout`
   SHA versions, always take the **newer SHA from `main`** (e.g., v6.0.2 over v6.0.1).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `chown -R dev:dev .pixi/` | Re-own the pixi env inside the container on startup | Doesn't survive container restarts; the named volume gets repopulated with root-owned files on next `pixi install` run inside the container | Ownership fixes are transient; the architectural problem (shared path) must be fixed |
| `chmod -R a+rwX .` | Grant world-write on the workspace | Fixes the immediate EPERM but the host and container envs still collide and can corrupt each other's packages | chmod is a band-aid; path isolation is the real fix |
| `PIXI_ENV_DIR` env var | Set env var to redirect pixi env path | Pixi does not support `PIXI_ENV_DIR`; only `PIXI_DETACHED_ENVIRONMENTS=true` env var (or the config file) work | Check pixi's supported env vars in `pixi --help env` before trying custom overrides |
| Named Docker volume (`workspace-pixi`) | Shadow `.pixi/` with an empty named volume | Works initially but rootless Podman UID mapping still corrupts ownership after volume recreation; fragile across host/container `pixi install` races | Named volumes solve the bind-mount problem but not the ownership problem under rootless Podman |
| `entry: "bash -c 'echo ERROR: ...'"` in pre-commit | Double-quoted entry string with colons | `yaml.scanner.ScannerError: mapping values are not allowed here` — colons in YAML values require quoting or block scalars | Use `>-` block scalar for `entry:` values that contain colons or other YAML special chars |
| `[ -d .pixi/envs ]` in pre-commit hook | Check only for directory existence | Also triggers on the convenience symlink pixi creates; hook fires even after a correct `detached-environments` setup | Always check `[ -d .pixi/envs ] && [ ! -L .pixi/envs ]` to allow the symlink |
| `pixi-cache:/home/dev/.pixi` volume mount | Mount pixi-cache at `~/.pixi/` to cache pixi data | An empty named volume at `~/.pixi/` at container startup shadows `~/.pixi/bin/pixi` installed during image build, causing `pixi: command not found` in all CI jobs | Mount at `~/.cache/pixi` (the `PIXI_CACHE_DIR`), not `~/.pixi/` — the binary lives at `~/.pixi/bin/pixi` and must not be shadowed |

## Results & Parameters

### Key Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Pixi config file | `.pixi/config.toml` | Committed to repo |
| Config key | `detached-environments = true` | Under `[detached-environments]` section |
| Alternative env var | `PIXI_DETACHED_ENVIRONMENTS=true` | Can be set in `docker-compose.yml` instead of config file |
| Pixi cache volume mount point | `~/.cache/pixi` | `PIXI_CACHE_DIR` — NOT `~/.pixi/` (that shadows the binary!) |
| Pixi binary location | `~/.pixi/bin/pixi` | Installed by Dockerfile; must not be shadowed by a named volume |
| Guard hook language | `system` | Not `python` or `script` |
| Guard hook flags | `always_run: true`, `pass_filenames: false` | Required for repo-wide checks |

### Host vs Container Env Paths After Fix

```text
Host:
  .pixi/envs              → ~/.cache/pixi/envs/          (symlink, pixi created)
  ~/.cache/pixi/envs/<hash>/  = actual host pixi env

Container (inside bind-mounted workspace):
  .pixi/envs              → dangling symlink (host cache not accessible)
  /home/dev/.cache/pixi/envs/<hash>/  = actual container pixi env (in pixi-cache volume)

pixi binary (container):
  ~/.pixi/bin/pixi        = installed by Dockerfile (NOT in pixi-cache volume)
  ~/.cache/pixi/          = pixi-cache volume (caches packages + detached envs)
```

Both sides install their own isolated envs; no path collision, no ownership conflict.
The pixi binary is not shadowed because the cache volume mounts at `~/.cache/pixi`, not `~/.pixi/`.

### docker-compose.yml After Fix

```yaml
services:
  projectodyssey-dev:
    volumes:
      - .:/workspace:delegated
      - pixi-cache:/home/dev/.cache/pixi  # Cache pixi packages + detached envs (NOT ~/.pixi/)
    entrypoint: ["/usr/local/bin/entrypoint.sh"]

volumes:
  pixi-cache:
    driver: local
  # workspace-pixi REMOVED
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5347 — env isolation fix (`detached-environments = true`) | Rootless Podman, host UID 1000, container UID 0, bind-mounted workspace |
| ProjectOdyssey | PR #5348 — pixi binary shadowing fix (volume mountpoint correction) | `pixi-cache` moved from `~/.pixi/` to `~/.cache/pixi`; all CI jobs passed |

## References

- [Pixi detached-environments docs](https://prefix.dev/docs/pixi/configuration#detached-environments)
- [docker-pixi-isolation](docker-pixi-isolation.md) — earlier named-volume approach (superseded by this skill for rootless Podman setups)
- [docker-mojo-uid-mismatch-crash-fix](docker-mojo-uid-mismatch-crash-fix.md) — companion skill for UID mismatch crashes in Mojo runtime
