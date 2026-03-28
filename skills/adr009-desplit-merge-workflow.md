---
name: adr009-desplit-merge-workflow
description: "Use when: (1) reversing ADR-009 test file splitting by merging _partN.mojo files
  back into single unified test files, (2) ADR-009 workaround is no longer needed and test file
  bloat from splitting needs cleanup, (3) performing post-merge audit for dropped struct definitions
  after running a merge script. CRITICAL: merge scripts commonly have a dedup bug where
  _deduplicate_functions() assigns ALL struct/alias/var definitions the generic name top-level,
  causing only the first struct to survive — silently dropping all subsequent struct definitions."
category: testing
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
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

## When to Use

- ADR-009 workaround is being reversed (splitting no longer needed)
- Test file bloat from `_partN.mojo` splitting needs cleanup
- Merging any set of Mojo test files that were mechanically split
- Automated merge of test files with shared imports and independent test functions
- **Post-merge audit**: checking for dropped struct definitions, stale imports, missing constants

## CRITICAL: Dedup Bug Warning

**The `_deduplicate_functions()` function in merge scripts assigns ALL struct/alias/var definitions the name `"<top-level>"`. The deduplication then keeps only the FIRST definition with that name, silently dropping all subsequent struct definitions. This causes CI compile failures with undefined type errors.**

This bug causes **silent data loss** — no warning is emitted, no error is thrown during the merge. The only symptom is CI compile failures after the fact.

Affected file types: any merged file where 2 or more part files each defined at least one struct.

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

#### Step 1: Run the merge script

Run `scripts/merge_split_tests.py` (or equivalent) over the target directories. This handles:
- Combining imports (deduplicating by module name)
- Merging test functions from all part files
- Updating the CI workflow patterns

#### Step 2: CRITICAL Post-Merge Audit

The merge script has a **dedup bug**: ALL struct/alias/var definitions get assigned the generic name `"<top-level>"`. The `_deduplicate_functions()` function then keeps only the FIRST one, silently dropping all subsequent structs.

**Audit checklist:**

- [ ] Check every merged file that had 2+ struct definitions in any single part file
- [ ] Verify all `comptime` constants were preserved
- [ ] Verify `run_all_tests.mojo` and similar runner files have updated import paths (not still pointing to `_partN` modules)
- [ ] Verify docstrings don't reference `_part` filenames
- [ ] Fix unclosed docstrings (merge script can mangle multi-line docstrings)
- [ ] Search entire codebase for `_part` imports after any file merge

```bash
# Check for stale _part imports in non-test files
grep -rn "from.*_part[0-9]" tests/ --include="*.mojo"
grep -rn "import.*_part[0-9]" tests/ --include="*.mojo"
```

#### Step 3: Restore dropped code from git history

When a struct definition is confirmed missing from a merged file:

```bash
# Get the struct definition from the original part file
git show <merge-commit>^:tests/path/to/test_foo_part1.mojo | grep -A 30 "struct MissingStruct"
```

Strip it from the diff format and insert it into the merged file in the appropriate location.

#### Step 4: Fix additional merge script casualties

In addition to dropped structs, check for:

```bash
# Missing comptime constants (e.g., DEFAULT_SEED)
git show <merge-commit>^:tests/path/test_foo_part1.mojo | grep "comptime"
grep "comptime" tests/path/test_foo.mojo  # should match

# Unclosed docstrings
python3 -c "
import ast, sys
with open('tests/path/test_foo.mojo') as f:
    content = f.read()
# count triple-quote opens vs closes
opens = content.count('\"\"\"')
if opens % 2 != 0:
    print('UNCLOSED DOCSTRING')
"
```

#### Step 5: Delete the merge script

```bash
git rm scripts/merge_split_tests.py
```

The merge script served its one-time purpose and has ruff lint/format violations (F841 unused variables, formatting issues) that will fail CI.

#### Step 6: Update CI workflow and run pre-commit

Update CI workflow patterns to use merged filenames (not `_part*` wildcards that might accidentally match non-merged split files).

**CI wildcard trap**: A pattern like `test_initializers_*.mojo` will match BOTH old `_part*.mojo` files AND unrelated `_validation.mojo` files. Use `test_initializers*.mojo` (no underscore before wildcard).

```bash
# Run pre-commit to catch ruff violations and other issues
pixi run pre-commit run --all-files
```

#### Step 7: Verify in CI (not just locally)

Running the full local test suite (`just test-mojo`) crashes the machine due to resource constraints. Use targeted group testing:

```bash
just test-group <group-name>
```

Then push to CI for full validation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merge script v1: strip all non-test functions | Stripped helper function signatures and bodies | Helper functions look syntactically similar to boilerplate | Parse helper functions as content to preserve |
| Spawning 5 parallel Haiku agents for directory merges | Planned as Wave 2 of Myrmidon swarm | Script runs in seconds — faster to run directly | Use agents for design/analysis, not for running scripts |
| CI pattern `test_initializers_*.mojo` | Wildcard matched old `_part*.mojo` AND `_validation.mojo` | Lost coverage of `test_initializers_validation.mojo` | Use `test_initializers*.mojo` (no underscore before wildcard) |
| Running `--dry-run` expecting no side effects | Dry-run wrote to dual-version base files in-place | Script's dual-version handling modified base files | True dry-run needs to skip ALL file writes |
| **Trusting merge script dedup for structs** | Script used `"<top-level>"` name for ALL struct/alias/var definitions | Only the FIRST struct survives — all subsequent dropped silently | **CRITICAL**: Extract ACTUAL names for struct definitions; never use a generic placeholder |
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
| ProjectOdyssey | PR #5130, CI Comprehensive Tests pass; merge of 391 split files into 132 unified files; 4 structs recovered from dedup bug | testing-desplit-adr009-merge-workflow.md (v2.0.0) |
