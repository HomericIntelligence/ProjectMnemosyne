---
name: pixi-precommit-hook-binary-resolution
description: "Pre-commit hooks that invoke 'pixi run <hephaestus-command>' appear to fail with the system-installed binary (newer version with stricter checks) when the project's own pixi env hasn't been populated via 'pixi run dev-install'. Use when: (1) pre-commit check-dep-sync fails locally with 'pyproject.toml contains [project.optional-dependencies] — remove it' but the same check passes in CI, (2) 'which hephaestus-*' inside 'pixi run' returns the system ~/.local/bin path instead of .pixi/envs/default/bin, (3) a pre-commit hook that invokes a console-script via 'pixi run' is using a newer/older version of that script than the one in the current repo, (4) CI pre-commit job runs 'pixi run dev-install' before running hooks but local dev environment does not."
category: ci-cd
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pixi, pre-commit, dev-install, binary-resolution, hephaestus, console-scripts]
---

# Pixi Pre-Commit Hook Binary Resolution

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-28 |
| **Objective** | Understand why pre-commit hooks invoking `pixi run <hephaestus-command>` use a different binary version than expected |
| **Outcome** | Root cause identified: before `pixi run dev-install`, the system-installed binary is used; after, the project's own binary takes precedence |
| **Verification** | verified-local |

## When to Use

- A pre-commit hook invoking `pixi run hephaestus-*` fails with an error that refers to content in `pyproject.toml` or `pixi.toml` that also exists in `origin/main` (which CI passes)
- `which hephaestus-check-dep-sync` inside `pixi run --environment default` returns `~/.local/bin/hephaestus-check-dep-sync` instead of `.pixi/envs/default/bin/...`
- CI pre-commit job passes but local pre-commit run fails for the same hook with a different error message
- You suspect a version mismatch between the project's code and the pre-commit hook's behavior

## Verified Workflow

### Quick Reference

```bash
# Fix: run dev-install to populate the pixi env with the project's own console scripts
cd <repo-root>
pixi run dev-install

# Verify the right binary is now used
pixi run --environment default which hephaestus-check-dep-sync
# Should print: <repo-root>/.pixi/envs/default/bin/hephaestus-check-dep-sync
# NOT: /home/<user>/.local/bin/hephaestus-check-dep-sync

# Re-run the pre-commit hook
pre-commit run check-dep-sync
# OR re-run all hooks
pre-commit run --all-files
```

### Root Cause Explanation

When `pixi run hephaestus-check-dep-sync` is invoked (directly or via a pre-commit hook),
pixi resolves the binary in this order:

1. **Pixi env bin** (`.pixi/envs/default/bin/`) — only populated AFTER `pixi run dev-install`
2. **System PATH fallback** — picks up `~/.local/bin/hephaestus-*` if (1) is empty

`pixi run dev-install` runs `pip install -e . --no-deps` which installs the project's console
scripts into `.pixi/envs/default/bin/`. Without this step, `pixi run` falls through to the
globally-installed hephaestus binary which may be a different version with stricter or
different checks.

### CI vs Local Discrepancy

The CI pre-commit job runs `pixi run dev-install` before `pre-commit run --all-files`:

```yaml
# .github/workflows/pre-commit.yml
- name: Run pre-commit
  run: |
    pixi install --environment lint
    pixi install --environment default
    pixi run dev-install            # ← This populates .pixi/envs/default/bin
    pixi run --environment lint pre-commit run --all-files --show-diff-on-failure
```

Local dev environments that skip `pixi run dev-install` will use the system binary.

### Diagnosing Version Mismatch

```bash
# Check which binary pixi resolves
pixi run --environment default which hephaestus-check-dep-sync

# Compare the two versions
hephaestus-check-dep-sync --version 2>/dev/null || true
pixi run --environment default hephaestus-check-dep-sync --version 2>/dev/null || true

# Check if the system binary has a newer check that the project's code lacks
grep "optional-dependencies\|pyproject.*contains" ~/.local/lib/python*/site-packages/hephaestus/config/dep_sync.py 2>/dev/null
grep "optional-dependencies\|pyproject.*contains" hephaestus/config/dep_sync.py
```

### When This Produces False Positives

The system-installed binary may have stricter checks than the in-repo version. Example:
- System binary v0.9.5 has `check_pyproject_no_deps()` which flags `[project.optional-dependencies]`
- In-repo code at v0.9.3 does NOT have this check
- Pre-commit picks up system binary → false positive failure that CI doesn't reproduce

**Resolution**: Always `pixi run dev-install` before running pre-commit locally. The CI job
always does this step; match that locally.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Removing `[project.optional-dependencies]` from pyproject.toml | The check reported the section as forbidden — tried to remove it to "fix" the hook | The section IS legitimately needed; removing it would break PyPI packaging | Never remove pyproject.toml sections to satisfy a pre-commit hook without first verifying the hook is using the correct binary version |
| Checking pixi.toml for the binary location | Looked in pixi.toml tasks for the hephaestus binary definition | The binary is registered as a console_script in pyproject.toml, not directly in pixi.toml | Console scripts from a `pip install -e .` editable install go into the pixi env's bin directory |
| Assuming the hook failure was a real issue | Spent time analyzing pyproject.toml for the optional-dependencies section | CI passes main with the same section present | Always verify: does the same check pass on `origin/main`? If yes, it's a local environment issue |

## Results & Parameters

### Key commands

```bash
# One-time setup after cloning or after pixi.lock changes:
pixi install
pixi run dev-install

# Verify binary resolution
pixi run --environment default which hephaestus-check-dep-sync
# Expected: <repo>/.pixi/envs/default/bin/hephaestus-check-dep-sync

# Run dep-sync check manually with explicit repo-root
pixi run hephaestus-check-dep-sync --repo-root .
```

### CI workflow pattern (the reference)

```yaml
- name: Run pre-commit
  run: |
    pixi install --environment lint
    pixi install --environment default
    pixi run dev-install  # CRITICAL: populates .pixi/envs/default/bin
    pixi run --environment lint pre-commit run --all-files
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 rebase — check-dep-sync pre-commit false positive | Local binary was v0.9.5 system install; project was v0.9.3; after dev-install the correct binary was used |
