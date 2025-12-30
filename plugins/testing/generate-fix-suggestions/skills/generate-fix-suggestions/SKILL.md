---
name: generate-fix-suggestions
description: "Generate fix suggestions based on error patterns and best practices"
category: testing
source: ProjectOdyssey
date: 2025-12-30
---

# Generate Fix Suggestions from Errors

Analyze error patterns to suggest specific fixes and improvements.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Convert errors to actionable fixes | Faster resolution of test/build failures |

## When to Use

- (1) Test failures need concrete solutions
- (2) Build errors require remediation steps
- (3) Creating PR comments with suggestions
- (4) Automating fix suggestions for common errors

## Verified Workflow

1. **Analyze error**: Categorize error type and context
2. **Match pattern**: Compare against known error patterns
3. **Find root cause**: Determine what caused the error
4. **Generate suggestion**: Recommend specific fix
5. **Provide example**: Show before/after code if applicable
6. **Prioritize fixes**: High impact fixes first
7. **Report suggestions**: Organized by priority

## Results

Copy-paste ready commands:

```bash
# Categorize errors
grep "Error\|FAILED" output.log | sed 's/.*Error: //' | sort | uniq -c | sort -rn

# Get context around error
grep -B 3 -A 3 "AssertionError" output.log

# Extract error type
grep -o "Error[A-Za-z]*" output.log | sort | uniq -c

# Find patterns in multiple failures
for file in test_*.log; do
  echo "=== $file ==="
  grep "Error:" "$file" | head -3
done
```

### Common Error Patterns & Fixes

**Assertion Errors**:
- Pattern: `assert_equal(actual, expected)` fails
- Fix: Check expected value is correct, verify test logic

**Type Mismatches**:
- Pattern: `TypeError`, `AttributeError`
- Fix: Check argument types, verify method exists

**Out of Bounds**:
- Pattern: `IndexError` or array access failure
- Fix: Verify array size, check loop bounds

**Import/Module Errors**:
- Pattern: `ModuleNotFoundError`, `ImportError`
- Fix: Check module path, verify file exists

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Generated generic suggestions | Not actionable, didn't help | Include specific code changes and examples |
| Suggested fix without context | Fix didn't apply to actual error | Extract surrounding code for context |
| Listed all possible causes | Overwhelmed user, unclear priority | Rank suggestions by likelihood and impact |
| Auto-applied fix without verification | Introduced new bugs | Always test fix before applying |

## Priority Levels

**Critical** (fix immediately):
- Compilation errors
- All tests failing
- Security issues

**High** (fix soon):
- Multiple tests failing
- Performance degradation
- Memory leaks

**Medium** (nice to have):
- Single test failing
- Code style issues
- Warnings

**Low** (backlog):
- Code polish
- Optional refactoring

## Output Format

Report suggestions with:

1. **Error Summary** - What went wrong
2. **Root Cause** - Why it happened
3. **Fix Steps** - Numbered remediation steps
4. **Code Example** - Before/after code snippet
5. **Priority** - Critical/High/Medium/Low
6. **Testing** - How to verify fix works

## Error Handling

| Problem | Solution |
|---------|----------|
| Unknown error type | Classify as "other", suggest investigation |
| Insufficient context | Request more detailed error info |
| Multiple causes | Suggest fixes in priority order |
| No matching pattern | Flag for manual review |

## References

- See extract-test-failures for error extraction
- See analyze-ci-failure-logs for CI-specific analysis
