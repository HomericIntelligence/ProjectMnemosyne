---
name: mojo-writable-write-to-migration
description: "Migrate Mojo structs from __str__/Stringable to write_to/Writable for Mojo 0.26.3+ conformance.
  Use when: (1) auditing a codebase for deprecated Stringable/\\_\\_str\\_\\_ patterns in Mojo 0.26.3+,
  (2) a struct declares Writable in its trait list but implements \\_\\_str\\_\\_ instead of write_to,
  (3) migrating from Stringable to Writable with optional transitional delegation for backward compatibility."
category: architecture
date: 2026-04-10
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [mojo, writable, stringable, write_to, __str__, trait, migration, modernization]
---

# Skill: Mojo `Writable` / `write_to` Migration from `__str__`

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Objective** | Modernize Mojo structs from deprecated `Stringable`/`__str__` pattern to `Writable`/`write_to` for Mojo 0.26.3+ conformance |
| **Outcome** | Successful — 5 structs across 3 files modernized; codebase reached ~98% Writable conformance |
| **Verification** | verified-precommit (pre-commit hooks passed; CI validation pending on PR #5212) |

## When to Use

- Auditing a Mojo 0.26.3+ codebase for deprecated `Stringable`/`__str__` patterns
- A struct declares `Writable` in its trait list but implements `__str__` instead of `write_to`
- Migrating a struct from `Stringable` to `Writable` (full migration or transitional delegation)
- Codebase audit reveals structs that are almost modernized but still use the old `__str__` API
- `__str__` formatting logic is complex and you want to avoid duplication during a phased migration

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end in CI. Pre-commit hooks (format/lint) passed.
> CI validation is pending on PR #5212. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Step 1: Find all __str__ implementations in Mojo source
grep -rn "__str__" shared/ --include="*.mojo"

# Step 2: Find all structs that declare Writable trait
grep -rn "Writable" shared/ --include="*.mojo" -l

# Step 3: Find structs that declare Writable but still implement __str__ (need migration)
# Cross-reference: files in both result sets still using __str__ without write_to
grep -rn "def __str__" shared/ --include="*.mojo" | grep -v "write_to"

# Step 4: Verify no remaining __str__ implementations after migration
grep -rn "def __str__" shared/ --include="*.mojo"
```

### Detailed Steps

1. **Audit the codebase** — Run the Quick Reference grep commands to identify structs
   that declare `Writable` but implement `__str__` instead of `write_to`.

2. **Classify each struct** — Decide between full migration and transitional delegation:
   - **Full migration**: Use when `__str__` is not called elsewhere and the formatting
     logic can be cleanly expressed with `writer.write(...)`.
   - **Transitional delegation**: Use when `__str__` is called by other code, or the
     formatting logic is complex and you want to avoid duplicating it.

3. **Apply the full migration pattern** (preferred):

   ```mojo
   # Before (Mojo <=0.26.0):
   struct MyStruct(Stringable):
       var value: Int

       def __str__(self) -> String:
           return "MyStruct(" + str(self.value) + ")"
   ```

   ```mojo
   # After (Mojo 0.26.3+):
   struct MyStruct(Writable):
       var value: Int

       def write_to(self, mut writer: Some[Writer]):
           writer.write("MyStruct(", self.value, ")")
   ```

4. **Apply the transitional delegation pattern** (when `__str__` still needed):

   ```mojo
   # Both traits declared; write_to delegates to __str__ to avoid duplication
   struct MyStruct(Writable, Stringable):
       var value: Int

       def write_to(self, mut writer: Some[Writer]):
           writer.write(str(self))  # delegate to __str__ during transition

       def __str__(self) -> String:
           return "MyStruct(" + str(self.value) + ")"
   ```

   This is the pattern used for `BenchmarkResult` in
   `shared/benchmarking/result.mojo` — `write_to` delegates to `str(self)`
   to avoid duplicating complex formatting logic during the transition.

5. **Handle the "already declared Writable but missing write_to" case** — Some
   structs may already have `Writable` in their trait list but are missing the
   `write_to` method entirely. Simply add the `write_to` method:

   ```mojo
   # Struct already declares Writable but is missing write_to:
   struct MXFP4(Writable):
       var bits: UInt8

       # Add this:
       def write_to(self, mut writer: Some[Writer]):
           writer.write("MXFP4(bits=", self.bits, ")")
   ```

6. **Remove `Stringable` from trait list** if the struct no longer needs `__str__`
   for external callers.

7. **Run pre-commit hooks** to verify format/lint checks pass:

   ```bash
   just pre-commit-all
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| None | This is a straightforward mechanical migration | N/A | The pattern is consistent across all structs |

## Results & Parameters

### Two Migration Patterns

**Pattern 1 — Full Migration** (preferred when `__str__` is not needed elsewhere):

```mojo
# Remove Stringable, add Writable; replace __str__ with write_to
struct MyStruct(Writable):
    def write_to(self, mut writer: Some[Writer]):
        writer.write("MyStruct(", self.value, ")")
```

**Pattern 2 — Transitional Delegation** (use when __str__ still called by other code):

```mojo
# Keep both traits; write_to delegates to __str__ to avoid duplication
struct MyStruct(Writable, Stringable):
    def write_to(self, mut writer: Some[Writer]):
        writer.write(str(self))

    def __str__(self) -> String:
        return "MyStruct(" + str(self.value) + ")"
```

### Audit Commands

```bash
# Find all remaining __str__ implementations
grep -rn "def __str__" shared/ --include="*.mojo"

# Find all files declaring Writable
grep -rn "Writable" shared/ --include="*.mojo" -l

# Find structs that declare Writable but use __str__ without write_to
# (cross-reference both result sets manually or with:)
grep -rn "Writable" shared/ --include="*.mojo" -l | \
  xargs grep -l "def __str__" | \
  xargs grep -rn "def write_to" --include="*.mojo" -L
```

### Files Modernized (ProjectOdyssey PR #5212)

| File | Struct(s) | Pattern Used |
|------|-----------|--------------|
| `shared/benchmarking/result.mojo` | `BenchmarkResult` | Transitional delegation (`write_to` → `str(self)`) |
| `shared/core/types/mxfp4.mojo` | `MXFP4`, `MXFP4Block` | Full migration (added `write_to`; already had `Writable` declared) |
| `shared/core/types/nvfp4.mojo` | `NVFP4`, `NVFP4Block` | Full migration (added `write_to`; already had `Writable` declared) |

### When to Choose Each Pattern

| Condition | Pattern |
|-----------|---------|
| `__str__` is only used for string representation | Full migration |
| `__str__` is called by other code (e.g., logging, display) | Transitional delegation |
| Formatting logic is simple (one or two fields) | Full migration |
| Formatting logic is complex / multi-line | Transitional delegation (avoids duplication) |
| Codebase is in the middle of a phased migration | Transitional delegation |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5212, branch `fix/ci-stability-and-quality`, Mojo 0.26.3 | 5 structs in 3 files modernized; pre-commit hooks passed |
