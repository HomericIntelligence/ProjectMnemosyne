---
name: automation-ambient-cwd-repo-resolution-breaker-cascade
description: "Diagnose why a handful of wrong-repo 404s silently opens a SHARED circuit breaker and poisons an ENTIRE multi-repo automation run. Use when: (1) a multi-repo loop aborts with hundreds of 'poisoned' items, CircuitBreakerOpenError, or 'FAIL:poisoned' and near-zero useful work, (2) you see 'Could not resolve to an Issue with the number of N' 404s in a cross-repo run, (3) a caught/swallowed exception still trips a breaker ('WARNING: ...using cache' next to 'ERROR: Non-transient error'), (4) a GitHub helper takes a bare issue NUMBER with no owning repo, (5) triaging a multi-repo abort and deciding how many DISTINCT root-cause bugs to file, (6) labels/comments/state appear on the WRONG repo's issues with no error anywhere — the silent WRITE twin (verified: epic state:skip tags landed on the cwd repo's colliding issue numbers)."
category: debugging
date: 2026-07-17
version: "1.1.0"
history: automation-ambient-cwd-repo-resolution-breaker-cascade.history
user-invocable: false
verification: verified-ci
tags:
  - circuit-breaker
  - ambient-cwd
  - repo-resolution
  - multi-repo
  - automation-loop
  - cascade
  - swallowed-exception
  - silent-corruption
  - triage
  - hephaestus-automation
  - 404-wrong-repo
  - get_repo_info
---

# Automation: Ambient-CWD Repo Resolution Opens a Shared Breaker (Cascade)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Objective** | Diagnose why a multi-repo automation run aborted with ~zero useful work: a handful of wrong-repo 404s silently tripped a shared circuit breaker and poisoned every subsequent item across all repos. |
| **Outcome** | Root cause confirmed from a real run log; cascade + fix reproduced with runnable scripts. Fix (thread the owning repo per-issue) merged as ProjectHephaestus PR #2047, all CI green. |
| **Verification** | verified-ci — PR #2047 merged to ProjectHephaestus main with CI green; cascade and fix both reproduced with runnable scripts. |
| **History** | (none yet) |

## When to Use

- A multi-repo loop aborts: hundreds of items `poisoned`, `CircuitBreakerOpenError` / `GitHubUnavailableError`, `finished FAIL:poisoned`, `run_end interrupted=True`, and `agent_jobs=0` — hundreds of items processed, zero useful work.
- The log shows `Could not resolve to an Issue with the number of N` (a GitHub 404) for issues that DO exist — in a DIFFERENT repo.
- You see a caught exception right beside a breaker-recorded failure: `WARNING: Failed to fetch ... (using cache)` immediately after `ERROR: Non-transient error detected`.
- Any GitHub helper takes a bare `issue: int` / `issue_number` and calls the API without an owning repo.
- You are triaging a multi-repo abort and must decide how many DISTINCT bugs to file (see the triage lesson — the answer is usually far fewer than the symptom count).

## The Bug Chain (fully diagnosed)

Confirmed from a real run log (`build/loop-watch/loop-20260710T055220Z.log`):

