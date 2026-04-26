---
name: evaluation-paper-rewrite-after-data-fix
description: "Rewrite an arXiv LaTeX paper after discovering that underlying experimental data was wrong due to implementation bugs. Covers: (1) fixing data pipeline issues before rewriting, (2) parallel data verification against ground-truth sources, (3) systematic stale-value grep to ensure no remnants, (4) parallel agent rewrites of paper sections, (5) post-rewrite audit for numerical cross-referencing and structural issues, (6) common pitfalls like alphabetical-sort directory shadowing, pricing version confusion, and undefined citations from expanded sections."
category: evaluation
date: 2026-04-25
version: 1.0.0
user-invocable: false
verification: verified-local
tags: [latex, arxiv, paper-rewrite, data-fix, evaluation, parallel-agents, audit, cross-reference]
---

# Evaluation Paper Rewrite After Data Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Rewrite an arXiv paper (LaTeX) after discovering underlying experimental data was wrong due to implementation bugs, and after re-running missing judge evaluations to complete the dataset |
| **Outcome** | Success -- paper rewritten with all numerical claims verified against corrected data, zero stale values remaining |
| **Task Type** | Multi-phase paper rewrite with data pipeline fix, parallel section rewrites, and post-rewrite audit |
| **Verification** | verified-local (paper builds via tectonic, data verified, no CI for the paper itself) |

## When to Use

Use this skill when:

- **Experimental data changed** due to bug fixes in the evaluation pipeline, and the paper must be updated to reflect corrected results
- **Missing evaluations were re-run** (e.g., judge re-runs) and the paper needs to incorporate the now-complete dataset
- **A data pipeline bug** caused incorrect data loading (e.g., directory shadowing, wrong experiment directory selected)
- **Bulk numerical rewrite** is needed across a large LaTeX paper (~2000+ lines) with dozens of numerical claims
- **Post-rewrite verification** is needed to ensure zero stale values remain from the old dataset

**Trigger patterns:**
- "The data was wrong, we need to rewrite the paper"
- "We re-ran the judges, now update all the numbers"
- "The data loader was picking up the wrong experiment directory"
- "Verify all numbers in the paper match the new data"

## Verified Workflow

### Phase 0: Fix the Data Pipeline

**Fix the root cause before touching the paper.** Common data pipeline issues:

1. **Directory shadowing bug**: `load_all_experiments()` picks the LAST directory alphabetically as the "latest timestamped directory." Any non-timestamp directory (like `repos/`) that sorts after a timestamp directory (like `2026-03-30T...`) will shadow it.

   ```python
   # Bug: sorted(exp_dir.iterdir())[-1] picks 'repos' over '2026-03-30T...'
   # Fix: rename repos/ to .repos/ (hidden, excluded from sort)
   mv experiment_dir/repos experiment_dir/.repos
   ```

   **Location in ProjectScylla**: `src/scylla/analysis/loader.py:800` -- `load_all_experiments()` uses alphabetical sort on directory names.

2. **Judge re-run side effects**: `manage_experiment.py run` may create a `repos/` cache directory inside the experiment's parent dir, which triggers the shadowing bug above.

3. **Verify data loading after fix**:
   ```bash
   # Before fix: 720 runs loaded (incomplete)
   # After fix: 1080 runs loaded (complete dataset)
   python -c "from scylla.analysis.loader import load_all_experiments; print(len(load_all_experiments()))"
   ```

### Phase 1: Parallel Data Verification

**Read ALL data sources in parallel before touching the paper.** This establishes ground truth.

```bash
# Read these files in parallel (use multiple Read tool calls):
# 1. data/summary.json          -- tier-level aggregates
# 2. data/statistical_results.json -- hypothesis tests, effect sizes
# 3. data/srh_tier_experiment.json -- SRH test results (if applicable)
# 4. tables/tab*.md              -- all markdown tables (pre-rendered from data)
```

**Create a verification mapping** of every numerical claim category:

