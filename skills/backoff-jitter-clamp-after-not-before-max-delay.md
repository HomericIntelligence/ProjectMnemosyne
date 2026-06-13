---
name: backoff-jitter-clamp-after-not-before-max-delay
description: "Clamp exponential-backoff delay to max_delay AFTER applying jitter so the cap is a hard ceiling, while KEEPING the pre-jitter clamp (the doubled clamp is intentional, not a DRY violation). Use when: (1) a retry/backoff helper applies max(min) cap before adding jitter and a caller's max_delay is being exceeded by the jitter percentage, (2) you are reviewing or fixing exponential-backoff code and need to decide whether the pre-jitter clamp is redundant, (3) you see delay = min(base * factor**n, cap) * jitter or cap-then-add-jitter and need the worst-case sleep bounded, (4) a max_delay is documented as advisory rather than a hard bound."
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [backoff, jitter, retry, max-delay, clamp, hard-ceiling, exponential-backoff, thundering-herd, rate-limit, python, hephaestus]
---

# Backoff Jitter: Clamp AFTER Jitter, Keep the Pre-Jitter Clamp Too

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Make `max_delay` a hard ceiling on the actual sleep, while preserving jitter spread at high attempt counts |
| **Outcome** | Success — re-applied `min(delay, max_delay)` after jitter; kept the pre-jitter clamp; 23/23 retry tests pass |
| **Verification** | verified-local (tests + ruff + mypy green locally; CI pending at authoring time) |

## When to Use

- A retry/backoff helper applies the `max_delay` cap **before** adding jitter, so the real sleep can exceed the cap by the jitter fraction (e.g. `max_delay * 1.25` for additive ±25%, or `max_delay * 1.5` for multiplicative `uniform(0.5, 1.5)`).
- A caller set `max_delay` specifically to **bound worst-case latency** and is not getting that bound. The docstring may even admit the cap is "approximate" or "advisory".
- You are reviewing a fix and wondering whether the **pre-jitter clamp is now redundant** and should be deleted (it is NOT — see the worked example below).
- Any code shaped like `delay = min(base * factor**attempt, cap) * random.uniform(...)` or "cap, then add jitter, then return".

## Verified Workflow

### Quick Reference

```python
# BEFORE (bug): cap applied before jitter → real sleep reaches max_delay * 1.25
def _compute_backoff_delay(attempt, initial_delay, backoff_factor, max_delay, jitter):
    delay = initial_delay * (backoff_factor ** attempt)
    if max_delay is not None:
        delay = min(delay, max_delay)
    if jitter:
        delay = float(delay + random.uniform(-0.25 * delay, 0.25 * delay))  # additive ±25%
    return max(0.1, delay)

# AFTER (fix): re-clamp AFTER jitter → max_delay is a hard ceiling. KEEP the pre-clamp.
def _compute_backoff_delay(attempt, initial_delay, backoff_factor, max_delay, jitter):
    delay = initial_delay * (backoff_factor ** attempt)
    if max_delay is not None:
        delay = min(delay, max_delay)          # pre-clamp: KEEP — bounds the magnitude jitter is computed from
    if jitter:
        delay = float(delay + random.uniform(-0.25 * delay, 0.25 * delay))
    if max_delay is not None:
        delay = min(delay, max_delay)          # post-clamp: the actual fix — hard ceiling
    return max(0.1, delay)                      # floor stays LAST
```

### The doubled clamp is intentional (do NOT delete the pre-clamp)

The pre-jitter clamp is **not** redundant after you add the post-jitter clamp. It bounds the magnitude that jitter is computed *from*, keeping jitter proportional to the *capped* delay rather than to an unbounded exponential. Worked example — `initial_delay=1.0, backoff_factor=10, attempt=2, max_delay=2.0` (raw exponential = `1.0 * 10**2 = 100.0`):

| | Pre-clamp present | Pre-clamp removed |
| --- | --- | --- |
| delay fed to jitter | `min(100, 2.0) = 2.0` | `100.0` |
| jitter range (±25%) | `[-0.5, +0.5]` | `[-25, +25]` |
| pre-final-clamp value | `[1.5, 2.5]` | `[75, 125]` |
| after final `min(.., 2.0)` | `[1.5, 2.0]` — **real spread around the cap** | `min(75..125, 2.0) = 2.0` — **jitter destroyed** |

Removing the pre-clamp would collapse every high-attempt delay to **exactly** `max_delay` with zero jitter — a thundering-herd regression that defeats the entire purpose of jitter (de-synchronizing retrying clients). The doubled clamp is correct, not a DRY violation; add a comment so the next reader does not "simplify" it away.

### Floor ordering

`return max(0.1, delay)` stays the **last** operation. If `max_delay < 0.1`, the floor wins (degenerate sub-0.1s cap). This is pre-existing sane behavior — preserve it; do not reorder the floor before the clamp.

### Keep the jitter shape the codebase already uses (YAGNI)

