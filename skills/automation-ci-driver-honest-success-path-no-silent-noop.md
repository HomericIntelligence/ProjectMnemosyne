---
name: automation-ci-driver-honest-success-path-no-silent-noop
description: "When a CI driver (e.g. `drive_prs_green`) reports 'pushed CI fixes for PR #N' but the remote PR head SHA is unchanged, the driver is silently no-op'ing. Three compounding bugs cause this: (1) bare `git push origin HEAD` pushes to whatever branch HEAD switched to inside the agent session instead of the PR head, (2) worktree setup creates a NEW branch off `main` when the local branch ref doesn't exist instead of resetting to `origin/<pr-head>`, (3) per-issue 'success' is treated as 'repo done' even with open PRs still outstanding. Fix all three: pre-sync the worktree to `origin/<pr-head>`, snapshot HEAD before/after the agent and fail if unchanged, push with explicit refspec `HEAD:<pr-head-branch>`, and gate 'repo done' on `gh api /repos/.../pulls?state=open --paginate` returning 0. Use when: (1) automation driver logs success but remote PR tips are unchanged, (2) `git push --force-with-lease` exits 0 with no remote update, (3) agent session resumed an old transcript and returned in seconds without a commit, (4) multi-repo run script's success/failed buckets don't match GitHub reality, (5) reviewing a driver that pushes commits to many PR branches across many repos."
category: ci-cd
date: 2026-06-02
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: automation-ci-driver-honest-success-path-no-silent-noop.history
tags:
  - hephaestus-automation-loop
  - drive-prs-green
  - ci-driver
  - silent-failure
  - git-push-refspec
  - worktree-sync
  - honest-reporting
  - repo-done-state
  - wait-for-merge
  - auto-merge-armed
  - dependabot-arming
  - re-arm-after-fix
  - session-id-collision
  - dirty-merge-conflict
  - markdownlint-blocker
  - homericintelligence
---

# CI Driver Honest Success Path - No Silent No-Op

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-02 |
| **Objective** | Stop a multi-repo CI driver from reporting "pushed CI fixes for PR #N" while the remote PR branch sits unchanged. Make the driver fail loudly when no commit was produced, sync the worktree to the actual PR head before the agent runs, and gate "repo done" on `pulls?state=open --paginate` returning empty. **v1.1.0:** stop reporting armed-and-merging PRs as FAILED — WAIT for the real terminal outcome (merge/fail) and partition the exit gate honestly. **v1.2.0:** a SECOND ecosystem run (after the v1.1.0 fix, failures 7→4 repos) surfaced four more bugs — re-arm after a successful CI fix, session-id collision under concurrency, DIRTY (merge-conflict) PRs never resolved, and the agent's "document the blocker" commit introducing NEW lint failures. |
| **Outcome** | Three layered bugs fixed and merged to `HomericIntelligence/ProjectHephaestus` main: PR #833 closes #832 (worktree pre-sync + explicit push refspec), PR #837 closes #836 (no-commit guard between agent return and push), PR #839 closes #838 (repo done-state gated on `pulls?state=open` count == 0). **v1.1.0:** PR #876 added wait-for-merge (`_wait_for_pr_terminal`), robust Dependabot arming, an honest exit gate that partitions armed-pending vs needs-action open PRs, and a bounded no-commit retry. **v1.2.0:** PR #879 (closes #878) added `_recheck_and_arm_after_fix` (re-poll + arm after a successful fix), a guarded session-id resume-then-fresh-uuid4 fallback, `mergeStateStatus`-aware `_wait_for_pr_terminal` returning `"DIRTY"` + `_resolve_dirty_pr`, and a force-engagement prompt that FORBIDS committing a blocker file and requires every edited file to pass the repo's own linters with NO rule disabled. A real second ecosystem run surfaced all four; full automation suite: 1011 passed, no hang. Driver went from "lies success" → "honest reporting" → "waits for the real outcome" → "re-arms, survives concurrency, resolves conflicts, never self-inflicts a lint failure". |
| **Verification** | verified-ci - v1.0.0's three PRs merged to main via the standard PR gate; v1.1.0's PR #876 merged and the new gate language appeared in production ecosystem-run logs (ProjectNestor flipped FAILED→complete; ProjectOdyssey waited 1743s then logged the armed-and-merging WARNING); v1.2.0's PR #879 (closes #878) fixes merged/in-flight, all four bugs surfaced by a real second ecosystem run (ProjectHermes #645/#648 CLEAN+un-armed, #647 session-id collision; ProjectOdyssey #5487/#5485/#5471 DIRTY). Full automation suite: 1011 passed, no hang. |

## When to Use

Trigger phrases that should route to this skill:

- "drive_prs_green says pushed but remote PR tip unchanged"
- "automation driver logs success with no commit on remote"
- "git push --force-with-lease exits 0 but no remote update"
- "agent session returned in seconds with no commit"
- "multi-repo run script success/failed buckets don't match GitHub"
- "automation reports 'pushed CI fixes for PR #N' silently"
- "worktree created off main instead of `origin/<pr-head>`"
- "repo done with open PRs still outstanding"
- "drive-green honest reporting"
- "silent no-op push to PR branch"
- "armed-and-merging PRs reported as FAILED"
- "auto-merge armed PR marked failed by the driver"
- "driver should wait for the PR to merge, not exit early"
- "Dependabot PR stuck NOT armed needs manual action"
- "gh pr merge --auto --squash fails on repo that disallows squash"
- "wait for PR terminal state merge or fail"
- "armed PR with merge conflict DIRTY sits open forever"
- "PR is CLEAN but auto-merge not armed, merges instantly when armed manually"
- "driver walked away after a CI fix without re-arming auto-merge"
- "re-arm auto-merge after a successful CI fix"
- "Session ID is already in use claude --session-id collision"
- "two parallel CI-fix workers race on the same session id"
- "DIRTY merge-conflict PR never resolved, waits out the full timeout"
- "agent CI_BLOCKER.md commit fails markdownlint MD013 MD032"
- "blocker file turns one red check into two"
- "committing to a Dependabot PR orphans it, dependabot refuses to rebase"
- "@dependabot recreate after PR edited by someone other than Dependabot"

