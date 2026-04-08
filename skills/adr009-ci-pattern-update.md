---
name: adr009-ci-pattern-update
description: "Update CI workflow files when splitting ADR-009 test files. Use when: (1) a Mojo test file split requires updating comprehensive-tests.yml because the CI group uses an explicit filename list, (2) verifying whether a CI group uses glob auto-discovery or explicit filenames before editing the workflow, (3) updating validate_test_coverage.py after a split, (4) splitting files in groups like Core Activations & Types, Core Tensors, or Core Utilities that use explicit filename patterns."
category: ci-cd
date: 2026-04-07
version: "1.1.0"
user-invocable: false
tags: [adr-009, mojo, ci, workflow, glob, explicit-pattern, validate-test-coverage]
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Consolidate all knowledge about CI workflow updates needed when splitting ADR-009 test files |
| **Outcome** | Single skill covering explicit-filename CI groups, glob-pattern auto-discovery, validate_test_coverage.py updates, and the decision tree for which update path applies |

> **ADR-009 is now OBSOLETE** — the heap corruption bug has been fixed. This skill is preserved for historical reference and for understanding existing split files. For new Mojo heap corruption, use ASAN builds instead.

## When to Use

- A Mojo test file is being split per ADR-009 and you need to determine whether the CI workflow requires updating
- The CI group for the target file uses an explicit filename list (not `test_*.mojo` glob)
- Splitting a file in CI groups like `Core Activations & Types`, `Core Tensors`, `Core Utilities`, or `Shared Infra` that enumerate files explicitly
- After splitting, new `_partN.mojo` files are not appearing in CI runs
- `validate_test_coverage.py` pre-commit hook fails after a split
- The issue says "update CI workflow" but you need to verify whether that is actually needed

## Verified Workflow

### Quick Reference

```bash
# Step 1: Determine CI pattern type for the file
grep -n "<filename>.mojo" .github/workflows/comprehensive-tests.yml

# If filename appears in a space-separated pattern: → explicit list (update required)
# If only test_*.mojo or path/test_*.mojo: → glob (no workflow update needed)

# Step 2: Count tests accurately (avoid ADR-009 header comment false positives)
grep -c "^fn test_[a-z]" tests/<path>/<filename>.mojo

# Step 3: After splitting, verify the workflow change
grep "old_filename\|part1\|part2" .github/workflows/comprehensive-tests.yml

# Step 4: Check validate_test_coverage.py independently
grep "<filename>" scripts/validate_test_coverage.py
```

### Decision Tree

```text
grep the original filename in comprehensive-tests.yml
├── Found (hardcoded in pattern:) → edit workflow to reference all new split files
└── Not found → check for glob pattern covering the directory
    ├── Glob pattern exists (e.g., training/test_*.mojo) → NO workflow edit needed
    └── No pattern at all → add glob pattern or explicit filenames

Then ALWAYS check validate_test_coverage.py separately:
grep "<filename>" scripts/validate_test_coverage.py
├── Found in exclusion list → replace 1 entry with N entries for new split files
└── Not found → no change needed
```

### Step 1: Determine the CI pattern type

Before splitting, check whether the CI group uses a glob or explicit filename list:

```bash
grep -n "test_original_name" .github/workflows/comprehensive-tests.yml
```

**Explicit list (update required):**
```yaml
# Space-separated filenames — new split files will NOT be auto-discovered
pattern: "test_tensors.mojo test_arithmetic.mojo test_reduction_forward.mojo ..."
```

**Glob pattern (no update needed):**
```yaml
# Wildcard — new test_*_partN.mojo files are automatically discovered
pattern: "test_*.mojo"
# or:
pattern: "training/test_*.mojo testing/test_*.mojo"
```

### Step 2: Count and plan the split

```bash
# Use [a-z] suffix to avoid counting ADR-009 header comment lines
grep -c "^fn test_[a-z]" tests/<path>/<filename>.mojo
```

Target <=8 tests per file (ADR-009 hard limit is 10; <=8 provides a safety buffer):

```text
11-16 tests → 2-way split (<=8 each)
17-24 tests → 3-way split (<=8 each)
25+   tests → 4-way split (<=7 each)
47    tests → 6 files (8+8+8+8+8+7)
```

### Step 3: Create split files with ADR-009 header

