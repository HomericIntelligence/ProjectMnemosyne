---
name: narrow-mypy-override-subset
description: Narrow a broad mypy module glob override to an explicit list when a subset
  of subdirs is fully annotated. Use when annotating tests/unit/<subdir>/ and removing
  it from a blanket suppressor.
category: testing
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# Narrow Mypy Override for Annotated Subset

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Issue** | #1287 — Annotate test functions in `tests/unit/scripts/` for mypy compliance |
| **Objective** | Ensure `tests/unit/scripts/` is mypy-compliant and excluded from the `no-untyped-def` suppressor |
| **Outcome** | ✅ Success — all 9 files were already annotated; replaced `tests.unit.*` glob with 14-entry explicit list excluding `tests.unit.scripts.*` |

## When to Use

Use this skill when:

- Fixing a GitHub issue to annotate test functions in one specific `tests/unit/<subdir>/`
- There is a broad `[[tool.mypy.overrides]]` block with `module = "tests.unit.*"` suppressing
  `no-untyped-def` for the whole `tests/unit/` tree
- You want to promote one subdir out of the suppressor without disrupting the others
- You need to verify whether a subdir is already annotated before doing any work

## Key Insight: Triage Before Editing Test Files

The annotation task may already be complete. Always run mypy against the target subdir **with
`--disallow-untyped-defs`** before touching any test file:

```bash
pixi run mypy tests/unit/scripts/ --disallow-untyped-defs
# If "Success: no issues found" — the subdir is already annotated
# Only then narrow the pyproject.toml override; no test files need editing
```

In this session `tests/unit/scripts/` had zero mypy errors — all 192 tests were annotated from
the start. The only change needed was in `pyproject.toml`.

## Verified Workflow

### 1. Triage the Target Subdir

```bash
# Check the target subdir directly (override not yet in effect here — we're probing)
pixi run mypy tests/unit/scripts/ --disallow-untyped-defs
```

If `Success: no issues found` → skip to step 3. Otherwise annotate functions in the target
subdir (add `-> None` to test functions, type-hint fixture parameters).

### 2. (If Needed) Annotate Test Functions

For each unannotated test function, add `-> None` return type and type-hint parameters:

```python
# Before
def test_something(tmp_path, mock_config):
    ...

# After
def test_something(tmp_path: pathlib.Path, mock_config: MockConfig) -> None:
    ...
```

Fixtures get typed based on their return annotation. `pytest.fixture` functions also need
`-> <ReturnType>`. Parametrize IDs don't need annotation changes.

### 3. Find All Remaining Subdirs That Still Need the Suppressor

```bash
# Remove the broad override temporarily, then:
pixi run mypy tests/unit/ --disallow-untyped-defs --no-error-summary 2>&1 \
  | grep "error:" | sed 's|tests/unit/||;s|/.*||' | sort -u
```

Example output (what still needs suppression):
```
adapters
analysis
automation
e2e
executor
judge
metrics
```

### 4. Replace the Broad Glob with an Explicit List

In `pyproject.toml`, replace:

```toml
# Before — broad glob suppresses everything including already-annotated scripts
[[tool.mypy.overrides]]
module = "tests.unit.*"
disable_error_code = ["no-untyped-def"]
```

With an explicit list of remaining subdirs:

```toml
# After — scripts excluded; each remaining subdir listed explicitly
# tests/unit/scripts/ is fully annotated (#1287). Remaining subdirs still have
# unannotated test functions — suppress no-untyped-def until each is annotated.
[[tool.mypy.overrides]]
module = [
    "tests.unit.adapters.*",
    "tests.unit.analysis.*",
    "tests.unit.automation.*",
    "tests.unit.cli.*",
    "tests.unit.config.*",
    "tests.unit.core.*",
    "tests.unit.discovery.*",
    "tests.unit.docker.*",
    "tests.unit.e2e.*",
    "tests.unit.executor.*",
    "tests.unit.judge.*",
    "tests.unit.metrics.*",
    "tests.unit.reporting.*",
    "tests.unit.utils.*",
]
disable_error_code = ["no-untyped-def"]
```

**Note**: mypy `[[tool.mypy.overrides]]` accepts a `module` array as of mypy 0.930+. This is
cleaner than multiple `[[tool.mypy.overrides]]` stanzas.

### 5. Verify Full Mypy Pass

```bash
pixi run mypy tests/unit/ scylla/ scripts/
# Expected: Success: no issues found in N source files
```

### 6. Run the Target Subdir Tests

```bash
pixi run python -m pytest tests/unit/scripts/ --no-cov -v
# Expected: all tests pass
```

### 7. Commit and PR

```bash
git add pyproject.toml
git commit -m "feat(mypy): narrow no-untyped-def override to exclude tests.unit.scripts

tests/unit/scripts/ is fully annotated with -> None return types and
typed parameters for mypy compliance.

Closes #1287"
git push -u origin 1287-auto-impl
gh pr create --title "feat(mypy): narrow no-untyped-def override to exclude tests.unit.scripts" \
  --body "Closes #1287"
gh pr merge --auto --rebase
```

## Failed Attempts

### Attempted Full Override Removal

Initially removed the entire `[[tool.mypy.overrides]]` block and ran full mypy — got 105 errors
across 12 files in `tests/unit/e2e/`, `tests/unit/analysis/`, `tests/unit/automation/`, and
other subdirs. These are not in scope for #1287.

**Lesson**: Check all subdirs before removing a broad override, not just the target subdir.

## Results & Parameters

```
Target subdir:          tests/unit/scripts/ (9 files)
Test functions checked: 192 passed
Mypy errors found:      0 (already annotated)
Test files modified:    0
pyproject.toml change:  broad glob → 14-entry explicit module list
Full mypy scope:        327 source files — Success: no issues found
PR:                     https://github.com/HomericIntelligence/ProjectScylla/pull/1316
```

## Related Skills

- `mypy-scripts-coverage-extension` — For removing a blanket `ignore_errors = true` override
  from a directory that is fully type-clean
- `mypy-per-directory-baseline` — For tracking per-directory error counts when overrides still
  exist
- `mypy-living-baseline` — For tracking and reducing error counts incrementally
