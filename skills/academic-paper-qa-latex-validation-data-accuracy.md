---
name: academic-paper-qa-latex-validation-data-accuracy
description: Validate and fix data accuracy issues, structural problems, statistical methodology errors, and LaTeX compilation errors in academic papers
category: documentation
date: 2026-02-06
version: 1.1.0
user-invocable: false
---
# Academic Paper QA: LaTeX Validation & Data Accuracy

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-06 (v1.0.0), 2026-04-06 (v1.1.0) |
| **Objective** | Fix data accuracy issues, verify statistical methodology claims, improve structure, and validate quantitative claims in academic LaTeX papers |
| **Outcome** | v1.0.0: Validated and corrected 8 critical data errors, removed 5 low-information figures, consolidated redundant sections, achieved clean compilation with automated arXiv build. v1.1.0: Verified 60+ quantitative claims, caught statistical method naming error (Dunn's vs Mann-Whitney U), caught incorrect pairwise comparison count (21 vs 7) |
| **Category** | Documentation |
| **Models Used** | Sonnet 4.5 (v1.0.0), Opus 4.6 (v1.1.0) |
| **Tools** | pdflatex, tectonic (via pixi), LaTeX, Python build scripts, grep, sed |

## When to Use This Skill

Use this skill when:

1. **Preparing academic papers for submission** with quantitative results that need validation
2. **Reviewing papers** where claims don't match source data (e.g., "scores 0.95-1.00" but actual data shows all 1.00)
3. **Verifying statistical methodology claims** -- checking that named tests (e.g., "Dunn's test") match what the code/data actually computed (e.g., Mann-Whitney U)
4. **Verifying multiple comparison corrections** -- checking that the number of claimed pairwise comparisons matches the actual comparisons conducted
5. **Fixing LaTeX compilation errors** related to Unicode characters, table formatting, or path issues
6. **Building arXiv submission packages** from source LaTeX with automated transformations
7. **Converting Markdown content** to proper LaTeX format in academic papers
8. **Consolidating redundant sections** (Abstract/Summary/Introduction overlap)
9. **Debugging failed LaTeX builds** with cryptic `\hline` or `\noalign` errors
10. **Checking table column semantics** -- verifying whether columns show means vs totals and that conventions are labeled

**Red flags that indicate you need this skill**:
- Paper contains phrases like "approximately", "~", or broad ranges where precise values exist
- Figures show "no variance" or "all zeros" but are still included
- Same content appears in multiple sections (Abstract + Summary + Introduction)
- Build script warnings about missing sections or alignment issues
- Unicode characters (rho, Delta, alpha, mu, sigma) in LaTeX source instead of math mode
- Table compilation errors with column count mismatches
- Paper names a statistical test but the JSON/CSV data contains field names suggesting a different test
- Paper claims C(k,2) pairwise comparisons but the data file has fewer actual comparisons

## Verified Workflow

### Phase 1: Data Validation (Read Source Data First)

**CRITICAL**: Always validate quantitative claims against source data files before accepting paper claims.

```bash
# 1. Read the paper to identify quantitative claims
# Look for: percentages, ranges, correlations, scores, statistics

# 2. Locate source data files
find . -name "*.csv" -o -name "*.json" -o -name "result.json"

# 3. Cross-reference each claim
# Example: Paper says "scores 0.95-1.00" -> Check actual CSV values
# Example: Paper says "correlations >0.85" -> Verify Pearson/Spearman values
```

**Common Data Accuracy Issues Found**:
- Broad ranges used when all values are identical (e.g., "0.95-1.00" when all are 1.00)
- Rounding that obscures precision (e.g., "25-41 seconds" when actual is 24.8-41.2s)
- Percentage claims that don't match actual data (e.g., "80-99%" when actual is 79.3-83.1%)
- Correlation strength claims that contradict values (e.g., ">0.85" when actual is 0.333/-0.273/-0.522)

### Phase 2: Statistical Methodology Verification (v1.1.0)

**CRITICAL**: Verify that named statistical tests match the actual computation. Do not trust test names in the paper -- check the data.

```bash
# 1. Identify what statistical test the paper claims
# Example: "Dunn's post-hoc test with Bonferroni correction"

# 2. Find the statistical results data file
find . -name "statistical_results.json" -o -name "srh_tier_experiment.json"

# 3. Check field names in the JSON for the actual test used
# Example: If the JSON contains "u_statistic" -> Mann-Whitney U test, NOT Dunn's test
# Example: If the JSON contains "H_statistic" -> Kruskal-Wallis H test
# Example: If the JSON contains "dunn_statistic" -> Dunn's test
python3 -c "import json; data=json.load(open('statistical_results.json')); print([k for k in data[0].keys() if 'stat' in k.lower()])"

# 4. Count actual pairwise comparisons vs claimed
# Paper may claim C(k,2) = C(7,2) = 21 comparisons
# But the actual data may only contain 7 (e.g., 6 adjacent transitions + 1 endpoint)
python3 -c "import json; data=json.load(open('statistical_results.json')); print(f'Actual comparisons: {len(data)}')"
```

**Key principle**: The JSON field names are ground truth for which test was used. A field named `u_statistic` means Mann-Whitney U was computed, regardless of what the paper's prose says.

### Phase 3: Table Semantics Verification (v1.1.0)

**Check column aggregation conventions**:

Tables that mix per-row means with a "Total" row showing absolute sums create ambiguity. Always verify:

```bash
# 1. Check if numeric columns show means or totals
# If tier rows show per-run averages but Total row shows absolute sums, add a footnote

# 2. Example fix (LaTeX table footnote):
# \footnote{Token columns show per-run means for tier rows; the Total row shows absolute totals.}
```

### Phase 4: Structural Cleanup

**Remove Low-Information Content**:

```bash
# Identify figures/tables that show:
# - All zeros (failure rates when pass rate = 100%)
# - All ones (pass rates at ceiling)
# - Flat lines (tier uplift when all tiers perform equally)
# - Negligible effect sizes (with N=1 dryrun)

# Example removal with explanation:
# Remove Fig 3 (failure_rate) - all zeros in N=1 dryrun
# Remove Fig 4 (pass_rate) - all 1.0, no discrimination
# Add note: "Additional diagnostic figures available in repository but show no variance"
```

**Consolidate Redundant Sections**:

Pattern: Abstract + Summary + Introduction often overlap heavily in papers.

Fix:
1. Identify unique content in Summary not in Abstract
2. Merge unique content into Introduction
3. Remove Summary section entirely
4. Result: Abstract (high-level) -> Introduction (detailed context)

### Phase 5: LaTeX Compilation Fixes

**Fix Unicode Characters**:

```latex
% WRONG (will fail compilation):
Spearman rho = 0.333, mean Delta = 0.033, Krippendorff's alpha = -0.117

% CORRECT (use LaTeX math):
Spearman $\rho$ = 0.333, mean $\Delta$ = 0.033, Krippendorff's $\alpha$ = -0.117
```

**Fix Table Column Mismatches**:

```latex
% ERROR: 5 columns declared |l|l|l|l|l| but only 4 in header
\begin{tabular}{|l|l|l|l|l|}  % <-- 5 columns
\hline
Tier & Agent Time & Judge Time & Total Time & Judge % \\  % <-- only 4!
\hline

% FIX: Match column count (use right-align for numbers)
\begin{tabular}{|l|r|r|r|r|}  % <-- 5 columns, right-align numbers
\hline
Tier & Agent Time (s) & Judge Time (s) & Total Time (s) & Judge \% of Total \\
\hline
```

**Escape Underscores in Auto-Generated Tables**:

```latex
% Auto-generated tables often have unescaped underscores:
code_quality & 0.20 & 1.000 $\pm$ 0.000 \\  % <-- FAILS

% Fix with backslash escaping:
code\_quality & 0.20 & 1.000 $\pm$ 0.000 \\  % <-- WORKS
```

### Phase 6: Path Transformations for ArXiv Builds

**Problem**: Source uses `docs/paper-dryrun/figures/` but arXiv build needs `figures/`

**Solution**: Add path transformations to build script:

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

### Phase 7: Build Verification

**Compile with tectonic via pixi** (preferred for Haiku paper builds):

```bash
pixi run --environment docs paper-build
```

**Or with pdflatex** (legacy):

```bash
cd docs/
pdflatex -interaction=nonstopmode paper.tex  # Pass 1
pdflatex -interaction=nonstopmode paper.tex  # Pass 2 (cross-refs)
```

### Phase 8: Establish Single Source of Truth

**Problem**: Build scripts check alignment between `paper.md` and `paper.tex`, causing false warnings when paper.tex becomes authoritative.

**Solution**: Update verification to skip outdated checks:

```python
# In verify_paper_alignment.py:
if __name__ == "__main__":
    # paper.tex is now the single source of truth
    # Skip alignment verification with paper.md
    print("Note: paper.tex is the source of truth (paper.md is deprecated)")
    print("Verification skipped - paper.tex is canonical")
    sys.exit(0)
```

## Failed Attempts & Lessons Learned
| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Trust paper claims without verification | 8+ data accuracy errors found | ALWAYS validate against source data |
| 2 | Compile LaTeX before fixing Unicode | Unicode char errors (rho, alpha) | Search for Unicode first, replace with math mode |
| 3 | Assume auto-generated tables are LaTeX-safe | Unescaped underscores caused errors | Always escape underscores in CSV-to-LaTeX |
| 4 | Incomplete path transformation | Missed bare `paper-dryrun/` prefix | Search for ALL path prefix variations |
| 5 | Keep all generated figures | Zero-information figures dilute message | Remove figures showing no variance |
| 6 | Trust automated contraction detection | Agent flagged "5 contractions" that did not exist | Always verify automated findings with regex |
| 7 | Accept reviewer's reference thresholds | Review prompt cited wrong Cliff's delta thresholds (0.11/0.28/0.43 vs correct Romano 0.147/0.33/0.474) | Verify the reviewer's assumptions too, not just the paper |
| 8 | Assume C(k,2) comparisons from k groups | Paper claimed 21=C(7,2) but only 7 comparisons were conducted | Count actual comparisons in the data file |


### Attempt 1: Trust Paper Claims Without Verification
**What we tried**: Initially accepted paper's quantitative claims as accurate.

**Why it failed**: Paper contained 8+ data accuracy errors:
- Figure 14: Claimed "correlations >0.85" but actual was 0.333/-0.273/-0.522
- Functional scores: Claimed "0.95-1.00" but all were exactly 1.00
- Cache read %: Claimed "80-99%" but actual was 79.3-83.1%

**Lesson**: ALWAYS validate quantitative claims against source data files. Never trust ranges or approximations without checking raw data.

### Attempt 2: Compile LaTeX Before Fixing Unicode
**What we tried**: Attempted to compile paper.tex with Unicode characters directly in source.

**Error**:
```
! LaTeX Error: Unicode character (U+03C1) not set up for use with LaTeX.
! LaTeX Error: Unicode character (U+03B1) not set up for use with LaTeX.
```

**Why it failed**: Standard LaTeX requires math mode for Greek letters.

**Lesson**: Search for Unicode characters and replace with LaTeX equivalents `$\rho$`, `$\Delta$`, `$\alpha$` BEFORE first compilation attempt.

### Attempt 3: Assume Auto-Generated Tables Are LaTeX-Safe
**What we tried**: Used table files generated from CSV with underscores in criterion names.

**Error**:
```
! Missing $ inserted.
<inserted text>
                $
l.10 code_quality & 0.20 & 1.000 $\pm$ 0.000 & --- & --- \\
```

**Why it failed**: Underscores are special characters in LaTeX (subscript in math mode) and must be escaped.

**Lesson**: Run `scripts/fix_table_underscores.py` on all auto-generated tables, or add escaping to the generation script. Never assume CSV-to-LaTeX conversion is LaTeX-safe.

### Attempt 4: Incomplete Path Transformation
**What we tried**: Added transformation for `docs/paper-dryrun/` but missed bare `paper-dryrun/` prefix.

**Error**:
```
! LaTeX Error: File `paper-dryrun/tables/tab04_criteria_performance.tex' not found.
```

**Why it failed**: Path transformation only caught `docs/paper-dryrun/` pattern, but manual `\input{paper-dryrun/tables/...}` used shorter form.

**Lesson**: When adding path transformations, search for ALL possible path prefixes:
```bash
grep -r "paper-dryrun" docs/paper.tex  # Find all patterns
# Then add regex for each: r"paper-dryrun/tables/" AND r"docs/paper-dryrun/tables/"
```

### Attempt 5: Keep All Generated Figures
**What we tried**: Included all 26 generated figures in appendix, even those showing no variance.

**Why it failed**: With N=1 dryrun:
- Fig 3 (failure_rate): All zeros (100% pass rate)
- Fig 4 (pass_rate): All 1.0 (ceiling effect)
- Fig 11 (tier_uplift): Flat lines (no improvement)
- Fig 18, 19: No discriminatory power

**Lesson**: Review each figure for information content. If figure shows "no variance" or "insufficient N", remove it and add explanatory note: "Additional diagnostic figures available in repository but show no variance in this N=1 dryrun."

### Attempt 6: Trust Automated Contraction Detection (v1.1.0)
**What we tried**: An exploration agent reported "5 contractions found at lines 112, 117, 133, 271, 400" during an academic paper review.

**Why it failed**: Regex verification (`grep -nP "\\b(don't|won't|can't|isn't|aren't|doesn't|wouldn't|shouldn't|couldn't|it's|we're|they're|we've|we'll|that's|there's|here's|let's|wasn't|weren't|hadn't|hasn't|haven't)\\b" paper.tex`) showed zero contractions exist in the file. The automated finding was a false positive.

**Lesson**: ALWAYS verify automated findings independently. When an agent or tool reports issues, run your own verification (e.g., targeted regex search) before acting on those findings. False positives from automated scanners waste review time and can introduce unnecessary edits.

### Attempt 7: Accept Reviewer's Reference Thresholds (v1.1.0)
**What we tried**: The review prompt asked to check whether the paper's Cliff's delta thresholds matched "FAIR: 0.11/0.28/0.43" (Vargha and Delaney's thresholds).

**Why it failed**: The paper correctly uses Romano (2006) thresholds of 0.147/0.33/0.474, which are a different but equally valid standard. The review prompt itself contained incorrect expectations.

**Lesson**: When reviewing a paper against a checklist or review prompt, verify the reviewer's reference values too. The reviewer may be citing a different standard or have incorrect expectations. Check the paper's cited source (e.g., "Romano et al., 2006") directly rather than assuming the review prompt's values are correct.

### Attempt 8: Assume C(k,2) Pairwise Comparisons (v1.1.0)
**What we tried**: Paper claimed "21 pairwise comparisons (C(7,2))" with Bonferroni correction, implying all possible pairs of 7 tiers were compared.

**Why it failed**: The statistical results JSON file contained only 7 comparisons (6 adjacent tier transitions T0-T1, T1-T2, ..., T5-T6, plus T0-T6 endpoint comparison). The Bonferroni correction was applied to 7 comparisons, not 21.

**Lesson**: Never assume the number of pairwise comparisons from C(k,2). Always check the actual data file to count how many comparisons were conducted:
```bash
python3 -c "import json; data=json.load(open('statistical_results.json')); print(f'Comparisons: {len(data)}')"
```
The difference matters for multiple comparison corrections -- Bonferroni with m=7 yields alpha=0.00714 vs m=21 yields alpha=0.00238.

## Results & Parameters

### LaTeX Compilation
```bash
# Preferred: tectonic via pixi (v1.1.0)
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

### Data Validation Results (v1.0.0)
| Issue | Paper Claim | Actual Data | Fixed To |
|-------|-------------|-------------|----------|
| Fig 14 correlation | ">0.85" | 0.333/-0.273/-0.522 (Spearman), 0.706/-0.063/-0.347 (Pearson) | "Low-to-moderate correlations, Opus-Sonnet highest (r=0.706)" |
| Functional scores | "0.95-1.00" | All exactly 1.00 | "Perfect functional scores (1.00)" |
| Build pipeline | "0.90-1.00" | All exactly 1.00 | "All tiers score 1.00" |
| Cache read % | "80-99%" | 79.3-83.1% | "~79-83%" |
| Agent time | "25-41 seconds" | 24.8-41.2s | "24.8-41.2 seconds" |

### Statistical Methodology Fixes (v1.1.0)
| Severity | Issue | Paper Claim | Actual Data | Fix Applied |
|----------|-------|-------------|-------------|-------------|
| Critical | Token column semantics | No label | Tier rows = per-run means, Total row = absolute totals | Added footnote to tab05_cost_analysis.tex |
| Important | Statistical test name | "Dunn's test" | `u_statistic` field in JSON = Mann-Whitney U | Changed to "Mann-Whitney U test" in 4 locations |
| Important | Comparison count | "21 pairwise comparisons C(7,2)" | 7 comparisons in statistical_results.json | Changed to "7 planned comparisons (6 adjacent + T0-T6)" |

### Verification Status
- v1.0.0: verified-local (pdflatex clean compilation)
- v1.1.0: verified-local (tectonic via pixi docs environment, all edits produce valid LaTeX, no CI pipeline for paper compilation)

### File Changes Summary (v1.0.0)
```
Modified files:
- docs/paper.tex (source of truth)
- docs/paper-dryrun/tables/tab04_criteria_performance.tex (escaped underscores)
- scripts/build_arxiv_paper.py (enhanced path transformations)
- scripts/verify_paper_alignment.py (skip paper.md check)

Removed sections:
- Section 1: Keywords (converted to unnumbered paragraph)
- Section 2: Summary (merged into Introduction)
- Section 9: Model Summary (merged into Section 7.3)
- Section 10.7: Statistical Limitations (merged into 11.4)

Removed figures:
- Fig 3, 4, 11, 18, 19 (zero-information with N=1)
```

### File Changes Summary (v1.1.0)
```
Modified files:
- docs/arxiv/haiku/paper.tex (statistical test name x4, comparison count)
- docs/arxiv/haiku/tables/tab05_cost_analysis.tex (token column footnote)
```

## Key Takeaways

1. **Data validation is non-negotiable**: Read source CSVs/JSONs before accepting any quantitative claim
2. **Verify statistical test names against data fields**: JSON field names (e.g., `u_statistic`) are ground truth for which test was computed
3. **Count actual comparisons in the data**: Do not assume C(k,2) -- check the data file for the real count
4. **Verify the reviewer too**: Review prompts and checklists may contain incorrect reference values
5. **Verify automated findings independently**: Agent-reported issues (contractions, style violations) may be false positives
6. **Check table column semantics**: Mixed conventions (means vs totals) need explicit footnotes
7. **Unicode to LaTeX math**: Always convert Greek letters to `$\rho$`, `$\Delta$`, etc.
8. **Escape underscores**: Auto-generated tables need `\_` for criterion names like `code_quality`
9. **Table column counts**: Match `\begin{tabular}{|l|r|r|r|}` column spec with header exactly
10. **Path transformations**: Cover ALL path prefix variations (`docs/paper-dryrun/` AND `paper-dryrun/`)
11. **Remove zero-information content**: Figures/tables that show no variance dilute the message
12. **Consolidate redundancy**: Abstract + Summary + Introduction often overlap heavily
13. **Single source of truth**: Pick one (paper.tex or paper.md) and update build scripts accordingly

## References

- LaTeX compilation errors: https://www.overleaf.com/learn/latex/Errors
- Booktabs package for tables: https://ctan.org/pkg/booktabs
- ArXiv submission guide: https://arxiv.org/help/submit_tex
- Data validation best practices: Verify quantitative claims against source data files
- Romano, J., Kromrey, J. D., Coraggio, J., & Skowronek, J. (2006). Appropriate statistics for ordinal level data: Should we really be using t-test and Cohen's d for evaluating group differences on the NSSE and other surveys?
