---
name: parallel-paper-correctness-audit
description: Multi-agent parallel workflow for verifying every numerical claim in a research paper against underlying data files (CSV, JSON), fixing errors, ensuring internal consistency across inline tables, generated tables, figure data, and post-correction narrative audit
category: documentation
date: 2026-04-28
version: 1.4.0
user-invocable: false
tags: [latex, paper, audit, verification, cross-reference, numerical-accuracy, parallel-agents, inline-tables, aggregation-mismatch, pandas, data-pipeline, post-correction, figure-caption, narrative-consistency, vl-json, idxmax, tiebreaker, myrmidon-swarm, pre-flight-recomputation, srh, kruskal-wallis, pivot-table, cross-experiment-averaging, spearman, krippendorff, inter-rater, silent-aggregation]
---
# Parallel Paper Correctness Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Verify every numerical claim in a LaTeX research paper against its underlying data files, fix errors, and ensure internal consistency using parallel agent teams |
| **Outcome** | Found and fixed 12 issues across 3 audit passes + 7 issues in post-correction audit (v1.2.0) + 1 best-tier mislabeling bug via 5-agent swarm (v1.3.0) + 1 CRITICAL pivot_table cross-experiment averaging bug (v1.4.0): original passes found false universality claim, stale inline tables, aggregation mismatch, pandas NaN bug, over-scoring judge, variable criteria; post-correction pass found 1 CRITICAL figure/caption mismatch, 4 MODERATE, 2 MINOR; v1.3.0 swarm found idxmax() tie-breaking bug; v1.4.0 swarm found pivot_table silently averaging across experiments, deflating Spearman correlations from ~0.5 to ~0.1 and Krippendorff's alpha from 0.135 to 0.034 |
| **Models Used** | Opus 4.6 (1M context), Sonnet (data-dense sections), Haiku (structural checks) |
| **Scale** | ~2,400-line LaTeX paper, 3 experiments, 7 tiers, 1,080 runs, 120 subtests |

## When to Use This Skill

Use this workflow when:

- A research paper presents results from a data pipeline and you need to verify ALL numbers match
- The paper has both auto-generated tables (from scripts) AND hand-written inline tables in LaTeX
- Multiple aggregation levels exist (per-run, per-subtest, per-tier, per-experiment) and tables/figures may compute the same metric at different levels
- The paper has undergone prior review rounds and you suspect stale values from earlier data versions
- You need to verify statistical claims (normality tests, effect sizes, test statistics) against raw data
- The paper contains universality claims ("all X", "every Y", "no Z") that could be falsified by a single exception
- The paper has undergone major narrative corrections (e.g., changing conclusions from "significant degradation" to "no significant effect") and you need to verify no residual old-narrative language remains
- Figure captions may have been written for a prior version of the analysis and not updated after corrections

**Trigger phrases**: "verify all numbers", "correctness audit", "cross-reference paper against data", "check inline tables", "second-pass audit", "third-pass audit", "grep for nan", "post-correction audit", "verify narrative consistency", "swarm audit", "myrmidon swarm", "best tier verification", "idxmax tiebreaker", "pivot_table averaging", "inter-rater recomputation", "cross-experiment averaging"

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

### Phase 6: Post-Correction Narrative Audit (3 Agents)

Deploy after major narrative corrections (e.g., changing conclusions from "significant effect" to "no significant effect"). This phase catches residual old-narrative artifacts.

**Agent A — Paper Structure + Claims**:
1. Read full `paper.tex` — catalog every factual claim, figure reference, and conclusion
2. Search for residual old-narrative language (grep for the old framing words: "degradation", "harm", "counterproductive", etc.)
3. Verify causal language matches the corrected conclusions (null results should not use causal framing)

**Agent B — All Data Files**:
1. Read ALL data files: `runs.csv`, `summary.json`, `statistical_results.json`, all table `.tex` files
2. Independently recompute pass rates, costs, and CoP per tier per experiment from `runs.csv` (do NOT trust `summary.json`)
3. Check for multiple statistical output files — a separate file (e.g., `srh_tier_experiment.json`) may contain the correct results while the main file uses the wrong grouping factor

