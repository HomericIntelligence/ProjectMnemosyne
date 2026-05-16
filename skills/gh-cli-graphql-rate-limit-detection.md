---
name: gh-cli-graphql-rate-limit-detection
description: "Detect GitHub `gh` CLI rate-limit errors from GraphQL endpoints, whose message format (`GraphQL: API rate limit already exceeded for user ID NNNN`) differs from the REST CLI form (`Limit reached … resets 2:30pm (America/Los_Angeles)`). REST-only regexes silently miss GraphQL errors and burn retries 1s apart against an hour-long window. Use when: (1) automation calls `gh api graphql`, `gh issue list --json …`, `gh issue view`, `gh pr list --json …`, or `gh search` at scale, (2) you see `GraphQL: API rate limit already exceeded for user ID NNNN` in retry storms, (3) your retry loop only knows the REST CLI message format, (4) `gh` exits 0 but stdout JSON contains `errors[].type == \"RATE_LIMITED\"`."
category: tooling
date: 2026-05-15
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - gh-cli
  - github-api
  - graphql
  - rate-limit
  - secondary-limit
  - retry-storm
  - regex
  - error-detection
  - python
  - subprocess
  - automation
  - http-200-errors
---

# gh CLI GraphQL Rate-Limit Detection

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-05-15 |
| **Objective** | Stop ProjectHephaestus automation loop from burning retry budget on `gh issue list --json …` calls that hit GraphQL rate limits but whose error format the existing REST-only detector ignored |
| **Outcome** | Added `GRAPHQL_RATE_LIMIT_RE`, `gh_rate_limit_reset_epoch()` (cached `gh api rate_limit` probe), and `_check_graphql_errors` / `_extract_reset_epoch` / `_handle_rate_limit_attempt` helpers; dedicated `GitHubRateLimitError` for clean batch-driver exit; pre-flight budget probe in shell wrapper |
| **Verification** | verified-ci — ProjectHephaestus PR #412, 2255 unit tests pass, coverage 82.73%, ruff + mypy clean |
| **Repo / PR** | `HomericIntelligence/ProjectHephaestus` PR #412 |

## When to Use

- Building automation that calls `gh api graphql`, `gh issue list --json …`, `gh issue view`, `gh pr list --json …`, or `gh search` at scale.
- You see `GraphQL: API rate limit already exceeded for user ID NNNN` in retry storms (most commonly on stderr from `gh issue list`/`gh issue view`).
- Your retry logic looks like `for attempt in range(max_retries): … detect_rate_limit(stderr)` and only knows the REST CLI message format.
- `gh` exits 0 but stdout JSON contains `{"errors": [{"type": "RATE_LIMITED", "message": "..."}]}` — exit-code checks miss this entirely.
- A shell driver fans out N parallel `gh` processes that each hold their own per-thread throttle — in-process throttles do not coordinate across processes.

**Key indicator**: retry loop logs `transient error, retrying in 1s…` repeatedly for an hour, with stderr containing `GraphQL: API rate limit already exceeded for user ID NNNN` that the detector never matches.

## Verified Workflow

### Quick Reference

```python
import json
import re
import subprocess
import time

# 1. GraphQL rate-limit regex — distinct from REST CLI "Limit reached … resets 2:30pm" form
GRAPHQL_RATE_LIMIT_RE = re.compile(
    r"(?:GraphQL:\s*)?API rate limit (?:already )?exceeded",
    re.IGNORECASE,
)


class GitHubRateLimitError(RuntimeError):
    """Raised when a GraphQL rate-limit is detected; callers catch and exit cleanly."""


# 2. Cached `gh api rate_limit` probe (GraphQL message has no embedded reset time)
_RATE_LIMIT_CACHE: dict[str, tuple[float, int]] = {}
_RATE_LIMIT_TTL_SEC = 30.0


def gh_rate_limit_reset_epoch(resource: str = "graphql") -> int | None:
    """Return Unix epoch when the given GitHub API resource resets; None on probe failure."""
    now = time.time()
    cached = _RATE_LIMIT_CACHE.get(resource)
    if cached and now - cached[0] < _RATE_LIMIT_TTL_SEC:
        return cached[1]
    try:
        result = subprocess.run(
            ["gh", "api", "rate_limit"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        reset = int(data["resources"][resource]["reset"])
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, ValueError):
        return None
    _RATE_LIMIT_CACHE[resource] = (now, reset)
    return reset


# 3. Detector that scans BOTH stderr text and parsed GraphQL JSON errors[]
def _check_graphql_errors(stdout: str) -> bool:
    """Return True if stdout JSON contains a RATE_LIMITED error (HTTP 200 path)."""
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return False
    for err in (data.get("errors") or []):
        if err.get("type") == "RATE_LIMITED":
            return True
        if "rate limit" in (err.get("message") or "").lower():
            return True
    return False


def detect_rate_limit(stderr: str, stdout: str = "") -> bool:
    """Detect both REST and GraphQL rate-limit forms across stderr + stdout JSON."""
    if GRAPHQL_RATE_LIMIT_RE.search(stderr or ""):
        return True
    if stdout and _check_graphql_errors(stdout):
        return True
    return False  # plus existing REST CLI checks


# 4. Retry-loop integration — raise dedicated exception so batch drivers exit cleanly
def _handle_rate_limit_attempt(stderr: str, stdout: str) -> None:
    if not detect_rate_limit(stderr, stdout):
        return
    reset = gh_rate_limit_reset_epoch("graphql")
    raise GitHubRateLimitError(
        f"GraphQL rate limit hit; resets at epoch {reset}" if reset
        else "GraphQL rate limit hit; reset time unknown"
    )
```

