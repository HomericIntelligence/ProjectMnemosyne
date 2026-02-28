---
name: "Skill: Export Process Metrics to Summary JSON"
description: "Workflow for wiring pre-existing dataframe columns into the export_data.py summary JSON output"
category: evaluation
date: 2026-02-27
user-invocable: false
---
# Skill: Export Process Metrics to Summary JSON

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Objective** | Add `mean_r_prog`, `mean_cfp`, `mean_pr_revert_rate` to `summary.json` (overall_stats, by_model, by_tier) |
| **Outcome** | ✅ Success — PR #1182, 3258 tests passing, coverage 78.43% |
| **Files Modified** | 3 (`scripts/export_data.py`, `tests/unit/analysis/conftest.py`, `tests/unit/analysis/test_export_data.py`) |
| **Issue** | #1135 (follow-up from #997) |

## When to Use This Skill

**Trigger conditions:**
- Columns already exist in `runs_df` (confirmed via `build_runs_df()` in `scylla/analysis/dataframes.py`)
- Task is to expose them in `summary.json` — not to add them to the dataframe layer
- The issue asks for `mean_<metric>` per overall/model/tier

**Distinction from `add-analysis-metric`:**
- `add-analysis-metric` = new metric, starts from `stats.py` → `dataframes.py` → `export_data.py`
- This skill = column already in `runs_df`; only `export_data.py` + fixtures + tests need changing

**Prerequisites:**
- Confirm columns exist: `grep -n "<column>" scylla/analysis/dataframes.py`
- Read `scripts/export_data.py` lines ~696–798 to understand the three summary sections

## Verified Workflow

### Step 1: Confirm columns exist in runs_df

```bash
grep -n "r_prog\|cfp\|pr_revert_rate" scylla/analysis/dataframes.py
```

Expected: entries in `build_runs_df()` around lines 147–150.
If absent, use the `add-analysis-metric` skill instead.

### Step 2: Add to overall_stats

In `scripts/export_data.py`, find the `"overall_stats"` dict (around line 706).
Add after existing keys:

```python
"overall_stats": {
    # ... existing fields ...
    "mean_r_prog": float(runs_df["r_prog"].dropna().mean()) if not runs_df["r_prog"].dropna().empty else None,
    "mean_cfp": float(runs_df["cfp"].dropna().mean()) if not runs_df["cfp"].dropna().empty else None,
    "mean_pr_revert_rate": float(runs_df["pr_revert_rate"].dropna().mean()) if not runs_df["pr_revert_rate"].dropna().empty else None,
},
```

**Pattern:** `dropna()` → check empty → `float(mean())` or `None`.
Never use bare `.mean()` without `dropna()` — NaN propagates and produces `np.nan`, which is not JSON-serializable.

### Step 3: Add to by_model loop

Inside the `for model in runs_df["agent_model"].unique():` loop in `export_data.py`.
Extract slices before the dict literal (avoids repeated computation):

```python
model_r_prog = model_df["r_prog"].dropna()
model_cfp = model_df["cfp"].dropna()
model_pr_revert_rate = model_df["pr_revert_rate"].dropna()

summary["by_model"][model] = {
    # ... existing fields ...
    "mean_r_prog": float(model_r_prog.mean()) if not model_r_prog.empty else None,
    "mean_cfp": float(model_cfp.mean()) if not model_cfp.empty else None,
    "mean_pr_revert_rate": float(model_pr_revert_rate.mean()) if not model_pr_revert_rate.empty else None,
}
```

### Step 4: Add to by_tier loop

Inside the `for tier in tier_order:` loop. Same pattern:

```python
tier_r_prog = tier_df["r_prog"].dropna()
tier_cfp = tier_df["cfp"].dropna()
tier_pr_revert_rate = tier_df["pr_revert_rate"].dropna()

summary["by_tier"][tier] = {
    # ... existing fields ...
    "mean_r_prog": float(tier_r_prog.mean()) if not tier_r_prog.empty else None,
    "mean_cfp": float(tier_cfp.mean()) if not tier_cfp.empty else None,
    "mean_pr_revert_rate": float(tier_pr_revert_rate.mean()) if not tier_pr_revert_rate.empty else None,
}
```

