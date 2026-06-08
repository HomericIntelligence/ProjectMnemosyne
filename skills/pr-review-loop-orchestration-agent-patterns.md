---
name: pr-review-loop-orchestration-agent-patterns
description: "Use when: (1) building or debugging a Python implement-review loop where an LLM sub-agent reviews a PR and a fixer agent addresses inline comments, (2) a review loop resolves threads even though no commit was produced — resolution must be gated on a real commit not the model self-report, (3) a loop ends AMBIGUOUS or NO-GO too fast before ever earning an explicit GO verdict, (4) LLM or agent-generated inline PR review comments are rejected by GitHub (HTTP 422) because they do not lie on a changed diff hunk, (5) an agent-driven CI-fix session produces no commit and the PR stays red; the correct response is a single bounded retry with unresolved review threads injected verbatim, (6) a review fix plan file concludes no changes are needed and the automation should self-cancel without opening a new PR, (7) a feature-dev:code-reviewer sub-agent cannot execute shell commands and cannot post gh pr review — wrong agent type was chosen, (8) a GitHub GraphQL PR-review mutation field selection is wrong and the automation loop fails on every call with Field X does not exist, (9) pre-commit must cover the full PR diff from the merge-base not just the most-recent-edit files before pushing"
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: pr-review-loop-orchestration-agent-patterns.history
tags:
  - implement-review-loop
  - review-thread-resolution
  - evidence-based-resolution
  - commit-gated-progress
  - verdict-go-convergence
  - inline-comment-diff-hunk
  - "422"
  - unprocessable-entity
  - no-commit-retry
  - review-thread-injection
  - force-engagement-retry
  - agent-type-selection
  - feature-dev-code-reviewer
  - general-purpose
  - graphql-field-validation
  - schema-introspection
  - addPullRequestReviewThreadReply
  - self-cancelling-review-plan
  - pre-commit-merge-base-diff
  - graphql-review-threads
  - homericintelligence
---

