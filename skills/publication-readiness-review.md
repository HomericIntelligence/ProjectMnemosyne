---
name: publication-readiness-review
description: Comprehensive 10-category GO/NO-GO assessment framework for academic paper publication readiness
category: documentation
date: 2026-02-07
version: 2.0.0
user-invocable: false
---
# Publication Readiness Review

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-07 |
| **Objective** | Establish comprehensive 10-category GO/NO-GO framework for academic paper publication readiness |
| **Context** | "Taming Scylla" arXiv paper after 5+ prior review passes |
| **Outcome** | ✅ GO - Paper ready for publication with 1 minor fix (Docker → Git Worktrees) |
| **Paper** | 32 pages, 1517 lines LaTeX, 10 bibliography entries |

## When to Use This Skill

Use this skill when:
- Preparing an academic paper for arXiv or journal submission
- Conducting final pre-publication review after multiple editing passes
- Need systematic verification across quality, technical accuracy, and formatting dimensions
- Want objective GO/NO-GO decision framework based on critical vs conditional issues
- Reviewing papers with empirical data requiring numerical verification against raw sources

**Trigger patterns:**
- "Review the paper for publication readiness"
- "Is the paper ready for arXiv submission?"
- "Check if all claims match the data"
- "Comprehensive paper quality assessment"
- "GO/NO-GO publication review"

## Verified Workflow

### 1. 10-Category Assessment Framework

Evaluate papers across these categories with GO/NO-GO/CONDITIONAL grades:

| # | Category | What to Check |
| --- | ---------- | --------------- |
| 1 | **Numerical Accuracy** | All numerical claims match raw data sources |
| 2 | **Internal Consistency** | Terminology, methodology descriptions, cross-references |
| 3 | **Clarity & Readability** | Logical flow, jargon explained, technical terms defined |
| 4 | **Grammar & Spelling** | Language quality, typos, style consistency |
| 5 | **LaTeX Formatting** | Clean compilation, resolved references, proper escaping |
| 6 | **Citations & References** | All entries complete, URLs verified, no orphaned citations |
| 7 | **Reproducibility** | Config files exist, data accessible, execution steps clear |
| 8 | **Figures & Tables** | Proper referencing, captions, format consistency |
| 9 | **Scientific Rigor** | Limitations acknowledged, claims hedged, hypotheses stated |
| 10 | **Completeness** | All sections present, appendices complete, acknowledgements |

### 2. Grading System

**Grade Definitions:**
- ✅ **GO** - No blocking issues, ready for publication
- ⚠️ **CONDITIONAL GO** - Minor issues present but non-blocking, should be addressed
- ❌ **NO-GO** - Critical issues that must be resolved before publication

**Overall Decision Tree:**
```
Any NO-GO grade? → Overall: NO-GO
All GO grades? → Overall: GO
Mix of GO + CONDITIONAL? → Overall: CONDITIONAL GO
```

### 3. Numerical Verification Process

For papers with empirical results:

**Step 1: Identify all numerical claims**
```bash
grep -E '[0-9]+\.[0-9]+' paper.tex  # Find all decimal numbers
grep -E '\$[0-9]+\.[0-9]+' paper.tex  # Find all dollar amounts
grep -E '[0-9]+%' paper.tex  # Find all percentages
```

**Step 2: Locate raw data sources**
- Check `data/summary.json` for aggregate metrics
- Check `data/runs.csv` for per-run values
- Check `data/statistical_results.json` for correlations/p-values

**Step 3: Verify each claim**
- Tier scores: Match against summary.json tier_scores
- Cost values: Match against summary.json tier_costs or calculate from runs.csv
- Token counts: Sum from runs.csv input_tokens/output_tokens
- Timing values: Match runs.csv duration_seconds
- Statistical claims: Match statistical_results.json exactly
- Derived metrics: Recalculate (e.g., "3.8x ratio" = $0.247 / $0.065)

**Step 4: Check precision consistency**
- Scores: 3 decimal places (0.973, not 0.97 or 0.9730)
- Costs: 3 decimal places ($0.135, not $0.13 or $0.1350)
- Correlations: 3 decimal places (ρ=0.935, not ρ=0.94)
- Percentages: Integer (78%, not 78.3%)

### 4. Internal Consistency Checks

**Methodology descriptions:**
```bash
# Find all occurrences of key methodology terms
grep -n "sequentially\|parallel\|concurrent" paper.tex
grep -n "mean\|median\|consensus" paper.tex
grep -n "independent\|blind\|sequential" paper.tex
```

**Cross-reference verification:**
```bash
# Extract all \label{} tags
grep -o '\\label{[^}]*}' paper.tex | sort > labels.txt

# Extract all \ref{} tags
grep -o '\\ref{[^}]*}' paper.tex | sort > refs.txt

# Find orphaned references
comm -13 <(sed 's/\\label{//;s/}//' labels.txt | sort) \
         <(sed 's/\\ref{//;s/}//' refs.txt | sort)
```

### 5. LaTeX Build Verification

**Clean build test:**
```bash
cd docs/arxiv/dryrun
./build.sh
```

