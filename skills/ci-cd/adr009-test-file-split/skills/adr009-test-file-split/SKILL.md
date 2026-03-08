---
name: adr009-test-file-split
description: "Split Mojo test files exceeding the ADR-009 ≤10 fn test_ limit to fix intermittent heap corruption crashes in CI. Use when: a Mojo test file has >10 fn test_ functions causing non-deterministic CI failures."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) under high test load |
| **Trigger** | `fn test_` count > 10 in a single `.mojo` file |
| **Fix** | Split into multiple files of ≤8 tests each |
| **ADR** | `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **CI Signal** | Non-deterministic failures rotating across CI groups, 13/20 recent runs |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- A CI group shows intermittent, non-deterministic failures with `libKGENCompilerRTShared.so` in the stack
- Creating new Mojo test files (enforce ≤10 from the start)
- ADR-009 compliance review of existing test files

## Verified Workflow

### 1. Count test functions in target file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, proceed with split.

### 2. Plan the split

Target ≤8 tests per file (not just ≤10) to leave headroom. Group by logical category:

- Part 1: Basic/foundational tests
- Part 2: Advanced/edge case tests
- Add more parts if needed

### 3. Create split files with ADR-009 header

Each new file must include this header comment immediately after the docstring:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Naming convention: `test_<name>_part1.mojo`, `test_<name>_part2.mojo`

### 4. Verify each file's test count

```bash
grep -c "^fn test_" tests/path/to/test_file_part1.mojo  # Must be ≤8
grep -c "^fn test_" tests/path/to/test_file_part2.mojo  # Must be ≤8
```

### 5. Delete original file

```bash
rm tests/path/to/test_file.mojo
```

### 6. Check CI workflow references

```bash
grep -r "test_<name>" .github/workflows/
```

If the CI uses `test_*.mojo` glob patterns, no workflow changes needed.
If the CI references the file by exact name, update the workflow.

### 7. Commit and verify pre-commit passes

```bash
git add tests/path/to/test_file.mojo tests/path/to/test_file_part1.mojo tests/path/to/test_file_part2.mojo
git commit -m "fix(ci): split test_<name>.mojo into 2 files per ADR-009 (≤10 tests)"
```

Pre-commit hooks include `validate_test_coverage.py` which will catch coverage regressions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Updating CI workflow | Considered updating `comprehensive-tests.yml` to reference new filenames | Not needed — CI uses `test_*.mojo` glob patterns that auto-discover files | Always check if CI uses glob patterns before assuming workflow changes are needed |
| Keeping original file | Considered renaming original instead of deleting | Would result in 3 files total (original + 2 parts), doubling test execution | Delete the original; the split files ARE the replacement |
| 5+7 test split | Considered keeping one file at the limit (10) | Leaves no headroom for future tests without triggering another split | Target ≤8 per file to provide buffer for future additions |

## Results & Parameters

### Session: Issue #3629 — ProjectOdyssey

**File split**: `tests/configs/test_merging.mojo` (12 tests) → `part1` (8) + `part2` (4)

**Test distribution**:

```
test_merging_part1.mojo (8 tests):
  - test_merge_two_configs
  - test_merge_empty_configs
  - test_merge_default_and_paper
  - test_merge_preserves_default_values
  - test_three_level_merge
  - test_experiment_overrides_all
  - test_three_level_merge_baseline_experiment
  - test_merge_nested_structures

test_merging_part2.mojo (4 tests):
  - test_merge_with_dotted_keys
  - test_merge_type_conflicts
  - test_merge_multiple_times
  - test_merge_associativity
```

**Key facts**:

- CI failure rate before fix: 13/20 recent runs (65%)
- CI group: `Configs` — uses `just test-group tests/configs "test_*.mojo"`
- No CI workflow YAML changes needed (glob auto-discovery)
- All pre-commit hooks passed on first attempt
- PR: HomericIntelligence/ProjectOdyssey#4423

### Commit message template

```
fix(ci): split test_<name>.mojo into 2 files per ADR-009 (≤10 tests)

Splits tests/<path>/test_<name>.mojo (<N> fn test_ functions) into two
files of ≤8 tests each to fix intermittent heap corruption crashes in
Mojo v0.26.1 (libKGENCompilerRTShared.so JIT fault) in the <Group> CI group.

- test_<name>_part1.mojo: <N1> tests (<categories>)
- test_<name>_part2.mojo: <N2> tests (<categories>)

Each file includes the ADR-009 tracking comment header. No tests deleted.
CI workflow uses test_*.mojo glob — no workflow changes needed.

Closes #<issue>
```
