---
name: e2e-rate-limit-detection
description: "Detect Claude/agent CLI 429 rate limits that hide inside stdout JSON (not stderr) and avoid silently breaking the retry path with `or`-chained detectors. Use when: (1) wrapping `claude -p --output-format=json` (or any CLI with structured output) and need rate-limit-aware retry, (2) every invocation dies in seconds with empty stderr but logs show `is_error: true` / 429, (3) widening a stderr-only detector to also scan stdout, (4) parsing reset times like 'resets May 8, 5pm (America/Los_Angeles)' that span multiple days."
category: debugging
date: 2026-05-05
version: "1.1.0"
user-invocable: false
verification: verified-local
history: e2e-rate-limit-detection.history
tags:
  - claude-cli
  - rate-limit
  - "429"
  - usage-cap
  - stdout-json
  - is_error
  - detector-chaining
  - or-vs-is-not-none
  - python
  - regex
  - json-parsing
  - error-detection
  - e2e-testing
  - api-errors
  - stderr-vs-stdout
  - tdd
---

# E2E Rate Limit Detection: JSON-Stdout, Detector Chaining, and the `0`-Sentinel Trap

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-05-05 (v1.1.0) — initial 2026-01-04 |
| **Objective** | Detect rate-limit / usage-cap errors emitted by Claude (and similar) CLIs whose 429 message lives inside stdout JSON, and avoid silently breaking the retry path when chaining detectors |
| **Outcome** | Operational across ProjectScylla and ProjectHephaestus; both gh-CLI and Claude-CLI message formats handled |
| **Verification** | verified-local (ProjectHephaestus: pixi pytest tests/unit → 1990 passed, coverage 83.04%; ruff + mypy clean) |
| **History** | [changelog](./e2e-rate-limit-detection.history) |

## When to Use

