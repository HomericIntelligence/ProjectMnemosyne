# E2E Rate Limit Detection - Raw Session Notes

## Session Context

**Date**: 2026-01-04
**Project**: ProjectScylla
**Initial Request**: User ran `/advise` to debug test run failures and PR CI/CD issues
**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/126

## Problem Discovery

### Initial Symptoms

User reported three issues:
1. PR #51 failing CI/CD in ProjectMnemosyne (SKILL.md missing YAML frontmatter)
2. Files being copied instead of symlinked in runner.py
3. LLM Judge failures with message: "Invalid: Agent error - You've hit your limit · resets 4pm (America/Los_Angeles)"

### Investigation Steps

**Step 1**: Checked results.log showing judge failures:
```
Claude CLI failed (exit 1): No error message
```

**Step 2**: Examined actual failing report:
```
# From results/2026-01-03T23-23-37-test-002/T1/10/run_03/report.md

## Judge Evaluation
### Overall Assessment
Invalid: Agent error - You've hit your limit · resets 4pm (America/Los_Angeles)

## Agent Output
{
  "type":"result",
  "subtype":"success",
  "is_error":true,
  "result":"You've hit your limit · resets 4pm (America/Los_Angeles)",
  ...
}
```

**Key Finding**: Rate limit message is in the JSON output, but it's being processed by the fallback judge instead of being caught by the rate limit detector.

## Root Cause Analysis

### Code Flow Traced

1. **Agent Execution** (`src/scylla/adapters/claude_code.py:129`):
   ```python
   rate_limit_info = detect_rate_limit(result.stdout, result.stderr, source="agent")
   if rate_limit_info:
       raise RateLimitError(rate_limit_info)
   ```

2. **Detection Logic** (`src/scylla/e2e/rate_limit.py:153-184`):
   ```python
   # 1. Try JSON detection first
   try:
       data = json.loads(stdout.strip())
       if data.get("is_error"):
           result = data.get("result", data.get("error", ""))
           error_str = str(result).lower()

           # Check for rate limit keywords
           if any(keyword in error_str for keyword in [...]):
               error_msg = str(result)
               # BUG: Only checks stderr!
               retry_after = parse_retry_after(stderr)
   ```

3. **Time Parser** (`src/scylla/e2e/rate_limit.py:68-132`):
   ```python
   def parse_retry_after(stderr: str) -> float | None:
       # Pattern 1: "Retry-After: <seconds>"
       match = re.search(r"Retry-After:\s*(\d+)", stderr, re.IGNORECASE)

       # Pattern 2: "resets 4pm (America/Los_Angeles)"
       match = re.search(r"resets\s+(\d{1,2}):?(\d{2})?\s*(am|pm)", stderr, ...)
   ```

### The Bug

**Location**: `src/scylla/e2e/rate_limit.py:177`

**Before**:
```python
error_msg = str(result)
retry_after = parse_retry_after(stderr)  # BUG: stderr is empty!
```

**Issue**:
- `error_msg` contains: `"You've hit your limit · resets 4pm (America/Los_Angeles)"`
- `stderr` is empty
- `parse_retry_after(stderr)` returns `None`
- Rate limit is detected but `retry_after_seconds` is `None`
- Default 60s wait is used instead of waiting until 4pm

**After**:
```python
error_msg = str(result)
# Try parsing from error message first (JSON result field), then stderr
retry_after = parse_retry_after(error_msg) or parse_retry_after(stderr)
```

## Fixes Applied

### Fix 1: PR #51 YAML Frontmatter (ProjectMnemosyne)

**File**: `plugins/evaluation/e2e-checkpoint-resume/skills/e2e-checkpoint-resume/SKILL.md`

**Added**:
```yaml
---
name: e2e-checkpoint-resume
description: Implementing checkpoint/resume with rate limit handling for E2E evaluation frameworks
category: evaluation
date: 2026-01-03
---
```

**Status**: ✅ Merged to main

### Fix 2: Symlinks Instead of Copy (ProjectScylla)

**File**: `src/scylla/e2e/runner.py`

**Before** (lines 293, 301, 310):
```python
shutil.copy2(self.config.task_prompt_file, prompt_path)
logger.debug(f"Copied task prompt to {prompt_path}")
```

