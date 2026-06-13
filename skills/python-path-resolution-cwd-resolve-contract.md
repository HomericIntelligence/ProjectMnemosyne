---
name: python-path-resolution-cwd-resolve-contract
description: "Path resolution contract for get_repo_root and similar helpers: Path.cwd() must always be followed by .resolve(), and test assertions comparing resolved paths must call .resolve() on expected values. Use when: (1) implementing path-returning helpers, (2) writing tests for functions that return resolved paths, (3) diagnosing symlink-fragile test failures."
category: testing
date: 2026-06-13
version: "1.1.0"
user-invocable: false
verification: verified-local
history: python-path-resolution-cwd-resolve-contract.history
tags: []
---

# Python Path Resolution: CWD Resolve Contract

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix unresolved fallback in `get_repo_root` when `start_path is None` and symlink-fragile test assertions |
| **Outcome** | Successful — single-line fix plus two assertion fixes |
| **Verification** | verified-local |

## When to Use

- Implementing any helper that returns a `Path` and has a `Path.cwd()` fallback
- Writing tests that compare `result == some_path` where the function under test calls `.resolve()`
- Diagnosing intermittent test failures on macOS where `$TMPDIR` is a symlink through `/private/`
- Planning code reviews for path-returning utilities
- When writing a TDD regression guard for a path-returning helper — the test must assert `is_absolute()`, not just `isinstance(Path)`

## Verified Workflow

### Quick Reference

```python
# CORRECT: both branches resolve
start_path = Path.cwd().resolve() if start_path is None else Path(start_path).resolve()

# WRONG: cwd() branch unresolved — fallback returns inconsistent type
start_path = Path.cwd() if start_path is None else Path(start_path).resolve()

# CORRECT test assertion for resolved-path functions
assert result == mock_git_repo.resolve()

# FRAGILE test assertion — fails on macOS where $TMPDIR is a symlink
assert result == mock_git_repo
```

### Detailed Steps

1. When writing a helper that returns a resolved `Path`, ensure ALL branches call `.resolve()` — including the `Path.cwd()` fallback case.
2. Document the return contract in the docstring: "Returns an absolute, resolved Path."
3. When writing tests for such helpers, always call `.resolve()` on expected values in equality assertions.
4. To find existing fragile assertions: `grep -n "assert result ==" tests/` and check if the expected value calls `.resolve()`.
5. Add an explicit `is_absolute()` check to the `None`/fallback test case: `assert get_repo_root(None).is_absolute()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| isinstance-only regression guard | Used `assert isinstance(result, Path)` as the sole test for the `Path.cwd().resolve()` fix | Passes before AND after the fix on Linux — `Path.cwd()` is already absolute, so zero coverage | Fallback tests for resolved-path helpers MUST assert `is_absolute()` — isinstance proves type only |
| Relying on `isinstance(result, Path)` in fallback test | `test_uses_cwd_when_none` only checks `isinstance` | Does not verify the path is resolved/absolute — a symlink path is still a `Path` | Fallback tests must also assert `is_absolute()` to prove the resolve contract |
| Skipping `.resolve()` on `Path.cwd()` | `Path.cwd() if ... else Path(start_path).resolve()` | Returns unresolved path on fallback code path — inconsistent return type | Both branches of a ternary path assignment must call `.resolve()` |
| Comparing `result == tmp_path` in test | `assert result == mock_git_repo` | Fails on macOS where `tmp_path` is under `/var/folders/...` which is a symlink to `/private/var/...`; `get_repo_root` resolves through the symlink but `tmp_path` does not | Always call `.resolve()` on expected path values in test equality checks |

## Results & Parameters

**Pattern: Path-returning helper with fallback**
```python
def get_something(start_path: str | Path | None = None) -> Path:
    # Always resolve both branches
    start_path = Path.cwd().resolve() if start_path is None else Path(start_path).resolve()
    # ... logic ...
    return start_path  # guaranteed to be resolved on all code paths
```

**Pattern: Test assertion for resolved-path function**
```python
# After: pytest fixture mock_git_repo = tmp_path / "repo"
result = get_repo_root(mock_git_repo)
assert result == mock_git_repo.resolve()  # not: == mock_git_repo
```

**Pattern: Fallback test with resolve-contract assertion**
```python
def test_uses_cwd_when_none():
    result = get_repo_root(None)
    assert isinstance(result, Path)
    assert result.is_absolute()  # proves the resolve contract
```

**TDD regression guard — insufficient vs required:**
```python
# INSUFFICIENT — passes before and after fix on Linux:
assert isinstance(result, Path)

# REQUIRED regression guard — fails before fix on symlinked $TMPDIR, passes after:
assert result.is_absolute()
```

**Audit command to find fragile assertions:**
```bash
grep -n "assert result ==" tests/unit/utils/test_general_utils.py
# Check each one: does the RHS call .resolve()?
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1309 follow-up to #1267 | `hephaestus/utils/helpers.py:117`, `tests/unit/utils/test_general_utils.py:140,152` |
