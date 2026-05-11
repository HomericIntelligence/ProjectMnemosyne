---
name: gh-cli-proactive-per-thread-throttle
description: "Add proactive per-thread token-bucket throttling at the single `gh` CLI invocation chokepoint to prevent GitHub secondary rate limits before they trigger. Use when: (1) a Python codebase wraps `gh` and bursts requests during fan-out (e.g. one `gh issue view` per discovered issue), (2) reactive rate-limit handling exists but secondary limits still fire, (3) a `ThreadPoolExecutor` fans out work and per-worker pacing is needed without global coordination, (4) deciding the architectural layer for a throttle (answer: at the per-call chokepoint, not the per-phase orchestrator)."
category: tooling
date: 2026-05-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - gh-cli
  - github-api
  - rate-limit
  - secondary-limit
  - throttle
  - token-bucket
  - threadpoolexecutor
  - per-thread
  - proactive
  - python
  - subprocess
---

# gh CLI Proactive Per-Thread Throttle

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | Stop tripping GitHub secondary rate limits during the 6-phase Hephaestus automation loop, where the planner phase fires 30+ `gh issue view` calls back-to-back per run |
| **Outcome** | Successful — 5 req/sec/thread proactive cap added at the `_gh_call()` chokepoint; reactive rate-limit handler kept as safety net; 427/427 automation unit tests pass |
| **Verification** | verified-local |
| **Repo / PR** | `HomericIntelligence/ProjectHephaestus` PR #404, branch `feat/automation-loop-6phase-knobs`, commit `ec771f1` |

## When to Use

- A Python codebase wraps the `gh` CLI (or any other rate-limited CLI) and a single phase fans out many calls (e.g. one `gh issue view` per discovered issue).
- The codebase already has reactive rate-limit handling (parses "Limit reached" / 429 from stderr, sleeps until reset) but is *still* tripping GitHub's secondary rate limits.
- A `ThreadPoolExecutor` (or other worker pool) fans out work; you want per-worker pacing without inter-thread coordination overhead.
- You are deciding **where** to insert a throttle. The answer for codebases that route every CLI invocation through a single helper is: at that helper, **not** at the per-call sites and **not** at the per-phase orchestrator.
- An operator needs an env-var escape hatch (e.g. `GH_RATE_LIMIT_PER_SEC=0`) to disable throttling for tests or one-off scripts.

## Verified Workflow

### Quick Reference

```python
# At module top (e.g. hephaestus/automation/github_api.py)
import os
import threading
import time

_GH_THROTTLE = threading.local()


def _gh_throttle_wait() -> None:
    """Sleep just long enough to keep this thread under GH_RATE_LIMIT_PER_SEC.

    Per-thread token bucket: with N ThreadPoolExecutor workers, aggregate
    rate is ~N x GH_RATE_LIMIT_PER_SEC. The reactive handler catches the
    case where the aggregate exceeds GitHub's secondary limit.
    """
    rate = float(os.environ.get("GH_RATE_LIMIT_PER_SEC", "5"))
    if rate <= 0:
        return  # disabled
    min_interval = 1.0 / rate
    last = getattr(_GH_THROTTLE, "last_call", 0.0)
    now = time.monotonic()  # NOT time.time() — clock-jump safe
    elapsed = now - last
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _GH_THROTTLE.last_call = time.monotonic()


def _gh_call(args: list[str], ...) -> subprocess.CompletedProcess:
    for attempt in range(max_retries):
        _gh_throttle_wait()  # <-- inside the retry loop, so retries also pace
        result = subprocess.run(["gh", *args], ...)
        # existing reactive rate-limit detection here, e.g.
        # if detect_rate_limit(result.stderr): wait_until(reset_ts); continue
        return result
```

```bash
# Operator escape hatches
export GH_RATE_LIMIT_PER_SEC=5    # default — burst-friendly, under secondary limit
export GH_RATE_LIMIT_PER_SEC=2    # tighter pacing for noisy environments
export GH_RATE_LIMIT_PER_SEC=0    # disabled — useful for unit tests / one-offs
```

### Detailed Steps

1. **Identify the chokepoint.** Grep for every `subprocess.run(["gh", ...])` or `subprocess.run(["gh", ...])` call site. If they all funnel through one helper (`_gh_call`, `run_gh`, etc.), the throttle goes there. If they don't, refactor to a single helper *first* — adding the throttle to N call sites is a maintenance trap.

2. **Pick the layer deliberately.** The throttle must live **at or below the per-call layer**. Putting it in a shell wrapper around the orchestrator (e.g. `sleep` between phases) does not help because the burst happens *inside* a phase (e.g. planner doing 35 `gh issue view` calls back-to-back). Putting it at the per-phase layer is the same mistake.

3. **Per-thread, not global.** Use `threading.local()`. With a `ThreadPoolExecutor(max_workers=N)`, this gives each worker its own `min_interval` budget; aggregate rate is `N x rate`. Document this trade-off — operators with high `max_workers` need to size `GH_RATE_LIMIT_PER_SEC` accordingly, or rely on the reactive handler as a safety net.

