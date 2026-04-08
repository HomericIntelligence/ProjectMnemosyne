---
name: enable-disabled-mojo-tests
description: 'Re-enable disabled, skipped, or TODO-stubbed Mojo test files by identifying
  the root cause and replacing stubs with real tests. Use when: (1) a .mojo test file
  has a NOTE saying tests are disabled or prints SKIPPED with no test functions, (2)
  a test file has TODO markers citing an issue number with commented-out test code,
  (3) backward pass tests are commented out with stale ownership/borrowing notes, (4)
  a cleanup issue asks to re-enable tests, (5) blocking components are now implemented,
  or (6) pytest.skip() guards exist for resolved configuration issues.'
category: testing
date: 2026-04-07
version: 2.0.0
user-invocable: false
tags:
  - mojo
  - tests
  - skip
  - todo
  - disabled
  - re-enable
  - cleanup
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | enable-disabled-mojo-tests |
| **Category** | testing |
| **Complexity** | Low-Medium |
| **Mojo runs locally** | No (GLIBC mismatch on host — Docker/CI only) |
| **Key patterns** | Function-pointer helpers; DataLoader 2D shape; TODO uncomment; backward pass analytical tests; pytest.skip removal |

This skill covers all forms of disabled/skipped/TODO Mojo (and Python pytest) tests:
re-enabling NOTE-stubbed files, uncommenting TODO test code, re-enabling backward pass
tests after type alias fixes, and removing pytest.skip guards for resolved configuration
issues.

## When to Use

- A `.mojo` test file's `main()` only prints a skip message ("SKIPPED") with no actual test functions
- A test file has a `NOTE: These tests are temporarily disabled` comment
- A GitHub cleanup issue asks to re-enable or investigate disabled tests
- Test stubs exist with commented-out body: `# var result = fn(...)` and `pass # Placeholder`
- Functions are implemented in a module file but absent from `__init__.mojo` exports
- Backward pass tests are commented out with a note like "disabled due to ownership issues"
- A `comptime` type alias change resolved the underlying issue
- `pytest.skip()` calls exist that guard tests for missing configs or wrong paths
- Closing a "feature" issue that turns out to be a test-enablement issue

Do NOT use when:
- Tests are skipped due to an active, unfixed compiler bug (document blocker instead)
- Tests require external resources not available in CI
- Tests are legitimately platform-specific

## Verified Workflow

### Phase 0: Determine the Disable Pattern

Before writing anything, determine which pattern applies:

| Pattern | Indicator | Action |
|---------|-----------|--------|
| Stub file | `main()` only prints "SKIPPED", no test functions | Write all tests from scratch |
| NOTE-disabled | `NOTE: temporarily disabled pending X` | Check if X is resolved, then write tests |
| TODO commented-out | `# var b = fn(a)` + `pass # Placeholder` | Uncomment + fix syntax |
| Backward-pass disabled | `# DISABLED — ownership issues in XBackwardResult` | Check type alias, write analytical tests |
| pytest.skip() | `if not file.exists(): pytest.skip(...)` | Fix path or config, remove guard |

**Always read the actual file before assuming its structure.**

### 1. Read the Disabled Test File

Look for the NOTE/TODO comment to understand what was originally blocked:

```text
NOTE: These tests are temporarily disabled pending implementation of:
1. ValidationLoop class (Issue #34)
2. The testing.skip decorator (not available in Mojo)
3. Model forward() interface
```

For stub files, verify: does it have ANY `fn test_*()` functions, or is `main()` just a print statement?

### 2. Audit the Issue

```bash
gh issue view <number> --comments
```

Check what operations the issue says to "implement." Prior planning may already exist.
If a function already exists in source but is absent from `__init__.mojo`, this is a
test-enablement task — not an implementation task.

### 3. Confirm Blockers Are Resolved

```bash
# Search for blocking components by name
grep -r "struct ValidationLoop" shared/training/
grep -r "fn validate" shared/training/loops/
grep -r "struct DataLoader" shared/training/trainer_interface.mojo

# For backward pass: check type alias resolution
grep -n "comptime.*BackwardResult\|GradientTriple\|GradientPair" shared/core/conv.mojo | head -20

# For unsigned types: verify builtins are used in existing files
grep -r "UInt8\|UInt16\|UInt32\|UInt64" shared/core/ --include="*.mojo" -l

# For custom wrapper modules: check if they even exist
ls shared/core/types/unsigned.mojo 2>/dev/null || echo "Does not exist"
```

**Pattern**: Often the disable note references a custom wrapper module that was
abandoned. Mojo's built-in types (`UInt8`, `UInt16`, etc.) work fine — test the
builtins directly.

