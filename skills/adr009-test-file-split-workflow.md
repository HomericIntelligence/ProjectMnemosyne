---
name: adr009-test-file-split-workflow
description: "OBSOLETE — ADR-009 has been fixed. Historical reference for Mojo test file splitting and de-splitting. Use when: understanding existing split files, reversing splits, investigating legacy heap corruption workarounds, auditing for dropped tests, or recovering dropped test implementations from git history."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [adr-009, mojo, test-splitting, obsolete, historical]
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Consolidate all ADR-009 test splitting knowledge into one historical reference |
| **Outcome** | Single skill covering split workflow, CI pattern handling, audit/recovery, and de-split merge — with prominent obsolescence notice |
| **Verification** | unverified (ADR-009 itself is fixed; see ASAN note below) |

## ADR-009 Status: OBSOLETE

> **ADR-009 has been fixed.** The heap corruption bug that motivated splitting test files into <=10 `fn test_` functions per file has been resolved at the compiler/runtime level.
>
> **Do NOT use this skill to implement ADR-009 splitting on new files.**
>
> For debugging Mojo heap corruption or memory safety issues, use **ASAN builds** instead:
> - Build with AddressSanitizer enabled to catch heap corruption at the source
> - ASAN provides precise stack traces pinpointing the actual corruption site
> - File splitting was a workaround, not a fix — ASAN finds the root cause
>
> This skill is preserved for historical reference and for understanding existing split files that have not yet been merged back.

## When to Use

Use this skill ONLY for:

1. Understanding the structure of existing `_partN.mojo` split files
2. Reversing ADR-009 splits by merging `_partN.mojo` files back into unified test files
3. Investigating legacy heap corruption workarounds in the codebase
4. Auditing existing split files to verify no tests were dropped
5. Recovering dropped test implementations from `.DEPRECATED` files or git history
6. Closing stale ADR-009 issues after the bug was fixed

Do NOT use to split new files. File splitting was a workaround — ADR-009 has been fixed.

## Verified Workflow

### Quick Reference

```bash
# Count tests accurately (use [a-z] suffix to avoid counting ADR-009 header lines)
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo

# Check if a CI group uses glob vs explicit filenames
grep -n "test_file" .github/workflows/comprehensive-tests.yml

# Post-split audit: find dropped tests
grep "^fn test_" <file>.DEPRECATED | sed 's/fn //; s/(.*$//' | sort > /tmp/dep.txt
grep -h "^fn test_" tests/path/to/test_<prefix>*.mojo | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt
comm -23 /tmp/dep.txt /tmp/split.txt  # shows dropped tests

# For files deleted without .DEPRECATED (recover from git):
git log --oneline --diff-filter=D -- "tests/**/<file>.mojo"
git show <parent-commit>^:<path>/<file>.mojo | grep "^fn test_"

# After merge, audit for dropped structs (merge scripts have a dedup bug)
for f in $(find tests/ -name "*.mojo"); do
  grep -oP '(?<=var \w+ = )[A-Z]\w+(?=\()' "$f" 2>/dev/null | sort -u | while read s; do
    if ! grep -q "^struct $s" "$f" 2>/dev/null; then
      echo "MISSING: $f uses $s but doesn't define it"
    fi
  done
done

# Check for stale _part imports after merging
grep -rn "from.*_part[0-9]" tests/ --include="*.mojo"
```

### Part A: Splitting Workflow (Historical Reference)

This section documents how splitting was performed when ADR-009 was active. It is preserved
so maintainers can understand existing split files.

#### Step 1: Count tests in the file

```bash
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo
```

Use `^fn test_[a-z]` (not `^fn test_`) to avoid counting ADR-009 header comment lines that
contain `fn test_` text. The issue description's test count should not be trusted — always
grep the actual file.

If count > 10, the file needed splitting. For deep networks (VGG-16 scale, 11+ layers),
the threshold was effectively > 5 due to heavier JIT load per test.

#### Step 2: Plan the split

Divide tests into logical groups by operation type (NOT alphabetically). Target <=8 tests
per file (safety margin below the hard 10-test limit).

