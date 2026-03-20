---
name: mock-expensive-simulations
description: Diagnose and fix pytest tests hanging due to expensive Monte Carlo or
  bootstrap simulation calls, with correct patch target (caller vs origin namespace)
  identification
category: debugging
date: 2026-02-23
version: 1.0.0
user-invocable: false
---
# Skill: Mock Expensive Simulations

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-23 |
| **Objective** | Diagnose why `test_cop_integration.py`, `test_duration_integration.py`, and `test_export_data.py` hung after ~7% of the test suite, then fix the hang without altering the test logic |
| **Outcome** | ✅ Success — 11 tests now pass in 14.8s (was hanging indefinitely); autouse mock in conftest.py prevents all future hangs |
| **Category** | Debugging |
| **Tags** | pytest, monte-carlo, mock, conftest, autouse, simulation, performance, hanging-tests |

## When to Use This Skill

Use this skill when:

- **Tests hang** partway through a run (e.g., at a fixed percentage like 7%) without a clear error
- Tests call functions that perform **Monte Carlo / bootstrap simulations** with high `n_iterations`
- A **push hook** runs the full test suite and blocks indefinitely before CI even starts
- Tests only assert **structural correctness** (keys, types, list lengths) — not exact numerical values

**Trigger phrases:**
- "Tests hang after X% of the suite runs"
- "pytest runs fine locally with a subset but times out in CI"
- "Push hook is blocking — tests don't finish"
- "Some tests started hanging after a new statistics/analysis feature was added"

## Verified Workflow

### Phase 1: Establish Whether the Hang Is on the Branch or Pre-existing on Main

Before bisecting, verify whether main itself hangs:

```bash
# Run the hanging files directly on origin/main
git stash
timeout 60 pixi run python -m pytest tests/unit/analysis/test_cop_integration.py --no-cov -q
git stash pop
```

If main also hangs — the issue is pre-existing, not introduced by the branch. Skip bisect.

If only the branch hangs — use bisect (see Phase 2).

### Phase 2: Git Bisect to Find Introducing Commit (if branch-specific)

```bash
git bisect start
git bisect bad HEAD          # current tip hangs
git bisect good <main-sha>   # main is good

# For each commit git shows, run with a timeout:
timeout 60 pixi run python -m pytest \
  tests/unit/analysis/test_cop_integration.py \
  tests/unit/analysis/test_duration_integration.py \
  --no-cov -q 2>&1 | tail -3

# exit 0 within timeout -> good; exit 124 (timeout killed) -> bad
git bisect good   # or
git bisect bad

git bisect reset  # when done
```

**Important:** If `timeout 60` kills the process, that IS a "bad" commit — don't wait longer.

### Phase 3: Identify the Expensive Call

Once the introducing commit is found (or on main, grep for the pattern):

```bash
# Find Monte Carlo / simulation calls
grep -rn "n_simulations\|n_resamples\|bootstrap\|monte_carlo\|for.*range.*n_sim" \
  scripts/ scylla/ --include="*.py" | grep -v "test_\|#"

# Find the function definition with its default parameter
grep -n "def.*power\|def.*bootstrap\|def.*simulate" scylla/analysis/stats.py
```

**Signature to look for:**
```python
def expensive_fn(..., n_simulations: int | None = None) -> float:
    if n_simulations is None:
        n_simulations = config.power_n_simulations  # often 10_000
```

**Call site in production code:**
```python
# export_data.py — called without n_simulations override
result = mann_whitney_power(n1, n2, effect_size)      # uses default 10,000
result = kruskal_wallis_power(group_sizes, effect_size)
```

### Phase 4: Verify the Function Is Imported via `from ... import`

This matters for the patch target:

```bash
grep "^from.*import\|^import" scripts/export_data.py | grep -i "power\|stat"
```

- `from scylla.analysis.stats import mann_whitney_power` → patch `"export_data.mann_whitney_power"`
- `import scylla.analysis.stats` then `stats.mann_whitney_power()` → patch `"scylla.analysis.stats.mann_whitney_power"`

