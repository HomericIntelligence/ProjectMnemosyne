---
name: enable-disabled-mojo-tests
description: "Re-enable disabled Mojo test files by identifying resolved blockers and writing real tests. Use when: a test file has a NOTE stub saying tests are pending, the blocking components are now implemented, or a cleanup issue requires converting skip stubs to real test functions."
category: testing
date: 2026-03-04
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | enable-disabled-mojo-tests |
| **Category** | testing |
| **Complexity** | Low-Medium |
| **Mojo runs locally** | No (GLIBC mismatch on host — Docker/CI only) |
| **Key pattern** | Function-pointer helpers + DataLoader from trainer_interface |

This skill captures how to identify and re-enable Mojo test files that were
disabled with a NOTE stub (e.g. "tests temporarily disabled pending
implementation of X"). The pattern from Issue #3082 (re-enable
`test_validation_loop.mojo`) applies to any similar cleanup task.

## When to Use

- A Mojo test file's `main()` only prints a skip message and does nothing
- A GitHub cleanup issue says "re-enable tests in `test_X.mojo`"
- The blocking components (e.g. `ValidationLoop`, `DataLoader`) are now
  implemented and exported
- You need to write real test functions without running Mojo locally

## Verified Workflow

### 1. Read the disabled test file

Look for the NOTE comment to understand what was originally blocked:

```text
NOTE: These tests are temporarily disabled pending implementation of:
1. ValidationLoop class (Issue #34)
2. The testing.skip decorator (not available in Mojo)
3. Model forward() interface
```

### 2. Confirm blockers are resolved

Search for each blocking component:

```bash
grep -r "struct ValidationLoop" shared/training/
grep -r "fn validate" shared/training/loops/
grep -r "struct DataLoader" shared/training/trainer_interface.mojo
```

If found — the blocker is resolved. Note the exact module paths for imports.

### 3. Read an analogous enabled test file

The best reference is a test file that was recently enabled for a similar
component. For `test_validation_loop.mojo`, the reference was
`test_training_loop.mojo`:

```bash
cat tests/shared/training/test_training_loop.mojo
```

This shows you:
- Which imports to use (`conftest`, `shared.training`, `shared.core`)
- The assertion helpers available (`assert_true`, `assert_almost_equal`, etc.)
- How `DataLoader` is constructed (requires 2D data: `[n_samples, feature_dim]`)

### 4. Check DataLoader shape requirement

`DataLoader` (from `shared/training/trainer_interface.mojo`) requires 2D input:

```python
fn __init__(out self, var data: ExTensor, var labels: ExTensor, batch_size: Int):
    self.num_samples = self.data.shape()[0]  # shape()[1] = feature_dim
```

Always create test data as `[n_samples, feature_dim]`, NOT `[n_samples]`:

```mojo
var data = ones([n_samples, 10], DType.float32)   # CORRECT
var labels = zeros([n_samples, 1], DType.float32) # CORRECT
return DataLoader(data^, labels^, batch_size=4)
```

### 5. Use function-pointer helpers, not full model instantiation

When the validation API takes `fn (ExTensor) raises -> ExTensor` callbacks,
define simple helpers at module scope:

```mojo
fn simple_forward(data: ExTensor) raises -> ExTensor:
    """Simple forward: returns ones matching data shape."""
    return ones(data.shape(), data.dtype())

fn simple_loss(pred: ExTensor, labels: ExTensor) raises -> ExTensor:
    """Simple loss: returns scalar ones tensor."""
    return ones([1], DType.float32)
```

This avoids needing to instantiate `SimpleMLP`+`TrainingLoop` just to test
the validation path.

### 6. Write tests covering the full API surface

Group tests by API method:

```text
- Constructor defaults and custom values
- standalone validation_step()
- standalone validate() over a full DataLoader
- ValidationLoop.run() — check return value AND metrics update
- ValidationLoop.run_subset() — verify max_batches limit
- No-weight-update property — same input => same loss every call
```

### 7. Run pre-commit with SKIP=mojo-format

On host systems where Mojo requires Docker (GLIBC mismatch), the `mojo-format`
hook fails with `GLIBC_2.32` errors. Skip only that hook:

```bash
SKIP=mojo-format git commit -m "fix(training): re-enable X tests"
```

All other hooks (markdownlint, ruff, trailing-whitespace, check-yaml, etc.)
run normally. CI will run `mojo-format` inside Docker.

### 8. Commit, push, create PR with cleanup label

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Write file via Write tool without reading first | Called Write tool on existing file | Write tool requires the file to be Read first | Always Read the existing file before calling Write, even for full rewrites. Use Bash `cat >` as fallback. |
| Run `pixi run mojo run test_X.mojo` to verify | Executed mojo directly on host | GLIBC_2.32/2.33/2.34 not found — Mojo requires newer libc | Mojo tests can only be verified in CI (Docker). Trust existing test patterns and submit to CI. |
| Run `just pre-commit-all` | Called `just` command | `just` not in PATH on this host | Use `pixi run pre-commit run --all-files` instead. |
| Run all pre-commit hooks including mojo-format | Ran full pre-commit | mojo-format fails with GLIBC error | Use `SKIP=mojo-format git commit` — this is documented in CLAUDE.md as a valid use of SKIP. |
| Create DataLoader with 1D data `[n_samples]` | Passed flat tensor to DataLoader | DataLoader reads `self.data.shape()[1]` for feature_dim, panics on 1D | DataLoader requires 2D input: `[n_samples, feature_dim]`. |

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

### Commit with mojo-format skip

```bash
SKIP=mojo-format git commit -m "fix(training): re-enable X loop tests

mojo-format skipped: GLIBC version mismatch on host (requires Docker)
Closes #NNNN"
```
