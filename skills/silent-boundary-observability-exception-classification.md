---
name: silent-boundary-observability-exception-classification
description: "Add observability to broad exception boundaries in orchestrator code without changing fail-safe behavior. Use when: (1) a broad `except Exception` boundary is designed for fail-safe/non-blocking behavior but swallows errors silently making bugs hard to debug, (2) you need to surface exceptions to observability systems (logging, monitoring) while preserving the safety contract (returns None, never blocks), (3) exception classification (expected vs unexpected) enables aggregation in log analysis, (4) modules like run_follow_up_issues, planner, or ci_driver need better observability for post-mortem debugging. Pattern: define a module-level tuple of expected exception types, use isinstance() to route to WARNING (expected) or ERROR (unexpected) severity, capture full traceback with exc_info=True, and include exception type as discrete log argument for aggregation."
category: architecture
date: 2026-06-06
version: "1.0.0"
user-invocable: true
verification: verified-local
tags:
  - orchestrator
  - exception-handling
  - observability
  - silent-boundaries
  - fail-safe
  - logging
  - exception-classification
  - debugging
  - incident-response
  - hephaestus-automation
---

# Silent Boundary Observability - Exception Classification Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-06 |
| **Objective** | Preserve fail-safe behavior (return None, never block) in orchestrator code while surfacing exceptions to observability systems so bugs can be detected and debugged post-mortem. |
| **Pattern** | Module-level tuple of expected exception types; isinstance() routing to WARNING (expected) or ERROR (unexpected); exc_info=True for traceback capture; exception type as discrete log argument for aggregation. |
| **Outcome** | Broad exception boundaries remain safe but observable. Expected pipeline failures (e.g., subprocess.CalledProcessError, json.JSONDecodeError) log at WARNING and don't trigger alerts. Unexpected exceptions (e.g., AttributeError, TypeError) log at ERROR and surface to on-call. Traceback captured for post-mortem analysis. |
| **Verification** | verified-local — Implemented in ProjectHephaestus issue #807 (`run_follow_up_issues`); all unit tests pass; integration with follow_up module verified. |

## When to Use

Trigger phrases that should route to this skill:

- "broad exception boundary swallows errors silently"
- "except Exception catches bugs we never see"
- "orchestrator code needs observability without changing safety"
- "pipeline failure hard to debug because exception is muted"
- "fail-safe code path needs better visibility"
- "distinguish expected from unexpected errors in broad catches"
- "exception not surfaced to observability systems"
- "silent boundary hiding genuine bugs"
- "run_follow_up_issues swallows exceptions"
- "planner.py silent catch-all boundary"
- "ci_driver.py needs exception classification"
- "post-mortem debugging of orchestrator crash"
- "aggregable exception types in logs"
- "non-blocking code path needs observability"

Trigger situations:

- Broad `except Exception` boundary designed for fail-safe behavior (returns None, never blocks on error)
- Exceptions being silently swallowed with no logging, making bugs hard to detect
- Orchestrator modules (automation, workflow coordination) where errors should surface to observability
- Need to distinguish between "expected pipeline failures" (log WARNING) and "unexpected bugs" (log ERROR)
- Post-mortem debugging of orchestrator behavior; traceback required but not available
- Aggregate exception types across a fleet in log analysis; exception type must be discrete argument

## Verified Workflow

### Quick Reference

Define a module-level tuple of expected exceptions:

```python
# At module level, before any functions
_EXPECTED_FOLLOW_UP_FAILURES = (
    subprocess.CalledProcessError,
    json.JSONDecodeError,
    OSError,
)
```

Use isinstance() to classify and route to appropriate severity:

```python
def run_follow_up_issues(...) -> None:
    """Run follow-up issue creation loop. Returns None on error (fail-safe)."""
    try:
        # ... do work ...
    except _EXPECTED_FOLLOW_UP_FAILURES as e:
        logger.warning(
            "follow-up pipeline failed (expected failure type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            "follow-up pipeline failed (unexpected exception type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
    # Always return — never re-raise, never block
    return None
```

Include exception type as discrete log argument for aggregation:

