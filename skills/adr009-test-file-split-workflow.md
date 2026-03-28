---
name: adr009-test-file-split-workflow
description: "Use when: (1) a Mojo test file has >10 fn test_ functions causing intermittent
  CI heap corruption crashes, (2) CI shows libKGENCompilerRTShared.so JIT fault or non-deterministic
  failures in a test group, (3) implementing ADR-009 compliance for a test file, (4) a CI group
  uses explicit filename lists requiring workflow update after split, (5) validate-test-coverage
  pre-commit hook fails because new split files are not in the workflow, (6) a test file takes
  >120s to compile due to heavyweight backward passes, (7) a new large test file is being added
  proactively."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - adr-009
  - mojo
  - heap-corruption
  - test-splitting
  - ci
  - jit
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 has a JIT heap corruption bug (`libKGENCompilerRTShared.so`) triggered when too many `fn test_` functions are compiled in a single file |
| **Symptom** | Non-deterministic CI failures (~65% failure rate, e.g. 13/20 runs), or deterministic crash at Nth sequential call for deep networks |
| **Root Cause** | Cumulative JIT memory from sequential test function compilations exceeds heap capacity |
| **Fix** | ADR-009: split test files so each has <=10 `fn test_` functions (target <=8 for safety) |
| **ADR** | `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **Deep Networks** | VGG-16 scale (11+ layers): use <=5 tests per file; medium (6-10 layers): <=7 |
| **Effort** | ~15-20 minutes per file |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` crashes in a test group (no code changes)
- A CI test group fails non-deterministically — not always the same test, just the same group
- CI failure rate across recent runs is high (e.g., 13/20) with no single reproducible root cause
- ADR-009 compliance audit flags a file as exceeding the limit
- Issue title contains "ADR-009" and involves splitting a test file
- A CI group has `continue-on-error: true` as a heap corruption workaround
- The `validate-test-coverage` pre-commit hook fails because new `test_*.mojo` files are not listed in the CI workflow
- `grep "test_<filename>.mojo" .github/workflows/*.yml` returns a match in an explicit filename list
- A test file takes >120s to compile (heavyweight backward passes, large parametric types)
- A new large test file is being added with 10+ tests (proactive split)

**CI pattern note**: Some CI groups use a glob (`test_*.mojo`) that auto-discovers `_partN` files. Others use explicit space-separated filenames that must be updated manually. Always check which pattern applies before assuming no CI changes are needed.

## Verified Workflow

### Quick Reference

```bash
# 1. Count tests accurately (use [a-z] suffix to avoid counting ADR-009 header lines)
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo

# 2. Check CI pattern type (glob vs explicit)
grep -n "test_file" .github/workflows/comprehensive-tests.yml

# 3. Check validate_test_coverage.py independently
grep -n "test_file" scripts/validate_test_coverage.py

# 4. Create part files (target <=8 tests each, ADR-009 header required in each)
# 5. Delete original
git rm tests/path/to/test_file.mojo

# 6. If explicit CI pattern: update workflow; if glob: no changes needed
# 7. Verify counts
for f in tests/path/to/test_file_part*.mojo; do
  echo "$f: $(grep -c "^fn test_[a-z]" "$f") tests"
done

# 8. Commit
git add tests/path/to/test_file_part*.mojo tests/path/to/test_file.mojo \
        .github/workflows/comprehensive-tests.yml \
        scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_file.mojo into N files (ADR-009)"
```

### Step 1: Count tests in the file

```bash
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo
```

Use `^fn test_[a-z]` (not `^fn test_`) to avoid counting ADR-009 header comment lines that contain `fn test_` text. Never trust the issue description's test count — always grep the actual file.

If count > 10, proceed with split. For deep networks (VGG-16 scale), split if count > 5.

### Step 2: Plan the split

Divide tests into logical groups by operation type (NOT alphabetically). Target <=8 tests per file (safety margin below the hard 10-test limit).

