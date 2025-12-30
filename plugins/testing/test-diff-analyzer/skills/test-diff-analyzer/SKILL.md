---
name: test-diff-analyzer
description: "Analyze test differences between runs to identify flaky tests"
category: testing
source: ProjectOdyssey
date: 2025-12-30
---

# Analyze Test Differences Between Runs

Compare test results across multiple runs to identify flaky tests.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Identify flaky and inconsistent tests | Reliable test suite with consistent results |

## When to Use

- (1) Test passes locally but fails in CI
- (2) Test sometimes passes, sometimes fails (flaky test)
- (3) Need to understand test consistency issues
- (4) Comparing test results before/after code changes

## Verified Workflow

1. **Collect baseline**: Run tests locally N times
2. **Collect CI data**: Get CI test results from recent runs
3. **Compare outputs**: Diff between test runs
4. **Identify flaky tests**: Tests with inconsistent results
5. **Find patterns**: When does test fail vs pass
6. **Root cause**: Timing, randomness, resource issues
7. **Remediation**: Fix or isolate flaky test

## Results

Copy-paste ready commands:

```bash
# Run tests and capture output
pytest tests/ > /tmp/test_run_1.log 2>&1
pytest tests/ > /tmp/test_run_2.log 2>&1

# Compare two test runs
diff -u /tmp/test_run_1.log /tmp/test_run_2.log

# Extract failures from logs
grep "FAILED" /tmp/test_run_*.log | sort | uniq -c

# Show tests that sometimes pass, sometimes fail
grep "FAILED\|PASSED" /tmp/test_run_*.log | cut -d: -f2 | sort | uniq -d

# Run same test multiple times
for i in {1..5}; do
  pytest tests/test_specific.py > /tmp/run_$i.log 2>&1
  grep -c "PASSED\|FAILED" /tmp/run_$i.log
done
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Ran test once to check flakiness | Not enough data to detect intermittent failures | Run at least 5-10 times to establish pattern |
| Compared CI runs from different branches | Environment differences caused false positives | Compare runs on same branch/commit |
| Ignored timing-related output | Missed timeout-based flakiness | Include timing info in analysis |
| Tested in different environments | Results not comparable | Use same environment (Docker) for consistency |

## Flaky Test Indicators

**Timing Issues**:
- Test passes when run in isolation
- Test fails when run with other tests
- Timeout values too aggressive
- Race conditions in setup/teardown

**Randomness Issues**:
- Random seed not fixed
- Hash ordering varies
- Dictionary/set iteration order
- Floating point precision

**Resource Issues**:
- Test passes locally but fails in CI
- Fails under resource constraints
- Out of memory errors intermittently

## Output Format

Report analysis with:

1. **Flaky Tests** - Tests with inconsistent results
2. **Consistency Score** - Pass rate across runs (e.g., 80%)
3. **Failure Patterns** - When/how tests fail
4. **Impact** - How many test runs affected
5. **Root Cause Hypothesis** - What likely causes instability
6. **Recommendations** - How to fix or isolate flaky test

## Error Handling

| Problem | Solution |
|---------|----------|
| Different environment | Run in controlled environment (docker) |
| Insufficient data | Run more iterations to get pattern |
| No failure info | Enable debug output, increase verbosity |
| External dependencies | Mock or isolate external services |

## References

- See extract-test-failures for failure analysis
- See fix-ci-failures for CI debugging