When using `from X import Y`, you must patch the **caller's namespace**, not the origin.

### Phase 5: Add autouse Mock in conftest.py

Add to `tests/unit/analysis/conftest.py` (or whichever conftest covers the hanging tests):

```python
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def mock_power_simulations():
    """Mock expensive Monte Carlo simulations to prevent test hangs.

    mann_whitney_power() and kruskal_wallis_power() each run 10,000 simulations
    by default (~5s each). With 2 models × 6 transitions × 2 calls = 24 calls per
    compute_statistical_results() invocation, this causes tests to hang for 2+ minutes.

    Tests only assert output structure — the exact power values are irrelevant.
    """
    # Patch in caller's namespace (from-import) AND in origin module (for direct callers)
    with (
        patch("export_data.mann_whitney_power", return_value=0.8, create=True),
        patch("export_data.kruskal_wallis_power", return_value=0.75, create=True),
        patch("scylla.analysis.stats.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.stats.kruskal_wallis_power", return_value=0.75),
    ):
        yield
```

**Key design decisions:**
- `autouse=True` — applies to every test in the directory without requiring explicit use
- `create=True` — needed when patching `export_data.*` because the module is in `scripts/` and loaded via `sys.path.insert`, so the attribute may not exist in the Python module registry at conftest load time
- Patch both namespaces for safety (caller + origin)
- Return values (`0.8`, `0.75`) are realistic power estimates — tests checking structure don't care

### Phase 6: Verify the Fix

```bash
# Must complete in << 60 seconds
timeout 60 pixi run python -m pytest \
  tests/unit/analysis/test_cop_integration.py \
  tests/unit/analysis/test_duration_integration.py \
  tests/unit/analysis/test_export_data.py \
  --no-cov -q

# Expected: 11 passed in ~15s
```

Then run pre-commit:
```bash
pixi run pre-commit run --files tests/unit/analysis/conftest.py
```

Ruff will reformat the `with` block to use parenthesized form — accept this and re-run to confirm clean pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Before vs After

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| `test_cop_integration.py` | Hang (>120s) | 1 passed, ~14s total |
| `test_duration_integration.py` | Hang (>120s) | 1 passed, ~14s total |
| `test_export_data.py` | Hang (>120s) | 9 passed, ~14s total |
| Push hook | Blocks indefinitely | Completes, suite passes |

### Simulation Budget (Root Cause)

| Function | Default n_simulations | Calls per invocation | Total simulations |
|----------|----------------------|---------------------|-------------------|
| `mann_whitney_power` | 10,000 | 24 (2 models × 6 transitions × 2) | 240,000 |
| `kruskal_wallis_power` | 10,000 | 2 (1 per model) | 20,000 |
| **Total** | | | **260,000 iterations** |

At ~5s per 10,000 simulations: **~130 seconds per `compute_statistical_results()` call**.

### The Fix (copy-paste)

```python
# Add to tests/unit/analysis/conftest.py
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def mock_power_simulations():
    """Mock expensive Monte Carlo simulations to prevent test hangs."""
    with (
        patch("export_data.mann_whitney_power", return_value=0.8, create=True),
        patch("export_data.kruskal_wallis_power", return_value=0.75, create=True),
        patch("scylla.analysis.stats.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.stats.kruskal_wallis_power", return_value=0.75),
    ):
        yield
```

### General Pattern for Any Expensive Simulation Function

```python
@pytest.fixture(autouse=True)
def mock_slow_computations():
    """Mock any function with O(N*simulations) runtime in tests."""
    patches = {
        "your_module.expensive_fn": 0.5,       # caller namespace
        "scylla.analysis.stats.expensive_fn": 0.5,  # origin namespace
    }
    with contextlib.ExitStack() as stack:
        for target, return_val in patches.items():
            stack.enter_context(patch(target, return_value=return_val, create=True))
        yield
```