```text
files_needed = ceil(total_tests / 8)

Examples:
  11-16 tests -> 2 files (<=8 each)
  17-24 tests -> 3 files (<=8 each)
  25+  tests  -> 4 files (<=7 each)
  47   tests  -> 6 files (8+8+8+8+8+7)
```

Prefer semantic suffix names over generic `_part1`/`_part2` when groupings are clear:
```text
test_extensor_slicing.mojo (19 tests) ->
  test_extensor_slicing_1d.mojo    (8: basic + strided)
  test_extensor_slicing_2d.mojo    (6: multi-dim + batch)
  test_extensor_slicing_edge.mojo  (5: edge cases + copy semantics)
```

#### Step 3: Audit imports before splitting

Check for import gaps in the original file. Mojo sometimes resolved symbols through
transitive or JIT context imports that only manifest as errors when isolated:

```bash
# Find all top-level imports
grep "^from\|^import" tests/path/to/test_file.mojo

# Find symbols actually used
grep -oE "\brandn\b|\bzeros\b|\bones\b|\bfull\b|\bExTensor\b" tests/path/to/test_file.mojo | sort -u
```

Cross-reference: if a symbol appears in usage but NOT in the import line, add it before splitting.
Also check for inline imports inside function bodies — copy these verbatim to the part file that
contains that function.

#### Step 4: Create part files with ADR-009 header

Each new file was required to begin with:

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Each part file was fully self-contained:
- Complete import block (copy from original, trim to only what that file actually uses)
- All helper structs/functions redefined verbatim in each file that uses them (Mojo test files cannot import from sibling test files)
- Its own `fn main() raises:` calling only its subset of tests

**Naming convention**: `test_<original>_part1.mojo`, `test_<original>_part2.mojo`, etc.

#### Step 5: Delete the original file

```bash
git rm tests/path/to/test_original.mojo
```

Do NOT keep the original alongside split files — it causes duplicate test runs.

#### Step 6: Check CI workflow pattern type (critical fork)

```bash
grep -n "test_original_name" .github/workflows/comprehensive-tests.yml
```

**Case A: Glob pattern** (e.g., `test_*.mojo`) — No workflow changes needed. `_partN` files auto-discovered.

**Case B: Explicit filename list** — Must update:

```yaml
# Before:
pattern: "... test_original.mojo ..."

# After:
# ADR-009: test_original.mojo split into N parts (<=8 tests each)
pattern: "... test_original_part1.mojo test_original_part2.mojo test_original_part3.mojo ..."
```

#### Step 7: Update validate_test_coverage.py (independently of CI pattern)

A glob in the CI workflow does NOT mean glob in `validate_test_coverage.py`. Check both:

```bash
grep -n "test_original_name" scripts/validate_test_coverage.py
```

If found in an exclusion list, replace the single entry with entries for each part file.
If the CI group had `continue-on-error: true` as a heap corruption workaround, remove it.

#### Step 8: Verify test counts

```bash
for f in tests/path/test_*_part*.mojo; do
  echo "$f: $(grep -c '^fn test_[a-z]' "$f") tests"
done
# Total must equal original count
```

#### Step 9: Pre-commit validation

```bash
# Run hooks one at a time (pixi run pre-commit does not accept multiple hook names)
pixi run pre-commit run mojo-format --files path/to/part1.mojo path/to/part2.mojo
pixi run pre-commit run validate_test_coverage --files ...
pixi run pre-commit run check-yaml --files .github/workflows/comprehensive-tests.yml
```

Do NOT use `just pre-commit` in worktree shell environments — `just` is not installed there.

### Part B: De-Splitting / Merge-Back Workflow

This is the CURRENT relevant workflow — merging split files back into unified test files
now that ADR-009 is fixed.

#### Step 1: Run a merge script

A merge script handles:
- Combining imports (deduplicating by module name)
- Merging test functions from all part files
- Updating CI workflow patterns

#### Step 2: CRITICAL — Post-Merge Audit for Dropped Structs

**The `_deduplicate_functions()` function in merge scripts assigns ALL struct/alias/var
definitions the name `"<top-level>"`. The deduplication keeps only the FIRST one, silently
dropping all subsequent struct definitions. This causes CI compile failures.**

