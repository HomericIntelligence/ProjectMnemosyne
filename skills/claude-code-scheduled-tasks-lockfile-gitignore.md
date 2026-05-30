---
name: claude-code-scheduled-tasks-lockfile-gitignore
description: "Untrack and gitignore Claude Code's .claude/scheduled_tasks.lock runtime lockfile to stop two distinct failure modes: (a) end-of-file-fixer pre-commit failures in CI, (b) CLI tools like hephaestus-tidy that abort because `git status --porcelain` reports the untracked lockfile as dirty. Use when: (1) CI pre-commit / lint check fails on `Fixing .claude/scheduled_tasks.lock`, (2) a CLI tool refuses to run with `Working tree has uncommitted changes` and `git status --porcelain` shows `?? .claude/scheduled_tasks.lock`, (3) the same failure recurs across unrelated PRs in the same repo, (4) the `/schedule` skill is in use."
category: ci-cd
date: 2026-05-30
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: claude-code-scheduled-tasks-lockfile-gitignore.history
tags: [claude-code, gitignore, pre-commit, end-of-file-fixer, lockfile, scheduled-tasks, ci-flake, runtime-state, hephaestus-tidy, dirty-working-tree, git-status-porcelain]
---

# Claude Code `scheduled_tasks.lock` Gitignore Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-30 |
| **Objective** | Stop two related failure modes caused by Claude Code's `/schedule` skill writing a per-machine, per-process runtime lockfile (`.claude/scheduled_tasks.lock`) that is NOT in the default `.gitignore` of most repositories: (a) CI `pre-commit` / `end-of-file-fixer` rewrites the lockfile (no trailing newline) and the hook fails on every PR; (b) any local CLI tool that gates on `git status --porcelain` (canonical example: `hephaestus-tidy` via `_working_tree_clean()` in `hephaestus/github/tidy.py`) refuses to start, treating the untracked lockfile as a dirty working tree. Both failures share one root cause: the lockfile is held open by a live Claude session, is regenerated on every scheduled-task acquisition, and must not be tracked, stashed, or deleted. |
| **Outcome** | Two-part durable fix: `git rm --cached` the file (if tracked) AND add `.claude/scheduled_tasks.lock` to `.gitignore`. Verified three times: ProjectOdyssey PR #5445 (2026-05-24, commit 702a5a2e), ProjectOdyssey PR #5457 (2026-05-26), and ProjectHephaestus PR #816 (2026-05-30). The Hephaestus run is the strongest evidence — immediately after the gitignore landed on main, `pixi run hephaestus-tidy` ran cleanly and deleted 6 stale merged branches without needing the conflict-resolution swarm. |
| **Verification** | verified-ci |
| **History** | [changelog](./claude-code-scheduled-tasks-lockfile-gitignore.history) |

## When to Use

**CI pre-commit / lint failures:**

- CI `pre-commit` workflow or `lint` job fails with `Fix End of Files....Failed` and the log shows `Fixing .claude/scheduled_tasks.lock`.
- The pre-commit hook reports a file was "modified" but the user's commit/diff did not touch that file (giveaway signature).
- Your PR shows status `BLOCKED` despite touching no `.claude/` files at all.
- The same `end-of-file-fixer` failure on `.claude/scheduled_tasks.lock` recurs across multiple unrelated PRs in the same repo (durable fix was never landed to main).

**Local CLI tools that gate on a clean working tree:**

- `pixi run hephaestus-tidy` (or `hephaestus-tidy --dry-run`) aborts with:

  ```text
  ERROR - Working tree has uncommitted changes. Commit or stash them before running hephaestus-tidy.
  ```

  and `git status --porcelain` reports `?? .claude/scheduled_tasks.lock`. The check lives in `hephaestus/github/tidy.py:76-89` (`_working_tree_clean()`) and treats any non-empty porcelain output as dirty.
- Any other tool that gates on `git status --porcelain == ""` before running (release scripts, pre-push hooks, `release-please`-style guards) refuses to proceed on a freshly cloned Claude Code-active repo.
- You catch yourself wanting to `git stash` or `rm` the lockfile to make a tool happy — DON'T. The live Claude session re-creates it within seconds.

