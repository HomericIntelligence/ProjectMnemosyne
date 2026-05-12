---
name: tooling-gh-pr-auto-merge-rebase-squash-fallback
description: "EVERY HomericIntelligence repo (verified org-wide as of 2026-05-11) rejects `gh pr merge --auto --rebase` with the GraphQL error 'rebase merging is not allowed on this repository (enablePullRequestAutoMerge)'. Default to `--auto --squash` for any HomericIntelligence repo. Use when: (1) opening PRs on any HomericIntelligence repo and arming auto-merge, (2) writing skills/agents/hooks that call `gh pr merge --auto`, (3) you observe a repo's UI lets you manually rebase-merge but auto-merge with rebase fails, (4) you want a single command pattern that works across all HomericIntelligence repos without per-repo branching, (5) updating stale skills (e.g. multi-repo-pr-orchestration-swarm-pattern v2.2.0) that still scope rebase rejection to specific repos like Myrmidons."
category: tooling
date: 2026-05-11
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: tooling-gh-pr-auto-merge-rebase-squash-fallback.history
tags:
  - gh-cli
  - auto-merge
  - rebase
  - squash
  - github
  - pr-automation
  - fallback-pattern
  - homericintelligence-org-policy
---

# Skill: gh pr merge --auto on HomericIntelligence — Default to --squash

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | Make `gh pr merge --auto` reliably arm auto-merge on every HomericIntelligence repo. As of 2026-05-11 the entire org has rebase auto-merge disabled at the repo settings level — there is no longer a "some repos" caveat. |
| **Outcome** | Two recommended patterns: (a) for HomericIntelligence callers, use `--auto --squash` unconditionally — saves a round-trip per PR; (b) for portable skills that may run against non-HomericIntelligence repos, use the `--rebase`-first-then-fall-back-on-specific-error pattern from v1.0.0. The 2026-05-11 ecosystem-wide easy-issue sweep produced 11 PRs across 11 repos — all 11 rejected `--rebase`, all 11 accepted `--squash`. |
| **Verification** | verified-ci — 11 PRs across 11 distinct HomericIntelligence repos in a single sweep, unanimous behavior. Each PR's CI completed and the auto-merge armed cleanly with `--squash`. |
| **History** | [changelog](./tooling-gh-pr-auto-merge-rebase-squash-fallback.history) |

## When to Use

- You are about to run `gh pr merge --auto` against any HomericIntelligence repo (org-wide finding — no per-repo check needed)
- You ran `gh pr merge <PR> --auto --rebase` and got:
  > `GraphQL: Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)`
- You are writing a skill, hook, or agent that calls `gh pr merge --auto` across multiple HomericIntelligence repos
- A repo's web UI lets you manually rebase-merge a PR, yet `gh pr merge --auto --rebase` is still rejected — `enablePullRequestAutoMerge` is a separate setting from the merge methods exposed to the UI
- You are auditing a skill that asserts rebase auto-merge "works on most repos except X" (e.g. `multi-repo-pr-orchestration-swarm-pattern` v2.2.0 currently lists Myrmidons / AchaeanFleet) — that scoping is stale; this skill supersedes it
- You want the fallback to be precise — only fall through on the *specific* method-not-allowed error, not on auth/network errors that should bubble up

## Verified Workflow

### Quick Reference

```bash
# RECOMMENDED for HomericIntelligence repos (skip the round-trip — rebase always fails):
gh pr merge "$PR" --auto --squash --repo "HomericIntelligence/$REPO"

# PORTABLE FALLBACK (use when the skill may target non-HomericIntelligence repos):
gh pr merge "$PR" --auto --rebase 2>/dev/null || gh pr merge "$PR" --auto --squash

# PRECISE PORTABLE FORM (preferred for automation — only falls through on the specific error):
out=$(gh pr merge "$PR" --auto --rebase 2>&1) || true
if echo "$out" | grep -q "rebase merging is not allowed"; then
  gh pr merge "$PR" --auto --squash
elif [ -n "$out" ]; then
  echo "$out" >&2  # surface unexpected errors (auth, network, missing PR, etc.)
fi
```