```bash
# 5. Pre-flight budget probe inside a shell driver (avoid starting a loop with 0 budget)
remaining=$(gh api rate_limit --jq '.resources.graphql.remaining' 2>/dev/null || echo 0)
if [ "${remaining:-0}" -lt 50 ]; then
    reset=$(gh api rate_limit --jq '.resources.graphql.reset' 2>/dev/null || echo 0)
    echo "GraphQL budget exhausted (remaining=$remaining); next reset epoch=$reset" >&2
    exit 0   # exit clean — let the cron / outer scheduler retry later
fi
```

### Detailed Steps

#### 1. Recognize the two distinct gh CLI rate-limit prose formats

| Source | Example message | Where it lands | Has reset time? |
| ------ | --------------- | -------------- | --------------- |
| REST CLI | `Limit reached for resource X, resets 2:30pm (America/Los_Angeles)` | stderr | Yes (intra-day) |
| GraphQL CLI (most common) | `GraphQL: API rate limit already exceeded for user ID NNNN` | stderr | **No** |
| GraphQL CLI (bare) | `API rate limit exceeded` | inside JSON `errors[].message` | **No** |
| GraphQL CLI (HTTP 200 path) | `{"errors": [{"type": "RATE_LIMITED", "message": "..."}]}` | stdout JSON, exit code **0** | **No** |

The REST regex `r"Limit reached.*resets …"` will not match any of the GraphQL forms. Add a second regex; do not try to fold the formats into one.

#### 2. Resolve the reset time via `gh api rate_limit`

Because the GraphQL message has no embedded reset, query the API for the real epoch:

```bash
gh api rate_limit --jq '.resources.graphql.reset'
```

Cache the result for ~30 seconds — a tight retry loop will otherwise issue a probe per attempt, compounding the rate-limit problem.

#### 3. Detect the HTTP-200-with-errors path

Some GraphQL endpoints return HTTP 200 with a JSON body containing `errors[].type == "RATE_LIMITED"`. `gh` exits 0 in that case, so a retry loop that only inspects exit code + stderr silently treats this as success and proceeds with empty data. Always parse stdout JSON and check `data["errors"]` when the call could be GraphQL.

#### 4. Raise a dedicated exception class

Use `GitHubRateLimitError(RuntimeError)` (or similar) so a batch driver iterating over many repos can `except GitHubRateLimitError` once and exit 0, instead of dumping a 100-line traceback per stuck repo. This also disambiguates rate limits from genuine transient network errors that DO deserve retries.

#### 5. Add a pre-flight budget probe to outer schedulers

Inside an automation loop shell wrapper, query remaining budget before each iteration:

```bash
remaining=$(gh api rate_limit --jq '.resources.graphql.remaining' 2>/dev/null || echo 0)
[ "${remaining:-0}" -lt 50 ] && exit 0   # let the next cron tick retry
```

This prevents starting a 30-call planner phase with only 10 calls of budget.

#### 6. Verify

```bash
pixi run ruff check hephaestus/ tests/
pixi run mypy
pixi run pytest tests/unit -v
```

