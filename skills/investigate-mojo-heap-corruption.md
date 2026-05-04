---
name: investigate-mojo-heap-corruption
description: "Systematic workflow for investigating and fixing Mojo heap corruption crashes, test file splitting (ADR-009), and Mojo version deprecation pitfalls. Use when: (1) CI-only heap corruption crashes in libKGENCompilerRTShared.so, (2) splitting oversized Mojo test files to <=10 functions (ADR-009), (3) Mojo 0.26.3+ parse errors in test files after splitting."
category: debugging
date: 2026-05-03
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: investigate-mojo-heap-corruption.history
tags:
  - mojo
  - heap-corruption
  - adr-009
  - test-splitting
  - fn-main
  - def-main
  - deprecation
  - ci
---

# Investigate Mojo Heap Corruption Crashes

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Investigate and fix Mojo heap corruption crashes; split oversized test files per ADR-009; avoid Mojo 0.26.3 `fn main` deprecation parse errors |
| **Outcome** | Crash identified and fixed (v1.0); ADR-009 test splits confirmed (v1.1); `fn main` deprecation CI fix confirmed (v1.1) |
| **Verification** | verified-ci -- `def main()` fix confirmed by CI passing after global replace |
| **History** | [changelog](./investigate-mojo-heap-corruption.history) |

## When to Use This Skill

Invoke this workflow when you encounter:

1. **CI-only crashes** that don't reproduce locally
2. **Heap corruption** errors in `libKGENCompilerRTShared.so`
3. **Crashes after ~15 cumulative tests** (heap corruption threshold in Mojo 0.26.x)
4. **Runtime crashes** with stack traces but no symbols
5. **Intermittent failures** in integration test suites
6. **ADR-009 file splitting** -- oversized Mojo test files need splitting to <=10 functions each
7. **Parse errors in new Mojo test files** after splitting (Mojo 0.26.3+: `fn main` deprecated)

### Trigger Patterns

```text
error: execution crashed
#0 0x00007fe7ca5c60bb (/path/to/libKGENCompilerRTShared.so+0x3c60bb)
#1 0x00007fe7ca5c3ce6 (/path/to/libKGENCompilerRTShared.so+0x3c3ce6)
```

```text
# Mojo 0.26.3 parse error in new split files:
error: 'fn' keyword not valid for 'main'; use 'def' instead
```

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Reproduce or localize crash
gh run view <run-id> --log 2>&1 | grep -A 10 -B 10 "<test-file-name>"
git checkout <headSha>
pixi run mojo -I . tests/path/to/test.mojo

# Phase 2: Fix root cause (type conversion or oversized file)
# For type conversion: replace ._get_float64() with ._get_float32()

# Phase 3: Split oversized test files (ADR-009 -- <=10 functions per file)
# Copy full import block verbatim to each part file
# Keep <=10 test functions per file
# Name parts: test_<base>_part1.mojo, test_<base>_part2.mojo, ...

# CRITICAL: After splitting, fix fn main deprecation (Mojo 0.26.3+)
# ALL new part files must use def main() not fn main()
find . -name "test_*_part*.mojo" -exec grep -l "fn main" {} \;
# Global replace in each file found:
sed -i 's/fn main() raises:/def main() raises:/g' test_*_part*.mojo

# Phase 4: Update CI glob patterns
# Old:  test_<base>.mojo
# New:  test_<base>_part*.mojo

# Phase 5: Validate
pixi run bash -c "for f in tests/**/test_*_part*.mojo; do mojo -I . \$f && echo OK: \$f; done"
```

### Detailed Steps

#### Phase 1: Identify Failing CI Run

1. **Locate the exact failing CI run** (don't rely on general reports)

   ```bash
   gh run list --workflow="Comprehensive Tests" --limit 10
   gh run view <run-id> --json conclusion,headSha,headBranch
   ```

2. **Extract crash logs**

   ```bash
   gh run view <run-id> --log 2>&1 | grep -A 10 -B 10 "<test-file-name>"
   ```

3. **Identify crash location**
   - Look for: Test number, last output before crash
   - Example: "Test 9: FP16 vs FP32 accuracy..." followed by crash

#### Phase 2: Checkout Exact Failing Commit

```bash
git checkout <headSha>
git log -1 --oneline
```

#### Phase 3: Attempt Local Reproduction

1. **Run test file individually** (usually passes):

   ```bash
   pixi run mojo -I . tests/path/to/test.mojo
   ```

2. **Run tests cumulatively** (like CI):

   ```bash
   pixi run just test-group "tests/shared/integration" "test_*.mojo"
   ```

3. **Stress test** (20+ iterations):

   ```bash
   for i in $(seq 1 20); do
     echo "=== Run $i ==="
     pixi run mojo -I . tests/path/to/test.mojo 2>&1 | tail -5
   done
   ```

#### Phase 4: Analyze Crashing Code

Look for suspicious patterns:
- Unnecessary type conversions (e.g., `._get_float64()` on Float32 data)
- Multiple ExTensor allocations in sequence
- Complex dtype casting operations

**Fix pattern**: Replace unnecessary type conversions with native type operations.

```mojo
# Before (causes heap corruption):
var original_val = test_data._get_float64(0)      # Float32 -> Float64

