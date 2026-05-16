---
name: pytest-mock-time-sleep-cross-module-hazard
description: "Warns that unittest.mock.patch('some_module.time.sleep') patches the SHARED time module object — neutralising time.sleep for every caller in the process, which can OOM the host via runaway print/log loops. Use when: (1) writing pytest tests that mock time.sleep to skip waits, (2) debugging a test that runs 30+ seconds or OOM-kills the host, (3) reviewing retry/backoff code containing `while True: ... time.sleep(...)`, (4) a single unit test allocates GBs of memory."
category: testing
date: 2026-05-15
version: "1.0.0"
user-invocable: false
tags: [pytest, unittest-mock, time-sleep, oom, retry-loops, patch-target]
---

# Pytest `patch("module.time.sleep")` Cross-Module Hazard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-15 |
| **Objective** | Document why `patch("some_module.time.sleep")` is NOT scope-limited to `some_module` and how the resulting hazard can OOM the host |
| **Outcome** | verified-ci — ProjectHephaestus PR #412 green; 113 targeted tests pass in 2.6s after fix vs 30s + OOM before |

## When to Use

Apply this skill when you encounter any of the following:

- Writing pytest tests that use `patch("some_module.time.sleep")` (or similar) to skip waits
- Debugging a single unit test that runs for 30+ seconds, allocates GBs, or OOM-kills WSL/CI
- Reviewing production code that contains `while True: ... time.sleep(N)` polling loops
- A test's captured-stdout buffer grows unboundedly (e.g. carriage-return countdown printers)
- A retry/backoff helper is being patched indirectly via `time.sleep` instead of at its own seam

## Root Cause

`unittest.mock.patch("some_module.time.sleep")` does **not** scope the patch to `some_module`.
`some_module.time` and every other module's `import time` resolve to the **same singleton module
object**; `patch` simply replaces the `sleep` attribute on that shared object. Consequence: every
caller in the entire process (background threads, retry loops in dependencies, countdown printers)
sees the mocked `time.sleep` and immediately returns, regardless of which module imported `time`.

If any of those silently-neutralised callers lives inside a `while True: print(...); time.sleep(N)`
loop, the loop spins at full CPU writing to pytest's captured-stdout buffer until memory is
exhausted.

## Verified Workflow

### Quick Reference

Three orthogonal safeguards — apply all of them when the situation warrants:

```python
# 1. Patch the dedicated wait helper, NOT time.sleep
with patch("module_under_test.wait_until") as mock_wait:
    ...

# 2. If you MUST patch a probe, patch at its source namespace
#    (where the function is defined), not via a re-export
with patch("hephaestus.github.rate_limit.gh_rate_limit_reset_epoch", return_value=None):
    ...

# 3. Add a defensive iteration cap in any production `while True: time.sleep(N)` loop
iterations = 0
while True:
    print(f"\rwaiting... {remaining}", end="")
    time.sleep(1)
    iterations += 1
    if iterations >= 100_000:
        logger.warning("wait_until iteration cap reached after %.2fs; bailing out", elapsed)
        return
```

### Detailed Steps

1. **Identify the seam.** If retry/backoff logic lives in a helper like `wait_until`, `wait_for`,
   `poll_for`, etc., mock the helper itself — not the underlying `time.sleep`. The helper is the
   correct test seam.

2. **Patch at the source, not via re-exports.** If `module_b` imports `func` from `module_a`, patch
   `module_a.func` when the call originates inside `module_a`. Patch `module_b.func` only when
   `module_b` itself calls the rebound name. A patch that "misses" because it targets the wrong
   namespace will let the real function run — which can cascade into the runaway loop described
   above.

3. **If you must patch `time.sleep`, audit the call graph.** Identify every dedicated wait helper
   that might be reached from the test's call graph and mock each of them too. Otherwise an
   unrelated helper's sleep is silently neutralised.

4. **Add a defensive iteration cap.** Any production `while True: ... time.sleep(N)` loop should
   include a simple counter that breaks after a large bound (e.g. 100,000 iterations). This is
   belt-and-suspenders against future mocking accidents — cheap to add, prevents host OOM.

5. **Diagnose runaway tests by signature.** A test that OOM-kills the host with high CPU + low real
   I/O + an unboundedly-growing captured-stdout buffer is the smoking gun for mocked-sleep cascade.
   Reproduce outside pytest with `python -X tracemalloc=10` and inspect peak memory + top
   allocation sites. If the top sites are `print`/`write` calls inside a `while True` loop,
   mocked-sleep is the cause.

