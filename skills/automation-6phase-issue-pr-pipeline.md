---
name: automation-6phase-issue-pr-pipeline
description: "6-phase automation pipeline for GitHub issue processing across HomericIntelligence repos. Use when: (1) building a multi-phase GitHub issue automation loop (plan, review-plan, implement, review-PR, address-review, drive-green), (2) implementing inline PR review comments via GitHub GraphQL addPullRequestReview mutation, (3) resuming a Claude session from a prior implementer's session_id, (4) preventing Claude workers from launching for issues without open PRs (pre-discovery no-PR guard), (5) implementing dry-run discipline where side-effectful calls are gated but Claude analysis still runs."
category: architecture
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [automation, github, pipeline, pr-review, address-review, ci-driver, graphql, session-reuse, dry-run, multi-repo]
---

# 6-Phase GitHub Issue Automation Pipeline

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Design and implement a complete 6-phase automation pipeline in Python for processing open GitHub issues across HomericIntelligence repos in a loop |
| **Outcome** | SUCCESS — all 6 phases implemented with 251 unit tests passing; ruff + mypy clean; verified-precommit |
| **Verification** | verified-precommit — 251 unit tests pass locally, ruff + mypy clean |
| **History** | Extends multi-repo-automation-loop-shell-script (2-phase plan+implement) to a full 6-phase loop |

## When to Use

- Building a multi-phase GitHub issue automation loop (plan → review-plan → implement → review-PR → address-review → drive-green)
- Implementing inline PR review comments via GitHub GraphQL (`addPullRequestReview` mutation) rather than normal PR comments
- Resuming a prior Claude session from an implementer's saved `session_id` (`claude --resume <session_id>`)
- Preventing Claude workers from being launched for issues that have no open PR (pre-discovery no-PR guard)
- Implementing dry-run discipline: side-effectful API calls are gated but Claude analysis still runs
- Adding new GitHub API helpers for PR review posting, unresolved thread listing, thread resolution, and CI checks
- Gating a final-loop-only phase (e.g., auto-merge) on `loop == LOOPS`

## Verified Workflow

### Quick Reference

```python
# Phase sequence per repo per iteration:
# 1. plan-all       — plan every open issue, post plan as GH issue comment
# 2. review-plans   — review every posted plan, post plan-review as GH issue comment
# 3. implement-all  — implement every issue, create PR
# 4. review-PRs     — review each PR, post INLINE review comments (GraphQL)
# 5. address-review — for each PR with unresolved threads, resume implementer session
# 6. drive-green    — 1 fix iteration on red CI checks, enable auto-merge [FINAL LOOP ONLY]

# address_review session reuse pattern:
session_id = self._load_impl_session_id(issue_number)
# session_id read from .issue_implementer/issue-{N}.json
if session_id:
    cmd = ["claude", "--resume", session_id, "--print", ...]
else:
    cmd = ["claude", "--print", ...]  # fresh session fallback

# Pre-discovery no-PR guard in run():
pr_map = self._discover_prs(issue_numbers)  # BEFORE submitting workers
for issue_number in issue_numbers:
    if issue_number not in pr_map:
        continue  # Never launch a worker for a PR-less issue
with ThreadPoolExecutor(...) as executor:
    futures = {executor.submit(self._address_issue, n, pr_map[n], slot): n
               for n, slot in zip(filtered_issues, slots)}

# drive-green gating:
if loop == loops:
    ci_driver.run(repo_dir, issue_numbers)
```

### Detailed Steps

#### Phase 1: plan-all (PlanIssues)

Calls `hephaestus.automation.planner` for each open issue. Posts the generated plan as a GitHub issue comment. Existing plan comments are detected and skipped to avoid duplicates.

#### Phase 2: review-plans (PlanReviewer)

Iterates all open issues that have a plan comment. Claude reads the plan and posts a review comment on the same issue. The reviewer is strictly read-only — no commits, no pushes.

**New file**: `hephaestus/automation/plan_reviewer.py`

```python
class PlanReviewer:
    def run(self, repo_dir, issues): ...
    def _review_issue(self, issue_number, plan_comment): ...
    # Posts review via: gh issue comment <N> --body "<review text>"
```

#### Phase 3: implement-all (IssueImplementer)

Existing `hephaestus.automation.implementer` — creates worktree, runs Claude, creates PR. Saves `session_id` to `.issue_implementer/issue-{N}.json`.

