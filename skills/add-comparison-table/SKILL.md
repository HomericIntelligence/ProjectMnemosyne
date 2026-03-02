---
name: add-comparison-table
description: "TRIGGER CONDITIONS: Adding a new pairwise statistical comparison table to scylla/analysis/tables/comparison.py. Use when a new metric (e.g. CFP, R_Prog, impl_rate) needs tier-by-tier Kruskal-Wallis + Mann-Whitney U + Holm-Bonferroni comparison in both Markdown and LaTeX formats."
user-invocable: false
category: analysis
date: 2026-03-02
---

# add-comparison-table

How to add a new pairwise comparison table to `scylla/analysis/tables/comparison.py`, reusing the existing `_generate_pairwise_comparison()` helper, with a column-existence guard, dual-format output, and 4 focused unit tests.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Add `table_cfp_comparison()` for CFP and R_Prog across tiers (research.md §6.3) |
| Outcome | Success — 4 new tests, 39 tables tests total, 3589 total passing, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1187 |
| PR | HomericIntelligence/ProjectScylla#1298 |

## When to Use

- Adding a new metric comparison table using the Kruskal-Wallis → pairwise Mann-Whitney U → Holm-Bonferroni pipeline
- The metric column already exists in `runs_df` (from `build_runs_df()`)
- The table should produce both Markdown and LaTeX output
- The new table function should mirror `table02_tier_comparison` or `table02b_impl_rate_comparison`

## Architecture: tables/comparison.py structure

```
_generate_pairwise_comparison()    ← private helper, reused by all comparison tables
    |
    ├── table02_tier_comparison()          metric_column="passed"
    ├── table02b_impl_rate_comparison()    metric_column="impl_rate"
    └── table_cfp_comparison()             metric_column="cfp" + "r_prog"
```

The helper runs the full statistical pipeline and returns `(markdown, latex)`. New comparison tables are thin wrappers that supply `metric_column`, `metric_name`, `table_title`, and `table_label`.

## Verified Workflow

### Step 1: Confirm the metric column is already in runs_df

Check `scylla/analysis/dataframes.py` `build_runs_df()` to verify the column exists. If not, add it there first (see `add-analysis-metric` skill).

### Step 2: Add the table function to comparison.py

Insert after the last existing comparison function (before `__all__`):

```python
def table_<metric>_comparison(runs_df: pd.DataFrame) -> tuple[str, str]:
    """Compare <Metric> across tiers.

    Uses the same Kruskal-Wallis → pairwise Mann-Whitney U → Holm-Bonferroni
    pipeline as table02_tier_comparison.

    Args:
        runs_df: Runs DataFrame (requires '<metric>' column).

    Returns:
        Tuple of (markdown_table, latex_table).

    """
    if "<metric>" not in runs_df.columns:
        return (
            "*(CFP data not yet collected)*",
            "% CFP data not yet collected",
        )

    return _generate_pairwise_comparison(
        runs_df,
        metric_column="<metric>",
        metric_name="<MetricDisplayName>",
        table_title="<Table Title>",
        table_label="<latex_label>",
    )
```

**For two related metrics** (e.g. CFP + R_Prog together), call `_generate_pairwise_comparison` twice and concatenate:

```python
cfp_md, cfp_latex = _generate_pairwise_comparison(runs_df, metric_column="cfp", ...)
r_md, r_latex = _generate_pairwise_comparison(runs_df, metric_column="r_prog", ...)
return (cfp_md + "\n\n" + r_md, cfp_latex + "\n\n" + r_latex)
```

### Step 3: Add to __all__ in comparison.py

```python
__all__ = [
    "table02_tier_comparison",
    "table02b_impl_rate_comparison",
    "table04_criteria_performance",
    "table06_model_comparison",
    "table_<metric>_comparison",   # ← add here
]
```

### Step 4: Export from tables/__init__.py

In `scylla/analysis/tables/__init__.py`:

```python
from scylla.analysis.tables.comparison import (
    table02_tier_comparison,
    table02b_impl_rate_comparison,
    table04_criteria_performance,
    table06_model_comparison,
    table_<metric>_comparison,     # ← add import
)
```

And add to `__all__`:

```python
"table_<metric>_comparison",       # ← add to __all__
```

### Step 5: Write 4 unit tests in test_tables.py

