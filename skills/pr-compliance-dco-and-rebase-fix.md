---
name: pr-compliance-dco-and-rebase-fix
description: "Fix pr-policy CI failures caused by missing DCO trailers and merge conflicts. Use when: (1) pr-policy check fails with DCO missing, (2) rebase creates conflicts requiring resolution, (3) need to amend commit with both GPG signature and DCO trailer."
category: ci-cd
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [dco-signoff, pr-policy, merge-conflict, ci-fix, dcosignoff, pr-compliance, rebase-conflict]
---

# PR Compliance: DCO Sign-off & Rebase Conflict Resolution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-27 |
| **Objective** | Fix two related PR CI failures in one workflow: missing DCO trailers causing pr-policy rejection and merge conflicts from rebasing onto updated main |
| **Outcome** | Successful — all CI gates green (69 tests passed, 39/39 pre-commit hooks, all required checks) |
| **Verification** | verified-ci |
| **Context** | PR #1638, issue #1412, HomericIntelligence/ProjectHephaestus, branch `1412-auto-impl` |

## When to Use

- **Trigger 1**: pr-policy check fails with "missing Signed-off-by: Name `<email>` trailer" even though commit appears signed
- **Trigger 2**: Merge conflict appears after `git rebase origin/main` on a PR branch
- **Trigger 3**: Need to amend last commit to add BOTH `-s` (DCO trailer) AND `-S` (GPG signature)
- **Trigger 4**: PR combines auto-impl changes (which often lack DCO) with rebase-onto-updated-main (which creates conflicts)

## Verified Workflow - Quick Reference

```bash
# Step 1: Ensure you're on the correct branch
git checkout 1412-auto-impl

# Step 2: Add DCO trailer + GPG signature to last commit
git commit --amend -s -S

# Step 3: If rebase conflict occurs, resolve manually
git rebase origin/main
# On conflict, git status shows conflicted files
# Edit each file, keeping improvements from both sides
git add <conflicted-files>
git rebase --continue

# Step 4: Force-push to PR branch (safe with --force-with-lease)
git push origin 1412-auto-impl --force-with-lease

# Step 5: Monitor CI in GitHub
# - pr-policy check should now pass (DCO detected)
# - All pre-commit hooks should pass (39/39 for Hephaestus)
# - All tests should pass (69 for Hephaestus)
# - All CI gates should turn GREEN
```

## Verified Workflow - Detailed Steps

### Step 1: Diagnose the Failures

```bash
# Check pr-policy output
gh pr view <number> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.name == "pr-policy") | {name, conclusion, status}'
# Look for: conclusion=FAILURE, status=COMPLETED

# Check if commits are signed but lack DCO trailer
git log --pretty=fuller -1
# Should show both:
#  - "Commit: <hash>" with "GPG signature" line (GPG check)
#  - "Signed-off-by: Name <email>" trailer (DCO check)
# If only the GPG line is present, the DCO trailer is missing.
```

### Step 2: Add DCO Trailer + GPG Signature

The key insight: **`git commit -S` (GPG-only) does NOT add the DCO trailer.**

```bash
# Both flags are REQUIRED per ProjectHephaestus PR policy:
#  -s : adds "Signed-off-by: Name <email>" trailer (DCO)
#  -S : adds GPG cryptographic signature
git commit --amend -s -S
# This command:
# 1. Opens $EDITOR for optional message edit (save and exit to keep current message)
# 2. Adds the DCO trailer to the commit
# 3. Signs the commit with GPG

# Verify the trailer was added
git log --pretty=fuller -1 | grep "Signed-off-by"
# Should show: Signed-off-by: Your Name <your-email>
```

### Step 3: Rebase Onto Updated Main (If Conflicts)

```bash
# Attempt rebase
git rebase origin/main

# If conflicts appear:
git status
# Output shows conflicted files (both ours and theirs)

# Edit each conflicted file manually
# - Read the conflict markers: <<<<<<< HEAD / ======= / >>>>>>> <sha>
# - Keep improvements from BOTH sides (merge, don't pick one side)
# - Remove conflict markers

# Example: for file hephaestus/automation/some_module.py
# 1. Open the file
# 2. Find <<<<<<< HEAD sections
# 3. Merge the two versions: keep base improvements + PR's new code
# 4. Remove the markers: <<<<<<< / ======= / >>>>>>>
nano hephaestus/automation/some_module.py

# Stage all resolved files
git add hephaestus/automation/some_module.py
git add <other-resolved-files>

# Continue rebase (no --no-edit flag; rebase doesn't support it)
GIT_EDITOR=true git rebase --continue
# If the commit is now empty (content already on main), use:
# git rebase --skip
```

### Step 4: Force-Push (Safe Method)

```bash
# Always use --force-with-lease (safer than --force)
# It checks that the remote matches what you expect before pushing
git push origin 1412-auto-impl --force-with-lease
# If push fails with "stale info", the remote changed — fetch and retry:
git fetch origin
git push origin 1412-auto-impl --force-with-lease
```

### Step 5: Monitor & Verify

```bash
# Open PR in GitHub and wait for CI
gh pr view <number>

# Check specific gates
gh pr view <number> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.name | test("pr-policy|lint|tests")) | {name, conclusion, status}'

# Expected state:
# - pr-policy: conclusion=SUCCESS (DCO now detected)
# - lint: conclusion=SUCCESS (pre-commit hooks passed)
# - tests: conclusion=SUCCESS (all tests passed)
# When all are SUCCESS, the PR is unblocked.
```

