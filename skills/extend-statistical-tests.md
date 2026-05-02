---
name: extend-statistical-tests
description: 'TRIGGER CONDITIONS: Adding a new nullable per-run metric to all four
  statistical test sections (normality, omnibus, pairwise, effect sizes) in scripts/export_data.py
  compute_statistical_results(). Use when surfacing process or quality metrics in
  statistical_results.json.'
category: evaluation
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# extend-statistical-tests

How to add a new metric to all four statistical test categories in `compute_statistical_results()`
inside `scripts/export_data.py`, with correct NaN/missing-column guards and TDD workflow.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-02 |
| Objective | Add `r_prog`, `cfp`, `pr_revert_rate` to normality, omnibus, pairwise, and effect-size sections of `statistical_results.json` |
| Outcome | Success — 15 new tests, 3598 total passing, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1186 |
| PR | HomericIntelligence/ProjectScylla#1300 |

## When to Use

- Adding any nullable per-run metric to `normality_tests`, `omnibus_tests`, `pairwise_comparisons`,
  or `effect_sizes` in `compute_statistical_results()` (`scripts/export_data.py`)
- The metric already exists as a column in `runs_df` (i.e. it's already in `build_runs_df()`)
- You want the research paper to have significance data for the metric, not just descriptive means

**Related skill**: `add-analysis-metric` — use that when adding *aggregations* (mean/median/std)
to `build_subtests_df()` / `tier_summary()`. This skill is for the *statistical tests* layer.

## Architecture: Statistical Tests Layer

`compute_statistical_results()` composes four helpers:

```
_compute_normality_tests()     → Shapiro-Wilk per (model, tier)
_compute_omnibus_tests()       → Kruskal-Wallis across tiers per model
_compute_pairwise_comparisons() → Mann-Whitney consecutive pairs (Holm-corrected)
_compute_effect_sizes()        → Cliff's delta with 95% CI
```

Process metrics use **consecutive-tier pairs only** — no first→last overall contrast.
The overall contrast applies only to `pass_rate` (it has explicit meaning as the
"baseline vs best tier" comparison).

## Verified Workflow

### Step 1: Confirm the column exists in `runs_df`

```python
# Check build_runs_df() output in scylla/analysis/dataframes.py
# The column must exist before add it to statistical tests
assert "r_prog" in runs_df.columns  # True if #1134 / add-analysis-metric was done
```

### Step 2: Add to `_compute_normality_tests()`

Extend `metric_cols` list and add a column-existence guard in the inner loop:

```python
metric_cols = [
    "score", "impl_rate", "cost_usd", "duration_seconds",
    "r_prog", "cfp", "pr_revert_rate",   # NEW
]

for metric in metric_cols:
    if metric not in tier_data.columns:   # guard — backward compat
        continue
    values = tier_data[metric].dropna()
    if len(values) >= 3:
        ...
```

### Step 3: Add to `_compute_omnibus_tests()`

Append to `metric_configs` **after** the static list, using a column-existence guard:

```python
# Static entries (pass_rate, impl_rate, duration_seconds) stay as-is
metric_configs = [...]

# Conditionally append process metrics
for process_metric in ("r_prog", "cfp", "pr_revert_rate"):
    if process_metric in model_runs.columns:
        metric_configs.append(
            (
                process_metric,
                [
                    model_runs[model_runs["tier"] == t][process_metric].dropna()
                    for t in tier_order
                ],
            )
        )
```

**Why not extend the static list?** The static entries use `.astype(int)` or columns guaranteed
present. Process metrics are optional — they may be absent in old DataFrames.

### Step 4: Add to `_compute_pairwise_comparisons()`

Add metrics to the consecutive-pairs tuple and guard with column-existence check:

```python
# Before: ("impl_rate", "duration_seconds")
# After:
for metric in ("impl_rate", "duration_seconds", "r_prog", "cfp", "pr_revert_rate"):
    if metric not in model_runs.columns:
        continue
    ...
```

**Do NOT add** an overall first→last contrast for process metrics. That is intentionally
reserved for `pass_rate` only.

### Step 5: Add to `_compute_effect_sizes()`

Same pattern — extend the inner metric tuple and guard:

```python
# Before: ("impl_rate", "duration_seconds")
# After:
for metric in ("impl_rate", "duration_seconds", "r_prog", "cfp", "pr_revert_rate"):
    if metric not in model_runs.columns:
        continue
    d1 = t1[metric].dropna()
    d2 = t2[metric].dropna()
    if len(d1) >= 2 and len(d2) >= 2:
        ...
```

### Step 6: Write TDD tests (red → green)

Add to `tests/unit/analysis/test_export_data.py`. The `sample_runs_df` fixture already
has `r_prog`, `cfp`, `pr_revert_rate` columns (~90% populated).

**Add `import pytest` at top of the file** if not already present.

**Parametrized per-category tests** (12 tests for 4 categories × 3 metrics):

```python
@pytest.mark.parametrize("metric", ["r_prog", "cfp", "pr_revert_rate"])
def test_process_metrics_in_normality_tests(sample_runs_df, metric):
    from export_data import _compute_normality_tests
    from scylla.analysis.figures import derive_tier_order
    tier_order = derive_tier_order(sample_runs_df)
    models = sorted(sample_runs_df["agent_model"].unique())
    results = _compute_normality_tests(sample_runs_df, models, tier_order)
    entries = [e for e in results if e["metric"] == metric]
    assert len(entries) > 0, f"{metric} should appear in normality_tests"
    required = {"model", "tier", "metric", "n", "w_statistic", "p_value", "is_normal"}
    for entry in entries:
        assert required <= entry.keys()
        assert isinstance(entry["is_normal"], bool)
        assert entry["n"] >= 3
```

**Regression guard** (1 test — catches accidental metric removal):

```python
def test_normality_tests_all_metrics(sample_runs_df):
    from export_data import _compute_normality_tests
    from scylla.analysis.figures import derive_tier_order
    tier_order = derive_tier_order(sample_runs_df)
    models = sorted(sample_runs_df["agent_model"].unique())
    results = _compute_normality_tests(sample_runs_df, models, tier_order)
    expected = {
        "score", "impl_rate", "cost_usd", "duration_seconds",
        "r_prog", "cfp", "pr_revert_rate",
    }
    assert expected <= {e["metric"] for e in results}
```

**Graceful-degradation test** (1 test — all-NaN and missing-column robustness):

```python
def test_sparse_process_metrics_graceful_degradation():
    import numpy as np
    import pandas as pd
    from export_data import (
        _compute_effect_sizes, _compute_normality_tests,
        _compute_omnibus_tests, _compute_pairwise_comparisons,
    )
    rng = np.random.RandomState(0)
    rows = []
    for tier in ["T0", "T1"]:
        for _ in range(5):
            rows.append({
                "agent_model": "model1", "tier": tier,
                "score": rng.uniform(0.3, 0.9), "impl_rate": rng.uniform(0.3, 0.9),
                "cost_usd": rng.uniform(0.01, 0.1), "duration_seconds": rng.uniform(5.0, 25.0),
                "passed": rng.choice([0, 1]),
                "r_prog": np.nan, "cfp": np.nan, "pr_revert_rate": np.nan,
            })
    df = pd.DataFrame(rows)
    models, tier_order = ["model1"], ["T0", "T1"]
    norm = _compute_normality_tests(df, models, tier_order)
    omni = _compute_omnibus_tests(df, models, tier_order)
    pairwise = _compute_pairwise_comparisons(df, models, tier_order)
    effects = _compute_effect_sizes(df, models, tier_order)
    process_metrics = {"r_prog", "cfp", "pr_revert_rate"}
    assert not any(e["metric"] in process_metrics for e in norm)
    assert not any(e["metric"] in process_metrics for e in omni)
    assert not any(e["metric"] in process_metrics for e in pairwise)
    assert not any(e["metric"] in process_metrics for e in effects)
```

### Step 7: Verify

```bash
# New tests only (fast)
pixi run python -m pytest tests/unit/analysis/test_export_data.py \
  -k "process_metrics or normality_tests_all_metrics or sparse_process" -q

# Full analysis suite
pixi run python -m pytest tests/unit/analysis/test_export_data.py -q

# Full unit suite (required before PR)
pixi run python -m pytest tests/unit/ -q

# Pre-commit (ruff format will reformat the file on first run — run twice)
pre-commit run --files scripts/export_data.py tests/unit/analysis/test_export_data.py
pre-commit run --files scripts/export_data.py tests/unit/analysis/test_export_data.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Invariants

- **Process metrics use consecutive pairs only** — `pairwise_comparisons` and `effect_sizes`
  loop over `tier_order[i], tier_order[i+1]` pairs; no first→last contrast.
- **Pass-rate has overall contrast** — the `_collect_pairwise_pass_rate()` helper deliberately
  adds a first→last pair. Do not replicate this pattern for other metrics.
- **Column guards are backward-compatible** — any DataFrame lacking process metric columns
  (e.g. old data, minimal test fixtures) will silently skip those metrics and return
  results only for the always-present columns.
- **Holm-Bonferroni is per model per metric** — each (model, metric) pair forms its own
  correction family. Don't mix metrics into one family.
- **Minimum sample sizes** — normality requires `n >= 3`; pairwise requires `n >= 2` per group;
  effect sizes require `n >= 2` per group.

## Results & Parameters

### Metrics added

```python
PROCESS_METRIC_COLS_STATS = ["r_prog", "cfp", "pr_revert_rate"]
```

(`strategic_drift` is intentionally excluded — it is a tier-level metric, not per-run.)

### conftest mock (required for test speed)

```python
# tests/unit/analysis/conftest.py — already present as autouse fixture
@pytest.fixture(autouse=True)
def mock_power_simulations():
    with (
        patch("scylla.analysis.stats.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.stats.kruskal_wallis_power", return_value=0.75),
        ...
    ):
        yield
```

Without this mock, `compute_statistical_results()` runs 10,000 Monte Carlo iterations
per tier-pair per model, causing tests to hang for 2+ minutes.

### Test count

- New tests added: 15
- Total after: 3598 passing, 1 skipped

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1186, PR #1300 | extend `compute_statistical_results()` with process metrics |

## References

- Related skill: `add-analysis-metric` — aggregation layer (dataframes.py)
- Production file: `scripts/export_data.py`
- Test file: `tests/unit/analysis/test_export_data.py`
- Fixture file: `tests/unit/analysis/conftest.py`