4. **`time.monotonic()` not `time.time()`.** The wall clock can jump (NTP sync, DST changes). `monotonic` is guaranteed non-decreasing and is the correct primitive for "how long since the last event."

5. **Inside the retry loop, not outside.** Call `_gh_throttle_wait()` at the top of each retry attempt. Retries also count against the rate limit — if you only throttle the first attempt, a tight retry loop on a transient error blows the budget.

6. **Compose, don't replace, the reactive handler.** This is **proactive** (pace requests so the limit is never hit). Keep the existing **reactive** handler (parse "Limit reached" / 429 from stderr after the fact, sleep until reset). Proactive cap underestimates → reactive handler is the safety net. Replacing one with the other loses defense-in-depth.

7. **Env-var override with a sane default.** `GH_RATE_LIMIT_PER_SEC` defaults to `5` (empirically burst-friendly but under GitHub's secondary-limit threshold). `0` disables entirely. Document both.

8. **Test the throttle in isolation.** Three unit tests cover the surface:
   - Same thread, two consecutive calls separated by `>= 1/rate - epsilon`.
   - `GH_RATE_LIMIT_PER_SEC=0` → many calls complete in negligible time.
   - Pre-warm thread A's bucket, then thread B's first call completes immediately (per-thread isolation).

9. **Audit existing tests that count `time.sleep` calls.** This pattern adds `time.sleep` calls inside the retry loop. Tests that assert `sleep_call_count == 2` will break. Refactor them to assert on `time.sleep` *durations* (`assert 1 in sleep_durations and 2 in sleep_durations`) — the duration-based assertion is more semantic and survives this kind of change.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| 1 | Throttle in the shell wrapper — add `sleep` between phases in `run_automation_loop.sh` | Doesn't help. The burst happens *inside* each phase (planner doing 35 `gh issue view` calls back-to-back), not between phases. | The throttle must live at or below the per-call layer, not above the per-phase layer. |
| 2 | Rely on existing reactive `detect_rate_limit()` only | Lets the burst hit the API, then waits a long reset window after the limit fires. Wastes time and pollutes logs with rate-limit messages. | Combine reactive (safety net) with proactive (avoids tripping in the first place). They are different concerns; use both. |
| 3 | Initial implementation broke `test_retry_on_transient_error` which counted total `time.sleep` calls | The throttle adds its own `time.sleep` calls, throwing off the count assertion (expected 2, got 4). | Tests that assert on `time.sleep` *count* are fragile. Assert on the *durations passed* (e.g. `1 in sleep_durations`, `2 in sleep_durations`) — duration-based assertions survive instrumentation changes. |
| 4 | Considered global `threading.Lock` + shared `last_call` for true cross-thread cap | Adds lock contention on every call, serializes the worker pool, and defeats the purpose of `ThreadPoolExecutor(max_workers=N)`. Operator intent ("5 issues/sec") was clearly per-burst-source, not cross-process global. | Per-thread local state is the right primitive when the goal is "pace each producer," not "globally cap the API." Document the aggregate trade-off explicitly. |

## Results & Parameters

### Files touched

- `hephaestus/automation/github_api.py` — added `_GH_THROTTLE`, `_gh_throttle_wait()`, call site at top of `_gh_call`'s retry loop.
- `tests/unit/automation/test_github_api.py` — new `TestGhCallThrottle` class with 3 tests.

### Parameters

| Knob | Default | Meaning |
| --- | --- | --- |
| `GH_RATE_LIMIT_PER_SEC` | `5` | Per-thread cap on `gh` invocations per second. `0` disables. |

### Verification evidence

- `pixi run pytest tests/unit/automation/` → **427/427 passing**.
- New tests:
  - `TestGhCallThrottle::test_consecutive_calls_are_paced_to_min_interval` — same thread, two calls separated by ≥0.18s at default 5/sec.
  - `TestGhCallThrottle::test_throttle_disabled_when_rate_zero` — `GH_RATE_LIMIT_PER_SEC=0` → 5 calls in <0.05s.
  - `TestGhCallThrottle::test_buckets_are_per_thread` — pre-warm thread A, thread B's first call completes in <0.05s.
- `ruff check` clean.
- Pushed to PR #404, commit `ec771f1`.

### Related skills (cross-reference)

These cover the **reactive** half of GitHub rate-limit handling. This skill is the **proactive** complement — they compose, they do not replace each other.

- `ci-cd-github-api-rate-limit-ci-monitoring` — recovery patterns for the 5000/hr REST limit during CI diagnostic loops.
- `github-bulk-issue-filing-rate-limit-recovery` — handling 403 BCE2 secondary limits and org monthly limits during bulk issue creation.
- `e2e-rate-limit-detection` — detecting 429s that hide inside stdout JSON (Claude CLI), with the `or`-vs-`is not None` chaining pitfall.
- `processpoolexecutor-rate-limit-recovery` — sibling pattern for `ProcessPoolExecutor` (vs the `ThreadPoolExecutor` covered here).
