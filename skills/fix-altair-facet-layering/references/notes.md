# Fix Altair Facet Layering - Detailed Session Notes

## Session Context

**Date**: 2026-02-08
**Issue**: #322 - Analysis figure generation bugs + PNG/PDF rendering
**Duration**: ~2 hours implementation
**Outcome**: All 27 figures generate correctly with proper domains and visible overlays

## Problem Breakdown

### Original Plan (from issue #322)

```
Phase 1: Core Infrastructure (spec_builder.py)
- Fix rounding 0.1→0.05
- Add compute_dynamic_domain_with_ci()
- Remove CSV from save_figure()
- Format JSON with indentation

Phase 2: Critical Domain Fixes
- fig11: hardcoded [-0.1, 0.1] → dynamic
- fig21: regression line clipping
- fig04, fig12, fig25: CI clipping

Phase 3: Invisible Overlay Layers
- fig23: Q-Q reference line
- fig24: KDE overlay + scaling
- fig19: zero line (multi-model)

Phase 4: Static Domain Fixes
- fig16, fig17: static [0, 0.3] domains

Phase 5: Render PNG/PDF
```

## Detailed Implementation Log

### Phase 1: Core Infrastructure ✅

**spec_builder.py changes**:
1. Fixed rounding: `0.1` → `0.05` (lines 67-69)
2. Added `compute_dynamic_domain_with_ci()` function
3. Removed CSV output from `save_figure()` (removed lines 164-172)
4. Added JSON formatting with `json.dumps(indent=2)` (line 162)
5. Removed `data` parameter from function signature

**Ripple effects**: Updated 26 `save_figure()` calls across 13 figure modules

### Phase 2: Critical Domain Fixes ✅

**fig11 (model_comparison.py:120-124)**:
```python
# Before: scale=alt.Scale(domain=[-0.1, 0.1])
# After: scale=alt.Scale(domain=compute_dynamic_domain(uplift_df["uplift"], floor=-1.0, ceiling=1.0))
```

**fig21 (correlation.py:192-199)**:
```python
# Added regression Y-values to domain computation
reg_line_rows = reg_df[reg_df["type"] == "regression_line"]
all_y = pd.concat([subtest_stats["mean_score"], reg_line_rows["y"].dropna()])
score_domain = compute_dynamic_domain(all_y)
```

**fig21 multi-model (correlation.py:264-271)**:
```python
# Before: alt.layer(scatter, regression_lines, annotations, data=subtest_stats)
# After: alt.layer(scatter, regression_lines, annotations).facet(..., data=subtest_stats)
```

**fig04, fig12, fig25 CI fixes**:
- tier_performance.py:73 → `compute_dynamic_domain_with_ci()`
- model_comparison.py:249 → `compute_dynamic_domain_with_ci()`
- impl_rate_analysis.py:78 → `compute_dynamic_domain_with_ci()`

### Phase 3: Invisible Overlay Layers ✅

**fig23 Q-Q plots (diagnostics.py:101-129)**:
```python
# Before: Simple reference line with generic x, y columns
reference_line = alt.Chart(pd.DataFrame({"x": [q_min, q_max], "y": [q_min, q_max]}))...
chart = alt.layer(reference_line, scatter, data=qq_df).facet(...)  # ❌ FAILS

# After: Reference line data includes facet columns
ref_rows = []
for model in sorted(runs_df["agent_model"].unique()):
    for tier in tier_order:
        ref_rows.append({"agent_model": model, "tier": tier, "theoretical_quantile": q_min, "observed_quantile": q_min})
        ref_rows.append({"agent_model": model, "tier": tier, "theoretical_quantile": q_max, "observed_quantile": q_max})
ref_df = pd.DataFrame(ref_rows)

reference_line = alt.Chart(ref_df).mark_line().encode(x="theoretical_quantile:Q", y="observed_quantile:Q")
chart = alt.layer(reference_line, scatter).facet(..., data=qq_df)  # ✅ WORKS
```

**fig24 KDE overlay (diagnostics.py:195-232)**:

Bug 1 - Invisible KDE:
```python
# Before: (histogram + kde_lines).facet(...)  # ❌ FAILS
# After: alt.layer(histogram, kde_lines).facet(..., data=runs_df)  # ✅ WORKS
```

Bug 2 - Wrong KDE scaling:
```python
# Before: Global scaling
kde_df["scaled_density"] = kde_df["density"] * (max_count / kde_df["density"].max())

# After: Per-group scaling
for (model, tier), group_idx in kde_df.groupby(["agent_model", "tier"]).groups.items():
    group_mask = (kde_df["agent_model"] == model) & (kde_df["tier"] == tier)
    group_density_max = kde_df.loc[group_mask, "density"].max()
    tier_count = len(runs_df[(runs_df["agent_model"] == model) & (runs_df["tier"] == tier)])
    if group_density_max > 0:
        kde_df.loc[group_mask, "scaled_density"] = kde_df.loc[group_mask, "density"] * (tier_count / group_density_max)
```

