---
name: document-normalization-test-gotcha
description: 'Document normalization backward pass test gotchas in project docs. Use
  when: a normalization layer backward gradient test produced a false mismatch that
  was a mathematical identity, or adding Known Gotchas sections to testing-strategy.md
  or backward-pass-catalog.md.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | document-normalization-test-gotcha |
| **Category** | documentation |
| **Language** | Markdown |
| **Issue Type** | Test gotcha documentation |
| **Resolution** | Add Known Gotchas section + cross-reference in backward-pass-catalog |

## When to Use

1. A normalization layer backward test produced a false gradient mismatch
   (analytical ~0, numerical ~0.009, apparent ~1000x mismatch) that is NOT a bug
2. Closing a GitHub issue requesting documentation of a known test pathology
3. Adding a "Known Test Gotchas" section to `docs/dev/testing-strategy.md`
4. Adding a "Known Test Pathologies" note to `docs/dev/backward-pass-catalog.md`
5. Any `ones_like(grad_output)` normalization backward edge case needs to be recorded

## Verified Workflow

### Step 1: Read the issue and existing docs

```bash
gh issue view <number> --comments
```

Read both target files in full before editing:

- `docs/dev/testing-strategy.md` — find the "Gradient Checking" section end
- `docs/dev/backward-pass-catalog.md` — find "TRAINING READINESS VERIFICATION"

Also check `docs/dev/testing-patterns.md` — it may already have the per-layer
warning (it does for batch_norm2d and layer_norm). Link to it rather than duplicating.

### Step 2: Add "Known Test Gotchas" to testing-strategy.md

Insert a new `## Known Test Gotchas` section between `## Gradient Checking`
and `## Layer Deduplication`. The section must contain:

- **Symptom** — what the false failure looks like (numbers, error message)
- **Root cause** — clear statement that it is NOT a bug
- **Mathematical Proof** sub-section with the identity derivation
- **Why the Gradient is Zero** — walk through the backward formula
- **Why Numerical Gradient Also Appears Near Zero** — degenerate loss explanation
- **Safe Alternatives** — at least 2 options with code examples
- **Rule** line and **Discovery context** with PR/issue reference

For `batch_norm2d` / `ones_like` the key identity is:

```text
sum(x_norm) = 0  (zero-mean property of batch norm in training mode)
=> dotp = sum(grad_output * x_norm) = sum(x_norm) = 0
=> grad_input[i] = (1 - N/N - x_norm[i] * 0/N) * gamma/std = 0  exactly
```

### Step 3: Add "Known Test Pathologies" to backward-pass-catalog.md

Insert a `### Known Test Pathologies` subsection inside
`### Recommended Improvements` → `### Training Readiness Conclusion`.
Keep it concise — show only the cancellation identity and cross-reference
testing-strategy.md for the full proof.

Pattern:

```markdown
### Known Test Pathologies

#### <Layer>: `<bad_pattern>` Produces Analytically-Zero Gradients

When testing `<backward_fn>`, using `<bad_pattern>` causes
`grad_input = 0` for all elements. This is **not a bug** — it is a mathematical identity:

```text
<cancellation identity>
```

**See**: `docs/dev/testing-strategy.md` — "Known Test Gotchas" section for full proof.

**Applies also to**: <other affected layers>.
```

### Step 4: Validate with pre-commit

```bash
pixi run pre-commit run --all-files
```

Markdown Lint must pass. Common issues:

- Blank lines required before and after all fenced code blocks
- Blank lines required before and after all headings
- Language tag required on every fenced code block (` ```text `, ` ```mojo `, etc.)
- Lines ≤ 120 characters

### Step 5: Commit and PR

```bash
git add docs/dev/testing-strategy.md docs/dev/backward-pass-catalog.md
git commit -m "docs(testing): document <layer> <pattern> gotcha

<summary of what was documented and why>

Closes #<issue>
"

git push -u origin <branch>
gh pr create --title "docs(testing): ..." --body "Closes #<issue>" --label "documentation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Duplicate content in testing-patterns.md | Wrote the full gotcha there as well | testing-patterns.md already had the per-layer warning | Always read ALL docs files first; testing-patterns.md has the canonical code pattern, testing-strategy.md gets the mathematical proof |
| Used ` ```mojo ` for math derivation block | Typed the Kratzert formula as mojo code | markdownlint passed but the code block had no mojo syntax so it looked odd | Use ` ```text ` for mathematical formulas and pseudocode |
| Added gotcha after References section | Placed the section at end of file | Disrupts reading flow — gotchas should be near gradient checking, not at the end | Insert between Gradient Checking and Layer Deduplication |

## Results & Parameters

### Files Modified

| File | Location | What Was Added |
|------|----------|----------------|
| `docs/dev/testing-strategy.md` | Between `## Gradient Checking` and `## Layer Deduplication` | `## Known Test Gotchas` section with full mathematical proof |
| `docs/dev/backward-pass-catalog.md` | Inside TRAINING READINESS VERIFICATION, before Training Readiness Conclusion | `### Known Test Pathologies` with cross-reference |

### Section Template: testing-strategy.md

```markdown
## Known Test Gotchas

This section documents edge cases that have caused false failures in the past.
Always check here before assuming a gradient mismatch is a real bug.

### <Layer>: `<bad_pattern>` Produces Zero Gradients

**Symptom**: Analytical gradient ≈ 0, numerical gradient ≈ 0.009 — apparent ~1000x mismatch.

**Root cause**: This is **not a bug**. The zero analytical gradient is mathematically correct,
and the numerical gradient is also essentially zero — the apparent mismatch is finite-difference
noise against an exactly-zero baseline.

#### Mathematical Proof

<derivation>

#### Why the Gradient is Zero

<Kratzert formula walkthrough>

#### Why Numerical Gradient Also Appears Near Zero

<degenerate loss explanation>

#### Safe Alternatives

**Option 1**: ...

**Rule**: ...

**Discovery context**: Found during PR #<N> / issue #<N>. ...
```

### Related Skills

- `batch-norm-backward-gradient-analysis` — diagnosing the gradient mismatch (testing/)
- `batch-norm-gradient-test-fix` — fixing the test to use non-uniform grad_output (testing/)
