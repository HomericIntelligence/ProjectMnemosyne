# Skill: Rubric Conflict Detection in Multi-Experiment Loaders

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Project** | ProjectScylla |
| **Issue** | #995 |
| **PR** | HomericIntelligence/ProjectScylla#1126 |
| **Objective** | Add rubric conflict detection to `load_rubric_weights()` / `load_all_experiments()` to prevent silent data corruption when experiments define incompatible rubric category weights |
| **Outcome** | Success — 11 new tests, all 3196 tests pass, 78.42% coverage, pre-commit clean |

---

## When to Use

Apply this pattern when:

- A data loader scans **multiple experiments / directories** and aggregates shared configuration (rubric weights, scoring criteria, thresholds)
- The same key can appear in multiple sources with **potentially different values**
- Silent last-write semantics would **corrupt downstream cross-experiment comparisons**
- You need **user-configurable conflict resolution** (strict by default, relaxed optional)

Trigger phrases:
- "loader silently takes whichever it loads last"
- "cross-experiment comparison may be corrupted"
- "rubric weights conflict"
- "same subtest in two experiments with differing weights"

---

## Verified Workflow

### 1. Define a conflict resolution policy type

```python
from typing import Literal

# 'error'  – raise descriptive error (default; safest for research pipelines)
# 'warn'   – emit UserWarning and keep the *first* value
# 'first'  – silently keep the first value encountered
# 'last'   – silently overwrite with the last value encountered
RubricConflict = Literal["error", "warn", "first", "last"]
```

### 2. Define a descriptive exception class

```python
class RubricConflictError(ValueError):
    """Raised when two experiments define conflicting rubric weights.

    Attributes:
        category: Category name where the conflict was detected.
        exp_first: Experiment name that first defined this category.
        weight_first: Weight from the first experiment.
        exp_second: Experiment name that introduced the conflict.
        weight_second: Conflicting weight from the second experiment.
    """

    def __init__(
        self,
        category: str,
        exp_first: str,
        weight_first: float,
        exp_second: str,
        weight_second: float,
    ) -> None:
        """Initialize RubricConflictError with conflict details."""
        self.category = category
        self.exp_first = exp_first
        self.weight_first = weight_first
        self.exp_second = exp_second
        self.weight_second = weight_second
        super().__init__(
            f"Rubric conflict for category '{category}': "
            f"experiment '{exp_first}' defines weight={weight_first}, "
            f"but experiment '{exp_second}' defines weight={weight_second}. "
            "Use the rubric_conflict parameter to control resolution."
        )
```

**Key design decisions:**
- Subclass `ValueError` so callers can catch it specifically _or_ as a generic `ValueError`
- Store conflict details as attributes for programmatic inspection
- Error message must contain category name, both experiment names, and both values — operators need this to diagnose data issues without reading logs

### 3. Refactor the loader to accumulate and check

Replace "return on first found" logic with full scan + accumulation:

```python
def load_rubric_weights(
    data_dir: Path,
    exclude: list[str] | None = None,
    rubric_conflict: RubricConflict = "error",
) -> dict[str, float] | None:
    exclude = exclude or []
    # maps category → (weight, source_experiment_name)
    accumulated: dict[str, tuple[float, str]] = {}
    found_any = False

    for exp_dir in sorted(data_dir.iterdir()):
        if not exp_dir.is_dir() or exp_dir.name in exclude:
            continue
        exp_name = exp_dir.name

        # Use latest timestamp dir
        ts_dirs = sorted(d for d in exp_dir.iterdir() if d.is_dir())
        if not ts_dirs:
            continue
        ts_dir = ts_dirs[-1]

        rubric_path = ts_dir / "rubric.yaml"
        if not rubric_path.exists():
            continue

        with rubric_path.open() as f:
            data = yaml.safe_load(f)

        categories = data.get("categories", {}) if data else {}
        found_any = True

        for cat_name, cat_data in categories.items():
            new_weight: float = cat_data.get("weight", 0.0) if cat_data else 0.0

            if cat_name not in accumulated:
                accumulated[cat_name] = (new_weight, exp_name)
                continue

            existing_weight, existing_exp = accumulated[cat_name]
            if abs(existing_weight - new_weight) <= 1e-6:
                continue  # Identical within tolerance – no conflict

            # Genuine conflict – apply policy
            if rubric_conflict == "error":
                raise RubricConflictError(
                    category=cat_name,
                    exp_first=existing_exp,
                    weight_first=existing_weight,
                    exp_second=exp_name,
                    weight_second=new_weight,
                )
            elif rubric_conflict == "warn":
                warnings.warn(
                    f"Rubric conflict for category '{cat_name}': "
                    f"experiment '{existing_exp}' defines weight={existing_weight}, "
                    f"but experiment '{exp_name}' defines weight={new_weight}. "
                    "Keeping first value.",
                    UserWarning,
                    stacklevel=2,
                )
            elif rubric_conflict == "first":
                pass  # Keep first – no update
            elif rubric_conflict == "last":
                accumulated[cat_name] = (new_weight, exp_name)

    if not found_any:
        return None

    return {cat: weight for cat, (weight, _) in accumulated.items()}
```

