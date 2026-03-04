---
name: pixi-toml-dep-dedup
description: Reconcile duplicate package version specs between [dependencies] and [feature.dev.dependencies] in pixi.toml. Use when a package appears in both sections with conflicting constraints, or when a quality audit flags dependency ambiguity.
category: ci-cd
date: 2026-03-03
user-invocable: true
---

# Pixi TOML Dependency Deduplication

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Reconcile conflicting package version specs in `pixi.toml` |
| **Outcome** | Single authoritative constraint per package; `pixi install` succeeds cleanly |

## When to Use This Skill

Use this pattern whenever:
- A package appears in both `[dependencies]` and `[feature.dev.dependencies]` with different constraints
- A quality audit flags "conflicting pytest version specifications" or similar
- Lower bound in `[feature.dev.dependencies]` is looser than `[dependencies]` (e.g., `>=7.0` vs `>=9.0.2,<10`)
- Missing upper bound in dev section could allow a major-version bump (e.g., no `<10`)

**Symptom example** (pixi.toml):
```toml
[dependencies]
pytest = ">=9.0.2,<10"       # restrictive, correct
pytest-cov = ">=7.0.0,<8"

[feature.dev.dependencies]
pytest = ">=7.0"              # looser lower bound, no upper bound — ambiguous!
pytest-cov = ">=4.0"
```

## Root Cause

pixi merges `[dependencies]` and activated feature dependencies at solve time. When the
same package appears in both with conflicting constraints:

1. The solver takes the **intersection** of both ranges — but this is implicit and easy to miss
2. A loose `>=7.0` in dev with no upper bound could allow `>=10` if the base constraint
   were ever removed or if a dev-only environment activated without `[dependencies]`
3. The authoritative constraint in `[dependencies]` is the one verified by CI; the dev
   duplicate adds noise and maintenance risk

## Verified Workflow

### Step 1: Identify duplicates

```bash
grep -n "pytest\|<package-name>" pixi.toml
```

Look for the same package name appearing under both `[dependencies]` and
`[feature.dev.dependencies]`.

### Step 2: Determine authoritative constraint

- The `[dependencies]` spec is the authoritative one — it is active in all environments
  and is what CI validates
- `[feature.dev.dependencies]` overrides should only exist when dev genuinely needs a
  **different** (typically looser) constraint than production (rare for test runners)

### Step 3: Remove the duplicate from [feature.dev.dependencies]

If the dev spec is weaker or redundant, delete it entirely:

```toml
# BEFORE
[feature.dev.dependencies]
pytest = ">=7.0"
pytest-cov = ">=4.0"
pre-commit = ">=3.0"

# AFTER — duplicates removed
[feature.dev.dependencies]
pre-commit = ">=3.0"
```

### Step 4: Verify

```bash
pixi install
pixi run pytest --version   # confirm resolved version matches [dependencies] constraint
```

### Step 5: Commit

```bash
git add pixi.toml
git commit -m "fix(deps): remove duplicate <package> specs from feature.dev.dependencies"
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| Aligning both to identical spec | Works, but leaves unnecessary duplication | Two entries to maintain instead of one — prefer single source of truth |
| Keeping dev spec as the authoritative one | Risk of CI and dev diverging | `[dependencies]` is what locked CI environments use |

## Results & Parameters

Concrete fix applied to ProjectScylla (issue #1354):

```toml
# Removed from [feature.dev.dependencies]:
# pytest = ">=7.0"       → already in [dependencies] as >=9.0.2,<10
# pytest-cov = ">=4.0"   → already in [dependencies] as >=7.0.0,<8
```

Post-fix verification:
```
pixi install     → ✔ The default environment has been installed.
pytest --version → pytest 9.0.2
```

## Related Skills

- `pixi-lock-rebase-regenerate` — regenerating pixi.lock after rebase
- `pixi-pip-audit-severity-filter` — configuring pip-audit severity in pixi
- `python-version-drift-detection` — detecting Python version drift across config files

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | March 2026 quality audit, issue #1354 — pytest `>=7.0` vs `>=9.0.2,<10` | PR #1373 |
