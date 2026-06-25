---
name: automation-loop-log-driven-layered-debug
description: "Use when: (1) debugging hephaestus-automation-loop / a multi-stage plan→implement→drive-green pipeline from its output.log, (2) a single symptom ('PR not reviewed/implemented') turns out to be a stack of layered bugs revealed one at a time as each prior blocker is removed, (3) a fix 'didn't work' because the loop runs editable working-tree code and the fix wasn't dev-installed, (4) --issues was given PR numbers instead of issue numbers, (5) validating an automation-loop fix with a scoped re-run, (6) verifying automation-loop fixes by driving a single issue end-to-end to a merged PR + closed issue (scoped plan→implement re-run, artifact-chain success signals, zero-error health-check grep, live GitHub cross-check)."
category: debugging
date: 2026-06-20
version: "1.1.0"
history: automation-loop-log-driven-layered-debug.history
verification: verified-ci
user-invocable: false
tags:
  - hephaestus-automation-loop
  - output-log
  - log-driven-debugging
  - layered-bugs
  - editable-install
  - dev-install
  - pixi-run
  - scoped-re-run
  - issue-vs-pr
  - plan-implement-drive-green
  - pr-review-loop
  - methodology
  - single-issue-end-to-end-verify
  - artifact-chain-signals
  - merged-pr-closed-issue
  - zero-error-health-check
---

# Automation-Loop Log-Driven Layered Debugging

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-09 |
| **Objective** | Debug `hephaestus-automation-loop` (and similar multi-stage `plan → implement → drive-green` pipelines) iteratively from its `output.log`, when a single symptom ("PR not reviewed/implemented") is actually a STACK of layered bugs that only reveal themselves one at a time as each prior blocker is removed. |
| **Outcome** | Six layered bugs in the loop were peeled off one at a time, each surfacing only after the prior fix landed and was dev-installed. Every fix shipped to ProjectHephaestus `main` with green CI. |
| **Verification** | verified-ci — PRs #1104, #1106, #1108, #1110, #1112, #1114 all merged to ProjectHephaestus main with green CI. |

