---
name: adr009-test-file-splitting
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
description: "Split Mojo test files exceeding the ADR-009 limit of 10 fn test_ per file
  to fix heap corruption CI crashes. Use when: (1) a Mojo test file has >10 fn test_
  functions, (2) CI shows intermittent non-deterministic libKGENCompilerRTShared.so
  crashes, (3) ADR-009 compliance audit flags a file, (4) a CI group fails
  non-deterministically, (5) CI workflow uses explicit filename lists requiring
  workflow update after split, (6) validate-test-coverage pre-commit hook fails
  because new split files are not in the workflow."
tags:
  - adr-009
  - mojo
  - heap-corruption
  - ci
  - test-splitting
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 JIT (`libKGENCompilerRTShared.so`) crashes non-deterministically under high test load when a single file has >10 `fn test_` functions |
| **ADR** | ADR-009 -- max 10 `fn test_` functions per `.mojo` test file |
| **Fix** | Split oversized test files into `_part1.mojo` / `_part2.mojo` / ... with target 8 tests each |
| **CI Impact** | Eliminates intermittent CI group failures (observed: 13/20 runs failing) |
| **Scope** | Any `.mojo` test file with >10 `fn test_` functions |
| **Effort** | ~15-20 minutes per file |

## When to Use

Trigger this skill when any of the following apply:

1. A Mojo test file has more than 10 `fn test_` functions
2. CI shows intermittent crashes with `libKGENCompilerRTShared.so` JIT fault in the error log
3. A CI group (e.g., "Testing Fixtures", "Shared Infra & Testing", "Core Tensors") fails non-deterministically -- not always the same test, just the same group
4. ADR-009 compliance audit flags a file as exceeding the limit
5. CI failure rate across recent runs is high (e.g., 13/20) with no single reproducible root cause
6. A new large test file is being added with 10+ tests (proactive split)
7. Issue title contains "ADR-009" and involves splitting a test file
8. The `validate-test-coverage` pre-commit hook fails because new `test_*.mojo` files are not listed in the CI workflow
9. `grep "test_<filename>.mojo" .github/workflows/*.yml` returns a match in an explicit filename list (not a glob)
10. After splitting, CI silently skips new part files because they are not in the explicit pattern

**CI pattern note**: Some CI groups use a glob (`test_*.mojo`) that auto-discovers `_partN` files. Others use explicit space-separated filenames that must be updated manually. Always check which pattern applies before assuming no CI changes are needed.

## Verified Workflow

### Quick Reference

```bash
# 1. Count tests
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo

# 2. Check CI pattern type (glob vs explicit)
grep -n "test_file" .github/workflows/comprehensive-tests.yml

# 3. Create part files (target <=8 tests each, ADR-009 header required)
# 4. Delete original
git rm tests/path/to/test_file.mojo

# 5. If explicit CI pattern: update workflow
# 6. Verify counts
for f in tests/path/to/test_file_part*.mojo; do
  echo "$f: $(grep -c "^fn test_[a-z]" "$f") tests"
done

# 7. Verify coverage script
python scripts/validate_test_coverage.py

# 8. Commit
git add tests/path/to/test_file_part*.mojo tests/path/to/test_file.mojo \
        .github/workflows/comprehensive-tests.yml \
        scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_file.mojo into N files (ADR-009)"
```

### Detailed Steps

#### Step 1 -- Count tests in the file

```bash
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo
```

Use `^fn test_[a-z]` (not just `^fn test_`) to avoid matching ADR-009 header comments that contain `fn test_` text. If count > 10, proceed with split.

#### Step 2 -- Plan the split

Divide tests into logical groups of 8 or fewer per file:

- Group by the function under test or operation category (e.g., all sqrt tests together, all log tests together) -- NOT alphabetically
- Keep integration/workflow tests together in the last file
- Target 8 per file (not 10) for a safety margin
- Calculate files needed: `ceil(total_tests / 8)`

Examples:
- 47 tests -> 6 files (8+8+8+8+8+7)
- 28 tests -> 4 files (8+5+8+7)
- 14 tests -> 2 files (7+7)

#### Step 3 -- Create split files with ADR-009 header

