---
name: latex-paper-peer-review
description: Apply expert peer review corrections to LaTeX research papers with statistical analysis pipelines
category: research
date: 2026-02-22
user-invocable: false
---

# Skill: LaTeX Paper Peer Review Corrections

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Apply rigorous expert peer review to a 900-line LaTeX paper with a Python statistical pipeline |
| **Outcome** | ✅ All 7 critical + 8 minor issues resolved; 0 LaTeX errors; 316 tests pass; PR merged |
| **Context** | ProjectScylla Haiku analysis paper (arXiv), stats pipeline in `scylla/analysis/` |

## Overview

This skill documents the complete workflow for applying expert peer review corrections to a
LaTeX paper that is backed by a reproducible Python statistical pipeline. The key pattern:
**fix the pipeline first, regenerate data, then fix the paper text** — never manually patch
paper numbers.

## When to Use

Use this skill when:

- A peer review identifies factual errors, statistical inconsistencies, or missing analyses in a LaTeX paper
- The paper claims are generated from a Python pipeline (stats, figures, tables)
- Statistical methodology issues exist: wrong family size for multiple comparisons, hand-calculated instead of pipeline-computed values, missing uncertainty bounds
- The paper references generated figures/artifacts that are not actually included
- LaTeX packages are imported but never used (graphicx loaded, no `\includegraphics`)

## Verified Workflow

### 1. Triage Issues by Category Before Starting

**Separate issues into three tracks:**
1. **Pipeline code fixes** — `export_data.py`, `stats.py` (must come first)
2. **Paper text fixes** — `paper.tex` (depends on pipeline output)
3. **Generated artifact fixes** — figures, tables (regenerate after pipeline fix)

Fix pipeline → regenerate JSON → fix paper text. Never go in reverse order.

### 2. Reconcile Pipeline vs Paper Discrepancies

**Common pattern**: Two code paths compute overlapping statistics with different family sizes.

Example from this session:
- `export_data.py` computed 6 adjacent Holm-Bonferroni comparisons
- `comparison.py` computed 7 (6 adjacent + T0→Tlast overall contrast)
- Paper showed 7 in the table but pipeline only stored 6

**Fix pattern for `export_data.py`**:
```python
# After the adjacents loop, add the first→last contrast to the SAME raw_p_values list
# so Holm-Bonferroni is applied to all 7 together
first_data = model_runs[model_runs["tier"] == tier_order[0]]
last_data = model_runs[model_runs["tier"] == tier_order[-1]]
if len(first_data) > 0 and len(last_data) > 0:
    _, p_fl = mann_whitney_u(
        first_data["passed"].astype(int), last_data["passed"].astype(int)
    )
    raw_p_values.append(p_fl)
    test_metadata.append({
        ...,
        "overall_contrast": True,  # flag for downstream filtering
    })
# THEN apply correction to all len(raw_p_values) at once
corrected = holm_bonferroni_correction(raw_p_values)
```

**State in paper**: "Holm-Bonferroni corrected, $m=7$" — be explicit about family size in table captions.

### 3. Integrate Pipeline-Computed Power Analysis

**Problem**: Power analysis functions existed in `stats.py` but were never called from `export_data.py`. Paper stated hand-calculated "approximately 0.40–0.50".

**Fix**:
1. Import `mann_whitney_power` and `kruskal_wallis_power` in `export_data.py`
2. Add `"power_analysis": []` to the results dict
3. After effect sizes loop, iterate tier transitions again to compute power at observed δ AND at reference medium effect (δ=0.3)
4. Also compute omnibus KW power at a reference η²=0.06

**Paper update**: Replace "approximately 0.40–0.50" with actual computed values per transition. This converts a hand-calculated claim into a pipeline-verified claim.

