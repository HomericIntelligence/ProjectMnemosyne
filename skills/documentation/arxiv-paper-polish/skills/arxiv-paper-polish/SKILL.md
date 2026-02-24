---
name: "Skill: arXiv Paper Publication Polish"
description: "Skill: arXiv Paper Publication Polish"
category: documentation
date: 2026-02-07
user-invocable: false
---
# Skill: arXiv Paper Publication Polish

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-07 |
| Objective | | Field | Value | |-------|-------| | **Date** | 2026-02-07 | | **Objective** | Apply publication-ready polish to LaTeX papers based on comprehensi... |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| **Date** | 2026-02-07 |
| **Objective** | Apply publication-ready polish to LaTeX papers based on comprehensive review feedback |
| **Outcome** | ✅ SUCCESS - All 5 fix categories applied, paper compiles cleanly, ready for arXiv submission |
| **Paper** | "Taming Scylla: Measuring Cost-of-Pass in Agentic CLI Tools" |
| **Files Modified** | 3 (paper.tex, references.bib, paper.pdf) |
| **Changes** | +36 insertions, -343 deletions |

---

## When to Use This Skill

Use this skill when you have:

1. **Completed comprehensive paper review** with identified issues across multiple categories
2. **LaTeX paper ready for submission** to arXiv or conference
3. **Multiple fix categories** requiring systematic application (precision, terminology, bibliography, paths, grammar)
4. **Need for verification** that all fixes compile correctly without breaking references

**Trigger conditions**:
- User provides structured fix list from paper review
- Paper has passed initial review but needs publication polish
- Need to reduce bibliography to only cited entries
- Multiple small fixes across different sections require coordination

---

## Verified Workflow

### 1. Parse Fix Categories

Organize fixes into categories for systematic application:

| Category | Examples |
|----------|----------|
| **Precision** | Decimal places, rounding consistency, numerical formatting |
| **Terminology** | Standardize technical terms (containers → git worktrees) |
| **Bibliography** | Remove uncited entries, verify all citations resolve |
| **Paths** | Correct file glob patterns, directory structures |
| **Grammar & Style** | Subject-verb agreement, hyphenation, capitalization, formality |

### 2. Read Affected Sections

```bash
# Read paper sections in parallel for all fix locations
# Use offset/limit for targeted reads
Read paper.tex (lines 1040-1060)  # Tier summary table
Read paper.tex (lines 305-320)     # Container references
Read paper.tex (lines 855-865)     # Test infrastructure
Read paper.tex (lines 1480-1495)   # Reproducibility paths
Read references.bib               # Full bibliography
```

### 3. Apply Fixes Systematically

**Apply by category, not by line number** to prevent errors:

```bash
# Fix 1: Precision updates (tier summary table)
Edit: Update all CoP values to 3 decimal places
Edit: Fix inconsistent T4 mean score (4dp → 3dp)

# Fix 2: Terminology standardization
Edit: "container" → "git worktree" (3 locations)
Edit: Remove "Docker" from required software list

# Fix 3: Bibliography cleanup
Write: New references.bib with only 10 cited entries (was 36)

# Fix 4: Path corrections
Edit: "tests/*/test.yaml" → "tests/fixtures/tests/*/test.yaml"

# Fix 5: Grammar & style polish (20+ edits)
Edit: Subject-verb agreement fixes
Edit: Verb form corrections ("setup" → "set up")
Edit: Hyphenation ("top level" → "top-level")
Edit: Capitalization ("github" → "GitHub", "mcp" → "MCP")
Edit: Formalize informal phrases ("super useful" → "particularly useful")
```

### 4. Full Compilation Verification

**Critical**: Run full LaTeX compilation cycle to verify all fixes:

```bash
cd docs/arxiv/dryrun

# Full compilation cycle (required for bibliography updates)
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex

# Verification checks
grep -c "^!" paper.log              # Check for LaTeX errors (expect: 0)
grep "??" paper.log | grep -v pdfTeX # Check unresolved references (expect: empty)
ls -lh paper.pdf                     # Verify PDF generated
grep -c "@" references.bib           # Verify bibliography count
```

### 5. Targeted Verification

**Verify each fix category was applied correctly**:

```bash
# Verify precision fixes (3 decimal places for CoP)
grep -A 10 "Tier & Pass Rate" paper.tex | grep "& 0\.[0-9][0-9][0-9] \\\\"

# Verify terminology fixes (no "container" references)
grep -n "container" paper.tex  # Expect: 0 matches

# Verify path fixes (full glob patterns)
grep -n "tests/\*/test.yaml" paper.tex  # Expect: 0 matches

# Verify grammar fixes (check removed informal phrases)
grep -n "super useful\|kitchen sink\|spit out" paper.tex  # Expect: 0 matches

# Verify bibliography reduced
wc -l references.bib  # Should be ~100 lines (was ~400)
```

### 6. Commit All Changes

