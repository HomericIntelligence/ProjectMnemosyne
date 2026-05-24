---
name: claude-code-scheduled-tasks-lockfile-gitignore
description: "Untrack and gitignore Claude Code's .claude/scheduled_tasks.lock runtime lockfile to stop end-of-file-fixer pre-commit failures in CI. Use when: (1) CI pre-commit / lint check fails on `Fixing .claude/scheduled_tasks.lock` even though the user's diff didn't touch it, (2) the `/schedule` skill is in use and the lockfile got accidentally committed via `git add .`."
category: tooling
date: 2026-05-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [claude-code, gitignore, pre-commit, end-of-file-fixer, lockfile, scheduled-tasks]
---

# Claude Code `scheduled_tasks.lock` Gitignore Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-24 |
| **Objective** | Stop CI `pre-commit` / `end-of-file-fixer` failures caused by Claude Code's `/schedule` skill writing a runtime lockfile (`.claude/scheduled_tasks.lock`) that was accidentally committed and lacks a trailing newline. |
| **Outcome** | Two-part fix: `git rm --cached` the file and add it to `.gitignore`. After applying on ProjectOdyssey PR #5445 (commit 702a5a2e), the `pre-commit` and `lint` Required Checks went from FAILURE to SUCCESS. |
| **Verification** | verified-ci |

## When to Use

- CI `pre-commit` workflow or `lint` job fails with `Fix End of Files....Failed` and the log shows `Fixing .claude/scheduled_tasks.lock`.
- The pre-commit hook reports a file was "modified" but the user's commit/diff did not touch that file (giveaway signature).
- The `/schedule` skill (Claude Code scheduled tasks / routines) is in use on the project.
- Setting up a new repo or template that will be used with Claude Code — preempt the issue by adding the gitignore entry up front.

## Verified Workflow

### Quick Reference

```bash
# 1. Untrack the lockfile from git (keeps the working copy on disk)
git rm --cached .claude/scheduled_tasks.lock

# 2. Add it to .gitignore (next to the existing .claude/worktrees/ line)
cat >> .gitignore <<'EOF'
.claude/scheduled_tasks.lock
EOF

# 3. Commit and push
git add .gitignore
git commit -m "chore: untrack and gitignore .claude/scheduled_tasks.lock"
git push
```

### Detailed Steps

1. **Confirm the diagnostic signature.** In the failing CI log, look for:

   ```text
   Fix End of Files.............................................................................Failed
   - hook id: end-of-file-fixer
   - exit code: 1
   - files were modified by this hook

   Fixing .claude/scheduled_tasks.lock
   ```

   If the user's diff doesn't touch this file but the hook keeps rewriting it, you've found it.

2. **Untrack the file from git's index** (do NOT delete the working copy — `/schedule` will keep using it):

   ```bash
   git rm --cached .claude/scheduled_tasks.lock
   ```

3. **Add the path to `.gitignore`.** Place it next to the existing `.claude/worktrees/` line so the Claude-Code-runtime ignores are grouped:

   ```gitignore
   .claude/worktrees/
   .claude/scheduled_tasks.lock
   ```

4. **Commit both changes in the same commit** so the next checkout of this branch has the file untracked AND ignored simultaneously.

5. **Verify in CI.** Push the branch and confirm the `pre-commit` and `lint` checks pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-run pre-commit locally on a different machine | Hoped a fresh `end-of-file-fixer` pass would settle the file | The lockfile is rewritten every time `/schedule` acquires the lock; it's perpetually missing its trailing newline | Don't fight the hook — untrack the file from git entirely |
| Manually append a trailing newline and commit | One-shot newline addition to satisfy `end-of-file-fixer` | The next `/schedule` invocation in any session rewrote the file with no trailing newline, regressing immediately | Fix the tracking, not the formatting — runtime state must not be tracked |
| Add `.claude/scheduled_tasks.lock` to `.gitignore` without `git rm --cached` | Just gitignored, no index removal | `.gitignore` does NOT untrack files already in the index; the file stays tracked and CI keeps failing | Both steps are required: `git rm --cached` AND `.gitignore` entry |

## Results & Parameters

**The offending lockfile content** (for recognition — never edit, never commit):

```json
{"sessionId":"c1e70650-1afc-4e7b-b2eb-985706236c40","pid":1497360,"procStart":"14813809","acquiredAt":1779168468293}
```

No trailing newline. Written by Claude Code's `/schedule` skill to coordinate scheduled-task ownership across sessions.

**Recommended `.gitignore` block for any repo using Claude Code:**

```gitignore
# Claude Code runtime state — never commit
.claude/worktrees/
.claude/scheduled_tasks.lock
```

**Other tool-managed runtime files to watch for** (same pattern, same fix — `git rm --cached` + `.gitignore`):

- `.idea/` (JetBrains workspace state)
- `.vscode/settings.json` (when per-user, not per-project)
- `.DS_Store` (macOS Finder metadata)

**Verification evidence:** ProjectOdyssey PR #5445, commit 702a5a2e — `pre-commit` and `lint` Required Checks transitioned FAILURE → SUCCESS after applying this fix; no other changes were needed to unblock CI.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5445 (AnyTensor overload repro branch, 2026-05-24) — CI `pre-commit` and `lint` checks failing every push on `Fixing .claude/scheduled_tasks.lock` despite unrelated diff | Two-part fix (`git rm --cached` + `.gitignore` entry) on commit 702a5a2e unblocked CI; both checks went FAILURE → SUCCESS |
