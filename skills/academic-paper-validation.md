---
name: academic-paper-validation
description: Systematic workflow for validating and improving academic paper quality through data accuracy checks, statistical methodology verification, LaTeX compilation fixes, and arXiv build preparation
category: documentation
date: 2026-04-07
version: 3.0.0
user-invocable: false
---
# Academic Paper Validation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-05 (v1.0.0), 2026-02-06 (v2.0.0), 2026-02-22 (v2.1.0), 2026-04-06–08 (v3.0.0) |
| **Objective** | Validate and improve academic paper quality through systematic data accuracy checks, statistical rigor improvements, LaTeX fixes, and noise reduction |
| **Outcome** | v1.0.0: Fixed contractions, colloquialisms, broken paths, statistical language (N=1 dryrun). v2.0.0: Fixed 2 data errors, 2 typos, 12+ statistical claims, 11 cross-references, removed 3 degenerate figures. v2.1.0: Fix pipeline → regenerate data → fix paper text pattern, Holm-Bonferroni family size, SRH degenerate framing, Cliff's delta citation. v3.0.0: Verified 60+ quantitative claims, caught statistical method naming error (Dunn's vs Mann-Whitney U), caught incorrect pairwise comparison count (21 vs 7), fixed Unicode/table/path issues, built arXiv submission |
| **Models Used** | Sonnet 4.5 (v1.0.0), Opus 4.6 (v2.0.0–v3.0.0) |

## When to Use This Skill

Use this workflow when:

- Preparing an academic paper for submission or publication
- Reviewing a paper that presents experimental results with small sample sizes
- Validating quantitative claims against source data
- Improving statistical rigor and hedging language
- Cleaning up redundant content and low-value visualizations
- Fixing LaTeX cross-references and formatting issues
- Verifying statistical methodology claims — checking that named tests match what the code/data actually computed
- Verifying multiple comparison corrections — checking that the number of claimed pairwise comparisons matches actual
- Fixing LaTeX compilation errors related to Unicode characters, table formatting, or path issues
- Building arXiv submission packages from source LaTeX with automated transformations
- A peer review identifies factual errors, statistical inconsistencies, or missing analyses in a LaTeX paper
- The paper claims are generated from a Python pipeline (stats, figures, tables)
- Formalizing informal writing to academic standards (contractions, colloquialisms)
- Fixing reproducibility issues (broken paths, incorrect scripts)
- The paper's abstract and conclusions contain near-verbatim repeated statistics

**Trigger phrases**: "validate the paper", "check paper accuracy", "review paper for errors", "improve paper quality", "prepare paper for submission"

**Red flags that indicate you need this skill**:
- Paper contains phrases like "approximately", "~", or broad ranges where precise values exist
- Figures show "no variance" or "all zeros" but are still included
- Same content appears in multiple sections (Abstract + Summary + Introduction)
- Unicode characters (rho, Delta, alpha, mu, sigma) in LaTeX source instead of math mode
- Table compilation errors with column count mismatches
- Paper names a statistical test but the JSON/CSV data contains field names suggesting a different test
- Paper claims C(k,2) pairwise comparisons but the data file has fewer actual comparisons
- Paper uses causal language ("causes", "drives") in an observational (non-randomized) study
- Universality words ("consistently", "always") appear adjacent to hedging words ("task-dependent", "contingent")
- Paper claims "monotonic" trends from aggregate data but per-experiment trends differ
- A non-significant result is described with unhedged strong language in summary sections

## Verified Workflow

### Phase 0: Pre-Review Planning (DO NOT Skip)

**DO NOT start fixing immediately.** First, create a comprehensive analysis plan:

1. **Consult prior review notes** (if multiple rounds): Search for existing review skills or `.notes.md` files documenting what was already fixed. After 3+ rounds, remaining issues shift from factual errors to subtle rounding discrepancies and framing issues.
2. **Read the entire paper** to understand scope and structure.
3. **Create systematic analysis plan** organized by severity:
   - CRITICAL: Factual errors, broken paths, incorrect data
   - IMPORTANT: Statistical language issues, inconsistencies
   - MINOR: Spelling, grammar, style
