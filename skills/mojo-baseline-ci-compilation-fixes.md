---
name: mojo-baseline-ci-compilation-fixes
description: 'Fix baseline Mojo compilation errors on main that block all open PRs.
  Use when: CI test groups fail with errors inherited from main branch (unused variable
  --Werror, full() type mismatch, alias deprecation, missing re-exports).'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Baseline compilation errors on `main` propagate to all open PRs, causing CI failures in multiple test groups |
| **Context** | Mojo `--Werror` treats warnings as errors; `full()` only accepts `Float64` for fill_value; `alias` keyword deprecated in favor of `comptime` |
| **Outcome** | 4 files changed, 12 insertions/deletions; all pre-commit hooks passed; PR created with auto-merge enabled |
| **Scope** | ProjectOdyssey (Mojo ML research platform) |

## When to Use

- Multiple open PRs show CI failures in Benchmarks, Core Utilities, or Integration Tests groups
- Errors are **identical across PRs** — indicating a `main` baseline problem, not PR-specific issues
- Mojo `--Werror` flags an unused variable that was assigned but its value never read
- `full()` receives integer types where `Float64` is required by the function signature
- `alias` keyword deprecation warning promoted to error
- `from shared import X` fails because the re-export was commented out in `__init__.mojo`

## Verified Workflow

### Quick Reference

```bash
# 1. Identify baseline errors (look for same error across many PRs)
gh pr list --limit 30 --json number,statusCheckRollup

# 2. Branch from main
git checkout -b fix-baseline-ci-errors

# 3. Apply fixes (see patterns below)

# 4. Stage and run pre-commit
git add <files>
just pre-commit

# 5. Commit, push, create PR with auto-merge
git commit -m "fix(ci): resolve baseline compilation errors"
git push -u origin fix-baseline-ci-errors
gh pr create --title "..." --body "..."
gh pr merge --auto --rebase <PR-number>
```

### Step 1 — Diagnose: baseline vs. PR-specific errors

Check if the same compilation error appears on unrelated PRs. If yes, fix on `main` via a dedicated PR.

Key indicators of a **baseline** error:

- Same error message across 5+ PRs with unrelated code changes
- Error is in a file not touched by any of those PRs
- CI test group failure (e.g., "Benchmarks", "Core Utilities") affects all PRs uniformly

### Step 2 — Find the unstaged changes situation

If `git pull --rebase` fails due to unstaged changes from a previous session:

```bash
git stash
git checkout -b fix-baseline-ci-errors
# Apply stash back only if the changes are relevant
```

### Step 3 — Apply the four common Mojo baseline fixes

#### Fix A: Unused variable (`--Werror`)

```mojo
# Before (causes error: assignment was never used)
var throughput = Float64(n_params * n_iters) / (Float64(total_ns) / 1e9)

# After
_ = Float64(n_params * n_iters) / (Float64(total_ns) / 1e9)
```

**When there are multiple identical lines**: provide surrounding context in the Edit call to uniquely
identify the instance to fix. Check with `grep -n` first.

#### Fix B: `full()` type mismatch

```mojo
# Before (error: cannot convert from 'Int8' to 'Float64')
var t = full([3], Int8(5), DType.int8)
var t = full([3], UInt8(255), DType.uint8)

# After (wrap with Float64 — safe for __str__ formatting tests)
var t = full([3], Float64(5), DType.int8)
var t = full([3], Float64(255), DType.uint8)
```

Apply to all integer variants: `Int8`, `Int16`, `Int32`, `Int64`, `UInt8`, `UInt16`, `UInt32`, `UInt64`.

#### Fix C: Deprecated `alias` keyword

```mojo
# Before (deprecated)
alias ToTensor = ToExTensor

# After
comptime ToTensor = ToExTensor
```

#### Fix D: Missing re-export (commented-out import)

```mojo
# Before (commented out — causes ImportError in test)
# from .data.transforms import Normalize, ToTensor, Compose

# After (uncomment)
from .data.transforms import Normalize, ToTensor, Compose
```

### Step 4 — Stage files and run pre-commit

Pre-commit **skips Mojo files if they are not staged**. Always stage before running:

```bash
git add tests/shared/benchmarks/bench_optimizers.mojo \
        tests/shared/core/test_extensor_int_str.mojo \
        shared/data/__init__.mojo \
        shared/__init__.mojo
just pre-commit
```

### Step 5 — Commit message format

```
fix(ci): resolve <N> baseline compilation errors causing CI test failures

Fix unused variable warning, full() type mismatch, and alias deprecation
that caused <TestGroupA>, <TestGroupB>, and <TestGroupC> groups to fail
on main, blocking all <N> open PRs from inheriting clean CI baselines.

Changes:
- <file>:<line> — <what changed and why>
- ...
```

### Step 6 — PR with auto-merge

```bash
gh pr merge --auto --rebase <PR-number>
```

Verify auto-merge is enabled:

```bash
gh pr view <PR-number> --json autoMergeRequest
# Should show: {"mergeMethod":"REBASE","enabledAt":"..."}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit with duplicate context | Used `old_string` matching a line that appeared twice in the file (`var throughput = Float64(...)`) | Edit tool returned "Found 2 matches, replace_all is false" error | Always `grep -n` first to check for duplicate lines; use more surrounding context to make the match unique |
| `git pull --rebase` on main | Tried to pull main before branching, while there were unstaged modifications to workflow files | Git rejected with "cannot pull with rebase: You have unstaged changes" | Use `git stash` before pulling/branching when there are unstaged changes from a previous session |
| Running `just pre-commit` without staging | Ran hooks before `git add` — all Mojo hooks reported "no files to check, Skipped" | Pre-commit only runs on staged files by default | Always `git add` the target files before running `just pre-commit` |

## Results & Parameters

### Session outcome

- **Branch**: `fix-baseline-ci-errors`
- **PR**: #4846 on `HomericIntelligence/ProjectOdyssey`
- **Files changed**: 4
- **Lines changed**: 12 insertions, 12 deletions
- **Pre-commit**: All hooks passed (Mojo Format, type-check, trailing-whitespace, end-of-file-fixer)
- **Auto-merge**: Enabled (rebase strategy)

### Test groups fixed

| Test Group | Root Cause | Fix Applied |
| ------------ | ----------- | ------------- |
| Benchmarks | `var throughput` unused (`--Werror`) | Changed to `_ = ...` |
| Core Utilities | `full()` received integer types, requires `Float64` | Wrapped 9 call sites with `Float64()` |
| Integration Tests | `alias` deprecation + missing `Normalize/ToTensor/Compose` re-export | `alias` → `comptime`, uncommented import |

### Edit tool tip: handling duplicate lines

When the same line appears multiple times in a file, provide enough surrounding context:

```python
# Instead of:
old_string = "    var throughput = Float64(n_params * n_iters) / (Float64(total_ns) / 1e9)"

# Use:
old_string = """    var avg_time_ms = Float64(total_ns) / Float64(n_iters) / 1_000_000.0
    var throughput = Float64(n_params * n_iters) / (Float64(total_ns) / 1e9)

    # Estimated SIMD speedup"""
```
