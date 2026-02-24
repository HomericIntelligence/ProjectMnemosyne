---
name: "Publication Pipeline Enhancement"
description: "Publication Pipeline Enhancement"
category: evaluation
date: 2026-01-31
user-invocable: false
---
# Publication Pipeline Enhancement

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-31 |
| **Objective** | Enhance analysis pipeline to produce rigorous, publication-quality figures, tables, and statistical outputs suitable for academic papers |
| **Outcome** | ✅ Successfully implemented all 6 work packages (WP1-WP6) across 6 PRs with comprehensive test coverage |
| **Category** | Evaluation |
| **Complexity** | High - Multi-phase enhancement requiring statistical rigor, visualization design, and data pipeline architecture |

## When to Use This Skill

Use this skill when you need to:

- **Enhance existing analysis pipelines** for publication-quality output
- **Add rigorous statistical testing** to evaluation frameworks
- **Generate publication-ready visualizations** (figures, tables, LaTeX integration)
- **Remove hardcoded assumptions** and make pipelines data-driven
- **Implement comprehensive statistical workflows** (normality testing, omnibus tests, pairwise comparisons, effect sizes)
- **Export rich statistical results** for reproducible research

**Trigger patterns:**
- "Make the analysis pipeline publication-ready"
- "Add rigorous statistical testing to the evaluation framework"
- "Generate LaTeX-compatible figures and tables"
- "Remove hardcoded values from the analysis code"
- "Export comprehensive statistical results"

## Verified Workflow

### Phase 1: Statistical Foundation (WP1)

**Goal:** Add core statistical functions and update workflows to use proper statistical methodology.

**Steps:**
1. Add statistical functions to `stats.py` following thin-wrapper pattern over scipy/statsmodels:
   - `shapiro_wilk(data)` - Normality testing
   - `kruskal_wallis(*groups)` - Omnibus test
   - `mann_whitney_u(group1, group2)` - Pairwise comparison
   - `holm_bonferroni_correction(p_values)` - Step-down correction (less conservative)
   - `benjamini_hochberg_correction(p_values)` - FDR control
   - `cliffs_delta_ci(g1, g2, confidence=0.95)` - Effect size with bootstrap CI
   - `ols_regression(x, y)` - Linear regression with diagnostics

2. Add logging warnings for insufficient sample sizes (N<3 for normality, N<2 for effect sizes)

3. Update table workflows to use proper omnibus-first approach:
   - Run Kruskal-Wallis omnibus test first
   - Only proceed to pairwise comparisons if omnibus p < 0.05
   - Use Holm-Bonferroni instead of plain Bonferroni (less conservative)
   - Report omnibus result in table footer

4. Add statsmodels dependency to `pixi.toml` analysis environment

5. Write comprehensive tests (32+ tests covering edge cases, small samples, invalid inputs)

**Key insight:** Bootstrap confidence intervals using BCa (bias-corrected accelerated) method provide better coverage on small samples than normal approximation.

### Phase 2: New Tables (WP2)

**Goal:** Add descriptive, configuration, and normality test tables.

**Steps:**
1. Create `table08_summary_statistics`:
   - Descriptive stats per model (N, mean, median, Q1/Q3, std, min/max, skewness, kurtosis)
   - Covers all key metrics (score, cost, duration, tokens)

2. Create `table09_experiment_config`:
   - Derive all config from data (not hardcoded)
   - Show experiment, agent models, tiers, subtests/tier, runs/subtest, total runs, judge models

3. Create `table10_normality_tests`:
   - Shapiro-Wilk results per (model, tier, metric)
   - Justifies non-parametric test choices
   - Shows W statistic, p-value, Normal? (α=0.05)

4. Register all tables in `generate_tables.py`

5. Add smoke tests to verify generation without errors

**Key insight:** Deriving configuration from data instead of hardcoding makes the pipeline robust to schema changes.

### Phase 3: New Figures (WP3)

**Goal:** Add effect size, correlation, regression, and diagnostic visualizations.