Trigger situations:

- Building or reviewing an automation driver that pushes commits to many PR branches across many repos.
- Driver appears to "succeed" but `gh pr view <N> --json headRefOid` shows the SAME SHA hours after the run "succeeded".
- `git push --force-with-lease` exits 0 but no remote update happens.
- The agent session resumed an old transcript and returned in seconds with no commit.
- A multi-repo run script's success/failed buckets don't match reality on GitHub - "Driven: ProjectX" printed while open PRs in ProjectX remain failing.
- Scoping an audit of `hephaestus/automation/ci_driver.py` or `hephaestus/automation/loop_runner.py` for honest reporting.

## Verified Workflow

> Apply all four guards in order. Each catches a different failure mode the
> next layer cannot see. Do NOT cherry-pick one — the bugs compound and a
> partial fix still lies about success.

### Quick Reference

End-to-end per-PR iteration in the driver:

```python
from pathlib import Path
import subprocess
from hephaestus.utils.git_utils import (
    sync_worktree_to_remote_branch,
    push_current_branch_with_lease_on_divergence,
    run,
)

def drive_one_pr(worktree: Path, pr_head_branch: str) -> bool:
    # Guard 1: pre-sync worktree to the PR's actual remote head.
    try:
        sync_worktree_to_remote_branch(worktree, pr_head_branch)
    except subprocess.CalledProcessError as exc:
        logger.error("pre-sync to origin/%s failed: %s", pr_head_branch, exc)
        return False

    # Guard 2: snapshot HEAD post-sync, compare post-agent.
    pre_agent_sha = run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()

    run_agent_session(worktree, pr_head_branch)  # may resume an old transcript

    post_agent_sha = run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()
    if post_agent_sha == pre_agent_sha:
        logger.warning(
            "agent session produced no new commit (HEAD unchanged at %s); skipping push",
            pre_agent_sha[:8],
        )
        return False

    # Guard 3: push with explicit refspec to the named remote branch.
    push_current_branch_with_lease_on_divergence(
        worktree,
        branch=pr_head_branch,
        push_ref=f"HEAD:{pr_head_branch}",
    )
    return True

# Guard 4: after the per-issue loop, gate "repo done" on truly-open PRs.
def repo_done(owner: str, name: str) -> tuple[bool, list[dict]]:
    out = run(
        ["gh", "api", "--paginate",
         f"/repos/{owner}/{name}/pulls?state=open&per_page=100"],
        cwd=Path.cwd(),
    ).stdout
    open_prs = json.loads(out)
    return (len(open_prs) == 0, open_prs)
```

`hephaestus/utils/git_utils.py` helpers:

```python
def sync_worktree_to_remote_branch(cwd: Path, branch: str, *, remote: str = "origin") -> None:
    """Hard-reset the worktree to ``<remote>/<branch>``.

    Safe ONLY when the worktree is throwaway (the driver removes it after each
    iteration). Catches the case where worktree creation fell back to ``-b
    <branch> ... main`` and ignored the existing remote branch.
    """
    run(["git", "fetch", remote, branch], cwd=cwd)
    run(["git", "reset", "--hard", f"{remote}/{branch}"], cwd=cwd)


def push_current_branch_with_lease_on_divergence(
    cwd: Path,
    *,
    branch: str | None = None,
    remote: str = "origin",
    push_ref: str = "HEAD",
) -> subprocess.CompletedProcess[str]:
    """Push ``push_ref`` to ``<remote>``.

    On non-fast-forward (`! [rejected] (non-fast-forward)`), retry with
    ``--force-with-lease=<branch>`` while PRESERVING the explicit refspec so
    the lease push still lands on the named remote branch.
    """
    try:
        return run(["git", "push", remote, push_ref], cwd=cwd)
    except subprocess.CalledProcessError as exc:
        if not _is_push_rejected_diverged(exc):
            raise
        if branch is None:
            branch = get_current_branch(cwd)
        run(["git", "fetch", remote, branch], cwd=cwd)
        lease_push_ref = push_ref if push_ref != "HEAD" else f"HEAD:{branch}"
        return run(
            ["git", "push", f"--force-with-lease={branch}", remote, lease_push_ref],
            cwd=cwd,
        )
```

Multi-repo driver exit code:

```python
def main(repos: list[str]) -> int:
    failed_repos: list[str] = []
    open_prs_per_repo: dict[str, list[dict]] = {}

    for repo in repos:
        drive_all_failing_prs(repo)  # per-issue loop
        done, open_prs = repo_done(owner_of(repo), name_of(repo))
        open_prs_per_repo[repo] = open_prs
        if not done:
            failed_repos.append(repo)
            for pr in open_prs:
                logger.warning(
                    "[%s] open: PR #%d '%s' head=%s auto_merge=%s",
                    repo, pr["number"], pr["title"],
                    pr["head"]["ref"], pr.get("auto_merge") is not None,
                )

    return 1 if failed_repos else 0
```

### Detailed Steps

1. **Pre-sync the worktree to `origin/<pr-head>` BEFORE the agent runs.**
   The worktree manager only checked `git rev-parse --verify <branch>` for the
   LOCAL branch. On a clean clone the local branch didn't exist, so it fell
   through to `git worktree add -b <branch> <path> main` — creating a NEW
   branch off `main` with the same name, **ignoring `origin/<branch>`**. Even
   if the push later targeted the right name, the content was main-tip + the
   agent's noise — destroying the PR's actual history. Always pre-sync via
   `sync_worktree_to_remote_branch(worktree, pr_head_branch)`. If the sync
   fails, mark the iteration failed and skip — there is no point letting the
   agent commit on the wrong base.

