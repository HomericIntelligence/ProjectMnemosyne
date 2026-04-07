---
name: latex-paper-accuracy-review
description: Review a LaTeX research paper for factual accuracy against raw experiment
  data, statistical outputs, and codebase constants before publication
category: documentation
date: 2026-04-06
version: 4.0.0
user-invocable: false
tags: [latex, paper, review, accuracy, statistics, data-verification, publication, confidence-intervals, iftex, rounding, BCa-bootstrap, pass-classification, grading-scale, majority-vote, cliffs-delta, myrmidon-swarm]
---
# Skill: latex-paper-accuracy-review

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 (v1.0.0), 2026-04-05 (v2.0.0), 2026-04-06 (v3.0.0, v3.1.0, v4.0.0) |
| Category | documentation |
| Objective | Review a LaTeX research paper for factual accuracy against raw experiment data, statistical outputs, and codebase source files |
| Outcome | Five successful sessions — v1.0.0 fixed 6 errors + 4 warnings in an 884-line first draft; v2.0.0 verified 30+ claims and fixed 6 critical + 3 important + 1 minor issue in a 2,020-line paper with 1,080 runs; v3.0.0 discovered bootstrap CIs mislabeled as Clopper-Pearson, 536 missing judge evaluations, and BH monotonicity comment errors; v3.1.0 found 2 cost rounding errors, 16 pass/score>0.5 mismatches, and unnamed bootstrap CI method; v4.0.0 found grading scale paper-vs-code mismatch (864/1080 rows), pass classification mechanism wrong (majority vote vs threshold, 16 mismatches prove difference), Cliff's delta FAIR vs journal threshold convention, judge agreement N-value on pivoted data (360 vs 2696), and recurring column specifier off-by-one. Used myrmidon swarm (2 Sonnet + 3 Haiku) for independent verification. |

## When to Use

- Before submitting a research paper for publication or arXiv upload
- When paper prose or statistics may diverge from raw experiment data
- When code and paper share constants/thresholds that must stay consistent
- After a long paper-writing session where numbers were typed manually from reports
- When partial/incomplete experiments are referenced in a paper
- When a paper has been revised multiple times and claims may have drifted from data
- When confidence intervals are reported and need independent verification (e.g., Clopper-Pearson vs bootstrap)
- When judge evaluations may be missing or incomplete across experiment conditions
- After 3+ review rounds when remaining issues are likely subtle rounding discrepancies rather than factual errors
- When a pipeline pre-computes pass/fail differently from the paper's stated threshold (e.g., judge_passed field vs consensus_score > 0.5)
- When paper documents grading scales, classification thresholds, or effect size conventions that may have been manually typed rather than derived from source code
- When using multi-agent (myrmidon swarm) review to get independent verification across methodology, framing, and mechanical checks
- When analysis code aggregates data (e.g., pivot_table) and the paper cites the raw N rather than the aggregated N

## Verified Workflow

### Step 0: Consult prior review notes (NEW in v3.1.0)

Before starting a new review pass, search ProjectMnemosyne for existing review skills and their `.notes.md` files. Prior sessions document what was already fixed and verified, preventing redundant work. After 3+ rounds, the remaining issues shift from factual errors to subtle rounding discrepancies and disclosure gaps.

### Step 1: Parallel exploration for comprehensive coverage

Launch 3 parallel Explore agents simultaneously for maximum coverage:

1. **Paper text agent** — reads the full `.tex` file, extracts every quantitative claim (numbers, percentages, statistical test results, cost figures, counts)
2. **Source data agent** — reads all data files (CSV, JSON, generated tables) and builds a ground-truth reference
3. **Figures/tables/bib agent** — checks figure captions, table column counts, bibliography completeness, cross-references

This parallel-first approach gives comprehensive coverage in a single pass and avoids serial bottlenecks.

### Step 2: Build the accuracy review plan

Cross-check every quantitative claim against source data. Organize findings into tiers:

- **ERRORS** — must fix before publication (factual errors, contradictions, arithmetic mistakes)
- **WARNINGS** — should fix (imprecision, inconsistency, misleading framing)
- **UNVERIFIABLE** — note what cannot be checked without external data
- **VERIFIED OK** — explicitly confirm correct values to build confidence

For each issue record:
- Exact location (section, line numbers)
- The claim as written
- The actual value from source
- The source file/path
- The specific fix required

