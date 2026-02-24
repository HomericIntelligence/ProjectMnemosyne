---
name: "Paper Final Review - Publication Readiness Workflow"
description: "Paper Final Review - Publication Readiness Workflow"
category: documentation
user-invocable: false
---
# Paper Final Review - Publication Readiness Workflow

## Overview

| Attribute | Value |
|-----------|-------|
| Date | 2026-02-07 |
| Objective | Validate academic paper against experimental data across 10 categories for publication readiness |
| Outcome | ✅ Success - Paper ready for publication after 5 minor fixes |
| Context | Final comprehensive review after multiple validation sessions (50+ prior fixes applied) |
| Paper | "Taming Scylla" - AI agent evaluation framework with N=1 dryrun results |

## When to Use This Skill

Use this workflow when:

1. **Final publication check** - Paper has been through multiple reviews and needs final GO/NO-GO assessment
2. **Post-validation cleanup** - Previous automated/manual validation passes completed, need human-level polish
3. **Reproducibility verification** - Need to verify paths, commands, and instructions match actual repository structure
4. **Multi-category assessment** - Need comprehensive review across numerical accuracy, clarity, grammar, formatting, citations, reproducibility, figures, scientific rigor, and completeness
5. **N=1 or pilot studies** - Papers with limited sample size requiring careful claim scoping

**Do NOT use for:**
- Initial drafts (use simpler validation workflows first)
- Major structural rewrites (this is for polish, not reorganization)
- Papers without experimental data to verify against

## Verified Workflow

### Phase 1: Establish Ground Truth

1. **Identify raw data location** - Locate experimental output directory
   ```bash
   # Example: ~/fullruns/test001-dryrun/
   # Contains: result.json, per-tier data, judge scores, timing logs
   ```

2. **Extract all numerical claims from paper** - Use structured extraction:
   - Tier scores (T0-T6)
   - Cost metrics (CoP values)
   - Token counts (input/output/cache by tier)
   - Timing values (latency, wall-clock, duration)
   - Statistical values (correlations, alpha scores, ratios)
   - Percentages and ranges

3. **Cross-reference every number** - Verify against ground truth:
   - Use exact file paths from data directory
   - Document calculation method for derived values (ratios, percentages)
   - Accept minor rounding differences (3 decimal places in text vs 2 in tables)

### Phase 2: Category-by-Category Review

Use this 10-category rubric with GO/CONDITIONAL GO/NO-GO grading:

| # | Category | What to Check |
|---|----------|---------------|
| 1 | Numerical Accuracy | All numbers match data sources within rounding tolerance |
| 2 | Internal Consistency | Terminology consistent, sections cross-reference correctly, methodology matches implementation |
| 3 | Clarity & Readability | Logical flow, jargon explained, abstractions introduced before use |
| 4 | Grammar & Spelling | Verb agreement, missing words, typos |
| 5 | LaTeX Formatting | Compiles cleanly, figures resolve, math renders, cross-refs work |
| 6 | Citations & References | BibTeX entries complete, all citations resolve, no missing author/key fields |
| 7 | Reproducibility | Paths match repository structure, commands are copy-pasteable, software versions specified |
| 8 | Figures & Tables | All render correctly, captions descriptive, referenced in text |
| 9 | Scientific Rigor | Claims scoped to data, limitations acknowledged, uncertainty quantified |
| 10 | Completeness | All major sections present, no TODOs or placeholders |

### Phase 3: Document Issues with Precision

For each issue found:

```markdown
**Issue Category: [Category Name]**

**Location**: Line XXX or section reference
**Severity**: NO-GO (blocks publication) / CONDITIONAL GO (polish) / MINOR (optional)
**Current**: [exact text from paper]
**Should be**: [corrected text]
**Justification**: [why this matters, reference to data if applicable]
```

### Phase 4: Implement Fixes

**Critical Pattern**: Fix all issues in a single commit/PR

1. Read relevant sections to verify current state
2. Apply all fixes using Edit tool (preserves line numbers better than Write)
3. For BibTeX: Read first, then Edit (Write tool requires prior Read)
4. Compile paper to verify: `cd docs && pdflatex -interaction=nonstopmode paper.tex && bibtex paper && pdflatex ... && pdflatex ...`
5. Verify fixes: `grep -n "pattern1\|pattern2\|pattern3" paper.tex` should return 0 matches
6. Check PDF: page count unchanged, file size reasonable

### Phase 5: Create Implementation Plan

Structure the plan document with:

```markdown
## Overall Assessment
- Grade: GO / CONDITIONAL GO / NO-GO
- Critical issues: [count]
- Minor issues: [count]
- Estimated fix time: [realistic estimate]

## Review Categories
[For each category: Grade, Justification, Issues Found, Verification Results]

## Implementation Plan (Fixes)
- Files to Modify: [list]
- Fix 1: [description with old/new text]
- Fix 2: [description with old/new text]
- ...
- Verification Steps: [checklist]

## Checklist for Publication Readiness
- [ ] All NO-GO issues resolved
- [ ] All CONDITIONAL GO issues addressed
- [ ] Final compilation successful
- [ ] PDF reviewed
- [ ] Co-authors acknowledged
- [ ] Repository links functional
```

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Don't assume file paths are correct without verification

