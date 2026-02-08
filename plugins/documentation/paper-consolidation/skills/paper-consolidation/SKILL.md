---
name: "Paper Consolidation Skill"
description: "Consolidate scattered LaTeX paper files into unified directory structure with publication readiness fixes"
category: documentation
date: 2026-02-07
user-invocable: false
---
# Paper Consolidation Skill

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-07 |
| **Objective** | Consolidate scattered LaTeX paper files into unified `docs/arxiv/dryrun/` structure with publication readiness fixes |
| **Outcome** | ✅ Success - Clean structure, 11 publication fixes applied, 0 LaTeX errors, 494KB PDF generated |
| **Files Changed** | 808 (mostly git mv renames preserving history) |
| **Build Status** | ✅ Compiles cleanly (pdflatex + bibtex) |

## When to Use This Skill

Use this skill when you need to:

1. **Consolidate scattered paper files** from multiple locations into a single canonical directory
2. **Prepare LaTeX papers for arXiv submission** requiring:
   - Single source directory with all dependencies
   - `\pdfoutput=1` directive
   - Clean build without external path dependencies
   - Standardized terminology and formatting
3. **Migrate from derived copies** (e.g., `main.tex`) back to single source of truth
4. **Apply batch publication fixes** across content, grammar, and technical corrections
5. **Preserve git history** during large-scale file reorganizations

**Trigger Conditions:**
- Paper files scattered across 3+ directories
- Build scripts reference multiple source locations
- Derived arxiv copy has diverged from canonical source
- Publication submission requires consolidated structure
- Need to standardize terminology (e.g., "dryrun" vs "dry run")

## Verified Workflow

### Phase 1: Directory Restructuring

**Goal:** Consolidate all files preserving git history

```bash
# 1. Create target directory structure
mkdir -p docs/arxiv/dryrun/{figures,tables,data,raw,archives}

# 2. Move files with git mv (preserves history)
git mv docs/paper.tex docs/arxiv/dryrun/paper.tex
git mv docs/references.bib docs/arxiv/dryrun/references.bib
git mv docs/paper-dryrun/figures/* docs/arxiv/dryrun/figures/
git mv docs/paper-dryrun/tables/* docs/arxiv/dryrun/tables/
git mv docs/paper-dryrun/data/* docs/arxiv/dryrun/data/
git mv docs/paper-dryrun-data/* docs/arxiv/dryrun/raw/
git mv docs/*.tar.gz docs/arxiv/dryrun/archives/
git mv docs/paper-dryrun-arxiv/00README.json docs/arxiv/dryrun/

# 3. Delete old directories AFTER move completes
rm -rf docs/paper-dryrun-arxiv docs/paper-dryrun docs/paper-dryrun-data
```

**Critical Success Factors:**
- Use `git mv` not `mv` - preserves file history
- Move files BEFORE deleting source directories
- Create all target subdirectories upfront
- Verify moves completed: `git status --short | grep "^R"`

### Phase 2: Update Internal References

**Goal:** Fix LaTeX paths to work from new location

```bash
# paper.tex moves from docs/ to docs/arxiv/dryrun/
# All relative paths change
```

**Required Edits:**

| Pattern | Old Value | New Value |
|---------|-----------|-----------|
| `\graphicspath{}` | `{{paper-dryrun/}}` | `{{./}}` |
| `\input{}` | `{paper-dryrun/tables/...}` | `{tables/...}` |
| Data references | `docs/paper-dryrun/` | `docs/arxiv/dryrun/` |

**Tool:** Use `Edit` tool with exact string matching (read file first)

### Phase 3: Apply Publication Fixes

**Goal:** Make paper submission-ready

**Priority 1: ArXiv Directive (REQUIRED)**
```latex
\documentclass[11pt]{article}
\pdfoutput=1 % Required by arXiv
```

**Priority 2: Content Fixes**

| Line | Pattern | Replacement | Reason |
|------|---------|-------------|--------|
| ~761 | "extra steps that actually helped" | "completed all expected steps" | Clarity - R_Prog metric description |
| ~95 | "state of the art" | "state-of-the-art" | Hyphenation rule |
| ~125 | "improvement on the output" | "effect on the output" | Grammar - "effect" not "improvement" |
| ~440 | "give idea what" | "give an idea of what" | Missing article |
| ~362 | `# /usr/bin/python3` | `#!/usr/bin/python3` | Shebang syntax |