### Step 2b: Independent CI verification (NEW in v3.0.0)

When the paper reports confidence intervals, independently recompute them to verify:

```python
# Clopper-Pearson exact CIs (binomial proportion)
from scipy.stats import beta as beta_dist
def clopper_pearson(k, n, alpha=0.05):
    lo = beta_dist.ppf(alpha/2, k, n - k + 1) if k > 0 else 0.0
    hi = beta_dist.ppf(1 - alpha/2, k + 1, n - k) if k < n else 1.0
    return lo, hi

# Example: 17 passes out of 24 trials
lo, hi = clopper_pearson(17, 24)  # [0.495, 0.882]
```

**Critical check**: If paper says "Clopper-Pearson 95% CI" but the intervals are narrower than exact Clopper-Pearson bounds, they are likely bootstrap CIs mislabeled. Bootstrap percentile CIs and Clopper-Pearson CIs are computed differently and can diverge significantly, especially at small n.

**Name the method precisely** (NEW in v3.1.0): If bootstrap CIs are used, specify the variant (BCa, percentile, basic) and the number of resamples in the paper. E.g., "bootstrap 95% CI (BCa method, 10,000 resamples)" rather than just "bootstrap 95% CI".

**Also verify**: Count judge evaluations per experiment x tier combination. Missing evaluations are a critical undisclosed finding. Use:
```bash
# Count evaluations per experiment and tier
python3 -c "
import csv
from collections import Counter
with open('data/judges.csv') as f:
    rows = list(csv.DictReader(f))
counts = Counter((r['experiment'], r['tier']) for r in rows)
for key, count in sorted(counts.items()):
    print(f'{key}: {count}')
print(f'Total: {len(rows)}')
"
```

### Step 2c: Myrmidon swarm independent verification (NEW in v4.0.0)

For thorough academic review, deploy a myrmidon swarm with role-based specialization:

**Professor agents (Sonnet-class):**
- Professor 1: Statistical methodology review — verify test choices, assumptions, effect size conventions
- Professor 2: Experimental design and framing review — check overclaims, causal language, missing caveats

**Student agents (Haiku-class):**
- Student 1: Tier summary table verification — exhaustive mechanical check of every number in every table
- Student 2: SRH/pairwise stats verification — verify all H-stats, df values, p-values against data files
- Student 3: LaTeX quality check — column specifiers, cross-references, formatting consistency

**Critical lesson**: When delegating data verification to budget-class (Haiku) agents, provide the EXACT computation formula, not just "compute X from the data." Haiku students are excellent at exhaustive mechanical verification but produce false positives when they infer the wrong computation method (e.g., computing CoP as `sum(cost_of_passed_runs)/count` instead of `mean_cost/pass_rate`, or computing consistency at run-level instead of subtest-level).

**What works well**: Sonnet professors catch higher-level framing and logic issues that mechanical checking misses (e.g., "first" without hedging, causal language, missing T6 caveats, Pareto qualification needed).

### Step 3: Prioritize fixes

Apply in this order:
1. Arithmetic errors (wrong totals, sums, averages)
2. Claims directly contradicted by the paper's own tables
3. Confidence interval methodology errors (e.g., bootstrap mislabeled as exact — see Pattern 15)
4. Statistical test attribution errors (which test produced which stat — see Pattern 6)
5. LaTeX structural errors (column specifiers, nan values — see Patterns 9-10)
6. Fabricated/extrapolated data for incomplete experiments
7. Code/paper constant mismatches (thresholds, formulas)
8. Missing data disclosures (e.g., missing evaluations — see Pattern 16)
9. Overly broad claims that don't hold across all cases (see Pattern 7)
10. Missing citations for borrowed thresholds or methodologies
11. Missing p-values in pairwise comparisons
12. Ambiguous column headers or undefined terms in tables

### Step 4: Apply fixes systematically

Use `Edit` tool with exact string replacement. For each fix:
- Replace the exact wrong text
- Verify with `Grep` that old text is gone
- Read the changed section to confirm correctness

### Step 5: Commit

Conventional commit with full list of issues fixed in the message body.

### Quick Reference

