---
name: statistical-claim-verification
description: Verify statistical methodology claims in research papers against raw
  data and authoritative references before making corrections
category: documentation
date: 2026-02-23
version: 1.0.0
user-invocable: false
---
# Skill: Statistical Claim Verification for Research Papers

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-23 |
| **Objective** | Apply expert peer review corrections (9 fixes) to an ablation study paper's statistical claims, verifying each against raw CSV data and authoritative references before editing |
| **Outcome** | SUCCESS - All 9 fixes applied, paper compiles cleanly (0 LaTeX errors), critical issues resolved |
| **Paper** | Haiku 4.5 ablation study across T0-T6 tiers, N=5 runs, 620 raw data rows |
| **Category** | Research / Statistical Methodology |

## When to Use This Skill

Apply when you need to:

1. **Correct statistical test usage** in a paper where a test was planned but degenerates given the data structure
2. **Verify effect size threshold citations** against authoritative references (Romano et al., Cohen, etc.)
3. **Audit count claims** (N framework failures, N zero-cost runs) against raw CSV before editing the paper
4. **Fix statistical range errors** in power analysis sections (e.g., wrong tier range for non-significant transitions)
5. **Add reproducibility notes** for derived statistics not archived in the primary results file
6. **Hedge causal/comparative conclusions** that are confounded by the experimental design

**Trigger signals**:
- Paper uses a two-way test with single-factor data (SRH with one model)
- Effect size thresholds cited from a conference variant differ from the standard reference
- A count in the paper (N failures) doesn't match a simple CSV query
- Power analysis names a range of transitions that includes a significant one
- Bootstrap CIs appear in tables but the statistical results archive doesn't contain them
- Cross-model conclusions use "is" language rather than "appears" or "for the tasks tested"

## Verified Workflow

### Step 1: Read the Paper in Full Before Any Edits

Read the entire paper top-to-bottom (all 900+ lines). Build a mental map of:
- Which tests are used (Methods section)
- Every numerical claim with a line number
- Every citation to an external reference standard

**Tools**: `Read` with `offset`/`limit` in chunks of 30-50 lines.

**Critical**: Never edit based on a plan document alone. The plan may be stale relative to the paper. Verify each claim exists exactly as described before applying a fix.

### Step 2: Verify Counts Against Raw Data Before Editing

For any count claim (N framework failures, N zero-cost runs, tier distributions):

```python
import csv
from collections import Counter

zeros = []
with open('data/runs.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if float(row['cost_usd']) == 0.0:
            zeros.append((row['tier'], row['subtest'], row['exit_code']))

tier_counts = Counter(r[0] for r in zeros)
print('By tier:', dict(tier_counts))
print('Total:', len(zeros))
```

**Lesson learned**: A plan may say "T4=4" but the CSV may show T4=5. Always verify before propagating a wrong correction.

### Step 3: Verify Statistical Test Applicability

**SRH degeneration check** — Before reporting a Scheirer-Ray-Hare (two-way non-parametric ANOVA) result, verify:
- How many levels does the second factor (model/group) have?
- If df=0 for the second factor: the test degenerates to one-way Kruskal-Wallis
- Check `statistical_results.json` for `agent_model` effect: if H=0, df=0, p=NaN — it's degenerate

**Fix**: Report Kruskal-Wallis directly. Mention SRH was planned but is not applicable with single-factor data. Move SRH to Future Work.

```latex
% BEFORE (incorrect):
\item \textbf{Interaction}: Scheirer-Ray-Hare test for tier $\times$ task interaction
  (tier effect: $H_{\text{tier}}(6) = 22.63$, $p = 0.0009$; interaction not estimable)

% AFTER (correct):
\item \textbf{Omnibus (score)}: Kruskal-Wallis $H$ test on score confirms tier main effect:
  $H_{\text{tier}}(6) = 22.63$, $p = 0.0009$.
  Note: Scheirer-Ray-Hare was planned but degenerates with single-model data
  (agent\_model df=0; interaction not estimable). See Future Work.
```