**Preemptive setup:**

- The `/schedule` skill (Claude Code scheduled tasks / routines) is in use on the project.
- Setting up a new repo or template that will be used with Claude Code — preempt both failure modes by adding the gitignore entry up front, BEFORE the file is ever created.

## Verified Workflow

### Quick Reference

```bash
# Durable fix — covers BOTH failure modes (CI pre-commit AND dirty-tree CLI guards)
# Required steps depend on whether the file is currently tracked:

# Case A: file is TRACKED on main (CI pre-commit failure scenario)
git rm --cached .claude/scheduled_tasks.lock

# Case B: file is UNTRACKED but on disk (dirty-tree CLI guard scenario, e.g. hephaestus-tidy)
# No `git rm --cached` needed — just add to .gitignore

# Both cases: append the gitignore entry (relative path, no leading slash — matches in any worktree)
cat >> .gitignore <<'EOF'

# Claude Code scheduled-task runtime lock (per-machine, per-process — not source)
.claude/scheduled_tasks.lock
EOF

# Post-fix sanity check — MUST report the file as ignored before committing
git check-ignore -v .claude/scheduled_tasks.lock
# Expected: .gitignore:N:.claude/scheduled_tasks.lock  .claude/scheduled_tasks.lock

# Confirm `git status --porcelain` is now empty (with the lockfile still on disk)
git status --porcelain
# Expected: (empty)

# Commit and push (sign per repo convention)
git add .gitignore
git commit -S -m "chore: gitignore .claude/scheduled_tasks.lock"
git push
```

```bash
# Triage workaround for CI pre-commit failures ONLY
# (ACCEPTABLE for unblocking a single PR fast, DOES NOT fix the dirty-tree CLI failure mode)
# Use ONLY when the durable fix can't land immediately. Follow up with the durable fix.
printf '\n' >> .claude/scheduled_tasks.lock
git add .claude/scheduled_tasks.lock
git commit -m "chore: add trailing newline to .claude/scheduled_tasks.lock"
git push
```

### Detailed Steps

1. **Confirm the diagnostic signature.** Two distinct shapes — pick the one that matches your failure:

   **Shape A — CI pre-commit (`end-of-file-fixer`) failure.** In the failing CI log:

   ```text
   Fix End of Files.............................................................................Failed
   - hook id: end-of-file-fixer
   - exit code: 1
   - files were modified by this hook

   Fixing .claude/scheduled_tasks.lock
   ```

   If the user's diff doesn't touch this file but the hook keeps rewriting it, you've found it.

   **Shape B — CLI tool refuses to start on a "dirty" working tree.** Tool reports:

   ```text
   ERROR - Working tree has uncommitted changes. Commit or stash them before running <tool>.
   ```

   and:

   ```bash
   git status --porcelain
   # ?? .claude/scheduled_tasks.lock
   ```

   Canonical example: `pixi run hephaestus-tidy` aborts via `_working_tree_clean()` in `hephaestus/github/tidy.py:76-89`.

2. **Determine tracked vs untracked.** This decides whether you need `git rm --cached`:

   ```bash
   # Is it tracked on main? (Shape A scenario)
   git ls-tree -r origin/main --name-only | grep scheduled_tasks.lock

   # Is it tracked in your branch's index?
   git ls-files --error-unmatch .claude/scheduled_tasks.lock 2>/dev/null && echo TRACKED || echo UNTRACKED
   ```

   If tracked anywhere → use `git rm --cached` AND `.gitignore`. If untracked but present → just `.gitignore` (Shape B is usually this).

3. **Apply the durable fix.** Do NOT delete the working copy — `/schedule` will keep using it, and a live Claude session will re-create it within seconds anyway.

   ```bash
   # Only if currently tracked:
   git rm --cached .claude/scheduled_tasks.lock
   ```

   Anchor the gitignore pattern with `.claude/` (no leading slash) so it matches the file in any worktree of this repo, not just at the top-level checkout. Group it with other Claude-Code-runtime ignores:

   ```gitignore
   # Claude Code runtime state — never commit
   .claude/worktrees/
   .claude/scheduled_tasks.lock
   ```

