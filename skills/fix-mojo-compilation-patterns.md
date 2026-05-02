---
name: fix-mojo-compilation-patterns
description: "Use when: (1) CI fails with Mojo import errors after module renames, (2) mojo-format pre-commit hook fails due to lines exceeding 88-char limit, (3) Mojo stable vs nightly version mismatch causes compilation failures or deprecation warnings, (4) Python module docstrings contain Mojo migration artifact fragments, (5) mypy fails on union syntax, (6) assert_equal fails to compile for DType comparisons"
category: debugging
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Fix Mojo Compilation Patterns

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-29 |
| Objective | Consolidated patterns for fixing Mojo compilation errors: import path changes, format line limits, nightly version mismatches, and migration artifact cleanup |
| Outcome | Merged from 4 skills covering CI compilation errors, format line length, migration artifacts, and nightly compatibility |
| Verification | unverified |

## When to Use

- CI fails with Mojo import errors (`activation_ops`, `batch_norm` not found) after module renames
- mypy fails on `X | Y` union syntax in Python scripts
- `assert_equal` fails to compile for `DType` comparisons in Mojo tests
- `pre-commit` CI check fails with `mojo-format` hook reformatting files
- `mojo` binary unavailable locally (GLIBC version mismatch: requires GLIBC_2.32/2.33/2.34)
- `print()` statements with string literals exceed 88-character line limit
- CI resolves a different Mojo version than local (e.g., stable 0.26.1 vs nightly 0.26.1.0.dev*)
- `mojo format` crashes on `comptime` keyword with `_python_symbols` error
- Deprecation warnings for `alias`, `owned`, `ptr.offset()` need bulk fixing
- A module docstring contains Mojo-related language ("which have no Mojo equivalents") or ends mid-sentence with a library list

## Verified Workflow

### Quick Reference

```bash
# Check Python type checking
pixi run mypy scripts/

# Verify Mojo compilation (not full test run)
pixi run mojo build <test_file>.mojo

# Check GLIBC compatibility before attempting local mojo run
pixi run mojo --version 2>&1 | grep -i glibc
# If "version GLIBC_2.3x not found" — use manual Edit approach or CI

# Get exact CI diff for mojo-format failures
gh run view <run-id> --log-failed 2>&1 | grep -A 100 "All changes made by hooks:"

# Find String[byte=] usages needing migration
grep -rn '\[byte\s*=' --include='*.mojo'

# Find alias deprecations
grep -rn '^\s*alias\b' --include='*.mojo'

# Verify zero errors/warnings after nightly fixes
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep "error:\|warning:"
```

### 1. Fix CI Compilation Errors (Import Paths and mypy)

When CI fails due to module renames or Python type errors:

| Error Type | Root Cause | Fix |
| ------------ | ----------- | ----- |
| mypy `X \| Y` unsupported | `python_version` in `mypy.ini` too low | Bump to match runtime (e.g., 3.12) |
| Mojo import not found | Module was renamed/moved | Check actual module path in `shared/` package `__init__.mojo` files |
| `assert_equal` won't compile | Type doesn't implement required trait | Use `assert_true(a == b, msg)` instead |

Common Mojo module renames:
- `activation_ops` → `activation`
- `batch_norm` → `normalization`

Check `__init__.mojo` re-exports to find where symbols live now. Test files often lag behind refactors.

```ini
# mypy.ini — before
python_version = 3.9

# mypy.ini — after
python_version = 3.12
```

```mojo
# DType assert fix
# Before (won't compile):
assert_equal(dtype, DType.float32)

# After:
assert_true(dtype == DType.float32, "dtype should be float32")
```

### 2. Fix mojo-format Line Length Failures

When mojo-format CI fails and mojo binary is unavailable locally:

1. **Get the exact CI diff** from the failed pre-commit run:
   ```bash
   gh run view <run-id> --log-failed 2>&1 | grep -A 50 "All changes made by hooks"
   ```

2. **Identify reformatted lines** — mojo format splits long print strings at ~88 chars using implicit string concatenation:
   ```mojo
   # Before (>88 chars — fails mojo format):
   print("STATUS: Backward pass is a documented placeholder (full implementation tracked in GitHub issue #3181)")

   # After (mojo format output):
   print(
       "STATUS: Backward pass is a documented placeholder (full"
       " implementation tracked in GitHub issue #3181)"
   )
   ```

3. **Apply changes manually using Edit tool** — match the CI diff exactly:
   - Wrap `print("...")` → `print(\n    "part1"\n    " part2"\n)`
   - Note the leading space on continuation strings (mojo formatter convention)

4. **Verify CI re-runs** cleanly:
   ```bash
   gh pr checks <pr-number>
   ```

**Mojo Format Line-Wrapping Rules**:

| Rule | Detail |
| ------ | -------- |
| Line limit | 88 characters |
| String splitting | Implicit concatenation with leading space on continuation |
| Wrap style | `print(\n    "first part"\n    " continuation"\n)` |
| Long args | Same rule applies to any function call argument, not just print |
| Indentation | Continuation strings indented 4 extra spaces from `print(` call |

