# Move Loose Test Files Into Sub-packages

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Move test files from `tests/unit/` root into sub-packages mirroring source structure |
| **Outcome** | ✅ All 3 files moved, 2432 tests pass (identical to baseline), PR #964 merged |
| **PR** | HomericIntelligence/ProjectScylla#964 |

## Overview

When test files accumulate at the `tests/unit/` root level they break the convention where tests
mirror the source package structure. This skill documents the safe, repeatable process for
relocating them into the correct sub-packages with full git history preservation.

**Context**: ProjectScylla enforces `tests/unit/<subpackage>/` mirroring of `scylla/<subpackage>/`.
The same pattern applies to any Python project that uses mirrored test layouts.

## When to Use This Skill

Invoke when:

- A quality audit identifies `.py` test files at `tests/unit/` root (excluding `__init__.py`, `conftest.py`)
- A new source sub-package `scylla/X/` exists but its tests landed in `tests/unit/` root
- CI reports test discovery inconsistencies due to misplaced files
- Code review flags test files at the wrong level

## Verified Workflow

### Step 1 — Capture Baseline

```bash
pixi run pytest tests/unit/ -v --tb=short 2>&1 | tail -5
# Record: "N passed, M warnings"
```

### Step 2 — Check for Naming Conflicts

Before moving, verify the destination doesn't already contain a file with the same name:

```bash
ls tests/unit/<subpackage>/
```

If a conflict exists, use a distinct name (e.g. keep `test_config_loader.py` instead of
renaming to `test_loader.py` if `test_loader.py` already exists).

### Step 3 — Check for Fixture Path Dependencies

Read the file being moved and find any `Path(__file__)` expressions:

```python
# BEFORE MOVE (tests/unit/test_config_loader.py):
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
# .parent -> tests/unit/, .parent -> tests/, / "fixtures" -> tests/fixtures/ ✓

# AFTER MOVE (tests/unit/config/test_config_loader.py):
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
# .parent -> tests/unit/config/, .parent -> tests/unit/, / "fixtures" -> tests/unit/fixtures/ ✗
# FIX: Add one more .parent
FIXTURES_PATH = Path(__file__).parent.parent.parent / "fixtures"
# .parent -> tests/unit/config/, .parent.parent -> tests/unit/, .parent.parent.parent -> tests/ ✓
```

**Rule**: Moving one directory level deeper requires one additional `.parent` in any
`Path(__file__).parent...` fixture path expression.

### Step 4 — Move Each File with git mv

```bash
git mv tests/unit/test_foo.py tests/unit/<subpackage>/test_foo.py
```

Using `git mv` preserves the full commit history (visible in `git log --follow`).

### Step 5 — Fix Fixture Paths (if needed)

After moving, update `Path(__file__)` fixture path expressions in the moved file.
Apply the `+1 parent` rule from Step 3 for each directory level gained.

### Step 6 — Run Sub-package Tests

```bash
pixi run pytest tests/unit/<subpackage>/ -v --tb=short --no-cov
```

All tests in the sub-package must pass before moving to the next file.

### Step 7 — Full Suite Verification

```bash
pixi run pytest tests/unit/ -v --tb=short 2>&1 | tail -5
```

The final pass count MUST be identical to the baseline from Step 1.

### Step 8 — Pre-commit Hooks

```bash
pre-commit run --all-files
```

Fix any issues surfaced before committing.

### Step 9 — Commit and PR

```bash
git add tests/unit/<subpackage>/test_foo.py  # stage the moved + edited file
git commit -m "refactor(tests): move loose test files into proper sub-packages"
git push -u origin <branch>
gh pr create --title "refactor(tests): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

### ❌ Using `Path(__file__).parent.parent / "fixtures"` After Moving One Level Deeper

**What happened**: Moved `tests/unit/test_config_loader.py` to `tests/unit/config/test_config_loader.py`
without updating the fixture path. The path expression `Path(__file__).parent.parent` now resolved
to `tests/unit/` instead of `tests/`, so `/ "fixtures"` looked for `tests/unit/fixtures/` which
doesn't exist.

**Symptom**: 18 tests in `TestConfigLoaderEvalCase`, `TestConfigLoaderRubric`, `TestConfigLoaderTier`,
`TestConfigLoaderMerged` all failed with `ConfigurationError: Configuration file not found`.

**Fix**: Added one extra `.parent`:
```python
# Before (wrong after move):
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"

# After (correct):
FIXTURES_PATH = Path(__file__).parent.parent.parent / "fixtures"
```

**Lesson**: Always count directory levels from the moved file's new location to the fixtures root,
not its old location.

### ❌ Renaming to Match Issue's Proposed Destination Name Without Checking for Conflicts

**Risk**: The issue proposed `test_config_loader.py` → `tests/unit/config/test_loader.py`.
`tests/unit/config/test_loader.py` already existed (tests production model config validation).

**Lesson**: Always `ls` the destination directory before choosing the destination filename.
When a conflict exists, keep the source filename (e.g. `test_config_loader.py`) rather than
clobbering existing tests.

## Results & Parameters

**Baseline**: 2432 passed, 8 warnings
**After all moves**: 2432 passed, 8 warnings (identical)
**Coverage**: 74.16% (unchanged, above 73% threshold)

**Files moved**:
```
tests/unit/test_config_loader.py     → tests/unit/config/test_config_loader.py  (+path fix)
tests/unit/test_docker.py            → tests/unit/executor/test_docker.py
tests/unit/test_grading_consistency.py → tests/unit/metrics/test_grading_consistency.py
```

**Code change required** (only one file needed a code edit):
```python
# tests/unit/config/test_config_loader.py line 32
# BEFORE:
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
# AFTER:
FIXTURES_PATH = Path(__file__).parent.parent.parent / "fixtures"
```

**CI note**: No changes needed to `.github/workflows/` — CI uses directory-level paths
(`tests/unit/`), not individual filenames, so test discovery is automatic.

**`__init__.py` note**: All target sub-directories already had `__init__.py` files.
If a sub-directory lacks `__init__.py`, create one before moving the test file.

## Related Skills

- `fix-tests-after-config-refactor` — Fixing test failures after source code is restructured
- `config-dir-consolidation` — File move pattern with git history preservation
- `ci-test-matrix-management` — Verifying CI doesn't hardcode individual test file paths
