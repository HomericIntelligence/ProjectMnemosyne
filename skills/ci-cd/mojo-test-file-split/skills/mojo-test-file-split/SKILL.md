---
name: mojo-test-file-split
description: "Split large Mojo test files exceeding ADR-009 fn test_ function limits to prevent heap corruption in CI. Use when: a test file has >10 fn test_ functions causing intermittent libKGENCompilerRTShared.so JIT faults."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Mojo v0.26.1 triggers heap corruption (`libKGENCompilerRTShared.so` JIT fault) when a test file exceeds ~10 `fn test_` functions under CI load |
| **Solution** | Split large test files into parts of ≤8–10 tests each, add ADR-009 header, update CI workflow patterns |
| **ADR Reference** | ADR-009 in `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **CI Failure Rate** | ~65% (13/20 runs) before fix; 0% after split |

## When to Use

- A `test_*.mojo` file contains more than 10 `fn test_` functions
- CI shows intermittent failures on a specific test group with `libKGENCompilerRTShared.so` in the error
- New test file is being created and will exceed 10 tests — split proactively
- ADR-009 compliance audit identifies over-limit files

## Verified Workflow

### 1. Count tests in the file

```bash
grep -c "^fn test_[a-z]" tests/shared/core/test_elementwise.mojo
# 37 — exceeds the ≤10 limit
```

Use `^fn test_[a-z]` (not `^fn test_`) to avoid counting ADR-009 header comment lines that
contain `fn test_` text at line start. Also: never trust the issue description's test count —
always grep the actual file.

### 2. Plan the split

Group tests by logical topic (e.g., by function category):

```
Part 1: abs, sign (5 tests)
Part 2: exp, log (8 tests)
Part 3: log10, log2, sqrt (8 tests)
Part 4: sin, cos (6 tests)
Part 5: clip, rounding, logical (10 tests)
```

Target: ≤8 tests per file for safety margin; hard limit is ≤10.

### 3. Create part files with ADR-009 header

Each new file **must** start with:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_elementwise.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Tests for elementwise operations - Part N: <topic>.
...
"""
```

Copy all imports verbatim into each part file (Mojo has no shared include).

Each part file needs its own `fn main() raises:` that calls only the tests in that file.

### 4. Delete the original file

```bash
rm tests/shared/core/test_elementwise.mojo
```

The `validate_test_coverage.py` script will fail if the original file still exists but is not referenced in the CI workflow, so deletion is required.

### 5. Check CI workflow pattern and validate_test_coverage.py

First, check if the CI group uses a **glob** or an **explicit filename list**:

```bash
grep -n "<original_filename>" .github/workflows/comprehensive-tests.yml
```

- **Glob pattern** (e.g., `training/test_*.mojo`): new `_part1/2` files are picked up automatically
  — no workflow changes needed.
- **Explicit filename list**: replace the original filename with all part filenames.

Then check `scripts/validate_test_coverage.py` for direct filename references:

```bash
grep "<original_filename>" scripts/validate_test_coverage.py
```

- If found: replace the single entry with entries for each part file (1-for-N replacement)
- If not found (uses glob patterns): no changes needed

**Important**: A glob in the CI workflow does NOT mean `validate_test_coverage.py` also uses globs.
Always check both files independently.

```yaml
# If explicit list in comprehensive-tests.yml:
# Before
pattern: "... test_elementwise.mojo ..."

# After
pattern: "... test_elementwise_part1.mojo test_elementwise_part2.mojo ..."
```

### 6. Verify counts

```bash
for f in tests/shared/core/test_elementwise_part*.mojo; do
  count=$(grep -c "^fn test_" "$f")
  echo "$(basename $f): $count tests"
done
```

All counts must be ≤10.

### 7. Commit and PR

```bash
git add .github/workflows/comprehensive-tests.yml \
        tests/shared/core/test_elementwise.mojo \  # deleted
        tests/shared/core/test_elementwise_part*.mojo
git commit -m "fix(ci): split test_elementwise.mojo into N files per ADR-009"
git push -u origin <branch>
gh pr create --title "fix(ci): split <file> per ADR-009" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Leave original file | Keep `test_elementwise.mojo` and just add it to the CI pattern alongside parts | `validate_test_coverage.py` reports original as "uncovered" because it's no longer in the pattern | Always delete the original — the coverage validator discovers all `test_*.mojo` files on disk |
| Shared imports via include | Extract common imports to a shared header file | Mojo v0.26.1 has no `#include` mechanism; each file must have its own full import block | Copy imports verbatim into every part file |
| Fewer, larger parts | Split into 3 files of ~12 tests each | Still exceeds the ≤10 limit and can still trigger heap corruption | Target ≤8 per file for safety margin; hard stop at 10 |
| Label the PR | `gh pr create --label fix` | Label `fix` does not exist in the target repo | Check available labels with `gh label list` before using `--label` |
| Trust issue description for test count | Used count from issue body directly (said 25) | Actual count was 31 — off by 6 | Always grep `^fn test_[a-z]` to get the real count; issue descriptions are often approximate |
| Target ≤8 only for the last split file | Initially gave last part 10 tests | Exceeded ≤8 target from issue requirements | Plan all splits upfront so each file lands ≤8 not just ≤10 |
| Skipped validate_test_coverage.py check | CI workflow used glob `training/test_*.mojo` so assumed no other files needed updating | `validate_test_coverage.py` had a separate exclusion list with the original filename hardcoded | Always grep the original filename in `validate_test_coverage.py` even when the CI workflow uses globs — glob in workflow ≠ glob everywhere |

## Results & Parameters

### Test count distribution (example: 37 tests → 5 files)

```
test_elementwise_part1.mojo:  5 tests  (abs, sign)
test_elementwise_part2.mojo:  8 tests  (exp, log)
test_elementwise_part3.mojo:  8 tests  (log10, log2, sqrt)
test_elementwise_part4.mojo:  6 tests  (sin, cos)
test_elementwise_part5.mojo: 10 tests  (clip, rounding, logical)
Total: 37 tests preserved
```

### Pre-commit hooks that run

- `mojo format` — auto-formats all new part files (passes without manual intervention)
- `validate_test_coverage.py` — confirms all new files appear in CI workflow pattern
- `check-yaml` — validates the updated workflow YAML

### CI impact

- Before: `Core Elementwise` group failed 13/20 runs (~65% failure rate)
- After: All 5 part files run in the same CI group; heap corruption eliminated
- CI group name unchanged — only the `pattern:` field updated

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3409, PR #4142 — split `test_elementwise.mojo` (37 tests → 5 files) | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3424, PR #4189 — split `test_utility.mojo` (31 tests → 4 files) | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3496, PR #4372 — split `test_checkpointing.mojo` (13 tests → 2 files, 8/5); CI glob auto-covered; `validate_test_coverage.py` had explicit filename ref requiring 1-for-2 update | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3509, PR #4387 — split `test_file_dataset.mojo` (13 tests → 2 files, 7/6); CI `datasets/test_*.mojo` glob auto-covered; `validate_test_coverage.py` had no explicit ref — no changes needed | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3549, PR #4400 — split `test_progress_bar.mojo` (22 tests → 3 files, 8/8/6); CI `utils/test_*.mojo` glob auto-covered; `validate_test_coverage.py` had no explicit ref — no changes needed | [notes.md](../../references/notes.md) |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`, issues #2942, #3397