**Agent C — All Figure Specs**:
1. Read every `.vl.json` file — compare title, encoding, mark type, and data transforms against paper captions
2. Verify figure content matches what the caption claims (e.g., caption says "CoP" but spec shows raw cost)
3. Check data cardinality (caption says "21 tier-experiment combinations" but spec aggregates to 7 tier-level values)

**Post-Correction Checklist** (apply after agents report):
1. Search for residual old-narrative language — grep for the old framing to ensure no orphaned claims remain
2. Check figure/caption alignment — figures may have been created for the old narrative and not updated
3. Verify causal language matches new conclusions — old conclusions may have used causal framing inappropriate for corrected null results
4. Cross-check body text H-values against updated tables — body prose may reference rounded values that no longer match updated table precision

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

### Pattern 11: Figure/Caption Mismatch After Corrections

After major data corrections, figures may have been regenerated but captions not updated (or vice versa). The figure spec (e.g., VL JSON) shows one metric while the caption describes another.

**Detection**: Read every `.vl.json` spec and compare its `title`, `encoding.y.field`, and `mark` against the corresponding `\caption{}` in the paper. Common mismatches:
- Caption says "Cost-of-Pass" but spec plots raw cost
- Caption says "21 tier-experiment combinations" but spec aggregates to 7 tier-level values
- Caption describes a trend that matched the old narrative but contradicts the corrected data

**Fix**: Update either the caption or the figure spec to match, depending on which reflects the intended analysis.

### Pattern 12: Residual Old-Narrative Language

After changing conclusions (e.g., from "significant effect" to "no significant effect"), orphaned phrases from the old narrative may remain scattered throughout the paper.

**Detection**: Grep for characteristic words from the old framing. If the old conclusion was "harmful degradation", search for: "degradation", "harm", "counterproductive", "detrimental", "penalty". Check abstract, introduction, discussion, and conclusion sections.

**Fix**: Replace with language consistent with the corrected conclusions. For null results, use neutral framing: "no significant difference", "comparable performance", "within expected variation".

### Pattern 13: Causal Language for Non-Significant Results

Papers originally written around significant findings often use causal framing ("X caused Y", "X led to degradation") that becomes inappropriate when the analysis is corrected to show null results.

**Detection**: Search for causal verbs near the corrected metrics: "caused", "led to", "resulted in", "produced", "drove". Null or non-significant results should use associative or descriptive language only.

**Fix**: Replace causal framing with descriptive framing: "X was associated with" or "X showed no significant difference in Y".

### Pattern 14: Rounding Precision Inconsistency Between Body and Appendix

Summary tables in the body may use fewer decimal places than appendix tables for the same statistic (e.g., body: H=4.0, appendix: H=4.00). Both are valid roundings but the inconsistency looks sloppy and can cause confusion.

**Detection**: For every statistic that appears in both body and appendix, compare precision. Common cases: H-statistics, p-values, effect sizes.

**Fix**: Standardize to the same precision throughout. Typically 2 decimal places for test statistics, 3-4 for p-values.

### Pattern 15: Consensus vs Per-Judge Metric Levels

A claim like "only one value exceeding 1.0 in the dataset" may be true at the consensus (median across judges) level but false at the per-judge level. When auditing such claims, determine which level the paper is referring to.

**Detection**: Check the surrounding context for "consensus", "median", "per-judge", or "individual". If ambiguous, check both levels against the data.

**Fix**: Add explicit qualification: "at the consensus level" or "across individual judge scores".

### Pattern 16: Multiple Statistical Output Files

Statistical analysis may produce results in multiple files with different grouping factors. The main `statistical_results.json` might use `agent_model` as the factor (wrong for a single-model study), while the correct results are in a separate file like `srh_tier_experiment.json` using `tier` as the factor.

**Detection**: List all statistical output files in the data directory. Compare the factor/grouping variable in each against what the paper claims to be testing.

**Fix**: Ensure the paper cites results from the correct file. Add a note documenting which file contains which analysis.