```python
# Add to results dict init:
"power_analysis": [],

# After effect_sizes computation:
for model in models:
    for i in range(len(tier_order) - 1):
        # Look up observed delta from effect_sizes just computed
        observed_delta = next(
            (es["cliffs_delta"] for es in results["effect_sizes"]
             if es["model"]==model and es["metric"]=="pass_rate"
             and es["tier1"]==tier_order[i] and es["tier2"]==tier_order[i+1]),
            None
        )
        if observed_delta is None:
            continue
        power_obs = mann_whitney_power(n1, n2, abs(observed_delta))
        power_med = mann_whitney_power(n1, n2, 0.3)
        results["power_analysis"].append({
            "model": model, "metric": "pass_rate",
            "tier1": tier_order[i], "tier2": tier_order[i+1],
            "n1": n1, "n2": n2,
            "observed_delta": float(observed_delta),
            "power_at_observed": float(power_obs),
            "power_at_medium_0_3": float(power_med),
        })
```

### 4. Fix Superlative Claims Against Aggregate Data

**Common error**: "X achieves the highest Y" when a tier with very few samples has a higher value.

**Pattern**:
- Check the actual data: T6=0.933 > T2=0.831 for pass rate
- But T6 has n=1 subtest (15 runs) vs T2 has n=14 subtests (130 runs)
- T6's CI is [0.667, 1.000] — extremely wide

**Fix template**:
```latex
% WRONG:
highest pass rate (83.1\%)

% CORRECT:
highest pass rate among tiers with representative coverage (T0--T4: 83.1\%,
compared to T6's 93.3\% from a single subtest with wide CI [0.667, 1.000])
```

### 5. Fix Degenerate Statistical Test Framing

**Scheirer-Ray-Hare with single model = Kruskal-Wallis**

When there is only one model in the dataset, SRH degenerates:
- `agent_model` factor: df=0, H=0.0, p=NaN
- interaction: df=0, H=0.0, p=NaN
- Only tier effect is meaningful

**Wrong framing** (implies full two-way analysis worked):
```latex
The Scheirer-Ray-Hare two-way test (tier × task) confirms the tier effect...
```

**Correct framing**:
```latex
The Scheirer-Ray-Hare test, which reduces to a one-way Kruskal-Wallis equivalent
in this single-model design (agent\_model has df=0; interaction term is not estimable),
confirms the tier main effect on score: $H_{\text{tier}}(6) = 22.63$, $p = 0.0009$.
This result is mathematically equivalent to a standalone Kruskal-Wallis test on tier.
```

### 6. Include Figures That Were Generated But Not Included

**Symptom**: Paper loads `graphicx`, sets `\graphicspath`, but has zero `\includegraphics`. Data dictionary claims N generated figures.

**Verify figures exist**:
```bash
ls docs/arxiv/haiku/figures/*.png | wc -l
```

**Include 4–6 key figures** near the cross-test analysis section using `subfigure`:
```latex
\begin{figure}[htbp]
\centering
\begin{subfigure}[b]{0.48\textwidth}
  \includegraphics[width=\textwidth]{fig04_pass_rate_by_tier}
  \caption{Pass rate by tier (aggregate, 95\% CI).}
  \label{fig:pass-rate-tier}
\end{subfigure}
\hfill
\begin{subfigure}[b]{0.48\textwidth}
  \includegraphics[width=\textwidth]{fig08_cost_quality_pareto}
  \caption{Cost-quality Pareto front.}
  \label{fig:pareto}
\end{subfigure}
\caption{Key aggregate results. All N figures available in \texttt{figures/}.}
\label{fig:key-results}
\end{figure}
```

Note: `\graphicspath{{./figures/}}` means filenames do NOT include the directory.

### 7. Regenerate Pipeline Output and Verify Numbers Match Paper

```bash
# Regenerate statistical_results.json
pixi run python scripts/export_data.py \
  --data-dir ~/fullruns/<experiment-name> \
  --output-dir docs/arxiv/<paper>/data

# Verify key values match paper
python3 -c "
import json
with open('docs/arxiv/<paper>/data/statistical_results.json') as f:
    d = json.load(f)
# Check T0->Tlast is in pairwise_comparisons
print([x for x in d['pairwise_comparisons'] if x.get('tier1')=='T0' and x.get('tier2')=='T6'])
print('power_analysis entries:', len(d.get('power_analysis', [])))
"
```

