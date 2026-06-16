---
name: automation-529-overload-not-retried-classifier-gap
description: "Use when: (1) an agent/API call hits 529 Overloaded or 5xx and is treated as fatal despite max_retries being set; (2) a retry loop only fires on quota/429-with-reset-epoch and ignores server-overload; (3) auditing whether retryability covers ALL transient failure families; (4) a subprocess hard-codes a timeout that bypasses a centralized timeout module."
category: debugging
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Automation 529 Overload Not Retried — Classifier Gap

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Identify and fix why 529 Overloaded bubbled as a fatal error despite max_retries=3 being configured in PlannerClaudeRunner |
| **Outcome** | Root cause found and fixed: single quota-reset-epoch classifier structurally excluded 529s; union-of-classifiers pattern applied (PR #1375) |
| **Verification** | verified-ci |

## When to Use

- An agent or API call receives `API Error: 529 Overloaded` (or any 5xx) and execution fails with `phase plan FAILED rc=1` despite `max_retries` being non-zero
- A retry loop is gated on `scan_quota_reset()` / `resolve_quota_reset_epoch()` or any similar function that only matches 429-with-reset-epoch phrasings — meaning it structurally cannot trigger on server-overload responses
- Auditing a retry implementation to confirm retryability covers ALL transient failure families (quota/rate-limit, server-overload, timeout)
- A subprocess invokes a hard-coded literal timeout (e.g. `timeout=600`) that bypasses a centralized timeout helper, silently capping the budget below the configured value

## Verified Workflow

### Quick Reference

```python
# 1. Separate classifier for server overload (does NOT require a reset epoch)
import re

_OVERLOAD_PATTERNS = re.compile(
    r"(API Error.*?529|status[:\s]+529|Overloaded|overloaded_error"
    r"|API Error.*?5[0-9]{2}|status[:\s]+5(?!00\b)[0-9]{2})",
    re.IGNORECASE,
)
_OVERLOAD_REJECT = re.compile(r"\b4[0-9]{2}\b")  # never match 4xx

def detect_server_overload(*texts: str) -> bool:
    """Return True if any text signals a transient server-overload (529 / 5xx)."""
    combined = " ".join(t for t in texts if t)
    if _OVERLOAD_REJECT.search(combined):
        return False
    return bool(_OVERLOAD_PATTERNS.search(combined))

# 2. Union-of-classifiers retry branch in call_claude()
for attempt in range(max_retries + 1):
    result = _run_claude(...)
    reset_epoch = scan_quota_reset(result.stderr, result.stdout)  # 429 path
    if reset_epoch is not None:
        _wait_until(reset_epoch)
        continue
    if detect_server_overload(result.stderr, result.stdout):     # 529/5xx path
        delay = min(5 * (2 ** attempt), 20)                     # 5s → 10s → 20s
        time.sleep(delay)
        continue
    # ... timeout path, fatal path

# 3. Route subprocess timeout through centralized helper (not a literal)
timeout = planner_claude_timeout()   # reads HEPH_PLANNER_AGENT_TIMEOUT, default 7200
subprocess.run([...], timeout=timeout)
```

### Detailed Steps

1. **Identify the single-classifier gate**: locate the retry loop and find the ONLY condition that enables retry. If that condition requires a reset epoch (or any field 529s never carry), the loop is structurally broken for 529s.

2. **Add `detect_server_overload(*texts)`**: implement a separate regex classifier matching `529`, `Overloaded`, `overloaded_error`, and `5xx` patterns anchored to `API Error` / `status` context. Explicitly reject bare 4xx matches with a negative pattern so fatal client errors are never retried.

3. **Wire a separate overload-retry branch**: after the quota-reset check, add `elif detect_server_overload(...)` with bounded exponential backoff (e.g. 5 / 10 / 20 seconds). Do not mix it with the quota path — they have different wait strategies.

4. **Enumerate all transient families and confirm each has a detector**:
   - Quota / 429 with reset epoch → `scan_quota_reset` / `resolve_quota_reset_epoch`
   - Server overload / 529 / 5xx → `detect_server_overload` (new)
   - Timeout / SIGKILL → separate timeout detector or exception catch

5. **Route subprocess timeouts through the centralized helper**: replace any literal `timeout=600` (or similar hard-coded value) with `timeout=planner_claude_timeout()` which reads `HEPH_PLANNER_AGENT_TIMEOUT` (default 7200).

6. **Validate**: run `pixi run pytest tests/unit -v` — confirm new unit tests for `detect_server_overload` pass and existing retry tests are unaffected.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single quota-reset-epoch retry trigger | Retry loop conditioned solely on `scan_quota_reset()` returning non-None; `max_retries=3` was set | `resolve_quota_reset_epoch` only matches 429 phrasings that carry a reset timestamp; 529 Overloaded has no reset epoch so `scan_quota_reset` returned None and the retry branch was skipped entirely | A retry loop gated on ONE classifier is structurally blind to any transient error family that classifier does not recognize — even if `max_retries` is non-zero |
| Hard-coded 600s subprocess timeout | `plan-issues` subprocess used `timeout=600` literal instead of the centralized `planner_claude_timeout()` | The configured budget is 7200s (`HEPH_PLANNER_AGENT_TIMEOUT`); the literal 600s cap silently killed long-running plan runs 12x earlier than intended | Every subprocess timeout must be routed through the centralized timeout helper — never a literal value — to honor the operator-configured budget |

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Overload backoff schedule | 5s / 10s / 20s (capped) | `min(5 * 2**attempt, 20)` |
| Overload retry max attempts | Shares `max_retries` (default 3) | Same counter as quota retries |
| Centralized timeout env var | `HEPH_PLANNER_AGENT_TIMEOUT` | Default 7200s; read by `planner_claude_timeout()` |
| Classifier match set (529) | `API Error.*529`, `status.*529`, `Overloaded`, `overloaded_error` | Case-insensitive |
| Classifier match set (5xx) | `API Error.*5[0-9]{2}`, `status.*5[0-9]{2}` (excluding 500) | Anchored to avoid bare digit matches |
| Classifier reject set | `\b4[0-9]{2}\b` | Prevents matching fatal 4xx client errors |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1375 / issue #1374 — automation-loop planner hit 529 on issue #1357 | CI green; `detect_server_overload` unit tests pass; subprocess timeout routed through `planner_claude_timeout()` |
