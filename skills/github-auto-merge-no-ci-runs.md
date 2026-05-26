---
name: github-auto-merge-no-ci-runs
description: "GitHub auto-merge stalls indefinitely on a CLEAN PR when no CI workflow ever runs on the branch. Use when: (1) PR has mergeStateStatus: CLEAN and auto-merge armed but hasn't merged after hours, (2) gh pr view --json statusCheckRollup returns empty array [], (3) docs-only, pod-spec, or non-code PRs stuck with armed auto-merge, (4) investigating why auto-merge didn't fire on a PR that looks ready, (5) gh pr list returns fewer PRs than expected — default limit is 30 and silently omits older PRs, (6) gh pr merge --auto --squash returns GraphQL 'Pull request is in clean status' error on a CLEAN PR, (7) gh pr merge --auto --squash returns GraphQL 'Pull request is in unstable status' — transient; retry after a few seconds, (8) squash-only repos reject --rebase flag on gh pr merge --auto, (9) scheduled workflow (apply.yml) shows failure on main but required checks all pass, (10) PRs armed with --auto --squash do not auto-fire after branch protection rules are relaxed (e.g., review requirement removed) — must be nudged with manual `gh pr merge <n> --squash`, (11) a required-check gate job (e.g. pr-policy) fails with 'Auto-merge is not enabled' immediately after PR creation though auto-merge IS enabled — a propagation race; re-run the failed job."
category: ci-cd
date: 2026-05-21
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: github-auto-merge-no-ci-runs.history
tags:
  - auto-merge
  - github
  - ci-cd
  - path-filter
  - status-checks
  - docs-only
---

# GitHub Auto-Merge Stalls When No CI Runs

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-23 | Diagnose and fix 11 CLEAN PRs stuck with armed auto-merge for 9+ hours | All 11 PRs merged after path-filter broadening and manual merges |

GitHub auto-merge requires at least one completed status check event before it fires — even
when there are **no required status checks** configured on branch protection. A PR with
`mergeStateStatus: CLEAN`, no required reviews, and auto-merge armed will wait indefinitely
if no CI workflow ever ran on the branch. PRs that touch only paths excluded by every
workflow's `paths:` filter (e.g., `pods/**`, `**/*.md`, `scripts/**`, `justfile`) are the
most common victims because no workflow triggers and zero status check events are generated.

## When to Use

- PR has `mergeStateStatus: CLEAN` and auto-merge armed but hasn't merged after hours
- `gh pr view <n> --json statusCheckRollup` returns empty array `[]`
- `gh run list --branch <headRef>` returns `[]` (zero CI runs ever started on the branch)
- Docs-only (`*.md`), pod-spec (`pods/**`), or other non-code PRs stuck with armed auto-merge
- Investigating why auto-merge didn't fire on a PR that looks ready to merge
- Multiple PRs all show `CLEAN` + armed auto-merge yet sit unmoved for hours
- `gh pr list` returns fewer PRs than expected — default limit is 30 and silently omits older PRs in large repos; use `--limit 200` when arming auto-merge across a backlog
- `gh pr merge --auto --squash` returns GraphQL "Pull request is in clean status" error — transient API lag on CLEAN PRs; retry immediately (second call seconds later succeeds)
- `gh pr merge --auto --squash` returns GraphQL "Pull request is in unstable status" — retry after a few seconds; state often resolves to UNKNOWN which accepts the arm call
- Repo rejects `--rebase` flag on `gh pr merge --auto` — check `allow_rebase_merge` before arming; squash-only repos require `--squash`
- Scheduled workflow (e.g., `apply.yml`) shows `conclusion: failure` on main while all required branch-protection checks pass — verify required checks separately before concluding main is broken
- Branch protection rule was relaxed (e.g., review requirement removed) on a repo with PRs already armed via `gh pr merge --auto`, but the now-unblocked PRs do not auto-fire — issue `gh pr merge <n> --squash` directly to consume the armed state
- A required-check gate job (e.g. `pr-policy`) fails with `Auto-merge is not enabled on this PR` within seconds of PR creation even though auto-merge IS armed — the gate fetched PR metadata before the auto-merge enablement propagated; enable auto-merge faster, and if it still races, re-run the failed job

## Verified Workflow

### Quick Reference