**Priority 3: Standardization**

Use `Edit` with `replace_all: true` for consistent terminology:

| Pattern | Standardize To | Occurrences |
|---------|---------------|-------------|
| "dry run", "Dryrun" | "dryrun" | ~5 |
| "sub-test", "sub-tests" | "subtest", "subtests" | ~14 |
| "mcp" | "MCP" | 1 |
| "claude code" | "Claude Code" | 1 |

### Phase 4: Update Metadata Files

**ArXiv Config (`00README.json`):**
```json
{
  "sources": [
    { "filename": "paper.tex", "usage": "toplevel" }
  ]
}
```

**Gitignore (.gitignore):**
```gitignore
# LaTeX build artifacts
docs/arxiv/dryrun/*.aux
docs/arxiv/dryrun/*.blg
docs/arxiv/dryrun/*.log
docs/arxiv/dryrun/*.out
docs/arxiv/dryrun/*.bbl
```

### Phase 5: Compile & Verify

**Build Commands:**
```bash
cd docs/arxiv/dryrun
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

**Verification Checklist:**
```bash
# 1. Zero LaTeX errors
grep -c "^!" paper.log  # Should return 0

# 2. No unresolved references
grep "??" paper.log | grep -v "pdfTeX"  # Should be empty

# 3. Publication fixes applied
grep -n "extra steps" paper.tex  # Should return 0
grep -n "state of the art" paper.tex  # Should return 0
grep -n "paper-dryrun" paper.tex  # Should return 0