### Pattern 17: `idxmax()` Silently Picks Alphabetical First Among Ties

When multiple pandas Series values are tied, `idxmax()` returns the first index alphabetically. For test-001, 6 tiers (T1-T6) tied at pass_rate=1.0, and `idxmax()` returned T1 (first alphabetically). The actual "best" tier by secondary metric (mean score) was T5 (0.930 vs T1=0.908).

**Detection**: For every "best tier by X" claim, check whether multiple tiers tie on the primary metric. If they do, verify that the selected tier also wins on a meaningful secondary metric.

**Fix**: When ties exist on the primary metric, add a tiebreaker using a secondary metric (e.g., mean score for pass rate ties, or score for cost ties):

```python
# WRONG — idxmax() picks alphabetically among ties
best_tier = tier_stats['pass_rate'].idxmax()

# CORRECT — tiebreak with secondary metric
max_val = tier_stats['pass_rate'].max()
tied = tier_stats[tier_stats['pass_rate'] == max_val]
if len(tied) > 1:
    best_tier = tied['mean_score'].idxmax()
else:
    best_tier = tied.index[0]
```

**Recurrence note**: This is the SECOND time this exact bug pattern was found in the Haiku paper (v1.1.0 found T2 mislabeled as T1 for CoP, v1.3.0 found T5 mislabeled as T1 for best tier by pass rate). The root cause is the same: `idxmax()` tie-breaking behavior in pandas.

### Pattern 18: SRH vs KW Recomputation Produces Different H-Statistics

An agent that independently recomputes statistics from runs.csv using standard Kruskal-Wallis will get different H-values than the paper's Scheirer-Ray-Hare analysis. SRH uses ranked data with a two-way design; KW is a one-way test.

**Detection**: When auditing statistical claims, first identify which test was actually used (check the authoritative data file, e.g., `srh_tier_experiment.json`). Do not assume a standard KW recomputation will match SRH results.

**Fix**: Verify paper values against their authoritative data file, not against independent recomputation with a different test. If recomputing, use the same statistical test the paper used.

### Pattern 19: Silent Cross-Experiment Averaging in pivot_table

When `pivot_table` index columns don't uniquely identify rows across a grouping dimension (like experiment), pandas silently averages instead of raising an error. This is particularly insidious because the output has the expected shape (correct number of tiers x subtests x runs) but wrong values.

In the observed case, `detail.py:39-43` omitted `experiment` from the pivot index. Since all 3 experiments share the same subtest names, pivot_table silently averaged scores across experiments, producing N=360 cross-experiment-averaged items instead of ~1,050 per-run items. This deflated:
- Spearman correlations from ~0.5 (moderate) to ~0.1 (near-zero)
- Krippendorff's alpha from 0.135 to 0.034
- The paper's entire narrative about "nearly uncorrelated evaluations" was driven by this bug

**Detection**: When auditing inter-rater statistics, independently recompute correlations from raw per-run data (e.g., `judges.csv`) rather than trusting the output of the analysis pipeline. If your recomputed values differ dramatically (not just rounding), suspect a pivot/aggregation bug.

**Prevention**: Always include ALL grouping dimensions in `pivot_table` index. If the data has experiment, tier, subtest, run_number -- include all four:

```python
# WRONG — omits experiment, silently averages across experiments
pivot = df.pivot_table(
    index=['tier', 'subtest', 'run_number'],
    columns='judge',
    values='score'
)

# CORRECT — includes all grouping dimensions
pivot = df.pivot_table(
    index=['experiment', 'tier', 'subtest', 'run_number'],
    columns='judge',
    values='score'
)
```

