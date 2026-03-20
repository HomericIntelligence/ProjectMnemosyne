---
name: wire-figure-pipeline
description: 'TRIGGER CONDITIONS: Adding new figure functions to the generate_figures.py
  pipeline in ProjectScylla. Use when: (1) a new figure function exists in scylla/analysis/figures/
  but is not called from scripts/generate_figures.py, (2) registering batch-generated
  figures so they run automatically with all other figures, (3) wiring process-metric
  or other optional figures into the report pipeline.'
category: evaluation
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# wire-figure-pipeline

How to register a new figure function in the `generate_figures.py` report pipeline in ProjectScylla, including the correct dispatch category, import order, and registry tests.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-27 |
| Objective | Wire `fig_r_prog_by_tier`, `fig_cfp_by_tier`, `fig_pr_revert_by_tier` into `scripts/generate_figures.py` so they are produced automatically during analysis runs |
| Outcome | Success — 2 new registry tests, 3259 total passing, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1136 |
| PR | HomericIntelligence/ProjectScylla#1194 |

## When to Use

- A figure function exists in `scylla/analysis/figures/*.py` but never appears in the `FIGURES` dict in `scripts/generate_figures.py`
- Running `generate_figures.py --list-figures` does **not** list a figure that should be auto-generated
- Adding process-metrics figures (`r_prog`, `cfp`, `pr_revert_rate`) that were implemented but not wired in
- Any follow-up issue mentioning "figure exists but is not called from the main pipeline"

## Architecture: generate_figures.py Dispatch System

`scripts/generate_figures.py` uses a registry + category-based dispatch:

```python
# FIGURES dict: maps figure name -> (category, generator_func)
FIGURES: dict[str, tuple[str, Any]] = {
    "fig04_pass_rate_by_tier": ("tier", fig04_pass_rate_by_tier),
    ...
}

# Dispatch block in main() — maps category to DataFrame argument:
if category in ("variance", "tier", "cost", "token", "model", ...):
    generator_func(runs_df, output_dir, render=render)
elif category == "judge":
    generator_func(judges_df, output_dir, render=render)
elif category == "criteria":
    generator_func(criteria_df, output_dir, render=render)
```

**Category selection rule**: Pick the category whose dispatch block matches the figure function's call signature:
- `(runs_df, output_dir, render=...)` → use `"tier"` (or `"variance"`, `"cost"`, `"impl_rate"`, etc. — they all dispatch identically)
- `(judges_df, output_dir, render=...)` → use `"judge"`
- `(criteria_df, output_dir, render=...)` → use `"criteria"`

## Verified Workflow

### Step 1: Confirm the figure function's call signature

```python
# In scylla/analysis/figures/process_metrics.py:
def fig_r_prog_by_tier(runs_df: pd.DataFrame, output_dir: Path, render: bool = True) -> None:
```

Signature matches the `runs_df` dispatch categories.

### Step 2: Add the import to `scripts/generate_figures.py`

Insert an alphabetically-sorted import block after the existing figure imports (ruff enforces import order):

```python
from scylla.analysis.figures.process_metrics import (
    fig_cfp_by_tier,
    fig_pr_revert_by_tier,
    fig_r_prog_by_tier,
)
```

**Important**: Place in alphabetical module order (process_metrics comes after model_comparison, before spec_builder). Ruff will auto-fix ordering during pre-commit if wrong.

### Step 3: Register in the `FIGURES` dict

Append at the end of `FIGURES` (before the closing `}`):

```python
"fig_r_prog_by_tier": ("tier", fig_r_prog_by_tier),
"fig_cfp_by_tier": ("tier", fig_cfp_by_tier),
"fig_pr_revert_by_tier": ("tier", fig_pr_revert_by_tier),
```

No changes to the dispatch block in `main()` are needed — existing categories already handle `runs_df` figures.

### Step 4: Add registry tests to `tests/unit/analysis/test_figures.py`

```python
def test_generate_figures_registry_includes_process_metrics() -> None:
    """FIGURES registry contains the three process-metrics figures."""
    from scripts.generate_figures import FIGURES

    assert "fig_r_prog_by_tier" in FIGURES
    assert "fig_cfp_by_tier" in FIGURES
    assert "fig_pr_revert_by_tier" in FIGURES


def test_generate_figures_process_metrics_use_tier_category() -> None:
    """Process-metrics figures are registered under the 'tier' category."""
    from scripts.generate_figures import FIGURES

    assert FIGURES["fig_r_prog_by_tier"][0] == "tier"
    assert FIGURES["fig_cfp_by_tier"][0] == "tier"
    assert FIGURES["fig_pr_revert_by_tier"][0] == "tier"
```

### Step 5: Verify

```bash
# Run analysis tests in directory mode (required — file-only mode has conftest issue)
pixi run python -m pytest tests/unit/analysis/ -q --no-cov

# Full suite (required before PR)
pixi run python -m pytest tests/ -q --no-cov

# Pre-commit
pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Conftest / test_figures.py: Known Import Quirk

`tests/unit/analysis/conftest.py` has an `autouse` fixture that patches `export_data` (a top-level script module):

```python
with (
    patch("export_data.mann_whitney_power", return_value=0.8, create=True),
    ...
):
```

This requires `export_data` to be importable (it's in `scripts/`, which is on `sys.path` via `pythonpath = ["."]` in `pyproject.toml` + `scripts/__init__.py`). The module only gets loaded when tests are collected in a broader scope that causes it to be imported.

**Practical rule**: Tests in `test_figures.py` that import from `scripts.generate_figures` will fail with `ModuleNotFoundError: No module named 'export_data'` when run in isolation but pass when run as part of `tests/unit/analysis/` or `tests/`. This is a pre-existing quirk, not a bug in the new tests.

## Results & Parameters

### Import block location

```python
# After: scylla.analysis.figures.model_comparison
# Before: scylla.analysis.figures.spec_builder
from scylla.analysis.figures.process_metrics import (
    fig_cfp_by_tier,
    fig_pr_revert_by_tier,
    fig_r_prog_by_tier,
)
```

### FIGURES dict entries

```python
"fig_r_prog_by_tier": ("tier", fig_r_prog_by_tier),
"fig_cfp_by_tier": ("tier", fig_cfp_by_tier),
"fig_pr_revert_by_tier": ("tier", fig_pr_revert_by_tier),
```

### Test count delta

3257 → 3259 (2 new registry tests)

### Coverage

78.38% (above 75% threshold)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1136, PR #1194 | Follow-up from #997 |

## Note: figures wired here were later renamed

The three process-metrics figures documented in this skill used ad-hoc names at wire time. They were subsequently renamed to the `fig{NN}` convention in issue #1199 / PR #1302:

- `fig_r_prog_by_tier` → `fig28_r_prog_by_tier`
- `fig_cfp_by_tier` → `fig29_cfp_by_tier`
- `fig_pr_revert_by_tier` → `fig30_pr_revert_by_tier`

See the `rename-figure-convention` skill for the complete rename workflow.

## References

- Related skills: `add-analysis-metric` (adding metrics), `add-analysis-figure` (adding new figure modules), `rename-figure-convention` (standardizing fig{NN} names post-wire)
- Production file: `scripts/generate_figures.py`
- Figure module: `scylla/analysis/figures/process_metrics.py`
- Test file: `tests/unit/analysis/test_figures.py`
