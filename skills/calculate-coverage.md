---
name: calculate-coverage
description: Measure test coverage and identify untested code. Use when assessing
  test completeness.
category: evaluation
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Calculate Coverage

## Overview

| Item | Details |
| ------ | --------- |
| Date | N/A |
| Objective | Measure code coverage percentage and identify which code paths are untested to ensure comprehensive testing. |
| Outcome | Operational |

Measure code coverage percentage and identify which code paths are untested to ensure comprehensive testing.

## When to Use

- Checking test coverage for modules
- Identifying gaps in test suites
- Meeting coverage thresholds (typically 80%+)
- Planning additional test cases

### Quick Reference

```bash
# Python coverage with pytest
pip install coverage pytest-cov
pytest --cov=module_name --cov-report=html tests/

# View coverage report
open htmlcov/index.html

# Check coverage threshold
coverage report --fail-under=80
```

## Verified Workflow

1. **Install coverage tool**: Set up measurement infrastructure
2. **Run tests with coverage**: Execute test suite capturing coverage data
3. **Generate report**: Create HTML or text coverage report
4. **Analyze gaps**: Identify untested functions, branches, edge cases
5. **Plan improvements**: Create tests for uncovered code paths

## Output Format

Coverage analysis:

- Overall coverage percentage
- Per-module coverage breakdown
- Uncovered lines (with line numbers)
- Branch coverage (if applicable)
- Recommendations for improvement

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `run-tests` skill for test execution
- See `generate-tests` skill for test creation
- See CLAUDE.md > Key Development Principles (TDD) for testing strategy