This codebase uses **additive** jitter `random.uniform(-0.25 * delay, 0.25 * delay)` (±25%). The fix is purely about **clamp ordering**, not jitter shape. Do NOT switch to multiplicative `random.uniform(0.5, 1.5)` just because a snippet elsewhere uses that form — that is scope creep that silently changes behavior. Same bug class, different shape: a `min(base * 2**n, 2.0) * random.uniform(0.5, 1.5)` form reaches `2.0 * 1.5 = 3.0` (cap-before-jitter, multiplicative). The marketplace skill `homeric-crosshost-deployment-and-mesh-topology` contains exactly that defective snippet in its `publish_with_retry` example — cross-reference it, but do NOT amend it (it is a deployment/mesh-topology skill; the bug appears only incidentally).

### RED-first regression test technique

```python
from unittest.mock import patch

@patch("hephaestus.utils.retry.time.sleep")
@patch("hephaestus.utils.retry.random.uniform")  # MUST be module-qualified, not global random
def test_jittered_delay_never_exceeds_max_delay(mock_uniform, mock_sleep):
    mock_uniform.side_effect = lambda lo, hi: hi  # force the maximum +25% jitter

    # backoff_factor=10 so the un-clamped jittered value would be 2.5 > cap=2.0
    flaky = _make_flaky_func(fail_times=3)
    decorated = retry(max_delay=2.0, backoff_factor=10, jitter=True)(flaky)
    decorated()

    for call in mock_sleep.call_args_list:
        assert call.args[0] <= 2.0   # RED against buggy code: "assert 2.5 <= 2.0"
```

Steps:
1. Mock `random.uniform` to its max positive value via `side_effect = lambda lo, hi: hi` (forces +25%).
2. Patch the target **module-qualified**: `@patch("hephaestus.utils.retry.random.uniform")`, never global `random`.
3. Patch `time.sleep` and assert every `mock_sleep.call_args` is `<= max_delay`.
4. Use `backoff_factor=10` so the un-clamped jittered value reaches `2.5 > 2.0` — this makes the test genuinely fail RED (observed `assert 2.5 <= 2.0`).
5. **Fix any pre-existing test that bakes in the buggy tolerance.** Here `test_max_delay_respected` had `<= 2.0 * 1.25 + 0.1` and was tightened to `<= 2.0`. A test that encodes buggy tolerance must be corrected, not left.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Remove the pre-jitter clamp | After adding the post-jitter clamp, deleted the pre-clamp as a presumed DRY violation | At high attempts the raw exponential (e.g. 100.0) is fed to jitter, producing `[75, 125]`; the final clamp collapses all of it to exactly `max_delay` → zero jitter → thundering herd | The doubled clamp is intentional; the pre-clamp bounds the magnitude jitter is proportional to. Comment it so it survives future "simplification" |
| Switch jitter to multiplicative `uniform(0.5, 1.5)` | Borrowed a `* random.uniform(0.5, 1.5)` shape seen in another skill while fixing the cap | Changed observable behavior (jitter spread, sign symmetry) unnecessarily; the bug was ordering, not shape; widened the diff and the review surface | Keep the existing jitter shape (additive ±25% here). Fix only the ordering. YAGNI / scope discipline |
| Patch global `random.uniform` | `@patch("random.uniform")` instead of the module path | The retry module already bound `random` at import; patching the global namespace does not intercept the module's reference, so the test mocked nothing and passed against buggy code | Patch target must be module-qualified: `@patch("hephaestus.utils.retry.random.uniform")` |
| Trust the existing `test_max_delay_respected` | Assumed the green test proved the cap held | The assertion was `<= 2.0 * 1.25 + 0.1` — it had *encoded* the buggy `* 1.25` overshoot as acceptable tolerance | A passing test can ratify a bug. Tighten tolerances that bake in defective behavior to the true invariant (`<= max_delay`) |
| Cross-host snippet `min(base*2**n, 2.0) * uniform(0.5, 1.5)` (related pattern) | Seen in `homeric-crosshost-deployment-and-mesh-topology` `publish_with_retry` | Same cap-before-jitter defect, multiplicative variant: real delay reaches `2.0 * 1.5 = 3.0`; cap is advisory not hard | Same bug class recurs across jitter shapes. Recognize "cap, then jitter" anywhere. Do NOT amend that skill — different search surface; cross-reference only |

## Results & Parameters

**File changed**: `hephaestus/utils/retry.py` — `_compute_backoff_delay`: re-applied `min(delay, max_delay)` after the jitter step, kept the pre-jitter clamp, kept `max(0.1, delay)` as the final floor.

**Tests**: `tests/unit/utils/test_retry.py` — added RED-first regression test forcing max +25% jitter with `backoff_factor=10` (asserts every sleep `<= max_delay`); tightened `test_max_delay_respected` from `<= 2.0 * 1.25 + 0.1` to `<= 2.0`. All 23 tests pass locally.

**Quality gates**: `ruff format`, `ruff check`, `mypy` all clean locally.

**Invariants captured**:
- `max_delay` is a **hard ceiling** on the actual sleep, including after jitter.
- The **doubled clamp** (pre + post jitter) is intentional: pre-clamp preserves jitter spread, post-clamp enforces the ceiling.
- The `max(0.1, delay)` **floor stays last**.
- Jitter **shape is unchanged** (additive ±25%) — the fix is ordering-only.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1206 — `max_delay` not a hard ceiling under jitter | PR #1246, `hephaestus/utils/retry.py::_compute_backoff_delay`, 23/23 retry tests pass, ruff + mypy clean (verified-local; CI pending at authoring time) |
