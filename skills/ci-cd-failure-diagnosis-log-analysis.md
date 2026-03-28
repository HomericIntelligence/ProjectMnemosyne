---
name: ci-cd-failure-diagnosis-log-analysis
description: "Diagnose CI failures by reading logs, identifying error patterns, and classifying root causes. Use when: (1) CI pipeline fails and you need to understand why, (2) tests pass locally but fail in CI, (3) multiple unrelated checks fail simultaneously, (4) CI retry logic labels failures as JIT crashes, (5) need to distinguish Mojo JIT crashes from real compile/test errors."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# CI Failure Diagnosis and Log Analysis

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-28 | Consolidated diagnosis and log-analysis knowledge for CI failures | Operational |

Systematic approach to reading CI logs, identifying error patterns, classifying failure types, and diagnosing root causes before attempting fixes.

## When to Use

- CI pipeline fails and you need to understand why
- Analyzing test failure logs from GitHub Actions
- Extracting error messages from build artifacts
- Identifying patterns in recurring failures
- Determining if failure is environmental or code-related
- Tests pass locally but fail in CI (especially when CI uses `--Werror`)
- Multiple unrelated-looking checks fail simultaneously
- A check that passed on the previous run now fails with identical code
- Mojo runtime crashes (`error: execution crashed`) appear in CI
- CI retry logic labels failures as "Mojo JIT crash" — verify before trusting
- CI tests fail and retry logic labels them as "likely Mojo JIT crash" but tests pass locally
- `execution crashed` is assumed but never actually appears in CI logs
- Deprecation warnings exist in the codebase and CI uses `--Werror`

## Verified Workflow

### Quick Reference

```bash
# View PR checks
gh pr checks <pr-number>

# Get failed logs only
gh run view <run-id> --log-failed

# Download CI logs from artifact
gh run download <run-id> -D /tmp/ci-logs

# Extract from workflow run
gh run view <run-id> --log > /tmp/ci-output.log

# Grep for error patterns
grep -i "error\|failed\|panic\|exception" /tmp/ci-output.log

# Get summary of failures
tail -100 /tmp/ci-output.log | grep -A 5 "FAILED\|ERROR"

# View failed job output specifically
gh run view <run-id> --log-failed

# Get error details for a specific job
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep -E "error:|FAIL|❌" | head -30
```

### Phase 1: Collect and Extract Logs

1. **Get PR check status**
   ```bash
   gh pr checks <PR_NUMBER>
   ```
   Identifies which checks are failing and provides direct links to logs.

2. **View detailed logs**
   ```bash
   gh run view --job=<JOB_ID> --log
   ```
   Downloads complete CI logs for analysis.

3. **Extract error messages**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -E "FAILED|ERROR|error" | head -20
   ```
   Quickly surfaces actual failure points.

4. **Search for specific error context**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -B 10 -A 10 "<error_message>"
   ```
   Gets surrounding context for error understanding.

### Phase 2: Classify the Failure Type

**Error category patterns**:

| Category | Look For | Check |
|----------|----------|-------|
| Compilation Errors | `error:`, `undefined`, `type mismatch` | Mojo/Python syntax, imports, type annotations |
| Test Failures | `FAILED`, `AssertionError`, `ValueError` | Test logic, expected vs actual values |
| Timeout Issues | `timeout`, `timed out`, `hanging` | Long-running loops, infinite recursion |
| Dependency Issues | `not found`, `import failed`, `version conflict` | Package versions, environment setup |
| Environmental Issues | `permission denied`, `out of memory`, `disk full` | Resource limits, configuration |
| JIT Crashes | `execution crashed`, `libKGENCompilerRTShared.so` | Non-deterministic Mojo compiler crash |
| Compile Errors (--Werror) | `'alias' is deprecated`, `unused return value` | Mojo deprecation promoted to error |

### Phase 3: Classify as PR-Caused, Pre-Existing, or Flaky

| Failure Type | Signal | Action |
|---|---|---|
| **PR-caused** | Error points to a file you changed | Fix the code |
| **Pre-existing** | Same failure appears on main branch history | Ignore (not your fault) |
| **Flaky crash** | `error: execution crashed` or passes on other PRs | Re-run failed jobs |

```bash
# Check if issue exists on main branch
gh run list --branch main --limit 5

# Compare CI failure to main branch
gh run list --branch main --workflow "<Workflow Name>" --limit 3
gh run view <main-run-id> --repo <owner>/<repo> 2>&1 | grep "JobName"

# Check if a job passes on other open PRs
gh run list --repo <owner>/<repo> --workflow "Comprehensive Tests" --limit 5
```

### Phase 4: Handle Mojo-Specific Failures

#### Check for --Werror Misattribution

Retry logic may mislabel compile errors as JIT crashes. **Always read the actual logs**:

```bash
gh run view <run-id> --log-failed 2>&1 | grep -E "error:|FAILED" | head -20
```

Look for **compile errors** (e.g., `'alias' is deprecated`) rather than `execution crashed`.

#### Reproduce Locally with CI Flags

```bash
# Match CI conditions exactly
pixi run mojo --Werror -I "$(pwd)" -I . tests/path/to/test.mojo
```

#### Find All Deprecated Syntax

```bash
grep -rn "^alias " --include="*.mojo" shared/ tests/
```

#### Identify Flaky Runtime Crashes

Mojo runtime crashes (`error: execution crashed`) in CI are often non-deterministic:
- Not reproducible locally (environment-specific)
- Not correlated with code changes in your PR
- Can be marked `continue-on-error: true` in CI matrix

```bash
gh run view <run-id> --repo <owner>/<repo> --job <job-id> --log 2>&1 | grep -B2 "execution crashed"
```

