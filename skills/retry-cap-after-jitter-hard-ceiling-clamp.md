---
name: retry-cap-after-jitter-hard-ceiling-clamp
description: 'Fix and verify exponential-backoff retry helpers where max_delay is
  applied BEFORE jitter, making the cap advisory so the actual sleep exceeds it. Use
  when: (1) planning or reviewing a retry/backoff function that clamps with
  min(delay, max_delay) and then adds jitter, (2) a sleep-cap unit test asserts
  <= max_delay * 1.25 instead of <= max_delay, (3) deciding how to clamp jittered
  backoff without changing jitter shape.'
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
- retry
- backoff
- jitter
- exponential-backoff
- max-delay
- cap-ordering
- hephaestus
- planning
---

# Skill: retry-cap-after-jitter-hard-ceiling-clamp

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Project** | ProjectHephaestus (issue #1206) |
| **Objective** | Plan and verify the fix for an exponential-backoff helper where `max_delay` is clamped BEFORE jitter, so jitter pushes the real sleep above the advertised cap |
| **Outcome** | Plan produced; fix is theoretically sound but NOT executed (no tests run, no CI) |
| **Verification** | unverified — planned only, end-to-end run pending |

## When to Use

- You are planning or reviewing a retry/backoff helper that computes
  `delay = min(growth, max_delay)` and THEN applies jitter — the classic
  "cap is advisory" bug.
- A backoff function uses additive `random.uniform(-0.25*delay, 0.25*delay)`
  (±25%) or multiplicative `random.uniform(0.5, 1.5)` jitter on top of a
  pre-clamped delay.
- A sleep-cap unit test asserts `sleep <= max_delay * 1.25` (or `* 1.5`) — the
  test bakes the bug's tolerance into the suite.
- You need to clamp jittered backoff to a hard ceiling WITHOUT changing the
  jitter distribution (avoiding scope creep).
- There is a trailing `max(0.1, delay)` floor and you must reason about how the
  floor interacts with the cap.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated
> end-to-end. Treat as a hypothesis until CI confirms. Verification level:
> `unverified` — the fix was planned for ProjectHephaestus issue #1206 but no
> tests were run and CI did not validate it.

### Quick Reference

```python
# BUG: cap applied before jitter -> cap is advisory.
delay = min(base * (factor ** attempt), max_delay)   # pre-clamp (KEEP this)
if jitter:
    delay += random.uniform(-0.25 * delay, 0.25 * delay)   # additive +-25%
    delay = min(delay, max_delay)   # FIX: re-clamp AFTER jitter (hard ceiling)
delay = max(0.1, delay)   # floor stays LAST (degenerate if max_delay < 0.1)
time.sleep(delay)
```

```python
# RED-first test: force jitter to its maximum, assert the cap is a hard ceiling.
@patch("hephaestus.utils.retry.random.uniform", side_effect=lambda lo, hi: hi)
def test_jitter_never_exceeds_max_delay(self, _uniform, mock_sleep):
    # ... drive several attempts with jitter=True ...
    for call in mock_sleep.call_args_list:
        assert call.args[0] <= max_delay   # NOT max_delay * 1.25
```

### Detailed Steps

1. **Locate the ordering.** Find where `min(delay, max_delay)` is applied
   relative to the jitter term. If the clamp precedes jitter, the cap is
   advisory.

2. **Keep the pre-jitter clamp; add a post-jitter clamp.** Leave
   `delay = min(growth, max_delay)` in place — it bounds the magnitude that
   jitter is computed from, keeping jitter proportional to the *capped* value.
   Add a second `delay = min(delay, max_delay)` AFTER the jitter term so the
   cap becomes a hard ceiling.

3. **Preserve jitter SHAPE.** If the code uses additive ±25%
   (`random.uniform(-0.25*delay, 0.25*delay)`), keep it additive. If it uses
   multiplicative (`uniform(0.5, 1.5)`), keep it multiplicative. Only clamp the
   result. Changing the distribution to "fix" the cap is scope creep
   (KISS/YAGNI) and changes observable timing behavior unnecessarily.

4. **Keep the floor last and document the degenerate case.** A trailing
   `max(0.1, delay)` floor must stay the final operation. If `max_delay < 0.1`,
   the floor wins and the sleep (0.1) legitimately exceeds the cap. This is an
   acceptable degenerate config — document it rather than reordering the floor
   before the cap (which would clamp below the floor and could yield a
   zero/negative-ish sleep).

5. **RED test before GREEN.** Patch `random.uniform` with
   `side_effect=lambda lo, hi: hi` to force jitter to its maximum, then assert
   every `time.sleep` argument is `<= max_delay` with `jitter=True`. This test
   FAILS on the buggy ordering and PASSES after the post-jitter clamp.

6. **Tighten any bug-encoding assertion.** If an existing test asserts
   `sleep <= max_delay * 1.25` (or `* 1.5`), it encodes the buggy tolerance.
   TIGHTEN it to `<= max_delay`. Do not leave it — a green suite that permits
   cap*1.25 has not actually pinned the fix.

7. **Anchor regression with `jitter=False`.** A `jitter=False` cap test is
   unaffected by the fix and makes a good untouched regression anchor; leave it
   as-is to prove the non-jittered path still respects the cap.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Apply cap before jitter only (`min(growth, cap)` then `* jitter` / `+ jitter`) | The cap is advisory — additive ±25% jitter reaches `cap * 1.25` and multiplicative `uniform(0.5,1.5)` reaches `cap * 1.5`, so the real sleep exceeds `max_delay` | Re-clamp AFTER jitter with `min(jittered_delay, max_delay)` to make the cap a hard ceiling |
| 2 | Leave the `assert sleep <= cap * 1.25` test unchanged | Suite stays green but the cap is still violated in spirit; the test certifies the buggy tolerance instead of the cap | Tighten the assertion to `<= cap` so the test actually pins the fix |
| 3 | Switch additive jitter to multiplicative (or vice-versa) to "fix" the cap | Unnecessary behavior change — alters the timing distribution and observable retry cadence without being required to enforce the cap | Preserve jitter shape; only clamp the result (KISS/YAGNI) |
| 4 | Move the `max(0.1, delay)` floor before the cap clamp to "be consistent" | When `max_delay < 0.1` the cap would clamp below the floor, defeating the minimum-sleep guarantee | Keep the floor LAST; accept and document the degenerate `max_delay < 0.1` case where floor (0.1) > cap |

## Results & Parameters

**Fix shape (additive ±25% jitter):**

```python
delay = min(base_delay * (backoff_factor ** attempt), max_delay)
if jitter:
    delay += random.uniform(-0.25 * delay, 0.25 * delay)
    delay = min(delay, max_delay)   # the one-line fix
delay = max(0.1, delay)
```

**Bug envelope (without the post-jitter clamp):**

| Jitter form | Max real sleep vs cap |
|-------------|-----------------------|
| Additive ±25% (`uniform(-0.25*d, 0.25*d)`) | up to `max_delay * 1.25` |
| Multiplicative (`uniform(0.5, 1.5)`) | up to `max_delay * 1.5` |

**Test pattern (forces worst-case jitter):**

```python
@patch("hephaestus.utils.retry.random.uniform", side_effect=lambda lo, hi: hi)
def test_jitter_capped(self, _u, mock_sleep):
    ...  # run retries with jitter=True
    assert all(c.args[0] <= MAX_DELAY for c in mock_sleep.call_args_list)
```

**Uncertain assumptions / verification gaps (record honestly):**

- The plan's cited line numbers (`retry.py:73-78, 65-70, 100`;
  `test_retry.py:150-168, 248-263`) were read directly from disk during
  planning, so they are verified-local — but they drift as the file changes.
  Re-locate by code shape (the `min(... , max_delay)` clamp and the
  `random.uniform` jitter term), not by line number.
- The two Mnemosyne skills surfaced via `/advise`
  (`homeric-crosshost-deployment-and-mesh-topology:265`,
  `github-api-secondary-rate-limit-backoff`) were NOT re-opened during
  planning — their exact snippet contents are unverified second-hand.
- The plan was NOT executed: no tests were run and CI did not validate it. The
  fix is theoretically sound but unverified end-to-end.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1206 — implementation plan (planning only, not executed) | Plan-stage learning; cap-before-jitter ordering bug in `hephaestus/utils/retry.py` |
