---
name: ci-cd-flaky-ci-root-cause-triage
description: "Triage flaky CI failures by separating infrastructure issues, deterministic code bugs, and genuine runtime flakiness. Use when: (1) CI tests fail intermittently across unrelated PRs, (2) re-running CI sometimes fixes failures, (3) multiple test groups fail simultaneously, (4) failures appear on PRs with no Mojo code changes."
category: ci-cd
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - flaky-tests
  - ci-cd
  - docker
  - mojo
  - root-cause-analysis
  - container-cache
---

# Flaky CI Root Cause Triage

Systematic approach to triaging CI failures that appear flaky but often have distinct,
fixable root causes hiding behind infrastructure noise.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Investigate and fix intermittent Mojo test failures in ProjectOdyssey CI |
| **Outcome** | Success -- found 3 distinct root causes: only 1 of 4 failures was actually a JIT flake; the rest were deterministic bugs masked by infrastructure failures |
| **Repository** | ProjectOdyssey |
| **PR** | #5097 |

## When to Use

- CI tests fail intermittently -- some PRs pass, some fail with identical code
- Multiple unrelated test groups fail in the same CI run
- Re-running CI sometimes makes failures disappear
- Failures occur on PRs that don't change test code (docs-only, config-only)
- Error messages include `execution crashed`, `504 Gateway Time-out`, or parse errors
- The team attributes all failures to "JIT flakiness" without reading actual logs

## Verified Workflow

### Quick Reference

```bash
# Step 1: Get actual failure logs (don't trust labels)
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "FAILED|execution crashed|error:|parse" | head -40

# Step 2: Classify each failure
gh run view <RUN_ID> --log-failed 2>&1 | grep -B10 "FAILED.*<test_file>"

# Step 3: Check if failures reach test execution at all
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "504|Gateway|Cache not found" | head -10

# Step 4: Verify which files the PR actually changed
gh pr diff <PR_NUMBER> --name-only
```

### Detailed Steps

#### Phase 1: Classify Failures Into 3 Buckets

**CRITICAL**: Read actual CI error output before assuming any failure mode. The
`mojo-ci-failure-misdiagnosis` skill documents a case where "JIT crashes" were actually
`--Werror` compile errors from deprecated syntax.

For each failing test, classify into exactly one bucket:

| Bucket | Signature | Action |
|--------|-----------|--------|
| **Infrastructure** | `504 Gateway Time-out`, `Cache not found`, container build failure | Fix CI config |
| **Deterministic bug** | `failed to parse`, `error:` with line number, assertion failure | Fix code |
| **Genuine JIT flake** | `execution crashed` with `libKGENCompilerRTShared.so` stack, NO test output before crash | Upstream Mojo bug |

```bash
# Extract and classify all failures from a CI run
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "❌ FAILED" | sort -u
# Then for each failed test:
gh run view <RUN_ID> --log-failed 2>&1 | grep -B15 "FAILED.*<test_file>"
```

#### Phase 2: Fix Infrastructure Issues First

Infrastructure failures block ALL tests. Common patterns:

**Docker Hub Thundering Herd** (found in this session):
- Symptom: `504 Gateway Time-out` when pulling base image
- Root cause: Podman storage cache exceeds GitHub Actions 10 GB limit, so every
  parallel job (15+) independently pulls from Docker Hub
- Diagnosis: `grep "Cache not found" <ci-logs>` -- if every job misses cache, this is it
- Fix: Replace Podman storage cache with image tar cache (`podman save/load`)

```bash
# Check if cache is actually restoring
gh run view <RUN_ID> --log 2>&1 | grep -E "Cache (not found|restored)"
```

**Container Build Failures**:
- Symptom: Jobs fail before any test runs
- Diagnosis: Check if the failure is in `setup-container` action, not in test execution
- Fix: Depends on root cause (registry issues, Dockerfile errors, permission issues)

#### Phase 3: Fix Deterministic Test Bugs

These are NOT flaky -- they fail 100% of the time but get lost in infrastructure noise.

**Common patterns found**:

1. **Fast-path optimization bugs**: Code has an optimization for common cases but
   misses edge cases. In this session: multi-dim slice memcpy fast-path checked
   `start/end` but ignored `step` parameter.

2. **Mojo syntax incompatibility**: Python patterns that don't work in Mojo:
   - f-strings in function call arguments: `fn(f"text {var}")` -- use concatenation
   - Tuple destructuring: `var (a, b, c) = fn()` -- use `var result = fn(); var a = result[0]`
   - These cause `failed to parse` errors, NOT runtime crashes

3. **`--Werror` asymmetry**: CI uses `--Werror` but local dev doesn't. Tests that compile
   locally may fail in CI due to deprecation warnings becoming errors.

```bash
# Reproduce locally with CI flags
pixi run mojo --Werror -I "$(pwd)" -I . <test_file>
```