```text
files_needed = ceil(total_tests / 8)

Examples:
  11-16 tests -> 2 files (<=8 each)
  17-24 tests -> 3 files (<=8 each)
  25+ tests   -> 4 files (<=7 each)
  47 tests    -> 6 files (8+8+8+8+8+7)
```

Prefer semantic suffix names over generic `_part1`/`_part2` when possible:
```text
test_extensor_slicing.mojo (19 tests) ->
  test_extensor_slicing_1d.mojo    (8: basic + strided)
  test_extensor_slicing_2d.mojo    (6: multi-dim + batch)
  test_extensor_slicing_edge.mojo  (5: edge cases + copy semantics)
```

### Step 3: Audit imports before splitting

Before creating split files, check for import gaps in the original file. Mojo sometimes resolves symbols through transitive or JIT context imports that only manifest as errors when the file is isolated.

```bash
# Find all top-level imports
grep "^from\|^import" tests/path/to/test_file.mojo

# Find symbols actually used
grep -oE "\brandn\b|\bzeros\b|\bones\b|\bfull\b|\bExTensor\b" tests/path/to/test_file.mojo | sort -u
```

Cross-reference: if a symbol appears in usage but NOT in the import line, add it before creating split files.

Also check for inline imports inside function bodies — copy these verbatim into the part file that contains that function. Do NOT hoist them to top level unless used by multiple tests in the same part.

### Step 4: Create part files with ADR-009 header

Each new file MUST begin with this header comment:

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Each part file must be fully self-contained:
- Complete import block (copy from original, trim to only what that file actually uses)
- All helper structs/functions redefined verbatim in each file that uses them (Mojo test files cannot import from sibling test files)
- Its own `fn main() raises:` calling only its subset of tests (update the final count in the print)

**Naming convention**: `test_<original>_part1.mojo`, `test_<original>_part2.mojo`, etc.

### Step 5: Delete the original file

```bash
git rm tests/path/to/test_original.mojo
```

Do NOT keep the original — it will cause duplicate test runs and still trigger heap corruption.

### Step 6: Check CI workflow pattern type

This is the critical fork. Check whether the CI group uses a glob or explicit filenames:

```bash
grep -n "test_original_name" .github/workflows/comprehensive-tests.yml
```

#### Case A: Glob pattern (e.g., `test_*.mojo`)

No workflow changes needed. New `_partN` files are auto-discovered by the glob. Skip to Step 7.

#### Case B: Explicit filename list

The `pattern:` field lists filenames by name (e.g., `"test_a.mojo test_b.mojo"`). You MUST update the workflow:

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
# Should show only part files in pattern: line
```

### Step 7: Update validate_test_coverage.py (independently of CI pattern)

**Important**: A glob in the CI workflow does NOT mean glob in `validate_test_coverage.py`. Check both independently.

```bash
grep -n "test_original_name" scripts/validate_test_coverage.py
```

If found (e.g., in an exclusion list), replace the single entry with entries for each part file:

```python
# Before
"tests/path/to/test_file.mojo",

# After
"tests/path/to/test_file_part1.mojo",
"tests/path/to/test_file_part2.mojo",
```

If the CI group had `continue-on-error: true` as a heap corruption workaround, remove it.

### Step 8: Verify test counts and total preservation

```bash
# Verify no file exceeds limit
for f in tests/path/test_*_part*.mojo; do
  echo "$f: $(grep -c '^fn test_[a-z]' "$f") tests"
done

# Total must equal original count
grep -c "^fn test_[a-z]" tests/path/test_*_part*.mojo
```

### Step 9: Run pre-commit validation

```bash
# Run hooks one at a time (pixi run pre-commit does not accept multiple hook names)
pixi run pre-commit run mojo-format --files path/to/part1.mojo path/to/part2.mojo
pixi run pre-commit run validate_test_coverage --files ...
pixi run pre-commit run check-yaml --files .github/workflows/comprehensive-tests.yml
# OR run all:
python scripts/validate_test_coverage.py
```

**Do NOT** use `just pre-commit` in worktree shell environments — `just` is not installed there. Use `pixi run pre-commit run` directly.

### Step 10: Commit and PR

```bash
git add tests/path/to/test_*_part*.mojo \
        tests/path/to/test_original.mojo \
        .github/workflows/comprehensive-tests.yml \
        scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_<name>.mojo into N files per ADR-009"
