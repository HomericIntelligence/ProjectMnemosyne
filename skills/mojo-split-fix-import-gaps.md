---
name: mojo-split-fix-import-gaps
description: 'Fix missing imports when splitting Mojo test files. Use when: (1) splitting
  a test file and symbols are used without explicit top-level imports, (2) auditing
  split part files for import completeness before committing.'
category: ci-cd
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Original Mojo test files sometimes use symbols (e.g. `randn`) without a top-level import — Mojo resolves them through transitive or inline imports and the file compiles fine. When split, each part file needs its own complete import block, exposing the gap. |
| **Solution** | Grep the original file for all symbol usages, cross-reference against the top-level imports, and add any missing symbols to the import line before creating the split files. |
| **Related** | `mojo-test-file-split` skill (ADR-009 splitting workflow) |
| **Discovery** | Found during `test_mobilenetv1_e2e.mojo` split — `randn` used in 2 tests but not in the top-level `from shared.core.extensor import` line |

## When to Use

- Splitting any Mojo test file as part of the ADR-009 workflow
- Compiler errors in split part files about undefined symbols that work in the original
- Auditing an original test file before splitting to proactively catch import gaps

## Verified Workflow

### 1. Audit symbol usage vs. top-level imports

Before creating split files, grep all used symbols and compare against the import block:

```bash
# Find all top-level imports
grep "^from\|^import" tests/models/test_mobilenetv1_e2e.mojo

# Find symbols from a specific module that are actually used
grep -oE "\brandn\b|\bzeros\b|\bones\b|\bfull\b|\bExTensor\b" tests/models/test_mobilenetv1_e2e.mojo | sort -u
```

Cross-reference: if a symbol appears in usage but NOT in the `import` line, add it.

### 2. Common gap: extensor symbols

The `shared.core.extensor` module exports many symbols. Original files often import only
`zeros`, `ones`, `full` but also use `randn` inline:

```mojo
# Original (broken — randn silently available but not imported)
from shared.core.extensor import ExTensor, zeros, ones, full

# Fixed — add randn to import
from shared.core.extensor import ExTensor, zeros, ones, full, randn
```

### 3. Check for inline imports in function bodies

Some functions import inside the function body:

```mojo
fn test_mobilenetv1_backward_conv_only() raises:
    ...
    from shared.core.conv import conv2d_backward, depthwise_conv2d_backward
```

These inline imports are fine and should be copied verbatim into the part file that contains
that test function. Do NOT hoist them to the top level unless they are used by multiple tests
in the same part file.

### 4. Verify each part file compiles independently

After creating split files, check that each part file's imports are self-contained:

```bash
# Quick symbol check — all used names should appear in imports
grep -oE "\b[a-z_]+\b" tests/models/test_mobilenetv1_e2e_part1.mojo \
  | sort -u \
  | grep -v "^fn\|^var\|^let\|^for\|^if\|^return\|^raises\|^from\|^import"
```

For thorough validation, use `mojo build` on each split file.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Copy imports verbatim from original | Copied the original import line exactly into each part file | Original's `from shared.core.extensor import ExTensor, zeros, ones, full` was missing `randn` which was used in test functions | Always grep for actual symbol usage, not just copy the import line |
| Rely on Mojo to catch missing imports | Assumed Mojo would error if a symbol was undefined | Mojo v0.26.1 sometimes resolves symbols through transitive imports or JIT context — the original file "worked" with a missing import | Test files can have latent import bugs that only manifest when the file is isolated during a split |
| Trust the original file's imports as complete | Treated existing imports as the source of truth | Original file had `randn` called in 2 test functions (`test_mobilenetv1_forward_for_classification`, `test_mobilenetv1_training_step_simulation`) with no top-level import | Grep actual function bodies for symbols, then verify they appear in the import list |

## Results & Parameters

**File that triggered this finding**: `tests/models/test_mobilenetv1_e2e.mojo`

**Missing import**: `randn` from `shared.core.extensor`

**Grep to find the gap**:

```bash
# Find all symbols used from extensor
grep -oE "\b(ExTensor|zeros|ones|full|randn|empty|arange)\b" \
  tests/models/test_mobilenetv1_e2e.mojo | sort | uniq -c | sort -rn

# Check top-level import for extensor
grep "extensor" tests/models/test_mobilenetv1_e2e.mojo
```

**Fix applied**:

```mojo
# Before (in original and broken split files)
from shared.core.extensor import ExTensor, zeros, ones, full

# After (correct — added randn)
from shared.core.extensor import ExTensor, zeros, ones, full, randn
```

**Integration with mojo-test-file-split workflow**:

Add this as **Step 2.5** between "Plan the split" and "Create part files":

> 2.5. Audit imports — grep all symbol usages in the original file, compare to top-level
> imports, and add any missing symbols before creating part files.
