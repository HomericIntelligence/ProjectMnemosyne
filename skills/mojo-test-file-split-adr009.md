---
name: mojo-test-file-split-adr009
description: "Split Mojo test files exceeding ADR-009 limit (<=10 fn test_ per file) to prevent heap corruption and compile hangs. Use when: (1) a .mojo test file has >10 fn test_ functions, (2) CI fails intermittently with libKGENCompilerRTShared.so JIT fault, (3) a test file takes >120s to compile due to heavyweight backward passes."
category: testing
date: 2026-03-27
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, adr-009, heap-corruption, test-splitting, ci, jit]
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 has a JIT heap corruption bug (`libKGENCompilerRTShared.so`) triggered when too many `fn test_` functions are compiled in a single file |
| **Symptom** | Non-deterministic CI failures (~65% failure rate), or deterministic crash at Nth sequential call for deep networks |
| **Root Cause** | Cumulative JIT memory from sequential test function compilations exceeds heap capacity |
| **Fix** | ADR-009: split test files so each has <=10 `fn test_` functions (target <=8 for safety) |
| **Deep Networks** | VGG-16 scale (11+ layers): use <=5 tests per file; medium (6-10 layers): <=7 |

## When to Use

- A `.mojo` test file contains more than 10 `fn test_` functions
- CI fails intermittently with `libKGENCompilerRTShared.so` JIT fault (no code changes)
- A CI test group has `continue-on-error: true` as a heap corruption workaround
- A test file takes >120s to compile (heavyweight backward passes, large parametric types)
- CI shows a test file passing fewer tests than it has functions (early exit on crash)
- ADR-009 compliance check flags a file as over-limit

## Verified Workflow

### Quick Reference

```bash
# Count test functions (use [a-z] suffix to avoid counting ADR-009 header lines)
grep -c "^fn test_[a-z]" <test-file>.mojo

# Plan split: target <=8 per file, group by logical topic
# Create part files with ADR-009 header + own imports + own main()
# Delete original, verify CI coverage, commit
```

### Step 1: Count test functions

```bash
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo
```

Use `^fn test_[a-z]` (not `^fn test_`) to avoid counting ADR-009 header comment lines that contain `fn test_` text. Never trust the issue description's test count -- always grep the actual file.

If count > 10, proceed with split. For deep networks (VGG-16 scale), split if count > 5.

### Step 2: Plan the split

Divide tests into logical groups by operation type. Target <=8 tests per file (safety margin below the hard 10-test limit).

```text
parts = ceil(total_tests / 8)
tests_per_part = ceil(total_tests / parts)
```

Examples:
- 22 tests -> 3 files of 8/8/6
- 37 tests -> 5 files of 5/8/8/6/10
- 13 tests -> 2 files of 8/5

### Step 3: Audit imports before splitting

Before creating split files, check for import gaps in the original file. Mojo sometimes resolves symbols through transitive or JIT context imports that only manifest as errors when the file is isolated.

```bash
# Find all top-level imports
grep "^from\|^import" tests/path/to/test_file.mojo

# Find symbols from a specific module that are actually used
grep -oE "\brandn\b|\bzeros\b|\bones\b|\bfull\b|\bExTensor\b" tests/path/to/test_file.mojo | sort -u
```

Cross-reference: if a symbol appears in usage but NOT in the import line, add it before creating split files.

Also check for inline imports inside function bodies -- copy these verbatim into the part file that contains that function. Do NOT hoist them to top level unless used by multiple tests in the same part.

### Step 4: Create part files with ADR-009 header

Each new file MUST begin with this header comment:

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Each part file must be fully self-contained:
- Complete import block (copy from original, trim to only used imports)
- All helper functions redefined (Mojo has no `#include` or conftest mechanism)
- Its own `fn main() raises:` calling only the tests in that file

### Step 5: Delete the original file

```bash
git rm tests/path/to/test_original.mojo
```

The original must be deleted -- keeping it alongside split files would double-run tests and negate the fix.

### Step 6: Update CI workflow and validate_test_coverage.py

Check whether CI uses a **glob** or **explicit filename list**:

```bash
grep "<original_filename>" .github/workflows/comprehensive-tests.yml
```

- **Glob pattern** (e.g., `test_*.mojo`): new `_part1/2/3` files are picked up automatically -- no workflow changes needed
- **Explicit filename list**: replace the original filename with all part filenames

Then check `validate_test_coverage.py` **independently** (glob in workflow does NOT mean glob in this script):

```bash
grep "<original_filename>" scripts/validate_test_coverage.py
```

If found, replace the single entry with entries for each part file.

If the CI group had `continue-on-error: true` as a heap corruption workaround, remove it.

### Step 7: Verify counts and total preservation

```bash
# Verify no file exceeds limit
for f in tests/path/test_*_part*.mojo; do
  echo "$f: $(grep -c '^fn test_[a-z]' "$f") tests"
done

# Verify total test count matches original
grep -c "^fn test_[a-z]" tests/path/test_*_part*.mojo
```

Total test count must be identical before and after the split.

### Step 8: Run pre-commit validation

```bash
just pre-commit-all
```

The `validate_test_coverage.py` hook will catch any files not covered by CI patterns.

### Step 9: Commit

```bash
git add tests/path/to/test_*_part*.mojo \
        tests/path/to/test_original.mojo \
        .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_<name>.mojo into N files per ADR-009"
```

### Compile Hang Variant

When a test file compiles but hangs (>120s) rather than crashing, the cause is usually heavyweight backward-pass tests alongside forward-pass tests. Instead of creating new part files, move the heavyweight tests to a sibling part file that has capacity:

