---
name: pr-review-ci-flake-analysis
description: 'Analyze CI failures on a PR to distinguish pre-existing flakes from
  regression. Use when: reviewing a PR whose only CI failures are execution crashes
  unrelated to the changed files, or when a review-fix plan concludes no code changes
  are needed.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | pr-review-ci-flake-analysis |
| **Category** | ci-cd |
| **Trigger** | Review-fix plan says "no code changes required" or CI fails with `execution crashed` |
| **Outcome** | Confirm PR safety, re-trigger CI, no unnecessary commits made |

## When to Use

- A `.claude-review-fix-<issue>.md` plan concludes the PR change is correct and safe
- CI failure type is `execution crashed` (Mojo heap corruption / ADR-009 flake)
- The failing test files have no logical connection to the files changed in the PR
- You need to distinguish a pre-existing CI flake from a regression introduced by the PR

## Verified Workflow

1. **Read the review-fix plan** — check if it explicitly states "no code changes required"
2. **Verify the safety claim** — grep for imports of the deleted/changed file across the codebase:
   ```bash
   grep -r "from shared.training.schedulers import\|from shared.training import schedulers" \
     --include="*.mojo" <worktree>/
   ```
3. **Understand the git state** — check branch status, note if it is behind main
4. **Inspect CI failure type** — `execution crashed` = ADR-009 heap corruption flake, not a regression
5. **Re-trigger failed CI** (if a run ID is provided in the plan):
   ```bash
   gh run rerun <run-id> --failed
   ```
6. **Do NOT commit** — no changes were made; the working tree only has the untracked review file

## Key Patterns Learned

### Worktree vs PR Branch Mismatch

The review-fix file is dropped into the worktree for the **parent tracking issue** (e.g. `3059-auto-impl`),
but the actual PR is on a **child issue branch** (e.g. `3060-auto-impl`). This is expected — do not
try to reconcile the branch names or create extra commits.

### Grep Can Be Misleading

When verifying "no imports of deleted file", grep may return hits **because the file still exists on
this branch** (the branch is behind main). This is normal — it means the deletion has not yet landed
on this worktree. Confirm by checking `git status` and `git log`.

### ADR-009: Mojo 0.26.1 Heap Corruption

CI test groups named "Core Gradient" fail intermittently with:
```
error: execution crashed
libKGENCompilerRTShared.so (segfault)
```
This is a **runtime-level crash**, not caused by application code changes. It is documented in
ADR-009 and partially addressed by file-splitting in commit `8a78d3aa`. Re-running CI often passes.

### The "Gradient Checking Tests" Workflow vs "Core Gradient" Group

The separately-named "Gradient Checking Tests" **workflow** (which runs gradient-specific validation)
can pass even when the "Core Gradient" **test group** in Comprehensive Tests fails. These are
different CI targets — one passing does not imply the other will.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming grep hits = real imports | Ran grep for scheduler imports, got 16 files | The file `schedulers.mojo` still exists on this branch (21 commits behind main) | Always check `git log` and branch position before interpreting grep results |
| Treating all CI failures as actionable | Initial reaction was to investigate the "Core Gradient" failures | They are ADR-009 heap corruption flakes with no connection to the PR change | Read the failure type (`execution crashed`) and cross-reference with ADR-009 before investigating |

## Results & Parameters

```bash
# Re-trigger only failed jobs (copy run ID from the review-fix plan)
gh run rerun <run-id> --failed

# Verify no real imports of a deleted file (adjust pattern for your file)
grep -r "from shared\.training\.schedulers import\|from shared\.training import schedulers" \
  --include="*.mojo" <worktree>/

# Check branch position relative to main
git status  # shows "behind 'origin/main' by N commits"
git log --oneline -5
```