2. **Snapshot HEAD post-sync; compare HEAD post-agent. If unchanged, fail the iteration.**
   `pre_agent_sha = git rev-parse HEAD`; run the agent session; `post_agent_sha
   = git rev-parse HEAD`. If equal, log a warning and return `False`. This
   catches the "Claude resumed an old session and decided nothing was needed"
   case that would otherwise produce a silent no-op `git push
   --force-with-lease` exiting 0. The driver previously had NO guard here —
   the agent returning meant "push and report success" regardless of whether a
   commit actually existed.

3. **Push with explicit refspec `HEAD:<pr-head-branch>`, not bare `HEAD`.**
   Bare `git push origin HEAD` pushes to **whatever branch HEAD happened to be
   on**. Claude often followed `CLAUDE.md`'s general "git checkout -b
   `<issue>`-description" workflow and switched to a new branch locally; the
   bare push then landed on a stray `<issue>-fix-ci` remote ref while the PR's
   actual head branch sat unchanged. Extend the push helper with a `push_ref`
   parameter, default `"HEAD"`, and preserve it on the lease-retry path so the
   force-with-lease push still lands on the right named remote branch.

4. **Gate "repo done" on `gh api --paginate /repos/<owner>/<name>/pulls?state=open&per_page=100`.**
   Not `gh pr list --limit 100` — that silently caps at 100. The previous
   logic treated "every input issue's drive returned success" as "repo done",
   which is FALSE: PRs from outside the input list, dependency bumps,
   auto-merge-waiting-on-CI all sit open while the script reports "Driven:
   ProjectX". Fold the open-PR count into the exit code: non-empty list ⇒
   `rc=1`, and log each open PR's number, title, head ref, and auto-merge
   state. The driver MUST exit 1 if any PR is still open in any driven repo.

5. **Verify by re-running and comparing the PR head SHA.**
   After the run claims success, sample the touched PRs:
   ```bash
   gh pr view <N> --json headRefOid,statusCheckRollup --jq '.headRefOid'
   ```
   The SHA must differ from the pre-run head. If it doesn't, the driver is
   still lying — recheck which of the four guards is missing or being bypassed
   in the code path you took.

### v1.1.0 — Armed-and-waiting PRs are NOT failures: wait for merge + honest gate partition

> The v1.0.0 honest gate (Guard 4) was *too blunt*. It exited `rc=1` whenever
> ANY open PR remained — including PRs that were `auto-merge=armed` and merging
> on their own. A real `drive_prs_green` ecosystem run marked **7 of 15 repos
> FAILED**; root-cause analysis of every per-repo log showed NONE were real
> driver crashes. The driver OBSERVED-AND-RETURNED instead of WAITING for the
> real outcome. The fix is to actually wait until each PR reaches a terminal
> state, then partition the still-open PRs into "armed & merging" (fine) vs
> "needs manual action" (genuinely stuck).

The single `rc=1` was masking three distinct buckets:

1. **False failures** — PRs armed & merging on their own (fast ~8s exits).
2. **Dependabot backlog** — bot PRs left `NOT armed (needs manual action)`
   accumulating forever because `gh pr merge --auto --squash` failed on repos
   that disallow squash.
3. **Genuine agent give-ups** — a single no-commit agent turn was terminal with
   `max_fix_iterations=1`.

