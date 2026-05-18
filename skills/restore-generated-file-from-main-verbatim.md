---
name: restore-generated-file-from-main-verbatim
description: "Restore a drifted generated file (pixi.lock, Cargo.lock, poetry.lock, package-lock.json, lock-format-shifted YAML, vendor-imports JSON, etc.) on a feature branch by copying main's exact bytes when the source file (pixi.toml, Cargo.toml, pyproject.toml) is identical to main and main is GREEN. Use when: (1) `pixi install --locked` (or equivalent) fails in CI and your branch's pyproject.toml/pixi.toml/Cargo.toml is unchanged vs main, (2) 2+ local regeneration attempts produced different lock content that CI still rejects (tool-version skew between developer and CI runner), (3) you've already tried installing CI's pinned tool version locally and the regenerated lock STILL diverges, (4) origin/main has a recent GREEN CI run on the same source-file SHA, (5) you don't need any branch-specific generation context in the lock (no new deps on this branch), (6) you're about to dispatch a 4th 'regenerate locally' agent — STOP and copy from main instead, (7) lockfile format has shifted across pixi/cargo/poetry binary versions and you can't pin to CI's version, (8) you cut a release tag and the lockfile mismatch is the only blocker between you and merge."
category: ci-cd
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [pixi-lock, cargo-lock, poetry-lock, package-lock, lockfile, generated-file, verbatim-copy, git-checkout-from-main, ci-cd, drift-recovery, tool-version-skew]
---

