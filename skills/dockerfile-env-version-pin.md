---
name: dockerfile-env-version-pin
description: Pin installer versions in Dockerfiles via ENV variable injection (e.g.
  PIXI_VERSION, NVM_VERSION) for reproducible builds. Use when a Dockerfile curl-installs
  a tool without a pinned version, or when Dockerfile.ci is pinned but the main Dockerfile
  is not.
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# dockerfile-env-version-pin

Pin installer tool versions in Dockerfiles using `ENV` + env var injection into the install script,
matching the pattern used in CI Dockerfiles for consistency and reproducibility.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-07 |
| Issue | #3350 (ProjectOdyssey) |
| PR | #3986 |
| Objective | Pin `PIXI_VERSION=0.65.0` in main `Dockerfile` development stage to match `Dockerfile.ci` |
| Outcome | Success — 3-line change: comment + `ENV PIXI_VERSION=0.65.0` + updated `RUN` curl command |
| Category | ci-cd |
| Project | ProjectOdyssey |

## When to Use

- When a Dockerfile uses `curl -fsSL https://<tool>/install.sh | bash` without a version pin
- When `Dockerfile.ci` already pins the version but the main `Dockerfile` does not
- When you want reproducible Docker builds regardless of when the image is rebuilt
- When the install script supports `TOOL_VERSION=x.y.z` environment variable injection (common pattern for pixi, nvm, rustup, etc.)
- As a follow-up consistency fix after pinning one Dockerfile in a multi-Dockerfile repo

## Verified Workflow

### Step 1: Find unpinned install commands

```bash
grep -n "install.sh" Dockerfile Dockerfile.ci
grep -n "ENV.*VERSION" Dockerfile Dockerfile.ci
```

Identify which Dockerfiles already pin and which do not.

### Step 2: Identify the pinned version from the reference Dockerfile

```bash
grep "PIXI_VERSION" Dockerfile.ci
# ENV PIXI_VERSION=0.65.0
# RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

Use the same version that `Dockerfile.ci` already declares.

### Step 3: Apply the fix in the target Dockerfile

Replace:

```dockerfile
# Install Pixi as dev user
RUN curl -fsSL https://pixi.sh/install.sh | bash
```

With:

```dockerfile
# Install Pixi as dev user (pinned version for reproducible builds)
ENV PIXI_VERSION=0.65.0
RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

Key points:
- Add `ENV PIXI_VERSION=x.y.z` on the line before the `RUN` curl command
- Pass it via `PIXI_VERSION=${PIXI_VERSION}` in the inline env (not `export`) so it scopes to the install call
- Update the comment to mention "pinned version for reproducible builds"
- The `ENV` instruction also makes the version inspectable via `docker inspect`

### Step 4: Commit and create PR

```bash
git add Dockerfile
git commit -m "fix(docker): pin PIXI_VERSION in <stage> stage

Adds ENV PIXI_VERSION=x.y.z and passes it to the install script,
matching the pattern already used in Dockerfile.ci for consistency
and reproducible builds.

Closes #<issue>"

git push -u origin <branch>
gh pr create \
  --title "fix(docker): pin PIXI_VERSION in <stage> stage" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| None | The fix was straightforward — find, edit, commit | N/A | When a reference Dockerfile already has the pattern, just replicate it exactly |

## Results & Parameters

### Files Changed

| File | Change |
| ------ | -------- |
| `Dockerfile` | +2 lines: `ENV PIXI_VERSION=0.65.0` + updated `RUN` curl; comment updated |

### Pattern Template (generalize for any curl-installer)

```dockerfile
# Install <Tool> (pinned version for reproducible builds)
ENV TOOL_VERSION=x.y.z
RUN curl -fsSL https://<tool>.sh/install.sh | TOOL_VERSION=${TOOL_VERSION} bash
```

Works for tools whose install scripts honor an env var for version selection, including:

| Tool | Env Var | Install URL |
| ------ | --------- | ------------- |
| Pixi | `PIXI_VERSION` | `https://pixi.sh/install.sh` |
| nvm | `NVM_VERSION` | `https://raw.githubusercontent.com/nvm-sh/nvm/v.../install.sh` |
| rustup | `RUSTUP_INIT_RELEASE` | `https://sh.rustup.rs` |

### Why ENV vs inline export

Using `ENV PIXI_VERSION=0.65.0` (Dockerfile `ENV` instruction):
- Makes version visible in `docker inspect` output
- Allows child stages to inherit and reference the same version
- Can be overridden at build time via `--build-arg` if paired with `ARG`

Using inline `TOOL_VERSION=x.y.z curl | bash`:
- Scopes version only to that one `RUN` command
- Doesn't propagate to child stages
- Preferred only if version shouldn't bleed into the image env

For consistency with `Dockerfile.ci` and cross-stage visibility, `ENV` is the correct choice.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3350, PR #3986 | [notes.md](../references/notes.md) |

## Related Skills

- **dockerfile-dep-pin** — Pin pip `install` dependencies in Dockerfile builder stages
- **pin-npm-dockerfile** — Pin npm packages in Dockerfiles
- **dockerfile-python-version-guard** — Static tests to prevent Python base image version drift
- **dockerfile-layer-caching** — Docker build layer caching optimization patterns