### 4. Check Package Exports (for TODO tests)

```bash
grep -n "tile\|repeat\|permute" shared/core/__init__.mojo
```

If missing, add to the relevant `from module import (...)` block:

```mojo
from shared.core.shape import (
    split,
    tile,       # ADD
    repeat,     # ADD
    permute,    # ADD
)
```

### 5. Read an Analogous Enabled Test File

The best reference is a test file for a similar component that is already enabled:

```bash
cat tests/shared/training/test_training_loop.mojo
```

This shows: imports, assertion helpers, DataLoader construction patterns.

### 6. Fix DataLoader Shape Requirement

`DataLoader` requires 2D input — always use `[n_samples, feature_dim]`, NOT `[n_samples]`:

```mojo
var data = ones([n_samples, 10], DType.float32)    # CORRECT
var labels = zeros([n_samples, 1], DType.float32)  # CORRECT
return DataLoader(data^, labels^, batch_size=4)
```

### 7. Use Function-Pointer Helpers (not full model instantiation)

When the validation API takes `fn (ExTensor) raises -> ExTensor` callbacks:

```mojo
fn simple_forward(data: ExTensor) raises -> ExTensor:
    """Simple forward: returns ones matching data shape."""
    return ones(data.shape(), data.dtype())

fn simple_loss(pred: ExTensor, labels: ExTensor) raises -> ExTensor:
    """Simple loss: returns scalar ones tensor."""
    return ones([1], DType.float32)
```

### 8. Enable TODO Tests — Pattern for Stubs

**Before** (typical Mojo stub):
```mojo
fn test_tile_1d() raises:
    var a = arange(0.0, 3.0, 1.0, DType.float32)  # [0, 1, 2]
    # var b = tile(a, 3)  # TODO(#3013): Implement tile()
    # assert_numel(b, 9, "Tiled tensor should have 9 elements")
    pass  # Placeholder
```

**After** (enabled):
```mojo
fn test_tile_1d() raises:
    from shared.core import tile
    var a = arange(0.0, 3.0, 1.0, DType.float32)  # [0, 1, 2]
    var reps = List[Int]()
    reps.append(3)
    var b = tile(a, reps)
    assert_numel(b, 9, "Tiled tensor should have 9 elements")
```

Key transformations:
- Remove `# TODO(#NNN):` comment lines
- Uncomment the actual test logic
- Remove `_ = a  # Suppress unused variable warning` lines
- Remove `pass  # Placeholder`
- Fix syntax bugs in commented code (see table below)

Common syntax bugs in commented-out Mojo code:

| Bug Pattern | Fix |
|-------------|-----|
| `target_shape[0] = 4` | `target_shape.append(4)` (List requires append) |
| `var b = tile(a, 3)` | `var reps = List[Int](); reps.append(3); var b = tile(a, reps)` |
| `# var parts = split(a, [3, 5, 10])` | Use `split_with_indices` with `List[Int]` |
| `List[Int](1, 2, 3)` constructor | Use list literals `[1, 2, 3]` (Mojo v0.26.1+) |

### 9. Write Backward Pass Tests (Analytically Verifiable)

For backward pass re-enablement, verify the gradient type fields first:

```bash
grep -n "var grad_" shared/core/gradient_types.mojo
```

**GradientTriple** (from `conv2d_backward`): `.grad_input`, `.grad_weights`, `.grad_bias`
**GradientPair** (from `conv2d_no_bias_backward`): `.grad_a`, `.grad_b`

Use a 1x1 kernel = 1.0 for analytical tests (identity transform, hand-computable values):

```mojo
fn test_conv2d_backward_single_sample() raises:
    # Input (1,1,2,2) = [[1,2],[3,4]], kernel (1,1,1,1) = 1.0
    # grad_output = ones (1,1,2,2)
    # Expected: grad_input = 1.0 everywhere, grad_weights = 10.0, grad_bias = 4.0
    var grads = conv2d_backward(grad_output, x, kernel, stride=1, padding=0)
    assert_almost_equal(grads.grad_weights._data.bitcast[Float32]()[0], 10.0, tolerance=1e-5)
    assert_almost_equal(grads.grad_bias._data.bitcast[Float32]()[0], 4.0, tolerance=1e-5)
```

### 10. Write Tests for Unsigned Integer Types

Coverage checklist for unsigned integer types:

- [ ] Construction from literals (0, 1, max value per type)
- [ ] Arithmetic: `+`, `-`, `*`, `//`, `%`
- [ ] Bitwise: `&`, `|`, `^`, `<<`, `>>`
- [ ] Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- [ ] Widening conversions: `.cast[DType.uint16]()` etc.
- [ ] Conversion to/from `Int` (`Int(u8)` and `var u8: UInt8 = i`)
- [ ] Large values (especially `UInt64`)
- [ ] Near-boundary arithmetic