This is silent data loss — no warning is emitted during the merge.

**Audit checklist after any merge:**

- [ ] Check every merged file that had 2+ struct definitions in any single part file
- [ ] Verify all `comptime` constants were preserved
- [ ] Verify `run_all_tests.mojo` and similar runner files have updated import paths (not still pointing to `_partN` modules)
- [ ] Verify docstrings don't reference `_part` filenames
- [ ] Fix unclosed docstrings (merge script can mangle multi-line docstrings)
- [ ] Search entire codebase for `_part` imports after any file merge

```bash
# Check for stale _part imports in non-test files
grep -rn "from.*_part[0-9]" tests/ --include="*.mojo"
grep -rn "import.*_part[0-9]" tests/ --include="*.mojo"
```

#### Step 3: Restore dropped code from git history

```bash
# Get struct definition from the original part file before the merge
git show <merge-commit>^:tests/path/to/test_foo_part1.mojo | grep -A 30 "struct MissingStruct"
```

Strip from diff format and insert into the merged file.

#### Step 4: Fix additional merge script casualties

```bash
# Check missing comptime constants
git show <merge-commit>^:tests/path/test_foo_part1.mojo | grep "comptime"
grep "comptime" tests/path/test_foo.mojo  # should match
```

#### Step 5: Delete the merge script

```bash
git rm scripts/merge_split_tests.py
```

The merge script serves its one-time purpose and typically has ruff lint violations that fail CI.

#### Step 6: CI workflow patterns after merge

Update CI patterns to use merged filenames. Beware the CI wildcard trap:

`test_initializers_*.mojo` — matches old `_part*.mojo` AND unrelated `_validation.mojo`
`test_initializers*.mojo` — correct (no underscore before wildcard)

#### Step 7: Verify in CI (not locally)

Running `just test-mojo` locally can crash the machine. Use targeted group testing:

```bash
just test-group <group-name>
```

Then push to CI for full validation.

### Part C: Audit and Recovery Workflow

Use when auditing existing split files or recovering dropped tests.

#### Codebase-wide audit

```bash
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then echo "$count $f"; fi
done | sort -rn
```

#### Issue creation (if still needed for legacy tracking)

Run synchronously in batches of <=20. **Never background this loop** — 502 GitHub API errors
cause the script to re-run from index 0, generating duplicate waves:

```python
# Run in explicit index-range batches -- NEVER background this loop
for file_path, test_count, ci_group, run_ids in VIOLATING_FILES[0:20]:
    create_issue(file_path, test_count, ci_group, run_ids)
```

Run: `python3 script.py --start 0 20`, then `--start 20 40`, etc.

#### Post-split audit: find dropped tests

```bash
# From .DEPRECATED file
grep "^fn test_" <file>.DEPRECATED | sed 's/fn //; s/(.*$//' | sort > /tmp/dep.txt
grep -h "^fn test_" tests/path/test_<prefix>*.mojo | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt
comm -23 /tmp/dep.txt /tmp/split.txt

# For files deleted without .DEPRECATED (recover from git):
SPLIT_COMMIT=$(git log --oneline -- "tests/path/to/test_original.mojo" | head -1 | cut -d' ' -f1)
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_"
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep -A 40 "^-fn test_missing_name"
```

#### Comprehensive family audit

```bash
for f in tests/path/to/test_<family>_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

#### Deduplicate issues if duplicates were created

```bash
gh issue list --label "ci-cd" --search "Mojo heap corruption" --state open \
  --limit 200 --json number,title | python3 -c "
import sys, json
from collections import defaultdict
issues = json.load(sys.stdin)
by_title = defaultdict(list)
for i in issues:
    by_title[i['title']].append(i['number'])
to_close = []
for title, nums in sorted(by_title.items()):
    if len(nums) > 1:
        keep = sorted(nums)[0]
        for n in sorted(nums)[1:]:
            to_close.append(n)
            print(f'Close #{n} (keep #{keep}): {title[:60]}')
