---
name: placeholder-test-staleness-annotations
description: 'Upgrade pass-only placeholder tests with TODO annotations, cross-issue
  references, and concrete test specs. Use when: placeholder tests contain only `pass`,
  are blocked on an unimplemented dependency, or need to be made grep-discoverable.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Prevent placeholder tests from going silently stale |
| **Language** | Mojo (applies to any language) |
| **Trigger** | Issue tracking stale/pass-only placeholder tests |
| **Output** | Annotated tests with `# TODO(#N)`, cross-issue docstrings, and concrete test specs |

## When to Use

- Placeholder tests contain only `pass` and a vague `NOTE(#N)` comment in the docstring
- A separate tracking issue (e.g. #4127) was filed to prevent the placeholder from becoming stale
- The blocking dependency (e.g. `from_array()` in #3013) is not yet implemented
- You want `grep -r 'TODO(#3013)'` to surface all tests waiting on a dependency

## Verified Workflow

### Quick Reference

```
1. grep for placeholder tests (fn test_foo.*raises)
2. For each: add # TODO(#<dep-issue>) above pass
3. Update docstring: reference both dep issue and tracking issue
4. Add concrete test spec (array values, expected shapes/dtypes)
5. Commit with docs(tests): prefix
```

### Step 1 — Locate placeholders

```bash
grep -rn "pass$" tests/ --include="*.mojo"
# Also search for vague NOTE comments
grep -rn "NOTE(#" tests/ --include="*.mojo"
```

### Step 2 — Identify both issues

Every placeholder upgrade involves two issues:

- **Dependency issue** (`#3013`): the feature being waited on (`from_array()`)
- **Tracking issue** (`#4127`): filed to avoid indefinite staleness

Read both with:

```bash
gh issue view 3013
gh issue view 4127
```

### Step 3 — Upgrade the docstring

Replace vague `NOTE(#N)` comments with structured docstrings:

**Before:**

```mojo
fn test_from_array_1d() raises:
    """Test creating tensor from 1D array.

    NOTE(#3013): from_array() is not yet implemented. This test is a
    placeholder for array-to-tensor conversion. Current workaround
    is to use arange(), zeros(), or manual element initialization.
    """
    pass
```

**After:**

```mojo
fn test_from_array_1d() raises:
    """Test creating tensor from 1D array.

    Blocked on #3013 (from_array() not yet implemented).
    Tracked by #4127 to prevent this placeholder from going stale.
    Once #3013 merges, implement using a 3-element Float32 array:
      [0.5, 1.0, 1.5] -> shape [3], dtype float32.
    """
    # TODO(#3013): implement when from_array() ships
    pass
```

### Step 4 — Choose test spec values

Use the project's standard FP-representable special values for specs:

| Values | Rationale |
| -------- | ----------- |
| `0.0, 0.5, 1.0, 1.5, -0.5, -1.0` | Tier 1 layerwise test values (exactly representable in FP32) |

For multi-dimensional tests, scale up:

- 1D: `[0.5, 1.0, 1.5]` → shape `[3]`
- 2D: `[[0.5, 1.0, 1.5], [-0.5, -1.0, 0.0]]` → shape `[2, 3]`
- 3D: 2×2×3 array → shape `[2, 2, 3]`

### Step 5 — Commit

Use the `docs(tests):` conventional commit prefix (not `fix:` or `feat:` — no behavior changes):

```bash
git commit -m "docs(tests): upgrade from_array() placeholder tests with TODO annotations"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Implement the actual test | Write real assertions without `from_array()` existing | `from_array()` is not in the codebase yet; compilation would fail | Don't implement until the dependency ships; annotation is the right deliverable |
| Remove the placeholder entirely | Delete the `pass`-only test functions | Loses intent and spec — future implementor has no guidance | Keep placeholders; they document what must be tested |
| Use `NOTE(#N)` prose only | Leave as vague comment in docstring | Not grep-discoverable; Claude would generate the same vague comment again | `# TODO(#N)` above `pass` is machine-readable and survives issue searches |
| Combine dep and tracking issue refs | Only reference `#3013` | The tracking issue (#4127) context lost — why was this annotated now? | Always reference both: the blocker and the staleness-tracker |

## Results & Parameters

### Commit message template

```text
docs(tests): upgrade <feature> placeholder tests with TODO annotations

Add # TODO(#<dep>) comments and detailed implementation specs to all
<N> <feature> placeholder tests, preventing silent staleness. Updated
docstrings reference both the blocking dependency (#<dep>) and tracking
issue (#<tracker>) with concrete test specs (array values, expected shapes).

Closes #<tracker>
```

### PR description template

```markdown
## Summary

- Add `# TODO(#<dep>)` comments above each `pass` statement
- Update docstrings to reference both the blocking dependency (#<dep>) and tracking issue (#<tracker>)
- Include concrete test specs (array values, expected shapes) so implementors know exactly what to write when #<dep> ships

## Files Modified

- `tests/.../test_foo_part2.mojo` — `test_feature_1d`
- `tests/.../test_foo_part3.mojo` — `test_feature_2d`, `test_feature_3d`

## Verification

- Pre-commit hooks pass
- No regressions (placeholder tests unchanged functionally — still `pass`)

Closes #<tracker>
```
