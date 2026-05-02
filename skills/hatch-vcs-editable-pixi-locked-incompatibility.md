---
name: hatch-vcs-editable-pixi-locked-incompatibility
description: "Fix CI failures caused by hatch-vcs auto-versioning making pixi.lock perpetually stale. Use when: (1) CI fails with 'lock-file not up-to-date with the workspace' on every push after switching from a hardcoded version to hatch-vcs, (2) all pixi-based CI jobs (lint, pre-commit, security) fail identically while the local editable package uses hatch-vcs, (3) regenerating pixi.lock immediately becomes stale on the next commit."
category: ci-cd
date: 2026-04-21
version: "1.0.0"
user-invocable: true
verification: verified-precommit
tags: [hatch-vcs, pixi, pixi-lock, editable-install, setup-pixi, locked, ci-cd]
---
# Hatch-VCS Editable Install / Pixi Lock Incompatibility

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-21 |
| **Objective** | Fix perpetual `lock-file not up-to-date with the workspace` CI failures caused by `hatch-vcs` editable installs invalidating `pixi.lock` on every commit |
| **Outcome** | All CI jobs pass without requiring a new lock-file commit on each push; external dependencies remain reproducibly pinned |
| **Verification** | verified-precommit (v1.0.0) |

## When to Use

- CI fails with `lock-file not up-to-date with the workspace` on **every** push after adding `hatch-vcs`
- The project uses an editable path dependency in `pixi.toml`: `mypackage = { path = ".", editable = true }`
- Regenerating `pixi.lock` fixes CI once but the very next commit breaks it again
- All pixi-based CI jobs (lint, pre-commit, security, test) fail at the `setup-pixi` / `pixi install --locked` step
- The package version in the lock file shows a dev version like `0.7.1.dev15+g4980b19`

## Root Cause

`hatch-vcs` derives the editable package version from the current git commit SHA:

```text
0.7.1.dev15+g4980b19
```

When pixi builds the local editable install, it hashes the built wheel and records that hash in
`pixi.lock`. Every new git commit produces a new SHA → new dev version → new wheel hash →
`pixi.lock` is instantly stale on the next push.

`setup-pixi@v0.9.5` (and earlier versions) run `pixi install --locked` by default, which rejects
any workspace that does not exactly match the recorded hashes. This creates an infinite cycle:

```text
commit → new SHA → new dev version → new wheel hash → pixi.lock stale → CI fails
```

**Why regenerating the lock file is not a solution**: Each commit that regenerates the lock file
produces a new SHA, which immediately invalidates the newly-written lock file on the commit that
includes the regeneration. There is no way to regenerate `pixi.lock` into a state that will
survive the next commit.

## Verified Workflow

### Quick Reference

```bash
# Find all setup-pixi steps missing locked: false
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"

# Fix: add locked: false to every setup-pixi step in every workflow file
# Then verify no step was missed:
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"
# Should produce no output

# Confirm lock file is still consistent for external deps
pixi install --locked  # will fail only if external deps are also stale
```

### Phase 1: Diagnose — Confirm It Is hatch-vcs / Editable Hash Staleness

```bash
# Check the failing CI job log for the lock error
gh run view <run-id> --log-failed | grep "lock-file"

# Confirm the project uses hatch-vcs
grep -r "hatch-vcs\|hatch_vcs" pyproject.toml pixi.toml

# Confirm an editable local path dependency exists in pixi.toml
grep -A2 "path.*editable" pixi.toml

# Check if the version contains a dev+git SHA suffix
pixi run python -c "import importlib.metadata; print(importlib.metadata.version('<package-name>'))"
# If output looks like "0.7.1.dev15+g4980b19", this is the root cause
```

**Confirming signals:**

- Error: `lock-file not up-to-date with the workspace`
- Failure happens on every push, not just after main advances
- No changes to `pixi.toml` or `pyproject.toml` between failing pushes
- Package version contains `.dev` + git SHA suffix

### Phase 2: Apply the Fix

Add `locked: false` to every `setup-pixi` step across all workflow files:

```yaml
# Before (default locked: true — breaks with hatch-vcs editable deps)
- name: Install pixi
  uses: prefix-dev/setup-pixi@v0.9.5
  with:
    pixi-version: v0.63.2

# After
- name: Install pixi
  uses: prefix-dev/setup-pixi@v0.9.5
  with:
    pixi-version: v0.63.2
    locked: false  # required when using hatch-vcs with editable path deps
```

Apply to every workflow file that installs pixi:

```bash
# List all workflow files with setup-pixi
grep -rl "setup-pixi" .github/workflows/

# For each file, add locked: false under the 'with:' block of setup-pixi steps
# Then verify coverage:
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"
# Must produce zero output
```

### Phase 3: Verify

```bash
# Verify all setup-pixi steps have locked: false
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"
# Expected: no output

# Run pre-commit locally to confirm hooks pass
pixi run pre-commit run --all-files

# Push and confirm CI passes on the next commit
git push origin <branch>
gh pr checks <pr-number> --watch
```

