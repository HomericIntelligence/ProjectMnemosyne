# Skill: Unit Tests for RuntimeError Precondition Guards

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-27 |
| Project | ProjectScylla |
| Objective | Add unit tests covering all `if x is None: raise RuntimeError(...)` guards added in #1066 |
| Outcome | Success — 8 new tests pass, full suite 3265 passed, 78.42% coverage |
| Issue | HomericIntelligence/ProjectScylla#1144 |
| PR | HomericIntelligence/ProjectScylla#1210 |

## When to Use

Use this skill when:
- Adding `if x is None: raise RuntimeError(...)` precondition guards to production code
- Writing regression tests to prevent guards from being silently removed or weakened
- Verifying precondition contracts documented via RuntimeError (as opposed to assert)
- Testing multi-guard functions with parametrize to keep tests DRY

## Key Principle: Guards Over Asserts

ProjectScylla uses `if x is None: raise RuntimeError(...)` instead of `assert x is not None` for precondition checks because:
- `assert` can be disabled with Python's `-O` flag
- `RuntimeError` fires unconditionally and is testable with `pytest.raises`
- The guard pattern documents preconditions as explicit contracts in the error message

## Verified Workflow

### 1. Find Guards to Test

```bash
grep -n "raise RuntimeError" scylla/e2e/stages.py scylla/e2e/runner.py
```

Look for the pattern:
```python
if ctx.some_field is None:
    raise RuntimeError("some_field must be set before ...")
```

### 2. Single-Guard Test (Simple Form)

```python
class TestMyFunctionGuard:
    """Tests for the RuntimeError guard in my_function."""

    def test_raises_when_field_is_none(self, my_fixture: MyContext) -> None:
        """my_function raises RuntimeError when ctx.field is None."""
        my_fixture.field = None

        with pytest.raises(RuntimeError, match=r"field"):
            my_function(my_fixture)
```

**Key**: Use `match=r"field"` (the field name) — the guard message always contains the field name.

### 3. Multi-Guard Test (Parametrized Form)

When a function has multiple sequential guards, use `@pytest.mark.parametrize` to test each one in isolation:

```python
class TestStageFinalizeRunGuards:
    """Tests for RuntimeError guards in stage_finalize_run."""

    @pytest.mark.parametrize(
        "field,expected_match",
        [
            ("agent_result", r"agent_result"),
            ("judgment", r"judgment"),
        ],
    )
    def test_raises_when_field_is_none(
        self, stage_context: RunContext, field: str, expected_match: str
    ) -> None:
        """stage_finalize_run raises RuntimeError when the required field is None."""
        from scylla.adapters.base import AdapterResult, AdapterTokenStats

        # Set up all fields with valid values first
        stage_context.agent_result = AdapterResult(
            exit_code=0, stdout="output", stderr="",
            token_stats=AdapterTokenStats(), cost_usd=0.0, api_calls=0,
        )
        stage_context.judgment = {
            "score": 0.9, "passed": True, "grade": "A",
            "reasoning": "ok", "criteria_scores": {},
        }
        # Null out the specific field under test
        setattr(stage_context, field, None)

        with pytest.raises(RuntimeError, match=expected_match):
            stage_finalize_run(stage_context)
```

**Key**: Set all required fields to valid values first, then null out only the field being tested. This ensures the guard under test fires (not an earlier guard).

### 4. Dependent-Guard Test (Pre-build then null)

When a guard requires a previous stage to have run (e.g., `write_report` requires `run_result` which is set by `finalize_run`):

