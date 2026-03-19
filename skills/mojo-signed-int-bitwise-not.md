---
name: mojo-signed-int-bitwise-not
description: 'Pattern for adding bitwise NOT (~) tests for Mojo signed integer types
  using two''s complement semantics. Use when: adding ~ operator tests for Int8/Int16/Int32/Int64,
  extending unsigned NOT tests to signed types, or implementing ADR-009 compliant
  test splits.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Language** | Mojo 0.26.1 |
| **Operator** | `~` (bitwise NOT) |
| **Types** | `Int8`, `Int16`, `Int32`, `Int64` |
| **Semantics** | Two's complement: `~x == -x - 1` |
| **Split** | 2 files (ADR-009: ≤10 tests per file) |
| **CI** | Explicit filenames in `comprehensive-tests.yml` |

## When to Use

- Adding `~` operator tests for any signed Mojo integer type
- Following up on unsigned bitwise NOT tests (e.g., after issues covering `UInt8`–`UInt64`)
- Creating new integer operator test files that must comply with ADR-009 (Mojo 0.26.1 heap corruption limit)
- Registering new Mojo test files into the `comprehensive-tests.yml` CI pattern

## Verified Workflow

### Quick Reference

```
Test cases per type: ~0, ~(-1), ~MAX, ~~x (double inversion)
Split: part1 = Int8 + Int16, part2 = Int32 + Int64
Files: tests/shared/core/test_int_bitwise_not_part1.mojo
       tests/shared/core/test_int_bitwise_not_part2.mojo
CI update: .github/workflows/comprehensive-tests.yml (explicit filenames)
```

### Step 1: Understand the semantics

Mojo signed integer types use two's complement. Key boundary values:

| Type | `~0` | `~(-1)` | `~MAX` | MAX | MIN |
|------|------|---------|--------|-----|-----|
| `Int8` | -1 | 0 | -128 | 127 | -128 |
| `Int16` | -1 | 0 | -32768 | 32767 | -32768 |
| `Int32` | -1 | 0 | -2147483648 | 2147483647 | -2147483648 |
| `Int64` | -1 | 0 | -9223372036854775808 | 9223372036854775807 | -9223372036854775808 |

### Step 2: Check ADR-009 limit

ADR-009 caps test files at **≤10 test functions** due to a Mojo 0.26.1 heap corruption bug
triggered after ~15 cumulative tests. With 4 types × 4 cases = 16 tests, split into 2 files:

- **part1**: Int8 (4 tests) + Int16 (4 tests) = 8 total
- **part2**: Int32 (4 tests) + Int64 (4 tests) = 8 total

### Step 3: Write each test file

```mojo
"""Tests for the bitwise NOT (~) operator on signed integer types (part 1).

Covers Int8 and Int16 with signed-specific boundary values using two's complement
semantics: ~x == -x - 1.

Follow-up from #3293 (issue #3896).

Note: Split from part2 due to Mojo 0.26.1 heap corruption bug that occurs after
~15 cumulative tests. See ADR-009 and Issue #2942.
"""


fn test_int8_not_zero() raises:
    """~Int8(0) should equal -1 (two's complement: ~0 == -1)."""
    var result: Int8 = ~Int8(0)
    if result != -1:
        raise Error("~Int8(0) expected -1, got " + String(result))


fn test_int8_not_neg_one() raises:
    """~Int8(-1) should equal 0 (two's complement: ~(-1) == 0)."""
    var result: Int8 = ~Int8(-1)
    if result != 0:
        raise Error("~Int8(-1) expected 0, got " + String(result))


fn test_int8_not_max() raises:
    """~Int8(127) should equal -128 (two's complement boundary: ~MAX == MIN)."""
    var result: Int8 = ~Int8(127)
    if result != -128:
        raise Error("~Int8(127) expected -128, got " + String(result))


fn test_int8_double_inversion() raises:
    """~~Int8(42) should equal 42 (double complement identity)."""
    var val: Int8 = 42
    if ~~val != val:
        raise Error("~~Int8(42) expected 42")
```

Use the same 4-case pattern for each type, then add a `fn main()` that calls each test
in a `try/except` block and prints `OK <test_name>` or `FAIL <test_name>: <error>`.

### Step 4: Check CI auto-discovery vs explicit registration