## The Fix

Add `locked: false` to every `setup-pixi` step in all GitHub Actions workflows:

```yaml
- name: Install pixi
  uses: prefix-dev/setup-pixi@v0.9.5
  with:
    pixi-version: v0.63.2
    locked: false  # required when using hatch-vcs with editable path deps
```

With `locked: false`:

- pixi still uses `pixi.lock` to pin all **external** conda and PyPI packages (reproducible)
- pixi re-resolves the **local path dependency** on each install, allowing the wheel hash to update
- CI always installs the correct version of the local package without requiring a lock-file commit

## Verification

After applying the fix to all workflow files:

```bash
# Verify no workflow file still uses default (locked) behavior for setup-pixi steps
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"
# Should produce no output (all setup-pixi steps have locked: false)

# Run pre-commit locally to confirm hooks pass
pixi run pre-commit run --all-files
```

In CI, confirm that:

1. All `setup-pixi` install steps complete without `lock-file not up-to-date` errors
2. All pixi-based jobs (lint, pre-commit, security, test) proceed past the install phase
3. Making a new commit and pushing does not re-introduce the failure

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Regenerating `pixi.lock` after each commit | Manually ran `pixi install` and committed the updated lock | The commit that adds the regenerated lock creates a new SHA, which immediately invalidates the lock again — infinite cycle | The root cause is SHA-based versioning, not a stale lock; regeneration cannot fix it |
| Adding `hatch-vcs` to `[pypi-dependencies]` in `pixi.toml` | Listed `hatch-vcs` as an explicit dependency | Does not affect the local editable package hash; `hatch-vcs` is a build-time tool, not the source of the problem | The problem is the editable package's wheel hash changing per commit, not `hatch-vcs` being missing |
| Running `pixi install --all` to update all solve groups | Updated both `default` and `dev` solve groups before pushing | The install regenerates the lock, but the new commit SHA again invalidates it | Same infinite cycle; `--all` does not avoid SHA-based versioning |
| Suppressing ruff lint rules with `per-file-ignores: ["ALL"]` for `_version.py` | Added `[tool.ruff.lint.per-file-ignores]` entry for the generated `_version.py` | `ruff format --check` is a separate check from `ruff lint`; format violations in `_version.py` remain | Use `[tool.ruff] exclude = ["src/.../\_version.py"]` to suppress both lint and format checks on generated files |

## Results & Parameters

### Key Commands

```bash
# Identify all workflow files needing the fix
grep -rl "setup-pixi" .github/workflows/

# Verify fix applied to all steps (must return zero lines)
grep -rn "setup-pixi" .github/workflows/ | grep -v "locked: false"

# Check the installed version (confirms hatch-vcs SHA embedding)
pixi run python -c "import importlib.metadata; print(importlib.metadata.version('<pkg>'))"

# Confirm external deps are still pinned (lock file still valid for external packages)
pixi install --locked

# Run full pre-commit suite
pixi run pre-commit run --all-files
```

### Behavior With `locked: false`

| Dependency Type | With `locked: true` | With `locked: false` |
| ---------------- | --------------------- | ---------------------- |
| External conda packages (ruff, mypy, etc.) | Pinned from lock file | Still pinned from lock file |
| External PyPI packages | Pinned from lock file | Still pinned from lock file |
| Local editable `path = "."` package | Hash checked — fails on new commit | Hash re-resolved — always current |

`locked: false` does NOT make external dependencies unpinned or non-reproducible. It only
relaxes the hash check for local path dependencies, which are re-installed from source anyway.

### Impact

| Metric | Before Fix | After Fix |
| -------- | ----------- | ----------- |
| CI success on new commit | Never (every commit invalidates lock) | Always |
| External dep reproducibility | Yes | Yes (unchanged) |
| Need to commit pixi.lock per push | Yes (impossible to keep up) | No |

## Related Patterns

- **`pixi-lock-rebase-regenerate`** — covers the complementary case where `pixi.lock` is stale
  because `main` advanced (version bump, new dep). Use that skill when staleness is caused by
  rebase; use this skill when staleness is caused by SHA-based versioning on every commit.
- If `ruff format --check` fails on the generated `_version.py`, add it to `[tool.ruff] exclude`
  in `pyproject.toml` (not `per-file-ignores`, which only suppresses lint rules).

## Scope

This pattern applies to any project where all of the following are true:

1. `pixi.toml` has a local editable path dependency (`path = "."` or `path = "./subpackage"`)
2. The package uses `hatch-vcs` (or any other VCS-based versioning that embeds the commit SHA)
3. CI uses `setup-pixi` with default `locked: true` behavior

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Switched from hardcoded `version = "0.7.0"` in `pyproject.toml` to `hatch-vcs` auto-versioning; all pixi-based CI jobs (lint, pre-commit, security) failed with `lock-file not up-to-date`; fixed by adding `locked: false` to all `setup-pixi` steps; PR #298, 2026-04-21 | v1.0.0 |
