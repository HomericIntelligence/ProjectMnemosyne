---
name: testing-desplit-adr009-merge-workflow
description: 'Reverse ADR-009 test file splitting by merging _partN.mojo files back
  into single test files. Use when: (1) ADR-009 workaround is no longer needed, (2)
  test file bloat from splitting needs cleanup, (3) merging split Mojo test files
  with deduplication. CRITICAL: merge script has a dedup bug that drops struct definitions.'
category: testing
date: 2026-03-27
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: testing-desplit-adr009-merge-workflow.history
tags:
  - adr-009
  - test-splitting
  - merge
  - mojo
  - refactor
  - myrmidon-swarm
  - dedup-bug
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Reverse ADR-009 test file splitting — merge 391 `_partN.mojo` files back into 132 unified test files |
| **Outcome** | All 132 groups merged. Merge script had a critical dedup bug dropping struct definitions — 4 structs lost across 3 files, plus stale imports and missing constants. All fixed in PR #5130. |
| **Verification** | verified-ci (Comprehensive Tests pass, PR merged to main) |
| **History** | [changelog](./testing-desplit-adr009-merge-workflow.history) |

## When to Use

- ADR-009 workaround is being reversed (splitting no longer needed)
- Test file bloat from `_partN.mojo` splitting needs cleanup
- Merging any set of Mojo test files that were mechanically split
- Automated merge of test files with shared imports and independent test functions
- **Post-merge audit**: checking for dropped struct definitions, stale imports, missing constants

## Verified Workflow

### Quick Reference

```bash
# After merge, ALWAYS audit for dropped structs (the merge script has a dedup bug)
# 1. Find files with undefined struct references
for f in $(find tests/ -name "*.mojo"); do
  grep -oP '(?<=var \w+ = )[A-Z]\w+(?=\()' "$f" 2>/dev/null | sort -u | while read s; do
    if ! grep -q "^struct $s" "$f" 2>/dev/null; then
      echo "MISSING: $f uses $s but doesn't define it"
    fi
  done
done

# 2. Check for stale _part imports
grep -rn "from.*_part[0-9]" tests/ --include="*.mojo"

# 3. Check for missing comptime constants
# Compare original part files against merged files for comptime definitions

# 4. Delete the merge script after verification (it has ruff violations)
git rm scripts/merge_split_tests.py
```

### Detailed Steps

1. **Run the merge script** (same as v1.0.0)

2. **CRITICAL: Post-merge audit** (NEW in v2.0.0):

   The merge script (`scripts/merge_split_tests.py`) has a **dedup bug on line 234**: ALL struct/alias/var definitions get assigned the generic name `"<top-level>"`. The `_deduplicate_functions()` function then keeps only the FIRST one, silently dropping all subsequent structs.

   **Audit checklist:**

   - [ ] Check every merged file that had 2+ struct definitions in any single part file
   - [ ] Verify all `comptime` constants were preserved
   - [ ] Verify `run_all_tests.mojo` and similar runner files have updated import paths
   - [ ] Verify docstrings don't reference `_part` filenames
   - [ ] Fix unclosed docstrings (merge script can mangle multi-line docstrings)

3. **Restore dropped code from git history:**

   ```bash
   # Get the struct definition from the original part file
   git show <merge-commit>^:tests/path/to/test_foo_part1.mojo | grep -A 30 "struct MissingStruct"
   ```

4. **Delete the merge script** — it served its purpose and has ruff lint/format violations that will fail CI.

5. **Update CI workflow and run pre-commit**

6. **Verify in CI** (not just locally — local test suite can crash the machine)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merge script v1: strip all non-test functions | Stripped helper function signatures and bodies | Helper functions look syntactically similar to boilerplate | Parse helper functions as content to preserve |
| Spawning 5 parallel Haiku agents for directory merges | Planned as Wave 2 of Myrmidon swarm | Script runs in seconds — faster to run directly | Use agents for design/analysis, not for running scripts |
| CI pattern `test_initializers_*.mojo` | Wildcard matched old `_part*.mojo` AND `_validation.mojo` | Lost coverage of `test_initializers_validation.mojo` | Use `test_initializers*.mojo` (no underscore before wildcard) |
| Running `--dry-run` expecting no side effects | Dry-run wrote to dual-version base files in-place | Script's dual-version handling modified base files | True dry-run needs to skip ALL file writes |
| **Trusting merge script dedup for structs** | Script used `"<top-level>"` name for ALL struct/alias/var definitions | Only the FIRST struct survives — all subsequent dropped silently | **CRITICAL**: Extract ACTUAL names for struct definitions, never use a generic placeholder |
| **Trusting merged files compile** | Assumed merge preserved all code blocks | Also dropped `comptime DEFAULT_SEED` and left unclosed docstrings | Always compile-check merged files, don't just count test functions |
| **Trusting import paths auto-update** | `run_all_tests.mojo` still imported from `_part1` module names | Merge script only updates merged files, not files that import from them | Search entire codebase for `_part` imports after any file merge |
| **Running full test suite locally** | `just test-mojo` to validate | Crashes the machine due to resource constraints | Use `just test-group` for targeted checks, push to CI for full validation |

## Results & Parameters

### Scale

```yaml
split_files_merged: 391
groups_created: 132
directories_affected: 22
test_functions_preserved: 2872
net_files_reduced: 259
net_lines_reduced: 20170
```

### Files Damaged by Dedup Bug (4 structs across 3 files)

```text
tests/shared/data/transforms/test_pipeline.mojo     — missing StubPipeline (7 references)
tests/shared/core/test_composed_op.mojo              — missing ScaleAdd (10+ references)
tests/shared/core/test_elementwise_dispatch.mojo     — missing IncrementOp + AverageOp
```

### Additional Merge Script Casualties

```text
tests/shared/fuzz/test_tensor_fuzz.mojo              — missing comptime DEFAULT_SEED: Int = 42
tests/shared/core/test_elementwise_dispatch.mojo     — unclosed module docstring
tests/shared/data/run_all_tests.mojo                 — stale _part1/_part2 import paths
```

### Merge Script Status

Deleted after merge — served its one-time purpose and had ruff violations (F841 unused variables, formatting issues) that failed CI.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5130, CI Comprehensive Tests pass | [notes.md](./testing-desplit-adr009-merge-workflow.notes.md) |
