---
name: pr-review-no-action-ci-diagnosis
description: "Use when: (1) a PR review-fix plan concludes no code changes are required, (2) CI failures appear on a PR but changes are unrelated to the failing jobs, (3) CI flakes need to be distinguished from PR-introduced regressions, (4) a fix commit may be local-only and not yet pushed to remote, (5) a stale branch was force-pushed dropping a fix commit, (6) verifying a PR is ready to merge despite red CI, (7) a REQUIRED status check (e.g. security/dependency-scan, pip-audit) fails identically across multiple unrelated PRs because of a stale build/dependency cache in CI rather than anything in the PR's diff"
category: ci-cd
date: 2026-06-05
version: "2.2.0"
user-invocable: false
verification: unverified
history: pr-review-no-action-ci-diagnosis.history
tags: []
---
# pr-review-no-action-ci-diagnosis

Consolidated skill for handling PR review plans that conclude no code changes are needed, distinguishing pre-existing CI flakes from PR-introduced regressions, verifying fix commit push state, handling stale branches after force-push, and confirming no-op PR merge readiness.

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-06-05 |
| Objective | Consolidated skill covering all "PR review needs no action" and CI diagnosis scenarios |
| Outcome | Merged from 7 skills covering clean state handling, no-op detection, CI flake analysis, stale branch, no-action determination, no-fixes-needed, no-op verification; extended in v2.2.0 with a verified-ci stale-cache required-check diagnosis (see Phase 5b) |
| Verification | unverified (consolidated skill has mixed provenance; the v2.2.0 stale-cache required-check finding in Phase 5b is verified-ci) |

## When to Use

- A `.claude-review-fix-<issue>.md` plan concludes "No problems found" or "No fixes required"
- CI failure type is `execution crashed` (e.g. Mojo heap corruption flake)
- The failing test files have no logical connection to the files changed in the PR
- A PR shows red CI but only modifies documentation, configuration, or agent files
- A fix plan says "already fixed" but CI still shows failures (fix may be local-only)
- `git fetch` output shows `(forced update)` — a force-push may have dropped a fix commit
- You need to verify auto-merge is enabled without making code changes
- `link-check` fails on a PR that did not add new broken links
- Runtime crash tests fail on a PR that does not touch the crashing code
- A **required** status check (e.g. `security/dependency-scan`, pip-audit) fails **identically across multiple unrelated PRs** — and on main-derived branches too — while the failing tool passes when you run it **locally in the same env** (stale/poisoned CI build or dependency cache, not your diff) *(verified-ci, 2026-06-05)*
- CI logs show the gate **installing** dependency version X while the gate **reports** the vulnerable version Y — the fingerprint of a poisoned/stale `.pixi` / setup-pixi cache layer *(verified-ci, 2026-06-05)*

## Verified Workflow

### Quick Reference

```bash
# Check if fix commit is on remote (vs local-only)
BRANCH=$(git branch --show-current)
git log --oneline origin/${BRANCH}...${BRANCH}

# Confirm CI failures are pre-existing on main
gh run list --branch main --workflow "<failing-workflow-name>" --limit 3

# Re-trigger failed CI (if plan confirms no code change needed)
gh run rerun <run-id> --failed

# Check PR auto-merge state
gh pr view <PR_NUMBER> --json state,autoMergeRequest,mergeStateStatus,title

# Enable auto-merge if not set
gh pr merge <PR_NUMBER> --auto --rebase
```

### Phase 1: Read the review plan

```bash
cat .claude-review-fix-<issue>.md
```

Check the "Problems Found" and "Fix Order" sections.

- If both say "None" / "No fixes required" → proceed to Phase 2 verification
- If fixes are listed → implement them (this skill does not apply)

**Decision logic:**
```text
Read review plan
  |
  v
Problems Found == "None"?
  YES --> Fix Order == "No fixes required"?
            YES --> Verify CI, confirm no-op, stop.
            NO  --> Follow the fix order
  NO  --> Implement the listed fixes
```

### Phase 2: Verify the "no action" claim

**2a. Check git status** — confirm no uncommitted changes beyond the plan file itself:

```bash
git status
```

**2b. Confirm pre-commit passes on changed files:**

```bash
pixi run pre-commit run --files <changed-file>
```

**2c. Cross-reference CI failures against main** — the definitive confirmation step:

```bash
gh run list --branch main --workflow "<failing-workflow-name>" --limit 3
gh run view <main-run-id> --log-failed | grep -E "(FAILED|error)"
```