Expected: clean ruff/mypy, all tests pass, coverage roughly preserved.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Treat `gh issue list --json …` failures as "transient" and retry N times 1s/2s apart | The GraphQL rate-limit window is an hour, not seconds; all N retries fail and the loop burns budget | When the error format is unknown, log raw stderr verbatim and inspect before classifying as transient |
| 2 | Reuse `RATE_LIMIT_RE` (REST form `Limit reached … resets 2:30pm (TZ)`) for GraphQL errors too | GraphQL message is `GraphQL: API rate limit already exceeded for user ID NNNN` — different prefix AND no reset time; regex never matches | Add a sibling regex (`GRAPHQL_RATE_LIMIT_RE`); do not collapse two prose formats into one |
| 3 | Rely solely on stderr parsing for rate-limit detection | GraphQL endpoints can return HTTP 200 with `{"errors": [{"type": "RATE_LIMITED"}]}` in stdout; `gh` exits 0 so exit-code + stderr both look healthy | Parse stdout JSON's `errors[]` array whenever the call could be GraphQL |
| 4 | Use a single shared in-process throttle (`threading.Semaphore` / per-thread token bucket) | Shell driver fans out N parallel `gh` processes; each process holds its own per-thread state, so the aggregate rate is N × per-thread | If you genuinely have parallel processes, use a cross-process flock-backed token bucket (or move the throttle into a wrapper script) |
| 5 | Raise a generic `RuntimeError` on rate limit detection | Batch driver iterating 15 repos dumped a 100-line traceback per stuck repo and exited non-zero | Use a dedicated `GitHubRateLimitError(RuntimeError)` so callers can `except` it and return 0 cleanly |
| 6 | Call `gh api rate_limit` inside the retry loop per attempt | The probe itself counts against the REST `core` budget and adds latency to every retry | Cache the probe result for ~30 seconds so a tight loop reuses one answer |

## Results & Parameters

### Regex (copy-paste ready)

```python
import re

# Matches:
#   "GraphQL: API rate limit already exceeded for user ID 12345"
#   "API rate limit exceeded"  (bare form, inside JSON errors[].message)
GRAPHQL_RATE_LIMIT_RE = re.compile(
    r"(?:GraphQL:\s*)?API rate limit (?:already )?exceeded",
    re.IGNORECASE,
)
```

### Reset-time resolution

| Source | Field | Notes |
| ------ | ----- | ----- |
| `gh api rate_limit` | `.resources.graphql.reset` | Unix epoch; use for GraphQL detections |
| `gh api rate_limit` | `.resources.graphql.remaining` | Pre-flight budget probe |
| `gh api rate_limit` | `.resources.core.reset` | REST CLI fallback |
| Cache TTL | 30 seconds | Avoids probe storm in tight retry loops |

### Detection priority (recommended)

1. Stderr regex (REST form: `Limit reached … resets <time> (<tz>)`).
2. Stderr regex (GraphQL form: `GraphQL: API rate limit already exceeded`).
3. Stdout JSON `errors[].type == "RATE_LIMITED"` (HTTP 200 path).
4. Stdout JSON `errors[].message` containing `"rate limit"` (case-insensitive).

### Exception design

```python
class GitHubRateLimitError(RuntimeError):
    """Raised when a GitHub API rate-limit (REST or GraphQL) is detected.

    Batch drivers catch this and exit 0 (deferred to next cron tick) instead of
    raising a generic transient error and burning the rest of the retry budget.
    """
```

### Code locations (ProjectHephaestus PR #412)

| File | Change |
| ---- | ------ |
| `hephaestus/github/rate_limit.py` | Added `GRAPHQL_RATE_LIMIT_RE`, `gh_rate_limit_reset_epoch()`, updated `detect_rate_limit()` |
| `hephaestus/automation/github_api.py` | Added `GitHubRateLimitError`, `_check_graphql_errors`, `_extract_reset_epoch`, `_handle_rate_limit_attempt` |
| `scripts/run_automation_loop.sh` | Inter-loop budget probe via `gh api rate_limit --jq '.resources.graphql.remaining'` |
| `tests/unit/github/test_rate_limit.py` | Regression tests for GraphQL stderr form, bare form, and HTTP 200 JSON path |
| `tests/unit/automation/test_github_api.py` | Tests for `GitHubRateLimitError` raise behavior and batch-driver clean exit |

### Verification (ProjectHephaestus PR #412)

```text
pixi run ruff check hephaestus/ tests/   # clean
pixi run mypy                            # clean
pixi run pytest tests/unit               # 2255 passed, coverage 82.73%
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHephaestus | PR #412 — automation loop was burning retry budget against an hour-long GraphQL rate-limit window because the existing REST-only detector did not match `GraphQL: API rate limit already exceeded for user ID NNNN` | 2026-05-15, CI green |

## Related Skills

- `e2e-rate-limit-detection` — Claude CLI 429 inside stdout JSON; `0`-sentinel detector chaining (the `or` trap)
- `ci-cd-github-api-rate-limit-ci-monitoring` — Avoiding REST rate exhaustion in CI diagnostic loops
- `github-bulk-issue-filing-rate-limit-recovery` — Secondary (403 BCE2) and org-limit recovery for bulk filing
- `gh-cli-proactive-per-thread-throttle` — Proactive per-thread token-bucket throttle at the `_gh_call` chokepoint
- `processpoolexecutor-rate-limit-recovery` — Defensive rate-limit recovery in parallel executors

## Tags

`tooling` `gh-cli` `github-api` `graphql` `rate-limit` `secondary-limit` `retry-storm` `regex` `error-detection` `python` `subprocess` `automation` `http-200-errors`