### 4. Add the parameter to the public API surface

```python
def load_all_experiments(
    data_dir: Path,
    exclude: list[str] | None = None,
    rubric_conflict: RubricConflict = "error",
) -> dict[str, list[RunData]]:
    ...
```

Even if `load_all_experiments` does not call `load_rubric_weights` internally, expose the parameter so callers have a consistent API surface and can pass the same policy to both functions.

### 5. Write tests (TDD order: tests first)

Cover all four policies, tolerance edge case, error message content, new-category merging, identical weights (no false positives), and signature inspection:

```python
def test_rubric_conflict_raises_by_default(tmp_path):
    """Two experiments with same category, different weights → RubricConflictError."""
    from scylla.analysis.loader import RubricConflictError, load_rubric_weights
    data_dir = _make_two_experiment_dir(
        tmp_path,
        cats1={"functional": {"weight": 10.0}},
        cats2={"functional": {"weight": 5.0}},
    )
    with pytest.raises(RubricConflictError):
        load_rubric_weights(data_dir)

def test_rubric_conflict_error_message_contains_details(tmp_path):
    """Error message includes category name, both experiment names, both weights."""
    ...
    with pytest.raises(RubricConflictError) as exc_info:
        load_rubric_weights(data_dir)
    msg = str(exc_info.value)
    assert "functional" in msg
    assert "experiment1" in msg
    assert "experiment2" in msg
    assert "10.0" in msg or "10" in msg
    assert "5.0" in msg or "5" in msg

def test_rubric_conflict_float_tolerance(tmp_path):
    """Weights differing by ≤ 1e-6 are not treated as a conflict."""
    data_dir = _make_two_experiment_dir(
        tmp_path,
        cats1={"functional": {"weight": 10.0}},
        cats2={"functional": {"weight": 10.0 + 1e-10}},
    )
    weights = load_rubric_weights(data_dir)  # Should not raise
    assert weights["functional"] == pytest.approx(10.0)
```

---

## Failed Attempts

### 1. Placing conflict detection in `load_all_experiments()` instead of `load_rubric_weights()`

**What was considered:** Detect conflicts in `load_all_experiments()` by comparing rubric dicts loaded per-experiment.

**Why it was rejected:** `load_rubric_weights()` already iterates all rubric.yaml files and is the right abstraction layer. Putting the detection in `load_all_experiments()` would duplicate the rubric-reading logic. The loader layer detects; callers decide whether to use rubric weights for analysis.

### 2. Using `!=` for float comparison

**Problem:** JSON serialisation round-trips can introduce tiny floating-point differences (e.g., `10.0` stored as `10.000000000000001`). Using `!=` would produce spurious conflicts on identical logical values.

**Fix:** Use `abs(w1 - w2) <= 1e-6` as the "same value" threshold.

### 3. Pre-push hook flaky test blocking push

**Problem:** The `test_run_single_with_mocks` test failed intermittently when the pre-push hook ran the 3183-test full suite under system load. The test passes in isolation and in smaller subsets.

**Root cause:** The worktree was branched from an older `origin/main` that lacked the `fix(tests): replace timing assertion with sleep mock in test_retry.py` fix. The flaky retry timing test (`test_uses_longer_initial_delay`) caused the hook to abort early, which stopped test collection at position 1688 and caused `test_run_single_with_mocks` to register as a failure.

**Fix:** `git fetch origin main && git rebase origin/main` to pick up the timing fix before pushing.

---

## Results & Parameters

### Test coverage added

| File | Tests Added |
|------|------------|
| `tests/unit/analysis/test_rubric_conflict.py` | 11 new tests |
| `tests/unit/analysis/test_loader.py` | 1 updated signature test |

### Final metrics

| Metric | Value |
|--------|-------|
| Tests passed | 3196 / 3196 |
| Coverage | 78.42% (threshold: 75%) |
| Pre-commit hooks | All passed |

### Key configuration

```python
# Float tolerance for weight comparison
WEIGHT_TOLERANCE = 1e-6

# Default policy (safest for research pipelines)
DEFAULT_POLICY: RubricConflict = "error"
```

### Commit message

```
feat(analysis): add rubric conflict detection to load_rubric_weights()

- Add RubricConflictError (ValueError subclass) with descriptive message
  including category name, both experiment names, and both weight values
- Add RubricConflict literal type: 'error'|'warn'|'first'|'last'
- Refactor load_rubric_weights() to scan all experiments (not just first),
  accumulate weights, and apply conflict policy when same category appears
  with differing weights (float tolerance 1e-6 avoids spurious conflicts)
- Add rubric_conflict parameter to load_all_experiments() (default 'error')
- Add tests/unit/analysis/test_rubric_conflict.py with 11 targeted tests
- Update test_load_all_experiments_signature to assert new parameter

Closes #995
```
