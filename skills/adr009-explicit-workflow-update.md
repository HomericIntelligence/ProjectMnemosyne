---
name: adr009-explicit-workflow-update
description: 'Splitting Mojo test files per ADR-009 when CI workflow uses explicit
  filename patterns. Use when: test file has >10 fn test_ functions AND CI workflow
  lists filenames explicitly (not glob), requiring workflow update alongside the file
  split.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~20 minutes |

Extends the base `adr009-test-file-splitting` workflow for the case where the CI workflow
uses **explicit filename patterns** in its matrix (e.g., `test_activations.mojo`) instead of
a glob like `test_*.mojo`. In this case, the new split files must also be added to the
workflow's `pattern:` field — they will not be auto-discovered.

Contrast with `adr009-test-file-splitting` (issue #3397) where `test_assertions_*.mojo` was
auto-discovered by a glob and no workflow change was needed.

## When to Use

- A Mojo test file has >10 `fn test_` functions and must be split per ADR-009
- The CI workflow (`comprehensive-tests.yml` or similar) lists the file by exact name in a
  `pattern:` field, NOT by glob
- CI group (e.g., "Core Activations & Types") would silently drop the new split files if the
  workflow is not updated

## Verified Workflow

### 1. Count tests and confirm split is needed

```bash
grep -c "^fn test_[a-z]" tests/shared/core/test_activations.mojo
# Output: 45 → exceeds ADR-009 ≤10 hard limit, ≤8 target
```

### 2. Check CI workflow for explicit vs glob pattern

```bash
grep "test_activations" .github/workflows/comprehensive-tests.yml
```

If the output shows `test_activations.mojo` by exact name in a `pattern:` field, a workflow
update is required. If it shows `test_*.mojo`, a glob covers it automatically.

### 3. Plan the split (≤8 tests per file)

With 45 tests split into 6 files of ≤8:

- Part 1: 8 tests
- Part 2: 8 tests
- Part 3: 8 tests
- Part 4: 8 tests
- Part 5: 8 tests
- Part 6: 5 tests (remainder)

Group by activation function family (ReLU, Leaky ReLU, PReLU, Sigmoid, Tanh, Softmax,
GELU, Swish, Mish, ELU, Integration) for semantic coherence.

### 4. Create split files with ADR-009 header

Each new file must start with the ADR-009 docstring comment:

```mojo
"""Tests for activation functions - Part N: <description>.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_activations.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md

Tests: test_foo, test_bar, ...
"""
```

Each file needs:
- Only the imports it actually uses (trim unused imports from the original)
- Its subset of `fn test_` functions (verbatim copy)
- Its own `fn main()` runner with only its tests

### 5. Delete the original file

```bash
git rm tests/shared/core/test_activations.mojo
```

Do NOT keep the original file — it will cause duplicate test runs if left.

### 6. Update the CI workflow

Replace the exact filename with the 6 new filenames in the `pattern:` field:

```yaml
# Before:
pattern: "test_activations.mojo test_activation_funcs.mojo ..."

# After (add ADR-009 comment above):
# ADR-009: test_activations.mojo split into 6 parts (≤8 tests each)
# to avoid Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so)
pattern: "test_activations_part1.mojo test_activations_part2.mojo test_activations_part3.mojo test_activations_part4.mojo test_activations_part5.mojo test_activations_part6.mojo test_activation_funcs.mojo ..."
```

### 7. Update README if it lists the file explicitly

```bash
grep -r "test_activations.mojo" tests/shared/README.md
```

Update to list all 6 part files.

### 8. Commit (pre-commit hooks validate everything)

```bash
git add tests/shared/core/test_activations_part*.mojo
git add tests/shared/core/test_activations.mojo  # staged as deletion
git add .github/workflows/comprehensive-tests.yml
git add tests/shared/README.md
git commit -m "fix(ci): split test_activations.mojo into 6 parts per ADR-009"
```

Pre-commit hooks that run: `mojo format`, `validate_test_coverage`, `markdownlint`,
`check-yaml`, `trailing-whitespace`, `end-of-file-fixer`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keeping the original file alongside split files | Left `test_activations.mojo` in place | Would cause duplicate test execution (all 45 + 45 = 90 runs) | Always delete the original when splitting — it is fully replaced |
| Assuming glob covers new files | Expected CI to auto-pick up `test_activations_part*.mojo` | CI pattern listed `test_activations.mojo` explicitly, not a glob | Always grep the workflow for the exact filename before assuming auto-discovery |
| Copying all imports to each split file | Each split file had the full import block | Unused imports cause compile warnings or errors in Mojo | Trim imports to only what each split file actually uses |

## Results & Parameters

**Split distribution for 45 tests into 6 files:**

```text
Part 1: 8 tests  (ReLU x6, Leaky ReLU basic x2)
Part 2: 8 tests  (Leaky ReLU backward x1, PReLU x4, Sigmoid basic x3)
Part 3: 8 tests  (Sigmoid stability/dtype x3, Tanh x4, Softmax basic x1)
Part 4: 8 tests  (Softmax x4, GELU x4)
Part 5: 8 tests  (GELU x4, Swish x3, Mish basic x1)
Part 6: 5 tests  (Mish x2, ELU x2, Integration x1)
```

**Grep to verify counts before commit:**

```bash
grep -c "^fn test_[a-z]" tests/shared/core/test_activations_part*.mojo
# Each line should show ≤8
```

**Grep to verify no remaining reference to old filename in workflow:**

```bash
grep "test_activations\.mojo" .github/workflows/comprehensive-tests.yml
# Should only appear in the ADR-009 comment line, not in the pattern: field
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3400, PR #4111 | [notes.md](../../references/notes.md) |

**Related:** `adr009-test-file-splitting` (base skill), `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
