---
name: test-state-machine-docstring-accuracy
description: "Test names and docstrings must document actual code paths (early-exit guards, fast-forwards) not hypothetical later logic. Use when: (1) writing tests for state-machine early-exit guards, (2) documenting fast-forward paths, (3) fixing misleading test docstrings that claim 'defense-in-depth' but test fast-forward behavior."
category: testing
date: 2026-07-05
version: "1.0.0"
user-invocable: true
verification: verified-local
tags:
  - testing
  - state-machine
  - docstring
  - naming
  - fast-forward
  - early-exit
  - guard
  - automation
---

# Test State-Machine Docstring Accuracy

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-05 |
| **Objective** | Capture the learning that test names and docstrings MUST document actual executed code paths, especially when testing early-exit guards or fast-forward short-circuits in state machines. Hypothetical later logic that never executes must not be cited in docstrings as the test's purpose. |
| **Outcome** | SUCCESS — PR #1934 (issue #1857) merged with corrected test naming and docstring: `test_plan_go_on_entry_fast_forwards_without_swap` with accurate inline comments citing the guard that fires first (line 176). |
| **Verification** | verified-local — fix applied and tests pass locally; CI pending merge. |

## When to Use

- **Writing state-machine tests for early-exit guards**: When a guard condition fires and causes an early return before other code paths can execute.
- **Documenting fast-forward behavior**: When a test verifies that a fast-forward condition short-circuits subsequent logic (e.g., `on_enter` guards that return `ADVANCE` before reaching later swap logic).
- **Fixing misleading test docstrings**: When a test docstring claims the test verifies "defense-in-depth" or a later code block but the actual behavior is an earlier guard firing first.
- **Inline comments on unreachable paths**: When explaining why certain code in a guard-protected function is never reached during test execution.

## Verified Workflow

### Quick Reference

