---
name: immutable-method-refactor
description: "Refactoring a class method to follow an immutable (purely functional)\
  \ pattern by removing in-place self.attribute mutation and returning a new value\
  \ instead. Use when a class has mixed patterns \u2014 some methods mutate self and\
  \ some return new values \u2014 and consistency is needed."
category: architecture
date: 2026-03-02
version: 1.0.0
mcp_fallback: none
tier: 1
---
# Immutable Method Refactor: Making handle_zombie Purely Functional

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-03-02 |
| **Objective** | Remove `self.checkpoint` mutation from `handle_zombie()` to match the immutable pattern of sibling methods |
| **Outcome** | ✅ Success — 2-line change, all 30 tests pass, new immutability assertion added |
| **Root Cause** | `handle_zombie()` assigned `self.checkpoint = reset_zombie_checkpoint(...)` while `restore_cli_args` and `reset_failed_states` used `model_copy()` and returned new objects |
| **Solution** | Assign to local variable, return via early-return; add test assertion `rm.checkpoint is original_checkpoint` |

## Problem Statement

`ResumeManager.handle_zombie()` had a dual-write pattern:

```python
# BEFORE: mutates self AND returns the value
self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
return self.config, self.checkpoint
```

The caller did:

```python
self.config, self.checkpoint = rm.handle_zombie(...)
```

This worked in practice, but violated the immutable contract of the class. If a future caller
only checked `rm.checkpoint` instead of unpacking the return value, it would see the mutated
value — creating a hidden coupling between method call and internal state.

Sibling methods `restore_cli_args` and `reset_failed_states` used `self.config.model_copy(update=...)`
and returned `(self.config, self.checkpoint)` without mutating self. `handle_zombie` was the
one inconsistent method.

## When to Use This Skill

Apply this pattern when:
- A class has methods that **mostly return updated (config, checkpoint) tuples** but one mutates `self`
- You want to enforce a **purely functional / immutable API** so callers must use the return value
- You need a **test-enforced contract** that `self.attribute` is never mutated by a method
- The mutation was **incidental** (assigned before returning), not load-bearing state

## Verified Workflow

### Step 1: Identify the Inconsistency

Look for methods that both mutate `self.X` and return a value containing `self.X`:

```python
# Red flag: assign-then-return pattern
self.checkpoint = some_function(self.checkpoint, ...)
return self.config, self.checkpoint  # returns the mutated self.checkpoint
```

Compare with sibling methods to confirm the intended pattern is purely functional (return-only).

### Step 2: Refactor to Local Variable + Early Return

```python
# BEFORE
if is_zombie(self.checkpoint, experiment_dir, heartbeat_timeout_seconds):
    logger.warning("Zombie experiment detected — resetting to 'interrupted'")
    self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)

return self.config, self.checkpoint

# AFTER
if is_zombie(self.checkpoint, experiment_dir, heartbeat_timeout_seconds):
    logger.warning("Zombie experiment detected — resetting to 'interrupted'")
    reset_checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
    return self.config, reset_checkpoint

return self.config, self.checkpoint
```

Key points:
- Use a **descriptively named local variable** (`reset_checkpoint`)
- Use **early return** in the mutating branch so `self.checkpoint` is never touched
- The non-zombie path already returned `self.checkpoint` unchanged — no change needed there

### Step 3: Add Immutability Assertion to the Test

```python
def test_zombie_detected_resets_checkpoint(...):
    rm = _make_manager(base_checkpoint, base_config, mock_tier_manager)
    original_checkpoint = rm.checkpoint  # capture reference BEFORE call

    with patch("...is_zombie", return_value=True), \
         patch("...reset_zombie_checkpoint", return_value=reset_checkpoint):
        config, checkpoint = rm.handle_zombie(checkpoint_path, experiment_dir)

    assert checkpoint.status == "interrupted"
    assert config is base_config
    # NEW: enforce the immutable contract — self.checkpoint must NOT change
    assert rm.checkpoint is original_checkpoint
```

This test will **fail** if anyone re-introduces the mutation, making the contract explicit.

### Step 4: Verify Tests Pass

```bash
pixi run pytest tests/unit/e2e/test_resume_manager.py --override-ini="addopts=" -v --strict-markers
```

Expected: all tests pass including the new assertion.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Files changed**: 2
- `scylla/e2e/resume_manager.py`: 3 lines changed (removed mutation, added local var, early return)
- `tests/unit/e2e/test_resume_manager.py`: 3 lines added (capture original, add assertion)

**Test count**: 30 unit tests, all passing

**PR**: HomericIntelligence/ProjectScylla#1311

## Key Insight

The dual-write pattern (`self.X = f(...); return self.X`) is a subtle inconsistency that works
in isolation but creates risk when the class is used in multi-caller contexts. The fix is:

1. **Never assign to `self.attribute`** in a method that is supposed to be purely functional
2. **Use early return** in branches that produce a new value
3. **Assert `rm.attr is original_attr`** in tests to lock the contract in permanently