# Restore Generated File From Main Verbatim

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | When a feature branch's generated/lock file has drifted in confusing ways and the matching SOURCE file is identical to main, restore the generated file to main's exact bytes — bypassing the "regenerate locally and hope CI agrees" rabbit hole that consumes multiple failed agent dispatches |
| **Outcome** | One commit, one push, CI green. Avoids the entire tool-version-skew / format-shift / partial-regenerate trap |
| **Verification** | verified-ci (ProjectAgamemnon PR #400, 2026-05-18) |

## When to Use

- A generated file on your branch (`pixi.lock`, `Cargo.lock`, `poetry.lock`, `package-lock.json`, lock-format-shifted YAML, vendor-imports JSON, etc.) is rejected by CI
- The matching source file (`pixi.toml`, `Cargo.toml`, `pyproject.toml`, `package.json`) is **identical** between your branch and `origin/main`
- `origin/main` had a recent GREEN CI run on this exact source-file SHA
- You've already attempted local regeneration 1+ times and CI still rejects the result
- You have no branch-specific reason for the generated file to differ from main (no new deps, no version bumps)
- You're considering dispatching yet another agent to "regenerate the lock properly" — STOP, copy from main first
- Tool-version skew suspected (developer pixi/cargo/poetry binary differs from CI's pinned version) and you can't easily pin locally
- The lockfile blocks a release tag and time-to-merge matters more than carrying your branch's specific lock generation

## When This Approach is WRONG

Do NOT use this skill if any of the following are true:

- The generated file SHOULD differ from main because your PR adds/removes/changes dependencies — you MUST regenerate properly
- Your branch has source-file changes that haven't yet propagated to the lock — regenerate the lock IN YOUR BRANCH
- The generated file is partially hand-maintained (config-as-data, not pure tool output)
- Main itself is RED — copying its lock just propagates the bug (see `ci-cd-pixi-lock-stale-multi-pr-triage` for that case)

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm source files match main (must be empty output)
git diff origin/main..HEAD -- clients/python/pixi.toml

# 2. Confirm main is GREEN on the same source-file SHA
gh run list --workflow=python-client.yml --branch=main --limit=3 \
  --json conclusion,headSha,displayTitle

# 3. Restore generated file verbatim from main
git checkout origin/main -- clients/python/pixi.lock

# 4. Verify zero diff vs main on the generated file
git diff origin/main -- clients/python/pixi.lock | wc -l   # must be 0

# 5. Run pre-commit on JUST the restored file, then commit (signed)
pre-commit run --files clients/python/pixi.lock
git commit -S -m "fix(ci): align clients/python/pixi.lock with main verbatim"
git push --force-with-lease   # if branch was previously rebased

# 6. DO NOT run `pixi install` (or `cargo update`, etc.) locally afterwards
#    — that re-writes the lock and undoes the alignment.
```

### Detailed Steps

1. **Confirm main has the same source file you do.** If `pyproject.toml`/`pixi.toml`/`Cargo.toml` differs, this skill DOES NOT apply — you need to regenerate properly:

   ```bash
   git fetch origin
   git diff origin/main..HEAD -- clients/python/pixi.toml
   # Empty output = source files match, generated file is the only drift
   ```

2. **Confirm main is GREEN with this source file.** Check the latest CI run on main:

   ```bash
   gh run list --workflow=python-client.yml --branch=main --limit=3 \
     --json conclusion,headSha,displayTitle
   # A recent successful run on a SHA that has the same pyproject/pixi.toml = safe to copy lock
   ```

3. **Restore the generated file from main verbatim:**

   ```bash
   git checkout origin/main -- clients/python/pixi.lock
   # Multiple files at once if needed:
   git checkout origin/main -- clients/python/pixi.lock clients/python/tests/test_bump_version.py
   ```

4. **Verify zero diff vs main on the restored file:**

   ```bash
   git diff origin/main -- clients/python/pixi.lock | wc -l   # must be 0
   ```

5. **Sign-commit and push** (use `--force-with-lease` only if the branch was rebased):

   ```bash
   pre-commit run --files clients/python/pixi.lock
   git commit -S -m "fix(ci): align clients/python/pixi.lock with main verbatim"
   git push --force-with-lease
   ```

6. **CRITICAL — do NOT run `pixi install` / `cargo update` / `poetry lock` / `npm install` locally afterward.** Local tool invocations re-write the lock based on your local binary version, undoing the alignment. Just commit the verbatim file and let CI's pinned tool consume it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Install pixi v0.39.5 locally (matching CI's pinned `prefix-dev/setup-pixi` version) and regenerate from current branch | Produced ANOTHER format that CI couldn't parse: `lock-file not up-to-date with the project`. Likely subtle environment differences (OS, glibc, conda channel cache) between developer machine and CI runner | Pinning developer pixi to CI's version is necessary but not sufficient — environment differences can still produce a divergent lock |
| 2 | Regenerate with pixi v0.67.2 (developer's installed version) and accept the format drift | Hit the v0.39.5 vs v0.67.2 binary-skew rabbit hole — newer pixi writes a lock format the older CI pixi rejects | Newer-to-older pixi lockfile compatibility is NOT guaranteed; always use CI's pinned version for regeneration OR copy from main |
| 3 | `git checkout origin/main -- pixi.lock` AND then `pixi install` locally to "sync" my environment | `pixi install` immediately re-wrote the lock based on the local pixi binary, re-introducing the exact drift the checkout fixed | Once you copy verbatim, **do not touch the file with any tool**. Local install is the trap |
| 4 (WORKED) | `git checkout origin/main -- pixi.lock` and DO NOT run `pixi install` afterward | CI's `pixi install --locked` accepted main's exact lock — CI tooling is the only environment that needs to agree with the lock | The shortest path is always: trust main's bytes, commit them, let CI consume them |

## Results & Parameters

### Real Recovery — ProjectAgamemnon PR #400 (2026-05-18)

```bash
# Branch was preparing v0.1.0 release tag. Lockfile mismatch was the only CI blocker.
# 3 prior agent dispatches had tried regeneration approaches and failed.

git diff origin/main..HEAD -- clients/python/pixi.toml   # empty — source files identical
gh run list --workflow=python-client.yml --branch=main --limit=3 --json conclusion
# [{"conclusion":"success",...}]

git checkout origin/main -- clients/python/pixi.lock
git diff origin/main -- clients/python/pixi.lock | wc -l   # 0
pre-commit run --files clients/python/pixi.lock            # passes
git commit -S -m "fix(ci): align clients/python/pixi.lock with main verbatim"
git push --force-with-lease

# CI green on first run. v0.1.0 tag cut shortly after.
```

### Decision flowchart

```
Generated file CI failure on feature branch
  │
  ├─ Source file differs from main?     ──► Regenerate (different skill)
  │
  ├─ Branch adds new deps to source?    ──► Regenerate (different skill)
  │
  ├─ main is RED on same source SHA?    ──► Fix main first (different skill)
  │
  └─ Source matches main, main is GREEN, no new deps
        │
        └─► THIS SKILL: git checkout origin/main -- <generated-file>
                       commit, push, DO NOT run install tool locally
```

### Generated files this skill applies to

- `pixi.lock` (pixi)
- `Cargo.lock` (cargo)
- `poetry.lock` (poetry)
- `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` (Node)
- `go.sum` (Go modules — when source `go.mod` matches main)
- `requirements.txt` if pip-compile generated (when `requirements.in` matches main)
- Vendored generated JSON/YAML where source-of-truth is a manifest in the repo
- Any file whose contents are 100% determined by another file in the repo + a tool version

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | PR #400 (clients/python/pixi.lock, 2026-05-18) — 3 failed regeneration attempts, verbatim copy worked first try; v0.1.0 tag cut shortly after | See `git log --grep="align clients/python/pixi.lock with main verbatim"` in ProjectAgamemnon |
