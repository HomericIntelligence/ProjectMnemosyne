# Doc Stale Future Improvements Audit

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Systematically audit all design docs for "Future Improvements" sections listing features already implemented in source code |
| **Outcome** | Fixed stale entries across 2 doc files; confirmed 2 others have genuinely-future items; PR #989 merged |
| **Category** | Documentation |
| **Related Issues** | #880 (follow-up from #759) |

## When to Use This Skill

Use this skill when:

- A "Future Improvements" or "Future Work" section in documentation describes something that's already implemented
- Systematic doc auditing is needed after a period of active development
- Issue specifically asks to audit docs for staleness against actual source code
- Follow-up after a single-file audit (like #759 for `container-architecture.md`) to cover remaining docs

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

- Ignore `docs/arxiv/` (raw run output, not authoritative docs)
- Ignore `docs/dev/code-quality-audit-*.md` (issue-tracking docs, not design docs)

### Phase 2: Cross-reference Against Source Code

For each candidate entry, verify against actual implementation:

**Adapters listed as Planned:**
```bash
ls scylla/adapters/          # Check which .py files exist
head -3 scylla/adapters/<name>.py  # Confirm it's real implementation, not stub
```

**Metrics listed as future:**
```bash
grep -n "def calculate_\|def compute_\|def <function>" scylla/metrics/process.py
grep -n "def <function>" scylla/analysis/stats.py
```

**Multi-experiment support:**
```bash
grep -n "load_all_experiments\|load_experiment" scylla/analysis/loader.py
```

### Phase 3: Categorize Findings

| Status | Action |
|--------|--------|
| Listed as Planned/Future but .py file exists with real code | **Fix: mark Implemented** |
| Listed as Future but function exists, not integrated | **Fix: move to "Implemented but not yet integrated" section** |
| Listed as Future and genuinely not in source | **Leave as-is** |

### Phase 4: Apply Fixes

**Adapter status tables**: Update `Planned` → `Implemented`, add missing rows.

**ASCII diagrams**: Add missing adapters to diagram if they exist.

**Directory listings**: Correct filenames (e.g., `codex.py` vs `openai_codex.py`).

**Research doc sections**: Move implemented-but-not-integrated items from "Future Work" to "Currently Implemented" with an accurate status note.

### Phase 5: Commit and PR

```bash
git add docs/design/architecture.md docs/research.md
git commit -m "docs(design): audit and fix stale Future Improvements entries (#880)"
git push -u origin <branch>
gh pr create --title "docs(design): audit and fix stale Future Improvements entries" \
  --body "Closes #880"
gh pr merge --auto --rebase
```

## Failed Attempts

### Skill tool blocked in don't-ask mode

The `/commit-commands:commit-push-pr` skill was attempted but denied in the current permission
mode. Fell back to manual git commands — this worked fine and is the correct approach when
skills are blocked.

### Over-broad grep patterns

Initial grep with `TODO\|FIXME` in docs/ produced hundreds of false positives from:
- `docs/arxiv/` raw run capture (test template placeholders)
- `docs/dev/code-quality-audit-*.md` (issue references, not stale design entries)

**Fix**: Narrow scope with `grep -v "docs/arxiv/"` and focus on design docs only.

## Key Observations

1. **ASCII diagrams and directory listings go stale faster than tables** — when an adapter file
   is added, the status table might get updated but the diagram and `ls`-style directory block
   often don't. Always check both.

2. **"Implemented but not integrated" is a valid intermediate state** — don't conflate
   "function exists" with "fully integrated into pipeline". Stats functions may exist in
   `stats.py` but not yet be surfaced in comparison tables. Document this accurately.

3. **Multi-experiment loaders can be added without updating docs** — `load_all_experiments()`
   was implemented but the Future Work section still said "add multi-experiment support."
   Cross-referencing loader.py revealed it was already done.

4. **Raw run archives are not design docs** — `docs/arxiv/` contains captured workspace state
   from evaluation runs. TODOs in those files are intentional template placeholders, not
   documentation debt.

## Results

| File | Stale Entries Found | Fixed |
|------|--------------------|----|
| `docs/design/architecture.md` | 4 adapters listed as Planned, GooseAdapter missing, wrong filename, diagram missing Goose | Yes |
| `docs/research.md` | Power Analysis functions not listed as implemented; Multi-experiment loading not listed as done | Yes |
| `docs/design/container-architecture.md` | None (ARM64, layer caching genuinely not implemented) | N/A |
| `docs/design/analysis_pipeline.md` | Narrative generation genuinely future work | N/A |

## Reusable Grep Commands

```bash
# Find adapter status tables
grep -n "Planned\|Implemented\|Status" docs/design/architecture.md

# Find all Future Improvements sections in real design docs
grep -rn "## Future\|### Future\|Future Work\|Future Improvements" docs/design/ docs/dev/

# Cross-reference adapters doc table vs actual files
ls scylla/adapters/*.py | xargs -I{} basename {} .py

# Cross-reference research.md "implemented" claims vs stats.py
grep -n "def " scylla/analysis/stats.py | grep -i "power\|mann\|kruskal"
```
