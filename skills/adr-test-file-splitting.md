---
name: adr-test-file-splitting
description: 'Split large Mojo test files into smaller per-file limits defined by
  an ADR to prevent heap corruption. Use when: test file exceeds fn test_ limit, CI
  has intermittent JIT crashes, or Mojo heap corruption is suspected from test load.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Single Mojo test file with too many `fn test_` functions causes intermittent heap corruption (libKGENCompilerRTShared.so JIT fault) in CI |
| **Root Cause** | Mojo v0.26.1 has a JIT memory issue that triggers under high test load within a single compilation unit |
| **Solution** | Split large test files into multiple smaller files, each within the ADR-009 limit (≤10 `fn test_` functions) |
| **ADR** | ADR-009: Heap Corruption Workaround (`docs/adr/ADR-009-heap-corruption-workaround.md`) |
| **CI Impact** | Eliminates non-deterministic `Core Tensors` group failures (was failing 13/20 runs) |

## When to Use

- A Mojo test file has more `fn test_` functions than the ADR limit (e.g., ADR-009 limits to ≤10)
- CI shows intermittent `libKGENCompilerRTShared.so` crashes or segfaults on test runs
- A specific CI test group fails non-deterministically with no code changes
- A test file count badge shows a file exceeding the per-file limit

## Verified Workflow

### 1. Count existing tests

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Plan the split

Group related tests logically (by operation, feature, or phase):

- Aim for ≤8 tests per file (conservative margin below the ≤10 limit)
- Keep related tests together (e.g., all "addition" tests in one file)
- Name files `test_<base>_part1.mojo`, `test_<base>_part2.mojo`, etc.

### 3. Create each split file

Each split file must:

1. Include the ADR tracking comment at the top of the module docstring:

   ```mojo
   # ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
   # Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
   # high test load. Split from <original_file>. See docs/adr/ADR-009-heap-corruption-workaround.md
   ```

2. Import only what is needed for its subset of tests
3. Include a `main()` function that runs all tests in the file
4. Have ≤8 `fn test_` functions

### 4. Delete the original file

```bash
rm tests/path/to/test_<base>.mojo
```

### 5. Update CI workflow patterns

In `.github/workflows/comprehensive-tests.yml`, find the test group pattern and replace the single filename with all split filenames:

```yaml
# Before
pattern: "test_arithmetic.mojo test_other.mojo"

# After
pattern: "test_arithmetic_part1.mojo test_arithmetic_part2.mojo ... test_other.mojo"
```

### 6. Update any README/documentation references

Search for the old filename:

```bash
grep -r "test_<base>.mojo" tests/ docs/ .github/
```

Replace example references with `test_<base>_part1.mojo`.

### 7. Verify counts and commit

```bash
# Verify all files are within limit
for f in tests/path/to/test_<base>_part*.mojo; do
  count=$(grep -c "^fn test_" "$f")
  echo "$f: $count tests"
done

# Verify total is preserved
total=$(for f in tests/path/to/test_<base>_part*.mojo; do grep -c "^fn test_" "$f"; done | awk '{s+=$1} END {print s}')
echo "Total: $total"

# Stage and commit
git add tests/path/to/test_<base>*.mojo .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_<base>.mojo (N tests) into M files per ADR-009"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep original file | Leave `test_arithmetic.mojo` in place alongside split files | Would create duplicate test registration and double test count | Must delete original; it cannot coexist with split files |
| Alphabetical splitting | Distribute tests A–Z across files regardless of topic | Tests for same operation (e.g., `add_shapes` and `add_backward`) ended up in different files | Group by operation/feature for maintainability; reviewers expect related tests together |
| Uniform 7-test split | Divide 58 tests into 8 equal 7-8 files mechanically | Not wrong per se, but some files ended with unrelated tests mixed together | Prefer semantic grouping even if file sizes vary (5–8 is fine, all ≤8) |

## Results & Parameters

### Key Numbers (test_arithmetic.mojo example)

```text
Original: 58 fn test_ functions in 1 file (5.8x over ADR-009 limit)
Split into: 8 files
Distribution: 7, 7, 8, 7, 8, 8, 8, 5 tests
All files: ≤8 tests (within ADR-009 ≤10 limit)
Total preserved: 58 tests (no tests deleted)
CI impact: Core Tensors group failure rate dropped from 13/20 to 0/N
```

### ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Grouping Strategy (for arithmetic operations)

```text
Part 1: addition ops (forward + backward)
Part 2: subtraction ops (forward + backward)
Part 3: multiplication ops (forward + backward)
Part 4: division ops (forward + backward)
Part 5: floor_divide + modulo (basic cases)
Part 6: modulo (edge cases) + power
Part 7: operator overloading (dunders) + dtype preservation
Part 8: shape preservation + error handling
```

### CI Workflow Pattern Update

```yaml
# In .github/workflows/comprehensive-tests.yml
# Replace single filename with all split files in the pattern field:
pattern: "test_arithmetic_part1.mojo test_arithmetic_part2.mojo test_arithmetic_part3.mojo test_arithmetic_part4.mojo test_arithmetic_part5.mojo test_arithmetic_part6.mojo test_arithmetic_part7.mojo test_arithmetic_part8.mojo test_other.mojo"
```
