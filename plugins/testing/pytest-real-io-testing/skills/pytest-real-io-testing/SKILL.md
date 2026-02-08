---
name: "Skill: Replace Pytest Mocks with Real File I/O"
description: "Pattern for replacing pytest mocks with real file I/O to fix test isolation issues"
category: testing
date: 2026-02-05
user-invocable: false
---
# Skill: Replace Pytest Mocks with Real File I/O

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-05 |
| **Objective** | Fix test isolation issues by removing mocks and using real file I/O in pytest |
| **Context** | PR #353 failing CI due to mock pollution between test_figures.py and test_integration.py |
| **Outcome** | ✅ All 332 tests passing, no mock leakage, simpler test code |
| **Related Issues** | #353 |

## When to Use This Skill

Use this pattern when you encounter:

1. **Test isolation failures** - Tests passing individually but failing when run together
2. **Mock pollution** - Mocks from one test file affecting another test file
3. **CI failures with "expected real files but got mocked behavior"** errors
4. **Complex mock setup** - Tests with extensive `patch()` blocks and mock fixtures
5. **Integration tests expecting real I/O** - When integration tests need actual file creation

**Trigger Phrases:**
- "Tests failing in CI but passing locally"
- "Mock pollution between test files"
- "Expected file to exist but got None"
- "save_figure mock leaking into integration tests"

## Problem Pattern

### Symptoms
- Tests pass individually: `pytest test_figures.py` ✅
- Tests pass individually: `pytest test_integration.py` ✅
- Tests fail together: `pytest test_figures.py test_integration.py` ❌
- Error: Integration tests expect real files but sometimes get mocked behavior

### Root Cause
- Mocks patching module-level functions (like `save_figure`) leak between test files
- `clear_patches` fixture in `conftest.py` doesn't fully isolate tests
- Integration tests import same modules that were mocked in unit tests

## Verified Workflow

### Step 1: Identify Mock Patterns

Count mock usage to understand scope:

```bash
# Count mock fixtures
grep -c "mock_save_figure" tests/unit/analysis/test_figures.py

# Count patch contexts
grep -c "with patch(" tests/unit/analysis/test_figures.py

# Find all mock imports
grep "from unittest.mock import" tests/unit/analysis/*.py
```

**Expected Output:**
- ~12 uses of mock fixtures
- ~51 uses of `with patch()` contexts
- Multiple test files with mock imports

### Step 2: Convert Basic Figure Tests

Replace mock-based tests with real file I/O:

**Before:**
```python
def test_fig01_score_variance_by_tier(sample_runs_df, mock_save_figure):
    """Test Fig 1 generates without errors."""
    from scylla.analysis.figures.variance import fig01_score_variance_by_tier

    fig01_score_variance_by_tier(sample_runs_df, Path("/tmp"), render=False)
    assert mock_save_figure.called
```

**After:**
```python
def test_fig01_score_variance_by_tier(sample_runs_df, tmp_path):
    """Test Fig 1 generates files correctly."""
    from scylla.analysis.figures.variance import fig01_score_variance_by_tier

    fig01_score_variance_by_tier(sample_runs_df, tmp_path, render=False)

    # Verify files created
    assert (tmp_path / "fig01_score_variance_by_tier.vl.json").exists()
    assert (tmp_path / "fig01_score_variance_by_tier.csv").exists()
```

**Pattern:**
1. Replace `mock_save_figure` parameter with `tmp_path`
2. Replace `Path("/tmp")` with `tmp_path` in function call
3. Replace `assert mock.called` with file existence checks
4. Verify both `.vl.json` and `.csv` files created

### Step 3: Convert Patch Context Tests

Replace `with patch()` blocks:

**Before:**
```python
def test_fig06_cop_by_tier(sample_runs_df):
    """Test Fig 6 generates without errors."""
    from scylla.analysis.figures.cost_analysis import fig06_cop_by_tier

    with patch("scylla.analysis.figures.cost_analysis.save_figure") as mock:
        fig06_cop_by_tier(sample_runs_df, Path("/tmp"), render=False)
        assert mock.called
```

**After:**
```python
def test_fig06_cop_by_tier(sample_runs_df, tmp_path):
    """Test Fig 6 generates files correctly."""
    from scylla.analysis.figures.cost_analysis import fig06_cop_by_tier

    fig06_cop_by_tier(sample_runs_df, tmp_path, render=False)
    assert (tmp_path / "fig06_cop_by_tier.vl.json").exists()
    assert (tmp_path / "fig06_cop_by_tier.csv").exists()
```

**Pattern:**
1. Add `tmp_path` parameter to test function
2. Remove entire `with patch()` block
3. Remove `mock.called` assertion
4. Add file existence checks

### Step 4: Convert Content Verification Tests

For tests that verify data structure, read actual CSV files:

**Before:**
```python
def test_fig04_pass_rate_content_verification(sample_runs_df):
    """Test Fig 4 generates correct pass-rate data with bootstrap CIs."""
    from scylla.analysis.figures.tier_performance import fig04_pass_rate_by_tier

    with patch("scylla.analysis.figures.tier_performance.save_figure") as mock:
        fig04_pass_rate_by_tier(sample_runs_df, Path("/tmp"), render=False)
        assert mock.called

        # Get the data passed to save_figure
        call_args = mock.call_args
        data_df = call_args[0][3] if len(call_args[0]) > 3 else None

        if data_df is not None:
            required_cols = ["agent_model", "tier", "pass_rate", "ci_low", "ci_high"]
            for col in required_cols:
                assert col in data_df.columns
```

**After:**
```python
def test_fig04_pass_rate_content_verification(sample_runs_df, tmp_path):
    """Test Fig 4 generates correct pass-rate data with bootstrap CIs."""
    import pandas as pd
    from scylla.analysis.figures.tier_performance import fig04_pass_rate_by_tier

    fig04_pass_rate_by_tier(sample_runs_df, tmp_path, render=False)

    # Read and verify data
    csv_path = tmp_path / "fig04_pass_rate_by_tier.csv"
    assert csv_path.exists()

    data_df = pd.read_csv(csv_path)
    required_cols = ["agent_model", "tier", "pass_rate", "ci_low", "ci_high"]
    for col in required_cols:
        assert col in data_df.columns, f"Missing column: {col}"

    # Verify pass_rate is in [0, 1]
    assert data_df["pass_rate"].min() >= 0.0
    assert data_df["pass_rate"].max() <= 1.0
```

**Pattern:**
1. Add `import pandas as pd` at top
2. Add `tmp_path` parameter
3. Remove `with patch()` block
4. Read CSV from `tmp_path / "filename.csv"`
5. Verify CSV file exists first
6. Use `pd.read_csv()` to load data
7. Perform same validation on actual data

### Step 5: Clean Up Mock Infrastructure

Remove mock fixtures and imports:

**conftest.py - Before:**
```python
"""Shared fixtures for analysis tests."""

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

@pytest.fixture(scope="function", autouse=True)
def clear_patches():
    """Clear all mock patches between tests to prevent pollution."""
    yield
    patch.stopall()

@pytest.fixture(scope="function")
def mock_save_figure():
    """Mock save_figure to avoid file I/O during tests."""
    with patch("scylla.analysis.figures.spec_builder.save_figure") as mock:
        yield mock
```

**conftest.py - After:**
```python
"""Shared fixtures for analysis tests."""

import numpy as np
import pandas as pd
import pytest

# mock_save_figure and clear_patches removed - using real I/O now
```

**test_figures.py - Before:**
```python
"""Unit tests for figure generation."""

from pathlib import Path
from unittest.mock import patch
import pytest
```

**test_figures.py - After:**
```python
"""Unit tests for figure generation."""

from pathlib import Path
import pytest

# No mock imports needed - using real I/O
```

### Step 6: Verify All Tests Pass

Run comprehensive test suite:

```bash
# Run figure tests
pixi run pytest tests/unit/analysis/test_figures.py -v

# Run integration tests
pixi run pytest tests/unit/analysis/test_integration.py -v

# Run all analysis tests together (the critical test)
pixi run pytest tests/unit/analysis/ -v

# Count results
pixi run pytest tests/unit/analysis/ -v --tb=short | grep "passed"
```

**Expected Output:**
```
======================== 71 passed, 1 warning in 5.09s =========================  # test_figures.py
======================== 7 passed in 1.08s ==========================  # test_integration.py
======================== 332 passed, 6 warnings in 9.25s ========================  # all tests
```

**Success Criteria:**
- ✅ All figure tests pass individually
- ✅ All integration tests pass individually
- ✅ All tests pass when run together (no isolation failures)
- ✅ No `unittest.mock` imports in test files
- ✅ All tests use `tmp_path` instead of mocks

## Failed Attempts

### ❌ Attempt 1: Keep `clear_patches` Fixture

**What We Tried:**
- Keep `clear_patches` autouse fixture in conftest.py
- Use `patch.stopall()` between tests to clear mocks

**Why It Failed:**
- `clear_patches` fixture wasn't called between test files
- Mocks from `test_figures.py` still leaked into `test_integration.py`
- Autouse fixtures don't isolate across different test modules

**Lesson Learned:**
Mock cleanup fixtures are insufficient for cross-file isolation. The only reliable solution is to remove mocks entirely.

### ❌ Attempt 2: Use Mock Verification for Content Tests

**What We Tried:**
- Access mock call args to verify data structure
- Pattern: `call_args = mock.call_args; data_df = call_args[0][3]`

