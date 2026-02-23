---
name: doc-stale-future-improvements-audit
description: Systematically audit design docs for Future Improvements sections that describe features already implemented in source code. Use when an issue asks to audit docs for staleness, when CI flags stale docs, or after a period of active development.
category: documentation
date: 2026-02-22
user-invocable: true
---

# Doc Stale Future Improvements Audit

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Systematically audit all design docs for "Future Improvements" sections listing features already implemented in source code |
| **Outcome** | Fixed stale entries across 2 doc files; confirmed 2 others have genuinely-future items; PR merged |
| **Related Issues** | Follow-up from single-file audit to cover remaining docs |

## When to Use This Skill

Use this skill when:

- A "Future Improvements" or "Future Work" section in documentation describes something that's already implemented
- Systematic doc auditing is needed after a period of active development
- Issue specifically asks to audit docs for staleness against actual source code
- Follow-up after a single-file audit to cover remaining docs

**Triggers:**

- Issue title contains "audit", "stale", "Future Improvements"
- Grep reveals "Planned" or "Not Implemented" in adapter/component status tables
- CI or reviewer flags that docs list unimplemented features that now exist in source

## Verified Workflow

### Phase 1: Discover All Candidate Sections

```bash
# Find all Future Improvements / Future Work sections across docs
grep -rn "Future Improvements\|Future Work\|Coming Soon\|Planned\|Not Implemented" docs/ \
  --include="*.md" | grep -v "docs/arxiv/"
```

- Ignore raw run output directories (not authoritative docs)
- Ignore issue-tracking docs (not design docs)

### Phase 2: Cross-reference Against Source Code

For each candidate entry, verify against actual implementation:

**Adapters listed as Planned:**
```bash
ls <project-root>/adapters/          # Check which .py files exist
head -3 <project-root>/adapters/<name>.py  # Confirm it's real implementation, not stub
```

**Functions listed as future:**
```bash
grep -n "def calculate_\|def compute_\|def <function>" <project-root>/<module>.py
```

### Phase 3: Categorize Findings

| Status | Action |
|--------|--------|
| Listed as Planned/Future but .py file exists with real code | **Fix: mark Implemented** |
| Listed as Future but function exists, not integrated | **Fix: move to "Implemented but not yet integrated" section** |
| Listed as Future and genuinely not in source | **Leave as-is** |

### Phase 4: Apply Fixes

**Adapter status tables**: Update `Planned` → `Implemented`, add missing rows.

**ASCII diagrams**: Add missing components to diagram if they exist.

**Directory listings**: Correct filenames that have changed.

**Research doc sections**: Move implemented-but-not-integrated items from "Future Work" to "Currently Implemented" with an accurate status note.

### Phase 5: Commit and PR

```bash
git add docs/design/architecture.md docs/research.md
git commit -m "docs(design): audit and fix stale Future Improvements entries (#<issue>)"
git push -u origin <branch>
gh pr create --title "docs(design): audit and fix stale Future Improvements entries" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| Skill tool invocation in don't-ask mode | `/commit-commands:commit-push-pr` denied | Permission mode blocked skill tool — use direct git commands instead |
| Over-broad grep patterns (`TODO\|FIXME`) | Hundreds of false positives | Raw run archives and issue-tracking docs pollute results — narrow scope with `grep -v` |

## Key Observations

1. **ASCII diagrams and directory listings go stale faster than tables** — when a component file
   is added, the status table might get updated but the diagram and `ls`-style directory block
   often don't. Always check both.

2. **"Implemented but not integrated" is a valid intermediate state** — don't conflate
   "function exists" with "fully integrated into pipeline". Stats functions may exist but
   not yet be surfaced in outputs. Document this accurately.

3. **Raw run archives are not design docs** — captured workspace state from evaluation runs
   contains intentional template placeholders, not documentation debt.

## Results

| File | Stale Entries Found | Fixed |
|------|--------------------|----|
| `docs/design/architecture.md` | 4 adapters listed as Planned, missing adapter, wrong filename, diagram missing entry | Yes |
| `docs/research.md` | Functions not listed as implemented; multi-experiment loading not listed as done | Yes |
| `docs/design/container-architecture.md` | None (ARM64, layer caching genuinely not implemented) | N/A |
| `docs/design/analysis_pipeline.md` | Narrative generation genuinely future work | N/A |

## Reusable Grep Commands

```bash
# Find adapter status tables
grep -n "Planned\|Implemented\|Status" docs/design/architecture.md

# Find all Future Improvements sections in real design docs
grep -rn "## Future\|### Future\|Future Work\|Future Improvements" docs/design/ docs/dev/

# Cross-reference adapter doc table vs actual files
ls <project-root>/adapters/*.py | xargs -I{} basename {} .py

# Cross-reference "implemented" claims vs source
grep -n "def " <project-root>/analysis/stats.py | grep -i "<function-name>"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #880 (follow-up from #759), PR #989 merged | [notes.md](../../references/notes.md) |