### Step 4: Verify Effect Size Threshold Citations

**Cliff's delta thresholds** — The standard Romano et al. 2006 thresholds are:
- Negligible: |δ| < 0.147
- Small: < 0.33
- Medium: < 0.474
- Large: ≥ 0.474

**Red flag pattern**: A paper cites a "FAIR conference variant" (0.11/0.28/0.43) without a verifiable DOI/URL. This variant is not in the standard Romano 2006 paper.

**Impact**: With the 0.43 threshold, δ=+0.433 becomes "large" (barely). With standard 0.474, it's "medium". Check all effect size classifications throughout the paper for consistency.

**Fix**: Adopt the standard thresholds throughout and update all classifications in Methods, Results, and appendix table captions.

### Step 5: Fix Power Analysis Tier Ranges

Power analysis sections often say "for the non-significant transitions (T0--TX)". Verify:

1. Get the list of adjacent transitions tested
2. Check which ones were significant (from statistical_results.json)
3. The range in the paper should cover only non-significant ones

```python
# From statistical_results.json, significant transitions are those with corrected p < 0.05
# If T4->T5 is significant (p=0.0024), it must NOT appear in the non-significant range
# "T0--T4" means transitions T0->T1, T1->T2, T2->T3, T3->T4 (4 transitions)
# "T0--T3" means transitions T0->T1, T1->T2, T2->T3 (3 transitions)
```

**Fix**: `T0--T4` → `T0--T3` if T4→T5 is significant.

### Step 6: Add BCa CI Reproducibility Notes

If bootstrap BCa confidence intervals appear in paper tables but are absent from the primary statistical archive:

1. In Methods, add a note pointing to the generation script
2. In the Data Dictionary appendix, annotate the statistical_results.json entry

```latex
% In Methods, after describing BCa CIs:
Pass-rate BCa CIs (Table~\ref{tab:aggregate-tiers}) are computed during table generation
(\texttt{scripts/export\_data.py}) and are not separately archived in
\texttt{statistical\_results.json}; see Appendix~\ref{app:data}.

% In Data Dictionary:
\item \texttt{data/statistical\_results.json} --- Full statistical test outputs
  (Cliff's delta CIs, KW/MWU results, power analysis; does not include bootstrap BCa
  CIs for pass rate, which are generated by \texttt{scripts/export\_data.py})
```

### Step 7: Hedge Confounded Cross-Group Conclusions

When cross-model (or cross-group) comparisons have enumerated confounds (different tasks, judges, N, etc.), check that conclusions use hedged language:

| Too Strong | Appropriately Hedged |
| ----------- | ---------------------- |
| "Model X is economically viable for real coding tasks" | "Model X *appears* economically viable for the tasks tested here, pending confirmatory same-task comparison" |
| "X's economics are competitive with Y" | "X's economics are competitive with Y for tasks where X can succeed" |
| "X consistently produces lower quality" | "X produced lower quality on the single subtest available (no selection advantage)" |

### Step 8: Distinguish Failure Modes

When reporting zero-cost/zero-token runs, distinguish:
- **Deliberate refusals**: Empty prompt → model refuses without generating output (T0 test-002). No crash.
- **Framework crashes**: SIGABRT (exit_code=134) → agent process killed by OS. Different cause, different remediation.

The paper should note which is which to avoid conflating them as "framework failures."

### Step 9: Compile and Verify

```bash
# Two-pass compile to resolve cross-references
cd docs/arxiv/haiku && pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Verify fixes applied
grep -n "FAIR conference" paper.tex          # Should be 0 lines
grep -n "Scheirer-Ray-Hare" paper.tex        # Should only appear in Future Work + intro note
grep -n "economically viable" paper.tex      # Should have hedging
grep -n "T0--T4" paper.tex                   # Power analysis line should be gone

# Check for errors
grep "^!" paper.log                          # Should be 0 fatal errors
```