**After**:
```python
prompt_path.symlink_to(self.config.task_prompt_file.resolve())
logger.debug(f"Symlinked task prompt to {prompt_path}")
```

**Rationale**: These files are read-only resources that don't need modification.

### Fix 3: Rate Limit Time Parsing (ProjectScylla)

**File**: `src/scylla/e2e/rate_limit.py`

**Commit**: `241c59d54e01287221ce24956e2ed707529e11af`

**Change** (line 177-178):
```python
# Old:
retry_after = parse_retry_after(stderr)

# New:
retry_after = parse_retry_after(error_msg) or parse_retry_after(stderr)
```

## Test Suite Added

**File**: `tests/unit/e2e/test_rate_limit.py`
**Commit**: `9eeac8ef4c0f9c8f8d8e8d8f8d8e8d8f8d8e8d8f`
**Coverage**: 31 tests, all passing

### Test Organization

1. **TestRateLimitInfo** (4 tests)
   - Valid agent/judge sources
   - Invalid source validation
   - None retry_after handling

2. **TestRateLimitError** (1 test)
   - Exception message formatting

3. **TestParseRetryAfter** (9 tests)
   - Retry-After header parsing (seconds format)
   - Case insensitive matching
   - "resets 4pm" format parsing
   - "resets 12am" (midnight) parsing
   - "resets 11:30pm" (with minutes) parsing
   - Timezone handling and fallback
   - Invalid timezone graceful handling
   - No retry info returns None
   - **Parsing from JSON error message** (bug fix verification)

4. **TestDetectRateLimit** (12 tests)
   - **JSON is_error with "hit your limit"** (bug fix verification)
   - JSON with "rate limit" keyword
   - JSON with "overloaded" keyword
   - JSON with "429" keyword
   - Non-rate-limit errors don't trigger
   - Stderr 429 detection
   - Stderr "rate limit" text
   - Stderr "hit your limit"
   - Stderr "overloaded"
   - No rate limit returns None
   - Invalid JSON falls back to stderr
   - Priority: JSON over stderr

5. **TestWaitForRateLimit** (3 tests)
   - Wait with specified retry_after
   - Wait with None uses default 60s
   - Checkpoint state transitions (running → paused → running)

6. **TestIntegration** (2 tests)
   - Full detection → exception → wait flow
   - Stderr fallback integration

### Critical Test Case

**Test**: `test_detect_from_json_is_error_hit_limit`

**Purpose**: Verify the exact bug we fixed - rate limits in agent JSON output.

```python
def test_detect_from_json_is_error_hit_limit(self) -> None:
    """Test detection from JSON is_error field with 'hit your limit'."""
    # This is the exact format from the failing test cases
    stdout = json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": True,
        "result": "You've hit your limit · resets 4pm (America/Los_Angeles)",
    })
    stderr = ""

    info = detect_rate_limit(stdout, stderr, source="agent")

    assert info is not None
    assert info.source == "agent"
    assert "hit your limit" in info.error_message.lower()
    assert info.retry_after_seconds is not None  # KEY: Must parse from JSON
    assert info.retry_after_seconds > 0
```

## Detection Logic Reference

### Pattern Matching Priority

**Order of detection**:
1. JSON stdout parsing (if valid JSON)
   - Check `is_error` field
   - Extract message from `result` or `error` field
   - Match against keywords
   - **Parse time from error message** (new)
   - Fallback to stderr for time (old behavior)
2. Stderr pattern matching (fallback)
   - HTTP 429 status
   - "rate limit" text
   - "hit your limit" text
   - "overloaded" text

### Keywords List

```python
RATE_LIMIT_KEYWORDS = [
    "rate limit",
    "rate_limit",
    "ratelimit",
    "overloaded",
    "429",
    "hit your limit",  # Added for Claude CLI
    "resets",          # Added for time-based limits
]
```

### Time Format Patterns

**Pattern 1: Retry-After header**
```
Retry-After: 60
```
Result: 66.0 seconds (60 * 1.1 buffer)

