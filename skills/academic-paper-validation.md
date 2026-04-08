---
name: academic-paper-validation
description: Systematic workflow for validating and improving academic paper quality through data accuracy checks, statistical methodology verification, LaTeX compilation fixes, and arXiv build preparation
category: documentation
date: 2026-04-07
version: 2.0.0
user-invocable: false
---
# Academic Paper Validation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-06 (v1.0.0), 2026-04-06 (v2.0.0) |
| **Objective** | Validate and improve academic paper quality through systematic data accuracy checks, statistical rigor improvements, LaTeX fixes, and noise reduction |
| **Outcome** | v1.0.0: Fixed 2 data errors, 2 typos, 12+ statistical claims, 11 cross-references, removed 3 degenerate figures. v2.0.0: Verified 60+ quantitative claims, caught statistical method naming error (Dunn's vs Mann-Whitney U), caught incorrect pairwise comparison count (21 vs 7), fixed Unicode/table/path issues, built arXiv submission |
| **Models Used** | Sonnet 4.5 (v1.0.0), Opus 4.6 (v2.0.0) |

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

**Trigger phrases**: "validate the paper", "check paper accuracy", "review paper for errors", "improve paper quality", "prepare paper for submission"

**Red flags that indicate you need this skill**:
- Paper contains phrases like "approximately", "~", or broad ranges where precise values exist
- Figures show "no variance" or "all zeros" but are still included
- Same content appears in multiple sections (Abstract + Summary + Introduction)
- Unicode characters (rho, Delta, alpha, mu, sigma) in LaTeX source instead of math mode
- Table compilation errors with column count mismatches
- Paper names a statistical test but the JSON/CSV data contains field names suggesting a different test
- Paper claims C(k,2) pairwise comparisons but the data file has fewer actual comparisons

## Verified Workflow

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

**Steps**:
1. Search for strong causal language:
   ```bash
   grep -n "confirms\|proves\|demonstrates\|validates" paper.tex
   ```
2. For each instance, assess context — hedge results, not methodology
3. Verify paper still acknowledges N=1 limitations in dedicated section

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

### Phase 6: LaTeX Compilation Fixes

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

### Phase 7: Redundancy Reduction (MEDIUM Priority)

**Strategy**:
1. Identify repeated numeric claims (e.g., "3.8x" mentioned 6 times)
2. Keep claims in 3 key locations: Abstract/Introduction, Results section, Conclusions
3. For middle sections, replace with back-references

**Consolidate Redundant Sections** — Abstract + Summary + Introduction often overlap:
1. Identify unique content in Summary not in Abstract
2. Merge unique content into Introduction
3. Remove Summary section entirely

### Phase 8: Low-Value Content Removal (LOWER Priority)

For N=1 experiments, identify degenerate content (zero variance):
- Box plots with no variance (all values identical)
- Bootstrap confidence intervals that collapse to points
- Histograms with single bins

**Steps**:
1. Review all figures in appendix
2. For each, ask: "Does this show meaningful variance or provide insight?"
3. Remove degenerate figures by deleting entire `\begin{figure}...\end{figure}` blocks

### Phase 9: Path Transformations for ArXiv Builds

**Problem**: Source uses `docs/paper-dryrun/figures/` but arXiv build needs `figures/`

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

### Phase 10: Establish Single Source of Truth

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
grep -n "confirms\|proves\|demonstrates" docs/paper.tex
grep -n "Section~\\ref{" paper.tex | head

# Verify PDF
ls -lh paper.pdf  # Should exist and be reasonable size
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

## Results & Parameters

### Input Parameters

- **Source file**: `docs/paper.tex` (LaTeX academic paper)
- **Source data**: raw experimental data (CSV/JSON result files)
- **Tool**: Edit tool for precise string replacement
- **Sample size**: N=1 (key constraint requiring hedged language)

### LaTeX Compilation

```bash
# Preferred: tectonic via pixi (v2.0.0)
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

### Output Metrics (v1.0.0)

- **Data errors fixed**: 2
- **Typos fixed**: 2
- **Statistical language improvements**: 12+ instances
- **Cross-references added**: 11 section labels + 9 reference conversions
- **Figures removed**: 3 degenerate figures
- **Final PDF**: 32 pages, 5.3 MB, 0 errors, 0 unresolved references
- **Net change**: 73 insertions, 91 deletions (-18 lines, improved quality)

### Key Takeaways

1. **Data validation is non-negotiable**: Read source CSVs/JSONs before accepting any quantitative claim
2. **Verify statistical test names against data fields**: JSON field names (e.g., `u_statistic`) are ground truth
3. **Count actual comparisons in the data**: Do not assume C(k,2) — check the data file for the real count
4. **Verify the reviewer too**: Review prompts and checklists may contain incorrect reference values
5. **Verify automated findings independently**: Agent-reported issues may be false positives
6. **Check table column semantics**: Mixed conventions (means vs totals) need explicit footnotes
7. **Unicode to LaTeX math**: Always convert Greek letters to `$\rho$`, `$\Delta$`, etc.
8. **Path transformations**: Cover ALL path prefix variations (`docs/paper-dryrun/` AND `paper-dryrun/`)
9. **Remove zero-information content**: Figures/tables that show no variance dilute the message

## Related Skills

- `latex-compilation` - Compiling LaTeX documents with proper error checking
- `statistical-rigor` - Applying appropriate statistical language for sample sizes
- `code-review` - Systematic review patterns applicable to paper review

## References

- LaTeX compilation errors: https://www.overleaf.com/learn/latex/Errors
- ArXiv submission guide: https://arxiv.org/help/submit_tex
- Romano, J., et al. (2006). Appropriate statistics for ordinal level data.
