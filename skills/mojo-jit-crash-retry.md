---
name: mojo-jit-crash-retry
description: "Use when: (1) CI produces 'execution crashed' (libKGENCompilerRTShared.so) before any test output, (2) multiple unrelated test files crash in the same CI run on unchanged code, (3) a Mojo test file crashes deterministically at the Nth sequential call to a complex function, (4) removing retry workarounds from CI test runners to expose root causes, (5) a Copyable struct with UnsafePointer fields and no explicit __copyinit__ is stored in List, (6) tests crash non-deterministically and the code changes don't touch those test files at all, (7) creating minimal crash reproducers to file upstream issues against modular/modular, (8) required CI checks are blocked by JIT flakiness and PRs cannot auto-merge, (9) diagnosing which of THREE distinct crash types a CI failure is: bitcast UAF (resolved), fortify_fail HOME permission (CI-only UID mismatch), or JIT volume overflow (intermittent, targeted imports fix)"
category: debugging
date: 2026-04-14
version: "3.2.0"
user-invocable: false
verification: verified-precommit
history: mojo-jit-crash-retry.history
tags:
  - mojo
  - jit
  - crash
  - repro
  - ci
  - libKGENCompilerRTShared
  - upstream
  - required-checks
---
# Mojo JIT Crash Diagnosis and Upstream Reporting

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-04-10 |
| Objective | Consolidated patterns for diagnosing Mojo JIT compiler crashes, investigating root causes (double-free, broken locks, bitcast UAF), creating minimal standalone reproducers, and filing upstream issues against modular/modular. **v3.0.0 note**: retry workaround approach from v2.2.0 has been reversed — do not add retry logic; create reproducers and file upstream bugs instead. |

## Three Distinct Crash Types in Mojo 0.26.x CI

> **[v3.2.0]** Verified 2026-04-14. There are exactly THREE crash signatures in Mojo 0.26.x CI,
> each requiring a completely different fix. Misidentifying the type leads to wasted investigation.

### Crash 1 — Bitcast UAF / Heap Corruption (RESOLVED — ADR-013)

- **Stack**: `libKGENCompilerRTShared.so+0x3cb78b / +0x3c93c6 / +0x3cc397` +
  `libAsyncRTRuntimeGlobals.so+0x416ba`
- **Determinism**: 100% deterministic — same offsets every run, crashes after ~15 cumulative tests in one file
- **Trigger**: `List[Int]` struct churn + bitcast write to tensor data
- **Fix**: ADR-013 bitcast UAF fix (2026-03-20) — **fully resolved**
- **INVALID workaround** (do not apply): splitting test files to ≤10 functions (ADR-009)
  — ADR-009 was written for Crash 1, which is now resolved

### Crash 2 — `__fortify_fail_abort` / HOME Directory Permission (CI-ONLY)

- **Stack**: `libKGENCompilerRTShared.so+0x6d4ab / +0x6a686 / +0x6e157` + `libc.so.6+0x45330`
- **Determinism**: Appears non-deterministic but is actually deterministic given the same UID
  mismatch conditions
- **Trigger**: Cold pixi volumes + container UID 1001 ≠ image owner UID 1000 + no TTY (`-T` flag)
- **Deceptive symptom**: Crash appears **BEFORE any test output** — looks identical to Crash 3 on surface
- **Root cause**: Cached image built with `USER_ID=1000`; CI runs as UID 1001; `/home/dev` is mode 750
  (unwritable by UID 1001); Mojo JIT cannot write `$HOME/.modular` →
  `libAsyncRTMojoBindings.so` throws `filesystem_error` → `std::terminate` → `__fortify_fail_abort`
- **Fix**: Include UID in image cache key + HOME-fixup in `entrypoint.sh`
  (see `docker-mojo-uid-mismatch-crash-fix` skill for complete Dockerfile fix)

### Crash 3 — JIT Compilation Volume Overflow (Intermittent)

- **Stack**: Variable `libKGENCompilerRTShared.so` offsets (addresses change per run due to ASLR)
- **Determinism**: Non-deterministic — ASLR, memory layout, JIT caching vary per run
- **Trigger**: Test file has >20 functions OR uses package-level `from shared.core import` instead of
  targeted submodule imports
- **Fix**: Convert package-level imports to targeted submodule imports (reduces JIT compilation
  footprint ~95%); keep test files to ~20 or fewer functions

### Crash Diagnostic Quick-Reference Table

