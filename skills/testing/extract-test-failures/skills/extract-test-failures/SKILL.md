---
name: extract-test-failures
description: "Extract and summarize test failures from logs"
category: testing
date: 2025-12-30
---

# Extract and Summarize Test Failures

Parse test logs to extract failure information and create summary.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Systematic test failure analysis | Quick identification of what broke |

## When to Use

- (1) CI test run failed, need to understand failures
- (2) Large test suite with many failures needs summary
- (3) Categorizing failures by type (assertion, runtime, timeout)
- (4) Creating PR review comments about failures

## Verified Workflow

1. **Collect log**: Get test output from CI or local run
2. **Find failures**: Extract FAILED markers and error types
3. **Group by type**: Categorize assertion vs runtime vs timeout
4. **Extract details**: Get error messages and stack traces
5. **Count totals**: Summary of how many failures
6. **Identify patterns**: Common failure causes
7. **Summarize**: Create concise failure report

## Results

Copy-paste ready commands:

```bash
# Extract failed test names
grep "FAILED" test_output.log

# Get failure details with context
grep -A 10 "FAILED\|Error\|AssertionError" test_output.log

# Count failures by type
grep "FAILED\|AssertionError\|ValueError\|TypeError" test_output.log | sort | uniq -c

# Extract test summary line
tail -20 test_output.log | grep -E "passed|failed|error"

# Get specific failure info
grep -B 5 "AssertionError" test_output.log | head -50
```

### Failure Categories

**Assertion Failures**: `AssertionError`, `assert_equal()`, `assert_true()`
- Fix: Check test logic and expected values

**Type/Attribute Errors**: `AttributeError`, `TypeError`, `ValueError`
- Fix: Check code syntax and types

**Runtime Errors**: `IndexError`, `KeyError`, `ZeroDivisionError`
- Fix: Check boundary conditions

**Timeout/Hanging**: Test takes too long, infinite loop
- Fix: Optimize or add timeout

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Only searched for "FAILED" | Missed error types like "Error:" and "exception" | Use comprehensive pattern: `FAILED\|Error\|exception` |
| Extracted failures without context | Couldn't understand why tests failed | Use `-A 10` to get context after match |
| Counted raw lines instead of unique failures | Overcounted due to multi-line errors | Use `sort | uniq` to deduplicate |
| Processed entire huge log file | Too slow, ran out of memory | Use `tail` or `head` to limit, or `grep` first |

## Output Format

Report failures with:

1. **Total Failures** - Count and percentage of total tests
2. **Failure Summary** - By type (assertion, runtime, timeout)
3. **Failed Tests** - List of test names that failed
4. **Top Issues** - Most common failure patterns
5. **Error Messages** - Representative error snippets
6. **Recommendations** - Which tests to focus on first

## Error Handling

| Problem | Solution |
|---------|----------|
| No FAILED markers | Check log format, may use different pattern |
| Truncated output | Get full log from artifacts |
| Mixed output types | Filter by log level or timestamp |
| Very large logs | Split and process in chunks |

## References

- See test-diff-analyzer for identifying flaky tests
- See analyze-ci-failure-logs for CI-specific failures
- See generate-fix-suggestions for automated fixes