### Phase 1: Decide Whether to Skip the Rebase Attempt

If the target repo is **any HomericIntelligence repo**, skip directly to `--squash`. Verified org-wide as of 2026-05-11 across 11 repos.

If the skill is portable (may be invoked against a non-HomericIntelligence repo), keep the `--rebase`-first attempt with a precise fallback as documented in v1.0.0.

### Phase 2: Apply the Squash Auto-Merge

```bash
gh pr merge "$PR" --auto --squash --repo "HomericIntelligence/$REPO"
```

On success, gh emits no stdout — silent success is expected. To verify:

```bash
gh pr view "$PR" --repo "HomericIntelligence/$REPO" \
  --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
# Expect: SQUASH
```

### Phase 3: Wire It Into Automation

Recommended pattern for HomericIntelligence-only automation:

```bash
# After `gh pr create ...` returns the PR URL or number:
PR_NUM=$(gh pr view --json number --jq .number)
gh pr merge "$PR_NUM" --repo "HomericIntelligence/$REPO" --auto --squash
```

Recommended pattern for portable automation (try rebase first, fall back precisely):

```bash
PR_NUM=$(gh pr view --json number --jq .number)
out=$(gh pr merge "$PR_NUM" --repo "$REPO_FULL" --auto --rebase 2>&1) || true
if echo "$out" | grep -q "rebase merging is not allowed"; then
  gh pr merge "$PR_NUM" --repo "$REPO_FULL" --auto --squash
elif [ -n "$out" ]; then
  echo "$out" >&2
  exit 1
fi
```

### Phase 4 (Optional): Pre-Flight Detection

A pre-flight check via the GitHub API is **unreliable** for non-admin tokens:

```bash
gh api repos/HomericIntelligence/$REPO --jq '{allow_merge_commit, allow_rebase_merge, allow_squash_merge}'
```

This returns `null` for all three fields when the calling token lacks admin scope — which is the common case for bot/PAT callers. **Do not rely on this check.** Default to `--squash` for HomericIntelligence repos and use the precise fallback pattern for portability.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `gh pr merge <PR> --auto --rebase` against Odysseus PR #275 (2026-05-06) | GraphQL error: "Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)" | The repo-level auto-merge config can disallow `--rebase` even if rebase merging works via the UI for manual merges. |
| 2 | Assuming `--rebase` always works because it works in another repo in the same org | Org-wide settings != per-repo `enablePullRequestAutoMerge` settings (true at the time; later evidence shows the org-wide setting is now uniformly disallowing rebase auto-merge) | Each repo needs its own check; later confirmed all 11 fail uniformly. |
| 3 | Trusting the v2.2.0 `multi-repo-pr-orchestration-swarm-pattern` claim that only Myrmidons (and previously AchaeanFleet) reject auto-merge rebase, then hardcoding `--rebase` for the other repos in a 2026-05-11 ecosystem-wide easy-issue sweep | All 11 PRs across 11 distinct HomericIntelligence repos rejected `--rebase` with the GraphQL `enablePullRequestAutoMerge` error. The "some repos" scoping is now stale. | Default `--squash` for any HomericIntelligence repo; treat the v2.2.0 skill's per-repo allowlist as out-of-date until that skill is amended. |
| 4 | Using `gh api repos/<repo> --jq '.allow_rebase_merge'` as a pre-flight detection step | The API returned `null` for `allow_merge_commit`, `allow_rebase_merge`, and `allow_squash_merge` because the calling PAT lacked admin scope | Pre-flight detection is unreliable without admin scope; just default to `--squash` for HomericIntelligence. |
| 5 | Glossing over the GraphQL error in JSON-mode `gh` output during a multi-PR loop | The error text `"Merge method rebase merging is not allowed"` is clear when read individually but easy to miss when 11 PRs scroll past in JSON mode | When auto-merging in a loop, capture stderr per PR and surface non-zero exits explicitly — do not let them disappear into a `|| true` aggregator. |

