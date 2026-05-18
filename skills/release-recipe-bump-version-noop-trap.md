---
name: release-recipe-bump-version-noop-trap
description: "Diagnose and fix the silent failure where `just release X.Y.Z` (or any recipe wrapping bump-version + git commit + git tag + push --follow-tags) exits non-zero when the pyproject(s) already contain the target version. The bump is a no-op, the subsequent commit fails with 'nothing to commit', and the recipe aborts before tagging — even though nothing is actually wrong. Use when: (1) `just release X.Y.Z` ends with 'nothing added to commit' and 'Recipe `release` failed with exit code 1', (2) `git status` shows clean working tree after a failed release run, (3) a release recipe only stages one of multiple source-of-truth pyproject files, (4) you need to recover and ship the tag manually after a recipe failure."
category: ci-cd
date: '2026-05-18'
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - release
  - just
  - justfile
  - bump-version
  - git-tag
  - pyproject
  - idempotency
  - recipe
---

# Release Recipe Bump-Version No-op Trap

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | Document the silent failure mode where `just release X.Y.Z` exits non-zero because `bump-version.py` is a no-op (versions already at target), causing the following `git commit` to fail. Provide both the verified manual recovery workaround and the proper justfile fix. |
| **Outcome** | Successful — v0.1.0 tag was cut and pushed manually on ProjectAgamemnon during Phase F-6, and the `python-client-release.yml` workflow fired correctly off the tag push. The underlying justfile bug is documented and a fix is staged for a follow-up PR. |
| **Verification** | verified-local |

## When to Use

- `just release X.Y.Z` output ends with:
  ```
  bumped version to X.Y.Z
  bumped version to X.Y.Z
  nothing added to commit but untracked files present (use "git add" to track)
  error: Recipe `release` failed with exit code 1
  ```
