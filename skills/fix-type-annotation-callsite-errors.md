---
name: fix-type-annotation-callsite-errors
description: "Fix CI failures caused by AI-generated type annotations placed at function call sites instead of definitions, plus cascading mock path and return type errors. Use when: (1) pytest collection errors with SyntaxError on type annotations in function calls, (2) ruff F821 undefined name errors from annotations referencing unimported types, (3) mypy return-value errors from fixtures annotated -> None that return values, (4) mock patch paths changed to wrong modules."
category: ci-cd
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - type-annotations
  - mypy
  - pytest
  - mock-patching
  - ci-fix
---

# Fix Type Annotation Call-Site Errors

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-24 |
| **Objective** | Fix CI failures on a branch that bulk-replaced `Any` type annotations with specific types across 28+ test files |
| **Outcome** | Success — 4782 tests passing, all pre-commit hooks green, PR updated |
| **Issue** | HomericIntelligence/ProjectScylla#1379 |
| **PR** | HomericIntelligence/ProjectScylla#1517 |

## When to Use

- AI-generated code added type annotations to function **call sites** (e.g., `func(param: pd.DataFrame)`) instead of only function **definitions**
- pytest fails with `SyntaxError: invalid syntax` or `IndentationError: unexpected indent` during collection
- ruff reports `F821 Undefined name` because a type (e.g., `pd`) is used in annotations but not imported at module level
- mypy reports `[return-value] No return value expected` on fixtures that actually return values (were `-> Any`, incorrectly changed to `-> None`)
- Mock `patch()` paths were bulk-changed to wrong modules (e.g., `scylla.automation.follow_up.run` → `scylla.automation.implementer.run`)
- A bulk type annotation refactor introduces 200+ errors across multiple error categories

## Verified Workflow

### Quick Reference

```bash
# 1. Find call-site annotations (NOT in def lines)
grep -rn '(\w\+:\s*pd\.\|np\.\|dict\[' tests/ | grep -v "def "

# 2. Find missing module-level imports for annotation types
pixi run ruff check tests/ 2>&1 | grep "F821"

# 3. Find -> None on functions that return values
pixi run mypy tests/ 2>&1 | grep "return-value\|func-returns-value"

# 4. Compare mock patch paths against main
diff <(git show origin/main:path/to/test.py | grep -n 'patch(') <(grep -n 'patch(' path/to/test.py)
```

### Detailed Steps

#### Step 1: Fix call-site type annotations (SyntaxError)

The most critical error — type annotations at function **call sites** are invalid Python:

```python
# WRONG (call site — SyntaxError)
tier_order = derive_tier_order(sample_runs_df: pd.DataFrame)
assert len(degenerate_single_element: np.ndarray) == 1

# CORRECT (remove annotation from call)
tier_order = derive_tier_order(sample_runs_df)
assert len(degenerate_single_element) == 1
```

Use regex to find and fix all occurrences. Only remove annotations from **non-def** lines:

```python
import re

type_pattern = re.compile(
    r'(\b\w+)\s*:\s*(?:pd\.DataFrame|np\.ndarray|dict\[.*?\]|...)'
)
for line in lines:
    if line.strip().startswith('def '):
        continue  # Skip definitions
    # Check if annotation is inside parentheses (call site)
    # Remove the ': Type' part, keep just the variable name
```

#### Step 2: Fix misplaced imports

AI sometimes moves module-level imports inside function bodies:

```python
# WRONG — imports at module-level indentation inside a function
def test_foo(sample_runs_df: pd.DataFrame) -> None:
    from export_data import compute_statistical_results
import pandas as pd      # <- Wrong! Inside function body at col 0
from pathlib import Path  # <- Wrong!

# CORRECT — imports at module level, before function
import pandas as pd
from pathlib import Path

def test_foo(sample_runs_df: pd.DataFrame) -> None:
    from export_data import compute_statistical_results
```

