---
name: add-unit-tests-for-existing-script
description: "Add comprehensive pytest unit tests for an existing Python script with no coverage. Use when: a script has no tests, bugs were found during implementation, or a follow-up issue requests test coverage."
category: testing
date: 2026-03-07
user-invocable: false
---

# add-unit-tests-for-existing-script

## Overview

| Item | Details |
|------|---------|
| Name | add-unit-tests-for-existing-script |
| Category | testing |
| Description | Add comprehensive pytest unit tests for an existing Python script that has no tests |
| Language | Python / pytest |
| Pattern | Class-grouped tests by function, sys.path.insert import, tmp_path fixtures |

## When to Use

- A Python script in `scripts/` has been identified as having zero test coverage
- Bugs were discovered during manual use that unit tests would have caught
- A follow-up GitHub issue explicitly requests tests for specific public functions
- You need to retrofit tests onto existing code without modifying the script itself

## Verified Workflow

1. **Read the script** thoroughly before writing a single test — understand all public functions, their signatures, return types, and edge cases
2. **Explore function behavior interactively** with quick `python3 -c` one-liners to verify assumptions before encoding them as assertions
3. **Check the existing test file** (if any) — avoid duplicating tests that already exist; extend the file rather than creating a new one
4. **Add `sys.path.insert`** at the top of the test file to allow direct imports from `scripts/`:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
   from my_script import func_a, func_b
   ```
5. **Group tests into classes** — one `TestClassName` per public function, following `tests/scripts/` precedents
6. **Use `tmp_path` fixtures** for any file I/O; never write to real directories
7. **Cover edge cases first**: empty input, missing files, unclosed delimiters, unknown keys, None arguments
8. **Run tests** with `python3 -m pytest tests/scripts/test_<script>.py -v` — use direct `python3` not `pixi run` to avoid slow env activation during development
9. **Fix pre-commit auto-fixes**: ruff may auto-remove unused imports; re-stage and commit again
10. **Commit only the test file** — never stage `.pyc`, prompt files, or build directories

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests via `pixi run python -m pytest` | Used pixi for test execution during development | Command timed out (>2 min env activation) | Use `python3 -m pytest` directly for fast iteration; only use pixi for final validation |
| Running background pytest task | Launched pytest as a background task to avoid blocking | Output file was empty for minutes | Background tasks don't stream output — run pytest synchronously in foreground |
| Importing unused constant in tests | Imported `SKILL_CATEGORY_OVERRIDE` for documentation but never asserted on it | Ruff auto-removed it, causing first commit to fail | Only import symbols you actually use in assertions; ruff-check runs in pre-commit |
| Extending file without reading it | Attempted to write new test classes without reading existing file content | Edit tool rejected the change (file not read first) | Always `Read` the target file before any `Edit` — required by tool policy |

## Results & Parameters

### Import Pattern (preferred)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from my_script import func_a, func_b, CONSTANT_A
```

### Dynamic Loader (for tests needing module-level patching)

```python
import importlib.util
SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "my_script.py"

def load_module():
    spec = importlib.util.spec_from_file_location("my_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def mod():
    return load_module()
```

Use `unittest.mock.patch.object(mod, "GLOBAL_CONSTANT", fake_value)` to override
module-level constants (e.g., hardcoded paths) in tests.

### Class Grouping Template

```python
class TestMyFunction:
    def test_happy_path(self) -> None: ...
    def test_empty_input(self) -> None: ...
    def test_missing_file_returns_false(self, tmp_path: Path) -> None: ...
    def test_edge_case_colon_in_value(self) -> None: ...
```

### Quick Behavior Exploration

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from my_script import parse_frontmatter
fm, rest = parse_frontmatter('---\nname: foo\n---\nBody')
print('fm:', fm)
print('rest:', repr(rest))
"
```

### Pre-Commit Fix Pattern

If `ruff-check-python` fails with "files were modified by this hook":
```bash
git add tests/scripts/test_my_script.py  # re-stage after auto-fix
git commit -m "..."                       # commit again — will pass this time
```