gh pr create --title "fix(ci): split test_<name>.mojo to fix ADR-009 heap corruption"
```

### Compile Hang Variant

When a test file compiles but hangs (>120s) rather than crashing, the cause is usually heavyweight backward-pass tests compiled together with forward-pass tests. Instead of creating new part files, check if an existing sibling part file has capacity:

```bash
for f in tests/models/test_<name>_part*.mojo; do
  echo "$f: $(grep -c '^fn test_[a-z]' "$f")"
done
```

Move backward-pass tests to a sibling with fewer than 8 tests. Avoid creating unnecessary new files.

### ADR-009 Header Template (copy-paste)

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring the limit | Running >10 tests in one file | Non-deterministic heap corruption crashes CI 13/20 runs | Always split at >10; do not wait for failures |
| Reducing test count by deleting tests | Deleting some tests to stay under the limit | Loses test coverage | Split into parts, never delete tests |
| Assuming CI uses glob for all groups | Expected new `_partN` files to be auto-discovered without checking | Some CI groups (e.g., Core Activations & Types, Core Tensors) use explicit filename lists | Always `grep "test_original_name" .github/workflows/` before assuming glob coverage |
| Keeping original + adding split files | Left original file in place alongside split files | Doubles test execution, negates the fix, `validate_test_coverage.py` reports original as uncovered | Delete original entirely; replace completely with part files |
| Sharing struct definitions via import | Tried to import custom struct from part1 in part3 | Mojo test files do not export symbols to other test files | Duplicate custom structs in each split file that needs them |
| Using `_part_1` naming (underscore before number) | Considered `test_foo_part_1.mojo` naming | Sorts inconsistently in file listings | Use `_part1`, `_part2` (no underscore before number) |
| Placing ADR-009 comment inside docstring | Put `# ADR-009:` lines inside `"""..."""` | Comments inside string literals are not code comments in Mojo | Place ADR-009 comment block before the docstring at the top of the file |
| Copying all imports to each split file | Each split file had the full import block from original | Unused imports cause compile warnings or errors in Mojo | Trim imports to only what each split file actually uses |
| Using `grep "^fn test_"` to count (no `[a-z]`) | Counted lines matching the basic pattern | The ADR-009 header comment text itself can match `fn test_` | Use `^fn test_[a-z]` to match only real function definitions |
| Trusting issue description for CI group name | Issue said one CI group name | Actual CI group was different | Always grep the actual workflow file to find the real group name |
| Creating `.orig` or `.bak` backup files | Kept backup copies of original file | Pollutes git staging and confuses pre-commit hooks | Delete original cleanly; git history preserves it |
| Running `git push` before commit finished | Ran push immediately after `git commit` in background | Push executed before commit was visible in git index | Wait for commit to complete before pushing |
| Running `gh pr create` before push settled | `gh pr create` ran immediately after `git push` | "you must first push the current branch" error | Allow push to propagate; verify with `git status` first |
| Keeping 10 tests per file (at limit) | Set exactly at the ADR-009 limit | Edge cases still triggered corruption | Use <=8 (safety margin); for deep networks use <=5 |
| Using `continue-on-error: true` | Marked CI group as non-fatal | Masked real failures, did not fix root cause | Only use as temporary mitigation, not a fix |
| Trusting issue description test count | Issue said N tests; planned split accordingly | Actual count differed — issue undercounted | Always `grep -c "^fn test_[a-z]"` to get the real count |
| Copy imports verbatim from original | Copied the original import line exactly | Original had latent import gap (e.g. `randn` used but not imported) — Mojo resolved it through transitive imports | Grep actual symbol usage vs imports before splitting |
| Deleting backward tests to fix compile hang | Removed heavyweight tests entirely | Loses backward-pass test coverage | Move to sibling part file with capacity, never delete tests |
| Creating new part file for overflow | Created brand new file when sibling had capacity | Unnecessary fragmentation | Check existing sibling capacity first |
| Skipped validate_test_coverage.py check | CI workflow used glob so assumed everything was fine | `validate_test_coverage.py` had a separate exclusion list with original filename hardcoded | Always check both workflow YAML and validate_test_coverage.py independently |
| Multi-hook pre-commit | `pixi run pre-commit run hook1 hook2 --files ...` | pre-commit CLI doesn't accept multiple hook names in one call | Run hooks one at a time |
| `just pre-commit` in worktree | Ran `just pre-commit` to use project's justfile recipe | `just` not installed in worktree shell environment | Use `pixi run pre-commit run` directly in worktrees |
| Background pre-commit | Ran pre-commit in background, checked output file | Output file remained 0 bytes during session (task still running) | Use foreground for pre-commit hooks |
| Using `--label fix` in PR creation | `gh pr create --label "fix"` | Label `fix` does not exist in the repo | Check `gh label list` first or omit `--label` |