1. **Name the test after the actual behavior it verifies, not hypothetical later behavior.**
   - ❌ `test_replan_entry_with_stale_go_swaps_atomically` (claims test verifies swap, but it doesn't)
   - ✓ `test_plan_go_on_entry_fast_forwards_without_swap` (accurate: test verifies fast-forward via guard)

2. **Update the docstring to cite the guard that fires FIRST, not later unreachable code.**
   - ❌ "Defense-in-depth protection for the swap logic at line 191"
   - ✓ "The is_plan_go guard fires first and returns ADVANCE; swap block never reached."

3. **Correct inline comments with actual line numbers and explain WHY paths are unreachable.**
   - ❌ Comment at line 206: "# Swap logic here (but defense prevents execution)"
   - ✓ Comment at line 176: "# is_plan_go guard fires first; swap at line 206 never executes"

### Detailed Steps

#### Step 1: Identify Misleading Test Names & Docstrings

Read the test and the function it exercises:

```python
# test_replan_entry_with_stale_go_swaps_atomically — claims "swaps"
def test_replan_entry_with_stale_go_swaps_atomically(self):
    """Atomic swap of plan if stale GO detected."""
    # ... test code ...
```

Then read the function being tested:

```python
def on_enter(self, machine_state):
    # Line 176: guard fires FIRST
    if self.is_plan_go(machine_state):
        return ADVANCE  # Early exit; rest of function never executes

    # Line 206: swap logic (unreachable when is_plan_go=True)
    self._swap_plan(machine_state)
```

**Key question**: Does the test actually trigger the swap at line 206, or does the guard at line 176 fire first?

If the guard fires first, the test does NOT verify the swap — it verifies the fast-forward.

#### Step 2: Rename Test to Match Actual Behavior

Rename to emphasize the actual code path (the guard):

```python
# Old: test_replan_entry_with_stale_go_swaps_atomically
# New: test_plan_go_on_entry_fast_forwards_without_swap
def test_plan_go_on_entry_fast_forwards_without_swap(self):
```

#### Step 3: Update Docstring to Cite the Guard

```python
def test_plan_go_on_entry_fast_forwards_without_swap(self):
    """The is_plan_go guard fires first and returns ADVANCE; swap block never reached."""
    # Test setup: is_plan_go returns True
    # Expected: function returns ADVANCE immediately
    # Assertion: verify no swap was performed
```

#### Step 4: Correct Inline Comments with Line Numbers

In the function being tested, add comments explaining why later code is unreachable:

```python
def on_enter(self, machine_state):
    # Line 176: is_plan_go guard fires first
    if self.is_plan_go(machine_state):
        return ADVANCE  # Short-circuit; lines below never execute

    # Line 206: swap logic unreachable when is_plan_go=True
    # (only executes if is_plan_go=False, which is the opposite test case)
    self._swap_plan(machine_state)
```

#### Step 5: Run Tests Locally

```bash
# Verify test passes with corrected name/docstring
pixi run pytest tests/unit/automation/planning/test_state_machine.py::TestPlanningStages::test_plan_go_on_entry_fast_forwards_without_swap -v

# Verify all state-machine tests pass
pixi run pytest tests/unit/automation/planning/test_state_machine.py -v
```

### Anti-Pattern: "Defense-in-Depth" Docstrings

❌ **Don't claim a test verifies a "defense-in-depth" pattern if the early-exit guard makes later logic unreachable:**

```python
# WRONG: Claims test verifies swap + defense, but only guards prevent swap
def test_replan_entry_with_stale_go_swaps_atomically(self):
    """Defense-in-depth protection for the swap logic.

    The is_plan_go guard defends against incorrect state transitions,
    and the swap logic provides additional protection.
    """
```

✓ **Instead, name and document what the test ACTUALLY verifies:**

```python
# CORRECT: Clear about what fires first
def test_plan_go_on_entry_fast_forwards_without_swap(self):
    """The is_plan_go guard fires first and returns ADVANCE; swap block never reached."""
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Test named `test_replan_entry_with_stale_go_swaps_atomically` with docstring "Defense-in-depth for swap logic" | Claimed the test verifies an atomic swap operation | The actual behavior: `STATE_PLAN_GO` triggers the `is_plan_go` guard at line 176, which returns `ADVANCE` immediately. The swap logic at line 206 never executes; the test verifies the fast-forward, not the swap. Docstring was misleading about what the test actually verified. | Test names and docstrings MUST match actual code paths. When a guard fires first and causes early return, document THAT guard, not later unreachable code. |
| Inline comment explaining swap logic without referencing the guard | Comment said "Swap logic here" but didn't explain why it was unreachable | Reader couldn't tell if the code path executed during the test or was protected by some other mechanism | Inline comments must cite the line number of the guard that prevents execution AND explain why the path is unreachable in this specific test case. |

## Results & Parameters

- **PR**: ProjectHephaestus#1934 (issue #1857), merged with fix for state-machine planning→plan_review deadlock.
- **Test file**: `tests/unit/automation/planning/test_state_machine.py`
- **Before (misleading)**:
  ```python
  def test_replan_entry_with_stale_go_swaps_atomically(self):
      """Atomic swap of plan if stale GO detected."""
  ```
- **After (accurate)**:
  ```python
  def test_plan_go_on_entry_fast_forwards_without_swap(self):
      """The is_plan_go guard fires first and returns ADVANCE; swap block never reached."""
  ```
- **Corrected inline comments**:
  - Line 176 guard: "# is_plan_go guard fires first"
  - Line 206 swap: "# Swap logic unreachable when is_plan_go=True"

## Test Naming Convention

For state-machine tests, use this pattern when documenting fast-forward paths:

```
test_<trigger>_on_<hook>_<early_exit_behavior>_<without_later_path>

Example:
test_plan_go_on_entry_fast_forwards_without_swap
  ├─ test: marker
  ├─ plan_go: the trigger condition (is_plan_go=True)
  ├─ on_entry: the hook/lifecycle point
  ├─ fast_forwards: the early-exit behavior
  └─ without_swap: what does NOT happen
```

## Docstring Template

```python
def test_<name>(self):
    """The <guard_name> guard fires first and returns <early_exit_result>; <later_path> never reached.

    Test verifies:
    - Guard condition: <condition>
    - Early exit: <action>
    - Unreachable code: <path that doesn't execute>
    """
```

## Key Principles

1. **Actual behavior > hypothetical behavior**: Document what the code actually does, not what it could do or what later logic might do.
2. **Guards fire first**: In state machines with early-exit guards, the guard is the primary behavior. Later code is secondary.
3. **Line numbers are load-bearing**: Cite actual line numbers so readers can verify guards and unreachable code.
4. **Inline comments explain WHY, not WHAT**: "Why is this path unreachable in this test?" not "What would this code do?"
5. **Test names + docstrings form a contract**: They must align precisely with actual execution paths.
