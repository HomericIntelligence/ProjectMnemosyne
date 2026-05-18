---
name: committed-pixi-venv-poisons-ruff-and-pixi-install
description: "Diagnose simultaneous ruff F403 (on stdlib paths) and pixi install --locked failures caused by an accidentally-committed `.pixi/envs/` directory. Use when: (1) ruff reports F403 / undefined-import errors at paths like `.pixi/envs/default/lib/python*/ast.py`, `_ast`, `__future__`, or other Python stdlib files, (2) `pixi install --locked` fails with `Querying Python at .../.pixi/envs/default/bin/python* failed with exit status 1` while the env directory still exists on disk, (3) both ruff and pixi/poetry/uv errors appear in the same CI run with no obvious connection — symptoms point at lock-file drift but the real bug is a tracked venv, (4) you find yourself regenerating pixi.lock repeatedly with no effect, (5) `git ls-files <pkg>/.pixi/` or `git ls-files <pkg>/.venv/` returns ANY paths, (6) a recent commit added thousands of files under `**/.pixi/envs/` or `**/.venv/`."
category: debugging
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pixi
  - venv
  - ruff
  - f403
  - git-rm-cached
  - ci-cd
  - gitignore
  - stdlib-scan
---

# Committed Pixi Venv Poisons Ruff and Pixi Install

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | Recognize and recover from an accidentally-committed pixi (or generic) virtualenv directory that simultaneously breaks ruff and `pixi install --locked` with misleading symptoms |
| **Outcome** | Verified fix: `git rm -r --cached` the venv path, add to `.gitignore`, re-push. Ruff stops scanning stdlib; pixi reclaims ownership of the env. |
| **Verification** | verified-ci (ProjectAgamemnon PR #400 commit `29ee393`, 2026-05-18 — ruff F403 and `pixi install --locked` both cleared on next CI run) |

## When to Use

Trigger this skill IMMEDIATELY (before any lock-file rabbit holes) when you see ANY of:

- Ruff errors at paths inside `**/.pixi/envs/**` or `**/.venv/**` (e.g., `.pixi/envs/default/lib/python3.14/ast.py`)
- Ruff F403 (`from X import *`) errors that reference Python stdlib modules: `_ast`, `__future__`, `builtins`, `typing`, `collections.abc`, `_collections_abc`, `os.path`, `posixpath`
- `pixi install --locked` failing with `Querying Python at .../.pixi/envs/.../bin/python* failed with exit status 1`
- A single PR/commit shows thousands of added files (`git show --stat | wc -l` > 1000)
- Both ruff AND pixi/poetry/uv fail in the same CI run with no shared dependency
- You've already tried regenerating `pixi.lock` and the lock-file errors keep coming back
- A previous agent in the session committed something and you don't remember reviewing the file list

If even one of these triggers fires, run the 2-line diagnostic in Quick Reference BEFORE doing anything else.

## Verified Workflow

### Quick Reference

```bash
# 1. DIAGNOSE: does the venv live in git? (one of these returning lines = bug found)
git ls-files '**/.pixi/' | head -5
git ls-files '**/.venv/' | head -5
# Adjust the glob for your repo, e.g.:
git ls-files clients/python/.pixi/ | head -5

# 2. FIX: untrack the directory (keeps files on disk so dev environment is preserved)
git rm -r --cached clients/python/.pixi    # adjust path to match your repo

# 3. PREVENT: ensure gitignore covers it
grep -qxF '.pixi/' .gitignore || echo '.pixi/' >> .gitignore
grep -qxF '.venv/' .gitignore || echo '.venv/' >> .gitignore
git add .gitignore

# 4. COMMIT: expect thousands of deletions — this is correct
git commit -S -m "fix(ci): untrack accidentally-committed .pixi/envs/ virtualenv"

# 5. PUSH and verify CI: ruff stops scanning stdlib, pixi install --locked succeeds
git push --force-with-lease
```

### Detailed Steps

1. **Halt the lock-file rabbit hole.** If you've already tried regenerating `pixi.lock`, restoring it from `origin/main`, bumping pixi versions, or `ruff check --fix`, STOP. None of those address a tracked venv.

2. **Run the diagnostic.** From the repo root:

   ```bash
   git ls-files | grep -E '(^|/)\.pixi/envs/' | head -10
   git ls-files | grep -E '(^|/)\.venv/' | head -10
   ```

   ANY output means the venv is tracked. The number of tracked files will typically be in the thousands (a Python 3.14 stdlib alone is ~7,000+ files).

3. **Confirm scale of the bug.** Count the tracked entries — this informs the commit message and reviewers:

   ```bash
   git ls-files | grep -cE '(^|/)\.pixi/envs/'
   ```

4. **Untrack with `git rm -r --cached`** (NOT plain `git rm` — that would delete the files on disk and break your local dev env):

   ```bash
   git rm -r --cached clients/python/.pixi    # adjust the path
   ```

5. **Patch `.gitignore`.** Add both `.pixi/` and `.venv/` — agents often hit the same bug with whichever tool is in vogue:

   ```bash
   {
     grep -qxF '.pixi/' .gitignore || echo '.pixi/'
     grep -qxF '.venv/' .gitignore || echo '.venv/'
   } >> .gitignore
   ```

   If there's a nested gitignore (e.g., `clients/python/.gitignore`), patch the most-specific one.

6. **Commit with a sign-off / GPG signature if your repo requires it.** Expect an enormous diff in the commit (thousands of deletions) — this is the expected shape:

   ```bash
   git commit -S -m "fix(ci): untrack accidentally-committed clients/python/.pixi/envs/"
   ```

7. **Push and let CI run.** `--force-with-lease` is appropriate if you're amending a fix branch:

   ```bash
   git push --force-with-lease
   ```

8. **Verify in CI.** Both symptoms must clear in the same run:
   - Ruff: no more F403 errors on stdlib paths
   - Pixi: `pixi install --locked` completes successfully (it can now own the env directory)

9. **Cross-reference.** If you were following [`pixi-lock-rebase-regenerate`](./pixi-lock-rebase-regenerate.md) and the diff after regeneration is empty or trivial — that's another signal you're in the wrong skill. Run this skill's diagnostic first.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Regenerated `pixi.lock` with pixi v0.39.5 (matched CI version) | The env directory was still tracked by git; pixi couldn't take ownership of `.pixi/envs/default/` because git "owned" every file in it | Lock-file regeneration cannot fix a tracked env directory. Pixi needs write access to the env; git tracking prevents pixi from rebuilding it cleanly. |
| 2 | Restored `pixi.lock` + `pixi.toml` verbatim from `origin/main` | Same root cause as above — env directory remained tracked | Restoring lock files only matters when lock drift is the actual bug. It isn't here. |
| 3 | Ran `ruff check --fix` | Ruff kept discovering "new" F403 violations in committed stdlib files (`_ast.py`, `__future__.py`, etc.) — there are thousands, and you can't fix Python's stdlib | If ruff is reporting errors on paths you don't recognize as your source code, look at the paths themselves before changing config or running --fix |
| 4 | Dispatched 3+ Haiku agents in a row to "fix the lock file" | Each agent inherited the wrong mental model from the previous session's symptoms; none ran the venv-tracking diagnostic | When subagent dispatches stack up on the same "obvious" bug class without progress, escalate to a diagnostic checklist instead of more agents. The first question to ask: "what does `git ls-files | wc -l` look like compared to last week?" |
| 5 | Configured ruff `exclude` to skip `.pixi/` | Would have masked the symptom but left pixi install broken; also doesn't compose with `pre-commit run --all-files` which still walks the tree | Suppressing symptoms while the root cause persists is anti-debugging. The tracked venv must be untracked even if ruff is silenced. |

## Results & Parameters

### Diagnostic snippet (copy-paste)

```bash
# Run this FIRST when you see the symptoms in "When to Use".
# Zero output = venv is not tracked (look elsewhere).
# ANY output = venv IS tracked and that is the bug.
for path in .pixi .venv venv env clients/python/.pixi clients/python/.venv; do
  count=$(git ls-files "$path/" 2>/dev/null | wc -l)
  if [ "$count" -gt 0 ]; then
    echo "TRACKED: $path ($count files)"
    git ls-files "$path/" | head -3
  fi
done
```

### Expected fix-commit shape

| Metric | Value |
|--------|-------|
| Files changed | thousands (≈ size of Python stdlib + site-packages) — observed 7,785 in ProjectAgamemnon PR #400 |
| Lines added | ~5–20 (just `.gitignore`) |
| Lines deleted | hundreds of thousands |
| Commit message | `fix(ci): untrack accidentally-committed .pixi/envs/ virtualenv` |
| Verification | next CI run: ruff green, `pixi install --locked` green |

### Prevention recommendations

1. **Project-template `.gitignore`** must include at minimum:

   ```gitignore
   .pixi/
   .venv/
   venv/
   __pycache__/
   *.egg-info/
   ```

2. **Optional pre-commit guard** — reject commits that add more than 100 files under `**/.pixi/` or `**/.venv/`:

   ```yaml
   # .pre-commit-config.yaml
   - repo: local
     hooks:
       - id: block-committed-venvs
         name: Block committed virtualenvs (.pixi, .venv)
         entry: bash -c 'paths=$(git diff --cached --name-only --diff-filter=A | grep -E "(^|/)(\.pixi|\.venv)/" | head -101); count=$(echo "$paths" | grep -c .); if [ "$count" -gt 100 ]; then echo "ERROR: $count+ files staged under .pixi/ or .venv/. Did you mean to commit a virtualenv?"; echo "$paths"; exit 1; fi'
         language: system
         pass_filenames: false
   ```

3. **Reviewer heuristic** — when a PR's "Files changed" count exceeds ~500, scan the file list for `.pixi/envs/` or `.venv/` paths before approving.

### Related skills

- [`pixi-lock-rebase-regenerate`](./pixi-lock-rebase-regenerate.md) — handles GENUINE pixi.lock drift; run this skill FIRST to rule out the tracked-venv case before applying lock-file remedies
- [`docker-pixi-isolation`](./docker-pixi-isolation.md) — analogous category of bug where pixi's env directory is contaminated, but the cause is bind-mounting instead of git tracking
- [`tooling-pixi-container-env-isolation`](./tooling-pixi-container-env-isolation.md) — container-side pixi env ownership issues

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | PR #400 commit `29ee393` on 2026-05-18; previous CI runs burned 5+ iterations chasing pixi.lock regeneration and ruff config tweaks before discovering 7,785 tracked files under `clients/python/.pixi/envs/default/` | Fix landed on next CI run; both ruff F403 and `pixi install --locked` cleared simultaneously |