```bash
# Diagnose: confirm zero CI runs on the branch
PR_HEAD=$(gh pr view <pr-number> --json headRefName --jq '.headRefName')
gh run list --branch "$PR_HEAD"
# [] output = no CI ever ran = auto-merge will never fire

# Confirm no required checks and check rollup is empty
gh pr view <pr-number> --json statusCheckRollup,mergeStateStatus,autoMergeRequest

# Manual merge bypass (immediate fix for any stuck CLEAN PR)
gh pr merge <pr-number> --rebase

# Batch manual merge all open CLEAN PRs stuck with no CI
gh pr list --state open --json number,mergeStateStatus,autoMergeRequest \
  --jq '.[] | select(.mergeStateStatus=="CLEAN" and .autoMergeRequest!=null) | .number' \
  | xargs -I{} gh pr merge {} --rebase

# Permanent fix: broaden path filters in ci.yml to include previously-excluded paths
# Add to the paths: block in .github/workflows/ci.yml:
#   - 'pods/**'
#   - 'scripts/**'
#   - '**/*.md'
#   - 'justfile'
```

### Phase 1: Confirm the Root Cause

1. **Check PR merge state and auto-merge status**
   ```bash
   gh pr view <PR_NUMBER> --json mergeStateStatus,mergeable,rebaseable,autoMergeRequest,statusCheckRollup
   ```
   Look for `statusCheckRollup: []` — this is the definitive signal.

2. **Check CI run history on the branch**
   ```bash
   PR_HEAD=$(gh pr view <PR_NUMBER> --json headRefName --jq '.headRefName')
   gh run list --branch "$PR_HEAD"
   ```
   Empty output (`[]`) confirms zero workflow runs ever started on this branch.

3. **Verify branch protection has no required checks**
   ```bash
   gh api repos/<owner>/<repo>/branches/main/protection 2>/dev/null \
     | python3 -c "import json,sys; p=json.load(sys.stdin); print(p.get('required_status_checks',{}))"
   ```
   No required checks + empty statusCheckRollup = auto-merge stall confirmed.

4. **Check which paths the PR touches**
   ```bash
   gh pr diff <PR_NUMBER> --name-only
   ```
   Compare against the `paths:` filter in `.github/workflows/ci.yml`.

### Phase 2: Choose a Fix

Three options based on urgency and permanence needed:

**Option A: Manual merge (immediate, per-PR)**
```bash
gh pr merge <PR_NUMBER> --rebase
```
Best when: one-off situation, PR is already verified CLEAN, need it merged now.

**Option B: Broaden path filters (permanent, prevents recurrence)**
Edit `.github/workflows/ci.yml` to add the missing paths to the `paths:` block:
```yaml
on:
  push:
    paths:
      - '**/*.ts'
      - '**/*.yml'
      - 'pods/**'        # add
      - 'scripts/**'     # add
      - '**/*.md'        # add
      - 'justfile'       # add
```
Best when: multiple PR types are repeatedly hitting this; prevents future stalls.

**Option C: Add an always-runs workflow (nuclear option)**
Create a minimal workflow with no `paths:` filter that always runs and always passes:
```yaml
name: auto-merge-gate
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - run: echo "gate passed"
```
Best when: you want auto-merge to fire on 100% of PRs unconditionally.

### Phase 3: Apply and Verify

After Option B (path filter broadening):
```bash
# Push the ci.yml change on its own branch/PR, then re-run any open stuck PRs
# Existing stuck PRs need a new commit or re-run to trigger CI:
git commit --allow-empty -m "ci: trigger CI run" && git push

# Or manually merge PRs that are already confirmed CLEAN:
for pr in <list-of-stuck-pr-numbers>; do
  gh pr merge $pr --rebase
done
```

After merges:
```bash
# Confirm all target PRs are closed
gh pr list --state open --json number,mergeStateStatus | python3 -c \
  "import json,sys; prs=json.load(sys.stdin); print(f'{len(prs)} still open')"
```

### Required-Check Gate Race (pr-policy)

Some repos add a required CI gate job (e.g. `pr-policy`, often part of a `Required Checks`
reusable workflow) that enforces PR-hygiene rules — for example: the PR body contains a
literal `Closes #N` line, auto-merge is enabled on the PR, and every commit is
cryptographically signed. Such a gate typically fetches PR metadata **live at job runtime**
via `gh pr view --json body,autoMergeRequest` plus a GraphQL signature query.

**The race:** `pr-policy` runs on the `pull_request` event and fires within ~4 seconds of
PR creation. If you run `gh pr create` and then `gh pr merge --auto --squash` as two
sequential commands, the gate can read `autoMergeRequest` **before** the auto-merge
enablement has propagated, failing with `::error::Auto-merge is not enabled on this PR`
even though auto-merge IS enabled moments later. (Observed on ProjectHephaestus
PRs #423 and #428; PR #430 passed first try because auto-merge was enabled fast
enough to beat the job.)

**Fixes, in order of preference:**