**Recurrence note**: This bug survived 4 prior audit passes (v1.0.0 through v1.3.0) because prior passes verified paper values against tab03 output -- which was itself wrong. The bug was only caught when Agent D independently recomputed Spearman correlations from judges.csv and got dramatically different values.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Verify 16 divergent pass classifications | Tried to reconstruct majority-vote logic from raw judge data | Would require full replay of judge aggregation pipeline; too complex for manual verification | Accept qualitative documentation for complex derived classifications; verify a sample, not all |
| Glob on large figures directory | Used glob tool to list all figure files | Timeout on directory with 100+ files | Use `ls` via Bash for large directories instead of glob |
| pre-commit gitleaks hook | Ran pre-commit to validate changes | Go version mismatch broke gitleaks | Run individual linters directly (`pixi run python -m ruff`, `pixi run python -m mypy`) when pre-commit hooks have environment issues |
| Compare best-CoP at rounded precision | Checked T1 best CoP ($0.037) against rounded table values | T2 was actually $0.0366 vs T1 $0.0373; both round to $0.037 but T2 wins | Always compare at full precision, not rounded values |
| Fix `is not None` in one file only | Fixed the NaN leak in summary.py only | Same bug existed in detail.py and comparison.py (12 instances total) | When finding a systematic bug pattern, grep ALL related files before declaring done |
| Check only paper-referenced tables for nan | Grepped for "nan" only in tables mentioned in paper narrative | tab03 (judge agreement) also had nan values but paper text never quotes those specific cells | Grep for "nan" across ALL generated files, not just the ones the paper references |
| Trusting exploration agent claim about line 472 | Exploration agent said line 472 had "[0,1] scale" | Initially flagged as potentially not existing without verification | Always verify agent claims by reading the actual file; do not trust agent summaries without cross-checking |
| vl2png with default npx invocation | Used `npx vl2png` to render VL JSON specs | Missing explicit packages; default dimensions too small (207x369) | Requires `npx -p vega-lite -p vega-cli -p canvas vl2png` with explicit width/height in spec + scale factor of 3 |
| Independent SRH recomputation was actually KW | Agent D ran scipy kruskal() to verify paper's SRH H-statistics | KW is a one-way test; SRH is a two-way ranked test. Produced H_tier=8.46 vs paper's H_tier=4.00, flagged as discrepancy | When auditing statistical claims, verify which test was used before recomputing. SRH and KW produce different H-values by design |
| idxmax() tiebreaker not caught in 4 prior audit passes | Four previous audit passes examined "best tier" claims | Prior passes compared at full precision but did not check for ties on the primary metric where idxmax() picks alphabetically | After finding a "best X" mislabel once, add the tiebreaker pattern to ALL table generation code, not just the one instance found |
| Verifying paper values against pipeline output only | 4 prior audit passes verified paper's inter-rater statistics against tab03 output | tab03 was itself wrong due to the pivot_table bug in detail.py -- verifying paper against pipeline confirmed the wrong values | At least one agent must recompute from raw data using independent code, not just verify paper against pipeline output |
| `run_in_background` bash commands producing empty output | Used `run_in_background` for parallel agent tasks | Some background commands produced empty output files | Fall back to foreground execution when output reliability is critical |

## Results & Parameters

### Input Parameters

| Parameter | Value |
|-----------|-------|
| Paper | `docs/arxiv/haiku/paper.tex` (~2,400 lines) |
| Experiments | 3 (test-001, test-002, test-003) |
| Tiers | 7 (T0-T6) |
| Total runs | 1,080 |
| Subtests | 120 |
| Data files | runs.csv (1,080 rows), judges.csv (3,210 rows), criteria.csv (12,140 rows), subtests.csv, summary.json, statistical_results.json, srh_tier_experiment.json |
| Figure specs | 72 Vega-Lite JSON specs (.vl.json) |
| Tools | pandas for independent aggregation, grep for cross-referencing, direct file reads |

### Issues Found

#### Passes 1-3 (v1.0.0-v1.1.0)

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

#### 5-Agent Swarm Audit (v1.3.0)

| Severity | Issue | Paper Claim | Data Value | Error Magnitude |
|----------|-------|-------------|------------|-----------------|
| Major | Best-tier mislabel (test-001 pass rate) | T1 best tier | T5 best tier (score 0.930 vs T1 0.908) | Wrong tier (6 tied at pass_rate=1.0, idxmax picked T1 alphabetically) |

#### 5-Agent Swarm Audit with Pre-Flight Recomputation (v1.4.0)