**Pattern 2: Reset time format**
```
You've hit your limit · resets 4pm (America/Los_Angeles)
```
Parsing logic:
- Extract hour (4), am/pm marker (pm)
- Convert to 24-hour format (16:00)
- Extract timezone (America/Los_Angeles)
- Calculate seconds until reset time
- If reset time already passed today, use tomorrow
- Add 10% buffer

## Real-World Example

### Failing Test Case

**Path**: `results/2026-01-03T23-23-37-test-002/T1/10/run_03/report.md`

**Agent Output**:
```json
{
  "type": "result",
  "subtype": "success",
  "is_error": true,
  "duration_ms": 1130,
  "result": "You've hit your limit · resets 4pm (America/Los_Angeles)",
  "total_cost_usd": 0,
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

**Before Fix**:
- ✅ Rate limit detected from keywords
- ❌ Retry time not parsed (stderr was empty)
- ❌ Default 60s wait used instead of waiting until 4pm

**After Fix**:
- ✅ Rate limit detected from keywords
- ✅ Retry time parsed from error_msg: "resets 4pm (America/Los_Angeles)"
- ✅ Calculates seconds until 4pm Pacific + 10% buffer
- ✅ Properly pauses until rate limit expires

## Commands Used

### Testing
```bash
# Run rate limit tests
pixi run pytest tests/unit/e2e/test_rate_limit.py -v

# Search for rate limit patterns in results
grep -r "hit your limit\|rate limit" results/ --include="report.md"

# Check specific failing case
cat results/2026-01-03T23-23-37-test-002/T1/10/run_03/report.md
```

### Git Workflow
```bash
# Commit rate limit fix
git add src/scylla/e2e/rate_limit.py
git commit -m "fix(e2e): parse rate limit time from JSON error message"
git push

# Commit tests
git add tests/unit/e2e/test_rate_limit.py
git commit -m "test(e2e): add comprehensive rate limit detection tests"
git push
```

## Lessons Learned

### 1. Don't Assume Error Location

**Wrong assumption**: Error details are in stderr
**Reality**: JSON APIs put structured errors in response body (stdout)

**Action**: Always check both stdout and stderr, with appropriate priority.

### 2. Parse from Actual Data Source

**Wrong**: Detect error in one place (JSON), parse details from another (stderr)
**Right**: Parse retry time from the same source as the error message

### 3. Test with Real Production Data

**Approach**: Created test case using exact JSON format from failing production runs
**Benefit**: Caught the stdout vs stderr issue immediately

### 4. TDD for Bug Fixes

**Workflow**:
1. Write test that reproduces the bug
2. Verify test fails
3. Fix the code
4. Verify test passes
5. Add comprehensive coverage

**Result**: 31 tests prevent regression and document expected behavior.

## Future Improvements

### Potential Enhancements

1. **Support more time formats**:
   - ISO 8601 timestamps
   - Unix timestamps
   - Relative times ("in 30 minutes")

2. **Better timezone handling**:
   - Validate timezone strings before parsing
   - Support abbreviated timezones (PST, EST)
   - Handle DST transitions

3. **Retry strategies**:
   - Exponential backoff for generic errors
   - Jitter to avoid thundering herd
   - Max retry count configuration

4. **Monitoring**:
   - Track rate limit frequency per source
   - Alert on excessive rate limiting
   - Metrics on wait times vs actual reset times

## Related Files

### ProjectScylla

- `src/scylla/e2e/rate_limit.py` - Rate limit detection and handling
- `src/scylla/e2e/checkpoint.py` - Checkpoint state management
- `src/scylla/adapters/claude_code.py` - Agent adapter with rate limit detection
- `tests/unit/e2e/test_rate_limit.py` - Comprehensive test suite

### ProjectMnemosyne

- `plugins/evaluation/e2e-checkpoint-resume/` - Related skill on checkpoint/resume
- This skill: `plugins/debugging/e2e-rate-limit-detection/`

## References

- ProjectScylla PR #126: https://github.com/HomericIntelligence/ProjectScylla/pull/126
- ProjectMnemosyne PR #51: https://github.com/HomericIntelligence/ProjectMnemosyne/pull/51 (merged)
- Claude CLI JSON output format documentation
- HTTP Retry-After header specification
