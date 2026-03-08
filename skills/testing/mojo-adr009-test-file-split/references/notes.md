# Session Notes: Mojo ADR-009 Test File Split

## Session Details

- **Date**: 2026-03-07
- **Project**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3441
- **PR**: #4233
- **Branch**: `3441-auto-impl`

## Problem

`tests/shared/data/datasets/test_emnist.mojo` had 21 `fn test_` functions. ADR-009 limits
Mojo test files to ≤10 `fn test_` functions due to a JIT heap corruption bug in Mojo v0.26.1
(`libKGENCompilerRTShared.so`). The Data Datasets CI group was failing non-deterministically
(13/20 recent runs on `main`).

Sample failing CI run: `22755966807`

## File Before Split

```
tests/shared/data/datasets/test_emnist.mojo — 21 fn test_ functions
```

Functions in order:
1. test_emnist_init_balanced
2. test_emnist_init_byclass
3. test_emnist_init_digits
4. test_emnist_init_letters
5. test_emnist_init_invalid_split
6. test_emnist_len
7. test_emnist_getitem_index
8. test_emnist_getitem_negative_index
9. test_emnist_getitem_out_of_bounds
10. test_emnist_shape
11. test_emnist_num_classes_balanced
12. test_emnist_num_classes_byclass
13. test_emnist_num_classes_digits
14. test_emnist_num_classes_letters
15. test_emnist_num_classes_mnist
16. test_emnist_get_train_data
17. test_emnist_get_test_data
18. test_emnist_train_vs_test_sizes
19. test_emnist_data_label_consistency
20. test_emnist_all_valid_splits
21. test_emnist_performance_random_access

## Files After Split

- `test_emnist_part1.mojo`: tests 1–9 (init + access) — 9 fn test_
- `test_emnist_part2.mojo`: tests 10–17 (shape + class counts + integration) — 8 fn test_
- `test_emnist_part3.mojo`: tests 18–21 (edge cases + performance) — 4 fn test_

## CI Workflow

The `Data` test group in `comprehensive-tests.yml` uses:
```
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo ..."
```

The `datasets/test_*.mojo` wildcard automatically picks up the new `_part1/2/3` files.
No workflow changes required.

## Pre-commit Results

All hooks passed on commit:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
- Fix Mixed Line Endings: Passed

## Key Commands Used

```bash
# Verify test counts in each new file
grep -c "^fn test_" tests/shared/data/datasets/test_emnist_part1.mojo  # → 9
grep -c "^fn test_" tests/shared/data/datasets/test_emnist_part2.mojo  # → 8
grep -c "^fn test_" tests/shared/data/datasets/test_emnist_part3.mojo  # → 4

# Verify CI pattern covers new files
grep -A2 "datasets" .github/workflows/comprehensive-tests.yml
# → pattern: "test_*.mojo datasets/test_*.mojo ..."

# Stage and commit
git add tests/shared/data/datasets/test_emnist.mojo  # deleted
git add tests/shared/data/datasets/test_emnist_part1.mojo
git add tests/shared/data/datasets/test_emnist_part2.mojo
git add tests/shared/data/datasets/test_emnist_part3.mojo
```

## ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_emnist.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

This comment is placed in the module docstring immediately after the description paragraph.