4. **Verify the ignore took effect — BEFORE committing.** This is the universal post-fix sanity check that catches anchoring mistakes (`/.claude/...` vs `.claude/...`) and typos:

   ```bash
   git check-ignore -v .claude/scheduled_tasks.lock
   # Expected: .gitignore:N:.claude/scheduled_tasks.lock  .claude/scheduled_tasks.lock

   git status --porcelain
   # Expected: (empty, with the lockfile still on disk and held by the live session)
   ```

   If `git check-ignore` prints nothing, the pattern is wrong — fix the gitignore line and re-run before committing.

5. **Commit both changes in the same commit** so the next checkout of this branch has the file untracked AND ignored simultaneously. Sign per repo convention (`git commit -S`).

6. **Land the durable fix to `main` ASAP.** A feature branch fix only unblocks one PR. If you only apply the workaround (or the durable fix) to your own feature branch, the failure will recur on the next PR opened in this repo by anyone else.

7. **Verify the fix works.** For Shape A: push and confirm CI `pre-commit` / `lint` go green. For Shape B: re-run the blocked tool (e.g. `pixi run hephaestus-tidy`) and confirm it now starts and completes successfully.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-run pre-commit locally on a different machine | Hoped a fresh `end-of-file-fixer` pass would settle the file | The lockfile is rewritten every time `/schedule` acquires the lock; it's perpetually missing its trailing newline | Don't fight the hook — untrack the file from git entirely |
| Manually append a trailing newline and commit (treated as durable fix) | Treated `printf '\n' >> .claude/scheduled_tasks.lock` as the fix | The next `/schedule` invocation in any session rewrote the file with no trailing newline, regressing immediately on the next PR | The newline trick is a TRIAGE workaround, not a fix. It buys you one passing CI run, then the failure recurs |
| Add `.claude/scheduled_tasks.lock` to `.gitignore` without `git rm --cached` | Just gitignored, no index removal | `.gitignore` does NOT untrack files already in the index; the file stays tracked and CI keeps failing | Both steps are required: `git rm --cached` AND `.gitignore` entry |
| Ignore the failure as "unrelated to my PR — someone else will fix it" | Left the PR `BLOCKED`, hoped repo maintainers would land the durable fix | Nobody owns the durable cleanup unless you do; the PR stays blocked indefinitely while the same failure hits every other PR in the repo | If the failure is blocking your PR, it's yours to fix. The durable fix is one commit — land it |
| Apply the durable fix only to a feature branch (PR #5445), assuming it would propagate | Landed `git rm --cached` + `.gitignore` on the AnyTensor repro branch, expected the cleanup to "stick" | If the durable fix branch is rebased / squashed / abandoned before merging to main, the file stays tracked on main and the failure recurs on the next PR (PR #5457, two days later) | The durable fix MUST merge to main. Until it does, every PR in the repo remains vulnerable |
| Stash the untracked lockfile to make a dirty-tree CLI happy | `git stash push -u .claude/scheduled_tasks.lock` to clear `git status --porcelain` so `hephaestus-tidy` would run | Stashing races with the live Claude session that holds the file open; the next scheduled-task acquisition writes the file again within seconds, so `git status --porcelain` re-populates and the next CLI invocation re-fails | Don't fight the live session. The file is held open by a long-running process — only `.gitignore` actually makes it disappear from `git status` output |
| Delete the lockfile to clear the dirty-tree check | `rm .claude/scheduled_tasks.lock` then re-run `hephaestus-tidy` | The live Claude session re-creates the file immediately on its next scheduled-task acquisition (typically within seconds); there's no way to out-race a process that owns the lock from the client side | The only durable answer is to make git stop reporting the file at all — that requires `.gitignore`, not deletion |

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

**Pattern anchoring matters.** Write the entry as `.claude/scheduled_tasks.lock` (no leading slash), NOT `/.claude/scheduled_tasks.lock`. The unanchored form matches the file in any worktree of this repo (including `.git/worktrees/<branch>/.claude/scheduled_tasks.lock` and nested submodules). The anchored form only matches at the repo root, which silently fails when the same repo is used via `git worktree add` — and that's the common Claude Code workflow.

**Two failure-mode shapes — same fix.**

| Shape | Trigger | Diagnostic |
|-------|---------|------------|
| **A — CI hook rewrites the file** | Lockfile is tracked in git; `end-of-file-fixer` (or any normalizing pre-commit hook) rewrites the no-trailing-newline contents on every CI checkout | `Fixing .claude/scheduled_tasks.lock` in pre-commit log; PR `BLOCKED` despite unrelated diff |
| **B — Local CLI sees dirty tree** | Lockfile is untracked but on disk; tool gates on `git status --porcelain == ""` | `git status --porcelain` returns `?? .claude/scheduled_tasks.lock`; tool prints `Working tree has uncommitted changes` and refuses to start |

Both shapes are fixed by the same gitignore entry. Shape A additionally requires `git rm --cached` if the file was ever tracked.

**Canonical Shape B example: `hephaestus-tidy`.** The pre-check lives in `hephaestus/github/tidy.py:76-89`:

```python
def _working_tree_clean() -> bool:
    """Return True only if the working tree has no uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip() == ""
```

Any non-empty `git status --porcelain` output aborts the run. A single untracked lockfile is enough.

**General pattern — runtime-mutable files cause both CI flakes AND local-tool guard failures.**

Any file that satisfies (a) created/rewritten at runtime by a long-running tool, (b) NOT in `.gitignore` of the repo where it lives, will hit at least one of these failure modes. The fix is always the same: add to `.gitignore` (and `git rm --cached` if tracked). Watch for:

- `.claude/scheduled_tasks.lock` (Claude Code `/schedule`)
- `.idea/workspace.xml` (JetBrains workspace state)
- `.vscode/settings.json` (when per-user, not per-project)
- `.DS_Store` (macOS Finder metadata)
- Editor swapfiles, lock files, PID files, session caches

**Verification evidence:**

- ProjectOdyssey PR #5445, commit 702a5a2e (2026-05-24) — `pre-commit` and `lint` Required Checks transitioned FAILURE → SUCCESS after applying durable fix. (Shape A)
- ProjectOdyssey PR #5457 (2026-05-26) — same failure recurred on unrelated autograd Phase 2 work because the durable fix from PR #5445 had not landed to main. One-line newline workaround unblocked the PR; durable fix landing tracked separately. (Shape A recurrence)
- ProjectHephaestus PR #816, merged 2026-05-30 — `pixi run hephaestus-tidy --dry-run` was permanently aborting with `Working tree has uncommitted changes` because `.claude/scheduled_tasks.lock` was untracked-but-not-ignored on main. Adding the path to `.gitignore` (`git check-ignore -v` confirmed) made `git status --porcelain` return empty with the file still on disk. Tidy then ran successfully and deleted 6 merged branches without needing the conflict-resolution swarm. (Shape B — first verified case)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5445 (AnyTensor overload repro branch, 2026-05-24) — CI `pre-commit` and `lint` checks failing every push on `Fixing .claude/scheduled_tasks.lock` despite unrelated diff (Shape A — tracked lockfile) | Two-part fix (`git rm --cached` + `.gitignore` entry) on commit 702a5a2e unblocked CI; both checks went FAILURE → SUCCESS |
| ProjectOdyssey | PR #5457 (autograd Phase 2 substrate, 2026-05-26) — same Shape A failure recurred on totally unrelated branch because the durable fix from PR #5445 had not merged to main | One-line `printf '\n' >> .claude/scheduled_tasks.lock` workaround unblocked the PR; CI then passed. Demonstrates that the durable fix MUST land to main, not just a feature branch |
| ProjectHephaestus | PR #816 (merged 2026-05-30) — Shape B failure: `pixi run hephaestus-tidy` aborted with `Working tree has uncommitted changes`; `git status --porcelain` reported `?? .claude/scheduled_tasks.lock`. The lockfile was untracked but held open by the live Claude session that issued the tidy command, so stash/delete attempts immediately regressed | Added `.claude/scheduled_tasks.lock` to `.gitignore` (no leading slash, anchored with `.claude/` so it matches in any worktree). `git check-ignore -v` confirmed the rule applied. Post-merge, `pixi run hephaestus-tidy` ran cleanly and deleted 6 stale merged branches without needing the conflict-resolution swarm |