### Phase 5: Re-run Flaky Failures

```bash
# Re-run only the failed jobs (not the whole workflow)
gh run rerun <run-id> --repo <owner>/<repo> --failed

# Monitor until completion
gh run watch <run-id> --repo <owner>/<repo> --exit-status
```

### Phase 6: Validate Fix Didn't Break Unrelated Tests

The key question: **does the failure exist in commits on main that don't include your changes?**

```bash
# Check if error references a file you touched
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep "error:" | grep -v "warning"
```

### Triage: Separate Real Bugs from JIT Crashes

```bash
# Get the failing workflow run
gh run view <run-id> --log-failed | head -200

# Look for patterns:
# - "LLVM ERROR" / "libKGENCompilerRTShared.so" = JIT crash (not your bug)
# - Assertion failures with wrong values = real bug
# - "link check failed" = network flake or dead URL
```

**Key insight**: JIT crashes are non-deterministic Mojo compiler bugs. You cannot fix them in user code. Mark affected CI matrix entries as `continue-on-error: true`.

### CI Matrix: Mark JIT-Crash Groups Non-Blocking

```yaml
matrix:
  test-group:
    - name: "Core Gradient"
      path: "tests/shared/core"
      pattern: "test_gradient*.mojo"
      continue-on-error: true  # Mojo JIT crash - see #<issue>
```

Then in the step: `continue-on-error: ${{ matrix.test-group.continue-on-error == true }}`

### Handle Flaky Link Checkers

```yaml
# In link-check.yml, exclude URLs with transient failures
args: --exclude conventionalcommits.org --exclude example.com
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Read only last few lines | Used `tail` to check end of log | Missed earlier context and root cause | Read full log or use grep for patterns |
| Search for single keyword | Grepped only "error" | Missed "FAILED", "panic", "exception" variants | Use multiple error patterns together |
| Analyze without PR context | Looked at logs in isolation | Couldn't connect to code changes | Always compare with PR diff |
| Skip stack traces | Focused only on error message | Missed actual source location | Full stack trace shows root cause |
| Check if failure is pre-existing using only PR CI output | Looked at PR CI output without comparing to main history | Cannot tell if failure pre-exists without checking main branch runs | Always cross-reference against `gh run list --branch main` |
| Assume all CI failures are PR-caused | Treated `Core ExTensor` crash as caused by serialization change | ExTensor crashes are flaky runtime crashes unrelated to the serialization fix | Check which files the failing test covers vs which files you changed |
| Wait for log output before run completes | Called `gh run view --log-failed` while run still in progress | GitHub returns "run is still in progress; logs will be available when it is complete" | Check `gh run view` status first; use `gh run watch` for background waiting |
| Controlled experiment without `--Werror` | Ran heavy vs light import tests 30x locally | 0 crashes — the JIT crash hypothesis was untestable without `--Werror` | Always reproduce with exact CI flags first |
| Controlled experiment in Docker (GLIBC 2.35) | Ran same tests 30-100x in Docker matching CI env | Still 0 crashes — the crash wasn't GLIBC-dependent | Environment matching alone doesn't reproduce if the failure mode is wrong |
| ADR-009 reproduction (25 tests in one file) | Ran monolithic test file 50x locally and in Docker | 0 crashes — heap corruption also not reproducible | Historical bugs may already be fixed; verify before building workarounds |
| Searching CI logs for "execution crashed" | Searched 10+ recent CI runs | Zero instances found — the actual errors were compile failures | Read the logs before assuming the failure mode |
| Docker bind-mount pixi install | Ran `pixi install` inside Docker with shared `.pixi/` | Corrupted host Mojo installation (hardcoded paths) | Never share `.pixi/` between host and Docker; use separate volumes |

## Results & Parameters

### Output Format for CI Analysis Report

Provide analysis with:

1. **Error Category** — Type of failure (compilation, test, timeout, dependency, environmental, JIT crash)
2. **Root Cause** — What line/code caused the failure
3. **Context** — Full error message and stack trace
4. **Related Changes** — Which PR changes might have caused it
5. **Remediation** — Recommended fix or investigation steps

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

### Mojo --Werror Fix Reference

```diff
# Mojo 0.26.1: alias deprecated, replace with comptime
- alias MY_CONST: Int = 42
+ comptime MY_CONST: Int = 42
```

### Environment Comparison for Misdiagnosis

| Parameter | Local | Docker | CI |
|-----------|-------|--------|-----|
| GLIBC | 2.39 | 2.35 | 2.35 |
| Mojo | 0.26.1 | 0.26.1 | 0.26.1 |
| `--Werror` | No (default) | No (default) | Yes |
| Crash rate | 0% | 0% | 100% (compile error) |

### Error Handling

| Problem | Solution |
|---------|----------|
| Logs not accessible | Use `gh run view` to check permissions |
| Truncated logs | Download full artifact instead of view |
| Large log files | Use grep to extract relevant sections |
| Encoded artifacts | Unzip and decompress before analysis |

### Common Pre-Existing Failures (ProjectOdyssey)

| Check | Status | Notes |
|-------|--------|-------|
| `link-check` | Pre-existing | Root-relative links (`/.claude/...`) fail on all PRs — lychee needs `--root-dir` |
| `Core ExTensor` | Intermittent flaky | Mojo runtime crash; passes on other PRs; re-run resolves it |
| `Core Initializers` | Intermittent flaky | Same pattern as Core ExTensor |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #336 CI diagnosis | Multiple CI check triage and fix |
| ProjectOdyssey | PR #4494 / #4898 Mojo JIT vs compile error misdiagnosis | alias→comptime fix |
| ProjectOdyssey | PR #4897 Dockerfile + pre-commit triage | GID collision + bash -c args |
