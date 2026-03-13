# Skill: wired-runner-fixture

## Overview

| Field     | Value                                                      |
|-----------|------------------------------------------------------------|
| Date      | 2026-02-20                                                 |
| Issue     | #771                                                       |
| PR        | #815                                                       |
| Objective | Extract shared `wired_runner` pytest fixture for `E2ERunner` tests |
| Outcome   | Success — 4 tests refactored, zero per-test boilerplate    |
| Category  | testing                                                    |

## When to Use

Trigger this skill when:

- Multiple test methods in a class each construct the same object with `SomeClass(mock_a, mock_b, ...)` before calling the method under test
- The real constructor takes a `Path` argument and creates a heavy dependency (e.g. `TierManager`) internally, requiring mocking to avoid filesystem access
- You want to add `experiment_dir` or other post-construction attributes that the constructor leaves as `None`
- A follow-up issue references "extract fixture" or "eliminate boilerplate" across a test class

## Verified Workflow

### 1. Identify the boilerplate pattern

```python
# BEFORE: each test method constructs the object directly
def test_foo(self, mock_config, mock_tier_manager):
    runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
    result = runner.some_method(...)
```

Check the real constructor signature — the second arg may be a `Path`, not a mock:

```python
# Real constructor (scylla/e2e/runner.py)
def __init__(self, config: ExperimentConfig, tiers_dir: Path, results_base_dir: Path, ...):
    self.tier_manager = TierManager(tiers_dir)  # filesystem access!
    self.experiment_dir: Path | None = None
```

### 2. Add imports

```python
from unittest.mock import MagicMock, patch
from scylla.e2e.tier_manager import TierManager
```

### 3. Write the fixture

Place it **after** the lower-level fixtures it depends on (`mock_config`, `mock_tier_manager`) and **before** the test class:

```python
@pytest.fixture
def wired_runner(
    mock_config: ExperimentConfig,
    mock_tier_manager: MagicMock,
    tmp_path: Path,
) -> E2ERunner:
    """Pre-configured E2ERunner with experiment_dir and tier_manager already set."""
    with patch.object(TierManager, "__init__", return_value=None):
        runner = E2ERunner(mock_config, tmp_path / "tiers", tmp_path / "results")
    runner.tier_manager = mock_tier_manager
    runner.experiment_dir = tmp_path / "experiment"
    runner.experiment_dir.mkdir(parents=True)
    return runner
```

**Key decisions:**

- `patch.object(TierManager, "__init__", return_value=None)` — bypass real filesystem init, inject mock afterward
- `tmp_path` (pytest built-in) — real directory, auto-cleaned, no `Path("/tmp")` collisions
- Post-construction attribute injection — matches how tests actually use the object
- Function scope (default) — `E2ERunner` mutates state, so per-test isolation is required

### 4. Refactor all test methods in the class

```python
# AFTER: fixture parameter replaces both mock parameters and construction
def test_foo(self, wired_runner: E2ERunner) -> None:
    result = wired_runner.some_method(...)
```

Remove the `E2ERunner(...)` construction line from every method. Adopt **all-or-nothing** within the class — partial adoption creates inconsistency.

### 5. Verify

```bash
# All tests in file pass
pixi run python -m pytest tests/unit/e2e/test_runner.py -v

# Only one E2ERunner(...) call remains — inside the fixture
grep -n "E2ERunner(" tests/unit/e2e/test_runner.py

# Pre-commit clean
pre-commit run --files tests/unit/e2e/test_runner.py
```

## Failed Attempts

**None in this session.** The approach was derived from prior skill knowledge (`pytest-real-io-testing`, `shared-fixture-migration`) and worked on the first implementation.

However, be aware of these potential pitfalls:

- **Passing `MagicMock` as a `Path` arg** — the tests used to pass `mock_tier_manager` as `tiers_dir`, which worked at runtime (no type enforcement) but was semantically wrong. The fixture corrects this by passing a real `tmp_path / "tiers"` path.
- **Forgetting `patch` import** — `patch.object` requires `from unittest.mock import patch` in addition to `MagicMock`.
- **Forgetting `TierManager` import** — `patch.object` needs the class itself: `from scylla.e2e.tier_manager import TierManager`.
- **Promoting to `conftest.py` prematurely** — keep the fixture local to the test file unless multiple test files need it (YAGNI).

## Results & Parameters

```
File modified: tests/unit/e2e/test_runner.py
Tests refactored: 4 (TestTokenStatsAggregation class)
Net line change: +25 insertions, -24 deletions (fixture adds ~16 lines, removes boilerplate)
Pre-commit: all hooks passed (ruff, black, mypy)
Test result: 4/4 passed
```

### Final fixture (copy-paste ready)

```python
@pytest.fixture
def wired_runner(
    mock_config: ExperimentConfig,
    mock_tier_manager: MagicMock,
    tmp_path: Path,
) -> E2ERunner:
    """Pre-configured E2ERunner with experiment_dir and tier_manager already set."""
    with patch.object(TierManager, "__init__", return_value=None):
        runner = E2ERunner(mock_config, tmp_path / "tiers", tmp_path / "results")
    runner.tier_manager = mock_tier_manager
    runner.experiment_dir = tmp_path / "experiment"
    runner.experiment_dir.mkdir(parents=True)
    return runner
```