| Metric | Data Source | Field Path |
|--------|-------------|------------|
| Pass rates per tier | summary.json | `.tiers[].pass_rate` |
| Cost-of-Pass per tier | summary.json | `.tiers[].cost_of_pass` |
| Effect sizes | statistical_results.json | `.pairwise[].effect_size` |
| Confidence intervals | statistical_results.json | `.pairwise[].ci_lower`, `.ci_upper` |
| SRH test statistic | srh_tier_experiment.json | `.H_statistic` |
| Model pricing | Official pricing page | Verify model generation (e.g., Haiku 3 vs Haiku 4.5) |

### Phase 2: Systematic Stale-Value Identification

**Before rewriting, identify ALL old values that must change.**

```bash
# Grep for known old values (examples from a real session):
grep -n "0.630" paper.tex    # old pass rate
grep -n "0.759" paper.tex    # old score
grep -n "119.01" paper.tex   # old cost
grep -n "\-0.219" paper.tex  # old effect size
grep -n "catastrophic" paper.tex  # old narrative that may no longer apply

# Also grep for key narrative phrases tied to old data:
grep -n "degradation" paper.tex
grep -n "significant.*transition" paper.tex
grep -n "performance drop" paper.tex
```

**Record every match location.** This becomes the checklist for Phase 4 verification.

### Phase 3: Parallel Agent Rewrites

**Partition the paper into independent sections for parallel rewriting.** Recommended partitioning:

| Agent | Sections | Content |
|-------|----------|---------|
| Agent 1 | Abstract + Introduction | High-level claims, key findings summary |
| Agent 2 | Experimental Design + Methodology | Setup description, tier definitions |
| Agent 3 | Results + Analysis | All numerical results, statistical tests, figures |
| Agent 4 | Discussion + Conclusion + Appendices | Interpretation, limitations, supplementary tables |

**Each agent receives:**
1. The current paper section (Read with offset/limit)
2. The complete ground-truth data from Phase 1
3. The stale-value list from Phase 2
4. Explicit instruction: "Remove any narrative about [old finding] -- the data no longer supports it"

**Critical instruction for agents:**
- Replace ALL numerical values with values from the data sources
- Do NOT invent or interpolate numbers
- If a claim cannot be verified against a data source, flag it with `%% UNVERIFIED: <claim>`
- Remove narrative that depended on old data patterns (e.g., "T4-T6 degradation" if tiers now show improvement)

### Phase 4: Post-Rewrite Audit

**Run TWO independent audit agents after the rewrite:**

**Audit Agent 1 -- Numerical Cross-Reference:**
```bash
# For every number in the paper, verify it traces to a data source
# Check: summary.json, statistical_results.json, tables/*.md
# Flag: any number that doesn't match within rounding tolerance

# Example verification:
# Paper says "T6 CI [0.664, 1.000]"
# statistical_results.json says ci_lower: 0.664, ci_upper: 1.000
# PASS
```

**Audit Agent 2 -- Structural and LaTeX Issues:**
- Check for undefined citations (`\cite{key}` where key is not in .bib)
- Check for stale TikZ figures (colors, arrows, labels referencing old data)
- Check for inconsistent tier ordering or naming
- Check for orphaned figure/table references

**Common audit findings (from real session):**
1. Confidence intervals swapped between locations (T6 CI was [0.333, 0.889] in one place, [0.664, 1.000] in another)
2. New statistical glossary introduced 3 undefined citations
3. Wrong citation keys (e.g., `romano2006exploring` vs `romano2006appropriate`)
4. TikZ figure still had red coloring and "Performance drop" arrow from old narrative
5. Related Work section still referenced "significant T2-T3 transition point" from old data

### Phase 5: Final Stale-Value Sweep

