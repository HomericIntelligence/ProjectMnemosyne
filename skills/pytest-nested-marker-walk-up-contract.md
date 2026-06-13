---
name: pytest-nested-marker-walk-up-contract
description: "Documents planning patterns for nested-marker test coverage of walk-up path resolvers. Use when: (1) writing tests for functions that walk directory trees looking for marker files (e.g., .git, pyproject.toml), (2) pinning first-match-up (innermost-wins) contracts against regressions, (3) testing nested-repo scenarios where a seed path may sit inside a sub-repo nested under a parent repo."
category: testing
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: ["pytest", "walk-up", "get_repo_root", "nested-marker", "tmp_path", "first-match"]
---

# pytest-nested-marker-walk-up-contract

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Pin the walk-up resolver's first-match-up (innermost-wins) contract with nested-marker test layouts to prevent regressions when a seed path sits inside a sub-repo nested under a parent repo |
| **Outcome** | Planning complete — four test cases designed; not yet executed |
| **Verification** | unverified (plan only, tests not run, CI not observed) |
| **History** | N/A (initial version) |

## When to Use

- You are writing or reviewing tests for a function that walks up a directory tree looking for marker files (`.git`, `pyproject.toml`, `WORKSPACE`, etc.)
- You need to pin the "innermost-wins" / "first-match-up" contract — i.e., the walk terminates at the nearest ancestor that has the marker, not the outermost one
- You are guarding against regressions where a seed path inside a nested sub-repo might incorrectly resolve to the outer parent repo root
- The function under test is `get_repo_root()` in `hephaestus/utils/helpers.py` (lines 99–127) or any analogous walk-up resolver
- You need exhaustive cross-combination coverage of multiple supported marker types

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
# Minimal inline layout construction — no shared fixture needed
def test_nested_git_over_git(tmp_path):
    outer = tmp_path / "outer"
    inner = outer / "inner"
    (outer / ".git").mkdir(parents=True)
    (inner / ".git").mkdir(parents=True)
    seed = inner / "src"
    seed.mkdir(parents=True)
    assert get_repo_root(seed) == inner
```

### Detailed Steps

1. **Identify the existing test class boundary** — read `tests/unit/utils/test_general_utils.py` to find the enclosing class (e.g., `TestGetRepoRoot` at lines 132–157 as of the planning session; line numbers may shift if file was edited).

2. **Add four new test methods** covering every cross-combination of the two supported markers (`.git` directory and `pyproject.toml` file):

   | Test Method | Outer Marker | Inner Marker | Seed Location | Expected Result |
   |-------------|--------------|--------------|---------------|-----------------|
   | `test_nested_git_over_git` | `.git` dir | `.git` dir | `inner/src/` | `inner/` |
   | `test_nested_pyproject_over_pyproject` | `pyproject.toml` file | `pyproject.toml` file | `inner/src/` | `inner/` |
   | `test_nested_git_over_pyproject` | `.git` dir | `pyproject.toml` file | `inner/src/` | `inner/` |
   | `test_nested_pyproject_over_git` | `pyproject.toml` file | `.git` dir | `inner/src/` | `inner/` |

3. **Build layouts inline with `tmp_path`** — do not extract to a shared fixture. Each test constructs its own `outer/.git` (or `outer/pyproject.toml`) and `outer/inner/.git` (or `outer/inner/pyproject.toml`) from scratch. This keeps tests self-contained and avoids fixture coupling.

4. **Place the seed one level below the inner marker** (`inner/src`) — this confirms the walk terminates at `inner/`, not `outer/`, and that the resolver doesn't over-walk past the first match.

5. **Assert `get_repo_root(seed) == inner`** (not `outer`) for all four cases.

6. **Run tests locally** before pushing:
   ```bash
   pixi run pytest tests/unit/utils/test_general_utils.py::TestGetRepoRoot -v
   ```

7. **Verify no existing nested-marker test already exists** before adding:
   ```bash
   grep -n "nested\|outer.*inner\|inner.*outer" tests/unit/utils/test_general_utils.py
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Shared fixture for layout construction | Extract `outer`/`inner` directory setup into a `@pytest.fixture` | Fixtures complicate the test by introducing indirection and coupling multiple tests to one setup shape; different marker combos need different structures | Build layouts inline in each test method; `tmp_path` is already a pytest fixture, no extra layer needed |
| Single "representative" test | Cover only `git+git` nesting and skip pyproject combos | Misses cross-marker interaction bugs where the resolver treats `.git` and `pyproject.toml` with different priority logic | All four cross-combinations are required for full contract coverage |
| Seed placed at `inner/` directly | Pass `inner/` (the marker directory) as the seed | If the walk starts at a directory that IS the marker level, it may trivially return `inner/` without exercising the walk-termination logic | Place seed one level below inner marker (`inner/src`) to force the walk to actually traverse upward |

## Results & Parameters

### Inline Layout Pattern

```python
# For .git marker: create a directory named .git (no need for a real git repo)
(outer / ".git").mkdir(parents=True)
# get_repo_root() checks .exists() only, not whether it is a real git repo

# For pyproject.toml marker: create an empty file
(outer / "pyproject.toml").touch()
```

### Confirmed Behavior of `get_repo_root()` (helpers.py:99–127)

- Uses `Path(start_path).resolve()` before walking — resolves symlinks
- Walks upward via `.parent` until a `.git` dir or `pyproject.toml` file is found
- Returns the **first** (innermost) ancestor that has a marker — does NOT continue to outer
- Returns `None` (or raises) if neither marker is found before reaching filesystem root

### Risk Notes

- `(outer / ".git").mkdir(parents=True)` creates a **directory** named `.git`, not a real git repo. Confirm `get_repo_root()` checks `.exists()` only, not `.is_dir()` vs `.is_file()` specifically — as of planning session, inspection confirmed `.exists()` is used.
- `Path(start_path).resolve()` can follow symlinks on some CI environments and escape `tmp_path`. This is a low-probability risk but worth noting for debugging if tests behave unexpectedly on CI.
- Confirm no existing test already covers nested markers before adding the four new cases (`grep -n "nested" tests/unit/utils/test_general_utils.py`).
- Line numbers for the existing `TestGetRepoRoot` class boundary (132–157 as of planning) may have shifted; always re-read the file before inserting new methods.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning session for issue #1267 — adding nested-marker test coverage | Plan only; tests not executed |