## Results & Parameters

### Safe Test Limits by Network Scale

| Network Scale | Safe Tests Per File | Notes |
|--------------|--------------------|----|
| Shallow (<=5 layers) | <=10 | Standard ADR-009 limit |
| Medium (6-10 layers) | <=7 | LeNet-5, small ResNets |
| Deep (11+ layers) | <=5 | VGG-16, ResNet-50 |

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file (ADR-009 hard limit) | 10 |
| Target tests per file (headroom) | 8 |
| Naming convention | `test_<original>_partN.mojo` |
| ADR-009 header comment | Required in every split file |
| Mojo version affected | v0.26.1 (JIT fault in libKGENCompilerRTShared.so) |
| CI failure pattern | Non-deterministic, load-dependent |
| ADR reference | `docs/adr/ADR-009-heap-corruption-workaround.md` |

### Commit Message Template

```text
fix(ci): split test_<name>.mojo into N files (ADR-009)

Split N-test file into part1 (X tests) and part2 (Y tests) to stay
within the ADR-009 limit of <=10 fn test_ functions per file, fixing
intermittent heap corruption crashes in the <CI Group> CI group.

All N original test cases are preserved. Each new file includes the
ADR-009 header comment. The CI workflow pattern <pattern>
automatically picks up both new files without changes.

Closes #<issue-number>
```

### Files Commonly Requiring Updates

