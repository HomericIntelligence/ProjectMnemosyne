---
name: doc-config-drift-test-count-check
description: "Extend doc/config consistency scripts to validate README.md test count claims against actual pytest --collect-only output, with graceful skip and 10% tolerance"
category: ci-cd
date: 2026-03-02
user-invocable: false
---

# Doc/Config Drift: README Test Count Check

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Category** | ci-cd |
| **Objective** | Add a drift check that validates test count claims in README.md against `pytest --collect-only -q` output |
| **Outcome** | ✅ 20 new tests added (6 unit + 8 unit + 2 integration + updated 5 integration), all pass |
| **Issue** | #1226 |
| **PR** | #1315 |

## When to Use

Use this skill when you need to:

- Add a new check to an existing `check_doc_config_consistency.py`-style script
- Validate that README.md test count badges/mentions stay in sync with the real test count
- Implement a "collect-and-compare" pattern using `subprocess.run(pytest --collect-only)`
- Add graceful skip logic for checks that depend on slow/external commands
- Mock `subprocess.run` in tests without spawning real processes

**Triggers**:

- "README says N tests but CI collects a different count"
- "Add test count drift detection to consistency script"
- "README badge is stale after adding tests"
- "Validate documented test count against actual pytest output"

## Verified Workflow

### Step 1: Add `collect_actual_test_count()` to the script

```python
import subprocess
import sys

def collect_actual_test_count(repo_root: Path) -> int | None:
    """Run pytest --collect-only -q and return the number of collected tests."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None

    output = result.stdout + result.stderr
    # Match "N selected" or "N tests collected" or "N test collected"
    m = re.search(r"(\d+)\s+(?:tests?\s+)?(?:selected|collected)", output)
    if m:
        return int(m.group(1))
    return None
```

**Key design decisions**:
- Returns `int | None` — `None` means skip (no hard failure for pytest being unavailable)
- Catches `FileNotFoundError` and `OSError` to handle any subprocess spawn failure
- Merges `stdout + stderr` before parsing (pytest may write summary to either stream)
- Uses `sys.executable` so it always invokes the same Python interpreter

### Step 2: Add `check_readme_test_count()` to the script

```python
def check_readme_test_count(
    repo_root: Path, actual_count: int, tolerance: float = 0.10
) -> list[str]:
    """Check that test count claims in README.md are within tolerance of actual_count."""
    readme = repo_root / "README.md"
    if not readme.exists():
        return [f"README.md not found at {readme}"]

    text = readme.read_text(encoding="utf-8")
    raw_matches = re.findall(r"(\d[\d,]*)\+?\s+tests?", text, re.IGNORECASE)

    if not raw_matches:
        return ["README.md: No test count mention found (expected pattern: '<N> tests')"]

    errors: list[str] = []
    for raw in raw_matches:
        doc_count = int(raw.replace(",", ""))
        if abs(doc_count - actual_count) / actual_count > tolerance:
            errors.append(
                f"README.md: Test count mismatch — "
                f"README.md says {doc_count}, actual pytest count is {actual_count} "
                f"(tolerance: {int(tolerance * 100)}%)"
            )
    return errors
```

**Key design decisions**:
- Pattern `(\d[\d,]*)\+?\s+tests?` matches: `3172 tests`, `3,500+ tests`, `1 test`
- Strips commas before `int()` conversion so `3,500` → `3500`
- 10% tolerance avoids false positives when tests are added between doc updates
- Returns error list (not raises) to be consistent with other checks in the script

### Step 3: Add Check 4 to `main()`

```python
# --- Check 4: README.md test count ---
actual_count = collect_actual_test_count(repo_root)
if actual_count is None:
    if args.verbose:
        print("SKIP: Could not collect actual test count (pytest unavailable)")
else:
    count_errors = check_readme_test_count(repo_root, actual_count)
    if count_errors:
        all_errors.extend(count_errors)
    elif args.verbose:
        print(f"PASS: README.md test count is within 10% of actual ({actual_count})")
```

**Key design decision**: `None` from collector → silent skip (not an error). Only fail when
pytest is reachable and the documented count is out of range.

### Step 4: Write unit tests with mocked subprocess

```python
from unittest.mock import MagicMock, patch

class TestCollectActualTestCount:
    def test_parses_n_tests_collected_line(self, tmp_path):
        mock_result = MagicMock()
        mock_result.stdout = "100 tests collected\n"
        mock_result.stderr = ""
        with patch(
            "scripts.check_doc_config_consistency.subprocess.run",
            return_value=mock_result,
        ):
            assert collect_actual_test_count(tmp_path) == 100

    def test_returns_none_on_subprocess_failure(self, tmp_path):
        with patch(
            "scripts.check_doc_config_consistency.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert collect_actual_test_count(tmp_path) is None
```

