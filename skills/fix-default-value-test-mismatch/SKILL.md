# Fix Default Value Test Mismatch

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-13 |
| **Category** | testing |
| **Objective** | Fix failing CI test caused by default value change in source code |
| **Outcome** | ✅ One-line test fix, all tests passing, CI green |
| **Context** | Test failure on main branch for 5+ consecutive CI runs |

## When to Use

Use this skill when:

- CI shows test failures related to default values
- A commit changed a default value but tests weren't updated
- Assertion errors show expected vs actual mismatch for default values
- Test name includes `test_default_values` or similar
- Error message shows `assert options.<field> is <value>` failing

## Problem Pattern

**Root Cause**: Source code default value changed, but test assertion not updated.

**Example**:

```python
# Commit 6055dda changed this in scylla/automation/models.py:
enable_retrospective: bool = True  # Was: False

# But test still expected old default:
assert options.enable_retrospective is False  # ❌ FAILS
```

## Verified Workflow

### 1. Identify the Mismatch

```bash
# Find the failing test in CI logs or run locally
pixi run python -m pytest tests/unit/automation/test_models.py::TestImplementerOptions::test_default_values -v
```

**Look for**:

- Assertion errors with `is False` vs `is True`
- Test method named `test_default_values` or `test_defaults`
- Recent commits that changed default values

### 2. Locate Source of Truth

```bash
# Find the model/class definition
git log --oneline --all -S "enable_retrospective" | head -5
```

**Check**:

- What is the CURRENT default value in source code?
- When was it changed (git blame)?
- Was the test updated in the same commit?

### 3. Update the Test

```python
# Read the test file to see exact line
Read(file_path="tests/unit/automation/test_models.py", offset=305, limit=10)

# Fix the assertion to match current source code default
Edit(
    file_path="tests/unit/automation/test_models.py",
    old_string="        assert options.enable_retrospective is False",
    new_string="        assert options.enable_retrospective is True"
)
```

### 4. Verify Fix

```bash
# Run the specific test
pixi run python -m pytest tests/unit/automation/test_models.py::TestImplementerOptions::test_default_values -v

# Run full unit suite
pixi run python -m pytest tests/unit/ -v

# Run pre-commit hooks
pre-commit run --all-files
```

**Expected Output**:

- Specific test: PASSED ✅
- Full suite: All tests passing
- Pre-commit: All checks green

### 5. Commit and PR

```bash
# Stage changes
git add tests/unit/automation/test_models.py

# Commit with clear message
git commit -m "fix(tests): Update test_default_values for <field>=<new_value>

Fixed failing test that was broken since commit <hash>. The test assertion
expected <field>=<old_value> but the default was changed to <new_value>.

Verification:
- Specific test passes: test_default_values
- Full unit suite passes: <count> passed
- Pre-commit hooks pass: all checks green

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push and create PR
git push origin <branch>
gh pr create --title "fix(tests): Update test_default_values for <field>=<new_value>" \
  --body "Fixes failing test on main..."
gh pr merge --auto --rebase
```

## Failed Attempts

None in this session - the approach was straightforward:

1. Read test file to confirm mismatch
2. Edit one line
3. Verify with test run
4. Commit and PR

**Key Success Factor**: Identified exact root cause from plan mode research before implementing.

## Results & Parameters

### Test Fix

**File**: `tests/unit/automation/test_models.py:309`

**Change**:

```python
# Before
assert options.enable_retrospective is False

# After
assert options.enable_retrospective is True
```

### Verification Results

```bash
# Specific test
============================= test session starts ==============================
tests/unit/automation/test_models.py::TestImplementerOptions::test_default_values PASSED [100%]
============================== 1 passed in 0.10s =================

# Full unit suite
================= 2077 passed, 6 skipped, 7 warnings in 35.30s =================

# Pre-commit hooks
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Strip Notebook Outputs...............................(no files to check)Skipped
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

### PR Details

- **Branch**: `skill/optimization/centralize-repo-clones`
- **PR**: #620
- **Commit**: `639b070`
- **Auto-merge**: Enabled (--rebase)

## Key Learnings

1. **Always check git history** when default value tests fail - likely a recent commit changed the default
2. **One-line fixes are common** - don't overthink when assertion just needs to match new default
3. **Run specific test first** - faster feedback before full suite
4. **Include verification in commit message** - shows due diligence

## Related Skills

- `ci-cd/fix-failing-ci` - General CI failure resolution
- `debugging/git-bisect` - Finding when a default changed
- `testing/update-test-fixtures` - Broader test maintenance patterns