4. **Validate against source data** — read actual data files before claiming errors.
5. **Document findings** before making any changes.

**Key Learning:** Analysis plans can incorrectly flag correct statistics. Always verify claims by recomputing from source data first.

### Phase 1: Data Accuracy (CRITICAL - Do First)

**Objective**: Cross-reference every quantitative claim against source data

**Steps**:
1. Identify all numeric claims in the paper (counts, percentages, ratios, costs)
2. Locate the source data files or analysis outputs:
   ```bash
   find . -name "*.csv" -o -name "*.json" -o -name "result.json"
   ```
3. Verify each claim by recalculating from raw data
4. Document discrepancies in a table: Location | Current | Ground Truth | Fix
5. Apply fixes using Edit tool with exact string matching

**Example fixes**:
- Figure/table counts: "25 figures and 10 tables" → "24 figures and 10 tables" (counted PDFs)
- Percentages: "80-99%" → "79-95%" (recalculated from actual data)
- Typos: "what it is means" → "what it means"

**Critical**: Fix data errors FIRST before any other changes, as these affect credibility.

**Common Data Accuracy Issues Found**:
- Broad ranges used when all values are identical (e.g., "0.95-1.00" when all are 1.00)
- Rounding that obscures precision (e.g., "25-41 seconds" when actual is 24.8-41.2s)
- Percentage claims that don't match actual data
- Correlation strength claims that contradict values

### Phase 2: Statistical Methodology Verification (CRITICAL)

**Objective**: Verify that named statistical tests match the actual computation.

#### 2a. Verify Test Names and Comparison Counts

```bash
# 1. Identify what statistical test the paper claims
# Example: "Dunn's post-hoc test with Bonferroni correction"

# 2. Find the statistical results data file
find . -name "statistical_results.json" -o -name "srh_tier_experiment.json"

# 3. Check field names in the JSON for the actual test used
# "u_statistic" → Mann-Whitney U test, NOT Dunn's test
# "H_statistic" → Kruskal-Wallis H test
# "dunn_statistic" → Dunn's test
python3 -c "import json; data=json.load(open('statistical_results.json')); print([k for k in data[0].keys() if 'stat' in k.lower()])"

# 4. Count actual pairwise comparisons vs claimed
# Paper may claim C(k,2) = C(7,2) = 21 comparisons but data may only have 7
python3 -c "import json; data=json.load(open('statistical_results.json')); print(f'Actual comparisons: {len(data)}')"
```

**Key principle**: The JSON field names are ground truth for which test was used.

#### 2b. Verify Holm-Bonferroni Family Size

When two code paths compute overlapping statistics with different family sizes, the paper must be explicit about which is used. Example:

- `export_data.py` computed 6 adjacent Holm-Bonferroni comparisons
- `comparison.py` computed 7 (6 adjacent + T0→Tlast overall contrast)
- Paper showed 7 in the table but pipeline only stored 6

**Fix pattern for `export_data.py`**: Add the first→last contrast to the SAME `raw_p_values` list so Holm-Bonferroni is applied to all comparisons together. State in paper: "Holm-Bonferroni corrected, $m=7$" — be explicit about family size in table captions.

#### 2c. Pipeline-Computed Power Analysis

**Problem**: Power analysis functions may exist but never be called from the data export script. The paper then states hand-calculated estimates.

**Fix**:
1. Import power functions in `export_data.py`
2. Add `"power_analysis": []` to the results dict
3. After effect sizes loop, compute power at observed δ AND at reference medium effect (δ=0.3)
4. Replace hand-calculated estimates with actual pipeline-verified values

