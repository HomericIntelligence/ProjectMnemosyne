# Analysis Pipeline Code Review - Raw Session Notes

## Session Timeline

**Date**: 2026-01-31
**Duration**: ~11 hours (03:18 to 13:59)
**Total PRs**: 15 merged
**Total Issues**: 26 closed

## Original Plan Structure

Plan file: `/home/mvillmow/.claude/plans/swirling-swinging-lantern.md`

### User Decisions

1. **Krippendorff alpha**: Replace custom impl with `krippendorff` Python package
2. **Pareto fix**: Fix + add unit test with counterexample in PR 1
3. **Dead code**: Remove all 4 unused stats functions
4. **Deliverable**: Full review document + all 7 PRs

### Planned PRs (7)

1. PR 1: Critical Statistical & Algorithm Fixes (P0)
2. PR 2: Statistical Methodology Improvements (P1)
3. PR 3: Robustness & Error Handling (P1)
4. PR 4: DRY Refactoring (P2)
5. PR 5: Test Suite (P1)
6. PR 6: Cleanup + Documentation (P2-P3)
7. PR 7: Architecture Improvements (Deferred)

## Actual Execution (15 PRs)

The 7 planned PRs were broken down into 15 individual PRs for faster parallel execution:

### P0 PRs (Critical Fixes)

**PR #241** - `215-fix-krippendorff-alpha`
- Replaced 114-line custom implementation with `krippendorff` package wrapper
- Added `krippendorff` to pixi.toml and pyproject.toml
- Fixed Table 3 label from "(ordinal)" to "(interval)"
- Merged: 2026-01-31 03:18

**PR #242** - `216-fix-pareto-frontier`
- Fixed inverted Pareto frontier algorithm in cost_analysis.py:163-182
- Counterexample: A(1,0.8), B(2,0.6), C(3,0.4) should return {A}, not {C}
- Added test_pareto.py with regression test
- Merged: 2026-01-31 03:20

**PR #243** - `217-fix-fig11-crash`
- Added guard for `iloc[0]` in fig11_tier_uplift at model_comparison.py:43
- Prevents IndexError if model has no T0 data
- Merged: 2026-01-31 03:21

### P1 PRs (High Priority)

**PR #244** - `231-remove-unused-functions`
- Removed 4 unused functions: kruskal_wallis, cohens_d, intraclass_correlation, bonferroni_correction
- Note: Bonferroni was re-implemented fresh in PR #246
- Merged: 2026-01-31 03:22

**PR #245** - `219-vectorize-cliffs-delta`
- Replaced O(n²) Python loops with vectorized numpy: `np.sign(g1[:, None] - g2[None, :]).sum() / (n1 * n2)`
- Performance: ~50x speedup (~1.6M comparisons)
- Merged: 2026-01-31 03:27

**PR #246** - `218-add-bonferroni-correction`
- Re-implemented Bonferroni correction: `min(1.0, p * n_tests)`
- Applied to Table 2 (7 tests per model) and Table 4 (5 criteria)
- Documented correction in table notes
- Merged: 2026-01-31 03:31

**PR #247** - `220-bootstrap-ci-fig12`
- Replaced normal-approx CI (`mean ± 1.96*std`) with bootstrap_ci()
- Ensures consistency with other figures
- Merged: 2026-01-31 03:32

**PR #248** - `222-223-remove-dead-code`
- Removed dead DataFrame creation in table05_cost_analysis (line 595)
- Fixed dead code in generate_all_results.py (line 37): removed `check=True`, check returncode explicitly
- Merged: 2026-01-31 03:34

**PR #249** - `221-fix-hardcoded-judge-columns`
- Changed Table 3 and Fig 14 to use dynamic column names from pivot_table
- Removed hardcoded `judge_pivot.columns = [..., "judge_1", "judge_2", "judge_3"]`
- Merged: 2026-01-31 03:41