The `test-mojo` justfile recipe auto-discovers `tests/**/*.mojo`, so new files run locally
without any changes. However, `comprehensive-tests.yml` requires **explicit filenames**
(not globs) per ADR-009 CI constraint (see Issue #4110).

Add filenames to the correct group pattern in the workflow:

```yaml
- name: "Core Activations & Types"
  path: "tests/shared/core"
  pattern: "... test_uint_bitwise_not.mojo test_int_bitwise_not_part1.mojo test_int_bitwise_not_part2.mojo ..."
```

Use `sed` to insert the new filenames adjacent to the existing related entry:

```bash
sed -i 's/test_uint_bitwise_not\.mojo test_dtype_dispatch/test_uint_bitwise_not.mojo test_int_bitwise_not_part1.mojo test_int_bitwise_not_part2.mojo test_dtype_dispatch/' \
  .github/workflows/comprehensive-tests.yml
```

### Step 5: Run pre-commit validation

```bash
# Stage files first (pre-commit needs them staged)
git add tests/shared/core/test_int_bitwise_not_part1.mojo \
        tests/shared/core/test_int_bitwise_not_part2.mojo \
        .github/workflows/comprehensive-tests.yml

# Run pre-commit (SKIP mojo-format if local GLIBC differs from CI)
SKIP=mojo-format pixi run pre-commit run --files \
  tests/shared/core/test_int_bitwise_not_part1.mojo \
  tests/shared/core/test_int_bitwise_not_part2.mojo \
  .github/workflows/comprehensive-tests.yml
```

Expected output: all hooks `Passed` or `Skipped`.

Note: `mojo-format` actually runs fine on this project even locally — `SKIP=mojo-format`
is listed only as a fallback for GLIBC-constrained environments.

### Step 6: Commit and create PR

```bash
git commit -m "test(core): Add bitwise NOT tests for signed integer types

Add two split test files covering the ~ operator for Int8, Int16,
Int32, and Int64 with signed two's complement semantics (~x == -x - 1).

Each file covers two types × 4 cases (not_zero, not_neg_one, not_max,
double_inversion), keeping under the ADR-009 limit of ≤10 tests per file.

Also registers the new files in comprehensive-tests.yml CI pattern (per
ADR-009 CI constraint: explicit filenames, not globs).

Closes #3896

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

gh pr create \
  --title "test(core): Add bitwise NOT tests for signed integer types (Int8/16/32/64)" \
  --body "..." \
  --label "testing"

gh pr merge --auto --rebase <PR_NUMBER>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single file with 16 tests | Put all Int8/16/32/64 tests in one file | Would exceed ADR-009 ≤10 limit, risking Mojo 0.26.1 heap corruption | Always split at 8 tests/file when covering 4 integer types × 4 cases |
| Glob pattern in CI | Used `test_int_bitwise_not*.mojo` in comprehensive-tests.yml | ADR-009 CI constraint: `pattern` field accepts only space-separated literal filenames, not globs | Enumerate all split filenames explicitly in the pattern field |
| Omitting `~(-1) == 0` test case | Initial draft only tested `~0`, `~MAX`, and `~~x` | The `~(-1) == 0` case is the canonical signed complement identity and was mentioned in the issue | Include all four boundary cases: `~0`, `~(-1)`, `~MAX`, `~~x` |

## Results & Parameters

### Test count per file

```
part1: 8 (Int8×4 + Int16×4) — safely under ADR-009 limit of 10
part2: 8 (Int32×4 + Int64×4) — safely under ADR-009 limit of 10
```

### Boundary values used

```
Int8:  ~0 == -1, ~(-1) == 0, ~127 == -128, ~~42 == 42
Int16: ~0 == -1, ~(-1) == 0, ~32767 == -32768, ~~1000 == 1000
Int32: ~0 == -1, ~(-1) == 0, ~2147483647 == -2147483648, ~~12345 == 12345
Int64: ~0 == -1, ~(-1) == 0, ~9223372036854775807 == -9223372036854775808, ~~999999 == 999999
```

### Pre-commit hooks that validated these files

```
Mojo Format .......................... Passed
Check for deprecated List[Type]() ... Passed
Enforce no .__matmul__() ............. Passed
Validate Test Coverage ............... Passed
Validate ADR-009 Headers ............. Passed
Trim Trailing Whitespace ............. Passed
Fix End of Files ..................... Passed
Check YAML ........................... Passed
Fix Mixed Line Endings ............... Passed
```
