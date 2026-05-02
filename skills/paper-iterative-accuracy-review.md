---
name: paper-iterative-accuracy-review
description: 'Second-pass review after initial paper fixes: catch internal inconsistencies introduced by edits, verify statistical effect-size labels against defined thresholds, clarify ambiguous table headers, explain counter-intuitive results, and add missing pricing context'
category: documentation
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Paper Iterative Accuracy Review

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-22 |
| **Objective** | Apply post-fix accuracy review to a research paper, catching issues that survived or were introduced by the first correction round |
| **Outcome** | ✅ 6 fixes applied (1 new consistency issue, 1 missed error, 4 optional improvements), 0 LaTeX errors, clean 2-pass compile |
| **Category** | Documentation |
| **Models Used** | Sonnet 4.6 |
| **Tools** | pdflatex, grep |

## When to Use This Skill

Use this skill when:

1. **After a first round of paper fixes** — verify no new issues were introduced by edits
2. **Statistical effect-size labels need checking** — confirm labels match the threshold definitions stated in the paper itself (not informal usage)
3. **A partial-results experiment is described in two places** — check both descriptions are consistent
4. **Tables have a "Cost" or similar ambiguous column** — confirm the column header communicates mean/total/best clearly
5. **A metric shows a counter-intuitive value** (e.g., 0.00 score with 40% pass rate) — add an explanatory sentence
6. **Pricing is quoted at base rates** but cache reads dominate actual cost — add a footnote with effective rate

**Trigger patterns:**
- "I fixed E1-E4 last session, let me check nothing new broke"
- "The effect size says medium-large but I defined thresholds in Section X"
- "Line 288 says minimal runs but line 478 says 3 tiers completed — contradiction"
- "The Cost column — is that per-run or total?"
- "97% of tokens are cache reads but pricing says $1/M input"

## Verified Workflow

### Phase 1: Verify All Prior Fixes Are Correct

Before looking for new issues, confirm the first-round fixes are still accurate.

```bash
# For each prior fix, grep to confirm old value is gone
grep "old_value" paper.tex  # Should return 0 matches

# Spot-check key statistics against source JSON
grep "W=0.835" paper.tex    # Confirm statistical values match data files
```

Create a fix verification table:

| Fix | Paper Value | Source Value | Status |
| ----- | ------------- | -------------- | -------- |
| E1: Shapiro-Wilk W | 0.835, p=9.3e-11 | statistical_results.json: W=0.8351 | CORRECT |

Only proceed to new issues after confirming all prior fixes are sound.

### Phase 2: Cross-Reference Internal Descriptions

**Critical**: Search for every description of a partial/in-progress experiment. Papers often describe the same experiment in multiple sections written at different times.

```bash
# Find all mentions of a partial experiment
grep -n "test-021\|partial\|early stages" paper.tex

# Look for contradictions between:
# - A short summary description (often written first, early in paper)
# - A detailed analysis section (written when more data was available)
```

**Pattern to catch**: Summary section says "very early stages with minimal runs" while the analysis section says "3 tiers have completed reports." If the analysis section has more recent/accurate information, update the summary to match.

**Fix template**:
```latex
% OLD (written when experiment was new):
At the time of writing, this experiment is still in very early stages with minimal completed runs.

% NEW (consistent with analysis section that shows 3 tiers done):
At the time of writing, this experiment is partially complete with 3 of 7 tiers finished (see Section~\ref{sec:partial}).
```

### Phase 3: Validate Effect-Size Labels Against Paper's Own Thresholds

**Critical rule**: Use the paper's own defined thresholds, not informal labels.

```bash
# Find where the paper defines effect-size thresholds
grep -n "negligible\|small\|medium\|large" paper.tex | head -20

# Then check each effect-size label in results sections
grep -n "effect)" paper.tex
```

**Romano et al. (2006) standard thresholds** (verify paper defines these explicitly):

| Label | δ range |
| ------- | --------- |
| negligible | < 0.11 |
| small | 0.11–0.27 |
| medium | 0.28–0.42 |
| large | ≥ 0.43 |

**The trap**: δ = 0.433 is exactly ≥ 0.43 → **large**, not "medium-large". "Medium-large" is not a Romano category. The boundary is hard, not fuzzy.

```bash
# Search for non-standard composite labels
grep -n "medium-large\|small-medium\|large-very large" paper.tex
# Each match is a potential error — check δ value against defined thresholds
```

### Phase 4: Clarify Ambiguous Table Column Headers

**Problem**: Columns labeled just "Cost" or "Duration" don't tell readers whether it's:
- Mean cost per run
- Total cost across all runs
- Cost for the best-scoring subtest only
- Cost-of-Pass (CoP)

**Fix**: Add clarifying text to each table caption.

```latex
% Before:
\caption{test-002 Tier Performance Summary (Mojo Hello World)}

% After:
\caption{test-002 Tier Performance Summary (Mojo Hello World). Cost = mean cost per run for best subtest.}
```

### Phase 5: Explain Counter-Intuitive Metric Combinations

If a table shows a combination that looks impossible (e.g., Best Score = 0.00 but Pass% = 40%), add an explanatory sentence near the anomaly call-out.

**Example explanation**:
```latex
% Near the T5 Anomaly paragraph:
Best Score reflects the mean score of the selected best subtest, which can be 0.00 when the
subtest whose overall metric is optimized averages to zero despite individual runs passing.
```

