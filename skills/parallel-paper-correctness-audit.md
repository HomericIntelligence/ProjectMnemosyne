---
name: parallel-paper-correctness-audit
description: Multi-agent parallel workflow for verifying every numerical claim in a research paper against underlying data files (CSV, JSON), fixing errors, and ensuring internal consistency across inline tables, generated tables, and figure data
category: documentation
date: 2026-04-26
version: 1.1.0
user-invocable: false
tags: [latex, paper, audit, verification, cross-reference, numerical-accuracy, parallel-agents, inline-tables, aggregation-mismatch, pandas, data-pipeline]
---
# Parallel Paper Correctness Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 |
| **Objective** | Verify every numerical claim in a LaTeX research paper against its underlying data files, fix errors, and ensure internal consistency using parallel agent teams |
| **Outcome** | Found and fixed 12 issues across 3 audit passes: 1 false universality claim (13/14 not 14/14), stale inline table values (34% cost error), consistency metric aggregation mismatch (0.23 delta), pandas None-to-NaN bug (systematic: 12 instances in 3 files), impl_rate > 1.0 from over-scoring judge, variable criteria counts undisclosed, wrong missing-judges count, p-value precision inconsistency, best-CoP tier mislabel (T1->T2), tab03 nan values, p-value precision inconsistency across sections |
| **Models Used** | Opus 4.6 (1M context) |
| **Scale** | ~2,400-line LaTeX paper, 3 experiments, 7 tiers, 1,080 runs, 120 subtests |

## When to Use This Skill

Use this workflow when:

- A research paper presents results from a data pipeline and you need to verify ALL numbers match
- The paper has both auto-generated tables (from scripts) AND hand-written inline tables in LaTeX
- Multiple aggregation levels exist (per-run, per-subtest, per-tier, per-experiment) and tables/figures may compute the same metric at different levels
- The paper has undergone prior review rounds and you suspect stale values from earlier data versions
- You need to verify statistical claims (normality tests, effect sizes, test statistics) against raw data
- The paper contains universality claims ("all X", "every Y", "no Z") that could be falsified by a single exception

**Trigger phrases**: "verify all numbers", "correctness audit", "cross-reference paper against data", "check inline tables", "second-pass audit", "third-pass audit", "grep for nan"

**Distinguishing from related skills**:
- `academic-paper-validation` covers the full paper lifecycle (tone, cross-refs, LaTeX, statistics, arXiv build). Use that for initial review.
- `paper-iterative-accuracy-review` covers second-pass review after targeted fixes. Use that for reviewing your own prior fixes.
- `statistical-claim-verification` covers statistical methodology correctness. Use that for test selection and effect size verification.
- **This skill** covers exhaustive numerical cross-referencing with parallel agents. Use when you need to verify every number in the paper, not just methodology.

## Verified Workflow

### Phase 1: Parallel Data Exploration (3 Agents)

Deploy 3 agents simultaneously, each reading different data sources:

**Agent 1 — Paper + Data Files**:
1. Read the full `paper.tex`
2. Read all data files: `summary.json`, `statistical_results.json`, all table `.md`/`.tex` files
3. Build a verification table: every numeric claim mapped to its data source and expected value

**Agent 2 — Figures + Embedded Data**:
1. Read all figure Vega-Lite JSON specs (`.vl.json`) and associated CSVs
2. Extract embedded data values from figure specs
3. Cross-reference figure annotations against paper claims

**Agent 3 — Source Code**:
1. Read metrics, analysis, and reporting modules
2. Understand how numbers are derived (aggregation methods, rounding, edge cases)
3. Identify any computation that could produce surprising results (e.g., impl_rate > 1.0)

### Phase 2: Cross-Reference Verification

Build systematic verification tables comparing paper claims vs data file values for each category:

```markdown
| Category | Paper Claim | Data Value | Source File | Match? |
|----------|-------------|------------|-------------|--------|
| T0 pass rate | 0.42 | 0.42 | summary.json | YES |
| T6 cost | $0.070 | $0.106 | runs.csv | NO (34%) |
```

Cover these categories:
- Pass rates, scores, standard deviations
- Sample sizes (N runs, N subtests, N judges)
- Statistical test results (SRH, KW, Shapiro-Wilk statistics and p-values)
- Inter-rater reliability metrics
- Cost analysis (per-run, per-tier, total)
- Normality test results

**Independent computation**: Use pandas to independently compute per-experiment per-tier aggregates from `runs.csv` and compare against inline tables:

