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
