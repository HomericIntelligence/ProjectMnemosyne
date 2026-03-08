---
name: adr009-test-file-split
description: "Split oversized Mojo test files to comply with ADR-009 heap corruption workaround. Use when: a Mojo test file exceeds 10 fn test_ functions causing intermittent CI failures from libKGENCompilerRTShared.so JIT faults."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 triggers heap corruption (libKGENCompilerRTShared.so JIT fault) under high test load |
| **Workaround** | ADR-009 mandates ≤10 `fn test_` functions per file |
| **Symptom** | Non-deterministic CI failures rotating across test groups |
| **Fix** | Split large test files into multiple files of ≤8 tests each |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI fails intermittently with `libKGENCompilerRTShared.so` JIT fault in logs
- A CI group (e.g. "Shared Infra") has >13/20 recent run failures rotating non-deterministically
- ADR-009 compliance checker flags a file as over the limit

## Verified Workflow

### 1. Count test functions in the file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Identify the split boundary

- Target ≤8 tests per file (not just ≤10) for safety margin
- Keep logically related tests together (e.g. struct tests, function tests, integration tests)
- Split into `test_<name>_part1.mojo` and `test_<name>_part2.mojo`

### 3. Create split files with ADR-009 header

Each new file MUST start with this header comment:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Each file needs its own `fn main() raises:` test runner calling only its own tests.

### 4. Remove the original file

```bash
git rm tests/path/to/test_<original>.mojo
git add tests/path/to/test_<name>_part1.mojo tests/path/to/test_<name>_part2.mojo
```

### 5. Update validate_test_coverage.py

Replace the single entry with two entries:

```python
# Before
"tests/shared/training/test_evaluation.mojo",

# After
"tests/shared/training/test_evaluation_part1.mojo",
"tests/shared/training/test_evaluation_part2.mojo",
```

### 6. Check CI workflow glob patterns

If the CI workflow uses a glob like `training/test_*.mojo`, new files are picked up automatically.
Only update the workflow if it references the exact filename:

```yaml
# If using glob - no change needed
pattern: "training/test_*.mojo"

# If using exact filename - update it
pattern: "training/test_evaluation_part1.mojo training/test_evaluation_part2.mojo"
```

### 7. Verify with pre-commit hooks

```bash
just pre-commit
# or
pixi run pre-commit run --all-files
```

The `validate_test_coverage` hook will catch any missing filename registrations.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Updating CI workflow pattern | Manually replacing `test_evaluation.mojo` in `comprehensive-tests.yml` | Pattern was a glob `training/test_*.mojo` — new files matched automatically | Check if CI uses glob before editing workflow files |
| Keeping original file alongside parts | Considered leaving `test_evaluation.mojo` as an alias | Would re-introduce the >10 fn test_ problem and confuse coverage validation | Always `git rm` the original file, never keep it alongside split files |

## Results & Parameters

### Split ratio used in this session

- Original: 13 tests in 1 file
- Part 1: 8 tests (EvaluationResult × 2, evaluate_model × 3, evaluate_model_simple × 2, evaluate_topk basic × 1)
- Part 2: 5 tests (evaluate_topk edge cases × 2, integration × 3)

### Files affected

```text
tests/shared/training/test_evaluation.mojo         → deleted
tests/shared/training/test_evaluation_part1.mojo   → 8 fn test_
tests/shared/training/test_evaluation_part2.mojo   → 5 fn test_
scripts/validate_test_coverage.py                  → updated filename list
```

### Key invariants

- All original test functions preserved — no tests deleted
- Each file has its own `fn main() raises:` runner
- ADR-009 header present in every split file
- CI workflow unchanged when glob pattern already matches new filenames