| Severity | Issue | Paper Claim | Data Value | Error Magnitude |
|----------|-------|-------------|------------|-----------------|
| Critical | pivot_table cross-experiment averaging (detail.py:39-43) | Spearman ~0.1, Krippendorff 0.034 | Spearman ~0.5, Krippendorff 0.135 | 5x deflation (entire inter-rater narrative wrong) |
| Critical | 20+ paper references to wrong statistics | "nearly uncorrelated", "poor agreement" | "low-to-moderate rank agreement" | Narrative reversal across 20 sections |

#### Post-Correction Audit (v1.2.0)

| Severity | Issue | Paper Claim | Data Value | Error Magnitude |
|----------|-------|-------------|------------|-----------------|
| Critical | Figure/caption mismatch (fig06) | Caption: "CoP" | Spec plots raw cost | Metric identity wrong |
| Moderate | Caption error (fig08) | "21 tier-experiment combos" | Spec aggregates to 7 tier-level values | Cardinality wrong |
| Moderate | Scale inconsistency | Body: H=4.0 (1dp) | Appendix: H=4.00 (2dp) | Precision inconsistency |
| Moderate | Causal language for null results (x4) | "caused", "led to" | Non-significant SRH results | Inappropriate framing |
| Moderate | Overclaim from old narrative | Strong conclusion | Null result | Narrative mismatch |
| Minor | SRH precision standardization | H=4.0, 5.5, 3.7 | H=4.00, 5.47, 3.66 | Standardized to 2dp |
| Minor | Consensus vs per-judge ambiguity | "only value >1.0" | 1 at consensus, 3 at per-judge | Level unspecified |

### Verification Level

verified-local (4,950 tests pass, ruff clean, mypy clean, corrected tab03 regenerated and verified)

## Key Takeaways

1. **Always verify inline tables independently from generated tables** — Generated tables match the pipeline; inline tables in LaTeX body may be stale from a prior data version
2. **Check aggregation method when table and figure disagree** — Same metric name computed at different levels (pooled tier vs per-subtest mean) produces very different values
3. **pandas `None` to `NaN` breaks `is not None`** — Always use `pd.notna()` for DataFrame values
4. **"All X" claims are fragile** — A single exception invalidates universality; use "N of M" instead
5. **Judge-generated rubrics vary wildly** — LLM judges do not follow rubric structure for unfamiliar tasks
6. **Missing data compounds with over-scoring** — A missing judge + an over-scoring judge created the only impl_rate > 1.0
7. **Each audit pass finds DIFFERENT bugs** — First pass catches methodology/computation/LaTeX bugs; second pass catches stale inline tables and wrong counts; third pass catches best-tier mislabels, systematic `is not None` bug patterns, and p-value precision inconsistency; post-correction pass catches figure/caption mismatches, residual narrative language, and causal framing errors
8. **Deploy parallel agents with different data sources** — Agent reading paper+data, agent reading figures, agent reading source code find complementary issues
9. **Grep for "nan" across ALL generated files** — Not just the ones the paper references. The tab03 nan was invisible because the paper narrative does not quote those specific table values.
10. **`is not None` is NEVER safe for pandas DataFrame values** — This is a systematic bug pattern. When auditing code that generates tables from DataFrames, search for ALL instances of `is not None` and replace with `pd.notna()`. If one file has it, check every related file.
11. **Always compare "best X" claims at full precision** — Rounded values can tie when full-precision values have a clear winner. Table generation code may pick alphabetically among ties.
12. **Recompute from raw data, not summary files** — summary.json may be stale or use wrong aggregation. Always recompute key metrics from runs.csv independently for verification.
13. **Read every VL JSON spec, not just a sample** — Figure/caption mismatches are invisible without reading the actual spec. The title/encoding/mark in the spec may contradict the caption.
14. **After major narrative corrections, run the post-correction checklist** — Search for residual old-narrative language, check figure/caption alignment, verify causal language matches new conclusions, cross-check body H-values against updated tables.
15. **Check for multiple statistical output files** — The main statistical results file may use the wrong grouping factor. Always list all statistical output files and verify which one matches the paper's analysis.
16. **Distinguish consensus vs per-judge levels in claims** — "Only one value exceeding X" may be true at one level but false at another. Always specify which level.
17. **`idxmax()` is NEVER safe for "best X" selection without tiebreaker** — When multiple values tie, `idxmax()` returns alphabetically first. Always check for ties and use a meaningful secondary metric as tiebreaker. This is a recurring bug pattern (found twice in the same paper).
18. **Pre-flight centralized recomputation prevents agent divergence** — Run a single pandas script BEFORE spawning parallel agents, embed the JSON output in each agent's prompt. Without this, each agent running independent pandas can use different aggregation logic and produce contradictory findings.
19. **pivot_table silently averages when index columns don't uniquely identify rows** — This produced systematically wrong inter-rater statistics that survived 4 prior audit passes. The bug was only caught by independently recomputing from raw data.
20. **Verifying paper values against pipeline output is NOT sufficient** — If the pipeline itself has a bug, verifying paper against pipeline confirms the wrong values. At least one agent must recompute from raw data using independent code.
21. **Section-level Go/NoGo grading accelerates review decisions** — Grading each of 20 sections independently (GO/CONDITIONAL/NO-GO) makes it immediately clear where issues are and whether the paper can proceed.
22. **Agent D finding what 4 prior passes missed validates the swarm approach** — The statistics-focused agent with independent recomputation capability found a bug that 4 sequential audit sessions did not.
23. **Verify which statistical test was used before flagging discrepancies** — SRH and KW produce different H-statistics by design (two-way ranked vs one-way). An agent that recomputes with the wrong test will produce false alarms.
24. **5-agent swarm with model tiering works well for paper audits** — Opus for high-value sections (abstract, conclusions), Sonnet for data-dense sections (results, statistics), Haiku for structural checks (cross-references, appendices). All 5 agents completed within ~16 minutes.