```bash
# Check all sibling part files for capacity
for f in tests/models/test_<name>_part*.mojo; do
  echo "$f: $(grep -c '^fn test_' "$f")"
done
```

Move backward-pass tests to a sibling with fewer than 8 tests. This avoids creating unnecessary new files.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `continue-on-error: true` | Marked CI group as non-fatal | Masked real failures, did not fix root cause | Only use as temporary mitigation, not a fix |
| Keeping 10 tests per file (at limit) | Set exactly at the ADR-009 limit | Edge cases still triggered corruption | Use <=8 (safety margin); for deep networks use <=5 |
| Reducing batch size | Halved batch_size in tests | Crash still occurs -- issue is cumulative JIT memory across function calls, not per-call memory | Number of sequential JIT compilations is the trigger, not test complexity |
| Trusted issue description test count | Issue said 15 tests; planned a 2-way split | Actual count was 20 -- issue undercounted | Always `grep -c "^fn test_[a-z]"` to get the real count |
| Used `grep -c "fn test_"` to count | Counted lines matching pattern | ADR-009 header comment contains `fn test_` text, inflating count by 1 | Use `^fn test_[a-z]` to exclude comment lines |
| Copy imports verbatim from original | Copied the original import line exactly | Original had latent import gap (`randn` used but not imported) -- Mojo resolved it through transitive imports | Grep actual symbol usage vs imports before splitting |
| Keep original + add new files | Kept original alongside split files | Doubles test execution, negates the fix, `validate_test_coverage.py` reports original as uncovered | Original must be deleted; split files fully replace it |
| Shared imports via include | Extract common imports to a shared file | Mojo v0.26.1 has no `#include` mechanism | Copy imports into every part file |
| Skipped validate_test_coverage.py check | CI workflow used glob so assumed everything was fine | `validate_test_coverage.py` had a separate exclusion list with original filename hardcoded | Always check both workflow YAML and validate_test_coverage.py independently |
| Modified CI workflow for glob-covered files | Thought new files would not be matched by existing glob | Glob `test_*.mojo` already covers `test_*_part1.mojo` | Verify existing glob before making workflow changes |
| Split into 3 files of ~4 tests each | Over-fragmented the test suite | More files than needed; harder to navigate | Target <=8 per file (not minimum possible); 2 files usually sufficient for 13-15 tests |
| Delete backward tests to fix compile hang | Removed heavyweight tests entirely | Loses backward-pass test coverage | Move to sibling part file with capacity, never delete tests |
| Create new part6 for overflow | Created brand new file when sibling had capacity | Unnecessary fragmentation | Check existing sibling capacity first |

## Results & Parameters

### Safe test limits by network scale

| Network Scale | Safe Tests Per File | Notes |
|--------------|--------------------|----|
| Shallow (<=5 layers) | <=10 | Standard ADR-009 limit |
| Medium (6-10 layers) | <=7 | LeNet-5, small ResNets |
| Deep (11+ layers) | <=5 | VGG-16, ResNet-50 |

### ADR-009 header template

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Naming convention

```text
test_<name>.mojo        -> deleted
test_<name>_part1.mojo  -> first group of tests
test_<name>_part2.mojo  -> second group of tests
```

### CI workflow pattern (explicit filename lists)

```yaml
pattern: "core/test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo"
```

### Pre-commit hooks

- `mojo format` -- auto-formats all new part files
- `validate_test_coverage.py` -- confirms all files appear in CI workflow pattern
- `check-yaml` -- validates updated workflow YAML

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3409, PR #4142 | test_elementwise.mojo (37 -> 5 files) |
| ProjectOdyssey | Issue #3424, PR #4189 | test_utility.mojo (31 -> 4 files) |
| ProjectOdyssey | Issue #3438, PR #4223 | test_reduction.mojo (22 -> 3 files) |
| ProjectOdyssey | Issue #3444, PR #4238 | test_backward.mojo (21 -> 3 files) |
| ProjectOdyssey | Issue #3447 | test_utils.mojo (20 -> 3 files); issue said 18, actual 20 |
| ProjectOdyssey | Issue #3454, PR #4270 | test_comparison_ops.mojo (19 -> 3 files) |
| ProjectOdyssey | Issue #3457, PR #4278 | test_optimizer_base.mojo (18 -> 3 files); glob CI |
| ProjectOdyssey | Issue #3461, PR #4289 | test_normalization.mojo (21 -> 3 files); explicit CI filenames |
| ProjectOdyssey | Issue #3477, PR #4322 | test_conv.mojo (20 -> 3 files); issue undercounted (said 15) |
| ProjectOdyssey | Issue #3496, PR #4372 | test_checkpointing.mojo (13 -> 2 files); validate_test_coverage.py had explicit ref |
| ProjectOdyssey | Issue #3498, PR #4373 | test_gradient_checker_meta.mojo (14 -> 2 files) |
| ProjectOdyssey | Issue #3509, PR #4387 | test_file_dataset.mojo (13 -> 2 files); glob auto-covered |
| ProjectOdyssey | Issue #3549, PR #4400 | test_progress_bar.mojo (22 -> 3 files) |
| ProjectOdyssey | Issue #3635, PR #4444 | test_base.mojo (11 -> 2 files) |
| ProjectOdyssey | PR (VGG-16 split) | test_vgg16_e2e.mojo (10 -> 2 files of 5); deep network scale |
| ProjectOdyssey | PR (MobileNetV1 split) | test_mobilenetv1_e2e.mojo; import gap found (randn missing) |
| ProjectOdyssey | PR (AlexNet compile hang) | test_alexnet_layers_part4.mojo; backward tests moved to part5 |

**Related**: `docs/adr/ADR-009-heap-corruption-workaround.md`, issues #2942, #3397
