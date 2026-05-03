---
name: tooling-rebase-conflict-semantic-analysis
description: "Resolve git rebase conflicts using semantic analysis rather than blindly taking
  --ours or --theirs. Use when: (1) git rebase origin/main produces conflicts and you are tempted
  to use --ours/--theirs for all hunks without inspecting each one, (2) a rebase conflict involves
  documentation or code that both branches modified for different reasons, (3) you need to verify
  that a 'take ours' or 'take theirs' decision is actually correct rather than just expedient."
category: tooling
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - git
  - rebase
  - conflict
  - semantic-analysis
  - merge
---

# Tooling: Rebase Conflict Semantic Analysis

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Resolve rebase conflicts correctly by inspecting what each conflicting commit was trying to accomplish, rather than applying a blanket `--ours`/`--theirs` rule |
| **Outcome** | Successful — all pre-commit hooks passed on resolved files; conflicts correctly resolved |
| **Verification** | verified-precommit (pre-commit hooks passed on resolved files) |

## When to Use

- `git rebase origin/main` produces conflicts on a branch with multiple commits
- You are tempted to resolve all conflicts with `git checkout --ours` or `git checkout --theirs`
  reasoning that "main already has the right version"
- A conflict involves a documentation file, workflow file, or source file that was modified by
  both the branch and main for potentially different reasons
- You want to verify that your conflict resolution decision is semantically correct (not just
  expedient)
- After applying `--ours`/`--theirs`, you want to validate that lint/pre-commit confirms the choice

## Verified Workflow

### Quick Reference

```bash
# 1. When rebase stops at a conflict:
git status  # See which files are conflicted

# 2. For each conflicted file — understand WHAT the incoming commit was trying to do:
git show REBASE_HEAD -- <file>   # See what the incoming commit changed
git show HEAD:<file>             # See what main currently has (the "ours" side)

# 3. Inspect each hunk individually — DO NOT apply blanket --ours or --theirs
grep -n "<<<<<<\|======\|>>>>>>" <file>

# 4. For each hunk, ask:
#    - What was the branch's change trying to accomplish?
#    - Does main already have that change (or a better version)?
#    - Are the two sides doing different things, or the same thing differently?
#    - Which version is more correct? (may differ hunk-by-hunk)

# 5. After resolving, confirm pre-commit passes:
pre-commit run --files <file>

# 6. Stage and continue:
git add <file>
git rebase --continue
```

### Detailed Steps

#### Step 1 — Understand the Incoming Commit's Intent

Before resolving any hunk, understand what the **incoming commit** (the commit being replayed)
was trying to accomplish:

```bash
# See the full diff of the commit being replayed
git show REBASE_HEAD

# See only changes to the specific conflicted file
git show REBASE_HEAD -- <file>

# If multiple commits are conflicting, check which one is current
cat .git/rebase-merge/head-name    # The branch being rebased
cat .git/rebase-merge/onto         # The target (main)
```

#### Step 2 — Understand What Main Already Has

```bash
# See the current state of the file on main (the "ours" side in a rebase)
git show HEAD:<file>

# In a rebase, "ours" = main (HEAD), "theirs" = the incoming commit from your branch
# This is the OPPOSITE of a merge (where "ours" = your branch)
```

Note: In `git rebase`, the labels are counter-intuitive:

- `<<<<<<< HEAD` (or `<<<<<<< Updated upstream`) = **main's version** (the base you're rebasing onto)
- `>>>>>>> <commit-sha>` = **your branch's version** (the commit being replayed)

#### Step 3 — Analyze Each Hunk Semantically

For each conflict block, ask these questions:

1. **Did main already fix what the branch was fixing?**
   - If main squash-merged all the branch's fixes (e.g., 41 markdownlint fixes), and the
     branch's version is doing the same reflow slightly differently → take main's version

2. **Is the branch's version an improvement over main?**
   - If the branch added content that main deleted (e.g., a useful comment), evaluate whether
     the deletion was intentional. If yes → take main. If no → keep the branch's addition.

3. **Are the two sides doing different things to the same line?**
   - If main removed a verbose prefix ("NOTE: ") making a line shorter, and the branch split the
     line to handle the old longer form → main's version (shorter line) is correct

4. **Per-hunk decision**: The same `--ours` or `--theirs` choice may be correct for some hunks
   but wrong for others in the same file. Always evaluate per hunk.

