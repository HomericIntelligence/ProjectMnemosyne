---
name: tooling-cross-repo-git-history-format-patch-replay
description: "Move a file/package between two INDEPENDENT git repos (e.g. submodules) while preserving its real `git log --follow` commit history. Plain `git mv` only preserves history WITHIN one repo; across submodule boundaries it strands the history. The technique that works: per-file `git format-patch --root --follow --stdout` piped through `sed` (path rewrite) into `git am -3` in the destination. Use when: (1) relocating code from one submodule/repo to another, (2) the issue/plan requires keeping commit history or `git blame`/`--follow`, (3) you assumed `git mv` would carry history across the boundary."
category: tooling
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [git, history-preservation, format-patch, git-am, cross-repo, submodule, migration, follow, planning]
---

# Cross-Repo Git History: format-patch / am Replay

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-20 |
| Objective | Move a Python orchestration layer ProjectKeystone → ProjectAgamemnon (independent submodules of the Odysseus meta-repo) while preserving each file's `git log --follow` history |
| Outcome | Planning-only (R1 re-plan after NOGO). Replaced the plan's plain cross-repo `git mv` with a per-file `format-patch --follow` / `git am -3` replay pipeline that carries pre-move commits across the repo boundary |
| Verification | unverified — technique not executed; no CI ran |

## When to Use

- You are moving a file or package from one repository to another **independent** repository (git submodules are independent repos, each with its own object database).
- The migration plan or GitHub issue requires preserving commit history, `git blame`, or `git log --follow` for the moved files.
- You (or a prior plan) assumed `git mv source dest` across the boundary would keep history — it does NOT; it produces a single "copy-in" commit and breaks the `--follow` chain.
- You want a per-file, reviewable, conflict-tolerant replay rather than rewriting an entire repo with `git filter-repo`/`subtree` (those are heavier and rewrite all of history).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

The core idea: export the **complete** history of each file from the source repo as a patch series (`format-patch --root --follow` walks back to the file's first commit, tracing prior renames), rewrite the path in the patch text so it lands under the destination's package layout, then replay the series in the destination repo with `git am -3` (3-way apply tolerates context drift). Use `--committer-date-is-author-date` so the replayed commits keep their original chronology.

1. **Enumerate the exact files to move.** Scope to verified paths (e.g. top-level `*.py`), not whole directories, so you don't sweep files that must stay.
2. **For each file**, run the export → path-rewrite → replay pipeline (Quick Reference below). Do this per file so a conflict in one file doesn't abort the whole batch.
3. **Prove history landed**: `git -C <dest> log --follow --oneline -- <new/path> | wc -l` must return **> 1** (i.e. pre-move commits are present, not just the single replay/copy commit).
4. **Remove the originals** in the source repo in a follow-up commit (optionally leaving a re-export shim if downstream imports still reference the old location).
5. **Bump submodule pins** in the meta-repo to the new SHAs once both sides land.

### Quick Reference

```bash
# Per-file: preserve full history when moving ONE file across independent repos.
SRC=~/repos/ProjectKeystone          # source repo (its own .git)
DEST=~/repos/ProjectAgamemnon        # destination repo (its own .git)
OLD=src/keystone/orchestration/runner.py
NEW=src/agamemnon/orchestration/runner.py

# 1. Export full history (--follow traces prior renames; --root reaches the first commit),
#    rewrite the path with sed, replay in dest with 3-way apply.
git -C "$SRC" format-patch --root --follow --stdout -- "$OLD" \
  | sed "s#$(dirname "$OLD")/#$(dirname "$NEW")/#g" \
  | git -C "$DEST" am --committer-date-is-author-date -3

# 2. ACCEPTANCE: pre-move commits must be present (count > 1, not just the copy-in commit).
git -C "$DEST" log --follow --oneline -- "$NEW" | wc -l   # expect > 1

# If `git am` halts on a conflict for a file:
#   git -C "$DEST" am --abort   # then resolve path/sed for that file and retry, or
#   git -C "$DEST" am --skip    # to drop a single problematic patch in the series.
```

Notes:
- `sed` rewrites the directory prefix inside the patch's `diff`/`---`/`+++` lines so `am` applies the content under the **new** package path. Match the actual prefix in the patch (the path is relative to the source repo root).
- `--follow` is what carries history through earlier renames; without it the series stops at the most recent rename.
- `-3` (3-way) lets `am` apply even when surrounding context differs slightly in the destination.

## Verified Workflow

_Not applicable_ — unverified; no workflow was executed. This skill was captured during an R1 re-planning session; the pipeline above is a hypothesis to be confirmed by CI/execution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Plain per-file `git mv $OLD $NEW` to move files across the Keystone→Agamemnon boundary | `git mv` preserves `git log --follow` only WITHIN a single repo; submodules are independent repos, so the move lands as one "copy-in" commit and the pre-move history is unreachable in the destination | Use a `format-patch --follow` / `git am -3` replay to carry the real history across the repo boundary |
| 2 | Assumed `format-patch` output could be `git am`'d as-is in the destination | The patch paths are relative to the SOURCE package layout, so `am` would recreate the file under the old path | Rewrite the path inside the patch (`sed 's#old/dir/#new/dir/#g'`) before piping to `am` so it lands under the new package |
| 3 | (Considered) `git filter-repo` / `git subtree split` for the whole directory | Heavier than needed: rewrites entire repo history and complicates per-file scoping when only a subset of files move | Prefer per-file `format-patch`/`am` replay for a scoped, reviewable, conflict-tolerant move |

## Results & Parameters

- **Pipeline:** `git -C <src> format-patch --root --follow --stdout -- <old> | sed 's#<old-dir>/#<new-dir>/#g' | git -C <dest> am --committer-date-is-author-date -3`
- **Acceptance check:** `git -C <dest> log --follow --oneline -- <new> | wc -l` returns **> 1**.
- **Key flags:** `--root` (reach first commit), `--follow` (trace renames), `-3` (3-way apply), `--committer-date-is-author-date` (preserve chronology).
- **Conflict handling:** `git am --skip` (drop one patch) or `git am --abort` (reset and retry with corrected path rewrite).
- **Scope:** per file, not whole directory — keeps files that must stay in the source repo from being swept.
- **Status:** unverified (planning-only); not executed, no CI run.

## Verified On

| Item | Value |
|------|-------|
| Migration | ProjectKeystone → ProjectAgamemnon |
| Meta-repo | Odysseus |
| Issue | #143 (R1 planning) |
| Verification | unverified — not executed |
