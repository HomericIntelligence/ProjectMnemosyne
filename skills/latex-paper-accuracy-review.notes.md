## 2026-02-22: latex-paper-accuracy-review — Haiku Analysis Paper

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