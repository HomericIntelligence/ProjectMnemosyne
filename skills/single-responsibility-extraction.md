---
name: single-responsibility-extraction
description: Extracting a complex multi-concern method into a dedicated collaborator
  class using TDD. Use when a method violates SRP, triggers complexity suppressions
  (C901), or mixes 3+ distinct concerns.
category: architecture
date: 2026-02-27
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Single-Responsibility Extraction: Decomposing Complex Methods into Collaborator Classes

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-02-27 |
| **Objective** | Extract a 170-line multi-concern method (`_initialize_or_resume_experiment`) into a dedicated `ResumeManager` class with 4 focused methods |
| **Outcome** | ✅ Success — runner.py reduced 1638→1509 lines, 26 new tests, all 3211 existing tests pass, 78.46% coverage |
| **Root Cause** | `_initialize_or_resume_experiment()` mixed 4 distinct concerns: CLI arg restoration, failed-state reset, tier merging, and incomplete-run detection |
| **Solution** | `ResumeManager` collaborator class with `restore_cli_args()`, `reset_failed_states()`, `merge_cli_tiers_and_reset_incomplete()`, `check_tiers_need_execution()` |

## Problem Statement

When a method grows to combine multiple concerns:
1. It triggers linting complexity suppressions (`# noqa: C901`)
2. Unit testing becomes hard — you must set up all concerns to test any one
3. The parent class accumulates private helpers that belong elsewhere
4. Changes to one concern risk breaking unrelated ones

In this case, `_initialize_or_resume_experiment()` combined:
1. **CLI arg restoration** — reapply CLI `--until` flags over checkpoint-loaded config
2. **Failed-state reset** — reset `failed`/`interrupted` experiment/tier/subtest states
3. **Tier merging** — add new CLI-specified tiers not in the saved checkpoint
4. **Incomplete detection** — detect which tiers need re-execution and reset their states

## When to Use This Skill

Use this pattern when:
- A method has `# noqa: C901` (McCabe complexity) suppression
- A method is >100 lines and handles 3+ distinct logical steps
- Helper methods on the parent class are only called from one method
- The method is hard to unit test without setting up unrelated concerns
- You want to reduce a large file's line count without breaking the API

## Verified Workflow

### Phase 1: Identify Concerns (Read, Don't Write)

Read the target method carefully and label each logical block with a concern:

```python
# CONCERN 1: CLI arg restoration
non_none = {k: v for k, v in cli_ephemeral.items() if v is not None}
self.config = self.config.model_copy(update=non_none)

# CONCERN 2: Failed-state reset
if self.checkpoint.experiment_state in ("failed", "interrupted"):
    self.checkpoint.experiment_state = "tiers_running"
    ...

# CONCERN 3 & 4: Tier merging + incomplete detection
new_tiers = [t for t in cli_tiers if t.value not in existing_tier_ids]
...
needs_execution = self._check_tiers_need_execution(cli_tiers)
```

Also identify **private helpers** that belong to the extracted class:
- `_check_tiers_need_execution()` — only called from step 4
- `_subtest_has_incomplete_runs()` — only called from step 4

### Phase 2: Write Tests First (TDD)

Write tests **before** creating the class. This forces the API design:

```python
# tests/unit/e2e/test_resume_manager.py
from scylla.e2e.resume_manager import ResumeManager

def test_restore_cli_args_non_none_overrides():
    rm = ResumeManager(checkpoint, config, tier_manager)
    config, _ = rm.restore_cli_args({"max_subtests": 5})
    assert config.max_subtests == 5

def test_restore_cli_args_none_keeps_saved():
    config_with_saved = config.model_copy(update={"max_subtests": 3})
    rm = ResumeManager(checkpoint, config_with_saved, tier_manager)
    config, _ = rm.restore_cli_args({"max_subtests": None})
    assert config.max_subtests == 3  # None CLI doesn't override
```

**Key design choice**: Methods return `(config, checkpoint)` tuples rather than mutating self. This makes tests trivial — no need to inspect internal state.

### Phase 3: Implement the Collaborator Class

```python
# scylla/e2e/resume_manager.py

class ResumeManager:
    """Manages experiment resume logic.

    Receives checkpoint, config, and tier_manager as collaborators.
    Methods return updated (config, checkpoint) tuples.
    """

    def __init__(self, checkpoint, config, tier_manager):
        self.checkpoint = checkpoint
        self.config = config
        self.tier_manager = tier_manager

    def restore_cli_args(self, cli_ephemeral):
        non_none = {k: v for k, v in cli_ephemeral.items() if v is not None}
        if non_none:
            self.config = self.config.model_copy(update=non_none)
        return self.config, self.checkpoint

    def reset_failed_states(self):
        if self.checkpoint.experiment_state not in ("failed", "interrupted"):
            return self.config, self.checkpoint
        # ... reset logic ...
        return self.config, self.checkpoint

    def merge_cli_tiers_and_reset_incomplete(self, cli_tiers, checkpoint_path):
        # ... merge + detect + save ...
        return self.config, self.checkpoint
```

