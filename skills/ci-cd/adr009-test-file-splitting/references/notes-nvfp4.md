# Session Notes: ADR-009 Test File Splitting (Issue #3440)

## Date

2026-03-07

## Problem

`tests/core/types/test_nvfp4_block.mojo` had 22 `fn test_` functions (limit: 10, target: ≤8),
causing intermittent heap corruption in Mojo v0.26.1 CI (`libKGENCompilerRTShared.so` JIT fault).
CI failure rate: 13/20 recent runs on `main`.

## Initial State

Single file with all 22 tests, no prior splitting:

- Block creation tests (4)
- Round-trip conversion tests (3)
- Scale computation tests (1)
- Accuracy comparison (1)
- Bit packing (1)
- Indexing get/set (4)
- All-negative blocks TEST-001 (3)
- NaN/infinity handling TEST-003 (3)
- Edge cases (2)

## Split Strategy

Grouped by semantic category, 3 files of ≤8 tests each:

- `test_nvfp4_block_part1.mojo` (8 tests): creation + round-trip + scale
- `test_nvfp4_block_part2.mojo` (8 tests): accuracy + bit packing + indexing + TEST-001 negatives
- `test_nvfp4_block_part3.mojo` (6 tests): TEST-001 scale + TEST-003 NaN/inf + edge cases

## Actions Taken

1. Read `test_nvfp4_block.mojo` to catalog all 22 tests
2. Verified CI workflow pattern: `test_*.mojo` glob in `tests/core/types` directory — no update needed
3. Created 3 new files, each with ADR-009 header comment
4. Deleted original file
5. Committed with all pre-commit hooks passing (mojo format, validate test coverage)

## Final State

- 3 files: 8 + 8 + 6 = 22 tests total (all original tests preserved)
- CI glob `pattern: "test_*.mojo"` auto-discovers new files
- No workflow changes needed
- PR #4230 created, auto-merge enabled

## Key Insight

When a `test_*.mojo` file is being replaced (not incrementally split), delete the original
file entirely rather than leaving it with a reduced test set. The `part{N}` naming convention
(`test_<name>_part1.mojo`, etc.) is cleaner than derived names when the original had no
natural subgrouping names.
