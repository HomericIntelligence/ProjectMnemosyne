---
name: squash-only-repo-merge-method-docs
description: "Repo allows squash-only merges (allow_rebase_merge=false); using --rebase in gh pr merge silently fails to arm auto-merge. Use when: (1) gh pr merge --auto --rebase returns no error but auto-merge is not armed, (2) project docs or CLAUDE.md instruct --rebase for a repo that has disabled rebase merges, (3) verifying which merge method a repo supports before arming auto-merge, (4) updating stale documentation that references the wrong merge flag."
category: ci-cd
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - auto-merge
  - squash
  - rebase
  - github
  - docs
---

# Squash-Only Repo: Use --squash Not --rebase for Auto-Merge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Fix stale `--rebase` instruction in CLAUDE.md for a squash-only repo |
| **Outcome** | CLAUDE.md corrected; PR #668 merged with `autoMergeRequest.mergeMethod=SQUASH` confirmed |
| **Verification** | verified-ci |

Some GitHub repos have `allow_rebase_merge: false` and `allow_squash_merge: true`. When
project documentation (e.g. CLAUDE.md) instructs `gh pr merge --auto --rebase`, auto-merge
silently fails to arm in squash-only repos — `gh pr merge` accepts the command without error
but does not enable auto-merge. The fix is to use `--squash` and to correct any stale docs.

## When to Use

- `gh pr merge --auto --rebase` completes without error but auto-merge is not armed
- Project CLAUDE.md or other docs instruct `--rebase` for a GitHub repo
- Verifying which merge method a repo supports before writing automation or instructions
- Updating stale documentation that references the wrong merge flag for a repo
- CI gate (`pr-policy`) reports auto-merge not enabled even though `--auto` was issued

## Verified Workflow

### Quick Reference

```bash
# Step 1: Check which merge methods the repo allows
gh api repos/OWNER/REPO --jq '{rebase: .allow_rebase_merge, squash: .allow_squash_merge, merge: .allow_merge_commit}'
# Example output: {"rebase": false, "squash": true, "merge": false}

# Step 2: Use the correct flag — squash-only repos require --squash
gh pr merge --auto --squash   # NOT --rebase

# Step 3: Verify auto-merge is armed with the correct method
gh pr view <PR_NUMBER> --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
# Should output: SQUASH
```

### Detailed Steps

1. **Check repo merge settings** before writing any automation or docs:
   ```bash
   gh api repos/OWNER/REPO --jq '{rebase: .allow_rebase_merge, squash: .allow_squash_merge, merge: .allow_merge_commit}'
   ```

2. **Correct any stale documentation**. Common locations to audit:
   - `CLAUDE.md` — Git Workflow section and PR policy section
   - `CONTRIBUTING.md` — PR workflow steps
   - `.claude/shared/` — shared guidance files
   - Automation scripts that call `gh pr merge`

3. **Create a tracking issue** (required by `pr-policy` CI gate):
   ```bash
   gh issue create --title "docs: fix stale --rebase merge instruction (repo is squash-only)" \
     --body "CLAUDE.md instructs gh pr merge --auto --rebase but the repo has rebase disabled."
   ```

4. **Commit the doc fix** (signed), with `Closes #N` in the commit body, and arm auto-merge with `--squash`:
   ```bash
   git commit -S -m "docs(claude): use --squash for auto-merge (repo has rebase disabled)

   Closes #<N>"
   gh pr merge --auto --squash
   ```

5. **Confirm** auto-merge is armed correctly:
   ```bash
   gh pr view <PR> --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
   # Expect: SQUASH
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh pr merge --auto --rebase` on squash-only repo | Issued auto-merge with `--rebase` flag as instructed by stale CLAUDE.md | Repo has `allow_rebase_merge: false`; the command appeared to succeed but auto-merge was not armed | Always verify allowed merge methods with `gh api repos/OWNER/REPO` before using `--rebase` |
| Relying on stale docs | CLAUDE.md documented `--rebase` because it was originally correct | Repo settings changed (or were always squash-only) without corresponding doc update | Docs about merge flags rot silently; audit CLAUDE.md against `gh api` before issuing PRs |

## Results & Parameters

### Repo merge-method audit command (copy-paste ready)

```bash
# Check what merge methods are enabled — run once before writing any PR automation
gh api repos/OWNER/REPO --jq '
  "rebase=\(.allow_rebase_merge) squash=\(.allow_squash_merge) merge=\(.allow_merge_commit)"'
```

### Confirmed settings for ProjectHephaestus

```json
{"rebase": false, "squash": true, "merge": false}
```

Always use `gh pr merge --auto --squash` in ProjectHephaestus (and any repo with the same settings).

### Verification that auto-merge is armed

```bash
gh pr view <PR> --json autoMergeRequest
# Expected (squash-only repo):
# {"autoMergeRequest": {"mergeMethod": "SQUASH", "enabledAt": "...", "enabledBy": {...}}}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-28: CLAUDE.md had stale `--rebase` instruction; PR #668 corrected it | `gh pr view 668 --json autoMergeRequest` confirmed `mergeMethod=SQUASH`; issue #666 |
