---
name: audit-runtime-note-prints
description: 'Audit example scripts for ambiguous runtime NOTE/TODO/FIXME print statements
  and replace with plain status messages. Use when: following up after a partial fix
  of NOTE prints, auditing all examples/ scripts for misleading runtime output, or
  converting Note: prefixes to factual plain text.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Category** | documentation |
| **Trigger** | Follow-up audit after partial NOTE/TODO/FIXME print cleanup in examples/ |
| **Outcome** | Zero `print.*NOTE\|TODO\|FIXME` matches in examples/; all pre-commit hooks pass |
| **Files Touched** | examples/*/train.mojo, examples/*/infer.mojo, examples/*/inference.mojo |

## When to Use

- A previous issue (e.g., #3084) fixed NOTE prints in a subset of files but may have missed others
- You need to audit all `examples/*/train.mojo` and `examples/*/infer.mojo` for runtime NOTE/TODO/FIXME
- Runtime `print("Note: ...")` statements exist that could confuse users into thinking something is broken
- Cleanup issue asks to convert misleading NOTE-prefixed prints to plain factual messages

## Verified Workflow

1. **Read the issue plan** via `gh issue view <number> --comments` — the plan may already list all affected files
2. **Run the audit grep** to find all candidates:
   ```bash
   grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME' examples/
   # Also run case-insensitive to catch "Note:" variants:
   # Use Grep tool with -i flag on examples/ glob *.mojo
   ```
3. **Cross-check against the plan** — the issue plan may reference files already partially fixed. Read current file state before editing (the plan can be stale).
4. **For each match**, apply one of these patterns:
   - **Redundant with existing STATUS block**: remove the NOTE line(s) entirely
   - **Misleading "broken" implication**: reword to a plain factual statement (remove `Note:` prefix)
   - **Two-line Note + detail**: merge into single factual line
5. **Verify zero matches** after edits:
   ```
   Grep pattern: print.*NOTE|print.*TODO|print.*FIXME|print.*Note:
   path: examples/  glob: *.mojo  -i: true
   ```
6. **Run pre-commit**:
   ```bash
   pixi run pre-commit run --all-files
   ```
7. **Commit, push, create PR** linked to the issue with `Closes #<number>`

## Key Patterns

### Before (alarming)
```mojo
print("Note: Training requires batch_norm2d_backward implementation.")
print("See GAP_ANALYSIS.md for details.")
```

### After (factual)
```mojo
print("Training requires batch_norm2d_backward (see GAP_ANALYSIS.md).")
```

### Before (misleading prefix)
```mojo
print("\nNote: This implementation demonstrates the inference structure.")
```

### After (plain)
```mojo
print("\nThis implementation demonstrates the inference structure.")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting the issue plan line numbers | Used plan's line numbers directly to edit files | Files were partially fixed already; line numbers had shifted | Always read the actual file state before editing — issue plans can be stale |
| Case-sensitive grep only | Used `print.*NOTE` without `-i` flag | Missed `Note:` (mixed case) variants in inference.mojo files | Use case-insensitive grep (`-i`) or include `\| print.*Note:` in pattern |

## Results & Parameters

**Grep command (case-insensitive, catches all variants)**:
```
Pattern: print.*NOTE|print.*TODO|print.*FIXME|print.*Note:
Tool: Grep with -i: true, output_mode: content, glob: *.mojo
Path: examples/
```

**Files changed in issue #3194**:
- `examples/resnet18-cifar10/inference.mojo` — merged two-line Note into one factual statement
- `examples/lenet-emnist/inference.mojo` — removed `Note:` prefix
- `examples/alexnet-cifar10/train_new.mojo` — removed `Note:` prefixes (×2)

**Files already fixed (not touched)**:
- `examples/resnet18-cifar10/train.mojo` — already used `STATUS:` from #3084
- `examples/mobilenetv1-cifar10/train.mojo` — already used `STATUS:` from prior work
- `examples/googlenet-cifar10/train.mojo` — already used `STATUS:` from prior work

**Pre-commit command**:
```bash
pixi run pre-commit run --all-files
```
