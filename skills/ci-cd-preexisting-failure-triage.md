---
name: ci-cd-preexisting-failure-triage
description: "Determine whether CI failures on a PR are pre-existing on main vs introduced by the PR. Use when: (1) CI fails but PR changes look unrelated to failures, (2) deciding whether to block merge on CI failures, (3) docs-only or cleanup PRs show red CI, (4) need to verify a PR is safe to merge despite failing checks, (5) a review plan claims failures are pre-existing and needs confirmation."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# CI Pre-Existing Failure Triage

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-28 | Consolidated workflow to distinguish pre-existing CI failures from PR-introduced ones | Operational |

Systematic approach to determining whether CI failures existed before a PR and confirming it is safe to merge despite red CI checks.

## When to Use

- CI fails on a PR but PR changes look unrelated to failures
- PR only changes documentation/config (no code) and CI test failures involve runtime crashes
- CI failure category (link-checking, infrastructure crashes) seems unrelated to PR scope
- Need to decide whether to block merge or proceed
- Suspecting flaky or pre-existing infrastructure failures
- A review plan states both CI failures are pre-existing on `main`
- Before implementing fixes, want to confirm failures actually originate from this PR
- Reviewing a cleanup or deletion PR where no Mojo/logic code was changed
- Closing a review loop to confirm no commits are required

## Verified Workflow

### Quick Reference

```bash
# Step 1: What did the PR change?
git diff main...HEAD --name-only

# Step 2: Check main CI history for same failures
gh run list --branch main --workflow "Comprehensive Tests" --limit 5
gh run list --branch main --workflow "Check Markdown Links" --limit 5

# Step 3: View a specific run to compare failing jobs
gh run view <run-id> --log-failed

# Step 4: Confirm no relevant source files changed
git diff main...HEAD --name-only | grep -E "\.(mojo|py)$"

# Step 5: Check if pre-commit passes
pre-commit run --all-files
```

### Step 1: Identify Changed Files

Understand the PR's scope before investigating failures:

```bash
# All changed files
git diff main...HEAD --name-only

# Or for a different branch comparison
git diff main..<branch> --name-only
```

### Step 2: Classify Changed Files

Can they cause the failing tests?

| File Type | Can Cause |
|-----------|-----------|
| `.claude/agents/*.md`, `.claude/skills/*.md`, `agents/*.md` | Documentation only — cannot cause Mojo runtime crashes |
| `.mojo`, `.🔥`, `shared/`, `tests/` | Can cause test failures |
| `docs/adr/README.md`, `*.md` only | Documentation only — can affect pre-commit and link-check only |
| `.github/workflows/` | Can affect CI infrastructure |

### Step 3: Check Main Branch CI History

For each failing workflow, check recent runs on main:

```bash
# Check recent runs of the failing workflow on main
gh run list --branch main --workflow "<Workflow Name>" --limit 5

# View a specific main run's failures
gh run view <run-id> --log-failed 2>&1 | head -100

# Confirm link check failure is pre-existing
gh run list --branch main --limit 5 --json name,conclusion
```

If all recent runs on `main` show `failure`, the failure is pre-existing.

### Step 4: Compare Failure Signatures

Do the failing test names match between PR and main?

- Same test groups failing (e.g., `Core DTypes`, `Data Loaders`, `Data Samplers`) → **pre-existing**
- New test groups failing that correspond to changed files → **PR-caused**

```bash
# Confirm no Mojo code was changed (for non-code PRs)
git diff main...HEAD -- '*.mojo'
# Empty output confirms no logic changes

# Check specifically for source files relevant to the failure
git diff main..<branch> --name-only | grep "\.mojo$"
git diff main..<branch> --name-only | grep "\.py$"
```

### Step 5: Verify New Links (for link-check failures)

If the PR adds new links, verify they use relative paths and all target files exist:

```bash
# Check target files exist
ls path/to/linked/file1.md path/to/linked/file2.md

# Grep new links added in the PR
git diff main..<branch> -- "*.md" | grep "^+" | grep -o '([^)]*\.md)'
```

**Key distinction**: Root-relative paths (`/path/...`) fail lychee; relative paths (`../path/...`) are fine.

### Step 6: Verify CI Run IDs (for review plan confirmation)

When confirming specific run IDs cited in a review plan:

```bash
gh run view <run-id> --json jobs | python3 -c \
  "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'FailingJob' in j['name']]"
```

### Step 7: Verify Branch State

```bash
# Check branch is clean
git status

# Confirm PR scope
git log --oneline main..HEAD

# Confirm no broken references after deletions/renames
grep -rn "old-filename.md" . --include="*.md"
# Expected: no output
```

### Step 8: Decision

| Changed files | Failing CI | Action |
|---------------|-----------|--------|
| Only `.claude/`, `agents/`, docs | Mojo runtime crashes | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `link-check` on untouched files | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `pre-commit` / `test-agents` | PR-caused — fix required |
| Any `.mojo` / `shared/` / `tests/` | Any test failure | Investigate — may be PR-caused |

**Pre-existing only** → PR is ready to merge as-is.

**PR introduced failures** → fix before merging.

### Step 9: Document Findings

Post to PR or issue when confirmed pre-existing:

```bash
gh issue comment <number> --body "All CI failures are pre-existing on main (confirmed via gh run list). PR only modifies documentation files. Safe to merge."
```

