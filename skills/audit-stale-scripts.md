---
name: audit-stale-scripts
description: 'Audit scripts/ for stale one-time tools and safely remove confirmed
  candidates. Use when: follow-up cleanup after a bulk script removal PR, scripts/
  has grown with historical one-off files, or you need a caller-check pattern before
  deleting.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Category** | tooling |
| **Complexity** | Low |
| **Risk** | Low (read-only audit first, removal only after confirmation) |
| **Repo** | Any project with a `scripts/` directory |

Removes one-time and historical scripts that have no active callers, freeing the
`scripts/` directory of technical debt without breaking CI or other tooling.

## When to Use

- A prior bulk-cleanup PR removed a batch of scripts and a follow-up audit was requested
- `scripts/` contains files named with patterns like `bisect_*`, `fix-*`, `merge_*`, `add_*_to_*`, `migrate_*`, `batch_*`, `document_*`
- You need to confirm zero callers before deletion
- Preparing a `chore(scripts)` PR with a clear rationale for each removal

## Verified Workflow

### Step 1 — List all top-level scripts

```bash
ls scripts/*.py scripts/*.sh 2>/dev/null | sort
```

Use `Glob` for a full recursive view including subdirectories.

### Step 2 — Identify candidates by name pattern

Look for names that suggest one-time operations:

- `bisect_*` / `run_bisect_*` — git bisect artifacts
- `fix-*` / `fix_*` — autonomous one-time repair scripts
- `merge_*` — branch merge workflows already completed
- `execute_*` — one-off execution scripts
- `add_*_to_*` — bulk attribute injection (agents, configs, etc.)
- `batch_*` — one-time batch operations
- `document_*` — one-time documentation generators
- `migrate_*` — cross-project migrations

### Step 3 — Verify zero callers for each candidate

```bash
for script in execute_backward_tests_merge merge_backward_tests bisect_heap_test; do
  hits=$(grep -r "$script" .github/ justfile scripts/ \
    --include="*.yml" --include="*.py" --include="*.sh" --include="*.yaml" 2>/dev/null \
    | grep -v "^scripts/${script}" | grep -v "README" | grep -v "CHANGELOG")
  [ -n "$hits" ] && echo "REFERENCED: $script" || echo "NO CALLERS: $script"
done
```

**Important**: if script A references script B, both must be removed together or neither.
Check cross-references within the removal set before finalising.

### Step 4 — Read script headers to confirm purpose

```bash
head -20 scripts/candidate.py
```

Verify the docstring confirms a completed one-time operation.

### Step 5 — Check git history for context (optional)

```bash
git log --oneline --follow scripts/candidate.py | head -5
```

### Step 6 — Remove confirmed candidates

```bash
git rm \
  scripts/execute_backward_tests_merge.py \
  scripts/merge_backward_tests.py \
  scripts/bisect_heap_test.py \
  scripts/run_bisect_heap.sh \
  scripts/fix-build-errors.py \
  scripts/batch_planning_docs.py \
  scripts/add_delegation_to_agents.py \
  scripts/add_examples_to_agents.py \
  scripts/document_foundation_issues.py \
  scripts/migrate_odyssey_skills.py
```

### Step 7 — Update scripts/README.md

Add a "Removed Scripts" section under "Deprecated Scripts" listing each removed file
with a one-line rationale.

### Step 8 — Run pre-commit and commit

```bash
pixi run pre-commit run --all-files
git commit -m "chore(scripts): remove N stale one-time tool scripts

<list each script with reason>

Closes #<issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Include `migrate_odyssey_skills.py` in "active" category | Assumed cross-project migration scripts might still be needed | Script targets a different repo (ProjectMnemosyne) with no callers in CI, justfile, or README | Always grep for callers before assuming a script is active; cross-project tools with no callers are stale |
| Remove `bisect_heap_test.py` without checking its pair | Would have left `run_bisect_heap.sh` referencing a deleted file | `run_bisect_heap.sh` copies `bisect_heap_test.py` to /tmp | Always grep within the removal candidate set itself — scripts can reference each other |
| Skip README update | Only remove files, skip documentation | `scripts/README.md` overview mentioned "Migration utilities" which became inaccurate after removal | Always update README when removing scripts; the overview bullet list needs to stay accurate |

## Results & Parameters

**Issue context** (ProjectOdyssey): #3337 — follow-up to #3148 (19 scripts removed earlier)

**Scripts removed** (10 files, ~4,571 lines deleted):

```text
execute_backward_tests_merge.py  — one-time branch merge, already merged
merge_backward_tests.py          — duplicate merge approach
bisect_heap_test.py              — git bisect artifact (ADR-009 heap issue)
run_bisect_heap.sh               — wrapper for bisect_heap_test.py
fix-build-errors.py              — one-time autonomous repair
batch_planning_docs.py           — one-time batch doc generation
add_delegation_to_agents.py      — bulk agent update (completed)
add_examples_to_agents.py        — bulk agent update (completed)
document_foundation_issues.py    — one-time doc script (completed)
migrate_odyssey_skills.py        — cross-project migration (completed)
```

**Grep command for caller check**:

```bash
grep -r "$script" .github/ justfile scripts/ \
  --include="*.yml" --include="*.py" --include="*.sh" --include="*.yaml" 2>/dev/null \
  | grep -v "^scripts/${script}" | grep -v "README" | grep -v "CHANGELOG"
```

**Pre-commit result**: All 14 hooks passed on first run.