The fix (merged as **ProjectHephaestus PR #876**, `hephaestus/automation/ci_driver.py`):

6. **Wait for the PR's terminal state — `_wait_for_pr_terminal(issue, pr)`.**
   Returns `"MERGED" | "CLOSED" | "FAILING" | "TIMEOUT"`. Polls `_gh_pr_state`
   with exponential backoff capped at 60s (`min(2**n, 60)`), bounded by env
   `HEPH_PR_MERGE_MAX_WAIT` (default `1800`s). On each OPEN poll it also checks
   required checks via `gh_pr_checks`; a required check concluding `failure`
   returns `FAILING` **immediately** — so the driver reacts to a PR that went
   red *after* arming instead of waiting out the full timeout. Wired into
   `_drive_issue` right after arming, and into the "still OPEN at armed SHA"
   branch of `_check_arming_on_drive_start`. On `FAILING` it falls through to
   `_attempt_ci_fixes`; on `MERGED` it fires the post-merge `/learn` once.

   ```python
   def _wait_for_pr_terminal(self, issue: int, pr: int) -> str:
       deadline = time.monotonic() + int(os.environ.get("HEPH_PR_MERGE_MAX_WAIT", "1800"))
       n = 0
       while time.monotonic() < deadline:
           state = self._gh_pr_state(pr)          # MERGED / CLOSED / OPEN
           if state == "MERGED":
               return "MERGED"
           if state == "CLOSED":
               return "CLOSED"
           # still OPEN — react to a required check that went red after arming
           if any(c["conclusion"] == "failure" for c in self._gh_pr_checks(pr) if c["isRequired"]):
               return "FAILING"
           time.sleep(min(2 ** n, 60))
           n += 1
       logger.warning("PR #%d still OPEN after %ss (limit %ss); leaving armed and pending",
                      pr, ..., ...)
       return "TIMEOUT"
   ```

7. **Robust Dependabot arming — `_enable_auto_merge(pr, is_bot_pr=False)`.**
   For bot PRs, on `gh pr merge --auto --squash` failure, retry
   `gh pr merge --auto` (strategy-agnostic, no `--squash`) before giving up, so
   repos that disallow squash stop stranding every Dependabot PR.

8. **Honest exit gate — `_evaluate_run_result()`.** Partition
   `open_prs_remaining` (each dict carries `autoMergeRequest`) into:
   - `armed_pending` — truthy `autoMergeRequest` ⇒ still merging ⇒ log a
     **WARNING but DO NOT fail**.
   - `needs_action` — falsy `autoMergeRequest` ⇒ genuinely stuck ⇒ `rc=1`.

   `failed` per-issue still ⇒ `rc=1`. The JSON status now emits both buckets
   distinctly. New log lines:
   `"N PR(s) armed and still merging (waited; not a failure)"` and
   `"Repo not done: N open PR(s) need manual action"`.

9. **No-commit hardening — `_retry_no_commit_once(..., max_retries=2)`.**
   Re-engage the agent up to 2 times (bounded loop: `retry 1/2`, `retry 2/2`)
   before recording the forensics marker, instead of giving up after one
   no-commit turn. **Do NOT change `max_fix_iterations`** — that controls a
   different loop.

**Production verification (verified-ci).** A follow-up ecosystem run on the new
build showed:

- **ProjectNestor** flipped `FAILED → complete`.
- **ProjectOdyssey** WAITED 1743s then logged
  `"PR #5487 still OPEN after 1743s (limit 1800s); leaving armed and pending"`
  and `"3 PR(s) armed and still merging (waited; not a failure)"` — failing on
  only **1 genuine `needs_action` PR** instead of the old 4.
- The no-commit retry landed fixes on **5 PRs** (`CI fix applied successfully`)
  that the old code abandoned.

**Known limitation (future enhancement).** A PR that is `auto-merge armed` but
`mergeStateStatus == DIRTY` (merge conflict) sits OPEN forever;
`_wait_for_pr_terminal` treats it as `TIMEOUT` (pending) and never makes
progress. Detect `DIRTY` in the wait loop and re-trigger a mechanical rebase
rather than waiting out the full 1800s.

**Test impact.** Adding a blocking wait inside `_drive_issue`'s green path hangs
any unit test that drives to green+arm without mocking `_wait_for_pr_terminal`
(real `gh pr view` + real `time.sleep`). Every green-path / `run()`-level test
MUST `patch.object(driver, "_wait_for_pr_terminal", return_value="MERGED")`
(or set `HEPH_PR_MERGE_MAX_WAIT=0`).

### v1.2.0 — Re-arm after a fix, survive session-id collisions, resolve DIRTY PRs, never self-inflict a lint failure

> A SECOND `drive_prs_green` ecosystem run, on the v1.1.0 build, dropped
> failures from 7 → 4 repos but surfaced **four new `ci_driver` bugs**. All four
> are fixed in **ProjectHephaestus PR #879 (closes #878)**. A real run surfaced
> every one — these are not hypotheticals.

10. **Re-arm after a successful CI fix — `_recheck_and_arm_after_fix(issue, pr, slot)` (HIGH).**
    `_attempt_ci_fixes` returned `WorkerResult(success=True)` the instant
    `_run_ci_fix_session` returned `fixed=True` and NEVER re-polled CI or armed
    auto-merge. The pushed fix re-triggers CI, the driver walks away, and the
    now-green PR sits `mergeStateStatus=CLEAN` but **auto-merge NOT armed
    forever** (observed: ProjectHermes #645, #648 — both CLEAN + un-armed,
    merged instantly once manually armed). Fix: after a fix returns `fixed=True`,
    re-enter the check→arm→wait flow ONCE via a bounded poll on `gh_pr_checks`:

    ```python
    def _recheck_and_arm_after_fix(self, issue: int, pr: int, slot) -> str | None:
        """Re-poll CI once after a fix lands; arm + wait if green.

        Returns the terminal outcome if it armed and waited, or None so a
        LATER run picks the PR up (still pending / red is not terminal here).
        """
        checks = self._poll_pr_checks_bounded(pr)         # bounded on gh_pr_checks
        if self._all_required_green(checks):
            self._enable_auto_merge(pr, is_bot_pr=self._is_bot_pr(pr))
            self._arm_drive_green(issue, pr, slot)
            return self._wait_for_pr_terminal(issue, pr)
        return None  # still pending/red → a later run arms it
    ```

    Wire it into **BOTH** the post-arm FAILING path and the failing-checks path
    of `_drive_issue` — a fix can land on either path and both must re-arm.

11. **Session-id "already in use" under concurrency — guarded resume + fresh-uuid4 fallback (HIGH).**
    The Claude session id is a deterministic UUIDv5 of `(repo, issue, agent)`
    (`session_naming.session_uuid`). With 3 parallel CI-fix workers, two race on
    the same id **before the transcript JSONL is on disk**; the loser's `claude
    --session-id` create fails `"already in use"`, and the existing resume
    fallback in `claude_invoke.py` was **UNGUARDED** — if resume also failed
    (sibling still initializing), the error propagated and killed the drive
    (ProjectHermes #647: `Session ID … is already in use`). Fix: wrap the resume
    fallback in try/except, retry resume up to 3× with backoff, then fall back to
    a **FRESH `uuid4` session** so the worker decouples from the contended id
    rather than aborting:

    ```python
    try:
        return _claude_create(session_id=deterministic_id, ...)
    except SessionIdInUse:
        for attempt in range(3):
            try:
                return _claude_resume(session_id=deterministic_id, ...)
            except (SessionIdInUse, ResumeFailed):
                time.sleep(backoff(attempt))      # sibling may still be init'ing
        # decouple from the contended id entirely
        return _claude_create(session_id=str(uuid.uuid4()), ...)
    ```

12. **DIRTY (merge-conflict) PRs never resolved — `mergeStateStatus` + `_resolve_dirty_pr` (MEDIUM).**
    `_gh_pr_state` fetched only `state,headRefOid,mergedAt` — **NOT
    `mergeStateStatus`**. So `_wait_for_pr_terminal` could not tell a
    genuinely-pending armed PR from an armed-but-DIRTY one (merge conflict), and
    waited out the full `HEPH_PR_MERGE_MAX_WAIT` (1800s) every run forever
    (ProjectOdyssey #5487/#5485/#5471). The mechanical rebase correctly defers
    conflicts "to agent", but the agent path only fires on FAILING checks — a
    DIRTY PR with GREEN checks has no failing checks and `_get_failing_ci_logs`
    is empty, so the agent gets no conflict guidance. Fix:
    - add `mergeStateStatus` to `_gh_pr_state`'s `--json`;
    - `_wait_for_pr_terminal` returns a new `"DIRTY"` outcome when an OPEN PR is
      `DIRTY`/`CONFLICTING`;
    - new `_resolve_dirty_pr` tries a mechanical rebase, then hands the agent an
      explicit conflict-resolution prompt via a new `extra_context` param on
      `_attempt_ci_fixes`.

    ```python
    def _wait_for_pr_terminal(self, issue: int, pr: int) -> str:
        ...
        state, mss = self._gh_pr_state(pr)        # now returns mergeStateStatus too
        if state == "OPEN" and mss in ("DIRTY", "CONFLICTING"):
            return "DIRTY"
        ...

    # in _drive_issue, on "DIRTY":
    if outcome == "DIRTY":
        self._resolve_dirty_pr(issue, pr, slot)   # rebase → agent w/ conflict prompt
    ```

13. **The agent's "document the blocker" commit introduces NEW lint failures — fix the prompt, never disable the lint (HIGH).**
    The force-engagement prompt told the agent: *"if no fix is possible, write a
    commit that documents the blocker in the PR description."* The agent created
    a `CI_BLOCKER.md` that itself **FAILS** the repo's markdownlint (MD013
    line-length, MD032 blanks-around-lists), turning ONE red check into TWO and
    blocking ~4 dependabot PRs. **Fix the ROOT CAUSE, never disable the lint
    rule** (explicit user instruction). The prompt now:
    - **FORBIDS** committing a blocker file — use the `BLOCKED:` line instead;
    - requires **every added/edited file to pass the repo's own linters with NO
      rule disabled**;
    - names `CI_BLOCKER.md` as **forbidden** explicitly.

    > **Cross-cutting (connects bug 13 to the dependabot drain): an agent
    > committing ANYTHING to a Dependabot-authored PR orphans it.** Dependabot
    > then refuses to rebase it (`"Looks like this PR has been edited by someone
    > other than Dependabot"`); the only recovery is `@dependabot recreate`
    > (rebuilds from clean main) or a manual rebase. **The driver should avoid
    > committing to bot PRs where possible** — a self-inflicted blocker commit on
    > a bot PR is doubly bad: it fails lint AND orphans the PR from its own
    > auto-rebase.

**Production / test verification (verified-ci).** All four fixes landed as
ProjectHephaestus **PR #879 (closes #878)**; the second ecosystem run that
surfaced them confirmed: ProjectHermes #645/#648 were CLEAN + un-armed (bug 10),
PR #647 hit the session-id collision (bug 11), ProjectOdyssey #5487/#5485/#5471 were
DIRTY (bug 12), and ~4 dependabot PRs were double-red from the `CI_BLOCKER.md`
commit (bug 13). Full automation suite after the fix: **1011 passed, no hang**.

**Test impact (v1.2.0).** Same hazard class as v1.1.0 (and
`pytest-asyncio-hang-and-mock-hazards`): every green-path / `run()`-level unit
test that drives `_drive_issue` to green+arm must now mock **both**
`_wait_for_pr_terminal` AND the new `_recheck_and_arm_after_fix` — otherwise the
re-arm path re-enters real `gh_pr_checks` + `_wait_for_pr_terminal` and hangs on
real `gh`/`sleep`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bare `git push origin HEAD` after Claude returns | Driver did `subprocess.run(["git", "push", "origin", "HEAD"])` and logged "pushed CI fixes for PR #N" on `returncode == 0`. Worked in dev where Claude stayed on the PR head branch. | Claude often followed `CLAUDE.md`'s general "git checkout -b `<issue>`-description" workflow and switched to a new branch locally; the bare push then landed on a stray `<issue>-fix-ci` remote ref while the PR's actual head branch sat unchanged. Driver still logged success. Remote PR tip unchanged hours after the run "succeeded". | Never push `HEAD` bare from a driver when the agent's working state is untrusted. Always pass an explicit refspec `HEAD:<intended-remote-branch>` and preserve it through the force-with-lease retry. |
| Trust `WorktreeManager.create_worktree` to land on the PR's actual head | The manager checked `git rev-parse --verify <branch>` for the LOCAL branch. On a clean clone the local branch didn't exist; it fell through to `git worktree add -b <branch> <path> main`. | Created a NEW branch off `main` with the same name, **ignoring `origin/<branch>`**. Even when the push later targeted the right name (after fix #1), the content was main-tip + Claude's noise — destroying the PR's actual history. Lost commits. | Worktree-setup local-branch-only checks are unsafe for driver use. The driver MUST explicitly `fetch origin <branch>` and `reset --hard origin/<branch>` before the agent runs. Throwaway worktree makes the hard reset safe. |
| Skip the no-commit guard and just push whatever HEAD points to | Assumed "agent returned ⇒ agent did work ⇒ push is safe". | Claude resumed an OLD session transcript and decided nothing was needed (correctly!), returning in seconds with no commit. `git push --force-with-lease HEAD:<pr-head>` then exited 0 because the local HEAD == remote tip already. Driver logged "pushed CI fixes for PR #N" with no fix in flight. | Agent return is NOT proof of work. Snapshot HEAD pre/post and treat `pre_sha == post_sha` as a hard failure for the iteration — log it, skip the push, and let the run script's exit code reflect reality. |
| Capture `/learn` on auto-merge-armed PRs (not on merged) | Considered firing the skill-capture pipeline when `gh pr merge --auto --squash` returned 0 (auto-merge armed). | PRs auto-merge-arm but later get blocked by CI flake, branch-protection veto, or manual cancellation. Capturing learnings on the optimistic point polluted ProjectMnemosyne with lessons from PRs that never shipped. | Lessons must come from MERGED state, not auto-merge-armed state. Poll `mergedAt != null` (or wait on the merge webhook) before capturing. Same principle applies to the driver: don't claim success at any intermediate optimistic point. |
| Treat per-issue success as "repo done" | Multi-repo run script collected return values from each `drive_one_pr` call; printed "Driven: ProjectX" if every input issue returned success. | Per-issue success ≠ repo cleanliness. PRs from outside the input list (dependency bumps, auto-merge-waiting-on-CI, PRs from other actors) sat open while the script reported "Driven". Operators trusted the green output and moved on. | Repo done-state MUST be evaluated independently against `gh api --paginate /repos/{owner}/{name}/pulls?state=open` — not `gh pr list --limit 100` which silently caps. Non-empty list ⇒ `rc=1` with each open PR logged. |
| (v1.1.0) Exit `rc=1` on ANY open PR, including armed-and-merging ones | Guard 4's blunt "any open PR ⇒ rc=1". An ecosystem run marked 7/15 repos FAILED while every PR was `auto-merge=armed (waiting on CI / branch protection)` — i.e. merging on its own. Fast ~8s exits, `Successful: N, Failed: 0`. | Driver OBSERVED-AND-RETURNED instead of waiting for the real outcome. Operators chased 7 "failures" that were all merging on their own. The fix is NOT to exit 0 on armed PRs (rejected by the user) — it is to **actually WAIT** until the PR finishes (merge or fail) so the driver can react to failures/conflicts. | The exit gate MUST partition open PRs: truthy `autoMergeRequest` ⇒ `armed_pending` ⇒ WARNING not failure; falsy ⇒ `needs_action` ⇒ `rc=1`. And add a real wait loop (`_wait_for_pr_terminal`) so the terminal state is observed, not guessed. |
| (v1.1.0) "Just exit 0 on any armed PR" as the fix | Proposed early-exit: treat `autoMergeRequest != null` as success and return rc=0 immediately. | User rejected it: an armed PR can still go red (CI flake, post-arm failure) or hit a merge conflict. Exiting 0 abandons the driver's ability to react. | WAIT for the terminal state with a bounded backoff loop; only then decide. Early-exit on the optimistic point is the same class of bug as v1.0.0's "claim success at an intermediate optimistic point". |
| (v1.1.0) Wait out `TIMEOUT` for a DIRTY (conflicted) armed PR | `_wait_for_pr_terminal` polls an armed PR whose `mergeStateStatus == DIRTY` (merge conflict). | The PR sits OPEN forever; the wait loop returns `TIMEOUT` after the full `HEPH_PR_MERGE_MAX_WAIT` (1800s) and makes no progress — wasted 30 min per conflicted PR. | Known limitation. Detect `DIRTY` inside the wait loop and re-trigger a mechanical rebase instead of waiting out the timeout. Documented as a future enhancement. |
| (v1.1.0) Add the blocking wait without mocking it in tests | Wired `_wait_for_pr_terminal` into `_drive_issue`'s green path, ran the unit suite. | Any test that drives to green+arm without a mock hit real `gh pr view` + real `time.sleep`, hanging the suite. | Every green-path / `run()`-level test MUST `patch.object(driver, "_wait_for_pr_terminal", return_value="MERGED")` or set `HEPH_PR_MERGE_MAX_WAIT=0`. A blocking wait inside a hot path is a test hazard — mock it at the seam. |
| (v1.2.0) Return `success=True` the instant `_run_ci_fix_session` returns `fixed=True` | `_attempt_ci_fixes` treated a landed fix as terminal success and returned immediately, never re-polling CI or arming auto-merge. | The pushed fix re-triggers CI; the driver walks away; the now-green PR sits `mergeStateStatus=CLEAN` but auto-merge NOT armed forever (ProjectHermes #645, #648 — both CLEAN + un-armed, merged instantly once armed manually). A fix is not the end — it's the start of a fresh CI run that still needs arming. | Re-enter the check→arm→wait flow ONCE after a fix via `_recheck_and_arm_after_fix(issue, pr, slot)` (bounded poll on `gh_pr_checks`; green → `_enable_auto_merge` + `_arm_drive_green` + `_wait_for_pr_terminal`; still pending/red → return None so a later run arms it). Wire into BOTH the post-arm FAILING path and the failing-checks path of `_drive_issue`. |
| (v1.2.0) Leave the `claude --session-id` resume fallback unguarded | The session id is a deterministic UUIDv5 of (repo, issue, agent); the existing fallback resumed on create-collision with no try/except. | With 3 parallel CI-fix workers, two race on the same id before the transcript JSONL is on disk; create fails "already in use" AND resume fails (sibling still initializing), so the error propagated and killed the drive (ProjectHermes #647). A deterministic id is a contended resource under concurrency. | Wrap the resume fallback in try/except, retry resume up to 3× with backoff, then fall back to a FRESH `uuid4` session so the worker DECOUPLES from the contended id instead of aborting. Never let a deterministic-id collision be terminal. |
| (v1.2.0) Fetch only `state,headRefOid,mergedAt` in `_gh_pr_state` | `_wait_for_pr_terminal` polled PR state without `mergeStateStatus`. | It could not distinguish a genuinely-pending armed PR from an armed-but-DIRTY (merge-conflict) one, so it waited out the full `HEPH_PR_MERGE_MAX_WAIT` (1800s) every run forever (ProjectOdyssey #5487/#5485/#5471). The agent conflict path only fires on FAILING checks, but a DIRTY PR with GREEN checks has no failing checks and `_get_failing_ci_logs` is empty — the agent gets no conflict guidance. | Add `mergeStateStatus` to `_gh_pr_state`'s `--json`; return a new `"DIRTY"` outcome from `_wait_for_pr_terminal` on `DIRTY`/`CONFLICTING`; add `_resolve_dirty_pr` (mechanical rebase, then hand the agent an explicit conflict prompt via a new `extra_context` param on `_attempt_ci_fixes`). |
| (v1.2.0) Tell the agent to "commit a file documenting the blocker" | The force-engagement prompt said: if no fix is possible, write a commit that documents the blocker in the PR description. | The agent created a `CI_BLOCKER.md` that itself FAILS the repo's markdownlint (MD013 line-length, MD032 blanks-around-lists), turning ONE red check into TWO and blocking ~4 dependabot PRs. Worse, committing to a Dependabot PR orphans it ("edited by someone other than Dependabot" → refuses to rebase; needs `@dependabot recreate`). | Fix the ROOT CAUSE, never disable the lint rule (explicit user instruction): the prompt now FORBIDS committing a blocker file (use a `BLOCKED:` line instead), requires every added/edited file to pass the repo's own linters with NO rule disabled, and names `CI_BLOCKER.md` as forbidden. The driver should avoid committing to bot PRs at all where possible. |
| (v1.2.0) Mock only `_wait_for_pr_terminal` in green-path tests | After adding `_recheck_and_arm_after_fix`, kept the v1.1.0 test mock (only `_wait_for_pr_terminal`). | The re-arm path re-enters real `gh_pr_checks` + `_wait_for_pr_terminal`, so tests that drive `_drive_issue` to green+arm through a fix still hung on real `gh`/`sleep`. | Mock BOTH `_wait_for_pr_terminal` AND `_recheck_and_arm_after_fix` in every green-path / `run()`-level test. Same hazard class as `pytest-asyncio-hang-and-mock-hazards` — mock every new blocking seam, not just the first. Full suite after: 1011 passed, no hang. |

## Results & Parameters

### The three PRs that landed (all merged to ProjectHephaestus main)

| PR | Closes | Guard | What changed |
| ---- | -------- | ------- | -------------- |
| [#833](https://github.com/HomericIntelligence/ProjectHephaestus/pull/833) | #832 | Guard 1 + Guard 3 | `hephaestus/utils/git_utils.py`: added `sync_worktree_to_remote_branch`; added `push_ref` parameter to `push_current_branch_with_lease_on_divergence` and preserved it on the lease-retry path. Driver call site now passes `push_ref=f"HEAD:{pr_head_branch}"`. |
| [#837](https://github.com/HomericIntelligence/ProjectHephaestus/pull/837) | #836 | Guard 2 | `hephaestus/automation/ci_driver.py`: snapshot `pre_agent_sha = git rev-parse HEAD` post-sync, compare `post_agent_sha = git rev-parse HEAD` post-agent. If equal, `logger.warning(...)` and `return False`. No push happens. |
| [#839](https://github.com/HomericIntelligence/ProjectHephaestus/pull/839) | #838 | Guard 4 | Multi-repo run script: replaced "every issue returned success ⇒ repo done" with `gh api --paginate /repos/{owner}/{name}/pulls?state=open&per_page=100`. Non-empty list logs each open PR (number, title, head ref, auto-merge state) and folds into `rc=1`. |
| [#876](https://github.com/HomericIntelligence/ProjectHephaestus/pull/876) | — | Wait-for-merge (v1.1.0) | `hephaestus/automation/ci_driver.py`: added `_wait_for_pr_terminal` (bounded exponential backoff, `HEPH_PR_MERGE_MAX_WAIT`, reacts to required-check failure post-arm); robust Dependabot arming in `_enable_auto_merge(is_bot_pr)` (retry `--auto` without `--squash`); honest exit gate `_evaluate_run_result()` partitioning `armed_pending` (WARNING) vs `needs_action` (rc=1); bounded no-commit retry `_retry_no_commit_once(max_retries=2)`. |
| [#879](https://github.com/HomericIntelligence/ProjectHephaestus/pull/879) | #878 | Re-arm + concurrency + DIRTY + lint (v1.2.0) | `hephaestus/automation/ci_driver.py` + `claude_invoke.py`: `_recheck_and_arm_after_fix(issue, pr, slot)` re-enters check→arm→wait ONCE after a fix (wired into both FAILING paths of `_drive_issue`); guarded session-id resume (3× backoff) then fresh-`uuid4` fallback in `claude_invoke.py`; `mergeStateStatus` added to `_gh_pr_state`, new `"DIRTY"` outcome from `_wait_for_pr_terminal`, `_resolve_dirty_pr` (rebase → agent conflict prompt via `extra_context` on `_attempt_ci_fixes`); force-engagement prompt FORBIDS a blocker file (`BLOCKED:` line instead) and requires every edited file to pass the repo's linters with NO rule disabled. Suite: 1011 passed. |

### Verification command

After landing the three PRs, re-run the driver and confirm honest reporting:

```bash
# Snapshot remote head SHAs before the run
for pr in 832 836 838; do
  gh pr view "$pr" --json number,headRefOid \
    --jq '"\(.number) \(.headRefOid)"'
done > /tmp/pre-run-shas.txt

# Run the driver
pixi run python scripts/drive_prs_green.py --issues 832 836 838 --force-run

# Confirm SHAs changed (or driver exited non-zero with honest reason)
for pr in 832 836 838; do
  gh pr view "$pr" --json number,headRefOid \
    --jq '"\(.number) \(.headRefOid)"'
done > /tmp/post-run-shas.txt

diff /tmp/pre-run-shas.txt /tmp/post-run-shas.txt
# Expected: SHAs differ for every PR the driver claimed to push to.
# If a SHA is unchanged, the driver MUST have logged either a guard-2
# warning or a guard-1 sync failure for that PR.
```

### Expected output of a healthy run

```text
[ProjectHephaestus] drive PR #832 -> sync origin/832-fix-ci OK (pre=ab12cd34)
[ProjectHephaestus] drive PR #832 -> agent session returned
[ProjectHephaestus] drive PR #832 -> HEAD changed ab12cd34 -> ef56gh78
[ProjectHephaestus] drive PR #832 -> push HEAD:832-fix-ci OK
[ProjectHephaestus] repo done check: gh api /repos/.../pulls?state=open
[ProjectHephaestus] repo done check: 0 open PRs => repo done
Completed. rc=0
```

### Expected output of an HONEST failure (no longer silently green)

```text
[ProjectHephaestus] drive PR #836 -> sync origin/836-fix-ci OK (pre=ab12cd34)
[ProjectHephaestus] drive PR #836 -> agent session returned
[ProjectHephaestus] drive PR #836 -> WARNING: agent session produced no new commit
                                     (HEAD unchanged at ab12cd34); skipping push
[ProjectHephaestus] repo done check: gh api /repos/.../pulls?state=open
[ProjectHephaestus] repo done check: 2 open PRs:
                                     PR #840 'chore(deps): bump foo' head=deps/foo auto_merge=true
                                     PR #841 'fix(x): repair' head=841-fix auto_merge=false
Completed. rc=1
```

### Trigger-phrase index (for `/advise` discovery)

- "drive_prs_green says pushed but no change on remote"
- "git push origin HEAD pushed wrong branch"
- "worktree created off main instead of origin"
- "force-with-lease exits 0 silently"
- "agent resumed transcript no commit"
- "repo done with open PRs"
- "gh pr list limit 100 silent cap"
- "multi-repo success/failed wrong"
- "drive-green honest reporting"
- "automation driver lies success"
- "armed-and-merging PR reported as failed"
- "driver should wait for merge not exit early"
- "dependabot PR stuck not armed squash disallowed"
- "wait for pr terminal state"
- "armed PR DIRTY merge conflict sits open"
- "PR CLEAN but auto-merge not armed after a CI fix"
- "re-arm auto-merge after a successful fix"
- "session id already in use parallel workers"
- "deterministic uuidv5 session id collision fresh uuid4"
- "DIRTY conflict PR never resolved waits out timeout"
- "agent CI_BLOCKER.md fails markdownlint MD013 MD032"
- "committing to dependabot PR orphans it recreate"

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR [#833](https://github.com/HomericIntelligence/ProjectHephaestus/pull/833) closes #832 - worktree pre-sync via `sync_worktree_to_remote_branch` + explicit push refspec `HEAD:<pr-head-branch>`. | Merged to main 2026-05-31. Fixes Guard 1 + Guard 3. |
| ProjectHephaestus | PR [#837](https://github.com/HomericIntelligence/ProjectHephaestus/pull/837) closes #836 - no-commit guard: `git rev-parse HEAD` before/after agent session, skip push and return False if unchanged. | Merged to main 2026-05-31. Fixes Guard 2. |
| ProjectHephaestus | PR [#839](https://github.com/HomericIntelligence/ProjectHephaestus/pull/839) closes #838 - repo done-state gated on `gh api --paginate /repos/{owner}/{name}/pulls?state=open&per_page=100` returning empty; otherwise rc=1 with each open PR logged. | Merged to main 2026-05-31. Fixes Guard 4. |
| ProjectHephaestus | PR [#876](https://github.com/HomericIntelligence/ProjectHephaestus/pull/876) - wait-for-merge (`_wait_for_pr_terminal`), robust Dependabot arming, honest exit-gate partition (`armed_pending` vs `needs_action`), bounded no-commit retry. | v1.1.0. Merged to main; production ecosystem run flipped ProjectNestor FAILED→complete, ProjectOdyssey waited 1743s and failed on only 1 genuine PR (was 4), no-commit retry landed fixes on 5 PRs. |
| ProjectHephaestus | PR [#879](https://github.com/HomericIntelligence/ProjectHephaestus/pull/879) closes #878 - `_recheck_and_arm_after_fix` (re-arm after a fix), guarded session-id resume → fresh-`uuid4` fallback, `mergeStateStatus`-aware `_wait_for_pr_terminal` `"DIRTY"` + `_resolve_dirty_pr`, force-engagement prompt forbidding a blocker file and requiring lint-clean edits with no rule disabled. | v1.2.0. A second ecosystem run (failures 7→4 repos) surfaced all four: ProjectHermes #645/#648 CLEAN+un-armed (bug 10), #647 session-id collision (bug 11), ProjectOdyssey #5487/#5485/#5471 DIRTY (bug 12), ~4 dependabot PRs double-red from `CI_BLOCKER.md` (bug 13). Full automation suite: 1011 passed, no hang. |

## References

- [PR #833 - worktree pre-sync + explicit push refspec](https://github.com/HomericIntelligence/ProjectHephaestus/pull/833)
- [PR #837 - no-commit guard between agent return and push](https://github.com/HomericIntelligence/ProjectHephaestus/pull/837)
- [PR #839 - repo done gated on open PR count == 0](https://github.com/HomericIntelligence/ProjectHephaestus/pull/839)
- [PR #876 - wait-for-merge + honest gate partition + Dependabot arming (v1.1.0)](https://github.com/HomericIntelligence/ProjectHephaestus/pull/876)
- [PR #879 - re-arm after fix + session-id collision + DIRTY resolution + lint-clean blocker prompt (v1.2.0)](https://github.com/HomericIntelligence/ProjectHephaestus/pull/879)
- [Issue #878 - second ecosystem run: re-arm, session-id, DIRTY, blocker-file lint failures](https://github.com/HomericIntelligence/ProjectHephaestus/issues/878)
- [Issue #832 - worktree did not sync to `origin/<pr-head>`](https://github.com/HomericIntelligence/ProjectHephaestus/issues/832)
- [Issue #836 - driver pushed silently when agent produced no commit](https://github.com/HomericIntelligence/ProjectHephaestus/issues/836)
- [Issue #838 - repo done evaluated per-issue, not per-repo](https://github.com/HomericIntelligence/ProjectHephaestus/issues/838)
- [tooling-hephaestus-automation-loop-drive-green-broken-design](tooling-hephaestus-automation-loop-drive-green-broken-design.md) - related design-level bugs in the loop runner's phase model and PR discovery. Different layer; both skills apply when auditing `drive_prs_green`.
- [tooling-gh-pr-list-limit-cap-use-api-paginate](tooling-gh-pr-list-limit-cap-use-api-paginate.md) - the `gh pr list --limit 100` silent cap that motivates the `gh api --paginate` substitution in Guard 4.
- [pytest-asyncio-hang-and-mock-hazards](pytest-asyncio-hang-and-mock-hazards.md) - same hazard class as the v1.1.0/v1.2.0 test impact: a blocking wait inside a hot path (`_wait_for_pr_terminal`, `_recheck_and_arm_after_fix`) hangs any test that hits it without a mock at the seam.