**Expected output:**
- ✓ Compilation successful
- ✓ Validation passed (page count, file size)
- ✓ Tarball created for arXiv submission
- 0 errors, 0 unresolved references

**Common LaTeX issues to check:**
- `\input{}` files exist in tarball
- All figure PDFs included
- Bibliography file (.bib) included
- No absolute paths in `\includegraphics`

### 6. Citation Completeness Check

**Verify bibliography entries:**
```bash
# Extract all citation keys from paper
grep -o '\\cite{[^}]*}' paper.tex | \
  sed 's/\\cite{//;s/}//' | \
  tr ',' '\n' | sort -u > cited.txt

# Extract all bib entry keys
grep '^@' references.bib | \
  sed 's/@[^{]*{//;s/,//' | sort > bibitems.txt

# Find missing citations (cited but not in .bib)
comm -23 cited.txt bibitems.txt

# Find orphaned entries (in .bib but not cited)
comm -13 cited.txt bibitems.txt
```

**Verify URL accessibility (for arXiv papers):**
- Standardized format: `https://arxiv.org/abs/XXXX.XXXXX`
- No DOI URLs for arXiv papers (use arxiv.org directly)
- All URLs resolve (manual check recommended)

### 7. Scientific Rigor Verification

**Check limitation statements:**
```bash
# Find where N=1 or sample size is mentioned
grep -in "n=1\|sample size\|single.*test" paper.tex

# Find hedging language
grep -in "suggests\|indicates\|consistent with\|preliminary" paper.tex

# Find overstatement risks
grep -in "proves\|demonstrates\|shows that\|confirms" paper.tex
```

**Required elements:**
- N=1 limitation explicitly stated (if applicable)
- Statistical caveats for underpowered analyses
- Ceiling effects acknowledged (if scores > 0.95)
- Single-model limitations mentioned
- Claims appropriately hedged ("suggests" not "proves")

### 8. Reproducibility Checklist

**Verify all referenced files exist:**
```bash
# Extract config file paths from paper
grep -o 'config/[^}]*\.yaml' paper.tex | sort -u > configs_cited.txt

# Check existence
while read path; do
  [ -f "$path" ] || echo "MISSING: $path"
done < configs_cited.txt
```

**Check data availability:**
- Raw data files in repo (runs.csv, judges.csv, etc.)
- Aggregate summaries (summary.json, statistical_results.json)
- Git commit hashes for referenced versions
- Repository URL accessible

### 9. Common Issues Found in This Session

| Issue | Location | Fix |
| ------- | ---------- | ----- |
| Docker listed as container runtime | Software Stack table (line 883) | Changed to "Git Worktrees" (actual isolation mechanism) |
| Prior: Fabricated bibliography URLs | references.bib | Verified all 10 entries against official sources |
| Prior: Parallel/sequential contradiction | Judge execution description | Standardized to "sequentially" throughout |
| Prior: Precision inconsistencies | Numerical claims | Standardized to 3 decimal places for scores/costs |

## Failed Attempts

### ❌ Failed: Trusting Paper Claims Without Verification

**What was tried**: Accepted paper's claim that "judges run in parallel" at face value.

**Why it failed**: Would have shipped with architectural contradiction (3 places say "parallel", 1 says "sequential", source code confirms sequential).

**Lesson**: Always verify architectural claims against source code. Don't trust paper text, especially after multiple revision rounds where copy-paste errors accumulate.

**Fix**: `grep -r "judge_num" scylla/` → found `for judge_num, model in enumerate(...)` → confirmed sequential.

---

### ❌ Failed: Spot-Checking Numerical Claims

**What was tried**: Planned to verify only "suspicious" numbers (outliers, round numbers).

**Why it failed**: Would have missed valid value with wrong precision (T4: 0.9595 instead of 0.960).

**Lesson**: Verify ALL numbers, not just suspicious ones. Precision errors, rounding inconsistencies, and copy-paste mistakes appear in "normal-looking" values.

---

### ❌ Failed: Assuming Bibliography Tools Auto-Validate

**What was tried**: Assumed that if BibTeX compiles, all references are valid.

**Why it failed**: Would have shipped with `polo2024efficient` pointing to arXiv paper about paradise fish instead of LLM evaluation.

**Lesson**: BibTeX only checks syntax, not semantic correctness. A fabricated URL that returns HTTP 200 will compile fine but destroy paper credibility. Manual verification of all URLs required.

---

### ❌ Failed: Fixing Everything in One Pass

**What was tried**: Tried to implement all 10 fixes simultaneously in a single edit.

**Why it failed**: Risk of introducing new errors; hard to verify which fixes applied successfully.

**Lesson**: Fix critical issues first, then polish. Allows early verification that blocking issues are resolved and easier rollback.

---

### ❌ Failed: Trusting "Already Reviewed 4 Times"

**What was tried**: Assumed that after 4+ prior review passes, only minor issues remained.

**Why it failed**: Found 2 publication-blocking critical issues (fabricated URL, architectural contradiction) that survived 4 reviews.

**Lesson**: Review fatigue is real. Use systematic checklists, not intuition. The 10-category framework catches issues that manual reviews miss.
## Results & Parameters

