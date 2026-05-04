---
name: mojo-lint-syntax
description: Validate Mojo syntax against current v0.26.1+ standards. Use to catch
  syntax errors before compilation.
category: optimization
date: '2026-05-03'
version: 1.1.0
mcp_fallback: none
verification: verified-local
history: mojo-lint-syntax.history
---
# Lint Mojo Syntax

## Overview

| Item | Details |
| ------ | --------- |
| Date | N/A |
| Objective | Validate Mojo code against v0.26.1+ syntax standards. - Writing new Mojo code before testing - Reviewing Mojo code for syntax issues |
| Outcome | Operational |

Validate Mojo code against v0.26.1+ syntax standards.

## When to Use

- Writing new Mojo code before testing
- Reviewing Mojo code for syntax issues
- Migrating code from older Mojo versions
- Checking for deprecated patterns
- Pre-commit validation of Mojo files

## Verified Workflow

### Quick Reference

```bash
# Validate single executable file (with main())
mojo build -I . file.mojo

# Build entire package (for library files)
mojo package shared

# Format code (fixes many syntax issues)
pixi run mojo format .

# Check for deprecated patterns
grep -r "inout self\|@value\|DynamicVector\|->" *.mojo | grep -v "result\|fn"
```

**IMPORTANT**: Library files with relative imports CANNOT be validated using `mojo build` - use `mojo package` instead.

## Common Syntax Issues

**Deprecated Patterns**:

- ❌ `inout self` → ✅ `out self` in `__init__`, ✅ `mut self` in methods
- ❌ `@value` → ✅ `@fieldwise_init` with trait list
- ❌ `DynamicVector` → ✅ `List`
- ❌ `-> (T1, T2)` → ✅ `-> Tuple[T1, T2]`

**Constructor Issues**:

- Wrong parameter type in `__init__` (must be `out self`)
- Missing trait conformances (`Copyable`, `Movable`)
- Incorrect initialization order
- ❌ `take`/`owned` argument modifiers in `def` functions — these are ONLY valid in `fn`
  - `def __init__(out self, *, take existing: Self)` is a parse error in Mojo 0.26.3
  - `mojo format` silently strips the space: `take existing` → `takeexisting` (now a single
    parameter name — compiles but does nothing useful, `existing` field is inaccessible)
  - Fix: delete the constructor if it has no callers (most common), or convert to
    `fn __init__(out self, owned existing: Self):` if genuinely needed
  - Detection:

    ```bash
    # Find "takeXxx" or "ownedXxx" — space was stripped by formatter
    grep -rn "\btake[A-Z]\|\bowned[A-Z]" examples/ shared/
    # Also find the unstripped form before formatting
    grep -rn "def.*\*, take \|def.*\*, owned " examples/ shared/
    ```

**Type Issues**:

- Missing type annotations (required in fn declarations)
- Mismatched types in assignments
- Invalid type parameters

**Ownership Issues**:

- Missing transfer operator `^` for non-copyable types
- Using `var` parameter incorrectly
- Copy/move semantics violations

## Validation Workflow

1. **Identify file type**: Determine if file is library (has relative imports) or executable (has main())
2. **Check syntax**: Run appropriate command:
   - Executable files: `mojo build -I . file.mojo`
   - Library files: Skip standalone compilation (part of package)
3. **Fix format**: Run `pixi run mojo format` to auto-fix style
4. **Verify patterns**: Check for deprecated patterns
5. **Type check**: Ensure all types are correct
6. **Ownership check**: Verify ownership semantics
7. **Package validation**: Use `mojo package shared` for library files
8. **Report issues**: List all problems found

## Output Format

Report syntax issues with:

1. **File** - Which file has the issue
2. **Line** - Line number of error
3. **Error** - Syntax error message
4. **Pattern** - What deprecated/wrong pattern was used
5. **Fix** - How to correct it
6. **Severity** - Critical (won't compile) or warning

## Error Handling

| Problem | Solution |
| --------- | ---------- |
| Compiler not found | Verify mojo is installed and in PATH |
| Module not found | Add `-I .` flag to include current directory |
| Encoding issues | Convert file to UTF-8 |
| Version mismatch | Check mojo version against v0.26.1+ |
| Large files | Process one file at a time |

## Validation Checklist

Before committing Mojo code:

- [ ] File compiles with `mojo build`
- [ ] No syntax errors in compiler output
- [ ] No deprecated patterns (inout, @value, DynamicVector)
- [ ] All `__init__` use `out self` (not `mut self`)
- [ ] All non-copyable returns use `^` operator
- [ ] All type annotations present in fn declarations
- [ ] Zero compiler warnings
- [ ] No `take`/`owned` argument modifiers in `def` functions (use `fn` or delete if no callers)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `def __init__(out self, *, take existing: Self)` | Used `take` modifier in a `def` function to express ownership transfer | Parse error in Mojo 0.26.3; `take`/`owned` modifiers are only valid in `fn` functions. `mojo format` strips the space, turning `take existing` into `takeexisting` as a single parameter name — compiles silently but `existing` field is inaccessible and the constructor is useless | Delete dead constructors (zero callers) or convert to `fn __init__(out self, owned existing: Self):` if genuinely needed |

## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See CLAUDE.md for v0.26.1+ syntax standards
- See validate-mojo-patterns for pattern validation
- See mojo-format skill for code formatting