#### Phase 4: Handle Genuine JIT Flakes

After removing infrastructure and deterministic failures, the remaining `execution crashed`
errors with `libKGENCompilerRTShared.so` stack traces are genuine Mojo compiler bugs.

**Key characteristics**:
- Crash happens BEFORE any test output (during JIT compilation, not execution)
- Stack trace shows fixed offsets in `libKGENCompilerRTShared.so`
- Same test passes on other runs with identical code
- Cannot reproduce locally (tried 30-100x in prior investigations)

**Do NOT**:
- Add retry logic (masks real bugs, user explicitly rejects this)
- Add `continue-on-error` (masks real failures)
- Split test files (ADR-009 was resolved, the old workaround is unnecessary)

**Do**:
- Document as upstream Mojo 0.26.1 bug
- Use targeted submodule imports to reduce compilation footprint
- Track separately from deterministic failures

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed all failures were JIT flakes | Investigated `libKGENCompilerRTShared.so` crashes as the sole root cause | Only 1 of 4 failing tests was actually a JIT crash; 2 were parse errors and 1 was a logic bug | Always read actual CI error output -- classify each failure individually |
| Relied on Podman storage cache | GitHub Actions cached `~/.local/share/containers` keyed on Dockerfile hash | Podman storage directory exceeded 10 GB cache limit -- tar save always failed silently | Image tar cache (`podman save/load`) is much smaller and stays under the limit |
| Tried controlled experiments to reproduce JIT crashes | Ran tests 30-100x locally and in Docker matching CI GLIBC | 0 crashes -- the JIT bug is environment-specific to GitHub Actions runners | Don't spend time reproducing JIT crashes locally -- focus on fixing deterministic bugs instead |
| Used retry logic to handle JIT crashes | `scripts/run_test_group.sh` had 3-attempt retry with exponential backoff | Retry masked real deterministic failures -- a parse error retried 3 times still fails | Retry is a workaround, not a fix. Remove it to make all failures immediately visible |
| `continue-on-error` on flaky jobs | Gradient tests job had `continue-on-error: true` | Masked real gradient checking failures after ADR-009 was resolved | Workarounds outlive their usefulness -- remove them when the underlying issue is fixed |

## Results & Parameters

### Triage Classification Commands

```bash
# Full triage of a failed CI run
RUN_ID=<your-run-id>

# 1. Get all unique failures
gh run view $RUN_ID --log-failed 2>&1 | grep "❌ FAILED" | sort -u

# 2. Check for infrastructure failures (cache miss, Docker timeout)
gh run view $RUN_ID --log-failed 2>&1 | grep -E "504|Cache not found|Gateway" | head -5

# 3. Check for parse/compile errors (deterministic)
gh run view $RUN_ID --log-failed 2>&1 | grep -E "failed to parse|error:.*line" | head -10

# 4. Check for JIT crashes (genuine flake)
gh run view $RUN_ID --log-failed 2>&1 | grep "execution crashed" | head -5

# 5. For each failed test, get context
gh run view $RUN_ID --log-failed 2>&1 | grep -B15 "FAILED.*<test_file>"
```

### Fix Patterns

```yaml
# Image tar cache (replaces broken Podman storage cache)
- name: Cache container image tar
  uses: actions/cache@v5
  with:
    path: /tmp/podman-image-cache
    key: container-image-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}

- name: Load cached image or build
  run: |
    if [ -f /tmp/podman-image-cache/dev.tar ]; then
      podman load -i /tmp/podman-image-cache/dev.tar
    else
      podman compose build projectodyssey-dev
      mkdir -p /tmp/podman-image-cache
      podman save -o /tmp/podman-image-cache/dev.tar projectodyssey:dev
    fi
```

```mojo
# Mojo: Replace f-strings in function arguments
# WRONG (parse error in Mojo):
assert_value_at(t, i, 1.0, message=f"t[{i}] should be 1.0")
# CORRECT:
assert_value_at(t, i, 1.0, message="t[" + String(i) + "] should be 1.0")

# Mojo: Replace tuple destructuring
# WRONG (unknown declaration error):
var (a, b, c) = fn_returning_tuple()
# CORRECT:
var result = fn_returning_tuple()
var a = result[0]
var b = result[1]
var c = result[2]
```

### Key Statistics from This Investigation

| Metric | Value |
|--------|-------|
| Total CI failures investigated | 4 unique test files |
| Infrastructure failures | 1 (Docker 504 -- blocked ALL CI) |
| Deterministic code bugs | 3 (parse errors + logic bug) |
| Genuine JIT flakes | 1 (`test_training_loop.mojo`) |
| Percentage of "flaky" failures that were actually deterministic | 75% |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5097 | Container cache fix, workaround removal, 3 deterministic bug fixes |
