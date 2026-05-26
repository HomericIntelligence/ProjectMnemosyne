---
name: claude-code-scheduled-tasks-lockfile-gitignore
description: "Untrack and gitignore Claude Code's .claude/scheduled_tasks.lock runtime lockfile to stop end-of-file-fixer pre-commit failures in CI. Use when: (1) CI pre-commit / lint check fails on `Fixing .claude/scheduled_tasks.lock` even though the user's diff didn't touch it, (2) the same failure recurs across unrelated PRs in the same repo, (3) the `/schedule` skill is in use and the lockfile got accidentally committed via `git add .`."
category: ci-cd
date: 2026-05-26
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: claude-code-scheduled-tasks-lockfile-gitignore.history
tags: [claude-code, gitignore, pre-commit, end-of-file-fixer, lockfile, scheduled-tasks, ci-flake, runtime-state]
---

# Claude Code `scheduled_tasks.lock` Gitignore Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Stop CI `pre-commit` / `end-of-file-fixer` failures caused by Claude Code's `/schedule` skill writing a runtime lockfile (`.claude/scheduled_tasks.lock`) that is tracked in git but rewritten at runtime without a trailing newline. The failure bites every PR in the repo, not just the one that "broke" it, because whichever Claude session most recently wrote the file determines the on-disk EOL state at CI checkout time. |
| **Outcome** | Two-part durable fix: `git rm --cached` the file and add it to `.gitignore`. Verified twice: ProjectOdyssey PR #5445 (2026-05-24, commit 702a5a2e) and the recurrence on PR #5457 (2026-05-26) — both unblocked CI. The one-line newline workaround works for the current PR but regresses on the next session. |
| **Verification** | verified-ci |
| **History** | [changelog](./claude-code-scheduled-tasks-lockfile-gitignore.history) |

## When to Use

- CI `pre-commit` workflow or `lint` job fails with `Fix End of Files....Failed` and the log shows `Fixing .claude/scheduled_tasks.lock`.
- The pre-commit hook reports a file was "modified" but the user's commit/diff did not touch that file (giveaway signature).
- Your PR shows status `BLOCKED` despite touching no `.claude/` files at all.
- The same `end-of-file-fixer` failure on `.claude/scheduled_tasks.lock` recurs across multiple unrelated PRs in the same repo (durable fix was never landed to main).
- The `/schedule` skill (Claude Code scheduled tasks / routines) is in use on the project.
- Setting up a new repo or template that will be used with Claude Code — preempt the issue by adding the gitignore entry up front.

## Verified Workflow

### Quick Reference

```bash
# Durable fix (REQUIRED — land to main to stop recurrence)
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

```bash
# Triage workaround (ACCEPTABLE for unblocking a single PR fast, but DOES NOT prevent recurrence)
# Use ONLY when you need the current PR unblocked immediately and cannot wait
# for the durable fix to merge to main. Follow up with the durable fix.
printf '\n' >> .claude/scheduled_tasks.lock
git add .claude/scheduled_tasks.lock
git commit -m "chore: add trailing newline to .claude/scheduled_tasks.lock"
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

2. **Verify the file is tracked on `main`** (root cause of the recurrence):

   ```bash
   git ls-tree -r origin/main --name-only | grep scheduled_tasks.lock
   ```

   If this returns a hit, every CI run on every PR is vulnerable — the durable fix MUST land to main.

3. **Apply the durable fix.** Untrack the file from git's index (do NOT delete the working copy — `/schedule` will keep using it) and add it to `.gitignore`:

   ```bash
   git rm --cached .claude/scheduled_tasks.lock
   ```

   Place the gitignore entry next to the existing `.claude/worktrees/` line so the Claude-Code-runtime ignores are grouped:

   ```gitignore
   .claude/worktrees/
   .claude/scheduled_tasks.lock
   ```

4. **Commit both changes in the same commit** so the next checkout of this branch has the file untracked AND ignored simultaneously.

