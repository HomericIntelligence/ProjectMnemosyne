---
name: mojo-adr009-test-file-split
description: "Split oversized Mojo test files to comply with ADR-009 heap corruption workaround. Use when: a test file exceeds the fn test_ limit, CI shows non-deterministic JIT crashes from libKGENCompilerRTShared.so, or applying ADR-009 to new test files."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) triggers when test files contain too many `fn test_` functions |
| **ADR-009 Limit** | ≤10 `fn test_` per file (target ≤8 for safety margin) |
| **CI Symptom** | Non-deterministic CI group failures, ~65% failure rate on main |
| **Fix** | Split oversized file into N parts, each with ≤8 tests, each with ADR-009 header |
| **CI Impact** | Wildcard patterns (`utils/test_*.mojo`) automatically pick up new files |

## When to Use

- A `test_*.mojo` file has more than 10 `fn test_` functions
- CI group shows intermittent heap corruption crashes unrelated to test logic
- Adding tests would push an existing file over the limit
- Applying ADR-009 retroactively to legacy test files
- `libKGENCompilerRTShared.so` segfaults appear in CI logs

## Verified Workflow

### 1. Count Tests in the File

```bash
grep -c '^fn test_' tests/path/to/test_foo.mojo
```

### 2. Plan the Split

Divide tests into groups of ≤8. For N tests: `ceil(N / 8)` files.

Example for 39 tests: 5 files × 8 tests (last file gets 7).

### 3. Create Split Files

Each file needs:

- ADR-009 header comment at top (before docstring)
- All imports from the original file
- Its subset of `fn test_` functions
- A `fn main() raises:` that calls only its own tests

**Required ADR-009 header**:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_foo.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### 4. Delete the Original File

```bash
git rm tests/path/to/test_foo.mojo
```

### 5. Check CI Workflow Pattern

The CI `comprehensive-tests.yml` uses wildcard patterns like `utils/test_*.mojo`.
These automatically cover `test_foo_part1.mojo`, `test_foo_part2.mojo`, etc.

If the original file was named explicitly (not via wildcard), update the pattern:

```yaml
# Before
pattern: "test_foo.mojo test_bar.mojo"

# After
pattern: "test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo test_bar.mojo"
```

### 6. Verify Test Count

```bash
for f in tests/path/to/test_foo_part*.mojo; do
  echo "$f: $(grep -c '^fn test_' "$f") tests"
done
```

### 7. Verify Total Preservation

Original count must equal sum of all part counts:

```bash
# Should match original count
grep -c '^fn test_' tests/path/to/test_foo_part*.mojo | awk -F: '{sum+=$2} END{print sum}'
```

### 8. Commit

```bash
git add tests/path/to/test_foo_part*.mojo tests/path/to/test_foo.mojo
git commit -m "fix(ci): split test_foo.mojo into N files per ADR-009 (≤8 tests each)"
```

Pre-commit `validate-test-coverage` hook will confirm all new files are covered by CI.

## Results & Parameters

### Key Numbers

| Parameter | Value |
|-----------|-------|
| Mojo version | v0.26.1 |
| ADR-009 hard limit | ≤10 `fn test_` per file |
| Recommended target | ≤8 `fn test_` per file (safety margin) |
| Files created for 39 tests | 5 files (4×8 + 1×7) |
| CI failure rate before | ~65% (13/20 runs) |

### File Naming Convention

```text
test_foo.mojo         → test_foo_part1.mojo
                        test_foo_part2.mojo
                        test_foo_part3.mojo
                        ...
```

### CI Wildcard Coverage

Most CI groups use wildcard patterns. Verify with:

```bash
grep -A2 "Shared Infra" .github/workflows/comprehensive-tests.yml
```

If the pattern ends in `test_*.mojo`, all part files are covered automatically.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `continue-on-error: true` | Marking the CI group non-blocking instead of fixing root cause | Masked the real failure; other unrelated failures also got hidden | Always fix the root cause (file size); `continue-on-error` is a last resort |
| Keeping `test_io.mojo` and adding parts | Leaving original alongside split files | Would double-run tests in CI, doubling the load and defeating the purpose | Delete the original; the parts are the full replacement |
| Updating CI workflow explicitly | Hardcoding `test_io_part1.mojo test_io_part2.mojo ...` in pattern | Unnecessary work since wildcard `utils/test_*.mojo` already covers them | Check existing patterns first — wildcards often already cover new files |
