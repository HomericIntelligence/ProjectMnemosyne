# Raw Notes: LaTeX Paper Peer Review Session

## Session Context

- **Date**: 2026-02-22
- **Paper**: "Navigating Scylla with Haiku: Multi-Task Evaluation of Agentic Coding Architectures Using a Budget Frontier Model"
- **Repository**: ProjectScylla, branch `1048-haiku-analysis-paper`
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1060
- **Paper path**: `docs/arxiv/haiku/paper.tex` (~940 lines after edits)
- **Pipeline**: `scripts/export_data.py` → `docs/arxiv/haiku/data/statistical_results.json`

## Review Verdict

**Major Revision** — 7 critical issues (none fatal), 8 minor issues, all resolved in one session.

## Files Modified

| File | Change Type |
|------|------------|
| `docs/arxiv/haiku/paper.tex` | All text fixes (Issues 1, 4, 5, 6, 7, minors) |
| `scripts/export_data.py` | T0→T6 in pairwise family, power analysis integration |
| `scylla/analysis/stats.py` | Cliff's delta docstring clarification |
| `docs/arxiv/haiku/data/statistical_results.json` | Regenerated (power_analysis + T0→T6) |
| `docs/arxiv/haiku/data/summary.json` | Regenerated (same data, trailing newline fix) |
| `docs/arxiv/haiku/paper.pdf` | Rebuilt (18 pages, ~742KB, 4 figures now included) |

## Issue Detail: Holm-Bonferroni Family Size (Issue 2)

- `export_data.py` loop: `for i in range(len(tier_order) - 1)` → only 6 pairs
- `comparison.py` lines 143–168: explicitly adds T0→T6 before Holm-Bonferroni
- Paper Table 10 showed 7 rows
- Fix: append T0→T6 test to `raw_p_values` BEFORE calling `holm_bonferroni_correction()`
- Verified: `statistical_results.json` now has T0→T6 entry with `p_value=0.1187` matching paper

## Issue Detail: Power Analysis (Issue 3)

Functions `mann_whitney_power()` (lines 141–197) and `kruskal_wallis_power()` (lines 200–252)
in `stats.py` were simulation-based (10,000 iterations, seed=42) — already implemented but
never called from `export_data.py`.

Key discovery: with aggregated tier-level N (not per-subtest N=5), T0–T4 transitions are
actually well-powered for medium effects (0.95–0.98). The "underpowered" concern mainly
applies to T5→T6 (n=30 vs n=15), where power at medium effect is only 0.37.

## Issue Detail: fullruns Directory Structure (Failed Attempt)

Tried `--data-dir ~/fullruns/haiku` — failed because structure was:
```
~/fullruns/haiku/
  2026-02-21T17-07-31-test-002/  ← timestamped directly at top level
```

The loader `load_all_experiments()` expects:
```
<data-dir>/
  <exp-name>/         ← named directory iterates here
    <timestamp>/      ← then finds latest timestamped subdir
```

Correct path was `~/fullruns/haiku-analysis/` which had `test-002/`, `test-007/`, etc.

## Issue Detail: Pre-commit Double-Stage

The `end-of-file-fixer` hook modifies JSON files to add a trailing newline.
When the hook modifies staged files, the commit is aborted.
Must run `git add <modified-json-files>` and commit again.

This happened because `export_data.py`'s JSON serialization doesn't add a trailing newline:
```python
json.dump(results, f, indent=2, default=json_nan_handler)
# Missing: f.write('\n')
```

## Statistical Results Summary (from regenerated JSON)

### Pairwise Comparisons (pass_rate, Holm-Bonferroni, m=7)

| Transition | N1, N2 | Raw p | Corrected p | Significant |
|------------|--------|-------|-------------|-------------|
| T0→T1 | 117, 83 | 0.162 | 0.487 | No |
| T1→T2 | 83, 130 | 0.093 | 0.373 | No |
| T2→T3 | 130, 122 | 0.178 | 0.487 | No |
| T3→T4 | 122, 123 | 0.334 | 0.487 | No |
| T4→T5 | 123, 30 | 0.0004 | 0.0024 | **Yes** |
| T5→T6 | 30, 15 | 0.0049 | 0.0243 | **Yes** |
| T0→T6 | 117, 15 | 0.0237 | 0.1187 | No |

### Aggregate Pass Rates (verified against paper Table 7)

| Tier | N | Pass Rate | 95% CI |
|------|---|-----------|--------|
| T0 | 117 | 0.641 | (0.547, 0.726) |
| T1 | 83 | 0.735 | (0.639, 0.819) |
| T2 | 130 | 0.831 | (0.754, 0.892) |
| T3 | 122 | 0.762 | (0.680, 0.836) |
| T4 | 123 | 0.813 | (0.732, 0.878) |
| T5 | 30 | 0.500 | (0.333, 0.667) |
| T6 | 15 | 0.933 | (0.667, 1.000) |

## Figures Included in Paper

| Figure | Filename | Caption |
|--------|----------|---------|
| fig04 | `fig04_pass_rate_by_tier.png` | Pass rate by tier (aggregate, 95% CI) |
| fig08 | `fig08_cost_quality_pareto.png` | Cost-quality Pareto front |
| fig01 | `fig01_score_variance_by_tier.png` | Score distribution by tier |
| fig19 | `fig19_effect_size_forest.png` | Effect size forest plot (Cliff's δ with 95% CI) |

## Test Results

- 316 unit tests passed (full `tests/unit/analysis/` suite, 547s runtime)
- 41 analysis-only tests pass in 3.71s
- 0 LaTeX errors (`grep -c "^!" paper.log`)
- All pre-commit hooks pass (ruff, mypy, ruff-format, end-of-file-fixer)