```python
import pandas as pd

df = pd.read_csv('runs.csv')
# Compute per-tier aggregates independently
tier_stats = df.groupby('tier').agg(
    mean_score=('score', 'mean'),
    mean_cost=('cost_usd', 'mean'),
    n_runs=('score', 'count')
)
# Compare against paper's inline tables
```

### Phase 3: Fix Application

Apply fixes in this priority order:

1. **Source code bugs** — Fix root causes in pipeline code (e.g., `summary.py`). Use `pd.notna()` instead of `is not None` for DataFrame values.
2. **Generated output files** — Fix both `.tex` and `.md` table files for immediate correctness
3. **Paper text** — Fix factual errors in `paper.tex`
4. **Add disclosures** — Document anomalies (e.g., impl_rate > 1.0) with footnotes providing full trace

### Phase 4: Second-Pass Audit (3 More Agents)

Deploy a fresh set of agents to catch issues the first pass missed:

**Agent 1 — Inline Table Verification**:
- Compare every inline table in the LaTeX body against raw CSV data
- Focus specifically on inline tables (hand-written in LaTeX) that may not have been regenerated

**Agent 2 — Cross-Reference Integrity**:
- Check all LaTeX cross-references, citations, figure file references, table inputs
- Verify `\ref{}`, `\input{}`, `\includegraphics{}` all resolve

**Agent 3 — Deep Statistical Claims**:
- Verify degrees of freedom, missing data counts, criteria variability descriptions
- Check universality claims ("all X reject Y") against every individual case

### Phase 5: Third-Pass Audit (Systematic Patterns)

Deploy after first and second passes are complete. Third-pass targets systematic code bugs and precision issues that earlier passes miss:

**Agent 1 — Best-Value Verification**:
- For every "best tier" claim, compare ALL tiers at full precision (not rounded)
- When tiers tie at rounded precision, verify which actually wins at full precision
- Check that table generation code does not pick alphabetically when values round equally

**Agent 2 — Systematic Code Bug Scan**:
- Grep ALL table generation files for `is not None` — replace with `pd.notna()`
- Grep ALL generated output files for literal "nan" (not just files referenced in paper)
- Check every file that reads DataFrame rows, not just the ones that produced visible bugs

**Agent 3 — Precision Consistency**:
- Grep for ALL occurrences of each reported statistic (p-values, test statistics)
- Verify uniform precision across all sections (body, appendix, tables)
- After fixing any number, search for all other occurrences to update them consistently

## Common Error Patterns

### Pattern 1: Stale Inline Tables

**Generated tables** (tab01-tab11) are regenerated by the pipeline and tend to be correct. **Inline tables** (hand-written in LaTeX body) are often stale from a prior data version.

**Detection**: Compare inline table values against `runs.csv` aggregates. Look for systematic offsets (all values differ by a consistent amount = old data version).

**Fix**: Recompute from current data and update inline tables.

### Pattern 2: Aggregation Method Mismatch

The same metric name (e.g., "consistency") can be computed at different levels:
- **Pooled tier-level**: `1 - CV` over all runs in a tier (used in tables)
- **Per-subtest mean**: Mean of per-subtest `1 - CV` values (used in figures)

These can differ substantially (observed delta: 0.23 for T0).

**Detection**: When a table value and figure value for the same metric disagree, check whether they use different aggregation methods.

**Fix**: Clarify the computation method in the paper text. Add a footnote explaining which aggregation is used where.

### Pattern 3: False Universality Claims

Claims like "all 14 distributions reject normality" are fragile. A single exception (e.g., T6 Cost with n=9, p=0.069 > 0.05) invalidates the universality.

**Detection**: For every "all X" claim, check every individual case. Pay special attention to:
- Small-N tiers (T5, T6) where tests have lower power
- Edge cases near significance thresholds

**Fix**: Change "all 14" to "13 of 14" with a footnote identifying the exception.

### Pattern 4: pandas None-to-NaN Conversion

When pipeline code uses `is not None` to check DataFrame values, it silently passes NaN through (since `float('nan') is not None` is True).

**Detection**: Search for `is not None` in pipeline code that processes DataFrame columns.

**Fix**: Replace with `pd.notna(value)` which correctly handles both None and NaN.

```python
# WRONG — NaN passes this check
if value is not None:
    formatted = f"${value:.2f}"

# CORRECT — catches both None and NaN
if pd.notna(value):
    formatted = f"${value:.2f}"
```

