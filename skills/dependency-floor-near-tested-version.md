---
name: dependency-floor-near-tested-version
description: "Pattern for raising a tool's version floor to match the tested minor version. Use when: (1) a dependency floor is much lower than the CI-resolved version, (2) adding a cross-manifest consistency regression guard for a dev tool."
category: ci-cd
date: 2026-06-13
version: "1.1.0"
user-invocable: false
verification: unverified
history: dependency-floor-near-tested-version.history
tags: []
---

# Dependency Floor Near Tested Version

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Raise a dev tool's floor (e.g., `ruff>=0.1.0`) to match the tested minor (`>=0.15`) and add a cross-manifest regression guard |
| **Outcome** | Plan approved (NOGO→GO after DRY fix); implementation pending |
| **Verification** | unverified |
| **History** | [changelog](./dependency-floor-near-tested-version.history) |

## When to Use

- A dependency floor in `pyproject.toml` or `pixi.toml` is much lower than what the lock resolves (e.g., `>=0.1.0` but lock resolves `0.15.12`)
- A dev tool (ruff, mypy, pytest) has no cross-manifest consistency test in `tests/unit/scripts/test_dependency_floor_consistency.py`
- A pip-install `.[dev]` consumer could land on a version with a different default behavior than CI enforces

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Confirm what the lock resolves
grep "name: ruff" pixi.lock   # or grep the conda URL

# 2. Update both manifests together
# pyproject.toml: "ruff>=0.1.0,<1" → "ruff>=0.15,<1"
# pixi.toml [feature.shared.dependencies]: ruff = ">=0.1.0,<1" → ruff = ">=0.15,<1"

# 3. No lock re-solve needed if lock already satisfies the new floor
# (0.15.12 satisfies >=0.15 — pixi install not required)

# 4. Add TestRuffConsistency to tests/unit/scripts/test_dependency_floor_consistency.py

# 5. Run verification
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v
pixi run ruff check hephaestus scripts tests
```

### Detailed Steps

1. Grep the lock to confirm the resolved version: `grep "ruff-" pixi.lock | grep conda`
2. Check all pixi.toml locations: `grep -n "ruff" pixi.toml` — confirm only one entry exists
3. Raise the floor in both `pyproject.toml` and `pixi.toml` to `>=<tested_minor>`
4. Add a `TestXxxConsistency` class to `test_dependency_floor_consistency.py` mirroring `TestPytestConsistency` (lines 231–331):
   - **Reuse `TestPytestConsistency._find_dep(dev_deps, "ruff")`** — do NOT copy/duplicate the helper; it already accepts a `name` parameter for exactly this purpose
   - Add `test_xxx_floor_matches_across_manifests` and `test_xxx_upper_cap_matches_across_manifests`
   - Do NOT add a hardcoded sentinel test (`assert floor >= Version("0.15")`) — it goes stale
   - Add a docstring note if the test only checks one pixi feature section (e.g., `[feature.shared]`)
5. Verify the lock is still valid (`pixi run pytest` — if the lock satisfies the new floor, no re-solve needed)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded sentinel test | `assert floor >= Version("0.15")` in a test | Goes stale silently when lock bumps to 0.16.x | Use only cross-manifest comparison — no hardcoded expected values |
| `dep.startswith("ruff")` | Simple prefix check to find ruff in dev_deps list | Would match `ruff-lsp` or other ruff-prefixed packages | Use PEP 508 specifier splitting via the existing `_find_dep(dev_deps, name)` helper |
| Copying `_find_dep` as new per-class helper | Defined `_find_ruff_dep` as verbatim copy of `TestPytestConsistency._find_dep` with `"ruff"` hardcoded | DRY violation; reviewer NOGO'd; `_find_dep` already takes `name` parameter | Call `TestPytestConsistency._find_dep(dev_deps, "ruff")` directly |
| Separate pre-commit script | `scripts/check_ruff_floor_consistency.py` + pre-commit hook | Disproportionate for a single constraint; unit tests already run in CI | The existing `test_dependency_floor_consistency.py` gate is sufficient |

## Results & Parameters

**Floor target**: `>=<tested_minor>` where tested_minor is the first two version components of the lock-resolved version (e.g., `0.15.12` → `>=0.15`).

**Upper cap**: Keep unchanged (`<1` for ruff, `<3` for mypy) — consistent with existing patterns.

**Test class pattern** (approved template — reuses existing helper, no duplication):
```python
class TestRuffConsistency:
    """Tests for ruff floor/cap consistency across pyproject.toml and pixi.toml.

    Note: reads pixi.toml [feature.shared.dependencies] only — if ruff is ever
    added under [feature.lint.dependencies], extend this test to check that key.
    """

    def test_ruff_floor_matches_across_manifests(self, repo_root: Path) -> None:
        with open(repo_root / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
        # Reuse existing helper — do NOT copy it into a new _find_ruff_dep method
        pyproject_spec = TestPytestConsistency._find_dep(dev_deps, "ruff")
        assert pyproject_spec is not None

        with open(repo_root / "pixi.toml", "rb") as f:
            pixi = tomllib.load(f)
        pixi_shared_spec = pixi["feature"]["shared"]["dependencies"]["ruff"]

        assert Version(_floor(pyproject_spec)) == Version(_floor(pixi_shared_spec)), (
            "ruff floor skew — update both together, see issue #1201."
        )

    def test_ruff_upper_cap_matches_across_manifests(self, repo_root: Path) -> None:
        # same structure as above but using _upper_cap()
        ...
```

**pixi.toml lookup key**: `pixi["feature"]["shared"]["dependencies"]["ruff"]` (not `feature.lint` — ruff is in `feature.shared`)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1201 planning (plan approved after v1.1.0 DRY fix) | ruff floor >=0.1.0 → >=0.15; lock at 0.15.12 |