#### Phase 4: review-PRs (PRReviewer — read-only)

Claude analyzes the PR diff and CI state, then posts inline review comments via GitHub GraphQL `addPullRequestReview` mutation. Strictly read-only: no commits, no pushes — only comment posting.

**New file**: `hephaestus/automation/pr_reviewer.py` (refactored from reviewer.py)

```python
class PRReviewer:
    def run(self, repo_dir, issues): ...
    def _review_pr(self, issue_number, pr_number): ...
    # Posts via gh_pr_review_post() — GraphQL addPullRequestReview
    # Returns list of thread IDs
```

#### Phase 5: address-review (AddressReview)

For each PR with unresolved review threads:
1. Load the implementer's `session_id` from `.issue_implementer/issue-{N}.json`
2. Resume that session with `claude --resume <session_id> --print <prompt>`
3. Parse Claude's JSON output for `{"addressed": [...thread_ids...], "replies": {...}}`
4. Resolve ONLY threads that Claude explicitly lists in `addressed` — others stay open
5. Post reply comments for threads listed in `replies`

**New file**: `hephaestus/automation/address_review.py`

```python
class AddressReview:
    def run(self, repo_dir, issues): ...
    def _address_issue(self, issue_number, pr_number, slot_id): ...
    def _load_impl_session_id(self, issue_number) -> str | None: ...
    # Reads .issue_implementer/issue-{N}.json -> session_id
```

**Critical selective resolution rule**: Claude's output is parsed for:
```json
{"addressed": ["thread_abc", "thread_xyz"], "replies": {"thread_abc": "Fixed by..."}}
```
Only threads in `addressed` get `resolveReviewThread` called. Threads not mentioned stay open.

#### Phase 6: drive-green (CIDriver — final loop only)

Gated by `loop == LOOPS`. For each PR with failing required CI checks:
1. Fetch failing check names via `gh_pr_checks()`
2. Run exactly 1 fix iteration (never more) per PR per invocation
3. Resume implementer session with failing check context
4. Push fix, re-check CI
5. Enable auto-merge when all required checks pass: `gh pr merge --auto --rebase`

**New file**: `hephaestus/automation/ci_driver.py`

```python
class CIDriver:
    def run(self, repo_dir, issues): ...
    def _fix_pr(self, issue_number, pr_number): ...
    # Exactly 1 fix iteration per invocation — never loops internally
```

#### New GitHub API helpers

**New additions in `hephaestus/automation/github_api.py`**:

```python
def gh_pr_review_post(pr_number, comments, dry_run=False) -> list[str]:
    """Post inline review comments via GraphQL addPullRequestReview mutation.
    Returns list of review thread IDs."""

def gh_pr_list_unresolved_threads(pr_number, dry_run=False) -> list[dict]:
    """List all unresolved review threads on a PR."""

def gh_pr_resolve_thread(thread_id, reply=None, dry_run=False) -> None:
    """Resolve a review thread, optionally posting a reply first."""

def gh_pr_checks(pr_number, dry_run=False) -> list[dict]:
    """List CI check runs for a PR with their status and conclusion."""
```

#### Dry-run discipline

Every module short-circuits all side-effectful calls when `dry_run=True`:

```python
if self.options.dry_run:
    self._log("info", f"[DRY RUN] Would post review for PR #{pr_number}")
    return []  # No gh api calls

# Side-effectful calls only in non-dry-run:
gh_pr_review_post(pr_number, comments, dry_run=False)
gh_pr_resolve_thread(thread_id, dry_run=False)
gh pr merge --auto --rebase  # only in ci_driver non-dry-run
```

Claude analysis still runs in dry-run mode — only GitHub API mutations are suppressed.

#### Shell loop integration

`scripts/run_automation_loop.sh` updated to 6-phase loop with `--parallel-repos N`:

