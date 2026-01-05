# Skill: Adding Retry Logic for Transient Errors

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Fix git clone failures caused by transient network errors ("Connection reset by peer", "curl 56") |
| **Outcome** | ✅ Successfully implemented exponential backoff retry logic with comprehensive tests |
| **Files Modified** | `src/scylla/e2e/workspace_manager.py`, `tests/unit/e2e/test_workspace_manager.py` |
| **PR** | #146 (merged) |

## When to Use This Skill

Use this skill when:

1. **Intermittent failures** occur during external operations (network calls, file I/O, subprocess execution)
2. **Error messages indicate transient issues**:
   - "Connection reset by peer"
   - "Network unreachable"
   - "Operation timed out"
   - "Temporary failure"
   - "curl 56" (RPC failed)
   - "early EOF"
3. **Operations should succeed on retry** (not permanent errors like authentication or "not found")
4. **No existing retry logic** is present in the code

**Red Flags** - When NOT to add retry logic:
- Permanent errors (authentication failed, resource not found, permission denied)
- Logic errors or bugs in code
- User input validation failures
- Configuration errors

## Verified Workflow

### 1. Identify the Failure Point

**What worked:**
- Read the error logs to identify the exact subprocess call or operation that's failing
- Check if error message indicates transient vs permanent failure
- Example: `"RPC failed; curl 56 Recv failure: Connection reset by peer"` → transient network error

**Location:** `workspace_manager.py:74-81` - single `subprocess.run()` call with no error handling

### 2. Categorize Error Patterns

**What worked:**
- Create a list of transient error patterns to detect in `stderr`
- Use lowercase comparison for case-insensitive matching
- Include both general patterns and specific error codes

**Transient patterns identified:**
```python
transient_patterns = [
    "connection reset",
    "connection refused",
    "network unreachable",
    "network is unreachable",  # Include variations
    "temporary failure",
    "could not resolve host",
    "curl 56",  # Specific RPC error code
    "timed out",
    "early eof",
    "recv failure",
]
```

### 3. Implement Exponential Backoff Retry

**What worked:**
- Use 3 total attempts (initial + 2 retries) - matches project's error-handling.md standard
- Base delay: 1.0 seconds
- Exponential: `delay = base_delay * (2 ** attempt)` → 1s, 2s, 4s
- Break on success, sleep only between failed attempts

**Code pattern:**
```python
max_retries = 3
base_delay = 1.0

for attempt in range(max_retries):
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        break  # Success - exit retry loop

    stderr = result.stderr.lower()
    is_transient = any(pattern in stderr for pattern in transient_patterns)

    # Fail immediately on non-transient errors or last attempt
    if not is_transient or attempt == max_retries - 1:
        raise RuntimeError(f"Failed: {result.stderr}")

    # Exponential backoff
    delay = base_delay * (2 ** attempt)
    logger.warning(f"Retry {attempt+1}/{max_retries} in {delay}s: {result.stderr.strip()}")
    time.sleep(delay)
```

### 4. Add Comprehensive Tests

**What worked:**
- Use `unittest.mock` to simulate transient failures
- Test multiple scenarios:
  - ✅ Success on first attempt
  - ✅ Retry succeeds on 2nd/3rd attempt
  - ✅ Exponential backoff timing verification
  - ✅ Immediate failure on auth/not-found errors
  - ✅ Exhausted retries raises error
  - ✅ Idempotent behavior
  - ✅ Case-insensitive error detection

**Test pattern:**
```python
def test_retry_on_transient_error(self, tmp_path: Path) -> None:
    """Test retry succeeds on second attempt."""
    fail_result = MagicMock()
    fail_result.returncode = 1
    fail_result.stderr = "curl 56 Recv failure: Connection reset by peer"

    success_result = MagicMock()
    success_result.returncode = 0

    with patch("subprocess.run", side_effect=[fail_result, success_result]):
        with patch("time.sleep") as mock_sleep:
            manager.setup_base_repo()

    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args == call(1.0)  # First retry = 1s
```

### 5. Document in Docstring

**What worked:**
- Add retry behavior to method docstring
- Mention exponential backoff and transient error types

```python
def setup_base_repo(self) -> None:
    """Clone repository once at experiment start.

    Uses exponential backoff retry for transient network errors
    (connection reset, curl failures, timeouts).
    """
```

## Failed Attempts & Learnings

### ❌ Initial Pattern Matching Too Narrow

**What failed:**
- Pattern: `"network unreachable"`
- Actual error: `"Network is unreachable"`
- **Why it failed:** Didn't account for "is" in the middle of the phrase

**Fix:**
```python
transient_patterns = [
    "network unreachable",
    "network is unreachable",  # Added variation
]
```

**Lesson:** When pattern matching error messages, check actual error logs for variations in phrasing.

### ⚠️ Consider Adding Import Check

**Observation:** Had to add `import time` to the imports section.

**Lesson:** When adding retry logic, verify the `time` module is imported. In Python, this is standard library - always available.

## Results & Parameters

### Test Results
```bash
pixi run pytest tests/unit/e2e/test_workspace_manager.py -v
# 11/11 tests passed
```

### Final Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Max retries** | 3 | Project standard from `.claude/shared/error-handling.md` |
| **Base delay** | 1.0s | Project standard |
| **Backoff multiplier** | 2x | Exponential: 1s, 2s, 4s |
| **Total max wait** | 7s | Sum of delays (1+2+4) |

### Files Changed

**workspace_manager.py** (`src/scylla/e2e/workspace_manager.py:51-126`):
- Added `import time`
- Wrapped `subprocess.run()` in retry loop
- Added transient error detection
- Added exponential backoff logic
- Added warning logs on retry

**test_workspace_manager.py** (`tests/unit/e2e/test_workspace_manager.py`):
- New file with 11 test cases
- Tests both transient and permanent error handling
- Validates backoff timing with mock assertions

## Key Takeaways

1. **Always check project standards first** - `.claude/shared/error-handling.md` had the exact retry pattern
2. **Distinguish transient vs permanent errors** - don't waste retries on auth failures
3. **Log retry attempts** - helps with debugging and visibility
4. **Test both success and exhaustion paths** - ensure retries eventually fail if error persists
5. **Use case-insensitive matching** - error messages vary in capitalization
6. **Include error variations** - "network unreachable" vs "network is unreachable"

## Copy-Paste Code Template

```python
import time

# Inside the function with failing operation:
max_retries = 3
base_delay = 1.0

for attempt in range(max_retries):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        break

    stderr = result.stderr.lower()

    # Define transient patterns specific to your operation
    transient_patterns = [
        "connection reset",
        "connection refused",
        "network unreachable",
        "network is unreachable",
        "temporary failure",
        "timed out",
        # Add operation-specific patterns here
    ]

    is_transient = any(pattern in stderr for pattern in transient_patterns)

    # Fail on non-transient errors or last attempt
    if not is_transient or attempt == max_retries - 1:
        raise RuntimeError(f"Operation failed: {result.stderr}")

    # Exponential backoff
    delay = base_delay * (2 ** attempt)
    logger.warning(
        f"Attempt {attempt + 1}/{max_retries} failed, "
        f"retrying in {delay}s: {result.stderr.strip()}"
    )
    time.sleep(delay)
```

## Related Resources

- `.claude/shared/error-handling.md` - Project retry standards
- `src/scylla/e2e/rate_limit.py` - Similar retry pattern for rate limits
- `src/scylla/executor/runner.py:138-587` - Another retry implementation example