**fig19 effect size (effect_size.py:118-144)**:
```python
# Multi-model path: Build zero line data with facet column
if effect_df["agent_model"].nunique() > 1:
    zero_data = pd.DataFrame([{"agent_model": m, "x": 0} for m in effect_df["agent_model"].unique()])
    zero_line = alt.Chart(zero_data).mark_rule().encode(x="x:Q")
    chart = alt.layer(zero_line, error_bars, points).facet(..., data=effect_df)
```

### Phase 4: Static Domain Fixes ✅

**fig16 Panel B (variance.py:201-211)**:
```python
# Before: scale=alt.Scale(scheme="plasma", domain=[0, 0.3])
# After:
std_max = max(0.3, float(variance_df["score_std"].max()) * 1.1)
scale=alt.Scale(scheme="plasma", domain=[0, round(std_max / 0.05) * 0.05])
```

**fig17 Panel B (judge_analysis.py:241-250)**:
```python
# Before: scale=alt.Scale(domain=[0, 0.3])
# After:
std_max = max(0.3, float(std_data["score_std"].max()) * 1.1)
scale=alt.Scale(domain=[0, round(std_max / 0.05) * 0.05])
```

### Phase 5: Test Cleanup ✅

**Removed CSV assertions**:
```bash
sed -i '/assert (tmp_path \/ "fig.*\.csv")\.exists()/d' tests/unit/analysis/test_figures.py
```

**Removed content verification tests**:
- Attempted regex removal → left broken bodies
- Manual cleanup with awk → worked
- Added `import pytest` at top
- Fixed LaTeX snippet test (removed `data` parameter)

**Final test results**:
- 71 tests → 45 tests (26 CSV tests removed)
- 0 failures
- All figure generation tests passing

## Error Patterns Encountered

### Error 1: "Facet charts require data to be specified at the top level"

**Trigger**: Using `+` operator with charts from different data sources
```python
chart1 = alt.Chart(df1).mark_line()...
chart2 = alt.Chart(df2).mark_circle()...
(chart1 + chart2).facet(...)  # ❌ FAILS
```

**Solution**: Use `alt.layer()` with explicit data
```python
alt.layer(chart1, chart2).facet(..., data=df1)  # ✅ WORKS
```

### Error 2: Invisible overlay layers

**Trigger**: Data override in faceting
```python
# scatter uses columns from qq_df
# reference_line uses columns from ref_df (different structure)
alt.layer(reference_line, scatter, data=qq_df).facet(...)  # reference_line invisible
```

**Solution**: Include facet columns in overlay data
```python
# Build ref_df with same facet columns as qq_df
ref_df = pd.DataFrame([
    {"agent_model": m, "tier": t, "x": x_min, "y": y_min}
    for m in models for t in tiers
])
```

### Error 3: Data clipped outside bounds

**Trigger**: Domain computed from incomplete data
```python
# Only uses means, ignores CI bounds
domain = compute_dynamic_domain(df["mean_value"])
# Result: CI whiskers extend beyond chart
```

**Solution**: Include all rendered data
```python
domain = compute_dynamic_domain_with_ci(df["mean_value"], df["ci_low"], df["ci_high"])
```

## Key Insights

1. **Altair `+` vs `alt.layer()`**:
   - `+` is syntactic sugar that works ONLY when charts share data structure
   - `alt.layer()` is more explicit and required when data differs
   - Always use `alt.layer()` with `.facet(data=...)`

2. **Faceting requirements**:
   - ALL layers must have data with facet columns
   - Can't mix faceted and non-faceted data
   - Reference lines/overlays need dummy rows for each facet

3. **Domain computation**:
   - Must include ALL marks that will render (points, error bars, lines, etc.)
   - Common mistake: computing domain from centers only, ignoring error bars
   - Use padding to avoid marks touching axis bounds

4. **Per-group operations in faceted charts**:
   - Normalization/scaling must happen per facet group
   - Global operations create misleading relative scales
   - Always group by facet variables before computing statistics

## Performance Notes

- No performance issues observed
- All 27 figures generate in < 5 seconds total
- PNG rendering (300 DPI) adds ~2-3 seconds per figure
- PDF rendering negligible additional time

## Future Considerations

1. **Vega-Lite v6 migration**: Current code uses some deprecated Altair 5.5 patterns (theme registration warning)
2. **Dynamic figure selection**: Could optimize to only regenerate changed figures
3. **Parallel rendering**: Could render PNG/PDF in parallel for speed
4. **JSON spec validation**: Could add schema validation for .vl.json files

## Tools Used

- Python 3.14.2
- Altair 5.5+ (Vega-Lite wrapper)
- pytest 9.0.2
- pandas for data manipulation
- vl-convert-python for PNG/PDF rendering

## Related Issues

- #322: This implementation
- Future: Add figure diff tool to compare rendered outputs

## Lessons Learned

1. Read Altair docs carefully - `+` and `alt.layer()` are NOT equivalent
2. Always include facet columns in overlay data
3. Test with actual data - synthetic test data may not expose domain issues
4. Regex for test file modification is fragile - use Python AST or manual cleanup
5. Per-group operations matter in faceted visualizations