print('Close IDs:', ' '.join(str(n) for n in to_close))
"
```

### Key Patterns

**Pattern: False completion in commit messages** — Split commit messages often say "All N tests
preserved" even when they aren't. Always verify with `comm -23` rather than trusting commit messages.

**Pattern: Tests present under different names** — `test_operators_preserve_shape` and
`test_unary_ops_preserve_shape` are different tests despite similar intent. The comm-based
diff catches this correctly.

**Pattern: Split files may exceed deprecated count** — Later commits often add new tests to
split files. This is expected and correct. The audit only checks for tests that exist in
deprecated but not in any split file.

**Pattern: Wildcard CI patterns absorb new split files** — CI workflows using `test_extensor_*.mojo`
wildcards automatically pick up new split files. Only explicit filename lists need updating.

**Pattern: Stale issue plans** — Issue plans generated by planning agents reflect a point-in-time
snapshot. Between plan generation and implementation, other PRs may have already fixed some issues.
Always re-audit current state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring the limit | Running >10 tests in one file | Non-deterministic heap corruption crashes CI 13/20 runs | Always split at >10; do not wait for failures (historical — ADR-009 now fixed) |
| Reducing test count by deleting tests | Deleting some tests to stay under the limit | Loses test coverage | Split into parts, never delete tests |
| Assuming CI uses glob for all groups | Expected new `_partN` files to be auto-discovered without checking | Some CI groups use explicit filename lists (Core Activations & Types, Core Tensors) | Always `grep "test_original_name" .github/workflows/` before assuming glob coverage |
| Keeping original + adding split files | Left original file in place alongside split files | Doubles test execution, negates the fix | Delete original entirely |
| Sharing struct definitions via import | Tried to import custom struct from part1 in part3 | Mojo test files do not export symbols to other test files | Duplicate custom structs in each split file that needs them |
| Using `_part_1` naming (underscore before number) | Considered `test_foo_part_1.mojo` naming | Sorts inconsistently in file listings | Use `_part1`, `_part2` (no underscore before number) |
| Placing ADR-009 comment inside docstring | Put `# ADR-009:` lines inside `"""..."""` | Comments inside string literals are not code comments in Mojo | Place ADR-009 comment block before the docstring at the top of the file |
| Copying all imports to each split file | Each split file had the full import block from original | Unused imports cause compile warnings or errors in Mojo | Trim imports to only what each split file actually uses |
| Using `grep "^fn test_"` to count (no `[a-z]`) | Counted lines matching the basic pattern | The ADR-009 header comment text itself can match `fn test_` | Use `^fn test_[a-z]` to match only real function definitions |
| Trusting issue description for CI group name | Issue said one CI group name | Actual CI group was different | Always grep the actual workflow file to find the real group name |
| Running `git push` before commit finished | Ran push immediately after `git commit` in background | Push executed before commit was visible in git index | Wait for commit to complete before pushing |
| Running `gh pr create` before push settled | `gh pr create` ran immediately after `git push` | "you must first push the current branch" error | Allow push to propagate; verify with `git status` first |
| Keeping 10 tests per file (at limit) | Set exactly at the ADR-009 limit | Edge cases still triggered corruption | Use <=8 (safety margin); for deep networks use <=5 |
| Using `continue-on-error: true` | Marked CI group as non-fatal | Masked real failures, did not fix root cause | Only use as temporary mitigation, not a fix |
| Trusting issue description test count | Issue said N tests; planned split accordingly | Actual count differed — issue undercounted | Always `grep -c "^fn test_[a-z]"` to get the real count |
| Copy imports verbatim from original | Copied the original import line exactly | Original had latent import gap (e.g. `randn` used but not imported) | Grep actual symbol usage vs imports before splitting |
| Deleting backward tests to fix compile hang | Removed heavyweight tests entirely | Loses backward-pass test coverage | Move to sibling part file with capacity, never delete tests |
| Skipped validate_test_coverage.py check | CI workflow used glob so assumed everything was fine | `validate_test_coverage.py` had a separate exclusion list with original filename hardcoded | Always check both workflow YAML and validate_test_coverage.py independently |
| Multi-hook pre-commit | `pixi run pre-commit run hook1 hook2 --files ...` | pre-commit CLI doesn't accept multiple hook names in one call | Run hooks one at a time |
| `just pre-commit` in worktree | Ran `just pre-commit` to use project's justfile recipe | `just` not installed in worktree shell environment | Use `pixi run pre-commit run` directly in worktrees |
| Background pre-commit | Ran pre-commit in background, checked output file | Output file remained 0 bytes during session | Use foreground for pre-commit hooks |
| Using `--label fix` in PR creation | `gh pr create --label "fix"` | Label `fix` does not exist in the repo | Check `gh label list` first or omit `--label` |
| Background batch script | Used `run_in_background=True` for the 60-file batch issue creation | 502 GitHub API errors caused early exit; task system re-ran from index 0, creating 3 duplicate waves (41 + 64 + 8 duplicates) | Never background a sequential issue-creation loop — run synchronously with explicit `--start N M` index ranges |
| Single large batch | Ran all 115 files in one `--start 0 115` call | Same problem: 502 error mid-run then background re-execution from 0 | Break into batches of <=20 and run each synchronously |
| Fix only the issue-specified file | Addressed only the file named in the issue | That file was already split; sibling files still violated ADR-009 | Always audit ALL files in the family, not just the one named in the issue |
| Trusted commit message | Assumed "All 21 tests preserved" in split commit message was accurate | Commit message was aspirational; audit found 1 dropped test | Always verify with `comm -23` diff, never trust commit message counts |
| Searched only .DEPRECATED files | Looked only for `.DEPRECATED` marker files | Some files were deleted entirely (no `.DEPRECATED`); required `git log --diff-filter=D` | Check both `.DEPRECATED` files AND git-deleted files |
| Assuming plan was current | Implemented the issue plan directly | Earlier PRs had already fixed some issues in the plan | Always re-audit current state; plan may be stale |
| Assumed split was complete | Checked only that original was deleted and new files existed in CI | 3 tests were silently dropped; count 13 != 16 | Always compare `git show <split_commit> \| grep "^-fn test_"` count vs split file count |
| Checked only the primary file | Audited only the issue's specified file | A sibling file in the same CI group still violated ADR-009 | Always audit ALL files in the CI group, not just the issue's primary file |
| Prose docstring as ADR-009 header | Used `"Note: Split from X due to ADR-009"` in docstring | Issue spec requires exact `# ADR-009:` comment block format | Check acceptance criteria for exact header format requirements |
| Trusting merge script dedup for structs | Script used `"<top-level>"` name for ALL struct/alias/var definitions | Only the FIRST struct survives — all subsequent dropped silently | **CRITICAL**: Extract ACTUAL names for struct definitions; never use a generic placeholder |
| Trusting merged files compile | Assumed merge preserved all code blocks | Also dropped `comptime DEFAULT_SEED` and left unclosed docstrings | Always compile-check merged files, don't just count test functions |
| Trusting import paths auto-update | `run_all_tests.mojo` still imported from `_part1` module names | Merge script only updates merged files, not files that import from them | Search entire codebase for `_part` imports after any file merge |
| Running full test suite locally | `just test-mojo` to validate merged files | Crashes the machine due to resource constraints | Use `just test-group` for targeted checks, push to CI for full validation |
| CI pattern `test_initializers_*.mojo` | Wildcard matched old `_part*.mojo` AND `_validation.mojo` | Lost coverage of `test_initializers_validation.mojo` | Use `test_initializers*.mojo` (no underscore before wildcard) |
| Merge script `--dry-run` expecting no side effects | Dry-run wrote to dual-version base files in-place | Script's dual-version handling modified base files | True dry-run needs to skip ALL file writes |

