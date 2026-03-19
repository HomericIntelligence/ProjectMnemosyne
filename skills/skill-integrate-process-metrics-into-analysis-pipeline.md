---
name: 'Skill: Integrate Process Metrics into Analysis Pipeline'
description: "Workflow for wiring pre-implemented process metrics (R_Prog, CFP, PR\
  \ Revert Rate, Strategic Drift) into the ProjectScylla loader \u2192 dataframes\
  \ \u2192 figures stack"
category: evaluation
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Skill: Integrate Process Metrics into Analysis Pipeline

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Objective** | Integrate R_Prog, CFP, PR Revert Rate, Strategic Drift from `scylla/metrics/process.py` into the analysis pipeline |
| **Outcome** | ✅ Success — 3199 tests passing, 78.44% coverage, PR #1127 merged |
| **Issue** | #997 (follow-up from #880) |
| **Files Modified** | 3 modified, 2 created |

## When to Use This Skill

**Trigger conditions:**
- A metric is implemented in `scylla/metrics/` but not exposed in analysis output
- Issue says "metrics are implemented but not integrated into analysis pipeline"
- Need to add optional/nullable metric columns to `runs_df`
- Adding figures for process/stability metrics to the report

**Prerequisites:**
- Metric functions exist in `scylla/metrics/process.py` (or similar)
- Understanding of pipeline: `run_result.json` → `loader.py` → `dataframes.py` → `figures/`
- JSON schema at `scylla/analysis/schemas/run_result.schema.json`

## Verified Workflow

### Phase 1: Extend JSON Schema

**File: `scylla/analysis/schemas/run_result.schema.json`**

Add property definitions for pre-computed block **and** raw tracking arrays:

```json
"process_metrics": {
  "type": "object",
  "description": "Pre-computed process metrics for this run",
  "properties": {
    "r_prog": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "strategic_drift": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "cfp": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "pr_revert_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  },
  "additionalProperties": false
},
"progress_tracking": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "step_id": {"type": "string"},
      "description": {"type": "string"},
      "weight": {"type": "number", "minimum": 0},
      "completed": {"type": "boolean"},
      "goal_alignment": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["step_id", "description"],
    "additionalProperties": false
  }
},
"changes": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "change_id": {"type": "string"},
      "description": {"type": "string"},
      "succeeded": {"type": "boolean"},
      "caused_failure": {"type": "boolean"},
      "reverted": {"type": "boolean"}
    },
    "required": ["change_id", "description"],
    "additionalProperties": false
  }
}
```

**Key design decision:** Two-path extraction — pre-computed block takes priority; raw tracking arrays are fallback. This supports both future instrumented runs and manual/retrospective entry.

### Phase 2: Extend RunData Dataclass + load_run()

**File: `scylla/analysis/loader.py`**

**2a. Add optional fields to RunData:**

```python
@dataclass
class RunData:
    # ... existing fields ...
    # Optional process metrics (from run_result.json process_metrics block)
    r_prog: float | None = None
    strategic_drift: float | None = None
    cfp: float | None = None
    pr_revert_rate: float | None = None
```

**2b. Add extraction logic in load_run() with two-path fallback:**

```python
# Extract process metrics from run_result.json
r_prog_val: float | None = None
strategic_drift_val: float | None = None
cfp_val: float | None = None
pr_revert_rate_val: float | None = None

process_metrics_data = result.get("process_metrics")
if process_metrics_data and isinstance(process_metrics_data, dict):
    # Path 1: pre-computed block
    def _extract_process_float(key: str) -> float | None:
        raw = validate_numeric(process_metrics_data.get(key), key, np.nan)
        return None if (raw is None or np.isnan(raw)) else raw

    r_prog_val = _extract_process_float("r_prog")
    strategic_drift_val = _extract_process_float("strategic_drift")
    cfp_val = _extract_process_float("cfp")
    pr_revert_rate_val = _extract_process_float("pr_revert_rate")
else:
    # Path 2: compute from raw tracking data
    progress_tracking = result.get("progress_tracking")
    changes = result.get("changes")
    if progress_tracking or changes:
        from scylla.metrics.process import (
            ChangeResult, ProgressStep, ProgressTracker,
            calculate_cfp, calculate_pr_revert_rate,
            calculate_r_prog, calculate_strategic_drift,
        )
        if progress_tracking and isinstance(progress_tracking, list):
            steps = []
            achieved = []
            for s in progress_tracking:
                if isinstance(s, dict):
                    step = ProgressStep(
                        step_id=s.get("step_id", ""),
                        description=s.get("description", ""),
                        weight=float(s.get("weight", 1.0)),
                        completed=bool(s.get("completed", False)),
                        goal_alignment=float(s.get("goal_alignment", 1.0)),
                    )
                    steps.append(step)
                    if step.completed:
                        achieved.append(step)
            tracker = ProgressTracker(expected_steps=steps, achieved_steps=achieved)
            r_prog_val = calculate_r_prog(tracker)
            strategic_drift_val = calculate_strategic_drift(tracker)

        if changes and isinstance(changes, list):
            change_results = [
                ChangeResult(
                    change_id=c.get("change_id", ""),
                    description=c.get("description", ""),
                    succeeded=bool(c.get("succeeded", True)),
                    caused_failure=bool(c.get("caused_failure", False)),
                    reverted=bool(c.get("reverted", False)),
                )
                for c in changes if isinstance(c, dict)
            ]
            cfp_val = calculate_cfp(change_results)
            pr_revert_rate_val = calculate_pr_revert_rate(change_results)
```

