---
name: retrigger-flaky-ci
description: 'Diagnose and re-trigger pre-existing flaky CI failures on PRs without
  code changes. Use when: CI fails on a PR with only cosmetic/doc changes, the failure
  is in test files not touched by the PR, or Mojo runtime crashes (SIGABRT, execution
  crashed) appear in CI logs.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | retrigger-flaky-ci |
| **Category** | ci-cd |
| **Trigger** | Pre-existing flaky CI failure on a PR with unrelated changes |
| **Resolution** | Verify flakiness, then re-trigger failed jobs |
| **Key Tool** | `gh run rerun <run-id> --failed` |

## When to Use

1. CI fails on a PR that only modifies cosmetic files (print strings, READMEs, comments)
2. The failing test files are not in `gh pr diff <pr> --name-only`
3. Mojo runtime crashes appear: `execution crashed`, `SIGABRT`, `libKGENCompilerRTShared.so`
4. The same CI job passes on the latest successful `main` run (confirming flakiness)

## Verified Workflow

1. **Identify the failing run ID** from `gh pr checks <pr-number>`
2. **Confirm the failure is unrelated** — check that failing test files are NOT in the PR diff:
   ```bash
   gh pr diff <pr-number> --name-only
   gh pr checks <pr-number>
   ```
3. **Verify it passes on main** — find a recent successful main CI run and confirm the job passes there
4. **Re-trigger failed jobs only**:
   ```bash
   gh run rerun <run-id> --failed
   ```
5. **Confirm resolution** — watch for the jobs to go green on the next run

## Results & Parameters

```bash
# Step 1: Get PR check status and run ID
gh pr checks 3189 --watch=false

# Step 2: Verify PR diff does NOT contain failing test files
gh pr diff 3189 --name-only
# Expected: only examples/ and README files, no test_backward_*.mojo

# Step 3: Re-trigger only failed jobs (not the whole workflow)
gh run rerun 22749573506 --failed

# Step 4: Monitor re-run
gh run watch 22749573506
```

**Mojo Flaky Test Signature** (pre-existing, not PR-caused):
- Job name: "Core Gradient"
- Files: `test_backward_linear.mojo`, `test_backward_conv_pool.mojo`, `test_backward_losses.mojo`, `test_gradient_checking_basic.mojo`
- Error: `execution crashed` / `SIGABRT in libKGENCompilerRTShared.so`
- Pattern: Intermittent — passes on main's latest successful run

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Making code changes | Considered modifying test files to fix the crash | Not needed — crash is a pre-existing Mojo runtime flake, not introduced by PR | Always verify whether failing tests are in the PR diff before attempting fixes |
| Full workflow rerun | Could have re-run the entire workflow | Wastes CI minutes re-running passing jobs | Use `--failed` flag to re-trigger only the failed jobs |
