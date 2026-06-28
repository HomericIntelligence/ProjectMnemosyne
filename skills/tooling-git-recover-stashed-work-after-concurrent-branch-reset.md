---
name: tooling-git-recover-stashed-work-after-concurrent-branch-reset
description: "Recover uncommitted work that 'vanished' because a CONCURRENT agent/automation process switched branches and stashed your dirty tree in a SHARED git checkout. Use when: (1) you were editing a working tree on a feature branch and suddenly `git status` is clean and your files are gone from disk, (2) you suspect data loss but never actually committed (you only edited the working tree), (3) multiple agents / automation-loops share ONE git checkout and one of them ran `git checkout main` + `git reset` + `git pull --ff-only` under you, (4) `git stash list` shows an entry labeled 'PRESERVED ... (not mine)' created by the concurrent tooling, (5) you need to confirm the checkout/reset/pull sequence via reflog and re-apply the stash onto a fresh branch."
category: tooling
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, stash, reflog, concurrent, multi-agent, shared-checkout, lost-work, recovery, branch-reset, preserved-stash, automation-loop, stash-apply, commit-early]
---

# Recover Stashed Work After a Concurrent Branch Reset in a Shared Checkout

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-27 |
| **Objective** | Recover a large uncommitted working tree that disappeared after a concurrent agent/automation process switched branches and updated main in a SHARED git checkout |
| **Outcome** | Success — the "lost" work was found in a `PRESERVED` stash entry, re-applied cleanly onto a fresh branch off the updated main, re-verified, and shipped as a PR that passed full CI |
| **Verification** | verified-local (recovery itself verified locally; the recovered work then passed full CI as PR #1668) |

## When to Use

- You were editing a working tree on a feature branch in a checkout that **multiple concurrent agents / automation-loops share**, and your edits suddenly vanished: `git status` is clean and the files are gone from disk.
- You are about to conclude "my work is lost" — STOP and run the triage below first.
- `git stash list` shows an entry labeled like `stash@{0}: ... PRESERVED: ... (not mine)` — that label is created by the concurrent tooling when it stashes a dirty tree before switching branches.
- `git reflog` shows a `checkout: moving from <my-branch> to main`, then `reset: moving to HEAD`, then `pull --ff-only origin main: Fast-forward` sequence you did not initiate.
- You realize the branch you created with `git checkout -b <branch>` **never held any commits** — you only edited the working tree, so the branch pointer was meaningless and your dirty tree was carried/stashed away when another process switched branches.

## Verified Workflow

### Quick Reference

```bash
# === DON'T DESPAIR — triage first. Your work is probably stashed, not lost. ===

# 1. Look for a stash, often labeled PRESERVED by the concurrent tooling
git stash list
#   stash@{0}: On main: PRESERVED: <branch> working tree (not mine)   <-- your work

# 2. Confirm the concurrent checkout/reset/pull sequence and find last-good HEAD
git reflog | head -20
#   <sha> HEAD@{0}: pull --ff-only origin main: Fast-forward
#   <sha> HEAD@{1}: reset: moving to HEAD
#   <sha> HEAD@{2}: checkout: moving from <my-branch> to main   <-- another process switched

# 3. Create a FRESH branch off the now-updated main (do NOT reuse the empty branch)
git checkout -b <newbranch>

# 4. Re-apply the stash — auto-merges cleanly if main moved and files don't overlap
git stash apply stash@{0}        # apply, NOT pop — keep the backup until committed
git status                       # files are back; verify counts/paths

# 5. Re-verify, then COMMIT IMMEDIATELY (sign if the repo requires it)
ruff check . && mypy . && pytest -q     # or this repo's equivalent
git add -A
git commit -S -m "<message>"            # commit promptly — you are still in a shared checkout

# 6. Leave the backup stash in place. Do NOT drop it until committed and pushed.
#    Note: CC Safety Net BLOCKS `git stash drop` — that's fine, a leftover backup is harmless.
```

### Detailed Steps

1. **Recognize the symptom, not the panic.** In a shared/multi-agent checkout, a clean
   `git status` plus missing files almost never means destroyed data — it means another
   process stashed your tree before switching branches. Treat "files gone" as a signal to
   inspect stash + reflog, never as a conclusion of data loss.
2. **`git stash list` first.** The concurrent tooling that resets the shared checkout
   typically stashes the dirty tree with a descriptive label such as
   `PRESERVED: <branch> working tree (not mine)`. That entry is your work. If there are
   multiple entries, the `PRESERVED`-labeled one (usually `stash@{0}`) is the relevant one.
3. **`git reflog` to confirm the sequence.** You should see, newest-first:
   `pull --ff-only origin main: Fast-forward` → `reset: moving to HEAD` →
   `checkout: moving from <my-branch> to main`. This proves an external process moved off
   your branch to update main, and explains why your working tree was carried away.
4. **Create a fresh branch off the updated main.** `git checkout -b <newbranch>`. Do NOT
   try to revive the original `<my-branch>` — it never held a commit, so it has no value;
   branching from the freshly-pulled main gives you the latest base.
5. **`git stash apply stash@{0}` (apply, not pop).** Apply restores all files. If main moved
   while your changes were stashed, git performs a clean three-way auto-merge as long as your
   files don't overlap the incoming changes. Verify with `git status` and a smoke import/test
   that the expected files and content are present.
6. **Re-run verification, then commit immediately.** Run the repo's lint/type/test gates,
   then `git add` + `git commit` (signed if required) right away. You are still in a shared
   checkout — every minute of uncommitted work is exposed to the same concurrent-reset hazard
   that just hit you.
7. **Leave the backup stash in place.** Use `apply`, not `pop`, so the stash survives until
   your work is committed and pushed. Do not try to clean it up — `git stash drop` is blocked
   by the CC Safety Net hook (requires a manual user run), and a leftover backup stash is
   harmless.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Assumed "my branch holds my work" | Relied on `git checkout -b <branch>` to protect in-progress edits while a concurrent process ran | The branch never held a commit — only the working tree was edited. When another process switched branches underneath, the branch pointer was meaningless and the dirty tree was stashed away | In shared/multi-agent checkouts, an uncommitted branch protects nothing. Commit early and in small increments |
| Concluded data loss from a clean `git status` | Saw files gone from disk and `git status` clean, and started treating the work as lost | The work was not deleted — a concurrent process had stashed it (often labeled `PRESERVED`) before switching branches | ALWAYS run `git stash list` (look for `PRESERVED`) and `git reflog` before despairing |
| Planned to reuse / revive the original branch | Tried to go back to `<my-branch>` to find the changes | The branch had zero commits and the working tree had already been moved to a stash | Branch off the freshly-updated main and re-apply the stash there; don't chase the empty branch |
| `git stash pop` to restore work | Instinct was to pop the stash to both restore and clean up | Popping removes the only backup before the work is committed/pushed — risky in a churning shared checkout; also `git stash drop` (pop's cleanup half) is Safety-Net-blocked | Use `git stash apply` and leave the backup stash in place until the work is committed and pushed |

## Results & Parameters

### Recovery parameter map

| Parameter | Value |
| --------- | ----- |
| Environment | Multi-agent / automation-loop SHARED git checkout (e.g. HomericIntelligence ecosystem repos worked on by concurrent agents) |
| Triggering external sequence | `git checkout main` → `git reset` (`reset: moving to HEAD`) → `git pull --ff-only origin main` (`Fast-forward`) run by a concurrent process |
| Stash signature to look for | `stash@{0}: On main: PRESERVED: <branch> working tree (not mine)` |
| Reflog signature | `checkout: moving from <my-branch> to main` followed by reset + ff-pull entries |
| Recovery branch | Fresh `git checkout -b <newbranch>` off the updated main |
| Restore command | `git stash apply stash@{0}` (apply, not pop) |
| Cleanup | Leave the backup stash; `git stash drop` is Safety-Net-blocked and unnecessary |
| Verification level | verified-local — recovery verified locally; recovered work then passed full CI as PR #1668 |

### Copy-paste recovery sequence

```bash
git stash list                       # find the PRESERVED entry (your work)
git reflog | head -20                # confirm checkout/reset/ff-pull sequence
git checkout -b recover-work         # fresh branch off the updated main
git stash apply stash@{0}            # restore (apply, keep the backup)
git status                           # verify files are back
ruff check . && mypy . && pytest -q  # re-verify on the new base
git add -A && git commit -S -m "<message>"   # commit immediately
# do NOT git stash drop — it is Safety-Net-blocked and the backup is harmless
```

### Prevention

- **Commit early and often in shared/multi-agent checkouts.** An uncommitted working tree is
  the only thing a concurrent branch switch can carry away; a committed branch tip survives.
- **Prefer isolated worktrees** (`git worktree add /tmp/<task>`) when working in a checkout
  that concurrent automation may reset, so no other process can switch branches under you.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence ecosystem (shared checkout) | A concurrent automation-loop ran `git checkout main` + `git reset` + `git pull --ff-only origin main` while a large uncommitted working tree sat on a never-committed feature branch. Work appeared lost (clean `git status`, files gone). Found in `stash@{0}: ... PRESERVED: ... (not mine)`; reflog confirmed the checkout/reset/ff-pull sequence. Created a fresh branch off updated main, `git stash apply stash@{0}` restored everything cleanly, re-verified, committed. Recovered work shipped as PR #1668 and passed full CI. | verified-local |