1. **Enable auto-merge as fast as possible** after `gh pr create` — ideally before CI
   schedules the gate job. Chain the commands tightly; do not wait between them.

2. **Re-run the failed job.** Because `pr-policy` re-fetches PR metadata live at runtime,
   a re-run re-evaluates against the now-correct auto-merge state and passes:
   ```bash
   gh run rerun <RUN_ID> --failed --repo OWNER/REPO
   ```
   **Caveat:** you cannot re-run while the parent workflow run is still in progress —
   `gh run rerun` errors `This workflow is already running`. Wait until the run's `status`
   is `completed`, then re-run:
   ```bash
   # Poll until completed, then re-run the failed jobs
   gh run view <RUN_ID> --repo OWNER/REPO --json status --jq '.status'  # wait for "completed"
   gh run rerun <RUN_ID> --failed --repo OWNER/REPO
   ```

3. **Editing the PR body does NOT re-trigger the workflow.** The `pull_request` event fires
   on `opened`, `synchronize`, and `reopened` — not on `edited`. After editing the PR body
   to add a missing `Closes #N`, you must still re-run the failed job (fix 2) for the gate
   to re-evaluate; the body edit alone never re-triggers the gate.

**Note on GPG-signed commits:** `git log --show-signature` may locally show `U`
(good signature, untrusted key) — that is fine. GitHub verifies by the registered key, so a
`pr-policy` signature check that queries GraphQL passes on `verified: true`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Waiting for auto-merge to fire | Left 11 CLEAN PRs with auto-merge armed for 9+ hours | GitHub auto-merge never fires with zero status check events, regardless of CLEAN state | Auto-merge is not the same as "merge when CLEAN" — it requires at least one check completion |
| Assuming no required checks = immediate merge | Verified branch protection had no required checks and expected auto-merge to proceed | GitHub still waits for a status check signal even when none are required | The requirement is for a check event to occur, not for any check to pass |
| Checking mergeStateStatus only | Inspected `mergeStateStatus: CLEAN` and assumed merge would proceed | CLEAN means "no conflicts/reviews blocking", not "ready for auto-merge without CI" | Always also check `statusCheckRollup` — empty array is the actual blocker |
| Re-triggering CI via comment | Added a PR comment hoping to re-trigger a CI run | PR comments do not trigger `push` or `pull_request` CI workflows | Must push a new commit or use `gh workflow run` to trigger a run |
| Assuming path-filter change would fix existing PRs | Broadened `paths:` filter on main and expected open PRs to auto-merge | Open PR branches had no new commits; no new CI run was triggered | Existing open PRs need a new commit or manual merge after path-filter is fixed |
| gh pr list without --limit | Listed open PRs with default limit to find unarmed ones | Default limit is 30 — repos with 31+ open PRs silently omit the older ones; armed count appeared correct but 60+ PRs were missed | Always use --limit 200 when arming auto-merge across a repo backlog |
| gh pr merge --auto --squash on CLEAN PR (first call) | Called `gh pr merge --auto --squash` on a PR with `mergeStateStatus=CLEAN` | GitHub GraphQL returns "Pull request is in clean status" — API internal state hadn't caught up yet | Retry immediately; the second call seconds later succeeds without any other change |
| gh pr merge --auto --squash on UNSTABLE PR | Called `gh pr merge --auto --squash` on a PR with `mergeStateStatus=UNSTABLE` | GitHub GraphQL returns "Pull request is in unstable status" — auto-merge cannot be armed while checks are actively failing | Wait a few seconds and retry; state often resolves to UNKNOWN which accepts the arm call |
| Waiting for armed auto-merge to fire after relaxing branch protection review requirement | Removed `REVIEW_REQUIRED` from branch protection on a repo with 23 armed CLEAN PRs and waited | GitHub does not re-evaluate armed auto-merges in response to branch-protection changes alone — it requires a status-check event to fire the recheck | After loosening branch protection, sweep already-armed PRs with `gh pr merge <n> --squash` (no `--auto`) to immediately consume their armed state |
| Ran `gh pr create` then `gh pr merge --auto` sequentially | Issued PR creation and auto-merge enablement as two separate sequential commands | `pr-policy` read `autoMergeRequest` ~4s after PR creation, before enablement propagated → failed with `Auto-merge is not enabled on this PR` | Enable auto-merge fast; if it still races, re-run the failed job |
| Edited the PR body to add `Closes #N` expecting CI to re-evaluate | Edited the PR body and waited for `pr-policy` to re-run against the new body | `pull_request` event does not fire on `edited`, only `opened`/`synchronize`/`reopened` | Re-run the failed job after a body edit; editing alone never re-triggers the gate |
| `gh run rerun` while the parent run was still in_progress | Called `gh run rerun <id> --failed` before the workflow run had finished | Errors `This workflow is already running` | Wait until the run's `status` is `completed`, then `gh run rerun <id> --failed` |

