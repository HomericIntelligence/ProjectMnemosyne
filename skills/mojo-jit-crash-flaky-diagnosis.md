---
name: mojo-jit-crash-flaky-diagnosis
description: 'Diagnose and distinguish genuine Mojo JIT crash failures from infrastructure
  flakiness in CI. Use when: CI shows execution crashed errors in unchanged test files,
  multiple unrelated test groups fail together, or a PR fails tests that pass on main.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo JIT compiler produces `execution crashed` errors in CI that look like code bugs but are actually infrastructure flakiness |
| **Context** | ProjectOdyssey / Mojo test suites on GitHub Actions |
| **Trigger** | PR CI fails with crashes in test files that were NOT changed |
| **Resolution** | Rebase branch onto latest main and re-push to trigger fresh CI run |

## When to Use

- CI run shows `mojo: error: execution crashed` without a meaningful stack trace
- **Multiple unrelated test files** crash in the same CI run (key indicator of infrastructure vs. code issue)
- Tests that PASS on `main` are FAILING on a PR with identical content in those files
- The PR only changed a small number of files but whole test groups (e.g. "Core NN Modules") fail
- Failure pattern: tests in positions 4-5 of a sequence crash, but later positions are fine on main

## Verified Workflow

### Step 1: Determine if failures are genuine or flaky

Compare which files changed vs. which files failed:

```bash
# Files changed in this PR
git diff main...HEAD --name-only

# Check failing job logs
gh run view <run-id> --job <job-id> --log 2>&1 | grep -E "(FAILED|crash|execution)"
```

**Flaky indicator**: If unchanged files crash (e.g. `test_layers.mojo`, `test_linear.mojo`) in the same run as changed files, it's infrastructure flakiness.

### Step 2: Cross-reference with main branch CI

```bash
# Find a recent passing run on main
gh run list --workflow "comprehensive-tests.yml" --limit 5

# Check the specific failing job on main
gh run view <main-run-id> --job <job-id> --log 2>&1 | grep -E "(PASSED|FAILED|test_)"
```

If main passes all the same tests with `PASSED` and your PR fails them without code changes, it's flaky.

### Step 3: Rebase and re-trigger

```bash
git fetch origin main
git rebase origin/main
git push origin <branch> --force-with-lease
# If stale info error, use --force
git push origin <branch> --force
```

This triggers a new CI run on fresh infrastructure, which typically resolves the flakiness.

### Step 4: Verify PR auto-merge is still enabled

```bash
gh pr view <pr-number> --json autoMergeRequest,mergeStateStatus
```

If `mergeStateStatus` is `BLOCKED` after push, check CI run:

```bash
gh run list --branch <branch> --limit 3
```

## Key Diagnostic Pattern

The definitive flakiness signature for Mojo JIT crashes:

```
# What you see in failing CI:
test_unchanged_file_1.mojo  ->  execution crashed (after 4 tests)
test_unchanged_file_2.mojo  ->  execution crashed (0 tests pass)
test_changed_file.mojo      ->  execution crashed

# What you see on main CI at same time:
test_unchanged_file_1.mojo  ->  PASSED (15+ tests)
test_unchanged_file_2.mojo  ->  PASSED (10+ tests)
test_changed_file.mojo      ->  PASSED
```

If unchanged files fail in your PR but pass on main, the failures are infrastructure-related.

## Mojo Closure Capture Gotcha (Related)

When un-skipping Mojo tests that use closures with `compute_numerical_gradient`:

```mojo
# WRONG - missing 'escaping' but works when non-capturing:
fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    return some_op(inp)  # Only uses inp, no captured vars

# CORRECT when capturing outer variables:
fn forward_for_grad(inp: ExTensor) raises escaping -> ExTensor:
    return multiply(inp, captured_grad_output)  # Captures grad_output
```

`compute_numerical_gradient` requires `fn (ExTensor) raises escaping -> ExTensor`. Non-escaping functions can be passed where escaping is required in Mojo (escaping is a weaker constraint), but captured ExTensor variables in closures may cause lifetime issues if not declared escaping.

## batch_norm2d Pathological Test Case

When `grad_output = ones_like(output)`, batch norm backward gives analytically-zero gradients:
- `k = sum(grad_output) = N`
- `dotp = sum(grad_output * x_norm) = sum(x_norm) = 0` (batch norm property)
- Formula: `(grad_output - k/N - x_norm * dotp/N) * gamma * invstd = (1 - 1 - 0) = 0`

Float32 noise makes numerical gradient non-zero (~0.009), causing false ~1000x mismatch.

**Fix**: Use non-uniform `grad_output` that breaks symmetry:
```mojo
var grad_output = zeros_like(output)
for i in range(numel):
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    grad_output._data.bitcast[Float32]()[i] = val
# Also update forward_for_grad to compute sum(output * grad_output)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed crash was caused by new test functions | Investigated new backward test code for memory bugs, syntax issues | Unchanged files (test_layers, test_linear) were ALSO crashing, proving code wasn't the issue | Always check if unchanged files are also failing before debugging new code |
| Assumed crash was in test_batch_norm2d_shapes (first test) | Analyzed the first test function for issues | Timing showed crash occurred after ~7s of execution, not immediately | Cross-reference timing between PR CI and main CI to identify WHERE in execution the crash occurs |
| Using `grad_output = ones_like(output)` in batch norm gradient test | Standard approach of using uniform upstream gradient | Analytically-zero gradient due to batch norm normalization property causes false mismatch | Use non-uniform grad_output to break symmetry when testing batch norm backward |
| PyTorch consolidated formula for batch_norm2d_backward | Switched to optimized formula `(grad_output - k/N - x_norm*dotp/N) * gamma * invstd` | When grad_output is uniform (ones), formula reduces to exactly 0 by design | The formula is correct; the test case was pathological, not the implementation |

## Results & Parameters

### Confirmed Flakiness Indicators
- Multiple unrelated test files crash in same CI run: **definitive indicator**
- "execution crashed" without meaningful stack trace: **common with Mojo JIT flakiness**
- Tests pass on main but fail on PR with no relevant code changes: **confirms infrastructure issue**

### Rebase Command
```bash
git fetch origin main && git rebase origin/main && git push origin <branch> --force
```

### PR Status Check
```bash
gh pr checks <pr-number>  # See all check statuses
gh run list --branch <branch> --limit 3  # Find new CI run after push
```
