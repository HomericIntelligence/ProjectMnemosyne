# References: Statistical Claim Verification

## Session Context

**Date**: 2026-02-23
**Project**: ProjectScylla
**Branch**: `1048-haiku-analysis-paper`
**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1060

## Paper Details

- **File**: `docs/arxiv/haiku/paper.tex` (958 lines after fixes)
- **Subject**: Empirical evaluation of Claude Haiku 4.5 across T0-T6 ablation tiers
- **Data**: `docs/arxiv/haiku/data/runs.csv` (620 rows), `summary.json`, `statistical_results.json`
- **N**: 5 runs per subtest, 74 active subtests, 3 complete experiments

## Raw Data Verification Outputs

### Zero-cost Run Count (Fix 7)

```
$ python3 -c "
import csv; from collections import Counter
zeros = [(r['tier'],r['subtest'],r['exit_code']) for r in csv.DictReader(open('docs/arxiv/haiku/data/runs.csv'))
         if float(r['cost_usd']) == 0.0]
print(Counter(r[0] for r in zeros))
print('Total:', len(zeros))
"
Counter({'T5': 6, 'T1': 5, 'T4': 5})
Total: 16
```

**Result**: T4=5 (not 4 as stated in the plan). Total 16 is correct. T4 distribution corrected in paper.

### SRH Degeneration Evidence (Fix 2)

From `statistical_results.json`:
```json
"srh_results": {
  "tier_effect": {"H": 22.63, "df": 6, "p": 0.0009},
  "agent_model_effect": {"H": 0.0, "df": 0, "p": NaN},
  "interaction": {"H": 0.0, "df": 0, "p": NaN}
}
```

The agent_model and interaction effects are both H=0/df=0/p=NaN — confirming the test degenerates to KW.

### Power Analysis Significant Transitions (Fix 6)

From `statistical_results.json` (Holm-Bonferroni corrected):
```
T0→T1: p=0.487 (not significant)
T1→T2: p=0.373 (not significant)
T2→T3: p=0.487 (not significant)
T3→T4: p=0.487 (not significant)
T4→T5: p=0.0024 ✓ SIGNIFICANT
T5→T6: p=0.0243 ✓ SIGNIFICANT
T0→T6: p=0.1187 (not significant)
```

Non-significant adjacent transitions: T0→T1, T1→T2, T2→T3, T3→T4 = "T0--T3" range (4 transitions).
The paper incorrectly said "T0--T4" which would include T4→T5 (significant).

## All 9 Fixes Applied

| Fix | Critical/Minor | Status | Line(s) |
|-----|---------------|--------|---------|
| C1: Cliff's delta thresholds | Critical | Applied | ~312, ~591-593, ~933 |
| C2: SRH → KW | Critical | Applied | ~313-314, ~582, ~585-588 |
| C3: Cross-model hedging | Critical | Applied | ~729-731 |
| C4: BCa CI reproducibility | Low-Medium | Applied | ~315-317, ~949 |
| C5: CoP bootstrap note | Low-Medium | Applied | ~179-182 |
| Fix 6: Power range T0--T4→T0--T3 | Minor | Applied | ~324 |
| Fix 7: T4 count 4→5 | Minor | Applied | ~797 |
| Fix 8: T6 single-subtest caveat | Minor | Applied | ~469-473 |
| Fix 9: T0 refusal vs crash | Minor | Applied | ~375-380 |

## Pre-commit Notes

Commit required two attempts:
1. First `git commit`: pre-commit auto-fixed trailing whitespace in `paper.aux` and `paper.log`
2. Second `git commit` with re-staged `.aux`/`.log`: passed cleanly

This is the standard "pre-commit double-stage" pattern for LaTeX aux files.

## Cliff's Delta Standard Reference

Romano, J. L., Kromrey, J. D., Coraggio, J., & Salkind, N. (2006). Appropriate statistics for ordinal level data: Should we really be using t-test and Cohen's d for evaluating group differences on the NSSE and other surveys?

**Standard thresholds**: negligible <0.147, small <0.33, medium <0.474, large ≥0.474

The "FAIR conference" variant (0.11/0.28/0.43) is not in this paper and has no verifiable citation. When encountered, adopt the standard thresholds.
