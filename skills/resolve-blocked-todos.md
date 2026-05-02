---
name: resolve-blocked-todos
description: 'Resolve TODO markers blocked by a now-closed issue. Use when: (1) a
  tracking issue has TODO(#N) markers and issue #N is now closed, (2) disabled tests
  have TODO comments waiting on a dependency, (3) cleanup issues need to be resolved
  after a blocking PR merges.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
| ---------- | ------- |
| **Category** | testing |
| **Trigger** | Blocking issue closed; TODO(#N) markers remain in code |
| **Outcome** | All TODO markers removed, disabled tests enabled, functionality implemented |
| **Scope** | Test files, assertion helpers, implementation files |

## When to Use

- A tracking issue documents `TODO(#N)` or `TODO: ... #N` markers waiting on another issue
- `gh issue view N --json state -q '.state'` returns `"CLOSED"` for the blocking issue
- Tests are commented out with TODO markers and the dependency is now resolved
- You need to resolve accumulated technical debt after a blocking PR merges

## Verified Workflow

### Phase A: Verify blocking issue is closed

```bash
gh issue view <BLOCKING_ISSUE_NUMBER> --json state -q '.state'
# Must return "CLOSED" before proceeding
```

If still `"OPEN"`: post an audit comment to the tracking issue and stop. Do not implement.

### Phase B: Locate all TODO markers

```bash
grep -rn "TODO.*#<N>\|TODO(#<N>)" --include="*.mojo" .
# Verify count matches the tracking issue table
```

### Phase C: Check if implementation exists elsewhere

Before writing new code, check if a feature branch already has the implementation:

```bash
git branch --all | grep "<issue-number>"
git log --oneline --all | grep "<issue-number>"
```

If an implementation branch exists, cherry-pick rather than re-implementing:

```bash
git log --oneline <branch-name> --not main | head -5
# Find the implementation commit hash
git cherry-pick <commit-hash> --no-commit
git status  # Verify only expected files changed
```

### Phase D: Add missing helpers

For each TODO that referenced a missing assertion/helper function, add it following the existing pattern:

```mojo
fn assert_contiguous(tensor: ExTensor, message: String = "") raises:
    """Assert tensor has contiguous memory layout."""
    if not tensor.is_contiguous():
        var error_msg = message if message else "Tensor should be contiguous"
        raise Error(error_msg)
```

Export from conftest if tests need it:

```mojo
# In tests/shared/conftest.mojo
from shared.testing.assertions import (
    ...,
    assert_contiguous,  # Add here
)
```

### Phase E: Enable disabled tests

For each commented-out test block, uncomment and update:

1. Remove `# TODO(#N): ...` comment
2. Uncomment the actual test code
3. Replace `pass  # Placeholder` with real assertions
4. Add imports for any newly-available functions (`transpose`, `contiguous`, etc.)

Example transformation:

```mojo
# BEFORE
fn test_is_contiguous_true() raises:
    var t = ones(shape, DType.float32)
    # TODO(#2722): assert_contiguous(t)
    var _ = t.is_contiguous()
    pass  # Placeholder

# AFTER
fn test_is_contiguous_true() raises:
    var t = ones(shape, DType.float32)
    assert_contiguous(t, "Newly created tensor should be contiguous")
```

### Phase F: Update tracking comments

For any TODO comments that can't be fully resolved (e.g., view semantics deferred):

```mojo
# BEFORE
# Should be 1D view of same data (currently copies, TODO(#2722): implement views)

# AFTER
# Currently returns a 1D copy (view semantics deferred to future work)
```

### Phase G: Verify no TODO markers remain

```bash
grep -rn "TODO.*#<N>" --include="*.mojo" .
# Expected: no output
```

### Phase H: Run pre-commit and commit

```bash
pixi run pre-commit run --all-files
git add <changed-files>
git commit -m "cleanup(tests): resolve TODOs blocked by #<N> ..."
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<tracking-issue>"
gh pr merge --auto --rebase
```

## Key Patterns

### Checking if implementation commit already exists

When a blocking issue has been closed via a PR that hasn't merged to main yet:

```bash
# Find branch
git branch --all | grep "<issue-number>"

# Find what the implementation commit changed
git show <commit-hash> -- shared/core/extensor.mojo | grep "^+fn " | head -20

# Cherry-pick just the implementation (without committing)
git cherry-pick <commit-hash> --no-commit
```

This avoids re-implementing what was already written.

### Enabling __str__, __repr__, __hash__ tests

When these string/hash methods are newly available:

```mojo
# Minimal test - just verify non-empty
var s = String(t)
assert_true(len(s) > 0, "String representation should be non-empty")

var r = repr(t)
assert_true(len(r) > 0, "Repr should be non-empty")

# Hash consistency test
var hash_a = hash(a)
var hash_b = hash(b)
assert_equal_int(hash_a, hash_b, "Equal tensors should have same hash")
```

### Adding module-level function imports in test files

```mojo
# At top of test file, add specific import
from shared.core.matrix import transpose
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Check if blocking issue is open before acting | Assumed blocking issue #2722 was still open because the tracking issue said to wait | Issue had been closed (merged) since the tracking issue was created | Always verify `gh issue view N --json state` first - don't trust the tracking issue description |
| Wait for methods to appear in main | Expected `__str__`, `__repr__`, `__hash__` to be in the current main branch after #2722 closed | The implementation PR existed on a feature branch (`2722-auto-impl`) not yet merged to main | Check git branches and cherry-pick from the feature branch instead of waiting |
| Use `contiguous(b)` as a module-level function | Test code had `# var c = contiguous(b)` implying a module-level function | No module-level `contiguous()` exists; only `tensor.contiguous()` method and `as_contiguous()` function | Always verify function signatures with grep before enabling commented-out test code |

## Results & Parameters

### Typical file changes for a TODO(#N) resolution

```text
shared/core/extensor.mojo          - cherry-pick or add missing methods
shared/testing/assertions.mojo     - add assert_* helper functions
tests/shared/conftest.mojo         - export new assertions
tests/shared/core/test_utility.mojo - enable 5-7 disabled tests
tests/shared/core/test_shape.mojo  - update stale TODO comments
```

### Commit message format

```
cleanup(tests): resolve TODOs blocked by #<N> <brief description>

- Cherry-pick/implement: <list methods added>
- Add <helper function> to shared/testing/assertions.mojo
- Enable <N> previously-disabled tests: <list test names>
- Update stale TODO comments

Closes #<tracking-issue>
```