- `scripts/validate_test_coverage.py` — exclusion list uses exact filenames
- `.github/workflows/comprehensive-tests.yml` — check for hardcoded filenames (glob patterns auto-update)
- `tests/shared/README.md` — if it lists the file explicitly

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3483, PR #4330 — split `test_layer_testers.mojo` (14 tests -> 2 files, 8/6); CI glob auto-covered | adr-009-test-file-split.md |
| ProjectOdyssey | Issue #3503, PR #4381 — split `test_pipeline.mojo` (13 tests -> 2 files, 8/5); CI glob auto-covered; no validate_test_coverage.py update needed | adr-009-test-file-split.md |
| ProjectOdyssey | Issue #3628, PR #4422 — split `test_resnet18_layers.mojo` (12 tests -> 2 files, 8/4); CI glob auto-covered | adr-009-test-file-split.md |
| ProjectOdyssey | Issue #3631, PR #4431 — split `test_data_integrity.mojo` (11 tests -> 2 files, 8/3); issue described wrong CI group name — always verify from workflow file | adr-009-test-file-split.md |
| ProjectOdyssey | Issue #3397, PR #4094 — test_assertions.mojo (61 -> 9 files); glob pattern | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3399, PR #4106 — test_elementwise_dispatch.mojo (47 -> 6 files); glob auto-discovered | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3400, PR #4111 — test_activations.mojo (45 -> 6 files); explicit pattern, workflow update required | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3415, PR #4159 — test_reduction_forward.mojo -> 4 files; Core Tensors group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3419, PR #4175 — test_elementwise_edge_cases.mojo (28 -> 4 files); explicit pattern | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3429, PR #4209 — test_activation_funcs.mojo (24 -> 3 files); explicit pattern | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3432, PR #4215 — test_logging.mojo (22 -> 3 files); glob auto-discovered | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3435, PR #4220 — test_arithmetic_backward.mojo (23 -> 3 files); explicit pattern | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3445, PR #4244 — test_callbacks.mojo (20 -> 3 files); glob; validate_test_coverage.py exclusion list updated | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3446, PR #4245 — test_fixtures.mojo (20 -> 3 files); explicit; Shared Infra group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3452, PR #4263 — test_integration.mojo (19 -> 3 files); explicit; Core Utilities group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3455, PR #4276 — test_mobilenetv1_layers.mojo (19 -> 3 files); glob; Models group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3456, PR #4277 — test_training_infrastructure.mojo (18 -> 3 files); glob | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3458, PR #4279 — test_googlenet_layers.mojo (18 -> 3 files); explicit; Models group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3463, PR #4290 — test_optimizer_utils.mojo (16 -> 2 files); `fn test_main()` does not count | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3466, PR #4293 — test_early_stopping.mojo (16 -> 2 files); glob | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3474, PR #4312 — test_weighted.mojo (15 -> 2 files); glob | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3475, PR #4316 — test_reduction_edge_cases.mojo (15 -> 2 files); explicit | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3490, PR #4352 — test_linear.mojo (14 -> 2 files); explicit; issue named wrong CI group | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3607, PR #4402 — test_mixed_precision.mojo (13 -> 2 files); glob; validate_test_coverage.py exclusion list required | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3623, PR #4412 — test_gradient_ops.mojo (12 -> 2 files); glob; no validate_test_coverage.py changes needed | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3626, PR #4417 — test_gradient_validation.mojo (12 -> 2 files); explicit | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3636, PR #4445 — test_cache.mojo (11 -> 2 files); glob; updated inline CI comment | adr009-test-file-splitting.md |
| ProjectOdyssey | Issue #3409, PR #4142 — test_elementwise.mojo (37 -> 5 files); explicit CI filenames | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3424, PR #4189 — test_utility.mojo (31 -> 4 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3438, PR #4223 — test_reduction.mojo (22 -> 3 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3444, PR #4238 — test_backward.mojo (21 -> 3 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3447 — test_utils.mojo (20 -> 3 files); issue said 18, actual 20 | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3454, PR #4270 — test_comparison_ops.mojo (19 -> 3 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3457, PR #4278 — test_optimizer_base.mojo (18 -> 3 files); glob CI | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3461, PR #4289 — test_normalization.mojo (21 -> 3 files); explicit CI filenames | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3477, PR #4322 — test_conv.mojo (20 -> 3 files); issue undercounted (said 15) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3496, PR #4372 — test_checkpointing.mojo (13 -> 2 files); validate_test_coverage.py had explicit ref | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3498, PR #4373 — test_gradient_checker_meta.mojo (14 -> 2 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3509, PR #4387 — test_file_dataset.mojo (13 -> 2 files); glob auto-covered | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3549, PR #4400 — test_progress_bar.mojo (22 -> 3 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3635, PR #4444 — test_base.mojo (11 -> 2 files) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | PR — test_vgg16_e2e.mojo (10 -> 2 files of 5); deep network scale applied | mojo-test-file-split-adr009.md |
| ProjectOdyssey | PR — test_mobilenetv1_e2e.mojo; import gap found (randn missing from imports) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | PR — test_alexnet_layers_part4.mojo; backward tests moved to part5 (compile hang variant) | mojo-test-file-split-adr009.md |
| ProjectOdyssey | Issue #3427, PR #4201 | split-test-file-adr009.md |
| ProjectOdyssey | Issue #3625, PR #4416 — test_parallel_loader.mojo (12 -> 2 files); Data group wildcard; all pre-commit hooks passed | testing-adr-009-test-file-split.md |
