---
name: mojo-jit-crash-retry
description: "Use when: (1) CI produces 'execution crashed' (libKGENCompilerRTShared.so) before any test output, (2) multiple unrelated test files crash in the same CI run on unchanged code, (3) a Mojo test file crashes deterministically at the Nth sequential call to a complex function, (4) removing retry workarounds from CI test runners to expose root causes, (5) a Copyable struct with UnsafePointer fields and no explicit __copyinit__ is stored in List, (6) tests crash non-deterministically and the code changes don't touch those test files at all, (7) creating minimal crash reproducers to file upstream issues against modular/modular, (8) required CI checks are blocked by JIT flakiness and PRs cannot auto-merge, (9) diagnosing which of THREE distinct crash types a CI failure is: bitcast UAF (resolved), fortify_fail HOME permission (CI-only UID mismatch), or JIT volume overflow (intermittent, targeted imports fix), (10) considering @always_inline to fix bitcast crashes (ANTI-PATTERN: worsens crashes), (11) ASAP destruction crash in finite-difference perturbation loops after test output prints, (12) codebase-wide swarm elimination of bitcast UAF writes across 50+ files, (13) KGEN internal buffer overflow with fixed crash address +0x6d4ab from 4-condition trigger combination, (14) shared library modules carry heavy module-level imports that cause JIT volume overflow for all their importers, (15) splitting oversized Mojo test files per ADR-009 (<=10 functions), (16) fn main deprecation parse errors after file splitting in Mojo 0.26.3+"
category: debugging
date: 2026-04-14
version: "3.9.0"
user-invocable: false
verification: verified-precommit
history: mojo-jit-crash-retry.history
absorbed:
  - investigate-mojo-heap-corruption (ADR-009 test splitting, heap threshold, fn main deprecation)
  - mojo-always-inline-worsens-jit-crashes (@always_inline anti-pattern guidance)
  - mojo-asap-destruction-perturbation-loop-fix (post-test-output UAF crash diagnostic)
  - mojo-bitcast-always-inline-crash-fix (codebase-wide swarm pattern, blog PR workflow)
  - mojo-copyinit-double-free (synthesized __copyinit__ shallow copy fix)
  - mojo-kgen-jit-buffer-overflow-diagnostic (4-condition KGEN trigger, upstream issue #6445)
  - mojo-library-import-audit (module-level library import audit)
tags:
  - mojo
  - jit
  - crash
  - repro
  - ci
  - libKGENCompilerRTShared
  - upstream
  - required-checks
  - always-inline
  - asap-destruction
  - bitcast
  - uaf
  - copyinit
  - double-free
  - kgen
  - swarm
  - test-splitting
  - adr-009
  - library-imports
---
# Mojo JIT Crash Diagnosis and Upstream Reporting

## Overview

| Field | Value |
| ------- | ------- |
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
| --------- | ----------- | -------- |
| `execution crashed` BEFORE any test output + fixed stack offsets `+0x6d4ab` | Crash 2 — UID mismatch | Fix UID in Docker cache key + entrypoint HOME-fixup |
| `execution crashed` BEFORE any test output + variable stack offsets | Crash 3 — volume overflow | Audit imports; convert to targeted submodule imports |
| `execution crashed` AFTER test output at ~15th test, fixed offsets `+0x3cb78b` | Crash 1 — bitcast UAF | Already resolved by ADR-013; verify bitcast fix was applied |
| Crash after test output with assertion message | Real test bug | Debug the assertion |

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
| ------ | --------- |
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
| --------- | ------- |
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
| ---------- | ------ | ------- |
| ASAP Destruction + Bitcast UAF | `repro/repro_crash_standalone.mojo` | modular/modular#6187 |
| JIT Compilation Volume Crash | `repro/repro_jit_volume_crash.mojo` | `repro/issues/jit-compilation-volume-crash.md` |
| ASAN + Python FFI dlsym Conflict | — | `repro/issues/asan-dlsym-abort.md` |

### Step 5: Document the Crash (when creating a dev doc)

For `docs/dev/mojo-jit-crash-workaround.md`, include:
- **Problem** — what `execution crashed` means and that it originates in `libKGENCompilerRTShared.so`
- **Diagnosis table** — crash before vs. after test output
- **Workaround: CI Retry Pattern** — shell retry loop + GitHub Actions `nick-fields/retry` snippet
- **Crash type comparison** — table distinguishing JIT flake (non-deterministic, retry) from heap corruption (deterministic, use ASAN to find root cause)
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
| --------- | ---------------- | --------------- | ---------------- |
| Assumed crash was caused by new test code | Investigated new backward test code for memory bugs | Unchanged files (test_layers, test_linear) were ALSO crashing | Always check if unchanged files are also failing before debugging new code |
| Removing imports to narrow the crash | Changed `loss.mojo` to avoid `activation.mojo` import | `test_loss_funcs.mojo` doesn't import activation at all but still crashed | The crash is in the JIT compiler itself, not triggered by any specific Mojo code pattern |
| Region-specific theory | Checked if specific Azure region always fails | Crashes occur on multiple regions; others pass sometimes | Azure region is not the determining factor |
| Reduce batch size | Halved batch_size from 4 to 2 in all tests | Crash still occurs — root cause is cumulative JIT memory across test calls, not per-call memory | Batch size is not the root cause; number of sequential JIT compilations is |
| Use smaller model variant | Considered using fewer channels (e.g., VGG-8) | Would change test semantics | Keep the real model, reduce the number of calls per session instead |
| Add teardown between tests | Mojo has no per-test teardown hooks in v0.26.1 | Not applicable — Mojo `main()` runs tests sequentially with shared JIT state | Fix the root cause with ASAN rather than working around it |
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
| --------- | --------- |
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

## ADR-009 Test File Splitting and fn main Deprecation

> **[Absorbed from `investigate-mojo-heap-corruption` v1.1.0, 2026-05-03]**
> Use when splitting oversized Mojo test files to resolve heap corruption crashes or when
> Mojo 0.26.3+ parse errors appear in newly split files.

### Heap Corruption Threshold

Mojo 0.26.x exhibits a heap corruption threshold at approximately **15 cumulative test
function executions** within a single JIT process session. CI-only crashes that pass locally
are characteristic because CI runs all integration tests sequentially (cumulative), while
local runs typically execute a single file.

**Trigger**: Unnecessary type conversions (e.g., `_get_float64()` on Float32 data) combined
with cumulative test executions exceeding the threshold.

```mojo
# Before fix (triggers heap corruption at 15+ cumulative tests):
var original_val = test_data._get_float64(0)      # Float32 -> Float64 (unnecessary)

# After fix (uses native type):
var original_val = test_data._get_float32(0)      # Native Float32
```

### ADR-009 Splitting Rules

When a test file has >10 functions, split it into part files:

| Rule | Detail |
| ---- | ------ |
| Max functions per file | 10 |
| Part file naming | `test_<base>_part1.mojo`, `test_<base>_part2.mojo`, ... |
| Import block | Copy FULL import block verbatim to every part file |
| main entrypoint | MUST use `def main() raises:` (not `fn main()`) for Mojo 0.26.3+ |
| CI glob | Update to `test_*_part*.mojo` |

```bash
# Count functions in a test file
grep -c "^fn test_\|^def test_" tests/path/to/test_<base>.mojo

# Phase 3: Split oversized test files (ADR-009 -- <=10 functions per file)
# Copy full import block verbatim to each part file
# Keep <=10 test functions per file
# Name parts: test_<base>_part1.mojo, test_<base>_part2.mojo, ...
```

### CRITICAL: fn main Deprecation (Mojo 0.26.3+)

After splitting, every new part file must have `def main() raises:` not `fn main() raises:`.
Mojo 0.26.3 deprecated `fn main()` and produces a parse error in CI.

```bash
# Find all new part files using fn main
find . -name "test_*_part*.mojo" -exec grep -l "fn main" {} \;

# Fix: global replace in each file
for f in $(find . -name "test_*_part*.mojo"); do
  sed -i 's/fn main() raises:/def main() raises:/g' "$f"
done

# Verify all fixed:
grep -r "fn main" tests/ --include="*.mojo" | grep "part"
# Should produce no output
```

### Mojo Version Compatibility

| Version | `fn main()` | `def main()` |
| ------- | ----------- | ------------ |
| 0.26.1 | OK | OK |
| 0.26.3 | DEPRECATED (parse error in CI) | Required |

### CI Glob Update After Splitting

```yaml
# Old pattern (misses part files):
- "tests/**/test_<base>.mojo"

# New pattern (catches all parts):
- "tests/**/test_<base>_part*.mojo"
```

**Additional Failed Attempts** (from investigate-mojo-heap-corruption):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running test file individually to reproduce crash | Used `pixi run mojo -I . tests/.../test.mojo` | Crash requires 15+ cumulative test executions (heap corruption threshold) | CI-only crashes may need cumulative reproduction — run all integration tests sequentially |
| `fn main() raises:` in new split files | All split files written with `fn main()` | Mojo 0.26.3 deprecates `fn main()`; CI failed with parse error on every new file | After any file split in Mojo 0.26.3+, globally replace `fn main() raises:` with `def main() raises:` |
| Not updating CI glob after splitting | Left CI glob as `test_<base>.mojo` | Split files named `test_<base>_part*.mojo` were not discovered by CI | Always update CI glob patterns to `test_*_part*.mojo` when splitting |
| Partial import block in part files | Only copied some imports to part files | Missing imports cause compile errors in all functions that depend on them | Copy the FULL import block verbatim to every part file when splitting |

## CRITICAL Anti-Pattern: @always_inline Worsens JIT Crashes

> **[Absorbed from `mojo-always-inline-worsens-jit-crashes` v1.0.0, 2026-03-25]**
> WARNING: Adding `@always_inline` to large branching methods DRAMATICALLY WORSENS Mojo JIT crashes.
> This is a verified anti-pattern — do not use to fix bitcast crashes.

### The Anti-Pattern

```mojo
# BAD — causes MORE crashes across ALL test groups:
@always_inline
fn _get_float64(self, index: Int) -> Float64:
    if self._dtype == DType.float16: ...
    elif self._dtype == DType.bfloat16: ...
    elif self._dtype == DType.float32: ...
    elif self._dtype == DType.float64: ...
    else: ...  # integer fallback

# GOOD — works reliably:
fn _get_float64(self, index: Int) -> Float64:
    # same body, no @always_inline
```

### Why It Fails

Inlining large branching methods (15+ line body, 5+ runtime branches) into every call site
expands the JIT compilation footprint massively — especially in gradient checking with hundreds
of calls. This increases JIT memory pressure and triggers MORE `libKGENCompilerRTShared.so`
crashes than before.

### @always_inline Safety Rules

| Method Characteristics | @always_inline Safe? |
| ---------------------- | --------------------- |
| Small body (1-3 lines), compile-time params | Yes |
| Large body (10+ lines), runtime branching | NO |
| Called in tight loops (100+ times) | Risky — test thoroughly |
| Has 5+ if/elif branches | NO |

**Key distinction**:
- `load[dtype]` / `store[dtype]` — 1 line body, compile-time dtype, safe to inline
- `_get_float64` — 15+ line body, 5+ runtime branches, unsafe to inline

### Impact Observed (ProjectOdyssey PR #5099)

| Test Group | Before @always_inline | After @always_inline |
| ------------ | ----------------------- | --------------------- |
| Models | PASSED | FAILED (ALL crash) |
| Autograd | PASSED | FAILED (4 crashes) |
| Core Utilities | PASSED | FAILED |
| Core Gradient | PASSED | FAILED |
| Core Activations | PASSED | FAILED (16/17 crash) |
| Gradient Checking | FAILED (intermittent) | FAILED |

**If CI crashes get worse after a change**, check git diff for `@always_inline` additions.

## ASAP Destruction in Perturbation Loops (Post-Test-Output UAF)

> **[Absorbed from `mojo-asap-destruction-perturbation-loop-fix` v1.0.0, 2026-03-29]**
> Use when the crash appears AFTER test output (not before) — distinguishes runtime UAF
> from JIT compilation overflow which always crashes before any output.

### Key Diagnostic: Before vs. After Test Output

| Symptom | Cause | Fix |
| --------- | ------- | ----- |
| `execution crashed` appears **before any test output** | JIT compilation buffer overflow — reduce imports | Crash 3 / library import audit in this skill |
| `execution crashed` appears **after test output** | Runtime memory bug — ASAP destruction UAF | This section |
| Crash after "Running X tests..." + warning lines | UAF during perturbation loop | This section |
| Crash after specific assertion failure message | Real test logic bug | Debug the backward pass |

### The Root Cause

Mojo 0.26.1 applies **ASAP (As Soon As Possible) destruction** to local variables. When
`forward_fn(x)` returns a temporary `AnyTensor`, the compiler may destroy it as soon as it
appears "used" — but `tensor.numel()` in `range(output_plus.numel())` is the last apparent
structural use, not the element reads in the loop body. Each subsequent `_get_float64(j)`
call reads through a dangling pointer → heap corruption → `__fortify_fail_abort`.

The crash is **non-deterministic** because ASLR changes memory layout between runs —
sometimes the freed region is re-used quickly (crash), sometimes not (pass).

### Fix: Acquire data_ptr Before the Loop

```mojo
# BEFORE (DANGEROUS — ASAP destruction UAF):
var output_plus = forward_fn(input_copy_plus)
var output_minus = forward_fn(input_copy_minus)
for j in range(output_plus.numel()):
    var diff = output_plus._get_float64(j) - output_minus._get_float64(j)
    ...

# AFTER (SAFE — data_ptr derivation keeps tensors alive):
var output_plus = forward_fn(input_copy_plus)
var output_minus = forward_fn(input_copy_minus)
# Acquire typed pointers BEFORE the loop. Deriving data_ptr keeps the
# tensor alive for the pointer's scope (modular/modular#6187).
var out_plus_ptr = output_plus.data_ptr[dtype]()
var out_minus_ptr = output_minus.data_ptr[dtype]()
for j in range(output_plus.numel()):
    var diff = Float64(out_plus_ptr[j]) - Float64(out_minus_ptr[j])
    ...
```

The fix only works inside dtype-dispatched functions (those with `[dtype: DType]` parameter).

### Audit grep for Perturbation Loop UAF

```bash
# Find all _get_float64/_set_float64 calls on temporaries in loop bodies
grep -n "_get_float64\|_set_float64" shared/testing/gradient_checker.mojo

# Pattern to look for (DANGEROUS — temporary tensor in loop):
# var output_plus = forward_fn(input_copy_plus)
# for j in range(output_plus.numel()):
#     var diff = output_plus._get_float64(j) ...  ← UAF risk
```

### Two Crash Populations With Identical Stack Traces

```text
Both crashes: libKGENCompilerRTShared.so+0x3cb78b → libc __fortify_fail_abort
Both crashes: same 4-frame stack trace

Population A (JIT buffer overflow):
  - Crash BEFORE any test output
  - Fix: targeted submodule imports (reduce compilation footprint)
  - Trigger: from shared.core import forces 37K+ line compilation

Population B (ASAP destruction UAF):
  - Crash AFTER test output (some tests ran successfully)
  - Fix: data_ptr[dtype]() before inner loop
  - Trigger: _get_float64 per-element bitcast on temporary from forward_fn
```

### ASAN Diagnostic Output

```text
ERROR: AddressSanitizer: heap-use-after-free on address 0x... at pc ...
READ of size 4 at 0x... thread T0
    #0 in AnyTensor::_get_float64(int)
    #1 in _check_gradients_perturb[...]
    ...
freed by thread T0 here:
    #0 in operator delete(void*)
    #1 in AnyTensor::__del__()
```

Add ASAN coverage to prevent regression:

```yaml
# .github/workflows/asan-tests.yml
- name: Run gradient checking tests under ASAN
  run: |
    just test-group-asan "tests/shared/core" "test_gradient_checking_basic.mojo test_gradient_checking_dtype.mojo"
```

## Codebase-Wide Bitcast UAF Swarm Elimination

> **[Absorbed from `mojo-bitcast-always-inline-crash-fix` v2.0.0, 2026-03-27]**
> Use when grep returns 50+ files with UAF write patterns — swarm elimination workflow
> with parallel agents and blog PR workflow.

### The Three-Ingredient UAF Crash Formula

The Mojo bitcast UAF requires ALL three:

1. **Heavy alloc/free churn** — 2+ conv2d+relu in a function
2. **`UnsafePointer.bitcast` WRITE** — `tensor._data.bitcast[T]()[i] = val`
3. **`List[Int]`-containing struct** — shape fields as `List[Int]` with temp construction

Missing any one = no crash.

### Discovery: Finding All Instances

```bash
# Find all bitcast write patterns (indexed form)
grep -rn "\._data\.bitcast\[.*\]()\[.*\] *=" . --include="*.mojo"

# Find variant: empty-index dereference write
grep -rn "\._data\.bitcast\[.*\]()[] *=" . --include="*.mojo"

# Combined count (sorted by file)
grep -rc "\._data\.bitcast\[.*\]()" . --include="*.mojo" | grep -v ":0" | sort -t: -k2 -rn
```

### Safe Replacement API

Replace `tensor._data.bitcast[T]()[i] = val` with:

```mojo
tensor.set(i, T(val))
```

**Signature cascade requirements**: The `mut self` and `raises` on `set()` propagate outward:

```mojo
# BEFORE
fn fill_tensor(tensor: AnyTensor):

# AFTER
fn fill_tensor(mut tensor: AnyTensor) raises:
```

**Avoid double-wrapping**:
```mojo
# WRONG — double-wrap
tensor.set(i, Float32(Float32(x)))
# CORRECT
tensor.set(i, Float32(x))
```

Use Python regex (not sed) for batch replacements.

### Swarm Partition Workflow (5 Parallel Agents)

```bash
# Get file list sorted by line count (spread large files evenly)
grep -rl "\._data\.bitcast\[.*\]()" . --include="*.mojo" | \
  xargs wc -l 2>/dev/null | sort -rn | grep -v total > /tmp/bitcast_files.txt

# Split into N batches — assign files round-robin by line count
# Critical constraint: no file in more than one batch (causes merge conflicts)
```

For each batch (agent 1–5 in parallel):

```bash
# 1. Create isolated worktree
git worktree add worktrees/fix-bitcast-batch-N -b fix/bitcast-writes-batch-N

# 2. Apply replacements via Python script
python3 scripts/fix_bitcast_writes.py --files batch_N_files.txt

# 3. Verify: no bitcast writes remain in assigned files
grep -n "\._data\.bitcast\[.*\]()\[.*\] *=" <assigned-files>

# 4. Add mut/raises to helper functions as needed
# 5. Run pre-commit on changed files
pixi run pre-commit run --files <changed-files>

# 6. Commit and push
git commit -m "fix(tensor): replace bitcast writes with safe set() in batch N"
git push -u origin fix/bitcast-writes-batch-N

# 7. Create PR with auto-merge
gh pr create --title "fix(tensor): eliminate bitcast UAF writes batch N/5" \
  --body "Replaces tensor._data.bitcast[T]()[i]=val with tensor.set(i,T(val)).
Batch N of 5: <list files>"
gh pr merge --auto --rebase
```

PRs can merge in any order — non-overlapping files prevent rebase conflicts.

### Python Regex Replacement Script

```python
#!/usr/bin/env python3
"""Replace tensor._data.bitcast[T]()[i] = val with tensor.set(i, T(val))."""
import re
import sys
from pathlib import Path

BITCAST_INDEXED = re.compile(
    r'(\w+)\._data\.bitcast\[(\w+)\]\(\)\[([^\]]+)\]\s*=\s*(.+)'
)

def fix_line(line: str) -> str:
    m = BITCAST_INDEXED.match(line.strip())
    if not m:
        return line
    tensor, typ, idx, rhs = m.groups()
    rhs = rhs.rstrip()
    if rhs.startswith(f"{typ}(") and rhs.endswith(")"):
        wrapped = rhs
    else:
        wrapped = f"{typ}({rhs})"
    indent = len(line) - len(line.lstrip())
    return " " * indent + f"{tensor}.set({idx}, {wrapped})\n"

for path in sys.argv[1:]:
    p = Path(path)
    lines = p.read_text().splitlines(keepends=True)
    new_lines = [fix_line(l) for l in lines]
    p.write_text("".join(new_lines))
    print(f"Fixed: {path}")
```

### Blog PR on Separate Branch (While Fix Branch is Active)

```bash
# 1. Stash current work on fix branch
git stash --include-untracked

# 2. Create blog branch off main
git switch -c blog/day-53-investigation main

# 3. Copy artifacts from fix branch (not stash)
git show fix-branch:path/to/file > path/to/file

# 4. Force-add gitignored test files
git add -f path/to/test_*.mojo

# 5. Commit, push, create PR with auto-merge
git push -u origin blog/day-53-investigation
gh pr create --title "docs: ..." --body "..."
gh pr merge --auto --rebase

# 6. Switch back and unstash
git switch fix-branch
git stash pop
```

### Renaming test_* Artifacts to Avoid CI Hooks

The `validate-test-coverage` hook triggers on `test_*.mojo`. For blog/debug artifacts:

```bash
# Rename test_*.mojo → bug_repro_*.mojo.bug
git mv artifacts/test_lenet5_monolithic.mojo artifacts/bug_repro_lenet5_monolithic.mojo.bug
```

### .gitignore Subdirectory Over-Matching Fix

```bash
# BEFORE: matches ANY directory named datasets/ anywhere
datasets/

# AFTER: matches ONLY top-level datasets/
/datasets/
```

Verify: `git check-ignore -v shared/data/datasets/cifar10.mojo` should return nothing.

### Swarm Elimination Results

| Parameter | Value |
| ----------- | ------- |
| Files affected | ~50 `.mojo` files (including `DISABLED_*.mojo`) |
| Total instances | ~1,062 writes |
| Agents / PRs | 5 parallel |
| Time to complete | ~2 hours |
| Verification | `verified-precommit` |
| Grep pattern | `\._data\.bitcast\[.*\]()\[.*\] *=` |
| Safe replacement | `tensor.set(i, T(val))` |

### Post-Swarm Verification

```bash
# After all PRs merge — confirm no bitcast writes remain
grep -rn "\._data\.bitcast\[.*\]()\[.*\] *=" . --include="*.mojo"
# Expected: no output
```

## Synthesized __copyinit__ Double-Free Fix

> **[Absorbed from `mojo-copyinit-double-free` v1.0.0, 2026-04-07]**
> Use when a Copyable struct with UnsafePointer fields has no explicit __copyinit__
> and is stored in a List — synthesized shallow copy causes double-free on reallocation.

### How the Bug Arises

From [docs.modular.com/mojo/manual](https://docs.modular.com/mojo/manual):

> "If you don't define `__copyinit__`, Mojo synthesizes one that simply copies each field."

For an `UnsafePointer` field, "copies each field" means copying the **pointer value** — not
the heap data. `List[T].append()` reallocates (capacity: 0→1→2→4→8→…), copying elements
via `__copyinit__` then destroying old copies via `__del__`. Shallow copies share the same
heap allocation → both `__del__` calls `free()` on the same address → **double-free**.

The crash is non-deterministic because it depends on `List` reallocation timing.

### Detection

```bash
# Find candidate structs: Copyable with UnsafePointer, no explicit __copyinit__
for f in $(grep -rl "Copyable" . --include="*.mojo"); do
    if grep -q "UnsafePointer" "$f" && ! grep -q "__copyinit__" "$f"; then
        echo "CANDIDATE: $f"
    fi
done
```

### Fix: Explicit __copyinit__ and __moveinit__

```mojo
fn __copyinit__(out self, existing: Self):
    self._state = alloc[UInt8](8)
    memcpy(self._state, existing._state, 8)

fn __moveinit__(out self, deinit existing: Self):
    self._state = existing._state
    # existing._state is NOT freed — deinit keyword suppresses its __del__

fn __del__(owned self):
    self._state.free()  # called exactly once — on the current owner
```

**Always pair `__copyinit__` with `__moveinit__`**: Without explicit `__moveinit__`, Mojo
synthesizes a shallow move; the source destructor still runs and frees the now-shared pointer.

### Reproducer Test Pattern

```mojo
fn test_list_realloc() raises:
    var locks = List[SpinLock]()
    for _ in range(5):          # forces 0→1→2→4 realloc sequence
        locks.append(SpinLock())
    locks[0].lock()             # crash here if double-free occurred
    locks[0].unlock()
```

**Additional Failed Attempt** (from mojo-copyinit-double-free):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Add only `__copyinit__`, not `__moveinit__` | Added deep-copy `__copyinit__` but omitted `__moveinit__` | Without explicit `__moveinit__`, Mojo synthesizes a shallow move — source destructor still runs and frees the now-shared pointer | Always pair `__copyinit__` with `__moveinit__` (using `deinit` parameter) when a struct owns heap memory |

## KGEN JIT Buffer Overflow — 4-Condition Trigger (Upstream #6445)

> **[Absorbed from `mojo-kgen-jit-buffer-overflow-diagnostic` v1.0.0, 2026-04-22]**
> Warning — verified-precommit: upstream issue filed (modular/modular#6445). CI fix pending.
> Use when crash address is FIXED `+0x6d4ab` on every run (not ASLR-variable).

### How This Differs from Crash 2 and Crash 3

| Indicator | KGEN Buffer Overflow (this section) | Crash 2: UID Mismatch | Crash 3: JIT Volume |
| ----------- | ------------------------------------- | ----------------------- | --------------------- |
| Crash address | Fixed: `+0x6d4ab` every run | Fixed: `+0x6d4ab` or `+0x6a686` | Variable (ASLR) |
| Determinism | 100% — fails every run | Deterministic given same UID | Non-deterministic |
| `ulimit -v unlimited` | No effect | No effect | No effect |
| `max-parallel: 1` | No effect | May reduce | Reduces (but doesn't fix) |
| Fix | Remove trigger pattern / await Modular fix | Fix UID in Docker cache key + entrypoint HOME-fixup | Targeted submodule imports |

### The 4-Condition Trigger Combination

All four conditions must be present in the same compilation unit:

1. **CPython interop**: `from std.python import Python, PythonObject` at module level
2. **`List[String]` field**: A struct that has `var <name>: List[String]`
3. **6+ overloaded `__init__`**: The same struct has six or more `def __init__(out self, ...)`
4. **`Dict[String, <that struct>]`**: The struct is used as a `Dict` value type

Removing **any one** of the four stops the crash.

### Quick Confirmation Diagnostic

```bash
# Step 1: Confirm 100% determinism (run 3 times — same offset every run = this pattern)
for i in 1 2 3; do
  echo "=== Run $i ==="; pixi run mojo run <crashing_file>.mojo 2>&1 | grep -E "fortify|0x[0-9a-f]+"
done

# Step 2: Check for the trigger combination
FILE=<your_file>.mojo
echo "Python: $(grep -c 'from std.python import' $FILE)"
echo "List[String]: $(grep -c 'List\[String\]' $FILE)"
echo "init overloads: $(grep -c 'def __init__(out self' $FILE)"   # needs >= 6
echo "Dict[String: $(grep -c 'Dict\[String,' $FILE)"
```

**Key diagnostic**: If `print("If you see this...")` at the start of `main()` never prints
before the crash, the crash fires at JIT compilation time — confirmed KGEN internal overflow.

### Minimal Reproducer (stdlib-only)

```mojo
# Reproducer for KGEN JIT buffer overflow
# Mojo 0.26.3, Ubuntu (GitHub Actions runner)
# Filed: modular/modular#6445
from std.python import Python, PythonObject
struct Value(Copyable, Movable):
    var list_val: List[String]
    def __init__(out self, v: Int): self.list_val = List[String]()
    def __init__(out self, v: Float64): self.list_val = List[String]()
    def __init__(out self, v: String): self.list_val = List[String]()
    def __init__(out self, v: Bool): self.list_val = List[String]()
    def __init__(out self, var v: List[String]): self.list_val = v^
    def __init__(out self, v: List[Int]): self.list_val = List[String]()
struct Container(Copyable, Movable):
    var data: Dict[String, Value]
    def __init__(out self): self.data = Dict[String, Value]()
def main() raises:
    print("If you see this, the KGEN crash did NOT occur.")
    var c = Container()
    print("Success")
```

### Workaround Options

| Option | Trade-off |
| ------- | ---------- |
| Move Python interop to a separate compilation unit | Requires restructuring; most correct |
| Reduce `__init__` overloads from 6 to 5 | Needs bisection; reduces API convenience |
| Replace `List[String]` field with delimited `String` | Ugly but removes the heap field trigger |
| Mark CI job advisory + track upstream issue | Temporary until modular/modular#6445 resolves |

- **Upstream issue**: [modular/modular#6445](https://github.com/modular/modular/issues/6445) — filed 2026-04-22

**Additional Failed Attempts** (from mojo-kgen-jit-buffer-overflow-diagnostic):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `ulimit -v unlimited` | Set virtual memory limit to unlimited in CI runner | No effect — KGEN internal buffer is not a virtual memory allocation | `ulimit` only affects process virtual address space limits, not KGEN's fixed-size internal codegen buffers |
| `max-parallel: 1` in GitHub Actions | Reduce concurrent compilation load | Reduces load but single-file overflow still crashes the single job | Overflow is triggered by one file's complexity, not aggregate CI parallelism |
| Treat as random JIT noise and rerun | Assumed non-deterministic; re-triggered CI | Crash occurred 100% of the time — NOT random flake | 100% determinism is the distinguishing signal — stop retrying and start bisecting |
| Diagnose as UID mismatch (Crash 2) | Checked Docker image UID, entrypoint HOME-fixup | UID fix already applied; same crash address `+0x6d4ab` seen for Crash 2 as well | Same crash address can come from different root causes; check the trigger combination |

## Library Module Import Audit (Shared Modules, Not Test Files)

> **[Absorbed from `mojo-library-import-audit` v1.0.0, 2026-04-20]**
> Companion to Crash 3 (JIT Volume Overflow). Use when test-file import audit was already done
> but crashes persist in multiple CI groups that share a common library module.

### When This Applies (vs. Test-File Audit)

The `mojo-jit-crash-retry` Crash 3 fix converts test files from `from shared.core import` to
targeted submodule imports. This section covers the complementary case: **shared library
modules themselves** carry heavy module-level imports that apply to ALL their importers.

Apply both in sequence:
1. First: convert test files to targeted imports (Crash 3 in this skill)
2. Then: audit those targeted submodule files for their own module-level imports

### Crash Diagnostic Rule for Library-Level Overflow

```text
"Running: test_X.mojo"  → crash with NO test output  →  import explosion at MODULE LOAD time
"Running test_X tests..." → crash                     →  runtime or accumulation issue
```

The first pattern means JIT is overwhelmed **before the first test function executes** —
the module import graph (test file + all transitively-imported library modules) exceeds the
JIT compilation budget.

### Audit Workflow

```bash
# Step 1: Identify which library modules the crashing test groups import
grep -rn "^from shared\." tests/shared/core/test_gradient* \
  tests/shared/integration/ tests/shared/data/ --include="*.mojo" | head -40

# Step 2: Scan those library modules for heavy module-level imports
for mod in shared/core/reduction.mojo shared/core/conv.mojo \
    shared/core/pooling.mojo shared/core/matrix.mojo \
    shared/core/loss_utils.mojo shared/data/datasets/cifar10.mojo; do
  echo "=== $mod ==="
  grep -n "^from \.\|^import " "$mod" | head -20
done

# Step 3: Check module sizes to quantify the cost
wc -l shared/core/shape.mojo shared/core/elementwise.mojo \
  shared/core/dtype_dispatch.mojo shared/core/*.mojo | sort -rn | head -20

# Step 4: Check for unused module-level imports in test files
# (imports that appear only in comments, never in executable code)
SYMBOL="reduce_sum"
FILE="tests/shared/core/test_gradient_checking_batch_norm.mojo"
grep -n "\b$SYMBOL\b" "$FILE"  # If only the import line, it's unused
```

### Fix: Move Heavy Imports into Per-Function Bodies

```mojo
# BEFORE (module level — compiled for ALL importers):
from .shape import as_contiguous

fn my_func(tensor: AnyTensor) -> AnyTensor:
    return as_contiguous(tensor)

# AFTER (per-function — compiled lazily only when function is called):
fn my_func(tensor: AnyTensor) -> AnyTensor:
    from .shape import as_contiguous  # LOCAL import — lazy compilation
    return as_contiguous(tensor)
```

### Module Heaviness Reference

| Module | Lines | Impact | Notes |
| -------- | ------- | -------- | ------- |
| `shared/core/shape.mojo` | 1371 | HIGH — pulled in by 5+ library modules | Most common transitive culprit |
| `shared/core/elementwise.mojo` | 1650 | HIGH — pulled in by loss_utils at module level | Fixed by localizing in loss_utils |
| `shared/core/dtype_dispatch.mojo` | 1520 | CRITICAL — 176+ monomorphizations | Heaviest; never import at module level |

### Lines Saved Per Library Module Fix

| Module Fixed | Heavy Import Removed | Lines Eliminated Per Importer |
| -------------- | --------------------- | ------------------------------- |
| `shared/core/reduction.mojo` | `from .shape import as_contiguous` → per-function | 1371 |
| `shared/core/conv.mojo` | `from .shape import ...` → per-function | 1371 |
| `shared/core/pooling.mojo` | `from .shape import ...` → per-function | 1371 |
| `shared/core/loss_utils.mojo` | `from .elementwise import ...` → per-function | 3170 (elementwise + dtype_dispatch) |
| `shared/data/datasets/cifar10.mojo` | `from shared.core.shape import ...` → per-function | 1371 |

### __init__.mojo Transitive Chain

If `datasets/__init__.mojo` re-exports `cifar10.mojo` which has module-level `from shared.core.shape import ...`,
then ANY test importing from `shared.data.datasets` pulls in `shape.mojo` transitively.
Fix: localize the heavy import in `cifar10.mojo` to per-function bodies.

**Additional Failed Attempts** (from mojo-library-import-audit):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test-file import audit only | Converted all test files from `from shared.core import` to targeted submodule imports | Crashes persisted in Core Gradient, Core Loss, Integration, and Data groups | Library modules themselves carry module-level imports that apply to ALL their importers — test file audit is necessary but not sufficient |
| Auditing only direct imports in test files | Checked what test files import, not what those imports import | Transitive chain `cifar10.mojo` → `shape.mojo` was invisible until library module was read | Always trace the full transitive import chain, not just the immediate imports |