```python
# Add to results dict init:
"power_analysis": [],

# After effect_sizes computation:
for model in models:
    for i in range(len(tier_order) - 1):
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

#### 2d. Cliff's Delta Citation Verification

The thresholds 0.11/0.28/0.43 come from Romano et al. 2006 FAIR conference paper. Standard literature sometimes cites different thresholds (0.147/0.33/0.474 from the Romano et al. 2006 journal article — a different publication).

**Always note borderline cases**: δ=0.433 is barely above the 0.43 threshold — classified as "large" under FAIR thresholds but "medium" under the alternative.

**Fix in both `stats.py` docstring AND `paper.tex`**:
```latex
Effect size: Cliff's $\delta$ (Romano et al., 2006 FAIR conference thresholds:
negligible $|{\delta}| < 0.11$, small $< 0.28$, medium $< 0.43$, large $\geq 0.43$;
note these differ from the widely-cited Romano et al.\ 0.147/0.33/0.474
thresholds---effects near 0.43 are borderline medium/large).
```

#### 2e. Degenerate Statistical Test Framing

**Scheirer-Ray-Hare with single model = Kruskal-Wallis**

When there is only one model in the dataset, SRH degenerates:
- `agent_model` factor: df=0, H=0.0, p=NaN
- interaction: df=0, H=0.0, p=NaN
- Only the tier effect is meaningful

**Wrong framing**:
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

### Phase 3: Table Semantics Verification

**Check column aggregation conventions**:

Tables that mix per-row means with a "Total" row showing absolute sums create ambiguity. Always verify:

```bash
# If tier rows show per-run averages but Total row shows absolute sums, add a footnote
# Example LaTeX table footnote:
# \footnote{Token columns show per-run means for tier rows; the Total row shows absolute totals.}
```

### Phase 4: Statistical Language (HIGH Priority)

**Objective**: Adjust language strength to match statistical power (N=1 requires hedging)

**Pattern matching**:
- "confirms" → "is consistent with" / "supports" / "suggests"
- "proves" → "showing" / "indicating"
- "demonstrates" → "suggesting" (when making causal claims)
- Keep "validates" when referring to methodology/pipeline validation (appropriate use)
- "consistently outperform" → "outperform in aggregate" (when per-task results vary)
- "eliminates the possibility" → "provides no evidence of" (for non-significant results under low power)

**Add explicit warnings for small samples**:
```markdown
**Note**: N=7 is insufficient for reliable correlation estimates; these
values are reported for completeness but should be interpreted with extreme
caution.
```

**Remove misleading headers**:
- Table header "Mean Score (±σ)" → "Mean Score" (when N=1 has no σ)

**Steps**:
1. Search for strong causal language:
   ```bash
   grep -n "confirms\|proves\|demonstrates\|validates\|causes\|drives\|consistently\|eliminates" paper.tex
   ```
2. For each instance, assess context — hedge results, not methodology
3. Verify paper still acknowledges N=1 limitations in dedicated section
4. **After fixing one section, grep ALL other sections for the same phrasing** (cross-section regression is common — Abstract/Contributions/Appendix/Further Work often retain unhedged language after body is fixed)

### Phase 5: Cross-Reference Infrastructure (HIGH Priority)

**Objective**: Replace hardcoded section numbers with LaTeX auto-references

**Steps**:
1. Add `\label{}` to all `\section`, `\subsection`, `\subsubsection` commands
   ```latex
   \section{Introduction}\label{sec:intro}
   \subsection{Cost Analysis}\label{sec:cost-tradeoffs}
   ```

2. Find all hardcoded references:
   ```bash
   grep -n "section [0-9]\|Section [0-9]\|Section~[0-9]" paper.tex
   ```

3. Replace with `\ref{}`:
   - "Section 4" → "Section~\ref{sec:methodology}"

4. Remove manual numbering from subsection titles:
   - "\subsubsection{4.2.1 Title}" → "\subsubsection{Title}"

5. Compile twice and verify: `grep "??" paper.log` should return 0

6. After renaming any `\label{}`, grep for all `\ref{}` and `\autoref{}` calls to the old label name. Also check `\input{}` files.

### Phase 6: Tone Formalization (When Needed)

**Step 1: Remove all contractions** using replace_all:

```python
contractions = {
    "don't": "do not",
    "doesn't": "does not",
    "can't": "cannot",
    "it's": "it is",
    "that's": "that is",
    "there's": "there is",
    "let's": "let us",
    "we're": "we are",
    "isn't": "is not",
    "haven't": "have not",
    # ... etc
}
# Use Edit tool with replace_all=true for each
```

**Step 2: Mark colloquial segments** with `<coq>` tags for manual review:
- "Here's the thing" → `<coq>Here is the thing</coq>`
- "heavy hitter" → `<coq>heavy hitter</coq>`
- "eats the budget" → `<coq>eats the budget</coq>`

**Result:** User can then manually replace tagged segments with formal equivalents.

### Phase 7: LaTeX Compilation Fixes

**Fix Unicode Characters**:

```latex
% WRONG (will fail compilation):
Spearman rho = 0.333, mean Delta = 0.033, Krippendorff's alpha = -0.117