```bash
# Key source files to verify against
runs.csv              # Ground truth: individual run data (scores, costs, durations)
summary.json          # Aggregated experiment statistics
statistical_results.json  # omnibus_tests (KW), pairwise_comparisons, effect_sizes
srh_tier_experiment.json  # SRH interaction tests (tier/experiment factors)
judges.csv            # Inter-rater reliability data
criteria.csv          # Per-criterion scoring data
subtests.csv          # Per-subtest aggregates
tables/*.tex          # Generated LaTeX tables (check these, not just prose)

# Key verification commands
grep -c "pattern" data/runs.csv        # Count occurrences in run data
python3 -c "import json; d=json.load(open('file.json')); print(d['key'])"  # Spot-check JSON values
wc -l data/runs.csv                    # Verify row counts
```

## Common Error Patterns Found in ProjectScylla Papers

### Pattern 1: Tier-level vs subtest-level metric confusion
**Symptom:** "Tier X achieved 0% pass rate" when one subtest passed
**Root cause:** Tier-level "Best Score" uses tiebreaker selection; losing subtest metrics are dropped from tier summary
**Fix:** Report per-subtest breakdown, note tiebreaker selection rationale

### Pattern 2: Cross-task blanket claim from single-task observation
**Symptom:** "T0 framework failure is consistent across all three tasks" — actually only one task shows it
**Root cause:** Writing from memory of worst case; not cross-checking tables already in the paper
**Fix:** Restrict claim to the specific test(s) where it holds; cite other tests' actual values

### Pattern 3: Arithmetic sum error in suite counts
**Symptom:** "113 subtests (T0: 24, T1: 10, ...)" where per-tier counts add to 120
**Root cause:** Manual addition error; per-tier counts sourced from YAML file counts (correct), sum typed from memory (wrong)
**Fix:** Always verify total = sum(per-tier counts); use `wc` or count YAML files directly

### Pattern 4: Code/paper threshold mismatch
**Symptom:** Cliff's delta thresholds in paper (0.147/0.330/0.474) differ from code (0.11/0.28/0.43)
**Root cause:** Two different published conventions exist (Cohen-derived vs Romano et al. 2006); paper used wrong one
**Fix:** Always grep the codebase for the actual thresholds used (`scylla/analysis/stats.py`); cite Romano et al. 2006 for ProjectScylla
**Correct thresholds (Romano et al. 2006):** negligible <0.11, small <0.28, medium <0.43, large >=0.43

### Pattern 5: Fabricated partial experiment results
**Symptom:** "T1 achieves 0.83 at 100% pass rate" for a test that only has 1 run completed
**Root cause:** Extrapolating from expected pattern rather than reading checkpoint.json
**Fix:** Always read `checkpoint.json` for partial experiments; only report what is actually in the checkpoint
**Source files:** `~/fullruns/haiku/<timestamp>-<test-id>/checkpoint.json`

### Pattern 6: Statistical test attribution (KW vs SRH)
**Symptom:** "Score: H(6) = 22.63, p = 0.0009" listed under Kruskal-Wallis omnibus — but score isn't in the KW omnibus
**Root cause:** The stat actually comes from Scheirer-Ray-Hare interaction test tier effect, not KW
**Fix:** Check `data/statistical_results.json` — `omnibus_tests` array (KW) vs `srh_tier_experiment.json` (SRH tier/experiment factors)
**Rule:** KW omnibus tests standalone metrics: pass_rate, impl_rate, duration_seconds. Score and Cost tier effects come from SRH tier factor. Papers commonly present these together without distinguishing their source — this is a subtle but critical methodological distinction.
**Table fix pattern:** Add a "Source" column distinguishing KW vs SRH provenance for each row

### Pattern 7: Blanket normality claim with exceptions
**Symptom:** "All tier/metric combinations failed Shapiro-Wilk (p < 0.001)" — T6 actually passes
**Root cause:** T6 has n=15 (small); SW test is underpowered at small n, returns high p-values
**Fix:** "Nearly all... T6 score (p=0.329) and T6 cost (p=0.177) passed normality (n=15); non-parametric applied throughout for consistency"
**Scope verification:** Check the actual scope of normality testing. "All 14 tier x metric combinations" may actually mean 7 tiers x 2 metrics (Score, Cost) = 14, not 7 x 7 = 49. Always read the generated table (e.g., `tab10_normality_tests.tex`) to verify scope — the table reveals the truth faster than re-deriving from prose.