**Important:** Use `from scylla.metrics.process import ...` inside the `else` branch (lazy import). This avoids circular imports and only loads the metrics module when raw tracking data is actually present.

### Phase 3: Add Columns to build_runs_df()

**File: `scylla/analysis/dataframes.py`**

Simply pass through from RunData — no calculation needed (already done in loader):

```python
rows.append({
    # ... existing fields ...
    # Optional process metrics (R_Prog, CFP, PR revert rate, strategic drift)
    "r_prog": run.r_prog,
    "strategic_drift": run.strategic_drift,
    "cfp": run.cfp,
    "pr_revert_rate": run.pr_revert_rate,
})
```

These columns will be `None` for runs without process tracking data — that's correct behavior. Downstream code should use `.dropna(subset=["r_prog"])` before analysis.

### Phase 4: Create Figure Module

**File: `scylla/analysis/figures/process_metrics.py`**

Key patterns:
1. Import guard — skip gracefully if column absent or all-null
2. Use `_filter_process_data()` helper to warn on sparse coverage
3. Box plot for R_Prog (shows distribution), bar+error for CFP/revert (shows mean ± stderr)
4. Facet by `agent_model` for model comparison

```python
def _filter_process_data(runs_df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Filter to non-null rows, warn if < 5."""
    filtered = runs_df.dropna(subset=[column])
    if len(filtered) < 5:
        logger.warning("Process metric '%s' has only %d non-null rows", column, len(filtered))
    return filtered


def fig_r_prog_by_tier(runs_df: pd.DataFrame, output_dir: Path, render: bool = True) -> None:
    if "r_prog" not in runs_df.columns:
        logger.warning("r_prog column not found; skipping")
        return
    data = _filter_process_data(runs_df[["tier", "agent_model", "r_prog"]], "r_prog")
    if data.empty:
        return
    # box plot ...
    save_figure(chart, "fig_r_prog_by_tier", output_dir, render)
```

### Phase 5: Tests

**File: `tests/unit/analysis/test_process_metrics_integration.py`**

Test structure:

1. **Loader tests** — create tmp_path run directories with mock `run_result.json`:
   - Pre-computed block: values extracted correctly
   - No process data: all fields `None`
   - Partial block: present fields populated, absent fields `None`
   - Raw tracking fallback: r_prog and drift computed correctly
   - Raw changes fallback: cfp and revert rate computed correctly
   - Precedence: pre-computed block wins over raw data

2. **DataFrame tests** — use `_make_run_data()` helper:
   - Columns present in output
   - Values correct
   - `None` preserved for runs without process metrics

3. **Figure smoke tests** — use fixture with `r_prog`, `cfp`, `pr_revert_rate` columns:
   - Output file created
   - Graceful skip when column absent
   - Graceful skip when column all-null

**Critical pattern** for loader tests:

```python
def _make_run_dir(tmp_path: Path, run_result_data: dict[str, Any], *, run_name: str = "run_01") -> Path:
    run_dir = tmp_path / run_name
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text(json.dumps(run_result_data))
    return run_dir
```

**Import at top of test file** (required for mypy):

```python
from scylla.analysis.loader import RunData
from scylla.e2e.models import TokenStats
```