### 8. LaTeX Compilation Verification

```bash
cd docs/arxiv/<paper>
# First pass (may have undefined references)
pdflatex -interaction=nonstopmode paper.tex

# Second pass (resolves cross-references)
pdflatex -interaction=nonstopmode paper.tex

# Check for errors (expect 0)
grep -c "^!" paper.log
```

Pre-commit hook fixes trailing newlines in JSON — always re-stage after first commit attempt.

### 9. Cliff's Delta Citation Verification

The thresholds (0.11/0.28/0.43) come from Romano et al. 2006 FAIR conference paper.
Standard literature sometimes cites different thresholds (0.147/0.33/0.474).

**Always note borderline cases**: δ=0.433 is barely above the 0.43 threshold — classified as "large" under FAIR thresholds but "medium" under the alternative.

**Fix in both `stats.py` docstring AND `paper.tex`**:
```latex
% In paper.tex:
Effect size: Cliff's $\delta$ (Romano et al., 2006 FAIR conference thresholds:
negligible $|{\delta}| < 0.11$, small $< 0.28$, medium $< 0.43$, large $\geq 0.43$;
note these differ from the widely-cited Romano et al.\ 0.147/0.33/0.474
thresholds---effects near 0.43 are borderline medium/large).
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|---------------|---------------|
| Running `export_data.py --data-dir ~/fullruns/haiku` | `ERROR: No experiments found` | Directory structure was flat timestamped dirs, not named experiment dirs |
| Looking for `result.json` in run dirs | `JSONDecodeError: Expecting value` | Correct filename is `run_result.json` (not `result.json`) |
| Committing without re-staging after pre-commit | Commit failed | `end-of-file-fixer` hook modifies JSON files; must `git add` them again |
| Expecting `load_all_experiments` to work on any path | Silent "skipping" | Loader expects `<data-dir>/<exp-name>/<timestamp>/` structure; haiku-analysis had the right layout |

## Results & Parameters

### fullruns Directory Structure Required by Loader

```text
<data-dir>/
  <experiment-name>/          ← named directory (e.g., test-002)
    <timestamp>/              ← timestamped subdir (loader uses latest)
      config/
        experiment.json       ← must have "models": ["<model-id>"]
      T0/
        00/
          run_01/
            run_result.json   ← NOT result.json
```

### Correct `export_data.py` Invocation

```bash
pixi run python scripts/export_data.py \
  --data-dir ~/fullruns/haiku-analysis \   # named-exp parent dir
  --output-dir docs/arxiv/haiku/data
```

### Pre-commit Double-Stage Pattern

```bash
git add <files>
git commit -m "..."
# If end-of-file-fixer fires:
git add <json-files>   # re-stage the fixed files
git commit -m "..."    # commit again
```

### Power Values from This Session (Haiku paper)

| Transition | N1, N2 | Observed δ | Power@observed | Power@medium(0.3) |
|------------|--------|------------|----------------|-------------------|
| T0→T1 | 117, 83 | 0.094 | 0.20 | 0.95 |
| T1→T2 | 83, 130 | 0.096 | 0.22 | 0.96 |
| T2→T3 | 130, 122 | -0.068 | 0.16 | 0.98 |
| T3→T4 | 122, 123 | 0.051 | 0.10 | 0.98 |
| T4→T5 | 123, 30 | -0.313 | **0.77** | 0.73 |
| T5→T6 | 30, 15 | +0.433 | **0.68** | **0.37** ← underpowered |

Key insight: T0–T4 null results reflect genuinely small effects (power 0.95–0.98 at medium), not insufficient power.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1060 — Haiku analysis paper peer review | [notes.md](references/notes.md) |