## Results & Parameters

### The Exact Error String

```
GraphQL: Merge method rebase merging is not allowed on this repository (enablePullRequestAutoMerge)
```

The literal substring to match in fallback logic is `rebase merging is not allowed`. Matching on `enablePullRequestAutoMerge` works too but is less robust if GitHub changes the wording around the setting name.

### The Working Command (HomericIntelligence default)

```bash
gh pr merge "$PR" --auto --squash --repo "HomericIntelligence/$REPO"
```

Silent success — no stdout output. Exit code 0. Verify via:

```bash
gh pr view "$PR" --repo "HomericIntelligence/$REPO" --json autoMergeRequest
# autoMergeRequest.mergeMethod will be "SQUASH" once armed
```

### Why Default `--squash` for HomericIntelligence (v2.0.0 change)

- **Empirical**: 11/11 PRs across 11/11 HomericIntelligence repos in the 2026-05-11 sweep rejected `--rebase`. There is no remaining HomericIntelligence repo for which rebase auto-merge is known to work.
- **Performance**: skipping the failed `--rebase` attempt saves one GraphQL round-trip per PR. At scale (a 16-PR sweep), that is 16 wasted API calls.
- **Clarity**: removes the need for stderr-capture-and-grep boilerplate in HomericIntelligence-only callers.
- **Trade-off**: gives up linear history (squash collapses commits). For HomericIntelligence repos this trade-off has already been made at the org-policy level — there is no rebase auto-merge to recover.

### Why the `--rebase`-First Portable Pattern Is Still Valid

- For skills that target arbitrary GitHub orgs, `--rebase` may still be allowed
- The precise fallback pattern (grep for `"rebase merging is not allowed"`) gives clean signal: known-bad config = fall through, anything else = surface and stop
- Falling back is cheap; falling forward is impossible (auto-merge can only be armed with one method at a time, and re-arming requires a cancel)

### Why Not the `||` One-Liner in HomericIntelligence Automation

```bash
gh pr merge "$PR" --auto --rebase 2>/dev/null || gh pr merge "$PR" --auto --squash
```

This works interactively but is too coarse for HomericIntelligence automation:

- It swallows all errors, not just the method-not-allowed error
- An auth failure, network timeout, or wrong PR number would silently fall through to a `--squash` attempt that also fails — but with a confusing error
- For HomericIntelligence repos, you already know the rebase will fail — skip it entirely

### Verification Checklist

- [ ] For HomericIntelligence repos: `gh pr merge --auto --squash` returns exit 0 with no stdout
- [ ] `gh pr view "$PR" --json autoMergeRequest` shows `mergeMethod: SQUASH`
- [ ] If you used the portable `--rebase`-first pattern, the first call either succeeds (non-HomericIntelligence repos) or fails with the exact `rebase merging is not allowed` substring (HomericIntelligence repos)
- [ ] Unrelated errors (auth, network, missing PR) still surface and exit non-zero — they are not silently swallowed

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | 2026-05-06 — PR #275 | First observation of the mismatch in the Odysseus repo; rebase merging works via UI for manual merges but not for auto-merge |
| HomericIntelligence/Odysseus | 2026-05-06 — PR #276 | Confirms the repo config is the cause, not a transient API issue |
| HomericIntelligence/AchaeanFleet | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectAgamemnon | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectArgus | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectCharybdis | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectHermes | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectKeystone | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectMnemosyne | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectNestor | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectProteus | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectScylla | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| HomericIntelligence/ProjectTelemachy | 2026-05-11 — easy-issue sweep PR | `--auto --rebase` rejected, `--auto --squash` accepted |
| **2026-05-11 ecosystem-wide easy-issue sweep summary** | 11 PRs across 11 repos in a single session | Unanimous — every `--rebase` attempt rejected, every `--squash` attempt accepted. Org-wide org policy as of this date. |
