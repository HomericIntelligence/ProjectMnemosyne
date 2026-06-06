---
name: pixi-cache-true-unreliable
description: 'Fixes unreliable Pixi caching from setup-pixi''s built-in cache: true,
  AND warns that under locked: true a SECOND actions/cache over .pixi poisons the locked
  env (downgrades packages, fails pip-audit/dependency-scan). Replace cache: true with
  explicit actions/cache (non-locked); with locked: true rely ONLY on setup-pixi''s
  built-in cache. Use when: (1) CI logs show ''Saved cache with ID -1'', (2) cache hits
  inconsistent despite cache: true, (3) consolidating Pixi setup into a composite action,
  (4) dependency-scan/pip-audit fails on an already-patched pixi.lock, (5) setup-pixi
  installs a newer version than pip-audit then audits.'
category: ci-cd
date: 2026-06-06
version: 2.1.0
user-invocable: false
verification: verified-ci
history: pixi-cache-true-unreliable.history
---
# Pixi cache: true Is Unreliable — Use Explicit actions/cache

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-08 |
| Project | ProjectOdyssey |
| Objective | Consolidate 14+ independent Pixi setup blocks into a single shared composite action with reliable caching |
| Outcome | ✅ Success — 1 composite action, 0 inline `prefix-dev/setup-pixi` calls in workflows |
| Impact | High — eliminates `Saved cache with ID -1` failures; single source of truth for caching |
| Verification | verified-ci |
| History | [changelog](./pixi-cache-true-unreliable.history) |

> **CRITICAL caveat (v2.1.0):** The "add an explicit `actions/cache` over `.pixi`"
> recommendation below is for the **non-`locked`** case. If `prefix-dev/setup-pixi` runs
> with `locked: true`, do **NOT** add a second `actions/cache` over `.pixi` — it poisons
> the freshly-installed locked environment. See
> [Locked Mode: Do Not Add a Second .pixi Cache](#locked-mode-do-not-add-a-second-pixi-cache).

## When to Use

- CI logs show `Saved cache with ID -1` after a `prefix-dev/setup-pixi` step with `cache: true`
- CI logs show HTTP 400 errors during the `prefix-dev/setup-pixi` step with `cache: true`
- Cache hits are inconsistent or never occur despite `cache: true` being set
- Multiple workflows each independently set up Pixi (violating DRY)
- Consolidating Pixi setup into a shared composite action (`.github/actions/setup-pixi/action.yml`)
- Migrating from inline setup-pixi blocks to a composite action
- `security`/`dependency-scan` (pip-audit) fails on EVERY PR even though `pixi.lock` is
  already patched to the fixed version
- CI logs show setup-pixi installing a fixed version (e.g. urllib3 2.7.0) but pip-audit
  then reports a vulnerability against an OLDER version (e.g. 2.6.3)

## Root Cause

`prefix-dev/setup-pixi@v0.9.x` with `cache: true` uses an internal caching mechanism that
can silently fail, logging `Saved cache with ID -1`. This means **the cache is never actually
saved** and every CI run downloads the full Pixi environment from scratch.

The reliable fix is to **disable `cache: true`** and add an explicit `actions/cache@v5` step
that caches both paths that Pixi uses:

- `.pixi` — the environment directory (packages installed for this project)
- `~/.cache/rattler/cache` — the package download cache (avoids re-downloading)

## Locked Mode: Do NOT Add a Second .pixi Cache

> **This is the most important caveat in this skill. It contradicts the
> general recommendation above for the `locked: true` case.**

When a workflow uses `prefix-dev/setup-pixi@v0.9.x` with `locked: true` (e.g.
`pixi install -e <env> --locked`), setup-pixi **already** caches `.pixi` keyed exactly on
the `pixi.lock` hash AND installs the correct locked environment. Adding a **second**
`actions/cache@v5` step that caches/restores the same `.pixi` directory **POISONS** the
environment:

1. setup-pixi runs `pixi install -e <env> --locked` → installs the CORRECT locked
   versions (e.g. urllib3 `2.7.0`).
2. A later `actions/cache` restore step extracts a STALE `.pixi` archive **over** that
   fresh install — `actions/cache` restore extracts on top of existing paths, and
   **whichever cache restores LAST wins** — silently downgrading packages
   (urllib3 `2.7.0` → `2.6.3`).
3. `pip-audit` then audits the **downgraded** env and reports vulnerabilities
   (e.g. `PYSEC-2026-141` / `PYSEC-2026-142`), **failing `security` / `dependency-scan`
   on every PR — even though `pixi.lock` is already patched.**

### Two poisoning variants — BOTH are dangerous

| Variant | Cache key config | How it poisons |
| ------- | ---------------- | -------------- |
| Loose `restore-keys:` | e.g. `pixi-lint-${{ runner.os }}-` | On an exact-key miss, falls back to ANY prior lock's cache (stale) |
| Exact-key only (NO `restore-keys`) | `pixi-...-${{ hashFiles('pixi.lock') }}` only | A cache a PREVIOUS poisoned run saved under that exact key gets an exact hit and is restored — the same lock hash keeps restoring the poison |

**Key lesson:** "No `restore-keys` = safe" is **WRONG**. An exact-key-only `.pixi` cache
still poisons because it exact-hits a previously-poisoned cache stored under the same
`pixi.lock` hash. **ANY** second `actions/cache` over `.pixi` after a `--locked`
setup-pixi is unsafe, regardless of `restore-keys`.

### Diagnosis signature (read `gh run view --log`)

```text
# setup-pixi step
... pixi install -e lint --locked ... urllib3-2.7.0   <- CORRECT version installed
# later
Cache restored from key: pixi-lint-...                 <- stale .pixi restored over it
# pip-audit step
Found vulnerability in urllib3 2.6.3 (PYSEC-2026-141)   <- OLD version audited
```

If the version setup-pixi installs differs from the version pip-audit audits, you have
cache poisoning. Confirm with:

```bash
gh run view <run-id> --log | grep -iE "pixi install .*--locked|Cache restored from key|vulnerab|urllib3"
```

### Root-cause fix

**Remove the redundant second `actions/cache` step over `.pixi`** and rely on
`prefix-dev/setup-pixi`'s built-in caching (exact-keyed on `pixi.lock`, never clobbers
the install). Do this across **ALL** workflows that have the pattern — composite actions,
`release.yml`, `pre-commit.yml`, `security.yml`. A workflow whose `.pixi` cache has NO
`restore-keys` must be fixed too, not just the ones with loose `restore-keys`.