### Phase 4: Wire into Parent Class

Replace the method body with a thin shell that delegates to `ResumeManager`:

```python
def _initialize_or_resume_experiment(self) -> Path:
    checkpoint_path = self._find_existing_checkpoint()

    if checkpoint_path and not self._fresh:
        _cli_tiers = list(self.config.tiers_to_run)
        _cli_ephemeral = {
            "until_run_state": self.config.until_run_state,
            "max_subtests": self.config.max_subtests,
            # ...
        }

        try:
            self._load_checkpoint_and_config(checkpoint_path)
            # ... zombie check ...

            if self.checkpoint:
                rm = ResumeManager(self.checkpoint, self.config, self.tier_manager)
                self.config, self.checkpoint = rm.restore_cli_args(_cli_ephemeral)
                self.config, self.checkpoint = rm.reset_failed_states()
                self.config, self.checkpoint = rm.merge_cli_tiers_and_reset_incomplete(
                    _cli_tiers, checkpoint_path
                )
        except Exception as e:
            logger.warning(f"Failed to resume: {e}")
            # ...
    ...
```

**Remove** the extracted private helpers (`_check_tiers_need_execution`, `_subtest_has_incomplete_runs`) from the parent class.

### Phase 5: Fix Pre-commit Issues

Common issues after extraction:

| Issue | Fix |
| ------- | ----- |
| `E501` line too long | Split long logger strings into continuation strings |
| `type-arg` missing dict type params | Use `dict[str, Any]` not `dict` in type annotations |
| Ruff auto-fixes (applied automatically) | Re-run hooks until clean pass |

```python
# E501 fix: split long logger message
logger.info(
    "Resetting experiment from '%s' to 'tiers_running' "
    "— CLI-requested tiers need execution",
    self.checkpoint.experiment_state,
)

# type-arg fix: annotate dict with type params
cli_ephemeral: dict[str, None] = {"max_subtests": None}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| **Mutating self instead of returning** | Initial design considered modifying `self.config` and `self.checkpoint` directly, returning `None` | Hard to test — must inspect object internals; creates hidden coupling | Return `(config, checkpoint)` tuples instead for clean, testable API |
| **Expecting C901 suppressions** | Assumed runner.py had `# noqa: C901` flags to remove | `grep` found none — the method never had explicit suppressions | Always verify the actual state; the issue description may describe the desired end state, not the current one |
| **Re-creating `_save_config`** | Considered delegating to runner's `_save_config` via callback | Over-engineering — `ResumeManager._save_config` can write the JSON directly | Keep collaborator self-contained; don't inject callbacks for simple file writes |

## Key Decisions

| Decision | Rationale |
| ---------- | ----------- |
| **Return tuples, not void** | Makes unit tests trivial — assert on returned values |
| **Collaborator receives checkpoint+config at init** | Avoids passing them to every method; mirrors runner's own pattern |
| **`_save_config` on ResumeManager** | Keeps the class self-contained; runner's `_save_config` is equivalent |
| **Lazy imports inside methods** | `from scylla.e2e.state_machine import is_terminal_state` inside methods avoids circular imports |
| **Don't import `compute_config_hash` in tests** | Mock `_save_config` instead; avoids needing a real config hash |

## Implementation Checklist

When extracting a method into a collaborator class:

- [ ] Read the method and label each concern block
- [ ] Identify private helpers that are only called from this method
- [ ] Write failing tests before creating the class (TDD)
- [ ] Design the API around return values (not mutation) for testability
- [ ] Create the collaborator in a new file (`<concern>_manager.py`)
- [ ] Move private helpers to the collaborator
- [ ] Replace the method body with a thin delegation shell
- [ ] Remove extracted helpers from the parent class
- [ ] Add import to parent class
- [ ] Run pre-commit hooks and fix line-length / type-annotation issues
- [ ] Run full test suite (not just new tests — coverage threshold must pass)

## Results & Parameters

**Files modified**:
1. `scylla/e2e/runner.py` — 1638→1509 lines (−129); thin delegation shell
2. `scylla/e2e/resume_manager.py` — new file, 175 lines, 98.53% coverage
3. `tests/unit/e2e/test_resume_manager.py` — new file, 26 tests across 5 test classes

**Test results**:
- 26 new unit tests, all passing
- 3211 total tests passing (0 regressions)
- 78.46% overall coverage (threshold: 75%)

**Pre-commit**: All hooks pass (ruff format, ruff check, mypy, security, structure)

**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1145

## References

- Issue: [#1110 Decompose runner.py _initialize_or_resume_experiment() into ResumeManager](https://github.com/HomericIntelligence/ProjectScylla/issues/1110)
- Related skill: `architecture/e2e-resume-refactor` — earlier checkpoint schema refactor
- SOLID principles: Single Responsibility Principle
- Ruff complexity rule: [C901](https://docs.astral.sh/ruff/rules/complex-structure/)