## Related Skills

- `academic-paper-validation` — Full paper lifecycle review (tone, cross-refs, LaTeX, statistics, arXiv build)
- `paper-iterative-accuracy-review` — Second-pass review after targeted fixes
- `statistical-claim-verification` — Statistical methodology correctness (test selection, effect sizes)
- `latex-paper-accuracy-review` (history only) — Prior review sessions with error pattern catalog
- `evaluation-paper-rewrite-after-data-fix` — Post-data-correction paper rewrite workflow

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Branch fix-validate-model-retry-config, correctness audit of docs/arxiv/haiku/paper.tex (passes 1-2) | 2026-04-26, Opus 4.6 (1M context), 1,080 runs across 7 tiers |
| ProjectScylla | Branch fix-validate-model-retry-config, third-pass audit of docs/arxiv/haiku/paper.tex | 2026-04-26, Opus 4.6 (1M context), found 4 additional issues (best-CoP mislabel, systematic is-not-None, tab03 nan, p-value precision) |
| ProjectScylla | Branch fix-validate-model-retry-config, post-correction paragraph-level audit of docs/arxiv/haiku/paper.tex (2428 lines) | 2026-04-27, Opus 4.6 (1M context), 3 parallel Explore agents + 1 Plan agent, found 7 issues (1 CRITICAL figure/caption, 4 MODERATE, 2 MINOR), 72 VL JSON specs cross-checked |
| ProjectScylla | Branch fix-validate-model-retry-config, 5-agent myrmidon swarm audit of docs/arxiv/haiku/paper.tex (2432 lines) | 2026-04-28, Opus/Sonnet/Haiku model tiering, 5 parallel agents with pre-flight recomputation, found idxmax() tie-breaking bug in table generation pipeline, fixed comparison.py tiebreaker logic |
| ProjectScylla | Branch fix-validate-model-retry-config, 5-agent myrmidon swarm with pre-flight recomputation, paragraph-level data validation of docs/arxiv/haiku/paper.tex | 2026-04-28, Opus/Sonnet model tiering, 280+ claims verified across 20 sections, found CRITICAL pivot_table cross-experiment averaging bug in detail.py, fixed pivot index + regenerated tab03 + updated 20+ paper references |
