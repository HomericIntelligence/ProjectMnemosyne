---
name: validate-inputs
description: Check function inputs for correctness and safety. Use when implementing
  defensive programming.
category: evaluation
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Validate Inputs

## Overview

| Item | Details |
| ------ | --------- |
| Date | N/A |
| Objective | Implement input validation to ensure functions receive correct data types, shapes, ranges, and formats. |
| Outcome | Operational |

Implement input validation to ensure functions receive correct data types, shapes, ranges, and formats.

## When to Use

- Adding defensive checks to functions
- Improving error messages for bad inputs
- Ensuring tensor shape/dtype correctness
- Validating configuration parameters

### Quick Reference

```python
# Input validation pattern
def validate_tensor(tensor):
    assert tensor is not None, "Tensor cannot be None"
    assert isinstance(tensor, ExTensor), "Must be ExTensor type"
    assert len(tensor.shape) > 0, "Tensor shape cannot be empty"
    assert tensor.dtype() in [DType.float32, DType.float64], "Invalid dtype"
    return True

# Usage with context
try:
    validate_tensor(input_data)
except AssertionError as e:
    raise ValueError(f"Invalid input: {e}")
```

## Verified Workflow

1. **Document expectations**: Specify types, shapes, ranges for inputs
2. **Implement checks**: Add validation before processing
3. **Provide error messages**: Clear messages for validation failures
4. **Test edge cases**: Verify validation catches invalid inputs
5. **Document behavior**: Note what validation is performed

## Output Format

Input validation specification:

- Parameter name and type
- Constraints (shape, range, valid values)
- Error handling strategy
- Error messages returned
- Test cases for invalid inputs

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `generate-tests` skill for validation test cases
- See CLAUDE.md > Defensive Programming for best practices
- See `scan-vulnerabilities` skill for security validation
