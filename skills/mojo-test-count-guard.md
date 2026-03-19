---
name: mojo-test-count-guard
description: 'Add a pre-commit hook to enforce a per-file Mojo test function limit.
  Use when: a runtime bug causes crashes above N tests in one file, implementing ADR-style
  Phase 2 safeguards, or blocking regression after a manual file-splitting workaround.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo 0.26.1 heap-corruption bug crashes after ~15 cumulative `fn test_` calls in one file; manual file splitting was done but nothing prevents new tests from silently re-hitting the limit |
| **Solution** | Python script + pre-commit hook that counts `fn test_` per staged `.mojo` test file and exits 1 if any exceed the limit |
| **Limit** | 10 tests per file (safety margin below the ~15 crash threshold) |
| **Hook scope** | `files: '^tests/.*\.mojo$'` + `pass_filenames: true` — only staged Mojo test files |
| **Language** | Python (regex, pathlib, sys.argv) |

## When to Use

- A Mojo runtime bug has been worked around by splitting test files, and you need CI to enforce the limit going forward
- Any per-file test count cap needs automated pre-commit enforcement
- ADR Phase 2 "optional safeguards" are being implemented for a crash-threshold workaround
- You want a lightweight, zero-dependency check (no subprocess, no find) that runs only on staged test files

## Verified Workflow

### 1. Write the guard script

Core pattern — anchor regex to line start to avoid matching string literals:

```python
import re, sys
from pathlib import Path
from typing import List

LIMIT = 10  # ADR-009: stay below the ~15-test crash threshold
_TEST_FN_RE = re.compile(r"^\s*fn test_", re.MULTILINE)

def is_mojo_test_file(path: Path) -> bool:
    return path.suffix == ".mojo" and "tests" in path.parts

def count_tests_in_file(path: Path) -> int:
    try:
        return len(_TEST_FN_RE.findall(path.read_text(encoding="utf-8")))
    except OSError:
        return 0

def check_files(file_paths: List[str]) -> int:
    violations = []
    for raw in file_paths:
        path = Path(raw)
        if not is_mojo_test_file(path):
            continue
        count = count_tests_in_file(path)
        if count > LIMIT:
            violations.append(f"❌  {path}: {count} tests (limit: {LIMIT}) — split per ADR-009")
    if violations:
        for msg in violations:
            print(msg)
        return 1
    print(f"✅  All test file(s) within the {LIMIT}-test limit.")
    return 0

if __name__ == "__main__":
    sys.exit(check_files(sys.argv[1:]))
```

**Critical**: `re.MULTILINE` makes `^` match line-start throughout the file, not just the
string start. Without it, the first `fn test_` anchored to the file beginning would miss all
subsequent functions.

### 2. Add the pre-commit hook

```yaml
- id: check-test-count
  name: Check Mojo Test Count (ADR-009)
  description: Fail if any Mojo test file exceeds 10 tests (heap-corruption threshold per ADR-009)
  entry: python3 scripts/check_test_count.py
  language: system
  files: '^tests/.*\.mojo$'
  pass_filenames: true
```

Key choices:

- `pass_filenames: true` — pre-commit passes only the staged files, so the script never
  needs to walk the repo itself
- `files: '^tests/.*\.mojo$'` — scopes to test Mojo files only; production `.mojo` files
  (without limits) are skipped automatically
- `language: system` — uses the project's `pixi`/system Python, no virtualenv needed

### 3. Write tests (pytest, no fixtures needed)

Use `tempfile.mkdtemp()` + a helper to write files under a `tests/` subdirectory so
`is_mojo_test_file` accepts them:

```python
def _mojo(directory: str, filename: str, n_tests: int) -> str:
    tests_dir = Path(directory) / "tests"
    tests_dir.mkdir(exist_ok=True)
    fns = "".join(f"fn test_{i}():\n    pass\n" for i in range(n_tests))
    path = tests_dir / filename
    path.write_text(fns, encoding="utf-8")
    return str(path)
```

Cover: exactly-at-limit (0), one-above (1), non-test Mojo skipped, Python files skipped,
missing file returns 0, empty file returns 0, `LIMIT == 10` assertion.

### 4. Format before staging

```bash
pixi run ruff format scripts/check_test_count.py tests/test_check_test_count.py
git add scripts/check_test_count.py tests/test_check_test_count.py .pre-commit-config.yaml
git commit -m "feat(pre-commit): Add test-count guard hook per ADR-009 Phase 2"
```

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `LIMIT` | 10 | ADR-009 safety margin (crash at ~15) |
| Regex | `^\s*fn test_` with `re.MULTILINE` | Catches indented definitions; ignores string mentions |
| Hook `files` | `'^tests/.*\.mojo$'` | Scoped to test Mojo files only |
| `pass_filenames` | `true` | Pre-commit provides the staged file list |
| Tests written | 21 pytest unit tests | `is_mojo_test_file`, `count_tests_in_file`, `check_files` |
| Missing file handling | Returns 0 + stderr warning | Avoids crashing hook on deleted files |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| No `re.MULTILINE` flag | Used `re.compile(r"^\s*fn test_")` without flag | `^` only matches the very start of the string, so only the first occurrence was found | Always use `re.MULTILINE` when matching line-anchored patterns across multi-line file content |
| Filtering by filename only | Checked `path.name.startswith("test_")` | Would accept `test_foo.mojo` files outside `tests/`, letting production files with many `fn test_`-named helpers get flagged | Check both suffix AND that `"tests"` appears in `path.parts` |
| `pass_filenames: false` with glob walk | Script walked the entire `tests/` tree | Ran on every commit regardless of what was staged, slowing commits and causing false positives on unchanged files | Use `pass_filenames: true`; let pre-commit filter to staged files |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3962, PR #4841 | [notes.md](../references/notes.md) |
