---
name: normalization-backward-grad-output-warning
description: 'Document the grad_output=ones cancellation hazard in normalization backward
  tests as a shared testing guide warning. Use when: a normalization backward test
  produced a false failure due to sum(x_norm)=0 cancellation and you want to prevent
  recurrence via shared documentation.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Objective | Add a warning to the shared testing guide (testing-patterns.md) about `grad_output=ones` causing false-zero gradients in normalization backward tests |
| Outcome | Section added to Pattern 3 (Gradient Checking) with math, failing pattern, correct pattern, and canonical code reference |
| Applies To | Any project with a shared Mojo/Python testing guide and normalization layer backward tests |
| Related Skill | `batch-norm-gradient-test-fix` — covers fixing the test itself; this skill covers documenting the pattern for the team |

## When to Use

1. A normalization backward test silently passed trivially (or falsely failed) due to `grad_output=ones`
2. You want to prevent future engineers from repeating the same mistake by documenting it in a shared guide
3. A GitHub issue asks you to document a testing anti-pattern in `docs/dev/testing-patterns.md`
4. A code review or follow-up issue (e.g. "document this in the shared guide") was filed after fixing the actual test

## Verified Workflow

### Step 1: Read the existing shared guide

Find the gradient checking section in the shared testing patterns document:

```bash
grep -n "Gradient Checking" docs/dev/testing-patterns.md
```

Locate the existing tolerances block — the warning belongs immediately after it, before the
next `---` section separator.

### Step 2: Identify the correct insertion point

The warning should be inside **Pattern 3: Gradient Checking Pattern**, after the tolerances
table and before the `---` separator. This groups it logically with gradient checking guidance.

### Step 3: Write the warning subsection

Include all four components:

1. **Scope** — which layers are affected (batch norm, layer norm, any normalization)
2. **Math** — explain why `sum(x_norm) = 0` by construction
3. **Failing pattern** (❌) — show the `ones_like(output)` antipattern with a comment
4. **Correct pattern** (✅) — show the non-uniform `grad_output` + `forward_for_grad` closure,
   with a reference to the canonical implementation in the test file

### Step 4: Run markdown linting

```bash
pixi run pre-commit run --files docs/dev/testing-patterns.md
```

All hooks must pass (markdownlint, trailing whitespace, end-of-file).

### Step 5: Commit and PR

```bash
git add docs/dev/testing-patterns.md
git commit -m "docs(testing): document batch_norm2d_backward cancellation property warning

Add warning subsection to Pattern 3 (Gradient Checking) explaining
sum(x_norm)=0 cancellation with grad_output=ones.

Closes #<issue>"
```

## The Warning Content (Copy-Paste Ready)

Insert after the Gradient Checking Tolerances code block and before `---`:

````markdown
### Warning: Normalization Backward — Never Use `grad_output=ones`

**Applies to**: `batch_norm2d_backward`, `layer_norm_backward`, and any normalization layer
that computes normalized inputs `x_norm = (x - mean) / std`.

**The problem**: Passing `grad_output=ones` into a normalization backward pass produces
analytically-zero gradients for `dL/dx`. This is not a bug — it is a mathematical identity.
The zero result will match numerical finite differences (which also converge to zero), so the
gradient check passes trivially without actually validating anything.

**Mathematical explanation**: Batch normalization normalizes each channel across the spatial
and batch dimensions. By construction, the normalized values sum to zero:

```text
x_norm = (x - mean(x)) / std(x)
=> sum(x_norm) = 0   (always, by definition of mean-centering)
```

The gradient of the loss with respect to the input contains a term proportional to
`sum(grad_output * x_norm)`. When `grad_output = ones`, this term is `sum(x_norm) = 0`,
which cancels other gradient terms and yields `dL/dx = 0` for every element — a false result
that hides implementation errors entirely.

**Rule**: For normalization layers, never use `grad_output=ones` in backward gradient checks.
````

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3249, PR #3816 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Create a new standalone doc | Draft a new `normalization-testing-guide.md` | Duplication — content belongs in the existing shared guide | Always extend the existing doc rather than creating a parallel one |
| Add the warning to the Troubleshooting section | Place it under "Gradient Check Failing" | The existing troubleshooting entry is about discontinuities (ReLU), not cancellation; mixing them confused the pattern | Group normalization-specific warnings in the Gradient Checking Pattern section, not in general troubleshooting |
| Use `---` before the subsection | Added a horizontal rule before the warning | Created visual separation that broke the logical grouping within Pattern 3 | Insert warning as a `###` subsection inside the existing pattern, after the tolerances block |

## Results & Parameters

### Insertion location in testing-patterns.md

```text
## Pattern 3: Gradient Checking Pattern
  ### Using check_gradients Helper
  ### Verbose Mode for Debugging
  ### Pattern for Mixed Positive/Negative Inputs
  ### Gradient Checking Tolerances      ← insert after this block
  ### Warning: Normalization Backward — Never Use `grad_output=ones`   ← new
---                                     ← existing section separator
## Pattern 4: Model Testing Pattern
```

### Canonical test reference

`tests/shared/core/test_normalization.mojo:316-360` — the `test_batch_norm2d_backward_gradient_input`
function is the authoritative example of the correct `forward_for_grad` closure pattern.
