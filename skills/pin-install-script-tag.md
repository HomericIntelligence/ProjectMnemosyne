---
name: pin-install-script-tag
description: 'Pin a curl-piped install script to a specific version tag for reproducible
  Docker builds. Use when: (1) a Dockerfile uses curl | bash install.sh without a
  --tag or version flag, (2) a previously-pinned cargo/apt install was replaced with
  a pre-built binary installer but the version pin was dropped.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# pin-install-script-tag

Pin a `curl | bash install.sh` command to a specific version tag so Docker builds
are reproducible and do not silently upgrade binary tools.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-07 |
| Issue | #3349 |
| PR | #3982 |
| Objective | Add `--tag 1.14.0` to `just.systems/install.sh` curl command that was missing version pin |
| Outcome | Success — single-line Dockerfile change, PR #3982 created |
| Category | ci-cd |
| Project | ProjectOdyssey |

## When to Use

- A Dockerfile has `curl ... | bash -s -- <flags>` without a version/tag flag
- A prior `cargo install <tool> --version X.Y.Z` was replaced with a pre-built binary
  installer, but the version pin was not carried over to the new install command
- You want to prevent silent upgrades: the installer always fetches "latest" unless pinned
- The tool's official installer supports a `--tag` or `--version` flag (check the project's
  install docs or pass `--help` to the script)
- Follow-up to a "replace cargo with pre-built binary" PR where version pinning was deferred

## Decision: Which version to pin to

| Source | When to use |
| -------- | ------------- |
| Match previous `cargo install --version X.Y.Z` | Easiest — use the same version that was pinned before the installer migration |
| Check `CLAUDE.md` / `justfile` / CI for a version reference | If no prior pin, look for version hints in project tooling |
| Tool's latest stable release page | Only if no prior pin existed at all |

## Verified Workflow

### Step 1: Find the unpinned install command

```bash
grep -n "install.sh" Dockerfile
```

Look for `curl -fsSL https://<tool>.systems/install.sh | bash -s -- --to /usr/local/bin`
without a `--tag` or version argument.

### Step 2: Determine the version to pin

Check what version was used before the migration (e.g. in `cargo install just --version 1.14.0`):

```bash
git log --oneline --all -- Dockerfile | head -10
git show <commit>:Dockerfile | grep -i "just\|cargo"
```

Or check project docs / justfile for the intended version.

### Step 3: Add the version tag flag

For `just.systems/install.sh`, the flag is `--tag`:

```dockerfile
# BEFORE (unpinned — always installs latest)
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# AFTER (pinned to specific version)
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin --tag 1.14.0
```

For other tools, check their installer's `--help` or README for the version flag name
(`--tag`, `--version`, `--release`, etc.).

### Step 4: Verify locally (optional)

If Docker is available:

```bash
docker build --target <base-stage> -t test-pin .
docker run --rm test-pin just --version
```

Expected output: `just 1.14.0`

### Step 5: Commit and push

The change is typically a single line. Use a conventional commit:

```bash
git add Dockerfile
git commit -m "fix(docker): pin just version to 1.14.0 for reproducible builds

Use --tag 1.14.0 flag in just.systems install script instead of
always fetching latest, matching previous cargo install pinning.

Closes #<issue>"

git push -u origin <branch>
```

### Step 6: Create PR

```bash
gh pr create \
  --title "fix(docker): pin just version to 1.14.0 for reproducible builds" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — task was straightforward | The fix was a one-word addition (`--tag 1.14.0`) to an existing curl command | No failures encountered | When migrating from `cargo install --version` to a pre-built installer, always carry the version pin forward immediately |

## Results & Parameters

### Files changed

| File | Change |
| ------ | -------- |
| `Dockerfile` | Add `--tag 1.14.0` to `just.systems/install.sh` curl command |

### just installer version flag syntax

```dockerfile
# Pin to a specific version using --tag
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin --tag 1.14.0
```

- `--to /usr/local/bin` — install destination (system-wide, requires root)
- `--tag 1.14.0` — version to install (note: no `v` prefix for just's installer)
- The flag order (`--to` before `--tag`) does not matter

### Common installer version flags by tool

| Tool | Version flag | Example |
| ------ | ------------- | --------- |
| `just` | `--tag` | `--tag 1.14.0` |
| `pixi` | env var `PIXI_VERSION` | `PIXI_VERSION=0.65.0 curl ... \| bash` |
| `rustup` | `--default-toolchain` | `--default-toolchain 1.75.0` |

### Why this matters

An unpinned `curl | bash` install always fetches the latest release at build time. This means:

- Docker builds on different days may install different tool versions
- CI can silently break if a new release introduces incompatible behavior
- Layer cache invalidation logic cannot distinguish "same version cached" from "new version"

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3349, PR #3982 | [notes.md](../../references/notes.md) |

## Related Skills

- **dockerfile-cargo-to-prebuilt-binary** — Replace `cargo install` with pre-built binary
  installers (the step before this one)
- **dockerfile-dep-pin** — Pin `pip install` dependencies in Dockerfiles
- **pin-npm-dockerfile** — Pin npm packages in Dockerfiles

## References

- Issue #3349: <https://github.com/HomericIntelligence/ProjectOdyssey/issues/3349>
- PR #3982: <https://github.com/HomericIntelligence/ProjectOdyssey/pull/3982>
- Follow-up from #3152 / PR #3343
- just installer docs: <https://just.systems/install.sh>
