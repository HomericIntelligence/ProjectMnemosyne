---
name: split-file-group-tracking
description: 'TRIGGER CONDITIONS: Use when adding coverage tracking for _partN.mojo
  test files split from a single logical test, or when validate_test_coverage.py needs
  to group part files by base name using regex.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# split-file-group-tracking

How to extend a test coverage validator to track split test files (e.g., `test_foo_part1.mojo`,
`test_foo_part2.mojo`) as a single logical group, using a regex-based grouping function and
optional report sections.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Add `group_split_files()` and `check_stale_patterns()` to `validate_test_coverage.py` (issue #4109) |
| Outcome | Success — 10 new unit tests added, all 23 tests passing, script exits 0 on live repo |

## When to Use

- You need to group `_partN.mojo` files in a coverage report so that split files count as one
  logical test rather than N separate entries
- An existing test file imports functions that do not yet exist in the script under test
  (pre-existing TDD contract)
- You are extending a coverage script with new optional report sections while preserving
  backwards compatibility for callers that do not pass the new parameter

## Verified Workflow

### Step 1 — Read both the script and its test file first

Before writing any code, read both files:

1. `<project-root>/scripts/validate_test_coverage.py` — understand existing functions,
   imports, and `main()` structure
2. `<project-root>/tests/scripts/test_validate_test_coverage.py` — look at **every import**
   at the top of the file

The test file imports define the full API contract you must implement. In this session the
test file already imported `check_stale_patterns` and `group_split_files` — functions that
did not yet exist in the script. This caused an `ImportError` at collection time, failing
all tests before any ran.

### Step 2 — Implement `group_split_files()`

```python
import re
from pathlib import Path
from typing import Dict, List

_PART_RE = re.compile(r"^(.+)_part(\d+)\.mojo$")

def group_split_files(test_files: List[Path]) -> Dict[str, List[Path]]:
    """Group test_*_partN.mojo files by their logical base name.

    Returns a dict mapping base key -> sorted list of part paths.
    Only entries with 2+ parts are included.
    """
    groups: Dict[str, List[Path]] = {}
    for f in test_files:
        m = _PART_RE.match(f.name)
        if m:
            key = str(f.parent / m.group(1))
            groups.setdefault(key, []).append(f)
    return {k: sorted(v) for k, v in groups.items() if len(v) >= 2}
```

Key design choices:

- **Path-stable key**: `str(f.parent / m.group(1))` uses the full parent path so files in
  different directories never collide even if they share a base name.
- **Sort after grouping**: `sorted(v)` gives deterministic part order for report output.
- **Filter singles**: Only groups with 2+ parts are returned — a lone `_part1.mojo` with no
  `_part2.mojo` is not a true split file.

### Step 3 — Implement `check_stale_patterns()`

```python
def check_stale_patterns(
    ci_groups: Dict[str, str],
    root_dir: Path,
) -> List[str]:
    """Return CI group names whose glob pattern matches zero files.

    ci_groups maps group name -> glob pattern relative to root_dir.
    """
    stale = []
    for name, pattern in ci_groups.items():
        matched = list(root_dir.glob(pattern))
        if not matched:
            stale.append(name)
    return sorted(stale)
```

### Step 4 — Add an optional `split_groups` param to `generate_report()`

Preserve backwards compatibility by making the new param optional:

```python
def generate_report(
    ...,
    split_groups: Optional[Dict[str, List[Path]]] = None,
) -> str:
    ...
    if split_groups:
        lines.append("\n## Split File Groups\n")
        for key, parts in sorted(split_groups.items()):
            lines.append(f"- {key}: {len(parts)} parts")
            for p in parts:
                lines.append(f"  - {p.name}")
    return "\n".join(lines)
```

### Step 5 — Wire into `main()`

```python
def main() -> int:
    ...
    split_groups = group_split_files(test_files)
    report = generate_report(..., split_groups=split_groups)
    ...
```

### Step 6 — Write unit tests for `group_split_files()`

Use `tmp_path` to create real file paths (no disk I/O needed — the function only inspects
`Path.name`):

```python
class TestGroupSplitFiles:
    def test_groups_two_parts(self, tmp_path: Path) -> None:
        files = [tmp_path / "test_foo_part1.mojo", tmp_path / "test_foo_part2.mojo"]
        result = group_split_files(files)
        key = str(tmp_path / "test_foo")
        assert key in result
        assert result[key] == sorted(files)

    def test_ignores_non_part_files(self, tmp_path: Path) -> None:
        files = [tmp_path / "test_foo.mojo"]
        assert group_split_files(files) == {}

    def test_excludes_lone_part(self, tmp_path: Path) -> None:
        files = [tmp_path / "test_bar_part1.mojo"]
        assert group_split_files(files) == {}
```

Test cases to cover:

1. Two parts grouped correctly
2. Three or more parts grouped correctly
3. Non-part file ignored
4. Lone part excluded (only one part, no group)
5. Files in different directories never merged
6. Empty input returns empty dict
7. Files from multiple distinct groups returned separately
8. Parts are sorted (part1 before part2)

### Step 7 — Run tests and verify

```bash
cd <project-root>
python -m pytest tests/scripts/test_validate_test_coverage.py -v
python scripts/validate_test_coverage.py  # should exit 0
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| N/A — no failed attempts in this session | The test file's imports revealed the full API contract before writing any code | Read the test file imports first; they define the API you must implement |

## Results & Parameters

**Regex pattern**: `r"^(.+)_part(\d+)\.mojo$"`

- Group 1 (`m.group(1)`): base name, e.g., `test_lenet5_layers`
- Group 2 (`m.group(2)`): part number (not used in grouping key)

**Group key format**: `str(f.parent / m.group(1))` — full path without extension and without
`_partN` suffix, ensuring files from different directories never collide.

**New tests added**: 10 (in `TestGroupSplitFiles` class)

**Total tests after**: 23 (all passing)

**Files modified**:

- `scripts/validate_test_coverage.py` — added `group_split_files()`, `check_stale_patterns()`,
  updated `generate_report()` and `main()`
- `tests/scripts/test_validate_test_coverage.py` — added `TestGroupSplitFiles` class

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4109, PR #4871, branch `4109-auto-impl` | [notes.md](../references/notes.md) |