### Pattern 8: Understated cost ratios
**Symptom:** "T3/T4 cost 3.5-4x more than T1/T2" — some pairs are 7x
**Root cause:** Author computed one favorable comparison (T3/T1=3.55x) and generalized
**Fix:** Compute all four cross-products (T3/T1, T3/T2, T4/T1, T4/T2) and report the full range or all pairs

### Pattern 9: LaTeX column specifier mismatch (NEW in v2.0.0)
**Symptom:** `{lrrrrrr}` (7 column specifiers) for a table with 6 actual data fields
**Root cause:** Extra column specifier added during editing; LaTeX compiles without error but causes subtle spacing issues
**Fix:** Count the header fields in the table and match against the column specifier string. Check all `\begin{tabular}{...}` lines.
**Detection:** `grep -n 'begin{tabular}' paper.tex` then manually verify each one

### Pattern 10: nan values in generated LaTeX tables (NEW in v2.0.0)
**Symptom:** "All Judges (Overall) & nan & nan & nan" appearing in a table row
**Root cause:** Data generation script produced nan for an aggregate row; the row was included verbatim in the .tex file
**Fix:** Remove the offending row entirely, or trace back to the data pipeline to fix the nan generation

### Pattern 11: Missing p-values in pairwise comparisons (NEW in v2.0.0)
**Symptom:** Paper discusses T3->T4 transition without reporting the Dunn's test p-value
**Root cause:** Author focused on significant results and omitted non-significant pairwise comparisons
**Fix:** Add "Dunn's p=X.XXX (n.s.)" for completeness; non-significant results are still informative

### Pattern 12: Ambiguous table column definitions (NEW in v2.0.0)
**Symptom:** "Best Tier" column in a table without definition of what "best" means
**Root cause:** Column meaning is obvious to the author but not to readers
**Fix:** Add a footnote defining the criterion (e.g., "Best Tier = tier with highest pass rate")

### Pattern 13: Cost rounding errors (NEW in v2.0.0)
**Symptom:** "$0.224 for test-002" when total_cost / num_runs = $0.226
**Root cause:** Intermediate rounding or using pre-rounded source values
**Fix:** Recompute from raw data: total_cost / count. Verify: `python3 -c "print(81.28/360)"`

### Pattern 14: Pass rate computation confusion (NEW in v2.0.0)
**Symptom:** Different pass rates when computing from raw data vs paper values
**Root cause:** Paper uses consensus_score > 0.5 as pass threshold, but naive computation uses score > 0
**Fix:** Always verify the pass criterion definition before computing. Check the paper's methodology section for the threshold. Raw count of non-zero scores gives different results than consensus-based thresholds.

### Pattern 15: Bootstrap CIs mislabeled as Clopper-Pearson (NEW in v3.0.0)
**Symptom:** Paper claims "Clopper-Pearson 95% CI" but the reported intervals are narrower than exact binomial bounds
**Root cause:** The analysis pipeline computes bootstrap percentile CIs (resampling-based) but the paper labels them as Clopper-Pearson (exact). The two methods are fundamentally different: Clopper-Pearson inverts the binomial test and is conservative; bootstrap percentile CIs resample the observed data and can be anti-conservative at small n.
**Detection:** Independently compute Clopper-Pearson CIs using `scipy.stats.beta.ppf` and compare with paper values. If they don't match, check the pipeline code for `np.percentile` or `bootstrap` calls.
**Fix:** Either (a) relabel as "bootstrap percentile 95% CI" or (b) recompute using actual Clopper-Pearson formula. Option (a) is preferred when bootstrap was the intentional method.
**Example:** For 17/24 passes: Clopper-Pearson gives [0.495, 0.882], bootstrap might give [0.542, 0.833]. The difference matters for interpretation.

### Pattern 16: Missing judge evaluations across conditions (NEW in v3.0.0)
**Symptom:** Paper reports evaluation results but does not disclose that some experiment x tier combinations have fewer evaluations than expected
**Root cause:** Judge evaluation pipeline may have failures, timeouts, or skipped conditions. If one experiment has 1,620 evaluations and another has only 1,084, the 536-evaluation gap should be disclosed.
**Detection:** Count evaluations per experiment in judges.csv. Compare against expected count (runs x judges_per_run). Any shortfall > 5% should be flagged.
**Fix:** Add a disclosure in the methodology section: "test-001 has N fewer judge evaluations than test-002/test-003 due to [reason]" and note any impact on inter-rater reliability calculations.

