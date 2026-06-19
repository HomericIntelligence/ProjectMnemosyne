---
name: planning-verify-live-state-before-assuming-work-remains
description: "When an issue describes work to be done (a migration, rename, or config change), verify the LIVE external state FIRST with gh/grep before planning any edits — the work may already be complete, making the correct plan a verify-and-close plan with ZERO source edits. An issue body is a snapshot from when it was filed and drifts: the default branch, CI config, open-PR bases, and linked-issue states all change underneath it. Includes the gh-API gotcha that `gh api repos/ORG/REPO/branches/master` RETURNS the default branch via HTTP redirect for a MISSING branch (false positive that master exists) — use the `git/refs/heads` listing instead. Use when: (1) an issue/ticket describes a migration or change that may already be done, (2) planning work whose premise depends on live external state (default branch, CI config, issue status), (3) before recommending edits driven by an issue's stated assumptions, (4) before writing any 'Files to Modify' that exist only because the issue said so."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Planning: Verify Live State Before Assuming Work Remains

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | When planning an issue that asserts work needs doing (e.g. "5 repos still on master, CI broken"), determine whether that work is already complete BEFORE writing edits — and if it is, produce a verify-and-close plan with zero source changes instead of a rename plan |
| **Outcome** | Successful: live-state verification of GitHub issue #24 ("Standardize default branch name across ecosystem") revealed the migration was ALREADY COMPLETE — all 15 repos default to `main`, no `master` refs exist, all workflows target `main`, all open PRs are based on `main`, all 4 linked tracking issues were already CLOSED. The plan correctly became "verify-and-close, zero source edits." |
| **Verification** | verified-local (the gh/grep commands below were run this session and produced the cited outputs; not validated in ProjectMnemosyne CI) |

## When to Use

- An issue asserts a current state (e.g. "5 repos use master") that you can check directly before planning edits.
- The task premise depends on live GitHub/CI state that drifts after the issue was filed (default branch, CI config, open-PR bases, linked-issue status).
- Before writing any "Files to Modify" list whose entries exist only because the issue said the work was undone.
- Planning a migration, rename, or config-standardization issue that may already have shipped.

## Verified Workflow

The premise of an issue is a snapshot from filing time. Before planning any edit, run the
checks below to establish the LIVE state. If they show the work is done, the deliverable is a
verify-and-close plan (confirm state, close the issue) — not a rename/edit plan.

### Quick Reference

```bash
ORG=HomericIntelligence
REPO=ProjectMnemosyne

# 1. Authoritative default branch (NOT the issue's table)
gh repo view "$ORG/$REPO" --json defaultBranchRef --jq .defaultBranchRef.name

# 2. Prove a branch does NOT exist — list refs, do NOT GET branches/<name>
gh api "repos/$ORG/$REPO/git/refs/heads" --jq '.[].ref'
#   GOTCHA: `gh api repos/$ORG/$REPO/branches/master` returns the DEFAULT
#   branch via HTTP redirect for a missing branch → FALSE POSITIVE.

# 3. Workflow triggers still reference the old branch?
grep -rEn "branches:\s*\[?\s*[\"']?(main|master)" .github/workflows/*.yml

# 4. Any open PR based on something other than main?
gh pr list --repo "$ORG/$REPO" --state open --json baseRefName \
  --jq '[.[]|select(.baseRefName!="main")]|length'

# 5. Linked tracking issue states
gh issue view N --repo "$ORG/$REPO" --json state --jq .state
```

### Detailed Steps

1. **Confirm the real default branch** with `defaultBranchRef` per repo. Treat this as authoritative
   over any table in the issue body. If it already reads `main`, the rename premise is void for that repo.
2. **Prove the old branch is absent** by listing refs (`git/refs/heads`) and checking that
   `refs/heads/master` is NOT in the output. Do NOT probe `branches/master` — see the Failed Attempts
   table; it redirects to the default branch and falsely implies `master` exists.
3. **Check CI triggers** by grepping `.github/workflows/*.yml` for `branches:` entries. Confirm they
   target `main` and not `master`. A "CI broken because workflows point at master" claim is verifiable here.
4. **Semantically classify each `master` literal before editing.** Not every `master` is a branch ref.
   Distinguish: branch refs (rename candidates) vs. `no-commit-to-branch --branch master` pre-commit
   guards (intentional — leaving `master` here is correct) vs. third-party action pins like
   `action@master` (a version ref to someone else's repo — must NOT be rewritten). Blind find/replace
   corrupts the latter two.
5. **Check open-PR bases** — if zero PRs target anything but `main`, there is no in-flight work
   depending on the old branch.
6. **Check linked/tracking issue states** — if the tracking issues are already CLOSED, the work was
   already accepted and closed out; do not re-plan it.
7. **Decide the deliverable from the evidence.** If every check shows the work is complete, write a
   forward-looking verify-and-close plan (state the verification commands and their outputs, then the
   single close step) with an explicit "zero source edits" note — not a rename plan, and not a bare
   retrospective status note.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue's repo table | Took the issue's "these 5 repos use master" table at face value and started listing rename edits | The table was a stale snapshot; all repos had already migrated to `main` — the rename would have been a no-op against current state | Always verify `defaultBranchRef` live per repo before planning any rename |
| Probe `branches/master` to test existence | `gh api repos/ORG/REPO/branches/master` to check whether a `master` branch still exists | For a missing branch GitHub HTTP-redirects to the default branch and returns 200 with the default branch's data → false positive that `master` exists | Use `gh api repos/ORG/REPO/git/refs/heads --jq '.[].ref'` and check for `refs/heads/master`; absence proves non-existence |
| Blind find/replace master→main | Considered a tree-wide literal `master`→`main` substitution to "do the migration" | Corrupts non-branch uses: `no-commit-to-branch --branch master` guards and third-party `action@master` pins are not branch refs of this repo | Semantically classify every `master` literal; only rewrite actual local branch refs |

## Results & Parameters

**Verified outcome for issue #24 (live state, 2026-06-19):**
- All 15 repos: `defaultBranchRef.name == main`.
- No `refs/heads/master` in any of the 5 named repos' ref listings.
- All `.github/workflows/*.yml` triggers target `main`.
- Open PRs based on non-`main`: `0`.
- All 4 linked tracking issues: `state == CLOSED`.
- Correct plan: verify-and-close, **zero source edits**.

**Org plan constraint:** `HomericIntelligence` is on the **FREE** plan, so
`gh api orgs/ORG/rulesets` returns 404/403. Use **repo-level** rulesets
(`gh api repos/ORG/REPO/rulesets`) instead of org-level endpoints.

**Uncertain assumptions of THIS plan (flag for the reviewer):**
- (a) The repo-level `homeric-main-baseline` ruleset's live enforcement/target was NOT directly
  inspected — the org rulesets endpoint 404'd on the FREE plan. Its existence/intent was inferred
  from `justfile:683` + `configs/github/org-ruleset.json`, NOT confirmed against the live API.
- (b) Only the 5 named repos had their refs exhaustively listed (`git/refs/heads`). The other 10 repos
  were checked via `defaultBranchRef` only — sufficient to confirm `main` is default, but their full
  ref lists were not enumerated for stray `master` branches.
- (c) The closing step (closing issue #24) was specified in the plan but NOT executed by the planner —
  it remains an action for the implementer.
