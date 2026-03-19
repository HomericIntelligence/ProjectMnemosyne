# Session Notes: Paper Iterative Accuracy Review

## Raw Session Details

### Date
2026-02-22

### Context
ProjectScylla branch `1048-haiku-analysis-paper`. A first round of fixes (E1-E4, W4-W6) had
already been applied to `docs/arxiv/haiku/paper.tex` from a prior session. A second accuracy
review identified 1 new issue introduced by the fixes, 1 missed error, and 4 optional improvements.
All 6 were implemented in this session.

### Paper
`docs/arxiv/haiku/paper.tex` — Haiku 4.5 model evaluation analysis paper comparing T0-T6 agent
configurations across 5 tasks (3 complete, 2 partial), using N=5 runs per subtest and
Kruskal-Wallis + Mann-Whitney U statistics.

---

## Fix Details

### N1: test-021 Internal Inconsistency (New issue introduced by W4 fix)

**Root cause**: W4 (prior session) added detail to Section `sec:partial` about test-021 having 3
tiers complete. But the short description at line 288 (written when the experiment was new) was
never updated. After W4, the two descriptions contradicted each other.

**Old text (line 288)**:
```
At the time of writing, this experiment is still in very early stages with minimal completed runs.
```

**New text**:
```
At the time of writing, this experiment is partially complete with 3 of 7 tiers finished
(see Section~\ref{sec:partial}).
```

**Lesson**: When you add detail to one section describing a partial experiment, always grep for
other descriptions of the same experiment and update them.

---

### E5: T5→T6 Effect Size Label

**Location**: Line 574 in the pairwise transitions paragraph of the cross-task statistics section.

**Old text**:
```latex
T5$\rightarrow$T6 ($p = 0.0243$, $\delta = +0.433$, medium-large effect).
```

**New text**:
```latex
T5$\rightarrow$T6 ($p = 0.0243$, $\delta = +0.433$, large effect).
```

**Reasoning**: The paper defines Romano thresholds at line 306:
- negligible < 0.11
- small < 0.28
- medium < 0.43
- large ≥ 0.43

δ = 0.433 ≥ 0.43, so it is unambiguously **large**. "Medium-large" is not a Romano category.

**Why it was missed in the first pass**: The first pass focused on numerical values (p-values,
W statistics, costs). The qualitative labels were not cross-checked against the threshold table.

---

### W1: Table Cost Column Ambiguity

**Tables affected**: Tables 4 (test-002), 5 (test-007), 6 (test-017)

**Problem**: The "Cost" column could mean:
- Mean cost per run
- Total cost across all 5 runs
- Cost-of-Pass (CoP)
- Cost for the best subtest only

**Fix applied** (same pattern for all three tables):
```latex
% Before:
\caption{test-002 Tier Performance Summary (Mojo Hello World)}

% After:
\caption{test-002 Tier Performance Summary (Mojo Hello World). Cost = mean cost per run for best subtest.}
```

---

### W2: T5 Anomaly Explanation

**Location**: After line 376 (T5 Anomaly paragraph for test-002)

**Problem**: Table shows Best Score = 0.00 for T5 while Pass% = 40%. This looks like a data
error without context.

**Sentence added**:
```latex
Best Score reflects the mean score of the selected best subtest, which can be 0.00 when
the subtest whose overall metric is optimized averages to zero despite individual runs passing.
```

**Meaning**: The "best subtest" selection optimizes a combined metric. It's possible for the
selected subtest to have a pass rate > 0 but a mean judge score of 0.00 if all passing runs
received a score of 0 from the judge (pass/fail binary judge).

---

### W3: T3/T1 Cost Ratio Rounding

**Location**: Line 463

**Actual ratio**: T3 = $13.18/run, T1 = $0.79/run → ratio = 13.18 / 0.79 = 16.68 / 0.79...
Wait, re-reading: "T3 costs $13.18/run ($34.97 CoP) and T4 costs $17.62/run ($30.04 CoP)---T3
costs 3.5× T1 and 5.3× T2".

The T1 cost is mentioned elsewhere as $3.71/run for test-017 context... but for this specific
sentence about test-017's T3 vs T1: T3=$13.18, T1 reference. 13.18/3.71 = 3.553 → rounds to 3.6×.

**Old**: `3.5$\times$`
**New**: `3.6$\times$`

---

### W8: Cache Read Pricing Footnote

**Location**: Line 229, pricing comparison table

The paper states Haiku pricing as $1/$5 per M tokens (input/output). But in the actual
experiment runs, 97% of tokens are cache reads, priced at $0.10/M — 10% of the stated input
price. This materially affects cost interpretation: the effective cost is much lower than
the base rate implies.

**Footnote added**:
```latex
\footnote{Cache read tokens are priced at \$0.10/M for Haiku (10\% of input price).
Since 97\% of tokens in our experiments are cache reads, the effective per-token cost
is significantly lower than the base input rate.}
```

---

## Compilation Results

```
pdflatex -interaction=nonstopmode paper.tex  # Pass 1
pdflatex -interaction=nonstopmode paper.tex  # Pass 2
grep "^!" paper.log  → 0 errors
grep "??" paper.log  → 0 unresolved refs
Output: 17 pages, 332992 bytes
```

## Git Outcome

Branch: `1048-haiku-analysis-paper`
Commit: `1a009a19`
Message: `fix(research): apply post-review accuracy corrections to Haiku analysis paper`
Remote: Pushed (no PR — branch only)