# PR Review Loop Orchestration and Agent Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Build and debug a Python implement-review loop that drives LLM sub-agents to review a PR and fix its inline comments, converging on an EVIDENCE-BASED `Verdict: GO`. Covers: commit-gated thread resolution, inline-comment diff-hunk (422) validation, one-shot no-commit retry with unresolved review threads injected, agent-type selection for review tasks, GraphQL field/input validation for PR-review mutations, self-cancelling review plans, and full merge-base pre-commit scope. |
| **Outcome** | Merged across multiple ProjectHephaestus PRs (commit-gate + verdict-GO convergence #1084; inline-comment 422 validation #1043; no-commit retry + thread injection #847; GraphQL field/input validation #906/#1006) plus ProjectOdyssey and gh-tidy upstream review rounds. |
| **Verification** | verified-ci |

## When to Use

- You are building or auditing a Python loop where one LLM sub-agent reviews a PR and another fixes the inline review comments, and you need the contract for "what counts as progress" and "who resolves threads."
- A review loop resolved a thread but no commit was produced (the fixer replied "documented as a limitation" with a clean worktree).
- A loop ends NO-GO / AMBIGUOUS "too fast" before ever earning a `Verdict: GO`.
- A runtime log shows `gh: Unprocessable Entity (HTTP 422)` on a `POST .../pulls/{n}/reviews` because an LLM-generated inline comment is off-hunk.
- An agent CI-fix driver logs "agent session produced no new commit (HEAD unchanged …); skipping push" while required checks stay red.
- A `.claude-review-fix-*.md` plan says "implement all fixes" but its inner Fix Plan concludes no changes are required.
- A `feature-dev:code-reviewer` sub-agent returns "I cannot run shell commands. Available tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop."
- A `gh api graphql` PR-review mutation fails on every call with `Field 'X' doesn't exist on type 'Y'` or `InputObject '<Input>' doesn't accept argument '<arg>'`.
- You want a comprehensive multi-specialist PR review filed as structured GitHub review comments.

## Verified Workflow

### Quick Reference

```python
# ── Review loop progress + convergence contract ───────────────────────────
addressed = run_fixer_agent(...)          # model self-report (untrusted alone)
committed = _commit_if_changes(worktree)  # True only if HEAD advanced
made_progress = addressed and committed   # BOTH required; clean worktree = no progress
if reviewer_verdict == "GO":              # converge ONLY on the literal GO token
    converge()                            # "zero threads" + AMBIGUOUS/NO-GO is NOT GO
# Thread RESOLUTION lives in the reviewer, never the fixer:
for thread in prior_threads:
    if validator_says_addressed_by_diff(thread, new_diff):
        resolve(thread.id)                # match by thread id, NOT (path, line)
    else:
        reopen_as_new_thread(thread)      # re-open OVERRIDES a stale GO
```

```text
# ── Inline-comment 422 validation pipeline ────────────────────────────────
full_diff = gh pr diff <n>            # NOT the 8000-char model context
accepted  = parse(full_diff)          # {path -> {(line, side)}}
kept      = [c for c in comments if (c.line, c.side) in accepted[c.path]]
if not full_diff: return comments     # FAIL OPEN on empty/unfetchable diff
POST review(body, event, comments=kept)   # summary-only OK if kept == []
# RIGHT side = '+'/context numbered in NEW file; LEFT = '-'/context in OLD file.
# Hunk header @@ -oldStart[,oldLen] +newStart[,newLen] @@  (",len" OPTIONAL)
```

```bash
# ── GraphQL: validate against the LIVE schema before shipping ──────────────
gh api graphql -f query='{ __type(name: "PullRequestReviewComment") { fields { name } } }'
gh api graphql -f query='{ __type(name: "AddPullRequestReviewThreadReplyInput") { inputFields { name } } }'
# Two error signatures, one discipline:
#   wrong OUTPUT field  -> Field 'X' doesn't exist on type 'Y'
#   wrong mutation NAME -> InputObject '<Input>' doesn't accept argument '<arg>'
#                          + Variable $X is declared by <Mutation> but not used
```

```text
# ── Agent type selection ──────────────────────────────────────────────────
Need to write back (post review / create issue / commit / push)?
  YES -> general-purpose         (has Bash/Edit/Write; prompt includes the gh command)
  NO  -> feature-dev:code-reviewer (read-only; forbid gh syntax, return VERDICT + BODY)
```

### Detailed Steps

#### Evidence-based thread resolution

Gate "progress" on a real commit (`addressed AND committed`). `_commit_if_changes`
returns `True` only if HEAD advanced. The fixer's self-reported "addressed" list is
untrusted on its own — a clean worktree with prose replies (e.g., "documented as a
limitation", "this is intended") must count as ZERO progress and must NOT resolve any
thread.

Move thread RESOLUTION into the reviewer/validator on the NEXT pass. The fixer agent
ONLY edits, commits, and pushes; it MUST NOT call the GitHub resolve mutation. On the
next review pass, a fresh READ-ONLY sub-agent compares each prior thread against the new
diff and:

- resolves a thread ONLY if the diff genuinely addressed it (evidence-based);
- re-opens (as a NEW inline thread — GitHub has no "unresolve" mutation) every thread the
  diff did NOT address. A re-open OVERRIDES a stale GO so the loop keeps going.

Converge ONLY on an explicit `Verdict: GO`. Do not converge on "reviewer posted zero
threads" — a zero-thread pass with verdict AMBIGUOUS or NO-GO ends the loop too fast.
Parse the verdict explicitly (last line, not substring) and require the literal `GO`.

Match prior threads for resolution on the thread `id`, NOT `(path, line)` — two threads
can share a line (original + a re-open) and path normalization drifts across hunks. When
editing an existing comment, FETCH+CONCATENATE its body first: `updatePullRequestReviewComment`
REPLACES, it does not append. FENCE all untrusted comment text before interpolating into a
prompt — first-line truncation is not injection-safe.

Severity-tag every inline comment (`critical | major | minor | nitpick`) and SUPPRESS
nitpick by default; a `--nitpick` flag opts back in. Per-comment dispatch: classify each
comment's fix difficulty with a cheap sub-agent, render `@ <file> Line <#> - <difficulty> - <desc>`,
dispatch ONE sub-agent per comment (SERIALIZE same-file comments), tier models simple→haiku /
medium→sonnet / hard→opus. A `state:skip` label (name sourced from the single-source
`state_labels` module, auto-provisioned, honored on issue OR PR) skips all phases — gate the
auto-apply on TRUE iteration exhaustion, not on a single iteration-0 non-GO.

#### Inline-comment diff-hunk 422 validation

GitHub rejects the ENTIRE review with HTTP 422 if ANY single inline comment points at a
line not in the diff hunk; the in-loop reviewer then logs a spurious `Verdict=NOGO Grade=F`.
Before POSTing:

1. Fetch the FULL diff (`gh pr diff <n>`), not the truncated (8000-char) model context —
   the model can cite real-but-out-of-hunk lines on large diffs.
2. Parse the unified diff once into accepted `(line, side)` positions per file. `RIGHT` =
   added (`+`) and context (` `) lines numbered in the NEW file; `LEFT` = removed (`-`) and
   context lines numbered in the OLD file. Parse the hunk header defensively — the `,len`
   part is optional (`@@ -1 +1 @@`).
3. Keep comments whose `(path, line, side)` is in the accepted set; DROP + LOG the rest at
   WARNING so the loss is visible.
4. Still POST the summary review with whatever remains (empty `comments` array is fine).
5. FAIL OPEN: if the diff is empty or could not be fetched, return comments UNCHANGED — a
   possible 422 beats guaranteed silent feedback loss.

Add tests the post-reviews path lacked: out-of-hunk filtered while in-hunk survives;
all-out-of-hunk → summary-only POST; empty diff → fail open; pure hunk-parser unit tests
for RIGHT/LEFT/context numbering.

#### No-commit retry with thread injection

Treat `no-commit + still-red required CI` as a force-engagement trigger, not a stop. Earn
exactly ONE bounded same-session retry:

1. Snapshot HEAD before invoking the agent (`pre_agent_sha = git -C <wt> rev-parse HEAD`).
2. After the agent returns, gate the retry on BOTH: HEAD did not advance, AND
   `gh pr checks <pr> --required` exits non-zero. If CI went green via concurrent activity,
   do NOT retry (it would "fix" a green PR).
3. Build the failing-check list from `gh pr checks <pr> --required --json name,bucket` —
   `bucket` in `{fail, cancel, skipping}` is failing; `pass`/`pending` are not. Empty → abort.
4. Compose a force-engagement prompt that: opens with `## Force-Engagement Retry — Previous
   Turn Produced No Commit`, names the failing checks verbatim as a bullet list, states that
   no-commit on red CI is itself a bug, restates the branch invariant (NEVER `git checkout -b`/
   `git switch -c`; land on `{pr_head_branch}`), restates the signed-commit + no-`--no-verify`
   invariant verbatim, and ends with `BLOCKED: <reason>` escape hatch.
5. PREPEND the unresolved-review-thread block (via the existing `gh_pr_list_unresolved_threads`
   GraphQL helper) into BOTH the initial AND the retry prompt — a bot/human review thread is
   usually the real blocker the fix agent cannot otherwise see.
6. Re-invoke on the SAME PR-scoped `session_uuid` (do NOT mint a new one — the retry agent
   would lose the prior turn's context).
7. Cap at exactly 1 retry. On the second no-commit, write `state_dir/repeated-no-commit-<pr>.json`
   forensics marker and stop. NEVER loop, NEVER `gh pr create` — the fix must land on the
   existing PR head branch.

#### Agent-type selection

The `feature-dev:code-reviewer` toolset is exactly Read, WebFetch, WebSearch, Grep, Glob,
TaskStop — it has NO Bash/Edit/Write and CANNOT execute `gh pr review`. Detection signatures
in sub-agent output: "I cannot run shell commands", "Available tools: Read, WebFetch,
WebSearch, Grep, Glob, TaskStop", "the review body is composed below, ready for the
orchestrator to post".

- If write-back is required (post review, create issue, push): use `general-purpose`; the
  prompt MUST include the explicit `gh pr review N --repo OWNER/NAME [--approve|--request-changes|--comment] --body "$BODY"`.
- If analysis-only: use `feature-dev:code-reviewer`; the prompt MUST forbid `gh` syntax,
  tell the agent it has no Bash, and require it to return `VERDICT:` + `BODY:` deterministically.
  The orchestrator then wraps the body and posts it itself.

Probe ONE agent's toolset before fanning out to N. A prompt cannot grant tools the agent
type does not have — capability is enforced by the harness at registration. For comprehensive
reviews, a `code-review-orchestrator`-style agent routes to specialist reviewers (test, language,
implementation, docs, memory-safety, algorithm) and aggregates Priority 1/2/3 findings.

#### GraphQL field validation

A field selection or input argument has NO compile-time check; an invalid one ships
silently and fails on EVERY call. Before shipping any raw `gh api graphql` PR-review
query/mutation, introspect the LIVE schema:

```bash
gh api graphql -f query='{ __type(name: "TYPE") { fields { name } } }'          # output fields
gh api graphql -f query='{ __type(name: "<Mutation>Input") { inputFields { name } } }'  # input args
```

Two distinct error signatures, one discipline:

- Wrong OUTPUT field → `Field '<f>' doesn't exist on type '<T>'` (e.g. selecting
  `pullRequestReviewThread` on a `PullRequestReviewComment` — that field does not exist;
  return only `pullRequestReview { id }` and resolve threads via a separate
  `pullRequest.reviewThreads` query).
- Wrong mutation NAME → `InputObject '<Input>' doesn't accept argument '<arg>'` +
  `Variable $X is declared by <Mutation> but not used` (e.g. `addPullRequestReviewComment`
  has no `pullRequestReviewThreadId` — the correct reply mutation is
  `addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId, body}) { comment { id } }`).

Never assume a reverse child→parent edge exists; if `Child.parent` is absent, fetch via
`Parent.children` and filter. Treat HTTP 200 with a top-level `errors` array as a FAILURE
(a bare exit-code check misses it). Give every raw-query function a direct unit test that
asserts the query string and parsing — boundary mocks are what let broken queries ship.

#### Self-cancelling review plan and pre-push diff scope

When a `.claude-review-fix-*.md` file's outer wrapper says "implement all fixes" but the
inner Fix Plan concludes "No fixes are required / the PR is correct and complete" (failing
CI is pre-existing on `main`, `git status` clean, only the review file untracked), the plan
is self-cancelling: make NO changes, do NOT manufacture a commit, and report that the branch
is already up to date. Trust the inner plan, not the outer shell.

Before pushing, run pre-commit/validation over the FULL PR diff from the merge-base
(`git diff origin/main...HEAD`), not just the most-recently-edited files — a fix can be
clean while an earlier-touched file in the same PR still fails the gate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Resolve threads from the fixer's self-reported "addressed" list | Loop resolved threads whenever the fixer said it addressed them — even with a clean worktree and prose-only replies | Threads got resolved while NO commit was produced; the diff was unchanged | Gate resolution on a real commit: `made_progress = addressed and committed`. Never trust the model's self-report alone (PR #1084). |
| Converge when the reviewer posts zero threads | Loop terminated on "zero new threads" regardless of verdict | Ended AMBIGUOUS/NO-GO too fast, before ever earning a GO | Require an explicit `Verdict: GO` to converge; zero threads != GO (PR #1084). |
| Let the fixer agent resolve its own threads | Fixer both edited code AND called the resolve mutation | The fixer has every incentive to declare victory; not evidence-based | Move resolution to a fresh READ-ONLY reviewer on the next pass; fixer only edits+commits+pushes (PR #1084). |
| Match prior threads on `(path, line)` | Validator paired a prior thread to the new diff by file+line | Two threads can share a line; path normalization drifts across hunks → wrong thread resolved | Match on the thread `id`; echo it back through the validation prompt and payload. |
| Edit an existing comment via `updatePullRequestReviewComment` with only its node id | Fetched only the node id, then called the update mutation | The mutation REPLACES the body — it silently destroys the original comment | FETCH the existing body first and CONCATENATE; the comment index must return the body. |
| Post inline comments unvalidated | Mapped LLM comment dicts straight into the `POST .../reviews` payload with no diff check | GitHub 422s the ENTIRE review if ANY comment is off-hunk; loop logged spurious `Verdict=NOGO Grade=F` | Validate every `(path, line, side)` against the FULL diff before POST (PR #1043). |
| Validate against the truncated context diff | Reused the 8000-char model-context diff as the accepted-positions source | On large PRs truncation omits real hunks, wrongly dropping valid comments | Validate against the full `gh pr diff`, not the model's truncated context. |
| Fail closed on empty diff | Dropped all comments when the diff was empty/unavailable to be "safe" | A transient fetch hiccup silently discarded all reviewer feedback | FAIL OPEN: return comments unchanged when the diff cannot be fetched. |
| Give up after one no-commit | Logged "skipping push, iteration failed" and moved to the next PR | Same prompt on the same red CI reproduces the same no-commit run after run | Treat no-commit + red required CI as a force-engagement trigger; earn one bounded retry (PR #847). |
| Retry on ANY no-commit | Always retried regardless of whether required checks were still red | Wasted tokens "fixing" PRs whose CI passed via concurrent activity, risking regressions | Gate the retry on `gh pr checks --required` exit code. |
| Retry with the same prompt / a new session_uuid | Re-invoked the original prompt, or minted a fresh session id to "start over" | Same prompt+context → same no-commit; a new session loses the prior turn's context | Retry prompt must differ (name failing checks, restate invariants) and reuse the SAME PR-scoped session id. |
| Ignore PR review threads in the prompt | Built the prompt from `ci_logs` alone | The real blocker is often an unresolved bot/human review thread the fix agent never sees | Inject unresolved `reviewThreads { isResolved, comments { body, path, line } }` verbatim into BOTH the initial and retry prompts. |
| Open a new PR / loop the retry on second failure | Closed the stuck PR for a fresh one, or looped the retry until quota | Loses review history + `Closes #N` link; burns tokens on a genuinely stuck PR | Exactly ONE retry; on second no-commit write `repeated-no-commit-<pr>.json` and stop. Never `gh pr create` from the retry path. |
| Prompt `feature-dev:code-reviewer` with `gh pr review` action verbs | Dispatched 11 read-only agents expecting them to post reviews | The type has NO Bash; all 11 returned "I cannot run shell commands"; orchestrator posted all 11 manually | Use `general-purpose` for write-back; probe one agent's toolset before fanning out to N. |
| Tell `feature-dev:code-reviewer` to "use Bash anyway" | Added "you have Bash, use it" to the prompt | Toolset is harness-enforced at registration; the agent still reports no Bash | A prompt cannot grant tools the agent type lacks. |
| Select a non-existent GraphQL output field | `addPullRequestReview` selected `pullRequestReviewThread { id isResolved }` on a `PullRequestReviewComment` | That output field does not exist; the mutation failed on EVERY call (219 identical failures); no in-loop review posted | Introspect `__type { fields { name } }` against the live schema; return only `pullRequestReview { id }` (PR #906). |
| Reply with the wrong mutation name | `gh_pr_resolve_thread` used `addPullRequestReviewComment(input: {pullRequestReviewThreadId, body})` | `AddPullRequestReviewCommentInput` has no `pullRequestReviewThreadId` → `InputObject ... doesn't accept argument` + `Variable $threadId declared but not used` | Introspect the Input type's `inputFields`; the correct mutation is `addPullRequestReviewThreadReply` (PR #1006). |
| Trust `gh api graphql` exit code alone | Relied on exit 0 to mean success | `gh api graphql` returns HTTP 200 with a top-level `errors` array on a failed op | Surface the `errors` array from the JSON; do not trust the exit code alone. |
| Manufacture a commit for a self-cancelling plan | Considered committing a no-op when "implement all fixes" was the outer instruction | Would create spurious history and confuse reviewers; the inner plan said "no fixes required" | Read the entire plan body; if it cancels itself, do nothing and report the branch is already complete. |
| `if git branch --list "$branch"; then` (bash review trap) | Used the exit code of `git branch --list` to test branch existence | `git branch --list` always exits 0; the exit code reflects execution, not a match | Test the OUTPUT: `[[ -n "$(git branch --list "$branch")" ]]`. |

## Results & Parameters

### Progress / convergence contract (SHIPPED, verified-ci)

| Rule | Implementation | Why |
|------|----------------|-----|
| Progress requires a commit | `made_progress = addressed and committed`; `_commit_if_changes` returns bool (True iff HEAD advanced) | A clean worktree with prose replies is NOT progress |
| Convergence requires explicit GO | parse reviewer output, require literal `Verdict: GO` (last line, not substring) | "zero threads" + AMBIGUOUS/NO-GO is not success |
| Fixer never resolves | resolution mutation lives in the reviewer/validator on the next pass | evidence-based; fixer can't self-declare victory |
| Reviewer resolution is diff-evidence-based, matched by thread `id` | resolve addressed threads, re-open (new thread) the rest | re-open OVERRIDES a stale GO; GitHub has no unresolve mutation |

### `--nitpick` severity model and per-comment dispatch

```text
Reviewer tags every inline comment: critical | major | minor | nitpick
  Default:    suppress nitpick-severity comments
  --nitpick:  re-enable them
Per-comment dispatch:
  1. cheap sub-agent classifies each comment's fix difficulty
  2. todo list:  @ <file> Line <#> - <difficulty> - <description>
  3. ONE sub-agent per comment; SERIALIZE same-file comments; parallelize across files
  4. tier model:  simple -> haiku   medium -> sonnet   hard -> opus
```

### Inline-comment 422 validation

```text
Endpoint:   POST /repos/{owner}/{repo}/pulls/{n}/reviews   (gh api -X POST)
Failure:    gh: Unprocessable Entity (HTTP 422)  (any one off-hunk comment poisons all)
Side map:   RIGHT = '+'/context numbered in NEW file ;  LEFT = '-'/context in OLD file
Hunk hdr:   @@ -oldStart[,oldLen] +newStart[,newLen] @@   (",len" optional — parse defensively)
Invariant:  FAIL OPEN — never drop comments because the diff could not be fetched
```

### Force-engagement retry prompt template (verbatim from PR #847)

```text
## Force-Engagement Retry — Previous Turn Produced No Commit

You just returned from a CI-fix session for PR {pr} (issue {issue}) WITHOUT
producing a new commit on branch `{pr_head_branch}`. The required CI checks
below are STILL failing on the remote:

{failing_check_names_bulleted}

Returning no commit when required checks are still red is itself a bug.

Required behaviour:
1. Re-read the failing check logs for the names listed above.
2. Make the minimal change that addresses each failure.
3. Run the local test + pre-commit gates to verify before committing.
4. **Every commit MUST be cryptographically signed (`git commit -S`).**
   NEVER use `--no-verify`.
5. Do NOT run `git checkout -b` / `git switch -c` — the fix lands on `{pr_head_branch}`.

If you still cannot produce a commit, reply with a single line
`BLOCKED: <one-sentence reason>` and stop.
```

The `review_threads_block` from `_format_review_threads_block(pr_number)` is PREPENDED above
this entire template. `_failing_required_check_names` parses `gh pr checks <pr> --required
--json name,bucket` and returns names whose `bucket` ∈ `{fail, cancel, skipping}`.

### Forensics marker JSON (`state_dir/repeated-no-commit-<pr>.json`)

```json
{
  "issue_number": 41,
  "pr_number": 83,
  "pr_head_branch": "41-auto-impl",
  "failing_required_checks": ["lint", "test-py310"],
  "recorded_at": "2026-05-31T19:37:30Z"
}
```

`_run_ci_fix_session` checks for this marker at entry and skips the PR if it exists AND the
PR head SHA still matches — re-arming requires a new commit on the head branch.

### Agent type capability matrix (verified 2026-05-31)

| Agent type | Read | Grep | Glob | WebFetch | WebSearch | Bash | Edit | Write | TaskStop |
|---|---|---|---|---|---|---|---|---|---|
| `feature-dev:code-reviewer` | yes | yes | yes | yes | yes | NO | NO | NO | yes |
| `general-purpose` | yes | yes | yes | yes | yes | yes | yes | yes | yes |

### GraphQL introspection + corrected PR-review mutations

```bash
gh api graphql -f query='{ __type(name: "PullRequestReviewComment") { fields { name } } }'
gh api graphql -f query='{ __type(name: "AddPullRequestReviewThreadReplyInput") { inputFields { name } } }'
gh api graphql -f query='{ __type(name: "AddPullRequestReviewThreadReplyPayload") { fields { name } } }'
```

```graphql
# Reply to a review thread (right NAME + right Input + valid leaf):
mutation AddReply($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: $threadId, body: $body
  }) { comment { id } }
}
# resolveReviewThread(input: { threadId: $threadId }) is the follow-up (already correct).

# Post a review (select ONLY a field that exists):
mutation {
  addPullRequestReview(input: {
    pullRequestId: $prId, event: COMMENT, body: $body, comments: $comments
  }) { pullRequestReview { id } }   # PullRequestReview has `id`, NOT `databaseId`
}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1084 (closes #1083) | Commit-gated progress, `Verdict: GO` convergence, reviewer-side evidence-based resolution, `state:skip` vocabulary, `--nitpick` suppression, per-comment tiered dispatch |
| ProjectHephaestus | PR #1043 (closes #1039) | Inline-comment diff-hunk 422 validation; full-diff hunk parser; fail-open on empty diff; new 422-path tests |
| ProjectHephaestus | PR #847 | `_format_review_threads_block`, `_failing_required_check_names`, `_force_engagement_prompt`, `_retry_no_commit_once`; 18 new tests; forensics marker |
| ProjectHephaestus | PR #906 (closes #905) / PR #1006 (closes #999) | GraphQL field + input-argument validation; corrected `addPullRequestReview` selection and `addPullRequestReviewThreadReply` mutation |
| HomericIntelligence/AchaeanFleet | 11 Dependabot PRs, 2026-05-31 | `feature-dev:code-reviewer` read-only blocker discovered; agent-type selection rule |
| ProjectOdyssey | PR #3343 (issue #3152) / PR #3109 (issue #3033) | Self-cancelling review plan no-op; comprehensive multi-specialist PR review orchestration |
| gh-tidy (HaywardMorihara/gh-tidy) | PRs #63/#67/#68/#69 | Upstream bash PR review rounds; logic/safety traps (verified-local) |
