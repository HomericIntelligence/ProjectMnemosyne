---
name: ci-precommit-whole-dir-format-drift-blocks-unrelated-commits
description: "Pre-commit hooks that run `ruff format` / `ruff check --fix` over WHOLE DIRECTORIES (not just staged files) will reformat pre-existing format drift already committed on `origin/main`, aborting EVERY new commit — even ones touching completely unrelated files — with 'files were modified by this hook'. Use when: (1) you stage only your own clean files but `git commit -S` / `pre-commit run` reformats a DIFFERENT set of files you never touched, then aborts; (2) reverting those reformats makes them reappear on the next commit attempt because the drift lives in main's committed tree; (3) `ruff format --check hephaestus/ scripts/ tests/` reports `Would reformat:` for files unrelated to your change. Fix: land a separate format-only chore(lint) PR first, then stack your feature branches on it."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Pre-commit Whole-Directory Format Drift Blocks Unrelated Commits

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Unblock a stack of 6 fix PRs in ProjectHephaestus whose commits kept aborting because the pre-commit `ruff format` / `ruff check --fix` hooks reformatted pre-existing drift already committed on `origin/main` |
| **Outcome** | Successful — a separate format-only `chore(lint)` PR (#1325) committed exactly the drift-fix diff (behavior-preserving; 199 automation tests passed unchanged), and the 6 feature branches stacked on it commit cleanly |
| **Verification** | verified-local — `ruff format` / `ruff check --fix` were run locally and `pre-commit run` passed clean on the chore branch; CI merge-train confirmation was still pending at capture time |

## When to Use

- You stage ONLY your own clean files, run `git commit -S` (or `pre-commit run`), and the hook reformats a **different** set of files you never touched, then aborts the commit with "files were modified by this hook".
- `ruff format --check hephaestus/ scripts/ tests/` against the committed `origin/main` content reports `Would reformat: <files>` for files **unrelated** to your change.
- Reverting those reformats with `git checkout --` / `git stash` just makes them reappear on the next commit attempt — because the drift lives in the committed tree on `main`, not in your working changes.
- The pre-commit config runs the formatter/linter over whole directory arguments (e.g. `ruff format hephaestus/ scripts/ tests/`) rather than only the staged files passed by pre-commit.

Use this specific skill when **main already has format drift** and a whole-dir hook is therefore blocking unrelated commits. This is a DIFFERENT root cause from `ci-ruff-format-collapses-handwrapped-comprehensions` (where YOUR OWN clause-deletion edit collapses a comprehension you just touched) — see also that skill and `pre-commit-hooks-and-linting-config`. If the reformatted files are the ones you edited, you are in the wrong skill; the signature here is that the reformatted files are unrelated to your change and already drifted on main.

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the diagnosis cheaply — does main itself carry drift?
#    (use the repo's pinned ruff so the version matches CI)
/path/to/.pixi/envs/default/bin/ruff format --check hephaestus/ scripts/ tests/
# -> lists drifted files. If they are UNRELATED to your change AND on main,
#    a separate format-fix PR is the clean unblock.

# 2. Create the format-only chore branch off main and fix the WHOLE tree:
git checkout -b chore/lint-format-drift origin/main
ruff format hephaestus/ scripts/ tests/
ruff check --fix hephaestus/ scripts/ tests/

# 3. Verify behavior-preserving (run the affected modules' tests):
pixi run pytest tests/unit/automation -q   # 199 passed, unchanged

# 4. Commit EXACTLY the drift-fix diff (no logic change), signed:
git add -A && git commit -S -m "chore(lint): clear ruff-format drift on main"
pre-commit run --all-files   # now passes clean

# 5. Stack feature branches on the chore branch so they commit cleanly:
git checkout -b 1234-my-feature chore/lint-format-drift
# ...work + commit; once the chore PR merges, GitHub auto-retargets stacked PRs to main.
```

### Detailed Steps

1. **Recognize the signature.** You commit clean, unrelated files and the hook reformats a *different* file set, then aborts. This is not your edit's fault — the drift is in main's committed tree.

2. **Confirm the diagnosis cheaply.** Run `ruff format --check hephaestus/ scripts/ tests/` (with the repo's pinned ruff) against the committed `origin/main` content. If it lists files unrelated to your change, main itself carries drift. This happens when those files were committed before a ruff version/range resolved differently, or merged via a PR whose own gate passed under a slightly different ruff.

3. **Land a SEPARATE format-only PR first.** Branch off main, run `ruff format` + `ruff check --fix` over the whole tree, and commit exactly the drift-fix diff — no logic change. Verify behavior-preserving by running the affected modules' tests (here: 199 automation tests passed unchanged). This is the `chore(lint)` PR (#1325 in ProjectHephaestus).

4. **Stack your feature branches on the chore branch.** Base each feature branch on the chore branch so its commits land cleanly (the hook finds nothing to reformat). Once the chore PR merges to main, GitHub auto-retargets the stacked PRs to main.

5. **Never bypass.** Do not `--no-verify`, do not scope the hook to staged-only as a workaround, and do not silently bundle the unrelated reformats into your feature commit — that pollutes the PR. Fix the drift on main in its own PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Revert the unrelated reformats each commit attempt | `git checkout --` / `git stash` the files the hook reformatted, then re-run `git commit -S` | The reformats reappear on the next commit attempt because the drift lives in main's committed tree, not in your working changes — it is whack-a-mole | Stop reverting; land a separate format-fix PR that fixes the drift on main once |
| Scope the hook to staged-only / bypass it | Tried to limit the hook to staged files, or considered `--no-verify` to skip the reformat | Bypassing hooks is banned in this org, and it does not address the root cause — main is still drifted, so the next contributor hits the same wall | Fix the drift on main, don't hide it; never use `--no-verify` or any hook bypass |
| Bundle the unrelated reformats into the feature commit | Let the hook reformat the drifted files and committed them alongside the feature change | Pollutes the PR with unrelated whole-tree formatting noise, obscuring the actual feature diff in review | Keep format-only changes in their own `chore(lint)` PR; stack the feature on it |

## Results & Parameters

**Context:** ProjectHephaestus. The pre-commit hooks run `ruff format hephaestus/ scripts/ tests/` and `ruff check --fix hephaestus/ scripts/ tests/` over WHOLE DIRECTORIES, not just staged files. When `origin/main` itself carries ruff-format drift, every new commit — even one touching completely unrelated files — triggers the hook to reformat the drifted files, reports "files were modified by this hook", and aborts.

**Diagnostic signature:**

- Stage only your own clean files, run `git commit -S` / `pre-commit run` → the hook reformats a *different* set of files you never touched, then aborts.
- `ruff format --check hephaestus/ scripts/ tests/` against committed `origin/main` reports `Would reformat: <files>` for files unrelated to your change.
- Reverting the reformats (`git checkout --` / `git stash`) makes them reappear next commit, because the drift is in main's committed tree.

**The fix (verified this session):**

```bash
# Confirm the drift on main (repo's pinned ruff so the version matches CI):
/path/to/.pixi/envs/default/bin/ruff format --check hephaestus/ scripts/ tests/

# Land a separate format-only chore(lint) PR FIRST:
git checkout -b chore/lint-format-drift origin/main
ruff format hephaestus/ scripts/ tests/
ruff check --fix hephaestus/ scripts/ tests/
pixi run pytest tests/unit/automation -q   # 199 passed, behavior-preserving
git add -A && git commit -S -m "chore(lint): clear ruff-format drift on main"

# Then stack feature branches on the chore branch.
```

**Outcome:** The format-only PR (#1325) committed exactly the drift-fix diff with zero logic change (199 automation tests passed unchanged). It unblocked a stack of 6 fix PRs — each feature branch was based on the chore branch and committed cleanly. Once the chore PR merges to main, GitHub auto-retargets the stacked PRs to main.

**Distinction from related skills:** This skill is specifically *"main already has drift → whole-dir hook reformats unrelated files → blocks unrelated commits → fix via a separate format-only PR + stack"*. It is NOT `ci-ruff-format-collapses-handwrapped-comprehensions` (clause-deletion collapse of a comprehension YOU just edited — a different root cause). See also `pre-commit-hooks-and-linting-config` for hook configuration background.

**Verification:** verified-local — `ruff format` / `ruff check --fix` were run locally and `pre-commit run` passed clean on the chore branch. The format-fix PR #1325 was created and the 6-PR stack built on it; CI confirmation of the merge train was pending at capture time.
