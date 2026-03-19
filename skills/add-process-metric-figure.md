---
name: add-process-metric-figure
description: 'TRIGGER CONDITIONS: Adding a new figure function to scylla/analysis/figures/process_metrics.py
  for a per-run process metric (e.g. strategic_drift, r_prog, cfp, pr_revert_rate).
  Use when: (1) a new nullable column exists in build_runs_df() output but has no
  corresponding figure in process_metrics.py, (2) a follow-up issue says ''add a figure
  for <metric> following the same pattern as fig_r_prog_by_tier'', (3) a process metric
  column was added in a prior issue but the figure was deferred.'
category: analysis
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# add-process-metric-figure

How to implement a new figure function in `scylla/analysis/figures/process_metrics.py` for a nullable
process metric, wire it into `generate_figures.py`, and add the three required smoke tests — all as a
single self-contained change.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Add `fig_strategic_drift_by_tier` box-plot figure for the `strategic_drift` column |
| Outcome | Success — 3 new smoke tests, 388 analysis tests pass, pre-commit clean |
| Issue | HomericIntelligence/ProjectScylla#1198 |
| PR | HomericIntelligence/ProjectScylla#1301 |

## When to Use

- A new process-metric column was added to `build_runs_df()` (e.g. via issue #1134) but `process_metrics.py` only implements figures for the earlier metrics
- Follow-up issue says "add a figure for X following the same box-plot pattern as `fig_r_prog_by_tier`"
- Any issue mentioning `fig_<metric>_by_tier` that doesn't yet exist in `process_metrics.py`

## Two-Pattern Decision: Box-Plot vs Bar+ErrorBar

`process_metrics.py` uses two distinct patterns depending on metric semantics:

| Pattern | When to use | Examples |
|---------|-------------|---------|
| `mark_boxplot()` | Metric is a **distribution** value (bounded [0,1], shows spread) | `r_prog`, `strategic_drift` |
| `mark_bar()` + `mark_errorbar()` layered | Metric is a **rate/frequency** (mean makes more sense than distribution) | `cfp`, `pr_revert_rate` |

**Rule of thumb**: if the issue says "following the same box-plot pattern as `fig_r_prog_by_tier`", use `mark_boxplot()`. If it says "bar chart with error bars", use the layer pattern.

## Architecture: process_metrics.py Structure

```
_filter_process_data()      ← shared null-filter helper (reuse, never duplicate)
fig_r_prog_by_tier()        ← box-plot pattern (bounded [0,1] distributions)
fig_cfp_by_tier()           ← bar+errorbar pattern (rates)
fig_pr_revert_by_tier()     ← bar+errorbar pattern (rates)
fig_strategic_drift_by_tier() ← box-plot pattern (bounded [0,1])
```

All functions share:
- `(runs_df: pd.DataFrame, output_dir: Path, render: bool = True) -> None` signature
- Missing-column guard → `logger.warning(...)` + `return`
- `_filter_process_data(runs_df[["tier", "agent_model", <col>]], <col>)` filter + empty guard
- `derive_tier_order(data)` + `get_color_scale("models", models)` for consistent styling
- `save_figure(chart, "fig_<name>", output_dir, render)` at the end

## Verified Workflow

### Step 1: Verify the column exists in `sample_runs_df` fixture

Check `tests/unit/analysis/conftest.py` for the column in the `data.append({...})` block.
If absent, add it using the same ~10% NaN pattern as the other process metrics:

```python
strategic_drift = (
    np.random.uniform(0.0, 0.3) if np.random.random() > 0.1 else np.nan
)
```

**In this session**: `strategic_drift` was already present (added in issue #1134). No fixture change needed.

### Step 2: Add the figure function to `process_metrics.py`

Append **after** the last existing function (currently `fig_pr_revert_by_tier`).
Box-plot template (clone `fig_r_prog_by_tier`, substitute metric name):

```python
def fig_strategic_drift_by_tier(
    runs_df: pd.DataFrame, output_dir: Path, render: bool = True
) -> None:
    """Generate Fig_StrategicDrift: Strategic Drift by Tier.

    Box plot showing strategic_drift distribution per tier, faceted by agent_model.
    Skips gracefully if strategic_drift column is missing or all-null.

    Args:
        runs_df: Runs DataFrame (must contain 'strategic_drift', 'tier', 'agent_model' columns)
        output_dir: Output directory for figure files
        render: Whether to render to PNG/PDF (default: True)

    """
    if "strategic_drift" not in runs_df.columns:
        logger.warning(
            "strategic_drift column not found in runs_df; skipping fig_strategic_drift_by_tier"
        )
        return

    data = _filter_process_data(
        runs_df[["tier", "agent_model", "strategic_drift"]], "strategic_drift"
    )
    if data.empty:
        logger.warning("No strategic_drift data available; skipping fig_strategic_drift_by_tier")
        return

    tier_order = derive_tier_order(data)
    models = sorted(data["agent_model"].unique())
    domain, range_ = get_color_scale("models", models)

    chart = (
        alt.Chart(data)
        .mark_boxplot()
        .encode(
            x=alt.X("tier:N", sort=tier_order, title="Tier"),
            y=alt.Y("strategic_drift:Q", scale=alt.Scale(domain=[0, 1]), title="Strategic Drift"),
            color=alt.Color(
                "agent_model:N",
                scale=alt.Scale(domain=domain, range=range_),
                title="Model",
            ),
        )
        .facet(
            column=alt.Column("agent_model:N", title="Model"),
        )
        .properties(title="Strategic Drift by Tier")
    )

    save_figure(chart, "fig_strategic_drift_by_tier", output_dir, render)
```

**Important**: `domain=[0, 1]` is correct for bounded metrics. For unbounded metrics, use `compute_dynamic_domain(data["<col>"])`.

Also update the module docstring to list the new figure:

```python
"""Process metrics figures.

Generates Fig_RProg (R_Prog by tier), Fig_CFP (CFP by tier),
Fig_PRRevert (PR Revert Rate by tier), and Fig_StrategicDrift (Strategic Drift by tier).
"""
```

### Step 3: Wire into `generate_figures.py`

Two edits — see `wire-figure-pipeline` skill for full details:

1. Add to import block:
```python
from scylla.analysis.figures.process_metrics import (
    fig_cfp_by_tier,
    fig_pr_revert_by_tier,
    fig_r_prog_by_tier,
    fig_strategic_drift_by_tier,  # ← add alphabetically within block
)
```

2. Add to `FIGURES` registry (append after `fig_pr_revert_by_tier`):
```python
"fig_strategic_drift_by_tier": ("tier", fig_strategic_drift_by_tier),
```

No changes to the dispatch block in `main()` — the `"tier"` category already dispatches `runs_df`.

### Step 4: Add three smoke tests to `tests/unit/analysis/test_figures.py`

```python
def test_fig_strategic_drift_by_tier(sample_runs_df, tmp_path):
    """Smoke test: fig_strategic_drift_by_tier generates output file without error."""
    from scylla.analysis.figures.process_metrics import fig_strategic_drift_by_tier

    fig_strategic_drift_by_tier(sample_runs_df, tmp_path, render=False)
    assert (tmp_path / "fig_strategic_drift_by_tier.vl.json").exists()


def test_fig_strategic_drift_by_tier_missing_column(tmp_path):
    """fig_strategic_drift_by_tier skips gracefully when column absent."""
    import pandas as pd

    from scylla.analysis.figures.process_metrics import fig_strategic_drift_by_tier

    df = pd.DataFrame({"tier": ["T0"], "agent_model": ["Sonnet 4.5"], "score": [0.8]})
    fig_strategic_drift_by_tier(df, tmp_path, render=False)
    assert not (tmp_path / "fig_strategic_drift_by_tier.vl.json").exists()


def test_fig_strategic_drift_by_tier_all_null(tmp_path):
    """fig_strategic_drift_by_tier skips gracefully when column all-null."""
    import pandas as pd

    from scylla.analysis.figures.process_metrics import fig_strategic_drift_by_tier

    df = pd.DataFrame(
        {
            "tier": ["T0", "T1"],
            "agent_model": ["Sonnet 4.5", "Sonnet 4.5"],
            "strategic_drift": [None, None],
        }
    )
    fig_strategic_drift_by_tier(df, tmp_path, render=False)
    assert not (tmp_path / "fig_strategic_drift_by_tier.vl.json").exists()
```

Also update the two existing registry assertions to include the new figure:

```python
def test_generate_figures_registry_includes_process_metrics() -> None:
    assert "fig_strategic_drift_by_tier" in FIGURES  # add this line

def test_generate_figures_process_metrics_use_tier_category() -> None:
    assert FIGURES["fig_strategic_drift_by_tier"][0] == "tier"  # add this line
```

### Step 5: Run pre-commit (two passes)

```bash
pre-commit run --files scylla/analysis/figures/process_metrics.py scripts/generate_figures.py tests/unit/analysis/test_figures.py
# First pass: ruff-format auto-reformats long lines (e.g. wraps logger.warning() calls)
# Second pass: all checks pass
pre-commit run --files scylla/analysis/figures/process_metrics.py scripts/generate_figures.py tests/unit/analysis/test_figures.py
```

### Step 6: Run tests

```bash
PYTHONPATH=scripts pixi run python -m pytest tests/unit/analysis/ -v --no-cov
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Writing the long `logger.warning(...)` call on one line | ruff-format auto-wraps lines >88 chars during pre-commit | Write `logger.warning(...)` content as it will be after wrapping, or just let ruff fix it on first pass |
| Considered a `.facet().properties()` chaining issue for box-plots | Checked `fix-altair-facet-layering` skill — that issue is specific to `alt.layer()` + `.facet()`. Simple `.mark_boxplot().encode().facet().properties()` works without any workaround | Box-plot doesn't use `alt.layer()`, so the facet-layering quirk doesn't apply |

## Results & Parameters

### Files changed (3 files, 0 new files)

| File | Change |
|------|--------|
| `scylla/analysis/figures/process_metrics.py` | +50 lines: module docstring update + `fig_strategic_drift_by_tier` |
| `scripts/generate_figures.py` | +2 lines: import + registry entry |
| `tests/unit/analysis/test_figures.py` | +42 lines: 3 new tests + 2 registry assertion updates |

### Test count delta

388 → 391 analysis unit tests (3 new smoke tests)

### Pre-commit behaviour

- First run: ruff-format auto-reformats `process_metrics.py` (1 file modified)
- Second run: all checks pass

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1198, PR #1301 | Follow-up from #1136 (wire-figure-pipeline) |

## References

- Related skills: `wire-figure-pipeline` (wiring only, no new function), `add-analysis-metric` (adding raw columns to dataframes layer)
- Production file: `scylla/analysis/figures/process_metrics.py`
- Pipeline file: `scripts/generate_figures.py`
- Test file: `tests/unit/analysis/test_figures.py`
- Fixture file: `tests/unit/analysis/conftest.py`