### Pattern 17: BH monotonicity enforcement comment errors (NEW in v3.0.0)
**Symptom:** Code comments describe Benjamini-Hochberg monotonicity enforcement incorrectly (e.g., "enforce monotonicity: each adjusted p must be >= the next smaller" when the algorithm actually enforces "each adjusted p must be <= the next larger")
**Root cause:** BH adjustment sorts p-values ascending, applies correction from largest to smallest, then enforces monotonicity by taking cumulative minimums (each value <= the one after it in the sorted order). Comments often get the direction wrong.
**Detection:** Read the actual BH implementation and verify comments match the algorithm direction.
**Fix:** Correct comments to accurately describe the monotonicity direction. The standard BH step-up procedure enforces: `p_adj[i] = min(p_adj[i], p_adj[i+1])` scanning right-to-left.

### Pattern 18: Consensus method description errors (NEW in v3.0.0)
**Symptom:** Paper describes judge consensus as "majority vote" but the actual implementation uses mean score thresholding
**Root cause:** Natural language shorthand ("majority") diverges from implementation (mean > threshold)
**Detection:** Read the grading/consensus code and compare with paper methodology section
**Fix:** Describe the actual method: "consensus score computed as the mean of N judge scores, with pass threshold at 0.5"

### Pattern 19: Pipeline pass classification vs threshold mismatch (NEW in v3.1.0)
**Symptom:** Paper defines pass as consensus_score > 0.5, but some runs with score > 0.5 are marked as failed (or vice versa)
**Root cause:** The evaluation pipeline pre-computes a `judge_passed` field using its own logic, which may not exactly match a simple score > 0.5 threshold. In ProjectScylla, 16/1080 (1.5%) of runs have this mismatch.
**Detection:** Compare `passed` column (from pipeline's `judge_passed`) against `consensus_score > 0.5` for every row:
```python
import csv
mismatches = 0
with open('data/runs.csv') as f:
    for row in csv.DictReader(f):
        passed = row['passed'].lower() == 'true'
        score_pass = float(row['consensus_score']) > 0.5
        if passed != score_pass:
            mismatches += 1
print(f'Mismatches: {mismatches}')
```
**Fix:** Add a footnote disclosing the mismatch rate and explaining that the pipeline's pre-computed classification is used for all reported pass rates.

### Pattern 20: Subtle cost rounding at third decimal place (NEW in v3.1.0)
**Symptom:** Paper reports $0.039 per run but actual mean is $0.038472; paper reports $0.099 but actual is $0.098453
**Root cause:** At 3 decimal places, the difference between rounding $0.0385 to $0.039 vs the correct $0.038 is subtle but accumulates across tables and cross-references
**Detection:** Recompute all per-run costs from `runs.csv` using `total_cost / count` and compare to 3 decimal places. Use `round(value, 3)` consistently.
**Fix:** Replace with correctly rounded values. After 3+ review rounds, cost rounding errors at the third decimal place are the most common remaining issue type.

### Pattern 21: Grading scale paper-vs-code mismatch (NEW in v4.0.0)
**Symptom:** Paper documents grading thresholds (e.g., S>=0.95, B>=0.65, C>=0.50, D>=0.35, F<0.35) but code uses different thresholds (e.g., S==1.00, B>=0.60, C>=0.40, D>=0.20, F<0.20)
**Root cause:** Paper grading scale was manually typed rather than derived from the code's `assign_letter_grade()` function
**Detection:** Compare code grade function against every row in runs.csv: `code_grade(score) == actual_grade` for all rows. Paper scale matched only 864/1080 rows while code scale matched 1080/1080.
**Fix:** Always derive grading scales from the code's actual grading function; never manually type thresholds
**Source file:** `src/scylla/metrics/grading.py:111-145` (the `assign_letter_grade` function)

### Pattern 22: Pass classification mechanism wrong — majority vote vs threshold (NEW in v4.0.0)
**Symptom:** Paper says "consensus score > 0.5" but actual mechanism is majority vote of judges' individual pass/fail decisions
**Root cause:** Paper described an intuitive threshold mechanism rather than the actual pipeline implementation
**Detection:** Compare `majority_vote(judge_passed)` against runs.csv `passed` column (0 mismatches) vs `consensus_score > 0.5` (16 mismatches). The 16 mismatches prove these are different mechanisms.
**Evidence:** score=0.487 with passed=True (2/3 judges passed, majority True despite score < 0.5); score=0.635 with passed=False (1/2 judges passed, not majority)
**Fix:** Read the actual pipeline code to determine pass classification logic; never assume threshold-based
**Rule:** When a paper says "score > X implies pass," verify this against every row. Even a few mismatches prove the mechanism is different from what's described.

### Pattern 23: Cliff's delta threshold convention mismatch — journal vs FAIR conference (NEW in v4.0.0)
**Symptom:** Paper cites Romano et al. 2006 with thresholds 0.147/0.33/0.474 but code uses 0.11/0.28/0.43
**Root cause:** Romano et al. published TWO papers in 2006 — a journal article (JEE, about SAT/ACT) with thresholds 0.147/0.33/0.474 and a FAIR conference paper (about NSSE) with thresholds 0.11/0.28/0.43. The code uses the FAIR thresholds but the paper cited the journal article.
**Impact:** Classification changes at boundaries — e.g., T3-T4 delta=-0.116 is "negligible" under journal thresholds but "small" under FAIR thresholds
**Detection:** grep codebase for actual threshold values in stats.py; compare against paper's stated values and bibliography entry
**Fix:** Ensure the bibliography entry matches the source whose thresholds are actually used in code. Update or add the correct bib entry.

### Pattern 24: Judge agreement N-value computed on pivoted/averaged data (NEW in v4.0.0)
**Symptom:** Paper says "computed on N=2,696 available judge evaluations" but actual computation uses pivot_table averaging across experiments, producing N=360 data points
**Root cause:** The analysis code (e.g., `detail.py:40-55`) uses `pivot_table` with `index=['tier', 'subtest', 'run_number']` WITHOUT the experiment dimension, which averages judge scores across experiments
**Detection:** Count unique `(tier, subtest, run_number)` combos in judges.csv = 360; compare vs total rows = 2,696
**Fix:** Describe the actual computation unit in the paper; if recomputing, include experiment in the pivot index to preserve individual evaluations
**Rule:** When a paper cites N for an agreement metric, verify whether the analysis code aggregates before computing. The raw row count and the aggregated unit count are often very different.

### Pattern 25: Column specifier off-by-one is systematic, not one-time (NEW in v4.0.0)
**Symptom:** `{llrrrrrrrr}` (10 specifiers) for a 9-column table; `{llrrrrrrrrrrr}` (13 specifiers) for a 12-column table
**Root cause:** Extra column specifiers added during table generation; LaTeX compiles without error but causes subtle spacing
**Detection:** Count header fields and match against tabular specifier string for ALL tables, not just the ones flagged in prior reviews
**Files:** tab05_cost_analysis.tex, tab08_summary_statistics.tex (in this session); tab03, line 718/774/826 (in v2.0.0)
**Note:** This pattern was already documented as Pattern 9 in v2.0.0 but recurred in DIFFERENT tables in v4.0.0, suggesting the generation pipeline has a systematic off-by-one issue. The fix should address the generation code, not just individual tables.

## Key Source Files for ProjectScylla Papers

| Claim type | Source file |
|------------|-------------|
| Individual run data (ground truth) | `docs/arxiv/haiku/data/runs.csv` |
| Experiment aggregates | `docs/arxiv/haiku/data/summary.json` |
| KW omnibus tests | `docs/arxiv/haiku/data/statistical_results.json` → `omnibus_tests` |
| Pairwise comparisons | `docs/arxiv/haiku/data/statistical_results.json` → `pairwise_comparisons` |
| Effect sizes | `docs/arxiv/haiku/data/statistical_results.json` → `effect_sizes` |
| SRH interaction tests | `docs/arxiv/haiku/data/srh_tier_experiment.json` |
| Inter-rater reliability | `docs/arxiv/haiku/data/judges.csv` |
| Per-criterion scores | `docs/arxiv/haiku/data/criteria.csv` |
| Per-subtest aggregates | `docs/arxiv/haiku/data/subtests.csv` |
| Generated LaTeX tables | `docs/arxiv/haiku/tables/*.tex` |
| Experiment totals (cost, duration) | `~/fullruns/haiku/<ts>-<test>/batch_summary.json` |
| Tier best scores/pass rates | `~/fullruns/haiku/<ts>-<test>/<TIER>/report.md` |
| Partial experiment state | `~/fullruns/haiku/<ts>-<test>/checkpoint.json` |
| Cliff's delta thresholds | `scylla/analysis/stats.py:260-264` |
| Pass threshold | `scylla/metrics/grading.py` (check for consensus_score threshold) |
| Consistency metric direction | `scylla/analysis/statistics.py:173` (1-CV formula, higher = more consistent) |
| Bootstrap config | `scylla/analysis/config.yaml:11-15` |
| Subtest YAML counts | `tests/claude-code/shared/subtests/<tier>/` |
| Grading scale (letter grades) | `src/scylla/metrics/grading.py:111-145` (assign_letter_grade function) |
| Judge agreement analysis | `scylla/analysis/detail.py:40-55` (pivot_table aggregation, check index columns) |
| Table generation (column specs) | `scylla/reporting/` (check tabular specifier generation for off-by-one) |

## Results & Parameters

### Session outcome v4.0.0 (2026-04-06)
- Paper: `docs/arxiv/haiku/paper.tex` (fifth review pass — 2,084 lines, 1,080 runs, 7 tiers, 3 experiments)
- Model: Opus 4.6 (1M context)
- Review approach: Consulted prior review skills (v3.1.0), then 3 parallel Explore agents (paper/data/stats), then myrmidon swarm (2 Sonnet professors + 3 Haiku students) for independent verification
- New patterns discovered: 5
  - Pattern 21: Grading scale paper-vs-code mismatch (paper scale matched 864/1080, code scale matched 1080/1080)
  - Pattern 22: Pass classification via majority vote, not threshold (16 mismatches prove difference)
  - Pattern 23: Cliff's delta FAIR vs journal convention (Romano et al. published TWO 2006 papers)
  - Pattern 24: Judge agreement N on pivoted data (360 units vs 2,696 raw rows)
  - Pattern 25: Column specifier off-by-one is systematic (recurred in different tables from v2.0.0)
- Myrmidon swarm results:
  - Haiku students: 100% stat match (39/39), column specifier issues found, false positives on CoP/consistency (wrong computation method)
  - Sonnet professors: pass rate definition conflict in Section 6.2, overclaims ("first" without hedge, causal language), T6 caveat needed, Pareto qualification needed
- Claims verified correct: 60+ (all tier-level and experiment-level pass rates, all SRH H-stats/df/p-values, all pairwise p-values, all Cliff's delta values, Krippendorff's alpha, Spearman rho, Pearson r, cost figures, CoP values)
- Build: `pixi run --environment docs paper-build` (clean)
- Verification level: verified-local
- PR: HomericIntelligence/ProjectScylla#1754

### Session outcome v3.1.0 (2026-04-06)
- Paper: `docs/arxiv/haiku/paper.tex` (fourth review pass, same N=3 data)
- Model: Opus 4.6 (1M context)
- Review approach: consulted 3 prior review skills from ProjectMnemosyne, then launched 3 parallel Explore agents
- Issues found and fixed: 4
  - T4 cost rounding: $0.039 -> $0.038 (actual $0.038472)
  - T5 cost rounding: $0.099 -> $0.098 (actual $0.098453)
  - 16 passed/score>0.5 mismatches: added footnote disclosing pipeline pre-computed pass classification
  - Bootstrap CI method unnamed: added "(BCa method, 10,000 resamples)"
- Claims verified correct: 60+ (all tier-level and experiment-level pass rates, all SRH H-stats/df/p-values, all pairwise p-values, all Cliff's delta values, Krippendorff's alpha, Spearman rho, Pearson r, cost figures, CoP values)
- No contractions, no raw Unicode, all cross-references resolve
- Metric direction verified in source code: consistency = 1-CV (statistics.py:173), higher = better
- Build: `pixi run --environment docs paper-build` (clean, 42035 bytes, 14 files)
- Verification level: verified-local
- False positives: 0 (prior review skills provided accurate guidance)

### Session outcome v3.0.0 (2026-04-06)
- Paper: `docs/arxiv/haiku/paper.tex` (N=3 experiment data refresh, 7 tiers, 3 experiments, 120 subtests)
- Review approach: phased — data accuracy first, then statistical methodology, then LaTeX quality
- Key findings:
  - Bootstrap CIs mislabeled as Clopper-Pearson throughout paper (critical)
  - 536 missing judge evaluations in test-001 vs test-002/test-003 (critical, undisclosed)
  - BH monotonicity enforcement comments incorrect in analysis code (important)
  - Consensus method described as "majority vote" but implemented as mean thresholding (important)
- Independent CI verification: computed Clopper-Pearson CIs using `scipy.stats.beta.ppf` and compared against paper values
- LaTeX engine compatibility: used `iftex` package with `\ifpdftex` guards to make preamble work with both pdflatex and tectonic/XeTeX
- Verification level: verified-local (tectonic builds paper to 50-page 978KB PDF)

### Session outcome v2.0.0 (2026-04-05)
- Paper: `docs/arxiv/haiku/paper.tex` (2,020 lines, 1,080 runs, 7 tiers, 3 experiments, $122.31 total)
- Critical issues found and fixed: 6
- Important issues found and fixed: 3
- Minor issues found and fixed: 1
- Claims verified correct: 30+
- Files changed: 4
- Review method: 3 parallel exploration agents + systematic cross-verification

### Session outcome v1.0.0 (2026-02-22)
- Paper: `docs/arxiv/haiku/paper.tex` (first draft, ~884 lines)
- Errors found and fixed: 6 (E1-E6)
- Warnings fixed: 4 (W1, W5, W6, W9)
- Warnings noted but not fixed: 5 (W2-W4, W7-W8 — either correct or low priority)
- Unverifiable: 3 (U1-U3)
- Verified correct: all batch summary figures, all per-test table values, all aggregate tier values, all KW stats

### Commit format
```
fix(research): correct factual errors in Haiku analysis paper

Apply accuracy review fixes to docs/arxiv/haiku/paper.tex:

Critical:
- KW/SRH table mixing: added Source column distinguishing test provenance
- Normality scope: "all 14 tier x metric" -> "all 14 tier x {Score, Cost}"
- Missing citation: added Romano et al. (2006) for Cliff's delta thresholds
- nan in table: removed "All Judges (Overall) & nan & nan & nan" row
- Extra column specifiers: {lrrrrrr} -> {lrrrrr} in 3 tables
- Cost rounding: $0.224 -> $0.226 for test-002

Important:
- Missing p-value: added Dunn's p=0.058 (n.s.) for T3->T4
- Best Tier ambiguity: added footnote defining criterion

Minor:
- Spacing from extra column specifier
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Haiku analysis paper v1.0.0 (2026-02-22) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v2.0.0 (2026-04-05) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v3.0.0 (2026-04-06) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v3.1.0 (2026-04-06) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v4.0.0 (2026-04-06) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Exploration agent claim about judges | Agent reported all judges used claude-opus-4-6 | Misread judges.csv — 3 distinct judge models were actually present | Always verify exploration agent claims against raw data before treating them as findings |
| Pass rate from raw score > 0 | Computed pass_rate as proportion of runs with score > 0 | Paper uses consensus_score > 0.5 as pass threshold, giving different rates (e.g., T3=0.783 vs correct 0.759) | Always verify the pass criterion definition in the methodology section before computing pass rates from raw data |
| Git diff for change verification | Used git diff to verify targeted edits | Working tree had 125 files / 170K+ lines of unstaged changes from prior experiment reruns; edits were lost in noise | In a dirty working tree, verify individual file content with Read rather than relying on git diff |
| Trusting CI labels without recomputation | Accepted paper's "Clopper-Pearson 95% CI" labels at face value | Independent computation with `scipy.stats.beta.ppf` showed values did not match; they were actually bootstrap percentile CIs | Always recompute confidence intervals independently; never trust labels without verification |
| Assuming complete judge evaluations | Did not initially count judge evaluations per experiment x tier | test-001 had 536 fewer evaluations than expected; this gap was undisclosed in the paper | Count evaluations per condition early in the review; missing data is a critical finding that affects all downstream statistics |
| Haiku student computing CoP incorrectly | Student 1 computed CoP as sum(cost_of_passed_runs)/count instead of mean_cost/pass_rate | Produced false positive discrepancies that required manual verification to dismiss | When delegating data verification to budget-class agents, provide the EXACT computation formula, not just "compute X from the data" |
| Haiku student computing consistency incorrectly | Student 1 computed consistency at run-level instead of subtest-level | Produced false positive discrepancies in consistency metrics | Same lesson: provide the exact formula and aggregation level |
