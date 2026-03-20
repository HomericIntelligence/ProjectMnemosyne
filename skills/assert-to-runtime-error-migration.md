---
name: assert-to-runtime-error-migration
description: 'Skill: assert-to-runtime-error-migration. Use when replacing assert
  guards in production code with explicit RuntimeError raises to eliminate Ruff S101
  suppressions.'
category: testing
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Assert-to-RuntimeError Migration Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Issue** | #1143 — Replace assert guards with RuntimeError in workspace_manager.py, llm_judge.py, and executor/runner.py |
| **Objective** | Replace 4 remaining `assert x is not None  # noqa: S101` suppressions in production code with explicit `if x is None: raise RuntimeError(...)` guards, eliminating all S101 suppressions from production source files |
| **Outcome** | ✅ Success — all 4 sites converted, 4 regression tests added, 3261 tests pass, 78.39% coverage, zero S101 suppressions remain in `scylla/` |

## When to Use

Use this skill when:

- A codebase has `assert x is not None  # noqa: S101` patterns in production source files
- Ruff S101 rule is enforced and you want to eliminate all suppressions from production code (tests may keep `# noqa: S101`)
- Following up a bulk ruff rule expansion (e.g., after enabling S-rules) to clean up remaining suppressed assertions
- Converting defensive invariant checks from `assert` to explicit `RuntimeError` for production-safety guarantees

## Verified Workflow

### 1. Discovery — Find All Remaining S101 Suppressions

```bash
# Find all S101 suppressions in production code (not tests)
grep -rn "noqa: S101" scylla/ scripts/

# For full picture including tests
grep -rn "noqa: S101" scylla/ scripts/ tests/
```

Review each hit carefully — some may be in test files where assertions are legitimate.

### 2. Classify Each Site

For each `assert` site, determine the correct replacement pattern:

| Assert pattern | Correct replacement |
|---------------|---------------------|
| `assert x is not None` | `if x is None: raise RuntimeError("x must be set before calling method_name")` |
| `assert x is not None` before `raise x` | `if x is None: raise RuntimeError("invariant message"); raise x` |
| `assert condition` guarding logic | `if not condition: raise RuntimeError("condition description")` |

**Special case — for-else guard** (`llm_judge.py` pattern):
```python
# BEFORE:
for _attempt in range(max_attempts):
    try:
        result = parse(response)
        break
    except ValueError as e:
        last_parse_error = e
else:
    assert last_parse_error is not None  # noqa: S101
    raise last_parse_error

# AFTER:
else:
    if last_parse_error is None:
        raise RuntimeError("Retry loop exhausted but last_parse_error is None")
    raise last_parse_error
```

This is a defensive invariant: the `else` clause can only fire if all attempts failed to parse (each caught a `ValueError`), so `last_parse_error` is logically never `None` here. The `RuntimeError` guard protects against future code changes that might break this invariant.

### 3. Apply the Minimum Targeted Edit

Use the established pattern — no surrounding refactoring:

```python
# BEFORE:
assert self.commit is not None  # noqa: S101
# ... uses self.commit ...

# AFTER:
if self.commit is None:
    raise RuntimeError("commit must be set before calling _checkout_commit")
# ... uses self.commit ...
```

**Message format**: `"<attribute> must be set before calling <method_name>"` or equivalent description of invariant.

### 4. Add Regression Tests

For each converted site, add one test to the existing test class (no new test files):

**Pattern for `x is None` guard tests:**
```python
def test_method_raises_if_x_none(self, tmp_path: Path) -> None:
    """<method> raises RuntimeError when <attr> is None."""
    obj = MyClass(attr=None, ...)
    with pytest.raises(RuntimeError, match="attr must be set before calling method"):
        obj.method()
```

