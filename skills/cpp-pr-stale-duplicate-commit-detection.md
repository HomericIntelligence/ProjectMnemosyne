---
name: cpp-pr-stale-duplicate-commit-detection
description: "Detect and remove stale duplicate fix commits from a PR branch when the fix already landed on main via another PR. Use when: (1) all sanitizer CI jobs fail identically on a PR that looked correct, (2) a PR has extra commits not part of its stated payload, (3) a race/UB fix was authored in parallel with another branch."
category: ci-cd
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [cpp, pr, stale-commit, duplicate-fix, cherry-pick, force-with-lease, tsan, dangling-reference, return-by-value]
---

# Detecting and Removing Stale Duplicate Fix Commits from PR Branches

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Remove a stale parallel-attempt fix commit from a PR branch when that fix already landed on `main` via a different PR, restoring CI to green |
| **Outcome** | Success — CI re-armed after `git cherry-pick` of real payload only onto fresh `origin/main` base |
| **Verification** | verified-local (CI triggered, was in progress at capture time) |
| **History** | N/A (initial version) |

## When to Use

- A PR fails **all** sanitizer CI jobs identically (asan + tsan + ubsan + lsan), not just TSan
- The failure test is the same across every sanitizer (logical error, not a data race)
- `git log origin/main..origin/<branch>` shows MORE commits than the PR description claims
- A fix was authored concurrently with another branch, and you're unsure which version landed
- CI passes on `main` for the same tests that fail on the PR branch — regression is in the branch's own commits

## Verified Workflow

### Quick Reference

```bash
# 1. Inspect how many commits the PR actually carries
git fetch origin
git log --oneline origin/main..origin/<your-branch>

# 2. Check if any fix commit was already merged to main by another PR
gh pr list --state all --search "<symbol or function name from the suspicious commit>"

# 3. Once confirmed stale — rebuild branch with only the real payload commit
git checkout -B <branch> origin/main
git cherry-pick <real-payload-sha>
git push --force-with-lease origin <branch>

# 4. Re-arm auto-merge
gh pr merge <pr-number> --auto --rebase --repo <org>/<repo>
```

### Detailed Steps

#### Step 1: Diagnose — all sanitizers failing identically

When asan, tsan, ubsan, and lsan all fail with the **same test** and **same assertion**, the
root cause is logical UB or a logical error, not a data race. TSan-only failures point to
races; all-sanitizer failures point to incorrect code.

```bash
# Confirm main is green on the same tests
gh run list --branch main --limit 5

# View the failing test across multiple sanitizer runs
gh run view <run-id> --log-failed | grep -A 10 "FAILED\|Expected"
```

#### Step 2: Enumerate all commits on the PR branch

```bash
git fetch origin
git log --oneline origin/main..origin/<branch>
# Example output:
# 984fef0 fix(agents): synchronize TaskAgent::command_log_   <-- suspicious
# 51e34dd chore: remove MaestroClient and its tests          <-- real payload
```

If the PR should only carry one logical change but shows two commits, the second commit
is the primary suspect.

#### Step 3: Cross-reference against merged PRs

```bash
# Search by the symbol, function, or file that the suspicious commit touches
gh pr list --state all --search "command_log"
gh pr list --state all --search "<mutex_name> OR <function_name>"

# View the merged PR to confirm its fix content
gh pr view <merged-pr-number> --json mergedAt,commits,headRefName
```

If a PR is found that was merged **before** the current PR's branch was last pushed, and it
touches the same code, the commit on the current branch is a stale parallel attempt.

#### Step 4: Identify the regression introduced by the stale commit

Compare the stale commit against the already-merged fix:

```bash
git show <stale-sha>
git show <merged-correct-sha>  # From the other PR's merge commit on main
```

Common regressions in stale parallel fixes:
- Renamed symbols (e.g., `log_mutex_` → `command_log_mutex_`) that differ from the landed version
- Changed return types (e.g., `return-by-const-reference` instead of `return-by-value`)
- Missing or different lock scope

