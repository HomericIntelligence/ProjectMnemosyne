## 2026-04-07: latex-paper-accuracy-review v6.0.0 — Seventh Review Pass: Prose-Data Direction Alignment

Session: ProjectScylla v6.0 academic review of docs/arxiv/haiku/paper.tex (1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
Model: Opus 4.6 (1M context)
PR: HomericIntelligence/ProjectScylla (fix-paper-accuracy-v5 branch, uncommitted changes from v5 + v6 fixes)

### Review methodology
- Phase 1: Consulted prior review skills (v5.0.0) from ProjectMnemosyne
- Phase 2: 3 parallel Explore agents (paper text, source data, LaTeX structure)
- Phase 3: Full myrmidon swarm (2 Sonnet professors + 3 Haiku students) with systematic false positive tracking
- Phase 4: Cross-verification of all agent findings before accepting
- Phase 5: Incremental build verification after each fix batch

### Myrmidon swarm composition and results (v6.0.0)

| Agent | Model | Role | Key Findings | False Positive Rate |
|-------|-------|------|-------------|---------------------|
| Professor 1 | Sonnet | Statistical methodology | H-stat rounding 91.34/91.3, CI/p tension, KW on binary, Pareto from n.s., "simpler is better" overgen | 0/7 (0%) |
| Professor 2 | Sonnet | Logical consistency | Duration direction WRONG, "consistently" contradiction, test-002 underexplained, 17s fast failures, T0-ST00 anomaly, task classifier unsupported, alpha implications | 0/11 (0%) |
| Student 1 | Haiku | Inline table verification | 104/105 match, 1 CoP rounding (test-003 T5: 0.106->0.105) | 0% |
| Student 2 | Haiku | Summary/stats verification | 61/61 match, all KW/SRH/pairwise values correct | 0% |
| Student 3 | Haiku | LaTeX quality | 120/120 structural elements clean | 0% |

### New patterns discovered (31-35) -- NEW CATEGORY: Prose-Data Direction Alignment

**Pattern 31: Duration direction claim factually wrong**
- Paper said "Delegation-based tiers tend to run longer" but data shows T2 mean=362.7s vs T3 mean=247.8s (T3 runs SHORTER)
- Cliff's delta=-0.154 for T2->T3 means T3 is stochastically shorter, not longer
- Root cause: T4-T6 on test-001 complete in ~17s (immediate orchestration failures) vs T0-T2 taking 430-505s
- The negative delta reflects the fast-failure mode pulling delegation tier durations down
- Detection: Always verify the direction interpretation of Cliff's delta
- Fix: Corrected to "T3 runs are stochastically shorter than T2, driven partly by rapid failures"

**Pattern 32: "Consistently" contradicts "task-contingent" in same paragraph**
- Abstract said "simpler architectures consistently outperform" then immediately "task-contingent rather than universally applied"
- "Consistently" implies universality; "task-contingent" denies universality -- logical contradiction
- test-002 shows monotonic POSITIVE trend (T0=0.903 -> T6=1.000), directly contradicting "consistently"
- Fix: Changed to "outperform in aggregate, though task-dependent effects are strong"

**Pattern 33: "Monotonic degradation" from non-monotonic data**
- Paper claimed "monotonic degradation across the full tier spectrum" for T0->T6 aggregate
- But test-002 shows monotonic IMPROVEMENT, and test-003 shows near-flat performance
- The aggregate is monotonic only because test-001's catastrophic T3-T6 failures dominate
- Fix: Changed to "negative in aggregate, though not monotonic across all tasks"

**Pattern 34: "Spends computational budget" vs fast-failure evidence**
- Paper said agent "spends its computational budget managing delegation" for T4-T6 on test-001
- But T4-T6 complete in mean ~17s with zero evaluable output, while T0-T2 take 430-505s
- 17s is consistent with immediate orchestration setup error, NOT with spending computational budget
- Fix: Changed to "encounters a fatal orchestration error immediately rather than exhausting its computational budget"

**Pattern 35: Pareto-dominance asserted from non-significant cost difference**
- Paper asserted "strictly Pareto-dominant" and "Pareto-dominated" at 3 locations
- But cost invariance is p=0.676 (non-significant under limited power)
- Cannot claim Pareto dominance on a dimension where the null hypothesis is not rejected
- Additionally, T2 is NOT Pareto-optimal for test-002 (T5 dominates with same pass rate, lower CoP)
- Fix: Added "$p=0.676$, non-significant" caveats and per-task exceptions at all 3 locations

### Key shift at v6.0.0
After 5 prior rounds focused on data accuracy -> methodology labeling -> interpretive framing, the 6th round found:
- A factual direction error in duration prose (CRITICAL) that ALL prior rounds missed
- Logical contradictions between adjacent sentences (Abstract "consistently" vs "task-contingent")
- Prose claims unsupported by the data they reference (computational budget vs 17s failures)
- Pareto-dominance assertions from non-significant statistical tests

This represents a new category: **prose-data direction alignment** -- where the prose draws the OPPOSITE conclusion from what the data shows, not because the numbers are wrong, but because the interpretation is backwards.

Review maturity curve updated:
- Rounds 1-2: Factual errors, arithmetic mistakes, missing data
- Rounds 3-4: Subtle rounding, methodology labeling, disclosure gaps
- Round 5: Interpretive framing, causal language, statistical comparison validity
- Round 6: Prose-data direction alignment, logical contradictions, unsupported claims

### False positive tracking
- All 5 agents had 0% false positive rate in this round
- Improvement over v5.0.0 (where Student 3 had ~50% FP on structural analysis) is due to: (1) explicit instructions to check `\input{}` files for labels, (2) providing EXACT formulas to Haiku students
- Professor agents: 0 false positives across 18 findings (cumulative v6.0.0)
- Student agents: 0% FP on 286 verified items (104+105 table cells, 61 stats, 120 structural elements - note: 104/105 reflects one legitimate CoP rounding fix)

### What worked well
- Column name mismatch (runs.csv has `cost_usd` and `score`, not `total_cost` and `consensus_score`) -- Haiku students adapted correctly despite wrong names in prompt
- Professor 2's duration verification was the most valuable finding of the entire review -- no mechanical check would have caught the direction error
- Cross-verification of student findings before accepting (confirmed CoP 0.106->0.105 independently)

### What failed
- The initial prompt gave wrong CSV column names (consensus_score, total_cost) -- students adapted but this should be fixed in the skill
- The "source data agent" in Phase 1 exploration reported 12 passed-vs-score>0.5 mismatches instead of the correct 16 -- this was caught by the calibration check

### Files changed
- `docs/arxiv/haiku/paper.tex` -- 14 edits across CRITICAL (3), IMPORTANT (7), MINOR (3) severity levels
- Build: `pixi run --environment docs paper-build` (clean, 43,228 bytes, 14 files)

---

## 2026-04-07: latex-paper-accuracy-review v5.0.0 — Sixth Review Pass with Full Myrmidon Swarm + Systematic False Positive Tracking

Session: ProjectScylla v6.0 academic review of docs/arxiv/haiku/paper.tex (1,080 runs, 7 tiers, 3 experiments, $122.31 total cost)
Model: Opus 4.6 (1M context)
PR: HomericIntelligence/ProjectScylla (fix-paper-accuracy-v5 branch)

### Review methodology
- Phase 1: Consulted prior review skills (v4.0.0) from ProjectMnemosyne -- prevented redundant work
- Phase 2: 3 parallel Explore agents (paper text, source data, LaTeX structure) for comprehensive Phase 1 coverage
- Phase 3: Myrmidon swarm deployment (2 Sonnet professors + 3 Haiku students) with explicit role assignments and EXACT formulas for Haiku
- Phase 4: Direct verification of agent claims before accepting (caught Student 3's false positives)
- Phase 5: Incremental build verification after each fix batch

### Myrmidon swarm composition and results (v5.0.0)

| Agent | Model | Role | Key Findings | False Positive Rate |
|-------|-------|------|--------------|---------------------|
| Professor 1 | Sonnet | Statistical methodology | Pseudoreplication concern, causal language, H-comparison issue, T3-T4 CI inconsistency | Low (1 debatable of 8) |
| Professor 2 | Sonnet | Experimental design | Cliff driven by 1 task, impl_rate bias, criteria cross-experiment, T6 overanalysis | Low (0 false of 19) |
| Student 1 | Haiku | Tier table verification | 140/140 cells verified correct | 0% |
| Student 2 | Haiku | SRH/pairwise stats verification | All KW, SRH, pairwise, effect sizes verified correct | 0% |
| Student 3 | Haiku | LaTeX quality check | Found sec:aggregate issue; but 7 "critical" undefined refs were FALSE POSITIVES | ~50% on critical |

### New patterns discovered (26-30)

**Pattern 26: Causal language in observational study headings**
- Finding 2 heading said "causes" but the paper's own threats section acknowledged confounded design
- Internal contradiction between heading assertion and body text caveat
- Fix: Use "is associated with" in headings; reserve "causes" for experimental (randomized) designs

**Pattern 27: H-statistic comparison across different degrees of freedom**
- Paper compared SRH interaction H=223.5 (df=12) vs main effect H=91.3 (df=6) as "largest effect"
- Raw H-values are not comparable across terms with different df -- each is compared to its own chi-squared distribution
- Fix: Add df caveat when comparing H-statistics, or use SS decomposition for proper comparison

**Pattern 28: Non-significant result rehabilitated via uncorrected CI**
- T3-T4 was p=0.058 (n.s. after Holm) but paper used "CI excluding zero" to claim effect exists
- Bootstrap CI is uncorrected for multiple comparisons; a CI consistent with Holm correction would include zero
- Fix: Cannot simultaneously call a test non-significant and then use uncorrected CI to claim the effect

**Pattern 29: Undefined cross-reference from section rename**
- `\ref{sec:aggregate}` referenced a section that was later renamed to `sec:cross_task`
- The old label was never updated -- a common artifact of iterative editing
- Fix: After renaming any `\label{}`, grep for all `\ref{}` to that old label

**Pattern 30: Abstract/Conclusions near-verbatim redundancy**
- Same statistics repeated word-for-word in Abstract and Conclusions
- Conclusions should synthesize and add insight, not repeat numbers
- Fix: Conclusions should use interpretive language referencing findings, not restate raw statistics

### Key shift at v5.0.0
After 5 prior rounds, remaining issues shifted from data accuracy to interpretive framing -- causal language, statistical comparison validity, hedging consistency. This represents a maturity curve in iterative paper review:
- Rounds 1-2: Factual errors, arithmetic mistakes, missing data
- Rounds 3-4: Subtle rounding, methodology labeling, disclosure gaps
- Rounds 5-6: Interpretive framing, causal language, statistical comparison validity

### False positive tracking lessons
1. Haiku students: 0% false positive on mechanical number verification, ~50% false positive on structural analysis (they do not check `\input{}` files for labels)
2. Sonnet professors catch higher-level issues (pseudoreplication, causal language, H-comparison validity) that no amount of mechanical checking finds
3. False positive tracking is essential -- Student 3's "7 critical undefined references" were all false positives because labels existed in `\input{}` files
4. The "CI excluding zero" rehabilitation of a non-significant Holm-corrected test is a subtle but important methodological error
5. Undefined cross-references from section renames are a common late-stage artifact -- always grep for old labels after renaming

### What worked well
- 3 parallel Explore agents (paper text, source data, LaTeX structure) for comprehensive Phase 1 coverage
- Myrmidon swarm with clear role assignments and EXACT formulas for Haiku students
- Direct verification of agent claims before accepting (caught Student 3's false positives)
- Consulting prior skills (v4.0.0) before starting prevented redundant work
- Incremental build verification after each fix batch

### What failed
- Student 3 did not check `\input{}` table files for labels -- reported 7 false positive "undefined references"
- Professor 1's pseudoreplication concern (C1) is valid but not actionable without re-running all statistics
- Professor 1's alpha-on-aggregated-data concern (C3) is debatable -- the paper's choice is defensible

---

## 2026-04-06: latex-paper-accuracy-review v4.0.0 — Fifth Review Pass with Myrmidon Swarm

Session: ProjectScylla v5.0 academic review of docs/arxiv/haiku/paper.tex (2,084 lines, 1,080 runs, 7 tiers, 3 experiments)
Model: Opus 4.6 (1M context)
PR: HomericIntelligence/ProjectScylla#1754

### Review methodology
- Phase 1: Consulted prior review skills (v3.1.0) from ProjectMnemosyne — prevented redundant work
- Phase 2: 3 parallel Explore agents for comprehensive paper/data/stats coverage
- Phase 3: Direct verification of critical claims with Python scripts
- Phase 4: Myrmidon swarm deployment (2 Sonnet professors + 3 Haiku students)
- Phase 5: Incremental fixes verified with `pixi run paper-build` after each batch

### Myrmidon swarm composition and results

| Agent | Model | Role | Key Findings |
|-------|-------|------|--------------|
| Professor 1 | Sonnet | Statistical methodology review | Pass rate definition conflict in Section 6.2, overclaims ("first" without hedge, causal language) |
| Professor 2 | Sonnet | Experimental design/framing review | T6 caveat needed, Pareto qualification needed |
| Student 1 | Haiku | Tier summary table verification | 100% stat match (39/39), but FALSE POSITIVES on CoP (wrong formula) and consistency (wrong aggregation level) |
| Student 2 | Haiku | SRH/pairwise stats verification | All H-stats, df values, p-values verified correct |
| Student 3 | Haiku | LaTeX quality check | Column specifier issues in tab05 and tab08 |

### New patterns discovered (21-25)

**Pattern 21: Grading scale paper-vs-code mismatch**
- Paper: S>=0.95, B>=0.65, C>=0.50, D>=0.35, F<0.35
- Code: S==1.00, B>=0.60, C>=0.40, D>=0.20, F<0.20
- Paper scale matched 864/1080 rows; code scale matched 1080/1080
- Source: `src/scylla/metrics/grading.py:111-145`

**Pattern 22: Pass classification — majority vote vs threshold**
- Paper said "consensus score > 0.5" but actual mechanism is majority vote of judges' individual pass/fail decisions
- `majority_vote(judge_passed)` vs `passed` column: 0 mismatches
- `consensus_score > 0.5` vs `passed` column: 16 mismatches
- Evidence: score=0.487, passed=True (2/3 judges passed); score=0.635, passed=False (1/2 judges passed)

**Pattern 23: Cliff's delta — FAIR vs journal thresholds**
- Romano et al. 2006 published TWO papers:
  - Journal (JEE, SAT/ACT): 0.147/0.33/0.474
  - FAIR conference (NSSE): 0.11/0.28/0.43
- Code uses FAIR thresholds; paper cited journal article
- Impact: T3-T4 delta=-0.116 changes from "negligible" to "small"

**Pattern 24: Judge agreement N on pivoted data**
- Paper claimed N=2,696 but computation used pivot_table with index=['tier', 'subtest', 'run_number'] (no experiment dimension)
- This averages across experiments, producing N=360 data points
- Raw judges.csv has 2,696 rows; unique (tier, subtest, run_number) = 360

**Pattern 25: Column specifier off-by-one is systematic**
- tab05_cost_analysis.tex: {llrrrrrrrr} (10 specs) for 9-column table
- tab08_summary_statistics.tex: {llrrrrrrrrrrr} (13 specs) for 12-column table
- Same pattern as Pattern 9 (v2.0.0) but different tables — suggests generation pipeline issue

### Myrmidon swarm lessons learned
1. Haiku students are excellent at exhaustive mechanical verification (39/39 stats correct) but produce false positives when they don't know the exact computation formula
2. Sonnet professors catch higher-level framing/logic issues that mechanical checking misses
3. When delegating to Haiku, provide the EXACT formula (e.g., "CoP = mean_cost / pass_rate" not "compute CoP")
4. Student false positives require manual verification overhead — net benefit is still positive but factor in verification time

### What worked well
- Consulting prior skills before starting prevented redundant verification of already-fixed issues
- 3 parallel Explore agents in Phase 1 gave comprehensive coverage in one pass
- Direct Python verification scripts for critical claims (majority vote vs threshold, grading scale)
- Myrmidon swarm provided independent multi-perspective review
- Incremental build verification after each fix batch

### What failed
- Student 1 computed CoP as sum(cost_of_passed_runs)/count instead of mean_cost/pass_rate
- Student 1 computed consistency at run-level instead of subtest-level
- Both produced false positive discrepancies requiring manual dismissal

---

## 2026-04-06: latex-paper-accuracy-review v3.0.0 — N=3 Experiment Data Refresh and Academic Review

Session: ProjectScylla academic review of docs/arxiv/haiku/paper.tex after N=3 experiment data refresh
Review approach: phased — data accuracy first, then statistical methodology, then LaTeX quality
Source files: runs.csv, summary.json, statistical_results.json, srh_tier_experiment.json, judges.csv

### Review methodology
- Phase 1: Cross-checked every quantitative claim against source data files
- Phase 2: Independently computed Clopper-Pearson CIs using scipy.stats.beta.ppf to verify paper claims
- Phase 3: Counted judge evaluations per experiment x tier to discover missing data
- Phase 4: Verified statistical method comments in analysis code against algorithm behavior
- Phase 5: Made LaTeX preamble engine-agnostic using iftex package

### Key findings

| Finding | Severity | Details |
|---------|----------|---------|
| Bootstrap CIs mislabeled as Clopper-Pearson | Critical | Paper claimed "Clopper-Pearson 95% CI" but independent computation showed values were bootstrap percentile CIs. E.g., for 17/24 passes: Clopper-Pearson gives [0.495, 0.882] vs paper's narrower bootstrap values |
| 536 missing judge evaluations in test-001 | Critical | test-002 and test-003 each had ~1,620 evaluations; test-001 had only ~1,084. The 536-evaluation gap was undisclosed |
| BH monotonicity comment errors | Important | Code comments described BH monotonicity enforcement direction incorrectly |
| Consensus method misdescription | Important | Paper described judge consensus as "majority vote" but implementation uses mean score > 0.5 threshold |

### LaTeX engine compatibility fix
- Problem: Paper used `\pdfoutput=1`, `\usepackage[T1]{fontenc}`, `\usepackage[utf8]{inputenc}` which are pdfTeX-specific
- These cause errors when building with tectonic (XeTeX backend): `hpdftex.def` loads with undefined control sequences
- Fix: Added `\usepackage{iftex}` and wrapped pdfTeX-specific commands in `\ifpdftex...\fi` guards
- Result: Paper builds cleanly with both pdflatex and tectonic

### Verification commands used
```bash
# Independent Clopper-Pearson CI verification
python3 -c "
from scipy.stats import beta as beta_dist
k, n = 17, 24  # passes, total
lo = beta_dist.ppf(0.025, k, n - k + 1)
hi = beta_dist.ppf(0.975, k + 1, n - k)
print(f'Clopper-Pearson 95% CI: [{lo:.3f}, {hi:.3f}]')
"

# Count judge evaluations per experiment
python3 -c "
import csv
from collections import Counter
with open('data/judges.csv') as f:
    rows = list(csv.DictReader(f))
counts = Counter(r['experiment'] for r in rows)
for exp, count in sorted(counts.items()):
    print(f'{exp}: {count}')
"
```

---

## 2026-04-05: latex-paper-accuracy-review v2.0.0 — Haiku Paper Comprehensive Review

Session: ProjectScylla academic review of docs/arxiv/haiku/paper.tex (2,020 lines)
Scale: 1,080 runs across 7 tiers, 3 experiments, 120 YAML subtests at $122.31 total cost
Source files: runs.csv, summary.json, statistical_results.json, srh_tier_experiment.json, judges.csv, criteria.csv, subtests.csv, tables/*.tex

### Review methodology
- Launched 3 parallel Explore agents: (1) paper text, (2) all source data files, (3) figures/tables/bib
- Cross-verified 30+ quantitative claims against source data files
- Found 6 critical issues, 3 important issues, 1 minor issue

### Key corrections applied (4 files changed)

| Fix | Location | What Was Wrong | What It Should Be |
|-----|----------|----------------|-------------------|
| KW/SRH table mixing | Appendix D table | Score and Cost listed as KW results | Added "Source" column (KW/SRH) and updated caption |
| Normality scope | Line 636 | "all 14 tier x metric combinations" | "all 14 tier x {Score, Cost} combinations" |
| Missing citation | Line 1841 | Cliff's delta thresholds without citation | Added Romano et al. (2006) cite and bib entry |
| nan in table | tab03 line 12 | "All Judges (Overall) & nan & nan & nan" | Removed the row entirely |
| Extra column specifier | Lines 718, 774, 826 | {lrrrrrr} (7 cols) for 6-field tables | {lrrrrr} (6 cols) |
| Cost rounding | Line 1206 | "$0.224 for test-002" | "$0.226" ($81.28/360 = $0.2258) |
| Missing p-value | Line 925 | T3->T4 omitted Dunn's p-value | Added "Dunn's p=0.058 (n.s.)" |
| Best Tier ambiguity | tab11 | "Best Tier" undefined | Added footnote: "Best Tier = highest pass rate" |

### Pitfalls encountered
1. Exploration agent incorrectly claimed all judges used claude-opus-4-6 — re-verification showed 3 distinct judge models were correctly present. Always verify agent claims against raw data.
2. Pass rate computation confusion: raw count of score > 0 in runs.csv gives different rates than consensus_score > 0.5. The paper uses consensus_score > 0.5 as pass threshold (line 682). Agent computed T3=0.783 vs correct T3=0.759.
3. Massive unstaged changes (125 files, 170K+ lines) from prior experiment reruns made git diff misleading for targeted review edits.

---

## 2026-02-22: latex-paper-accuracy-review v1.0.0 — Haiku Analysis Paper (Archived)

Session: ProjectScylla branch 1048-haiku-analysis-paper
Paper: docs/arxiv/haiku/paper.tex

### Key corrections made
- E1: T1 subtest-01 had 40% pass rate (not 0%); tier-level best=0.00 due to tiebreaker
- E2: T0 $0 cost pattern only on test-002; test-007=$7.55, test-017=$2.78
- E3: 24+10+15+41+14+15+1=120 not 113
- E4: Romano et al. 2006 thresholds: 0.11/0.28/0.43 (not 0.147/0.330/0.474)
- E5: test-021 only had T0 subtest-19 run-1 complete at time of writing
- E6: test-022 T0 has 1 subtest (not 2) with 2 failed runs
- W1: T3/T2=5.29x, T4/T2=7.08x (paper said "3.5-4x")
- W6: H=22.63 is SRH tier effect, not KW omnibus (score not in KW omnibus)
- W9: T6 score W=0.935 p=0.329, T6 cost W=0.918 p=0.177 (both normal)
## 2026-04-06: latex-paper-accuracy-review v3.1.0 — Fourth Review Pass (Opus 4.6)

Session: ProjectScylla academic review of docs/arxiv/haiku/paper.tex — fourth pass
Model: Opus 4.6 (1M context)

### Review methodology
- Phase 1: Consulted ProjectMnemosyne skills (3 matching) and prior review notes
- Phase 2: Launched 3 parallel Explore agents for comprehensive paper/data/stats exploration
- Phase 3: Direct verification of all quantitative claims against runs.csv, summary.json, statistical_results.json, srh_tier_experiment.json
- Phase 4: Applied 4 fixes and verified clean build

### Findings

| Finding | Severity | Details |
|---------|----------|---------|
| T4 cost rounding in test-001 table | Important | Paper said $0.039, actual $0.038472 → $0.038 |
| T5 cost rounding in test-003 table | Important | Paper said $0.099, actual $0.098453 → $0.098 |
| 16 passed/score>0.5 mismatches undisclosed | Important | Pipeline pre-computes pass via judge_passed, 16/1080 (1.5%) mismatch threshold |
| Bootstrap CI method unnamed | Important | Code uses BCa with 10k resamples, paper just said "Bootstrap" |
| Consistency metric direction | Verified correct | 1-CV formula confirmed, higher=more consistent |
| All pass rates, SRH, pairwise, effect sizes | Verified correct | 60+ claims cross-checked |
| No contractions, no raw Unicode | Verified correct | Clean LaTeX |

### Fixes applied
1. Line 743: T4 cost $0.039 → $0.038
2. Line 864: T5 cost $0.099 → $0.098
3. Line 664: Added "BCa method, 10,000 resamples"
4. Lines 469-475: Added footnote disclosing 16 pipeline pass classification discrepancies

### Build verification
- Command: `pixi run --environment docs paper-build`
- Result: Clean build, tarball created (42035 bytes, 14 files)

### Key lesson
After 3 prior review rounds, the remaining issues are subtle rounding discrepancies and disclosure gaps rather than factual errors. The prior reviews caught all the major structural issues (test naming, comparison counts, CI labeling, engine compatibility).