| Symptom | Crash Type | Action |
|---------|-----------|--------|
| `execution crashed` BEFORE any test output + fixed stack offsets `+0x6d4ab` | Crash 2 — UID mismatch | Fix UID in Docker cache key + entrypoint HOME-fixup |
| `execution crashed` BEFORE any test output + variable stack offsets | Crash 3 — volume overflow | Audit imports; convert to targeted submodule imports |
| `execution crashed` AFTER test output at ~15th test, fixed offsets `+0x3cb78b` | Crash 1 — bitcast UAF | Already resolved by ADR-013; verify bitcast fix was applied |
| Crash after test output with assertion message | Real test bug | Debug the assertion |

### ADR-009 Status: INVALID

The ADR-009 constraint ("≤10 test functions per file") was written as a workaround for Crash 1
(bitcast UAF). Crash 1 is resolved by ADR-013. Applying ADR-009 file splits to Crashes 2 or 3
does nothing — the crash triggers before the test runner even starts. Removing stale
`# ADR-009:` annotations from test files is correct cleanup, not regression.

## When to Use

- CI produces `execution crashed` with no test output before the crash (compiler flake, not test bug)
- Multiple unrelated test files crash in the same CI run — key indicator of infrastructure flakiness
- Tests pass on `main` but fail on a PR with identical content in those files
- The PR only changed a few files but whole test groups fail
- The crash is non-deterministic: same test passes/fails randomly across runs
- A Mojo test file crashes **deterministically** at the Nth sequential call (heap corruption, not JIT flake)
- The test file has >10 test functions running deep-network-scale operations
- **Removing retry logic** from `just test-group` or `scripts/test-with-retry.sh` to expose real failures
- **Creating minimal standalone reproducers** to isolate a crash category for upstream filing
- **A `Copyable` struct with `UnsafePointer` fields and no explicit `__copyinit__` is stored in `List`** — synthesized shallow copy + reallocation = double-free
- **Tests crash non-deterministically and the code changes don't touch those test files at all** — suspect double-free, broken lock, or bitcast UAF before assuming JIT flakiness

## When Required Checks Are Blocked by JIT Flakiness

> **[NEW v3.1.0]** The correct response to required CI checks failing non-deterministically
> on every main run is **RC/CA investigation and an import audit — NOT adding retry logic.**

If `Core Types & Fuzz`, `Integration Tests`, or any other required check fails
non-deterministically across multiple consecutive `main` runs on different commits, the
corrective action workflow is:

### Step 0: Confirm It Is Pre-existing on Main (Not PR-Specific)

```bash
# Compare multiple recent main runs
gh run list --branch main --workflow "Comprehensive Tests" --limit 5 \
  --json databaseId,conclusion,headSha --jq '.[]'

# For each run, check which jobs failed
gh run view <run-id> --json jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | .name'
```

