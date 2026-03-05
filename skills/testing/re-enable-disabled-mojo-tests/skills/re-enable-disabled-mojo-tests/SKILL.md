---
name: re-enable-disabled-mojo-tests
description: "Re-enable disabled Mojo test files by investigating root cause and replacing stubs with real tests. Use when: a .mojo test file has a NOTE saying tests are disabled, a test file only prints SKIPPED, or cleanup issues ask to re-enable tests."
category: testing
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | re-enable-disabled-mojo-tests |
| **Category** | testing |
| **Trigger** | Test file with disable NOTE or SKIPPED stub |
| **Outcome** | Full test suite replacing the stub |

## When to Use

- A `.mojo` test file contains `NOTE: These tests are temporarily disabled`
- The test file only has a `main()` that prints "SKIPPED" with no actual test functions
- A GitHub cleanup issue asks to re-enable or investigate disabled tests
- You need to verify whether a Mojo type system issue from an older version is now resolved

## Verified Workflow

1. **Read the disabled test file** - Check whether it has real test functions or is just a stub
2. **Read the issue comments** with `gh issue view <N> --comments` - Prior planning may already be done
3. **Search for what the tests were supposed to test** - Check if referenced modules exist:
   ```bash
   # Look for the module referenced in the disable note
   find . -name "*.mojo" | xargs grep -l "UInt8\|uint8" 2>/dev/null
   ```
4. **Check if builtins work** - If the original issue was with custom wrapper structs that shadow builtins, verify the builtins are used in other working files:
   ```bash
   grep -r "UInt8\|UInt16\|UInt32\|UInt64" shared/core/ --include="*.mojo" -l
   ```
5. **Determine correct target** - If the custom module was never created, test the Mojo builtins directly
6. **Write test functions** using the pattern from other test files in the same directory:
   - Plain `fn test_*() raises:` functions
   - `if condition: raise Error("message")` assertions (no testing framework import needed)
   - `fn main()` that calls each test in a try/except block and prints OK/FAIL
7. **Test coverage for unsigned integer types** - Include:
   - Construction from literals and boundary values (0, max for each type)
   - Arithmetic: `+`, `-`, `*`, `//`, `%`
   - Bitwise: `&`, `|`, `^`, `<<`, `>>`
   - Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
   - Widening conversions via `.cast[DType.uintN]()`
   - Conversions to/from `Int`
   - Large value operations (especially for UInt64)
   - Near-boundary arithmetic
8. **Verify with mojo build** before committing:
   ```bash
   pixi run mojo build tests/shared/core/test_unsigned.mojo
   ```
9. **Run pre-commit** and commit:
   ```bash
   just pre-commit-all
   git add tests/shared/core/test_unsigned.mojo
   git commit -m "fix(tests): re-enable unsigned integer type tests"
   ```

## Key Findings

### The "disabled" test file may be an empty stub

When investigating issue #3081, the test file `test_unsigned.mojo` was not just "disabled" - it
had NO test functions at all. The entire file was a stub that only printed SKIPPED. The fix was
to write all test functions from scratch, not to remove a skip guard.

### Custom wrapper structs vs builtins

The original disable note said "type system issues with unsigned integer types." Investigation
revealed the issue was with custom wrapper structs (`shared/core/types/unsigned.mojo`) that
were NEVER created. Mojo's built-in `UInt8`, `UInt16`, `UInt32`, `UInt64` types work fine.
The correct fix was to test the builtins directly.

### Conversion syntax for Mojo builtins

Widening conversions between unsigned types use `.cast[]()` not implicit casting:
```mojo
var u8: UInt8 = 200
var u16: UInt16 = u8.cast[DType.uint16]()  # Correct
# var u16: UInt16 = u8  # May or may not work depending on Mojo version
```

Conversion to `Int` works via constructor:
```mojo
var i = Int(u8)  # Correct
```

Conversion FROM `Int` to unsigned types works via implicit assignment:
```mojo
var i: Int = 42
var u8: UInt8 = i  # Works in current Mojo
```

### Mojo format GLIBC issue in dev environment

Pre-commit hook `mojo format` fails locally due to GLIBC incompatibility in the dev environment.
This is pre-existing and expected - CI runs in Docker where it passes. Document this in PR body
so reviewers understand the hook failure is environmental, not a code issue.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming tests existed but were "disabled" | Expected to find a skip guard or `@disabled` annotation to remove | The file had zero test functions - it was a complete stub | Always `Read` the actual file before assuming its structure from the issue description |
| Looking for `shared/core/types/unsigned.mojo` | Searched for the custom wrapper module the disable note referenced | File never existed - was abandoned before being created | When a module is referenced in a note but doesn't exist, test the builtins instead |
| Using `List[Int](1, 2, 3)` constructor syntax | Tried older Mojo list construction pattern | Mojo v0.26.1+ uses list literals `[1, 2, 3]` | Compiler is truth - use `mojo build` to verify syntax |

## Results & Parameters

### Test file structure (copy-paste template)

```mojo
"""Tests for Mojo's built-in unsigned integer types (UInt8, UInt16, UInt32, UInt64).

These tests verify the behavior of Mojo's native unsigned integer builtins,
including arithmetic, bitwise operations, comparisons, boundary values,
and conversions.
"""


fn test_uint8_construction() raises:
    """Test UInt8 construction from literals and zero value."""
    var zero: UInt8 = 0
    var one: UInt8 = 1
    var max_val: UInt8 = 255

    if zero != 0:
        raise Error("UInt8 zero construction failed")
    if one != 1:
        raise Error("UInt8 one construction failed")
    if max_val != 255:
        raise Error("UInt8 max value construction failed")


fn main():
    """Main test runner."""
    try:
        test_uint8_construction()
        print("OK test_uint8_construction")
    except e:
        print("FAIL test_uint8_construction:", e)

    print("\n=== Tests Complete ===")
```

### PR description template for mojo format GLIBC issue

```markdown
## Verification

- Pre-commit hooks pass (trailing whitespace, end-of-file, YAML, markdown, Python linting)
- Mojo format hook fails for all files on this system due to GLIBC incompatibility -
  this is a pre-existing environment issue, CI runs in Docker where it passes

Closes #<issue-number>
```
