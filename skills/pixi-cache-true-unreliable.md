---
name: pixi-cache-true-unreliable
description: 'Fixes unreliable Pixi caching caused by setup-pixi''s built-in cache:
  true option. Replace with explicit actions/cache@v5 caching both .pixi and ~/.cache/rattler/cache
  keyed on pixi.lock. Use when: (1) CI logs show ''Saved cache with ID -1'', (2) cache
  hits are inconsistent despite cache: true, (3) consolidating Pixi setup into a shared
  composite action.'
category: ci-cd
date: 2026-03-08
version: 2.0.0
user-invocable: false
---
# Pixi cache: true Is Unreliable — Use Explicit actions/cache

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-08 |
| Project | ProjectOdyssey |
| Objective | Consolidate 14+ independent Pixi setup blocks into a single shared composite action with reliable caching |
| Outcome | ✅ Success — 1 composite action, 0 inline `prefix-dev/setup-pixi` calls in workflows |
| Impact | High — eliminates `Saved cache with ID -1` failures; single source of truth for caching |

## When to Use

- CI logs show `Saved cache with ID -1` after a `prefix-dev/setup-pixi` step with `cache: true`
- CI logs show HTTP 400 errors during the `prefix-dev/setup-pixi` step with `cache: true`
- Cache hits are inconsistent or never occur despite `cache: true` being set
- Multiple workflows each independently set up Pixi (violating DRY)
- Consolidating Pixi setup into a shared composite action (`.github/actions/setup-pixi/action.yml`)
- Migrating from inline setup-pixi blocks to a composite action

## Root Cause

`prefix-dev/setup-pixi@v0.9.x` with `cache: true` uses an internal caching mechanism that
can silently fail, logging `Saved cache with ID -1`. This means **the cache is never actually
saved** and every CI run downloads the full Pixi environment from scratch.

The reliable fix is to **disable `cache: true`** and add an explicit `actions/cache@v5` step
that caches both paths that Pixi uses:

- `.pixi` — the environment directory (packages installed for this project)
- `~/.cache/rattler/cache` — the package download cache (avoids re-downloading)

## Verified Workflow

### 1. Audit workflows for inline Pixi setup

```bash
# Find all direct prefix-dev/setup-pixi calls in workflows
grep -rn "prefix-dev/setup-pixi" .github/workflows/

# Find all cache: true patterns
grep -rn "cache: true" .github/workflows/

# Count workflows already using composite action
grep -rn "\.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
```

### 2. Check Callers for `with:` Blocks Before Rewriting

Before removing inputs from the composite action, verify no workflows pass `with:` inputs to it:

```bash
grep -rn -A3 "uses: ./.github/actions/setup-pixi" .github/workflows/ | grep -E "pixi-version|cache:"
```

If no output: safe to remove inputs entirely. If output: preserve the `inputs:` block and only fix the cache step.

### 3. Create (or update) the composite action

Create `.github/actions/setup-pixi/action.yml`:

```yaml
name: Set Up Pixi Environment
description: Install Pixi and restore the cached environment.

inputs:
  pixi-version:
    description: Pixi version to install
    required: false
    default: latest

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version }}

    - name: Cache Pixi environments
      uses: actions/cache@v5
      with:
        path: |
          .pixi
          ~/.cache/rattler/cache
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

Key decisions:
- **No `cache: true`** — omit it entirely; it's unreliable
- **Hash `pixi.lock` not `pixi.toml`** — lock file is more precise (exact resolved versions)
- **Cache both paths** — `.pixi` (env) AND `~/.cache/rattler/cache` (downloads)
- **Match `actions/cache` version** to what the repo already uses (check with `grep -r "actions/cache@" .github/workflows/`)

### 4. Update all workflows to use the composite action

Each inline block:

```yaml
# BEFORE — inline, unreliable
- name: Set up Pixi
  uses: prefix-dev/setup-pixi@v0.9.4
  with:
    pixi-version: latest
    cache: true
```

Becomes:

```yaml
# AFTER — composite action, reliable
- name: Set up Pixi
  uses: ./.github/actions/setup-pixi
```

### 5. Verify consolidation

```bash
# Should return nothing (no inline calls remain)
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml

# Should return nothing (no cache: true in actions)
grep -rn "cache: true" .github/actions/

# Count composite action uses
grep -rn "\.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
```

### 6. Validate YAML

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/actions/setup-pixi/action.yml')); print('OK')"
```

### 7. Commit and PR

```bash
git add .github/actions/setup-pixi/action.yml
git commit -m "fix(ci): replace cache: true with explicit actions/cache in setup-pixi composite action"
gh pr create --title "fix(ci): replace cache: true with explicit actions/cache" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `actions/cache` version | `@v5` | Match what other workflows use |
| Cache path 1 | `.pixi` | Project environment directory |
| Cache path 2 | `~/.cache/rattler/cache` | Package download cache — must include both |
| Cache key hash source | `pixi.lock` | More precise than `pixi.toml` |
| Restore key prefix | `pixi-${{ runner.os }}-` | Falls back to any OS-matching cache |
| `cache: true` | **omit** | Unreliable — causes "Saved cache with ID -1" |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep `cache: true` | Used `prefix-dev/setup-pixi@v0.9.4` with `cache: true` enabled | Internally fails silently; logs "Saved cache with ID -1"; no cache ever saved | Never use `cache: true` — always use explicit `actions/cache` |
| Cache only `.pixi` | Cached `.pixi` path only, skipped `~/.cache/rattler/cache` | Pixi re-downloads packages on every run even when `.pixi` hits | Must cache both paths or cache is incomplete |
| Hash `pixi.toml` | Used `hashFiles('pixi.toml')` as cache key | `pixi.toml` doesn't encode exact resolved versions; false positives on cache hits | Use `pixi.lock` for precise cache invalidation |
| Keeping unused `inputs:` block | Preserved `pixi-version` and `cache` inputs when no callers use `with:` blocks | Dead code; caused confusion and allowed accidental re-introduction of `cache: true` via the `${{ inputs.cache }}` passthrough | Remove inputs when no callers pass `with:` blocks; verify first with `grep -rn -A3 "uses: ./.github/actions/setup-pixi" .github/workflows/` |