### Concrete Failure (ProjectHephaestus PR #412)

```python
# Test wrote:
with patch("hephaestus.automation.github_api.time.sleep"), \
     patch("hephaestus.automation.github_api.gh_rate_limit_reset_epoch", return_value=None):
    _gh_call(["issue", "list"], max_retries=2)
```

What happened:

1. The probe patch missed — `detect_rate_limit` looks up the function in
   `hephaestus.github.rate_limit.gh_rate_limit_reset_epoch`, not via the `github_api` re-export —
   so the REAL function ran and returned a real future epoch.
2. `_gh_call` then called `wait_until(future_epoch)`, which contains
   `while True: print(...); time.sleep(1)`.
3. The `time.sleep` patch — intended only for the `github_api` module — also neutralised
   `rate_limit.time.sleep` because they share the same `time` module object.
4. The print loop spun at full CPU, filling pytest's captured-stdout buffer with
   `\r[INFO] Rate limit resets in 00:59:59` lines.
5. Process allocated 4 GiB, OOM-killed the WSL host, took 30+ seconds before death.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Patch `module.time.sleep` to skip waits in retry test | Patch leaked to every other module's `time.sleep` because `time` is a singleton module object — runaway print loop in `wait_until` filled pytest stdout buffer and OOMed WSL | `patch("module.time.sleep")` is process-wide for the `sleep` attribute, not module-scoped |
| 2 | Patch a probe function via a re-export namespace (`module_b.func`) when `module_a` calls it directly | Lookup happens in `module_a`'s namespace, so the patch was a no-op and the real function ran | Patch at the source namespace where the call site resolves the name |
| 3 | Rely solely on test-level mocking to keep `wait_until` quick | Any future test (or thread) that mocks `time.sleep` could re-trigger the same OOM cascade | Add a defensive iteration cap in the production loop itself |

## Results & Parameters

### The Three Safeguards (copy-paste ready)

```python
# Safeguard 1: prefer mocking the wait helper itself
with patch("hephaestus.automation.github_api.wait_until") as mock_wait:
    _gh_call(["issue", "list"], max_retries=2)
mock_wait.assert_called_once()

# Safeguard 2: patch probe functions at their source namespace
with patch(
    "hephaestus.github.rate_limit.gh_rate_limit_reset_epoch",
    return_value=None,
):
    ...

# Safeguard 3: iteration cap in production loop
def wait_until(epoch: float) -> None:
    iterations = 0
    while True:
        remaining = epoch - time.time()
        if remaining <= 0:
            return
        print(f"\r[INFO] Rate limit resets in {format_remaining(remaining)}", end="")
        time.sleep(1)
        iterations += 1
        if iterations >= 100_000:
            logger.warning(
                "wait_until iteration cap reached after %.2fs; bailing out",
                time.time() - start,
            )
            return
```

### Expected Output (verified-ci)

- Targeted test suite: 113 tests pass in ~2.6s (was: 30s + OOM)
- No unbounded memory growth under tracemalloc
- Captured-stdout buffer remains bounded
- CI green on ProjectHephaestus PR #412

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #412 — `_gh_call` retry test OOM-killed WSL; fixed by mocking `wait_until` directly, correcting probe-patch namespace, and adding 100k iteration cap to `wait_until` | `hephaestus/github/rate_limit.py`, `tests/unit/automation/test_github_api.py::TestGhCallRateLimitFromStdout` |

## References

- ProjectHephaestus PR #412 — original incident and fix
- `hephaestus/github/rate_limit.py` — `wait_until` with defensive iteration cap
- `tests/unit/automation/test_github_api.py::TestGhCallRateLimitFromStdout` — corrected patch targets
- Related skill: [`fix-flaky-sleep-mock.md`](fix-flaky-sleep-mock.md) — recommends `patch("module.time.sleep")` for retry tests; **read this skill alongside it** to understand the cross-module hazard that pattern introduces when other reachable code also calls `time.sleep`
- Related skill: [`flaky-test-patch-isolation.md`](flaky-test-patch-isolation.md) — class-level patch leakage (different mechanism, similar symptom of "test passes alone, breaks in suite")
- Python docs: [`unittest.mock` — where to patch](https://docs.python.org/3/library/unittest.mock.html#where-to-patch)