```python
# In observability system / log aggregation:
# Group by "exception_type" field enables:
# - "CalledProcessError across all follow-up runs"
# - "OSError burst indicates filesystem issue"
# - "Unexpected types flagged by ERROR severity"
```

### Detailed Steps

#### 1. Identify the broad exception boundary

Find the orchestrator function with `except Exception` (or bare `except`) that's designed for fail-safe behavior:

```python
def run_follow_up_issues(...) -> None:
    try:
        # ... orchestrator loop ...
    except Exception:
        # Silently swallow — PROBLEM: no observability
        pass
    return None
```

Confirm the safety contract: does this always return None? Never raise? Never block? If yes, it's safe to add logging without changing control flow.

#### 2. Classify expected exception types

Enumerate the exceptions that represent "normal pipeline failures" — subprocess exited non-zero, JSON malformed, file not found, etc. These should be rare but expected in a production pipeline:

```python
_EXPECTED_FOLLOW_UP_FAILURES = (
    subprocess.CalledProcessError,  # Tool exited non-zero
    json.JSONDecodeError,            # API response malformed
    OSError,                         # File I/O, permissions, network
)
```

Place this tuple at module level (above functions) so it's a single source of truth for classification.

#### 3. Use isinstance() to route to different severity

Replace the bare `except Exception` with two handlers:

```python
def run_follow_up_issues(...) -> None:
    try:
        # ... orchestrator loop ...
    except _EXPECTED_FOLLOW_UP_FAILURES as e:
        # Expected failure type — log at WARNING, no alert
        logger.warning(
            "follow-up pipeline failed (expected failure type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
    except Exception as e:
        # Unexpected exception — log at ERROR, trigger alert
        logger.error(
            "follow-up pipeline failed (unexpected exception type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
```

**Key points**:
- **Order matters**: specific expected types first, catch-all second
- **exc_info=True**: captures full traceback in logger output for post-mortem
- **extra={"exception_type": ...}**: discrete log argument enables aggregation in observability systems
- **Always return**: preserve fail-safe contract; never re-raise or change control flow

#### 4. Enrich on-disk logs with exception context

For additional debugging, write the exception type and traceback to on-disk logs (if your logger writes to file):

```python
except Exception as e:
    logger.error(
        "follow-up pipeline failed",
        extra={
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )
```

Or use a second logger for detailed forensics:

```python
forensics_logger = logging.getLogger("hephaestus.forensics")
forensics_logger.error(
    "follow-up exception details",
    extra={"exception": traceback.format_exc()},
)
```

#### 5. Test the classification behavior

Write unit tests that verify expected vs unexpected routing:

```python
def test_follow_up_expected_failure_logs_warning(caplog):
    """CalledProcessError should log at WARNING."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
        with caplog.at_level("WARNING"):
            run_follow_up_issues(...)

    assert "expected failure type" in caplog.text
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].exception_type == "CalledProcessError"

def test_follow_up_unexpected_failure_logs_error(caplog):
    """AttributeError should log at ERROR."""
    with patch("some.function", side_effect=AttributeError("bad attr")):
        with caplog.at_level("ERROR"):
            run_follow_up_issues(...)

    assert "unexpected exception type" in caplog.text
    assert caplog.records[0].levelname == "ERROR"
    assert caplog.records[0].exception_type == "AttributeError"

def test_follow_up_always_returns_none(caplog):
    """Even on exception, must return None (fail-safe contract)."""
    with patch("subprocess.run", side_effect=RuntimeError("boom")):
        result = run_follow_up_issues(...)

    assert result is None
```

Verify that expected exceptions log at WARNING, unexpected at ERROR, and the function always returns None.

#### 6. Wire into observability/alerting

Point observability systems at the discrete `exception_type` field for aggregation:

- **Log aggregation**: "Show me all CalledProcessError in run_follow_up_issues"
- **Alerting**: "Alert on ERROR severity exceptions (unexpected types only)"
- **On-call dashboard**: Exception types and counts enable pattern detection
- **Post-mortem**: exc_info=True includes full traceback in logs

### Side-by-side: Before and After

**Before** (silent boundary):