- Wrapping `claude -p --output-format=json` (or any structured-output CLI) and need rate-limit-aware retry — the 429 lives in stdout JSON's `result` field, not stderr.
- Every CLI invocation dies in 1–3 seconds with empty stderr and a generic "X failed" exception, but logs show `is_error: true` and an HTTP 429.
- Widening an existing stderr-only detector to also scan stdout — beware the `or`-chaining trap (see Failed Attempts #2 and #3).
- Parsing reset times that include a date prefix because the cap spans multiple days (e.g. `resets May 8, 5pm (America/Los_Angeles)`).
- A retry-after detector returns `0` (rate-limited, reset time unknown) and you need to distinguish that meaningful sentinel from `None` (no rate limit).
- Writing rate-limit detection for any structured-error JSON API: Claude CLI, Anthropic API, OpenAI's `error.type == "rate_limit_error"`, etc.

**Key indicator**: logs contain `{"is_error": true, "api_error_status": 429, "result": "You're out of extra usage · resets May 8, 5pm (America/Los_Angeles)", ...}` but the retry handler never fires.

## Verified Workflow

### Quick Reference

```python
# 1. Two distinct rate-limit message regexes (gh CLI and Claude CLI) — NOT interchangeable
RATE_LIMIT_RE = re.compile(  # gh CLI form
    r"(?:Limit reached|rate limit).*?resets\s+(?P<time>\d{1,2}(?::\d{2})?(?:am|pm)?)\s*\((?P<tz>[^)]+)\)",
    re.IGNORECASE,
)
CLAUDE_USAGE_CAP_RE = re.compile(  # Claude CLI form (with optional date prefix)
    r"resets\s+(?:(?P<date>[A-Za-z]+\s+\d{1,2})\s*,?\s+)?"
    r"(?P<time>\d{1,2}(?::\d{2})?(?:am|pm)?)\s*\((?P<tz>[^)]+)\)",
    re.IGNORECASE,
)

# 2. Helper: scan ALL streams with `is not None` chaining (NOT `or`)
def _scan_quota_reset(*texts: str) -> int | None:
    """Return reset epoch from any stream, or None.

    Returns 0 (NOT None) when rate-limit is detected but reset time is unknown —
    callers treat 0 as 'sleep 5s and retry'. NEVER chain detectors with `or`,
    because Python evaluates 0 as falsy and falls through to the next detector,
    silently treating 'rate-limited, time unknown' as 'no rate limit'.
    """
    for text in texts:
        for detect in (detect_rate_limit, detect_claude_usage_cap):
            epoch = detect(text)
            if epoch is not None:   # <-- the load-bearing check
                return epoch
    return None

# 3. In the CLI wrapper, scan both streams on BOTH paths:
#    a) the CalledProcessError branch (exit != 0)
#    b) the success-path-with-error branch (exit 0 but JSON has is_error: true)
try:
    result = subprocess.run(["claude", "-p", "--output-format=json", ...], check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as e:
    reset = _scan_quota_reset(e.stderr or "", e.stdout or "")
    if reset is not None:
        _wait_until(reset); return retry()
    raise

data = json.loads(result.stdout)
if data.get("is_error"):                  # <-- exit 0 + is_error: true is REAL
    reset = _scan_quota_reset(result.stderr or "", result.stdout or "")
    if reset is not None:
        _wait_until(reset); return retry()
    raise ClaudeError(data.get("result"))
```

### Detailed Steps

#### 1. Identify the bug pattern

Symptoms:

- Every CLI invocation dies in 1–3 seconds.
- `e.stderr` is empty.
- Real logs / `--output-format=json` payload contain `is_error: true` and a 429.
- Retry/wait handler never triggers.

Investigation:

```bash
# Capture both streams during a failing run
claude -p --output-format=json "<prompt>" > out.json 2> err.txt; echo "exit=$?"
jq '.is_error, .api_error_status, .result' out.json
# Look for: true, 429, "You're out of extra usage · resets May 8, 5pm (America/Los_Angeles)"
```

#### 2. Recognize the two distinct message formats

| Source | Example message | Notes |
| ------ | --------------- | ----- |
| `gh` CLI | `Limit reached for resource X, resets 2:30pm (America/Los_Angeles)` | Always intra-day; emitted on stderr |
| Claude CLI (intra-day) | `Claude usage limit reached · resets 9pm (America/Los_Angeles)` | Emitted in stdout JSON `result` field |
| Claude CLI (multi-day) | `You're out of extra usage · resets May 8, 5pm (America/Los_Angeles)` | **Date prefix** when cap spans days |

The two regexes share the `resets <time> (tz)` tail but **not the prefix** — do not collapse them into one.

#### 3. Add a date-aware reset parser

Sibling to the existing intra-day parser:

```python
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

def _parse_reset_with_date(date_str: str, time_str: str, tz: str) -> int | None:
    # date_str: "May 8" — disambiguate year by assuming next year if more
    # than ~6 months in the past (handles end-of-year wrap).
    # time_str: "5pm" or "5:30pm" or "17:00"
    # tz: IANA name like "America/Los_Angeles"
    ...
```

#### 4. Wire detection into the CLI wrapper on BOTH paths

A subtle truth: the Claude CLI sometimes returns **exit 0 with `is_error: true` in the JSON** for usage caps. A wrapper that only checks `subprocess.CalledProcessError` will silently log `session_id: null` and lose the failure signal. Always check `data.get("is_error")` on the success path too, and run `_scan_quota_reset` there as well.

#### 5. The `or` trap — use `is not None` chaining

`detect_*` functions return:

- `None` → no rate-limit detected
- `int > 0` → reset epoch (sleep until then)
- `0` → rate-limited but reset time unknown (sleep 5s and retry)

This makes `0` a meaningful sentinel. Chaining detectors with `or`:

```python
# WRONG — `0 or X` evaluates to X, silently swallowing the 0 sentinel
reset_epoch = (
    detect_rate_limit(stderr)
    or detect_rate_limit(stdout)
    or detect_claude_usage_cap(stderr)
    or detect_claude_usage_cap(stdout)
)
```

…silently treats "rate-limited, time unknown" (which is a real 429!) as "no rate limit". Always use the `_scan_quota_reset(*texts)` helper above, or write `is not None` checks explicitly.

#### 6. Write regression tests

Required test inputs (all must trigger the wait path):

```python
# Date form
"You're out of extra usage · resets May 8, 5pm (America/Los_Angeles)"
# Intra-day form
"Claude usage limit reached · resets 9pm (America/Los_Angeles)"
# JSON-embedded form
'{"is_error": true, "api_error_status": 429, "result": "You\'re out of extra usage · resets May 8, 5pm (America/Los_Angeles)"}'
```

Plus regression tests for both wrapper paths:

- `test_claude_usage_cap_in_stdout_triggers_wait` (CalledProcessError branch)
- `test_claude_usage_cap_with_exit_zero_is_error_true_triggers_wait` (success-path branch)

Audit existing mocks: tests like `test_rate_limit_retry` may use `side_effect=[0, None]` that breaks once new detectors are called per invocation. Switching the prod code to `is not None` chaining (instead of `or`) typically makes those tests pass naturally — the `0` is recognized on the first detector call.

#### 7. Verify

```bash
pixi run ruff check hephaestus/ tests/
pixi run mypy
pixi run pytest tests/unit -v
```

Expected: clean ruff/mypy, all tests pass, coverage roughly preserved.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Inspect only `e.stderr` for rate-limit text in `_call_claude` | Claude CLI emits 429 in stdout JSON when `--output-format=json`; stderr was empty | Always inspect **both** streams when wrapping a CLI with structured output |
| 2 | Chain four detectors with `or` after widening detection across both streams and both formats | A detector returning `0` (rate-limited, reset time unknown) was treated as "no rate limit" because `0 or X == X` in Python | Use `is not None` checks, not truthiness, when sentinel `0` has meaning |
| 3 | Place the new `_scan_quota_reset` helper between import groups for proximity to the call site | Triggered ruff `E402 module-level import not at top of file` | Module-level helpers go below **all** imports, never between them |
| 4 | Trust the `subprocess.CalledProcessError` branch alone for usage-cap detection | The Claude CLI sometimes returns exit 0 with `is_error: true` in JSON for usage caps; success-path branch needs the same detection wiring | Check both error-path and success-path-with-error JSON in any CLI wrapper |
| 5 | Reuse the existing `RATE_LIMIT_RE` (gh-CLI form) for Claude CLI messages | Claude form has a date prefix (`resets May 8, 5pm`) when cap spans multiple days; the gh regex doesn't match it | Add a sibling regex (`CLAUDE_USAGE_CAP_RE`) — don't try to make one regex match two distinct prose formats |
| 6 (legacy v1.0.0) | (ProjectScylla) Parse retry time from stderr only after detecting `is_error: true` in JSON stdout | The retry-time text was in the JSON `result` field, not stderr | Parse from the error message field first, then fall back to stderr |

## Results & Parameters

### Regex (copy-paste ready)

```python
import re

# gh CLI rate-limit form (intra-day only, emitted on stderr)
RATE_LIMIT_RE = re.compile(
    r"(?:Limit reached|rate limit).*?resets\s+"
    r"(?P<time>\d{1,2}(?::\d{2})?(?:am|pm)?)\s*\((?P<tz>[^)]+)\)",
    re.IGNORECASE,
)

# Claude CLI usage-cap form (intra-day OR with date prefix; emitted in stdout JSON)
CLAUDE_USAGE_CAP_RE = re.compile(
    r"resets\s+(?:(?P<date>[A-Za-z]+\s+\d{1,2})\s*,?\s+)?"
    r"(?P<time>\d{1,2}(?::\d{2})?(?:am|pm)?)\s*\((?P<tz>[^)]+)\)",
    re.IGNORECASE,
)
```

### Detector contract

| Return value | Meaning | Caller behavior |
| ------------ | ------- | --------------- |
| `None` | No rate-limit detected | Continue / treat as normal error |
| `int > 0` | Reset epoch (Unix seconds) | Sleep until that time, then retry |
| `0` | Rate-limited, reset time unknown | Sleep 5s, then retry |

**Critical**: `0` is a meaningful sentinel. Never chain detectors with `or`; always use `is not None`.

### Helper pattern

```python
def _scan_quota_reset(*texts: str) -> int | None:
    """Run all detectors against all streams; return first non-None result."""
    for text in texts:
        for detect in (detect_rate_limit, detect_claude_usage_cap):
            epoch = detect(text)
            if epoch is not None:
                return epoch
    return None
```

### Two-path detection (any CLI wrapper)

```python
try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as e:
    reset = _scan_quota_reset(e.stderr or "", e.stdout or "")
    if reset is not None:
        _wait_until(reset)
        return retry()
    raise

# Success path — but is_error: true is still possible (exit 0!)
data = json.loads(result.stdout or "{}")
if data.get("is_error"):
    reset = _scan_quota_reset(result.stderr or "", result.stdout or "")
    if reset is not None:
        _wait_until(reset)
        return retry()
    raise ClaudeError(data.get("result", "<empty>"))
```

### Code locations

| Project | File | Change |
| ------- | ---- | ------ |
| ProjectScylla (v1.0.0) | `src/scylla/e2e/rate_limit.py:177-178` | Parse `error_msg` before stderr |
| ProjectScylla (v1.0.0) | `tests/unit/e2e/test_rate_limit.py` | 31 tests |
| ProjectHephaestus (v1.1.0) | `hephaestus/github/rate_limit.py` | Added `CLAUDE_USAGE_CAP_RE`, `_parse_reset_with_date`, `detect_claude_usage_cap` |
| ProjectHephaestus (v1.1.0) | `hephaestus/automation/planner.py` | `_call_claude` scans both streams via `_scan_quota_reset` |
| ProjectHephaestus (v1.1.0) | `hephaestus/automation/implementer.py` | Same fix on both `CalledProcessError` and `is_error: true` JSON branches |
| ProjectHephaestus (v1.1.0) | `tests/unit/github/test_rate_limit.py` | New `TestDetectClaudeUsageCap` (4 tests: date form, intra-day, JSON-embedded, no-match) |
| ProjectHephaestus (v1.1.0) | `tests/unit/automation/test_planner.py` | New `test_claude_usage_cap_in_stdout_triggers_wait` |

### Verification (ProjectHephaestus, v1.1.0)

```text
pixi run ruff check hephaestus/ tests/   # clean
pixi run mypy                            # clean
pixi run pytest tests/unit               # 1990 passed, 7 pre-existing skips, coverage 83.04%
```

### Detection priority (recommended)

1. JSON `is_error` field on **both** the `CalledProcessError` branch and the success branch (exit 0 + `is_error: true`).
2. Stdout text scan (covers both the `result` field and any non-JSON output).
3. Stderr text scan (gh-CLI legacy form, backwards compatibility).

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | PR #126 — E2E checkpoint/resume implementation (v1.0.0 origin) | [Full session notes](../references/notes.md) |
| ProjectHephaestus | `feat/hephaestus-tidy` branch — fixing automation pipeline retry path; every issue died in seconds with empty stderr while logs showed Claude-CLI 429 in stdout JSON | v1.1.0 amendment |

## Related Skills

- `e2e-rate-limit-diagnosis-reset` — Diagnosing experiments after rate-limit damage, resetting affected runs
- `processpoolexecutor-rate-limit-recovery` — Defensive rate-limit recovery in parallel executors
- `github-bulk-issue-filing-rate-limit-recovery` — gh-CLI rate-limit handling in bulk operations
- `ci-cd-github-api-rate-limit-ci-monitoring` — Avoiding gh CLI rate exhaustion in CI loops
- TDD debugging workflow

## Tags

`debugging` `claude-cli` `rate-limit` `429` `usage-cap` `stdout-json` `is_error` `detector-chaining` `or-vs-is-not-none` `python` `regex` `json-parsing` `error-detection` `e2e-testing` `api-errors` `stderr-vs-stdout` `tdd`