## Results & Parameters

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file (ADR-009 hard limit — historical) | 10 |
| Target tests per file (headroom — historical) | 8 |
| Naming convention | `test_<original>_partN.mojo` |
| ADR-009 header comment | Required in every split file |
| Mojo version affected | v0.26.1 (JIT fault in libKGENCompilerRTShared.so) |
| CI failure pattern | Non-deterministic, load-dependent |
| ADR reference | `docs/adr/ADR-009-heap-corruption-workaround.md` |

### Safe Test Limits by Network Scale (Historical)

| Network Scale | Safe Tests Per File | Notes |
|--------------|--------------------|----|
| Shallow (<=5 layers) | <=10 | Standard ADR-009 limit |
| Medium (6-10 layers) | <=7 | LeNet-5, small ResNets |
| Deep (11+ layers) | <=5 | VGG-16, ResNet-50 |

### De-Split Merge Scale (ProjectOdyssey, 2026-03-27)

```yaml
split_files_merged: 391
groups_created: 132
directories_affected: 22
test_functions_preserved: 2872
net_files_reduced: 259
net_lines_reduced: 20170
```

### Files Damaged by Merge Script Dedup Bug (4 structs across 3 files)

```text
tests/shared/data/transforms/test_pipeline.mojo     — missing StubPipeline (7 references)
tests/shared/core/test_composed_op.mojo              — missing ScaleAdd (10+ references)
tests/shared/core/test_elementwise_dispatch.mojo     — missing IncrementOp + AverageOp
tests/shared/fuzz/test_tensor_fuzz.mojo              — missing comptime DEFAULT_SEED: Int = 42
tests/shared/core/test_elementwise_dispatch.mojo     — unclosed module docstring
tests/shared/data/run_all_tests.mojo                 — stale _part1/_part2 import paths
```