% CORRECT (use LaTeX math):
Spearman $\rho$ = 0.333, mean $\Delta$ = 0.033, Krippendorff's $\alpha$ = -0.117
```

**Fix Table Column Mismatches**:

```latex
% ERROR: 5 columns declared but only 4 in header
\begin{tabular}{|l|l|l|l|l|}  % <-- 5 columns
\hline
Tier & Agent Time & Judge Time & Total Time & Judge % \\  % <-- only 4!

% FIX: Match column count (use right-align for numbers)
\begin{tabular}{|l|r|r|r|r|}
\hline
Tier & Agent Time (s) & Judge Time (s) & Total Time (s) & Judge \% of Total \\
```

**Escape Underscores in Auto-Generated Tables**:

```latex
% FAILS: unescaped underscore
code_quality & 0.20 & 1.000 $\pm$ 0.000 \\

% WORKS:
code\_quality & 0.20 & 1.000 $\pm$ 0.000 \\
```

**Fix Appendix Structure**:
- Move `\appendix` command BEFORE appendix content
- Change `\subsection{Appendix A}` → `\section{Title}` (LaTeX auto-letters them)

### Phase 8: Fix Superlative Claims Against Aggregate Data

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

### Phase 9: Path and Reproducibility Fixes

**Extract archived data** if references point to nonexistent directories:

```bash
# Check if archives exist
ls docs/*.tar.gz

# Extract to create referenced directory structure
tar -xzf docs/dryrun-analysis.tar.gz -C docs/

# Verify extraction
ls docs/paper-dryrun/figures/*.png | wc -l
```

**Update script paths** to reference actual scripts:

```bash
# Find actual script names
ls scripts/*.py | grep -E "(run|experiment)"
# Update paper references: Wrong: scylla/run_evaluation.py → Right: scripts/run_e2e_experiment.py
```

**For arXiv path transformations**:

```python
# In build_arxiv_paper.py or transformation script:
def fix_relative_paths(content: str) -> str:
    """Transform paths for arXiv submission."""
    # Fix docs/paper-dryrun/ prefixes
    content = re.sub(r"docs/paper-dryrun/figures/", "figures/", content)
    content = re.sub(r"docs/paper-dryrun/tables/", "tables/", content)

    # ALSO fix bare paper-dryrun/ prefixes (commonly missed!)
    content = re.sub(r"paper-dryrun/figures/", "figures/", content)
    content = re.sub(r"paper-dryrun/tables/", "tables/", content)

    return content
```

**Verify build script file globs**: If the script includes figures by extension (e.g., `*.pdf`), verify this matches actual file format (PNG, PDF). A format mismatch produces a tarball with ZERO figure files even though LaTeX compiles fine.

### Phase 10: Pipeline-First Approach for Generated Papers

When paper claims are generated from a Python pipeline, always: **fix the pipeline → regenerate data → fix the paper text**. Never manually patch paper numbers.

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
print([x for x in d['pairwise_comparisons'] if x.get('tier1')=='T0' and x.get('tier2')=='T6'])
print('power_analysis entries:', len(d.get('power_analysis', [])))
"
```

### Phase 11: Redundancy Reduction (MEDIUM Priority)

**Strategy**:
1. Identify repeated numeric claims (e.g., "3.8x" mentioned 6 times)
2. Keep claims in 3 key locations: Abstract/Introduction, Results section, Conclusions
3. For middle sections, replace with back-references

**Consolidate Redundant Sections** — Abstract + Summary + Introduction often overlap:
1. Identify unique content in Summary not in Abstract
2. Merge unique content into Introduction
3. Remove Summary section entirely

**Abstract/Conclusions near-verbatim redundancy**: The Abstract states results for readers deciding whether to read the paper; Conclusions synthesize findings and add interpretive insight. Conclusions should use interpretive language ("These results suggest...") rather than restating raw statistics verbatim.

### Phase 12: Low-Value Content Removal (LOWER Priority)

For N=1 experiments, identify degenerate content (zero variance):
- Box plots with no variance (all values identical)
- Bootstrap confidence intervals that collapse to points
- Histograms with single bins

**Steps**:
1. Review all figures in appendix
2. For each, ask: "Does this show meaningful variance or provide insight?"
3. Remove degenerate figures by deleting entire `\begin{figure}...\end{figure}` blocks

### Phase 13: Establish Single Source of Truth

**Problem**: Build scripts check alignment between `paper.md` and `paper.tex`, causing false warnings.

```python
# In verify_paper_alignment.py:
if __name__ == "__main__":
    # paper.tex is now the single source of truth
    print("Note: paper.tex is the source of truth (paper.md is deprecated)")
    print("Verification skipped - paper.tex is canonical")
    sys.exit(0)
```

### Verification Checklist

```bash
cd docs/
# Compile twice to resolve references
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Or with tectonic via pixi (preferred):
pixi run --environment docs paper-build

# Check for errors
grep -c "??" paper.log      # Should be 0 (no unresolved refs)
grep -c "^!" paper.log       # Should be 0 (no LaTeX errors)

# Spot-check key fixes
grep -n "confirms\|proves\|demonstrates\|consistently\|eliminates" docs/paper.tex
grep -n "Section~\\ref{" paper.tex | head

# Verify PDF
ls -lh paper.pdf  # Should exist and be reasonable size

# Verify build tarball includes figures (check glob format)
ls figures/ | head   # Check actual extensions (PNG vs PDF)
grep "figures/\*\." build.sh  # Verify glob matches actual format
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempting to fix all issues in parallel | Made multiple types of edits simultaneously (data fixes + language + formatting) | Hard to track which changes addressed which issues; critical data errors missed | Work through phases sequentially — data accuracy MUST come first |
| Using `replace_all=true` for statistical language | Replaced all instances of "confirms" at once | Some uses of "confirms" are appropriate (methodology context) — blanket replacement broke them | Manually review each instance in context; use `replace_all=false` with enough surrounding context |
| Removing "validates" from all contexts | Initial plan was to replace "validates" along with "confirms/proves/demonstrates" | "Validates" is appropriate when discussing methodology validation (not results generalization) | Keep "validates" for pipeline/methodology/design validation; only hedge causal claims about results |
| Compile LaTeX before fixing Unicode | Attempted to compile with Unicode characters directly in source | `! LaTeX Error: Unicode character (U+03C1) not set up for use with LaTeX.` | Search for Unicode first (`grep -P "[\x80-\xFF]" paper.tex`), replace with math mode before compiling |
| Assume auto-generated tables are LaTeX-safe | Used table files generated from CSV with underscores | `! Missing $ inserted.` on `code_quality & 0.20` | Run `scripts/fix_table_underscores.py` on all auto-generated tables |
| Incomplete path transformation | Added transformation for `docs/paper-dryrun/` but missed bare `paper-dryrun/` prefix | `! LaTeX Error: File 'paper-dryrun/tables/...' not found.` | Search for ALL path prefix variations: `grep -r "paper-dryrun" docs/paper.tex` |
| Keep all generated figures | Included all 26 generated figures in appendix | With N=1 dryrun, 5 figures showed all zeros or flat lines — dilutes message | Review each figure for information content; remove if "no variance" |
| Trust automated contraction detection | An exploration agent reported "5 contractions found" | Zero contractions existed — confirmed with `grep -nP` regex; the automated finding was a false positive | ALWAYS verify automated findings independently with your own regex search |
| Accept reviewer's reference thresholds | Review prompt cited Cliff's delta thresholds 0.11/0.28/0.43 | Paper correctly uses Romano (2006) thresholds 0.147/0.33/0.474 — a different but valid standard | Verify the reviewer's assumptions too, not just the paper; check the paper's cited source directly |
| Assume C(k,2) pairwise comparisons | Paper claimed "21 pairwise comparisons C(7,2)" | Statistical results JSON had only 7 comparisons (6 adjacent transitions + T0-T6) | Never assume C(k,2) — check actual data file for real count; difference matters for Bonferroni correction |
| Fix statistical language in one section only | Fixed "consistently" in Abstract | The same word appeared in Conclusions section and was missed | After any hedging fix, grep ALL sections — Abstract, Introduction, Contributions, Discussion, Conclusions, Appendix, Further Work |
| Patch paper numbers manually | Edited paper.tex directly with revised statistics | Statistics re-diverged from pipeline when pipeline was later corrected | Fix pipeline first, regenerate JSON, then update paper — never manually patch generated numbers |
| Claim Pareto-dominance from one significant dimension | Asserted "strictly Pareto-dominant" when cost difference p=0.676 (n.s.) | Cannot claim Pareto dominance on a dimension where the null hypothesis is not rejected | When "Pareto" language appears, verify BOTH dimensions are established (significant or at least equal) |
| Use "eliminates the possibility" for a non-significant result | Said n.s. cost finding "eliminates the possibility of a trade-off" | Non-significant result under low power does not eliminate the possibility — it fails to detect a difference | Change to "provides no evidence of" for n.s. results; "eliminates" requires definitive power to reject |
| Trust build script glob for figure format | Build script used `figures/*.pdf` but all 71 figures were PNG | LaTeX compiled fine (finds files regardless of packaging), but tarball contained ZERO figures | Always verify build/packaging script globs against actual file extensions in the directory |

## Results & Parameters

### Input Parameters

- **Source file**: `docs/paper.tex` (LaTeX academic paper)
- **Source data**: raw experimental data (CSV/JSON result files)
- **Tool**: Edit tool for precise string replacement
- **Sample size**: N=1 (key constraint requiring hedged language)

### LaTeX Compilation

```bash
# Preferred: tectonic via pixi (v2.0.0+)
pixi run --environment docs paper-build

# Legacy: pdflatex
cd docs/
pdflatex -interaction=nonstopmode paper.tex  # Pass 1
pdflatex -interaction=nonstopmode paper.tex  # Pass 2 (cross-refs)
```

### ArXiv Build

```bash
# Automated build with verification:
bash <project-root>/scripts/build_arxiv_submission.sh

# Output:
# main.tex generated (34 pages, 663 KB PDF)
# submission.tar.gz created (4.77 MB)
# All 24 figures copied
# All 10 tables copied with underscore escaping
```

### Pre-commit Double-Stage Pattern

```bash
git add <files>
git commit -m "..."
# If end-of-file-fixer fires:
git add <json-files>   # re-stage the fixed files
git commit -m "..."    # commit again
```

### Data Validation Results

| Issue | Paper Claim | Actual Data | Fixed To |
|-------|-------------|-------------|----------|
| Fig 14 correlation | ">0.85" | 0.333/-0.273/-0.522 (Spearman) | "Low-to-moderate correlations, Opus-Sonnet highest (r=0.706)" |
| Functional scores | "0.95-1.00" | All exactly 1.00 | "Perfect functional scores (1.00)" |
| Cache read % | "80-99%" | 79.3-83.1% | "~79-83%" |
| Agent time | "25-41 seconds" | 24.8-41.2s | "24.8-41.2 seconds" |

### Statistical Methodology Fixes

| Severity | Issue | Paper Claim | Actual Data | Fix Applied |
|----------|-------|-------------|-------------|-------------|
| Critical | Token column semantics | No label | Tier rows = per-run means, Total row = absolute totals | Added footnote to tab05_cost_analysis.tex |
| Important | Statistical test name | "Dunn's test" | `u_statistic` field in JSON = Mann-Whitney U | Changed to "Mann-Whitney U test" in 4 locations |
| Important | Comparison count | "21 pairwise comparisons C(7,2)" | 7 comparisons in statistical_results.json | Changed to "7 planned comparisons (6 adjacent + T0-T6)" |
| Important | SRH framing | "SRH two-way test confirms tier effect" | Single model → SRH degenerates to KW equivalent | Added explicit disclosure of degeneration |
| Important | Cliff's delta citation | 0.147/0.33/0.474 thresholds cited | Code uses FAIR 0.11/0.28/0.43 thresholds | Updated citation to FAIR conference paper; noted both conventions |

### Power Analysis Reference Values (Haiku paper example)

| Transition | N1, N2 | Observed δ | Power@observed | Power@medium(0.3) |
|------------|--------|------------|----------------|-------------------|
| T0→T1 | 117, 83 | 0.094 | 0.20 | 0.95 |
| T1→T2 | 83, 130 | 0.096 | 0.22 | 0.96 |
| T2→T3 | 130, 122 | -0.068 | 0.16 | 0.98 |
| T3→T4 | 122, 123 | 0.051 | 0.10 | 0.98 |
| T4→T5 | 123, 30 | -0.313 | 0.77 | 0.73 |
| T5→T6 | 30, 15 | +0.433 | 0.68 | 0.37 (underpowered) |

Key insight: T0–T4 null results reflect genuinely small effects (power 0.95–0.98 at medium), not insufficient power.

### Output Metrics (v1.0.0 / v2.0.0)

- **v1.0.0 (tone/formalization pass)**: 47+ contractions removed, 24 colloquial segments tagged, 6 spelling errors fixed, 4 grammar errors fixed, broken paths extracted from archives, script paths corrected
- **v2.0.0 (data validation pass)**: 2 data errors fixed, 2 typos fixed, 12+ statistical language improvements, 11 section labels + 9 reference conversions added, 3 degenerate figures removed
- **Final PDF**: 32 pages, 5.3 MB, 0 errors, 0 unresolved references
- **Net change**: 73 insertions, 91 deletions (-18 lines, improved quality)

### Key Takeaways

1. **Data validation is non-negotiable**: Read source CSVs/JSONs before accepting any quantitative claim
2. **Fix pipeline first**: When claims come from a pipeline, fix the pipeline and regenerate — never patch numbers manually
3. **Verify statistical test names against data fields**: JSON field names (e.g., `u_statistic`) are ground truth
4. **Count actual comparisons in the data**: Do not assume C(k,2) — check the data file for the real count
5. **Explicit family size in multiple correction**: State Holm-Bonferroni family size $m$ explicitly in table captions
6. **Cliff's delta convention**: Two Romano 2006 papers exist with different thresholds — verify which the codebase uses
7. **SRH degeneracy disclosure**: Single-model designs collapse SRH to KW — paper must acknowledge this
8. **Cross-section regression**: After fixing language in one section, grep ALL other sections for the same phrasing
9. **Verify the reviewer too**: Review prompts and checklists may contain incorrect reference values
10. **Verify automated findings independently**: Agent-reported issues may be false positives
11. **Check table column semantics**: Mixed conventions (means vs totals) need explicit footnotes
12. **Unicode to LaTeX math**: Always convert Greek letters to `$\rho$`, `$\Delta$`, etc.
13. **Path transformations**: Cover ALL path prefix variations (`docs/paper-dryrun/` AND `paper-dryrun/`)
14. **Remove zero-information content**: Figures/tables that show no variance dilute the message
15. **Causal language in observational studies**: Use "is associated with" not "causes" when design is non-randomized
16. **Verify build script format globs**: Check packaging script extension patterns match actual figure files

## Related Skills

- `academic-paper-myrmidon-swarm-review` - Parallel multi-agent review with Opus/Sonnet/Haiku roles for thorough coverage
- `latex-compilation` - Compiling LaTeX documents with proper error checking
- `statistical-rigor` - Applying appropriate statistical language for sample sizes
- `code-review` - Systematic review patterns applicable to paper review

## References

- LaTeX compilation errors: https://www.overleaf.com/learn/latex/Errors
- ArXiv submission guide: https://arxiv.org/help/submit_tex
- Romano, J., et al. (2006). Appropriate statistics for ordinal level data. (FAIR conference — thresholds 0.11/0.28/0.43)
- Romano, J., et al. (2006). Journal article — thresholds 0.147/0.33/0.474 (different publication)
