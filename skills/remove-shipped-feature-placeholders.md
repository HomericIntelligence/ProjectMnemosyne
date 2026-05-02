---
name: remove-shipped-feature-placeholders
description: 'Remove stale ''feature not yet supported'' comments, TODO placeholders,
  and disabled test stubs from source code once the underlying feature ships natively.
  Use when: an issue asks to document a dtype/language feature that was aliased or
  stubbed, code has ''X aliases to Y until Z is supported'' comments, or tests are
  disabled with pass-placeholder and TODO.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Skill: remove-shipped-feature-placeholders

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-04 |
| Objective | Remove stale BF16 alias/placeholder comments from Mojo training code after DType.bfloat16 shipped natively |
| Outcome | Success — 4 files cleaned, stale NOTE/TODO comments removed, disabled test enabled, PR #3197 created |
| Category | documentation |

## When to Use

Use this skill when:

- An issue says to "document" or "verify support status" of a feature that was previously unsupported (dtype, API, language feature)
- Source code has comments like `# NOTE: X aliases to Y until <language> supports X`
- Source code has comments like `# Will use X when available`
- Tests have `pass  # Placeholder — feature not yet supported in runtime` stubs with commented-out assertions
- Tests have `# TODO(#N): Uncomment when <language> adds X` blocks
- Docstrings say "Currently uses Y as X is not natively supported" when X is now available

## Verified Workflow

### 1. Verify the feature actually shipped

Before removing any comments, confirm native support exists:

```bash
# For Mojo dtypes: grep for the comptime/alias definition
grep -r "bfloat16_dtype\|DType.bfloat16" shared/ --include="*.mojo"
```

Look for `comptime bfloat16_dtype = DType.bfloat16` (or equivalent). If the alias still
points to the fallback (e.g., `DType.float16`), the feature has NOT shipped — do not remove comments.

### 2. Search exhaustively for all stale references

Use multiple grep patterns to find every affected location:

```bash
# Pattern 1: Explicit alias notes
grep -rn "aliases to.*until.*supports\|until.*supports.*alias" . --include="*.mojo"

# Pattern 2: "when available" future-tense comments
grep -rn "Will use.*when available\|when.*is available" . --include="*.mojo"

# Pattern 3: Currently-uses fallback docstrings
grep -rn "Currently uses.*as.*not.*supported\|not natively supported" . --include="*.mojo"

# Pattern 4: Commented-out test blocks with TODO
grep -rn "TODO.*Uncomment when\|pass.*Placeholder.*not yet supported" . --include="*.mojo"
```

Typical affected file types:
- Core dtype/config modules (`dtype_utils.mojo`, `precision_config.mojo`)
- Integration tests (`test_multi_precision_training.mojo`)
- Unit test utilities (`test_special_values.mojo`)

### 3. Apply the fixes

For each location:

**Case A — Alias NOTE comment above return statement**: Delete the comment line entirely.

```mojo
# Before
# NOTE: bfloat16_dtype aliases to float16_dtype until Mojo supports BF16
return PrecisionConfig(...)

# After
return PrecisionConfig(...)
```

**Case B — "Will use X when available" inline comment**: Remove the comment, keep the code as-is
(if the code still uses the fallback for other reasons like hardware compatibility, that's correct
and the comment becomes misleading):

```mojo
# Before
return DType.float16  # Will use bfloat16_dtype when available

# After
return DType.float16
```

**Case C — Docstring "Currently uses Y as X not natively supported"**: Replace with accurate text
describing current behavior. Include any real limitations (e.g., Apple Silicon):

```mojo
# Before
Note:
    Currently uses FP16 as BF16 is not natively supported in Mojo v0.26.1.
    When Mojo adds native BF16 support, this will automatically use it.

# After
Note:
    Uses native DType.bfloat16 via bfloat16_dtype in dtype_utils.mojo.
    Not supported on Apple Silicon hardware (use FP16 instead).
```

