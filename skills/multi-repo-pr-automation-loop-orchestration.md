---
name: multi-repo-pr-automation-loop-orchestration
description: "Use when: (1) running an automation loop (drive-prs-green, hephaestus-automation-loop, loop_runner.py, ci_driver.py) across multiple repos and it skips PRs, reports success incorrectly, silently no-ops, or never arms auto-merge, (2) a multi-repo swarm is orchestrating PRs across 3+ HomericIntelligence repos with sequential-within-repo merge ordering, (3) an ecosystem-wide sweep implements every planned issue across all repos in parallel waves, (4) the automation driver logs success but live GitHub state shows open failing PRs — always cross-check live state per repo before reporting done, (5) a hephaestus automation loop deadlocks because the drive-green phase skips iterations or the implementer returns early before labeling with state:implementation-go, (6) an org-wide issue backlog across 10+ repos needs parallel implementation with one signed auto-merge PR per issue, (7) automated review-plan files (claude-review-fix-*.md) need to be bulk-processed across stale PR branches, (8) _wait_for_pr_terminal polls the full timeout on a BLOCKED PR — add early-exit guarded by both _failing_required_check_names and _pending_required_check_names, (9) PLANNING (not driving) against a STALE completed-sweep / status-report issue (a myrmidon sweep report listing 'flagged for human' PRs, dated weeks ago) — re-verify the LIVE state of every flagged item before trusting ANY action item, because most have already changed state (merged, fixed, or re-gated) and the report's stated root causes are stale, (10) classifying an open PR's mergeStateStatus=BLOCKED at PLAN time: BLOCKED with ZERO failing AND zero pending required checks ⇒ branch-protection / review gate ⇒ the action is approve+merge, NOT a CI fix; BLOCKED with failing/pending checks ⇒ real CI work"
category: ci-cd
date: 2026-06-20
version: "1.3.0"
user-invocable: false
history: multi-repo-pr-automation-loop-orchestration.history
tags:
  - multi-repo
  - pr-automation
  - drive-prs-green
  - hephaestus-automation-loop
  - ci-driver
  - loop-runner
  - myrmidon-swarm
  - report-vs-live-state
  - silent-no-op
  - honest-reporting
  - wait-for-merge
  - auto-merge-armed
  - implementation-go-label
  - ecosystem-sweep
  - org-wide-swarm
  - batch-review-plan
  - sequential-within-repo
  - squash-auto-merge
  - homericintelligence
  - blocked-pr-early-exit
  - pending-required-checks
  - wait-for-pr-terminal
  - issues-scoped-drive-green
  - bot-pr-discovery-scope
  - stale-sweep-report-replan
  - completed-sweep-issue
  - blocked-zero-failures
  - branch-protection-review-gate
  - cheap-live-verification
  - re-verify-before-trusting
---

