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