```python
def test_table_<metric>_comparison_format(sample_runs_df):
    """Smoke test: returns (str, str), non-empty, metric name in markdown."""
    from scylla.analysis.tables import table_<metric>_comparison
    markdown, latex = table_<metric>_comparison(sample_runs_df)
    assert isinstance(markdown, str) and isinstance(latex, str)
    assert len(markdown) > 0 and len(latex) > 0
    assert "<MetricDisplayName>" in markdown
    assert "tabular" in latex or "table" in latex.lower()


def test_table_<metric>_comparison_missing_column():
    """Returns placeholder when metric column absent — no exception raised."""
    import pandas as pd
    from scylla.analysis.tables import table_<metric>_comparison
    df = pd.DataFrame({"agent_model": ["M"] * 3, "tier": ["T0"] * 3, "score": [0.5] * 3})
    markdown, latex = table_<metric>_comparison(df)
    assert isinstance(markdown, str) and len(markdown) > 0
    assert isinstance(latex, str) and len(latex) > 0


def test_table_<metric>_comparison_all_nan(sample_runs_df):
    """Completes without error when all values are NaN."""
    from scylla.analysis.tables import table_<metric>_comparison
    df = sample_runs_df.copy()
    df["<metric>"] = float("nan")
    markdown, latex = table_<metric>_comparison(df)
    assert isinstance(markdown, str) and isinstance(latex, str)


def test_table_<metric>_comparison_statistical_workflow(sample_runs_df):
    """Kruskal-Wallis, Mann-Whitney, Holm-Bonferroni documented in output."""
    from scylla.analysis.tables import table_<metric>_comparison
    markdown, latex = table_<metric>_comparison(sample_runs_df)
    assert "Kruskal-Wallis" in markdown
    assert "Mann-Whitney" in markdown
    assert "Holm-Bonferroni" in markdown
```

Also update `test_table_function_signatures()` to include the new function name in `table_functions`.

### Step 6: Verify

```bash
# Targeted (fast feedback)
pixi run python -m pytest tests/unit/analysis/test_tables.py -v -k "<metric>"

# Full tables suite
pixi run python -m pytest tests/unit/analysis/test_tables.py -v

# Pre-commit
pre-commit run --all-files
```

Expected: all hooks pass; ruff may auto-fix minor style issues on first run — run a second time to confirm.

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Using backslash in metric_name inside f-string | SyntaxError in Python <3.12 | Use a variable: `name = "R\\_Prog"` then pass `metric_name=name`, or use a raw string approach |
| Putting `table_cfp_comparison` in `__all__` of `__init__.py` in the wrong position | No functional failure, but broke logical grouping (comparison vs detail tables) | Place new comparison table entries in the "Comparison tables" section of `__all__`, not the "Detail tables" section |

## Results & Parameters

### NaN handling

The `_generate_pairwise_comparison()` helper already calls `.dropna()` on each tier group. No additional NaN logic is needed in the wrapper — all-NaN groups simply produce zero valid groups and the statistical tests are skipped gracefully.

### Column guard pattern

```python
if "cfp" not in runs_df.columns:
    return (
        "*(CFP data not yet collected)*",
        "% CFP data not yet collected",
    )
```

Use the markdown placeholder `*(data not yet collected)*` and a LaTeX comment `% data not yet collected` — these parse cleanly downstream without breaking table rendering.

### conftest.py mock_power_simulations fixture

The `autouse=True` fixture in `tests/unit/analysis/conftest.py` mocks `mann_whitney_power` (→ `0.8`) and `kruskal_wallis_power` (→ `0.75`) in **both** `scylla.analysis.stats` and `scylla.analysis.tables.comparison`. New comparison table functions automatically benefit from this mock since they call through `_generate_pairwise_comparison` which uses the already-patched symbols.

### test count delta

4 new tests added to `test_tables.py`; total tables tests: 35 → 39.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1187, PR #1298 | Branch: `1187-auto-impl` |

## References

- Prerequisite skill: `add-analysis-metric` (HomericIntelligence/ProjectMnemosyne)
- Production file: `scylla/analysis/tables/comparison.py`
- Test file: `tests/unit/analysis/test_tables.py`
- Fixture file: `tests/unit/analysis/conftest.py`
