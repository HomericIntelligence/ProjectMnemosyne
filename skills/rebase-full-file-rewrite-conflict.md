---
name: rebase-full-file-rewrite-conflict
description: "Resolve a git rebase conflict where one branch completely rewrote a file and the other branch made small targeted changes to the original. Use when: (1) git rebase reports a conflict on a file that one branch replaced entirely, (2) auto-merge produces incoherent output mixing old and new structure, (3) a post-migration rewrite PR conflicts with a small incremental change on main."
category: architecture
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, rebase, conflict, merge, full-rewrite, migration]
---

# Rebase Full-File Rewrite Conflict

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-29 |
| **Objective** | Resolve a rebase conflict on `docs/architecture.md` where PR #64 completely rewrote the file (post-migration, ~230 lines) and `origin/main` had a small incremental change (one-line ProjectScylla description update in commit `d85bcfa`) |
| **Outcome** | Successful. Took the full rewrite side (`git checkout --theirs`), then manually applied the one-line delta from main. Rebase continued cleanly. |
| **Verification** | verified-local (confirmed by push and GitHub showing MERGEABLE status) |

## When to Use

- `git rebase` reports a conflict and one side of the conflict is a complete file replacement (e.g., a post-migration doc rewrite)
- The auto-merged result contains duplicated sections, mixed old/new structure, or nonsensical content
- One branch rewrote a file top-to-bottom; the other branch changed only 1–3 lines in the old version
- GitHub shows PR as CONFLICTING/DIRTY after a newer commit landed on main that touched the same file

## Verified Workflow

### Quick Reference

```bash
# During git rebase conflict on a fully-rewritten file:

# 1. Identify which side is the full rewrite (usually the PR branch = "theirs" during rebase)
git diff HEAD docs/architecture.md          # what main has
git show REBASE_HEAD:docs/architecture.md   # what the PR commit intended

# 2. Take the full rewrite side entirely
git checkout --theirs docs/architecture.md

# 3. Identify the small delta from the other side (main's commit)
git log --oneline origin/main | head -5     # find the commit that changed the file
git show <commit-sha> -- docs/architecture.md  # see what it changed

# 4. Apply the delta by hand (e.g., update one description line)
# Edit the file to incorporate the small change from main

# 5. Stage and continue
git add docs/architecture.md
git rebase --continue
```

### Detailed Steps

1. **Identify the nature of the conflict.** Run `git diff HEAD docs/architecture.md` and `git show REBASE_HEAD:docs/architecture.md` to understand which side is the rewrite and which is the incremental change.

2. **Do not use `git mergetool` or auto-merge on a full rewrite.** The 3-way merge algorithm will produce a hybrid with sections from both versions interleaved — stale content mixed with new content, broken headings, duplicate tables.

3. **Take the rewrite side explicitly:**
   ```bash
   git checkout --theirs docs/architecture.md
   ```
   During `git rebase`, `--theirs` means the incoming commit being rebased (the PR branch), not the base. Confirm: `git show REBASE_HEAD:docs/architecture.md` should match what you want.

4. **Find the small delta from the other side.** Look at which commit on main changed the file:
   ```bash
   git log --oneline origin/main -- docs/architecture.md
   git show <sha> -- docs/architecture.md
   ```
   The delta will be 1–5 lines. In this session it was: one table row description changed from "chaos testing" to "AI agent ablation benchmarking".

5. **Apply the delta by hand.** Edit the already-accepted rewrite file and incorporate just the changed lines from main's commit. This is always simpler than resolving the full conflict.

6. **Stage and continue:**
   ```bash
   git add docs/architecture.md
   git rebase --continue
   ```

7. **Verify the result** matches the intent of both branches: the full rewrite structure is intact, and the small change from main is present.

**Key insight:** During `git rebase <upstream>`, the conflict sides are:
- `--ours` = the upstream branch (origin/main) — the base you're rebasing onto
- `--theirs` = the commit currently being replayed (the PR branch commit)

This is the **opposite** of `git merge` where `--ours` is your branch. Always verify before choosing a side.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Let git auto-merge the conflict | Allowed `git rebase` to produce a merged result | Result mixed old ai-maestro content with new Agamemnon content, duplicated sections, broken markdown | Never auto-merge when one side is a complete rewrite — the result is always incoherent |
| Use `git checkout --ours` | Attempted to take main's version (the incremental change) | This kept the old pre-migration architecture.md, discarding the entire post-migration rewrite | During `git rebase`, `--ours` is the upstream (main), not the PR branch. Use `--theirs` to get the PR branch version. |
| Copy the clean file from a known-good ref | Did `git show REBASE_HEAD:docs/architecture.md > docs/architecture.md` | This works but skips the manual delta application step — result was missing main's one-line description update | Use `git checkout --theirs` instead (cleaner), then apply the delta explicitly. |

## Results & Parameters

```yaml
repo: HomericIntelligence/Odysseus
context: PR #64 rebase onto origin/main
conflict_file: docs/architecture.md

conflict_shape:
  theirs_size_lines: 234        # PR #64's full post-migration rewrite
  ours_delta_lines: 3           # main's commit d85bcfa: 1 table row + 2 diagram lines updated
  resolution: take_theirs_apply_delta_manually

rebase_sides_reminder:
  git_rebase:
    ours: "upstream branch (origin/main) — base being rebased onto"
    theirs: "the commit being replayed (PR branch commit)"
  git_merge:
    ours: "your current branch"
    theirs: "the branch being merged in"
  # NOTE: --ours/--theirs are SWAPPED between rebase and merge
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | PR #64 rebase onto origin/main, 2026-03-29 | Conflict on docs/architecture.md: 234-line post-migration rewrite vs 3-line incremental update |
