---
name: mojo-note-to-docstring
description: 'Convert inline NOTE comments describing implementation constraints to
  proper docstring Note sections in Mojo code. Use when: cleaning up legacy NOTE comments,
  doing a documentation pass, or preparing code for public API docs.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Objective** | Convert `# NOTE:` inline comments to proper docstring `Note:` sections |
| **Language** | Mojo (.mojo files) |
| **Scope** | Implementation constraint comments that describe design decisions |
| **Trigger** | GitHub cleanup issues requesting NOTE → docstring conversion |

## When to Use

- A cleanup issue asks to convert `# NOTE:` comments to docstrings
- Code review flags inline NOTE comments that should be in the public API docs
- Preparing a module for documentation generation
- Reducing comment noise while preserving constraint knowledge

## Verified Workflow

### Step 1: Discover all NOTE comments

```bash
grep -rn "# NOTE:" --include="*.mojo" .
```

This gives a complete list of files and line numbers to review.

### Step 2: Categorize each NOTE

Classify each NOTE into one of these types:

| Type | Action |
|------|--------|
| Implementation constraint (design decision) | Add to function/struct docstring `Note:` section |
| Redundant (already covered by docstring) | Remove inline NOTE entirely |
| Module-level constraint (no function context) | Reword as plain comment, remove `NOTE:` prefix |
| Test-specific / skip explanation | Leave as-is (not an API constraint) |
| Large block comment (detailed rationale) | Summarize in docstring, remove block |

### Step 3: Apply transformations

**Pattern A — Redundant NOTE (docstring already covers it):**

```mojo
# Before
fn bf16(...) -> PrecisionConfig:
    """...
    Note:
        Currently uses FP16 as BF16 is not natively supported.
    """
    # NOTE: bfloat16_dtype aliases to float16_dtype until Mojo supports BF16
    return PrecisionConfig(...)

# After — just remove the inline NOTE
fn bf16(...) -> PrecisionConfig:
    """...
    Note:
        Currently uses FP16 as BF16 is not natively supported.
    """
    return PrecisionConfig(...)
```

**Pattern B — NOTE with no existing docstring Note section:**

```mojo
# Before
fn remove_safely(filepath: String) -> Bool:
    """Remove file safely.

    Args:
        filepath: File to remove.

    Returns:
        True if removed, False if error.
    """
    # NOTE: Mojo v0.26.1 doesn't have os.remove() or file system operations
    if not file_exists(filepath):
        return False

# After — add Note section, remove inline NOTE
fn remove_safely(filepath: String) -> Bool:
    """Remove file safely.

    Args:
        filepath: File to remove.

    Returns:
        True if removed, False if error.

    Note:
        Mojo v0.26.1 does not have os.remove() or file system delete operations.
        This is a placeholder that simulates successful removal.
    """
    if not file_exists(filepath):
        return False
```

**Pattern C — Large block NOTE comment:**

```mojo
# Before (lines 283-304 of mixed_precision.mojo)
if params.dtype() == DType.float16:
    # NOTE: FP16 SIMD vectorization is blocked by Mojo compiler limitation.
    # Mojo does not support SIMD load/store operations for FP16 types.
    # [... 20 more lines of explanation ...]
    var src_ptr = params._data.bitcast[Float16]()

# After — summarize in function docstring, condense inline comment
# (docstring gets the Note: section, inline becomes one-liner)
if params.dtype() == DType.float16:
    # FP16 SIMD blocked, see docstring Note
    var src_ptr = params._data.bitcast[Float16]()
```

**Pattern D — Struct-level NOTE between methods:**

```mojo
# Before — NOTE floating between __init__ and __next__
fn __init__(...): ...

# NOTE: We intentionally do not implement __iter__() because List[Int] fields
# are not Copyable, and __iter__ would need to return Self which requires copying.

fn __next__(...): ...

# After — move to struct docstring
struct BroadcastIterator:
    """Iterator for efficiently iterating over broadcast tensor elements.

    Note:
        __iter__() is intentionally not implemented because List[Int] fields
        are not Copyable. Use __next__ directly with a while loop instead.
    """
    fn __init__(...): ...
    fn __next__(...): ...
```

**Pattern E — Module-level NOTE (no function context):**

```mojo
# Before
# NOTE: Callbacks must be imported directly from submodules due to Mojo limitations:

# After — rephrase without NOTE: prefix
# Mojo limitation: callbacks must be imported directly from submodules:
```

### Step 4: Verify no # NOTE: remain in target files

```bash
grep -rn "# NOTE:" --include="*.mojo" shared/ tests/shared/
```

Only notes in test skip contexts or examples should remain.

### Step 5: Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass. Mojo format may be skipped with GLIBC warnings on older Linux — this is expected.

## Results & Parameters

**Session: Issue #3072 (ProjectOdyssey)**

- 12 `# NOTE:` implementation constraints converted across 10 files
- 5 NOTEs removed (redundant — already in docstring)
- 4 NOTEs moved to function/struct docstrings as `Note:` sections
- 3 NOTEs reformatted (prefix removed, integrated into surrounding comments)
- Pre-commit hooks: all passed (exit 0)

**Files modified:**

```text
shared/core/broadcasting.mojo       — NOTE → struct docstring Note:
shared/core/loss.mojo               — NOTE removed (redundant)
shared/testing/layer_testers.mojo   — 3x NOTE prefix removed
shared/training/__init__.mojo       — NOTE → plain comment + condensed inline
shared/training/loops/training_loop.mojo  — NOTE → function docstring Note:
shared/training/mixed_precision.mojo — large block NOTE → docstring + 1-liner
shared/training/precision_config.mojo — NOTE removed (redundant)
shared/training/trainer_interface.mojo — NOTE → function docstring Note:
shared/utils/config.mojo            — NOTE removed (redundant)
shared/utils/file_io.mojo           — NOTE → function docstring Note:
```

**Commit message pattern:**

```
cleanup(docs): convert implementation constraint NOTEs to docstrings
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Convert ALL NOTE comments | Initially considered converting every `# NOTE:` in the repo | Test files have NOTE-style skip explanations that don't belong in docstrings | Filter by context: only convert NOTEs in production code that describe API constraints |
| Remove NOTE block wholesale | Considered deleting the large FP16 SIMD block comment entirely | Would lose important performance rationale for future developers | Summarize key points in docstring Note:, condense inline to 1-liner |
| Add Note: to every function | Considered adding Note: to all functions touched | Would bloat docstrings unnecessarily | Only add Note: when the constraint is something callers need to know |
| Convert module-level NOTEs to docstrings | Module-level comments aren't in functions/structs | Mojo doesn't have module-level docstrings the same way | Rephrase as plain comment, remove NOTE: prefix |