> **Critical C++ pitfall**: `return const std::vector<T>&` under a `lock_guard` is **always wrong**.
> The `lock_guard` is destroyed at function return, leaving the caller with an unguarded reference
> to a concurrently-mutating container. Always return by value from guarded accessors.

#### Step 5: Rebuild the branch with only the real payload

```bash
# Rebuild from clean main base — do NOT amend, that risks modifying the wrong commit
git checkout -B <branch> origin/main
git cherry-pick <real-payload-sha-only>

# Verify the branch now carries exactly one commit
git log --oneline origin/main..HEAD

# Push safely
git push --force-with-lease origin <branch>
```

#### Step 6: Re-arm auto-merge

```bash
gh pr merge <pr-number> --auto --rebase --repo <org>/<repo>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming TSan-only failure | Treated all-sanitizer failure as a data race | Data races only show under TSan; identical failures across all sanitizers indicate logical UB or incorrect code | When all sanitizers fail identically, suspect logic error first |
| Writing a new race fix without checking main | Started authoring a fresh synchronization fix | The fix already existed on main from a different PR; parallel authoring created a stale duplicate | Always `gh pr list --state all --search "<symbol>"` before writing a fix |
| Amending the stale commit | Considered `git commit --amend` to correct the stale commit | Would modify the wrong commit (the stale one) rather than cleanly removing it; also rewrites history in a confusing way | Cherry-pick only the real payload onto fresh `origin/main` — cleaner and auditable |
| `return const std::vector<T>&` from a guarded accessor | Returned a const-ref to a member vector under `lock_guard` | `lock_guard` is destroyed at function return; caller holds dangling reference to unguarded container | Always return by value from guarded accessors; never return references to members protected by a local lock |
| `git push --force` | Used bare `--force` to push the rebuilt branch | Safety Net hook blocks `--force`; non-fast-forward pushes to PR branches require `--force-with-lease` | Always use `--force-with-lease` — it also protects against overwriting unexpected remote commits |

## Results & Parameters

### Diagnosis Signals

| Signal | Interpretation |
|--------|---------------|
| All 4 sanitizers (asan/tsan/ubsan/lsan) fail the **same test** | Logical error in the branch's code, not a data race |
| `main` is green on the same tests | Regression is in the PR branch's commits, not upstream |
| `git log origin/main..origin/<branch>` shows N > expected commits | Branch carries extra/stale commits |
| `gh pr list --state all --search "<symbol>"` returns a merged PR | The fix already landed; branch commit is a stale duplicate |

### Safe Rebuild Commands

```bash
# Confirm real payload SHA before rebuilding
git log --oneline origin/main..origin/<branch>
# <real-sha>   <real commit message>
# <stale-sha>  <stale commit message>

# Rebuild
git checkout -B <branch> origin/main
git cherry-pick <real-sha>
git log --oneline origin/main..HEAD   # Should show exactly 1 commit
git push --force-with-lease origin <branch>
```

### Return-by-Value Pattern for Guarded Accessors (C++)

```cpp
// WRONG — lock released at return; caller has dangling reference
const std::vector<std::string>& getLog() const {
    std::lock_guard<std::mutex> lk(mutex_);
    return log_;  // lock_guard destroyed here; reference now unguarded
}

// CORRECT — copy made while lock is held; caller owns safe snapshot
std::vector<std::string> getLog() const {
    std::lock_guard<std::mutex> lk(mutex_);
    return log_;  // copy constructed under lock; lock released after
}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PR #436 (`chore/remove-maestro-client`), failing asan/tsan/ubsan/lsan on `E2E_PhaseB.AsyncAgentsConcurrentProcessing` | Stale commit `984fef0` duplicated fix already on main via PR #435 (`fix/tsan-command-log`); rebuilt branch with only `51e34dd`; CI re-armed |