### Session Parameters

**Paper Details:**
- File: `docs/arxiv/dryrun/paper.tex`
- Lines: 1517
- Pages: 32
- Build system: `build.sh` (4-pass LaTeX compilation)
- Bibliography: `references.bib` (10 entries)

**Data Sources:**
- `docs/arxiv/dryrun/data/summary.json` - Aggregate tier metrics
- `docs/arxiv/dryrun/data/runs.csv` - Per-run execution data
- `docs/arxiv/dryrun/data/statistical_results.json` - Correlation analysis
- `docs/arxiv/dryrun/data/judges.csv` - Judge evaluations
- `docs/arxiv/dryrun/data/criteria.csv` - Criteria scores

### Final Grading Summary

| Category | Grade | Issues Found |
| ---------- | ------- | -------------- |
| 1. Numerical Accuracy | ✅ GO | 0 |
| 2. Internal Consistency | ✅ GO | 0 |
| 3. Clarity & Readability | ✅ GO | 0 |
| 4. Grammar & Spelling | ⚠️ CONDITIONAL GO | 1 (Docker reference) |
| 5. LaTeX Formatting | ⚠️ CONDITIONAL GO | 0 (verify build needed) |
| 6. Citations & References | ✅ GO | 0 |
| 7. Reproducibility | ✅ GO | 0 |
| 8. Figures & Tables | ✅ GO | 0 |
| 9. Scientific Rigor | ✅ GO | 0 |
| 10. Completeness | ✅ GO | 0 |
| **Overall** | **⚠️ CONDITIONAL GO** | **1 minor fix** |

### Build Verification Results

```bash
cd docs/arxiv/dryrun && ./build.sh

# Output:
✓ Compilation successful
✓ Validation passed
  - PDF: 505511 bytes, 32 pages
  - Tarball: 406524 bytes, 29 files
```

### Changes Applied

**File: docs/arxiv/dryrun/paper.tex**
- Line 883: `Container Runtime & Docker \\` → `Isolation & Git Worktrees \\`

**Verification:**
```bash
grep -i docker paper.tex  # Returns 0 matches ✓
```

## References & Resources

**Tools used:**
- `grep` - Pattern matching for numerical claims, terminology consistency
- `./build.sh` - LaTeX compilation and arXiv tarball generation
- `git diff` - Verify changes applied correctly
- Manual inspection - Raw data verification against paper claims

**Related skills:**
- `arxiv-paper-polish` - LaTeX formatting and style improvements
- `paper-final-review` - Pre-submission quality checks
- `publication-readiness-check` - Earlier version of this framework

**Documentation:**
- arXiv submission guidelines: https://arxiv.org/help/submit
- LaTeX best practices for academic papers
- IEEE/ACM citation standards

## Recommendations for Future Use

### Before Starting Review

1. **Gather context:**
   - How many prior review passes have occurred?
   - What categories of issues were previously addressed?
   - Are there known problem areas to focus on?

2. **Set up verification environment:**
   - Clone/pull latest paper version
   - Locate all data sources (CSV, JSON, raw data files)
   - Test build script works: `./build.sh`
   - Have calculator/spreadsheet ready for numerical verification

3. **Define acceptance criteria:**
   - What constitutes NO-GO vs CONDITIONAL GO vs GO?
   - What is publication deadline (affects acceptable risk tolerance)?
   - Is this a preprint (more tolerant) or journal submission (stricter)?

### During Review

1. **Work category-by-category sequentially:**
   - Don't jump between categories
   - Complete all checks for one category before moving to next
   - Document issues immediately when found

2. **Verify from first principles:**
   - Don't trust prior reviews completely
   - Recalculate derived metrics yourself
   - Check raw data sources directly

3. **Use structured checklists:**
   - Check off items as you verify them
   - Note line numbers for all issues found
   - Capture exact before/after text for fixes

### After Review

1. **Prioritize fixes:**
   - NO-GO issues first (blocking)
   - CONDITIONAL GO issues second (non-blocking but important)
   - Document any issues deferred for future work

2. **Verify fixes:**
   - Re-run build after applying changes
   - Check no new issues introduced by fixes
   - Grep to confirm old issues removed

3. **Update paper version control:**
   - Create PR with clear fix descriptions
   - Link to review findings in PR description
   - Request final visual review of PDF output

## Team Knowledge Sharing

**When to use this vs other paper review skills:**

| Skill | Use When |
| ------- | ---------- |
| `publication-readiness-review` | Final GO/NO-GO decision before arXiv submission |
| `arxiv-paper-polish` | Formatting and LaTeX style improvements |
| `paper-final-review` | Content review focusing on narrative and clarity |
| `numerical-verification` | Deep dive on data accuracy only |

**Estimated effort:**
- Initial review setup: 15 minutes
- Category-by-category review: 2-3 hours for 32-page paper
- Applying fixes: 30 minutes - 2 hours depending on issues found
- Build verification: 5 minutes

**Success metrics:**
- Clean LaTeX build (0 errors, 0 unresolved references)
- All numerical claims verified against raw data
- No NO-GO issues remaining
- Clear documentation of any CONDITIONAL GO issues for user decision
