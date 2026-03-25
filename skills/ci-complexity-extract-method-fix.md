---
name: ci-complexity-extract-method-fix
description: "Fix C901 cyclomatic complexity CI failures by extracting helper functions. Use when: (1) pre-commit or CI fails with 'is too complex (N > 10)', (2) adding conditional blocks to an existing function pushes it over the CC limit."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - pre-commit
  - complexity
  - refactoring
  - ruff
  - C901
---

# Fix C901 Cyclomatic Complexity CI Failures

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix CI pre-commit failure where adding new conditional blocks to `_restore_run_context()` pushed cyclomatic complexity from ~8 to 11, exceeding the C901 limit of 10 |
| **Outcome** | Successful — extracted two helper functions, CC dropped below 10, all CI checks pass |

## When to Use

- CI fails with `C901 _function_name is too complex (N > 10)`
- Adding new `if`/`else` blocks to an existing function that is near the complexity limit
- Pre-commit hook "Check Cyclomatic Complexity" fails
- Ruff reports C901 violations

## Verified Workflow

### Quick Reference

```python
# BEFORE: All logic inline (CC=11)
def _restore_run_context(ctx, current_state):
    # ... agent restore (CC +3) ...
    # ... judge_prompt restore (CC +2) ...
    # ... judgment restore (CC +3) ...    <-- NEW
    # ... run_result restore (CC +3) ...   <-- NEW

# AFTER: Extract new blocks into helpers (CC=7)
def _restore_run_context(ctx, current_state):
    # ... agent restore (CC +3) ...
    # ... judge_prompt restore (CC +2) ...
    if condition:
        _restore_judgment(ctx)       # CC counted in helper
    if condition:
        _restore_run_result(ctx)     # CC counted in helper

def _restore_judgment(ctx):          # CC=3 (separate function)
    ...

def _restore_run_result(ctx, state): # CC=2 (separate function)
    ...
```

### Detailed Steps

1. **Identify the violation**: CI error shows function name and CC score (e.g., `_restore_run_context is too complex (11 > 10)`)

2. **Count branches**: Each `if`, `elif`, `else`, `for`, `while`, `except`, `and`, `or` adds +1 CC. The function starts at CC=1.

3. **Extract self-contained blocks**: Look for conditional blocks that:
   - Have their own imports
   - Operate on a clear subset of parameters
   - Don't share mutable state with surrounding code beyond `ctx`

4. **Create module-level helpers**: Place extracted functions near the original, with clear docstrings. Keep the same parameters — don't over-abstract.

5. **Verify locally**:
   ```bash
   pre-commit run --all-files  # Check both ruff C901 and custom CC hook
   pixi run python -m pytest tests/unit/e2e/ -x -q  # Ensure no regressions
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Inline all restore logic in one function | Added judgment + run_result restore as new `if` blocks in `_restore_run_context()` | CC went from ~8 to 11, exceeding C901 limit of 10 | Always check CC budget before adding conditional blocks to existing functions near the limit |
| Using `# noqa: C901` suppression | Considered suppressing the warning | ProjectScylla prohibits `--no-verify` and suppression of lint rules | Extract-method is the correct fix, not suppression |

## Results & Parameters

### CC Budget Rule of Thumb

| CC Score | Status | Action |
|----------|--------|--------|
| 1-7 | Safe | Can add 1-3 branches freely |
| 8-9 | Warning zone | One more `if/else` block hits the limit |
| 10 | At limit | Any new branch will fail CI |
| 11+ | CI failure | Must extract helpers |

### ProjectScylla CC Configuration

- **Ruff C901**: `max-complexity = 10` (in `pyproject.toml` or `.pre-commit-config.yaml`)
- **Custom hook**: `Check Cyclomatic Complexity` — runs separately from ruff, same threshold
- Both must pass for CI green

### Extract-Method Pattern

```python
# Pattern: delegate to helper, keep guard clause in parent
if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and ctx.judgment is None:
    _restore_judgment(ctx)  # All branching logic moves here

# Helper gets its own CC budget (starts at 1)
def _restore_judgment(ctx: Any) -> None:
    """Restore ctx.judgment from on-disk judge result."""
    from scylla.e2e.judge_runner import _has_valid_judge_result, _load_judge_result
    judge_dir = get_judge_dir(ctx.run_dir)
    if _has_valid_judge_result(ctx.run_dir):
        ctx.judgment = _load_judge_result(judge_dir)
        # ... timing loading ...
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1546 CI fix | Extracted `_restore_judgment()` and `_restore_run_result()` from `_restore_run_context()`, CC 11 -> ~7 |
