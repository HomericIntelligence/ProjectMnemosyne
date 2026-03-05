---
name: mojo-glibc-env-awareness
description: "Handle Mojo projects that require newer GLIBC than the host OS provides. Use when: mojo fails with GLIBC version errors, pre-commit mojo-format hook fails due to GLIBC mismatch, or running Mojo toolchain on older Linux distributions."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo requires GLIBC_2.32+ but many Linux hosts (e.g., Debian 10) only provide GLIBC_2.28 |
| **Symptom** | `mojo: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found` |
| **Scope** | All Mojo CLI operations: `mojo test`, `mojo build`, `mojo format` |
| **Impact** | Cannot run tests, build, or format locally; CI uses Docker with correct GLIBC |

## When to Use

Trigger this skill when you see errors like:

```text
/path/to/mojo: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.32' not found
/path/to/mojo: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.33' not found
/path/to/mojo: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.34' not found
```

Or when pre-commit reports:

```text
Mojo Format..............................................................Failed
- hook id: mojo-format
- exit code: 1
```

## Verified Workflow

### 1. Identify the GLIBC situation

```bash
ldd --version  # Check host GLIBC version
/path/to/.pixi/envs/default/bin/mojo --version  # Will fail on old hosts
```

If mojo fails with GLIBC errors, the environment cannot run Mojo directly.

### 2. Accept the constraint and work around mojo-format

The `mojo-format` pre-commit hook will always fail on hosts with old GLIBC.
Use `SKIP=mojo-format` when committing:

```bash
SKIP=mojo-format git commit -m "your message"
```

**Rationale**: This is safe because CI runs mojo-format inside Docker where
the correct GLIBC is available. The format check will still be enforced in CI.

### 3. Verify other hooks still pass

Other pre-commit hooks (markdown lint, trailing whitespace, YAML check, etc.)
do NOT require Mojo and will run normally. Verify they pass:

```bash
pixi run pre-commit run --files <changed-files>
# Expected: only mojo-format fails; all others pass
```

### 4. Rely on CI for Mojo verification

All Mojo compilation, testing, and formatting is verified in CI via Docker:

```bash
# CI uses Docker image with Ubuntu 22.04+ (GLIBC_2.35)
# ghcr.io/homericintelligence/projectodyssey:main
```

Do not block implementation on local Mojo execution when the environment
cannot support it.

### 5. Check previous commits on the branch for precedent

When implementing on a branch, check if previous commits used `SKIP=mojo-format`:

```bash
git log --oneline -5  # Check recent commits exist
# If the branch already has commits with SKIP=mojo-format, follow the same pattern
```

## Results & Parameters

### Environment Details

| Component | Version |
|-----------|---------|
| Host GLIBC | 2.28 (Debian 10 / buster) |
| Required GLIBC | 2.32+ (Mojo pixi env) |
| CI Docker base | Ubuntu 22.04+ (GLIBC 2.35) |

### Pre-commit Hook Behavior

```yaml
# .pre-commit-config.yaml
- id: mojo-format
  entry: pixi run mojo format
  language: system
  # This hook WILL fail on old GLIBC hosts
  # CI enforces it via Docker

# Workaround for old-GLIBC hosts:
SKIP=mojo-format git commit -m "message"
```

### Check Which Pre-commit Hooks Require Mojo

Only `mojo-format` and `check-list-constructor` (if it calls mojo) require Mojo.
All other hooks (markdownlint, ruff, trailing-whitespace, etc.) run fine.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pixi run mojo test` directly | Executed test runner on host | GLIBC_2.32/33/34 not found errors | Mojo pixi env requires newer GLIBC than Debian 10 host |
| Run `pixi run pre-commit run --files ...` | Ran pre-commit to validate changes | mojo-format hook always fails due to GLIBC | Only mojo-format fails; skip it specifically with `SKIP=mojo-format` |
| Use `just test-mojo` | Tried justfile recipe | `just` not installed on host | Check available commands before relying on justfile |
| Pull Docker image to run tests | `docker pull ghcr.io/homericintelligence/...` | `denied` - Docker registry auth required | Docker images require auth; can't test locally via Docker in restricted environments |