### Step 10: For Docs-Only PRs — Run Pre-commit to Confirm

Even docs-only PRs can fail pre-commit if they introduce formatting issues:

```bash
pixi run pre-commit run --all-files 2>&1 | tail -20
```

Expected output: all hooks show `Passed`. The `mojo format` hook may emit GLIBC errors (environment incompatibility on local host) but still reports `Passed` — this is a known pre-existing environment issue, not a failure of the PR.

### Important Notes

- **Do NOT commit `.claude-review-fix-*.md` files** — these are temporary task instruction artifacts, not implementation files. Leave them as untracked.
- **Untracked files in `git status` are normal** after a no-op review fix.
- **GLIBC errors in pre-commit are environment noise** — look at per-hook status lines, not stderr noise.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming failures require fixes | Saw red CI and started planning fixes | Both failures were pre-existing on main | Always check main's CI history before concluding a PR introduced failures |
| Root-relative link analysis | Worried new links in CLAUDE.md would trigger lychee errors | New links used relative paths, not root-relative; all targets existed | Distinguish root-relative (`/path`) from relative (`path`) — lychee fails on root-relative, not relative |
| Blaming doc PR for test crashes | `execution crashed` failures looked alarming | These were infrastructure-level crashes on main unrelated to docs | `execution crashed` (runtime) vs test assertion failures are different root causes |
| Fixing Mojo runtime crashes in PR | Attempted to diagnose `mojo: error: execution crashed` in test files | The PR changed zero `.mojo` files — Mojo crashes cannot be caused by markdown changes | Always check `git diff main...HEAD --name-only` before attempting any CI fix |
| Treating link-check as PR-caused | Assumed `link-check` failure was introduced by new markdown files | The failing links were in `docs/adr/README.md` and `notebooks/README.md`, neither touched by PR | Cross-reference failing file paths against PR diff before investigating |
| Running tests to verify Mojo failures | Considered running `pytest tests/` to confirm | The test failures are Mojo runtime crashes, not Python tests; running locally without CI environment won't help | Match the test runner to the failing workflow type |
| Immediately fixing CI | Jumping to fix CI failures without first verifying their origin | Would have introduced unnecessary changes to a PR that was already correct | Always verify failure origin before implementing fixes |
| Skipping verification | Trusting the review plan without independent confirmation | Could miss genuine issues introduced by the PR | Run the grep/ls checks even if the plan says no fixes needed |
| Assuming CI failures require a fix on cleanup PR | Automatically trying to fix red CI checks | The failures were unrelated to the PR — pre-existing on main from infrastructure issues | Always verify CI failure history on `main` before attempting any fix |
| Committing review instructions file | Including `.claude-review-fix-*.md` in the commit | These are temporary instruction files, not implementation files | Never commit review instruction/orchestration files |

## Results & Parameters

### Success Criteria for "Safe to Merge"

- [ ] `git diff main...HEAD --name-only` shows only documentation/config files
- [ ] Failing test groups match failures visible on recent `main` CI runs
- [ ] `pre-commit` CI check passes (the check that validates changed files)
- [ ] `test-agents` CI check passes (if agent configs were modified)

### Known Pre-Existing Failure Signatures (ProjectOdyssey)

| Failure | Signature | Pre-existing on main? |
|---------|-----------|----------------------|
| Check Markdown Links | lychee cannot resolve root-relative paths (`/.claude/shared/`) | Yes — 5+ consecutive failures on main |
| Comprehensive Tests | `mojo: error: execution crashed` (runtime, not assertion) | Yes — same crashes in main runs |
| `link-check` | Root-relative links (`/.claude/...`) fail on all PRs — lychee needs `--root-dir` | Pre-existing |
| `Core ExTensor` | Mojo runtime crash; passes on other PRs | Intermittent flaky |
| `Core Activations` | `mojo: error: execution crashed` pre-dates most PRs | Pre-existing infrastructure |

### Decision Rule

**If a PR only modifies markdown files and CI failures are in unrelated domains (Mojo execution, link resolution with root-relative paths), treat them as pre-existing until proven otherwise.**

### Key Commands Reference

```bash
# Verify no stale references remain
grep -rn "old-filename.md" . --include="*.md"

# Confirm deleted file is gone
ls agents/old-filename.md

# Confirm CI failure is pre-existing
gh run list --branch main --limit 5 --json name,conclusion

# Confirm Mojo crash pre-existing on main
gh run view <MAIN_RUN_ID> --json jobs | python3 -c \
  "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'Activ' in j['name']]"

# Check pre-commit locally
pixi run pre-commit run --all-files 2>&1 | tail -20

# Count lines in large docs (to verify trim targets)
wc -l CLAUDE.md
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3363 / issue #3158 — CLAUDE.md trim | Both failures confirmed pre-existing; PR merged without fixes |
| ProjectOdyssey | PR #3334 / issue #3147 — cleanup PR | Zero fixes needed; `Core Activations` and `link-check` pre-existing |
| ProjectOdyssey | PR #3338 / issue #3150 — ADR index update | Docs-only; `Core Elementwise`, `Core Tensors` pre-existing |
| ProjectOdyssey | Multiple docs/agent config PRs | Mojo runtime crashes on docs-only PRs consistently pre-existing |
