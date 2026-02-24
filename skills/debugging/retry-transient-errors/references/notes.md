# Session Notes: Retry Logic Implementation

## Original Error

```
RuntimeError: Failed to clone repository: Cloning into 'results/2026-01-05T00-14-06-test-002/repo'...
error: RPC failed; curl 56 Recv failure: Connection reset by peer
error: 7164 bytes of body are still expected
fetch-pack: unexpected disconnect while reading sideband packet
fatal: early EOF
fatal: fetch-pack: invalid index-pack output
```

## Investigation Steps

1. **Explored codebase** using Task agent (Explore subagent)
   - Found `workspace_manager.py:setup_base_repo` had no retry logic
   - Found existing retry patterns in `rate_limit.py` and `executor/runner.py`
   - Found documented standards in `.claude/shared/error-handling.md`

2. **Analyzed error characteristics**
   - "curl 56" = RPC failed (transient network error)
   - "Connection reset by peer" = TCP connection interrupted
   - "early EOF" = premature end of data stream
   - All indicate transient network issues, not permanent failures

3. **Reviewed project patterns**
   - Standard: 3 retries with exponential backoff (1s, 2s, 4s)
   - Error classification: transient (retry) vs permanent (fail immediately)
   - Logging: warn on retry, raise on exhaustion

## Implementation Details

### Code Location
- **File:** `src/scylla/e2e/workspace_manager.py`
- **Method:** `setup_base_repo` (lines 51-126)
- **Change type:** Wrapped existing `subprocess.run()` in retry loop

### Transient Error Patterns
Based on git error messages and network failure patterns:
- `"connection reset"` - TCP connection interrupted
- `"connection refused"` - Target rejected connection
- `"network unreachable"` / `"network is unreachable"` - Network path broken
- `"temporary failure"` - DNS or service temporary issue
- `"could not resolve host"` - DNS lookup failed (usually transient)
- `"curl 56"` - libcurl RPC failed error
- `"timed out"` - Operation exceeded timeout
- `"early eof"` - Premature end of data stream
- `"recv failure"` - Receive operation failed

### Non-Transient Patterns (Fail Immediately)
- Authentication errors
- Repository not found (404)
- Permission denied
- Invalid URL/path
- Configuration errors

## Test Coverage

Created 11 unit tests:
1. `test_successful_clone_first_attempt` - Happy path
2. `test_retry_on_transient_network_error` - curl 56 error retries
3. `test_retry_with_early_eof_error` - early EOF retries
4. `test_exponential_backoff_timing` - Verifies 1s, 2s delays
5. `test_immediate_failure_on_auth_error` - No retry on auth
6. `test_immediate_failure_on_not_found` - No retry on 404
7. `test_exhausted_retries_raises_error` - 3 attempts then fail
8. `test_retry_on_timeout_error` - Timeout is transient
9. `test_retry_on_network_unreachable` - Network error retries
10. `test_idempotent_setup` - Multiple calls don't re-clone
11. `test_case_insensitive_error_detection` - "RESET" matches "reset"

All tests use `unittest.mock.patch` to simulate failures without actual network calls.

## Bug Fixed During Testing

**Issue:** Test `test_retry_on_network_unreachable` failed
- **Expected:** Pattern match on "network unreachable"
- **Actual:** Error was "Network is unreachable" (with "is")
- **Fix:** Added both patterns to the list

This highlighted the importance of testing with actual error message variations.

## Results

- **PR #146:** https://github.com/HomericIntelligence/ProjectScylla/pull/146
- **Status:** Merged to main
- **CI Status:** All tests passed (108/108 e2e unit tests)
- **Lines changed:** +298 / -7

## Future Enhancements (Not Implemented)

1. **Configurable retry parameters** - Make max_retries and base_delay configurable
2. **Jitter addition** - Add random jitter to prevent thundering herd
3. **Retry on git fetch failures** - Apply same logic to `_checkout_commit()`
4. **Metrics collection** - Track retry counts and success rates
5. **Circuit breaker** - Stop retrying if failures are persistent across experiments

These were not implemented to follow YAGNI principle - add only when needed.

## Related Issues

This pattern can be applied to other subprocess operations in the codebase:
- `workspace_manager.py:_checkout_commit()` - git fetch/checkout
- Any other git operations
- External API calls
- File system operations on network mounts

## References

- Project error handling docs: `.claude/shared/error-handling.md`
- Existing retry patterns:
  - `src/scylla/e2e/rate_limit.py:231-295`
  - `src/scylla/executor/runner.py:538-587`
- Git error codes: https://github.com/git/git/blob/master/Documentation/gitcli.txt
- libcurl error 56: CURLE_RECV_ERROR (Recv failure)
