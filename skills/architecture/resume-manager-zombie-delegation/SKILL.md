# Skill: ResumeManager Zombie Delegation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-27 |
| Objective | Move inline zombie detection out of `_initialize_or_resume_experiment()` into `ResumeManager.handle_zombie()` |
| Outcome | Success — clean sequential call chain, all logic in ResumeManager, 3260 tests pass |
| PR | HomericIntelligence/ProjectScylla#1221 |
| Issue | HomericIntelligence/ProjectScylla#1148 (follow-up from #1110) |

## When to Use

Use this pattern when:
- A method delegates most logic to a manager/strategy object but retains one inline block
- The inline block imports a module lazily (inside the if-branch) rather than at module level
- The block is short (4–6 lines) and has clear preconditions (`if self.checkpoint and self.experiment_dir`)
- You want the caller to have a clean linear call chain (`rm.step1(); rm.step2(); rm.step3()`)

## Context: The Problem

`_initialize_or_resume_experiment()` in `runner.py` delegated 3 resume steps to `ResumeManager`, but one step — zombie detection — remained inline between the checkpoint load and the `ResumeManager` instantiation:

```python
# Before: zombie check inline, OUTSIDE ResumeManager
if self.checkpoint and self.experiment_dir:
    from scylla.e2e.health import is_zombie, reset_zombie_checkpoint
    if is_zombie(self.checkpoint, self.experiment_dir):
        logger.warning("Zombie experiment detected — resetting to 'interrupted'")
        self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)

if self.checkpoint:
    rm = ResumeManager(self.checkpoint, self.config, self.tier_manager)
    self.config, self.checkpoint = rm.restore_cli_args(_cli_ephemeral)
    self.config, self.checkpoint = rm.reset_failed_states()
    self.config, self.checkpoint = rm.merge_cli_tiers_and_reset_incomplete(...)
```

This was the only remaining logic not delegated to `ResumeManager`.

## Verified Workflow

### Step 1: Move imports to module level in resume_manager.py

```python
# resume_manager.py — top-level imports
from scylla.e2e.health import is_zombie, reset_zombie_checkpoint
```

Moving from lazy inline import to module-level import is important: it means the mock target
for tests becomes `scylla.e2e.resume_manager.is_zombie` (the name as imported into the module),
NOT `scylla.e2e.health.is_zombie`.

### Step 2: Add handle_zombie() as the first public method

```python
def handle_zombie(
    self,
    checkpoint_path: Path,
    experiment_dir: Path | None,
) -> tuple[ExperimentConfig, E2ECheckpoint]:
    """Check for zombie experiment and reset checkpoint if detected."""
    if experiment_dir is None:
        return self.config, self.checkpoint

    if is_zombie(self.checkpoint, experiment_dir):
        logger.warning("Zombie experiment detected — resetting to 'interrupted'")
        self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)

    return self.config, self.checkpoint
```

Key design decisions:
- `experiment_dir: Path | None` — accepts None to handle the case where no experiment dir exists yet (early resume path); method is a no-op in that case
- Returns `(config, checkpoint)` tuple — consistent with all other `ResumeManager` methods
- Mutates `self.checkpoint` in-place so subsequent method calls (`restore_cli_args`, etc.) use the reset checkpoint

### Step 3: Update runner.py to use the clean call chain

```python
# After: all 4 steps delegated to ResumeManager
if self.checkpoint:
    rm = ResumeManager(self.checkpoint, self.config, self.tier_manager)

    # STEP 1 (continued): Check for zombie (crashed) experiment
    self.config, self.checkpoint = rm.handle_zombie(
        checkpoint_path, self.experiment_dir
    )

    # STEP 2: Restore ephemeral CLI args
    self.config, self.checkpoint = rm.restore_cli_args(_cli_ephemeral)

    # STEP 3: Reset failed/interrupted states for re-execution
    self.config, self.checkpoint = rm.reset_failed_states()

    # STEP 4: Merge CLI tiers and reset incomplete tier/subtest states
    self.config, self.checkpoint = rm.merge_cli_tiers_and_reset_incomplete(
        _cli_tiers, checkpoint_path
    )
```

### Step 4: Write unit tests for handle_zombie()

Three test cases covering all branches:

```python
class TestHandleZombie:
    def test_zombie_detected_resets_checkpoint(...):
        # Asserts: is_zombie called once, reset_zombie_checkpoint called once,
        # returned checkpoint.status == "interrupted"

    def test_no_zombie_checkpoint_unchanged(...):
        # Asserts: is_zombie called once, reset_zombie_checkpoint NOT called,
        # returned checkpoint is same object

    def test_experiment_dir_none_is_noop(...):
        # Asserts: neither is_zombie nor reset_zombie_checkpoint called
```

### Step 5: Update mock paths in test_runner.py

**Critical**: mock the name in the module where it was imported, not where it was defined.

```python
# WRONG — health module, not where it's used after moving to module-level import
patch("scylla.e2e.health.is_zombie", return_value=False)

# CORRECT — resume_manager module, where is_zombie is now imported at module level
patch("scylla.e2e.resume_manager.is_zombie", return_value=False)
```

There were 6 occurrences in `test_runner.py` to update.

## Failed Attempts

None — the approach was straightforward once the mock path rule was understood.

## Key Rule: Mock Patch Paths After Import Refactoring

When moving an import from **lazy/inline** (`from x import y` inside a function) to **module-level**,
the mock patch path MUST change:

| Import style | Correct patch target |
|---|---|
| Lazy: `from scylla.e2e.health import is_zombie` inside method | `scylla.e2e.health.is_zombie` |
| Module-level: `from scylla.e2e.health import is_zombie` at top | `scylla.e2e.resume_manager.is_zombie` |

Python's `unittest.mock.patch` replaces the name in the namespace where it is **looked up at call time**,
not where it was originally defined. After moving to a module-level import, the calling module
(`resume_manager`) holds its own binding to the function, so that's what needs to be patched.

## Results

| Metric | Value |
|--------|-------|
| Tests | 3260 passed |
| Coverage | 78.41% (threshold 75%) |
| Files changed | 4 |
| Lines added | +125 |
| Lines removed | -14 |
| Pre-commit hooks | All pass |
