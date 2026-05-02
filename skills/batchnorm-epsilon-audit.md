---
name: batchnorm-epsilon-audit
description: 'Audit backward-pass tester methods for undocumented epsilon/tolerance
  magic numbers and apply structured NOTE comment pattern. Use when: following up
  a backward-pass epsilon audit, or when BatchNorm/Pooling backward testers lack gradient-checking
  constant documentation.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | batchnorm-epsilon-audit |
| **Category** | documentation |
| **Scope** | `shared/testing/layer_testers.mojo` |
| **Issue** | #3208 (follow-up from #3090) |
| **Outcome** | Structured NOTE comments added to `test_batchnorm_layer_backward` |

This skill captures the pattern for auditing ML layer tester methods that use hardcoded epsilon and
tolerance values in gradient checking, and upgrading vague placeholder comments to structured NOTE
comments that document rationale and cross-reference related issues.

## When to Use

- A follow-up issue asks to audit backward-pass tester methods not covered in a prior sweep
- A tester method has a vague comment like "Epsilon and tolerance values will be dtype-specific when gradient checking is added" without specifying the actual values or rationale
- You need to apply the same constant-extraction pattern as conv2d/linear/activation backward testers to BatchNorm or Pooling testers
- A method's gradient checking is not yet implemented but the planned constants should be documented for future implementers

## Verified Workflow

1. **Read the issue and prior work**: `gh issue view <N> --comments` — understand what #3090 established (epsilon aliases, tolerance rationale, issue #2704 cross-reference)

2. **Search for target methods**: Grep `layer_testers.mojo` for `test_batchnorm_layer_backward`, `NOTE.*epsilon`, `NOTE.*tolerance`, and known magic numbers (`3e-4`, `1e-3`, `1e-1`, `0\.10`)

3. **Read surrounding context**: Read the existing comment block at the site to understand what placeholder language is present

4. **Apply the structured NOTE pattern**: Replace vague placeholders with comments that include:
   - Planned `epsilon` values per dtype (float32 → `GRADIENT_CHECK_EPSILON_FLOAT32` = `3e-4`; other dtypes → `GRADIENT_CHECK_EPSILON_OTHER` = `1e-3`)
   - Planned `tolerance` value with rationale (BatchNorm accumulates division errors across N×H×W, so use `1e-1` = 10%, same as conv2d)
   - Issue cross-references (`#2704` for matmul precision, `#3090` for the audit pattern)

5. **Check for pooling tester**: Grep for any `test_pool*_backward` or `test_maxpool*_backward` — confirm absent (nothing to audit)

6. **Run pre-commit hooks**: `pixi run pre-commit run --all-files` — verify Mojo Format, markdownlint, trailing whitespace all pass

7. **Commit, push, PR**: Conventional commit `docs(layer_testers): document planned epsilon/tolerance for BatchNorm backward`, include `Closes #<N>` and enable auto-merge

## Results & Parameters

### Epsilon/Tolerance Constants (from #3090)

```mojo
# float32 matmul-heavy layers
alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4

# Non-float32 dtypes
alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3
```

### Tolerance values by layer type

| Layer | Tolerance | Rationale |
| ------- | ----------- | ----------- |
| Conv2d backward | `1e-1` (10%) | Accumulated matmul errors |
| Linear backward | `0.10` wide + `0.01` abs | Matrix op accumulated errors, see #2704 |
| Activation backward | `1e-2` float32, `1e-1` other | Elementwise, less accumulation |
| **BatchNorm backward** | `1e-1` (10%) all dtypes | Normalization divides across N×H×W, same regime as conv2d |

### NOTE Comment Pattern Applied

```mojo
# Note: Actual BatchNorm backward gradient checking will be implemented
# when BatchNorm forward pass is available.
# NOTE: When adding gradient checking, use epsilon=3e-4 for float32 to avoid
# precision loss in normalization ops (consistent with conv2d/linear, see #2704).
# BatchNorm accumulates division errors across N*H*W elements, so use
# tolerance=1e-1 (10%) for all dtypes — same as conv2d backward (see #3090).
# NOTE: For other dtypes use epsilon=1e-3, tolerance=1e-1 (same pattern as #3090).
# For now, we validate that we can compute numerical gradients on the input.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Looking for pooling backward tester | Searched for `test_pool*_backward` methods in `layer_testers.mojo` | No such method exists in the file | Always confirm scope first — issue says "if they also use hardcoded epsilon"; absence means nothing to audit |
| Assuming BatchNorm tolerance matches activation | Initially considered `1e-2` (activation pattern) for BatchNorm float32 | BatchNorm normalization accumulates division errors across all N×H×W elements, making it closer to conv2d than elementwise ops | Match tolerance to the accumulation regime of the operation, not to its layer category |