### Issue Creation Audit (2026-03-06, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Files audited | ~650 test files |
| Files violating ADR-009 (>10 tests) | 131 |
| Issues created | 131 file-split + 1 wildcard overlap = **132** |
| Duplicates created (and closed) | 105 |
| Labels applied | `bug`, `testing`, `ci-cd` |
| Issue numbers | #3396--#3640 |

### ADR-009 Header Template (for reference — use on existing files only)

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3483, PR #4330 — split `test_layer_testers.mojo` (14 tests -> 2 files, 8/6); CI glob auto-covered | adr-009-test-file-split |
| ProjectOdyssey | Issue #3503, PR #4381 — split `test_pipeline.mojo` (13 -> 2 files, 8/5); CI glob; no validate_test_coverage.py update needed | adr-009-test-file-split |
| ProjectOdyssey | Issue #3628, PR #4422 — split `test_resnet18_layers.mojo` (12 -> 2 files, 8/4); CI glob | adr-009-test-file-split |
| ProjectOdyssey | Issue #3631, PR #4431 — split `test_data_integrity.mojo` (11 -> 2 files, 8/3); issue described wrong CI group name | adr-009-test-file-split |
| ProjectOdyssey | Issue #3397, PR #4094 — test_assertions.mojo (61 -> 9 files); glob pattern | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3399, PR #4106 — test_elementwise_dispatch.mojo (47 -> 6 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3400, PR #4111 — test_activations.mojo (45 -> 6 files); explicit pattern, workflow update required | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3415, PR #4159 — test_reduction_forward.mojo -> 4 files; Core Tensors group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3419, PR #4175 — test_elementwise_edge_cases.mojo (28 -> 4 files); explicit | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3429, PR #4209 — test_activation_funcs.mojo (24 -> 3 files); explicit | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3432, PR #4215 — test_logging.mojo (22 -> 3 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3435, PR #4220 — test_arithmetic_backward.mojo (23 -> 3 files); explicit | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3445, PR #4244 — test_callbacks.mojo (20 -> 3 files); glob; validate_test_coverage.py exclusion list updated | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3446, PR #4245 — test_fixtures.mojo (20 -> 3 files); explicit; Shared Infra group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3452, PR #4263 — test_integration.mojo (19 -> 3 files); explicit; Core Utilities group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3455, PR #4276 — test_mobilenetv1_layers.mojo (19 -> 3 files); glob; Models group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3456, PR #4277 — test_training_infrastructure.mojo (18 -> 3 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3458, PR #4279 — test_googlenet_layers.mojo (18 -> 3 files); explicit; Models group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3463, PR #4290 — test_optimizer_utils.mojo (16 -> 2 files); `fn test_main()` does not count | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3466, PR #4293 — test_early_stopping.mojo (16 -> 2 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3474, PR #4312 — test_weighted.mojo (15 -> 2 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3475, PR #4316 — test_reduction_edge_cases.mojo (15 -> 2 files); explicit | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3490, PR #4352 — test_linear.mojo (14 -> 2 files); explicit; issue named wrong CI group | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3607, PR #4402 — test_mixed_precision.mojo (13 -> 2 files); glob; validate_test_coverage.py exclusion list required | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3623, PR #4412 — test_gradient_ops.mojo (12 -> 2 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3626, PR #4417 — test_gradient_validation.mojo (12 -> 2 files); explicit | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3636, PR #4445 — test_cache.mojo (11 -> 2 files); glob | adr009-test-file-splitting |
| ProjectOdyssey | Issue #3409, PR #4142 — test_elementwise.mojo (37 -> 5 files); explicit CI filenames | mojo-test-file-split-adr009 |
| ProjectOdyssey | Issue #3424, PR #4189 — test_utility.mojo (31 -> 4 files) | mojo-test-file-split-adr009 |
| ProjectOdyssey | Issue #3438, PR #4223 — test_reduction.mojo (22 -> 3 files) | mojo-test-file-split-adr009 |
| ProjectOdyssey | Issue #3444, PR #4238 — test_backward.mojo (21 -> 3 files); incomplete split found and fixed | mojo-test-file-split-adr009 |
| ProjectOdyssey | Issue #3447 — test_utils.mojo (20 -> 3 files); issue said 18, actual 20 | mojo-test-file-split-adr009 |
| ProjectOdyssey | Issue #3454, PR #4270 — test_comparison_ops.mojo (19 -> 3 files) | mojo-adr009-file-split |
| ProjectOdyssey | Issue #3457, PR #4278 — test_optimizer_base.mojo (18 -> 3 files); glob CI | mojo-adr009-test-split |
| ProjectOdyssey | Issue #3461, PR #4289 — test_normalization.mojo (21 -> 3 files); explicit CI filenames | mojo-adr009-test-split |
| ProjectOdyssey | Issue #3477, PR #4322 — test_conv.mojo (20 -> 3 files); issue undercounted (said 15) | mojo-adr009-test-split |
| ProjectOdyssey | Issue #3496 — test_checkpointing.mojo (13 -> 2 files) | mojo-adr009-test-split |
| ProjectOdyssey | Issue #3498, PR #4373 — test_gradient_checker_meta.mojo (14 -> 2 files) | mojo-adr009-test-split |
| ProjectOdyssey | Issue #3505, PR #4382 — test_datasets.mojo (13 -> 2 files); Data group wildcard | mojo-test-file-adr009-split |
| ProjectOdyssey | Issue #3625, PR #4416 — test_parallel_loader.mojo (12 -> 2 files); Data group wildcard | testing-adr-009-test-file-split |
| ProjectOdyssey | Issue #3635, PR #4444 — test_base.mojo (11 -> 2 files); glob; validate_test_coverage.py updated | mojo-adr009-file-split |
| ProjectOdyssey | ADR-009 codebase-wide audit, issue creation (#3396--#3640), tracking issue #3330 | 131 violations found, 132 issues created; adr009-split-audit |
| ProjectOdyssey | Issue #3476, extensor family audit and CI group creation | Semantic splits and dedicated "Core ExTensor" CI group; adr009-split-audit |
| ProjectOdyssey | Issue #3444, gradient checking split recovery | 3 dropped tests recovered; adr009-split-audit |
| ProjectOdyssey | PR #4877, split completeness audit across all deprecated files | 1 dropped test found and fixed; adr009-split-audit |
| ProjectOdyssey | PR #5130, CI Comprehensive Tests pass | De-split: 391 split files -> 132 unified; 4 structs recovered from dedup bug; testing-desplit-adr009-merge-workflow |
| ProjectOdyssey | CI group splitting: Core Utilities (71 files) -> 8 groups (A-H) | adr009-ci-pattern-updates |
| ProjectOdyssey | ADR-009 rmsprop split; glob pattern auto-discovered new files | adr009-ci-pattern-updates |
