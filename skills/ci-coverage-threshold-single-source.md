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
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Establish `[tool.coverage.report].fail_under` as the single source of truth for coverage thresholds |
| **Outcome** | Success - threshold raised from 9% to 75%, addopts flag removed, consistency checks updated |
| **Verification** | verified-local |
| **History** | [changelog](./ci-coverage-threshold-single-source.history) |

## When to Use

- `--cov-fail-under=<N>` in `[tool.pytest.ini_options].addopts` AND `fail_under = <M>` in `[tool.coverage.report]` - redundant, remove the addopts flag
- `--cov-fail-under=<N>` in a CI workflow AND `fail_under = <M>` in `pyproject.toml` with `N != M` - inconsistent, remove the CI flag
- Coverage floor is cosmetically low (e.g., 9%) and provides no regression protection
- Local `pytest` runs don\'t catch coverage regressions that CI would catch
- You want developers to get the same coverage feedback locally as CI provides

## Root Cause Pattern

pytest-cov supports two ways to set a minimum coverage threshold:

1. **CLI flag**: `--cov-fail-under=72` in the pytest command (or in `addopts`)
2. **Config file**: `fail_under = 73` under `[tool.coverage.report]` in `pyproject.toml`

When both are present, the **CLI flag wins** - it overrides the config file value.

**Three places this flag can hide:**

| Location | Precedence | Scope |
| ---------- | ----------- | ------- |
| `addopts` in `[tool.pytest.ini_options]` | Highest (local runs) | All local `pytest` invocations |
| `--cov-fail-under=N` in CI workflow | Highest (CI runs) | CI pytest invocations only |
| `fail_under` in `[tool.coverage.report]` | Lowest (fallback) | Any run without CLI override |

**The fix**: Remove the flag from addopts and CI, making `[tool.coverage.report].fail_under` the single source of truth.

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

# 4. Update any consistency check scripts that validate addopts

# 5. Add local test-unit task for CI parity
# pixi.toml: test-unit = "pytest tests/unit --override-ini=\'addopts=\' ..."
```

### Detailed Steps

#### Scenario A: Remove --cov-fail-under from pyproject.toml addopts

1. **Measure actual coverage** to determine the right `fail_under` value
2. **Remove the flag from addopts** and raise `fail_under` to actual - 2%
3. **Update consistency check scripts** that validate addopts (change "absent = error" to "absent = OK")
4. **Add a test-unit pixi task** for local CI parity
5. **Update documentation** (CLAUDE.md, CONTRIBUTING.md) referencing the old floor value

#### Scenario B: Remove --cov-fail-under from CI workflow

1. Remove `--cov-fail-under=<N>` from every pytest invocation in `.github/workflows/test.yml`
2. CI will inherit `fail_under` from `[tool.coverage.report]`

**Note**: If CI uses `--override-ini="addopts="` (clears all addopts), CI must specify its own `--cov-fail-under`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Removing flag only | Removed --cov-fail-under=9 from addopts without raising fail_under | Pre-commit consistency check script expected the flag in addopts | Always check for consistency-check scripts that validate addopts contents |
| Raising floor without measuring | Would have set fail_under=50 per issue suggestion | Would have left 27% gap below actual (77.42%) | Always measure actual coverage first, then set floor 2% below baseline |

## Results & Parameters

### v2.0.0 - Issue #1511, PR #1554

| Parameter | Value |
| ----------- | ------- |
| Previous combined floor | fail_under = 9 + --cov-fail-under=9 in addopts |
| New combined floor | fail_under = 75 (single source of truth) |
| Actual combined coverage | 77.42% (2.42% buffer) |
| Actual scylla/ unit coverage | 81.69% |
| Files changed | pyproject.toml, pixi.toml, CONTRIBUTING.md, CLAUDE.md, check script, tests |
| New pixi task | test-unit mirrors CI 75% scylla/ enforcement |

### v1.0.0 - Issue #754, PR #868

| Parameter | Value |
| ----------- | ------- |
| Threshold removed from CI | --cov-fail-under=72 |
| Authoritative threshold | fail_under = 73 in [tool.coverage.report] |
| Files changed | .github/workflows/test.yml |

## Key Insights

1. `[tool.coverage.report].fail_under` is sufficient - pytest-cov reads it automatically
2. CI with `--override-ini="addopts="` bypasses all addopts - CI must specify its own thresholds
3. Consistency check scripts are a hidden dependency - update them to accept absent flag
4. Dual-threshold design: fail_under for local combined, --cov-fail-under in CI for per-step

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1511, PR #1554 | Raised floor 9% to 75%, added test-unit task |
| ProjectScylla | Issue #754, PR #868 | Removed CI --cov-fail-under, aligned to pyproject.toml |
