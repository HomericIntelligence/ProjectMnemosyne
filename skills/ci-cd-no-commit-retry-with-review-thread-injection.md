---
name: ci-cd-no-commit-retry-with-review-thread-injection
description: "When an agent-driven CI-fix loop returns from a session without producing a new commit AND the PR's required CI checks are still red, that combination is itself a bug — not a 'do nothing' condition. The correct response is exactly ONE bounded retry on the SAME PR-scoped session with a force-engagement prompt that (1) names the failing required check names verbatim, (2) restates the branch invariant (do not create/switch branches), (3) restates the signed-commit + no-`--no-verify` policy, and (4) prepends ALL unresolved PR review threads (fetched via GraphQL `reviewThreads { isResolved, comments { body, path, line } }`) verbatim — because an unresolved bot or human review comment is usually the actual blocker behind the red CI, and the agent cannot fix what it cannot see. Inject the review-thread block into BOTH the initial CI-fix prompt AND the retry prompt, not just one. Gate the retry on `gh pr checks --required` exit code (don't retry if CI went green via concurrent activity). After the retry, if HEAD still has not advanced, write a `state_dir/repeated-no-commit-<pr>.json` forensics marker and move on — never loop, never open a new PR. Use when: (1) an agent CI-fix driver logs 'agent session produced no new commit (HEAD unchanged at …); skipping push', (2) the same PR is being skipped run after run while its required checks stay red, (3) reviewing/extending a `_run_ci_fix_session` or `drive_prs_green`-style driver, (4) a no-commit honesty guard (#836-style) is already in place but the driver still gives up after one no-commit turn, (5) a PR review bot left an unresolved comment naming the actual blocker and the fix agent never references it."
category: ci-cd
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - automation
  - ci-driver
  - force-engagement-retry
  - no-commit-honesty-guard
  - review-thread-injection
  - agent-contract-violation
  - drive-green
  - same-session-retry
  - gh-pr-checks
  - graphql-review-threads
  - signed-commit-invariant
  - forensics-marker
  - bounded-retry
---

# Agent CI-Fix: Retry Once on No-Commit + Red CI, and Inject Unresolved Review Threads Into the Prompt

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-31 |
| **Objective** | Close the gap between the `#836` no-commit honesty guard (which correctly refuses to push when HEAD did not advance) and the next obvious question: "the agent's contract was violated — what now?" Treat `no-commit + still-red required CI` as a force-engagement trigger that earns exactly one same-session retry with the failing check names named verbatim and all unresolved PR review threads injected into the prompt. |
| **Outcome** | Success — ProjectHephaestus PR #847 shipped `_format_review_threads_block`, `_failing_required_check_names`, `_force_engagement_prompt`, and `_retry_no_commit_once` on `CIDriver`. 18 new unit tests across `TestReviewThreadInjection`, `TestFailingRequiredCheckNames`, `TestForceEngagementPrompt`, and `TestNoCommitRetry`. 2998+ unit tests pass. mypy + ruff clean. Merged via auto-merge (squash). The driver now (a) prepends unresolved threads to both the initial and retry prompts, (b) only retries when `gh pr checks --required` exits non-zero, (c) caps retries at exactly 1, (d) writes `repeated-no-commit-<pr>.json` forensics on the second no-commit, (e) keeps the PR-scoped session_uuid stable across the retry. |
| **Verification** | verified-ci |

## When to Use

Trigger phrases / log lines that MUST surface this skill:

- "agent returned no commit"
- "agent session produced no new commit (HEAD unchanged at …); skipping push"
- "agent didn't engage with CI failure"
- "force-engagement retry prompt"
- "no-commit honesty guard"
- "inject unresolved review threads into prompt"
- "PR reviewer comments invisible to fix agent"
- "drive-green agent contract violation"
- "retry on no-commit + red CI"
- "same-session retry"
- "Previous Turn Produced No Commit"
- "BLOCKED:" reply line from a stuck CI-fix agent

Trigger situations:

