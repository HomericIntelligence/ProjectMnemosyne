---
name: e2e-rate-limit-detection
description: Debugging rate limit detection when error messages appear in JSON response fields instead of stderr
category: debugging
date: 2026-01-04
---

# E2E Rate Limit Detection: JSON vs Stderr Parsing

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-04 |
| Objective | | Field | Value | |-------|-------| | **Date** | 2026-01-04 | | **Project** | ProjectScylla | | **Objective** | Fix rate limit detection failing to... |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| **Date** | 2026-01-04 |
| **Project** | ProjectScylla |
| **Objective** | Fix rate limit detection failing to catch errors in agent JSON output that were reaching the fallback judge |
| **Outcome** | ✅ Success - Bug identified and fixed with comprehensive test coverage |
| **Impact** | High - Enables overnight E2E test runs to properly pause/resume on rate limits from agent output |

## When to Use This Skill

Use this skill when:

1. **Rate limits aren't being detected** from API responses that return JSON with error fields
2. **Error detection works for stderr but not stdout** - your code parses stderr but the actual error message is in JSON stdout
3. **Time-based rate limits fail to parse** - messages like "resets 4pm (timezone)" aren't being extracted from JSON response bodies
4. **Fallback error handlers are catching what should be rate limits** - errors are bypassing rate limit detection logic
5. **Writing rate limit detection for JSON APIs** - especially Claude CLI, Anthropic API, or similar structured error responses

**Key Indicator**: You see error messages like `"is_error": true, "result": "You've hit your limit · resets 4pm"` in logs, but your rate limit handler isn't triggering.

## Verified Workflow

### 1. Identify the Bug Pattern

**Symptom**: Rate limit detection works for some cases but not others.

**Investigation**:
```bash
# Check actual error output from failing cases
grep -r "hit your limit\|rate limit" results/ --include="report.md"

# Examine the JSON structure
cat results/*/T1/*/run_*/report.md | grep -A 5 "Agent Output"
```

**Finding**: Rate limit messages appear in JSON `result` field:
```json
{
  "is_error": true,
  "result": "You've hit your limit · resets 4pm (America/Los_Angeles)"
}
```

### 2. Locate the Parsing Bug

**Look for code that**:
- Detects `is_error: true` in JSON ✓
- Extracts the error message ✓
- **Parses retry time from stderr only** ✗ (BUG)

**Example bug** (from `src/scylla/e2e/rate_limit.py:177`):
```python
# Detects rate limit from JSON
if data.get("is_error"):
    error_msg = str(result)  # Has the "resets 4pm" message

    # BUG: Only checks stderr, but error_msg has the time info!
    retry_after = parse_retry_after(stderr)
```

### 3. Fix: Check Error Message First

**Solution**: Parse from the error message field before falling back to stderr.

```python
# FIXED: Try error message first, then stderr
retry_after = parse_retry_after(error_msg) or parse_retry_after(stderr)
```

**Why this works**:
- Claude CLI JSON output puts rate limit details in `result` field
- `error_msg` contains: "You've hit your limit · resets 4pm (America/Los_Angeles)"
- `parse_retry_after()` can extract time from this string
- Stderr fallback ensures backwards compatibility

### 4. Write Tests FIRST (TDD Approach)

**Critical test cases**:

```python
def test_detect_from_json_is_error_hit_limit():
    """Verify the exact bug we're fixing."""
    stdout = json.dumps({
        "is_error": True,
        "result": "You've hit your limit · resets 4pm (America/Los_Angeles)"
    })

    info = detect_rate_limit(stdout, stderr="", source="agent")

    assert info is not None
    assert "hit your limit" in info.error_message.lower()
    assert info.retry_after_seconds is not None  # Must parse time from JSON
```

**Additional coverage**:
- JSON detection with various rate limit keywords
- Stderr fallback for legacy formats
- Time parsing from multiple formats (Retry-After header, "resets 4pm", etc.)
- Integration tests for full detection → wait flow

### 5. Verify Fix with Real Data

```bash
# Run tests
pixi run pytest tests/unit/e2e/test_rate_limit.py -v

# Check previous failures would now be caught
# (Review actual error messages from your failing test runs)
```

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| Adding "hit your limit" keyword detection only | Detection triggered but retry time was `None` - still failed to wait properly | Keywords alone aren't enough; must parse time from correct source |
| Checking stderr for "resets 4pm" pattern | Pattern not in stderr for JSON responses - it's in the JSON result field | Don't assume error details are in stderr; check actual JSON structure |
| Adding time parsing without testing against real data | Didn't catch the stdout vs stderr issue until examining actual failing reports | Always test with real-world examples from production failures |

## Results & Parameters

### Detection Patterns (Copy-Paste Ready)

**Keywords that trigger rate limit detection**:
```python
RATE_LIMIT_KEYWORDS = [
    "rate limit",
    "rate_limit",
    "ratelimit",
    "overloaded",
    "429",
    "hit your limit",
    "resets",
]
```

**Time format patterns**:
- `Retry-After: <seconds>` (HTTP header)
- `resets 4pm (America/Los_Angeles)` (Claude CLI format)
- `resets 12am` (midnight reset)
- `resets 11:30pm` (with minutes)

**Buffer**: Add 10% to all parsed retry times for safety.

### Code Locations (ProjectScylla)

| File | Line | Change |
|------|------|--------|
| `src/scylla/e2e/rate_limit.py` | 177-178 | Parse error_msg before stderr |
| `tests/unit/e2e/test_rate_limit.py` | - | Added 31 comprehensive tests |

### Test Coverage

**31 tests** covering:
- RateLimitInfo dataclass validation
- RateLimitError exception handling
- `parse_retry_after()` with Retry-After headers and "resets 4pm" format
- `detect_rate_limit()` from JSON `is_error` field (bug fix verification)
- `detect_rate_limit()` from stderr patterns (backwards compatibility)
- `wait_for_rate_limit()` checkpoint updates
- Integration tests for full rate limit flow

**Key test for bug fix**: `test_detect_from_json_is_error_hit_limit`

### Detection Priority

1. **JSON `is_error` field** (primary) - checks stdout
2. **Stderr patterns** (fallback) - backwards compatibility

### Time Parsing Priority

1. **Error message from JSON** (primary) - `parse_retry_after(error_msg)`
2. **Stderr** (fallback) - `parse_retry_after(stderr)`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #126 - E2E checkpoint/resume implementation | [Full session notes](../references/notes.md) |

## Related Skills

- `evaluation/e2e-checkpoint-resume` - Checkpoint/resume context where this bug was discovered
- Generic JSON error parsing patterns
- TDD debugging workflow

## Tags

`debugging` `rate-limit` `json-parsing` `error-detection` `e2e-testing` `api-errors` `stderr-vs-stdout` `tdd`
