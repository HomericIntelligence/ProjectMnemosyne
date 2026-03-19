---
name: dockerfile-cargo-to-prebuilt-binary
description: 'Replace slow cargo install in Dockerfiles with pre-built binary installers
  to eliminate Rust compilation. Use when: Dockerfile uses cargo install for a tool
  (just, ripgrep, fd, etc.) that provides an official binary installer, and builds
  are slow due to Rust compilation overhead.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# dockerfile-cargo-to-prebuilt-binary

Replace `cargo install <tool>` in Dockerfiles with official pre-built binary installers to
eliminate slow Rust compilation from Docker build time.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Issue | #3152 |
| PR | #3343 |
| Objective | Remove `cargo install just --version 1.14.0` and `cargo` apt dep from Dockerfile; pin Pixi version in Dockerfile.ci |
| Outcome | Success — cargo dep removed, just install moved to base stage as root using pre-built binary, Pixi pinned to 0.65.0 in both CI stages |
| Category | ci-cd |
| Project | ProjectOdyssey |

## When to Use

- Dockerfile has `cargo install <tool>` and that tool provides an official binary installer
- Docker builds are slow due to Rust compilation (cargo install compiles from source)
- `cargo` is only in the image as a transitive dep to install one tool
- You want to reduce Docker image size (no Rust toolchain needed in final image)
- Dockerfile installs `just`, `ripgrep`, `fd`, `bat`, `starship`, or other tools that publish pre-built binaries
- Multi-stage Dockerfile where `just` (or similar) is needed in a base stage shared across all targets

## Decision Criteria: Where to install the binary

| Scenario | Install location | Notes |
|----------|-----------------|-------|
| Tool needed by all stages | Base stage, as root, to `/usr/local/bin` | Available everywhere, no sudo needed |
| Tool needed only by dev user | Development stage, to `~/.local/bin` | Must be on user PATH |
| Tool needed only in CI | CI stage, to `/usr/local/bin` as root | Smaller base image |

**Key insight**: If the tool was previously installed in a user stage with `cargo` (which runs
as that user), but the new installer writes to `/usr/local/bin`, it must run as root. Move it
to the base stage.

## Verified Workflow

### Step 1: Identify what cargo is used for

```bash
grep -n "cargo" Dockerfile
```

If `cargo install <tool>` is the only cargo usage, it's safe to remove the `cargo` apt dep entirely.

### Step 2: Find the official binary installer for the tool

For `just`:

```text
https://just.systems/install.sh
Install command: curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

For other tools, check the tool's GitHub releases page for an `install.sh` or equivalent.

### Step 3: Determine where in the Dockerfile to install

If the tool is needed across multiple stages (base, development, ci, production), install in
the base stage as root — before the user is created. This avoids permission issues.

### Step 4: Remove cargo from apt deps and PATH

```dockerfile
# BEFORE
RUN apt-get install -y ... cargo ...
ENV PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH:$HOME/.cargo/bin"

# AFTER
RUN apt-get install -y ...   # cargo removed
ENV PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH"  # .cargo/bin removed
```

### Step 5: Replace cargo install with pre-built binary

```dockerfile
# BEFORE (in development stage, as dev user)
RUN cargo install just --version 1.14.0

# AFTER (in base stage, as root — before USER switch)
# Install just tool (pre-built binary, much faster than cargo install)
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

### Step 6: Pin Pixi version in Dockerfile.ci (bonus: reproducible builds)

If Dockerfile.ci uses unpinned `curl | bash` for Pixi, pin it:

```dockerfile
# BEFORE
RUN curl -fsSL https://pixi.sh/install.sh | bash

# AFTER
ENV PIXI_VERSION=0.65.0
# ...
RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

Check current pixi version with: `pixi --version`

The `PIXI_VERSION` env var is supported by the official pixi installer script.
Add it to each stage that installs pixi independently (pixi doesn't copy across stages).

### Step 7: Verify with pre-commit

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

The `mojo-format` hook may fail due to GLIBC version mismatches in non-Docker environments —
this is a known environment constraint unrelated to Dockerfile changes.

### Step 8: Commit and PR

```bash
git add Dockerfile Dockerfile.ci
git commit -m "fix(docker): replace cargo install just with pre-built binary, pin Pixi version

- Remove cargo apt dependency (no longer needed)
- Remove \$HOME/.cargo/bin from PATH
- Replace slow cargo install just with pre-built binary installer
- Move just install to base stage (as root) so all stages have access
- Pin PIXI_VERSION=0.65.0 in both builder and runtime stages

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "fix(docker): replace cargo install just with pre-built binary" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Install just in development stage as dev user writing to /usr/local/bin | Moved `curl just.systems/install.sh \| bash -s -- --to /usr/local/bin` to development stage after `USER ${USER_NAME}` | Dev user lacks permission to write to `/usr/local/bin` (owned by root) | Move to base stage as root, OR install to `~/.local/bin` (user-writable) |
| Keep cargo in image just for just install | Left cargo in apt deps to avoid restructuring | Wastes ~500MB image space for a single tool; defeats purpose of optimization | Remove cargo entirely when it's only used for one tool install |

## Results & Parameters

### Files changed

| File | Change |
|------|--------|
| `Dockerfile` | Remove `cargo` from apt; remove `.cargo/bin` from PATH; add just pre-built install in base stage; remove `cargo install just` from development stage |
| `Dockerfile.ci` | Add `ENV PIXI_VERSION=0.65.0` in builder and runtime stages; pass version to pixi installer |

### just installer command

```dockerfile
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

- `--to /usr/local/bin` specifies install destination
- No version pin in this form (installs latest) — pin with `--tag v1.x.y` if needed:
  ```dockerfile
  RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin --tag 1.14.0
  ```

### Pixi version pinning

```dockerfile
ENV PIXI_VERSION=0.65.0
RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

- The `PIXI_VERSION` environment variable is recognized by the official pixi install script
- Use `pixi --version` in the host environment to find the current version
- Must be set in EACH stage that installs pixi (not inherited across `FROM` boundaries)

### Build time improvement

Removing `cargo install just --version 1.14.0` eliminates ~5-15 minutes of Rust compilation
depending on hardware. Pre-built binary download takes ~5 seconds.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3152, PR #3343 | [notes.md](../../references/notes.md) |

## Related Skills

- **dockerfile-dep-pin** — Pin pip/apt dependencies in Dockerfiles for reproducibility
- **dockerfile-layer-caching** — Optimize Docker layer caching for faster builds
- **docker-multistage-build** — Multi-stage build optimization patterns
- **dockerfile-python-version-guard** — Static tests to prevent base image version drift

## References

- Issue #3152: <https://github.com/HomericIntelligence/ProjectOdyssey/issues/3152>
- PR #3343: <https://github.com/HomericIntelligence/ProjectOdyssey/pull/3343>
- just installer: <https://just.systems/install.sh>
- pixi installer: <https://pixi.sh/install.sh>