```bash
for loop in $(seq 1 "$LOOPS"); do
  for repo in "${REPOS[@]}"; do
    "$PYTHON" -m hephaestus.automation.planner ...         # Phase 1
    "$PYTHON" -m hephaestus.automation.plan_reviewer ...   # Phase 2
    "$PYTHON" -m hephaestus.automation.implementer ...     # Phase 3
    "$PYTHON" -m hephaestus.automation.pr_reviewer ...     # Phase 4
    "$PYTHON" -m hephaestus.automation.address_review ...  # Phase 5
  done
  if [ "$loop" -eq "$LOOPS" ]; then
    for repo in "${REPOS[@]}"; do
      "$PYTHON" -m hephaestus.automation.ci_driver ...     # Phase 6 — final loop only
    done
  fi
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Workers discover their own PR | `_find_pr_for_issue()` called inside each worker thread | Claude could be launched before discovering there's no PR — wasting quota and producing noise | Move `_discover_prs()` to `run()` level as a pre-filter; workers only receive `(issue_number, pr_number)` pairs where PR is confirmed to exist |
| `_address_issue(issue_number, slot_id)` signature | Original signature without `pr_number` | When pre-discovery pattern was added, `pr_number` was needed inside the worker to avoid re-discovery | Changed to `_address_issue(issue_number, pr_number, slot_id)` — all tests updated accordingly |
| Hardcoded `dry_run=False` in thread list call | `gh_pr_list_unresolved_threads(pr_number, dry_run=False)` in address_review | In dry-run mode, the API call still ran — inconsistent dry-run behavior | Pass `dry_run=self.options.dry_run` through to all helper calls |
| Resolving all review threads | Resolved every unresolved thread after Claude ran | Threads Claude did not explicitly address were incorrectly closed | Only resolve threads in Claude's `{"addressed": [...]}` list — all others stay open |

## Results & Parameters

### Files Created

| File | Purpose |
| ------ | --------- |
| `hephaestus/automation/plan_reviewer.py` | Phase 2 — review posted plans, comment on issues |
| `hephaestus/automation/pr_reviewer.py` | Phase 4 — read-only inline PR review via GraphQL |
| `hephaestus/automation/address_review.py` | Phase 5 — resume implementer session to fix review feedback |
| `hephaestus/automation/ci_driver.py` | Phase 6 — 1 CI fix iteration, enable auto-merge |
| `hephaestus/automation/github_api.py` | 4 new helpers: `gh_pr_review_post`, `gh_pr_list_unresolved_threads`, `gh_pr_resolve_thread`, `gh_pr_checks` |
| `scripts/review_plans.py` | CLI entry for phase 2 |
| `scripts/address_review.py` | CLI entry for phase 5 |
| `scripts/drive_prs_green.py` | CLI entry for phase 6 |
| `scripts/run_automation_loop.sh` | Updated 6-phase loop with `--parallel-repos N` |

### Test Coverage

```
251 unit tests passing (all phases)
ruff check: clean
mypy: clean
```

### Session State Files

```
.issue_implementer/
  issue-{N}.json           # IssueImplementer state — contains session_id
  review-{N}.json          # PRReviewer state
  address-{N}.json         # AddressReview state
  ci-{N}.json              # CIDriver state
```

### GraphQL Patterns

```python
# Post inline review — addPullRequestReview mutation
gh api graphql -f query='
  mutation {
    addPullRequestReview(input: {
      pullRequestId: "<pr_node_id>",
      event: COMMENT,
      comments: [{path: "...", line: N, body: "..."}]
    }) { pullRequestReview { id } }
  }'

# Resolve thread — resolveReviewThread mutation
gh api graphql -f query='
  mutation { resolveReviewThread(input: {threadId: "<thread_id>"}) { thread { id } } }'

# Optionally post in-thread reply before resolving
gh api graphql -f query='
  mutation {
    addPullRequestReviewComment(input: {
      inReplyTo: "<thread_first_comment_id>", body: "..."
    }) { comment { id } }
  }'
```

### Key Invariants

| Invariant | Enforcement |
| ----------- | ------------- |
| `address_review` resolves only explicitly-addressed threads | Parse `{"addressed": [...]}` JSON; never resolve threads not in this list |
| `ci_driver` runs exactly 1 fix iteration per PR | No internal retry loop; 1 Claude invocation per `_fix_pr()` call |
| `drive-green` runs only on final loop | `if loop == LOOPS:` gate in `run_automation_loop.sh` |
| `pr_reviewer` is read-only | No `git push`, no `git commit`, no worktree mutation — only `gh api graphql` comment posts |
| Workers never launch for PR-less issues | `_discover_prs()` runs in `run()` before any `executor.submit()` |
| Dry-run suppresses all mutations | Every `gh api`, `git push`, `resolveReviewThread`, `pr merge --auto` call is gated on `not dry_run` |

### Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Session 2026-04-24 — 6-phase pipeline design + implementation | 251 tests pass, ruff + mypy clean; CI not yet run |