- `git status` shows a clean working tree after a failed release attempt
- `grep '^version = ' clients/python/pyproject.toml agamemnon/pyproject.toml` (or your project's equivalents) shows both/all files already at the target version
- A previous release attempt got far enough to bump pyproject files but failed before/at tag-push, and re-running the recipe now appears broken
- The release recipe stages only one of several source-of-truth pyproject files (silently dropping bumps to the unstaged ones)
- You need to recover and ship the tag without polluting git history with a needless version-down-then-up cycle

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm both/all pyprojects are already at the target version
grep -H '^version = ' clients/python/pyproject.toml agamemnon/pyproject.toml

# 2. Skip the broken recipe entirely — create and push the signed tag manually
git tag -s vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z

# 3. Verify the tag is properly signed
git tag --verify vX.Y.Z

# 4. Confirm the release workflow fired off the tag push (not PR merge)
gh run list --workflow=python-client-release.yml --limit=2
```

### Detailed Steps

1. **Confirm this is the no-op trap, not a real failure.** Run `git status` — it should be clean. Then grep every source-of-truth pyproject file for the target version. If they all already show `version = "X.Y.Z"`, the recipe failed because `bump-version.py` had nothing to do, not because of an actual problem.

2. **Skip the recipe; tag manually.** Use `git tag -s` to create a signed annotated tag matching the recipe's convention (typically `vX.Y.Z`). Push with `git push origin vX.Y.Z` — do NOT use `--follow-tags` since there's no commit to push alongside it.

3. **Verify the tag is signed.** Run `git tag --verify vX.Y.Z`. If the release workflow gates on signed tags, this is required.

4. **Confirm the release workflow fired.** Most release workflows trigger on `push.tags: ["v*"]` (not on PR merge). A tag push alone is sufficient to fire them. Use `gh run list --workflow=<release-workflow>.yml --limit=2` to confirm.

5. **File a follow-up PR fixing the recipe.** Apply the justfile patch in Results & Parameters below so the next release run isn't fragile. Two changes are required: (a) stage ALL source-of-truth pyproject files, not just one; (b) gate the commit on `git diff --cached --quiet` so no-op bumps don't abort the recipe.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-run `just release X.Y.Z` after seeing the error | Assumed transient issue; ran the same recipe again | `bump-version.py` is still a no-op (files already at target), so the subsequent `git commit` still has nothing to commit and the recipe still aborts before tagging | Recipe failure is deterministic when bump-version is a no-op; re-running cannot escape the trap |
| `git commit --allow-empty` before re-running the recipe | Tried to satisfy the commit step with an empty commit | Doesn't fix the recipe-flow problem (recipe still runs its own commit), and pollutes history with a meaningless empty commit | Don't paper over recipe bugs with manual side-commits — recover the tag manually instead |
| Edit pyprojects down to `0.0.1` then run `just release X.Y.Z` | Forced bump-version to have work to do | Works mechanically but adds a useless "0.0.1 -> X.Y.Z" version-down-then-up dance to git history; reviewers will (rightly) question it | Manipulating source files to satisfy a broken recipe pollutes history; manual tag-and-push is cleaner |
| Recipe stages only `clients/python/pyproject.toml` (not `agamemnon/pyproject.toml`) | Pre-existing justfile only `git add`s the first pyproject | Silently drops the bump to the second pyproject, leaving it on whatever version the bump script wrote but unstaged — release ships with one file bumped and the other dangling in the working tree | Whenever `bump-version.py` writes to N files, the recipe must `git add` all N — or the bump and the recipe diverge silently |
| **Manual `git tag -s` + `git push origin vX.Y.Z` (winning approach)** | Bypassed the recipe entirely, created a signed annotated tag, pushed it | Worked first try; release workflow fired off the tag push as designed | Release workflows triggered on tag pushes are decoupled from the recipe — manual recovery is safe and clean |

## Results & Parameters

### Diagnostic command set

```bash
# After a failed `just release X.Y.Z`, run all of these:
git status                                              # should be clean
grep -H '^version = ' clients/python/pyproject.toml agamemnon/pyproject.toml
git log --oneline -5                                    # confirm no half-done bump commit
git tag --list 'v*' --sort=-v:refname | head -5         # confirm tag wasn't already cut
```

If `git status` is clean AND all pyproject files already show the target version AND the tag doesn't exist, this is the no-op trap.

### Manual recovery (verified on ProjectAgamemnon 2026-05-18, v0.1.0)

```bash
# Signed annotated tag matching the recipe's convention
git tag -s v0.1.0 -m "v0.1.0"
git push origin v0.1.0

# Verify
git tag --verify v0.1.0
gh run list --workflow=python-client-release.yml --limit=2
```

### Proper justfile fix (apply as follow-up PR)

```diff
 release VERSION push='true':
   #!/usr/bin/env bash
   set -euo pipefail
   if ! [[ "{{VERSION}}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
     echo "error: VERSION must be X.Y.Z (got '{{VERSION}}')" >&2
     exit 1
   fi
   ./scripts/check-release-readiness.sh "{{VERSION}}"
   python3 scripts/bump-version.py "{{VERSION}}"
-  git add clients/python/pyproject.toml
-  git commit -S -m "chore: bump version to v{{VERSION}}"
+  git add clients/python/pyproject.toml agamemnon/pyproject.toml
+  # Only commit if the bump actually changed something
+  if ! git diff --cached --quiet; then
+    git commit -S -m "chore: bump version to v{{VERSION}}"
+  else
+    echo "Version already at {{VERSION}}; skipping no-op bump commit"
+  fi
   git tag -s "v{{VERSION}}" -m "v{{VERSION}}"
   if [ "{{push}}" = "true" ]; then
     git push --follow-tags
   fi
```

Two required changes:

1. **Stage every source-of-truth pyproject** — if `bump-version.py` writes to N files, `git add` must list all N. Whenever a new pyproject is added to the bump script (e.g., ProjectAgamemnon's Phase F-5 added `agamemnon/pyproject.toml` via PR #414), the recipe's `git add` line must be updated in lockstep.

2. **Gate the commit on staged content** — `git diff --cached --quiet` returns non-zero when something is staged. The `if !` inverts it, so the commit runs only when there's actually something to commit. No-op bumps now log a friendly message and continue to tagging instead of aborting.

### Generalization

This trap applies to ANY release recipe (just, make, npm scripts, shell) that follows the pattern:

```
bump-version  →  git commit  →  git tag  →  git push --follow-tags
```

If the bump step can be a no-op (because someone already ran it in a previous, partially-failed attempt), the commit step will fail and abort the chain before the tag is created. The fix is universal: gate the commit on whether anything is actually staged, and ensure the bump and the stage list cover the same files.

### Why this matters for first-time releases too

Even on a brand-new v0.1.0 cut, if a previous attempt got as far as bumping the pyprojects but failed at, say, the pre-commit signing step or tag creation, the second run will hit this trap. The user sees a red error on what they believe is the first real release attempt and assumes the entire release is broken — when in reality the pyprojects are already correctly bumped and only the tag is missing.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Phase F-6 v0.1.0 release cut, 2026-05-18 | `just release 0.1.0` failed with "nothing added to commit"; both `clients/python/pyproject.toml` and `agamemnon/pyproject.toml` already at 0.1.0; manual `git tag -s v0.1.0 && git push origin v0.1.0` succeeded and triggered `python-client-release.yml` |
