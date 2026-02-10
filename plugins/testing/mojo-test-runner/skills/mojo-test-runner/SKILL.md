---
name: mojo-test-runner
description: "Run Mojo tests using mojo test command. Use when executing tests or verifying test coverage."
mcp_fallback: none
category: mojo
---

# Mojo Test Runner Skill

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Execute Mojo tests with filtering and reporting. - Running Mojo test suites - Verifying implementation correctness |
| Outcome | Operational |


Execute Mojo tests with filtering and reporting.

## When to Use

- Running Mojo test suites
- Verifying implementation correctness
- TDD red-green-refactor cycle
- Checking test coverage before PR

## Quick Reference

```bash
# Run all tests
mojo test tests/

# Run specific file
mojo test tests/test_tensor.mojo

# Run with verbose output
mojo test -v tests/

# Run tests matching pattern
./scripts/run_tests.sh tensor
```

## Verified Workflow

1. **Run tests** - Execute `mojo test` or script
2. **Review output** - Check pass/fail summary
3. **Fix failures** - Address failing tests
4. **Re-run tests** - Verify all pass

## Mojo-Specific Notes

- Test functions must start with `test_`
- Test files must match `test_*.mojo` or `*_test.mojo`
- Tests run independently - no shared state between tests
- Use `raises` keyword for exception testing

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Import error` | Module not found | Verify `-I` include paths |
| `Syntax error` | Invalid test code | Fix syntax before testing |
| `Timeout` | Test too slow | Optimize or increase timeout |
| `Memory error` | Ownership issue | Check ownership and borrowing |

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| N/A | This skill was migrated from uncategorized | Document failures as they occur |


## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- `.claude/shared/mojo-anti-patterns.md` - Common test mistakes
- `/notes/review/` - Testing strategy documentation