```bash
git add docs/arxiv/dryrun/paper.tex
git add docs/arxiv/dryrun/references.bib
git add docs/arxiv/dryrun/paper.pdf  # Include regenerated PDF

git commit -m "fix(paper): polish for publication readiness

Apply 5 categories of fixes based on comprehensive review:
- Precision: 3 decimal places for CoP values
- Terminology: git worktrees, remove Docker
- Paths: correct glob patterns
- Grammar: formalize style, fix subject-verb agreement
- Bibliography: reduce to 10 cited entries only

Verified: compiles cleanly, 0 errors, 0 unresolved references

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Attempt: Apply fixes in line-number order

**Why it failed**: Line numbers shift after each edit, causing subsequent edits to target wrong text

**Lesson**: Apply fixes by category and use unique text strings for `old_string` parameter, not line numbers

---

### ❌ Attempt: Skip bibtex recompilation after bibliography changes

**Why it failed**: Bibliography changes require full compilation cycle (pdflatex → bibtex → pdflatex × 2) to update `.bbl` file

**Lesson**: Always run full 4-step LaTeX compilation when bibliography changes:
```bash
pdflatex → bibtex → pdflatex → pdflatex
```

---

### ❌ Attempt: Use `replace_all=true` for unique strings

**Why it failed**: Some terms appear in multiple contexts (e.g., "container" in text vs code listings)

**Lesson**: Default to `replace_all=false` and provide sufficient context in `old_string` to make matches unique

---

### ⚠️ Warning: Git worktree terminology requires Docker removal

**Context**: When changing "container" to "git worktree", must also remove Docker from required software list

**Lesson**: Terminology changes often have cascading effects in other sections (installation requirements, tool descriptions)

---

### ⚠️ Warning: Bibliography .bbl file must be committed for arXiv

**Context**: arXiv does not run bibtex during compilation, requires pre-compiled `.bbl` file

**Lesson**: Check `.gitignore` patterns for `*.bbl` - may need to force-add for arXiv submissions

---

## Results & Parameters

### Compilation Results

```
LaTeX Compilation: SUCCESS
- Errors: 0
- Unresolved references: 0
- PDF size: 494KB
- Page count: 32 pages
- Compilation time: ~8 seconds (full cycle)
```

### Fix Application Summary

| Category | Edits | Impact |
|----------|-------|--------|
| Precision | 8 | CoP values 2dp → 3dp, T4 score 4dp → 3dp |
| Terminology | 4 | "container" → "git worktree", remove Docker |
| Bibliography | 1 | 36 entries → 10 cited entries (-307 lines) |
| Paths | 2 | Add "fixtures/tests/" to glob patterns |
| Grammar & Style | 15+ | Formalize tone, fix agreement, standardize hyphenation |

### Verification Checklist Results

- ✅ No LaTeX errors (`grep -c "^!" paper.log` = 0)
- ✅ No unresolved references (`grep "??" paper.log` empty)
- ✅ PDF generated (494KB)
- ✅ Bibliography reduced (10 entries)
- ✅ Container references removed (0 matches)
- ✅ Glob paths corrected (0 old patterns)
- ✅ Grammar fixes applied (0 informal phrases)
- ✅ Pre-commit hooks passed

### File Changes

```
 docs/arxiv/dryrun/paper.tex      |  66 +++----
 docs/arxiv/dryrun/references.bib | 313 +------------------------------
 docs/arxiv/dryrun/paper.pdf      | Bin 505761 → 505883 bytes
 3 files changed, 36 insertions(+), 343 deletions(-)
```

---

## Copy-Paste Configuration

### LaTeX Compilation Pipeline

```bash
# Full compilation cycle (required after bibliography changes)
cd docs/arxiv/dryrun
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

### Verification Commands

```bash
# Error checking
grep -c "^!" paper.log                    # LaTeX errors (expect 0)
grep "??" paper.log | grep -v pdfTeX       # Unresolved refs (expect empty)

# Fix verification
grep -n "container" paper.tex              # Terminology (expect 0)
grep -n "tests/\*/test.yaml" paper.tex     # Paths (expect 0)
grep -c "@" references.bib                 # Bibliography count

# Grammar verification
grep -n "do not apply\|setup the\|top level\|github hash\|Sub-tests" paper.tex
grep -n "super useful\|figuring out\|kitchen sink\|hands out\|spit out" paper.tex
```

### arXiv Submission Checklist

```bash
# Required files for arXiv submission
- paper.tex              # Main source
- paper.bbl              # Pre-compiled bibliography (REQUIRED)
- 00README.json          # arXiv configuration
- figures/*.pdf          # Only PDFs referenced in paper
- tables/*.tex           # Only tables \input'ed in paper

# Files to EXCLUDE from arXiv submission
- *.aux, *.blg, *.log, *.out  # Build artifacts
- references.bib         # Not needed (use paper.bbl instead)
- data/, raw/, archives/  # Source data (optional supplementary)
```

---

## Related Skills

- `paper-final-review` - Comprehensive 10-category GO/NO-GO review before polish
- `latex-compilation-debug` - Troubleshoot LaTeX compilation errors
- `bibliography-cleanup` - Remove uncited references from .bib files

---

## Success Metrics

- **Compilation success rate**: 100% (0 errors, 0 warnings critical)
- **Fix application rate**: 100% (all 5 categories applied, verified)
- **Bibliography reduction**: 72% (36 → 10 entries, -307 lines)
- **Pre-commit pass rate**: 100% (all hooks passed)

---

## Notes

- This skill assumes you have a **structured fix list** from a prior review (see `paper-final-review` skill)
- **Always run full compilation cycle** after bibliography changes (4-step process)
- **Verify each fix category** independently before committing
- **Include regenerated PDF** in commit to reflect all changes
- For large papers (>50 pages), consider splitting fix categories into separate commits
