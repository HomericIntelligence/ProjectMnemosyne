---
name: fix-ci-compilation-and-lint
description: 'Fix CI failures from missing declarations and markdown lint errors.
  Use when: Mojo compilation fails with unknown declaration, or markdownlint blocks
  pre-commit.'
category: ci-cd
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
# Fix CI Compilation and Lint Errors

## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI blocked by Mojo compilation error + markdown lint failures |
| **Root Cause** | Function renamed without adding import/local definition; markdown formatting violations |
| **Fix Strategy** | Add local helper functions to avoid cross-module dependencies; fix markdown lint rules |
| **Verification** | `mojo package` compilation + `pre-commit run --all-files` |

## When to Use

- Mojo compilation fails with `use of unknown declaration '<function_name>'` after a refactor
- `markdownlint-cli2` reports MD051 (broken link fragments), MD037 (spaces in emphasis), MD031 (blank lines around code blocks), MD040 (missing language tags), or MD026 (trailing punctuation in headings)
- CI is blocked on both comprehensive tests (compilation) and pre-commit (lint)

## Verified Workflow

### Quick Reference

```bash
# Verify compilation fix
pixi run mojo package -I . shared -o /tmp/shared.mojopkg

# Verify lint fixes on specific files
SKIP=mojo-format pixi run pre-commit run --files <file1> <file2>

# Full pre-commit validation
SKIP=mojo-format pixi run pre-commit run --all-files
```

### Step 1: Fix Mojo Compilation Errors

When a function reference is broken after renaming:

1. **Find the pattern** in a sibling module that already has a local copy:

   ```bash
   grep -rn '_dtype_to_string' shared/core/
   ```

2. **Add a local private function** rather than importing from another module — this avoids creating wrong-direction dependencies (e.g., `core` should not depend on `utils`):

   ```mojo
   fn _dtype_to_string(dtype: DType) -> String:
       if dtype == DType.float32:
           return "float32"
       # ... etc
       else:
           return "unknown"
   ```

3. **Update the call site** to use the local function name (prefixed with `_`).

### Step 2: Fix Deprecated Mojo Syntax

| Deprecation | Old | New |
|-------------|-----|-----|
| Pointer offset | `ptr.offset(n)` | `ptr + n` |
| Type alias | `alias X = Y` | `comptime X = Y` |
| Docstring format | Missing period in Returns | Add `.` at end |

### Step 3: Fix Markdown Lint Errors

| Rule | Issue | Fix |
|------|-------|-----|
| MD051 | Link fragment points to non-existent heading | Remove link or fix anchor |
| MD037 | Spaces inside emphasis markers (`* text*`) | Escape asterisks with `\*` if used as math operators |
| MD031 | Missing blank line before/after code block | Add blank line between closing ``` and `---` |
| MD040 | Fenced code block without language | Add `text`, `bash`, `yaml`, etc. |
| MD026 | Trailing punctuation in heading | Remove colon from heading text |
| MD013 | Line exceeds 120 characters | Break line at natural boundary |

### Step 4: Verify

1. Run `mojo package` to confirm compilation passes (warnings OK, errors not)
2. Run pre-commit on changed files first (fast feedback)
3. Run pre-commit on all files (full validation)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix MD051 by changing `#pre-commit` to `#pre-commit-1` | Assumed GitHub auto-dedup suffix for duplicate anchors | The heading wasn't duplicated — `#pre-commit` was the correct anchor | Always check actual heading count before guessing dedup suffixes |
| Fix MD037 by removing spaces around `*` | Changed `grad_output * alpha` to `grad_output *alpha` | This created emphasis markers wrapping `alpha, ...` | Use `\*` to escape asterisks used as math multiplication operators |

## Results & Parameters

### Environment

- **Mojo version**: 0.26.1 (pinned in pixi.toml)
- **markdownlint-cli2**: v0.12.1 (markdownlint v0.33.0)
- **Pre-commit**: Configured in `.pre-commit-config.yaml`

### Key Architectural Decision

When a function exists in `shared/utils/` but is needed in `shared/core/`, create a local private copy prefixed with `_` rather than importing. The `core` module is foundational — it should not depend on higher-level modules like `utils`.

### Files Modified

| File | Changes |
|------|---------|
| `shared/core/extensor.mojo` | Added `_dtype_to_string()`, fixed `.offset()` → `+`, fixed docstring |
| `shared/__init__.mojo` | `alias` → `comptime` |
| `.github/workflows/README.md` | Removed 3 broken link fragments |
| `docs/dev/backward-pass-catalog.md` | Fixed line lengths, escaped `*` operators |
| `scripts/README.md` | Added language tags, blank lines, fixed heading punctuation |