**Why It Failed:**
- Brittle - depends on positional argument order
- Doesn't verify actual file output
- Still requires mocks (defeating the purpose)
- More complex than reading actual CSV files

**Lesson Learned:**
Reading real CSV files with `pd.read_csv()` is simpler and more robust than inspecting mock call arguments.

### ❌ Attempt 3: Partial Mock Removal

**What We Tried:**
- Remove mocks from basic tests only
- Keep mocks for "complex" content verification tests

**Why It Failed:**
- Partial mocks still cause pollution
- Creates inconsistent test patterns
- Doesn't solve the isolation problem

**Lesson Learned:**
All-or-nothing approach required. Either use mocks everywhere (with isolation issues) or use real I/O everywhere (clean isolation).

## Results & Validation

### Test Conversion Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Mock fixtures | 1 (`mock_save_figure`) | 0 | -100% |
| `with patch()` blocks | ~51 | 0 | -100% |
| `tmp_path` usage | 2 tests | 71 tests | +3450% |
| Tests using mocks | ~63 | 0 | -100% |
| Lines of code | 1,206 | 1,184 | -22 lines |
| Test passes | 332 | 332 | ✅ Same |

### File Changes

```
tests/unit/analysis/conftest.py     |    9 -
tests/unit/analysis/test_figures.py | 1079 +++++++++++++++++------------------
2 files changed, 536 insertions(+), 552 deletions(-)
```

### Performance Impact

| Test Suite | Before | After | Change |
|------------|--------|-------|--------|
| test_figures.py | 5.1s | 5.09s | -0.01s |
| test_integration.py | 1.1s | 1.08s | -0.02s |
| Full analysis suite | 9.3s | 9.25s | -0.05s |

**Conclusion:** No performance degradation from using real I/O vs mocks.

### CI Impact

**Before:**
- ❌ Tests failing in CI (mock pollution)
- ❌ Inconsistent results between local and CI
- ❌ Manual debugging required

**After:**
- ✅ All tests passing in CI
- ✅ Consistent local and CI behavior
- ✅ No manual intervention needed

## Key Takeaways

1. **tmp_path is superior to mocks for I/O testing**
   - Built-in pytest fixture
   - Automatic cleanup
   - Real integration testing
   - No pollution between tests

2. **Mock pollution is hard to debug**
   - Can manifest differently locally vs CI
   - Autouse fixtures don't solve cross-module pollution
   - Complete removal is easier than partial fixes

3. **Content verification is cleaner with real files**
   - `pd.read_csv(csv_path)` simpler than `mock.call_args[0][3]`
   - Verifies actual output, not just function calls
   - More maintainable test code

4. **Conversion is mechanical and safe**
   - Find/replace patterns work well
   - Tests fail quickly if conversion is incorrect
   - Can convert in batches and verify incrementally

## Quick Reference Card

### Conversion Patterns

| Pattern | Before | After |
|---------|--------|-------|
| **Fixture** | `mock_save_figure` | `tmp_path` |
| **Path** | `Path("/tmp")` | `tmp_path` |
| **Assertion** | `assert mock.called` | `assert (tmp_path / "file.vl.json").exists()` |
| **CSV Read** | `mock.call_args[0][3]` | `pd.read_csv(tmp_path / "file.csv")` |
| **Import** | `from unittest.mock import patch` | (remove) |

### Shell Commands

```bash
# Count mocks (before)
grep -c "mock_save_figure" tests/unit/analysis/test_figures.py  # Should be 0 after

# Verify no mock imports
grep "from unittest.mock import" tests/unit/analysis/*.py  # Should be empty

# Run all tests together (critical validation)
pixi run pytest tests/unit/analysis/ -v  # All should pass

# Check for file existence patterns
grep -c "tmp_path" tests/unit/analysis/test_figures.py  # Should be ~71
```

### Success Checklist

- [ ] No `unittest.mock` imports in test files
- [ ] No `mock_save_figure` fixture in conftest.py
- [ ] No `clear_patches` fixture in conftest.py
- [ ] All tests use `tmp_path` instead of mocks
- [ ] All tests verify file existence with `.exists()`
- [ ] Content tests read CSV files with `pd.read_csv()`
- [ ] All figure tests pass individually
- [ ] All integration tests pass individually
- [ ] **All tests pass when run together** (most critical)
- [ ] CI passes on PR

## Related Skills

- `pytest-fixtures` - Understanding pytest fixture patterns
- `test-isolation-debugging` - Debugging cross-test pollution issues
- `ci-failure-analysis` - Analyzing CI failures vs local successes

## References

- PR #353: https://github.com/HomericIntelligence/ProjectScylla/pull/353
- Pytest tmp_path docs: https://docs.pytest.org/en/stable/how-to/tmp_path.html
- Test isolation best practices: TESTING.md
