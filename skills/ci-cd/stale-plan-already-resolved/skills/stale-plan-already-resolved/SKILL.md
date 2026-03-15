---
name: stale-plan-already-resolved
description: "Detect when an issue's implementation plan is stale because the fix was already applied. Use when: the plan references specific line numbers that don't match current code, or the requested change is already satisfied by a broader fix already in place."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Issue plan was written when code was in state A, but code is now in state B (already fixed or changed further) |
| **Key insight** | Always verify actual current state before applying a plan — plans can become stale after other PRs merge |
| **Impact** | Prevents unnecessary changes and incorrect "fixes" that would revert progress |
| **Context** | Issue #4280: plan said change `test_*_layers.mojo` → `test_*_layers*.mojo`, but code already used `test_*.mojo` |

## When to Use

1. An issue's implementation plan references specific line numbers but the diff shows different content
2. A plan says "change X to Y" but X is not present — a broader/different change is already there
3. A follow-up issue references a prior fix (e.g., "follow-up from #3458") and the code may have evolved
4. The plan was written weeks ago and many PRs have merged since
5. CI pattern change issues where the pattern may have been updated as part of a broader consolidation

## Verified Workflow

### 1. Read the plan carefully for specific anchors

Look for references to:

- Specific line numbers (`line 234`)
- Specific patterns that should exist (`pattern: "test_*_layers.mojo"`)
- "Current state" described in the plan

```bash
# Issue plan said: "line 234: change test_*_layers.mojo → test_*_layers*.mojo"
```

### 2. Verify current file state against the plan's "before"

```bash
# Check if the "before" state from the plan still exists
grep -n "test_\*_layers\.mojo" .github/workflows/comprehensive-tests.yml
# If no output → the plan's "before" state is gone; something already changed it
```

### 3. Check what's actually there now

```bash
# Read the relevant section to understand current state
grep -A3 '"Models"' .github/workflows/comprehensive-tests.yml
```

### 4. Determine if the issue's goal is already satisfied

The key question: does the current state **achieve the same objective** as the planned change?

| Plan objective | Current state | Action |
|----------------|---------------|--------|
| `test_*_layers*.mojo` (match part files) | `test_*.mojo` (even broader, also matches part files) | Goal already met — add clarifying comment only |
| Add explicit filenames | Wildcard already present | Goal already met — no change needed |
| Remove explicit filenames | Already using wildcard | Goal already met — document only |

### 5. Apply the minimal appropriate change

If the goal is already met, the appropriate fix is:

- Update the **comment** to reflect current intent clearly
- Create a PR that closes the issue by documenting the already-correct state

```diff
- # ADR-009: test_googlenet_layers.mojo split into 3 parts (≤8 tests each)
- # to avoid Mojo v0.26.1 heap corruption under high test load.
+ # test_*.mojo glob auto-discovers all model tests including ADR-009 _partN split files
+ # (e.g., test_googlenet_layers_part1.mojo) without requiring manual CI updates.
```

### 6. Verify with validate_test_coverage.py

```bash
python3 scripts/validate_test_coverage.py
# Must exit 0 before committing
```

### 7. Close the issue via PR

Create the PR with `Closes #<issue>` even if the change is purely a comment update — this
formally closes the issue and documents that the goal was already achieved.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Key diagnostic | `grep -n "<pattern from plan>" <file>` — if empty, plan is stale |
| Validation command | `python3 scripts/validate_test_coverage.py` |
| Correct change scope | Comment-only update when the functional fix already exists |
| PR label | `cleanup` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Applying plan verbatim | Would have changed `test_*.mojo` back to `test_*_layers*.mojo` | This would have been a regression — narrowing a working broad pattern | Always read actual file before applying a "before → after" from a plan |
| Skipping verification | Assuming plan's "before" state was current | Plan said line 234 had `test_*_layers.mojo`; actual line 283 had `test_*.mojo` | Verify anchors (line numbers, patterns) before touching anything |
| Treating as no-op | Issue already resolved, do nothing | Issue remains open; no PR closes it | Even when goal is met, create a PR with a comment clarification to formally close |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4280 (follow-up from #3458) | [notes.md](../references/notes.md) |
