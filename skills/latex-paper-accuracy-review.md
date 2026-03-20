---
name: latex-paper-accuracy-review
description: Review a LaTeX research paper for factual accuracy against raw experiment
  data, statistical outputs, and codebase constants before publication
category: documentation
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Skill: latex-paper-accuracy-review

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Category | research |
| Objective | Review a LaTeX research paper for factual accuracy against raw experiment data, statistical outputs, and codebase source files |
| Outcome | Success — 6 errors (E1–E6) and 4 warnings (W1, W5, W6, W9) identified and fixed in a single session |

## When to Use

- Before submitting a research paper for publication or arXiv upload
- When paper prose or statistics may diverge from raw experiment data
- When code and paper share constants/thresholds that must stay consistent
- After a long paper-writing session where numbers were typed manually from reports
- When partial/incomplete experiments are referenced in a paper

## Verified Workflow

### Step 1: Build the accuracy review plan

Use a subagent (Plan or Explore) to cross-check every quantitative claim in the paper against source data. Organize findings into three tiers:

- **ERRORS** — must fix before publication (factual errors, contradictions, arithmetic mistakes)
- **WARNINGS** — should fix (imprecision, inconsistency, misleading framing)
- **UNVERIFIABLE** — note what cannot be checked without external data
- **VERIFIED OK** — explicitly confirm correct values to build confidence

For each ISSUE record:
- Exact location (section, line numbers)
- The claim as written
- The actual value from source
- The source file/path
- The specific fix required

### Step 2: Prioritize fixes

Apply in this order:
1. Arithmetic errors (wrong totals, sums)
2. Claims directly contradicted by the paper's own tables
3. Fabricated/extrapolated data for incomplete experiments
4. Code/paper constant mismatches (thresholds, formulas)
5. Overly broad claims that don't hold across all cases
6. Statistical test attribution errors (which test produced which stat)
7. Normality/distribution blanket claims with exceptions

### Step 3: Apply fixes systematically

Use `Edit` tool with exact string replacement. For each fix:
- Replace the exact wrong text
- Verify with `Grep` that old text is gone
- Read the changed section to confirm correctness

### Step 4: Commit

Conventional commit with full list of E/W items fixed in the message body.

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
**Symptom:** Cliff's δ thresholds in paper (0.147/0.330/0.474) differ from code (0.11/0.28/0.43)  
**Root cause:** Two different published conventions exist (Cohen-derived vs Romano et al. 2006); paper used wrong one  
**Fix:** Always grep the codebase for the actual thresholds used (`scylla/analysis/stats.py`); cite Romano et al. 2006 for ProjectScylla  
**Correct thresholds (Romano et al. 2006):** negligible <0.11, small <0.28, medium <0.43, large ≥0.43

### Pattern 5: Fabricated partial experiment results
**Symptom:** "T1 achieves 0.83 at 100% pass rate" for a test that only has 1 run completed  
**Root cause:** Extrapolating from expected pattern rather than reading checkpoint.json  
**Fix:** Always read `checkpoint.json` for partial experiments; only report what is actually in the checkpoint  
**Source files:** `~/fullruns/haiku/<timestamp>-<test-id>/checkpoint.json`

### Pattern 6: Statistical test attribution
**Symptom:** "Score: H(6) = 22.63, p = 0.0009" listed under Kruskal-Wallis omnibus — but score isn't in the KW omnibus  
**Root cause:** The stat actually comes from Scheirer-Ray-Hare interaction test tier effect  
**Fix:** Check `data/statistical_results.json` — `omnibus_tests` array (KW) vs `interaction_tests` array (SRH)  
**Rule:** KW omnibus tests: pass_rate, impl_rate, duration, cost. Score tested via SRH tier effect.

### Pattern 7: Blanket normality claim with exceptions
**Symptom:** "All tier/metric combinations failed Shapiro-Wilk (p < 0.001)" — T6 actually passes  
**Root cause:** T6 has n=15 (small); SW test is underpowered at small n, returns high p-values  
**Fix:** "Nearly all... T6 score (p=0.329) and T6 cost (p=0.177) passed normality (n=15); non-parametric applied throughout for consistency"

### Pattern 8: Understated cost ratios
**Symptom:** "T3/T4 cost 3.5–4× more than T1/T2" — some pairs are 7×  
**Root cause:** Author computed one favorable comparison (T3/T1=3.55×) and generalized  
**Fix:** Compute all four cross-products (T3/T1, T3/T2, T4/T1, T4/T2) and report the full range or all pairs

## Key Source Files for ProjectScylla Papers

| Claim type | Source file |
|------------|-------------|
| Experiment totals (cost, duration) | `~/fullruns/haiku/<ts>-<test>/batch_summary.json` |
| Tier best scores/pass rates | `~/fullruns/haiku/<ts>-<test>/<TIER>/report.md` |
| Subtest-level results | `~/fullruns/haiku/<ts>-<test>/<TIER>/<subtest>/report.md` |
| Partial experiment state | `~/fullruns/haiku/<ts>-<test>/checkpoint.json` |
| Aggregate tier statistics | `docs/arxiv/haiku/data/tab01_tier_summary.md` |
| Pairwise statistics | `docs/arxiv/haiku/data/tab02_pairwise_comparisons.md` |
| Statistical test outputs | `docs/arxiv/haiku/data/statistical_results.json` |
| Cliff's δ thresholds | `scylla/analysis/stats.py:260-264` |
| Pass threshold (0.60) | `scylla/metrics/grading.py:13` |
| Bootstrap config | `scylla/analysis/config.yaml:11-15` |
| Subtest YAML counts | `tests/claude-code/shared/subtests/<tier>/` |

## Results & Parameters

### Session outcome (2026-02-22)
- Paper: `docs/arxiv/haiku/paper.tex` (first draft, ~884 lines)
- Errors found and fixed: 6 (E1–E6)
- Warnings fixed: 4 (W1, W5, W6, W9)
- Warnings noted but not fixed: 5 (W2–W4, W7–W8 — either correct or low priority)
- Unverifiable: 3 (U1–U3)
- Verified correct: all batch summary figures, all per-test table values, all aggregate tier values, all KW stats

### Commit format
```
fix(research): correct factual errors and warnings in Haiku analysis paper

Apply accuracy review fixes to docs/arxiv/haiku/paper.tex:

Errors (must fix):
- E1: T1 test-007 pass rate — subtest-01 had 40% pass rate, not 0%
- E2: T0 framework failure — restrict to test-002 only
- E3: Subtest total 113 → 120 (arithmetic error)
- E4: Cliff's delta thresholds — Romano et al. 2006 (0.11/0.28/0.43)
- E5: test-021 — remove fabricated scores; only 1 run completed
- E6: test-022 T0 — only one subtest has data

Warnings:
- W1: Delegation cost ratios now specific (3.5–7.1×)
- W5: Token precision 41.7M total / 40.4M cache
- W6: Score stat attributed to SRH not KW omnibus
- W9: Normality exceptions (T6 score p=0.329, cost p=0.177)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |