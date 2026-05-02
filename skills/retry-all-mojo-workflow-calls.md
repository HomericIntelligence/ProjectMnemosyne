---
name: retry-all-mojo-workflow-calls
description: 'Audit GitHub Actions workflows for unprotected bare pixi run mojo calls
  and apply retry logic. Use when: retry was applied to one workflow but others still
  have bare pixi run mojo calls, or when auditing CI for JIT crash resilience.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# retry-all-mojo-workflow-calls

Audit all `.github/workflows/*.yml` files for unprotected `pixi run mojo` calls
and protect them with retry logic — either by routing through `just test-group`
(which has built-in retry) or by adding inline 3-attempt exponential-backoff loops.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Mojo Version | 0.26.1.0.dev2025122805 |
| Objective | Extend JIT crash retry from one workflow to all workflows |
| Outcome | Success — 8 files changed, all bare mojo calls now protected |
| Repository | ProjectOdyssey |
| Issue | #3329 (follow-up to #3120) |
| PR | #3950 |

## When to Use

- A retry fix was applied to `just test-group` or one workflow, but other workflows still
  call `pixi run mojo` directly without retry protection
- CI has intermittent Mojo JIT crashes across multiple workflows (not just one)
- You need to audit all workflows systematically for a class of vulnerability
- Adding a new workflow that runs Mojo and want to ensure it has retry from the start

## Verified Workflow

### 1. Audit: Find All Bare Calls

```bash
grep -rn "pixi run mojo" .github/workflows/ --include="*.yml"
```

### 2. Classify Each Call

For each hit, decide:

| Call type | Best fix |
|-----------|----------|
| Test file (`*.mojo` test) | Route through `just test-group` (add `Install Just` step) |
| Package build (`mojo package`) | Inline retry loop |
| Benchmark run (`mojo run`) | Inline retry loop |
| Build step (`mojo build`) | Inline retry loop |
| Version check (`mojo --version`) | No retry needed (not JIT compilation) |

### 3. Upgrade `just test-group` Retry (3 attempts, exponential backoff)

If `just test-group` currently has only 1 retry, upgrade to 3 attempts with exponential backoff:

```bash
# Replace the per-file if/else retry with a while loop
attempt=0
max_attempts=3
delay=1
test_passed=0
while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt + 1))
    if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
        test_passed=1
        break
    fi
    if [ $attempt -lt $max_attempts ]; then
        echo "Attempt $attempt failed, retrying in ${delay}s: $test_file"
        sleep $delay
        delay=$((delay * 2))
    fi
done
if [ $test_passed -eq 1 ]; then
    passed_count=$((passed_count + 1))
else
    failed_count=$((failed_count + 1))
    failed_tests="$failed_tests\n  - $test_file"
fi
```

### 4. Route Test Workflows Through `just test-group`

Add `Install Just` step after Pixi setup, then replace bare calls:

```yaml
- name: Install Just
  uses: extractions/setup-just@v3

# Before:
- name: Run tests
  run: |
    pixi run mojo -I . tests/path/test_foo.mojo

# After:
- name: Run tests
  run: |
    just test-group "tests/path" "test_foo.mojo"
```

Multiple files in one directory can be passed as a space-separated string:

```yaml
just test-group "tests/shared/core" "test_gradient_checking_basic.mojo test_gradient_checking_dtype.mojo"
```

### 5. Inline Retry for Non-Test Calls (Benchmarks, Builds, Package Compilation)

For calls that cannot use `just test-group`, add an inline retry loop:

```bash
attempt=0
delay=1
while [ $attempt -lt 3 ]; do
  attempt=$((attempt + 1))
  if pixi run mojo <args>; then
    break
  fi
  if [ $attempt -lt 3 ]; then
    echo "Attempt $attempt failed, retrying in ${delay}s..."
    sleep $delay
    delay=$((delay * 2))
  else
    echo "Failed after 3 attempts"
    exit 1
  fi
done
```

For soft-failure workflows (those already using `|| true`), preserve that behavior by
wrapping the loop with `|| true` instead of `exit 1`.

### 6. Verify YAML Syntax

```bash
# Pre-commit hooks validate YAML automatically:
just pre-commit-all

# Or manually:
pixi run check-yaml .github/workflows/*.yml
```

## Files Changed in ProjectOdyssey #3329

| File | Change |
|------|--------|
| `justfile` | Upgraded `test-group` per-file retry: 2 → 3 attempts, 1s/2s backoff |
| `comprehensive-tests.yml` | Wrapped `mojo package` compilation in 3-attempt retry |
| `test-gradients.yml` | Added `Install Just` + routed 2 bare calls through `just test-group` |
| `test-data-utilities.yml` | Added `Install Just` + routed 5 bare calls through `just test-group` |
| `simd-benchmarks-weekly.yml` | Wrapped benchmark run in 3-attempt retry |
| `benchmark.yml` | Wrapped Mojo benchmark run in 3-attempt retry |
| `release.yml` | Wrapped `mojo build` loop + 2 `mojo test` steps in 3-attempt retry |
| `paper-validation.yml` | Wrapped `mojo test` + `mojo train` in 3-attempt retry (preserving `|| true`) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Routing benchmark runs through `just test-group` | Tried to use `just test-group` for `simd-benchmarks-weekly.yml` | `test-group` expects test files, not benchmark scripts; output format is different | Benchmarks need inline retry, not `just test-group` routing |
| Single retry for all call types | Considered using one inline loop pattern everywhere | `|| true` soft-failure semantics must be preserved for paper validation scripts | Soft-failure workflows need the retry loop wrapped with `|| true`, not`exit 1` |
| Skipping `mojo --version` wrapping | Initially flagged `pixi run mojo --version` for retry | Version check does not invoke the JIT compiler, so it cannot crash this way | Only JIT-compilation calls (`mojo <file>`, `mojo test`, `mojo package`, `mojo build`, `mojo run`) need retry |

## Results & Parameters

Standard retry pattern used throughout:

- **Max attempts**: 3
- **Base delay**: 1s
- **Backoff factor**: 2x (1s, 2s)
- **Exit behavior**: `exit 1` on hard-fail workflows; `|| true` preserved on soft-fail workflows

```bash
# Audit command — shows all bare pixi run mojo calls across workflows
grep -n "pixi run mojo" .github/workflows/*.yml | grep -v "mojo --version" | grep -v "mojo format"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3329, PR #3950 | [notes.md](../../references/notes.md) |
