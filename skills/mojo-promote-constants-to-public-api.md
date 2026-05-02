---
name: mojo-promote-constants-to-public-api
description: 'Promote module-scoped Mojo constants to the package public API via __init__.mojo
  re-exports. Use when: (1) constants are alias/comptime in one module but needed
  across test files, (2) an issue asks to export constants from the public API, (3)
  callers must import the entire module just to access one constant.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Mojo: Promote Constants to Public API

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-07 |
| **Objective** | Move module-local `alias`/`comptime` constants to `tolerance_constants.mojo` and re-export via `__init__.mojo` so any test file can import them without pulling in the whole source module |
| **Outcome** | `GRADIENT_CHECK_EPSILON_FLOAT32` and `GRADIENT_CHECK_EPSILON_OTHER` exported from `shared.testing`; source module (`layer_testers.mojo`) imports from canonical location; PR #3721 created |
| **Related Issues** | ProjectOdyssey #3209 (export constants), #3090 (document magic numbers), #2704 (precision analysis) |

## When to Use

- A constant is defined as a local `alias` or `comptime` in module `X` but is needed by modules that shouldn't depend on `X`
- Issue title contains "export from public API", "make importable", "single canonical import"
- Multiple test files copy-paste the same value or define their own epsilon/tolerance
- `from shared.<subpackage>.<heavy-module> import CONSTANT` is the only way to get the value

## Verified Workflow

### Step 1: Identify the canonical constants home

In ProjectOdyssey the right file is `shared/testing/tolerance_constants.mojo`. Look for an
existing file that holds all tolerance/epsilon values for the package.

```bash
# Find the constants home
grep -r "comptime\|alias.*Float64\|alias.*Float32" shared/testing/ --include="*.mojo" -l
```

### Step 2: Add `comptime` constants to the canonical file

Use `comptime` (not `alias`) to match the existing style in `tolerance_constants.mojo`:

```mojo
# Float32-specific epsilon (3e-4): avoids precision loss in matmul (see issue #2704).
# Using 1e-5 causes ~56% precision loss; 3e-4 gives <1.5% gradient error.
comptime GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4

# Epsilon for non-float32 dtypes (BF16, FP16) in gradient checking.
comptime GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3
```

Update the module docstring's `Constants:` section to list the new entries.

### Step 3: Re-export from `__init__.mojo`

Add the new names to the existing `from shared.testing.tolerance_constants import (...)` block:

```mojo
from shared.testing.tolerance_constants import (
    TOLERANCE_DEFAULT,
    ...
    GRADIENT_CHECK_EPSILON,
    GRADIENT_CHECK_EPSILON_FLOAT32,   # ← new
    GRADIENT_CHECK_EPSILON_OTHER,     # ← new
    TOLERANCE_CONV,
    ...
)
```

### Step 4: Replace local definitions in the source module

The source module (`layer_testers.mojo`) previously had `alias` definitions. Replace them with
an import:

```mojo
# Before (remove these lines)
alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4
alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3

# After (add import alongside existing imports)
from shared.testing.tolerance_constants import (
    GRADIENT_CHECK_EPSILON_FLOAT32,
    GRADIENT_CHECK_EPSILON_OTHER,
)
```

The constants at usage sites don't need to change — the names are the same.

### Step 5: Write a test file

Create `tests/shared/testing/test_<constant-group>_constants.mojo`:

```mojo
from testing import assert_true
from shared.testing import (
    GRADIENT_CHECK_EPSILON_FLOAT32,
    GRADIENT_CHECK_EPSILON_OTHER,
)
from shared.testing.tolerance_constants import (
    GRADIENT_CHECK_EPSILON_FLOAT32 as EPSILON_FLOAT32_DIRECT,
    GRADIENT_CHECK_EPSILON_OTHER as EPSILON_OTHER_DIRECT,
)

fn test_float32_value() raises:
    assert_true(GRADIENT_CHECK_EPSILON_FLOAT32 == 3e-4, "should be 3e-4")

fn test_package_equals_submodule() raises:
    assert_true(GRADIENT_CHECK_EPSILON_FLOAT32 == EPSILON_FLOAT32_DIRECT,
                "package and submodule must be identical")

fn main() raises:
    test_float32_value()
    test_package_equals_submodule()
    print("All tests passed!")
```

Six useful test functions to include:

1. Numeric value correct (`== 3e-4`)
2. Companion value correct (`== 1e-3`)
3. Package import == submodule import (for both constants)
4. `EPSILON_FLOAT32 > GRADIENT_CHECK_EPSILON` (larger than generic)
5. `EPSILON_OTHER > EPSILON_FLOAT32` (ordering)

### Step 6: Run pre-commit and commit

```bash
pixi run pre-commit run --all-files

git add shared/testing/tolerance_constants.mojo \
        shared/testing/__init__.mojo \
        shared/testing/layer_testers.mojo \
        tests/shared/testing/test_gradient_epsilon_constants.mojo

git commit -m "$(cat <<'EOF'
feat(shared/testing): export GRADIENT_CHECK_EPSILON_FLOAT32 from public API

Add GRADIENT_CHECK_EPSILON_FLOAT32 (3e-4) and GRADIENT_CHECK_EPSILON_OTHER
(1e-3) as comptime constants in tolerance_constants.mojo, re-export them
from shared/testing/__init__.mojo, and replace the local alias definitions
in layer_testers.mojo with imports from the canonical source.

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

git push -u origin <branch>
gh pr create --title "feat(shared/testing): export GRADIENT_CHECK_EPSILON_FLOAT32 from public API" \
  --body "Closes #<issue>" --label "implementation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Keeping `alias` keyword in `tolerance_constants.mojo` | Used `alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4` to match `layer_testers.mojo` style | `tolerance_constants.mojo` uses `comptime` for all existing constants; mixing styles is inconsistent | Check the existing style in the target file before adding constants; use `comptime` in tolerance files |
| Checking if Mojo test runner works locally | Ran `pixi run mojo test` | GLIBC version mismatch on host (requires GLIBC_2.32+, host has older version) | Can't run Mojo tests directly on this host; rely on pre-commit hooks and CI for validation |

## Results & Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Source of truth file | `shared/testing/tolerance_constants.mojo` | All `comptime` tolerance/epsilon values live here |
| Keyword | `comptime` | Matches existing style in `tolerance_constants.mojo` (not `alias`) |
| `__init__.mojo` pattern | Add to existing `from shared.testing.tolerance_constants import (...)` block | No new `from` statement needed |
| Test import alias pattern | `from shared.testing.tolerance_constants import X as X_DIRECT` | Allows asserting package == submodule in same test |
| Commit type | `feat(shared/testing):` | Functional change — new public API surface |
| Pre-commit validation | `pixi run pre-commit run --all-files` | All 14 hooks passed including `Validate Test Coverage` |
| Files changed | 4 | `tolerance_constants.mojo`, `__init__.mojo`, `layer_testers.mojo`, new test file |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3209, PR #3721 | Branch `3209-auto-impl`; all pre-commit hooks passed |