### Pattern 5: Over-Scoring Judges

LLM judges can award more points than the rubric allows (e.g., 4/3 on a criterion), producing metrics > 1.0.

**Detection**: Check for `impl_rate > 1.0` or scores exceeding maximum possible values.

**Fix**: Document with a footnote providing the full trace (which judge, which criterion, which run). Do not silently clip the value.

### Pattern 6: Variable Criteria Counts

When LLM judges generate rubrics dynamically, different experiments may have wildly different criteria structures:
- Experiment A: Uniform 5 criteria per subtest
- Experiment B: 4-12 criteria with domain-specific names
- Experiment C: Collapsed to mostly 1 criterion

**Detection**: Query `criteria.csv` for distinct criteria counts per experiment.

**Fix**: Add a disclosure paragraph in the paper describing the variation and its implications.

### Pattern 7: Wrong Count from Misread Data

"30 missing across 10 runs" vs "30 runs each missing 1" are very different claims. Misreading grouped data as aggregated data (or vice versa) is common.

**Detection**: Verify counts by computing independently from raw data:

```python
# Count missing judges per run, not total missing
missing_per_run = df.groupby('run_id')['judge_id'].count()
runs_with_missing = (missing_per_run < expected_judges).sum()
```

### Pattern 8: p-Value Precision Inconsistency

The same test result reported as "p=0.202" in one location and "p=0.2015" in another creates doubt about which is correct.

**Detection**: Grep for all mentions of the same test statistic and compare precision/rounding.

**Fix**: Use consistent precision throughout. Round to 3 decimal places in body text, provide full precision in appendix.

### Pattern 9: Best-Tier Mislabel at Rounded Precision

When reporting "best tier by metric X", the table generation code may compare rounded values. If two tiers round to the same value (e.g., $0.037), the code may pick the first alphabetically (T1) when the actual winner at full precision is different (T2: $0.0366 vs T1: $0.0373).

**Detection**: For every "best tier" claim, compute the metric for all tiers at full precision and compare.

**Fix**: Always compare at full precision before rounding for display. Update narrative text to reflect the true winner.

### Pattern 10: Systematic `is not None` Across Multiple Files

The `is not None` bug (Pattern 4) is rarely isolated. If one table generation file has it, others likely do too. In the observed case, 3 files (summary.py, detail.py, comparison.py) contained 12 total instances.

**Detection**: After finding one instance, grep ALL Python files in the reporting/table-generation directory for `is not None`. Check every hit against whether it operates on DataFrame values.

**Fix**: Replace all instances with `pd.notna()`. This is a batch operation — do not fix one file and leave the others.

