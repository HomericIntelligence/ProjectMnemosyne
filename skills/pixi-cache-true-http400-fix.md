---
name: pixi-cache-true-http400-fix
description: 'Fix prefix-dev/setup-pixi cache:true HTTP 400 failures by replacing
  with explicit actions/cache@v4. Use when: CI shows HTTP 400 from setup-pixi caching,
  or a composite action still uses cache:true.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Fix setup-pixi cache:true HTTP 400 Failure

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Replace broken `cache: true` in `prefix-dev/setup-pixi` with explicit `actions/cache@v4` |
| Outcome | Reliable pixi environment caching; no HTTP 400 errors from GitHub cache service |
| Issue | #3341 — Extend setup-pixi composite to remaining 10 workflows |

## When to Use

- CI logs show HTTP 400 errors during the `prefix-dev/setup-pixi` step with `cache: true`
- A composite action wrapping `setup-pixi` still passes `cache: ${{ inputs.cache }}` or `cache: true`
- Migrating workflows from the broken double-setup pattern to a unified composite action
- The composite action has `inputs:` for `pixi-version` and `cache` that no callers actually use

## Verified Workflow

### 1. Identify the Problem

Check if the composite action (`.github/actions/setup-pixi/action.yml`) uses `cache: true`:

```bash
cat .github/actions/setup-pixi/action.yml
```

Look for:

```yaml
with:
  pixi-version: ${{ inputs.pixi-version }}
  cache: ${{ inputs.cache }}   # <-- broken pattern
```

### 2. Check Callers for `with:` Blocks

Verify no workflows pass `with:` inputs to the composite action — if they do, preserve the inputs:

```bash
grep -rn -A3 "uses: ./.github/actions/setup-pixi" .github/workflows/ | grep -E "pixi-version|cache:"
```

If no output: safe to remove inputs entirely. If output: preserve the `inputs:` block and only fix the cache step.

### 3. Rewrite the Composite Action

Replace the broken pattern with explicit caching. Remove unused `inputs:` block if no callers use it:

```yaml
name: Set Up Pixi Environment
description: Install Pixi with explicit ~/.pixi cache (avoids broken cache:true HTTP 400).

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: latest
      # DO NOT use cache: true — broken, fails with HTTP 400 from GitHub cache service

    - name: Cache pixi environments
      uses: actions/cache@v4
      with:
        path: |
          .pixi
          ~/.cache/rattler/cache
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

Key points:

- Cache path is `.pixi` (repo-relative), NOT `~/.pixi`
- Also cache `~/.cache/rattler/cache` (rattler package cache)
- Key uses `pixi.lock` hash, NOT `pixi.toml` (lock file captures exact resolved versions)
- Use `actions/cache@v4` (not v5 — v5 has its own instability issues)

### 4. Validate YAML

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/actions/setup-pixi/action.yml')); print('OK')"
```

### 5. Commit and Push

```bash
git add .github/actions/setup-pixi/action.yml
git commit -m "ci(actions): replace broken cache:true with explicit pixi cache step"
git push -u origin <branch>
```

## Cache Path Reference

| Path | Purpose |
|------|---------|
| `.pixi` | Pixi environments (repo-relative, not `~/.pixi`) |
| `~/.cache/rattler/cache` | Rattler package download cache |

## Key File: Correct `pixi.lock` vs `pixi.toml` for Cache Key

- `pixi.lock` — resolved dependency tree; changes when any dep version changes → correct cache key
- `pixi.toml` — version constraints only; may not change when lock file changes → stale cache risk

Always use `hashFiles('pixi.lock')` as the cache key.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `cache: true` in setup-pixi | Pass `cache: true` to `prefix-dev/setup-pixi@v0.9.4` | GitHub cache service returns HTTP 400; setup-pixi's built-in caching is unreliable | Use explicit `actions/cache@v4` instead |
| Keying cache on `pixi.toml` | `hashFiles('pixi.toml')` as cache key | Lock file changes without toml changes → stale cache hits | Always key on `pixi.lock` |
| Caching `~/.pixi` instead of `.pixi` | Used home-dir path for the pixi env cache | Pixi stores environments in the repo-local `.pixi/` directory, not `~/.pixi` | Use `.pixi` (repo-relative) |
| Keeping unused `inputs:` block | Preserved `pixi-version` and `cache` inputs when no callers use them | Dead code; caused confusion and allowed accidental re-introduction of `cache: true` | Remove inputs when no callers pass `with:` blocks |

## Results & Parameters

### Working Composite Action Template

```yaml
name: Set Up Pixi Environment
description: Install Pixi with explicit ~/.pixi cache (avoids broken cache:true HTTP 400).

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: latest

    - name: Cache pixi environments
      uses: actions/cache@v4
      with:
        path: |
          .pixi
          ~/.cache/rattler/cache
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

### Verification Commands

```bash
# Check no workflows still use cache:true directly
grep -rn "cache: true" .github/workflows/ .github/actions/

# Verify all workflows use composite action (not direct prefix-dev call)
grep -rn "prefix-dev/setup-pixi" .github/workflows/

# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('.github/actions/setup-pixi/action.yml')); print('OK')"
```
