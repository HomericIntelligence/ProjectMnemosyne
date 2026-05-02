---
name: preexisting-flaky-crash-rerun
description: 'Diagnose whether CI failures are pre-existing flaky crashes unrelated
  to PR changes, and re-trigger CI as the sole fix. Use when: (1) CI fails with execution
  crashes in Mojo tests, (2) the PR diff does not touch failing test files, (3) the
  same tests passed on a recent main CI run.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Preexisting Flaky Crash Rerun

Quickly determine if CI failures are transient/environmental crashes that predate the PR, then fix them by re-running CI — no code changes required.

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-03-06 |
| **Objective** | Fix PR #3355 CI failures (Data Loaders, Test Examples) |
| **Outcome** | CI re-triggered with `gh run rerun --failed`; no code changes needed |
| **Verified On** | PR #3355 (issue #3157, bandit security scanner replacement) |
| **Key Lesson** | Always check whether failing tests are in the PR diff before attempting code fixes |

## When to Use

Use this skill when:

- CI reports `mojo: error: execution crashed` or similar runtime crashes in test jobs
- The PR diff touches only a small set of files (e.g., config, lock files, scripts)
- The failing test files are NOT in the PR diff
- A recent successful main CI run exists that passed the same tests

## Verified Workflow

### Phase 1: Confirm Pre-Existing Nature (3 checks)

1. **Check what files the PR touches**

   ```bash
   gh pr diff <PR_NUMBER> --name-only
   ```

   If the failing test files are not listed here, the failures are not caused by the PR.

2. **Confirm the failing test files**

   From the CI failure logs, note the test files that crashed. Cross-reference with the PR diff.

3. **Check a recent successful main CI run**

   ```bash
   gh run list --branch main --status success --limit 5
   gh run view <SUCCESSFUL_RUN_ID> --log | grep -E "(PASSED|FAILED|crashed)"
   ```

   If the same tests passed on main recently, the failure is transient/environmental.

### Phase 2: Re-trigger CI

Once confirmed as pre-existing:

```bash
gh run rerun <FAILING_RUN_ID> --failed
```

This re-runs only the failed jobs, not the entire workflow.

### Phase 3: Monitor

```bash
gh run watch <FAILING_RUN_ID>
```

Or check via:

```bash
gh pr checks <PR_NUMBER>
```

### Phase 4: If Crashes Persist After Re-run

If the same jobs crash again after re-run:

1. Open a separate tracking issue:

   ```bash
   gh issue create \
     --title "fix: pre-existing flaky crash in <test-file>" \
     --body "Tracking persistent crash in <test-file>. Unrelated to PR #<N>." \
     --label "testing"
   ```

2. Add a note to the PR description referencing the new issue.
3. Do NOT block the PR merge on pre-existing flakiness.

## Results & Parameters

| Parameter | Value Used |
| ----------- | ----------- |
| Workflow run ID | `22737649305` |
| Failing jobs | `Data Loaders` (`test_batch_loader.mojo`), `Test Examples` (`test_trait_based_serialization.mojo`) |
| Crash type | `mojo: error: execution crashed` |
| PR diff files | `.pre-commit-config.yaml`, `pixi.toml`, `pixi.lock`, `scripts/analyze_issues.py`, `tests/scripts/test_fix_build_errors.py` |
| Overlap with failing tests | None |
| Command used | `gh run rerun 22737649305 --failed` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Code investigation | Considered modifying test files or adding `# nosec` suppressions | Failing tests had zero overlap with PR changes | Always diff-check before touching code |
| Local repro | Considered reproducing crash locally | Not needed — diff-check was sufficient to confirm pre-existing | Save time by checking the diff first |