### Step 5: Update sample_runs_df fixture

In `tests/unit/analysis/conftest.py`, the `sample_runs_df` fixture must include the columns.
Add to the `data.append({...})` block:

```python
# Process metrics (some NaN to exercise edge-case paths)
r_prog = np.random.uniform(0.0, 1.0) if np.random.random() > 0.1 else np.nan
cfp = np.random.uniform(0.0, 0.5) if np.random.random() > 0.1 else np.nan
pr_revert_rate = (
    np.random.uniform(0.0, 0.3) if np.random.random() > 0.1 else np.nan
)

data.append({
    # ... existing fields ...
    "r_prog": r_prog,
    "cfp": cfp,
    "pr_revert_rate": pr_revert_rate,
})
```

**Key:** use ~10% NaN rate (`> 0.1`) to exercise both the populated and empty-after-dropna paths.

### Step 6: Add tests

In `tests/unit/analysis/test_export_data.py`, add `test_process_metrics_in_summary()`:

```python
def test_process_metrics_in_summary(sample_runs_df):
    """Test that process metrics appear in overall_stats, by_model, and by_tier."""
    import numpy as np
    import pandas as pd
    from export_data import json_nan_handler
    from scylla.analysis.figures import derive_tier_order

    tier_order = derive_tier_order(sample_runs_df)
    process_metric_keys = ["mean_r_prog", "mean_cfp", "mean_pr_revert_rate"]

    # overall_stats check
    overall_stats = {
        "mean_r_prog": float(sample_runs_df["r_prog"].dropna().mean())
                       if not sample_runs_df["r_prog"].dropna().empty else None,
        "mean_cfp": float(sample_runs_df["cfp"].dropna().mean())
                    if not sample_runs_df["cfp"].dropna().empty else None,
        "mean_pr_revert_rate": float(sample_runs_df["pr_revert_rate"].dropna().mean())
                               if not sample_runs_df["pr_revert_rate"].dropna().empty else None,
    }
    for key in process_metric_keys:
        assert key in overall_stats
        val = overall_stats[key]
        assert val is None or isinstance(val, float)

    # All-NaN → None
    nan_df = sample_runs_df.copy()
    nan_df["r_prog"] = np.nan
    r_prog_vals = nan_df["r_prog"].dropna()
    assert (float(r_prog_vals.mean()) if not r_prog_vals.empty else None) is None

    # Zero → 0.0
    zero_df = sample_runs_df.copy()
    zero_df["r_prog"] = 0.0
    r_prog_vals = zero_df["r_prog"].dropna()
    assert (float(r_prog_vals.mean()) if not r_prog_vals.empty else None) == 0.0

    # Partial NaN → mean of non-NaN
    partial_df = pd.DataFrame({"r_prog": [0.2, np.nan, 0.4, np.nan, 0.6]})
    clean = partial_df["r_prog"].dropna()
    assert abs((float(clean.mean()) if not clean.empty else None) - 0.4) < 1e-9

    # JSON-serializable
    check = {"mean_r_prog": float(sample_runs_df["r_prog"].dropna().mean())
                             if not sample_runs_df["r_prog"].dropna().empty else None}
    parsed = json.loads(json.dumps(check, default=json_nan_handler))
    assert parsed["mean_r_prog"] is None or isinstance(parsed["mean_r_prog"], float)
```

### Step 7: Pre-commit + test run

```bash
# Run hooks (ruff will reformat long lines — re-run after first failure)
pre-commit run --files scripts/export_data.py tests/unit/analysis/conftest.py tests/unit/analysis/test_export_data.py

# Re-run after auto-formatting
pre-commit run --files scripts/export_data.py tests/unit/analysis/conftest.py tests/unit/analysis/test_export_data.py

# Full test suite
pixi run python -m pytest tests/ -v --tb=short -q
```

