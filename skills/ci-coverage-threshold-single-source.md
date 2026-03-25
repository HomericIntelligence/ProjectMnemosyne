---
name: ci-coverage-threshold-single-source
description: "Establish [tool.coverage.report].fail_under as the single source of truth for
  coverage thresholds by removing redundant --cov-fail-under from both CI workflows and
  pyproject.toml addopts. Use when: (1) --cov-fail-under appears in addopts or CI alongside
  fail_under in pyproject.toml, (2) coverage floor is cosmetically low, (3) local and CI
  thresholds diverge."
category: ci-cd
date: 2026-03-25
version: "2.0.0"
user-invocable: false
verification: verified-local
history: ci-coverage-threshold-single-source.history
tags:
  - coverage
  - pytest
  - single-source-of-truth
  - pyproject-toml
  - ci-cd
---

# Skill: ci-coverage-threshold-single-source

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Establish `[tool.coverage.report].fail_under` as the single source of truth for coverage thresholds — remove redundant `--cov-fail-under` from both CI and pyproject.toml addopts |
| **Outcome** | Success — threshold raised from 9% to 75%, addopts flag removed, consistency checks updated |
| **Verification** | verified-local |
| **History** | [changelog](./ci-coverage-threshold-single-source.history) |

## When to Use

- `--cov-fail-under=<N>` appears in `[tool.pytest.ini_options].addopts` AND `fail_under = <M>` exists in `[tool.coverage.report]` — redundant, remove the addopts flag
- `--cov-fail-under=<N>` appears in a CI workflow AND `fail_under = <M>` exists in `pyproject.toml` with `N != M` — inconsistent, remove the CI flag
- Coverage floor is cosmetically low (e.g., 9%) and provides no regression protection
- Local `pytest` runs don't catch coverage regressions that CI would catch
- You want developers to get the same coverage feedback locally as CI provides

## Root Cause Pattern

pytest-cov supports two ways to set a minimum coverage threshold:

1. **CLI flag**: `--cov-fail-under=72` in the pytest command (or in `addopts`)
2. **Config file**: `fail_under = 73` under `[tool.coverage.report]` in `pyproject.toml`

When both are present, the **CLI flag wins** — it overrides the config file value.

**Three places this flag can hide:**

| Location | Precedence | Scope |
|----------|-----------|-------|
| `addopts` in `[tool.pytest.ini_options]` | Highest (local runs) | All local `pytest` invocations |
| `--cov-fail-under=N` in CI workflow | Highest (CI runs) | CI pytest invocations only |
| `fail_under` in `[tool.coverage.report]` | Lowest (fallback) | Any run without CLI override |

**The fix**: Remove the flag from addopts and CI, making `[tool.coverage.report].fail_under` the single source of truth. CI can use `--override-ini="addopts="` to bypass pyproject.toml addopts and apply its own per-step floors.

## Verified Workflow

### Quick Reference

```bash
# 1. Find all --cov-fail-under flags
grep -rn "cov-fail-under" pyproject.toml .github/workflows/
grep -n "fail_under" pyproject.toml

# 2. Measure actual coverage
pixi run pytest tests/ -v --tb=no -q 2>&1 | tail -5

# 3. Remove --cov-fail-under from addopts, raise fail_under
# Edit pyproject.toml: remove "--cov-fail-under=N" from addopts list
# Edit pyproject.toml: set fail_under = <actual - 2%>

# 4. Update any consistency check scripts
# If scripts validate addopts contains --cov-fail-under, update them

# 5. Add local test-unit task for CI parity
# pixi.toml: test-unit = "pytest tests/unit --override-ini='addopts=' ..."
```

### Detailed Steps

#### Scenario A: Remove `--cov-fail-under` from pyproject.toml addopts

1. **Measure actual coverage** to determine the right `fail_under` value:
   ```bash
   pixi run pytest tests/ -v --tb=no -q 2>&1 | tail -5
   # Look for: "Required test coverage of X% reached. Total coverage: Y%"
   ```

