---
name: pr-review-loop-orchestration-agent-patterns
description: "Use when: (1) building or debugging a Python implement-review loop where an LLM sub-agent reviews a PR and a fixer agent addresses inline comments, (2) a review loop resolves threads even though no commit was produced — resolution must be gated on a real commit not the model self-report, (3) a loop ends AMBIGUOUS or NO-GO too fast before ever earning an explicit GO verdict, (4) LLM or agent-generated inline PR review comments are rejected by GitHub (HTTP 422) because they do not lie on a changed diff hunk, (5) an agent-driven CI-fix session produces no commit and the PR stays red; the correct response is a single bounded retry with unresolved review threads injected verbatim, (6) a review fix plan file concludes no changes are needed and the automation should self-cancel without opening a new PR, (7) a feature-dev:code-reviewer sub-agent cannot execute shell commands and cannot post gh pr review — wrong agent type was chosen, (8) a GitHub GraphQL PR-review mutation field selection is wrong and the automation loop fails on every call with Field X does not exist, (9) pre-commit must cover the full PR diff from the merge-base not just the most-recent-edit files before pushing, (10) an existing-PR review handler short-circuits NO-GO PRs as if they were settled (idempotency `if has_go or has_no_go: skip`) so a failed-review PR never re-enters the loop — short-circuit on GO ONLY, (11) an existing-PR worktree sync fails `git fetch origin {issue}-auto-impl` with exit 128 because the PR head branch was ASSUMED from the issue number instead of read from the PR's real `headRefName`, (12) an in-loop LLM PR reviewer posts a FALSE policy violation (e.g. `POLICY VIOLATION: Closes, auto-merge-premature, signed-commits` on a PR that actually has `Closes #N`, auto-merge OFF, and a signed commit) because its policy fetch failed open to violation, or you are tempted to make the reviewer re-check `Closes #N` / signed commits / auto-merge that a CI gate (`pr-policy` required, `auto-merge-policy` advisory) already enforces"
category: ci-cd
date: 2026-06-08
version: "1.3.0"
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
  - existing-pr-short-circuit
  - no-go-re-review
  - go-only-short-circuit
  - pr-head-branch-resolution
  - headrefname
  - assumed-branch-name-fetch-128
  - ci-gate-owns-policy
  - llm-reviewer-fails-open
  - false-policy-violation
  - pr-policy-gate
  - auto-merge-policy
  - no-duplicate-hard-gate
  - homericintelligence
---