**PR #250** - `224-fix-import-time-theme`
- Moved `apply_publication_theme()` from import-time to explicit call in scripts
- Fixes test isolation issues
- Merged: 2026-01-31 03:43

**PR #251** - `225-add-error-isolation`
- Added try/except per figure/table in generation scripts
- One failure no longer kills all subsequent outputs
- Merged: 2026-01-31 03:45

**PR #254** - `226-test-suite`
- Created 7 test files under tests/unit/analysis/
- 45 tests passing (2 skipped)
- Fixtures: ~60-row sample DataFrames
- Merged: 2026-01-31 04:20

### P2 PRs (Medium Priority)

**PR #252** - `227-230-dry-refactoring`
- Added TIER_ORDER to figures/__init__.py (replaced 17 duplications)
- Added compute_consistency() to stats.py (replaced 5 duplications)
- Added compute_cop() to stats.py (replaced 6 duplications)
- Added model_color_scale() to spec_builder.py (replaced 11 duplications)
- Centralized judge model ID mapping
- Merged: 2026-01-31 03:49

**PR #253** - `232-234-cleanup-docs`
- Updated docs/analysis_pipeline.md (removed "Not Yet Implemented" for figs 11-15)
- Ran `git rm --cached` on generated files
- Removed empty renderers/ directory
- Merged: 2026-01-31 03:52

### P3 PRs (Low Priority)

**PR #255** - `fix-p3-issues`
- P3-4: Fixed figure category metadata in generate_figures.py
- P3-5: Changed bootstrap method from "percentile" to "BCa"
- P3-6: Used compute_consistency helper uniformly
- P3-7: Fixed table06 consistency calculation to prevent NaN
- P3-8: Guarded mode()[0] against IndexError
- P3-9: Sorted timestamped directories deterministically
- P3-10: Added fallback for unknown judge models
- P3-11: Made run directory parsing more robust
- Merged: 2026-01-31 13:59

## All Issues Filed

### P0 (Critical) - 6 Issues