```python
# Search command to find all instances
# grep -rn "is not None" src/scylla/reporting/
# Then verify each hit touches DataFrame data
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Verify 16 divergent pass classifications | Tried to reconstruct majority-vote logic from raw judge data | Would require full replay of judge aggregation pipeline; too complex for manual verification | Accept qualitative documentation for complex derived classifications; verify a sample, not all |
| Glob on large figures directory | Used glob tool to list all figure files | Timeout on directory with 100+ files | Use `ls` via Bash for large directories instead of glob |
| pre-commit gitleaks hook | Ran pre-commit to validate changes | Go version mismatch broke gitleaks | Run individual linters directly (`pixi run python -m ruff`, `pixi run python -m mypy`) when pre-commit hooks have environment issues |
| Compare best-CoP at rounded precision | Checked T1 best CoP ($0.037) against rounded table values | T2 was actually $0.0366 vs T1 $0.0373; both round to $0.037 but T2 wins | Always compare at full precision, not rounded values |
| Fix `is not None` in one file only | Fixed the NaN leak in summary.py only | Same bug existed in detail.py and comparison.py (12 instances total) | When finding a systematic bug pattern, grep ALL related files before declaring done |
| Check only paper-referenced tables for nan | Grepped for "nan" only in tables mentioned in paper narrative | tab03 (judge agreement) also had nan values but paper text never quotes those specific cells | Grep for "nan" across ALL generated files, not just the ones the paper references |

## Results & Parameters

### Input Parameters

| Parameter | Value |
|-----------|-------|
| Paper | `docs/arxiv/haiku/paper.tex` (~2,400 lines) |
| Experiments | 3 (test-001, test-002, test-003) |
| Tiers | 7 (T0-T6) |
| Total runs | 1,080 |
| Subtests | 120 |
| Data files | runs.csv (1,080 rows), judges.csv (3,210 rows), criteria.csv (12,140 rows), subtests.csv, summary.json, statistical_results.json |
| Tools | pandas for independent aggregation, grep for cross-referencing, direct file reads |

### Issues Found

| Severity | Issue | Paper Claim | Data Value | Error Magnitude |
|----------|-------|-------------|------------|-----------------|
| Critical | False universality (normality) | "All 14 reject" | 13 of 14 (T6 Cost p=0.069) | Binary wrong |
| Critical | Stale inline T6 cost | $0.070 | $0.106 | 34% |
| Major | Consistency mismatch | Table: 0.77 (T0) | Figure: 0.54 (T0) | 0.23 absolute |
| Major | impl_rate > 1.0 | Not disclosed | 1.028 | Anomaly |
| Major | Variable criteria undisclosed | Implied uniform | 1-12 per experiment | Not disclosed |
| Major | LaTeX rendering bugs | `**Total**`, `nan` | Markdown in LaTeX, NaN leak | Visual |
| Moderate | Wrong missing count | "30 across 10 runs" | "30 runs" | Mischaracterization |
| Minor | p-value precision | 0.202 vs 0.2015 | Both correct, inconsistent | Precision |
| Major | Best CoP tier mislabel (test-001) | T1 best ($0.037) | T2 best ($0.0366 vs T1 $0.0373) | $0.0007/run |
| Major | 12x `is not None` bug in 3 files | N/A | summary.py, detail.py, comparison.py | Systematic |
| Major | tab03 nan values | Judge agreement table | "All Judges" row had nan for pairwise metrics | Display bug |
| Minor | p=0.442 vs p=0.4423 (impl_rate KW) | Results section vs appendix | Same statistic, different precision | Precision |

### Verification Level

verified-local (all fixes verified against data files; paper not recompiled to PDF in this session)

## Key Takeaways

1. **Always verify inline tables independently from generated tables** — Generated tables match the pipeline; inline tables in LaTeX body may be stale from a prior data version
2. **Check aggregation method when table and figure disagree** — Same metric name computed at different levels (pooled tier vs per-subtest mean) produces very different values
3. **pandas `None` to `NaN` breaks `is not None`** — Always use `pd.notna()` for DataFrame values
4. **"All X" claims are fragile** — A single exception invalidates universality; use "N of M" instead
5. **Judge-generated rubrics vary wildly** — LLM judges do not follow rubric structure for unfamiliar tasks
6. **Missing data compounds with over-scoring** — A missing judge + an over-scoring judge created the only impl_rate > 1.0
7. **Each audit pass finds DIFFERENT bugs** — First pass catches methodology/computation/LaTeX bugs; second pass catches stale inline tables and wrong counts; third pass catches best-tier mislabels, systematic `is not None` bug patterns, and p-value precision inconsistency
8. **Deploy parallel agents with different data sources** — Agent reading paper+data, agent reading figures, agent reading source code find complementary issues
9. **Grep for "nan" across ALL generated files** — Not just the ones the paper references. The tab03 nan was invisible because the paper narrative does not quote those specific table values.
10. **`is not None` is NEVER safe for pandas DataFrame values** — This is a systematic bug pattern. When auditing code that generates tables from DataFrames, search for ALL instances of `is not None` and replace with `pd.notna()`. If one file has it, check every related file.
11. **Always compare "best X" claims at full precision** — Rounded values can tie when full-precision values have a clear winner. Table generation code may pick alphabetically among ties.

## Related Skills

- `academic-paper-validation` — Full paper lifecycle review (tone, cross-refs, LaTeX, statistics, arXiv build)
- `paper-iterative-accuracy-review` — Second-pass review after targeted fixes
- `statistical-claim-verification` — Statistical methodology correctness (test selection, effect sizes)
- `latex-paper-accuracy-review` (history only) — Prior review sessions with error pattern catalog

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Branch fix-validate-model-retry-config, correctness audit of docs/arxiv/haiku/paper.tex (passes 1-2) | 2026-04-26, Opus 4.6 (1M context), 1,080 runs across 7 tiers |
| ProjectScylla | Branch fix-validate-model-retry-config, third-pass audit of docs/arxiv/haiku/paper.tex | 2026-04-26, Opus 4.6 (1M context), found 4 additional issues (best-CoP mislabel, systematic is-not-None, tab03 nan, p-value precision) |
