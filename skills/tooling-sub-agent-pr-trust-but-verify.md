---
name: tooling-sub-agent-pr-trust-but-verify
description: "Verify sub-agent PR reports against the GitHub API before assuming success. Use when: (1) a sub-agent reports a PR was opened/merged/auto-armed, (2) you need to confirm scope and merge state of an opaque-to-you sub-agent run."
category: tooling
date: 2026-05-06
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - sub-agent
  - pr-merge
  - gh-cli
  - verification
  - mergeable
  - trust-but-verify
  - orchestration
---

# Skill: Trust-But-Verify Discipline for Sub-Agent PR Reports

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-06 |
| **Objective** | Avoid downstream cascade failures from incorrect "PR done" reports by sub-agents that summarize intent rather than reality. |
| **Outcome** | Caught a real conflict (PR with `mergeable: CONFLICTING`) that the sub-agent reported as "auto-squash armed." Caught a false "auto-merge armed" that was actually a silent no-op (repo forbade rebase merges). |
| **Verification** | verified-local — observed live during the Atlas v0.2.1 patch series in May 2026, against HomericIntelligence/ProjectArgus. Not exercised by CI. |

## When to Use

- A sub-agent reports `auto-squash armed` or `auto-rebase armed` for a PR
- A sub-agent reports a PR is "merged" or "ready to merge"
- You're chaining work on top of a sub-agent's PR (next-PR-rebase-stacks-on-it)
- Multiple concurrent sub-agents touched files that might collide

## Verified Workflow

### Quick Reference

```bash
# After every sub-agent reports a PR is done, run this — sub-agent dialogue is intent, not state:
gh pr view <#> --repo <org/repo> --json \
    state,mergedAt,baseRefName,mergeable,mergeStateStatus,additions,deletions,files \
  --jq '{
    state, mergedAt,
    base: .baseRefName,
    mergeable, mergeState: .mergeStateStatus,
    additions, deletions,
    files: [.files[].path]
  }'

# Specifically check for: state == "MERGED" or mergeable == "MERGEABLE"
# Watch for: mergeable == "CONFLICTING" or mergeStateStatus == "DIRTY" → needs manual rebase
# Confirm: files is the expected scope, additions/deletions plausible

# If CONFLICTING, rebase in the sub-agent's worktree:
cd /tmp/<sub-agent-worktree> && git fetch origin && git rebase origin/<base>
# resolve conflicts, push --force-with-lease, re-arm auto-merge
```

### Detailed Steps

1. Sub-agent finishes and reports the PR number, URL, and a "merged" / "auto-armed" claim.
2. Run the `gh pr view --json` query above. Confirm:
   - `state` matches the claim (MERGED if claimed merged; OPEN if claimed armed)
   - `mergeable` is `MERGEABLE` and `mergeStateStatus` is `CLEAN` or `UNSTABLE` — anything else means the auto-merge will not fire
   - `files` matches the scope you briefed (no surprise files; no files outside the brief)
   - `additions` / `deletions` are the same order of magnitude as the sub-agent reported
3. If `mergeable: CONFLICTING`: a concurrent PR rewrote shared lines. Rebase in the sub-agent's worktree, resolve, force-push.
4. If auto-merge silently failed (sub-agent reports armed, but `autoMergeRequest` is `null` in the API): the repo's allowed merge methods don't include the one the sub-agent tried. Re-arm with the right method (`--squash` instead of `--rebase`, etc.).
5. Only THEN move on to the next dependent task.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust report verbatim | Took "auto-squash merge armed" at face value, queued the next dependent sub-agent on top | The PR was actually `CONFLICTING`. Auto-merge can't fire on a CONFLICTING PR; the next sub-agent's branch was forked off a base that didn't yet contain the conflicting PR's changes, leading to a downstream rebase later anyway. | Sub-agent dialogue is intent. `gh pr view --json mergeable` is state. They diverge often enough that the API call is mandatory. |
| Trust merge-method hint | Sub-agent ran `gh pr merge --auto --rebase`; the command exited 0 silently | Repo had rebase-merge disabled. `gh` errored once verbosely on the first attempt and then silently no-op'd subsequent ones. The PR was sitting OPEN with no auto-merge configured. | Check `autoMergeRequest` in the API response, not just the gh exit code. `null` means no auto-merge is set, regardless of what the command appeared to do. |
| Skim file list | Sub-agent reported "modified subscriber.go and added test" without listing exact paths | A sub-agent's understanding of "modified" can include `go.sum` churn or formatter sweep. One sub-agent's PR included an accidental `go.sum` reorder when it ran `go mod tidy`. | The `files: [.files[].path]` array in `gh pr view --json` is the only authoritative scope. Anything not in your brief belongs in the discussion before merge. |
| Trust "all tests pass" | Sub-agent reports green tests | True at sub-agent's local moment; not necessarily true on origin after a concurrent merge changed shared code. | Re-checking CI status (`statusCheckRollup`) post-rebase is part of verify, not the sub-agent's job. |

## Results & Parameters

### Single canonical verification call

```bash
gh pr view <#> --repo <org/repo> --json \
    state,mergedAt,baseRefName,mergeable,mergeStateStatus,autoMergeRequest,additions,deletions,files,statusCheckRollup
```

Watch fields and what they mean:

- `state`: `OPEN` / `MERGED` / `CLOSED`
- `mergeable`: `MERGEABLE` / `CONFLICTING` / `UNKNOWN`
- `mergeStateStatus`: `CLEAN` / `UNSTABLE` / `BEHIND` / `BLOCKED` / `DIRTY`
- `autoMergeRequest`: object means auto-merge is armed; `null` means it's NOT (regardless of `gh pr merge --auto` exit code)
- `files`: scope check
- `statusCheckRollup`: live CI status

### When sub-agent reports diverge from API state

| Sub-agent says | API actually shows | Action |
|---|---|---|
| "Auto-squash armed" | `autoMergeRequest: null` | Re-arm with the repo's allowed method. Check `mergeCommitAllowed` / `squashMergeAllowed` / `rebaseMergeAllowed` on the repo if needed. |
| "Tests pass" | `statusCheckRollup` has `FAILURE` | Wait or fetch the failure log; sub-agent's local environment may have differed |
| "Merged" | `state: OPEN` | Re-arm; or merge yourself |
| "Modified files X, Y" | `files: [X, Y, Z]` | Read Z and decide if it's acceptable scope creep |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectArgus | Atlas v0.2.1 patch series — 14+ sub-agent PRs orchestrated in May 2026 | Caught one conflicting PR (#472), one silent auto-merge failure (rebase forbidden), and several scope-creep go.sum churns |
