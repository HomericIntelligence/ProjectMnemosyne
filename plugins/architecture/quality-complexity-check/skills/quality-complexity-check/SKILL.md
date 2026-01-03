---
name: quality-complexity-check
description: "Analyze code complexity metrics including cyclomatic complexity and nesting depth"
category: architecture
date: 2025-12-30
---

# Analyze Code Complexity

Analyze and report code complexity metrics.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Identify complex code for refactoring | Maintainable, readable codebase |

## When to Use

- (1) Code review process
- (2) Identifying refactoring candidates
- (3) Maintaining code quality
- (4) Before major releases

## Verified Workflow

1. **Analyze code** - Run complexity analysis tool
2. **Review metrics** - Identify high-complexity functions
3. **Prioritize** - Focus on most complex first
4. **Refactor** - Apply simplification patterns
5. **Re-analyze** - Verify improvement
6. **Document** - Note refactoring decisions

## Results

Copy-paste ready commands:

```bash
# Python complexity analysis with radon
pip install radon
radon cc -s -a path/to/code/

# Show only complex functions (CC > 10)
radon cc -s -a --min B path/to/code/

# Maintainability index
radon mi path/to/code/

# Raw metrics (LOC, comments, etc.)
radon raw path/to/code/

# Alternative: lizard (multi-language)
pip install lizard
lizard path/to/code/ -l python
```

### Complexity Metrics

**Cyclomatic Complexity (CC)**

| CC Range | Assessment | Action |
|----------|------------|--------|
| 1-10 | Simple | Keep as is |
| 11-20 | Moderate | Consider refactoring |
| 21+ | Complex | Needs refactoring |

**Nesting Depth**

| Depth | Assessment | Action |
|-------|------------|--------|
| 1-3 | Good | Keep as is |
| 4-5 | High | Consider flattening |
| 6+ | Very High | Refactor required |

**Function Length**

| LOC | Assessment | Action |
|-----|------------|--------|
| 1-20 | Good | Keep as is |
| 21-50 | Acceptable | Monitor |
| 51+ | Too long | Consider splitting |

### Refactoring Patterns

**Extract Function (High CC)**

```python
# Before (CC: 15)
def process(data):
    if condition1:
        if condition2:
            if condition3:
                for item in data:
                    if item.valid:
                        # complex logic

# After (CC: 5)
def process(data):
    if not is_valid(data):
        return
    filtered = filter_valid_items(data)
    return process_items(filtered)
```

**Flatten Nesting (High Depth)**

```python
# Before (depth: 5)
def process(data):
    if check1(data):
        if check2(data):
            if check3(data):
                # complex logic

# After (depth: 2)
def process(data):
    if not check1(data): return
    if not check2(data): return
    if not check3(data): return
    # complex logic
```

### Project Thresholds

- Max CC per function: 15
- Max nesting depth: 4
- Max function length: 50 LOC

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Refactored all complex functions at once | Introduced regressions, hard to review | Refactor one function at a time with tests |
| Ignored CC metrics during code review | Technical debt accumulated | Include complexity check in review checklist |
| Set thresholds too strict (CC < 5) | Too many false positives, team ignored warnings | Use reasonable thresholds (CC < 15) |
| Extracted too many tiny functions | Code became harder to follow | Balance extraction - don't over-fragment |

## Error Handling

| Problem | Solution |
|---------|----------|
| Script not found | Install radon: `pip install radon` |
| Syntax errors | Fix code syntax before analyzing |
| No output | Verify source files exist |

## References

- Related skill: quality-security-scan for security analysis
- Radon documentation: https://radon.readthedocs.io/