If different jobs fail on different runs → non-deterministic → JIT crash, not code bug.
If the same PR-unrelated docs PR (#5219 type) fails the same jobs → confirmed pre-existing.

### Step 1: Identify the Affected Test Files

```bash
# Find which test files are in the failing required-check groups
grep -A20 '"Core Types & Fuzz"\|"Integration Tests"' \
  .github/workflows/comprehensive-tests.yml | grep "path:\|pattern:"
```

### Step 2: Audit Import Styles in Those Files

```bash
# Find package-level imports (the crash trigger)
grep -rn "^from shared\.core import\|^from shared import" \
  tests/shared/core/test_dtype* tests/shared/integration/ --include="*.mojo"
```

Convert any `from shared.core import X, Y` → targeted submodule imports per
`docs/dev/mojo-jit-crash-workaround.md`. This reduces JIT compilation footprint by ~95%
per file and lowers crash probability without hiding failures via retry.

### Step 3: Write the RC/CA ADR

Write a root-cause / corrective-action ADR (`docs/adr/ADR-NNN-...md`) documenting:

- **Evidence table**: which runs failed, which jobs, non-deterministic pattern
- **Root cause**: JIT compilation volume overflow in `libKGENCompilerRTShared.so`
- **Corrective actions** (ordered by impact, not ease):
  1. `[HIGH]` Import audit on affected test groups (see Step 2)
  2. `[MEDIUM]` File/update upstream issue against modular/modular with crash repro
  3. `[LOW]` Temporarily move affected checks from required to advisory IF crash rate
     does not improve after actions 1+2 (document the decision explicitly)
- **What NOT to do**: Do not increase `TEST_WITH_RETRY_MAX`; do not add retry logic.
  Retry hides failures and prevents meaningful upstream bug reports.

See `docs/adr/template.md` for the ADR format. Follow ADR-014 style (which documents
the retry approach — now marked SUPERSEDED — as a reference for what not to repeat).

### Step 4: PR the Import Fixes, Not a Retry Wrapper

```bash
git checkout -b fix/audit-required-check-imports
# Edit test files to use targeted imports
git commit -m "fix(tests): convert package-level imports in required-check groups

Addresses non-deterministic JIT crash in Core Types & Fuzz and Integration Tests.
See docs/adr/ADR-015-flaky-required-checks-jit-crash.md"
gh pr create --title "fix(tests): audit imports in required-check test groups" \
  --body "Closes #<issue>"
```

## CRITICAL: Execution Crashes ARE Real Bugs — Investigate First

> **Before assuming JIT flakiness, look for these three verified root causes.**
> All three were found in ProjectOdyssey PR #5197–5204 and each manifested as
> non-deterministic "execution crashed" output — indistinguishable from JIT flakiness
> on the surface. The non-determinism was explained by timing/allocation-layout variation,
> not compiler non-determinism.

### Root Cause 1: Synthesized Shallow Copy + List Reallocation = Double-Free

**Pattern**: A struct marked `Copyable` (or deriving it implicitly) has `UnsafePointer` fields
but no explicit `__copyinit__`. When stored in a `List[T]` that reallocates, Mojo synthesizes
a shallow `__copyinit__`, duplicating the pointer. Both copies call `__del__` → double-free →
crash.

**Diagnosis**:
```bash
# Find structs with UnsafePointer but no explicit __copyinit__
grep -rn "UnsafePointer" shared/ --include="*.mojo" -l
# Then for each file, check if __copyinit__ is defined
grep -n "__copyinit__\|UnsafePointer\|Copyable" shared/core/spinlock.mojo
```

**Fix**: Implement an explicit `__copyinit__` that deep-copies the heap allocation, OR remove
`Copyable` conformance if copying is not semantically meaningful.

### Root Cause 2: Incorrect Lock Implementation (fetch_add/fetch_sub ≠ Mutex)

**Pattern**: A `SpinLock.lock()` implemented using `fetch_add` to "claim" the lock and
`fetch_sub` to release it. This is NOT a correct mutex — `fetch_add` returns the previous
value and completes atomically, but two threads can both see `0` and both proceed into the
critical section if the add and the conditional branch are not atomic together.

**Diagnosis**: Read `lock()` implementation. A correct spinlock uses compare-exchange
(CAS / `compare_exchange_weak`) to atomically check-and-set, not fetch-add.

**Fix**:
```mojo
fn lock(mut self):
    while True:
        var expected: Int32 = 0
        if self._state.compare_exchange_weak[memory_order.acquire, memory_order.relaxed](
            expected, 1
        ):
            return
        # Spin until unlocked
        while self._state.load[memory_order.relaxed]() != 0:
            pass

fn unlock(mut self):
    self._state.store[memory_order.release](0)
```

### Root Cause 3: Bitcast UAF — Alias Survives ASAP Destruction

**Pattern**: Writing to tensor data via `tensor._data.bitcast[T]()[i] = val`. The `bitcast`
creates a pointer alias. Mojo's ASAP (As Soon As Possible) destruction may destroy `tensor`
before all writes through the bitcast pointer complete, leaving a dangling write.

**Affected pattern** (seen in 1,062 locations across 50 test files):
```mojo
# UNSAFE — bitcast alias may dangle after ASAP destruction of tensor
grad_output._data.bitcast[Float32]()[i] = val
```

**Safe replacement**:
```mojo
# SAFE — direct UnsafePointer with explicit lifetime
var ptr = grad_output.data_ptr()  # or equivalent safe accessor
ptr[i] = val
```

**Scale**: 1,062 bitcast writes fixed across 50 files in ProjectOdyssey using a
5-agent Myrmidon swarm with non-overlapping file assignments in parallel PRs (#5200–#5204).

## Mojo Language Semantics Reference

> These facts are verified from docs.modular.com/mojo/manual — use them when diagnosing
> suspected UAF or double-free in function parameters or struct lifecycle.

| Fact | Details |
|------|---------|
| **Default argument convention is `read`** | `fn foo(x: AnyTensor)` does NOT copy `x`. The default is an immutable borrow (reference). Only `owned` convention causes a copy/move. |
| **`deinit` in `__moveinit__` suppresses destructor on source** | `fn __moveinit__(out self, deinit existing: Self)` — Mojo does NOT call `__del__` on `existing` after the function. This is correct move semantics. Source is consumed, not destroyed separately. |
| **ASAP destruction** | Mojo destroys values as soon as their last use is seen — potentially before end-of-scope. Pointer aliases (bitcast, raw UnsafePointer) may dangle if the owning value is destroyed early. |
| **Synthesized `__copyinit__`** | If a struct is `Copyable` but defines no `__copyinit__`, Mojo synthesizes a field-by-field copy. For `UnsafePointer` fields this is a shallow copy — the pointer value is copied, not the heap data. |

## Diagnosis Methodology (What Worked)

1. **Compare same tests on previous successful `main` runs vs failing run** — if pass/fail is
   non-deterministic across runs with no code change, the non-determinism has a cause.
   It is NOT safe to assume "JIT flake" without investigating.

2. **Look for ALL possible causes, not just the most recent change** — the bitcast UAF existed
   long before the PR that exposed it; the PR changed allocation layout, making the race
   observable.

3. **Read struct declarations**: `Copyable` + `UnsafePointer` + no explicit `__copyinit__` =
   double-free risk under any `List` reallocation.

4. **Check for `_data.bitcast[T]()[i] = val` pattern** in test files → known UAF pattern.

5. **Check for incorrect lock implementations**: `fetch_add`/`fetch_sub` in `lock()`/`unlock()`
   is not a mutex — look for compare-exchange instead.

6. **Verify semantics from official docs** before concluding a bug: check if argument
   convention, destructor behavior, or copy semantics match expectations.

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

**Remove retry wrapper and run direct**:

```bash
# In justfile _test-group-inner and _test-mojo-inner:
pixi run mojo --Werror -I "$REPO_ROOT" -I . "$test_file"
# Delete scripts/test-with-retry.sh and mark ADR-014 SUPERSEDED
```

**Create minimal reproducer** (see `repro/` workflow below):

```bash
mkdir -p repro/issues
# Write repro_crash_standalone.mojo with minimal trigger
pixi run mojo repro/repro_crash_standalone.mojo   # confirm crash
# Fill out issue template following modular/modular#6187 format
```

### Step 1: Distinguish JIT Flake from Real Test Bug

**Diagnosis by output position** — the single most reliable heuristic:

| Symptom | Cause |
|---------|-------|
| `execution crashed` before any test output | Possibly compiler flake — but first check root causes above |
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

### Step 3: Remove Retry Logic — Direct Test Execution

**Do not add retry logic.** Replace any retry wrapper with direct test execution:

```bash
# In justfile _test-group-inner and _test-mojo-inner
# BEFORE (v2.2.0 pattern — do not use):
#   bash "$REPO_ROOT/scripts/test-with-retry.sh" "$test_file"
# AFTER (v3.0.0 — correct approach):
pixi run mojo --Werror -I "$REPO_ROOT" -I . "$test_file"
```

**Why**: Retry logic masks real failures. A crash that is retried away cannot be reliably
reproduced for an upstream bug report. Non-reproducible crashes cannot be filed with
confidence against modular/modular. Prefer visible failures that drive investigation.

**Cleanup checklist when removing retry**:

1. Delete `scripts/test-with-retry.sh`
2. Delete `tests/smoke/test_retry_script.py`
3. Update justfile recipes to use direct `pixi run mojo --Werror -I "$REPO_ROOT" -I . "$test_file"`
4. Mark any retry-justifying ADR (e.g. ADR-014) as SUPERSEDED

### Step 4: Create Minimal Reproducers and File Upstream

When a crash category is confirmed, extract the minimal trigger into `repro/`:

```bash
mkdir -p repro/issues
```

**Reproducer file** (`repro/repro_crash_<category>.mojo`): smallest possible Mojo program
that reproduces the crash — no test framework imports, no project imports, standalone.

```mojo
# repro_crash_standalone.mojo — Category 1: ASAP Destruction + Bitcast UAF
# Mojo version: 0.26.1  OS: Ubuntu 22.04  CPU-only (no GPU)
# Run: pixi run mojo repro_crash_standalone.mojo
# Expected: crash with libKGENCompilerRTShared.so in stack
# Filed: modular/modular#6187

from memory import UnsafePointer

struct Tensor:
    var _data: UnsafePointer[Float32]
    var _size: Int

    fn __init__(out self, size: Int):
        self._size = size
        self._data = UnsafePointer[Float32].alloc(size)

    fn __del__(owned self):
        self._data.free()

fn trigger_uaf() -> Float32:
    var t = Tensor(4)
    # bitcast alias — ASAP destruction of t may fire before write completes
    t._data.bitcast[Float32]()[0] = 1.0
    return t._data[0]

fn main():
    print(trigger_uaf())
```

**Issue template** (`repro/issues/<category>.md`) following modular/modular#6187 format:

```markdown
## Environment

- Mojo version: 0.26.1
- OS: Ubuntu 22.04 LTS
- Hardware: CPU-only
- Reproduced: [yes/no — always confirm before filing]

## Description

[One-paragraph plain-language description of the crash]

## Crash Signature

[Stack trace or `execution crashed` output — redact any project-specific paths]

## Minimal Reproducer

[Paste full content of repro_crash_<category>.mojo]

## Steps to Reproduce

1. Save above as `repro.mojo`
2. Run: `mojo repro.mojo`
3. Observe crash

## Expected Behavior

[What should happen]

## Actual Behavior

[What actually happens — crash, exit code, etc.]

## Relationship to Known Issues

[Cross-reference other filed issues if applicable]
```

**Known crash categories** (from ProjectOdyssey PR #5212):

| Category | File | Issue |
|----------|------|-------|
| ASAP Destruction + Bitcast UAF | `repro/repro_crash_standalone.mojo` | modular/modular#6187 |
| JIT Compilation Volume Crash | `repro/repro_jit_volume_crash.mojo` | `repro/issues/jit-compilation-volume-crash.md` |
| ASAN + Python FFI dlsym Conflict | — | `repro/issues/asan-dlsym-abort.md` |

### Step 5: Split Test Files for Deterministic Heap Corruption

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

### Step 6: Document the Crash (when creating a dev doc)

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

## When to Remove Retry Logic

Remove retry wrappers from CI test runners when ANY of the following are true:

1. **Crashes are being investigated** — retry masks the reproduction rate and makes
   root cause investigation harder. Fail fast, then diagnose.
2. **A retry script exists** (`scripts/test-with-retry.sh` or equivalent) — these are
   workarounds, not solutions. Delete them.
3. **An ADR exists that justifies retry** (e.g. ADR-014) — mark it SUPERSEDED and remove
   the machinery it justified.
4. **You want to file an upstream issue** — you cannot confidently file a bug report for a
   crash that only manifests after a retry. Make it fail deterministically first.

**Correct replacement**:

```bash
# Direct execution — fails visibly, enabling root cause investigation
pixi run mojo --Werror -I "$REPO_ROOT" -I . "$test_file"
```

**Note on `SKIP=mojo-format`**: When `mblack` has a broken `click.core` dependency
(ImportError at pre-commit time), use `SKIP=mojo-format` to skip only that hook — not
`--no-verify`. Document the skip reason in the commit message. This follows the CONTRIBUTING.md
pattern for hook exceptions. Never use `--no-verify`.

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
| **Assume crash = JIT flake** | Closed/retried without investigating root cause | 16 test files crashing had 3 concrete source-code bugs: double-free, broken lock, bitcast UAF | **Check for double-free, broken locks, and bitcast UAF first before concluding JIT instability** |
| **Add retry logic to CI** | Implemented `scripts/test-with-retry.sh` (88 lines) with `MAX_RETRIES=1` on `execution crashed` | Retry scripts hide real failures: a crash that is retried away cannot be filed upstream, prevents root cause investigation, masks reproducibility | **Delete retry scripts; use direct `pixi run mojo --Werror`; create minimal reproducers and file upstream** |
| **Re-add retry when required checks block PRs** | When required checks (`Core Types & Fuzz`, `Integration Tests`) fail non-deterministically on every main run, temptation is to increase `TEST_WITH_RETRY_MAX` from 1 to 2 to absorb double-crash scenarios | Retry absorbs symptoms, not the cause; same crash will recur post-Mojo-upgrade; upstream can't reproduce the issue; RC/CA ADR cannot be written for a masked failure | **Do the import audit (targeted submodule imports) and write the RC/CA ADR instead. Retry is always the wrong answer.** |

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

### Upstream Issue Template Format (modular/modular#6187 structure)

When filing crash reports against modular/modular, use this structure:

| Section | Content |
|---------|---------|
| **Environment** | Mojo version, OS, hardware (CPU-only/GPU), reproduction status |
| **Description** | One-paragraph plain-language explanation |
| **Crash Signature** | Stack trace with `libKGENCompilerRTShared.so` offsets (redact project paths) |
| **Minimal Reproducer** | Full content of standalone `.mojo` file, no external imports |
| **Steps to Reproduce** | Numbered steps: save file, run command, observe crash |
| **Expected Behavior** | What should happen |
| **Actual Behavior** | What actually happens (crash, exit code, signal) |
| **Relationship** | Cross-reference other filed issues if applicable |

**Key principles for reproducers**:

- No project-specific imports — standalone, copy-paste-and-run
- Minimal lines of code — strip everything that does not contribute to the crash
- Include Mojo version and OS in a comment at the top of the file
- Confirm the reproducer crashes before filing — run it 3 times

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