## Results & Parameters

### Diagnosis Decision Tree

```
PR has auto-merge armed but hasn't merged after hours
│
├── Check: gh pr view <n> --json statusCheckRollup
│   ├── statusCheckRollup: [] (empty)
│   │   └── Root cause: ZERO CI RUNS on branch → auto-merge stalls
│   │       └── Fix: Option A (manual merge) or Option B (broaden paths)
│   │
│   └── statusCheckRollup: [... entries ...]
│       └── Check mergeStateStatus
│           ├── BLOCKED → required check failing or review needed
│           ├── DIRTY → merge conflict
│           └── CLEAN → race condition or GitHub API lag; wait or re-check
│
└── Check: gh run list --branch <headRef>
    ├── [] (empty) → confirms no CI ever ran
    └── entries present → CI ran; investigate check results
```

### Key Diagnostic Commands

```bash
# Full PR state snapshot
gh pr view <PR> --json number,title,mergeStateStatus,mergeable,rebaseable,\
autoMergeRequest,statusCheckRollup,headRefName

# Confirm zero runs on branch (root cause confirmation)
gh run list --branch "$(gh pr view <PR> --json headRefName --jq '.headRefName')"

# List all open PRs with CLEAN state and armed auto-merge
gh pr list --state open --json number,title,mergeStateStatus,autoMergeRequest \
  --jq '.[] | select(.mergeStateStatus=="CLEAN" and .autoMergeRequest!=null)'

# Fetch ALL open PRs (not just the default 30)
gh pr list -R "$REPO" --state open --limit 200 --json number,mergeStateStatus,autoMergeRequest

# Check allowed merge methods before arming
gh api repos/$OWNER/$REPO --jq '{rebase: .allow_rebase_merge, squash: .allow_squash_merge, merge: .allow_merge_commit}'

# Distinguish required checks from advisory workflows
gh run list -R "$REPO" --branch main --limit 5 --json workflowName,conclusion,status --jq '.[] | [.workflowName, .status, .conclusion] | @tsv'
```

### Fix Trade-offs

| Fix | Immediacy | Permanence | Side Effects |
| ----- | ----------- | ------------ | -------------- |
| Manual merge (`gh pr merge --rebase`) | Immediate | Per-PR only | None; requires repeating for each stuck PR |
| Broaden `paths:` filter | Next CI push after change | Permanent; all future PRs | CI runs on more PRs (slightly higher CI usage) |
| Always-runs gate workflow | Immediate after merge | Permanent; 100% coverage | Adds a trivial job to every PR run |

### Common Victim PR Types

- `*.md` documentation PRs (README, CONTRIBUTING, SECURITY)
- Pod spec PRs (`pods/**`)
- Build script PRs (`scripts/**`, `justfile`, `Makefile`)
- Config-only PRs (`.env.example`, `.gitignore`, non-workflow YAML)
- Any PR where all changed files are listed under `paths-ignore:` but missed from `paths:`

### Verification Checklist

- [ ] `gh pr view <n> --json statusCheckRollup` returns `[]` (confirms root cause)
- [ ] `gh run list --branch <headRef>` returns empty (confirms no CI triggered)
- [ ] Chosen fix applied (manual merge or path-filter broadened)
- [ ] All previously-stuck PRs confirmed merged or new CI run confirmed triggered
- [ ] `gh pr list --state open` count reduced as expected

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | 11 open PRs stuck 9+ hours with CLEAN + armed auto-merge | Root cause confirmed; path filter broadened; remaining PRs merged manually with `gh pr merge --rebase` |
| ProjectCharybdis | 2026-05-05: 32 open PRs all armed with `--auto --squash`; branch protection initially required 1 review, then user removed the requirement; 23 CLEAN PRs did not auto-fire after relaxation | Manual `gh pr merge <n> --squash` loop consumed armed state; 17 merged cleanly, 6 reported `DIRTY` from sibling-induced conflicts that developed in the meantime |
| ProjectHephaestus | 2026-05-21: required `pr-policy` gate failed `Auto-merge is not enabled` on PRs #423 and #428 — gate read `autoMergeRequest` ~4s after PR creation, before enablement propagated; PR #430 passed first try | Re-ran the failed `pr-policy` job after the parent run completed; live metadata re-fetch re-evaluated against the now-armed auto-merge state and passed |