**Pattern for the for-else defensive guard (`last_parse_error is None`):**
Since the guard is logically unreachable in normal operation, test the adjacent behavior that confirms `last_parse_error` is always set when the `else` fires:
```python
def test_raises_value_error_not_runtime_error_when_parse_fails(self, tmp_path: Path) -> None:
    """When all retry attempts fail with ValueError, ValueError is re-raised (not RuntimeError).

    Confirms last_parse_error is always set before the else clause fires, so the
    RuntimeError guard is never triggered in normal operation.
    """
    bad = "Not valid JSON at all"
    with pytest.raises(ValueError):
        self._run_with_call_side_effects(tmp_path, [(bad, "", bad)] * 3)
```

**Pattern for `_state is None` guard in `_finalize_test_summary`:**
```python
def test_raises_runtime_error_when_state_is_none_and_state_file_configured(
    self, tmp_path: Path
) -> None:
    """_finalize_test_summary raises RuntimeError when _state is None but state_file is set."""
    config = RunnerConfig(state_file=tmp_path / "state.json")
    runner = EvalRunner(mock_docker, mock_tier_loader, config)
    assert runner._state is None

    summary = EvalSummary(test_id="test-001", started_at="2026-01-01T00:00:00+00:00")
    with pytest.raises(RuntimeError, match="_state must be initialized before finalizing"):
        runner._finalize_test_summary(summary)
```

### 5. Verify No S101 Suppressions Remain

```bash
# Must return empty (no output)
grep -rn "noqa: S101" scylla/

# Run full test suite
pixi run python -m pytest tests/ -q

# Run pre-commit
pre-commit run --all-files
```

### 6. Commit with Conventional Format

```bash
git add <modified files>
git commit -m "fix(e2e): replace assert guards with RuntimeError in <module1>, <module2>

Replace N remaining \`assert x is not None  # noqa: S101\` suppressions in
production code with explicit \`if x is None: raise RuntimeError(...)\` guards.
Eliminates all Ruff S101 suppressions from production source files.

Closes #<issue>
"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Conversion Table (Issue #1143)

| File | Line | Method | Guard Message |
|------|------|--------|---------------|
| `scylla/e2e/workspace_manager.py` | 198 | `_checkout_commit()` | `"commit must be set before calling _checkout_commit"` |
| `scylla/e2e/workspace_manager.py` | 244 | `_ensure_commit_available()` | `"commit must be set before calling _ensure_commit_available"` |
| `scylla/e2e/llm_judge.py` | 930 | retry loop `else` | `"Judge retry loop exhausted but last_parse_error is None"` |
| `scylla/executor/runner.py` | 486 | `_finalize_test_summary()` | `"_state must be initialized before finalizing test summary"` |

### Test Results

```
3261 passed, 9 warnings in 43.50s
Coverage: 78.39% (threshold: 75%)
Pre-commit: All hooks passed
S101 suppressions in scylla/: 0 (eliminated)
```

### Related Issues

- #1066: Original bulk S101 elimination (the predecessor)
- #1143: This follow-up for the remaining 4 sites
- PR #1211: Implementation PR

## Key Takeaways

1. **Follow the established pattern**: When a project has already done a bulk assert-to-RuntimeError migration, there is always a pattern to follow. Grep for `# noqa: S101` in the same codebase to see prior conversions, then match the message style.
2. **Defensive invariant guards (for-else)**: The `assert last_parse_error is not None` in a `for...else` clause is a common Python idiom. Replace with `if x is None: raise RuntimeError(...)` before re-raising, NOT by removing the check entirely.
3. **Test the observable behavior, not the guard path**: For logically-unreachable guards, test adjacent behavior (the normal retry path with exhausted attempts) rather than trying to contrive a path into the guard itself.
4. **Always check imports when adding tests**: When new test classes reference symbols used only in their tests, add them to the import block.
5. **Ruff formatter runs after edits**: Pre-commit's `ruff-format-python` hook may reformat code after your edits. Always run `pre-commit run --all-files` twice — once to apply formatting, once to confirm all hooks pass clean.
6. **Scope discipline**: The issue says "4 sites" — do not touch other assertions or refactor surrounding code. Minimal targeted edits only.