**Steps:**
1. Create `figures/effect_size.py`:
   - `fig19_effect_size_forest()` - Horizontal dot plot with error bars
   - Shows Cliff's delta + 95% CI for each tier transition
   - Vertical dashed line at δ=0
   - Color indicates significance (CI excludes zero)

2. Create `figures/correlation.py`:
   - `fig20_metric_correlation_heatmap()` - Spearman correlation matrix
   - Annotated with coefficients
   - Faceted by model
   - `fig21_cost_quality_regression()` - Scatter + OLS line with R²

3. Create `figures/diagnostics.py`:
   - `fig23_qq_plots()` - Q-Q plots per (model, tier) with scipy.stats.probplot
   - `fig24_score_histograms()` - Histograms with KDE overlay

4. Modify `figures/cost_analysis.py`:
   - `fig22_cumulative_cost()` - Line chart of cumulative cost over runs

5. Fix Altair faceting errors by passing `data=` parameter to `alt.layer()` before faceting

6. Register all figures in `generate_figures.py`

7. Add smoke tests for each figure

**Key lesson learned:** When layering charts in Altair, faceting requires data at the top level. Use `alt.layer(..., data=df).facet()` not `alt.layer(...).facet()`.

### Phase 4: Remove Hardcoded Values (WP4)

**Goal:** Make pipeline data-driven and eliminate hardcoded assumptions.

**Steps:**
1. Centralize color palettes in `figures/__init__.py`:
   - Add `register_colors(category, mapping)` for runtime registration
   - Add `get_color_scale(category, keys)` for consistent retrieval
   - Move all hardcoded colors (phases, token_types) to central COLORS dict

2. Update all figure modules to use `get_color_scale()` instead of direct COLORS access:
   - `criteria_analysis.py` - criteria colors
   - `token_analysis.py` - token type colors
   - `subtest_detail.py` - phase colors

3. Parameterize hardcoded thresholds:
   - Add `pass_threshold=0.60` parameter to `fig04_pass_rate_by_tier()`

4. Add missing model pricing to `config/pricing.py`:
   - `claude-haiku-4-5-20241223: {"input": 1.00, "output": 5.00}` (per 1M tokens)

5. Use `derive_tier_order(df)` everywhere instead of hardcoded TIER_ORDER constant

**Key insight:** Runtime color registration allows figure generation to adapt to new models/categories without code changes.

### Phase 5: Enhanced Data Export (WP5)

**Goal:** Export comprehensive statistics and statistical test results.

**Steps:**
1. Enhance `by_model` statistics in `summary.json`:
   ```python
   {
       "median_score": float(scores.median()),
       "std_score": float(scores.std()),
       "q1_score": float(scores.quantile(0.25)),
       "q3_score": float(scores.quantile(0.75)),
       "min_score": float(scores.min()),
       "max_score": float(scores.max()),
       "total_tokens": int(model_df["total_tokens"].sum()),
       "mean_duration": float(durations.mean()),
       "n_subtests": int(model_df["subtest"].nunique()),
       "tiers": sorted(model_df["tier"].unique().tolist()),
   }
   ```

2. Add `by_tier` section with aggregate stats across all models per tier

