---
name: diagnose-pr-ci-failures
description: "Diagnose CI failures on a pull request by classifying them as PR-caused, pre-existing, or flaky, then act accordingly. Use when: CI checks fail after pushing a PR and you need to determine root cause and correct action."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI failures on a PR — unclear if caused by the PR or pre-existing |
| **Approach** | Classify each failure: PR-caused / pre-existing / flaky crash |
| **Key Tool** | `gh run view <run-id> --log-failed` + cross-branch comparison |
| **Resolution** | Fix PR-caused failures; re-run flaky ones; ignore pre-existing on main |

## When to Use

- CI fails after pushing a PR
- Multiple unrelated-looking checks fail simultaneously
- A check that passed on the previous run now fails with identical code
- Mojo runtime crashes (`error: execution crashed`) appear in CI

## Verified Workflow

### Step 1: Get the failing check list

```bash
gh pr checks <pr-number> --repo <owner>/<repo> 2>&1 | grep "fail"
```

### Step 2: Get error details for each failing job

```bash
# Get the run ID from the checks output, then:
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep -E "error:|FAIL|❌" | head -30
```

### Step 3: Classify each failure

| Failure Type | Signal | Action |
|---|---|---|
| **PR-caused** | Error points to a file you changed | Fix the code |
| **Pre-existing** | Same failure appears on main branch history | Ignore (not your fault) |
| **Flaky crash** | `error: execution crashed` or passes on other PRs | Re-run failed jobs |

### Step 4: Verify pre-existing failures

```bash
# Check if the same job was failing on main before your PR
gh run list --repo <owner>/<repo> --workflow "Workflow Name" --branch main --limit 3
gh run view <main-run-id> --repo <owner>/<repo> 2>&1 | grep "JobName"

# Check if the same job passes on other open PRs
gh run list --repo <owner>/<repo> --workflow "Comprehensive Tests" --limit 5
gh run view <other-run-id> --repo <owner>/<repo> 2>&1 | grep "JobName"
```

### Step 5: Re-run flaky failures

```bash
# Re-run only the failed jobs (not the whole workflow)
gh run rerun <run-id> --repo <owner>/<repo> --failed
```

### Step 6: Verify your fix didn't break unrelated tests

The key question: **does the failure exist in commits on main that don't include your changes?**

```bash
# Check if the error message references a file you touched
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep "error:" | grep -v "warning"
```

## Mojo-Specific: Identifying Flaky Runtime Crashes

Mojo runtime crashes (`error: execution crashed`) in CI are often:

- Non-deterministic memory issues in ExTensor or complex operator tests
- Not reproducible locally (environment-specific)
- Not correlated with code changes in your PR

**Diagnosis command:**

```bash
gh run view <run-id> --repo <owner>/<repo> --job <job-id> --log 2>&1 | grep -B2 "execution crashed"
```

If you see `execution crashed` and the test file is unrelated to your changes, it's almost certainly flaky. Re-run with `--failed`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Check if failure is pre-existing using only the PR's CI output | Looked at PR CI output without comparing to main history | Cannot tell if failure pre-exists without checking main branch runs | Always cross-reference against `gh run list --branch main` |
| Assume all CI failures are PR-caused | Treated `Core ExTensor` crash as caused by serialization change | ExTensor crashes are flaky runtime crashes unrelated to the serialization fix | Check which files the failing test covers vs which files you changed |
| Wait for log output before run completes | Called `gh run view --log-failed` while run still in progress | GitHub returns "run is still in progress; logs will be available when it is complete" | Check `gh run view` status first; use `gh run watch` for background waiting |

## Results & Parameters

### Classification Decision Tree

```
CI check fails on your PR
├── Does the error reference a file you changed?
│   ├── YES → PR-caused, fix it
│   └── NO → Continue...
│
├── Does the same job fail on recent main branch runs?
│   ├── YES → Pre-existing, not your fault, ignore
│   └── NO → Continue...
│
└── Does the same job PASS on other open PRs?
    ├── YES → Flaky, re-run with --failed
    └── NO → Possibly a shared regression, investigate further
```

### Common Pre-Existing Failures in ProjectOdyssey

| Check | Status | Notes |
|-------|--------|-------|
| `link-check` | Pre-existing | Root-relative links (`/.claude/...`) fail on all PRs — lychee needs `--root-dir` |
| `Core ExTensor` | Intermittent flaky | Mojo runtime crash; passes on other PRs; re-run resolves it |
| `Core Initializers` | Intermittent flaky | Same pattern as Core ExTensor |

### Re-run Command

```bash
# Re-run only failed jobs (most efficient)
gh run rerun <run-id> --repo HomericIntelligence/ProjectOdyssey --failed

# Monitor until completion
gh run watch <run-id> --repo HomericIntelligence/ProjectOdyssey --exit-status
```
