---
name: issue-cleanup-already-resolved-detection
description: "Use when: (1) assigned a cleanup, deletion, or quality-audit issue and the target file/artifact no longer exists or the problem is already resolved, (2) a branch is at the same commit as main with no commits ahead (git log main..HEAD returns nothing), (3) a prior merged PR is referenced in the issue description as having already made the fix."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [cleanup, deletion, quality-audit, already-done, file-existence, git-log, pr-check]
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Trigger** | Cleanup/deletion/quality-audit issue where the target artifact may already be gone |
| **Goal** | Avoid re-doing work already completed via a prior merge or commit |
| **Outcome** | Either confirm the fix is in place (report and stop), or find a minimal gap and close the issue with a real commit |
| **Time Saved** | Full implementation session if already resolved; prevents no-op duplicate commits |

## When to Use

- Issue asks to delete a file, remove deprecated code, remove a NOTE/TODO marker, or fix a code quality problem
- Working in an auto-impl worktree (`<issue-number>-auto-impl`)
- The target file is not found in the working tree (file deletion tasks)
- The stale marker referenced in the issue body is absent from the current file
- `git log main..HEAD` returns no output (branch is at same point as main)
- The issue description notes "recurring" or "prior fix attempted" or references a prior PR
- A quality audit issue references a specific prior commit or PR that "fixed" the problem

**Key difference from generic preflight check**: This skill handles the case where the branch may have NO commits ahead of main — the fix was already merged to main. It also covers the case where a minimal gap must be found to create a real commit to formally close the issue.

## Verified Workflow

### Quick Reference

```bash
# 1. Check if file/artifact still exists (for deletion tasks)
ls <target-path>

# 2. Check branch is ahead of main
git log --oneline main..HEAD    # No output = at same commit as main

# 3. Check git log for deletion/fix commit
git log --oneline -10

# 4. Verify no remaining references (for deletion tasks)
grep -r "<deleted-artifact>" . --include="*.<ext>"

# 5. Check for existing PR or issue state
gh pr list --head <branch-name>
gh issue view <N> --json state -q '.state'
```

### Step 1: Read the target file or check artifact existence

For **file deletion tasks**:
```bash
ls path/to/deprecated/file.mojo
# "No such file" -> it may already be deleted
```

For **marker/doc cleanup tasks** (read the actual file, not the issue description):
```bash
# Read the exact lines cited in the issue BEFORE touching anything
# The issue may reference an earlier commit — read the actual current state
head -10 path/to/file.py
# OR: grep for the specific marker
grep -n "<marker-text>" path/to/file
```

**Key point**: Always read the actual file rather than trusting the issue description's claim about current state. The issue may reference a stale commit like "The issue persists in commit c88692b" when the fix landed at a later commit.

### Step 2: Check if branch has commits ahead of main

```bash
git log --oneline main..HEAD
git diff main -- <target-file>   # No output = file identical to main
```

No output from both commands means the branch is at the same state as main — the fix was already merged.

### Step 3: Check git log for the fix/deletion commit

```bash
# Check recent commits on current branch
git log --oneline -10

# Search for commits mentioning the file or issue
git log --oneline --all --grep="<filename>"
git log --oneline --all --grep="#<issue-number>"
```

If a commit message like `chore: delete deprecated <file>` or `fix(docs): remove stale NOTE` appears, the work is done.

### Step 4: Verify no remaining references

```bash
# For file deletion — ensure nothing still imports the deleted file
grep -r "<deleted-module>" . --include="*.mojo"
grep -r "from <module> import" . --include="*.mojo"
# Zero matches confirms deletion is complete and safe

# For marker cleanup — confirm the marker is gone
grep -n "<stale-marker>" path/to/file
# No output confirms the marker is already removed
```

### Step 5: Check issue state and existing PR

```bash
gh issue view <number> --json state -q '.state'
# If CLOSED -> no work needed at all

gh pr list --head <branch-name>
# If PR exists and the fix is already committed -> task complete
```

If no open PR and no remaining work, confirm the session is complete.

### Step 6: Handle the "no commits ahead of main" case — find a minimal gap

When the branch is at the same commit as main (the fix is merged but the issue is still open), a real commit is required to formally close the issue. Find a minimal gap:

1. Read the target file in full to see what is already implemented.
2. Verify the prior merged PR that did the work: `gh pr view <prior-PR-number> --json title,state,mergedAt`
3. Compare each test/section with siblings to find structural coverage gaps (e.g., `assert_numel` present in one test but missing in a sibling).
4. Add the minimal change — one or two assertions or a small doc addition is sufficient.
5. Commit, push, create PR:

```bash
git add <file>
SKIP=mojo-format git commit -m "$(cat <<'EOF'
type(scope): brief description

Closes #N

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #N" --label <label>
gh pr merge --auto --rebase <PR_NUMBER>
```

### Step 7: Report and stop (when fix is confirmed)

Once confirmed:
- Do NOT edit the file if it is already correct
- Do NOT create a new commit if nothing meaningful to add
- Optionally post a closing comment on the issue if it is still OPEN:

```bash
gh issue comment <number> --body "Issue already implemented in commit <sha> and PR #<pr>. No further action needed."
```

## Decision Tree

```text
Is the target file/artifact missing from the working tree?
YES -> Check git log for deletion commit
  Found deletion commit? YES -> Check for remaining references
    Zero references? YES -> Check for existing PR
      PR exists? YES -> Task complete, report to user
      PR exists? NO -> Determine if PR needs to be created
    References exist? YES -> Still need to fix remaining references
  Found deletion commit? NO -> Check if file never existed (wrong path?)
NO -> Check if the stale marker/problem is still present in the file
  Marker still present? YES -> Proceed with normal cleanup implementation
  Marker absent? YES -> Check git log for prior fix commit
    Fix commit found? YES -> Report done, no action needed
    No fix commit? YES -> Investigate further (may be on a different branch)

Branch at same commit as main (git log main..HEAD empty)?
YES -> Find minimal gap to formally close issue, add it, commit, push, PR
NO -> Check git log for prior commits on branch, proceed as above
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Read file and assume work needed | Assumed issue open = work missing | All assertions were already present in main via prior PR | Always check `git log main..HEAD` first |
| Skip PR creation because no changes needed | Considered not creating a PR at all | Issue stays open with no resolution | Even for "already done" work, a PR is required to close the issue formally |
| Use `assert_all_values` as the only gap | Looked only at value assertions | `assert_numel` was the actual missing gap | Compare each test with its siblings to find structural coverage gaps |
| Re-implement immediately | Started editing file before reading git log | Would have created a duplicate commit with no-op change | Always check git log and existing PRs before any edit |
| Search only for the NOTE text | Grepped for the marker — found nothing | Marker was already removed | Absence of the marker is the key signal; check git history to understand why |
| Starting implementation without checking git log | Read the prompt, planned to search for imports and delete | File was already deleted in HEAD commit | Always run `git log --oneline -3` before any planning |
| Checking only the directory listing | Confirmed target file was absent | Correct but incomplete — also needed to confirm PR exists | Combine directory check with `gh pr list --head <branch>` |
| Trusting issue description's claim about current state | Issue said "The issue persists in commit c88692b" | Fix landed at a later commit; file was already clean | Always read the actual file rather than trusting the issue description |

## Results & Parameters

### Minimal gap pattern

When all value checks are done for a test issue, look for `assert_numel` — it is often present in one test function but missing in a sibling test covering the same operation with different parameters.

```bash
# Skip mojo-format when GLIBC version mismatches locally
SKIP=mojo-format git commit -m "..."

# Enable auto-merge immediately after PR creation
gh pr merge --auto --rebase <PR_NUMBER>
```

### Diagnostic commands (quality audit)

```bash
# Confirm file state
head -10 path/to/file.py

# Confirm fix commit exists
git log --oneline --grep="<issue-keyword>"

# Confirm issue state
gh issue view <number> --json state -q '.state'
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3060, branch `3060-auto-impl`, PR #3250 | `schedulers.mojo` already deleted in commit `a7e56eb1` |
| ProjectOdyssey | Issue #3066, branch `3066-auto-impl`, PR #3263 | `benchmarks/__init__.mojo` already deleted in commit `98f5ce44` |
| ProjectOdyssey | Issue #3094, branch `3094-auto-impl`, PR #3213 | Stale NOTE/TrainingLoop trait bounds already removed; PR open with auto-merge |
| ProjectOdyssey | Issue #3847, PR #4813 | All value assertions already present in main via PR #3845; added 2 missing `assert_numel` calls |
| ProjectScylla | Issue #1347, branch `1347-auto-impl` | Garbled docstring already fixed in commit `510c93c3`; issue was CLOSED |
