---
name: ci-cd-homeric-intelligence-merge-gotchas
description: "Recurring HomericIntelligence CI/merge traps that block PR auto-merge even when the code is correct. Use when: (1) pixi-check fails 'lock-file not up-to-date with the workspace' or Lint/Type-Check break after removing pypi-dependencies; (2) a Keystone-style lint job fails fast (~20s) at 'Install build dependencies (just + linters)'; (3) CodeQL cpp/unused-{local,static}-variable flags a genuinely-used C++ variadic template parameter pack; (4) a PR is MERGEABLE with all REQUIRED checks green but auto-merge won't fire; (5) you are driving a chain of dependency-gated PRs and need to auto-arm each downstream PR when its gate merges; (6) a PR is MERGEABLE with every REQUIRED status check green, but mergeStateStatus stays BLOCKED and auto-merge won't fire — the gate is `required_review_thread_resolution: true` plus unresolved CodeQL/github-advanced-security review threads; detect via GraphQL reviewThreads (the REST field is empty), assess each finding before resolving, document accept-rationale, then resolveReviewThread; (7) the pr-policy required gate fails 'Auto-merge is enabled before implementation review GO' — do not pre-arm auto-merge before the state:implementation-go label (the inverse 'PR has state:implementation-go but auto-merge is not enabled' also fails); disable premature auto-merge and let the label workflow arm it."
category: ci-cd
date: 2026-06-06
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: ci-cd-homeric-intelligence-merge-gotchas.history
tags: [pixi, pixi-lock, codeql, auto-merge, branch-protection, just-systems, keystone, agamemnon, dependency-gated-pr, review-thread-resolution, github-advanced-security, pr-policy, implementation-go]
---

