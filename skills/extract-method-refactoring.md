---
name: extract-method-refactoring
description: 'Decompose large methods and inline closures into focused helper methods.
  Use when: (1) methods exceed 50-100 LOC or have high cyclomatic complexity, (2) code
  review requests decomposition, (3) a method defines multiple closures over 3+ variables
  from the enclosing scope, (4) closures use nonlocal rebinding signaling they should be
  private methods, or (5) inline closures prevent direct unit testing of guards.'
category: architecture
date: 2026-01-01
version: 2.0.0
user-invocable: false
---
# Extract Method Refactoring

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-15 |
| **Issue** | #639 - Decompose _initialize_or_resume_experiment |
| **Objective** | Reduce method complexity from 90 LOC to <50 LOC using Extract Method pattern |
| **Outcome** | ✅ Success - Reduced to 30 LOC main method + 2 focused helpers |
| **Test Impact** | 0 regressions (2,145 tests passed) |

## When to Use This Skill

Use this workflow when you encounter:

- **Methods exceeding 50 lines** (target threshold)
- **Methods exceeding 100 lines** (hard threshold from CLAUDE.md)
- **High cyclomatic complexity** (>15 according to quality-complexity-check)
- **Methods with multiple responsibilities** (violating Single Responsibility Principle)
- **Code review feedback** requesting decomposition
- **Unclear control flow** making code hard to understand
- **A method defines multiple closures** over 3+ variables from the enclosing scope
- **Closures contain `if x is None: raise RuntimeError(...)` guards** that cannot be tested in isolation
- **A closure uses `nonlocal`** to rebind a captured variable (a sign the closure should be a method)
- **Tests rely on indirect patching** (e.g., `patch.object(StateMachine, ...)`) instead of calling closures directly

**Trigger phrases:**

- "This method is too long"
- "Decompose this function"
- "Extract helper methods"
- "Refactor for readability"
- "Reduce complexity"
- "Cannot test these closures directly"
- "Guards are only reachable through the state machine"

## Verified Workflow

### Phase 1: Analysis (Before Touching Code)

1. **Read the entire method** to understand:
   - Overall purpose and return value
   - Natural section boundaries (blank lines, comments)
   - Dependencies between sections
   - Error handling patterns
   - State modifications (instance variables)

2. **Identify extraction candidates** by looking for:
   - **Sequential blocks** with clear purpose (lines 186-231: "load checkpoint")
   - **Creation/initialization logic** (lines 232-256: "create fresh experiment")
   - **Validation blocks** that can be isolated
   - **Multiple levels of indentation** suggesting nested concerns

3. **Check existing tests** BEFORE refactoring:

   ```bash
   # Find tests for the target method
   grep -r "def test.*<method_name>" tests/

   # Understand test coverage
   pixi run pytest tests/ -v --cov=scylla/e2e/runner.py
   ```

### Phase 2: Extract Methods Incrementally

**CRITICAL: Extract one method at a time, verify, then proceed**

1. **Extract first helper method**:
   - Copy the target lines into a new private method (use `_` prefix)
   - Add complete type hints:

     ```python
     def _load_checkpoint_and_config(
         self,
         checkpoint_path: Path
     ) -> tuple[E2ECheckpoint, Path]:
     ```

   - Write comprehensive docstring (Google style):

     ```python
     """Load and validate checkpoint and configuration.

     Args:
         checkpoint_path: Path to checkpoint.json file

     Returns:
         Tuple of (checkpoint, experiment_dir)

     Raises:
         ValueError: If validation fails
         Exception: If checkpoint loading fails
     """
     ```

   - Insert the new method **before** the main method (maintains logical order)

