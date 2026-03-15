---
name: validate-test-coverage-split-naming
description: "Verify CI coverage scripts handle split file naming (part1/part2, suffix variants) correctly. Use when: confirming wildcard-based CI group matching covers ADR-009 split files without requiring script changes."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | validate-test-coverage-split-naming |
| **Category** | testing |
| **Scope** | Coverage script validation for split test file naming |
| **Language** | Python (pytest) |
| **Issue** | ProjectOdyssey #4364 |

## When to Use

- A CI coverage/validation script uses glob patterns (`test_*.mojo`) to detect test files
- Test files are split per ADR-009 into `_part1`/`_part2` variants or other suffix variants
  (e.g. `_cmd_run`, `_parser`)
- You need to confirm the script handles split naming without any code changes
- You need to write tests documenting that wildcard matching already covers all variants

## Verified Workflow

### Quick Reference

```bash
# Run new tests
pixi run python -m pytest tests/test_validate_test_coverage.py -v

# Full test suite
pixi run python -m pytest tests/ -v
```

### Step 1 — Read the script and understand the matching logic

Read `scripts/validate_test_coverage.py` (or equivalent) to find the function that
expands CI group patterns to actual file paths. In this project it was `expand_pattern`.

Key insight: a glob pattern `test_*.mojo` matches **any** filename beginning with `test_`
and ending with `.mojo`, including:

- `test_arg_parser.mojo` (canonical)
- `test_arg_parser_part1.mojo` (ADR-009 split)
- `test_arg_parser_part2.mojo` (ADR-009 split)
- `test_arg_parser_cmd_run.mojo` (suffix variant)
- `test_arg_parser_parser.mojo` (suffix variant)

No script changes are needed — the wildcard already handles all naming variants.

### Step 2 — Identify the three public functions to test

For a coverage script following the pattern in this project:

| Function | What to test |
|----------|-------------|
| `find_test_files(root_dir)` | Discovers part1/part2 and suffix variant files |
| `expand_pattern(path, pattern, root)` | Wildcard matches all naming variants |
| `check_coverage(files, groups, root)` | Split files in covered dirs → not flagged; split files in uncovered dirs → flagged |

### Step 3 — Write pytest tests using tempfile + real filesystem

Use `tempfile.mkdtemp()` for isolation. Do NOT mock `glob` or `Path.rglob` —
test against a real (temporary) filesystem to catch any path resolution subtleties.

```python
import tempfile
import shutil
from pathlib import Path

class TestExpandPattern(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _create_file(self, rel_path: str) -> Path:
        full_path = self.test_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("# stub\n")
        return full_path

    def test_wildcard_matches_part1_part2(self):
        self._create_file("tests/shared/utils/test_arg_parser_part1.mojo")
        self._create_file("tests/shared/utils/test_arg_parser_part2.mojo")
        matched = expand_pattern("tests/shared/utils", "test_*.mojo", self.test_dir)
        self.assertIn(Path("tests/shared/utils/test_arg_parser_part1.mojo"), matched)
        self.assertIn(Path("tests/shared/utils/test_arg_parser_part2.mojo"), matched)
```

### Step 4 — Cover the negative case

Also test that split files in a directory **not** in the CI groups are correctly
reported as uncovered:

```python
def test_split_files_in_uncovered_directory_are_flagged(self):
    # Create files in a path that has no CI group
    self._create_file("tests/shared/other/test_arg_parser_part1.mojo")
    test_files = [Path("tests/shared/other/test_arg_parser_part1.mojo")]
    uncovered, _ = check_coverage(test_files, MINIMAL_CI_GROUPS, self.test_dir)
    self.assertEqual(len(uncovered), 1)
```

### Step 5 — Run and verify

```bash
pixi run python -m pytest tests/test_validate_test_coverage.py -v
# Expected: all 13 tests pass
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking if script needed code changes | Searched `validate_test_coverage.py` for hardcoded filenames | No hardcoded names found — wildcard already handles all naming variants | Read the code first before assuming a fix is needed |
| Mocking `Path.rglob` | Considered patching the glob method for isolation | Would not catch real path resolution edge cases | Use real tempfile filesystem for coverage script tests |

## Results & Parameters

**Test file**: `tests/test_validate_test_coverage.py`
**Test count**: 13 tests (3 classes: TestFindTestFiles, TestExpandPattern, TestCheckCoverage)
**All tests pass**: yes
**Script changes needed**: none

### Minimal CI groups fixture for tests

```python
MINIMAL_CI_GROUPS = {
    "Utils": {"path": "tests/shared/utils", "pattern": "test_*.mojo"},
}
```

Use this as a minimal fixture to avoid needing a real workflow YAML in unit tests.