Each new file MUST include the ADR-009 comment block at the top (before the docstring):

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Tests for <topic> - Part N: <focus area>."""
```

**Naming convention**: `test_<original>_part1.mojo`, `test_<original>_part2.mojo`, etc.

Each split file needs:
- The ADR-009 header comment (mandatory)
- Its own imports (only what that file uses -- trim unused imports)
- Custom structs/ops duplicated in each file that uses them (Mojo test files cannot import from each other)
- Its subset of `fn test_` functions (verbatim copy)
- Its own `fn main() raises:` that calls only its tests
- Updated final print reflecting the correct count

#### Step 4 -- Delete the original file

```bash
git rm tests/path/to/test_file.mojo
```

Do NOT keep the original -- it will cause duplicate test runs and still trigger heap corruption.

#### Step 5 -- Check CI workflow pattern type

This is the critical fork in the workflow. Check whether the CI group uses a glob or explicit filenames:

```bash
grep -n "test_original_name" .github/workflows/comprehensive-tests.yml
```

##### Case A: Glob pattern (e.g., `test_*.mojo`)

No workflow changes needed. New `_partN` files are auto-discovered by the glob. Skip to Step 6.

##### Case B: Explicit filename list

The `pattern:` field lists filenames by name (e.g., `"test_a.mojo test_b.mojo"`). You MUST update the workflow:

1. Find the `pattern:` line containing the original filename
2. Replace the original filename with all new part filenames
3. Add an ADR-009 comment above the matrix entry

```yaml
# Before:
pattern: "... test_original.mojo ..."

# After:
# ADR-009: test_original.mojo split into N parts (<=8 tests each)
# to avoid Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so)
pattern: "... test_original_part1.mojo test_original_part2.mojo test_original_part3.mojo ..."
```

Verify the change:
```bash
grep -n "test_original" .github/workflows/comprehensive-tests.yml
# Should show only part files in pattern: line (original may appear only in the ADR-009 comment)
```

#### Step 6 -- Update validate_test_coverage.py (if needed)

```bash
grep -n "test_original_name" scripts/validate_test_coverage.py
```

If found (e.g., in an exclusion list), replace the single entry with all part filenames:

```python
# Before
"tests/shared/training/test_file.mojo",

# After
"tests/shared/training/test_file_part1.mojo",
"tests/shared/training/test_file_part2.mojo",
```

If not found, no changes needed (the script may use `Path.rglob("test_*.mojo")` for dynamic discovery).

#### Step 7 -- Verify test counts

```bash
for f in tests/path/to/test_original_part*.mojo; do
  count=$(grep -c "^fn test_[a-z]" "$f")
  echo "$f: $count tests"
done
# Each file should show <=8
```

#### Step 8 -- Commit and PR

```bash
git add tests/path/to/test_original_part*.mojo \
        tests/path/to/test_original.mojo \
        .github/workflows/comprehensive-tests.yml \
        scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_original.mojo into N files (ADR-009)"
gh pr create --title "fix(ci): split test_original.mojo to fix ADR-009 heap corruption"
```

Pre-commit hooks that run: `mojo format`, `validate_test_coverage`, `check-yaml`, `trailing-whitespace`, `end-of-file-fixer`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring the limit | Running >10 tests in one file | Non-deterministic heap corruption crashes CI 13/20 runs | Always split at >10; do not wait for failures |
| Reducing test count by deleting tests | Deleting some tests to stay under the limit | Loses test coverage | Split into parts, never delete tests |
| Assuming CI uses glob patterns for all groups | Expected new `_partN` files to be auto-discovered without checking | Some CI groups (e.g., Core Activations & Types, Core Tensors, Core Utilities) use explicit filename lists, not globs | Always run `grep "test_original_name" .github/workflows/` before assuming glob coverage |
| Keeping original file alongside split files | Left original file in place with split files | Would cause duplicate test execution and still exceed ADR-009 | Delete original entirely; replace completely with part files |
| Sharing struct definitions via import between split files | Tried to import custom struct from part1 in part3 | Mojo test files do not export symbols to other test files | Duplicate custom structs in each split file that needs them |
| Using `_part_1` naming (underscore before number) | Considered underscore-number naming convention | Would sort inconsistently in file listings | Use `_part1`, `_part2` (no underscore before number) |
| Placing ADR-009 comment inside docstring | Put `# ADR-009:` lines inside `"""..."""` | Comments inside string literals are not code comments in Mojo | Place ADR-009 comment block before the docstring at the top of the file |
| Copying all imports to each split file | Each split file had the full import block from original | Unused imports cause compile warnings or errors in Mojo | Trim imports to only what each split file actually uses |
| Using `grep "^fn test_"` to count (no `[a-z]`) | Counted lines matching the basic pattern | The ADR-009 header comment text itself can match `fn test_` | Use `^fn test_[a-z]` to match only real function definitions |
| Trusting issue description for CI group name | Issue said one CI group name | Actual CI group was different (e.g., "Core Utilities" vs "Core NN Modules") | Always grep the actual workflow file to find the real group name |
| Creating `.orig` or `.bak` backup files | Kept backup copies of original file | Pollutes git staging and confuses pre-commit hooks | Delete original cleanly; git history preserves it |
| Using `--label fix` in PR creation | `gh pr create --label "fix"` | Label `fix` does not exist in the repo | Check `gh label list` first or omit `--label` |
| Running `git push` before commit finished | Ran push immediately after `git commit` in background | Push executed before commit was visible in git index | Wait for commit to complete before pushing |
| Running `gh pr create` before push settled | `gh pr create` ran immediately after `git push` | "you must first push the current branch" error | Allow push to propagate; verify with `git status` first |

## Results & Parameters

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file (ADR-009 hard limit) | 10 |
| Target tests per file (headroom) | 8 |
| Naming convention | `test_<original>_partN.mojo` |
| ADR-009 header comment | Required in every split file |
| CI workflow key | `pattern:` field in test group (glob or explicit) |
| Mojo version affected | v0.26.1 (JIT fault in libKGENCompilerRTShared.so) |
| CI failure pattern | Non-deterministic, load-dependent |
| ADR reference | `docs/adr/ADR-009-heap-corruption-workaround.md` |

### ADR-009 Header Template (copy-paste)

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### ADR-009 Compliance Formula

```text
files_needed = ceil(total_tests / 8)  # target <=8 per file
tests_per_file <= 8                   # safety margin below the 10-test limit
```

### Files Commonly Requiring Updates

- `scripts/validate_test_coverage.py` -- exclusion list uses exact filenames
- `.github/workflows/comprehensive-tests.yml` -- check for hardcoded filenames (glob patterns auto-update)
- `tests/shared/README.md` -- if it lists the file explicitly

### Grep Patterns for Verification

```bash
# Count tests accurately (avoids header comment false positives)
grep -c "^fn test_[a-z]" <file>.mojo

# Check CI pattern type
grep -n "test_<name>" .github/workflows/comprehensive-tests.yml

# Verify no remaining reference to old filename in workflow pattern
grep "test_<name>\.mojo" .github/workflows/comprehensive-tests.yml

# Verify coverage script
python scripts/validate_test_coverage.py
```

### Pre-commit Hooks That Validate the Split

- `validate_test_coverage.py` -- detects uncovered `test_*.mojo` files (catches missing workflow update)
- `mojo format` -- ensures new files are properly formatted
- `check-yaml` -- validates workflow YAML syntax
- `trailing-whitespace`, `end-of-file-fixer` -- formatting checks

## Verified On

| Project | Issue | PR | File Split | CI Pattern | Notes |
|---------|-------|-----|------------|------------|-------|
| ProjectOdyssey | #3397 | #4094 | test_assertions.mojo (61 -> 9 files) | Glob | Partially pre-split; fixed existing over-limit files |
| ProjectOdyssey | #3399 | #4106 | test_elementwise_dispatch.mojo (47 -> 6 files) | Glob | Auto-discovered |
| ProjectOdyssey | #3400 | #4111 | test_activations.mojo (45 -> 6 files) | Explicit | Workflow update required |
| ProjectOdyssey | #3415 | #4159 | test_reduction_forward.mojo -> 4 files | Explicit | Core Tensors group |
| ProjectOdyssey | #3419 | #4175 | test_elementwise_edge_cases.mojo (28 -> 4 files) | Explicit | Core Activations & Types group |
| ProjectOdyssey | #3429 | #4209 | test_activation_funcs.mojo (24 -> 3 files) | Explicit | |
| ProjectOdyssey | #3432 | #4215 | test_logging.mojo (22 -> 3 files) | Glob | Auto-discovered |
| ProjectOdyssey | #3435 | #4220 | test_arithmetic_backward.mojo (23 -> 3 files) | Explicit | |
| ProjectOdyssey | #3445 | #4244 | test_callbacks.mojo (20 -> 3 files) | Glob | validate_test_coverage.py exclusion list updated |
| ProjectOdyssey | #3446 | #4245 | test_fixtures.mojo (20 -> 3 files) | Explicit | Shared Infra group |
| ProjectOdyssey | #3452 | #4263 | test_integration.mojo (19 -> 3 files) | Explicit | Core Utilities group |
| ProjectOdyssey | #3455 | #4276 | test_mobilenetv1_layers.mojo (19 -> 3 files) | Glob | Models group |
| ProjectOdyssey | #3456 | #4277 | test_training_infrastructure.mojo (18 -> 3 files) | Glob | Auto-discovered |
| ProjectOdyssey | #3458 | #4279 | test_googlenet_layers.mojo (18 -> 3 files) | Explicit | Models group |
| ProjectOdyssey | #3462 | -- | test_advanced_activations.mojo (17 -> 3 files) | -- | |
| ProjectOdyssey | #3463 | #4290 | test_optimizer_utils.mojo (16 -> 2 files) | -- | `fn test_main()` does not count |
| ProjectOdyssey | #3466 | #4293 | test_early_stopping.mojo (16 -> 2 files) | Glob | |
| ProjectOdyssey | #3474 | #4312 | test_weighted.mojo (15 -> 2 files) | Glob | Auto-discovered |
| ProjectOdyssey | #3475 | #4316 | test_reduction_edge_cases.mojo (15 -> 2 files) | Explicit | |
| ProjectOdyssey | #3490 | #4352 | test_linear.mojo (14 -> 2 files) | Explicit | Issue named wrong CI group |
| ProjectOdyssey | #3517 | -- | test_no_grad_context.mojo | -- | |
| ProjectOdyssey | #3607 | #4402 | test_mixed_precision.mojo (13 -> 2 files) | Glob | validate_test_coverage.py exclusion list required |
| ProjectOdyssey | #3623 | #4412 | test_gradient_ops.mojo (12 -> 2 files) | Glob | No validate_test_coverage.py changes needed |
| ProjectOdyssey | #3626 | #4417 | test_gradient_validation.mojo (12 -> 2 files) | Explicit | validate_test_coverage.py not needed |
| ProjectOdyssey | #3636 | #4445 | test_cache.mojo (11 -> 2 files) | Glob | Updated inline CI comment |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`