2. **Extract second helper method**:
   - Repeat the same pattern for the next section
   - Keep error handling in the helper (don't duplicate)
   - Return appropriate types (single values or tuples)

3. **Refactor main method**:
   - Replace extracted code with method calls
   - Simplify control flow (if/else becomes clearer)
   - Update docstring if needed
   - Remove now-redundant inline comments

### Variation: Closure to Private Method

Use this variation when a method body is 40+ lines due to inline closure definitions, or
when closures capture 3+ variables and their guards cannot be tested in isolation.

#### Naming Convention

Each closure becomes exactly one private method. Use `_action_<scope>_<state>` naming:
- `_action_exp_<state>` for experiment-level actions (e.g., `_action_exp_tiers_complete`)
- `_action_tier_<state>` for tier-level actions (mirrors `TierActionBuilder` convention)

#### Mutable-Box for `nonlocal` Variables

When a closure uses `nonlocal x` to rebind a captured variable, the extracted method cannot
use `nonlocal` (it has no enclosing scope). Use a **single-element list as a mutable box**:

```python
# Before (closure with nonlocal)
def action_dir_created() -> None:
    nonlocal scheduler
    scheduler = self._setup_workspace_and_scheduler()

# After (extracted method)
def _action_exp_dir_created(self, scheduler_ref: list[ParallelismScheduler | None]) -> None:
    scheduler_ref[0] = self._setup_workspace_and_scheduler()

# Builder: initialise box before the return dict
scheduler_ref: list[ParallelismScheduler | None] = [scheduler]
# TIERS_RUNNING lambda reads scheduler_ref[0] to get the updated value
```

**Why not return the value?** The caller is a `Callable[[], None]` (zero-arg). Returning would
require wrapper lambdas — more complex. The mutable box matches how dicts are already mutated
in-place and is the standard Python idiom.

#### Thin Builder Pattern

After extraction, the builder method contains only:
1. One line initializing the mutable box: `scheduler_ref: list[...] = [scheduler]`
2. A `return {...}` dict with entries — direct method refs or lambdas forwarding captured args

```python
return {
    ExperimentState.INITIALIZING: self._action_exp_initializing,
    ExperimentState.DIR_CREATED: lambda: self._action_exp_dir_created(scheduler_ref),
    ExperimentState.TIERS_RUNNING: lambda: self._action_exp_tiers_running(
        tier_groups, scheduler_ref[0], tier_results
    ),
}
```

**No-arg actions**: use `self._method` directly (no lambda needed).
**Actions with captured args**: wrap with a lambda that forwards them.

#### TDD: Write Tests Alongside Extraction

Write the test file for extracted methods first (or in parallel). This validates each
extraction immediately and catches parameter-passing bugs before they accumulate.

#### Critical Gotcha: Assert Mock INSIDE `with` Block

A common mistake: calling `mock.assert_called_once_with(...)` **outside** the `with patch.object(...)` block. Outside the block, the attribute has been restored to the original function (which has no `.assert_*` methods):

```python
# WRONG — mock is gone outside the with block
with patch.object(runner, "_execute_tier_groups", return_value={}) as mock_exec:
    runner._action_exp_tiers_running(...)
mock_exec.assert_called_once_with(...)  # AttributeError: 'function' has no attr

# CORRECT — assert inside the with block
with patch.object(runner, "_execute_tier_groups", return_value={}) as mock_exec:
    runner._action_exp_tiers_running(...)
    mock_exec.assert_called_once_with(...)  # OK
```

This applies whenever `patch.object` targets an instance method that was not originally a Mock.

#### Ruff D401 During Extraction

If ruff D401 fires on an extracted method's docstring, reword to imperative mood:

```python
# BAD
"""INITIALIZING -> DIR_CREATED: No-op; setup done in ..."""

# GOOD
"""Handle INITIALIZING -> DIR_CREATED transition.

No-op: ...
"""
```

### Phase 3: Verification (Critical - Do Not Skip)

1. **Verify module imports**:

   ```bash
   pixi run python -c "from scylla.e2e.runner import E2ERunner; print('✓ OK')"
   ```

2. **Run full test suite**:

   ```bash
   pixi run pytest tests/ -v --tb=short -x
   ```

   - **ALL tests must pass** - no regressions allowed
   - If any failures: debug before proceeding
   - 0 failures = pure refactoring verified ✅

3. **Run pre-commit hooks**:

   ```bash
   pre-commit run --files <modified_file>
   ```

   - Ruff will auto-format
   - If formatting applied, verify tests still pass
   - Mypy validates type hints

### Phase 4: Commit and PR

1. **Create focused commit**:

    ```bash
    git add <file>
    git commit -m "refactor(scope): Decompose <method_name> into helpers

    Extract focused helper methods:
    - _helper_1(): Purpose (was lines X-Y)
    - _helper_2(): Purpose (was lines Z-W)

    Reduces main method from X LOC to Y LOC.

    Closes #<issue>

    Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    ```

2. **Push and create PR**:

    ```bash
    git push -u origin <branch>
    gh pr create \
      --title "refactor(scope): Decompose <method_name> into helpers" \
      --body "Closes #<issue>

    ## Summary
    - Extracted _helper_1() for X logic
    - Extracted _helper_2() for Y logic
    - Reduced from X LOC to Y LOC
    - 100% test pass rate

    ## Verification
    - ✅ All tests pass
    - ✅ Pre-commit hooks pass
    - ✅ No behavior changes" \
      --label "refactoring"

    gh pr merge --auto --rebase
    ```

## Failed Attempts & Lessons Learned

### ❌ Don't: Extract all methods at once

**Why it fails:** If tests fail, you can't isolate which extraction caused the problem.

**✅ Do:** Extract one method, verify it works (run tests), then extract the next.

### ❌ Don't: Change behavior while refactoring

**Why it fails:** Mixes refactoring with feature changes, making review harder and increasing regression risk.

**✅ Do:** Pure refactoring only - identical behavior before and after. Verify with unchanged test suite.

### ❌ Don't: Skip type hints or docstrings

**Why it fails:** Mypy will fail, and the extracted methods lack documentation.

**✅ Do:** Add complete type hints and Google-style docstrings immediately when creating the method.

### ❌ Don't: Extract methods without understanding dependencies

**Why it fails:** You might break state dependencies or error handling flow.

**✅ Do:** Read the entire method first, map out what modifies `self.x`, what raises exceptions, what depends on what.

### ❌ Don't: Assert mocks outside the `with patch.object(...)` block

**Why it fails:** Once the `with` block exits, `patch.object` restores the original function. The local `mock_exec` variable still refers to the Mock object, but calling `.assert_called_once_with()` on a restored non-Mock function raises `AttributeError`.

**✅ Do:** Place all `mock.assert_*` calls inside the `with` block, before it exits.

## Results & Parameters

### Input Characteristics

- **Method LOC:** 90 lines (below 100 hard limit, above 50 target)
- **Extraction targets:** 2 distinct sections with clear boundaries
- **Test coverage:** High (E2E runner heavily tested)

### Extraction Decisions

**Helper 1: `_load_checkpoint_and_config()`**

- **Lines extracted:** 189-230 (42 LOC)
- **Purpose:** Load and validate checkpoint from existing experiment
- **Returns:** `tuple[E2ECheckpoint, Path]`
- **Why tuple:** Need both checkpoint and experiment_dir for caller

**Helper 2: `_create_fresh_experiment()`**

- **Lines extracted:** 232-256 (25 LOC)
- **Purpose:** Create new experiment directory and initialize checkpoint
- **Returns:** `Path` (checkpoint path)
- **Why single return:** Only checkpoint path needed

### Final Metrics

- **Main method:** 90 LOC → 30 LOC (67% reduction)
- **Total LOC:** ~90 LOC → ~97 LOC (slightly more due to docstrings - acceptable)
- **Cyclomatic complexity:** Reduced (simpler control flow)
- **Test pass rate:** 2,145/2,145 (100%)
- **Regressions:** 0

### Pre-commit Configuration

```bash
# Hooks that ran automatically
- ruff-format-python (auto-formatted once)
- ruff (linting - passed)
- mypy (type checking - passed)
```

## Key Insights

1. **Line count targets are guidelines, not rules**
   - <50 LOC is ideal
   - 50-100 LOC is acceptable if cohesive
   - >100 LOC requires decomposition

2. **Natural boundaries matter**
   - Look for blank lines, comments like "# Resume from checkpoint"
   - These often mark logical sections perfect for extraction

3. **Return types drive design**
   - Single value → single return
   - Multiple related values → tuple return
   - Unrelated values → maybe shouldn't be one method

4. **Test suite is your safety net**
   - 100% pass rate before = must be 100% after
   - Any regression = stop and debug
   - Pure refactoring = tests unchanged

5. **Pre-commit hooks catch issues early**
   - Ruff formatting prevents style debates
   - Mypy catches type errors before manual review
   - Running hooks locally saves CI time

## References

- Issue: #639
- PR: #709
- File modified: `scylla/e2e/runner.py`
- Related skills: `quality-complexity-check`, `refactor-for-extensibility`
- CLAUDE.md guidelines: Method complexity targets (LOC <100, CC <15)

## Usage Examples

### Invoke this skill when you see

```
TODO: This method is 85 lines, consider breaking it down
```

### Or when code review comments say

```
This method does too much - can we extract the validation logic?
```

### Expected workflow

1. Analyze method structure
2. Identify 2-3 extraction candidates
3. Extract one at a time
4. Verify after each extraction
5. Commit with metrics in message

---

**Category:** architecture
**Tags:** refactoring, code-quality, method-extraction, complexity-reduction, single-responsibility
**Confidence:** High (verified on real codebase with 2,145 tests)
