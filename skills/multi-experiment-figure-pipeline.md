---
name: multi-experiment-figure-pipeline
description: 'Patterns for adding conditional figure generation to multi-experiment
  analysis pipelines. Use when: adding new Altair figures with data-dependent guards,
  creating task-level analysis, or scaling figure pipelines to large experiment counts.'
category: evaluation
date: 2026-03-17
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Adding new figures to an existing Altair pipeline for a multi-experiment dataset (47 tests, ~1196 runs) while gracefully handling degenerate cases (single model, single judge, N=1 runs/subtest) |
| **Solution** | Guard-set pattern for conditional generation + task-analysis module with 5 new figures + Kendall's tau for rank stability |
| **Key Insight** | Data-dependent guards (detecting model/judge count at generation time) are more robust than hardcoded exclusion lists |
| **Scope** | ProjectScylla analysis infrastructure: `scylla/analysis/figures/`, `scripts/generate_figures.py`, `scylla/analysis/stats.py` |

## When to Use

- Adding new Altair/Vega-Lite figures to an existing figure registry with `save_figure()` pattern
- Implementing conditional figure generation based on dataset characteristics (single-model, single-judge, N=1)
- Creating task-level (per-experiment) analysis figures for datasets with many experiments
- Adding new statistical functions to the stats module
- Scaling a figure pipeline from 5-test to 47-test datasets

## Verified Workflow

### Quick Reference

```python
# 1. Guard-set pattern in generate_figures.py
single_judge_figures = {"fig02_judge_variance", "fig14_judge_agreement", "fig17_judge_variance_overall"}
n_judges = int(judges_df["judge_model"].nunique())

for fig_name in figures_to_generate:
    if fig_name in single_judge_figures and n_judges < 2:
        print(f"\n{fig_name}: SKIPPED (requires >=2 judges, found {n_judges})")
        success_count += 1  # Not a failure, just inapplicable
        continue

# 2. Figure function pattern (early-return guards)
def fig35_task_difficulty_distribution(runs_df, output_dir, render=True):
    if "experiment" not in runs_df.columns or "passed" not in runs_df.columns:
        return
    exp_pass_rates = runs_df.groupby("experiment")["passed"].mean().reset_index()
    if len(exp_pass_rates) < 2:
        return  # Need multiple experiments
    chart = alt.Chart(exp_pass_rates).mark_bar().encode(...)
    save_figure(chart, "fig35_task_difficulty_distribution", output_dir, render)
    exp_pass_rates.to_csv(output_dir / "fig35_task_difficulty_distribution.csv", index=False)

# 3. Register in FIGURES dict
FIGURES = {
    ...
    "fig35_task_difficulty_distribution": ("tier", fig35_task_difficulty_distribution),
}
```

### Step-by-Step: Adding a New Figure

1. **Create the figure function** in the appropriate module under `scylla/analysis/figures/`:
   - Use `derive_tier_order(runs_df)` for consistent tier sorting
   - Use `get_color_scale("tiers", tier_order)` for color consistency
   - Call `save_figure(chart, name, output_dir, render)` to write `.vl.json` + optional render
   - Export CSV alongside the figure for reproducibility
   - Add early-return guards for missing columns or insufficient data

2. **Register the figure** in `scripts/generate_figures.py`:
   - Add import at top
   - Add entry to `FIGURES` dict: `"fig_name": ("category", func)`
   - Category determines which DataFrame is passed: `"tier"/"cost"/"variance"` → `runs_df`, `"judge"` → `judges_df`, `"criteria"` → `criteria_df`

3. **Add guard sets** if the figure has preconditions:
   - `multi_model_figures`: requires `runs_df["agent_model"].nunique() >= 2`
   - `single_judge_figures`: requires `judges_df["judge_model"].nunique() >= 2`
   - Guard check happens in the generation loop, counts as success (not failure)

4. **Write smoke tests** in `tests/unit/analysis/test_figures.py`:
   - Minimum 3 tests per figure: happy path, edge case (insufficient data → no output), registry check
   - Use `render=False` to skip PNG generation in tests
   - Assert both `.vl.json` and `.csv` files exist

5. **Add stats functions** to `scylla/analysis/stats.py`:
   - Add to `__all__` list (alphabetical order)
   - Guard for n < 2 samples
   - Return tuple of (statistic, p-value)

### Auto-Detection Pattern (Full-Ablation)

```python
# Detect full-ablation experiments by subtest count
subtests_per_exp_tier = runs_df.groupby(["experiment", "tier"])["subtest"].nunique().reset_index()
max_subtests = subtests_per_exp_tier.groupby("experiment")["subtest"].max()
full_ablation_experiments = list(max_subtests[max_subtests > 3].index)
```

### Figures Created in This Session

| Figure | Type | Purpose |
| -------- | ------ | --------- |
| fig35 | Histogram | Task difficulty distribution (per-experiment pass rates) |
| fig36 | Heatmap | Tier rank stability (rank 1=best per experiment, sorted by difficulty) |
| fig37 | Scatter | Task complexity vs tier differentiation (mean pass rate vs std) |
| fig38 | Grouped bar | Full-ablation vs standard sampling comparison |
| fig39 | Scatter | Cost scaling with difficulty (cost vs pass rate, colored by tier) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Kendall's tau test with p < 0.01 | Used strict threshold in unit test for perfect correlation | With n=5 samples, `scipy.stats.kendalltau` returns p=0.017 even for perfect correlation (exact test, not asymptotic) | Use p < 0.05 for small-sample rank correlation tests; Kendall's tau p-values are larger than Spearman's for small N |

## Results & Parameters

### Configuration

```yaml
# Figure generation
render: false  # For tests (skip PNG)
render: true   # For production (300 DPI via scale_factor=3.0)

# Guard thresholds
min_models_for_multi_model: 2
min_judges_for_multi_judge: 2
min_experiments_for_histogram: 2
min_subtests_for_full_ablation: 4  # >3 triggers full-ablation detection

# Stats
kendall_tau_min_samples: 2
```

### Test Results

```
Tests added: 14 (12 figure tests + 2 stats tests)
Total analysis tests: 1380 passed, 1 skipped
Pre-commit: all hooks pass
Figures registered: 43 total (38 existing + 5 new)
```

### Key Files Modified

| File | Change |
| ------ | -------- |
| `scylla/analysis/figures/task_analysis.py` | NEW — fig35, fig36, fig37, fig38 |
| `scylla/analysis/figures/cost_analysis.py` | Added fig39_cost_scaling_with_difficulty |
| `scylla/analysis/stats.py` | Added kendall_tau() |
| `scripts/generate_figures.py` | Single-judge guards, registered fig35-39 |
| `tests/unit/analysis/test_figures.py` | 12 new smoke tests |
| `tests/unit/analysis/test_stats.py` | 2 new kendall_tau tests |
