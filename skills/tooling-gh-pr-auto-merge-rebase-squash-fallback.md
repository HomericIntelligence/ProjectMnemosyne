---
name: tooling-gh-pr-auto-merge-rebase-squash-fallback
description: "GitHub auto-merge can reject `--rebase` even on repos where rebase merging works for manual merges, due to the separate `enablePullRequestAutoMerge` GraphQL setting. Use when: (1) `gh pr merge --auto --rebase` returns the GraphQL error 'Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)', (2) writing skills/agents that hardcode `--rebase` for auto-merge across multiple repos, (3) you observe a repo's UI lets you manually rebase-merge but auto-merge with rebase fails, (4) you want a single command pattern that works across HomericIntelligence repos with mixed auto-merge configs."
category: tooling
date: 2026-05-06
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - gh-cli
  - auto-merge
  - rebase
  - squash
  - github
  - pr-automation
  - fallback-pattern
---

# Skill: gh pr merge --auto --rebase Fallback to --squash

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-06 |
| **Objective** | Make `gh pr merge --auto` reliably enable auto-merge on repos where the `enablePullRequestAutoMerge` GraphQL setting disallows the rebase method, even when manual rebase merges are permitted |
| **Outcome** | Drop-in two-line fallback: try `--rebase` first, fall back to `--squash` on the specific GraphQL error. Verified live on HomericIntelligence/Odysseus PRs #275 and #276 — both rejected `--auto --rebase`, both succeeded with `--auto --squash` |
| **Verification** | verified-local — observed in a single live session against HomericIntelligence/Odysseus, 2026-05-06. The skill itself has not been exercised by CI |

## When to Use

- You ran `gh pr merge <PR> --auto --rebase` and got:
  > `GraphQL: Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)`
- You are writing a skill, hook, or agent that calls `gh pr merge --auto` across multiple repos and cannot assume all of them allow rebase auto-merge
- A repo's web UI lets you manually rebase-merge a PR, yet `gh pr merge --auto --rebase` is still rejected — `enablePullRequestAutoMerge` is a separate setting from the merge methods exposed to the UI
- You are dogfooding the team policy (memory: "After every `gh pr create`, immediately run `gh pr merge --auto --rebase`") and need it to actually succeed on every repo without manual intervention
- You want the fallback to be precise — only fall through on the *specific* method-not-allowed error, not on auth/network errors that should bubble up

## Verified Workflow

### Quick Reference

```bash
# Single-line fallback (acceptable for interactive use):
gh pr merge "$PR" --auto --rebase 2>/dev/null || gh pr merge "$PR" --auto --squash

# Precise form (preferred for automation — only falls through on the specific error):
out=$(gh pr merge "$PR" --auto --rebase 2>&1) || true
if echo "$out" | grep -q "rebase merging is not allowed"; then
  gh pr merge "$PR" --auto --squash
elif [ -n "$out" ]; then
  echo "$out" >&2  # surface unexpected errors (auth, network, missing PR, etc.)
fi
```

### Phase 1: Detect the Configuration Mismatch

Run the rebase attempt first. If the repo accepts it, you are done — no fallback needed:

```bash
gh pr merge "$PR" --auto --rebase
```

If the command fails with stderr containing `rebase merging is not allowed on this repository (enablePullRequestAutoMerge)`, the repo's auto-merge config disallows the rebase method specifically. The exit code is non-zero and stdout is empty.

### Phase 2: Apply the Squash Fallback

```bash
gh pr merge "$PR" --auto --squash
```

On success, gh emits no stdout — silent success is expected. To verify:

```bash
gh pr view "$PR" --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
# Expect: SQUASH
```

### Phase 3: Wire It Into Automation

Use the precise form in any skill/hook/agent that auto-merges PRs across multiple repos:

```bash
# After `gh pr create ...` returns the PR URL:
PR_NUM=$(gh pr view --json number --jq .number)

out=$(gh pr merge "$PR_NUM" --auto --rebase 2>&1) || true
if echo "$out" | grep -q "rebase merging is not allowed"; then
  gh pr merge "$PR_NUM" --auto --squash
elif [ -n "$out" ]; then
  echo "$out" >&2
  exit 1
fi
```

This keeps the team-preferred `--rebase` as the default, only degrades to `--squash` on the specific config mismatch, and surfaces every other error class for human attention.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `gh pr merge <PR> --auto --rebase` against Odysseus PR #275 | GraphQL error: "Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)" | The repo-level auto-merge config can disallow `--rebase` even if rebase merging works via the UI for manual merges. |
| 2 | Assuming `--rebase` always works because it works in another repo in the same org | Org-wide settings != per-repo `enablePullRequestAutoMerge` settings | Each repo needs its own check; don't assume org consistency. |

## Results & Parameters

### The Exact Error String

```
GraphQL: Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)
```

The literal substring to match in fallback logic is `rebase merging is not allowed`. Matching on `enablePullRequestAutoMerge` works too but is less robust if GitHub changes the wording around the setting name.

### The Working Command

```bash
gh pr merge "$PR" --auto --squash
```

Silent success — no stdout output. Exit code 0. Verify via:

```bash
gh pr view "$PR" --json autoMergeRequest
# autoMergeRequest.mergeMethod will be "SQUASH" once armed
```

### Why `--rebase` First, Not `--squash` First

- Team policy (per user memory: "After every `gh pr create`, immediately run `gh pr merge --auto --rebase`") prefers rebase for linear history.
- Falling back is cheap; falling forward (squashing first then trying to upgrade to rebase) is not possible — once auto-merge is armed with one method, you must cancel and re-arm to change it.
- The `--rebase`-first ordering preserves rebase merges on every repo that allows them and only degrades on the specific repos that do not.

### Why Not the `||` One-Liner in Automation

```bash
gh pr merge "$PR" --auto --rebase 2>/dev/null || gh pr merge "$PR" --auto --squash
```

This works interactively but is too coarse for automation:

- It swallows all errors, not just the method-not-allowed error
- An auth failure, network timeout, or wrong PR number would silently fall through to a `--squash` attempt that also fails — but with a confusing error
- The grep-based form gives clean signal: known-bad config = fall through, anything else = surface and stop

### Verification Checklist

- [ ] First call to `gh pr merge --auto --rebase` either succeeds or fails with the exact `rebase merging is not allowed` substring
- [ ] Fallback `gh pr merge --auto --squash` returns exit 0 with no stdout
- [ ] `gh pr view "$PR" --json autoMergeRequest` shows `mergeMethod: SQUASH` (or `REBASE` on repos that accept it)
- [ ] Unrelated errors (auth, network, missing PR) still surface and exit non-zero — they are not silently swallowed

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | 2026-05-06 — PR #275 (`gh pr merge 275 --auto --rebase` rejected with `enablePullRequestAutoMerge` error; retried with `--auto --squash` and armed cleanly) | First observation of the mismatch in the Odysseus repo; rebase merging works via UI for manual merges but not for auto-merge |
| HomericIntelligence/Odysseus | 2026-05-06 — PR #276 (same session, same behavior reproduced) | Confirms the repo config is the cause, not a transient API issue |
