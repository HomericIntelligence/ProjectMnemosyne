---
name: stale-doc-count-audit
description: 'TRIGGER CONDITIONS: Fixing stale numeric counts in documentation (figures,
  tables, sub-tests, source files). Use when a code registry or pipeline changes size
  but docs still reference old counts. Covers the pattern of searching all .md files
  for stale numbers after fixing the primary file.'
category: documentation
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
# stale-doc-count-audit

How to audit and fix stale numeric counts in documentation files when the underlying code registries change, ensuring no references are missed across the project.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-13 |
| Objective | Fix stale "27 figures" count across all docs after FIGURE_REGISTRY grew to 34 entries |
| Outcome | Success — fixed 8 occurrences across 3 files, plus 1 stale sub-test count |
| Issues | Quality audit finding (92/100, A-) |
| PRs | HomericIntelligence/ProjectScylla#1477 |

## When to Use

- A code registry (e.g., `FIGURE_REGISTRY`, table pipeline list) has grown or shrunk
- Documentation references hard-coded counts for generated artifacts
- After adding/removing figures, tables, subtests, or other enumerable outputs
- When an audit or review flags "stale counts" in docs

## Verified Workflow

### Step 1: Verify the actual count from code

Count entries in the authoritative source (the code registry), not from previous docs:

```bash
# Figures: count entries in FIGURE_REGISTRY dict
grep -c '"fig' scripts/generate_figures.py

# Tables: count entries in pipeline list (use AST for accuracy)
python3 -c "
import ast
tree = ast.parse(open('scripts/generate_tables.py').read())
for node in ast.walk(tree):
    if isinstance(node, ast.List) and any(
        isinstance(e, ast.Tuple) for e in getattr(node, 'elts', [])
    ):
        print(f'Table pipeline entries: {len(node.elts)}')
"

# Subtests: count YAML files
find tests/claude-code/shared/subtests/ -name "*.yaml" | wc -l
```

### Step 2: Fix the primary file with replace_all

Use `Edit` with `replace_all: true` to catch all occurrences in the main file (e.g., README.md). This is faster and less error-prone than fixing line-by-line.

### Step 3: Search ALL markdown files for remaining references

This is the critical step most plans miss. Always search project-wide:

```bash
grep -r "<old_count> figures" . --include="*.md" --exclude-dir=.git
grep -r "<old_count> total" . --include="*.md" --exclude-dir=.git
```

Files commonly missed:
- `docs/analysis-prompt.md` — analysis context descriptions
- `references/notes.md` — session notes with historical counts
- `docs/arxiv-submission.md` — paper submission metadata (may be intentionally different for a specific submission)

### Step 4: Run a broad exploration agent for other stale counts

After fixing the known issue, run an exploration agent to audit ALL numeric claims in docs against actual code. This catches cascading staleness (e.g., sub-test counts that also drifted).

### Step 5: Separate commits for separate fixes

Keep the planned fix and any newly-discovered fixes in separate commits for clean review.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Files fixed in this session

| File | Old | New | Occurrences |
|------|-----|-----|-------------|
| `README.md` | 27 figures | 34 figures | 5 |
| `docs/analysis-prompt.md` | 27 figures | 34 figures | 1 |
| `docs/analysis-prompt.md` | ~114 sub-tests | 120 sub-tests | 1 |
| `references/notes.md` | 27 figures | 34 figures | 1 |

### Verified correct counts (no change needed)

| Claim | Value | Source |
|-------|-------|--------|
| Tables | 11 | `scripts/generate_tables.py` pipeline list |
| Subtests | 120 | YAML files in `tests/claude-code/shared/subtests/` |
| Combined coverage | 9% | `pyproject.toml` `--cov-fail-under=9` |
| Unit coverage (scylla/) | 75% | Enforced separately in CI `test.yml` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1477 — fix stale figure/subtest counts | Quality audit finding |
