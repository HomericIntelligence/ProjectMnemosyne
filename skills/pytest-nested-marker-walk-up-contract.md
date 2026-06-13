---
name: pytest-nested-marker-walk-up-contract
description: "Pin the first-match-up (innermost-wins) contract of walk-up path resolvers using pytest tmp_path. Use when: (1) testing a function that walks up from a seed path returning the first ancestor containing a filesystem marker (.git, pyproject.toml, config file), (2) tests must assert equality against a resolved path returned by the SUT (Path(start_path).resolve() pattern), (3) building the nested-marker matrix (outer/inner with same or mixed markers) to pin innermost-wins semantics, (4) CI runs on macOS or symlinked-tmpdir Linux where bare tmp_path subpaths differ from their resolved form."
category: testing
date: 2026-06-13
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pytest
  - tmp_path
  - path-resolution
  - walk-up
  - nested-markers
  - get_repo_root
  - innermost-wins
  - first-match-up
  - symlink
  - resolve
---

# pytest: Nested Marker Walk-Up Contract

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Pin the first-match-up (innermost-wins) contract of `get_repo_root()` for nested filesystem marker scenarios |
| **Outcome** | Four tests cover the full nested-marker matrix; 4058 tests pass, coverage 85.57% |
| **Verification** | verified-ci |
| **History** | v1.0.0 was plan-only/unverified; v2.0.0 promotes to verified-ci and fixes critical assertion bug (`inner` → `inner.resolve()`) |
| **Project** | ProjectHephaestus |
| **Issue** | [#1267](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1267) |
| **PR** | [#1307](https://github.com/HomericIntelligence/ProjectHephaestus/pull/1307) |

## When to Use

- A function walks upward from a seed path and returns the first ancestor containing a marker (`.git`, `pyproject.toml`, `setup.cfg`, any sentinel file)
- The SUT calls `Path(start_path).resolve()` before walking — return value is always a resolved path
- Need to pin the "innermost-wins" contract when the same marker type exists in both a parent and child directory
- Need to cover mixed-marker scenarios (outer has `.git`, inner has `pyproject.toml`, and vice versa)
- CI runs on macOS or any environment where `$TMPDIR` is a symlink (macOS: `/var/folders/...` → `/private/var/folders/...`)

## Verified Workflow

### Quick Reference

```python
def test_nested_git_stops_at_inner_git(self, tmp_path):
    """Inner .git wins over outer .git — first-match-up (innermost) semantics."""
    outer = tmp_path / "outer"
    inner = outer / "inner"
    (outer / ".git").mkdir(parents=True)
    (inner / ".git").mkdir(parents=True)
    seed = inner / "src" / "module"
    seed.mkdir(parents=True)
    assert get_repo_root(seed) == inner.resolve()  # NOT inner — must resolve()

def test_nested_pyproject_stops_at_inner_pyproject(self, tmp_path):
    """Inner pyproject.toml wins over outer pyproject.toml."""
    outer = tmp_path / "outer"
    inner = outer / "inner"
    outer.mkdir(parents=True)
    inner.mkdir(parents=True)
    (outer / "pyproject.toml").write_text("[project]\n")
    (inner / "pyproject.toml").write_text("[project]\n")
    seed = inner / "src"
    seed.mkdir(parents=True)
    assert get_repo_root(seed) == inner.resolve()

def test_nested_pyproject_stops_at_inner_when_outer_has_git(self, tmp_path):
    """Inner pyproject.toml wins over outer .git."""
    outer = tmp_path / "outer"
    inner = outer / "inner"
    (outer / ".git").mkdir(parents=True)
    inner.mkdir(parents=True)
    (inner / "pyproject.toml").write_text("[project]\n")
    seed = inner / "src"
    seed.mkdir(parents=True)
    assert get_repo_root(seed) == inner.resolve()

def test_nested_git_stops_at_inner_when_outer_has_pyproject(self, tmp_path):
    """Inner .git wins over outer pyproject.toml."""
    outer = tmp_path / "outer"
    inner = outer / "inner"
    outer.mkdir(parents=True)
    (outer / "pyproject.toml").write_text("[project]\n")
    (inner / ".git").mkdir(parents=True)
    seed = inner / "src"
    seed.mkdir(parents=True)
    assert get_repo_root(seed) == inner.resolve()
```

### Detailed Steps

1. **Audit the SUT for `resolve()` calls** before writing tests:
   ```python
   # If the SUT has this pattern:
   start = Path(start_path).resolve()  # or Path(...).resolve() anywhere before the walk
   # Then ALL expected paths in assertions must also be .resolve()d
   ```
   In `hephaestus/utils/helpers.py:117` this is `current = Path(start_path).resolve()`.

2. **Build the nested directory structure** inline (no fixtures needed):
   - Create `outer` and `outer/inner` with `mkdir(parents=True)`
   - Place the marker in both outer and inner
   - Create `seed` as a subdirectory under `inner` — the walk must pass through `inner` before reaching `outer`

3. **Create markers correctly**:
   - `.git` as a bare **directory**: `(inner / ".git").mkdir(parents=True)` — the resolver uses `.exists()`, NOT `git.is_valid_repo()`
   - `pyproject.toml` as a file: `(inner / "pyproject.toml").write_text("[project]\n")`
   - Do NOT call `git init` — it creates extra files and is slower; `.exists()` suffices

4. **Cover the full nested-marker matrix** (4 combinations for 2-marker resolvers):

   | Test | Outer marker | Inner marker | Asserts stops at |
   |------|-------------|--------------|-----------------|
   | `test_nested_git_stops_at_inner_git` | `.git` | `.git` | `inner.resolve()` |
   | `test_nested_pyproject_stops_at_inner_pyproject` | `pyproject.toml` | `pyproject.toml` | `inner.resolve()` |
   | `test_nested_pyproject_stops_at_inner_when_outer_has_git` | `.git` | `pyproject.toml` | `inner.resolve()` |
   | `test_nested_git_stops_at_inner_when_outer_has_pyproject` | `pyproject.toml` | `.git` | `inner.resolve()` |

5. **Use explicit methods** (not `parametrize`) when the existing test class uses explicit methods — keeps failure messages readable and is consistent with the established style.

6. **Grep for duplicates** before inserting:
   ```bash
   grep -n "nested\|outer.*inner\|inner.*outer\|inner\.git\|inner.*pyproject" tests/unit/utils/test_general_utils.py
   # Expected: zero hits (or hits only in unrelated test classes)
   ```

7. **Run the full test class** to verify no regressions:
   ```bash
   pixi run pytest tests/unit/utils/test_general_utils.py::TestGetRepoRoot -v
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `assert get_repo_root(seed) == inner` (no `.resolve()`) | Compared resolved return against unresolved `tmp_path` subpath | Passes on non-symlinked CI (Ubuntu) but fails on macOS where `$TMPDIR=/var/folders/...` resolves to `/private/var/folders/...` | Always call `.resolve()` on expected paths when the SUT calls `Path(...).resolve()` |
| `git init` to create `.git` | Called `subprocess.run(["git", "init", str(inner)])` to create a proper repo | Adds latency, creates extra files (`.git/config`, `.git/HEAD`, etc.), and is fragile if git is not on PATH in all CI environments | Use `(path / ".git").mkdir(parents=True)` — the resolver checks `.exists()` only |
| Copy existing `test_finds_git_repo` assertion style (`== mock_git_repo` without `.resolve()`) | Used the existing test as a template without auditing for `.resolve()` | The existing test passes only because Ubuntu CI `$TMPDIR` is not a symlink — it's a latent fragility, not a pattern to copy | Always audit the SUT for `.resolve()` calls; don't trust an existing test's assertion style without checking |
| `parametrize` over the 4 cases | Converted 4 methods to a single `@pytest.mark.parametrize` | Inconsistent with the existing `TestGetRepoRoot` class style (explicit `def test_*` methods); adds indirection for minimal gain | Prefer explicit methods when the existing class already uses that pattern; KISS |
| Shared fixture for layout construction | Extract `outer`/`inner` directory setup into a `@pytest.fixture` | Different marker combos need different structures; fixtures complicate without adding value | Build layouts inline in each test method; `tmp_path` is already a pytest fixture |

## Results & Parameters

- **Test count**: 4 new methods in `TestGetRepoRoot`
- **Full suite result**: 4058 passed, 21 skipped, coverage 85.57% (ProjectHephaestus)
- **Insertion point**: After `test_uses_cwd_when_none`, inside `TestGetRepoRoot`, before the next class
- **Marker creation**: `(path / ".git").mkdir(parents=True)` for dir markers, `.write_text(...)` for file markers
- **Assertion pattern**: `assert get_repo_root(seed) == inner.resolve()` — always resolve expected
- **Seed depth**: `seed = inner / "src" / "module"; seed.mkdir(parents=True)` — at least 2 levels below inner so the walk is non-trivial

## Critical Insight: resolve() Symmetry

The SUT (`get_repo_root()`) calls `Path(start_path).resolve()` at line 117 before walking. This means:

1. The return value is always a resolved (symlink-free) absolute path
2. Any assertion comparing against an unresolved `tmp_path` subpath will be fragile
3. On macOS, `pytest`'s `tmp_path` may be under `/var/folders/...` which is a symlink to `/private/var/folders/...`
4. `inner.resolve()` in the test mirrors the SUT's own resolve call — this is the correct pattern

The existing test `test_finds_git_repo` uses `== mock_git_repo` without `.resolve()` and passes only because Ubuntu CI's `$TMPDIR` is not a symlink. That is a latent fragility — do NOT copy that pattern.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1267 / PR #1307 | 4 nested-marker tests added; 4058 tests pass; coverage 85.57%; verified-ci |