**Pre-commit**: Run `pre-commit run --files paper.tex`. LaTeX aux/log files may have trailing whitespace; pre-commit auto-fixes these. Re-stage and commit again.

## Failed Attempts & Lessons Learned

| Attempt | What Went Wrong | Lesson |
| --------- | ---------------- | -------- |
| Trusted plan's T4 failure count (said "4") without checking CSV | CSV showed T4=5, not 4. Total was still 16, but the distribution was wrong | **Always verify counts from raw data, not from the plan** |
| Applied SRH→KW fix without reading the existing footnote | The paper already had a footnote on the KW statistic mentioning SRH; removing it without reading caused loss of context | Read every related line before editing; the paper may already partially address the issue |
| Assumed "T0--T4" in power analysis was a table note | Two other `T0--T4` instances in the paper were legitimate (table footnote, quality summary); only the power analysis line needed fixing | Grep for the pattern and inspect each occurrence before replace_all |
| Used `replace_all: true` on a common phrase | Risk of changing a legitimate instance | Set `replace_all: false` and provide maximum context to ensure uniqueness |

## Results & Parameters

### Fixes Applied (Copy-Paste Reference)

**Fix 1 — Cliff's delta thresholds** (line ~312):
```latex
% Remove: Romano et al., 2006 FAIR conference thresholds: negligible $|{\delta}| < 0.11$, small $< 0.28$, medium $< 0.43$, large $\geq 0.43$
% Use: Romano et al., 2006 thresholds: negligible $|{\delta}| < 0.147$, small $< 0.33$, medium $< 0.474$, large $\geq 0.474$
```

**Fix 2 — SRH → KW** (Methods item + Results paragraph + footnote removal):
- Remove `\footnote{Cost tier effect sourced from Scheirer-Ray-Hare...}` on cost KW item
- Replace SRH Methods item with KW + note about degeneration
- Simplify Results paragraph to report KW directly

**Fix 3 — Cross-model hedging** (RQ3 conclusion):
```latex
% Remove: Haiku is economically viable for real coding tasks. Its economics are competitive with Sonnet
% Add: Haiku appears economically viable for the tasks tested here, pending confirmatory same-task comparison that controls for the confounds enumerated in Table~\ref{tab:confounds}.
```

**Fix 6 — Power analysis range**:
```latex
% Remove: For the non-significant transitions (T0--T4)
% Add:    For the non-significant transitions (T0--T3)
```

**Fix 7 — Framework failure count**:
```latex
% Remove: T1 (5), T4 (4), and T5 (6)
% Add:    T1 (5), T4 (5), and T5 (6)
% (verify with: python3 -c "import csv; from collections import Counter; ...")
```

### Pre-commit Double-Stage Pattern

After `git commit`, pre-commit may auto-fix trailing whitespace in `.aux`/`.log` files:
```
Trim Trailing Whitespace ... Failed (modified paper.aux, paper.log)
Fix End of Files         ... Failed (modified paper.log)
```
**Fix**: `git add paper.aux paper.log && git commit -m "..."` again. Second commit passes.

### Verification Checklist

- [ ] `grep "^!" paper.log` returns 0 lines
- [ ] `grep -n "FAIR conference" paper.tex` returns 0 lines
- [ ] `grep -n "Scheirer-Ray-Hare" paper.tex` returns only Future Work / intro note lines
- [ ] `grep -n "T0--T4" paper.tex` power analysis line is gone
- [ ] `grep -n "borderline large" paper.tex` returns 0 lines
- [ ] Counts verified against raw CSV
- [ ] Two LaTeX compile passes complete without errors

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Haiku 4.5 ablation study, PR #1060 | [notes.md](../references/notes.md) |

## Related Skills

- `research/latex-paper-peer-review` — Broader LaTeX paper editing patterns (Fix pipeline → regenerate data → fix tex)
- `evaluation/e2e-batch-result-analysis` — Reading and interpreting raw runs.csv data