Pre-existing = same failure on main = no fix needed.
PR-caused = passes on main but fails on PR = must fix.

**2d. Confirm PR diff scope** — verify the PR only touches the expected files:

```bash
gh pr diff <pr-number> --name-only
```

### Phase 3: Classify each CI failure

For each failing job, determine if it could plausibly be caused by the PR's diff:

- Agent/config-only changes cannot cause Mojo runtime crashes
- Documentation-only changes cannot cause test execution failures
- `link-check` failures from `CLAUDE.md` root-relative paths predate any PR
- `execution crashed` = Mojo 0.26.1 heap corruption flake, not a regression

**Mojo heap corruption signature:**
```
error: execution crashed
libKGENCompilerRTShared.so (segfault)
```
This is a runtime-level crash. Re-running CI often passes.

**Documentation-only PR heuristic** — if a PR touches only these file types, CI test failures are definitionally pre-existing:
- `README.md`, `*.md` documentation
- `docs/` directory files
- `CONTRIBUTING.md`, `CHANGELOG.md`
- Non-executable config comments

### Phase 4: Check if fix commit is local-only (stale CI scenario)

When a plan says "already fixed" but CI still shows failures:

```bash
# 1. Find fix commit hash from plan file
grep -E "commit|fix commit|[0-9a-f]{8}" .claude-review-fix-*.md | head -5

# 2. Check if fix commit is on remote
BRANCH=$(git branch --show-current)
git log --oneline origin/${BRANCH}...${BRANCH}

# 3. Confirm CI runs are against old commit
gh run list --branch ${BRANCH} --limit 5

# 4. Check remote branch HEAD
gh pr view <pr-number> --json headRefOid,headRefName
```

**Diagnosis matrix:**

| Local has fix commit | Remote has fix commit | CI shows failures | Action |
| --------------------- | ---------------------- | ------------------- | -------- |
| Yes | No | Yes (stale) | Push branch to trigger CI re-run |
| Yes | Yes | Yes (stale) | Re-run CI manually: `gh run rerun <id> --failed` |
| Yes | Yes | No | Done — CI is passing |
| No | No | Yes | Fix commit missing; implement the actual fix |

CI runs are stale when ALL runs show the same pre-fix commit message and the fix commit date is newer than the latest CI run date.

### Phase 5: Handle stale branch after force-push

If the plan says "no fixes needed" but CI still fails pre-commit:

```bash
# 1. Check if the remote was force-pushed
git fetch origin <head-branch>  # shows "(forced update)" if rebased

# 2. Identify the actual PR branch (may differ from current worktree)
gh pr view <pr-number> --json headRefName

# 3. Verify remote still has unfixed code
git show origin/<head-branch>:<path/to/file> | grep -n "problem pattern"

# 4. Reset local to remote (drop stale local history)
cd <worktree-for-that-branch>
git reset --hard origin/<head-branch>

# 5. Apply fix, commit (do NOT push — calling script pushes)
git add <files>
git commit -m "fix: Address review feedback for PR #<pr-number>
...
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Mojo format line length rule**: 88 characters. Split long strings with implicit concatenation:

```mojo
# Before (>88 chars):
print("STATUS: Very long string that exceeds the 88 char limit set by mojo format.")

# After:
print(
    "STATUS: Very long string that exceeds the 88 char"
    " limit set by mojo format."
)
```

### Phase 5b: Required check fails repo-wide due to a stale CI cache (verified-ci, 2026-06-05)

This is a distinct, **verified** scenario from the rest of this skill (which is `unverified`).
It applies when a **required** status check fails *identically across multiple unrelated PRs*
(including branches freshly derived from main) and the diff has nothing to do with the check.
The cause is repo-wide CI infrastructure (a stale/poisoned `.pixi` / setup-pixi build cache),
**not** your code.

**Worked example (ProjectHephaestus, 2026-06-05):** PRs #1019, #1022, #1024 were each
BLOCKED by the required `security/dependency-scan` check. pip-audit (run in the pixi `lint`
env) reported `urllib3 2.6.3` as vulnerable (PYSEC-2026-141/142, fix `2.7.0`) on *every*
branch — including unrelated ones.

**Diagnosis — distinguish repo-wide infra failure from a PR regression:**

```bash
# 1. Does the SAME required check fail on OTHER, unrelated branches (incl. main)?
#    If yes -> suspect repo-wide infra, not your diff.
gh run list --branch main --workflow "<failing-workflow>" --limit 5 \
  --json status,conclusion,headBranch,databaseId

