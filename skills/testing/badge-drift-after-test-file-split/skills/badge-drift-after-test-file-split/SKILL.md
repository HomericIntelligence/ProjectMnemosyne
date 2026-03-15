---
name: badge-drift-after-test-file-split
description: "Ensure test count badge stays accurate when a large test file is split into multiple parts. Use when: a test file has been split into part1/part2/etc. and the badge-check script must count all parts."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | badge-drift-after-test-file-split |
| **Category** | testing |
| **Trigger** | Split large Mojo test file → badge count script may under-count |
| **Outcome** | Unit test added verifying all `*_part*.mojo` files are counted |
| **Issue** | #4192 — follow-up from #3423 (ADR-009 test file split) |

## When to Use

- A test file (e.g. `test_arithmetic_contiguous.mojo`) is split into `test_arithmetic_contiguous_part1.mojo`, `part2`, `part3`, `part4` to work around compiler heap-corruption (ADR-009).
- A badge-check script (`check_test_count_badge.py`) scans the repo for `test_*.mojo` files to compute the badge count.
- You need to verify the script counts each split part as a separate file (glob `test_*.mojo` naturally covers them — no script changes required).
- You want a regression test so future splits don't silently break the badge.

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm glob covers split files (no script changes needed)
python3 scripts/check_test_count_badge.py

# 2. Add regression test (single pytest case)
# See "Test Pattern" section below

# 3. Commit and push
git add tests/scripts/test_check_test_count_badge.py
git commit -m "test(scripts): add split-file coverage for check_test_count_badge.py"
```

### Step 1 — Verify the script already counts split files

Run the existing badge script. Because it globs `test_*.mojo`, all four part files
match by default. No code changes to `check_test_count_badge.py` are needed.

```bash
python3 scripts/check_test_count_badge.py
# Expected: exits 0, badge count includes all 4 split files
```

### Step 2 — Add a targeted unit test

Add a new test section to `tests/scripts/test_check_test_count_badge.py`:

```python
# ---------------------------------------------------------------------------
# Split file name coverage (issue #4192)
# ---------------------------------------------------------------------------


def test_count_test_files_counts_split_files(tmp_path: Path) -> None:
    """Should count all test_arithmetic_contiguous_part*.mojo as separate test files."""
    core = tmp_path / "tests" / "shared" / "core"
    core.mkdir(parents=True)
    for part in range(1, 5):
        (core / f"test_arithmetic_contiguous_part{part}.mojo").write_text("")

    count = count_test_files(tmp_path)
    assert count == 4
```

**Why this works**: `count_test_files` uses `glob("**/test_*.mojo")`, which matches
`test_arithmetic_contiguous_part1.mojo` through `part4.mojo` without any special casing.
The test is a pure regression guard — it would catch any future glob-pattern change that
accidentally excluded split files.

### Step 3 — Confirm existing CI workflow covers the new test

Check that the CI workflow for scripts tests already runs this file:

```bash
grep -r "test_check_test_count_badge" .github/workflows/
```

If not, add the file to the appropriate workflow matrix.

### Step 4 — Commit

```bash
git add tests/scripts/test_check_test_count_badge.py
git commit -m "test(scripts): add split-file coverage for check_test_count_badge.py"
git push -u origin <branch>
gh pr create --title "test(scripts): add split-file coverage for check_test_count_badge.py" \
  --body "Closes #4192"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Modify `check_test_count_badge.py` to special-case `_part` suffix | Adding explicit logic to detect `*_part*.mojo` files | Unnecessary — the existing `glob("**/test_*.mojo")` already matches all part files | Verify the existing glob before writing new script logic |
| Read background task output immediately | Checking task output before the background command finished | Task was still running | Wait for task-completion notification before reading output |

## Results & Parameters

**Repository pattern**: `tests/shared/core/test_arithmetic_contiguous_part{1..4}.mojo`

**Badge script glob** (in `scripts/check_test_count_badge.py`):

```python
EXCLUDE_DIRS = {".pixi", "worktrees", ".git", "build"}

def count_test_files(root: Path) -> int:
    count = 0
    for f in root.rglob("test_*.mojo"):
        if not any(part in EXCLUDE_DIRS for part in f.parts):
            count += 1
    return count
```

**Test file location**: `tests/scripts/test_check_test_count_badge.py`

**Commit type**: `test(scripts):` — no production code changed, only test coverage added.
