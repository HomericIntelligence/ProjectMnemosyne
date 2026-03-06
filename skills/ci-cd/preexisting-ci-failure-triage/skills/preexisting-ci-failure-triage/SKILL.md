---
name: preexisting-ci-failure-triage
description: "Triage CI failures to determine if they are pre-existing on main branch vs caused by PR changes. Use when: CI fails on a PR with only doc/config changes, determining whether to block merge, or reviewing Mojo runtime crashes unrelated to changed files."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Name** | preexisting-ci-failure-triage |
| **Category** | ci-cd |
| **Trigger** | CI fails on a PR; need to determine if failures are caused by the PR or pre-existing |
| **Outcome** | Clear determination: block merge or proceed; no wasted fix attempts |

## When to Use

- CI test groups fail with `mojo: error: execution crashed` on a PR that only changed `.claude/`, `agents/`, or other non-code files
- `link-check` or linting CI fails on files the PR did not touch
- A PR review plan needs to confirm whether CI failures block merge
- You want to verify a PR is safe to merge despite red CI

## Verified Workflow

1. **Identify changed files** — what did this PR actually modify?

   ```bash
   git diff main...HEAD --name-only
   ```

2. **Classify changed files** — can they cause the failing tests?

   - `.claude/agents/*.md`, `.claude/skills/*.md`, `agents/*.md` → documentation only, cannot cause Mojo runtime crashes
   - `.mojo`, `.🔥`, `shared/`, `tests/` → can cause test failures

3. **Check main branch CI history** — are the same failures present on main?

   ```bash
   gh run list --branch main --workflow comprehensive-tests.yml --limit 5
   gh run list --branch main --workflow link-check.yml --limit 5
   ```

4. **Compare failure signatures** — do the failing test names match between PR and main?

   - Same test groups failing (e.g., `Core DTypes`, `Data Loaders`, `Data Samplers`) → pre-existing
   - New test groups failing that correspond to changed files → PR-caused

5. **Decision**:

   - All failures are pre-existing AND PR only changes non-code files → **proceed with merge**
   - Any failure corresponds to changed code → **block merge, fix required**

6. **Document findings** — post to PR or issue:

   ```bash
   gh issue comment <number> --body "All CI failures are pre-existing on main (confirmed via gh run list). PR only modifies documentation files. Safe to merge."
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fixing Mojo runtime crashes in PR | Attempted to diagnose `mojo: error: execution crashed` in test files | The PR changed zero `.mojo` files — Mojo crashes cannot be caused by markdown changes | Always check `git diff main...HEAD --name-only` before attempting any CI fix |
| Treating link-check as PR-caused | Assumed `link-check` failure was introduced by new markdown files | The failing links were in `docs/adr/README.md` and `notebooks/README.md`, neither touched by PR | Cross-reference failing file paths against PR diff before investigating |
| Running tests to verify | Considered running `pixi run python -m pytest tests/` to confirm | The test failures are Mojo runtime crashes, not Python tests; running them locally would not help without reproducing the exact CI environment | Match the test runner to the failing workflow type |

## Results & Parameters

### Key Commands

```bash
# Step 1: What did the PR change?
git diff main...HEAD --name-only

# Step 2: Check main CI history for same failures
gh run list --branch main --workflow comprehensive-tests.yml --limit 5
gh run list --branch main --workflow link-check.yml --limit 5

# Step 3: View a specific run to compare failing jobs
gh run view <run-id> --log-failed

# Step 4: Check if pre-commit passes (the one CI check that IS affected by doc changes)
just pre-commit-all
```

### Decision Matrix

| Changed files | Failing CI | Action |
|---------------|-----------|--------|
| Only `.claude/`, `agents/`, docs | Mojo runtime crashes | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `link-check` on untouched files | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `pre-commit` / `test-agents` | PR-caused — fix required |
| Any `.mojo` / `shared/` / `tests/` | Any test failure | Investigate — may be PR-caused |

### Success Criteria for "Safe to Merge"

- [ ] `git diff main...HEAD --name-only` shows only documentation/config files
- [ ] Failing test groups match failures visible on recent `main` CI runs
- [ ] `pre-commit` CI check passes (the check that validates changed files)
- [ ] `test-agents` CI check passes (if agent configs were modified)