# 4. Files present
ls figures/*.pdf | wc -l  # Expected count
ls tables/*.tex | wc -l  # Expected count
ls data/*.{csv,json} | wc -l  # Expected count

# 5. PDF generated
ls -lh paper.pdf  # Check size is reasonable

# 6. Old dirs removed
test ! -d docs/paper-dryrun-arxiv && echo "OK"
test ! -d docs/paper-dryrun && echo "OK"
```

**Success Criteria:**
- ✅ 0 LaTeX errors
- ✅ 0 unresolved references
- ✅ PDF generated (expected size ~500KB)
- ✅ All figures/tables included
- ✅ Old directories deleted
- ✅ Git shows renames (R prefix in status)

## Failed Attempts & Lessons Learned

### ❌ Failed: Editing Before Reading File

**What Happened:**
```
Edit tool call failed with "String to replace not found in file"
```

**Root Cause:**
- Attempted multi-line string replacement without reading file first
- Line breaks in plan didn't match actual file formatting
- Edit tool requires EXACT string match

**Solution:**
```bash
# ALWAYS read the file section first
Read tool: offset=435, limit=10

# Then edit with EXACT string from output
Edit: old_string="<paste exact string from Read output>"
```

**Lesson:** For multi-line edits, read the exact context first. Line breaks and whitespace must match perfectly.

---

### ❌ Failed: Assuming Current Working Directory

**What Happened:**
```bash
cd docs/arxiv/dryrun && bibtex paper
# Error: No such file or directory
```

**Root Cause:**
- Bash tool doesn't preserve working directory between calls
- Each Bash invocation starts fresh in project root
- Previous `cd` commands don't persist

**Solution:**
```bash
# Option 1: Chain commands in single call
cd docs/arxiv/dryrun && pdflatex paper.tex && bibtex paper

# Option 2: Check pwd first
pwd  # Verify you're where you think you are

# Option 3: Use absolute paths
pdflatex /full/path/to/paper.tex
```

**Lesson:** Never assume `cd` persists across Bash tool calls. Use absolute paths or chain commands with `&&`.

---

### ⚠️ Warning: Replace vs Replace-All Confusion

**What Happened:**
- Used `replace_all: false` for standardization fixes
- Had to make 5 separate Edit calls for "dryrun" variants
- Inefficient and error-prone

**Better Approach:**
```bash
# For standardization, use replace_all
Edit: old_string="dry run", new_string="dryrun", replace_all=true
Edit: old_string="Dryrun", new_string="dryrun", replace_all=true
```

**Lesson:** Use `replace_all: true` for terminology standardization. Use `replace_all: false` for unique content fixes.

---

### ✅ Success: Git MV Preserves History

**What Worked:**
```bash
git mv docs/paper.tex docs/arxiv/dryrun/paper.tex
# Git status shows: R  docs/paper.tex -> docs/arxiv/dryrun/paper.tex
```

**Why This Matters:**
- File history preserved for `git log --follow`
- Rename detection works in diffs
- Blame annotations continue through move
- Better than `mv` + `git add`

**Lesson:** Always use `git mv` for large restructurings to preserve provenance.

---

### ✅ Success: Parallel Edits After Single Read

**What Worked:**
```bash
# 1. Read once to understand structure
Read: file_path=paper.tex, offset=755, limit=20

# 2. Make multiple edits based on that read
Edit: line 761 fix
Edit: line 95 fix
Edit: line 125 fix
```

**Lesson:** One Read can inform multiple Edit operations. Don't re-read between every edit.

## Results & Parameters

### Final Directory Structure

```
docs/arxiv/dryrun/
├── paper.tex              ← Single source of truth (74KB)
├── references.bib         ← Bibliography (13KB)
├── 00README.json          ← ArXiv config
├── figures/               ← 24 figures × 4 formats (PDF/PNG/CSV/Vega-Lite)
│   ├── *.pdf             ← For LaTeX inclusion
│   ├── *.png             ← For presentations
│   ├── *.csv             ← Raw data
│   └── *_include.tex     ← LaTeX wrappers
├── tables/                ← 10 tables
│   ├── *.tex             ← LaTeX formatted
│   └── *.md              ← Markdown sources
├── data/                  ← 6 analysis files
│   ├── criteria.csv
│   ├── judges.csv
│   ├── runs.csv
│   ├── subtests.csv
│   ├── summary.json
│   └── statistical_results.json
├── raw/                   ← Experiment run data (3.9MB)
│   ├── T0/ T1/ ... T6/   ← Per-tier runs
│   ├── result.json       ← Main results
│   └── config/           ← Run configs
└── archives/              ← Compressed backups
    ├── dryrun-analysis.tar.gz
    └── dryrun-data.tar.gz
```

### Publication Fixes Applied

**Content Corrections:** 5
- R_Prog metric description clarity
- Grammar: "effect" vs "improvement"
- Grammar: article insertion
- Technical: shebang syntax
- Hyphenation: "state-of-the-art"

**Standardization:** 6
- "dryrun" (5 replacements)
- "subtests" (14 replacements)
- "MCP" (1 replacement)
- "Claude Code" (1 replacement)
- Test paths (2 replacements)

**Infrastructure:** 3
- ArXiv `\pdfoutput=1` directive
- Relative path updates (2 patterns)
- Data path references (1 pattern)

### Build Configuration

**LaTeX Toolchain:**
```bash
pdflatex -interaction=nonstopmode  # Non-interactive compilation
bibtex                              # Bibliography processing
# Run pdflatex 3× total for cross-references
```

**Expected Output:**
- Pages: 32
- Size: ~494-505KB
- Figures: 24
- Tables: 10
- References: Auto-generated from references.bib

### Git Commit Pattern

**Commit Message Template:**
```
refactor(paper): restructure to docs/arxiv/dryrun/ with publication fixes

Directory restructuring:
- Moved paper.tex from docs/ to docs/arxiv/dryrun/
- Consolidated figures/ (N PDFs + formats)
- Consolidated tables/ (N .tex files)
- Moved raw data to raw/
- Updated 00README.json to reference paper.tex

Internal path updates:
- \graphicspath: {{paper-dryrun/}} → {{./}}
- \input: paper-dryrun/tables/... → tables/...

Publication readiness fixes:
[List 11 fixes with line numbers]

Cleanup:
- Deleted docs/paper-dryrun-arxiv/ directory
- Deleted docs/paper-dryrun/ directory
- Deleted docs/paper-dryrun-data/ directory
- Updated .gitignore for LaTeX artifacts

Verification: Paper compiles successfully.
Output: N pages, NNNKB PDF with all figures and tables.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Files Changed:** 808 (mostly renames)

## Related Skills

- `arxiv-submission` - Actually submitting to arXiv after consolidation
- `latex-build-automation` - Automating the build/verify cycle
- `git-history-preservation` - Advanced git mv patterns

## References

- Session: 2026-02-07 paper restructuring
- Branch: `skill/documentation/paper-final-review`
- Commit: `b8b9406`
- Plan source: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/02fd06a8-7ce9-439b-9d84-679357b67cc6.jsonl`