```python
def run_follow_up_issues(config: Config) -> None:
    try:
        for issue in pending_issues:
            response = gh_api_call(...)  # May raise CalledProcessError
            issues = json.loads(response)  # May raise JSONDecodeError
            create_follow_up(...)  # May raise OSError
    except Exception:
        # Silent — bugs go undetected, alert never fires
        pass
```

**After** (observable boundary):

```python
_EXPECTED_FOLLOW_UP_FAILURES = (
    subprocess.CalledProcessError,
    json.JSONDecodeError,
    OSError,
)

def run_follow_up_issues(config: Config) -> None:
    try:
        for issue in pending_issues:
            response = gh_api_call(...)
            issues = json.loads(response)
            create_follow_up(...)
    except _EXPECTED_FOLLOW_UP_FAILURES as e:
        logger.warning(
            "follow-up pipeline failed (expected failure type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            "follow-up pipeline failed (unexpected exception type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | --------------- | --------------- | --------------- |
| Narrow the exception type to specific expected ones | Changed `except Exception` to `except subprocess.CalledProcessError` alone | Missed other legitimate pipeline failures (JSONDecodeError, OSError) that also need non-blocking behavior. Would have hidden genuine bugs. | The broad boundary is *intentional* — for fail-safe behavior. Don't narrow it. Instead, classify exceptions WITHIN the broad catch to distinguish expected from unexpected. |
| Log at ERROR for all exceptions | Added logging to bare `except Exception: logger.error(...)` | Floods alerts with expected pipeline failures (missing files, API errors). Ops team gets alert fatigue and stops reacting to error logs. Observability becomes noise. | Route by exception type: WARNING for expected (pipeline failures), ERROR for unexpected (bugs). Only error-level logs trigger alerts. |
| No discrete exception_type argument | Logged full exception in message: `logger.error(f"Exception: {type(e).__name__}: {e}")` | Exception details are part of the log message string. Can't aggregate across instances in log analysis. Searching for "CalledProcessError" finds message noise, not structured exception types. | Always include `extra={"exception_type": ...}` as a discrete log field. Enables faceted search / filtering / aggregation in observability systems. |
| Skip exc_info=True | Logged only message without traceback | When debugging post-mortem, traceback was absent. Stack trace essential for understanding the failure chain in orchestrator code. Re-running locally didn't produce the same exception, so logs alone insufficient. | Always pass `exc_info=True` (or `exc_info=e`) so the full traceback is captured in logger output. Non-negotiable for post-mortem debugging. |
| Preserve re-raise for bug visibility | On unexpected exceptions: `except Exception as e: logger.error(...); raise` | Violates the safety contract. Orchestrator crashes with unhandled exception, blocking the entire loop. That's the opposite of fail-safe. Re-raising defeats the purpose of the broad boundary. | The broad boundary is *designed* to be fail-safe (non-blocking). Never re-raise. The safety contract is intentional and must be preserved. Observability is a side-channel, not permission to change control flow. |
| Single log call for expected and unexpected | `except Exception as e: logger.log(level=..., ...)` with conditional level | Conditional logic for level assignment is fragile; easy to misclassify. And still floods with unexpected exceptions if not careful. Explicit two-handler approach is clearer and less error-prone. | Use two explicit except handlers: specific expected types first, catch-all unexpected second. No conditional logic. Clear intent. |

## Results & Parameters

### Implementation in ProjectHephaestus issue #807

**File**: `hephaestus/automation/follow_up.py`

**Code pattern applied** (lines 467-490):

```python
_EXPECTED_FOLLOW_UP_FAILURES = (
    subprocess.CalledProcessError,
    json.JSONDecodeError,
    OSError,
)

def run_follow_up_issues(
    config: Config,
    issues: list[int],
    github: GitHub,
) -> None:
    """Generate and create follow-up issues for completed tasks.

    Returns None on any error — this is a fail-safe operation designed
    to never block the automation loop.
    """
    try:
        # ... orchestrator loop ...
    except _EXPECTED_FOLLOW_UP_FAILURES as e:
        logger.warning(
            "follow-up pipeline failed (expected failure type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            "follow-up pipeline failed (unexpected exception type)",
            extra={"exception_type": type(e).__name__},
            exc_info=True,
        )