### 3. Fix Mojo Nightly Compatibility Issues

When CI uses a different Mojo version than local and compilation fails:

**Fix `String[byte=]` removal (nightly breaking change)**:
```mojo
# Character comparison
# Before: if path[byte=i] == ".":
if chr(Int(path.as_bytes()[i])) == ".":

# Getting raw byte value for writing
# Before: self.write_byte(UInt8(ord(value[byte=i])))
self.write_byte(value.as_bytes()[i])

# String indexing for lookup tables
# Before: result += hex_chars[byte=high]
result += chr(Int(hex_chars.as_bytes()[high]))
```

**Fix `alias` -> `comptime` deprecation**:
```bash
grep -rn '^\s*alias\b' --include='*.mojo'
# Replace top-level: sed -i 's/^alias /comptime /g' <files>
```

**Fix other deprecation warnings**:

| Warning | Fix |
| --------- | ----- |
| `ptr.offset(n)` | `ptr + n` |
| `transfer ^ on owned value` | Remove the `^` |
| `owned` keyword | Replace with `var` in function params |
| `unused variable` | Assign to `_` instead |

**Fix `mojo format` hook crash on `comptime`** (modular/modular#6144):

The stable `mojo format` crashes on files with docstring + `comptime` or multiple `comptime` declarations. Update the format wrapper script to treat exit code 123 as a warning:

```bash
# In scripts/mojo-format-compat.sh:
if [ $exit_code -eq 123 ]; then
    parse_errors=$(echo "$output" | grep "^error: cannot format")
    if [ -n "$parse_errors" ]; then
        echo "WARNING: mojo format cannot parse some files:"
        echo "$parse_errors" | sed 's/^/  /'
    fi
    exit 0
fi
```

### 4. Fix Mojo Migration Artifact in Docstrings

When a module docstring contains Mojo migration fragments:

1. **Identify the artifact pattern**:
   - Sentences ending with "which have no Mojo equivalents"
   - Docstrings ending with a list of Python libraries (numpy, scipy, matplotlib)
   - Incomplete sentence structure in the first 6 lines

2. **Replace with clean, accurate docstring**:
   ```python
   # Before (artifact):
   """Analysis pipeline for experiment results.

   This module provides data loading, statistical analysis, figure generation,
   and table generation for the ProjectScylla experiment results using Python
   libraries (numpy, scipy, matplotlib, altair).
   """

   # After (clean):
   """Statistical analysis package for <project> experiment results.

   This module provides data loading, statistical analysis, figure generation,
   and table generation for evaluating agent performance.
   """
   ```

3. **Verify with pre-commit**:
   ```bash
   pre-commit run --files <path/to/__init__.py>
   ```

### 5. Always Use PR Workflow

Even for CI fix commits — never push directly to main.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run `pixi run mojo format` locally | Execute mojo formatter to auto-fix files | GLIBC_2.32/2.33/2.34 not found on host OS (Debian Buster, glibc 2.31) | Mojo requires newer GLIBC than some CI/dev hosts have |
| Run `just pre-commit-all` locally | Apply all pre-commit hooks including mojo-format | Same GLIBC incompatibility blocks mojo binary | Pre-commit hooks using mojo also fail on incompatible hosts |
| Skip and rely on CI to auto-fix | Let CI apply the format and commit back | CI does not commit back — it just fails | Must apply formatting fixes manually when mojo unavailable |
| Changing tolerance for assertion | Increasing tolerance to hide format-related test failures | Masked the real issue without validating correctness | Fix the root cause; don't paper over CI failures |
| Assuming prior docstring fix was complete | PR #1121 removed worst fragment but left a residual | Partial fixes leave artifacts that pass casual review | Always read the current file state — don't assume a prior fix was complete |

## Results & Parameters

### Mojo Format

```
Mojo format column limit: 88 characters
String splitting: implicit concatenation (adjacent string literals)
Continuation: leading space on continuation strings
```

### Nightly Compatibility Fix Counts (Example Session)

| Fix Type | Count |
| ---------- | ------- |
| `String[byte=]` replacements | ~14 across 5 files |
| `alias` -> `comptime` replacements | 55 across 8 files |
| `owned` -> `var` replacements | 9 across 2 files |
| Other warning fixes | 8 across 6 files |

### Mojo Format Bug Details (modular/modular#6144)

Two patterns trigger the stable `mojo format` crash:
1. **Docstring + comptime**: `'_python_symbols' object has no attribute 'comptime_assert_stmt'`
2. **Multiple comptime decls**: `Cannot parse` (formatter only handles one per scope)

### Docstring Smell Pattern

A module docstring that ends by listing implementation libraries (numpy, scipy, etc.) is almost certainly a migration note artifact. Prefer describing *what* the package does, not *how* it is implemented. If a docstring fix recurs across multiple audits, verify the fix was actually merged to `main`.