# Multi-Repo PR Automation Loop and Swarm Orchestration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | One canonical for driving PRs to green across many HomericIntelligence repos via an automation loop or a myrmidon swarm: make the driver report honestly (no silent no-op, wait for the real terminal state, gate "repo done" on live open-PR count), cross-check every run summary against live GitHub state before reporting success, unblock the loop-runner / implementer deadlocks (drive-green discovery + the `state:implementation-go` labeling deadlock), orchestrate parallel waves across 3+ repos with sequential-within-repo merge ordering, run ecosystem-wide and org-wide planned-issue sweeps, and bulk-process automated review-plan files across stale PR branches. |
| **Outcome** | Driver hardened across five ProjectHephaestus releases (PRs #833/#837/#839 → #876 → #879 → #1090) from "lies success" → "honest reporting" → "waits for the real outcome" → "re-arms, survives concurrency, resolves conflicts, never self-inflicts a lint failure" → "BLOCKED early-exit (PR #1090 closes #1088)". Existing-PR labeling deadlock shipped fixed (PRs #1073/#1075/#1077/#1079). Report-vs-live-state protocol surfaced honesty gaps merged as PR #849. Swarm pattern merged 87 PRs across 8 repos and ran ecosystem sweeps (51+ PRs / 78 issues retired, 0 broken-main events). Org-wide planned-issue swarm piloted ~51 signed squash-auto-merge PRs across 5 repos (430 plan-carrying issues detected). Batch review-plan processing cleared 14 OPEN PRs in ~20-30 min. v1.3.0 extends report-vs-live-state to PLAN time: re-planning a 20-day-stale completed-sweep report (Odysseus #299) found ~13 "flagged for human" PRs mostly already merged and every surviving root cause stale — adding the stale-report re-verify pattern, a plan-time BLOCKED-zero-failures-vs-with-failures classification, and four cheap live-state verification commands. |
| **Verification** | verified-ci |

## When to Use

- An automation loop (`drive-prs-green`, `hephaestus-automation-loop`, `loop_runner.py`, `ci_driver.py`) across multiple repos skips PRs, reports success wrongly, silently no-ops, or never arms auto-merge.
- The driver logs `pushed CI fixes for PR #N` but `gh pr view <N> --json headRefOid` shows the SAME SHA hours later.
- A run summary (`Driven: 8 / Failed: 4`, `_summary.json`) disagrees with the GitHub UI; you are about to tell a user "all repos are green".
- A `drive-green` phase prints `SKIP (no open issues)` / `SKIP (not final loop)` while failing PRs sit untouched, or a green PR never gets `state:implementation-go` so auto-merge never arms.
- A myrmidon swarm orchestrates PRs across 3+ repos with sequential-within-repo merge ordering (merge/conflict/CI-fix waves, Odysseus submodule pin bumps).
- An ecosystem-wide sweep classifies 500+ issues and implements them in parallel waves or bundle-PR-per-repo.
- An org-wide planned-issue backlog (issues carrying a `# Implementation Plan` comment) across 10+ repos needs one signed squash-auto-merge PR per issue.
- Automated review-plan files (`review-plan-*.md` + `review-*.json` with `phase=failed`) need bulk processing across 10+ stale PR branches.
- A `--issues`-scoped drive-green run still pulls in unrelated bot PRs or scans/arms every open PR and fails `rc=1` on out-of-scope PRs.
- You are PLANNING (not driving) against a STALE completed-sweep / status-report issue — e.g. a myrmidon "open-PR health + auto-fix sweep" report, marked COMPLETED weeks ago, that lists ~13 "flagged for human" PRs. Do NOT trust the report's action items or root causes; re-verify the LIVE state of every flagged PR first.
- The plan you are about to write classifies an open PR as `mergeStateStatus=BLOCKED` and you are tempted to prescribe a "CI fix" — first confirm whether BLOCKED is caused by failing/pending required checks (real CI work) or by a branch-protection / review gate with all required checks green (approve+merge, NOT a CI fix).
- A report's stated root cause is a specific defect (a stale lockfile format version, a not-yet-removed file, a workflow `--tmpfs …:noexec` mount) — verify it still exists at the live HEAD/branch before planning a fix for it; the fix may have already landed.

## Verified Workflow

### Quick Reference

```bash
# 1. SCAN — enumerate org repos with open PRs (dynamic, guard empty = rate limit)
REPOS=($(gh repo list HomericIntelligence --json name,isArchived \
  --jq '[.[] | select(.isArchived==false) | select(.name|test("Odysseus";"i")|not) | .name][]'))
[[ ${#REPOS[@]} -eq 0 ]] && { echo "ERROR: empty repo list — GraphQL rate limit"; exit 1; }

# 2. DRIVE — per repo, sequential-within-repo merge; parallelize ACROSS repos only
#    haiku=clean merges, sonnet=conflicts/CI fixes, opus=orchestrator only

# 3. ARM auto-merge — squash org-wide (rebase-merge disabled on all 12 HI repos)
gh pr merge <PR#> --auto --squash --repo HomericIntelligence/<repo>

# 4. GATE "repo done" on LIVE open-PR count (NOT gh pr list --limit, which caps)
gh api --paginate "/repos/<owner>/<repo>/pulls?state=open&per_page=100" | jq length

# 5. VERIFY report vs live state BEFORE reporting success
for r in "${REPOS[@]}"; do
  open=$(gh pr list --repo HomericIntelligence/$r --state open --json number --jq length)
  echo "$r live-open=$open"   # cross-check against the run's _summary.json
done
```

Re-verifying a STALE completed-sweep report at PLAN time (cheap live-state checks):

```bash
# A. Drop already-resolved flagged PRs: most are MERGED/CLOSED weeks later
gh pr view <N> --repo <O>/<R> --json state,mergeStateStatus,statusCheckRollup

# B. BLOCKED classification: all required contexts SUCCESS yet BLOCKED ⇒ review/branch-protection
#    gate ⇒ approve+merge, NOT a CI fix
gh api repos/<O>/<R>/branches/main/protection/required_status_checks --jq .contexts

# C. "Stale lockfile format-version" claim — decode + grep instead of trusting the report
gh api repos/<O>/<R>/contents/pixi.lock?ref=<BRANCH> --jq .content | base64 -d | grep -m1 '^version:'

# D. "Remove file X" prescription already landed? 404 ⇒ already gone (check branch .gitignore too)
gh api repos/<O>/<R>/contents/<file>?ref=<BRANCH>   # 404 ⇒ removed

# E. Root-cause WORKFLOW defect gone? grep the LIVE workflow files at HEAD, not the report snippet
gh api repos/<O>/<R>/contents/.github/workflows?ref=<BRANCH> --jq '.[].name'   # then grep each
```

End-to-end per-PR iteration in the driver (the four compounding guards):

```python
def drive_one_pr(worktree, pr_head_branch) -> bool:
    sync_worktree_to_remote_branch(worktree, pr_head_branch)        # G1: pre-sync to origin/<head>
    pre = run(["git","rev-parse","HEAD"], cwd=worktree).stdout.strip()
    run_agent_session(worktree, pr_head_branch)
    post = run(["git","rev-parse","HEAD"], cwd=worktree).stdout.strip()
    if post == pre:                                                 # G2: no-commit guard
        logger.warning("no new commit (HEAD %s); skipping push", pre[:8]); return False
    push_current_branch_with_lease_on_divergence(                  # G3: explicit refspec
        worktree, branch=pr_head_branch, push_ref=f"HEAD:{pr_head_branch}")
    return True
# G4: gate repo-done on gh api --paginate .../pulls?state=open returning 0.
```

### Detailed Steps

#### Honest CI-driver success path (drive-prs-green silent no-op detection)

A driver that reports `pushed CI fixes for PR #N` while the remote PR head SHA is
unchanged is silently no-op'ing. Three compounding bugs cause it; apply all four
guards in order (each catches what the next cannot):

1. **Pre-sync the worktree to `origin/<pr-head>` BEFORE the agent runs.** A local-branch-only
   `git rev-parse --verify` check falls through to `git worktree add -b <branch> ... main` on a
   clean clone, creating a NEW branch off `main` and ignoring `origin/<branch>`. Hard-reset:
   `git fetch origin <branch> && git reset --hard origin/<branch>` (safe — worktree is throwaway).
2. **Snapshot HEAD pre/post agent; `pre == post` ⇒ hard-fail the iteration.** Agent return is NOT
   proof of work (it may have resumed an old transcript and correctly decided nothing was needed).
3. **Push with explicit refspec `HEAD:<pr-head-branch>`, never bare `HEAD`.** Bare `git push origin
   HEAD` lands on whatever stray branch the agent checked out. Preserve the refspec through the
   `--force-with-lease=<branch>` retry.
4. **Gate "repo done" on `gh api --paginate /repos/<o>/<n>/pulls?state=open&per_page=100` == 0** —
   not `gh pr list --limit 100` (silent cap). Per-issue success ≠ repo cleanliness.

**Wait for the terminal state (v1.1.0+).** An armed-and-merging PR is NOT a failure. Do not exit
`rc=1` on any open PR. `_wait_for_pr_terminal(issue, pr)` polls `MERGED|CLOSED|FAILING|DIRTY|BLOCKED|TIMEOUT`
with exponential backoff capped 60s, bounded by `HEPH_PR_MERGE_MAX_WAIT` (default 1800s); a required
check concluding `failure` returns `FAILING` immediately. Partition still-open PRs: truthy
`autoMergeRequest` ⇒ `armed_pending` (WARNING, not failure); falsy ⇒ `needs_action` ⇒ `rc=1`.

**BLOCKED early-exit (v1.3.0 / PR #1090 closes #1088).** `mergeStateStatus=BLOCKED` has two causes:
(a) branch-protection gate (e.g. unresolved required review threads) — **never self-heals**, the driver
will timeout in 30 min; and (b) required CI checks still in-flight — **transient, must keep polling**.
GitHub uses `BLOCKED` for BOTH causes, so a naive early-exit on `BLOCKED + not failing` is wrong when
checks are still pending. The correct guard:

```python
if merge_status == "BLOCKED":
    failing = self._failing_required_check_names(pr_number)
    if not failing:
        pending = self._pending_required_check_names(pr_number)
        if not pending:
            # All required checks concluded green but still BLOCKED →
            # definite branch-protection gate (unresolved threads etc.).
            # Leave armed and exit early — nothing the driver can fix.
            logger.warning(
                "PR #%d BLOCKED by branch-protection gate (0 failing, 0 pending required checks);"
                " leaving armed and exiting poll early",
                pr_number,
            )
            return "BLOCKED"
        # pending checks exist — keep polling (transient BLOCKED)
    # failing checks exist — keep polling (will return FAILING on conclusion)
```

`_pending_required_check_names` checks `c.get("status") != "completed"` for required checks (complement
of `_failing_required_check_names` which checks `conclusion == "failure"`). Handle `"BLOCKED"` in
callers: `_drive_issue` ⇒ `WorkerResult(success=True, pr_number=pr_number)` (leave armed, nothing to
fix); `_check_arming_on_drive_start` ⇒ same as `TIMEOUT` (leave armed, return success).

**Re-arm after a fix, survive concurrency, resolve DIRTY, never self-inflict lint (v1.2.0).**
After a fix returns `fixed=True`, re-enter check→arm→wait ONCE (`_recheck_and_arm_after_fix`) — a
fix re-triggers CI and the now-green PR otherwise sits CLEAN-but-unarmed forever. Wrap the
deterministic-uuid5 `--session-id` resume in try/except (3× backoff) then fall back to a fresh
`uuid4` so a collision under parallel workers is never terminal. Add `mergeStateStatus` to
`_gh_pr_state`, return `"DIRTY"` and run `_resolve_dirty_pr` (mechanical rebase → agent conflict
prompt). The force-engagement prompt FORBIDS committing a blocker file (use a `BLOCKED:` line) and
requires every edited file to pass the repo's own linters with NO rule disabled — and avoids
committing to bot PRs (a commit orphans a Dependabot PR; recovery is `@dependabot recreate`).

**A `--issues`-scoped drive-green run must touch ONLY those issues' PRs (v1.2.0 / PR #1110).**
When an operator scopes a `ci_driver` run with `--issues N1,N2`, the run must not over-reach into the
rest of the repo. The failing-PR discovery path was ALREADY correctly gated on `if not self.options.issues:`
(#819), but two other paths leaked repo-wide work into a scoped run and had to be fixed to mirror it:

1. **Bot-PR discovery is default-ON** (`--include-bot-prs`, default on, #848). A scoped `--issues 725,711`
   run still ran `_discover_bot_prs()` and pulled in an unrelated Dependabot PR (#1032):
   `Found 3 PR(s) to drive: {725:996, 711:997, 1032:1032}`. Gate it the same way as failing-PR discovery —
   the no-args backlog sweep keeps bot PRs, a scoped run does not:

   ```python
   if self.options.include_bot_prs and not self.options.issues:
       ...  # only discover bot PRs on the UNSCOPED backlog sweep
   ```

2. **The repo-done gate + `_arm_all_unarmed_open_prs` scanned ALL open PRs.** `_list_open_prs_remaining()`
   returns the FULL paginated open-PR set (#838), so a scoped run armed unrelated PRs and failed
   `rc=1` with `"Repo not done: 59 open PR(s) need manual action"` — for PRs the operator never selected.
   In `run()`, after building `self.open_prs_remaining`, FILTER it to only the PRs this run drove
   (`pr_map.values()`) when scoped, so the done-gate and arming consider only scoped PRs; the unscoped
   sweep keeps full repo-wide behavior:

   ```python
   if self.options.issues and self.open_prs_remaining:
       scoped = set(pr_map.values())
       self.open_prs_remaining = [pr for pr in self.open_prs_remaining if pr.get("number") in scoped]
   ```

The plan + implement phases already scope correctly (the loop passes the discovered issue list via
`--issues`); only drive-green over-reached. A scoped validation run (`--issues 725,711`) is the right way
to test one or two PRs without driving the whole backlog. Tests that asserted bot PRs union even when
`--issues` is set were asserting the BUG — flip them to assert the union only on the UNSCOPED path
(clear `options.issues=[]`).

#### Report-vs-live-state verification

Automation summaries are observation reports, not ground truth. `Driven: 8` only means the driver
was invoked, not that PRs reached green. NEVER report success from `_summary.json` alone — cross-check
live GitHub state per repo first:

1. Read the summary, then suspect every field (banner counts derive from rc codes set by gates that
   fire on noise).
2. For every "Driven" repo, `gh pr list --repo <o>/<r> --state open` — non-zero live count while the
   log says `Found 0 PR(s) to drive` ⇒ architecturally blind (PRs without `Closes #<open-issue>`,
   e.g. Dependabot, are invisible to issue-driven discovery).
3. For every claimed-pushed PR, confirm the head commit landed inside the run window:
   `gh pr view <pr> --json headRefOid,commits`.
4. For every "Failed" repo, classify: done-gate-on-noise / architecturally-blind / no-new-commit /
   real-crash. Only a real push-fail-or-crash warrants escalation. A "Failed" repo can have shipped a
   merged fix (one session: `Telemachy #246` MERGED 29s after it was reported failed).
5. Deliver the Reality-vs-Claim table, not the banner.

#### Planning against a STALE completed-sweep / status-report issue (re-verify before trusting)

The report-vs-live-state rule applies just as hard at PLAN time as at drive time. A myrmidon
"open-PR health + auto-fix sweep" issue is a SNAPSHOT report: it lists "flagged for human" PRs with
stated root causes, and is often marked COMPLETED. Re-planning that issue weeks later, **every action
item and every root cause is suspect** — re-verify each flagged PR's LIVE state before writing any
plan step. In one session (Odysseus #299, report dated 2026-05-31, re-planned 2026-06-20, 20 days
later): of ~13 "flagged for human" PRs, MOST were already MERGED; only 7 remained open, and the report's
stated root causes for the survivors had all gone stale. The reusable triage:

1. **`gh pr view <N> --json state,mergeStateStatus,statusCheckRollup` every flagged PR first.**
   Most are already MERGED/CLOSED — drop them from the plan before doing anything else.

2. **Classify each still-open BLOCKED PR by its required-check state (PLAN-time analogue of the driver's
   v1.3.0 early-exit).** `mergeStateStatus=BLOCKED` with ZERO failing AND zero pending required checks =
   a branch-protection / review gate → the action is **approve+merge, NOT a CI fix**. BLOCKED with
   failing/pending required checks = real CI work. Confirm by comparing the rollup to the required
   contexts:

   ```bash
   # required contexts the branch enforces
   gh api repos/<O>/<R>/branches/main/protection/required_status_checks --jq .contexts
   # this PR's check conclusions — if every required context is SUCCESS yet state is BLOCKED,
   # the blocker is a review/branch-protection gate, not CI
   gh pr view <N> --json mergeStateStatus,statusCheckRollup
   ```

   Evidence: 4 Scylla dependabot PRs had all 17 checks SUCCESS but were BLOCKED — by a newly-added
   1-approving-review rule (Odysseus commit d34e291) — so the action was approve+merge, not "fix CI".

3. **Verify a "stale lockfile / format-version" root-cause claim cheaply** by decoding the file at the
   relevant refs and grepping the version, instead of trusting the report's quoted version:

   ```bash
   gh api repos/<O>/<R>/contents/pixi.lock?ref=<BRANCH> --jq .content | base64 -d | grep -m1 '^version:'
   ```

   Evidence: the report's "Scylla pixi.lock format-v7 vs CI max-v6" root cause was GONE — both `main`
   and the dependabot branches returned `version: 6`.

4. **Confirm a prescribed fix hasn't ALREADY landed.** A `404` on the file the report says to "remove"
   means it is already gone; also check the branch `.gitignore`:

   ```bash
   gh api repos/<O>/<R>/contents/<file>?ref=<BRANCH>   # 404 ⇒ already removed
   ```

   Evidence: Nestor #103's prescribed fix ("remove `CMakeUserPresets.json`, gitignore it") had already
   landed (404 on the file at `ref=12-impl`; entry present in the branch `.gitignore`). The remaining
   blocker was purely DIRTY/CONFLICTING with 0 failing checks → action became **rebase**, not the
   report's fix. Several AchaeanFleet PRs (#691) similarly just needed a rebase to pick up fixes already
   on `main`.

5. **Confirm a root-cause WORKFLOW DEFECT is gone by grepping the live workflow files at HEAD**, not the
   report's quoted snippet. Evidence: the "codebuff tmpfs-noexec" root cause was gone — a grep of all
   workflows for `tmpfs|/home/agent/.config|codebuff` found no `--tmpfs …:noexec` mount and no smoke-test
   step. Also watch for the blocker-file anti-pattern in survivors (AchaeanFleet #683 carried a stray
   committed `.github/CI_FIX_683.md` plus a conflict).

**Known gaps when re-planning from a report (record these in the plan honestly).** The cheap live-state
DISCOVERY/triage above is verified-local — the queries were run and observed. But a re-plan's prescribed
FIXES are unverified hypotheses until executed. Mark them as such. From the same session, three honest
gaps that the report seeded and were NOT independently confirmed:

- A "populate `GIT_COMMIT`/`BUILD_UID`/`BUILD_GID` in `_required.yml`" fix (Keystone #568) where the
  actual `podman-compose up` job and the `docker-compose.yml` name template were NEVER opened — the
  `env:` snippet and the `BUILD_UID/GID=1000` values are guesses from the report, not from reading files.
- "Scylla requires 1 approving review" was INFERRED from an Odysseus commit title, not confirmed against
  Scylla's live ruleset (only that all required *status* contexts pass while state is BLOCKED).
- Dependabot rebase mechanics (`@dependabot rebase` vs manual force-push) were not tested live.

#### Hephaestus loop deadlocks (drive-green discovery + labeling)

Two complementary deadlocks keep `hephaestus-automation-loop` from driving PRs to green:

**(A) drive-green discovery (NOT shipped — use the bypass).** `--phases drive-green --loops N>1` is
structurally unreachable (the not-final-loop gate + zero-work early-exit). `--loops 1` prints
`SKIP (no open issues)` because discovery walks `@me`-scoped open issues, not failing PRs. Bypass:

```bash
cd /home/<you>/Projects/<repo>
issues=$(gh pr list --state open --json number,body,statusCheckRollup --limit 200 --jq '
  .[] | select((.statusCheckRollup//[])|map(.conclusion)|any(.=="FAILURE" or .=="CANCELLED" or .=="TIMED_OUT"))
      | .body | capture("Closes #(?<n>[0-9]+)").n' | sort -u)
pixi run python /home/<you>/Projects/ProjectHephaestus/scripts/drive_prs_green.py \
  --issues $issues --force-run   # --force-run / HEPH_CI_DRIVER_FORCE=1 escapes the HEPH_LOOP_INDEX gate
```

Filed as #818-#821 (phase model / PR-based discovery / optional `--issues` / `--all` for non-`@me`).

**(B) existing-PR labeling deadlock (SHIPPED FIX).** `state:implementation-go` is added in exactly
one place (`mark_pr_implementation_go`, after the in-loop review). But `_implement_issue`
hard-returned early on existing PRs (the "skip existing PRs" shortcut), so they were never reviewed
→ never labeled → `ci_driver.py` gates (:330/:627/:965) refused to arm → green-but-unmergeable forever
(9 PRs observed). Fix: replace the skip with `sync_worktree_to_remote_branch` (hard-reset is the
anti-clobber mechanism), let existing PRs enter the review→address loop, gate idempotency on the
TERMINAL GO/NO-GO label. Shipped as PRs #1073/#1075/#1077/#1079. Load-bearing facts: sessions resume
by deterministic uuid5 of `(repo, issue, agent)` (NOT the persisted `session_id` — `state-{n}.json`
vs `issue-{n}.json` path bug was invisible for Claude, broke Codex); the only way to re-raise a
resolved review thread is a NEW inline thread (no GitHub "unresolve" mutation).

#### Swarm orchestration across 3+ repos

Use a myrmidon swarm with wave/phase ordering; **sequential within a repo, parallel across repos**:

- **Phase 1 Scan** (opus): enumerate org repos, classify each PR MERGEABLE / DIRTY / BLOCKED / Dependabot.
- **Phase 2 Wave 1** (haiku, one per repo): merge clean PRs oldest-first. **Cap 5 merges/repo/pass** —
  each merge advances `main` and cascades downstream branches to DIRTY; rescan + rebase before continuing.
- **Phase 3 Wave 1b** (sonnet): rebase conflicts (`git fetch origin && git rebase origin/main &&
  git push --force-with-lease`). At scale ~15-20% of DIRTY PRs are subsumed (`git diff origin/main...HEAD`
  empty) — close, don't rebase. `BLOCKED` + empty `statusCheckRollup` = CI not started yet (transient,
  wait 60s). Under Safety Net, replace `git restore --theirs` with `git show MERGE_HEAD:<path> > <path>`.
- **Phase 4 Wave 1c** (sonnet): read CI logs, fix, push, poll to green, merge.
- **Phase 5 Wave 2** (sonnet): update Odysseus submodule pins ONLY after every repo's open PRs are
  merged; never pin to a stale feature-branch SHA (`git branch -r --contains HEAD`).
- Detect auto-merge support per repo (`gh api repos/<o>/<r> --jq .allow_auto_merge`); on repos with it
  disabled use direct `--rebase`, never `--auto --rebase` (GraphQL error). For automation loops, resolve
  Python via `pixi run which python`, export `PYTHONPATH`, guard empty repo list = rate limit.

**Direct Agent fan-out** when the parent already planned: write the brief once to
`~/.tmp/<topic>-brief.md`, dispatch short pointer-prompts per repo (~30K parent-token savings for a
14-agent dispatch) instead of re-invoking `/hephaestus:myrmidon-swarm` (which re-runs Phase 1).

#### Ecosystem-wide and org-wide sweeps

- **Ecosystem sweep**: Phase-0 parallel classifier swarm (one agent/repo, {EASY,MEDIUM,HARD,META,
  ALREADY_DONE}) → manual close-batch (NEVER close blindly; `gh issue view N` first) → wave (PR-per-issue,
  cap ~20) or bundle (bundle-PR-per-repo, cap 10 issues) → CVE unblock → rebase cascade → CI triage.
  Every wave-agent prompt: `git fetch && git rebase origin/main` first, a stale-check pre-action, a
  PRECOMMIT_STALL abort (>60s ⇒ `SKIP=...` or `--no-verify`), a COVERAGE-DELTA guard, `--auto --squash`.
  Phase-0 ALREADY_DONE is advisory (misses ~15%); always add a per-agent stale-check. For Phase-4
  rebase cascades use a SEQUENTIAL loop in fresh worktrees (never parallelize rebase against one clone);
  `:2:file` = upstream during rebase (ours/theirs inverted). Parallel `--admin` merge against one base
  hits the GraphQL stale-base race (~24% at concurrency 5) — drain sequentially.
- **Org-wide planned-issue swarm**: the "has a plan" signal is a `# Implementation Plan` issue COMMENT,
  not the `planning` label. Pre-warm gpg-agent once at session start. Dispatcher sub-agents do read-only
  TRIAGE only (sub-agents have no Agent/Task tool); **L0 fans out the implementers itself in waves**
  (`run_in_background`, `isolation: worktree`, `model: sonnet`, branch from fresh `origin/main`). One
  signed (`-S`) auto-merge PR per issue with `Closes #<N>` on its own line, `--auto --squash`. Dedup
  via closing-keyword regex on open PR bodies, NOT `--search "in:body #N"` (substring false positives:
  `#4` matches `#44`). Verify signatures via REST `gh api .../commits/<sha> --jq .commit.verification.verified`
  (GraphQL lags). Implementers EXECUTE the plan but RECONCILE divergences (plans predate refactors).

#### Batch review-plan pipeline

Bulk-process automated `review-plan-*.md` + `review-*.json` (`phase=failed`) across stale PR branches:

1. **Triage**: for each `review-*.json`, read `phase` / `pr_number` / `error`; cross-reference PR state.
   `failed`+OPEN ⇒ process; `failed`+MERGED+CI-flake ⇒ skip; `completed` ⇒ skip.
2. **Check for unpushed local fix commits** first: `git -C <wt> rev-list --count origin/<branch>..HEAD`
   — many worktrees already have a fix commit (the push is what failed); just rebase + push.
3. **Repair corrupted files** from the `git add EADME.md` typo bug: `git checkout -- README.md
   docs/dev/release-process.md`.
4. **Create missing worktrees, bulk-rebase onto `origin/main`, push `--force-with-lease`.** On conflict,
   detect real markers with line-anchored grep `^<<<<<<` (YAML `=====` echo lines are NOT markers).
5. **Enable auto-merge** on all fixed PRs and verify state + `autoMergeRequest` presence.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bare `git push origin HEAD` after the agent returns | Pushed HEAD bare, logged success on `rc==0` | Agent had checked out a stray `<issue>-fix-ci` branch; push landed there, PR head unchanged | Always pass explicit refspec `HEAD:<pr-head>` and preserve it through the force-with-lease retry |
| Trust worktree-create to land on the PR head | Local-branch-only `git rev-parse --verify` check | Fell through to `git worktree add -b <branch> ... main`, creating a new branch off main, ignoring `origin/<branch>` | Driver MUST `fetch origin <branch>` + `reset --hard origin/<branch>` before the agent runs |
| Skip the no-commit guard, push whatever HEAD points to | Assumed "agent returned ⇒ did work ⇒ safe to push" | Agent resumed an old transcript, returned in seconds with no commit; force-with-lease exited 0 (HEAD==remote) | Snapshot HEAD pre/post; `pre==post` is a hard iteration failure — skip the push |
| Treat per-issue success as "repo done" | Printed "Driven: ProjectX" when every input issue returned success | PRs outside the input list (Dependabot, auto-merge-waiting) sat open while the script reported done | Gate repo-done on `gh api --paginate .../pulls?state=open` == 0, not `gh pr list --limit` (silent cap) |
| Exit `rc=1` on ANY open PR (including armed-and-merging) | Blunt done-gate marked 7/15 repos FAILED while every PR was armed and merging | Driver observed-and-returned instead of waiting for the real outcome | Partition open PRs: truthy `autoMergeRequest` ⇒ WARNING; falsy ⇒ `rc=1`; add `_wait_for_pr_terminal` |
| Return success the instant a fix lands | `_attempt_ci_fixes` returned on `fixed=True`, never re-arming | The fix re-triggers CI; the now-green PR sat CLEAN but auto-merge un-armed forever | Re-enter check→arm→wait once via `_recheck_and_arm_after_fix`; mock it in tests too |
| Leave the `--session-id` resume fallback unguarded | Deterministic uuid5 id, unguarded resume on create-collision | Two parallel workers raced before the transcript JSONL was on disk; the error killed the drive | Wrap resume in try/except (3× backoff), then fall back to a fresh `uuid4` so a collision is never terminal |
| Wait out TIMEOUT for a DIRTY armed PR | `_gh_pr_state` fetched no `mergeStateStatus` | Could not tell pending from conflicted; waited the full 1800s every run forever | Add `mergeStateStatus`, return `"DIRTY"`, run `_resolve_dirty_pr` (rebase → agent conflict prompt) |
| BLOCKED early-exit guarded only by `not failing` (v1.3.0) | Added early-exit on `mergeStateStatus=BLOCKED` when `_failing_required_check_names` returns empty — no pending check | GitHub reports `BLOCKED` for both (a) branch-protection gates (unresolved threads — never self-heals) AND (b) required checks still in-flight (transient — must keep polling). Guard on `not failing` alone exits early while CI is still running, abandoning a PR that would have self-healed | Guard on BOTH: `not failing` AND `not pending` (`_pending_required_check_names` returns empty). Only then is BLOCKED definitively a branch-protection gate (all required checks concluded green). If either failing OR pending is non-empty, keep polling. |
| Tell the agent to commit a blocker file | Prompt said "commit a file documenting the blocker" | The `CI_BLOCKER.md` itself failed markdownlint (turning one red check into two) and orphaned Dependabot PRs | Forbid the blocker file (use a `BLOCKED:` line); require every edited file lint-clean, no rule disabled |
| Trust the summary banner / `rc=0` | Reported from `_summary.json` (`Driven 8 / Failed 4`) | "Driven" only means the driver was invoked; 7/8 had 0 in-scope PRs, 3/4 "Failed" were false | Cross-check live `gh pr list --state open` per repo before reporting; classify each failure mode |
| Plan directly from a completed-sweep report's action items | Took the ~13 "flagged for human" PRs and their stated root causes from a 20-day-old myrmidon sweep report (Odysseus #299) as the plan input | Most flagged PRs were already MERGED (only 7 still open) and every surviving root cause was stale (lockfile version, removed file, workflow mount) | Re-`gh pr view` every flagged PR FIRST; drop merged/closed ones; re-verify each root cause at live HEAD before planning any fix |
| Prescribe a "CI fix" for a BLOCKED PR at plan time | Saw `mergeStateStatus=BLOCKED` and assumed CI work, as the report implied | 4 Scylla PRs had all 17 required checks SUCCESS but were BLOCKED only by a newly-added 1-approving-review rule — a CI fix would have been wasted effort | At plan time classify BLOCKED the same way the driver does: 0 failing AND 0 pending required checks ⇒ branch-protection/review gate ⇒ approve+merge, NOT a CI fix |
| Trust the report's "stale pixi.lock format-v7 vs CI v6" root cause | Believed the report's quoted lockfile format version | `base64 -d` of `pixi.lock` at `main` AND the dependabot branches returned `version: 6` on both — the root cause was already gone | Decode the file at the actual refs and grep the version (`gh api .../contents/pixi.lock?ref=B --jq .content \| base64 -d \| grep '^version:'`) instead of trusting the report |
| Plan the report's prescribed file-removal / workflow fix | Was about to plan "remove CMakeUserPresets.json + gitignore it" (Nestor #103) and "remove the tmpfs:noexec mount" (AchaeanFleet) | Both had ALREADY landed — the file 404'd at `ref=12-impl` and was in the branch `.gitignore`; grep of live workflows found no `--tmpfs …:noexec` mount | Confirm the fix hasn't shipped: `gh api .../contents/<file>?ref=B` (404 ⇒ removed), grep the LIVE workflow files at HEAD; the residual blocker was just a rebase, not the report's fix |
| Record report-seeded fixes as verified in the plan | Wrote the Keystone `_required.yml` env fix + "Scylla needs 1 review" + dependabot-rebase steps as if confirmed | The compose job/name-template were never opened (env keys + `BUILD_UID/GID=1000` guessed), the review rule was inferred from a commit title, and rebase mechanics were untested | Mark report-seeded prescribed fixes as UNVERIFIED hypotheses with a "Known gaps" note; only the live-state DISCOVERY queries were verified-local |
| `hephaestus-automation-loop --phases drive-green --loops N` | Increased loop budget / set `--loops 1` | Not-final-loop gate + zero-work early-exit make N>1 unreachable; `--loops 1` discovers `@me` issues not PRs | Bypass via `drive_prs_green.py --issues <N> --force-run`; fix is PR-based discovery (#818-#821) |
| "Skip existing PRs to avoid clobbering" early-return | `_implement_issue` hard-returned before the review loop | Existing PRs never reviewed → never labeled `state:implementation-go` → never armed; 9 green PRs stuck | Replace the skip with `sync_worktree_to_remote_branch`; gate idempotency on the terminal label |
| Run drive-green with `--issues` but leave bot-PR discovery + the open-PR done/arming gate repo-wide | Scoped `--issues 725,711` but `_discover_bot_prs()` stayed default-ON and `_list_open_prs_remaining()` returned the full paginated open-PR set | Scoped run pulled in unrelated Dependabot PRs (e.g. #1032) and armed/failed `rc=1` on all 59 open PRs the operator never selected | Gate bot-PR discovery on `not options.issues` (mirror the #819 failing-PR gate) and filter the done-gate/arming to `pr_map.values()` when scoped; the unscoped sweep stays repo-wide |
| Parallel PR merges within one repo | Merged #4/#5/#6 in parallel on one base | #6 conflicted when #4/#5 advanced main | Merge sequentially within a repo (oldest-first); parallelize only across repos |
| Unlimited clean merges per wave | Tried to merge 39 CLEAN PRs in one pass | Each merge advanced main, cascading 24+ to DIRTY | Cap 5 merges/repo/pass; rescan + rebase before continuing |
| Parallel rebase / parallel `--admin` merge | One agent per branch / 5-concurrent admin merges on one base | Agents clobbered each other's checkout; admin merge hit GraphQL stale-base race (13/17 failed) | Sequential loop in fresh worktrees; `--admin` bypasses protection, not the mergeability race |
| `gh pr merge --auto --rebase` org-wide | Used the myrmidon-swarm template default | All 12 HI repos disable rebase-merge; `--rebase` silently never arms | Hardcode `--auto --squash`; verify `gh api repos/<o>/<r> --jq .allow_squash_merge` first |
| `Closes #N` in a markdown table / comma-list | Bundle PR body listed issues in a table / `closes #A, #B` | GitHub ignores closing keywords in tables; honors only the first in a comma-list | `Closes #A. Closes #B.` — one keyword per issue, period-separated, at the TOP of the body |
| Two-level swarm (dispatcher sub-agents spawn implementers) | Documented dispatcher→implementer two-level fan-out | Sub-agents have no Agent/Task tool at the second level | Dispatchers do read-only TRIAGE only; L0 fans out implementers itself in waves |
| `gh pr list --search "in:body #N"` for PR dedup | Substring search of open PR bodies | `#4` matched `#44`/`#42` — unrelated issues looked covered | Parse closing keywords with regex, flatten, unique |
| Trust GraphQL signature / Phase-0 ALREADY_DONE | Read GraphQL `signature.state`; trusted classifier buckets | GraphQL lags REST by minutes; classifiers miss ~15% ALREADY_DONE | Verify via REST `gh api .../commits/<sha>`; add a per-wave-agent stale-check |
| Push MERGED-PR fix commits / rebase without checking local state | Pushed per review-plan without checking PR state or unpushed commits | MERGED PRs can't receive pushes; many worktrees already had unpushed fix commits | Check PR state + `rev-list --count origin/<branch>..HEAD` before choosing rebase vs push |
| `grep -c "<<<<"` to detect conflict markers | Counted `=====` YAML echo lines as conflicts | YAML workflows use `=====` legitimately | Use line-anchored `grep -n "^<<<<<<"` |

## Results & Parameters

### Driver hardening (ProjectHephaestus, all merged to main)

| PR | Closes | What changed |
| ---- | -------- | -------------- |
| #833 | #832 | `sync_worktree_to_remote_branch` + `push_ref` refspec preserved through lease-retry |
| #837 | #836 | no-commit guard: compare `git rev-parse HEAD` pre/post agent, skip push if unchanged |
| #839 | #838 | repo-done gated on `gh api --paginate .../pulls?state=open` == 0 |
| #876 | — | v1.1.0: `_wait_for_pr_terminal`, robust Dependabot arming, honest exit-gate partition, bounded no-commit retry |
| #879 | #878 | v1.2.0: `_recheck_and_arm_after_fix`, guarded session-id resume → fresh uuid4, `mergeStateStatus`/`DIRTY`/`_resolve_dirty_pr`, lint-clean blocker prompt. Suite: 1011 passed |
| #1073/#1075/#1077/#1079 | #1072/#1074/#1076/#1078 | existing-PR review→label deadlock fix: enter review loop, origin-sync anti-clobber, session-path fix, review_validator, bot-thread resolve |
| #1090 | #1088 | v1.3.0: BLOCKED early-exit in `_wait_for_pr_terminal` — guarded by both `_failing_required_check_names` and new `_pending_required_check_names`; handle `"BLOCKED"` in `_drive_issue` and `_check_arming_on_drive_start` callers. Suite: 3402 passed. |
| #1110 | — | scope drive-green to `--issues`: gate bot-PR discovery on `include_bot_prs and not options.issues` (#848/#819); filter `open_prs_remaining` to `pr_map.values()` when scoped so the done-gate + `_arm_all_unarmed_open_prs` consider only scoped PRs. Full `ci_driver` suite green in CI; PR CLEAN/MERGEABLE. |

### Org merge policy (all 12 HomericIntelligence repos)

```json
{ "allow_rebase_merge": false, "allow_squash_merge": true, "allow_auto_merge": true, "required_approving_review_count": 0 }
```

A green PR with `--auto --squash` armed merges itself (CI required, 0 approvals).

### Agent tier + scale reference

| Task | Tier | | Scale | Agents | Time |
| ---- | ---- |-| ----- | ------ | ---- |
| Merge clean PRs | Haiku | | 5 repos, 2-4 PRs | 5 Haiku + 2 Sonnet | ~30-45 min |
| Conflicts / CI fixes | Sonnet | | 8 repos, 87 PRs | 6 Haiku + 8 Sonnet | ~8h (incl. CI waits) |
| Orchestrate / verify | Opus | | ecosystem sweep | 5 classifier + 50-65 wave | <24h |

### Sweep statistics (ecosystem + org-wide)

| Metric | v1 PR-per-issue | v2 bundle-per-repo | org-wide planned |
| ------ | --------------- | ------------------ | ---------------- |
| Repos | 5 | 11 | 12 (430 plan issues) |
| PRs | 51 merged | 11 (7 merged) | ~51 piloted (5 repos) |
| Issues retired | 78 | ~50 | — |
| Broken-main events | 0 | 0 | 0 |

### Admin-merge concurrency (same base branch)

| Concurrency | Success |
| ----------- | ------- |
| 1 (sequential) | 100% |
| 2-3 | ~80-90% |
| 5 | ~24% (4/17) |

### Batch review-plan distribution (51 plans, one session)

`completed` ~27 skip · `failed`+MERGED+flake ~12 skip · `failed`+OPEN+rebase ~8 · unpushed-fix ~6 ·
merge-conflict ~1.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Driver honest-success path | PRs #833/#837/#839 (guards) → #876 (wait-for-merge) → #879 (re-arm/concurrency/DIRTY/lint) → #1090 (BLOCKED early-exit closes #1088). Suite 3402 passed; verified-ci (mypy 320 files clean, ruff clean, all pre-commit hooks). |
| ProjectHephaestus | Scoped drive-green honors `--issues` | PR #1110: bot-PR discovery gated on `not options.issues` (mirror #819); `open_prs_remaining` filtered to `pr_map.values()` when scoped so the done-gate + arming consider only scoped PRs. Repro: `--issues 725,711` pulled in Dependabot #1032 and failed `rc=1` on all 59 open PRs before the fix. Full `ci_driver` suite green in CI; verified-ci. |
| ProjectHephaestus | Report-vs-live-state | Run `20260531T190615Z`: banner `Driven 8 / Failed 4` decomposed to 1 honest-idle + 7 architecturally-blind / 1 real-bug + 3 false-failures; honesty gaps merged as PR #849. `Telemachy #246` MERGED 29s after reported failed. |
| ProjectHephaestus | Loop deadlocks | drive-green discovery #818-#821 (NOT shipped, bypass verified live 2026-05-30); existing-PR labeling deadlock shipped as PRs #1073/#1075/#1077/#1079 (9 green PRs unblocked). |
| HomericIntelligence ecosystem | Swarm PR orchestration | 8 repos, 87 PRs merged + Odysseus pins (2026-04-19); 12-repo silent-failures sweep 17/18 auto-squash-merged (2026-05-10). |
| HomericIntelligence ecosystem | Ecosystem sweeps | v1: 5 repos, 717 issues classified, 51 PRs merged, 78 retired (2026-05-12); v2: 11 bundle PRs, 7 merged (2026-05-16); sequential rebase cleared 12 stuck PRs (2026-05-18). |
| 12 HomericIntelligence repos | Org-wide planned-issue swarm | 430 plan-carrying issues; ~51 piloted across 5 repos with signed squash-auto-merge PRs; L0-only fan-out + closing-keyword dedup + plan reconciliation (verified-local, 2026-05-29). |
| ProjectOdyssey | Batch review-plan pipeline | 24 failed review plans triaged; 14 OPEN PRs rebased/fixed/pushed with auto-merge, ~20-30 min (2026-03-06). |
| Odysseus meta-repo | Re-plan stale completed-sweep report (#299) | Report dated 2026-05-31 re-planned 2026-06-20 (20 days later). Live `gh pr view` showed ~13 "flagged for human" PRs were mostly already MERGED (Nestor #91/#95/#101/#102, Hermes #645, Odyssey #5471/#5488, AchaeanFleet #681/#682/#684-#690); only 7 remained open. Every surviving root cause was stale: Scylla "pixi.lock v7 vs v6" gone (`version: 6` on both refs); 4 Scylla PRs all-checks-SUCCESS but BLOCKED by a new 1-review rule (approve+merge, not CI fix); Nestor #103 fix already landed (file 404 + in `.gitignore`, residual = rebase); AchaeanFleet tmpfs:noexec mount gone from live workflows; #683 carried a stray committed `.github/CI_FIX_683.md`. Discovery/triage queries verified-local; prescribed fixes are UNVERIFIED hypotheses (PLAN never executed). |
