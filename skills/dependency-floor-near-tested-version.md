---
name: dependency-floor-near-tested-version
description: "Pattern for raising a tool's version floor to match the tested minor version. Use when: (1) a dependency floor is much lower than the CI-resolved version, (2) adding a cross-manifest consistency regression guard for a dev tool."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Dependency Floor Near Tested Version

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Raise a dev tool's floor (e.g., `ruff>=0.1.0`) to match the tested minor (`>=0.15`) and add a cross-manifest regression guard |
| **Outcome** | Plan produced; implementation pending |
| **Verification** | unverified |

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
   - Use a `_find_xxx_dep` static method with PEP 508 specifier splitting (not `startswith`)
   - Add `test_xxx_floor_matches_across_manifests` and `test_xxx_upper_cap_matches_across_manifests`
   - Do NOT add a hardcoded sentinel test (`assert floor >= Version("0.15")`) — it goes stale
5. Verify the lock is still valid (`pixi run pytest` — if the lock satisfies the new floor, no re-solve needed)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded sentinel test | `assert floor >= Version("0.15")` in a test | Goes stale silently when lock bumps to 0.16.x | Use only cross-manifest comparison — no hardcoded expected values |
| `dep.startswith("ruff")` | Simple prefix check to find ruff in dev_deps list | Would match `ruff-lsp` or other ruff-prefixed packages | Use PEP 508 specifier splitting: split on `>=`,`==`,etc. then compare package name exactly |
| Separate pre-commit script | `scripts/check_ruff_floor_consistency.py` + pre-commit hook | Disproportionate for a single constraint; unit tests already run in CI | The existing `test_dependency_floor_consistency.py` gate is sufficient |

## Results & Parameters

**Floor target**: `>=<tested_minor>` where tested_minor is the first two version components of the lock-resolved version (e.g., `0.15.12` → `>=0.15`).

**Upper cap**: Keep unchanged (`<1` for ruff, `<3` for mypy) — consistent with existing patterns.

**Test class pattern** (copy-paste template):
```python
class TestRuffConsistency:
    @staticmethod
    def _find_ruff_dep(dev_deps: list[str]) -> str | None:
        for dep in dev_deps:
            head = dep.split(";", 1)[0].strip()
            for sep in ("<=", ">=", "==", "!=", "~=", "<", ">", "="):
                if sep in head:
                    pkg = head.split(sep, 1)[0].strip()
                    break
            else:
                pkg = head.strip()
            if pkg == "ruff":
                return dep
        return None

    def test_ruff_floor_matches_across_manifests(self, repo_root: Path) -> None:
        # load pyproject.toml + pixi.toml, extract floors, compare with Version()
        ...

    def test_ruff_upper_cap_matches_across_manifests(self, repo_root: Path) -> None:
        # load pyproject.toml + pixi.toml, extract caps, compare with Version()
        ...
```

**pixi.toml lookup key**: `pixi["feature"]["shared"]["dependencies"]["ruff"]` (not `feature.lint` — ruff is in `feature.shared`)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1201 planning | ruff floor >=0.1.0 → >=0.15; lock at 0.15.12 |