```bash
# Find every actions/cache that touches .pixi after a setup-pixi/--locked step
grep -rn -B2 -A8 "actions/cache" .github/workflows/ .github/actions/ | grep -E "\.pixi|actions/cache|locked"

# After removing the redundant cache steps, confirm none remain over .pixi
grep -rn -A8 "actions/cache" .github/workflows/ .github/actions/ | grep -n "\.pixi"
```

### Decision: should you add an explicit `actions/cache` over `.pixi`?

```text
Does the workflow use prefix-dev/setup-pixi with locked: true (or pixi install --locked)?
├─ YES → DO NOT add a second actions/cache over .pixi.
│        Rely on setup-pixi's built-in lock-keyed cache. Remove any existing one.
└─ NO  → cache: true is unreliable → use ONE explicit actions/cache over
         .pixi + ~/.cache/rattler/cache keyed on pixi.lock (see Verified Workflow below).
```

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
| ----------- | ------- | ------- |
| `actions/cache` version | `@v5` | Match what other workflows use |
| Cache path 1 | `.pixi` | Project environment directory |
| Cache path 2 | `~/.cache/rattler/cache` | Package download cache — must include both |
| Cache key hash source | `pixi.lock` | More precise than `pixi.toml` |
| Restore key prefix | `pixi-${{ runner.os }}-` | Falls back to any OS-matching cache (**only when NOT using `locked: true`**) |
| `cache: true` | **omit** | Unreliable — causes "Saved cache with ID -1" |
| Second `actions/cache` over `.pixi` under `locked: true` | **remove** | Poisons the locked install; downgrades packages; fails pip-audit |
| Locked-mode caching | rely on built-in setup-pixi cache | setup-pixi exact-keys `.pixi` on `pixi.lock` and never clobbers the install |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Keep `cache: true` | Used `prefix-dev/setup-pixi@v0.9.4` with `cache: true` enabled | Internally fails silently; logs "Saved cache with ID -1"; no cache ever saved | Never use `cache: true` — always use explicit `actions/cache` |
| Cache only `.pixi` | Cached `.pixi` path only, skipped `~/.cache/rattler/cache` | Pixi re-downloads packages on every run even when `.pixi` hits | Must cache both paths or cache is incomplete |
| Hash `pixi.toml` | Used `hashFiles('pixi.toml')` as cache key | `pixi.toml` doesn't encode exact resolved versions; false positives on cache hits | Use `pixi.lock` for precise cache invalidation |
| Keeping unused `inputs:` block | Preserved `pixi-version` and `cache` inputs when no callers use `with:` blocks | Dead code; caused confusion and allowed accidental re-introduction of `cache: true` via the `${{ inputs.cache }}` passthrough | Remove inputs when no callers pass `with:` blocks; verify first with `grep -rn -A3 "uses: ./.github/actions/setup-pixi" .github/workflows/` |
| Second `actions/cache` over `.pixi` with `locked: true` | Kept setup-pixi's built-in `.pixi` cache AND added an explicit `actions/cache@v5` over the same `.pixi` path | The second restore extracts a STALE `.pixi` over the fresh `--locked` install (last restore wins), downgrading urllib3 2.7.0 → 2.6.3; pip-audit then audits the downgraded env and fails `dependency-scan` on every PR | With `locked: true`, never layer a second cache over `.pixi` — rely solely on setup-pixi's built-in lock-keyed cache |
| "No `restore-keys` = safe" assumption | Fixed only the workflows with loose `restore-keys:` (setup-pixi-env, release.yml, pre-commit.yml); left security.yml's exact-key-only `.pixi` cache in place | security.yml STILL failed `dependency-scan`: its exact key (`hashFiles('pixi.lock')`) hit a `.pixi` cache that a PREVIOUS poisoned run had saved under the same hash — exact-key hit restored the poison | An exact-key-only `.pixi` cache is NOT safe; ANY second `actions/cache` over `.pixi` after a `--locked` setup-pixi is unsafe, regardless of `restore-keys` |
| Bumping `pixi.lock` to patched version alone | Updated `pixi.lock` so the locked env had urllib3 2.7.0 | dependency-scan still failed because the poisoning cache restored 2.6.3 over the patched install; the lock fix was correct but invisible to pip-audit | Patching the lock is necessary but not sufficient when a second `.pixi` cache poisons the env — you must also remove the redundant cache |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | Consolidate 14+ Pixi setup blocks into a composite action (v2.0.0) | Eliminated `Saved cache with ID -1` |
| ProjectHephaestus | `.pixi` cache poisoning under `locked: true` — PR #1021 fixed setup-pixi-env composite + release.yml + pre-commit.yml; PR #1026 fixed security.yml (exact-key-only cache) | verified-ci: dependency-scan green on rebased PRs after the fix (e.g. PR #1011 passed) |