## Failed Attempts & Lessons Learned

| Attempt | Issue | Resolution |
|---------|-------|------------|
| Bare `.mean()` without `dropna()` | Produces `np.nan` → not JSON-serializable | Always chain `dropna()` first |
| Single pre-commit run | Ruff reformats long lines on first pass, then fails | Run twice: first pass reformats, second pass validates |
| Checking if column all-NaN via `isnan` | `np.isnan` raises on non-float dtypes | Use `dropna().empty` check instead |

### ❌ Attempt 1: Bare `.mean()` without dropna()

**What we tried:**
```python
"mean_r_prog": float(runs_df["r_prog"].mean()),
```

**Why it fails:**
- If any row has `NaN`, pandas `.mean()` skips them by default — but if **all** rows are NaN, returns `np.nan`
- `np.nan` is not JSON-serializable; `json.dumps` raises `ValueError` unless `json_nan_handler` is in the `default=` chain
- Even with the handler, downstream consumers may not expect `null` without being told it means "no data"

**Correct approach:**
```python
clean = runs_df["r_prog"].dropna()
"mean_r_prog": float(clean.mean()) if not clean.empty else None,
```

### ⚠️ Pre-commit ruff reformats long lines on first pass

Ruff auto-reformats files (line-length enforcement) on the first `pre-commit run`. The hook exits with status 1 and reports "files were modified". Re-running immediately passes because the files are now compliant.

**Workflow:**
```bash
pre-commit run --files <files>   # first: reformats
pre-commit run --files <files>   # second: all pass
```

Do NOT interpret the first failure as a real error — check if only `ruff-format-python` failed and files were modified.

## Results & Parameters

### Files Modified (Issue #1135)

| File | Change |
|------|--------|
| `scripts/export_data.py` | +27 lines: 3 new keys in overall_stats, 3 in by_model, 3 in by_tier |
| `tests/unit/analysis/conftest.py` | +10 lines: r_prog, cfp, pr_revert_rate columns in sample_runs_df |
| `tests/unit/analysis/test_export_data.py` | +108 lines: test_process_metrics_in_summary() |

### Test Results

```
3258 passed, 9 warnings in 48.85s
Total coverage: 78.43% (threshold: 75%)
```

### JSON Output Shape

After this change, `summary.json` includes:

```json
{
  "overall_stats": {
    "mean_r_prog": 0.512,
    "mean_cfp": 0.187,
    "mean_pr_revert_rate": 0.043
  },
  "by_model": {
    "Sonnet 4.5": {
      "mean_r_prog": 0.531,
      "mean_cfp": 0.172,
      "mean_pr_revert_rate": 0.038
    }
  },
  "by_tier": {
    "T0": {
      "mean_r_prog": 0.489,
      "mean_cfp": 0.201,
      "mean_pr_revert_rate": 0.051
    }
  }
}
```

Values are `float` or `null` (never `NaN`).

## Related Skills

- `add-analysis-metric` — use when the column does NOT yet exist in `build_runs_df()`
- `parallel-metrics-integration` — covers process metrics history and `build_runs_df()` column provenance
- `defensive-analysis-patterns` — NaN handling, `dropna()` before `.mean()`, `safe_float()` patterns

## Success Criteria

- ✅ Columns confirmed present in `build_runs_df()` before starting
- ✅ Three sections updated: `overall_stats`, `by_model`, `by_tier`
- ✅ `dropna()` + empty guard + `float()` wrapping on all values
- ✅ `sample_runs_df` fixture includes new columns with partial NaN (~10%)
- ✅ Tests cover: normal, all-NaN → None, partial-NaN, zero, JSON-serialization
- ✅ Pre-commit passes on second run (ruff auto-formats on first)
- ✅ Full test suite passes with ≥75% coverage