5. **Land the durable fix to `main` ASAP.** A feature branch fix only unblocks one PR. If you only apply the workaround (or the durable fix) to your own feature branch, the failure will recur on the next PR opened in this repo by anyone else.

6. **Verify in CI.** Push the branch and confirm the `pre-commit` and `lint` checks pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-run pre-commit locally on a different machine | Hoped a fresh `end-of-file-fixer` pass would settle the file | The lockfile is rewritten every time `/schedule` acquires the lock; it's perpetually missing its trailing newline | Don't fight the hook — untrack the file from git entirely |
| Manually append a trailing newline and commit (treated as durable fix) | Treated `printf '\n' >> .claude/scheduled_tasks.lock` as the fix | The next `/schedule` invocation in any session rewrote the file with no trailing newline, regressing immediately on the next PR | The newline trick is a TRIAGE workaround, not a fix. It buys you one passing CI run, then the failure recurs |
| Add `.claude/scheduled_tasks.lock` to `.gitignore` without `git rm --cached` | Just gitignored, no index removal | `.gitignore` does NOT untrack files already in the index; the file stays tracked and CI keeps failing | Both steps are required: `git rm --cached` AND `.gitignore` entry |
| Ignore the failure as "unrelated to my PR — someone else will fix it" | Left the PR `BLOCKED`, hoped repo maintainers would land the durable fix | Nobody owns the durable cleanup unless you do; the PR stays blocked indefinitely while the same failure hits every other PR in the repo | If the failure is blocking your PR, it's yours to fix. The durable fix is one commit — land it |
| Apply the durable fix only to a feature branch (PR #5445), assuming it would propagate | Landed `git rm --cached` + `.gitignore` on the AnyTensor repro branch, expected the cleanup to "stick" | If the durable fix branch is rebased / squashed / abandoned before merging to main, the file stays tracked on main and the failure recurs on the next PR (PR #5457, two days later) | The durable fix MUST merge to main. Until it does, every PR in the repo remains vulnerable |

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

**General pattern — tracked runtime-mutable files cause CI flakes:**

Any file that satisfies all three of (a) tracked in git, (b) rewritten at runtime by a tool, (c) subject to a normalizing pre-commit hook (end-of-file-fixer, trailing-whitespace, mixed-line-ending) will cause this exact failure mode. The fix is always the same: `git rm --cached` + `.gitignore`. Watch for:

- `.claude/scheduled_tasks.lock` (Claude Code `/schedule`)
- `.idea/workspace.xml` (JetBrains workspace state)
- `.vscode/settings.json` (when per-user, not per-project)
- `.DS_Store` (macOS Finder metadata)
- Editor swapfiles, lock files, PID files, session caches

**Verification evidence:**

- ProjectOdyssey PR #5445, commit 702a5a2e (2026-05-24) — `pre-commit` and `lint` Required Checks transitioned FAILURE → SUCCESS after applying durable fix.
- ProjectOdyssey PR #5457 (2026-05-26) — same failure recurred on unrelated autograd Phase 2 work because the durable fix from PR #5445 had not landed to main. One-line newline workaround unblocked the PR; durable fix landing tracked separately.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5445 (AnyTensor overload repro branch, 2026-05-24) — CI `pre-commit` and `lint` checks failing every push on `Fixing .claude/scheduled_tasks.lock` despite unrelated diff | Two-part fix (`git rm --cached` + `.gitignore` entry) on commit 702a5a2e unblocked CI; both checks went FAILURE → SUCCESS |
| ProjectOdyssey | PR #5457 (autograd Phase 2 substrate, 2026-05-26) — same failure recurred on totally unrelated branch because the durable fix from PR #5445 had not merged to main | One-line `printf '\n' >> .claude/scheduled_tasks.lock` workaround unblocked the PR; CI then passed. Demonstrates that the durable fix MUST land to main, not just a feature branch |
