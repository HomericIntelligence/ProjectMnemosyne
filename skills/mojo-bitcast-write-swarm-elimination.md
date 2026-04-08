---
name: mojo-bitcast-write-swarm-elimination
description: "Systematically find and eliminate all tensor._data.bitcast[T]()[i] = val UAF write patterns across a Mojo codebase using parallel agent swarm. Use when: (1) widespread bitcast write patterns need replacing codebase-wide, (2) grep finds >50 files with the pattern, (3) each file can be fixed independently with same safe API replacement."
category: debugging
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: []
---

# Skill: Mojo Bitcast Write Swarm Elimination

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Systematically eliminate all `tensor._data.bitcast[T]()[i] = val` UAF write patterns codebase-wide using a parallel agent swarm |
| **Outcome** | 1,062 writes fixed across 50 files in ~2 hours via 5 parallel agents (PRs #5200–#5204) |
| **Context** | ProjectOdyssey Mojo ML platform; unsafe bitcast writes are a UAF hazard under ASAP destruction |
| **Issues** | Identified after PR #5197 root-cause analysis |
| **PRs** | #5200, #5201, #5202, #5203, #5204 (batches 1–5) |

## When to Use

- `grep -rn "\._data\.bitcast\[.*\]()\[.*\] *=" . --include="*.mojo"` returns results across many files (>50 files)
- A codebase-wide safe replacement API (`AnyTensor.set()`) is already available
- Each file can be fixed independently — no cross-file coordination required
- You need the work completed quickly via parallelism rather than sequentially

## Why Bitcast Writes Are Unsafe

`tensor._data.bitcast[T]()[i] = val` is an unsafe pattern in Mojo because:

1. `_data.bitcast[T]()` returns a new `UnsafePointer[T]` — a temporary value
2. Mojo's ASAP (As Soon As Possible) destruction may free the underlying buffer before the write completes
3. This is a use-after-free (UAF): you write through a pointer to already-freed memory
4. Crashes manifest as `libKGENCompilerRTShared.so` segfaults after allocation churn

The variant `tensor._data.bitcast[T]()[] = val` (no index, dereference at offset 0) has the same UAF risk.

## Why `AnyTensor.store()` Is Safe

The internal `store()` method in `any_tensor.mojo`:

```mojo
fn store[dtype: DType](self, index: Int, value: Scalar[dtype])
```

Uses `read` convention for `self` — the tensor stays alive through the entire call under Mojo's borrow semantics. The `bitcast` inside `store()` is safe because it operates on a live reference, not a temporary derived from ASAP-eligible value.

## Discovery: Finding All Instances

```bash
# Find all bitcast write patterns (indexed form)
grep -rn "\._data\.bitcast\[.*\]()\[.*\] *=" . --include="*.mojo"

# Find variant: empty-index dereference write
grep -rn "\._data\.bitcast\[.*\]()[] *=" . --include="*.mojo"

# Combined count
grep -rc "\._data\.bitcast\[.*\]()" . --include="*.mojo" | grep -v ":0" | sort -t: -k2 -rn
```

In ProjectOdyssey this found **1,062 instances across 50 files** including `DISABLED_*.mojo` files
(fix those too — they may be re-enabled later).

## Safe Replacement API

Replace `tensor._data.bitcast[T]()[i] = val` with:

```mojo
tensor.set(i, T(val))
```

`AnyTensor.set()` signature:

```mojo
fn set[dtype: DType](mut self, index: Int, value: Scalar[dtype]) raises
```

Supported types: `Float32`, `Float64`, `Float16`, `Int32`, `Int64`, `Int8`, `UInt8`, `UInt16`, `UInt32`, `UInt64`.

### Signature cascade requirements

The `mut self` and `raises` on `set()` propagate outward. Any helper function that calls `set()` must also declare:

```mojo
# BEFORE
fn fill_tensor(tensor: AnyTensor):

# AFTER
fn fill_tensor(mut tensor: AnyTensor) raises:
```

And calling functions must also add `raises` if they don't already have it.

### Avoid double-wrapping

When the expression is already the target type, don't wrap again:

```mojo
# WRONG — double-wrap
tensor.set(i, Float32(Float32(x)))

# CORRECT
tensor.set(i, Float32(x))

# CORRECT — already Float32, no wrapping needed
tensor.set(i, val)  # when val: Float32
```

Use Python regex (not sed) for batch replacements to handle complex sub-expressions correctly.

## Verified Workflow

### 1. Partition files into non-overlapping batches

```bash
# Get file list sorted by line count (descending — spread large files evenly)
grep -rl "\._data\.bitcast\[.*\]()" . --include="*.mojo" | \
  xargs wc -l 2>/dev/null | sort -rn | grep -v total > /tmp/bitcast_files.txt

# Split into N batches (e.g. 5 agents)
# Assign files round-robin by line count so each batch has similar total work
```

Critical constraint: **no file appears in more than one batch**. Overlapping file assignments
cause merge conflicts and negate parallelism benefits.

### 2. Each agent workflow

For each batch (agent 1–5 in parallel):

```bash
# 1. Create isolated worktree
git worktree add worktrees/fix-bitcast-batch-N -b fix/bitcast-writes-batch-N

# 2. Apply replacements via Python script (see below)
python3 scripts/fix_bitcast_writes.py --files batch_N_files.txt

# 3. Verify: no bitcast writes remain in assigned files
grep -n "\._data\.bitcast\[.*\]()\[.*\] *=" <assigned-files>

# 4. Add mut/raises to helper functions as needed (manual review)

# 5. Run pre-commit on changed files
pixi run pre-commit run --files <changed-files>

# 6. Commit and push
git commit -m "fix(tensor): replace bitcast writes with safe set() in batch N"
git push -u origin fix/bitcast-writes-batch-N

# 7. Create PR with auto-merge
gh pr create --title "fix(tensor): eliminate bitcast UAF writes batch N/5" \
  --body "Replaces tensor._data.bitcast[T]()[i]=val with tensor.set(i,T(val)).
Batch N of 5: <list files>
Closes #ISSUE"
gh pr merge --auto --rebase
```

### 3. Python regex replacement script

```python
#!/usr/bin/env python3
"""Replace tensor._data.bitcast[T]()[i] = val with tensor.set(i, T(val))."""
import re
import sys
from pathlib import Path

# Pattern: tensor._data.bitcast[SomeType]()[expr] = rhs
BITCAST_INDEXED = re.compile(
    r'(\w+)\._data\.bitcast\[(\w+)\]\(\)\[([^\]]+)\]\s*=\s*(.+)'
)

def fix_line(line: str) -> str:
    m = BITCAST_INDEXED.match(line.strip())
    if not m:
        return line
    tensor, typ, idx, rhs = m.groups()
    rhs = rhs.rstrip()
    # Avoid double-wrapping if rhs already starts with typ(
    if rhs.startswith(f"{typ}(") and rhs.endswith(")"):
        wrapped = rhs
    else:
        wrapped = f"{typ}({rhs})"
    indent = len(line) - len(line.lstrip())
    return " " * indent + f"{tensor}.set({idx}, {wrapped})\n"

for path in sys.argv[1:]:
    p = Path(path)
    lines = p.read_text().splitlines(keepends=True)
    new_lines = [fix_line(l) for l in lines]
    p.write_text("".join(new_lines))
    print(f"Fixed: {path}")
```

### 4. Merge order

PRs can merge in any order — they operate on non-overlapping files, so rebase conflicts
are impossible. Enable auto-merge on all 5 simultaneously.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files affected | ~50 `.mojo` files (including `DISABLED_*.mojo`) |
| Total instances | ~1,062 writes |
| Agents / PRs | 5 parallel |
| Time to complete | ~2 hours |
| Verification | `verified-precommit` (pre-commit passes; CI pending) |
| Grep pattern | `\._data\.bitcast\[.*\]()\[.*\] *=` |
| Safe replacement | `tensor.set(i, T(val))` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Manual file-by-file sed | Used `sed -i` to replace patterns one file at a time | Too slow at scale (50 files, 1,062 writes); `sed` misses complex multiline expressions and nested parentheses | Use Python regex for batch replacement with type-wrapping awareness; avoids double-wrap bugs |
| Single large PR with all files | All 1,062 fixes in one branch and one PR | Creates merge conflicts between agents working in parallel; one huge diff is hard to review; CI takes longer on massive changesets | One PR per batch with non-overlapping file assignments enables true parallelism and reviewable diffs |

## Results & Verification

```bash
# After all PRs merge — confirm no bitcast writes remain
grep -rn "\._data\.bitcast\[.*\]()\[.*\] *=" . --include="*.mojo"
# Expected: no output

# Confirm set() is used everywhere
grep -rc "\.set(" . --include="*.mojo" | grep -v ":0" | wc -l
```

## Related Skills

- `mojo-bitcast-uaf-blog-and-ci-fix` — root-cause investigation, UAF crash formula,
  blog PR workflow for the original discovery session
- `hephaestus:myrmidon-swarm` — general pattern for dispatching parallel agent batches