Each new file must begin with the ADR-009 comment block before the docstring:

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Tests for ... - Part N: <focus area>."""
```

Each part file must be fully self-contained:
- Only the imports it actually uses (trim unused imports — unused imports cause compile errors in Mojo)
- Its own `fn main() raises:` calling only its subset of tests
- Duplicate any helper structs verbatim (Mojo test files cannot import from sibling test files)

**Naming conventions:**
- Generic: `test_<original>_part1.mojo`, `test_<original>_part2.mojo` (no underscore before number)
- Semantic (preferred when groupings are clear): `test_extensor_slicing_1d.mojo`, `test_extensor_slicing_2d.mojo`

### Step 4 (Explicit list only): Update the CI workflow

Replace the original filename with all new split filenames in the `pattern:` field:

```yaml
# Before:
pattern: "... test_original.mojo ..."

# After (add ADR-009 comment above the pattern):
# ADR-009: test_original.mojo split into N parts (<=8 tests each)
# to avoid Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so)
pattern: "... test_original_part1.mojo test_original_part2.mojo test_original_part3.mojo ..."
```

Do NOT keep the original filename in the pattern — it causes duplicate test runs.

### Step 5: Update validate_test_coverage.py (always check independently)

A glob in the CI workflow does NOT mean the coverage script also uses a glob:

```bash
grep "test_original_name" scripts/validate_test_coverage.py
```

If found in an exclusion list, replace the single entry with entries for each part file:

```python
# Before
"tests/shared/training/test_original.mojo",

# After
"tests/shared/training/test_original_part1.mojo",
"tests/shared/training/test_original_part2.mojo",
```

If the CI group had `continue-on-error: true` as a heap corruption workaround, remove it now.

### Step 6: Delete the original file

```bash
git rm tests/<path>/test_original.mojo
```

Do NOT keep the original alongside split files — it causes duplicate test runs.

Some teams rename to `.DEPRECATED` to preserve git history visibility:
```bash
git mv tests/path/test_original.mojo tests/path/test_original.mojo.DEPRECATED
```

### Step 7: Verify counts and workflow

```bash
# Verify per-file counts (all must be <=8)
for f in tests/<path>/test_<prefix>_part*.mojo; do
  echo "$f: $(grep -c '^fn test_[a-z]' "$f") tests"
done

# Verify old filename gone from workflow (should only appear in ADR-009 comments)
grep "test_original\.mojo" .github/workflows/comprehensive-tests.yml

# Verify new files are in workflow (explicit list case)
grep "test_original_part" .github/workflows/comprehensive-tests.yml
```

### Step 8: Commit with pre-commit validation

```bash
git add .github/workflows/comprehensive-tests.yml \
        scripts/validate_test_coverage.py \
        tests/<path>/test_original.mojo \
        tests/<path>/test_original_part1.mojo \
        tests/<path>/test_original_part2.mojo \
        tests/<path>/test_original_part3.mojo

# Run hooks one at a time (pre-commit CLI does not accept multiple hook names in one call)
pixi run pre-commit run mojo-format --files ...
pixi run pre-commit run validate_test_coverage --files ...
pixi run pre-commit run check-yaml --files .github/workflows/comprehensive-tests.yml

git commit -m "fix(ci): split test_<name>.mojo into N files per ADR-009"
```

Do NOT use `just pre-commit` in worktree shell environments — `just` is not installed there.

### When a Glob Already Covers the Split Files

If the CI workflow uses a glob pattern, no workflow edit is needed. Only verify:

1. `validate_test_coverage.py` — update any exclusion list entry
2. `comprehensive-tests.yml` — confirm glob pattern (`training/test_*.mojo`) already covers the new files

Example: `test_rmsprop.mojo` → `test_rmsprop_part1.mojo` + `test_rmsprop_part2.mojo`  
Both files match `training/test_*.mojo` — no workflow edit needed.

**Tip**: Issue descriptions sometimes defensively say "Update comprehensive-tests.yml to reference the new filenames" even when the glob already covers them. Always verify the actual workflow content rather than trusting the issue description.

### Dedicated CI Groups for File Families

When splitting an entire family of related files (e.g., all `test_extensor_*.mojo`), create a dedicated CI group to improve failure signal isolation:

```yaml
# Add before the overloaded group:
# ---- ExTensor tests (split per ADR-009 to avoid heap corruption) ----
- name: "Core ExTensor"
  path: "tests/shared/core"
  # All extensor files split per ADR-009 (<=10 tests each).
  pattern: "test_extensor_getset_float32.mojo test_extensor_inplace_ops.mojo test_extensor_randn.mojo test_extensor_reflected_ops.mojo test_extensor_serialization.mojo test_extensor_slicing_1d.mojo test_extensor_slicing_2d.mojo test_extensor_slicing_edge.mojo test_extensor_neg_pos.mojo test_extensor_abs_ops.mojo"
```

Remove the same files from the overloaded group to avoid duplicate runs. Target <=10 files per CI group.

**CI wildcard trap**: Use `test_initializers*.mojo` (no underscore before wildcard), NOT `test_initializers_*.mojo` — the underscore version also matches unrelated files like `test_initializers_validation.mojo`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming glob auto-discovery | Expected new `_partN.mojo` files to appear in CI without checking | CI groups like Core Activations & Types, Core Tensors use explicit filename lists, not globs | Always `grep "test_original_name" .github/workflows/` before assuming glob coverage |
| Keeping original file in pattern | Left `test_original.mojo` in workflow alongside part files | Causes duplicate test execution (all original tests run twice) | Delete original entirely and remove from workflow pattern |
| Trusting issue description | Issue said "Update comprehensive-tests.yml to reference the new filenames" | Glob pattern already covered new files; description was written defensively | Always verify actual workflow content rather than trusting issue descriptions |
| Skipping validate_test_coverage.py | Assumed CI workflow was the only file to update | Pre-commit `Validate Test Coverage` hook failed with deleted filename | Always check both `comprehensive-tests.yml` AND `validate_test_coverage.py` independently |
| Using `grep "^fn test_"` without `[a-z]` | Counted lines matching the basic pattern | ADR-009 header comment text itself matches `fn test_` | Use `^fn test_[a-z]` to match only real function definitions |
| Copying all imports to each split file | Each split file had the full import block from original | Unused imports cause compile warnings or errors in Mojo | Trim imports to only what each split file actually uses |
| Using `_part_1` naming (underscore before number) | Considered `test_foo_part_1.mojo` naming | Sorts inconsistently in file listings | Use `_part1`, `_part2` (no underscore before number) |
| Placing ADR-009 comment inside docstring | Put `# ADR-009:` lines inside `"""..."""` | Comments inside string literals are not code comments in Mojo | Place ADR-009 comment block before the docstring at the top of the file |
| CI pattern `test_initializers_*.mojo` | Used underscore before wildcard | Matched old `_part*.mojo` AND unrelated `_validation.mojo`, losing coverage | Use `test_initializers*.mojo` (no underscore before wildcard) |
| Multi-hook pre-commit | `pixi run pre-commit run hook1 hook2 --files ...` | pre-commit CLI does not accept multiple hook names in one call | Run hooks one at a time |
| `just pre-commit` in worktree | Ran `just pre-commit` to use project's justfile recipe | `just` not installed in worktree shell environment | Use `pixi run pre-commit run` directly in worktrees |
| Leaving split files in overloaded group | Added new files to existing large CI group | Group with 26 files had poor failure signal isolation | Create dedicated CI group for file families |

## Results & Parameters

### CI Pattern Type Summary

| Pattern Type | Example | Workflow Update? | validate_test_coverage.py? |
|---|---|---|---|
| Glob, same dir | `test_*.mojo` | No | Check if file is in exclusion list |
| Glob, with path | `training/test_*.mojo` | No | Check if file is in exclusion list |
| Explicit list | `test_a.mojo test_b.mojo` | **Yes — required** | Check if file is in exclusion list |

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file (ADR-009 hard limit) | 10 |
| Target tests per file (safety buffer) | 8 |
| Naming convention | `test_<original>_partN.mojo` (no underscore before number) |
| ADR-009 header comment | Required in every split file, placed before docstring |

### Verified On (CI Groups with Explicit Filename Lists)

| Project | Issue / PR | File Split | CI Group |
|---------|------------|------------|---------|
| ProjectOdyssey | Issue #3419, PR #4175 | `test_elementwise_edge_cases.mojo` (28 tests → 4 files) | Core Activations & Types |
| ProjectOdyssey | Issue #3415, PR #4159 | `test_reduction_forward.mojo` → 4 files | Core Tensors |
| ProjectOdyssey | Issue #3452, PR #4263 | `test_integration.mojo` (19 tests → 3 files) | Core Utilities |
| ProjectOdyssey | Issue #3400, PR #4111 | `test_activations.mojo` (45 tests → 6 files) | Core Activations & Types |
| ProjectOdyssey | Issue #3476 | `test_extensor_*.mojo` family | New "Core ExTensor" group created |

### Verified On (Glob Pattern — No Workflow Update)

| Project | Issue / PR | File Split | CI Pattern |
|---------|------------|------------|-----------|
| ProjectOdyssey | rmsprop split | `test_rmsprop.mojo` (11 → 8+3) | `training/test_*.mojo` |
| ProjectOdyssey | Issue #3465, PR #4292 | `test_metrics.mojo` (16 → 8+8) | glob; validate_test_coverage.py updated |
| ProjectOdyssey | Issue #3397, PR #4094 | `test_assertions.mojo` (61 → 9 files) | glob |

**Related:** `adr009-test-file-split-workflow` (full historical reference), `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
