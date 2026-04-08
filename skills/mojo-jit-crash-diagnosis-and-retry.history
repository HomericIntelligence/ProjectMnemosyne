---
name: mojo-jit-crash-diagnosis-and-retry
description: "Use when: (1) CI produces 'execution crashed' (libKGENCompilerRTShared.so) before any test output, (2) multiple unrelated test files crash in the same CI run on unchanged code, (3) a Mojo test file crashes deterministically at the Nth sequential call to a complex function, (4) adding or refining retry logic in just test-group to distinguish JIT flakiness from real test failures"
category: debugging
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# Mojo JIT Crash Diagnosis and Retry

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated patterns for diagnosing Mojo JIT compiler crashes, distinguishing flaky infrastructure failures from real test bugs, implementing retry logic, splitting test files, and documenting workarounds |
| Outcome | Merged from 5 source skills |
| Verification | unverified |

## When to Use

- CI produces `execution crashed` with no test output before the crash (compiler flake, not test bug)
- Multiple unrelated test files crash in the same CI run — key indicator of infrastructure flakiness
- Tests pass on `main` but fail on a PR with identical content in those files
- The PR only changed a few files but whole test groups fail
- The crash is non-deterministic: same test passes/fails randomly across runs
- A Mojo test file crashes **deterministically** at the Nth sequential call (heap corruption, not JIT flake)
- The test file has >10 test functions running deep-network-scale operations
- The `just test-group` retry loop retries all failures indiscriminately (needs crash-aware refinement)
- CI logs cannot distinguish retry-exhausted from normal test failures

## Verified Workflow

### Quick Reference

**Identify JIT flake**:
```bash
gh run view <run-id> --log-failed 2>&1 | grep -E "execution crashed|libKGENCompilerRTShared|#[0-9]"
```

**Rebase to re-trigger CI** (flaky infrastructure fix):
```bash
git fetch origin main && git rebase origin/main && git push origin <branch> --force
```

**Count test functions** (to decide if file split is needed):
```bash
grep -c "^fn test_" tests/models/test_my_model_e2e.mojo
```

### Step 1: Distinguish JIT Flake from Real Test Bug

**Diagnosis by output position** — the single most reliable heuristic:

| Symptom | Cause |
|---------|-------|
| `execution crashed` before any test output | Compiler flake — retry |
| `execution crashed` after test output | Likely a real test bug |
| Specific assertion failure message | Real test bug — investigate |

**JIT crash signature** (exact offsets vary by Mojo version):
```text
#0 libKGENCompilerRTShared.so+0x3c60bb  # Mojo internal assertion
#1 libKGENCompilerRTShared.so+0x3c3ce6  # Mojo internal assertion
#2 libKGENCompilerRTShared.so+0x3c6cc7  # Mojo internal assertion
#3 libc.so.6+0x45330                    # __fortify_fail_abort in glibc
#4 <varies per test file>               # Different JIT codegen path
```

**Flakiness indicators** (confirm all three for high confidence):
- Multiple unrelated test files crash in same CI run
- `execution crashed` without meaningful stack trace
- Tests pass on `main` but fail on PR with no relevant code changes

**Deterministic heap corruption indicators** (distinct from JIT flake):
- Always crashes at the same Nth test function call
- Test file has many test functions running deep-network-scale operations
- Crash is reproducible run-to-run

### Step 2: Handle JIT Flakiness — Rebase and Retry

Compare which files changed vs. which files failed:
```bash
git diff main...HEAD --name-only
gh run view <run-id> --job <job-id> --log 2>&1 | grep -E "(FAILED|crash|execution)"
```

Cross-reference with `main` CI:
```bash
gh run list --workflow "comprehensive-tests.yml" --limit 5
gh run view <main-run-id> --job <job-id> --log 2>&1 | grep -E "(PASSED|FAILED|test_)"
```

Rebase to trigger fresh infrastructure:
```bash
git fetch origin main
git rebase origin/main
git push origin <branch> --force-with-lease
# If stale info error:
git push origin <branch> --force
```

Verify PR auto-merge is still enabled:
```bash
gh pr view <pr-number> --json autoMergeRequest,mergeStateStatus
gh run list --branch <branch> --limit 3
```

### Step 3: Add Crash-Aware Retry Logic to justfile

**Refined retry logic** (crash-aware with distinct failure messages):

```bash
MAX_RETRIES=1

for test_file in $test_files; do
    if [ -f "$test_file" ]; then
        echo ""
        echo "Running: $test_file"
        test_count=$((test_count + 1))

        file_passed=false
        retry_used=false
        fail_reason=""

        for attempt in $(seq 1 $((MAX_RETRIES + 1))); do
            output=$(pixi run mojo -I "$REPO_ROOT" -I . "$test_file" 2>&1)
            exit_code=$?
            echo "$output"

            if [ $exit_code -eq 0 ]; then
                file_passed=true
                break
            fi

            # Only retry on JIT/execution crash
            if echo "$output" | grep -q "execution crashed" && [ $attempt -le $MAX_RETRIES ]; then
                echo "Execution crashed, retrying ($attempt/$MAX_RETRIES)..."
                retry_used=true
            else
                if [ "$retry_used" = true ]; then
                    fail_reason="FAILED after retry"
                else
                    fail_reason="FAILED (no crash, no retry)"
                fi
                break
            fi
        done

        if [ "$file_passed" = true ]; then
            echo "PASSED: $test_file"
            passed_count=$((passed_count + 1))
        else
            echo "$fail_reason: $test_file"
            failed_count=$((failed_count + 1))
            failed_tests="$failed_tests\n  - $test_file [$fail_reason]"
        fi
    fi
done
```

**Output distinction**:

| Scenario | Message |
|----------|---------|
| JIT crash → retry → fail | `FAILED after retry: test_file.mojo` |
| Normal assertion failure | `FAILED (no crash, no retry): test_file.mojo` |
| JIT crash → retry → pass | `PASSED: test_file.mojo` |

### Step 4: Split Test Files for Deterministic Heap Corruption

When crashes are deterministic (always at the same Nth call), the root cause is JIT heap corruption that accumulates across sequential test calls — not a code bug.

**Safe limits by network scale**:

| Network Scale | Safe Tests Per File | Notes |
|--------------|--------------------|----|
| Shallow (≤5 layers) | ≤10 | Standard Mojo guidance |
| Medium (6–10 layers) | ≤7 | LeNet-5, small ResNets |
| Deep (11+ layers) | ≤5 | VGG-16, ResNet-50 |

**Split workflow**:

1. Count test functions:
   ```bash
   grep -c "^fn test_" tests/models/test_my_model_e2e.mojo
   ```

2. Create `_part1.mojo` and `_part2.mojo` with ADR-009 header:
   ```mojo
   # ADR-009: This file is intentionally limited to <=10 fn test_ functions.
   # Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
   # high test load. Split from test_<model>_e2e.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
   ```

3. Duplicate any shared helpers (`conv_block`, `forward`) in both files — Mojo has no `include` mechanism.

4. Split tests:
   - **Part 1**: forward pass tests, training tests (heavier)
   - **Part 2**: gradient checks, output range, numerical stability (lighter)

5. Update each file's `main()` to only call the tests it contains.

6. Delete original: `git rm tests/models/test_my_model_e2e.mojo`

7. Verify CI uses glob discovery (no workflow changes needed if using `test_*.mojo` pattern).

**Naming convention**:
```text
test_<model>_e2e.mojo        → deleted
test_<model>_e2e_part1.mojo  → forward/training tests
test_<model>_e2e_part2.mojo  → gradient/numerical/stability tests
```

### Step 5: Document the Crash (when creating a dev doc)

For `docs/dev/mojo-jit-crash-workaround.md`, include:
- **Problem** — what `execution crashed` means and that it originates in `libKGENCompilerRTShared.so`
- **Diagnosis table** — crash before vs. after test output
- **Workaround: CI Retry Pattern** — shell retry loop + GitHub Actions `nick-fields/retry` snippet
- **Relationship to ADR-009** — comparison table distinguishing JIT flake (non-deterministic, retry) from heap corruption (deterministic, file split)
- **Long-term resolution** — checklist for what to remove when upgrading Mojo

Add cross-reference in `docs/dev/mojo-test-failure-patterns.md`:
```markdown
> **Note**: For `execution crashed` errors that appear _before_ any test output, see
> [Mojo JIT Crash Workaround](mojo-jit-crash-workaround.md) — this is a compiler flake,
> not a test bug. Retry the test run to confirm.
```

Run markdownlint via pre-commit (not npx — unavailable in pixi environment):
```bash
pixi run pre-commit run markdownlint-cli2 --files docs/dev/mojo-jit-crash-workaround.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed crash was caused by new test code | Investigated new backward test code for memory bugs | Unchanged files (test_layers, test_linear) were ALSO crashing | Always check if unchanged files are also failing before debugging new code |
| Removing imports to narrow the crash | Changed `loss.mojo` to avoid `activation.mojo` import | `test_loss_funcs.mojo` doesn't import activation at all but still crashed | The crash is in the JIT compiler itself, not triggered by any specific Mojo code pattern |
| Region-specific theory | Checked if specific Azure region always fails | Crashes occur on multiple regions; others pass sometimes | Azure region is not the determining factor |
| Reduce batch size | Halved batch_size from 4 to 2 in all tests | Crash still occurs — root cause is cumulative JIT memory across test calls, not per-call memory | Batch size is not the root cause; number of sequential JIT compilations is |
| Use smaller model variant | Considered using fewer channels (e.g., VGG-8) | Would change test semantics | Keep the real model, reduce the number of calls per session instead |
| Add teardown between tests | Mojo has no per-test teardown hooks in v0.26.1 | Not applicable — Mojo `main()` runs tests sequentially with shared JIT state | File splitting is the only reliable workaround |
| Blind retry-all loop | Original retry retried ALL failures, not just crashes | Wasted CI time retrying normal assertion failures | Only retry on `grep -q "execution crashed"` |
| Using `tee` + `${PIPESTATUS[0]}` for capture | Stream output in real-time while capturing | Works but adds temp file complexity | `$(... 2>&1)` with immediate `echo` is simpler for short test output |
| Separate crash-check run | Run mojo twice: once to capture, once to check exit code | Doubles execution time unnecessarily | Capture once with `$()`, check exit code and output from same run |
| Direct `pixi run npx markdownlint-cli2` | Ran markdownlint via npx through pixi | `npx: command not found` — npx not in pixi environment | Use `pixi run pre-commit run markdownlint-cli2 --files <files>` |
| Edit CLAUDE.md without Read | Tried to Edit before reading | Tool rejected: "File has not been read yet" | Always Read before Edit |

## Results & Parameters

### Crash Identification Commands

```bash
# Identify JIT crash signature in CI logs
gh run view <run-id> --log-failed 2>&1 | grep -E "execution crashed|libKGENCompilerRTShared|#[0-9]"

# Compare passing vs failing runs for same test
for run_id in <run1> <run2> <run3>; do
  echo "Run $run_id:"
  gh run view $run_id --log 2>&1 | grep -E "PASSED.*test_|FAILED.*test_" | grep test_loss | head -5
done

# Verify distinct failure messages after crash-aware retry
gh run view <run-id> --log 2>&1 | grep -E "FAILED after retry|FAILED \(no crash"

# Check PR auto-merge and CI status
gh pr checks <pr-number>
gh run list --branch <branch> --limit 3
```

### Mojo Closure Capture Note

When un-skipping Mojo tests that use closures capturing outer variables, mark the closure `escaping`:
```mojo
# CORRECT when capturing outer variables
fn forward_for_grad(inp: ExTensor) raises escaping -> ExTensor:
    return multiply(inp, captured_grad_output)  # Captures grad_output
```

### batch_norm2d Pathological Test Case

When `grad_output = ones_like(output)`, batch norm backward gives analytically-zero gradients. Float32 noise makes numerical gradient non-zero (~0.009), causing false ~1000x mismatch. Use non-uniform `grad_output` that breaks symmetry:
```mojo
var grad_output = zeros_like(output)
for i in range(numel):
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    grad_output._data.bitcast[Float32]()[i] = val
```
