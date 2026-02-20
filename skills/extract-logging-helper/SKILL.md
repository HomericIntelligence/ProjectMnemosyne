# Extract Logging Helper

Workflow for eliminating duplicate `logger.info/warning` calls by extracting a void helper method, with mock-logger test patterns.

## Overview

| Attribute | Details |
|-----------|---------|
| **Date** | 2026-02-19 |
| **Objective** | Extract duplicate checkpoint resume logging from two branches into `_log_checkpoint_resume()` |
| **Outcome** | ✅ Success — 2 duplicate logging blocks → 1 helper, 5 new tests, no behavior change |
| **Issue** | #713 (follow-up from #639) |
| **PR** | #761 |

## When to Use This Skill

Use when you encounter:

- **Identical `logger.info/warning` blocks** appearing in 2+ branches of a method
- **Logging in both the success and fallback paths** of a conditional
- **DRY violation review comment** mentioning duplicated log messages
- **Follow-up issues** from a prior extract-method refactoring noting residual duplication

**Trigger phrases**:

- "Duplicate logging in both branches"
- "Extract logging helper"
- "Same log messages appear in success and fallback"
- "Consider extracting `_log_*` helper"

## Key Difference from Generic DRY Refactoring

Logging helpers are **void methods** (`-> None`) with **side effects only** — no return value to test directly.
This requires a different test pattern: **mock the logger** and assert on `call()` objects, not return values.

## Verified Workflow

### Phase 1: Identify & Confirm Duplication

1. Read both branches carefully — confirm the *messages* are truly identical, not just similar.
2. Note any lines that differ between branches (those stay in-place, only the shared lines move).

```python
# BEFORE — duplicated in if and else:
if saved_config_path.exists():
    logger.info(f"📂 Resuming from checkpoint: {checkpoint_path}")
    logger.info(f"📋 Loading config from checkpoint: {saved_config_path}")  # unique
    self.config = ExperimentConfig.load(saved_config_path)
    logger.info(f"   Previously completed: {self.checkpoint.get_completed_run_count()} runs")
else:
    logger.warning(...)  # unique
    if not validate_checkpoint_config(...): raise ValueError(...)  # unique
    logger.info(f"📂 Resuming from checkpoint: {checkpoint_path}")  # ← duplicate
    logger.info(f"   Previously completed: {self.checkpoint.get_completed_run_count()} runs")  # ← duplicate
```

### Phase 2: Place the Helper Method

Insert the helper **just before** the method that will call it, keeping related methods together.

```python
def _log_checkpoint_resume(self, checkpoint_path: Path) -> None:
    """Log checkpoint resume status with completed run count.

    Args:
        checkpoint_path: Path to checkpoint.json file

    """
    logger.info(f"📂 Resuming from checkpoint: {checkpoint_path}")
    logger.info(
        f"   Previously completed: {self.checkpoint.get_completed_run_count()} runs"
    )
```

**Key details**:
- Return type is `-> None` (no return value — pure side effect)
- Docstring uses the same Args format as other helpers in the class
- The method accesses `self.checkpoint` — verify it's set before the call sites

### Phase 3: Update Call Sites

```python
# AFTER:
if saved_config_path.exists():
    self._log_checkpoint_resume(checkpoint_path)  # ← moved to top of branch
    logger.info(f"📋 Loading config from checkpoint: {saved_config_path}")
    self.config = ExperimentConfig.load(saved_config_path)
else:
    logger.warning(...)
    if not validate_checkpoint_config(...): raise ValueError(...)
    self._log_checkpoint_resume(checkpoint_path)  # ← end of fallback branch
```

Note: The order of the shared log messages **relative to branch-specific lines** may differ between
branches — preserve the original intent, not just mechanical replacement.

### Phase 4: Test with Mock Logger

Testing a void logging helper requires patching `logger` and asserting on `call()` objects:

```python
from unittest.mock import MagicMock, call, patch

class TestLogCheckpointResume:
    """Tests for _log_checkpoint_resume helper method."""

    def test_logs_checkpoint_path(self, mock_config, mock_tier_manager):
        runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
        runner.checkpoint = MagicMock()
        runner.checkpoint.get_completed_run_count.return_value = 5

        checkpoint_path = Path("/tmp/checkpoint.json")
        with patch("scylla.e2e.runner.logger") as mock_logger:
            runner._log_checkpoint_resume(checkpoint_path)

        mock_logger.info.assert_any_call(f"📂 Resuming from checkpoint: {checkpoint_path}")

    def test_logs_both_messages_in_order(self, mock_config, mock_tier_manager):
        runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
        runner.checkpoint = MagicMock()
        runner.checkpoint.get_completed_run_count.return_value = 3

        checkpoint_path = Path("/tmp/exp/checkpoint.json")
        with patch("scylla.e2e.runner.logger") as mock_logger:
            runner._log_checkpoint_resume(checkpoint_path)

        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_has_calls([
            call(f"📂 Resuming from checkpoint: {checkpoint_path}"),
            call("   Previously completed: 3 runs"),
        ])

    def test_load_checkpoint_success_path_calls_helper(self, mock_config, mock_tier_manager, tmp_path):
        """Verify the helper is actually called from both branches."""
        runner = E2ERunner(mock_config, mock_tier_manager, tmp_path)
        # ... set up checkpoint + config files ...
        with (
            patch("scylla.e2e.runner.load_checkpoint", return_value=mock_checkpoint),
            patch.object(runner, "_log_checkpoint_resume") as mock_log,
        ):
            runner._load_checkpoint_and_config(checkpoint_path)
        mock_log.assert_called_once_with(checkpoint_path)
```

**Test checklist for void logging helpers**:
- [ ] Test each message individually with `assert_any_call`
- [ ] Test message ordering with `assert_has_calls` + `call_count`
- [ ] Test that calling methods invoke helper with `patch.object(runner, "_log_*")` + `assert_called_once_with`
- [ ] Cover both the success path and the fallback path

### Phase 5: Quality Checks

```bash
pre-commit run --files scylla/e2e/runner.py tests/unit/e2e/test_runner.py
```

Ruff will collapse single-line f-strings inside `logger.info(...)` — let it reformat, then re-run to confirm green.

## Failed Attempts

### None in this session

The implementation was straightforward once the call-site ordering was confirmed. The main subtlety was
ensuring `_log_checkpoint_resume` was placed **before** `_load_checkpoint_and_config` in the class body.

## Results & Parameters

### Code Changes

| File | Change |
|------|--------|
| `scylla/e2e/runner.py` | +12 lines (helper) / -9 lines (deduplication) |
| `tests/unit/e2e/test_runner.py` | +103 lines (5 new tests) |

### Test Coverage

**New tests**: 5

- `test_logs_checkpoint_path` — message content assertion
- `test_logs_completed_run_count` — dynamic count assertion
- `test_logs_both_messages_in_order` — ordering assertion
- `test_load_checkpoint_success_path_calls_helper` — success path integration
- `test_load_checkpoint_fallback_path_calls_helper` — fallback path integration

**All 9 tests pass** (4 pre-existing + 5 new)

### Mock Logger Pattern (copy-paste ready)

```python
# Patch the module-level logger, not the stdlib logging module
with patch("scylla.e2e.runner.logger") as mock_logger:
    runner._log_checkpoint_resume(checkpoint_path)

# Single message check:
mock_logger.info.assert_any_call("expected message")

# Ordered multi-message check:
mock_logger.info.assert_has_calls([call("msg1"), call("msg2")])
assert mock_logger.info.call_count == 2
```

## Related Skills

- `dry-refactoring-workflow` — General DRY extraction workflow
- `extract-method-refactoring` — Extract Method for long methods (issue #639)

## Tags

`refactoring`, `dry-principle`, `logging`, `helper-methods`, `mock-logger`, `pytest`, `void-method`, `tdd`