## Failed Attempts Table

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial commit with `git commit -S` only | Used GPG signing flag (-S) alone, skipped DCO flag (-s) | pr-policy Check 4 failed: "missing Signed-off-by trailer"; the gate requires BOTH flags separately | DCO sign-off (-s) is orthogonal to GPG signature (-S); Git's -S does NOT automatically add the text trailer; always use both: `git commit -s -S` |
| Tried to merge conflicts with `git checkout --theirs` | Attempted to auto-resolve conflicts by taking one side | Lost PR's changes; base branch improvements were incorporated but PR's new code was discarded | Manual resolution required: edit each conflicted file and MERGE both sides' improvements; never auto-take one side |
| Force-pushed without `--force-with-lease` | Used `git push --force` | No immediate failure, but risky — if branch changed elsewhere concurrently, could overwrite another's work | Always use `--force-with-lease` for safety; it verifies the remote state before pushing |
| Rebased before adding DCO trailer | Attempted rebase first, thinking it would auto-add DCO during rebase | Rebase stripped GPG signatures; commit still lacked DCO trailer after rebase push | Add DCO+GPG signature to the commit BEFORE rebasing; if rebasing anyway, re-sign all commits with `git rebase --exec "git commit --amend --no-edit -s -S" origin/main` |
| Assumed conflict was resolved without git add | Manually edited conflicted files but forgot to stage them | Git rebase --continue refused with "unresolved conflicts" | After manually resolving each conflicted file, MUST `git add <file>` before calling `git rebase --continue` |

## Results & Parameters - Copy-Paste Workflow

```bash
# Complete end-to-end fix for PR #1638 / issue #1412 scenario
BRANCH="1412-auto-impl"
ISSUE_NUM="1412"

# 1. Checkout the branch
git checkout $BRANCH

# 2. Add DCO + GPG to last commit
git commit --amend -s -S

# 3. Rebase onto main (may have conflicts)
git rebase origin/main

# 4. If conflicts appear (you'll see "CONFLICT" in output):
#    - Edit conflicted files
#    - Keep improvements from both sides
#    - Remove conflict markers
#    - git add each resolved file
git add hephaestus/automation/some_module.py   # Example file
git add hephaestus/automation/another_module.py

# 5. Continue rebase
GIT_EDITOR=true git rebase --continue

# 6. Force-push with lease check
git push origin $BRANCH --force-with-lease

# 7. Monitor PR
gh pr view $ISSUE_NUM --json statusCheckRollup \
  --jq '.statusCheckRollup[] | {name, conclusion, status}'
```

## Results & Parameters - Expected Outputs

After successful execution, you should observe:

```bash
# 1. Commit log shows both DCO trailer AND GPG signature
git log --pretty=fuller -1
# Output includes:
# commit <sha>
# Commit: <hash>
#     gpg: Signature made <timestamp> with key <key-id>
#     gpg: Good signature from "<name>"
# Signed-off-by: Your Name <you@users.noreply.github.com>

# 2. All pre-commit hooks pass (ProjectHephaestus has 39/39)
pre-commit run --all-files
# Output: all hooks green, no failures

# 3. All tests pass (ProjectHephaestus has 69+ tests)
pixi run pytest tests/unit --co -q | wc -l
# Should show numeric count ≥ 69

# 4. All CI gates turn GREEN in GitHub
# - pr-policy: SUCCESS (DCO verified, conventional commits verified)
# - lint: SUCCESS (pre-commit hooks passed)
# - mypy: SUCCESS (type checking passed)
# - tests: SUCCESS (all test suites passed)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1638, Issue #1412 | Fixed auto-impl branch `1412-auto-impl`; added DCO trailer via `git commit --amend -s -S`; resolved rebase conflict on main by manually merging both sides; force-pushed with `--force-with-lease`; all 69 tests passed, 39/39 pre-commit hooks passed, all CI gates green (verified-ci) |

## Key Learnings

1. **DCO is Separate from GPG**: The `git commit -s` flag adds a *text trailer* (`Signed-off-by: ...`). The `git commit -S` flag adds a *cryptographic signature*. They are orthogonal. ProjectHephaestus PR policy requires BOTH, passed as separate flags.

2. **Rebase Conflicts Require Manual Resolution**: Auto-merge tools like `git checkout --ours` or `git checkout --theirs` lose one side's work. Always manually edit conflicted files, keeping improvements from both sides, then stage the resolved files.

3. **Force-Push Safely**: `git push --force-with-lease` is safer than `git push --force` because it checks that the remote matches your expectation before overwriting.

4. **PR Policy is Multi-Check**: A single `pr-policy` failure can mask multiple independent blockers (DCO, conventional commits, etc.). Always inspect the gate's sub-checks, not just the top-level status.

## References

- **git-dco-signoff-distinct-from-gpg-sign.md**: Detailed explanation of DCO vs GPG signatures
- **pr-rebase-conflict-resolution-patterns.md**: Comprehensive rebase and conflict resolution playbook (section K3 covers DCO+GPG re-signing in cluster PRs)
- **ProjectHephaestus CLAUDE.md**: PR policy requirements, commit message format, signing rules
- **PR #1638**: The actual fix PR that resolved issue #1412
- **Issue #1412**: auto-impl branch requiring DCO fix + rebase conflict resolution