1. A helper that takes only an issue NUMBER — `_fetch_issue_comment_ids(issue_number)` in `hephaestus/automation/github_api/issues.py` — called `get_repo_info()` with **no** `repo_root`.
2. `get_repo_info(repo_root=None)` (`git_utils.py`) falls back to `get_repo_root()` = the **ambient process CWD**.
3. In a multi-repo loop the CWD was ProjectHephaestus, so cross-repo lookups (Myrmidons#751, ProjectNestor#121, ...) queried the WRONG repo. Six 404s: `Could not resolve to an Issue with the number of N`.
4. `hephaestus/github/client.py` classifies each 404 as a **Non-transient** error and does a bare `raise` — which propagates OUT THROUGH `_GH_BREAKER.call(...)`, recording a failure BEFORE the caller's `except` swallows it.
5. `_GH_BREAKER` has `failure_threshold=5`. The **6th** 404 opens it. Every subsequent `gh` call raises `CircuitBreakerOpenError` / `GitHubUnavailableError`.
6. Blast radius: **236 items poisoned across 9 repos**, `run_end exit_code=130, items=250, agent_jobs=0, interrupted=True` — zero useful work.

## Key Insights (the whole value of this skill)

### 1. A swallowed / caught exception STILL trips the breaker

`breaker.call(fn)` records the failure **before** the caller's `except` runs. So a caller that catches the error and recovers does NOT stop the breaker from counting it. In the log:

```text
ERROR: Non-transient error detected: Could not resolve to an Issue with the number of 751
WARNING: Failed to fetch comment ids for issue 751 (using cache)
```

The `WARNING ... (using cache)` proves the CALLER recovered. It does **not** prove the SYSTEM recovered — the breaker already counted the failure toward its threshold. Never read "we fell back to cache" as "no harm done" when a shared breaker sits inside the call.

### 2. An issue NUMBER is meaningless without a repo

Treat any function signature that takes a bare `issue: int` (or `issue_number`) and then calls GitHub as **suspect**. Without an explicit `(owner, name)` it will resolve against whatever the ambient CWD happens to be — correct in a single-repo tool, catastrophic in a multi-repo loop.

### 3. The silent-corruption twin (WORSE than the 404s) — now VERIFIED on the write side

Where issue numbers **collide** across repos there is no 404 at all — so no error, no log line, no breaker trip. The loop silently reads/acts on an unrelated object in the wrong repo.

**Verified occurrence (2026-07-16/17, fixed in Hephaestus PR #2248):** the epic skip-tag chokepoint
(`github_api.skip_epics` → `gh_issue_add_labels`) built `gh issue edit N --add-label state:skip`
with no `--repo` selector. In the multi-repo parent process (cwd = the launch checkout), other
repos' epic numbers were written onto the cwd repo: Proteus#81 / Telemachy#92 / Hermes#316,#545
tagged Hephaestus#81/#92/#316/#545 — every write a clean 200. Because `state:skip` overrides all
planning, the mislabeled issues silently vanished from the loop. Label timelines
(`gh api repos/O/R/issues/N/timeline`) were the only evidence trail; see
[[github-label-mass-mislabel-forensics]] for the triage workflow. The fix threads an optional
`(owner, name)` through `gh_issue_add_labels` / `gh_list_labels` / `gh_create_label` / `skip_epics`
(appending `--repo owner/name` and keying the label cache by the explicit slug) — the same
thread-the-owning-repo pattern as PR #2047, applied to the WRITE path.

- Example: `ProjectAgamemnon#188` is a real issue; `ProjectHephaestus#188` also exists — as a merged PR. An ambient-CWD lookup for "188" while CWD=Hephaestus returns the wrong object with a 200.

**Always look for the silent twin of any wrong-repo 404.** The 404s are the loud, self-announcing half of the bug. The number-collision half is silent data corruption and will not appear in any error grep.

### 4. Triage: count DISTINCT root-cause signatures, not symptoms

When a multi-repo loop aborts, the log fills with cascade symptoms that are ONE bug's blast radius, not N bugs:
`poisoned`, `CircuitBreakerOpenError`, `finished FAIL:poisoned`, `label refresh failed (using cache)`.

A naive clustering filed **17 issues**. Correct clustering — normalize repo names + timestamps + issue numbers OUT of each line, then extract the **terminal exception of each traceback** — yielded **1 root-cause bug + 11 cascade signatures** (1,169 occurrences, report-only, NOT filed). Cluster on the terminal exception type, not on the surface message.

## Verified Workflow

### Quick Reference

```bash
# 1. Find the wrong-repo 404s (the loud half)
grep -nE "Could not resolve to an Issue with the number of [0-9]+" run.log

# 2. Confirm the breaker opened AFTER ~threshold 404s
grep -nE "Non-transient error detected|CircuitBreakerOpenError|GitHubUnavailableError|breaker.*open" run.log

# 3. Prove the swallow: WARNING '(using cache)' sitting right next to the ERROR
grep -nE "Non-transient error detected|using cache" run.log

# 4. Confirm the blast radius is one bug, not many:
#    normalize repo/number/timestamp OUT, then cluster on the terminal exception
grep -oE "[A-Za-z]+Error|poisoned|FAIL:poisoned" run.log | sort | uniq -c | sort -rn

# 5. Hunt the silent twin: any GitHub helper taking a bare issue number
grep -rnE "def .*\(.*issue(_number)?: int" hephaestus/automation/github_api/
```

### Detailed Steps

1. **Grep for the 404 signature** `Could not resolve to an Issue with the number of N`. If the issue exists in another repo, the CWD-vs-owning-repo mismatch is confirmed.
2. **Confirm the breaker threshold.** Count 404s before the first `CircuitBreakerOpenError`. If it matches `failure_threshold` (here 5 → the 6th trips it), the shared breaker is the amplifier.
3. **Confirm the swallow.** A `WARNING ... (using cache)` next to `ERROR: Non-transient error detected` means the caller recovered but the breaker already counted it. This is why "we recovered per-item" and "the whole run died" are both true at once.
4. **Trace the ambient CWD.** Follow the helper → `get_repo_info(repo_root=None)` → `get_repo_root()` → process CWD. That is the leak.
5. **Fix: thread the owning repo per-issue** (see below). Add `repo: tuple[str, str] | None = None`; when omitted, ambient behavior is preserved for single-repo callers.
6. **Hunt the silent twin.** For every wrong-repo 404, check whether the same number exists in the CWD repo. If it does, an earlier lookup silently corrupted state with a 200.
7. **Triage before filing.** Cluster on terminal exception type after normalizing repo/number/timestamp out. Report cascade signatures; file the single root cause.

## The Fix (PR #2047, merged)

Thread the owning `(owner, name)` down from the `WorkItem` (which already carries `.repo`) through the admission helpers to the `gh` call, resolved **PER ISSUE not per batch**. The implementation queue is keyed by StageName not repo, so one drain round legitimately holds issues from several repos even at `--parallel-repos 1` (proven: Myrmidons#751 + ProjectNestor#121 in flight together). Add an optional param so single-repo callers keep ambient behavior:

```python
def _fetch_issue_comment_ids(
    issue_number: int,
    repo: tuple[str, str] | None = None,   # (owner, name); None => ambient CWD
) -> list[str]:
    owner_name = repo if repo is not None else get_repo_info()  # explicit wins
    ...
```

Resolve `repo` from each `WorkItem.repo` at the point of use, one issue at a time.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Batch-wide repo parameter | Pass a single `(owner, name)` for a whole drain round / batch | The implementation queue is keyed by StageName, not repo, so one round legitimately holds issues from multiple repos (proven: Myrmidons#751 + ProjectNestor#121 in flight together under `--parallel-repos 1`). A batch-wide repo would mis-resolve every issue not from that repo. | Resolve the owning repo **per issue**, from `WorkItem.repo`, at the point of the gh call — never per batch. |
| One issue per poisoned-item signature | File a GitHub issue for each distinct poisoned/CircuitBreakerOpenError/FAIL:poisoned symptom | They are cascade symptoms of a SINGLE breaker opening, not independent bugs. Naive clustering produced 17 issues for one root cause. | Cluster on the terminal exception type after normalizing repo/number/timestamp out; file 1 root cause + report the cascade (here: 11 signatures, 1,169 occurrences). |
| Reading "using cache" as "no harm" | Assume per-item cache fallback means the run is healthy | The breaker records the failure BEFORE the caller's `except` runs; every swallowed 404 still counts toward the threshold. | A caught exception still trips a shared breaker. Per-item recovery does not imply system recovery. |
| Grepping only for errors during triage | Rely on error greps to enumerate the damage | The silent-corruption twin (issue-number collision across repos) returns a 200 and logs nothing. | Error greps miss the silent half. For each wrong-repo 404, check whether the same number exists in the CWD repo. |

## Results & Parameters

Real run signature (from `build/loop-watch/loop-20260710T055220Z.log`):

```text
# The loud half — six wrong-repo 404s (threshold=5, so the 6th trips it)
ERROR: Non-transient error detected: Could not resolve to an Issue with the number of 751   # Myrmidons#751
WARNING: Failed to fetch comment ids for issue 751 (using cache)
... (ProjectNestor#121, ... — six total)

# Breaker opens; everything after is cascade
raise CircuitBreakerOpenError / GitHubUnavailableError

# Terminal run state
run_end exit_code=130 items=250 agent_jobs=0 interrupted=True
# 236 items poisoned across 9 repos — zero useful work
```

Key constants and locations:

- `_GH_BREAKER` failure_threshold = **5** (6th failure opens it) — `hephaestus/github/client.py`
- Ambient CWD fallback — `get_repo_info(repo_root=None)` → `get_repo_root()` in `git_utils.py`
- Leaking helper — `_fetch_issue_comment_ids(issue_number)` in `hephaestus/automation/github_api/issues.py`
- Silent-twin example — `ProjectAgamemnon#188` (issue) vs `ProjectHephaestus#188` (merged PR)
- Companion learning: the StageQueue is stage-keyed, not repo-homogeneous — resolve repo per issue from `WorkItem.repo`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2047 (merged, CI green); cascade + fix reproduced with runnable scripts; diagnosed from run log `build/loop-watch/loop-20260710T055220Z.log` | Fix threads `(owner, name)` per-issue from `WorkItem.repo`; optional `repo` param preserves ambient behavior for single-repo callers |