| Issue | Title | PR |
|-------|-------|-----|
| #215 | Fix Krippendorff's alpha implementation for interval-level data | #241 |
| #216 | Fix inverted Pareto frontier algorithm | #242 |
| #217 | Fix fig11_tier_uplift crash when model has no T0 data | #243 |
| -- | Table 3 triple mismatch (covered in #215) | #241 |
| -- | Krippendorff nominal branch implements Scott's pi (covered in #215) | #241 |
| -- | Krippendorff ordinal metric uses index-based distance (covered in #215) | #241 |

### P1 (High) - 10 Issues

| Issue | Title | PR |
|-------|-------|-----|
| #218 | Add Bonferroni correction for multiple hypothesis tests | #246 |
| #219 | Vectorize Cliff's delta calculation for performance | #245 |
| #220 | Replace normal-approx CI with bootstrap in fig12_consistency | #247 |
| #221 | Fix hardcoded judge column names in Table 3 and Fig 14 | #249 |
| #222 | Remove dead code in table05_cost_analysis | #248 |
| #223 | Fix dead code in generate_all_results.py | #248 |
| #224 | Move apply_publication_theme() from import-time to explicit call | #250 |
| #225 | Add error isolation to figure and table generation scripts | #251 |
| #226 | Add unit tests for analysis pipeline | #254 |
| #231 | Remove unused stats functions | #244 |

### P2 (Medium) - 5 Issues

| Issue | Title | PR |
|-------|-------|-----|
| #227 | Eliminate tier_order duplication (17 instances) | #252 |
| #228 | Centralize consistency formula (5 duplications) | #252 |
| #229 | Centralize CoP formula (6 duplications) | #252 |
| #230 | Centralize model color scale (11 duplications) | #252 |
| -- | Unexported functions in dataframes.py (not filed) | -- |

### P3 (Low) - 11 Issues

| Issue | Title | PR |
|-------|-------|-----|
| #232 | Update stale analysis_pipeline.md documentation | #253 |
| #233 | Remove generated files from git tracking | #253 |
| #234 | Remove empty renderers directory | #253 |
| -- | P3-4: Figure category metadata (fixed in #255) | #255 |
| -- | P3-5: Bootstrap BCa method (fixed in #255) | #255 |
| -- | P3-6: Consistency clamping (fixed in #255) | #255 |
| -- | P3-7: Table06 NaN prevention (fixed in #255) | #255 |
| -- | P3-8: mode()[0] guard (fixed in #255) | #255 |
| -- | P3-9: Sorted directories (fixed in #255) | #255 |
| -- | P3-10: Judge model fallback (fixed in #255) | #255 |
| -- | P3-11: Run parsing robustness (fixed in #255) | #255 |

### META Tracking Issues (6)

| Issue | Title | Status |
|-------|-------|--------|
| #235 | [META] PR 1: Critical Statistical & Algorithm Fixes | Closed |
| #236 | [META] PR 2: Statistical Methodology Improvements | Closed |
| #237 | [META] PR 3: Robustness & Error Handling | Closed |
| #238 | [META] PR 4: DRY Refactoring | Closed |
| #239 | [META] PR 5: Test Suite | Closed |
| #240 | [META] PR 6: Cleanup & Documentation | Closed |

## Detailed P0 Bug Analysis

### Bug 1: Krippendorff's Alpha

**File**: `scylla/analysis/stats.py:184-297` (114 lines of custom code)

**Problem**:
1. `level="interval"` falls through to `else` branch (nominal)
2. Nominal branch uses exact float equality on continuous [0,1] scores
3. Two judges scoring 0.45 vs 0.46 counts as full disagreement (same as 0.0 vs 1.0)
4. Nominal branch implements Scott's pi formula, not Krippendorff's alpha
5. Ordinal branch uses index-based distance, not value-based

**Impact**: Table 3 reports incorrect alpha value AND wrong measurement level label

**Fix**: Replace with `krippendorff` package wrapper (5 lines)

**Code Before**:
```python
def krippendorff_alpha(ratings: np.ndarray, level: str = "ordinal") -> float:
    # ... 114 lines of complex custom implementation
    if level == "ordinal":
        # ... ordinal code (has bugs too)
    else:  # ← This catches "interval" and "ratio" too!
        # ... nominal code using float equality
        delta = 1 if valid[i] == valid[j] else 0  # ← Wrong for continuous data!
```

**Code After**:
```python
def krippendorff_alpha(ratings: np.ndarray, level: str = "ordinal") -> float:
    """Wrapper around krippendorff package for correct implementation."""
    return float(krippendorff.alpha(
        reliability_data=ratings,
        level_of_measurement=level
    ))
```

### Bug 2: Pareto Frontier Inverted

**File**: `scylla/analysis/figures/cost_analysis.py:163-182`

**Problem**: Algorithm removes points that DOMINATE the current point, not points DOMINATED BY it

**Counterexample**:
- A: cost=1, score=0.8 (optimal)
- B: cost=2, score=0.6 (dominated by A)
- C: cost=3, score=0.4 (dominated by A and B)
- Algorithm returns: {C} (worst point)
- Should return: {A} (best point)

**Impact**: Fig 8 Pareto frontier shows anti-optimal points

**Code Before**:
```python
# Remove points that dominate the current point
efficient = [
    p for p in efficient
    if not (p.cost <= current.cost and p.score >= current.score)
    #       ^^^^^^^^^^^^^^^^^^^^ This removes BETTER points!
]
```

**Code After**:
```python
# Remove points dominated by the current point
efficient = [
    p for p in efficient
    if not (p.cost >= current.cost and p.score <= current.score)
    #       ^^^^^^^^^^^^^^^^^^^^ This removes WORSE points
]
```

**Regression Test**:
```python
def test_pareto_frontier_counterexample():
    """Verify Pareto frontier on A(1,0.8), B(2,0.6), C(3,0.4)."""
    # ... setup temp dir with data ...
    # A dominates B and C, so only A should be on frontier
    assert len(frontier_df) == 1
    assert frontier_df.iloc[0]["cost_usd"] == 0.1
    assert frontier_df.iloc[0]["mean_score"] == 0.8
```

### Bug 3: fig11_tier_uplift Crash

**File**: `scylla/analysis/figures/model_comparison.py:43`

**Problem**: `baseline_t0 = baseline.iloc[0]` crashes with IndexError if model has no T0 data

**Impact**: Crash prevents figure generation

**Code Before**:
```python
baseline_t0 = baseline.iloc[0]  # ← IndexError if no T0!
```

**Code After**:
```python
if len(baseline) == 0:
    print(f"Warning: No T0 data for baseline model {baseline_model}")
    return
baseline_t0 = baseline.iloc[0]
```

## Test Suite Details

### conftest.py (Fixtures)

**sample_runs_df**: 60 rows (2 models × 3 tiers × 2 subtests × 5 runs)
- Simple pattern: run 1 = score 0.0, runs 2-3 = 0.5, runs 4-5 = 1.0
- Easy to verify aggregations

**sample_judges_df**: 180 rows (60 runs × 3 judges)
- Each run has 3 judges with slightly different scores

**sample_criteria_df**: 900 rows (180 judge evaluations × 5 criteria)

**sample_subtests_df**: 12 rows (pre-aggregated from runs_df)

### test_stats.py (17 tests)

**Statistical functions tested**:
- `cliffs_delta()` - 6 tests (basic, identical, negative, empty, pandas series, reference)
- `bootstrap_ci()` - 1 test (deterministic with random_state=42)
- `mann_whitney_u()` - 2 tests (basic, identical)
- `krippendorff_alpha()` - 3 tests (perfect, ordinal, nominal)
- `bonferroni_correction()` - 1 test
- `compute_consistency()` - 1 test
- `compute_cop()` - 1 test
- `spearman_correlation()` - 1 test
- `pearson_correlation()` - 1 test

### test_pareto.py (4 tests)

Uses actual `fig08_cost_quality_pareto()` with temp directories:
- Basic counterexample: A(1,0.8), B(2,0.6), C(3,0.4) → {A}
- Multiple efficient points
- Tied points (cost or score equal)
- Single point edge case

### test_dataframes.py (11 tests)

- Structure validation for all 4 DataFrames
- Aggregation (tier_summary, model_comparison)
- Consistency/CoP calculation correctness
- Empty DataFrame handling
- Filtering logic

### test_figures.py (10 tests)

- Smoke tests (fig01, fig04, fig06, fig11) with mock save_figure
- Publication theme test
- model_color_scale test
- TIER_ORDER constant
- COLORS constant
- Module structure validation

### test_tables.py (3 tests)

- Module imports
- Function signatures for all 7 table functions
- Format validation (markdown starts with `#`, LaTeX contains `\begin{table}`)
- 1 skipped: requires full DataFrame

### test_loader.py (4 tests)

- Module imports
- load_run signature
- load_all_experiments signature
- 1 skipped: requires filesystem data

## DRY Violations Fixed

### tier_order (17 duplications → 1)

**Files**:
- tables.py: 4 instances (lines 32, 150, 558, 849)
- tier_performance.py: 3 instances (30, 128, 192)
- model_comparison.py: 2 instances (29, 163)
- cost_analysis.py: 1 instance (30)
- token_analysis.py: 1 instance (29)
- variance.py: 2 instances (34, 98)
- judge_analysis.py: 1 instance (40)
- criteria_analysis.py: 1 instance (31)
- subtest_detail.py: 2 instances (27, 107)

**Fix**: Single source in `figures/__init__.py`:
```python
TIER_ORDER = ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]
```

### consistency formula (5 duplications → 1)

**Files**:
- dataframes.py: 2 instances (142, 208)
- tables.py: 2 instances (52, 761-767)
- model_comparison.py: 1 instance (188)

**Fix**: Helper in stats.py:
```python
def compute_consistency(mean: float, std: float) -> float:
    """Compute consistency: 1 - coefficient of variation, clamped to [0, 1]."""
    if mean == 0:
        return 0.0
    consistency = 1 - (std / mean)
    return max(0.0, min(1.0, consistency))
```

### CoP formula (6 duplications → 1)

**Files**:
- dataframes.py: 2 instances (149, 211)
- tables.py: 2 instances (56, 573)
- cost_analysis.py: 1 instance (43)
- tables.py: 1 instance (732-735)

**Fix**: Helper in stats.py:
```python
def compute_cop(mean_cost: float, pass_rate: float) -> float:
    """Compute Cost-of-Pass: mean_cost / pass_rate (inf if pass_rate=0)."""
    if pass_rate == 0:
        return float("inf")
    return mean_cost / pass_rate
```

### model_color_scale (11 duplications → 1)

**Files**:
- tier_performance.py: 2 instances (67, 213)
- variance.py: 1 instance (43)
- model_comparison.py: 4 instances (106, 132, 229, 253)
- cost_analysis.py: 4 instances (90, 122, 208, 254)

**Fix**: Helper in spec_builder.py:
```python
def model_color_scale():
    """Create model color scale for consistency."""
    return alt.Scale(
        domain=["Sonnet 4.5", "Haiku 4.5"],
        range=[COLORS["models"]["Sonnet 4.5"], COLORS["models"]["Haiku 4.5"]]
    )
```

## Commands Used

### Issue Creation
```bash
gh issue create \
  --title "Fix Krippendorff's alpha implementation" \
  --body "..." \
  --label "analysis"
```

### PR Workflow (Parallel)
```bash
# Create branch
git checkout -b 215-fix-krippendorff-alpha

# Make changes
# ... edit files ...

# Commit
git add -A
git commit -m "fix(analysis): Replace custom Krippendorff alpha with package

Fixes #215

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push
git push -u origin 215-fix-krippendorff-alpha

# Create PR
gh pr create \
  --issue 215 \
  --body "Closes #215"

# Enable auto-merge
gh pr merge --auto --rebase

# Switch back to main for next PR
git checkout main
```

### Testing
```bash
# Run analysis tests
pixi run -e analysis pytest tests/unit/analysis/ -v

# Run all tests
pixi run test

# Run pre-commit hooks
pre-commit run --all-files
```

### Verification
```bash
# Regenerate all outputs
pixi run -e analysis python scripts/generate_all_results.py

# Check git status
git status
```

## Lessons Learned

1. **Phased PRs > Mega-PRs**: 15 small PRs merged faster than 1 large PR would have
2. **Parallel execution**: Auto-merge + CI allowed parallel PR merging
3. **Fixtures over production data**: 60-row fixtures are faster and easier to debug than 2,238-row production data
4. **Use authoritative packages**: Don't implement statistical functions from scratch
5. **Extract helpers immediately**: Even "simple" formulas like consistency should be helpers
6. **Test with counterexamples**: Algorithm bugs need regression tests with known-wrong inputs
7. **Error isolation**: try/except per item in generation loops prevents cascade failures
8. **Dynamic over hardcoded**: Use actual data shape instead of hardcoded assumptions

## Deferred Work (PR 7)

**Branch**: `refactor-analysis-architecture` (not created)
**Priority**: P2-P3 (post-publication)

**Scope**:
1. `DualFormatTable` helper class to eliminate ~300 lines of boilerplate
2. Shared data loading across scripts (load once, pass to operations)
3. Plugin-based figure registration pattern

**Rationale**: Large refactors with high risk, better done post-publication

## Final State

**Current branch**: `main` (all PRs merged)
**Test status**: 45 passing, 2 skipped
**Documentation**: Updated and accurate
**Code quality**: All DRY violations fixed, dead code removed
**Statistical correctness**: All P0 bugs fixed, methodology validated

**Ready for**: Publication, production use