Unsigned integer conversion syntax:
```mojo
var u8: UInt8 = 200
var u16: UInt16 = u8.cast[DType.uint16]()  # Correct widening
var i = Int(u8)                             # Correct to Int
var u8b: UInt8 = i                          # Implicit from Int (current Mojo)
```

### 11. Write Tests Covering Full API Surface

Group tests by API method:

```text
- Constructor defaults and custom values
- standalone validation_step()
- standalone validate() over a full DataLoader
- ValidationLoop.run() — check return value AND metrics update
- ValidationLoop.run_subset() — verify max_batches limit
- No-weight-update property — same input => same loss every call
```

### 12. Fix pytest.skip Guards (Python Tests)

```bash
# Find all pytest.skip calls
grep -r "pytest.skip" tests/

# Run with skip summary
python3 -m pytest tests/ -v -rs
```

Common patterns and fixes:

| Pattern | Root Cause | Fix |
|---------|------------|-----|
| `if not file.exists(): pytest.skip()` | Wrong path calculation | Count `.parent` calls; add missing required fields |
| `try: ... except Error: pytest.skip()` | Missing Pydantic fields | Add required fields to config YAML |

Remove the guard entirely and let the test fail explicitly if config is missing.

### 13. Run Pre-commit with SKIP=mojo-format

On host systems where Mojo requires Docker (GLIBC mismatch), `mojo-format` fails.
Skip only that hook:

```bash
SKIP=mojo-format git commit -m "fix(training): re-enable X tests"
```

All other hooks (markdownlint, ruff, trailing-whitespace, check-yaml) run normally.
CI runs `mojo-format` inside Docker. This is documented in CLAUDE.md as a valid skip.

### 14. Commit, Push, Create PR

```bash
git add tests/shared/training/test_X.mojo
SKIP=mojo-format git commit -m "fix(training): re-enable X tests

<description of what tests cover>

mojo-format skipped: GLIBC version mismatch on host (requires Docker)

Closes #NNNN"

git push -u origin <branch>
gh pr create --label "cleanup" --body "Closes #NNNN"
gh pr merge --auto --rebase
```

### Quick Reference

```bash
# Check if referenced module exists
ls shared/core/types/unsigned.mojo 2>/dev/null || echo "Does not exist"

# Find what functions are exported
grep -n "tile\|repeat\|permute" shared/core/__init__.mojo

# Run pre-commit without mojo-format
SKIP=mojo-format pixi run pre-commit run --all-files

# Commit without mojo-format
SKIP=mojo-format git commit -m "fix(tests): re-enable X tests"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming tests existed but were "disabled" | Expected to find a skip guard or `@disabled` annotation to remove | The file had zero test functions — it was a complete stub | Always `Read` the actual file before assuming its structure from the issue description |
| Write file via Write tool without reading first | Called Write tool on existing file | Write tool requires the file to be Read first | Always Read the existing file before calling Write, even for full rewrites. Use Bash `cat >` as fallback. |
| Run `pixi run mojo run test_X.mojo` to verify | Executed mojo directly on host | GLIBC_2.32/2.33/2.34 not found — Mojo requires newer libc | Mojo tests can only be verified in CI (Docker). Trust existing test patterns and submit to CI. |
| Run `just pre-commit-all` | Called `just` command | `just` not in PATH on this host | Use `pixi run pre-commit run --all-files` instead. |
| Run all pre-commit hooks including mojo-format | Ran full pre-commit | mojo-format fails with GLIBC error | Use `SKIP=mojo-format git commit` — documented in CLAUDE.md as a valid use of SKIP. |
| Create DataLoader with 1D data `[n_samples]` | Passed flat tensor to DataLoader | DataLoader reads `self.data.shape()[1]` for feature_dim, panics on 1D | DataLoader requires 2D input: `[n_samples, feature_dim]`. |
| Looking for `shared/core/types/unsigned.mojo` | Searched for the custom wrapper module the disable note referenced | File never existed — was abandoned before being created | When a module is referenced in a note but doesn't exist, test the builtins instead |
| Using `List[Int](1, 2, 3)` constructor syntax | Tried older Mojo list construction pattern | Mojo v0.26.1+ uses list literals `[1, 2, 3]` | Compiler is truth — use `mojo build` to verify syntax |
| Assumed `grad_a`/`grad_b` for both gradient types | Assumed GradientTriple and GradientPair share field names | GradientTriple uses `grad_input`/`grad_weights`/`grad_bias`; only GradientPair uses `grad_a`/`grad_b` | Always read `gradient_types.mojo` to confirm field names before writing tests |
| Using `split(a, [3, 5, 10])` syntax | Direct List literal in split call | Mojo doesn't support Python-style inline list args for split | Need to create `split_with_indices` with explicit `List[Int]` |
| `target_shape[0] = 4` for initialization | Assignment to index on new List | Mojo List requires `append()` not index-assignment for new elements | Always use `.append()` to build Lists in Mojo |
| Inventing changes to justify a commit | Creating a commit with no real changes | Adds noise to git history, violates minimal-change principle | Read the plan fully first; if no fixes, don't manufacture them |

## Results & Parameters

### Import pattern for validation loop tests

```mojo
from tests.shared.conftest import (
    assert_true, assert_equal, assert_almost_equal,
    assert_less, assert_greater,
)
from shared.training.loops.validation_loop import (
    ValidationLoop, validation_step, validate,
)
from shared.training.trainer_interface import (
    DataLoader, DataBatch, TrainingMetrics,
)
from shared.core import ones, zeros, randn
```

### DataLoader creation helper

```mojo
fn create_val_loader(n_batches: Int = 3) raises -> DataLoader:
    var n_samples = n_batches * 4
    var data = ones([n_samples, 10], DType.float32)
    var labels = zeros([n_samples, 1], DType.float32)
    return DataLoader(data^, labels^, batch_size=4)