**Case D — Disabled test with `pass` placeholder**: Enable the test by uncommenting the
assertions and removing the long TODO docstring:

```mojo
# Before
fn test_dtypes_bfloat16() raises:
    """Test special values work with bfloat16.

    NOTE: BF16 is a custom type... not yet integrated...
    TODO(#3015): Enable BF16 DType support testing
    ...
    """
    # TODO(#3015): Uncomment when Mojo adds DType.bfloat16
    # var tensor = create_special_value_tensor([2, 2], DType.bfloat16, 1.0)
    # assert_dtype(tensor, DType.bfloat16, "Should be bfloat16")
    pass  # Placeholder - BFloat16 DType not yet supported

# After
fn test_dtypes_bfloat16() raises:
    """Test special values work with bfloat16.

    Uses native DType.bfloat16 available in current Mojo.

    Note:
        DType.bfloat16 is not supported on Apple Silicon hardware.
    """
    var tensor = create_special_value_tensor([2, 2], DType.bfloat16, 1.0)
    assert_dtype(tensor, DType.bfloat16, "Should be bfloat16")
    verify_special_value_invariants(tensor, 1.0)
```

### 4. Verify no stale references remain

```bash
grep -rn "aliases to.*until\|Will use.*when available\|not natively supported\|BFloat16 DType not yet\|Uncomment when Mojo adds" . --include="*.mojo"
# Should return: No matches found
```

### 5. Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks must pass. Common hooks that run on `.mojo` files: `mojo format`, `trailing-whitespace`,
`end-of-file-fixer`.

### 6. Commit and create PR

```bash
git add <affected files>
git commit -m "cleanup(<scope>): remove stale <feature> alias/placeholder comments

<Feature> is now natively supported. Remove outdated comments
claiming it was aliased or unsupported, and enable the previously
disabled test.

- <file1>: <what was changed>
- <file2>: <what was changed>

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "cleanup(<scope>): ..." --body "Closes #<number>" --label "cleanup"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `mojo build` locally | Tried to verify no syntax errors with `pixi run mojo build` | GLIBC version mismatch on host (needs 2.32/2.33/2.34, host has older version) | Mojo compilation only works in Docker CI on this host. Pre-commit hooks suffice for local validation. |
| Searching only `precision_config.mojo` | Initial grep focused on the file named in the issue | Missed 3 other files with stale comments (`dtype_utils.mojo`, 2 test files) | Always grep the entire repo with multiple patterns, not just the issue-cited file. |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Files changed | `shared/training/precision_config.mojo`, `shared/training/dtype_utils.mojo`, `tests/shared/testing/test_special_values.mojo`, `tests/shared/integration/test_multi_precision_training.mojo` |
| Lines removed | 37 lines of stale comments/placeholder code |
| Lines added | 12 lines of accurate documentation |
| Pre-commit hooks | All passed |
| PR | https://github.com/HomericIntelligence/ProjectOdyssey/pull/3197 |
| Issue | #3088 (part of #3059 cleanup epic) |
| Branch | `3088-auto-impl` |
| Commit message convention | `cleanup(<scope>): ...` |

## Key Insights

1. **Issue-cited file is rarely the only affected file**: The issue pointed to `precision_config.mojo:225`
   but 3 other files also had stale references. Always search the whole repo.

2. **"Will use X when available" comments are different from "X aliases to Y"**: The former
   are in code that still correctly uses the fallback (for reasons unrelated to feature support),
   while the latter are explicit workaround markers. Both need removal when the feature ships,
   but the code behavior may not need to change.

3. **Disabled tests with `pass` are the most valuable part**: Re-enabling test coverage is the
   actual quality improvement. The comment removal is cosmetic; the test enablement validates behavior.

4. **Verify native support before removing**: `comptime bfloat16_dtype = DType.bfloat16` in
   `dtype_utils.mojo` confirmed BF16 was already native. If it had been `DType.float16`, removal
   would have been wrong.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3088, cleanup epic #3059 | [notes.md](../references/notes.md) |