```

**Three acceptance tests**:

1. `test_follow_up_expected_subprocess_error_logs_warning` — CalledProcessError → WARNING severity
2. `test_follow_up_unexpected_attribute_error_logs_error` — AttributeError → ERROR severity
3. `test_follow_up_always_returns_none` — Both cases preserve fail-safe contract (return None)

### Pattern applicability

This pattern applies to other orchestrator modules with broad exception boundaries:

- **`hephaestus/automation/planner.py`** (line 465) — planning loop with broad exception boundary
- **`hephaestus/automation/ci_driver.py`** — multi-repo CI driving loop
- **`hephaestus/agents/runtime.py`** — agent execution loop
- Any fail-safe code path where exceptions are intentionally not re-raised

Expected exception types vary by module:

- **Planner**: `subprocess.CalledProcessError`, `json.JSONDecodeError`, `ValueError` (schema)
- **CI driver**: `subprocess.CalledProcessError`, `KeyError` (GitHub API), `TimeoutError`
- **Agent runtime**: `json.JSONDecodeError`, `AttributeError` (agent config), `ImportError` (skill loading)

### Verification commands

After applying the pattern, verify observability:

```bash
# Run the module with exceptions and check log output
pixi run python -m hephaestus.automation.follow_up --config test.yaml

# Expected output:
# WARNING: follow-up pipeline failed (expected failure type)
#   exception_type: CalledProcessError
#   Traceback (most recent call last): ...

# On-disk logs (usually stderr or file) should show:
# [WARNING] follow-up ... exception_type=CalledProcessError ...
# [ERROR] follow-up ... exception_type=AttributeError (if unexpected) ...

# Run unit tests to confirm classification
pixi run pytest tests/unit/automation/test_follow_up.py -v

# Expected: all three acceptance tests PASS
# - test_follow_up_expected_subprocess_error_logs_warning PASSED
# - test_follow_up_unexpected_attribute_error_logs_error PASSED
# - test_follow_up_always_returns_none PASSED
```

## Key Learnings

1. **Preserve the safety contract** — Broad exception boundaries in orchestrators are *intentional* for fail-safe behavior. Don't narrow them or add re-raises. Observability is a side-channel; control flow is off-limits.

2. **Classification via module-level tuple** — Define a single source of truth (`_EXPECTED_FOLLOW_UP_FAILURES`) for which exceptions are "normal" in the pipeline. Prevents classification logic from fragmenting across the codebase.

3. **Severity routing enables sane alerting** — WARNING for expected (CalledProcessError, OSError) won't trigger pages. ERROR for unexpected (AttributeError, TypeError) will. Ops team gets signal instead of noise.

4. **Traceback capture is non-negotiable** — exc_info=True is mandatory for post-mortem debugging. When a bug manifests in production, the stack trace is essential for root-cause analysis.

5. **Discrete exception_type argument enables aggregation** — Don't embed the exception type in the message string. Use `extra={"exception_type": ...}` so log analysis tools can group and count by exception type across the fleet.

6. **Three-tier observability** — (1) Logger captures the event with severity; (2) discrete field enables filtering/grouping; (3) exc_info=True provides the traceback for investigation. Together they enable detection, triage, and debugging.

## Verified On

| Project | Module | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | `hephaestus/automation/follow_up.py` | Issue #807: Exception classification pattern applied to `run_follow_up_issues`. All unit tests pass. Integration with follow_up module verified. Accepted as foundation for extending pattern to planner.py and ci_driver.py. |

## References

- [ProjectHephaestus issue #807 - improve observability for follow_up failure logging](https://github.com/HomericIntelligence/ProjectHephaestus/issues/807)
- [ProjectHephaestus follow_up.py - run_follow_up_issues orchestrator](https://github.com/HomericIntelligence/ProjectHephaestus/blob/main/hephaestus/automation/follow_up.py#L467)
- [Python logging — exc_info parameter](https://docs.python.org/3/library/logging.html#logging.Logger.exception)
- [Structured logging — discrete fields for aggregation](https://www.kartar.net/2015/12/structured-logging/)
- [Fail-safe design pattern — safety contracts](https://en.wikipedia.org/wiki/Fail-safe)
