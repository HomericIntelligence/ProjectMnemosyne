---
name: ci-mojo-gha-vma-sequential-job
description: "Fix non-deterministic GHA CI failures caused by Mojo compiler reserving ~3.6 GB virtual address space per invocation on free-tier runners with 7 GB RAM. Use when: (1) CI fails with 'JIT session error: Cannot allocate memory' or SIGSEGV in libKGENCompilerRTShared.so, (2) failures are non-deterministic and max-parallel:1 does not help, (3) ulimit -v on the runner confirms ~3.6 GB reservation per mojo process, (4) GHA matrix strategy is in use for Mojo test groups."
category: ci-cd
date: 2026-05-04
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - mojo
  - gha
  - virtual-memory
  - vmpeak
  - sequential
  - matrix
  - ci
  - libKGENCompilerRTShared
  - memory-exhaustion
---

# CI: Mojo GHA VMA Sequential Job

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until
> CI confirms. Verification is `verified-precommit` — pre-commit hooks pass and the PR is
> awaiting CI confirmation as of 2026-05-04 (PR #5351).

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-04 |
| **Objective** | Fix non-deterministic CI failures caused by Mojo 0.26.3 compiler exhausting GHA free-tier runner virtual memory (~7 GB total) by reserving ~3.6 GB VmPeak per invocation, even for trivial source files. |
| **Outcome** | Proposed fix: replace GitHub Actions matrix strategy with a single sequential job where all test groups run as named steps. Awaiting CI confirmation. |
| **Verification** | verified-precommit (pre-commit hooks pass; CI in progress on PR #5351 as of 2026-05-04) |
| **Upstream Issue** | modular/modular#6433 — Mojo JIT unconditionally reserves ~3.6 GB VmPeak on startup |

## When to Use

- CI produces `JIT session error: Cannot allocate memory` or `SIGSEGV` in
  `libKGENCompilerRTShared.so` with non-deterministic occurrence
- `max-parallel: 1` on a GHA matrix **does not** fix the failures
- `ulimit -v 3500000 && pixi run mojo` reproduces the crash deterministically locally
- Failures correlate with GHA free-tier runners (7 GB RAM / 2-core)
- Matrix strategy is currently used for Mojo test groups (one job per group)
- Distinct from: UID mismatch crash (Crash 2), KGEN buffer overflow (deterministic + fixed
  address), bitcast UAF (deterministic after Nth test) — see `mojo-jit-crash-retry` skill

## Root Cause

Upstream bug **modular/modular#6433**: Mojo 0.26.3 JIT unconditionally reserves ~3.6 GB of
virtual address space on startup, regardless of source file size or compilation complexity.

- GHA free-tier runners have **7 GB RAM total**
- Each `mojo` invocation consumes ~3.6 GB VmPeak
- Even with `max-parallel: 1`, GHA matrix jobs run **in separate processes on the same physical
  machine** — setup, teardown, and job orchestration overlap, meaning two `mojo` processes may
  co-exist transiently even when jobs are serialized at the GitHub Actions scheduling level
- Combined VmPeak: 2 × 3.6 GB = 7.2 GB → exceeds 7 GB → OOM → SIGSEGV in JIT

**Deterministic local reproducer (100% failure rate):**

```bash
ulimit -v 3500000 && pixi run mojo --Werror -I . tests/any_test.mojo
# → JIT session error: Cannot allocate memory in static TLS block
# Threshold: fails below ~3.6 GB virtual limit, passes at 4.0 GB+
```

## Verified Workflow

> **Warning — Proposed Steps**: Steps below are based on verified-precommit work only.
> CI confirmation is pending (PR #5351). Treat as a hypothesis until CI passes.

### Quick Reference

```yaml
# Replace matrix strategy with a single sequential job
# All test groups become named steps within ONE job
# Only ONE mojo process runs at any given time on the runner

test-mojo-comprehensive:
  runs-on: ubuntu-latest
  timeout-minutes: 120
  steps:
    - uses: actions/checkout@v4
    # ... setup steps (pixi install, container start) ...
    - name: "Memory snapshot"
      run: free -h && ulimit -v
    - name: "Core Tensors"
      run: just test-group "tests/shared/core" "test_tensors*.mojo test_any_tensor*.mojo"
    - name: "Core Activations & Types"
      run: just test-group "tests/shared/core" "test_activation*.mojo test_dtype*.mojo"
    # ... repeat for all test groups (22 total)
```

### Detailed Steps

**Step 1: Confirm root cause (virtual memory, not JIT volume or UID)**

```bash
# Test 1: Does ulimit reproduce the crash?
ulimit -v 3500000 && pixi run mojo --Werror -I . tests/any_test.mojo
# YES → confirmed VmPeak exhaustion

# Test 2: Does it pass with more virtual memory?
ulimit -v 4000000 && pixi run mojo --Werror -I . tests/any_test.mojo
# YES → threshold is ~3.6 GB, confirming per-process reservation

# Test 3: Does max-parallel:1 fix it?
# NO → confirms separate-job overlap is the actual concurrency vector
```

**Step 2: Replace matrix strategy with sequential steps in the workflow**

In `.github/workflows/comprehensive-tests.yml`, convert the matrix job to a single job
with all test groups as named steps:

```yaml
# BEFORE (fails): separate GHA jobs that overlap during setup/teardown
test-mojo-comprehensive:
  strategy:
    max-parallel: 1
    matrix:
      test-group:
        - name: "Core Tensors"
          path: "tests/shared/core"
          pattern: "test_tensors*.mojo test_any_tensor*.mojo"
        # ... more groups
  steps:
    - name: Run test group
      run: just test-group "${{ matrix.test-group.path }}" "${{ matrix.test-group.pattern }}"

# AFTER (fix): single job, all groups as named steps
test-mojo-comprehensive:
  runs-on: ubuntu-latest
  timeout-minutes: 120
  steps:
    - uses: actions/checkout@v4
    # ... all setup steps ...
    - name: "Memory snapshot"
      run: free -h && ulimit -v
    - name: "Core Tensors"
      run: just test-group "tests/shared/core" "test_tensors*.mojo test_any_tensor*.mojo"
    - name: "Core Activations & Types"
      run: just test-group "tests/shared/core" "test_activation*.mojo test_dtype*.mojo"
    # ... all remaining groups as steps
```

**Critical constraint: NO `continue-on-error: true`** — job must fail fast on first broken
step so failures are immediately visible signals, not silently swallowed.

**Step 3: Add `-debug-level=line-tables` to mojo invocations**

In `justfile`, add debug symbols to `_test-group-inner` and `_test-mojo-inner` recipes:

```just
# BEFORE
pixi run mojo --Werror -I "$REPO_ROOT" -I . "$test_file"

# AFTER
pixi run mojo --Werror -debug-level=line-tables -I "$REPO_ROOT" -I . "$test_file"
```

This produces symbolicated stack traces when a crash does occur, enabling faster diagnosis.

**Step 4: Add "Memory snapshot" diagnostic step**

Add this as the first non-setup step in the test job:

```yaml
- name: "Memory snapshot"
  run: free -h && ulimit -v
```

Documents available memory and virtual address limits per run — critical for future diagnosis
if the issue resurfaces with a different Mojo version.

**Step 5: Validate and create PR**

```bash
# Validate workflow YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/comprehensive-tests.yml'))" && echo "YAML valid"

# Run pre-commit on modified files
just precommit

# Create PR
gh pr create \
  --title "fix(ci): replace matrix with sequential steps to fix Mojo VMA exhaustion" \
  --body "Closes #<issue-number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `max-parallel: 1` on matrix | Set matrix `max-parallel: 1` to serialize GHA jobs | GHA jobs are separate processes — even with max-parallel:1, setup/teardown of adjacent jobs overlap on the same physical machine, causing transient co-existence of two `mojo` processes | `max-parallel` controls scheduling concurrency, not physical machine exclusivity; does NOT prevent VmPeak co-existence during job lifecycle overlap |
| `ulimit -v unlimited` in justfile | Added `ulimit -v unlimited` to test recipes | Cannot override cgroup memory limits imposed at GHA runner level; the limit is enforced by the container/VM hypervisor, not the shell | Shell `ulimit` only affects per-process soft limits within the cgroup boundary; hard cgroup limits are set by GHA infrastructure and are not overridable from within the job |
| Convert package-level imports to targeted submodule imports | Changed `from shared.core import X` to `from shared.core.tensor import X` etc. | Initial hypothesis (Crash 3 / JIT volume overflow) was wrong; 40/40 local runs passed after import changes but the root cause was per-process VmPeak, not compilation footprint | Reproducer with `ulimit -v` revealed the correct root cause; import volume was a red herring for this specific failure mode |
| Retry failed runs | Used `gh run rerun` to dismiss crashes as flake | Masks the bug without fixing it; prohibited per team policy (`feedback_no_ci_retries.md`) | Never retry to dismiss; reproduce and fix the root cause |
| Adding `continue-on-error: true` to matrix steps | Extend `continue-on-error` condition to cover crashing groups | Swallows failures silently; the actual goal is zero crashes, not ignoring them | `continue-on-error` is the wrong direction; it hides the symptom instead of fixing the cause |

## Results & Parameters

### Deterministic Local Reproducer

```bash
# Confirm threshold: fails below ~3.6 GB, passes at 4.0 GB
ulimit -v 3500000 && pixi run mojo --Werror -I . tests/any_test.mojo
# → SIGSEGV / "JIT session error: Cannot allocate memory in static TLS block"

ulimit -v 4000000 && pixi run mojo --Werror -I . tests/any_test.mojo
# → PASS
```

### GHA Runner Memory Profile

| Resource | Value |
| --------- | ------- |
| Total RAM | ~7 GB (GHA free-tier `ubuntu-latest`) |
| Mojo VmPeak per process | ~3.6 GB (modular/modular#6433) |
| Maximum concurrent `mojo` processes before OOM | 1 (any overlap causes failure) |
| `max-parallel: 1` prevents overlap? | NO — job lifecycle overlap still occurs |
| Sequential steps prevent overlap? | YES — steps within one job are serialized |

### Workflow Pattern Comparison

| Strategy | Concurrency | OOM Risk | GHA UI |
| --------- | ----------- | --------- | ------- |
| Matrix with `max-parallel: 1` | Low but non-zero (lifecycle overlap) | HIGH | One row per group |
| Matrix with no `max-parallel` | High | VERY HIGH | One row per group |
| Single job, sequential steps | Zero (guaranteed serialization) | NONE | Flat step list |

### Upstream Issue Reference

- **Issue**: [modular/modular#6433](https://github.com/modular/modular/issues/6433)
- **Description**: Mojo JIT unconditionally reserves ~3.6 GB VmPeak on startup
- **Status**: Open as of 2026-05-04
- **Expected resolution**: Mojo version upgrade that reduces startup VmPeak below 3 GB

### Files Changed in ProjectOdyssey

| File | Change |
| ------ | -------- |
| `.github/workflows/comprehensive-tests.yml` | Replaced matrix strategy with single sequential job (22 steps) |
| `justfile` | Added `-debug-level=line-tables` to mojo invocations in `_test-group-inner` recipe |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5351 — fix non-deterministic CI failures | CI run in progress as of 2026-05-04; verified-precommit |