2. **Remove the flag from addopts** and raise `fail_under`:
   ```toml
   # BEFORE
   [tool.pytest.ini_options]
   addopts = [
       "--cov=scylla",
       "--cov-report=term-missing",
       "--cov-fail-under=9",   # ← Remove this line
   ]

   [tool.coverage.report]
   fail_under = 9   # ← Raise to actual - 2% (e.g., 75 if actual is 77.42%)
   ```

   ```toml
   # AFTER
   [tool.pytest.ini_options]
   addopts = [
       "--cov=scylla",
       "--cov-report=term-missing",
   ]

   [tool.coverage.report]
   fail_under = 75   # Single source of truth
   ```

3. **Update consistency check scripts** that validate addopts:
   ```python
   # BEFORE: script errors when --cov-fail-under absent from addopts
   if addopts_threshold is None:
       return ["No --cov-fail-under=N flag found in addopts"]

   # AFTER: absent is fine — fail_under is the single source of truth
   if addopts_threshold is None:
       return []
   ```

4. **Add a `test-unit` pixi task** for local CI parity:
   ```toml
   # pixi.toml
   test-unit = "pytest tests/unit --override-ini='addopts=' -v --strict-markers --cov=scylla --cov-report=term-missing --cov-fail-under=75"
   ```
   This gives developers the same per-module floor as CI without relying on pyproject.toml addopts.

5. **Update documentation** (CLAUDE.md, CONTRIBUTING.md) referencing the old floor value.

#### Scenario B: Remove `--cov-fail-under` from CI workflow

1. Remove `--cov-fail-under=<N>` from every `pytest` invocation in `.github/workflows/test.yml`
2. The CI will now inherit `fail_under` from `[tool.coverage.report]`

**Note**: If CI uses `--override-ini="addopts="` (which clears all addopts), CI must specify its own `--cov-fail-under` — it won't read `addopts` from pyproject.toml. In this case, CI manages its own thresholds independently, and pyproject.toml only governs local runs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Removing flag only | Removed `--cov-fail-under=9` from addopts without raising `fail_under` | Pre-commit consistency check failed: script expected the flag in addopts | Always check for consistency-check scripts that validate addopts contents |
| Raising floor without measuring | Would have set `fail_under=50` per issue suggestion | Would have left 27% gap below actual (77.42%) — too loose for regression protection | Always measure actual coverage first, then set floor 2% below baseline |

## Results & Parameters

### v2.0.0 — Issue #1511, PR #1554

| Parameter | Value |
|-----------|-------|
| Previous combined floor | `fail_under = 9` + `--cov-fail-under=9` in addopts |
| New combined floor | `fail_under = 75` (single source of truth) |
| Actual combined coverage | 77.42% (2.42% buffer) |
| Actual scylla/ unit coverage | 81.69% |
| Files changed | `pyproject.toml`, `pixi.toml`, `CONTRIBUTING.md`, `CLAUDE.md`, `scripts/check_doc_config_consistency.py`, tests |
| New pixi task | `test-unit` — mirrors CI 75% scylla/ enforcement |

### v1.0.0 — Issue #754, PR #868

| Parameter | Value |
|-----------|-------|
| Threshold removed from CI | `--cov-fail-under=72` |
| Authoritative threshold | `fail_under = 73` in `[tool.coverage.report]` |
| Files changed | `.github/workflows/test.yml` |

## Key Insights

1. **`[tool.coverage.report].fail_under` is sufficient** — pytest-cov reads it automatically when no CLI `--cov-fail-under` flag is provided. Removing the CLI flag enforces the single source of truth.

2. **CI with `--override-ini="addopts="` bypasses all addopts** — this means pyproject.toml addopts changes only affect local runs. CI must specify its own thresholds explicitly.

3. **Consistency check scripts are a hidden dependency** — if your project has scripts that validate `--cov-fail-under` exists in addopts, removing the flag will break them. Update these scripts to accept the absent flag.

4. **Dual-threshold design**: Use `fail_under` in pyproject.toml for local combined coverage, and explicit `--cov-fail-under` in CI for per-step enforcement (unit at 75%, integration at 5%).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1511, PR #1554 | Raised floor 9%→75%, added test-unit task |
| ProjectScylla | Issue #754, PR #868 | Removed CI --cov-fail-under, aligned to pyproject.toml |