# HomericIntelligence CI / Merge Gotchas

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-06 |
| **Objective** | Unblock PR auto-merge across HomericIntelligence repos when the code is correct but CI/merge mechanics get in the way — pixi lock-format mismatch, just.systems install flakes, CodeQL variadic-pack false positives, auto-merge stalling on non-required checks, ordering of dependency-gated PR cascades, `required_review_thread_resolution` blocking merge on unresolved CodeQL review threads even with all required checks green, and the `pr-policy` gate failing when auto-merge is armed before the `state:implementation-go` label |
| **Outcome** | Seven distinct traps each have a verified, repeatable fix; established the diagnostic that distinguishes a real failure from infra flake (failing STEP NAME, not log), the correct CodeQL dismiss path (≤280-char comment + thread resolution), the required-contexts query, the action-monitor pattern that arms held downstream PRs only after their gates merge, the GraphQL `reviewThreads` query that surfaces hidden unresolved-thread merge gates (the REST field is empty) plus the assess-then-`resolveReviewThread` discipline, and the rule that auto-merge must NOT be pre-armed before `state:implementation-go` (disable premature auto-merge + rerun the failed pr-policy check; let the label workflow arm it) |
| **Verification** | verified-ci — all seven traps observed and fixed in live CI; traps 1–5 during the Keystone pure-transport refactor (Keystone #577–#581, Agamemnon #419–#421 merged 2026-05-31); trap 6 on ProjectNestor #101/#97, where resolving unresolved CodeQL review threads flipped BLOCKED→mergeable and both auto-merged to `main` (2026-06-02); trap 7 on ProjectHephaestus #1073/#1075/#1077, where pre-arming auto-merge failed the `pr-policy` gate's "Check 2" and disabling it flipped fail→pass (2026-06-06) |

## When to Use

1. **pixi lock mismatch.** `pixi-check` fails `lock-file not up-to-date with the workspace`, or `Lint` / `Type-Check` / `dependency-scan` go red — especially right after you removed a `[pypi-dependencies]` table from `pixi.toml`.
2. **Fast lint flake.** A Keystone-family `lint` job fails in ~20s at the step **"Install build dependencies (just + linters)"** (a `curl https://just.systems/install.sh` 403/EOF), not at an actual linter step.
3. **CodeQL variadic-pack false positive.** `cpp/unused-local-variable` or `cpp/unused-static-variable` flags a C++ variadic template parameter pack (`args`, `Rest`) that is genuinely consumed via pack-expansion or forwarding.
4. **Auto-merge won't fire.** A PR is `MERGEABLE` with every branch-protection-required context green, yet GitHub auto-merge does not merge because a NON-required check (Coverage, security/dependency-scan) is still red or pending.
5. **Dependency-gated cascade.** You are driving a chain where a downstream PR must not merge until its gate PR(s) merge first (extraction-before-deletion), and you want each downstream PR auto-armed the moment its gates land.
6. **Unresolved review threads block merge.** A PR is `MERGEABLE` with every REQUIRED status check green, yet `mergeStateStatus` stays `BLOCKED` and auto-merge will not fire — the gate is the HI ecosystem-standard branch-protection setting `required_review_thread_resolution: true` plus unresolved CodeQL / `github-advanced-security` review threads. Detect via the GraphQL `reviewThreads` query (the REST `reviewThreads` field is empty/unavailable), assess each finding before resolving, document the accept-rationale, then `resolveReviewThread`.
7. **pr-policy fails on premature auto-merge.** The REQUIRED `pr-policy` gate fails with `::error::Auto-merge is enabled before implementation review GO.` because you ran `gh pr merge --auto --squash` on a fresh PR before it carried the `state:implementation-go` label. (The inverse — `::error::PR has state:implementation-go but auto-merge is not enabled.` — fails when the label is present but auto-merge is off.) Do NOT pre-arm auto-merge; `gh pr merge <N> --disable-auto`, rerun the failed pr-policy check, and let the review→`state:implementation-go` label workflow arm `--auto --squash`.

## Verified Workflow

> **Verification level:** verified-ci — every trap below was hit and resolved in live CI; traps 1–5 during the Keystone pure-transport refactor (Keystone #577–#581, Agamemnon #419–#421 merged to `main` 2026-05-31); trap 6 on ProjectNestor #101/#97 (both auto-merged to `main` 2026-06-02 once the unresolved review threads were resolved); trap 7 on ProjectHephaestus #1073/#1075/#1077 (pre-armed auto-merge failed the `pr-policy` gate; disabling it flipped the check fail→pass 2026-06-06).

### 1. pixi lock-format version trap

CI's `setup-pixi` pins an **older** pixi that requires lock-file `version: 6`. Local pixi 0.69.x writes `version: 7`, which CI's pixi **cannot load** → `pixi install --locked` fails. This surfaces indirectly as red `Lint` / `Type-Check` / `dependency-scan` jobs (they all run `pixi install --locked` first), so the failure looks like a code problem when it is purely a lock-format problem.

- pixi **0.39.5** writes v6 but lacks a `lock` subcommand, and its parselmouth pypi-name-mapping download (`raw.githubusercontent.com/prefix-dev/parselmouth`) flakes from sandboxes — so it is unreliable for regenerating the lock.
- **Reliable fix:** resolve with a newer pixi to confirm the conda package set is unchanged, then **hand-edit the v6 lock** to drop orphaned pypi packages. Verify with `pixi install --locked` using a pixi NEWER than CI's: when it prints `lock file is up-to-date but uses an older format (v6)` and exits 0, that proves CI's older pixi will also accept it.
- **Companion trap:** removing the `[pypi-dependencies]` table from `pixi.toml` WITHOUT regenerating/editing the lock makes `pixi-check` fail `lock-file not up-to-date with the workspace`. The lock must be edited to match the workspace in the same change.

### 2. just.systems lint flake (transient infra, auto-rerunnable)

A Keystone-family `lint` job that fails in ~20s at the step **"Install build dependencies (just + linters)"** is almost always the `curl https://just.systems/install.sh` returning 403 / closing the connection (EOF) — transient infra, NOT a lint error.

- **Diagnose by the FAILING STEP NAME, not the log body:**
  ```bash
  gh api repos/<o>/<r>/actions/jobs/<jobid> \
    --jq '.steps[]|select(.conclusion=="failure")|.name'
  ```
- If the failing step is the dep-install step → just rerun: `gh run rerun <runid> --repo <o>/<r> --failed`.
- A REAL lint failure (clang-format / ruff / mypy) fails at a **later** step, after deps installed. Do not blindly rerun those.
- An action-monitor can fully automate this: match the failing step name, rerun if it is the dep-install flake, and escalate only when a NON-dep-install step fails.

### 3. CodeQL variadic-pack false positives

`cpp/unused-local-variable` and `cpp/unused-static-variable` flag C++ variadic template parameter packs (`args`, `Rest`) as unused even when they are consumed via pack-expansion (`stringify(args)...`) or forwarding (`f(args...)`).

- **No code rewrite eliminates it.** Removing a `(void)sizeof...(args)` hack, or de-recursing the formatter, just MOVES the flagged line numbers; the autofix bot keeps pushing non-sticking "Potential fix for pull request finding…" commits.
- **Correct action = DISMISS AS FALSE POSITIVE** (after confirming the pack IS used):
  ```bash
  gh api --method PATCH repos/<o>/<r>/code-scanning/alerts/<n> \
    -f state=dismissed \
    -f dismissed_reason="false positive" \
    -f dismissed_comment="<reason>"
  ```
  **CRITICAL:** `dismissed_comment` is capped at **280 chars**. Longer → HTTP 422 `Only 280 characters are allowed`.
- Then resolve the associated review threads via GraphQL `addPullRequestReviewThreadReply` + `resolveReviewThread`. Map a thread to its alert by parsing `code-scanning/(\d+)` out of the comment body.

### 4. Auto-merge blocks on ANY failing check, even non-required

A PR can be `MERGEABLE` with ALL branch-protection-required contexts green, yet GitHub auto-merge will NOT fire while a NON-required check (Coverage, security/dependency-scan) is red. **Auto-merge is stricter than branch protection.**

- Find what is actually required:
  ```bash
  gh api repos/<o>/<r>/branches/main/protection \
    --jq .required_status_checks.contexts
  ```
- If the red check is non-required AND a real issue → fix it (do not bypass; the user may have said "fix all even if pre-existing"). Auto-merge fires once ALL checks (including pending non-required ones) reach a terminal state with no failures.
- **Note:** some repos have NO branch protection. There `BLOCKED` + `mergeable=UNKNOWN` just means GitHub is still computing mergeability; it merges a moment later — nothing to fix.

### 5. Dependency-gated PR cascade orchestration

When PR-B must merge before PR-A is safe (e.g. extraction-before-deletion), enforce the ordering with an **action-monitor** (a persistent background `gh`-poll loop) rather than serializing wall-clock:

- The monitor watches the gate PRs' state; when ALL gates show `MERGED`, it runs `gh pr merge <downstream> --auto --squash` to arm the held PR.
- It emits ONLY actionable transitions: a gate reaching `MERGED`, a required check failing (`CI-FAIL`), or the held PR appearing.
- Hold the downstream PR **UNARMED** (create it, run its CI, but do NOT arm auto-merge) until the monitor confirms the gates merged. This preserves the ordering invariant while CI runs in parallel.
- When a gate's squash-merge creates a conflict for a sibling PR, rebase the sibling onto `main` (see [[parallel-swarm-pr-conflict-reconciliation]]).

### 6. Unresolved review threads block merge with all checks green

A PR can be `MERGEABLE` with **every REQUIRED status check green** (build, integration-tests, unit-tests, All Build/Test Checks, All Static Analysis Checks, branch-protection-drift, …) and STILL sit `mergeStateStatus=BLOCKED` with auto-merge refusing to fire. This is **distinct from Trap 4** — there a *non-required* check was still red/pending; here ALL checks (required and relevant) are green. The gate is the HI ecosystem-standard branch-protection setting **`required_review_thread_resolution: true`**: GitHub's `github-advanced-security` (CodeQL) bot posts inline findings as **review threads**, and any unresolved thread blocks merge regardless of check status.

- **Detect.** `gh pr view <n> --json mergeStateStatus` shows `BLOCKED` while `gh pr checks <n>` shows all required green. The REST `reviewThreads` field is often empty/unavailable, so confirm via GraphQL:
  ```bash
  gh api graphql -f query='{ repository(owner:"OWNER",name:"REPO"){ pullRequest(number:N){ reviewThreads(first:50){ nodes{ isResolved path line comments(first:1){ nodes{ author{login} body } } } } }}}' \
    --jq '[.data.repository.pullRequest.reviewThreads.nodes[]|select(.isResolved==false)]|length'
  ```
  A non-zero count of unresolved threads authored by `@github-advanced-security` = this trap. (In the verifying session a PR that MERGED had **0** unresolved threads; the two BLOCKED ones had **6** and **3** — a direct correlation.)
- **Assess — do NOT blanket-resolve.** READ each unresolved thread's `path:line` + first comment before resolving. Classify:
  - **False positive (resolve):** many CodeQL findings are stale/false after a rebase — e.g. "unused local variable `_`" on a structured-binding discard `auto [it, _] = map.emplace(...)`; "unreachable static function" that IS used in a member-initializer like `RateLimiter limiter_{permissive_cfg()}`.
  - **Genuine (judgment call / author input):** e.g. an env-var used in a file path, a world-writable test fixture, a stack address stored non-locally. These deserve a real fix or a conscious, documented accept.
- **Document then resolve.** When resolving findings that were assessed-and-accepted (not fixed), post a documenting PR comment FIRST recording the per-finding accept-rationale (so the security observation is consciously accepted, not silently dropped), THEN resolve. Get each thread's node `id` from the same `reviewThreads` query and resolve via mutation:
  ```bash
  gh api graphql -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }' \
    -f id="<thread node id>"
  ```
- **Companion gotchas:**
  - **Amending re-runs CodeQL.** A force-push amend re-runs CodeQL on the changed file and can post NEW review threads. After an amend, re-check the unresolved-thread count before assuming the PR will merge.
  - **Slow static-analysis ≠ failure.** `clang-tidy` and `CodeQL (cpp)` showing `in_progress` is why the required aggregate `All Static Analysis Checks` has not reported yet. A PR can sit `BLOCKED` purely waiting on these slow jobs even when build/test are already green — do not mistake it for a real failure.

### 7. pr-policy fails when auto-merge is armed before implementation-go

The REQUIRED `pr-policy` gate FAILS when auto-merge is enabled BEFORE the PR carries the `state:implementation-go` label. Following the generic "auto-merge is mandatory" guidance and running `gh pr merge <N> --auto --squash` on a freshly-opened PR is the trap: the gate's **"Check 2: auto-merge matches implementation-review state"** emits `::error::Auto-merge is enabled before implementation review GO.` and fails the run. The gate is symmetric — it also fails the inverse with `::error::PR has state:implementation-go but auto-merge is not enabled.` when the label IS present but auto-merge is off. In these repos auto-merge must NOT be enabled until a reviewer (or the in-loop implementation reviewer) applies `state:implementation-go`; a label-triggered workflow then arms `--auto --squash` automatically. This mirrors the in-code invariant `pr_manager.ensure_pr_auto_merge_deferred()`, which proactively DISABLES premature auto-merge.

- **Distinct from Traps 4 & 6.** There a non-required check (Trap 4) or an unresolved review thread (Trap 6) gated an otherwise-green PR. Here the act of arming auto-merge too early IS itself the failing REQUIRED check.
- **Diagnose by the failing CHECK + STEP.** The failing check is `pr-policy`; the failing step is "Check 2: auto-merge matches implementation-review state". Read the exact `::error::` line:
  ```bash
  gh run view <run-id> --log-failed | grep '::error::'
  #   "::error::Auto-merge is enabled before implementation review GO."  -> pre-armed too early
  #   "::error::PR has state:implementation-go but auto-merge is not enabled."  -> label present, arm it
  ```
- **Fix.** Do NOT pre-arm auto-merge on a fresh PR. If you already armed it, disable it and re-run the failed check — it flips fail→pass:
  ```bash
  gh pr merge <N> --disable-auto
  gh run rerun <run-id> --failed
  ```
  Then let the review→`state:implementation-go` label workflow arm `--auto --squash` for you. (These repos are squash-only — the label workflow uses `--squash`; do not arm `--rebase`.)

### Quick Reference

```bash
# Detect which STEP failed (flake vs real failure)
gh api repos/<o>/<r>/actions/jobs/<jobid> \
  --jq '.steps[]|select(.conclusion=="failure")|.name'

# Rerun only failed jobs (use for the just.systems dep-install flake)
gh run rerun <runid> --repo <o>/<r> --failed

# Dismiss a CodeQL variadic-pack false positive (comment must be <=280 chars)
gh api --method PATCH repos/<o>/<r>/code-scanning/alerts/<n> \
  -f state=dismissed -f dismissed_reason="false positive" \
  -f dismissed_comment="<=280 chars: pack is consumed via expansion/forwarding"

# What contexts are ACTUALLY required by branch protection
gh api repos/<o>/<r>/branches/main/protection \
  --jq .required_status_checks.contexts

# Arm auto-merge on a held downstream PR (once its gates merged)
gh pr merge <downstream> --auto --squash

# Confirm a pixi lock is v6 (the format CI's pinned pixi can load)
grep -m1 '^version:' pixi.lock   # expect: version: 6

# Count UNRESOLVED review threads (the hidden merge gate when all checks are green)
gh api graphql -f query='{ repository(owner:"OWNER",name:"REPO"){ pullRequest(number:N){ reviewThreads(first:50){ nodes{ isResolved path line comments(first:1){ nodes{ author{login} body } } } } }}}' \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[]|select(.isResolved==false)]|length'

# Resolve a review thread (after reading + documenting accept-rationale)
gh api graphql -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }' \
  -f id="<thread node id>"

# pr-policy "Check 2" failure: read the exact error, then un-arm premature auto-merge
gh run view <run-id> --log-failed | grep '::error::'
gh pr merge <N> --disable-auto      # un-arm auto-merge enabled before state:implementation-go
gh run rerun <run-id> --failed      # re-run pr-policy — flips fail->pass once auto-merge is off
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Regenerate `pixi.lock` with pixi 0.69 (`pixi update`) | Wrote lock-format v7; CI's older pixi can't load v7, so `Lint`/`Type-Check`/`dependency-scan` silently went red | Keep the lock at v6 — hand-edit it or regenerate with a v6-emitting pixi; verify with `pixi install --locked` |
| 2 | `git restore` stale worktree mods to discard them | The Safety Net BLOCKED `git restore` (irreversible discard is gated) | Print the command for the user to run; never `--force` an irreversible discard |
| 3 | Treated a fast (~20s) lint failure as a code error and re-ran blindly | It was the `just.systems` curl flake at the dep-install step, so the blind rerun wasted a cycle | Check the FAILING STEP NAME first; only rerun when it is the dep-install flake |
| 4 | Rewrote the logger to satisfy CodeQL unused-variadic-pack | Redesigned the variadic templates twice; CodeQL still flagged the pack, just at new line numbers | It is a known false positive — DISMISS the alert (≤280-char comment) and resolve threads instead of rewriting |
| 5 | Assumed a `MERGEABLE` PR with all required checks green would auto-merge | Auto-merge stalled on a non-required red check (Coverage) — auto-merge is stricter than branch protection | Query `required_status_checks.contexts`; fix the non-required red (don't bypass) so all checks reach a clean terminal state |
| 6 | Assumed a PR with all required checks green + MERGEABLE would auto-merge | `mergeStateStatus` stayed `BLOCKED` on `required_review_thread_resolution` — 6 unresolved CodeQL review threads gated it | Green required checks ≠ mergeable; query GraphQL `reviewThreads` for unresolved bot findings |
| 7 | Planned to resolve all CodeQL threads in bulk to unblock | Some findings were genuine (env-var file path, stack-address escape); blanket-resolving would silently drop real security observations | Read each thread's `path:line`+body; classify false-positive vs real; document accept-rationale before resolving; escalate genuinely-ambiguous ones |
| 8 | Ran `gh pr merge --auto --squash` on a fresh PR following the generic "auto-merge is mandatory" guidance | The REQUIRED `pr-policy` gate's "Check 2" fails `::error::Auto-merge is enabled before implementation review GO.` — auto-merge must not be armed before `state:implementation-go` | Don't pre-arm auto-merge; `gh pr merge <N> --disable-auto` + `gh run rerun <run-id> --failed`, then let the `state:implementation-go` label workflow arm `--auto --squash` |

## Results & Parameters

### Dismiss a CodeQL false positive (variadic pack)

```bash
gh api --method PATCH repos/<o>/<r>/code-scanning/alerts/<n> \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="Variadic pack consumed via expansion/forwarding; CodeQL mis-flags it."
# dismissed_comment MUST be <=280 chars or the call returns HTTP 422
#   "Only 280 characters are allowed"
```

### Required-contexts query (what auto-merge actually waits on minus non-required)

```bash
gh api repos/<o>/<r>/branches/main/protection \
  --jq .required_status_checks.contexts
```

### Failing-step diagnosis (flake vs real)

```bash
gh api repos/<o>/<r>/actions/jobs/<jobid> \
  --jq '.steps[]|select(.conclusion=="failure")|.name'
# "Install build dependencies (just + linters)"  -> just.systems flake, rerun
# a clang-format / ruff / mypy step               -> real lint failure, fix the code
```

### Rerun the flake

```bash
gh run rerun <runid> --repo <o>/<r> --failed
```

### Arm auto-merge on a held PR

```bash
gh pr merge <downstream> --auto --squash
```

### Un-arm premature auto-merge to clear the pr-policy gate

```bash
gh run view <run-id> --log-failed | grep '::error::'
#   "::error::Auto-merge is enabled before implementation review GO."
gh pr merge <N> --disable-auto   # auto-merge was armed before state:implementation-go
gh run rerun <run-id> --failed   # re-runs pr-policy "Check 2"; flips fail->pass
# Then let the review -> state:implementation-go label workflow arm --auto --squash
```

### pixi lock format check

```bash
grep -m1 '^version:' pixi.lock   # must read "version: 6" for CI's pinned pixi
# Verify acceptance with a pixi NEWER than CI's:
pixi install --locked
#   prints "lock file is up-to-date but uses an older format (v6)" and exits 0
#   => CI's older pixi will also accept it
```

### Key parameters

- `dismissed_comment` ≤ **280 chars** (HTTP 422 otherwise).
- pixi lock must stay at **`version: 6`** for CI's pinned pixi.
- Removing `[pypi-dependencies]` from `pixi.toml` requires editing/regenerating the lock in the SAME change, or `pixi-check` fails `lock-file not up-to-date with the workspace`.
- A ~20s `lint` failure at "Install build dependencies (just + linters)" is the `just.systems` flake — rerun, do not edit code.
- Auto-merge waits on ALL checks (required + non-required) reaching a clean terminal state; branch protection only gates the required ones.
- Hold a dependency-gated downstream PR UNARMED until its gates merge; arm with `--auto --squash` from the action-monitor.
- Do NOT pre-arm auto-merge before the PR has `state:implementation-go`, or the REQUIRED `pr-policy` gate's "Check 2" fails `Auto-merge is enabled before implementation review GO.`; un-arm with `gh pr merge <N> --disable-auto`, rerun the failed check, and let the label workflow arm `--auto --squash`.

### Verified On

| Repo | Context | PRs (all merged 2026-05-31) |
|------|---------|------------------------------|
| ProjectKeystone | Keystone pure-transport refactor (traps 1–5) | #577, #578, #579, #580, #581 |
| ProjectAgamemnon | Downstream consumers of the Keystone transport change (traps 1–5) | #419, #420, #421 |
| ProjectNestor | Unresolved CodeQL review threads gating merge (trap 6); resolving threads flipped BLOCKED→mergeable, both auto-merged 2026-06-02 | #101, #97 |
| ProjectHephaestus | pr-policy gate fails on auto-merge armed before `state:implementation-go` (trap 7); disabling auto-merge + rerunning flipped the failed check fail→pass (2026-06-06) | #1073, #1075, #1077 |

## Related Skills

- [[parallel-swarm-pr-conflict-reconciliation]] — rebasing a sibling PR when a gate's squash-merge conflicts.
- [[git-rebase-over-deletion]] — preferring rebase to discarding/deleting work.
- [[always-sign-commits]] — all commits must be `-S` signed and verified.
- [[squash-not-rebase-merge]] — HI repos disable rebase-merge; auto-merge with `--squash`.
- [[cpp-cmake-ci-build-and-test-fixes]] — C++/CMake CI build and test triage.
