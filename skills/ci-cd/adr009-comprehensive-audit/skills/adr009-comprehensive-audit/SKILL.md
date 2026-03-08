---
name: adr009-comprehensive-audit
description: "Audit all Mojo test files in a family/module for ADR-009 compliance when fixing one violation, then create a dedicated CI group. Use when: (1) fixing an ADR-009 violation and sibling files may also exceed the limit, (2) no dedicated CI group exists for the test family, (3) split files are buried in an overloaded CI group."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Fixing one ADR-009 file in isolation misses sibling violations; split files buried in overloaded CI groups still cause flaky failures |
| **ADR** | ADR-009 — max ≤10 `fn test_` functions per `.mojo` file |
| **Pattern** | Audit entire file family, split all violators, create dedicated CI group |
| **Split naming** | Use semantic suffixes (`_1d`, `_2d`, `_edge`) over generic (`_part1`, `_part2`) |
| **CI group size** | 10 files max per group; dedicated groups improve failure signal isolation |

## When to Use

- An issue asks to fix one ADR-009 file but related files in the same directory may also violate the limit
- Split files for a test family (e.g., `test_extensor_*.mojo`) are scattered across an overloaded CI group
- No dedicated CI group exists for a family of related tests
- A CI group has >15 test files (risk of slow or flaky runs)
- After splitting, the original file needs to be tracked as `.DEPRECATED`

## Verified Workflow

### Step 1: Audit the entire file family

```bash
# Count tests in ALL files matching the pattern
for f in tests/shared/core/test_extensor_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

Identify every file where count > 10. Fix ALL of them in one PR.

### Step 2: Determine split strategy by count

| Test count | Strategy |
|-----------|----------|
| 11-16 | 2-way split (≤8 each) |
| 17-24 | 3-way split (≤8 each) |
| 25+ | 4-way split (≤7 each) |

### Step 3: Choose semantic suffix names

Prefer descriptive suffixes over generic `_part1`/`_part2`:

```text
test_extensor_slicing.mojo (19 tests) →
  test_extensor_slicing_1d.mojo    (8: basic + strided)
  test_extensor_slicing_2d.mojo    (6: multi-dim + batch)
  test_extensor_slicing_edge.mojo  (5: edge cases + copy semantics)

test_extensor_unary_ops.mojo (12 tests) →
  test_extensor_neg_pos.mojo  (5: __neg__ and __pos__)
  test_extensor_abs_ops.mojo  (7: __abs__ and combined)
```

### Step 4: Add ADR-009 header to each new file

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Step 5: Rename originals to .DEPRECATED

```bash
git mv tests/path/test_original.mojo tests/path/test_original.mojo.DEPRECATED
```

This follows the established ADR-009 pattern and preserves git history.

### Step 6: Create dedicated CI group

In `.github/workflows/comprehensive-tests.yml`, add a new group **before** the overloaded group:

```yaml
# ---- <Family> tests (split per ADR-009 to avoid heap corruption) ----
- name: "Core ExTensor"
  path: "tests/shared/core"
  # All extensor files split per ADR-009 (≤10 tests each).
  # See docs/adr/ADR-009-heap-corruption-workaround.md
  pattern: "test_extensor_getset_float32.mojo test_extensor_inplace_ops.mojo test_extensor_randn.mojo test_extensor_reflected_ops.mojo test_extensor_serialization.mojo test_extensor_slicing_1d.mojo test_extensor_slicing_2d.mojo test_extensor_slicing_edge.mojo test_extensor_neg_pos.mojo test_extensor_abs_ops.mojo"
```

Remove the same files from the overloaded group to avoid duplicate runs.

### Step 7: Verify counts in split files

```bash
for f in tests/shared/core/test_extensor_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

All non-DEPRECATED files must show ≤10.

### Step 8: Check workflow references

```bash
grep -n "extensor\|<family>" .github/workflows/comprehensive-tests.yml
```

Verify new files appear in the dedicated group and not in the overloaded group.

## Results & Parameters

**Session results (2026-03-07, issue #3476):**

```text
test_extensor_slicing.mojo: 19 tests → 3 files (8, 6, 5)
test_extensor_unary_ops.mojo: 12 tests → 2 files (5, 7)
New "Core ExTensor" CI group: 10 files, all ≤10 tests
"Core Utilities" group: extensor files removed (was 26 files)
```

**Commit pattern:**

```bash
git commit -m "fix(ci): split extensor test files and add Core ExTensor CI group (ADR-009)

Split test_extensor_slicing.mojo (19 tests) into 3 files:
- test_extensor_slicing_1d.mojo (8 tests)
- test_extensor_slicing_2d.mojo (6 tests)
- test_extensor_slicing_edge.mojo (5 tests)

Split test_extensor_unary_ops.mojo (12 tests) into 2 files:
- test_extensor_neg_pos.mojo (5 tests)
- test_extensor_abs_ops.mojo (7 tests)

Added dedicated 'Core ExTensor' CI group in comprehensive-tests.yml.
Old files renamed to .DEPRECATED per ADR-009 pattern.

Closes #<issue>
"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix only the issue-specified file | Addressed only `test_extensor_new_methods.mojo` as listed in the issue | That file was already split in a previous commit; sibling files `test_extensor_slicing.mojo` (19) and `test_extensor_unary_ops.mojo` (12) still violated ADR-009 | Always audit ALL files in the family, not just the one named in the issue |
| Using `_part1`/`_part2` naming | Issue body suggested `test_extensor_new_methods_part1.mojo` as the naming convention | Generic names lose semantic context about what tests are in each file | Use descriptive semantic suffixes (`_1d`, `_2d`, `_edge`, `_neg_pos`, `_abs_ops`) |
| Leaving extensor files in "Core Utilities" | Split files were added to the existing "Core Utilities" group | "Core Utilities" had 26 files — too large, poor failure signal isolation | Create a dedicated CI group for the file family after splitting |
| Assuming issue file is unresolved | Treated `test_extensor_new_methods.mojo` as still needing splitting | It was already split in commit `8a78d3aa`; DEPRECATED file existed | Check git log for the target file before starting work: `git log --all --oneline -- path/to/file` |