#### Step 4 — Validate with a Linter or Formatter

After resolving, validate that your choice is correct:

```bash
# For Mojo files — let mojo format confirm the result
pixi run mojo format <file>
# If no changes → the resolved version is syntactically correct

# For Markdown files — let markdownlint check
pre-commit run markdownlint --files <file>

# For all files — run all pre-commit hooks
pre-commit run --files <file>
```

#### Step 5 — Stage and Continue

```bash
# Verify no conflict markers remain
grep -c "<<<<<<\|======\|>>>>>>" <file>   # Must be 0

# Stage the resolved file
git add <file>

# Continue the rebase
git rebase --continue

# If more conflicts arise, repeat Steps 1-4 for each
```

### Session Example: PR #5348 (ProjectOdyssey)

The branch `fix/adr009-split-test-files-5128` (3 commits) was rebased onto main after
main received a squash of 41 markdownlint fixes. Two files conflicted:

**File 1: `CI-FAILURE-ROOT-CAUSE-ANALYSIS.md`**

- Branch's change: Reflow of text to fix markdownlint line-length violations
- Main's change: All 41 markdownlint fixes (from the squash — a superset of the branch's reflow)
- Analysis: Main's version contains everything the branch was trying to do and more
- Decision: Take main's version (`--ours` in rebase terms, i.e., HEAD)
- Confirmation: `pre-commit run markdownlint` passed on main's version

**File 2: `bf8/fp8_example.mojo`**

- Branch's change: Split a `print` statement across 2 lines because the original had `NOTE:`
  making it exceed 80 chars
- Main's change: Removed `NOTE:` prefix, making the line 70 chars — single line OK
- Analysis: Main already solved the line-length problem a different way (by shortening the line)
- Decision: Take main's version — `mojo format` confirmed single-line form is correct at 70 chars
- Confirmation: `pixi run mojo format bf8/fp8_example.mojo` produced no changes

In both cases, `--ours` was correct — but the correctness was established by **semantic
analysis**, not assumption.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Blanket `--ours` for all conflicts | Applied `git checkout --ours <file>` to all conflicted files reasoning "main already has the fixes" | Process was wrong even if the result happened to be right — misses cases where the branch has genuine improvements not in main | Always do semantic analysis first; the correct side must be justified per hunk, not assumed globally |
| Resolving without checking what the incoming commit did | Jumped to resolution without running `git show REBASE_HEAD -- <file>` | Produces correct results by luck; fails when branch has genuine changes that main lacks | Always inspect the incoming commit's intent before resolving any hunk |

## Results & Parameters

### Key Commands Reference

```bash
# Understand the incoming commit
git show REBASE_HEAD -- <file>       # What the commit-being-replayed changed
git show HEAD:<file>                 # Current state on main ("ours" in rebase)

# Find all conflict locations
grep -n "<<<<<<\|======\|>>>>>>" <file>

# Validate resolution
pre-commit run --files <file>        # Run all hooks
pixi run mojo format <file>          # For Mojo: no changes = correct

# Confirm no markers remain
grep -c "<<<<<<\|======\|>>>>>>" <file>   # Must be 0
```

### Rebase Conflict Label Reference

| Label | In Rebase | In Merge |
|-------|-----------|----------|
| `<<<<<<< HEAD` (ours) | Main's version (the base) | Your branch's version |
| `>>>>>>> <sha>` (theirs) | Your branch's commit being replayed | The branch being merged in |

This labeling is counter-intuitive: in a rebase, `--ours` gives you **main's version**,
and `--theirs` gives you **your branch's version**.

### Decision Flowchart

```text
For each conflict hunk:
  Did main already incorporate what the branch was trying to do?
  ├─ YES → Take main's version (--ours in rebase)
  └─ NO  → Does the branch have a genuine improvement or different change?
      ├─ YES → Evaluate the branch's change on its own merits
      │         Could both sides be combined (true merge)?
      │         ├─ YES → Manually merge both sides
      │         └─ NO  → Take the more correct/complete side
      └─ UNCLEAR → Run linter/formatter on each side; the one with 0 issues is correct
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 2026-05-03 — PR #5348, rebasing `fix/adr009-split-test-files-5128` onto main | 3-commit branch, 2 conflicted files; all pre-commit hooks passed after semantic resolution |