- You are reading the `_run_ci_fix_session` (or equivalent) path on a driver that has a no-commit honesty guard already (a la PR #836) but still gives up silently after one no-commit turn.
- A driver run log shows the **same PR** hitting `agent session produced no new commit` on consecutive iterations and the required checks (`lint`, `test-py310`, etc.) are still red on the remote.
- An automation review (audit / PR review / `repo-analyze`) is touching a CI-fix driver and you need to confirm whether the driver injects unresolved review threads into the prompt — most don't.
- A reviewer bot (github-code-quality, CodeRabbit, etc.) or a human left an inline review comment naming the *real* blocker on the PR, but the fix agent keeps "fixing" something else because it only sees the raw CI logs.
- You are designing a driver that resumes the **same PR-scoped session** across iterations (see `automation-session-naming-pr-scoped-not-commit-scoped`) and need to confirm the retry path doesn't accidentally mint a new session_uuid.

## Verified Workflow

### Quick Reference

```python
# Three-call pattern. Place inside _run_ci_fix_session right after the agent returns.

# 1. Build the review-thread block (used by BOTH the initial prompt and the retry).
review_threads_block = self._format_review_threads_block(pr_number)

# 2. Snapshot HEAD before invoking the agent (used by the honesty guard AND retry).
pre_agent_sha = self._head_sha(worktree_path)

# ... invoke the agent with the prompt that PREPENDS review_threads_block ...

# 3. After the agent returns, if HEAD did not advance, do one bounded retry.
if not self._head_advanced(worktree_path, pre_agent_sha, issue_number):
    if not self._retry_no_commit_once(
        issue_number=issue_number,
        pr_number=pr_number,
        worktree_path=worktree_path,
        pr_head_branch=pr_head_branch,
        pre_agent_sha=pre_agent_sha,
        session_id=session_id,   # SAME session — PR-scoped, NOT regenerated
    ):
        return False   # second no-commit → forensics marker written, give up
```

```python
# _retry_no_commit_once: ONE bounded retry, same session. Never loops.

def _retry_no_commit_once(
    self, *, issue_number, pr_number, worktree_path,
    pr_head_branch, pre_agent_sha, session_id,
) -> bool:
    failing = self._failing_required_check_names(pr_number)
    if not failing:
        # CI is actually green now (concurrent activity fixed it). Do NOT perturb.
        return False

    review_threads_block = self._format_review_threads_block(pr_number)
    retry_prompt = self._force_engagement_prompt(
        pr_number=pr_number,
        issue_number=issue_number,
        pr_head_branch=pr_head_branch,
        failing_check_names=failing,
        review_threads_block=review_threads_block,
    )

    # CRITICAL: re-invoke on the SAME session_uuid — same repo, issue, AGENT_CI_DRIVER.
    invoke_claude_with_session(
        repo=repo_slug, issue=issue_number,
        agent=AGENT_CI_DRIVER,
        prompt=retry_prompt,
        session_id=session_id,
        cwd=worktree_path,
    )

    if self._head_advanced(worktree_path, pre_agent_sha, issue_number):
        return True

    # Second no-commit → write forensics marker and stop. Never retry again.
    self._record_repeated_no_commit(
        issue_number=issue_number,
        pr_number=pr_number,
        pr_head_branch=pr_head_branch,
        failing_required_checks=failing,
    )
    return False
```

```python
# The force-engagement prompt content — every requirement must be present.
# See the "Results & Parameters" section for the full literal template.
```

### Detailed Steps

1. **Inject the unresolved review-thread block into BOTH prompts.**
   Use the existing `gh_pr_list_unresolved_threads` helper (already in
   `hephaestus/automation/github_api.py`) — do not roll a new GraphQL query.
   The helper returns the `reviewThreads { isResolved, comments { body, path, line } }`
   shape; the formatter dumps every unresolved thread verbatim, one block per thread,
   with file path + line + comment body. Prepend the block above the existing CI-fix
   instructions in `_run_ci_fix_session`'s initial prompt AND inside `_retry_no_commit_once`'s
   force-engagement prompt. If `gh_pr_list_unresolved_threads` returns empty, the formatter
   must return the empty string (not a header with no body) so the prompt stays clean.

2. **Snapshot HEAD before invoking the agent.**
   `pre_agent_sha = git -C <worktree> rev-parse HEAD`. Save it; the honesty guard and
   the retry both need it.

3. **After the agent returns, gate the retry on TWO conditions.**
   - `_head_advanced(worktree_path, pre_agent_sha, issue_number)` returned `False` (no commit), AND
   - `gh pr checks <pr_number> --required` returned non-zero (still red).

   Skip the retry if either condition is false. If CI went green through concurrent
   activity (someone else fixed the PR, or a flake cleared), retrying just burns tokens.

4. **Build the failing-check list with `gh pr checks <pr> --required`.**
   Parse the `bucket` column (`fail`, `cancel`, `skipping` count as failing; `pass`
   does not). Return the check names — these will be embedded verbatim into the
   retry prompt so the agent knows exactly what to look at. If the list is empty,
   abort the retry (`return False`).

5. **Compose the force-engagement prompt with the literal template below.**
   The prompt MUST:
   - Open with `## Force-Engagement Retry — Previous Turn Produced No Commit`.
   - Quote the failing check names as a bullet list, verbatim from `gh pr checks`.
   - State that returning no commit on red CI is itself a bug.
   - Re-state the branch invariant: NEVER `git checkout -b` / `git switch -c`;
     the fix lands on `{pr_head_branch}` and nowhere else.
   - Re-state the signed-commit + no-`--no-verify` invariant verbatim — even though
     the original prompt already said it, the retry must repeat it. (Empirically,
     no-commit retries that drop this clause produce unsigned commits.)
   - End with an explicit escape hatch: `If after the steps above you still cannot
     produce a commit, reply with a single line BLOCKED: <one-sentence reason> and stop.`
     This stops the agent from looping the retry inside its own session.
   - PREPEND the same `review_threads_block` from step 1.

6. **Re-invoke on the SAME session_uuid.**
   The retry MUST use the existing PR-scoped session id (`session_uuid(repo, issue, AGENT_CI_DRIVER)`).
   See `automation-session-naming-pr-scoped-not-commit-scoped`: regenerating the
   id on retry fragments the transcript and the agent loses context of the first
   no-commit turn. Pass `session_id=session_id` straight through; do not call
   `session_uuid(...)` again.

7. **Cap the retry at exactly 1.**
   `_retry_no_commit_once` returns `True` if HEAD advanced after the retry, `False`
   otherwise. The caller does NOT loop. Two no-commits in a row is the final state.

8. **Write the forensics marker on second no-commit.**
   `state_dir/repeated-no-commit-<pr_number>.json` with the JSON schema in
   Results & Parameters. This is the breadcrumb downstream tools (and operators)
   use to triage stuck PRs. The marker is also what stops the next loop iteration
   from re-attempting the same PR for the same head SHA — `_run_ci_fix_session`
   should check for the marker and skip if it exists for the current PR head SHA.

9. **Do NOT open a new PR.**
   The retry never calls `gh pr create`. The fix has to land on the existing PR
   so its review history, `Closes #N` link, and arming state stay intact. If the
   second no-commit fires, the marker is written and the loop moves on — the
   operator (or the next loop run, after a code change) is responsible for
   unblocking the PR.

10. **Pin the contract with unit tests.** Mirror the PR #847 test layout:
    - `TestReviewThreadInjection` — empty list returns `""`; non-empty list
      formats one block per thread with `path:line` and comment body;
      the formatter is called with the same `pr_number` in both prompt paths.
    - `TestFailingRequiredCheckNames` — `gh pr checks` JSON with mixed
      `pass`/`fail`/`cancel`/`skipping` rows returns only the failing names;
      empty JSON returns `[]`.
    - `TestForceEngagementPrompt` — asserts every required clause is present:
      the title line, the failing check names, the branch invariant, the
      signed-commit invariant, the `BLOCKED:` escape hatch, the prepended
      review-thread block.
    - `TestNoCommitRetry` — green CI on retry-entry returns `False` without
      invoking the agent; red CI invokes the agent with `session_id=session_id`
      unchanged; second no-commit writes the forensics JSON to `state_dir`
      with the correct schema; HEAD-advance on retry returns `True` without
      writing the marker.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Push anyway on no-commit | Pre-#836 behavior: `git push --force-with-lease HEAD:branch` returns 0 silently when HEAD already matches origin | Driver logged "pushed CI fixes" for sessions that committed nothing — silent lie to operators and downstream consumers of the run log | #836 honesty guard: snapshot HEAD pre/post agent and refuse to push when they are equal (predecessor skill `automation-ci-driver-honest-success-path-no-silent-noop`) |
| Give up after one no-commit | Post-#836 behavior: log "skipping push and treating iteration as failed", `return False`, move to next iteration | Agent's contract was violated; nobody asked WHY. Same prompt every run on the same red CI produces the same no-commit. ProjectNestor run `20260531T190615Z` had 4 PRs (#49, #43, #40, #41) stuck this way for multiple consecutive runs | Treat `no-commit + still-red required CI` as a force-engagement trigger, not a stop. Earn one bounded retry with a stronger prompt. |
| Retry on ANY no-commit | Always retry whether or not the required checks are still red | Wasted tokens on PRs whose CI actually passed through concurrent activity (someone else pushed a fix, or a flake cleared). The retry would then "fix" a green PR and possibly introduce regressions | Gate the retry on `gh pr checks --required` exit code; if it's clean, return `False` from the retry path without invoking the agent |
| Retry with the same prompt | Re-invoke `claude` with the *original* CI-fix prompt unchanged | Same prompt, same context window (same session_id resumes the prior transcript), almost always the same no-commit. The agent has nothing new to chew on | The retry prompt MUST be different from the initial prompt: name the failing checks verbatim, state explicitly that the previous turn violated the contract, repeat the signed-commit + branch invariants |
| Ignore PR review threads | Build the prompt from `ci_logs` alone | Bot (github-code-quality, CodeRabbit) or human reviewers leave the real blocker in an unresolved review thread. The fix agent only sees raw CI logs and "fixes" something tangential. The PR stays red forever | Fetch unresolved `reviewThreads { isResolved, comments { body, path, line } }` via the existing GraphQL helper and inject them verbatim into BOTH the initial and the retry prompts |
| Inject review threads only into the retry | Skip the threads on the initial prompt, only show them after the first no-commit | The first iteration's no-commit is exactly the failure this skill is trying to prevent. Half the time the initial prompt with threads is enough; without them you guarantee one wasted iteration | Inject in BOTH places. The retry is a backstop, not the primary delivery mechanism |
| Loop the retry until commit or quota | No bound on retries inside `_retry_no_commit_once`; loop until either HEAD advances or some `max_retries` quota is exhausted | Burns tokens on a genuinely stuck PR; defers the operator decision indefinitely | Exactly ONE retry. Two no-commits in a row is a hard stop. Write the forensics marker and move on. Let the next loop run (with a different code state) try again. |
| Open a new PR on second failure | "Fix-forward" by closing the stuck PR and opening a fresh one from a clean branch | Loses the existing PR's review history (resolved threads, prior commit graph), breaks the `Closes #N` link, and orphans the arming-state record (see `automation-learn-on-merge-per-issue-arming-state`) | Always re-use the existing PR + its head branch. Never call `gh pr create` from the retry path. The fix MUST land on `{pr_head_branch}`. |
| Mint a new session_uuid for the retry | Call `session_uuid(repo, issue, AGENT_CI_DRIVER, "retry")` or similar to "start fresh" | A new session means the retry agent loses the prior turn's context. The prompt now has to re-establish state from scratch, defeating the point of the same-session retry | Pass the original `session_id` through unchanged. The PR-scoped invariant from `automation-session-naming-pr-scoped-not-commit-scoped` MUST hold here. |
| Drop the signed-commit reminder from the retry prompt | "The initial prompt already said it, no need to repeat" | Empirically, retry prompts that omit the signed-commit + no-`--no-verify` clause produce unsigned commits — possibly because the longer transcript pushes the original instructions out of the agent's attention window | Repeat the invariant verbatim in every prompt the driver constructs. Cost: a few tokens. Benefit: no rejected pushes. |
| Drop the branch invariant from the retry prompt | "It's obvious the agent should stay on the PR's head branch" | Without explicit `do NOT run git checkout -b / git switch -c` instructions, the retry agent has occasionally branched off, committed the fix, and left HEAD on a new branch — which then doesn't get pushed | Restate the branch invariant in every prompt. Same reasoning as the signed-commit invariant. |
| Skip writing the forensics marker | "The log line is enough; ops can grep" | The next loop run has no way to know the PR has already used its retry quota for this head SHA. Without the marker, the loop wastes another invocation on the same stuck PR | Write `state_dir/repeated-no-commit-<pr>.json` on second no-commit. Make `_run_ci_fix_session` check for the marker (keyed by PR + head SHA) and skip if present. |

## Results & Parameters

### Force-engagement prompt template (verbatim from PR #847)

```text
## Force-Engagement Retry — Previous Turn Produced No Commit

You just returned from a CI-fix session for PR {pr} (issue {issue}) WITHOUT
producing a new commit on branch `{pr_head_branch}`. The required CI checks
below are STILL failing on the remote:

{failing_check_names_bulleted}

Returning no commit when required checks are still red is itself a bug — either
fix the code so the failing checks pass, or, if no fix is possible, write a
commit that documents the blocker in the PR description and references the
upstream cause.

Required behaviour:
1. Re-read the failing check logs for the names listed above.
2. Make the minimal change that addresses each failure.
3. Run `pixi run python -m pytest tests/ -v` and `pre-commit run --all-files`
   locally to verify before committing.
4. **Every commit MUST be cryptographically signed (`git commit -S`).**
   NEVER use `--no-verify`. The repository's CI gate rejects unsigned commits
   and any commit that bypassed pre-commit hooks.
5. Do NOT run `git checkout -b`, `git switch -c`, or any command that creates
   or switches branches — the fix has to land on `{pr_head_branch}`.

If after the steps above you still cannot produce a commit, reply with a single
line `BLOCKED: <one-sentence reason>` and stop.
```

Where:

- `{pr}`, `{issue}`, `{pr_head_branch}` are the PR number, issue number, and head branch name.
- `{failing_check_names_bulleted}` is the output of `_failing_required_check_names`,
  one check name per line, prefixed with `- `. Example:

  ```text
  - lint
  - test-py310
  ```

- The `review_threads_block` from `_format_review_threads_block(pr_number)` is
  PREPENDED above this entire template (NOT inlined into a step).

### `gh_pr_list_unresolved_threads` GraphQL query shape

The helper already exists in `hephaestus/automation/github_api.py`. The query shape it issues:

```graphql
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          comments(first: 50) {
            nodes {
              body
              path
              line
            }
          }
        }
      }
    }
  }
}
```

Filter for `isResolved == false` client-side. `_format_review_threads_block` then
emits, for each unresolved thread, a block of the form:

```text
## Unresolved Review Thread — {path}:{line}

{comment_body}

---
```

If the list is empty, return `""` (NOT a header with no body).

### Failing-required-check parser

`_failing_required_check_names(pr_number)`:

```bash
gh pr checks <pr_number> --required --json name,bucket
```

Returns the list of `name`s where `bucket` is in `{"fail", "cancel", "skipping"}`.
`bucket == "pass"` is excluded; `bucket == "pending"` is excluded (treat in-flight
as "not failing yet"). Exit code 0 with empty array means CI is clean — abort the retry.

### Forensics marker JSON schema

Path: `state_dir/repeated-no-commit-<pr_number>.json`

```json
{
  "issue_number": 41,
  "pr_number": 83,
  "pr_head_branch": "41-auto-impl",
  "failing_required_checks": ["lint", "test-py310"],
  "recorded_at": "2026-05-31T19:37:30Z"
}
```

Fields:

- `issue_number` — the closed issue number (from the PR body's `Closes #N`)
- `pr_number` — the PR number
- `pr_head_branch` — the PR's head ref (e.g. `41-auto-impl`)
- `failing_required_checks` — sorted list of check names that were still red on second no-commit
- `recorded_at` — UTC ISO-8601 timestamp with `Z` suffix

`_run_ci_fix_session` should check for `state_dir/repeated-no-commit-<pr>.json`
at entry and short-circuit (skip the PR for this iteration) if it exists AND
the PR's current head SHA matches the SHA that was current when the marker
was written. Re-arming requires a new commit landing on the PR head branch
(operator pushes a fix, or the implementer agent on a later loop produces one).

### Cross-references to companion skills

- **`automation-ci-driver-honest-success-path-no-silent-noop`** (PR #836) — the
  predecessor. That skill installs the HEAD-snapshot honesty guard; this skill
  is the follow-up "OK, you caught the lie — now what?" answer.
- **`automation-learn-on-merge-per-issue-arming-state`** (PR #840) — uses the
  same `state_dir` convention as this skill's `repeated-no-commit-<pr>.json`
  marker. Reuse the existing `state_dir` resolution; do not add a parallel
  directory.
- **`automation-session-naming-pr-scoped-not-commit-scoped`** (PR #845) — the
  retry MUST stay on the same PR-scoped `session_uuid(repo, issue, AGENT_CI_DRIVER)`.
  This skill is downstream of #845's invariant; violating it (e.g., by passing
  a different `session_id` to the retry's `invoke_claude_with_session`) regenerates
  the session and the retry agent loses the first turn's context.

### Concrete failure evidence (motivating run)

ProjectNestor run `20260531T190615Z` log shows 4 issues stuck on
`agent session produced no new commit (HEAD unchanged at …); skipping push
and treating iteration as failed`:

| Issue | PR head SHA at no-commit |
|-------|--------------------------|
| #49   | `66871883` |
| #43   | `5d95f38c` |
| #40   | `d9d5bfd2` |
| #41   | `752ed43f` |

Pre-#847 behavior: the driver logged the warning and moved on; on the next
loop run, the same PRs hit the same no-commit at the same SHA, because nothing
changed in the prompt or the input. Post-#847 behavior: each PR earns one
force-engagement retry with the failing check names + unresolved review
threads in the prompt; if that second attempt also no-commits, the forensics
marker is written and the PR is skipped until its head SHA advances.
