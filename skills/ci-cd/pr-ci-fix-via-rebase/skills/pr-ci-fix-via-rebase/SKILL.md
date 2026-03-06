---
name: pr-ci-fix-via-rebase
description: "Fix PR CI failures caused by a stale branch that is many commits behind main. Use when: CI crashes/segfaults unrelated to PR changes, branch is 10+ commits behind main, or tests pass on main but fail on the PR branch."
category: ci-cd
date: 2026-03-06
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Fix PR CI failures caused by branch staleness, not the PR's own changes |
| **Trigger** | Fuzz/integration tests crash on PR but pass on main; branch is N commits behind |
| **Outcome** | Rebased branch pushed, new CI run triggered, failures resolved |
| **Risk** | Low — force-with-lease prevents overwriting unexpected remote changes |

## When to Use

1. PR CI shows test crashes (segfault, `execution crashed`) in tests unrelated to the PR's changes
2. The branch is 10+ commits behind `main`
3. The same tests pass on `main` but fail on the PR branch
4. CI failure log shows crash at startup/initialization (before test logic runs)
5. PR changes are small/focused (e.g., adding exports, enabling tests) with no fuzz infrastructure changes

## Verified Workflow

### Step 1: Confirm the failure is staleness-related

```bash
# Check how many commits behind main the branch is
git log --oneline origin/3013-auto-impl..origin/main | wc -l

# Verify the failing tests pass on main
gh run list --branch main --limit 5 --json databaseId,workflowName,conclusion
gh run view <run-id> --json jobs | python3 -m json.tool | grep -B2 -A3 '"name": "Fuzz Tests"'
```

Key indicator: if the failing test passes on `main`, the fix is a rebase — not a code fix.

### Step 2: Create worktree for isolation

```bash
git fetch origin <branch-name>
git worktree add worktrees/<issue>-fix <branch-name>
```

After adding the worktree, check if the local branch is already rebased:

```bash
git log --oneline origin/main..HEAD
# If this shows ONLY the PR commit(s), the local tracking is already rebased.
```

### Step 3: Verify the local branch state

```bash
# Show exactly what the rebased branch contributes vs main
git diff origin/main..HEAD --stat
git show --stat HEAD
```

Confirm the commit is clean, minimal, and correct.

### Step 4: Force-push the rebased branch

```bash
git push --force-with-lease origin <branch-name>
```

**Always use `--force-with-lease`** (not `--force`) — it fails if the remote has unexpected
new commits since your last fetch, preventing accidental overwrite.

### Step 5: Verify CI triggered and track

```bash
sleep 5
gh pr checks <pr-number> 2>&1 | grep -E "Fuzz|fail|pending" | head -10
```

### Step 6: Cleanup

```bash
cd /path/to/repo
git worktree remove worktrees/<issue>-fix
git worktree prune
```

## Diagnosing the Crash Type

| Crash pattern | Diagnosis | Fix |
|---------------|-----------|-----|
| Crash before test output, in `.so` library | Startup crash — pre-existing in old code | Rebase |
| Crash after some test output, OOM | Memory issue in test code | Check `max_numel` guards |
| Crash only for specific export names | Compiler/linker side-effect | Bisect exports |
| Crash intermittently across runs | Flaky test | Use retry logic |

For the startup crash pattern (seen in this session):
```
#0 ... libKGENCompilerRTShared.so
/bin/mojo: error: execution crashed
```
This is always a pre-existing issue in the older code, resolved by rebase.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally to reproduce | `pixi run mojo test tests/shared/fuzz/test_tensor_fuzz.mojo` | GLIBC version mismatch on local machine (`GLIBC_2.32/2.33/2.34` not found) | Local Mojo environment may not be usable; rely on CI for verification |
| Checking if fuzz crash was OOM | Reviewed `ShapeFuzzer` with `max_dim=50`, `max_ndim=5` | ShapeFuzzer already has `max_numel=10_000_000` guard (line 142-143 in fuzz_shapes.mojo) — OOM not the cause | Always check existing guards before assuming memory issue |
| Bisecting exports as cause | Considered removing `tile`/`repeat`/`permute` exports temporarily | Not needed — main CI proved fuzz tests pass on current main, so the exports aren't the cause | Confirm on main first before bisecting the PR's changes |

## Results & Parameters

**Session outcome**: PR #3241 CI fixed. Branch rebased from 17 commits behind to current main.

**Key parameters**:

```bash
# The push command that fixed it
git push --force-with-lease origin 3013-auto-impl
# Output: + c5ebf755...e3c4ce1b 3013-auto-impl -> 3013-auto-impl (forced update)

# How to check if fuzz tests pass on main before pushing
gh run view <main-run-id> --json jobs | python3 -m json.tool | grep -B2 '"name": "Fuzz Tests"'
# Look for: "conclusion": "success"
```

**Diagnostic command sequence** (copy-paste ready):

```bash
# 1. How far behind is the branch?
git log --oneline origin/<branch>..origin/main | wc -l

# 2. Does the failing test pass on main?
gh run list --branch main --limit 3 --json databaseId,workflowName,conclusion
gh run view <id> --json jobs | python3 -m json.tool | grep -A5 '"name": "<test-name>"'

# 3. Is the local branch already rebased?
git worktree add worktrees/<name> <branch>
git -C worktrees/<name> log --oneline origin/main..HEAD

# 4. Push and verify
git -C worktrees/<name> push --force-with-lease origin <branch>
sleep 5 && gh pr checks <pr-number> | grep -E "fail|pending"

# 5. Cleanup
git worktree remove worktrees/<name> && git worktree prune
```