# PR Review Loop Orchestration and Agent Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-08 |
| **Objective** | Build and debug a Python implement-review loop that drives LLM sub-agents to review a PR and fix its inline comments, converging on an EVIDENCE-BASED `Verdict: GO`. Covers: commit-gated thread resolution, inline-comment diff-hunk (422) validation, one-shot no-commit retry with unresolved review threads injected, agent-type selection for review tasks, GraphQL field/input validation for PR-review mutations, self-cancelling review plans, full merge-base pre-commit scope, the existing-PR short-circuit being GO-ONLY (NO-GO PRs MUST re-enter the loop), and using the PR's real `headRefName` for the worktree instead of an assumed `{issue}-auto-impl`. |
| **Outcome** | Merged across multiple ProjectHephaestus PRs (commit-gate + verdict-GO convergence #1084; inline-comment 422 validation #1043; no-commit retry + thread injection #847; GraphQL field/input validation #906/#1006; existing-PR NO-GO re-review #1104; real PR head-branch resolution #1106; in-loop policy enforcement removed in favor of CI gates #1112) plus ProjectOdyssey and gh-tidy upstream review rounds. |
| **Verification** | verified-ci |
| **Version** | 1.3.0 |

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
- An existing-PR review loop skips NO-GO PRs as if settled (e.g. `Successful: 0 / Skipped: N`, every PR already carries a terminal label), or fails `git fetch origin {issue}-auto-impl` with `exit 128` on an assumed `{issue}-auto-impl` branch.
- An in-loop LLM reviewer posts a FALSE policy violation, or you are tempted to make the reviewer re-check `Closes #N` / signed commits / auto-merge that a CI gate already enforces.

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

#### Existing-PR handler: short-circuit on GO ONLY, and use the PR's real head branch

The existing-PR handler (`_review_existing_pr`) must enforce two invariants that mirror the
core "converge ONLY on `Verdict: GO`; a re-open OVERRIDES a stale GO" rule:

1. **GO-ONLY short-circuit.** The idempotency guard must skip a PR ONLY when it already carries
   the GO label — `if has_go: return` — NOT `if has_go or has_no_go: return`. A
   `state:implementation-no-go` label is NOT terminal: it means the PR FAILED review and must
   keep going. Treating NO-GO as settled is identical to the long-standing "zero threads != GO"
   bug at the existing-PR layer. Symptom in a live 5-loop run: all 60 existing PRs carried a
   terminal label (10 GO, 50 NO-GO), so every PR was skipped every loop (`Successful: 0 /
   Skipped: 60`) AND the fallback `drive-green` phase was itself skipped, so NO-GO PRs were
   NEVER re-implemented or re-reviewed. FIX: short-circuit on `has_go` only; a NO-GO PR then
   falls through into `_run_impl_review_loop`, which already does NO-GO → address (resume the
   implementer session) → re-review → converge-on-GO. Bound the re-run with
   `MAX_REVIEW_ITERATIONS` and only re-implement when there are ACTIONABLE threads; the
   documented defense against burning tokens on a genuinely-stuck PR is to gate a re-run on the
   PR head SHA having advanced (same marker discipline as the no-commit forensics path).

2. **Resolve the PR's REAL head branch — never assume `{issue}-auto-impl`.** `_review_existing_pr`
   must NOT prepare the worktree with `branch_name = f"{issue_number}-auto-impl"`. That is an
   ASSUMPTION, and `find_pr_for_issue` can match a PR via a PR-body `Closes #N` search
   (strategy 2), so the PR's head branch may be named after a DIFFERENT issue or a bundle.
   `sync_worktree_to_remote_branch` then runs `git fetch origin {assumed-branch}` which fails
   `fatal: couldn't find remote ref ...; exit 128` whenever the real `headRefName` differs from
   the convention (confirmed live: issue #725 → PR #996 whose real `headRefName` is
   `708-auto-impl`). FIX: call `get_pr_head_branch(pr_number)` (`gh pr view <pr> --json
   headRefName`; returns `None` on failure for a safe fallback) and use the resolved branch for
   the worktree create + sync + review loop + `WorkerResult`; fall back to the assumed name ONLY
   if the lookup returns `None`. The FRESH-implementation path (no existing PR) keeps the
   `{issue}-auto-impl` convention because it CREATES the branch itself. This bug was LATENT —
   before the GO-ONLY fix, NO-GO PRs short-circuited before reaching the fetch, so it never
   fired for them; the GO-ONLY fix EXPOSED it. Test note: any test exercising this path MUST
   mock `get_pr_head_branch` or it makes a real `gh` call (a test took 103s before mocking).

#### Policy enforcement belongs in CI gates, not the in-loop LLM reviewer

Do NOT make the in-loop LLM PR reviewer enforce repo PR policy (`Closes #N` body
line, deferred auto-merge, signed commits). Those are enforced authoritatively by
the GitHub CI gates `pr-policy` (required status check) and `auto-merge-policy`
(advisory). Duplicating them in the reviewer is redundant AND fragile: LLM-context
policy fetches fail OPEN TO "violation", so a transient/empty fetch fabricates a
false NOGO that blocks a compliant PR.

Concrete failure (PR #996): the reviewer prompt had a "Policy checks (MANDATORY)"
block plus a strict-rubric "D1 — Policy compliance" NOGO gate, fed by
`_fetch_signing_state()` (per-commit GraphQL) and an auto-merge state fetch.
`_fetch_signing_state` returns `[]` on ANY error and the prompt treats an empty
array as a signed-commits NOGO. On PR #996 the reviewer posted a FALSE `POLICY
VIOLATION: Closes, auto-merge-premature, signed-commits` even though the body had
`Closes #725` / `#726`, auto-merge was OFF, and the commit was signed
(`verified=true`) — because a transient/empty fetch produced empty data blocks. The
generic message also forced the human to guess which check "failed".

Fix (PR #1112) — remove the in-loop policy enforcement entirely; let CI own it:

- `prompts/pr_review.py`: delete the "Policy checks (MANDATORY)" section + the
  `{auto_merge_state_block}` / `{commits_signing_block}` data blocks + the `POLICY
  VIOLATION` summary contract; drop the `auto_merge_enabled` /
  `commits_signing_state` params from `get_pr_review_analysis_prompt`. Keep the
  `Verdict: GO/NOGO` + JSON contract (now code-quality only).
- `prompts/_strict_rubric.py`: replace `D1 — Policy compliance (HIGHEST PRIORITY /
  NOGO gate)` with `D1 — Correctness & completeness`; add a note that CI gates own
  policy.
- `pr_reviewer.py`: delete `_fetch_signing_state` + the signing GraphQL query;
  stop populating `context["auto_merge_enabled"]` / `["commits_signing_state"]`;
  drop `autoMergeRequest` from the `gh pr view --json` projection.

KEY PRINCIPLE: when a hard gate already exists in CI (a required status check), an
LLM re-implementation of the same gate is redundant and, because LLM-context
fetches fail open to "violation", it produces false negatives that block good PRs.
Enforce policy ONCE, in the deterministic CI gate; let the LLM reviewer judge code
quality only.

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

For a SIMPLE one-line reply to a single existing review comment you do not need the GraphQL
`addPullRequestReviewThreadReply` mutation at all — the REST replies endpoint is shorter and
avoids resolving a thread node id:

```bash
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies --method POST -f body="..."
```

Use the GraphQL reply mutation only when you also need the returned `comment { id }` or are
already operating on thread node ids; otherwise the REST `comments/{id}/replies` POST is the
simpler path.

#### Three-location posting for a comprehensive review

To make a comprehensive review maximally visible, post it in THREE places: (1) the main PR
review body (`gh pr review`), (2) one line-specific PR comment for each concrete finding, and
(3) a tracking-issue comment via `gh issue comment <n> --body "..."` so the issue history
records the review outcome. KEY takeaway: prefer plain line-specific PR comments
(`gh pr comment` / `comments/{id}/replies`) over the inline REVIEW API — the inline review
path requires validating every comment against a changed diff hunk (see the 422 section),
which is complex and error-prone; a simple PR comment carries the same feedback without the
hunk-position constraint.

#### Self-cancelling review plan and pre-push diff scope

When a `.claude-review-fix-*.md` file's outer wrapper says "implement all fixes" but the
inner Fix Plan concludes "No fixes are required / the PR is correct and complete" (failing
CI is pre-existing on `main`, `git status` clean, only the review file untracked), the plan
is self-cancelling: make NO changes, do NOT manufacture a commit, and report that the branch
is already up to date. Trust the inner plan, not the outer shell.

Before pushing, run pre-commit/validation over the FULL PR diff from the merge-base
(`git diff origin/main...HEAD`), not just the most-recently-edited files — a fix can be
clean while an earlier-touched file in the same PR still fails the gate.

#### Bash traps in review-automation scripts

When the review loop or its helpers are shell scripts (e.g. gh-tidy-style wrappers), four
recurring traps:

- **Function-before-definition.** Do NOT call color/echo helper functions from the
  argument-parsing block at the top of the script — that block runs before the helpers are
  defined, so the call expands to nothing (or errors). Emit early diagnostics with a plain
  `echo "..." >&2` instead, and only switch to the pretty helpers after their definitions.
- **Value-flag consumes the next flag.** A flag that takes a value (`--branch X`) must guard
  against an absent value, otherwise it silently swallows the following flag as its argument.
  Guard with `if [[ -z "$1" || "$1" == --* ]]; then error "missing value for --branch"; fi`.
- **Pipe-subshell loses array mutations.** `cmd | while read ...; do arr+=(...); done` runs
  the loop body in a subshell, so array (and variable) mutations vanish after the pipe. Use
  process substitution to keep the loop in the current shell: `while read ...; do ...; done < <(cmd)`.
- **Helper that doesn't `exit` on error.** A `set_trunk_branch`-style helper that prints an
  error but forgets `exit 1` lets the script continue past a fatal condition with bad state.
  Every fatal branch in a helper MUST `exit 1` (or `return 1` + a checked caller).

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
| Post every comprehensive-review finding through the inline review API | Mapped each finding into the `POST .../reviews` inline-comments payload | Inline comments must validate against a changed diff hunk (422 on any off-hunk line) — complex and error-prone for prose findings | Prefer a simple line-specific PR comment (`gh pr comment` / `comments/{id}/replies`); reserve the inline review API for true on-hunk annotations. Post comprehensively in THREE places: PR review body + line-specific PR comment + `gh issue comment` on the tracking issue. |
| Reply to one review comment via the GraphQL thread-reply mutation | Resolved the thread node id then called `addPullRequestReviewThreadReply` for a one-line reply | Overkill — needed the thread node id and the full GraphQL round-trip for a trivial reply | For a single one-line reply use the REST endpoint `gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies --method POST -f body="..."`; reserve the GraphQL mutation for when you need the returned `comment { id }`. |
| Call color/echo helpers in the arg-parsing block (bash) | Invoked pretty-print helpers from the top-of-script flag parser | The parser runs before the helper definitions, so the call no-ops or errors | Emit early diagnostics with `echo "..." >&2`; only use the helpers after their definitions. |
| Value-taking flag without an absent-value guard (bash) | `--branch X` read `$1` blindly as its value | A missing value silently swallows the next flag as the argument | Guard with `[[ -z "$1" \|\| "$1" == --* ]]` before consuming the value, else error out. |
| Mutate an array inside a piped `while read` loop (bash) | Appended to an array inside `cmd \| while read` | The piped loop runs in a subshell; array mutations are lost after the pipe | Use process substitution: `while read ...; do arr+=(...); done < <(cmd)`. |
| `set_trunk_branch`-style helper prints an error but doesn't exit (bash) | Helper logged the error and returned normally | The script continued past a fatal condition with bad trunk state | Every fatal branch in a helper MUST `exit 1` (or `return 1` + a checked caller). |
| Short-circuit the existing-PR handler on GO **or** NO-GO | `_review_existing_pr` skipped re-review with `if has_go or has_no_go: return`, treating a `state:implementation-no-go` PR as terminal/settled | In a live 5-loop run all 60 existing PRs carried a terminal label (10 GO, 50 NO-GO), so every PR was skipped every loop (`Successful: 0 / Skipped: 60`) and the fallback `drive-green` phase was skipped too — NO-GO PRs were NEVER re-implemented or re-reviewed | Short-circuit on `has_go` ONLY; a NO-GO label is NOT terminal (it means review FAILED). Let NO-GO fall through into `_run_impl_review_loop` (NO-GO → resume implementer → re-review → converge-on-GO), bounded by `MAX_REVIEW_ITERATIONS`; gate a re-run on the PR head SHA advancing to avoid burning tokens on a stuck PR (PR #1104). |
| Sync the existing-PR worktree to the assumed `{issue}-auto-impl` branch | `_review_existing_pr` set `branch_name = f"{issue_number}-auto-impl"` and called `sync_worktree_to_remote_branch` → `git fetch origin {issue}-auto-impl` | `find_pr_for_issue` can match a PR via a PR-body `Closes #N` search, so the PR head branch may belong to a DIFFERENT issue/bundle; the fetch failed `fatal: couldn't find remote ref …; exit 128` every loop (live: issue #725 → PR #996, real `headRefName` `708-auto-impl`). Latent until the GO-ONLY fix let NO-GO PRs reach the fetch | Resolve the PR's REAL head via `get_pr_head_branch(pr_number)` (`gh pr view <pr> --json headRefName`; `None` on failure) and use it for worktree create + sync + loop + result; fall back to the assumed name only on `None`. The fresh-impl path keeps the convention (it creates the branch). Tests MUST mock `get_pr_head_branch` (a real `gh` call took 103s) (PR #1106). |
| Make the in-loop LLM reviewer enforce repo PR policy | Reviewer had a "Policy checks (MANDATORY)" prompt block + a strict-rubric `D1 — Policy compliance` NOGO gate that re-checked `Closes #N` / auto-merge / signed-commits, fed by a per-commit GraphQL signing fetch (`_fetch_signing_state`) + an auto-merge state fetch | The fetch returns `[]` on any error and the prompt treats empty = violation → fabricated false POLICY VIOLATIONs on compliant PRs. On PR #996 it posted `POLICY VIOLATION: Closes, auto-merge-premature, signed-commits` though the body had `Closes #725/#726`, auto-merge was OFF, and the commit was signed (`verified=true`) | Enforce PR policy ONCE in the deterministic CI gates (`pr-policy` required + `auto-merge-policy` advisory); the LLM reviewer judges code quality only — never duplicate a CI hard-gate in an LLM that fails open to violation. Removed the prompt block, the rubric D1 gate, `_fetch_signing_state`, and the auto-merge/signing context (PR #1112). |

## Results & Parameters

### Progress / convergence contract (SHIPPED, verified-ci)

| Rule | Implementation | Why |
|------|----------------|-----|
| Progress requires a commit | `made_progress = addressed and committed`; `_commit_if_changes` returns bool (True iff HEAD advanced) | A clean worktree with prose replies is NOT progress |
| Convergence requires explicit GO | parse reviewer output, require literal `Verdict: GO` (last line, not substring) | "zero threads" + AMBIGUOUS/NO-GO is not success |
| Fixer never resolves | resolution mutation lives in the reviewer/validator on the next pass | evidence-based; fixer can't self-declare victory |
| Reviewer resolution is diff-evidence-based, matched by thread `id` | resolve addressed threads, re-open (new thread) the rest | re-open OVERRIDES a stale GO; GitHub has no unresolve mutation |
| Existing-PR short-circuit is GO-ONLY | `_review_existing_pr`: `if has_go: return` (NOT `has_go or has_no_go`) | a NO-GO label is NOT terminal; it must re-enter the loop (PR #1104) |
| Existing-PR worktree uses the PR's real head branch | `get_pr_head_branch(pr)` → `headRefName`; fall back to `{issue}-auto-impl` only on `None` | the PR may have matched via `Closes #N`, so the head branch can differ from the issue number (PR #1106) |

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
| ProjectHephaestus | PR #1104 | Existing-PR handler short-circuits on GO ONLY; NO-GO PRs re-enter `_run_impl_review_loop` instead of being skipped as settled (`_review_existing_pr` in `implementer_phase_runner.py`) |
| ProjectHephaestus | PR #1106 | `get_pr_head_branch(pr_number)` in `_review_utils`; `_review_existing_pr` uses the PR's real `headRefName` (not the assumed `{issue}-auto-impl`) for worktree create + sync + loop; fixes `git fetch … exit 128` |
| ProjectHephaestus | PR #1112 | Removed in-loop policy enforcement from the LLM reviewer — deleted the "Policy checks (MANDATORY)" block + `POLICY VIOLATION` contract from `prompts/pr_review.py`, the `D1 — Policy compliance` rubric gate from `prompts/_strict_rubric.py`, and `_fetch_signing_state` + auto-merge/signing context from `pr_reviewer.py`. CI gates `pr-policy` (required) + `auto-merge-policy` (advisory) own policy; reviewer judges code quality only. Fixes false POLICY VIOLATION on compliant PR #996. Net +78/-345; prompt + pr_reviewer suites green, ruff + mypy 342 files clean |
| HomericIntelligence/AchaeanFleet | 11 Dependabot PRs, 2026-05-31 | `feature-dev:code-reviewer` read-only blocker discovered; agent-type selection rule |
| ProjectOdyssey | PR #3343 (issue #3152) / PR #3109 (issue #3033) | Self-cancelling review plan no-op; comprehensive multi-specialist PR review orchestration |
| gh-tidy (HaywardMorihara/gh-tidy) | PRs #63/#67/#68/#69 | Upstream bash PR review rounds; logic/safety traps (verified-local) |
