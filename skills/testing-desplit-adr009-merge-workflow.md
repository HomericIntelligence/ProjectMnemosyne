---
name: testing-desplit-adr009-merge-workflow
description: 'Reverse ADR-009 test file splitting by merging _partN.mojo files back
  into single test files. Use when: (1) ADR-009 workaround is no longer needed, (2)
  test file bloat from splitting needs cleanup, (3) merging split Mojo test files
  with deduplication.'
category: testing
date: 2026-03-25
version: 1.0.0
user-invocable: false
verification: verified-local
tags:
  - adr-009
  - test-splitting
  - merge
  - mojo
  - refactor
  - myrmidon-swarm
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Reverse ADR-009 test file splitting — merge 391 `_partN.mojo` files back into 132 unified test files |
| **Outcome** | All 132 groups merged, all tests pass locally, net -20,170 lines, -259 files. PR #5122. |
| **Verification** | verified-local (full `just test-mojo` passes, CI pending) |

## When to Use

- ADR-009 workaround is being reversed (splitting no longer needed)
- Test file bloat from `_partN.mojo` splitting needs cleanup
- Merging any set of Mojo test files that were mechanically split
- Automated merge of test files with shared imports and independent test functions

## Verified Workflow

### Quick Reference

```bash
# Dry-run to see what would be merged
python3 scripts/merge_split_tests.py --dry-run

# Merge a single directory
python3 scripts/merge_split_tests.py --directory tests/shared/core/

# Merge everything
python3 scripts/merge_split_tests.py

# Delete the old part files after verifying
find tests/ -name "test_*_part*.mojo" -exec git rm {} +

# Update CI workflow
# (manual — replace _part* patterns with single filenames)

# Verify
just build && just test-mojo
```

### Detailed Steps

1. **Build the merge script** (`scripts/merge_split_tests.py`):
   - Discovers all `test_*_partN.mojo` files recursively
   - Groups by base name (strips `_partN` suffix)
   - Parses each file: imports, test functions, helper functions, main()
   - Deduplicates imports (union across all parts)
   - Concatenates test functions in part order
   - Creates unified `fn main()` calling all test functions
   - Handles dual-version cases (base file + parts both exist)

2. **Run with `--dry-run` first** to verify grouping and counts

3. **Run the actual merge** — creates merged files, does NOT delete originals

4. **Fix merge script edge cases** — the script may strip helper function signatures.
   Check for "failed to parse" errors:
   ```bash
   just test-mojo 2>&1 | grep "failed to parse"
   ```
   For each, compare against `git show main:<original_part_file>` and restore
   missing function signatures/bodies.

5. **Delete part files**: `find tests/ -name "test_*_part*.mojo" -exec git rm {} +`

6. **Update CI workflow** (`.github/workflows/comprehensive-tests.yml`):
   - Replace `test_foo_part*.mojo` with `test_foo.mojo`
   - Replace explicit part lists with single filenames
   - Remove ADR-009 comments
   - Fix wildcard patterns that matched `_part*` but not the merged file

7. **Fix test coverage hooks**: Update badge and validate coverage

8. **Run full test suite**: `just build && just test-mojo`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merge script v1: strip all non-test functions | Stripped helper function signatures and bodies along with run_all_tests/main | Helper functions (create_basic_block, concatenate_depthwise, struct definitions) look syntactically similar to boilerplate | Parse helper functions as content to preserve, not boilerplate to strip |
| Spawning 5 parallel Haiku agents for directory merges | Planned as Wave 2 of Myrmidon swarm | Script runs in seconds — faster to run directly than spawn agents | Use agents for design/analysis, not for running scripts that already exist |
| CI pattern `test_initializers_*.mojo` after merge | Wildcard matched old `_part*.mojo` files AND `_validation.mojo` | Changing to `test_initializers.mojo` lost coverage of `test_initializers_validation.mojo` | Use `test_initializers*.mojo` (no underscore before wildcard) to match both |
| Running `--dry-run` expecting no side effects | Dry-run wrote to dual-version base files (modified them in-place) | Script's dual-version handling modified base files even in dry-run mode | True dry-run needs to skip file writes entirely, not just skip creating new files |

## Results & Parameters

### Scale

```yaml
split_files_merged: 391
groups_created: 132
directories_affected: 22
dual_version_cases: 11  # base file + parts both existed
missing_part1_anomalies: 2  # test_unsigned, test_tensor_factories
test_functions_preserved: 2872
net_files_reduced: 259
net_lines_reduced: 20170
```

### Merge Script Location

```text
scripts/merge_split_tests.py (614 lines)

Usage:
  python3 scripts/merge_split_tests.py                          # All directories
  python3 scripts/merge_split_tests.py --directory tests/shared/core/  # One directory
  python3 scripts/merge_split_tests.py --dry-run                # Preview only
```

### Files That Needed Manual Fixes After Merge

```text
tests/models/test_googlenet_e2e.mojo      — concatenate_depthwise + GoogLeNetSmall struct
tests/models/test_googlenet_layers.mojo   — concatenate_depthwise body
tests/models/test_lenet5_e2e.mojo         — LeNet5.update_parameters method
tests/models/test_resnet18_layers.mojo    — create_basic_block signature
tests/training/test_training_infrastructure.mojo — mock_compute_loss signature
```

All had the same bug: helper function closing `) raises -> AnyTensor:` stripped.

### CI Workflow Changes

```text
7 pattern fields updated in comprehensive-tests.yml
3 ADR-009 comments removed
Key fix: test_initializers_*.mojo → test_initializers*.mojo (keep wildcard for _validation)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5122, full test suite pass | [notes.md](./testing-desplit-adr009-merge-workflow.notes.md) |
