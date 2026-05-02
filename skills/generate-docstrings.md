---
name: generate-docstrings
description: Create docstrings for functions and classes. Use when documenting code
  APIs.
category: tooling
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Generate Docstrings

## Overview

| Item | Details |
| ------ | --------- |
| Date | N/A |
| Objective | Write comprehensive docstrings for functions and classes following standard formats (Google, NumPy, reStructuredText). |
| Outcome | Operational |

Write comprehensive docstrings for functions and classes following standard formats (Google, NumPy, reStructuredText).

## When to Use

- Adding documentation to undocumented functions
- Improving code documentation completeness
- Ensuring consistent docstring format
- Supporting API documentation generation

### Quick Reference

```python
# Google-style docstring format
def matrix_multiply(a: ExTensor, b: ExTensor) -> ExTensor:
    """Multiply two matrices using optimized Mojo kernels.

    Args:
        a: First matrix (shape: m x n)
        b: Second matrix (shape: n x k)

    Returns:
        Product matrix (shape: m x k)

    Raises:
        ValueError: If matrix dimensions don't align for multiplication

    Example:
        ```mojo
        >> a = ExTensor([[1, 2], [3, 4]], DType.float32)
        >>> b = ExTensor([[1, 0], [0, 1]], DType.float32)
        >>> c = matrix_multiply(a, b)
        ```
    """
    ...
```

## Verified Workflow

1. **Analyze function**: Understand purpose, parameters, return value
2. **Choose format**: Select docstring style (Google is recommended)
3. **Write summary**: Clear one-line description
4. **Document parameters**: Type, description, constraints
5. **Document return**: Type and description of return value
6. **Add examples**: Practical usage examples

## Output Format

Docstring structure:

- One-line summary
- Extended description (if needed)
- Args section (parameter documentation)
- Returns section (return value documentation)
- Raises section (exceptions)
- Examples section (usage examples)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `generate-api-docs` skill for API documentation generation
- See Google Python Style Guide for docstring conventions
- See PEP 257 for Python docstring conventions
