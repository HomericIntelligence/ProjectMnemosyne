---
name: regression-test-from-issue-plan
description: "Add missing regression tests by reading the issue's implementation plan. Use when: (1) an issue references a test by name that should exist as a harness, (2) a bug fix landed but the named test was never added, (3) issue comments contain hand-computed expected values."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Purpose** | Recover and implement regression tests specified in GitHub issue plans that were never added |
| **Input** | GitHub issue number with a named test in the description or comments |
| **Output** | New test function with verified passing behavior |
| **Risk** | Low — additive only, no production code changes |

## When to Use

- Issue description says "test X will serve as the regression harness" but test X does not exist in the codebase
- A bug fix is already merged to main but the paired regression test is missing
- Issue comments contain hand-computed expected values for specific inputs
- Issue cross-references another issue that planned a test (e.g. "follow-up from #NNNN")
- `grep -r "test_<name>" tests/` returns no matches for a test the issue expects to exist

## Verified Workflow

### Quick Reference

```bash
# 1. Find what test name the issue expects
gh issue view <N> | grep "test_"
gh issue view <N> --comments | grep -A5 "test_"

# 2. Check if test exists
grep -r "test_<name>" tests/

# 3. Check if the fix is already in source
git log --oneline -- <file> | head -5

# 4. Read the plan for expected values
gh issue view <REFERENCED_ISSUE> --comments

# 5. Count tests in target file (ADR-009: ≤10 per file)
grep -c "^fn test_" tests/path/to/test_file_part2.mojo

# 6. Validate pre-commit before commit
SKIP=mojo-format pixi run pre-commit run --files <file>
```

### Steps

1. **Read the issue** — `gh issue view <N>` — note exact test name mentioned
2. **Search for the test** — `grep -r "test_<name>" tests/` confirms it is missing
3. **Check fix status** — `git log --oneline -- shared/core/<file>.mojo | head -5`
4. **Read the referenced issue plan** — `gh issue view <REFERENCED> --comments` for expected values
5. **Find the right part file** — count tests with `grep -c "^fn test_"` per file, pick one with room
6. **Write the test** — use hand-computed expected values from the plan; manually set strides if testing stride logic
7. **Add to main()** — append the call in the appropriate section
8. **Validate** — `SKIP=mojo-format pixi run pre-commit run --files <file>`
9. **Commit and PR** — `git add <file> && git commit -m "test(scope): add <name> regression test"`

### Key insight: `_get_float64` vs stride-based indexing

When `as_contiguous()` uses `_get_float64(i)` with a flat index, it reads `index * dtype_size` from
memory — ignoring strides entirely. This means manually mutating `_strides` changes what
`is_contiguous()` reports but does NOT change the flat memory layout. The non-contiguous branch of
`as_contiguous()` that uses stride arithmetic will reorder values; the flat-copy branch preserves them.
Know which branch is exercised before computing expected values.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Search for test by exact name | `grep -r "test_contiguous_stride_correct_values" tests/` | Returned no matches — test never existed | Absence of a test is exactly the bug to fix |
| Checked existing branch for the fix | Expected `4088-fix-as-contiguous` branch to contain the test | Branch had a different change (pre-commit hook), not the regression test | Branch names can be misleading; use `git diff main..<branch> -- <file>` to confirm |
| Considered adding to original test file | `test_utility.mojo` seemed consistent with issue plan | File had 43 tests — far exceeds ADR-009 10-test limit | Always count tests before adding; use numbered part files |
| Assumed the fix still needed implementing | Expected the source fix to be missing | Fix was already in `shape.mojo` from a prior commit | Check `git log` for the source file first — fix and test can land separately |

## Results & Parameters

**Test template for stride-based bug regression (Mojo)**:

```mojo
fn test_contiguous_stride_correct_values() raises:
    """Regression test: as_contiguous() must use stride-based indexing.

    For shape [2, 3] with strides [1, 2] (column-major), the stride-based
    source offsets produce:
      Output[0,0] = src[0*1 + 0*2] = src[0] = 0.0
      Output[0,1] = src[0*1 + 1*2] = src[2] = 2.0
      Output[0,2] = src[0*1 + 2*2] = src[4] = 4.0
      Output[1,0] = src[1*1 + 0*2] = src[1] = 1.0
      Output[1,1] = src[1*1 + 1*2] = src[3] = 3.0
      Output[1,2] = src[1*1 + 2*2] = src[5] = 5.0
    Flat output: [0.0, 2.0, 4.0, 1.0, 3.0, 5.0]
    """
    var shape = List[Int]()
    shape.append(2)
    shape.append(3)
    var a = arange(0.0, 6.0, 1.0, DType.float32)
    var b = a.reshape(shape)

    # Manually set column-major strides to simulate non-contiguous view
    b._strides[0] = 1
    b._strides[1] = 2

    assert_false(b.is_contiguous(), "Column-major tensor should not be contiguous")
    var c = as_contiguous(b)
    assert_true(c.is_contiguous(), "as_contiguous() result should be contiguous")

    assert_almost_equal(c._get_float64(0), 0.0, 1e-6, "c[0,0] should be 0.0")
    assert_almost_equal(c._get_float64(1), 2.0, 1e-6, "c[0,1] should be 2.0")
    assert_almost_equal(c._get_float64(2), 4.0, 1e-6, "c[0,2] should be 4.0")
    assert_almost_equal(c._get_float64(3), 1.0, 1e-6, "c[1,0] should be 1.0")
    assert_almost_equal(c._get_float64(4), 3.0, 1e-6, "c[1,1] should be 3.0")
    assert_almost_equal(c._get_float64(5), 5.0, 1e-6, "c[1,2] should be 5.0")
```

**ADR-009 constraint**: ≤10 `fn test_` functions per `.mojo` file. Check with:

```bash
grep -c "^fn test_" tests/path/to/file.mojo
```

**Strides for common shapes**:

| Shape | Row-major (contiguous) | Column-major (non-contiguous) |
|-------|------------------------|-------------------------------|
| (2, 3) | `[3, 1]` | `[1, 2]` |
| (3, 4) | `[4, 1]` | `[1, 3]` |
| (2, 3, 4) | `[12, 4, 1]` | `[1, 2, 6]` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4088, PR #4868 | [notes.md](../references/notes.md) |