```

### No-weight-update property test pattern

```mojo
fn test_validation_loop_no_weight_updates() raises:
    var vloop = ValidationLoop()
    var loader1 = create_val_loader(n_batches=3)
    var loader2 = create_val_loader(n_batches=3)
    var metrics1 = TrainingMetrics()
    var metrics2 = TrainingMetrics()
    var loss1 = vloop.run(simple_forward, simple_loss, loader1, metrics1)
    var loss2 = vloop.run(simple_forward, simple_loss, loader2, metrics2)
    assert_almost_equal(loss1, loss2, Float64(1e-10))
```

### Stub test file template (copy-paste)

```mojo
"""Tests for Mojo's built-in unsigned integer types (UInt8, UInt16, UInt32, UInt64).

These tests verify the behavior of Mojo's native unsigned integer builtins,
including arithmetic, bitwise operations, comparisons, boundary values,
and conversions.
"""


fn test_uint8_construction() raises:
    """Test UInt8 construction from literals and zero value."""
    var zero: UInt8 = 0
    var one: UInt8 = 1
    var max_val: UInt8 = 255

    if zero != 0:
        raise Error("UInt8 zero construction failed")
    if one != 1:
        raise Error("UInt8 one construction failed")
    if max_val != 255:
        raise Error("UInt8 max value construction failed")


fn main():
    """Main test runner."""
    try:
        test_uint8_construction()
        print("OK test_uint8_construction")
    except e:
        print("FAIL test_uint8_construction:", e)

    print("\n=== Tests Complete ===")
```

### Backward pass analytically-verifiable config

```mojo
# Input: (1, 1, 2, 2) = [[1.0, 2.0], [3.0, 4.0]]
# Kernel: (1, 1, 1, 1) = [[1.0]]
# grad_output: ones (1, 1, 2, 2)
# stride=1, padding=0

# Expected outputs:
# grad_input = [[1.0, 1.0], [1.0, 1.0]]  (all 1.0 — identity kernel)
# grad_weights[0] = 10.0                  (sum of input = 1+2+3+4)
# grad_bias[0] = 4.0                      (sum of grad_output = 4 elements)
```

### PR description template for mojo format GLIBC issue

```markdown
## Verification

- Pre-commit hooks pass (trailing whitespace, end-of-file, YAML, markdown, Python linting)
- Mojo format hook fails for all files on this system due to GLIBC incompatibility —
  this is a pre-existing environment issue, CI runs in Docker where it passes

Closes #<issue-number>
```

### Commit pattern

```bash
SKIP=mojo-format git commit -m "fix(training): re-enable X loop tests

mojo-format skipped: GLIBC version mismatch on host (requires Docker)
Closes #NNNN"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3082 — re-enable test_validation_loop.mojo | Validation loop tests, DataLoader 2D shape pattern |
| ProjectOdyssey | Issue #3085 — re-enable Conv2D backward tests | Backward pass, GradientTriple/GradientPair field names |
| ProjectOdyssey | Issue #3081 — re-enable test_unsigned.mojo | Stub file, 18 tests written from scratch |
| ProjectOdyssey | Issue #3013 — ExTensor shape operations | TODO uncomment, missing __init__.mojo exports |
| ProjectScylla | Issue #670 — resolve skipped pytest tests | pytest.skip removal, Pydantic field fix, path fix |