# 2. Is the offending dependency ALREADY fixed in the committed lockfile?
grep -n "urllib3" pixi.lock | head        # showed 2.7.0 already pinned

# 3. TRUST a LOCAL run of the failing tool over the stale CI result:
pixi run -e lint pip-audit                 # -> "No known vulnerabilities found"
```

If the lockfile already pins the fixed version **and** the tool passes locally in the same
env, there is **nothing to fix in your PR** — the CI environment is stale.

**Cache-poisoning fingerprint:** the CI log shows the gate *installing* the fixed version
while pip-audit *simultaneously reports* the old vulnerable version:

```text
... Installing urllib3-2.7.0 ...
pip-audit: urllib3 2.6.3  PYSEC-2026-141  Fix: 2.7.0   <-- impossible given the install above
```

That contradiction means a stale `.pixi` / setup-pixi cache layer is serving the *old*
environment. (See the cross-referenced skill `pixi-cache-true-unreliable`: setup-pixi
`cache: true` keyed on `pixi.lock` can keep serving a poisoned layer even right after a
dependency bump merges — expect a window where every PR's dependency-scan is red until the
cache is invalidated.)

**Resolution — the fix is usually NOT in your PR:**

```bash
# 1. Check whether main was ALREADY fixed by a separate cache-invalidation commit:
git log origin/main --oneline | grep -iE "unblock CI|cache poison|\.pixi cache"
#   -> "[Fix] Unblock CI on main: ... fix .pixi cache poisoning (#1021)"

# 2. If main is fixed, just pull it into the blocked PR via GitHub's update-branch:
gh pr update-branch <N>     # creates a merge commit from the fixed main

# 3. Verify the GitHub-created update-branch merge commit is signature-verified,
#    so it still satisfies a signed-commits pr-policy gate:
gh api repos/<owner>/<repo>/commits/<merge-sha> --jq '.commit.verification.verified'
#   -> true

# 4. The required check now re-runs against the fresh cache and flips to PASS.
gh pr checks <N> --watch
```

**Decision logic:**
```text
Required check fails on my PR
  |
  v
Same check fail on OTHER/unrelated branches (incl. main)?
  NO  --> Likely a real PR regression — investigate the diff (rest of this skill).
  YES --> Lockfile already pins the fixed version AND tool passes locally in same env?
            NO  --> Genuine repo-wide dep issue — fix lockfile on main, not just your PR.
            YES --> Stale CI cache. Do NOT change your PR.
                    Look for a "[Fix] unblock CI / cache poisoning" commit on main.
                      Found    --> gh pr update-branch <N>; verify merge-commit signature; check flips green.
                      Not yet  --> Wait for / request a cache invalidation on main; rebase after.
```

### Phase 6: Conclude no-op and stop

If all checks confirm pre-existing failures and no fixes are needed:

1. Optionally leave a comment: `gh issue comment <issue-number> --body "CI failures confirmed pre-existing. PR ready to merge."`
2. Check auto-merge: `gh pr view <PR_NUMBER> --json state,autoMergeRequest,mergeStateStatus,title`
3. Enable auto-merge if not set: `gh pr merge <PR_NUMBER> --auto --rebase`
4. **Stop. Do NOT create empty commits, do not search for extra work, do not push.**

**No-op conclusion template:**
```text
Fix plan analysis: No fixes required.

Evidence:
- PR changes: <file types only>
- Pre-commit: PASS on changed files
- CI failures: Pre-existing on main (verified via gh run list)
- Linked files: All exist and are accessible