This is a META / methodology skill — it captures HOW to debug the loop, not the
individual per-bug fixes. The specific fixes live in the per-bug skills referenced
under [Related Skills](#related-skills); jump there for a particular blocker.

## When to Use

Trigger phrases / situations that should route to this skill:

1. Debugging `hephaestus-automation-loop` or a multi-stage `plan → implement → drive-green` pipeline from its `output.log`.
2. A single symptom ("PR not reviewed", "issue not implemented", "loop did nothing") turns out to be a STACK of layered bugs revealed one at a time as each prior blocker is removed.
3. A fix "didn't work" — but the loop runs the EDITABLE working-tree code and the fix was never dev-installed.
4. `--issues` was given PR numbers instead of ISSUE numbers (planner "Could not resolve to an Issue").
5. Validating an automation-loop fix with a scoped re-run before declaring victory.
6. Verifying automation-loop fixes by driving ONE real issue end-to-end — scoped `plan`→`implement` re-run that must produce a real artifact chain (`Created PR #N` → in-loop review `Verdict=GO` → `Enabled auto-merge` → `Removed worktree` → `phase implement done (rc=0)`), then the PR auto-MERGES and the issue auto-CLOSES — confirmed against live GitHub, not just a clean log.

## Verified Workflow

### Quick Reference

```bash
# 1. Capture the run as a per-phase timeline (the log IS the diagnostic instrument)
pixi run hephaestus-automation-loop --issues 725,711 2>&1 | tee output.log

# 2. Grep the decisive per-issue lines from the log
grep -nE 'Issue #[0-9]+: .*(implementation-review (GO|NO-GO))|re-running implement|head branch is|already checked out .* reusing|Verdict=.*Grade=.*threads=|Successful:|Skipped:|Failed:|Repo not done|Could not resolve to an Issue|Created PR #[0-9]+|Analysis complete for PR|Verdict=GO|Enabled auto-merge|Follow-up complete|Removed worktree|Failed to remove worktree|phase (plan|implement) done|implemented=|No JSON object found' output.log

# 3. CRITICAL: verify the fix is actually LIVE before re-running (loop runs editable code)
git checkout main && git pull && pixi run dev-install
pixi run python -c "import inspect, hephaestus.automation.<module> as m; print('<old-token>' in inspect.getsource(m))"
#   -> expect False for removed code, True for added code

# 4. Validate with a SCOPED re-run on a few REAL issue numbers (comma-delimited, NOT PR numbers)
pixi run hephaestus-automation-loop --issues <a,few,real,issues> 2>&1 | tee output.log
#   then cross-check live GitHub state (PR labels/comments) — the log is an observation report, not ground truth
```

### Detailed Steps

#### 1. The run log IS the diagnostic instrument

Always run the loop as `... 2>&1 | tee output.log` and read it as a per-phase
timeline. Grep the decisive per-issue lines:

- `Issue #N: ... implementation-review (GO|NO-GO)`
- `re-running implement`
- `head branch is`
- `already checked out ... reusing`
- `Verdict=... Grade=... threads=...`
- `Successful:` / `Skipped:` / `Failed:`
- `Repo not done`

The per-loop implementer summary (`Successful: 0 / Skipped: N`) is the fastest
signal of "did real work happen, or did the loop silently no-op?"

#### 2. Layered bugs surface one at a time

Fixing the top blocker exposes the next. Don't assume one fix is "the" fix —
re-run after each and read the NEW log; expect the symptom to MOVE, not vanish.
This session's actual stack, in the order each became visible only after the
previous fix landed:

| # | Blocker (became visible only after prior fix) | Fix | PR |
|---|------------------------------------------------|-----|-----|
| a | NO-GO PRs short-circuited as "settled" (`has_go or has_no_go` skip) → never re-reviewed | GO-only short-circuit | #1104 |
| b | Worktree sync did `git fetch origin {issue}-auto-impl` (an ASSUMED branch) → exit 128; the PR head branch was actually different | Read the PR's real `headRefName` | #1106 |
| c | `git worktree add` hit `fatal: branch already used by worktree` (branch checked out in another issue's worktree) | REUSE that worktree, don't force | #1110 |
| d | drive-green ignored `--issues` scope (pulled in unrelated bot PRs, scanned all open PRs, rc=1) | Scope drive-green to `--issues` | #1110 |
| e | In-loop reviewer posted a FALSE `POLICY VIOLATION` (fed empty/stale policy data that failed open) → no `Verdict:` line → AMBIGUOUS | Remove redundant in-loop policy checks; CI gates own policy | #1112 |
| f | Review loop converged on "0 threads" regardless of verdict → terminated at R0 on AMBIGUOUS and applied `state:skip` | Re-review on zero-thread non-GO; `state:skip` only on TRUE exhaustion | #1114 |

LESSON: each removed blocker uncovers the next. The symptom ("PR not reviewed")
stayed constant while the ROOT CAUSE moved six times.

#### 3. CRITICAL environment gotcha — the loop runs the EDITABLE working-tree code

`pixi run` imports `hephaestus` from the working tree (editable install). A fix
on a feature branch — or even a merged PR — does NOT take effect for the loop
until you `git checkout main && git pull && pixi run dev-install`, AND the working
tree is on a branch/commit that contains the fix.

Verify the fix is actually LIVE before re-running:

```bash
pixi run python -c "import inspect, hephaestus.automation.<module> as m; print('<old-token>' in inspect.getsource(m))"
# expect False for removed code / True for added code
```

MANY apparent "the fix didn't work" reports are really "the fix isn't installed
yet." Always confirm liveness before trusting a re-run. (Cross-ref
`pixi-runtime-env-gotchas`.)

#### 4. Input gotcha that masquerades as a code bug — `--issues` takes ISSUE numbers

`--issues` takes ISSUE numbers, comma-delimited (`--issues 725,711`) — NOT PR
numbers and NOT space-delimited. Passing PR numbers makes the planner's
`gh api graphql ... issue(number:N)` fail (`Could not resolve to an Issue with
the number of N`) AND then fail open and post planner comments onto the PR. When
the log shows that error, check whether N is actually a PR before chasing a code
bug. (Cross-ref `cli-flag-validation-prevent-silent-noop`.)

#### 5. Validation discipline

After a fix lands AND is installed, re-run a SCOPED loop
(`--issues <a few real issue numbers>`) and confirm the decisive log lines show
the NEW behavior — e.g. NO-GO → `re-running implement + review loop`, reviewer
emits a real `Verdict:` line (not AMBIGUOUS). Then cross-check live GitHub state
(PR labels, comments): the log is an observation report, not ground truth.
(Cross-ref `multi-repo-pr-automation-loop-orchestration`'s report-vs-live-state
rule.)

#### 6. Verifying a fix: single-issue end-to-end drive

The strongest form of step-5 validation is to drive ONE real issue all the way
through the loop to a MERGED PR + CLOSED issue. "No errors in the log" is NOT a
pass; a real artifact chain is. Pick one small, real, ready issue — e.g. an
audit-finding `severity:minor` already at `state:plan-go`, or a fresh
`state:needs-plan` one — and scope the loop tightly:

```bash
# Plan only (one issue, one loop, one worker) — capture per-issue
pixi run hephaestus-automation-loop --issues <N> --phases plan \
  --loops 1 --max-workers 1 -v 2>&1 | tee build/verify-<N>.log

# Implement (after the issue reaches plan-go). --allow-unsafe-phase-order
# silences the "plan without implement predecessor" warning when running
# implement standalone.
pixi run hephaestus-automation-loop --issues <N> --phases implement \
  --allow-unsafe-phase-order --loops 1 --max-workers 1 -v \
  2>&1 | tee -a build/verify-<N>.log
```

Scope notes:

- The loop runs ONLY the current repo by default (no `--org`) — exactly what you
  want for a single-repo verify.
- It operates on the clone under `--projects-dir` (default
  `/home/mvillmow/Projects/<repo>`), NOT necessarily your CWD, and reports
  `trunk=<sha>` — CONFIRM that sha contains your merged fixes before trusting the
  run (same liveness discipline as step 3, but for the projects-dir clone).

A clean PASS produces a real ARTIFACT CHAIN, not just "no errors":

```text
Created PR #N
... Analysis complete for PR ... found 0 inline comment(s)   # in-loop review
... Verdict=GO
Enabled auto-merge for implementation-GO PR #N
... Follow-up complete ... filed=none accepted=0 rejected=K
Removed worktree for issue #N
... phase implement done ... (rc=0)
```

Because auto-merge was armed, the PR then MERGES and the issue auto-CLOSES via its
`Closes #N`. The log is an OBSERVATION REPORT, not ground truth — always
cross-check live GitHub:

```bash
gh pr view <PR> --json state,mergedAt    # expect MERGED + a mergedAt timestamp
gh issue view <N> --json state           # expect CLOSED
```

Zero-error health check — across the WHOLE verify log, every one of these must be
absent (the ORIGINAL broken `output.log` was full of them; a clean verify run has
NONE):

```bash
grep -ciE "429|session limit|usage cap|waiting for reset|Traceback|\[ERROR\]|- ERROR -|Failed to remove worktree|No JSON object found" build/verify-<N>.log
#   -> expect 0
```

What is NORMAL in a verify log and must NOT be mistaken for failure:

- The implement phase runs the loop's OWN internal `/learn` step
  (`claude --resume ... /learn EXECUTE the /learn skill-creation workflow ...
  --model claude-haiku-4-5`) near the end — that is normal post-implementation
  behavior, not your own `/learn` and not a hang. After it, the follow-up +
  worktree-cleanup steps run, THEN the phase reports done.
- The implementer step can legitimately take 10–15 min for one issue: it edits
  files and runs the FULL `pytest` suite IN THE WORKTREE to self-validate before
  committing. A log "stalled" at `agent=implementer ... mode=create` is usually
  the implementer working — confirm via the nested `claude` child process
  consuming CPU and edits in `build/.worktrees/issue-<N>/`
  (`git -C <worktree> status --short`), not stuck.
- The `prompts: Path '...marketplace.json' is not under repo_root ...; injecting
  absolute path` WARNING appears once per phase and is working-as-designed — do
  NOT treat it as a failure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed one fix resolved the symptom | Landed the top-blocker fix and declared the loop fixed | The symptom ("PR not reviewed/implemented") MOVED to the next layered bug — it did not go away | Re-run + read the NEW log after EVERY fix; expect the root cause to shift, not vanish |
| Re-ran the loop expecting a branch/merged-PR fix to apply | Re-ran `pixi run hephaestus-automation-loop` after the fix merged | The loop runs the editable working-tree code; the fix was never installed, so behavior was unchanged | `git checkout main && git pull && pixi run dev-install`, then verify with `inspect.getsource` before re-running |
| Passed PR numbers to `--issues` | Invoked the loop with PR numbers in `--issues` | The planner could not resolve them as issues, failed open, and posted planner comments onto the PR | `--issues` takes comma-delimited ISSUE numbers, not PR numbers, not space-delimited |
| Trusted a clean log as proof the fix worked | Read `output.log`, saw expected lines, declared done | The log is an observation report, not ground truth — live GitHub state can differ | Cross-check PR labels/comments on GitHub after a scoped validation re-run |
| Polled `pgrep` to decide if the verify loop was still running | `pgrep -f "hephaestus-automation-loop --issues <N>"` to detect completion | It RACES: briefly shows RUNNING just after exit, and can miss the process under the pixi/python wrapper — one stale reading is not proof | Prefer the loop's OWN completion signal (backgrounded exit / `phase ... done (rc=0)`); if you must poll, re-check with `ps -eo pid,etime,args \| grep automation-loop` before concluding |
| Mistook the loop's internal `/learn` step for my own `/learn` or a hang | Saw `claude --resume ... /learn ... --model claude-haiku-4-5` late in the implement phase and assumed something went wrong | That step is NORMAL post-implementation behavior baked into the loop; follow-up + worktree-cleanup run after it, then the phase reports done | Recognize the internal `/learn` line as expected; wait for `Removed worktree` + `phase implement done (rc=0)` before judging |
| Assumed a long implementer step was stuck | Saw the log "stalled" at `agent=implementer ... mode=create` and thought it hung | The implementer legitimately takes 10–15 min: it edits files and runs the FULL `pytest` suite in the worktree to self-validate before committing | Confirm progress via the nested `claude` child CPU usage and edits in `build/.worktrees/issue-<N>/` (`git -C <wt> status --short`) before declaring a hang |
| Flagged the marketplace-path WARNING as a verify failure | Treated `prompts: Path '...marketplace.json' is not under repo_root ...; injecting absolute path` as an error | It is a once-per-phase working-as-designed WARNING, not a failure | Exclude it from the zero-error health check; only `429`/`Traceback`/`[ERROR]`/`- ERROR -`/`Failed to remove worktree`/`No JSON object found` count as failures |

## Results & Parameters

**Decisive log grep tokens** (per-issue timeline signals):

| Token | Meaning |
|-------|---------|
| `Issue #N: ... implementation-review (GO\|NO-GO)` | Implementation verdict for an issue |
| `re-running implement` | Implementer re-entered (expected after a NO-GO once fixed) |
| `head branch is` / `already checked out ... reusing` | Worktree sync used the real branch / reused an existing worktree |
| `Verdict=... Grade=... threads=...` | Reviewer emitted a real verdict (not AMBIGUOUS) |
| `Successful:` / `Skipped:` / `Failed:` | Per-loop implementer summary — fastest "did real work happen?" signal |
| `Repo not done` | Loop has more work to do |
| `Could not resolve to an Issue with the number of N` | `--issues` was likely given a PR number |
| `Created PR #N` | Implement phase opened the PR (verify-run artifact-chain start) |
| `Analysis complete for PR ... found 0 inline comment(s)` | In-loop review ran clean |
| `Verdict=GO` | In-loop review approved (verify pass requires this) |
| `Enabled auto-merge for implementation-GO PR #N` | Auto-merge armed → PR will merge when checks pass |
| `Follow-up complete ... filed=none accepted=0 rejected=K` | Follow-up step finished (rejected=K is fine) |
| `Removed worktree for issue #N` | Worktree cleaned up (vs `Failed to remove worktree` = bug) |
| `phase (plan\|implement) done ... (rc=0)` | Phase finished successfully |
| `No JSON object found` | Follow-up/plan JSON parse failure — must be ABSENT in a clean verify |

**Verify-run zero-error health check** (across the whole `build/verify-<N>.log`):

```bash
grep -ciE "429|session limit|usage cap|waiting for reset|Traceback|\[ERROR\]|- ERROR -|Failed to remove worktree|No JSON object found" build/verify-<N>.log
#   -> expect 0
```

**Commands:**

```bash
# Capture
pixi run hephaestus-automation-loop --issues 725,711 2>&1 | tee output.log

# Is-fix-live check
pixi run python -c "import inspect, hephaestus.automation.<module> as m; print('<old-token>' in inspect.getsource(m))"

# Scoped validation re-run
pixi run hephaestus-automation-loop --issues <a,few,real,issues> 2>&1 | tee output.log

# Single-issue end-to-end VERIFY drive (plan, then implement after plan-go)
pixi run hephaestus-automation-loop --issues <N> --phases plan \
  --loops 1 --max-workers 1 -v 2>&1 | tee build/verify-<N>.log
pixi run hephaestus-automation-loop --issues <N> --phases implement \
  --allow-unsafe-phase-order --loops 1 --max-workers 1 -v \
  2>&1 | tee -a build/verify-<N>.log
gh pr view <PR> --json state,mergedAt   # expect MERGED
gh issue view <N> --json state          # expect CLOSED
```

| Parameter | Value |
|-----------|-------|
| Pipeline | `hephaestus-automation-loop` (`plan → implement → drive-green`) |
| Diagnostic instrument | `output.log` via `2>&1 \| tee output.log` |
| Layered bugs peeled in one session | 6 (#1104, #1106, #1108, #1110, #1112, #1114) |
| Re-run scope | `--issues <comma-delimited ISSUE numbers>` |
| Single-issue verify scope | `--issues <N> --phases plan` then `--phases implement --allow-unsafe-phase-order` (`--loops 1 --max-workers 1 -v`) |
| End-to-end verify result | ProjectHephaestus issue #1517 (audit finding) driven plan→implement → PR #1538 (`fix(security): include NOTICE in license-scan path filter`), in-loop `Verdict=GO`, follow-up `rejected=2`, worktree removed cleanly, ZERO error/429/Traceback lines → PR #1538 auto-merged to main (commit `6c8fbed`), issue #1517 auto-closed. Verified fixes: PRs #1530 / #1531 / #1533 / #1535 / #1537. |
| **Verified On** | ProjectHephaestus PRs #1104 / #1106 / #1108 / #1110 / #1112 / #1114 (all merged to main, green CI); single-issue end-to-end verify drive of issue #1517 → merged PR #1538 + closed issue (verified-ci + verified live) |

## Related Skills

Jump to these per-bug skills for the specific fix behind each layered blocker:

- `pr-review-loop-orchestration-agent-patterns` — GO-only short-circuit, zero-thread non-GO re-review, `state:skip` on true exhaustion (#1104, #1112, #1114).
- `multi-repo-pr-automation-loop-orchestration` — drive-green scoping, report-vs-live-state discipline (#1110).
- `automation-reuse-repo-clone-with-worktree-per-pr` — real `headRefName` sync, worktree reuse on branch collision (#1106, #1110).
- `cli-flag-validation-prevent-silent-noop` — issue-vs-PR `--issues` validation.
- `pixi-runtime-env-gotchas` — editable working-tree code / dev-install gotcha.
