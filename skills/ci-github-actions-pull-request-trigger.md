---
name: ci-github-actions-pull-request-trigger
description: "GitHub Actions pull_request workflows not triggering after push. Use when: (1) commits pushed to a PR branch don't trigger on: pull_request workflows, (2) path-filtered CI is silently skipped after normal commits, (3) required status checks are missing after push and PR can't merge, (4) workflow_dispatch passed but the required check still shows missing."
category: ci-cd
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - pull_request
  - force-push
  - rebase
  - status-checks
  - path-filter
  - branch-protection
---

# GitHub Actions pull_request Event Not Triggering

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Reliably trigger `on: pull_request` GitHub Actions workflows when normal pushes fail to re-trigger CI |
| **Outcome** | Force push after rebase (or empty amend) reliably triggers pull_request event; all required checks passed; PR merged |
| **Verification** | verified-ci |

## When to Use

- Commits pushed to a PR branch don't trigger `on: pull_request` workflows
- Path-filtered CI workflows are silently skipped (GitHub sees no changed files matching `paths:`)
- Required status checks are absent after push — PR is blocked from merging
- `workflow_dispatch` passed but the required check still shows as missing/pending
- CI was previously triggered on the PR but subsequent pushes don't re-trigger it
- Empty commit + push trick didn't work

## Verified Workflow

### Quick Reference

```bash
# When CI isn't triggering on a PR branch:
git fetch origin
git rebase origin/main        # rebase on latest main (resolve conflicts if any)
git push --force-with-lease   # force push triggers the pull_request event

# If branch is already up-to-date with main (no rebase needed):
git commit --amend --no-edit   # changes the commit SHA without changing content
git push --force-with-lease    # new SHA triggers the event
```

### Detailed Steps

1. **Confirm the problem**: Check that workflows are not running via `gh pr checks <pr-number>` — if no checks are listed or they show as skipped, CI is not triggering.

2. **Do NOT try these first** (see Failed Attempts below):
   - Empty commit + push
   - Closing and reopening the PR
   - `workflow_dispatch` manual trigger

3. **Fetch and rebase**:
   ```bash
   git fetch origin
   git rebase origin/main
   # Resolve any conflicts if present
   ```

4. **Force push with lease** (safer than `--force`):
   ```bash
   git push --force-with-lease
   ```

5. **Verify CI triggered**: Check `gh pr checks <pr-number>` — within ~30 seconds the `pull_request` event workflows should appear as queued/in-progress.

6. **If branch is already up-to-date** with main and no rebase is needed, an empty amend achieves the same SHA change:
   ```bash
   git commit --amend --no-edit
   git push --force-with-lease
   ```

### Why This Works

A force push updates the branch tip SHA. GitHub evaluates the new SHA against all `pull_request` triggers, including those with `paths:` filters. The `paths:` filter re-evaluates which files changed between the PR base and the new tip — if any match, the workflow runs. A regular push after an empty commit has no file diff against the PR base, so path-filtered workflows skip it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Empty commit + push | `git commit --allow-empty -m "ci: trigger checks"` then `git push` | No files changed between the empty commit and the PR base — path-filtered workflows see no matching changed files and skip entirely | Empty commits do not re-evaluate path filters; they show zero file diff |
| Close and reopen PR | `gh pr close <pr> && gh pr reopen <pr>` | GitHub may re-trigger some workflows on reopen, but this is unreliable; required status checks may still show as missing | Not a reliable trigger for path-filtered or branch-protected workflows |
| `workflow_dispatch` manual trigger | `gh workflow run <workflow.yml> --ref <branch>` | The workflow runs and the code can be verified to pass, BUT `workflow_dispatch` runs do **not** satisfy branch protection required status checks — those specifically require the check to pass on a `pull_request` event | `workflow_dispatch` ≠ required check; always ensure CI is triggered by `pull_request` event |

## Results & Parameters

### Verification confirmed on

- **Project**: ProjectHermes
- **PR**: #291
- **Branch**: `192-193-auto-impl`
- **Workflow triggers**: `on: pull_request` with `paths:` filters
- **Required checks**: "Lint & Test", "Integration Tests (NATS)", "Secret Scanning (gitleaks)"
- **Resolution**: `git rebase origin/main && git push --force-with-lease` triggered all three required checks; PR merged successfully

### Key distinction: workflow_dispatch vs pull_request required checks

```
workflow_dispatch run result:  ✅ passes (confirms code is correct)
                                BUT does NOT appear in branch protection required checks

pull_request event run result: ✅ appears in required checks
                                AND satisfies branch protection merge gate
```

Branch protection rules require checks to run on the `pull_request` event specifically.
Always ensure CI is triggered via a push to the PR branch (not manual dispatch).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | PR #291, branch `192-193-auto-impl`, path-filtered workflows | Force push after rebase triggered all three required checks; PR merged |
