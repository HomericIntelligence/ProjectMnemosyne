---
name: fp16-accumulation-threshold-math-docs
description: 'Document Float16 convolution skips in dev testing-strategy guides using
  accumulation threshold math. Use when: adding a Float16 limitations subsection to
  testing-strategy.md, documenting why convolution gradient-checking skips Float16,
  or writing per-layer accumulation error tables for a dev guide.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
|----------|-------|
| **Skill Name** | fp16-accumulation-threshold-math-docs |
| **Category** | documentation |
| **Issue Type** | Follow-up doc addition — Float16 section omitted from original Success Criteria |
| **Files Affected** | `docs/dev/testing-strategy.md` (or equivalent dev guide) |
| **Key Pattern** | Insert subsection between `### Parameters` and `### Example` under Gradient Checking |

## When to Use

- A GitHub issue is a follow-up to an implementation issue that omitted a Float16 limitations
  section from the Success Criteria (e.g., "was in the plan notes but not added")
- A `docs/dev/testing-strategy.md` Gradient Checking section needs a subsection explaining
  why convolution tests skip Float16
- You need to write accumulation threshold math (`n × ε_machine`) into a developer guide
- A plan doc references `### Float16 Convolution Limitations` but the section was never added
- A reviewer asks for the math behind the Float16 skip decision in a testing guide

## Verified Workflow

1. **Read the issue** (`gh issue view <number>`) to confirm it is a doc-only follow-up
2. **Read the target file** around the insertion point — the section goes between
   `### Parameters` and `### Example` in the Gradient Checking section
3. **Insert the subsection** using `Edit` with exact surrounding context as `old_string`:

   ```markdown
   ### Float16 Convolution Limitations

   Convolution gradient-checking tests **skip Float16** due to insufficient precision for
   large-kernel accumulation. This is a mathematical limitation, not a test framework gap.

   **Why Float16 fails for convolution gradient checking:**

   Float16 has a 10-bit mantissa, giving ~0.1% relative precision (machine epsilon ≈ 9.77e-4).
   Convolution computes a dot product over `K × K × C_in` values per output element:

   \```text
   Accumulation error ≈ n × ε_machine
     where n = kernel_area × input_channels
   \```

   For common configurations, this exceeds the gradient-checking tolerance:

   | Layer | Kernel | C_in | n (accumulations) | Float16 error | Exceeds tolerance? |
   |-------|--------|------|-------------------|---------------|--------------------|
   | LeNet-5 Conv1 | 5×5 | 1 | 25 | ~2.4e-2 | Borderline |
   | LeNet-5 Conv2 | 5×5 | 6 | 150 | ~1.5e-1 | Yes |
   | AlexNet Conv1 | 11×11 | 3 | 363 | ~3.5e-1 | Yes |
   | AlexNet Conv2 | 5×5 | 64 | 1,600 | ~1.6 | Yes |
   | AlexNet Conv3 | 3×3 | 192 | 1,728 | ~1.7 | Yes |

   The 1e-1 tolerance for lower precision (see `### Parameters` above) is still exceeded for
   any convolution with more than ~100 accumulations.

   **Affected tests** (marked SKIPPED in output):

   - `tests/models/test_lenet5_conv_layers.mojo` — Conv2 forward Float16
   - `tests/models/test_alexnet_layers.mojo` — Conv1, Conv2, Conv3 forward Float16

   **What is tested instead**: Float16 forward pass is verified using special
   FP-representable values (0.0, 0.5, 1.0, 1.5) where exact accumulation holds regardless
   of mantissa width. Backward passes use Float32 only.

   See [#<original-issue>](<link>) for the full analysis that identified this limitation.
   ```

4. **Run markdown linting** via pre-commit (`just pre-commit-all` or `pixi run pre-commit`)
5. **Commit** doc-only change with `docs(testing):` conventional commit prefix and `Closes #<N>`
6. **Push and create PR** with auto-merge enabled

## Key Technical Facts

| Float16 Property | Value |
|-----------------|-------|
| Mantissa bits | 10 explicit + 1 implicit = 11 effective |
| Machine epsilon | ≈ 9.77e-4 |
| Relative precision | ~0.1% |
| Safe accumulations (tol=1e-1) | < ~100 |

### Per-layer accumulation counts (n = K² × C_in)

| Layer | Formula | n |
|-------|---------|---|
| LeNet-5 Conv1 | 5² × 1 | 25 |
| LeNet-5 Conv2 | 5² × 6 | 150 |
| AlexNet Conv1 | 11² × 3 | 363 |
| AlexNet Conv2 | 5² × 64 | 1,600 |
| AlexNet Conv3 | 3² × 192 | 1,728 |

Float16 error ≈ n × 9.77e-4. Exceeds tolerance 1e-1 when n > ~102.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking for existing skill before creating | Searched for `fp16` skills in marketplace | Found `fp16-precision-test-documentation` — similar but targets test file docstrings, not dev guides | Always read the existing skill before deciding to create a new one; scope difference (test file vs. dev guide) justifies a new skill |
| Trying markdownlint-cli2 via `pixi run npx` | `pixi run npx markdownlint-cli2 ...` | `npx: command not found` in this environment | Pre-commit hooks run markdownlint automatically on commit — rely on hooks rather than running manually |
| Trying `pixi run markdownlint-cli2` directly | Direct invocation without `npx` | `markdownlint-cli2: command not found` | The tool is invoked via pre-commit, not directly; `just pre-commit-all` is the correct entry point |

## Results & Parameters

### Insertion anchor (old_string for Edit tool)

```text
- **Method**: Central differences (more accurate than forward differences)

### Example
```

### Commit message format

```text
docs(testing): add Float16 convolution limitations section to testing-strategy.md

Adds a ### Float16 Convolution Limitations subsection under the Gradient
Checking Parameters section explaining why convolution gradient-checking
tests skip Float16. Includes accumulation threshold math (n × ε_machine),
a per-layer error table for LeNet-5 and AlexNet, affected test file names,
and a reference to issue #<original> where the limitation was first identified.

Closes #<follow-up-issue>
```

### PR description format

```markdown
## Summary

- Adds `### Float16 Convolution Limitations` subsection to `docs/dev/testing-strategy.md`
- Explains accumulation threshold math (n × ε_machine)
- Includes per-layer error table for affected model configurations
- Names affected test files and links to original analysis issue

## Test plan

- [x] Documentation-only change — no code modified
- [x] Markdown linting passed in pre-commit hooks
- [x] Section inserted at correct location between `### Parameters` and `### Example`

Closes #<follow-up-issue>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3299, follow-up to #3089 | [notes.md](../references/notes.md) |