**What happened**: Paper listed model config paths as `claude-opus-4.5.yaml` (dots) but actual files use `claude-opus-4-5.yaml` (dashes). Also test path was `tests/001-hello-world` instead of `tests/fixtures/tests/test-001`.

**Why it failed**: Copy-paste from outdated notes, didn't verify against actual directory structure.

**Solution**: Always verify reproducibility paths with actual repository:
```bash
ls -la config/models/  # Check actual filenames
ls -la tests/fixtures/tests/  # Verify test structure
```

### ❌ Don't use Write tool for BibTeX without reading first

**What happened**: First attempt to edit `references.bib` failed with "File has not been read yet" error.

**Why it failed**: Edit tool requires prior Read to establish baseline.

**Solution**: Always Read → Edit pattern for bibliography files.

### ⚠️ Be careful with precision inconsistencies

**What happened**: Table showed CoP as $0.07/$0.25 (2 decimals) but text said $0.065/$0.247 (3 decimals). Both were technically correct but inconsistent.

**Why it matters**: Readers may question data quality if precision varies across document.

**Solution**: Document as "not blocking but inconsistent" - let author decide if they want to unify precision.

### ✅ Use grep verification after all fixes

**What worked**: After applying all edits, ran:
```bash
grep -n "Section 10\|15+\|agreement improve" docs/paper.tex
```
Zero matches confirmed all issues resolved. This catches any missed occurrences or typos in fix application.

## Results & Parameters

### Session Context

- **Previous validation sessions**: 4+ prior passes (paper-validation-workflow, academic-paper-validation, academic-paper-review, academic-paper-qa)
- **Prior fixes applied**: 50+ numerical corrections, median→mean methodology change, grammar/typos, LaTeX formatting
- **This session**: Final comprehensive 10-category review

### Issues Found (5 minor, 0 critical)

1. **Grammar** (line 1130): "agreement improve" → "agreement should improve"
2. **LaTeX cross-reference** (lines 820, 1210): Hardcoded "Section 10" → `\ref{sec:further}`
3. **Clarity** (line 422): Ambiguous "15+" → exact "15"
4. **BibTeX** (references.bib): Missing author field → `author={Anand Tyagi}`
5. **Reproducibility paths** (lines 1302-1304, 1331): Incorrect file paths → corrected to match repository structure

### Compilation Verification

```bash
cd docs
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Results:
# - 0 compilation errors ✅
# - 0 BibTeX warnings ✅  (down from 1)
# - 29 pages (unchanged) ✅
# - 485KB PDF ✅
```

### Fix Verification Commands

```bash
# Verify no remaining issues
grep -n "Section 10\|15+\|agreement improve" docs/paper.tex
# Expected: 0 matches ✅

# Verify PDF generated
ls -lh docs/paper.pdf
# Expected: ~485KB, recent timestamp ✅

# Verify page count unchanged
pdfinfo docs/paper.pdf | grep Pages
# Expected: Pages: 29 ✅
```

## Key Takeaways

1. **Reproducibility paths are often wrong** - Authors write docs from memory, not by checking actual files. Always verify with `ls` commands.

2. **Final reviews should be comprehensive but scoped** - Use 10-category rubric for complete coverage, but grade each category independently (GO/CONDITIONAL/NO-GO).

3. **Fix everything in one commit** - Multiple validation passes are expensive. Once final review is done, apply all fixes atomically.

4. **Precision inconsistencies are common** - Tables often use different decimal places than text. Document but don't necessarily block on this.

5. **Post-fix verification is critical** - Run grep patterns, check compilation, verify PDF. Don't assume edits worked correctly.

6. **N=1 papers need careful claim scoping** - Review should verify that claims are appropriately hedged ("consistent with", "preliminary support", not "proves" or "demonstrates").

## Reusable Templates

### Review Assessment Template

```markdown
## [Category Name]

**Grade: ✅ GO / ⚠️ CONDITIONAL GO / ❌ NO-GO**

**Justification:** [1-2 sentences]

**Verification Results:**
- [Item 1]: [Status] ✅/❌
- [Item 2]: [Status] ✅/❌

**Issues Found:**
1. **Line XXX**: [Description] - [Current] → [Should be]

**Recommended Actions:**
- [Action 1]
- [Action 2]
```

### Fix Implementation Template

```bash
# Fix 1: [Short description]
# Old: [exact old text]
# New: [exact new text]

# Fix 2: [Short description]
# Old: [exact old text]
# New: [exact new text]
```

## Related Skills

- `paper-validation-workflow` - Automated numerical validation against data
- `academic-paper-validation` - Structured validation framework
- `academic-paper-review` - Peer review simulation
- `academic-paper-qa` - Q&A based validation

## Success Criteria

- [ ] All 10 categories assessed with GO/CONDITIONAL GO/NO-GO grades
- [ ] Every numerical claim verified against ground truth data
- [ ] All reproducibility paths verified against actual repository structure
- [ ] All fixes applied in single atomic commit
- [ ] Paper compiles with 0 errors and 0 warnings
- [ ] PDF generated with expected page count
- [ ] Grep verification confirms all issues resolved
- [ ] Overall assessment document created with clear GO/NO-GO recommendation