# After (uses native type):
var original_val = test_data._get_float32(0)      # Native Float32
```

#### Phase 5: ADR-009 Test File Splitting (>10 functions per file)

When a test file has >10 functions, split it into part files:

```bash
# Count functions in a test file
grep -c "^fn test_\|^def test_" tests/path/to/test_<base>.mojo

# If >10, split into parts:
# - test_<base>_part1.mojo  (functions 1-10)
# - test_<base>_part2.mojo  (functions 11-20)
# etc.

# RULES:
# 1. Copy the FULL import block verbatim to EVERY part file
# 2. Keep <= 10 test functions per file
# 3. Keep the original test_<base>.mojo if it still has <= 10 functions
#    (or delete it and replace with parts)
```

#### Phase 6: Fix fn main Deprecation (Mojo 0.26.3+) -- CRITICAL

**After splitting**, every new part file must have `def main() raises:` not `fn main() raises:`.
Mojo 0.26.3 deprecated `fn main()` and will produce a parse error in CI.

```bash
# Find all new part files using fn main
find . -name "test_*_part*.mojo" -exec grep -l "fn main" {} \;

# Fix: global replace in each file
# If using sed:
for f in $(find . -name "test_*_part*.mojo"); do
  sed -i 's/fn main() raises:/def main() raises:/g' "$f"
done

# Verify all fixed:
grep -r "fn main" tests/ --include="*.mojo" | grep "part"
# Should produce no output
```

#### Phase 7: Update CI Glob Patterns

Update CI workflow to include new part files:

```yaml
# Old pattern (misses part files):
- "tests/**/test_<base>.mojo"

# New pattern (catches all parts):
- "tests/**/test_<base>_part*.mojo"
```

Or use a broader glob if splitting many files:

```yaml
- "tests/**/test_*_part*.mojo"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running test file individually to reproduce crash | Used `pixi run mojo -I . tests/.../test.mojo` | Crash requires 15+ cumulative test executions (heap corruption threshold) | CI-only crashes may need cumulative reproduction -- run all integration tests sequentially |
| `fn main() raises:` in new split files | All 11 split files were written with `fn main()` | Mojo 0.26.3 deprecates `fn main()`; CI failed with parse error on every new file | After any file split in Mojo 0.26.3+, globally replace `fn main() raises:` with `def main() raises:` |
| Not updating CI glob after splitting | Left CI glob as `test_<base>.mojo` | Split files named `test_<base>_part*.mojo` were not discovered by CI | Always update CI glob patterns to `test_*_part*.mojo` when splitting |
| Partial import block in part files | Only copied some imports to part files | Missing imports cause compile errors in all functions that depend on them | Copy the FULL import block verbatim to every part file when splitting |
| Blocking PR on pre-existing ADR-009 flakes | Treated pre-existing test failures on main as regressions | Several test suites had ADR-009 flakes on main before the split | Pre-existing CI failures on main should not block a PR introducing the split fix |

## Results & Parameters

### Root Cause (v1.0 -- Type Conversion)

**Unnecessary Float32 -> Float64 conversion** in `test_fp16_vs_fp32_accuracy()`:

```mojo
# Before fix (lines 337-338):
var original_val = test_data._get_float64(0)
var roundtrip_val = back_to_fp32._get_float64(0)

# After fix (lines 339-340):
var original_val = test_data._get_float32(0)
var roundtrip_val = back_to_fp32._get_float32(0)
```

Triggered Mojo 0.26.1's heap corruption bug when combined with cumulative test executions
(13 tests total across all integration tests run before this one).

### ADR-009 Splitting Rules (v1.1)

| Rule | Detail |
| ---- | ------ |
| Max functions per file | 10 |
| Part file naming | `test_<base>_part1.mojo`, `test_<base>_part2.mojo`, ... |
| Import block | Copy FULL import block verbatim to every part file |
| main entrypoint | MUST use `def main() raises:` (not `fn main()`) for Mojo 0.26.3+ |
| CI glob | Update to `test_*_part*.mojo` |

### Mojo Version Compatibility

| Version | `fn main()` | `def main()` |
| ------- | ----------- | ------------ |
| 0.26.1 | OK | OK |
| 0.26.3 | DEPRECATED (parse error in CI) | Required |

### Verification Commands

```bash
# Check pre-commit passes
pixi run pre-commit run --all-files

# Verify test still passes
pixi run mojo -I . tests/shared/integration/test_multi_precision_training.mojo

# Verify no fn main in split files
grep -r "fn main" tests/ --include="test_*_part*.mojo"

# Check CI status
gh pr checks <pr-number>
```

### Configuration

- **Mojo Version**: 0.26.1 (v1.0 crash) / 0.26.3 (v1.1 deprecation)
- **Platform**: Linux x86_64 (GitHub Actions)
- **CI Environment**: Ubuntu 22.04
- **Test Framework**: Custom Mojo tests (not pytest)
- **ADR**: ADR-009 (heap corruption mitigation via file splitting)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/ProjectOdyssey | Test file splitting + fn main deprecation fix 2026-05-03 | 11 split files fixed; CI confirmed passing after def main replace; verified-ci |
| HomericIntelligence/ProjectOdyssey | Heap corruption crash fix 2026-01-08 (v1.0) | PR #3103 -- Float32->Float64 conversion removed; CI run #20826482385 |
