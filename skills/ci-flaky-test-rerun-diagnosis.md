---
name: ci-flaky-test-rerun-diagnosis
description: "Diagnose CI failures across batch PRs, distinguish real failures from flaky Mojo JIT crashes and transient infrastructure issues. Use when: (1) multiple PRs show BLOCKED status with failing checks, (2) need to determine if CI failures are caused by PR changes or pre-existing."
category: ci-cd
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - ci-failure
  - flaky-tests
  - mojo-jit
  - batch-pr
  - diagnosis
---

# CI Flaky Test Rerun & Diagnosis

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | After creating 14 PRs in batch waves, diagnose why all showed BLOCKED status and fix real failures while re-running flaky ones |
| **Outcome** | Identified 1 real failure (pip dependency conflict), rest were flaky Mojo JIT crashes and transient GitHub infrastructure issues. Fixed the real failure, re-ran flaky tests. |

## When to Use

- Multiple batch PRs all show BLOCKED merge status
- CI failures appear on PRs that only change config/docs (no Mojo code)
- Mojo tests crash with "execution crashed" or "libKGENCompilerRTShared.so" errors
- GitHub Actions fail with HTTP 429 (rate limiting) or HTTP 500 (CDN outage)
- Need to distinguish real CI failures from noise across many PRs

## Verified Workflow

### Quick Reference

```bash
# Step 1: Get CI status for all PRs at once
for pr in 5082 5083 5084; do
  echo "=== PR #$pr ==="
  gh pr checks $pr 2>&1 | grep -E "fail"
done

# Step 2: Check if a "clean" PR exists (no code changes) as baseline
gh pr checks <CLEAN_PR_NUMBER> 2>&1 | grep -E "pass|fail"

# Step 3: Get failure logs for a specific run
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "error|Error|FAILED" | head -20

# Step 4: Check files changed per PR (config-only PRs shouldn't cause Mojo failures)
gh pr diff <PR_NUMBER> --name-only

# Step 5: Re-run flaky failures
gh run rerun <RUN_ID> --failed

# Step 6: Fix real failures with dedicated agent
# (launch agent targeting the specific worktree)
```

### Detailed Steps

1. **Bulk status check**: Run `gh pr checks` across all PRs to get failure counts
2. **Identify baseline**: Find a PR that passes all checks (docs-only PRs are good baselines)
3. **Categorize failures** by checking what files each PR changes:
   - Config/docs PRs with Mojo test failures = flaky (JIT crashes)
   - PRs with pip/dependency errors = real failures from the PR's changes
   - HTTP 429/500 errors = transient GitHub infrastructure
4. **Get specific error messages**: Use `gh run view --log-failed` to extract actual errors
5. **Fix real failures**: Launch dedicated fix agent for the specific worktree
6. **Re-run flaky tests**: Use `gh run rerun <ID> --failed` for intermittent crashes
7. **Monitor re-runs**: Check status again after re-runs complete

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed all failures were transient | Initially classified all 3 failing PRs as transient without checking logs | PR #5082 had a real pip dependency conflict (pytest-benchmark needs pytest>=8.1 but we downgraded to 7.4.4) | Always check the actual error logs, not just the failure count. Config PRs can cause real failures in dependency resolution. |
| Tried re-running still-running jobs | Used `gh run rerun` on a run that was still in progress | Got "cannot be rerun; This workflow is already running" | Check run conclusion before attempting re-run: only re-run when conclusion is "failure", not when empty (in-progress). |
| Bulk re-run without checking status | Tried re-running all failed runs at once | Some runs had already been re-run or were still in progress | Always check individual run status with `gh run view <ID> --json conclusion` before re-running. |

## Results & Parameters

### Failure Classification Matrix

```yaml
failure_types:
  real_failure:
    example: "pip ResolutionImpossible - pytest-benchmark 5.2.3 requires pytest>=8.1"
    diagnosis: "Check error message, verify files changed could cause this"
    fix: "Launch dedicated agent to fix the specific issue"

  flaky_mojo_jit:
    example: "mojo: error: execution crashed (Core Utilities, Tensor, Shared Infra)"
    diagnosis: "Same tests pass on other PRs with identical main branch"
    fix: "gh run rerun <RUN_ID> --failed"

  transient_infrastructure:
    example: "HTTP 429 Too Many Requests (CodeQL), HTTP 500 (pixi CDN)"
    diagnosis: "External service error, not related to code"
    fix: "gh run rerun <RUN_ID> --failed"

  test_report_cascade:
    example: "Test Report job fails because upstream test job failed"
    diagnosis: "Dependent job, will pass when upstream re-run succeeds"
    fix: "Fix/re-run the upstream job, report job auto-resolves"
```

### Diagnostic Commands

```bash
# Check merge state of all PRs
gh pr list --state open --json number,mergeStateStatus

# Get failed check names for a PR
gh pr checks <PR> | grep fail | awk '{print $1}'

# Get actual error from a failed job
JOB_ID=$(gh api repos/OWNER/REPO/actions/runs/<RUN>/jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | .id')
gh api repos/OWNER/REPO/actions/jobs/$JOB_ID/logs | grep -B5 "error\|Error"

# Re-run only concluded failures (skip in-progress)
CONCLUSION=$(gh run view <RUN> --json conclusion --jq '.conclusion')
if [ "$CONCLUSION" = "failure" ]; then
  gh run rerun <RUN> --failed
fi
```

### Key Insight: Config PRs and Mojo Test Failures

```yaml
# PRs that ONLY change these files should NEVER cause Mojo test failures:
safe_file_types:
  - "*.md"           # Documentation
  - ".gitignore"     # Git config
  - "justfile"       # Build recipes
  - "*.yml"          # CI workflows (unless changing test commands)
  - "*.yaml"         # Config files

# If these PRs show Mojo failures, they are ALWAYS flaky JIT crashes
# Exception: requirements.txt/pixi.toml can cause pip install failures
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Diagnosed CI across 14 batch PRs after wave-based triage | 1 real fix, 6 flaky re-runs, 7 clean passes |