3. Create `compute_statistical_results()` function that exports `statistical_results.json`:
   - Normality tests (Shapiro-Wilk per model/tier/metric)
   - Omnibus tests (Kruskal-Wallis per model)
   - Pairwise comparisons (Mann-Whitney U for consecutive tiers)
   - Effect sizes (Cliff's delta with CIs for tier transitions)
   - Correlations (Spearman between score, cost, tokens, duration)

4. Use `json_nan_handler()` to convert NaN/inf to None for JSON serialization

5. Add tests for export functionality (import script from `scripts/` into test path)

**Key insight:** Exporting statistical_results.json enables reproducibility - readers can verify all statistical claims.

### Phase 6: LaTeX Figure Support (WP6)

**Goal:** Generate LaTeX inclusion snippets for seamless paper integration.

**Steps:**
1. Extend `save_figure()` in `spec_builder.py`:
   - Add `latex_caption` optional parameter
   - Add `_generate_latex_snippet()` helper function
   - Only generate snippet when "pdf" in formats

2. LaTeX snippet structure:
   ```latex
   \begin{figure}[htbp]
   \centering
   \includegraphics[width=\textwidth]{name.pdf}
   \caption{Extracted from chart title or custom}
   \label{fig:name}
   \end{figure}
   ```

3. Extract caption from Altair chart:
   - Check `chart.title` (string or dict with "text" key)
   - Fall back to name-based generation if no title

4. Update orchestrator `generate_all_results.py`:
   - Document new LaTeX snippet outputs in summary
   - Show usage example: `\input{docs/figures/*_include.tex}`

5. Add tests:
   - `test_latex_snippet_generation()` - verifies structure
   - `test_latex_snippet_with_custom_caption()` - verifies customization

**Key insight:** Auto-generating LaTeX snippets reduces manual work and prevents path/label inconsistencies.

## Implementation Strategy

### Work Package Order

```
WP1 (Stats Foundation)     <- Start first, everything depends on this
    |
    v
WP4 (Hardcoded cleanup)   <- Independent, can parallel with WP2/WP3
WP2 (New Tables)          <- Depends on WP1 for normality tests
WP3 (New Figures)         <- Depends on WP1 for effect size CIs
    |
    v
WP5 (Enhanced Export)     <- Depends on WP1 for statistical results
    |
    v
WP6 (LaTeX Support)       <- Depends on WP3 for figure generation
```

### PR Strategy

Create separate PRs for each work package:
- Keeps changes focused and reviewable
- Allows parallel CI runs
- Enables incremental merging
- Each PR is self-contained and testable

**PR Template:**
```
Title: feat(analysis): <WP description> (WP<N>)

Body:
## Summary
<1-2 sentence overview>

## Changes
### 1. <Feature 1>
- Bullet points

### 2. <Feature 2>
- Bullet points

## Testing
- List test coverage

## Part of Enhancement Plan
Completes Work Package <N> from analysis pipeline enhancement plan.

Next WP: <Next WP description>
```

### Testing Strategy

**Test pyramid:**
1. Unit tests for individual functions (stats functions, table logic, color helpers)
2. Smoke tests for figure/table generation (verify no errors)
3. Integration tests for data export (verify structure and JSON validity)

**Coverage targets:**
- Stats functions: 100% (critical for correctness)
- Tables: Smoke tests (generation without errors)
- Figures: Smoke tests + structure validation
- Export: Structure validation + JSON serialization

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: Direct figure module patching in tests

**What we tried:**
Initially tried using `@patch("scylla.analysis.figures.variance.save_figure")` in individual figure tests.

**Why it failed:**
- Import path inconsistencies led to patches not applying
- Had to repeat patch decorator for every test
- Fixture-based mocking is cleaner and auto-applies

**Solution:**
Created `mock_save_figure` fixture in `conftest.py`:
```python
@pytest.fixture(scope="function")
def mock_save_figure():
    with patch("scylla.analysis.figures.spec_builder.save_figure") as mock:
        yield mock
```

### ❌ Failed: Altair layering without data parameter

**What we tried:**
```python
chart = alt.layer(zero_line, error_bars, points).facet(row="model:N")
```

**Error:**
```
ValueError: Facet charts require data to be specified at the top level
```

**Why it failed:**
Altair's faceting requires data at the layer level, not inherited from mark specs.

**Solution:**
```python
chart = alt.layer(zero_line, error_bars, points, data=effect_df).facet(row="model:N")
```

**Lesson:** When layering charts before faceting, always pass `data=` explicitly to the layer.

### ❌ Failed: Importing scripts as modules in tests

**What we tried:**
```python
from scripts.export_data import compute_statistical_results
```

**Error:**
```
ModuleNotFoundError: No module named 'scripts'
```

**Why it failed:**
`scripts/` is not a Python package (no `__init__.py`), so it's not importable.

**Solution:**
Add scripts directory to sys.path in test:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from export_data import compute_statistical_results
```

### ❌ Failed: Testing LaTeX generation with mocked save_figure

**What we tried:**
Used `mock_save_figure` fixture in `test_latex_snippet_generation()`.

**Why it failed:**
Mock intercepts `save_figure()` call, so LaTeX snippet generation never executes.

**Solution:**
Create test chart directly and call `save_figure()` without mocking:
```python
def test_latex_snippet_generation(sample_runs_df, tmp_path, clear_patches):
    chart = alt.Chart(sample_runs_df).mark_bar()...
    save_figure(chart, "test_latex_fig", tmp_path, render=True, formats=["pdf"])
    # Now verify snippet exists
```

### ⚠️ Watch Out: Ruff auto-formatting during commits

**Issue:**
Pre-commit hook modifies files after staging, requiring re-staging and re-committing.

**Pattern:**
```bash
git add -u
git commit -m "message"
# ERROR: ruff modified files
git add -u  # Re-stage ruff changes
git commit -m "message"  # Re-commit
```

**Tip:** Just let ruff fix and re-commit. Don't fight the formatter.

### ⚠️ Watch Out: Small sample size warnings

**Issue:**
Statistical functions can fail or produce meaningless results with N<3.

**Solution:**
Add explicit guards and logging:
```python
if len(data) < 3:
    logger.warning(f"Sample size too small for normality test (N={len(data)})")
    return None, None
```

## Results & Parameters

### Files Modified (16)
```
scylla/analysis/stats.py                        # WP1
scylla/analysis/tables.py                       # WP1, WP2
scylla/analysis/figures/__init__.py             # WP4
scylla/analysis/figures/criteria_analysis.py    # WP4
scylla/analysis/figures/tier_performance.py     # WP4
scylla/analysis/figures/token_analysis.py       # WP4
scylla/analysis/figures/subtest_detail.py       # WP4
scylla/analysis/figures/cost_analysis.py        # WP3
scylla/analysis/figures/spec_builder.py         # WP6
scylla/config/pricing.py                        # WP4
scripts/generate_figures.py                         # WP3
scripts/generate_tables.py                          # WP2
scripts/export_data.py                              # WP5
scripts/generate_all_results.py                     # WP6
pixi.toml                                           # WP1
tests/unit/analysis/test_stats.py                   # WP1
```

### Files Created (5)
```
scylla/analysis/figures/effect_size.py          # WP3
scylla/analysis/figures/correlation.py          # WP3
scylla/analysis/figures/diagnostics.py          # WP3
tests/unit/analysis/test_export_data.py             # WP5
tests/unit/analysis/test_figures.py (enhanced)      # WP3, WP6
```

### Pull Requests (6)
```
PR #273: WP1 - Statistical Foundation
PR #274: WP2 - New Tables (3 tables)
PR #275: WP3 - New Figures (6 figures)
PR #276: WP4 - Remove Hardcoded Values
PR #277: WP5 - Enhanced Data Export
PR #278: WP6 - LaTeX Figure Support
```

### Test Coverage Added
```
tests/unit/analysis/test_stats.py:        32 tests (normality, omnibus, pairwise, corrections, effect sizes, regression)
tests/unit/analysis/test_tables.py:       +3 tests (table08, table09, table10)
tests/unit/analysis/test_figures.py:      +6 tests (fig19-24) + 2 LaTeX tests
tests/unit/analysis/test_export_data.py:  2 tests (statistical_results, enhanced_summary)
```

### Key Dependencies Added
```toml
# pixi.toml [feature.analysis.dependencies]
statsmodels = ">=0.14"  # For OLS regression and advanced diagnostics
```

### Statistical Parameters Used
```python
# Bootstrap confidence intervals
BOOTSTRAP_ITERATIONS = 10000
CONFIDENCE_LEVEL = 0.95
METHOD = "BCa"  # Bias-corrected accelerated

# Statistical significance threshold
ALPHA = 0.05

# Multiple comparison correction
CORRECTION = "holm"  # Less conservative than Bonferroni

# Normality test
NORMALITY_TEST = "shapiro_wilk"  # For N < 50, more powerful than K-S

# Non-parametric tests
OMNIBUS_TEST = "kruskal_wallis"  # For 3+ groups
PAIRWISE_TEST = "mann_whitney_u"  # For 2 groups

# Effect size
EFFECT_SIZE = "cliffs_delta"  # Non-parametric, robust to outliers
```

### Output Formats
```
Data Exports:
- docs/data/*.csv (runs, judges, criteria, subtests)
- docs/data/summary.json (enhanced with quartiles, tokens, duration)
- docs/data/statistical_results.json (all statistical test results)

Figures:
- docs/figures/*.png (300 DPI, scale_factor=2.0)
- docs/figures/*.pdf (vector, for LaTeX)
- docs/figures/*.vl.json (Vega-Lite specs, for editing)
- docs/figures/*.csv (underlying data)
- docs/figures/*_include.tex (LaTeX inclusion snippets)

Tables:
- docs/tables/*.md (Markdown for GitHub/docs)
- docs/tables/*.tex (LaTeX for paper)
```

## Verification Commands

### Run Full Pipeline
```bash
# Generate all outputs
pixi run python scripts/generate_all_results.py \
  --data-dir ~/fullruns \
  --output-dir docs \
  --exclude test001-dryrun

# Run all analysis tests
pixi run pytest tests/unit/analysis/ -v

# Verify test coverage
pixi run pytest tests/unit/analysis/ --cov=scylla/analysis --cov-report=html
```

### Check Outputs
```bash
# Verify all expected files exist
ls docs/data/*.csv docs/data/*.json
ls docs/figures/*.{png,pdf,vl.json,csv}
ls docs/figures/*_include.tex
ls docs/tables/*.{md,tex}

# Validate JSON exports
python -m json.tool docs/data/summary.json > /dev/null
python -m json.tool docs/data/statistical_results.json > /dev/null

# Check LaTeX snippet syntax
grep -E '\\(begin|end)\{figure\}' docs/figures/*_include.tex
```

### Spot-Check Statistical Results
```bash
# View normality test results
cat docs/tables/tab10_normality_tests.md

# View tier comparison with omnibus tests
cat docs/tables/tab02_tier_comparison.md

# Inspect statistical_results.json structure
jq '.normality_tests | .[0]' docs/data/statistical_results.json
jq '.effect_sizes | .[0]' docs/data/statistical_results.json
```

## Related Skills

- `statistical-testing-patterns` - Best practices for hypothesis testing
- `altair-visualization-guide` - Altair/Vega-Lite patterns
- `pytest-fixture-patterns` - Test fixture design
- `data-driven-configuration` - Eliminating hardcoded values

## References

- Research methodology: `docs/research.md`
- Metrics definitions: `CLAUDE.md` (metrics table)
- Statistical methods: `scylla/analysis/stats.py`
- Test fixtures: `tests/unit/analysis/conftest.py`

## Success Criteria

✅ **Pipeline produces publication-quality output:**
- Figures are 300 DPI PNG + vector PDF
- Tables are formatted for both Markdown and LaTeX
- Statistical tests follow accepted methodology
- All values derived from data, not hardcoded

✅ **Statistical rigor:**
- Omnibus tests before pairwise comparisons
- Multiple comparison corrections applied
- Effect sizes reported with confidence intervals
- Normality assumptions tested and documented

✅ **Reproducibility:**
- All statistical test results exported to JSON
- Random seeds controlled (where applicable)
- Configuration derived from data
- Complete test coverage

✅ **Extensibility:**
- New figures/tables follow established patterns
- Color palettes register dynamically
- Statistical functions are thin wrappers (easy to update)
- Clear separation between data loading, analysis, and export

## Future Enhancements

**Potential improvements:**
1. Add power analysis for sample size recommendations
2. Implement Bayesian alternatives to frequentist tests
3. Add more diagnostic plots (residuals, influence plots)
4. Support for multi-level statistical models
5. Interactive visualizations (Altair → Vega-Embed)
6. Automated PDF report generation with LaTeX
7. CI/CD integration for automated figure generation on data updates