Conclusion: PR is ready to merge as-is. No commit needed.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assuming grep hits = real imports | Ran grep for scheduler imports, got 16 files | File still exists on this branch (21 commits behind main) | Always check `git log` and branch position before interpreting grep results |
| Treating all CI failures as actionable | Investigated "Core Gradient" failures | They are Mojo heap corruption flakes unrelated to the PR | Read the failure type (`execution crashed`) and cross-reference with known flakes before investigating |
| Create empty fix commit | Ran `git commit --allow-empty` to satisfy automation | Empty commits add noise to history with zero value | Never fabricate work; if the plan says no fixes, do nothing |
| Re-run grep to find missed issues | Searched codebase for remaining NOTE: comments | The review plan already covered this; extra work is out of scope | Trust the review plan; if it says clean, it is clean |
| Assumed fix was pushed because plan said "already fixed" | Checked CI status without verifying remote branch | CI showed stale failures; fix commit was local-only | Always verify `git log origin/<branch>` vs local before concluding push state |
| Declared task complete after reading plan | Did not check `gh run list` timestamps vs. fix commit date | Would have left CI in failing state | Cross-check CI run commit message against the fix commit message |
| Trust the review plan without checking CI | Plan said "no fixes needed" so stopped | CI was still failing pre-commit due to mojo format violations | Always verify actual CI status even when plan says no fixes needed |
| Work in current worktree | Tried to fix files in `issue-3181` worktree | Wrong branch — PR was on `3084-auto-impl`, not `3181-auto-impl` | Always confirm the PR's `headRefName` before editing files |
| Apply fix to local branch as-is | Local branch had fix commit but was diverged from remote | Remote was force-pushed, dropping the fix commit | Must reset local to remote before re-applying fix |
| Applying fixes for link-check failures | Updated links in new files to pass lychee link-check | Checker fails on root-relative paths in CLAUDE.md regardless of PR additions | link-check failures are infrastructure-level; fixing individual file links does not resolve the CI job |
| Treating all red CI as blocking | Assumed every CI failure required a code fix | Autograd test crashes are Mojo runtime instability unrelated to agent config changes | Scope discipline: only fix regressions introduced by the PR |
| Manufacturing a commit | Creating an empty or trivial commit to satisfy task instructions | Pollutes history; the plan explicitly said no action needed | When the fix plan says "no action needed", do not create commits |
| Committing the plan file | Staged `.claude-review-fix-*.md` as a deliverable | The plan file is a temporary artifact, not an implementation file | Never commit review plan files — they are transient inputs, not outputs |
| Blindly following "implement all fixes" wrapper | Started looking for code to change despite the plan saying no fixes needed | The task wrapper says "implement all fixes" even when the plan says there are none — the wrapper is a generic template | Always read the plan body first; the wrapper instruction is not a guarantee of work |
| Inventing changes to justify a commit | Created changes with no real purpose just to satisfy the "commit" instruction | Adds noise to git history, violates minimal-change principle | Read the plan fully first; if no fixes, don't manufacture them |
| Running tests before enabling merge | Running `pixi run python -m pytest` before enabling auto-merge | Unnecessary work when CI already confirmed passing | Trust CI results — don't re-run passing tests locally for no-op fixes |
| Assume the failing required check is caused by my PR | Spent effort scrutinizing the diff because `security/dependency-scan` was red on PR #1019/#1022/#1024 | The *same* check failed identically on every branch, including ones freshly derived from main → it was repo-wide CI infra, not the diff | When a required check fails identically across multiple unrelated branches with a clean diff, suspect repo-wide infra (stale CI cache / drifted required-context), not your code |
| Try to fix urllib3 in my PR (bump/pin) | Attempted to bump/pin urllib3 to 2.7.0 inside the blocked PR to satisfy pip-audit | `pixi.lock` already pinned 2.7.0 (PR #1007 had merged) and local `pip-audit` reported "No known vulnerabilities found" → nothing to fix in-PR | Trust a local run of the failing tool over a stale CI result; a CI log installing version X while the gate reports version Y is a cache-poisoning fingerprint. The real fix was a separate cache invalidation on main — rebase via `gh pr update-branch <N>` |

## Results & Parameters

### Confirming pre-existing link-check failure

```bash
gh run list --branch main --workflow "Check Markdown Links" --limit 3 --json status,conclusion,databaseId
gh run view <run-id> --log-failed | grep -E "ERROR|404|not found"
```

### Confirming pre-existing test crashes

```bash
gh run list --branch main --workflow "Comprehensive Tests" --limit 3
gh run view <run-id> --log-failed | grep "execution crashed"
```

### CI failure classification table template

```
## CI Failure Analysis

| Job | Status | Caused by this PR? | Evidence |
|-----|--------|--------------------|----------|
| link-check | FAIL | No | Fails on main (run #XXXXX) — lychee lacks --root-dir |
| Autograd tests | FAIL | No | Fails on main (run #XXXXX) — Mojo runtime crash |

Conclusion: PR is merge-ready. No fixes required.
```

### Identifying the right PR branch

```bash
gh pr view <number> --json headRefName,baseRefName
```

### Checking if a fix commit survived a rebase

```bash
# Local has it:
git log --oneline main..<branch> | grep "fix"

# Remote may not:
git log --oneline origin/main..origin/<branch> | grep "fix"
```

If local has it but remote doesn't: the commit was dropped in a force-push.
Always reset local to remote before applying fixes to avoid working on stale history.

### Worktree vs PR branch mismatch (expected pattern)

The review-fix file is dropped into the worktree for the parent tracking issue (e.g. `3059-auto-impl`), but the actual PR is on a child issue branch (e.g. `3060-auto-impl`). This is expected — do not try to reconcile branch names or create extra commits.

### The "Gradient Checking Tests" workflow vs "Core Gradient" group

The separately-named "Gradient Checking Tests" workflow can pass even when the "Core Gradient" test group in Comprehensive Tests fails. These are different CI targets — one passing does not imply the other will.

### Plan File Pattern (No-Op)

```
## Problems Found
None. The PR:
- <reason 1 why it's already correct>
- <reason 2>

## Fix Order
No fixes required.
```

When this pattern is present, skip all implementation steps and go directly to verifying
worktree state and enabling auto-merge. The wrapper task instructions always say "Implement
all fixes from the plan above" — this is a generic template; the actual plan body determines
whether any work is needed.

### Stale-cache required-check failure — verified-ci (ProjectHephaestus, 2026-06-05)

**Symptom:** Required check `security/dependency-scan` BLOCKED PRs #1019, #1022, and #1024
identically. pip-audit (pixi `lint` env) flagged `urllib3 2.6.3` (PYSEC-2026-141/142,
fix `2.7.0`). The same check was red on unrelated branches too.

**Why it was NOT a code/lockfile problem:**

| Signal | Observation | Implication |
| ------- | ----------- | ----------- |
| Lockfile | `pixi.lock` already pinned `urllib3 2.7.0` (PR #1007 merged to main) | No vulnerable version committed |
| Local run | `pixi run -e lint pip-audit` → "No known vulnerabilities found" (2.7.0 at runtime + metadata) | Tool passes in the same env CI uses |
| CI log | Shows *installing* `urllib3 2.7.0` while pip-audit *reports* `2.6.3` | Contradiction = poisoned/stale `.pixi` / setup-pixi cache layer |
| Blast radius | Identical failure across multiple unrelated branches | Repo-wide infra, not any one diff |

**Resolution (verified):** main had already been fixed by a separate commit —
`[Fix] Unblock CI on main: remove stray LEARNINGS file + fix .pixi cache poisoning (#1021)`.
The blocked PRs were unblocked by pulling that fix in with `gh pr update-branch <N>` (no diff
change); `security/dependency-scan` then flipped to PASS. The GitHub-created update-branch
merge commit was confirmed signature-verified via
`gh api repos/<owner>/<repo>/commits/<sha> --jq '.commit.verification.verified'` → `true`,
so it still satisfied the signed-commits pr-policy gate.

**Reusable insights:**

1. A required check failing identically across multiple unrelated branches with a clean diff = repo-wide infra (stale CI cache / drifted required-context), not your code — distinguish from a PR-introduced regression.
2. Trust a local run of the failing tool over a stale CI result; a CI log installing version X while the gate reports version Y is a cache-poisoning fingerprint.
3. The fix is often NOT in your PR — check `git log origin/main` for a recent "[Fix] unblock CI / cache poisoning" commit; if main is fixed, `gh pr update-branch <N>` to pull it in, then verify the merge commit is signature-verified so the signed-commits gate still passes.
4. Pixi/setup-pixi caches keyed on the lockfile can serve a poisoned layer right after a dependency bump merges; expect a window where every PR's dependency-scan is red until the cache is invalidated (see `pixi-cache-true-unreliable`).

### Verified No-Op Sessions

**Session 1 — PR #3386 (Issue #3166)**
- Plan: `.claude-review-fix-3166.md` — all CI passing, 3 tests already implemented, no human review comments
- Action: `gh pr merge --auto --rebase 3386` — no code changes, no commit, no test run
- File already correct: `tests/shared/core/test_utility.mojo`

**Session 2 — PR #3182 (Issue #3083)**
- Plan: `.claude-review-fix-3083.md` — "No problems found. The PR is ready to merge."
- Action: confirmed HEAD was `3fea321a cleanup(logging): remove unimplemented RotatingFileHandler placeholder`
- Reported no action needed; script handled push