### Phase 6: Add Cache Read Pricing Context

When a paper states base input/output prices but the actual workload is dominated by cache reads (priced at ~10% of input), add a footnote at the first price mention.

```latex
% Before:
Agent pricing & \$3/\$15 per M tokens & \$1/\$5 per M tokens \\

% After (with footnote):
Agent pricing & \$3/\$15 per M tokens & \$1/\$5 per M tokens\footnote{Cache read tokens
are priced at \$0.10/M for Haiku (10\% of input price). Since 97\% of tokens in our
experiments are cache reads, the effective per-token cost is significantly lower than the
base input rate.} \\
```

**When to add**: When cache read % ≥ 90% of total tokens AND paper reports costs, the effective rate differs materially from the stated base rate.

### Phase 7: Compile and Verify

```bash
cd <paper-directory>
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex   # Second pass resolves cross-refs

# Check for errors
grep "^!" paper.log      # Should be 0
grep "??" paper.log      # Should be 0 (unresolved references)

# Confirm old values removed
grep "medium-large" paper.tex   # Should be 0
grep "very early stages" paper.tex  # Should be 0
grep "3\.5\$\\\\times\$" paper.tex  # Confirm ratio updated if changed
```

## Failed Attempts & Lessons Learned

| Attempt | Issue | Resolution |
| --------- | ------- | ------------ |
| Grepping for "3.5×" to verify fix | The pattern `3.5$\times$` in LaTeX source didn't match simple grep for `3.5` — other legitimate 3.5 occurrences exist | Use precise LaTeX pattern: `grep "3\.5\$\\\\times\$"` or visually inspect the specific context |
| Assuming internal consistency after first-round fixes | Fixing one section (analysis) while leaving a stale summary section created a new contradiction N1 | Always cross-reference ALL descriptions of the same entity after any edit |
| Trusting "medium-large" as a valid Romano category | Romano (2006) defines hard thresholds: small/medium/large — no composite labels | Check the paper's own threshold table and apply the hard boundary rule |
| Using replace_all for effect-size label changes | "medium" appears in legitimate uses ("medium effect" for δ=0.313) — replace_all would break correct labels | Always target the specific δ value context, not just the label string |

## Results & Parameters

### Fix Summary (This Session)

| Fix ID | Type | Location | Change |
| -------- | ------ | ---------- | -------- |
| N1 | New (introduced by prior fix) | Line 288 | "very early stages" → "partially complete with 3 of 7 tiers finished" |
| E5 | Missed error | Line 574 | "medium-large effect" → "large effect" (δ=0.433 ≥ 0.43) |
| W1 | Warning/improvement | Tables 4-6 captions | Added "Cost = mean cost per run for best subtest" |
| W2 | Warning/improvement | T5 Anomaly paragraph | Added explanation for Best Score = 0.00 with 40% pass rate |
| W3 | Warning/improvement | Line 463 | "3.5×" → "3.6×" (actual ratio 3.55×) |
| W8 | Warning/improvement | Line 229 (pricing table) | Added cache read pricing footnote |

### Verification Commands

```bash
# Post-fix verification
grep "medium-large" paper.tex      # 0 matches
grep "very early stages" paper.tex # 0 matches
grep "^!" paper.log                # 0 LaTeX errors
grep "??" paper.log                # 0 unresolved refs

# Confirm new values present
grep "partially complete" paper.tex
grep "large effect" paper.tex | grep "0.433"
grep "Cache read tokens" paper.tex
grep "Cost = mean cost" paper.tex
```

### Prior Fix Verification Table

| Fix | Paper Value | Source | Status |
| ----- | ------------- | -------- | -------- |
| E1: Shapiro-Wilk T2 | W=0.835, p=9.3e-11 | statistical_results.json: W=0.8351, p=9.345e-11 | CORRECT |
| E2: pairwise p-values | T4→T5 p=0.0024, T5→T6 p=0.0243 | JSON: 0.002373, 0.02430 | CORRECT |
| E3: test-007 T0 cost | $3.10 | Table 5 row | CORRECT |
| E4: test-017 T0 cost | $2.73 | Table 6 row | CORRECT |
| W4: test-021 tiers | T1, T2, T4 completed | External reports | CORRECT |
| W5: test-022 failures | T0/T5 framework failures | External reports | CORRECT |
| W6: subtest count | 74 of 120 | summary.json: 74, suite: 120 | CORRECT |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Branch 1048-haiku-analysis-paper, second review pass | [notes.md](../../references/notes.md) |

## Key Takeaways

1. **Every edit can introduce a new inconsistency**: After any fix, grep for ALL mentions of the affected concept
2. **Effect-size labels must use the paper's own threshold table**: δ=0.433 ≥ 0.43 = large, not medium-large
3. **Partial experiment descriptions appear in multiple places**: Summary intro vs. detailed analysis section often diverge
4. **"Cost" columns need units and scope**: Readers cannot distinguish mean/total/best without caption clarification
5. **Counter-intuitive numbers need one explanatory sentence**: Best Score = 0.00 with 40% pass rate looks like a bug without context
6. **Cache read pricing footnote matters when cache% ≥ 90%**: The stated $1/M input rate is misleading if 97% of tokens are $0.10/M cache reads
7. **Two-pass pdflatex is required**: Cross-references (Section~\ref{}) resolve on pass 2 only