#### Step 3: Add missing module-level imports for annotation types

When `pd.DataFrame` is used in function parameter annotations, `pd` must be importable at module level:

```python
# Add at module level (not inside functions)
import pandas as pd
```

#### Step 4: Fix return type annotations on fixtures

Fixtures annotated `-> Any` that were changed to `-> None` cause mypy errors:

```python
# WRONG (fixture returns a value but annotated -> None)
@pytest.fixture
def mock_options() -> None:
    return ImplementerOptions(...)

# CORRECT
@pytest.fixture
def mock_options() -> Any:
    return ImplementerOptions(...)
```

#### Step 5: Restore correct mock patch paths

Bulk replace can change mock `patch()` targets to wrong modules:

```python
# WRONG — retrospective.run was changed to implementer.run
patch("scylla.automation.implementer.run")

# CORRECT — patch at the module where the function is defined
patch("scylla.automation.retrospective.run")
patch("scylla.automation.follow_up.run")
```

**Always compare against main** to verify patch paths:
```bash
diff <(git show origin/main:tests/file.py | grep 'patch(') <(grep 'patch(' tests/file.py)
```

#### Step 6: Remove tests for deleted APIs

After rebase, check if tested APIs still exist:
```bash
# If test references _run_subtest_in_process_safe but it was renamed/removed:
grep -r "_run_subtest_in_process_safe" scylla/  # Empty = API gone, remove tests
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Automated script to add `Any` to unannotated params | Python script using regex to add `: Any` to all unannotated function parameters | Corrupted multi-line function signatures (stripped parameters from `def func(\n    param1,\n    param2\n)` patterns), inserted `from typing import Any` inside multi-line import statements | Never use simple regex on multi-line Python signatures; use AST-based tools or fix manually. Always syntax-check (`ast.parse()`) every file after automated edits |
| `replace_all=true` to fix mock patch paths | Used Edit tool with `replace_all=true` to change `implementer.run` → `retrospective.run` | Changed ALL occurrences including ones in `TestRunClaudeCode` that correctly used `implementer.run`, and also changed `follow_up.*` patches to `retrospective.*` | Never use `replace_all` for mock path fixes — each test class patches a different module. Always compare against `origin/main` to verify correct paths |
| Adding `from __future__ import annotations` | Considered adding future annotations to defer type evaluation | Decided against — could change runtime behavior and was inconsistent with codebase. Adding `import pandas as pd` at module level was simpler | Prefer the simplest fix that matches existing codebase patterns |

## Results & Parameters

### Error Categories and Counts (This Session)

| Error Category | Count | Fix |
| ---------------- | ------- | ----- |
| Call-site type annotations (SyntaxError) | 93 | Remove `: Type` from function calls |
| F821 undefined name (ruff) | 50 | Add module-level `import pandas as pd` |
| `[no-untyped-def]` (mypy) | 220 | Add `: Any` back to unannotated params |
| `[return-value]` / `[func-returns-value]` (mypy) | 37 | Change `-> None` to `-> Any` on fixtures |
| Wrong mock patch paths | 13 | Restore original module paths |
| Stale API tests | 2 classes | Remove tests for deleted APIs |
| Black formatting (E501) | 26 | Run `ruff format` |

### Verification Commands

```bash
# Syntax check all modified files
python3 -c "
import ast, subprocess, os
result = subprocess.run(['git', 'diff', '--name-only', 'origin/main'], capture_output=True, text=True)
for f in result.stdout.strip().split('\n'):
    if f.endswith('.py') and os.path.exists(f):
        try: ast.parse(open(f).read())
        except SyntaxError as e: print(f'{f}: ERROR line {e.lineno}')
"

# Full pre-commit + test verification
pre-commit run --all-files
pixi run python -m pytest tests/unit/ -q --tb=line
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1517 — bulk type annotation refactor | Fixed 400+ errors across 28 test files, rebased twice onto main |