```bash
# Grep for ALL old values identified in Phase 2
# Target: ZERO matches for any old value
grep -n "0.630\|0.759\|119.01\|\-0.219\|catastrophic" paper.tex
# Expected output: (empty)

# Build the paper to verify compilation
pixi run --environment docs paper-build
# Or: pdflatex + bibtex + pdflatex + pdflatex
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Judge re-run without checking side effects | Ran `manage_experiment.py run` to re-run missing judges | Created `repos/` directory that shadowed the real experiment directory in data loader (alphabetical sort picked `repos/` over `2026-03-30T...`) | Always check for side-effect directories after running pipeline commands; rename to `.repos/` or similar hidden name |
| Rewrite agents without explicit stale-narrative removal | Told agents to "update numbers" but not to remove old narrative | Two locations survived: Related Work still claimed "significant T2-T3 transition point" and TikZ figure still had red "Performance drop" arrow | Explicitly list OLD narrative claims that must be removed, not just old numbers |
| New statistical glossary without citation check | Agent expanded Section 4.5 with 9 statistical test subsections | Cited 3 papers not in references.bib (`shapiro1965analysis`, `benjamini1995controlling`, `razali2011power`) and used wrong citation key (`romano2006exploring` vs `romano2006appropriate`) | Any agent adding new citations must verify keys exist in the .bib file or add the entries |
| SRH formula transcription | Agent wrote formula from memory | Formula `H_factor = SS_factor/SS_total / ((N-1)/N)` was wrong; correct is `H_factor = SS_factor / (SS_total/(N-1))` | Always copy statistical formulas from authoritative sources, never from memory |
| Single-pass rewrite without audit | Rewrote all sections, then built the paper | 12 issues discovered only after a dedicated audit pass | Always run post-rewrite audit agents -- they catch issues the rewrite agents miss |
| Using old model pricing | Used Haiku 3 pricing ($0.25/$1.25 per MTok) for Haiku 4.5 | 4x pricing error in cost calculations | Always verify pricing against the official page for the SPECIFIC model version being evaluated |

## Results & Parameters

### Verified Rewrite (2026-04-25)

| Parameter | Value |
|-----------|-------|
| Paper size | ~2300 lines LaTeX |
| Data sources | summary.json, statistical_results.json, srh_tier_experiment.json |
| Tables | 11 table files (tab01-tab11, .md and .tex) |
| Parallel rewrite agents | 4 (abstract+intro, experimental design, results, sections 6-10+appendices) |
| Audit agents | 2 (numerical cross-reference, structural/LaTeX) |
| Issues found by audit | 12 |
| Stale values after sweep | 0 |
| Build system | `pixi run --environment docs paper-build` (tectonic engine) |

### Key Pricing Reference

| Model | Input (per MTok) | Output (per MTok) |
|-------|-------------------|---------------------|
| Haiku 3 | $0.25 | $1.25 |
| Haiku 4.5 | $1.00 | $5.00 |
| Sonnet 4.5 | $3.00 | $15.00 |

### Data Pipeline Fix

| Before | After |
|--------|-------|
| `repos/` directory shadowed experiment dir | Renamed to `.repos/` |
| 720 runs loaded (incomplete) | 1080 runs loaded (complete) |
| `sorted(exp_dir.iterdir())[-1]` picked `repos` | Now picks `2026-03-30T...` correctly |

### Critical Patterns

**Data loader alphabetical sort bug:**
```python
# src/scylla/analysis/loader.py:800
# load_all_experiments() picks LAST directory alphabetically
# Any non-timestamp directory sorting after the timestamp will shadow it
# Fix: ensure only timestamped directories exist, or hide others with dot-prefix
```

**Cross-reference verification checklist:**
```
For every numerical claim in the paper:
1. Identify the source file and field path
2. Read the actual value from the source
3. Compare to the paper's stated value (within rounding tolerance)
4. If mismatch: fix the paper, not the data
```

**Model pricing verification:**
```
Before writing any cost analysis:
1. Identify the exact model version (generation matters)
2. Check the official pricing page for that version
3. Verify input AND output pricing separately
4. Cross-check against the pricing used in the evaluation code
```

## Related Skills

- `paper-revision-workflow` -- Systematic paper revision (data validation, structural improvements, tone unification)
- `latex-paper-parallel-assembly` -- Assembling LaTeX paper from parallel agent parts
- `academic-paper-validation` -- Validating academic paper accuracy
- `paper-iterative-accuracy-review` -- Iterative accuracy review workflow
- `paper-validation-workflow` -- End-to-end paper validation

## References

- Data loader bug location: `src/scylla/analysis/loader.py:800` in ProjectScylla
- Paper location: `docs/arxiv/haiku/paper.tex` in ProjectScylla
- Data directory: `docs/arxiv/haiku/data/` in ProjectScylla
- Build command: `pixi run --environment docs paper-build`
