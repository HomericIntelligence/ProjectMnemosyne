---
name: latex-paper-accuracy-review
description: Review a LaTeX research paper for factual accuracy against raw experiment
  data, statistical outputs, and codebase constants before publication
category: documentation
date: 2026-04-08
version: 8.0.0
user-invocable: false
tags: [latex, paper, review, accuracy, statistics, data-verification, publication, confidence-intervals, iftex, rounding, BCa-bootstrap, pass-classification, grading-scale, majority-vote, cliffs-delta, myrmidon-swarm, causal-language, H-comparison, CI-rehabilitation, cross-reference-rename, abstract-conclusions-redundancy, prose-data-direction, duration-direction, pareto-dominance, consistently-contradiction, monotonic-degradation, eliminates-possibility, unobserved-mechanism, pareto-definite-article, BCa-binary-n9, alpha-aggregation, SRH-tie-correction, untracked-reproducibility-script, cross-section-regression, cost-invariance-overclaiming, build-script-format-mismatch, clopper-pearson-transcription]
---
# Skill: latex-paper-accuracy-review

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 (v1.0.0), 2026-04-05 (v2.0.0), 2026-04-06 (v3.0.0, v3.1.0, v4.0.0), 2026-04-07 (v5.0.0, v6.0.0), 2026-04-08 (v7.0.0, v8.0.0) |
| Category | documentation |
| Objective | Review a LaTeX research paper for factual accuracy against raw experiment data, statistical outputs, and codebase source files |
| Outcome | Eight successful sessions — v1.0.0 fixed 6 errors + 4 warnings in an 884-line first draft; v2.0.0 verified 30+ claims and fixed 6 critical + 3 important + 1 minor issue in a 2,020-line paper with 1,080 runs; v3.0.0 discovered bootstrap CIs mislabeled as Clopper-Pearson, 536 missing judge evaluations, and BH monotonicity comment errors; v3.1.0 found 2 cost rounding errors, 16 pass/score>0.5 mismatches, and unnamed bootstrap CI method; v4.0.0 found grading scale paper-vs-code mismatch (864/1080 rows), pass classification mechanism wrong (majority vote vs threshold), Cliff's delta FAIR vs journal convention, judge agreement N on pivoted data, and recurring column specifier off-by-one; v5.0.0 found causal language in observational study headings, H-statistic comparison across different df, non-significant result rehabilitated via uncorrected CI, undefined cross-reference from section rename, and abstract/conclusions near-verbatim redundancy; v6.0.0 found duration direction claim factually wrong (Cliff's delta sign misinterpreted), "consistently" contradicts "task-contingent" in same paragraph, "monotonic degradation" from non-monotonic per-task data, "spends computational budget" vs 17s fast-failure evidence, and Pareto-dominance asserted from non-significant cost difference. New pattern category: prose-data direction alignment. All 5 myrmidon agents achieved 0% false positive rate; v7.0.0 found cross-section regression (fixes not propagated across sections), "eliminates possibility" from non-significant result, unobserved mechanistic claim, BCa bootstrap for binary n=9, alpha on experiment-averaged data, and untracked reproducibility script; v8.0.0 found Clopper-Pearson upper bound wrong ([0.299, 0.901] should be [0.299, 0.925]), build script including wrong figure format (PDF vs PNG, submission blocker), cost invariance overclaiming in 4 summary sections, and H-statistic cross-df comparison reframed. All professors achieved 0% FP; Student 1 verified 126/126 correct (0% FP); Student 3 had ~7% FP from wrong aggregation method. |

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
- After 5+ review rounds when remaining issues shift from data accuracy to interpretive framing (causal language, statistical comparison validity, hedging consistency)
- When paper headings or findings use causal language ("causes", "drives") in an observational (non-randomized) study design
- When comparing test statistics (e.g., H-values) across terms with different degrees of freedom
- When a non-significant result (after multiple comparison correction) is rehabilitated using an uncorrected confidence interval
- When sections have been renamed during iterative editing and cross-references may be stale
- When the Abstract and Conclusions contain near-verbatim repetition of the same statistics
- When paper prose interprets the direction of an effect size (e.g., Cliff's delta sign) and the interpretation may be backwards
- When paper uses universality words ("consistently", "always", "invariably") adjacent to hedging words ("task-dependent", "contingent") creating logical contradictions
- When paper claims "monotonic" trends from aggregate data that may not hold per-experiment
- When paper describes resource consumption (e.g., "spends computational budget") but duration data suggests fast failures
- When paper asserts Pareto-dominance but one of the dimensions has a non-significant statistical test
- When summary sections (Abstract, Contributions, Further Work, Appendix) use stronger language than body sections for the same finding -- a sign of cross-section regression after prior hedging fixes
- When a build/submission script includes figure files by extension (e.g., `*.pdf`) that may not match the actual figure format (e.g., PNG)
- When Clopper-Pearson confidence intervals are reported and the upper bound may have been transcribed from a different confidence level (e.g., 90% CI upper bound used as 95%)

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

**What works well**: Sonnet professors catch higher-level framing and logic issues that mechanical checking misses (e.g., "first" without hedging, causal language, missing T6 caveats, Pareto qualification needed, pseudoreplication concerns, H-statistic comparison validity across different df).

**False positive tracking (NEW in v5.0.0, UPDATED in v6.0.0, v7.0.0, v8.0.0)**: Always verify agent claims before accepting them. In v5.0.0, Student 3 reported "7 critical undefined references" that were all false positives because the labels existed in `\input{}` table files that Haiku did not check. In v6.0.0, all 5 agents achieved 0% false positive rate due to: (1) explicit instructions to check `\input{}` files for labels, (2) providing EXACT formulas to Haiku students. In v7.0.0, Student 2 produced 15 FPs from wrong aggregation (ddof=0, raw vs pivoted). In v8.0.0, Student 3 produced ~7% FP on tab03 from computing Spearman/Pearson on raw judges.csv rows instead of pivoted/averaged data. False positive rates by task type:
- Haiku on mechanical number verification: 0% false positive (excellent, consistent across v5.0.0-v8.0.0; v8.0.0 Student 1 verified 126/126 correct)
- Haiku on computation-based verification (Spearman, Pearson, CoP): ~7-11% false positive when not given exact aggregation instructions (v7.0.0: 15/139 from ddof/pivot; v8.0.0: 9/132 from raw vs pivoted data)
- Haiku on structural analysis (cross-references, labels): ~50% false positive in v5.0.0, improved to 0% in v6.0.0 after adding `\input{}` check instructions
- Sonnet on higher-level methodology: 0% false positive (consistent across v6.0.0-v8.0.0; 0/7 and 0/10 in v7.0.0, maintained in v8.0.0)
- **Column name mismatch resilience**: Haiku students adapted correctly even when given wrong CSV column names in the prompt (consensus_score/total_cost instead of score/cost_usd) -- but this should be fixed in the prompt to avoid unnecessary adaptation overhead

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
runs.csv              # Ground truth: individual run data (columns: score, cost_usd, duration_seconds, passed, etc.)
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

### Pattern 26: Causal language in observational study headings (NEW in v5.0.0)
**Symptom:** A finding heading says "X causes Y" but the paper's own threats-to-validity section acknowledges confounded design (non-randomized tier assignment)
**Root cause:** Internal contradiction between a heading's causal assertion and the body text's caveats. Headings are often written assertively for readability without checking consistency with the limitations section.
**Detection:** Grep for "cause", "drives", "leads to", "results in" in section headings and finding titles; cross-check against the threats/limitations section for confounding acknowledgments
**Fix:** Use "is associated with" or "correlates with" in headings; reserve "causes" for experimental (randomized) designs. If the paper's own limitations section acknowledges confounding, causal language anywhere in the paper is an internal contradiction.

### Pattern 27: H-statistic comparison across different degrees of freedom (NEW in v5.0.0)
**Symptom:** Paper compares SRH interaction H=223.5 (df=12) against main effect H=91.3 (df=6) and calls the interaction the "largest effect"
**Root cause:** Raw H-values from Kruskal-Wallis or SRH tests are not comparable across terms with different degrees of freedom. Each H is compared to its own chi-squared distribution with its own df. A larger H with more df does not necessarily indicate a stronger effect.
**Detection:** Look for comparisons of H-statistics across terms; verify that the terms have the same df before accepting relative magnitude claims
**Fix:** Add a df caveat when comparing H-statistics (e.g., "H=223.5, df=12 vs H=91.3, df=6; note that raw H-values are not directly comparable across different df"), or use SS decomposition (sum-of-squares) for proper effect size comparison across terms.

### Pattern 28: Non-significant result rehabilitated via uncorrected CI (NEW in v5.0.0)
**Symptom:** A pairwise comparison is p=0.058 (non-significant after Holm correction), but the paper then uses "bootstrap CI excluding zero" to claim the effect exists
**Root cause:** The bootstrap CI is uncorrected for multiple comparisons. A CI consistent with the Holm-corrected test would be wider and would include zero. Using an uncorrected CI to rehabilitate a result that failed a corrected test is methodologically inconsistent.
**Detection:** When a pairwise test is non-significant after correction, check whether the paper uses an uncorrected CI to claim the effect anyway. The CI and the hypothesis test must use the same correction level.
**Fix:** Either (a) present the CI as uncorrected and note that it is not adjusted for multiple comparisons, without claiming the effect exists, or (b) compute a Bonferroni/Holm-adjusted CI that is consistent with the corrected test. Cannot simultaneously call a test non-significant and use an uncorrected CI to claim the effect.

### Pattern 29: Undefined cross-reference from section rename (NEW in v5.0.0)
**Symptom:** `\ref{sec:aggregate}` references a section that was later renamed to `sec:cross_task`, producing undefined reference warnings or wrong section numbers
**Root cause:** A common artifact of iterative editing — when a `\label{}` is changed to reflect a new section name, all `\ref{}` calls to the old label must also be updated. This is easy to miss in a large document.
**Detection:** After renaming any `\label{}`, grep for all `\ref{}` and `\autoref{}` calls to the old label name. Also check `\input{}` files for cross-references.
**Fix:** Rename the label and update all references. Use `grep -rn 'sec:old_name' *.tex tables/*.tex` to find all occurrences.

### Pattern 30: Abstract/Conclusions near-verbatim redundancy (NEW in v5.0.0)
**Symptom:** The same statistics appear word-for-word in both the Abstract and Conclusions sections (e.g., identical sentences with the same numbers, same phrasing)
**Root cause:** Copy-paste from Abstract to Conclusions (or vice versa) during writing, without rephrasing for the different rhetorical purpose of each section
**Detection:** Compare the Abstract and Conclusions side by side; flag any sentences that share >80% of their words
**Fix:** The Abstract should state results concisely for readers deciding whether to read the paper. The Conclusions should synthesize findings, discuss implications, and add interpretive insight. Conclusions should use interpretive language referencing findings (e.g., "These results suggest...") rather than restating raw statistics verbatim.

### Pattern 31: Duration direction claim factually wrong (NEW in v6.0.0)
**Symptom:** Paper said "Delegation-based tiers tend to run longer" but data shows T2 mean=362.7s vs T3 mean=247.8s (T3 runs SHORTER)
**Root cause:** Cliff's delta=-0.154 for T2->T3 means T3 is stochastically shorter, not longer. T4-T6 on test-001 complete in ~17s (immediate orchestration failures) vs T0-T2 taking 430-505s. The negative delta reflects the fast-failure mode pulling delegation tier durations down.
**Detection:** Always verify the direction interpretation of Cliff's delta -- a negative delta for group1->group2 means group2 has stochastically LOWER values, not higher
**Fix:** Correct to "T3 runs are stochastically shorter than T2, driven partly by rapid failures"
**Category:** Prose-data direction alignment -- the prose draws the OPPOSITE conclusion from what the data shows, not because the numbers are wrong, but because the interpretation is backwards

### Pattern 32: "Consistently" contradicts "task-contingent" in same paragraph (NEW in v6.0.0)
**Symptom:** Abstract said "simpler architectures consistently outperform" then immediately "task-contingent rather than universally applied"
**Root cause:** "Consistently" implies universality; "task-contingent" denies universality -- logical contradiction. test-002 shows monotonic POSITIVE trend (T0=0.903 -> T6=1.000), directly contradicting "consistently"
**Detection:** Search for universality words ("consistently", "always", "invariably") near hedging words ("task-dependent", "contingent") -- they create logical contradictions
**Fix:** Changed to "outperform in aggregate, though task-dependent effects are strong"
**Category:** Prose-data direction alignment -- adjacent sentences make logically incompatible claims

### Pattern 33: "Monotonic degradation" from non-monotonic data (NEW in v6.0.0)
**Symptom:** Paper claimed "monotonic degradation across the full tier spectrum" for T0->T6 aggregate
**Root cause:** test-002 shows monotonic IMPROVEMENT, and test-003 shows near-flat performance. The aggregate is monotonic only because test-001's catastrophic T3-T6 failures dominate.
**Detection:** When a paper claims "monotonic" for aggregate data, check per-experiment trends. An aggregate monotonic trend can mask non-monotonic per-experiment behavior.
**Fix:** Changed to "negative in aggregate, though not monotonic across all tasks"
**Category:** Prose-data direction alignment -- aggregate trend does not represent individual experiment behavior

### Pattern 34: "Spends computational budget" vs fast-failure evidence (NEW in v6.0.0)
**Symptom:** Paper said agent "spends its computational budget managing delegation" for T4-T6 on test-001
**Root cause:** T4-T6 complete in mean ~17s with zero evaluable output, while T0-T2 take 430-505s. 17s is consistent with immediate orchestration setup error, NOT with spending computational budget.
**Detection:** Cross-check prose claims about resource consumption against duration data. If a tier completes in <30s with zero output, it did not "spend" anything -- it failed immediately.
**Fix:** Changed to "encounters a fatal orchestration error immediately rather than exhausting its computational budget"
**Category:** Prose-data direction alignment -- prose describes slow resource consumption when data shows instant failure

### Pattern 35: Pareto-dominance asserted from non-significant cost difference (NEW in v6.0.0)
**Symptom:** Paper asserted "strictly Pareto-dominant" and "Pareto-dominated" at 3 locations
**Root cause:** Cost invariance is p=0.676 (non-significant under limited power). Cannot claim Pareto dominance on a dimension where the null hypothesis is not rejected. Additionally, T2 is NOT Pareto-optimal for test-002 (T5 dominates with same pass rate, lower CoP).
**Detection:** When "Pareto" language appears, verify both dimensions are established (one significant, one at least equal). If either dimension has a non-significant test, Pareto dominance is not established.
**Fix:** Added "$p=0.676$, non-significant" caveats and per-task exceptions at all 3 locations
**Category:** Prose-data direction alignment -- claiming dominance from a non-significant statistical test

### Pattern 36: Cross-section regression from prior fix (NEW in v7.0.0)
**Symptom:** Abstract was fixed in v6 to say "outperform in aggregate" but Conclusions still said "consistently outperform"
**Root cause:** When fixing a word in one section, the same word in other sections (Abstract, Introduction, Discussion, Conclusions) may not be updated. Each section is edited independently and prior fixes can be missed.
**Detection:** After any hedging fix, grep for the old phrasing across ALL sections. Use `grep -n 'old_word' paper.tex` to find all occurrences.
**Fix:** Changed Conclusions to match Abstract: "outperform in aggregate" with task-dependent reversal note
**Category:** Cross-section regression -- a fix applied to one section creates an inconsistency with other sections that use the same language

### Pattern 37: "Eliminates the possibility" from non-significant result (NEW in v7.0.0)
**Symptom:** Paper said non-significant cost finding "eliminates the possibility of a cost--quality trade-off" and calls quality degradation "a pure loss"
**Root cause:** A non-significant result under low power does not eliminate the possibility -- it merely fails to detect a difference. The paper's own Limitations section acknowledged this, creating an internal contradiction.
**Detection:** When a null/n.s. finding is described as "eliminating" or "ruling out" something, verify the power analysis supports such strong language
**Fix:** Changed to "provides no evidence of a cost--quality trade-off under current statistical power" and "appears as a net loss with no detected compensating benefit"

### Pattern 38: Unobserved mechanistic claim in observational study (NEW in v7.0.0)
**Symptom:** Paper claimed coordination overhead is "not additive but multiplicative" -- positing a specific functional form from observational data
**Root cause:** The study observes a zero pass rate but cannot distinguish additive from multiplicative failure mechanisms. The mechanistic claim goes beyond what the data can support.
**Detection:** Look for claims about HOW something works (mechanism) vs WHAT was observed (association). Mechanistic claims require experimental manipulation, not just observation.
**Fix:** Changed to threshold/catastrophic framing with "the specific failure mechanism cannot be determined from observational data alone"

### Pattern 39: Definite article for one-of-many Pareto-optimal tiers (NEW in v7.0.0)
**Symptom:** Paper said T2 is "the aggregate Pareto-optimal tier" but T0 and T1 are also on the Pareto frontier
**Root cause:** When multiple tiers are Pareto-optimal, using "the" implies singularity. T2 is the highest-pass-rate Pareto-optimal tier, but not the only one.
**Detection:** When Pareto language uses "the," verify the tier is uniquely optimal, not one of several
**Fix:** Changed to "the highest-pass-rate Pareto-optimal tier in the aggregate data (T0 and T1 also lie on the Pareto frontier at similar costs)"

### Pattern 40: BCa bootstrap for binary data at very small n (NEW in v7.0.0)
**Symptom:** Paper used BCa bootstrap CI [0.333, 0.889] for T6 pass rate with n=9 binary observations without noting BCa-specific limitations
**Root cause:** BCa bootstrap has poor coverage properties for binary data at n=9 because the jackknife influence values are degenerate. The Clopper-Pearson exact interval is methodologically more appropriate.
**Detection:** When bootstrap CIs are reported for binary outcomes at n<20, check whether the BCa method's small-sample limitations are acknowledged
**Fix:** Added note about BCa coverage properties and Clopper-Pearson exact interval [0.299, 0.901] for comparison

### Pattern 41: Krippendorff alpha computed on experiment-averaged data (NEW in v7.0.0)
**Symptom:** Paper reported alpha on N=360 scores averaged across experiments, without noting that averaging conflates inter-experiment variability with inter-rater disagreement
**Root cause:** The analysis code pivots by (tier, subtest, run_number) WITHOUT experiment, causing mean aggregation across experiments. This is a valid methodological choice but changes what alpha measures.
**Detection:** When alpha is reported with a specific N, verify the aggregation unit and whether averaging across conditions was performed
**Fix:** Added disclosure noting the averaging and its methodological implication

### Pattern 42: Untracked script producing paper's central finding (NEW in v7.0.0)
**Symptom:** `scripts/analyze_tier_task_interaction.py` was untracked in git despite being the source of the paper's SRH tier×experiment interaction results (H=223.5)
**Root cause:** The main export pipeline (`export_data.py`) runs SRH with agent_model as factor_a, which degenerates with a single model. A separate script was written for the correct tier×experiment analysis but never committed.
**Detection:** For every data file cited in the paper's reproducibility section, verify the generating script is tracked in version control
**Fix:** Committed the script to the repository

### Pattern 43: Cost invariance overclaiming persists in summary sections after body is fixed (NEW in v8.0.0)
**Symptom:** Body sections properly hedge cost invariance with "non-significant under limited power" but 4 high-visibility summary locations (Abstract, Contributions, Appendix, Further Work) still use strong/unhedged language ("show", "establishing", "explains why invariant")
**Root cause:** When body sections are fixed to add hedging during one review round, summary sections that reference the same finding are not updated. This is a specific instance of Pattern 36 (cross-section regression) that targets non-significant results where overclaiming is particularly problematic.
**Detection:** After fixing hedging language for any non-significant result in body sections, grep for the finding's keywords across ALL sections. Summary sections (Abstract, Introduction contributions list, Appendix summaries, Further Work) are the most common locations for regression.
**Fix:** Propagate identical hedging to all summary sections. Use the same qualifier ("non-significant under limited power") everywhere the finding is referenced.
**Category:** Cross-section regression -- variant of Pattern 36 specifically for non-significant results

### Pattern 44: Build script includes wrong figure file format (NEW in v8.0.0)
**Symptom:** `build.sh` line 121 used `figures/*.pdf` glob but all 71 figures in the directory are PNG files, resulting in a submission tarball containing ZERO figure files
**Root cause:** Build script was written assuming PDF figures (common for LaTeX workflows) but the actual figure generation pipeline produces PNG. The mismatch went undetected because the LaTeX compilation uses `\includegraphics` which finds the files regardless of what the build script packages.
**Detection:** Verify the build/packaging script's file glob patterns against the actual file formats in the figures directory. Run `ls figures/ | head` to check actual extensions, then grep the build script for file extension patterns.
**Fix:** Change the glob pattern in the build script to match the actual figure format (e.g., `figures/*.png` instead of `figures/*.pdf`)
**Category:** Submission blocker -- paper compiles fine but the packaged tarball is incomplete

### Pattern 45: Clopper-Pearson confidence interval transcription error (NEW in v8.0.0)
**Symptom:** Paper reported Clopper-Pearson 95% CI as [0.299, 0.901] for 6/9 successes, but `scipy.stats.beta.ppf(0.975, 7, 3)` = 0.9251, giving correct interval [0.299, 0.925]. Error of 0.024 on the upper bound.
**Root cause:** The value 0.901 corresponds approximately to a 90% CI upper bound (`beta.ppf(0.95, 7, 3)` ≈ 0.901), suggesting transcription from the wrong confidence level. The qualitative conclusion is unaffected but exact intervals must be exact.
**Detection:** Always independently recompute Clopper-Pearson intervals using `scipy.stats.beta.ppf(alpha/2, k, n-k+1)` and `beta.ppf(1-alpha/2, k+1, n-k)`. Compare to 3 decimal places. Watch specifically for values that match a different confidence level (90% vs 95%).
**Fix:** Replace with correctly computed values. For 6/9 at 95%: [0.299, 0.925].
**Verification script:**
```python
from scipy.stats import beta as beta_dist
k, n = 6, 9
lo = beta_dist.ppf(0.025, k, n - k + 1)  # 0.2993
hi = beta_dist.ppf(0.975, k + 1, n - k)   # 0.9251
print(f'Clopper-Pearson 95% CI: [{lo:.3f}, {hi:.3f}]')
```

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

### Session outcome v8.0.0 (2026-04-08)
- Paper: `docs/arxiv/haiku/paper.tex` (ninth review pass -- 2,176 lines post-v7, 1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
- Model: Opus 4.6 (1M context)
- Review approach: Consulted prior review skills (v7.0.0), 3 parallel Explore agents, then full myrmidon swarm (2 Sonnet professors + 3 Haiku students + 1 Sonnet code reviewer + 1 Haiku health checker)
- New pattern category: **cost invariance overclaiming** -- non-significant results described with unhedged language in summary sections after body sections were fixed
- New patterns discovered: 3
  - Pattern 43: Cost invariance overclaiming persists in summary sections (Abstract, Contributions, Appendix, Further Work used "show"/"establishing"/"explains why invariant" while body properly hedged)
  - Pattern 44: Build script includes wrong figure format (PDF glob vs PNG files, submission blocker -- tarball had ZERO figures)
  - Pattern 45: Clopper-Pearson transcription error ([0.299, 0.901] should be [0.299, 0.925] for 6/9 at 95% -- upper bound from wrong confidence level)
- Myrmidon swarm results:
  - Professor 1 (Sonnet): 0% FP (maintained)
  - Professor 2 (Sonnet): 0% FP (maintained)
  - Student 1 (Haiku, inline numbers): 126/126 verified correct; 0% FP
  - Student 2 (Haiku, cross-references): all checks pass; 0% FP
  - Student 3 (Haiku, tables): 123/132 match, ~7% FP on tab03 (computed Spearman/Pearson on raw judges.csv rows instead of pivoted/averaged data -- discrepancies of 0.29-0.39 on Spearman)
  - Code Review (Sonnet): no bugs affecting paper correctness; SRH, bootstrap (BCa, 10k, seed=42), Cliff's delta (FAIR 0.11/0.28/0.43), grade scale all verified correct
  - Health Check (Haiku): PASS
- Independent verification: Holm correction confirmed p=0.01763 for T0-T6
- H-statistic cross-df comparison reframed: removed ranking by raw H across different df, reframed to "all three effects significant at p<0.001"
- Latent code bug noted: export_data.py SRH degenerates with single-model data (df_a=0) but paper uses separate script
- Edits applied: 10 (3 critical, 5 important, 1 minor, 1 build script)
- Build: verified clean diff (+35/-31 lines)
- Verification level: verified-local (pre-commit infrastructure issues prevented full hook run)
- Decision: Conditional Go -> Go after fixes

### Session outcome v7.0.0 (2026-04-08)
- Paper: `docs/arxiv/haiku/paper.tex` (eighth review pass -- 1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
- Model: Opus 4.6 (1M context)
- Review approach: Consulted prior review skills (v6.0.0), 3 parallel Explore agents, then full myrmidon swarm (2 Sonnet professors + 3 Haiku students) + 3 implementation reviewers (Sonnet code review, Sonnet strict pipeline, Haiku health check)
- New pattern category: **cross-section regression** -- where a fix applied in one section creates an inconsistency with other sections using the same language
- New patterns discovered: 7
  - Pattern 36: Cross-section regression from prior fix ("consistently" fixed in Abstract but not Conclusions)
  - Pattern 37: "Eliminates the possibility" from non-significant result (overstated null under low power)
  - Pattern 38: Unobserved mechanistic claim ("not additive but multiplicative") in observational study
  - Pattern 39: Definite article for one-of-many Pareto-optimal tiers ("the" → "a/the highest-pass-rate")
  - Pattern 40: BCa bootstrap for binary data at very small n (n=9, poor coverage properties)
  - Pattern 41: Krippendorff alpha computed on experiment-averaged data (conflates variability sources)
  - Pattern 42: Untracked script producing paper's central finding (reproducibility failure)
- Myrmidon swarm results:
  - Professor 1 (Sonnet, statistical methodology): BCa n=9, alpha aggregation, untracked script, SRH ties; 0/7 (0% FP)
  - Professor 2 (Sonnet, narrative consistency): "consistently" regression, "eliminates possibility", "multiplicative", Pareto article, "two-cluster", Finding titles, Abstract-Conclusions overlap; 0/10 (0% FP)
  - Student 1 (Haiku, inline number verification): 43/43 match after FP dismissal; 1 FP (misread line attribution)
  - Student 2 (Haiku, table cross-check): 139 cells, 15 FPs from wrong computation method (ddof=0 vs ddof=1, raw vs pivoted); 0 real mismatches after independent verification
  - Student 3 (Haiku, appendix/figure verification): 56/56 verified; 0% FP
  - Code Review (Sonnet): SRH negative ss_ab, Holm docstring error; Cliff's delta, Pareto, bootstrap, pass classification all verified correct
  - Strict Pipeline (Sonnet): Grade B-, is_valid parsing bug (latent, all data has is_valid=True), N/A-as-zero in impl_rate
  - Health Check (Haiku): PASS, no showstoppers
- Key improvement over v6.0.0: (1) Haiku FP rate for computation-based tasks remains problematic when not given exact formulas/parameters (ddof, pivot method), (2) cross-section regression is a new error class not previously catalogued, (3) implementation review found latent code bugs that don't affect current paper but could affect future papers
- Edits applied: 10 edits across CRITICAL (1), IMPORTANT (6), MINOR (3) severity levels
- Build: `pixi run --environment docs paper-build` (clean, 991,600 bytes, 14 files, 51 pages)
- Verification level: verified-local
- PR: HomericIntelligence/ProjectScylla#1756

### Session outcome v6.0.0 (2026-04-07)
- Paper: `docs/arxiv/haiku/paper.tex` (seventh review pass -- 1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
- Model: Opus 4.6 (1M context)
- Review approach: Consulted prior review skills (v5.0.0), 3 parallel Explore agents, then full myrmidon swarm (2 Sonnet professors + 3 Haiku students) with systematic false positive tracking
- New pattern category: **prose-data direction alignment** -- where the prose draws the OPPOSITE conclusion from what the data shows, not because the numbers are wrong, but because the interpretation is backwards
- New patterns discovered: 5
  - Pattern 31: Duration direction claim factually wrong (Cliff's delta sign misinterpreted -- T3 runs SHORTER, not longer)
  - Pattern 32: "Consistently" contradicts "task-contingent" in same paragraph (logical contradiction in Abstract)
  - Pattern 33: "Monotonic degradation" from non-monotonic per-task data (aggregate masks individual behavior)
  - Pattern 34: "Spends computational budget" vs 17s fast-failure evidence (instant failure, not slow consumption)
  - Pattern 35: Pareto-dominance asserted from non-significant cost difference (p=0.676, not established)
- Myrmidon swarm results (all 5 agents achieved 0% false positive rate):
  - Professor 1 (Sonnet, statistical methodology): H-stat rounding 91.34/91.3, CI/p tension, KW on binary, Pareto from n.s., "simpler is better" overgeneralization; 0/7 (0% FP)
  - Professor 2 (Sonnet, logical consistency): Duration direction WRONG, "consistently" contradiction, test-002 underexplained, 17s fast failures, T0-ST00 anomaly, task classifier unsupported, alpha implications; 0/11 (0% FP)
  - Student 1 (Haiku, inline table verification): 104/105 match, 1 CoP rounding (test-003 T5: 0.106->0.105); 0% FP
  - Student 2 (Haiku, summary/stats verification): 61/61 match, all KW/SRH/pairwise values correct; 0% FP
  - Student 3 (Haiku, LaTeX quality): 120/120 structural elements clean; 0% FP
- Key improvements over v5.0.0: (1) explicit `\input{}` check instructions eliminated Haiku structural FPs, (2) EXACT formulas for Haiku students, (3) Professor 2's duration verification was most valuable finding
- Edits applied: 14 edits across CRITICAL (3), IMPORTANT (7), MINOR (3) severity levels
- Build: `pixi run --environment docs paper-build` (clean, 43,228 bytes, 14 files)
- Verification level: verified-local
- PR: HomericIntelligence/ProjectScylla (fix-paper-accuracy-v5 branch)

### Session outcome v5.0.0 (2026-04-07)
- Paper: `docs/arxiv/haiku/paper.tex` (sixth review pass -- 1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
- Model: Opus 4.6 (1M context)
- Review approach: Consulted prior review skills (v4.0.0), then 3 parallel Explore agents (paper text, source data, LaTeX structure), then full myrmidon swarm (2 Sonnet professors + 3 Haiku students) with systematic false positive tracking
- New patterns discovered: 5
  - Pattern 26: Causal language in observational study headings (heading said "causes" but threats section acknowledged confounded design)
  - Pattern 27: H-statistic comparison across different df (H=223.5 df=12 vs H=91.3 df=6 not directly comparable)
  - Pattern 28: Non-significant result rehabilitated via uncorrected CI (T3-T4 p=0.058 n.s. after Holm, but uncorrected bootstrap CI used to claim effect)
  - Pattern 29: Undefined cross-reference from section rename (`\ref{sec:aggregate}` referenced renamed `sec:cross_task`)
  - Pattern 30: Abstract/Conclusions near-verbatim redundancy (same statistics repeated word-for-word)
- Myrmidon swarm results:
  - Professor 1 (Sonnet, statistical methodology): pseudoreplication concern, causal language, H-comparison issue, T3-T4 CI inconsistency; low false positive (1 debatable of 8)
  - Professor 2 (Sonnet, experimental design): Cliff driven by 1 task, impl_rate bias, criteria cross-experiment, T6 overanalysis; low false positive (0 of 19)
  - Student 1 (Haiku, tier table verification): 140/140 cells verified correct; 0% false positive
  - Student 2 (Haiku, SRH/pairwise verification): all KW, SRH, pairwise, effect sizes verified correct; 0% false positive
  - Student 3 (Haiku, LaTeX quality): found sec:aggregate issue; but 7 "critical" undefined refs were FALSE POSITIVES (~50% false positive on structural analysis)
- Key shift: After 5 prior rounds, remaining issues shifted from data accuracy to interpretive framing (causal language, statistical comparison validity, hedging consistency)
- Build: `pixi run --environment docs paper-build` (clean)
- Verification level: verified-local
- PR: HomericIntelligence/ProjectScylla (fix-paper-accuracy-v5 branch)

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
| ProjectScylla | Haiku analysis paper v5.0.0 (2026-04-07) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v6.0.0 (2026-04-07) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v7.0.0 (2026-04-08) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |
| ProjectScylla | Haiku analysis paper v8.0.0 (2026-04-08) | [notes.md](../skills/latex-paper-accuracy-review.notes.md) |

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
| Haiku student reporting false positive undefined references | Student 3 reported 7 "critical" undefined `\ref{}` targets | Labels existed in `\input{}` table files that Haiku did not check | When Haiku students check LaTeX cross-references, explicitly instruct them to also check `\input{}` files for `\label{}` definitions |
| Using uncorrected CI to rehabilitate non-significant test | Tried to claim T3-T4 effect via "bootstrap CI excluding zero" after Holm correction showed p=0.058 (n.s.) | The bootstrap CI is uncorrected for multiple comparisons; a Holm-consistent CI would include zero | CI and hypothesis test must use the same multiple comparison correction level; cannot mix corrected test with uncorrected CI |
| Initial prompt gave wrong CSV column names | Prompt specified `consensus_score` and `total_cost` as column names for runs.csv | Actual column names are `score` and `cost_usd`; Haiku students adapted but had to infer the mapping | Always verify CSV column names before writing myrmidon prompts; use `head -1 data/runs.csv` to get actual headers |
| Phase 1 source data agent miscounted pass/score mismatches | Agent reported 12 passed-vs-score>0.5 mismatches | Correct count is 16 (already known from v3.1.0 calibration); agent used wrong threshold or subset | Always calibrate Phase 1 exploration results against known ground truth from prior review rounds before trusting them |
| Student 3 tab03 false positives from wrong aggregation | Student 3 computed Spearman/Pearson on raw judges.csv rows | Should have pivoted/averaged data first; discrepancies of 0.29-0.39 on Spearman were all FPs | Consistent with v7 finding: Haiku students produce ~7-11% FP when not given exact computation instructions including aggregation method |
| Clopper-Pearson upper bound transcribed from wrong CI level | Paper reported [0.299, 0.901] for 6/9 at 95% | 0.901 matches 90% CI upper bound; correct 95% is 0.925 | Always recompute CIs independently at the stated confidence level; watch for values matching a different alpha |
| Build script packaging zero figures | build.sh used `figures/*.pdf` glob | All 71 figures are PNG; tarball contained zero figure files | Verify build script globs against actual file formats before submission |
