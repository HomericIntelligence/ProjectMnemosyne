---
name: ci-pixi-lock-check-setup-order
description: "Fix GitHub Actions workflows that run pixi commands before pixi is installed, causing 'pixi: command not found'. Use when: (1) a workflow fails with 'pixi: command not found' on any pixi command, (2) adding a new workflow that uses pixi but forgot to install it first, (3) a lock-check or dependency-verification workflow runs pixi install --locked without a prior pixi setup step."
category: ci-cd
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pixi, ci, github-actions, setup-order, lock-check, command-not-found, setup-pixi, composite-action]
---

# CI Pixi Setup Order: Install Pixi Before Running Pixi Commands

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Fix a `lock-check.yml` workflow that ran `pixi install --locked` without first installing pixi |
| **Outcome** | Successful — workflow fixed by adding `.github/actions/setup-pixi` composite action before pixi commands |
| **Verification** | verified-local — fix applied to ProjectMyrmidons PR #350 and merged; lock-check workflow pattern is correct and standard |

## When to Use

- A GitHub Actions workflow fails with `pixi: command not found` on any step
- Adding a new workflow that runs `pixi install`, `pixi run`, or any other pixi command
- A `lock-check.yml` or similar dependency-verification workflow was added but does not install pixi first
- Auditing existing workflows to verify pixi is installed before any pixi commands are run

## Verified Workflow

### Quick Reference

```yaml
# BROKEN: pixi commands without pixi installation
jobs:
  lock-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies (locked)
        run: pixi install --locked   # FAILS: pixi not installed

# FIXED: use repo's composite action first
jobs:
  lock-check:
    name: Verify pixi.lock is in sync
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-pixi   # installs pixi + caches env
      - name: Install dependencies (locked)
        run: pixi install --locked
```

### Detailed Steps

1. **Identify the failure**: Look for `pixi: command not found` in the CI log. This means any step is running `pixi` before it is installed.

2. **Check if the repo has a composite action**:

   ```bash
   ls .github/actions/setup-pixi/action.yml
   ```

3. **If `setup-pixi` composite action exists** — add it before the first pixi command:

   ```yaml
   steps:
     - uses: actions/checkout@v4
     - uses: ./.github/actions/setup-pixi    # must come AFTER checkout (composite actions need the repo on disk)
     - name: Install dependencies (locked)
       run: pixi install --locked
   ```

4. **If no composite action exists** — use the official `prefix-dev/setup-pixi` action:

   ```yaml
   steps:
     - uses: actions/checkout@v4
     - uses: prefix-dev/setup-pixi@v0.8.1
       with:
         pixi-version: v0.63.2
     - name: Install dependencies (locked)
       run: pixi install --locked
   ```

5. **Audit all workflows** for pixi commands without prior setup:

   ```bash
   # Find workflows with pixi commands but no setup step
   grep -l "run:.*pixi " .github/workflows/*.yml | while read f; do
     if ! grep -q "setup-pixi\|prefix-dev/setup-pixi" "$f"; then
       echo "MISSING pixi setup: $f"
     fi
   done
   ```

### Step Order Rule

GitHub Actions runners (ubuntu-latest, etc.) do **not** have pixi pre-installed. Every job that runs pixi commands must have a pixi installation step. The correct order is always:

```
1. actions/checkout@v4        (required before any ./.github/actions/ composite)
2. ./.github/actions/setup-pixi  (or prefix-dev/setup-pixi)
3. pixi install / pixi run / etc.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Manual cache + pixi install pattern | Added a manual `actions/cache` step and `curl`-based pixi binary download | Fragile — duplicated logic already in the repo's composite action; cache key format differed from other workflows | Always use the repo's existing `.github/actions/setup-pixi` when it exists; don't duplicate install logic |

## Results & Parameters

### Expected Fix for `lock-check.yml`

Full correct workflow:

```yaml
name: Lock File Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lock-check:
    name: Verify pixi.lock is in sync
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: ./.github/actions/setup-pixi

      - name: Install dependencies (locked)
        run: pixi install --locked
```

### Diagnosis Command

```bash
# Check if a workflow will fail with this issue
grep -n "run:.*pixi " .github/workflows/lock-check.yml
# If the above has results but this doesn't, the setup is missing:
grep -n "setup-pixi\|prefix-dev/setup-pixi" .github/workflows/lock-check.yml
```

### Difference from `composite-action-checkout-order` issue

This is a **distinct** problem from `checkout-before-composite-action`:

| Issue | Symptom | Root Cause |
|-------|---------|------------|
| `composite-action-checkout-order` | `Cannot find action './.github/actions/X'` | `actions/checkout` not run before local composite action |
| `ci-pixi-lock-check-setup-order` | `pixi: command not found` | Pixi binary not installed before running pixi commands |

Both issues stem from missing prerequisite steps, but the errors and fixes are different.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMyrmidons | PR #350, `lock-check.yml` workflow | Fixed by adding `.github/actions/setup-pixi` before `pixi install --locked` |
