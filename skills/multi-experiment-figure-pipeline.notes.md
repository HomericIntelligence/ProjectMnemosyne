# Session Notes: Multi-Experiment Figure Pipeline Enhancement

## Date: 2026-03-17

## Context

ProjectScylla dryrun3 experiment completed with 47 tests, ~1196 runs, 60.1% pass rate using
Haiku 4.5 as both agent and judge. The existing analysis infrastructure had figures designed
for a smaller 5-test dataset. Needed to add task-level analysis figures and handle degenerate
cases from single-model/single-judge datasets.

## Session Objective

Implement Phases 1-3 of the haiku paper infrastructure plan:
1. Single-judge figure guards
2. New figures (fig35-39) for 47-test analysis
3. Stats enhancement (Kendall's tau)

## Approach

### Phase 1: Single-Judge Guards

Added a `single_judge_figures` set in `generate_figures.py` mirroring the existing
`multi_model_figures` pattern. Detection via `judges_df["judge_model"].nunique() < 2`.
Three figures guarded: fig02, fig14, fig17 — all would produce degenerate output with
a single judge model.

### Phase 2: New Figures

Created `scylla/analysis/figures/task_analysis.py` as a new module with 4 figures:
- fig35: Histogram of per-experiment pass rates — shows difficulty spectrum
- fig36: Heatmap of tier ranks per experiment — visualizes rank stability (RQ2)
- fig37: Scatter of difficulty vs tier std — shows differentiation patterns
- fig38: Grouped bar comparing full-ablation vs standard — auto-detects by subtest count

Added fig39 to existing `cost_analysis.py`:
- Scatter of cost vs pass rate, colored by tier — shows cost scaling

Key design decisions:
- All figures use early-return guards for missing columns or insufficient data
- fig38 auto-detects full-ablation experiments (>3 subtests per tier) but also accepts explicit list
- fig36 uses rank(ascending=False, method="average") for ties
- All figures export CSV alongside Vega-Lite spec

### Phase 3: Kendall's Tau

Added `kendall_tau()` to `scylla/analysis/stats.py` wrapping `scipy.stats.kendalltau`.
Guards for n < 2. Added to `__all__` in alphabetical order.

## Key Learnings

1. **Guard-set pattern scales well**: Adding new guard sets (single_judge_figures) follows
   the same pattern as multi_model_figures. Detection at runtime is more robust than
   hardcoded exclusion.

2. **Kendall's tau p-values are exact for small N**: With n=5, even perfect correlation
   gives p=0.017 (not <0.01). This is because scipy uses the exact permutation distribution,
   not an asymptotic approximation. Tests should use p < 0.05.

3. **Auto-detection over configuration**: fig38's auto-detection of full-ablation experiments
   by subtest count eliminates the need for user configuration.

4. **Category routing in FIGURES dict**: The category string ("tier", "cost", "judge") determines
   which DataFrame gets passed to the generator function. New task-analysis figures use "tier"
   category since they consume `runs_df`.

## Raw Stats

- 5 new figures created
- 1 new stats function (kendall_tau)
- 14 new tests (12 figure + 2 stats)
- 1380 total analysis tests pass
- 43 total figures in registry
- All pre-commit hooks pass