**Key design decision**: Patch `subprocess.run` in the script's own module namespace
(`scripts.check_doc_config_consistency.subprocess.run`), not `subprocess.run` globally.

### Step 5: Update integration tests to mock `collect_actual_test_count`

Existing `TestMainIntegration` tests call `main()` which now runs Check 4. Mock
`collect_actual_test_count` so they don't spawn real pytest:

```python
with patch(
    "scripts.check_doc_config_consistency.collect_actual_test_count",
    return_value=3507,
):
    result = main()
    assert result == 0
```

Also update `_make_repo()` to accept `readme_test_count: int | None = 3500` so the
generated README can contain a test count mention.

### Step 6: Run pre-commit and tests

```bash
# Run tests
pixi run python -m pytest tests/unit/scripts/test_check_doc_config_consistency.py -v --override-ini="addopts="

# Run pre-commit (ruff will auto-format on first run, pass on second)
pre-commit run --files scripts/check_doc_config_consistency.py tests/unit/scripts/test_check_doc_config_consistency.py
pre-commit run --files scripts/check_doc_config_consistency.py tests/unit/scripts/test_check_doc_config_consistency.py
```

## Failed Attempts

### ❌ First parse regex was too narrow

**What was tried**: Initial regex `r"(\d+)\+?\s+tests?"` failed to match `3,500+ tests` (comma in number).

**Fix**: Changed to `r"(\d[\d,]*)\+?\s+tests?"` and strip commas before `int()`:

```python
doc_count = int(raw.replace(",", ""))
```

### ❌ Missing `import subprocess` in script

**What was tried**: Added new functions without adding `import subprocess` at the top.

**Fix**: Always add `import subprocess` to the standard library imports block.

### ❌ Integration tests failed because main() now runs Check 4

**What happened**: Existing `TestMainIntegration` tests called `main()` which triggered
`collect_actual_test_count()` → spawned real pytest inside `tmp_path` (no tests there)
→ returned `None` → Check 4 skipped → BUT `_make_repo()` README had no test count
mention, so the error message about "No test count mention" was emitted → exit 1.

**Fix**: Updated `_make_repo()` to include a test count line by default
(`readme_test_count=3500`), and wrap each integration test with:

```python
with patch(
    "scripts.check_doc_config_consistency.collect_actual_test_count",
    return_value=3507,
):
```

## Results & Parameters

### Files Modified

1. **`scripts/check_doc_config_consistency.py`**:
   - Added `import subprocess`
   - Updated module docstring (Check 4 listed)
   - Added `collect_actual_test_count(repo_root)` (lines ~248-274)
   - Added `check_readme_test_count(repo_root, actual_count, tolerance=0.10)` (lines ~277-313)
   - Updated `main()` with Check 4 block (lines ~302-312)

2. **`tests/unit/scripts/test_check_doc_config_consistency.py`**:
   - Added `from unittest.mock import MagicMock, patch`
   - Added imports for `check_readme_test_count`, `collect_actual_test_count`
   - Added `TestCollectActualTestCount` (6 tests)
   - Added `TestCheckReadmeTestCount` (8 tests)
   - Updated `_make_repo()` with `readme_test_count: int | None = 3500` parameter
   - Updated 5 existing integration tests to mock `collect_actual_test_count`
   - Added 2 new integration tests (graceful skip, mismatch exit 1)

### Test Count Delta

| Category | Before | After |
|----------|--------|-------|
| Script tests | 33 | 53 |
| Net new tests | — | +20 |

### Tolerance Rationale

10% tolerance (`tolerance=0.10`) balances:
- **Too strict (0%)**: Every test addition breaks CI immediately
- **Too loose (50%)**: Allows numbers to drift significantly before catching
- **10%**: ~350 test gap on a 3500-test suite — roughly a sprint's worth of new tests

### Regex Pattern Breakdown

```python
r"(\d[\d,]*)\+?\s+tests?"
```

| Component | Matches |
|-----------|---------|
| `(\d[\d,]*)` | `3172`, `3,500`, `1` (commas allowed after first digit) |
| `\+?` | Optional `+` suffix (e.g. `3,500+`) |
| `\s+` | One or more spaces |
| `tests?` | `tests` or `test` (singular/plural) |

## Related Skills

- `pytest-coverage-threshold-config` — Configuring pytest coverage thresholds
- `ci-coverage-threshold-single-source` — Single source of truth for coverage thresholds
- `parallel-issue-wave-execution` — Running multiple issues in parallel worktrees

## Tags

`pytest`, `documentation`, `drift-detection`, `ci-cd`, `readme`, `test-count`, `consistency-check`, `subprocess`, `pre-commit`