Note: `TokenStats` is imported from `scylla.e2e.models`, NOT from `scylla.analysis.loader` (it's re-exported there but not in `__all__`). The `TokenStats` dataclass does NOT have a `total_tokens` field — it's a `@property`.

### Phase 6: Verification

```bash
# Run new tests only (fast feedback)
PYTHONPATH=scripts pixi run python -m pytest tests/unit/analysis/test_process_metrics_integration.py -v --no-cov

# Run full suite (required before push)
PYTHONPATH=scripts pixi run python -m pytest tests/ --no-cov -q

# Run pre-commit on changed files
pre-commit run --files scylla/analysis/loader.py scylla/analysis/dataframes.py \
  scylla/analysis/figures/process_metrics.py \
  scylla/analysis/schemas/run_result.schema.json \
  tests/unit/analysis/test_process_metrics_integration.py
```

## Failed Attempts & Lessons Learned

| Attempt | Issue | Resolution |
|---------|-------|------------|
| Putting process extraction in `dataframes.py` | Wrong layer — process.py imports are heavy | Keep in `loader.py` |
| Importing `TokenStats` from `loader.py` in tests | Not in `__all__`, mypy error | Import from `scylla.e2e.models` directly |
| Passing `total_tokens` to `TokenStats()` constructor | Field doesn't exist (it's a `@property`) | Only pass `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens` |
| `_make_run_data()` returning `object` | mypy: `"object" has no attribute "r_prog"` | Type return as `RunData` and import at module level |
| `dict` without type params in function signatures | mypy `[type-arg]` error | Use `dict[str, Any]` with `from typing import Any` |
| Pre-push hook failing due to flaky timing tests | `test_exponential_backoff_delay` fails under coverage load | Rebase onto latest `origin/main` which fixed the flaky tests |
| Stash pop created merge conflict in `runner.py` | `git stash pop` after failed push attempt conflicted | Resolve conflict keeping HEAD version (ours) |

### ❌ Attempt 1: Single-path extraction (no fallback)

**What we tried:** Only extract from `process_metrics` block, ignore raw tracking data.

**Why it failed:** The issue required supporting both pre-computed values AND raw tracking arrays. Future runs may have only raw tracking.

**Correct approach:** Two-path: pre-computed block first, raw arrays as fallback.

### ❌ Attempt 2: Eager import of `scylla.metrics.process`

**What we tried:** Import `calculate_r_prog`, etc. at module level in `loader.py`.

**Why it failed:** Would import process module even when no raw tracking data exists, adding startup overhead and potential circular import risk.

**Correct approach:** Lazy import inside the `else` branch with `# noqa: PLC0415`.

### ❌ Attempt 3: Pushing without rebasing onto latest main

**What we tried:** Push immediately after implementing.

**Why it failed:** `origin/main` had moved 5 commits ahead including fixes for flaky tests that were blocking the pre-push hook.

**Correct approach:** Always `git fetch origin && git rebase origin/main` before pushing when working on a feature branch.

## Results & Parameters

### Files Modified/Created

| File | Change | Lines |
|------|--------|-------|
| `scylla/analysis/schemas/run_result.schema.json` | Added 3 new property groups | +62 |
| `scylla/analysis/loader.py` | RunData fields + load_run() extraction | +78 |
| `scylla/analysis/dataframes.py` | 4 new columns in build_runs_df() | +5 |
| `scylla/analysis/figures/process_metrics.py` | New file: 3 figure functions | +195 |
| `tests/unit/analysis/test_process_metrics_integration.py` | New file: 14 tests | +420 |

**Total:** ~760 lines across 5 files

### Test Results

```
3199 passed, 8 warnings in 41.41s
Coverage: 78.44% (threshold: 75%)
```

**New tests:** 14 integration tests covering loader, DataFrame, and figures.

### Architecture Notes

The process metrics integration uses **optional nullable columns** in `runs_df`:
- Columns always present (`r_prog`, `cfp`, `strategic_drift`, `pr_revert_rate`)
- Values are `None` for runs without process tracking
- Figures skip gracefully (warn + return) when column is missing or all-null
- No breaking changes to existing downstream consumers

This is the correct pattern for **opt-in metrics** that are not available for all historical runs.

## Common Pitfalls

1. **TokenStats constructor:** Only 4 fields (`input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`). No `total_tokens` — that's a property.
2. **Import source for TokenStats in tests:** Use `from scylla.e2e.models import TokenStats`, not from `loader`.
3. **mypy in test helpers:** Return types must be concrete (`RunData`, not `object`).
4. **Lazy imports:** When importing from `scylla.metrics.process` inside loader, add `# noqa: PLC0415` to suppress ruff's "import not at top of file" warning.
5. **Pre-push hook:** The hook runs `pixi run pytest -x` (stop-first) without `PYTHONPATH=scripts`, so it relies on the installed `export_data` module path. Keep in sync with latest `origin/main` to avoid flaky test failures.
6. **Stash pop conflicts:** Never use `git stash` + `git push` in sequence during active development on a worktree. Use `git rebase origin/main` instead.

## Related Skills

- `add-analysis-metric` — Adding derived metrics to the pipeline
- `analysis-pipeline-architecture` — Understanding 4-layer architecture

## Success Criteria

- ✅ Schema extended with `process_metrics`, `progress_tracking`, `changes`
- ✅ `RunData` has 4 new optional fields (`r_prog`, `strategic_drift`, `cfp`, `pr_revert_rate`)
- ✅ `load_run()` extracts from pre-computed block OR computes from raw tracking
- ✅ `build_runs_df()` includes 4 new nullable columns
- ✅ 3 new figure functions with graceful null handling
- ✅ 14 integration tests (loader + dataframe + figure smoke)
- ✅ All 3199 tests passing, 78.44% coverage