```python
class TestStageWriteReportGuards:
    @pytest.mark.parametrize(
        "field,expected_match",
        [
            ("run_result", r"run_result"),
            ("agent_result", r"agent_result"),
            ("judgment", r"judgment"),
        ],
    )
    def test_raises_when_field_is_none(
        self, stage_context: RunContext, field: str, expected_match: str
    ) -> None:
        # Set up valid state
        stage_context.agent_result = AdapterResult(...)
        stage_context.judgment = {"score": 0.9, "passed": True, ...}
        stage_context.agent_duration = 1.0
        stage_context.judge_duration = 1.0
        # Build run_result via the real upstream stage (not a mock)
        stage_finalize_run(stage_context)

        # Now null out the specific field
        setattr(stage_context, field, None)

        with pytest.raises(RuntimeError, match=expected_match):
            stage_write_report(stage_context)
```

**Key**: Call the real upstream stage to produce dependent state, then null out the field.

### 5. Runner-Level Guard Test (Patching to Force the Guard)

For guards that fire inside complex methods (like `_initialize_or_resume_experiment`), patch intermediate methods to force the guard:

```python
class TestInitializeOrResumeExperimentGuard:
    def test_raises_when_experiment_dir_is_none_after_create(
        self, mock_config: ExperimentConfig, mock_tier_manager: MagicMock
    ) -> None:
        """Raises RuntimeError when experiment_dir stays None."""
        runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
        # No existing checkpoint → tries to create fresh experiment.
        # Patch _create_fresh_experiment as a no-op so experiment_dir stays None.
        with patch.object(runner, "_find_existing_checkpoint", return_value=None):
            with patch.object(runner, "_create_fresh_experiment"):
                with patch.object(runner, "_write_pid_file"):
                    with pytest.raises(RuntimeError, match=r"experiment_dir"):
                        runner._initialize_or_resume_experiment()
```

**Key**: Identify what side-effect sets the field, patch it out as a no-op, and let the guard fire.

### 6. Simple Attribute-Null Guard Test (E2ERunner methods)

For simple guards where self.checkpoint is accessed:

```python
class TestLogCheckpointResumeGuard:
    def test_raises_when_checkpoint_is_none(
        self, mock_config: ExperimentConfig, mock_tier_manager: MagicMock
    ) -> None:
        runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
        runner.checkpoint = None  # Override the initialized value

        with pytest.raises(RuntimeError, match=r"checkpoint"):
            runner._log_checkpoint_resume(Path("/tmp/checkpoint.json"))
```

## Guards Covered in This Session (ProjectScylla #1144)

| Guard Location | Field Tested | Test Class |
|---|---|---|
| `runner.py: _log_checkpoint_resume` | `self.checkpoint` | `TestLogCheckpointResumeGuard` |
| `runner.py: _initialize_or_resume_experiment` | `self.experiment_dir` | `TestInitializeOrResumeExperimentGuard` |
| `stages.py: stage_execute_agent` | `ctx.adapter_config` | `TestStageExecuteAgentGuard` |
| `stages.py: stage_finalize_run` | `ctx.agent_result` | `TestStageFinalizeRunGuards` |
| `stages.py: stage_finalize_run` | `ctx.judgment` | `TestStageFinalizeRunGuards` |
| `stages.py: stage_write_report` | `ctx.run_result` | `TestStageWriteReportGuards` |
| `stages.py: stage_write_report` | `ctx.agent_result` | `TestStageWriteReportGuards` |
| `stages.py: stage_write_report` | `ctx.judgment` | `TestStageWriteReportGuards` |

---

## Follow-Up: Closure and Inline Guards (ProjectScylla #1214)

Issue #1214 added guard tests for `_run_tier()` and `_run_experiment()` inner closures that were not
covered by #1144. These guards live inside closures returned from action-builder methods, or inline in
`run()`, requiring different test approaches.

### 7. Closure Guard Test (Action Builder Pattern)

When guards live inside closures returned from a builder method (`_build_experiment_actions`, `TierActionBuilder.build()`), call the builder to get the closure dict, null the required attribute, and invoke the closure directly:

```python
class TestBuildExperimentActionsGuards:
    """Tests for None-guard in action_tiers_complete closure inside _build_experiment_actions."""

    def test_action_tiers_complete_raises_when_experiment_dir_none(
        self,
        mock_config: ExperimentConfig,
        mock_tier_manager: MagicMock,
    ) -> None:
        """action_tiers_complete raises RuntimeError when experiment_dir is None."""
        from datetime import datetime, timezone
        from scylla.e2e.models import ExperimentState

        runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
        runner.experiment_dir = None

        tier_results: dict[TierID, TierResult] = {}
        actions = runner._build_experiment_actions(
            tier_groups=[[TierID.T0]],
            scheduler=None,
            tier_results=tier_results,
            start_time=datetime.now(timezone.utc),
        )

        with pytest.raises(
            RuntimeError, match="experiment_dir must be set before aggregating tier results"
        ):
            actions[ExperimentState.TIERS_COMPLETE]()
```

**Key**: No state machine needed — call the builder, get back the closure dict, invoke the specific key.

### 8. Inline Guard in run() — Guard 1 (Before Heartbeat)

For guards that fire early in `run()` because `self.checkpoint` is None after `_initialize_or_resume_experiment()`:

```python
class TestRunCheckpointGuards:
    def test_heartbeat_guard_raises_when_checkpoint_none(
        self,
        mock_config: ExperimentConfig,
        mock_tier_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """run() raises RuntimeError when checkpoint is None at heartbeat creation."""
        runner = E2ERunner(mock_config, mock_tier_manager, tmp_path)

        def fake_init() -> Path:
            # runner.checkpoint remains None — do NOT set it
            return tmp_path / "checkpoint.json"

        with (
            patch.object(runner, "_initialize_or_resume_experiment", side_effect=fake_init),
            pytest.raises(
                RuntimeError,
                match="checkpoint must be set before starting heartbeat thread",
            ),
        ):
            runner.run()
```

**Key**: Patch `_initialize_or_resume_experiment` to be a no-op that returns a path but never sets `runner.checkpoint`. The guard fires immediately.

### 9. Inline Guard in run() — Guard 2 (Before ESM, After Heartbeat)

When a second guard fires *after* a first guard (so the first must not fire), use a side-effect on the intermediate object (HeartbeatThread) to clear the checkpoint just before the second guard:

```python
    def test_esm_guard_raises_when_checkpoint_none_at_esm_creation(
        self,
        mock_config: ExperimentConfig,
        mock_tier_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """run() raises RuntimeError when checkpoint is None at ESM creation."""
        from scylla.e2e.checkpoint import E2ECheckpoint

        runner = E2ERunner(mock_config, mock_tier_manager, tmp_path)
        checkpoint = E2ECheckpoint(
            experiment_id="test-exp",
            experiment_dir=str(tmp_path),
            config_hash="abc123",
            started_at="2024-01-01T00:00:00+00:00",
            last_updated_at="2024-01-01T00:00:00+00:00",
            status="running",
        )

        def fake_init() -> Path:
            runner.checkpoint = checkpoint   # Guard 1 passes
            return tmp_path / "checkpoint.json"

        mock_heartbeat = MagicMock()

        def clear_checkpoint_on_start() -> None:
            runner.checkpoint = None         # Guard 2 will now fire

        mock_heartbeat.start.side_effect = clear_checkpoint_on_start

        with (
            patch.object(runner, "_initialize_or_resume_experiment", side_effect=fake_init),
            patch("scylla.e2e.health.HeartbeatThread", return_value=mock_heartbeat),
            pytest.raises(
                RuntimeError,
                match="checkpoint must be set before creating experiment state machine",
            ),
        ):
            runner.run()
```

**Critical**: Patch `scylla.e2e.health.HeartbeatThread` (the module where it is defined), NOT `scylla.e2e.runner.HeartbeatThread`. The runner uses a *local import* (`from scylla.e2e.health import HeartbeatThread`), so patching the runner module attribute fails with `AttributeError`.

### Local-Import Patch Target Rule

When a production method uses a **local import** like `from module.sub import Class`, patching the caller's namespace won't work:

```python
# runner.py
def run(self):
    from scylla.e2e.health import HeartbeatThread  # local import
    heartbeat = HeartbeatThread(...)
```

```python
# WRONG — runner module has no HeartbeatThread attribute at import time
patch("scylla.e2e.runner.HeartbeatThread", ...)
# → AttributeError: module 'scylla.e2e.runner' does not have the attribute 'HeartbeatThread'

# CORRECT — patch where the class is defined
patch("scylla.e2e.health.HeartbeatThread", ...)
```

This applies to any `from x import Y` inside a function body. Always patch `x.Y`, not `caller.Y`.

## Guards Covered in Follow-Up Session (ProjectScylla #1214)

| Guard Location | Field Tested | Test Class |
|---|---|---|
| `runner.py: _build_experiment_actions / action_tiers_complete` | `self.experiment_dir` | `TestBuildExperimentActionsGuards` |
| `runner.py: run() ~line 688` | `self.checkpoint` (heartbeat) | `TestRunCheckpointGuards` |
| `runner.py: run() ~line 730` | `self.checkpoint` (ESM) | `TestRunCheckpointGuards` |
| `tier_action_builder.py: action_pending` | `experiment_dir` | `TestActionPending` (in test_tier_action_builder.py) |
| `tier_action_builder.py: action_config_loaded` ×3 | `tier_config`, `tier_dir`, `experiment_dir` | `TestActionConfigLoaded` |
| `tier_action_builder.py: action_subtests_running` | `tier_dir` | `TestActionSubtestsRunning` |
| `tier_action_builder.py: action_subtests_complete` | `selection` | `TestActionSubtestsComplete` |
| `tier_action_builder.py: action_best_selected` | `tier_result` | `TestActionBestSelected` |

## Failed Attempts

### 1. Trying to Test All Guards in One Parametrize Call

**Problem**: Attempted to test all 3 `write_report` guards plus all 2 `finalize_run` guards in a single `@pytest.mark.parametrize`. This fails because:
- `write_report` requires `run_result` (set by `finalize_run`) to be present for `agent_result` and `judgment` guards to fire — you can't set up both contexts in a single fixture teardown.
- The `run_result` guard fires first, so you can't test `agent_result` guard without a valid `run_result`.

**Fix**: Use separate test classes (`TestStageFinalizeRunGuards` and `TestStageWriteReportGuards`) with different setup logic, calling `stage_finalize_run` as the setup step inside `TestStageWriteReportGuards`.

### 2. Forgetting `criteria_scores` in `judgment` dict

**Problem**: `stage_finalize_run` accesses `judgment["criteria_scores"]` when building the `E2ERunResult`. Tests that omitted this key caused a `KeyError` before reaching the guard.

**Fix**: Always include `"criteria_scores": {}` in the judgment dict used for setup.

### 3. `_find_existing_checkpoint` not patched in runner guard test

**Problem**: Without patching `_find_existing_checkpoint`, the runner checks the real filesystem for a checkpoint file, which doesn't exist in a unit test — it raises `FileNotFoundError` before the guard.

**Fix**: `patch.object(runner, "_find_existing_checkpoint", return_value=None)` to simulate no existing checkpoint.

## Results & Parameters

### Test counts added
- 1 test in `TestLogCheckpointResumeGuard`
- 1 test in `TestInitializeOrResumeExperimentGuard`
- 1 test in `TestStageExecuteAgentGuard`
- 2 parametrized tests in `TestStageFinalizeRunGuards`
- 3 parametrized tests in `TestStageWriteReportGuards`
- **Total: 8 new tests**

### Full suite result
```
3265 passed, 9 warnings in 50.37s
Coverage: 78.42% (threshold: 75%)
```

### Match pattern convention
Always use the field name as the match regex — guards follow the pattern:
```python
raise RuntimeError(f"{field_name} must be set before {function_name}")
```
So `match=r"agent_result"` will always match the guard message for `agent_result`.
