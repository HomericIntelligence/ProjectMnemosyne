---
name: state-machine-interrupt-handling
description: "Pattern for handling Ctrl+C/SIGINT interrupts in multi-level state machine\
  \ hierarchies without marking states FAILED. Use when subprocess.run() returns normally\
  \ after SIGINT but you want runs to stay resumable; or when a sentinel exception\
  \ must propagate through 4 state machine levels (run\u2192subtest\u2192tier\u2192\
  experiment) without triggering FAILED at any level. Also covers wiring hierarchical\
  \ state machines (Experiment \u2192 Tier \u2192 Run) into a production runner using\
  \ closure-based action maps."
category: architecture
date: 2026-02-27
version: 1.1.0
user-invocable: false
absorbed:
  - state-machine-wiring
---
# State Machine Interrupt Handling (Ctrl+C / SIGINT)

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-02-27 |
| Branch | `fix-resume-issues-triple-bug` |
| Objective | When Ctrl+C kills a subprocess, leave runs at their last good state (not FAILED) so they can be retried cleanly on the next invocation |
| Outcome | SUCCESS — 3121 tests pass, 78.10% coverage. Ctrl+C leaves runs at `REPLAY_GENERATED` (not `AGENT_COMPLETE` with broken output) |

## When to Use

- You use `subprocess.run()` to launch a child process, and Ctrl+C sends SIGINT to the OS process group — `subprocess.run()` returns **normally** (no Python exception) with a signal exit code
- Your state machine only advances the checkpoint state **after** a stage completes — so an incomplete stage should leave the run at the prior state
- You have a multi-level hierarchy (e.g. run→subtest→tier→experiment) and each level has `except Exception` that marks states `FAILED`
- You want `Ctrl+C` interrupts to be resumable (not permanently failed), while genuine errors still mark `FAILED`
- You use `ProcessPoolExecutor` with a safe wrapper that converts all exceptions to structured results — you need the interrupt to propagate through the wrapper instead

## The Core Problem: subprocess.run() Doesn't Raise on SIGINT

When Ctrl+C is pressed, the OS sends SIGINT to all processes in the process group. The agent subprocess dies, but from Python's perspective:

```python
result = subprocess.run(["bash", "replay.sh"], ...)
# ↑ Returns NORMALLY with result.returncode = -2 (SIGINT)
# No exception is raised — the caller continues!
```

The stage function sees a non-zero exit code and treats it as a normal (possibly failed) agent result, advancing state to `AGENT_COMPLETE` with empty/broken output. On the next resume, the run appears "complete" but is actually broken.

## Verified Workflow

### 1. Define `ShutdownInterruptedError` as a sentinel exception

Place it in the module that owns the shutdown flag (e.g., `runner.py`), not in a low-level module, to avoid circular imports:

```python
# <package>/runner.py
class ShutdownInterruptedError(Exception):
    """Raised when an in-progress stage is interrupted by a shutdown signal (Ctrl+C).

    Unlike a generic Exception, this is caught separately by StateMachine.advance_to_completion()
    so the run is NOT marked as FAILED.  The run state stays at its last successfully
    checkpointed value, allowing clean resume on the next invocation.
    """

_shutdown_requested = False

def is_shutdown_requested() -> bool:
    return _shutdown_requested

def request_shutdown() -> None:
    global _shutdown_requested
    _shutdown_requested = True
```

### 2. Check shutdown flag after subprocess.run() returns

In the stage that runs the subprocess, check `is_shutdown_requested()` immediately after `subprocess.run()` returns:

```python
def stage_execute_agent(ctx: RunContext) -> None:
    agent_start = datetime.now(timezone.utc)
    try:
        result = subprocess.run(
            ["bash", str(replay_script.resolve())],
            capture_output=True,
            text=True,
            timeout=adapter_config.timeout,
            cwd=ctx.workspace.resolve(),
        )

        # KEY: subprocess.run() returns normally even when the process was killed by SIGINT.
        # Check shutdown flag here before treating the result as a real agent completion.
        from <package>.runner import ShutdownInterruptedError, is_shutdown_requested

        if is_shutdown_requested():
            raise ShutdownInterruptedError(
                f"Shutdown requested during agent execution for run {ctx.run_number}"
            )

        # ... parse result, set ctx.agent_result ...

    except Exception as e:
        from <package>.runner import ShutdownInterruptedError
        if isinstance(e, ShutdownInterruptedError):
            raise  # Don't catch — let it propagate without setting agent_result

        # Handle other exceptions as before (e.g., timeout)
        agent_result = AdapterResult(exit_code=-1, stderr=str(e), ...)

    # Only reached if no exception — ctx.agent_result is set here
    ctx.agent_result = agent_result
```

### 3. Catch `ShutdownInterruptedError` in run-level StateMachine before `except Exception`

```python
def advance_to_completion(self, tier_id, subtest_id, run_num, actions, until_state=None):
    from <package>.rate_limit import RateLimitError
    from <package>.runner import ShutdownInterruptedError

    try:
        while not self.is_complete(tier_id, subtest_id, run_num):
            new_state = self.advance(tier_id, subtest_id, run_num, actions)
            if until_state is not None and new_state == until_state:
                break
    except RateLimitError:
        self.checkpoint.set_run_state(..., RunState.RATE_LIMITED.value)
        save_checkpoint(...)
        raise
    except ShutdownInterruptedError:
        # Run stays at its last successfully checkpointed state — NOT FAILED.
        current = self.get_state(tier_id, subtest_id, run_num)
        logger.warning(f"Shutdown interrupted at {current.value} — run left resumable")
        raise  # Re-raise so upper levels can also handle cleanly
    except Exception as e:
        # Genuine failures — mark FAILED
        self.checkpoint.set_run_state(..., RunState.FAILED.value)
        save_checkpoint(...)
        raise
```

**Critical**: `ShutdownInterruptedError` must be caught BEFORE `except Exception` since it IS an `Exception`. The run state is NOT updated — it stays wherever it was before the interrupted stage began.

### 4. Handle at subtest level — re-raise without marking FAILED

```python
# SubtestStateMachine.advance_to_completion()
except UntilHaltError as e:
    logger.info(f"[{tier_id}/{subtest_id}] {e}")  # don't fail
except ShutdownInterruptedError:
    current = self.get_state(tier_id, subtest_id)
    logger.warning(f"[{tier_id}/{subtest_id}] Shutdown interrupted at {current.value} — resumable")
    raise  # propagate without setting FAILED
except Exception:
    self.checkpoint.set_subtest_state(..., SubtestState.FAILED.value)
    save_checkpoint(...)
    raise
```

### 5. Handle at tier level — reset to CONFIG_LOADED (not FAILED)

The tier should be reset to a resumable state (the state that triggers subtest execution) rather than `FAILED`:

```python
# TierStateMachine.advance_to_completion()
except Exception as e:
    from <package>.runner import ShutdownInterruptedError

    if isinstance(e, ShutdownInterruptedError):
        # Reset to CONFIG_LOADED so the next invocation re-enters subtest execution
        self.checkpoint.set_tier_state(tier_id, TierState.CONFIG_LOADED.value)
        save_checkpoint(...)
        raise  # propagate

    # All other errors → FAILED
    self.checkpoint.set_tier_state(tier_id, TierState.FAILED.value)
    save_checkpoint(...)
    raise
```

### 6. Handle at experiment level — mark INTERRUPTED (resumable), not FAILED

```python
# ExperimentStateMachine.advance_to_completion()
except Exception as e:
    from <package>.rate_limit import RateLimitError
    from <package>.runner import ShutdownInterruptedError

    if isinstance(e, (RateLimitError, ShutdownInterruptedError)):
        # Both rate limits and Ctrl+C interrupts are resumable
        self.checkpoint.experiment_state = ExperimentState.INTERRUPTED.value
    else:
        self.checkpoint.experiment_state = ExperimentState.FAILED.value

    save_checkpoint(...)
    raise
```

### 7. Re-raise from ProcessPoolExecutor safe wrapper

If you have a `_run_subtest_in_process_safe()` wrapper that converts ALL exceptions to structured results, you must carve out `ShutdownInterruptedError`:

```python
def _run_subtest_in_process_safe(...) -> SubTestResult:
    try:
        return _run_subtest_in_process(...)
    except RateLimitError as e:
        return SubTestResult(selection_reason=f"RateLimitError: {e.info.error_message}", ...)
    except Exception as e:
        from <package>.runner import ShutdownInterruptedError
        if isinstance(e, ShutdownInterruptedError):
            raise  # Do NOT convert to SubTestResult — let it propagate to pool manager
        return SubTestResult(selection_reason=f"WorkerError: {type(e).__name__}: {e}", ...)
```

Also in the `as_completed` loop:

```python
except Exception as e:
    from <package>.runner import ShutdownInterruptedError
    if isinstance(e, ShutdownInterruptedError):
        raise  # Let pool manager shut down cleanly
    # Otherwise create error result...
```

## Failed Attempts (Critical)

| Attempt | Why It Failed | Fix |
| --------- | --------------- | ----- |
| Catch `KeyboardInterrupt` in the state machine | Signal handler sets `_shutdown_requested = True` rather than raising `KeyboardInterrupt` in Python; `subprocess.run()` returns normally, not via exception | Check `is_shutdown_requested()` after `subprocess.run()` returns instead |
| Raise `ShutdownInterruptedError` and rely on `except Exception` catching it at the run level | The `except Exception` clause marks the run as `FAILED` — exactly what we want to avoid | Add a dedicated `except ShutdownInterruptedError` clause BEFORE `except Exception` in every `advance_to_completion()` |
| Let `ShutdownInterruptedError` propagate through `_run_subtest_in_process_safe` | The safe wrapper's `except Exception` converts it to a `WorkerError SubTestResult`, swallowing the signal | Add `if isinstance(e, ShutdownInterruptedError): raise` in the wrapper |
| Reset tier to `SUBTESTS_RUNNING` on interrupt | `SUBTESTS_RUNNING` is the "select best subtest" phase — it expects aggregated results to already be present. Resuming there causes "No sub-test results to select from" error | Reset to `CONFIG_LOADED` which re-enters subtest execution from the beginning |
| Put `ShutdownInterruptedError` in `state_machine.py` | Causes circular import: `state_machine.py` would need to import `runner.py`; `runner.py` already imports `state_machine.py` | Define in `runner.py` (which owns the shutdown flag); use lazy imports in `state_machine.py` |

## Results & Parameters

| Metric | Value |
| -------- | ------- |
| Tests | 3121 passed |
| Coverage | 78.10% (threshold: 75%) |
| New tests | 4 (one per state machine level) |
| Files modified | 7 (runner.py, stages.py, state_machine.py, subtest_state_machine.py, tier_state_machine.py, experiment_state_machine.py, parallel_executor.py) |
| Behavior after fix | Ctrl+C leaves run at `REPLAY_GENERATED`; next resume re-executes agent cleanly |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1109 — Ctrl+C interrupt handling | [notes.md](../../references/notes.md) |

## Key Invariants

1. **`subprocess.run()` does NOT raise on SIGINT** — always check `is_shutdown_requested()` explicitly after it returns.
2. **Sentinel exception must be caught BEFORE `except Exception`** — since `ShutdownInterruptedError` IS an `Exception`, ordering matters.
3. **State machine only advances AFTER action completes** — the interrupted action never completes, so the run state stays at the pre-action state automatically.
4. **Tier resets to CONFIG_LOADED, not SUBTESTS_RUNNING** — `SUBTESTS_RUNNING` requires results already present; `CONFIG_LOADED` re-enters execution from scratch.
5. **Safe wrappers swallow all exceptions** — any `ProcessPoolExecutor` safe wrapper must explicitly re-raise the sentinel.
6. **All four SM levels need handling** — if any level catches `except Exception` without a prior `except ShutdownInterruptedError`, that level will mark FAILED.

## State Machine Architecture Wiring

Absorbed from `state-machine-wiring` (2026-02-22, branch `1008-state-machine-refactor`).
Outcome: 2676 tests pass, 76.11% coverage, all hooks pass.

### Ephemeral Config Fields for `--until-*` Controls

Add to your config dataclass (excluded from serialization/hash):

```python
# Ephemeral --until controls (not saved to experiment.json / not in config_hash)
until_run_state: RunState | None = None
until_tier_state: TierState | None = None
until_experiment_state: ExperimentState | None = None
```

Exclude in `to_dict()` by simply not including these fields.

### Pre-Seeding Mutable State Before Building Action Map

**Critical**: If resuming from a state where the setup action was already executed,
pre-seed shared mutable state BEFORE building the action map:

```python
_current_exp_state = ExperimentState.INITIALIZING
if self.checkpoint:
    try:
        _current_exp_state = ExperimentState(self.checkpoint.experiment_state)
    except ValueError:
        pass

_resume_states = {
    ExperimentState.TIERS_RUNNING,
    ExperimentState.TIERS_COMPLETE,
    ExperimentState.REPORTS_GENERATED,
}
scheduler: Any  # Single annotation before if/else to avoid duplicate-annotation mypy error
if _current_exp_state in _resume_states:
    self._validate_filesystem_on_resume(_current_exp_state)
    scheduler = self._setup_workspace_and_scheduler()
else:
    scheduler = None
```

### Closure-Based Action Map Construction

```python
def _build_experiment_actions(
    self,
    tier_groups: list[list[TierID]],
    scheduler: Any,
    tier_results: dict,
    start_time: datetime,
) -> dict:
    def action_initializing() -> None:
        # INITIALIZING -> DIR_CREATED: no-op, setup done before this call
        pass

    def action_dir_created() -> None:
        nonlocal scheduler
        scheduler = self._setup_workspace_and_scheduler()

    def action_tiers_running() -> None:
        results = self._execute_tier_groups(tier_groups, scheduler)
        tier_results.update(results)

    return {
        ExperimentState.INITIALIZING: action_initializing,
        ExperimentState.DIR_CREATED: action_dir_created,
        ExperimentState.TIERS_RUNNING: action_tiers_running,
        # ...
    }
```

For tier-level closures with multiple shared variables, use a **namespace dict** to share
multiple mutable variables across tier closures:

```python
tier_ns: dict[str, Any] = {}  # shared mutable state across tier closures

def action_pending() -> None:
    tier_ns["config"] = load_tier_config(tier_id)

def action_config_loaded() -> None:
    cfg = tier_ns["config"]
    tier_ns["results"] = run_subtests(cfg)
```

### Wire State Machine into Runner

```python
esm = ExperimentStateMachine(self.checkpoint, checkpoint_path)
actions = self._build_experiment_actions(...)
esm.advance_to_completion(actions, until_state=self.config.until_experiment_state)
```

### Extract Utilities to Library Modules with Backward Compatibility

```python
# <package>/model_validation.py — new home
def validate_model(model: str, ...) -> bool: ...
def is_rate_limit_error(output: str) -> tuple[bool, int | None]: ...

# scripts/run_e2e_experiment.py — old home, re-export for compat
from <package>.model_validation import is_rate_limit_error, validate_model  # noqa: F401
warnings.warn("deprecated, use manage_experiment.py", DeprecationWarning, stacklevel=1)
```

**Important**: Place `warnings.warn()` AFTER all imports to avoid E402 ruff errors.

### Replace sys.argv Mutation with Explicit argv Parameter

```python
# Old (fragile):
sys.argv = ["run_e2e_batch.py"] + batch_args
main()

# New (clean):
def main(argv: list[str] | None = None) -> int:
    args = parser.parse_args(argv)

# Caller:
run_e2e_batch.main(["--config", "batch.yaml"])
```

### Filesystem Cross-Validation on Resume (Warn, Don't Fail)

```python
def _validate_filesystem_on_resume(self, state: ExperimentState) -> None:
    if self.experiment_dir and not self.experiment_dir.exists():
        logger.warning(f"Resuming from {state.value} but experiment_dir missing: {self.experiment_dir}")
```

### Additional Wiring Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| CamelCase alias for state enum | `from package.models import ExperimentState as _ES` | Triggers ruff N814: `Camelcase 'ExperimentState' imported as constant '_ES'` | Use `ExperimentState` directly — no alias needed |
| State transition docstrings on inner functions | `"""INITIALIZING -> DIR_CREATED: ..."""` on closures | Triggers D401 (not imperative mood) | Use `# INITIALIZING -> DIR_CREATED: ...` inline comments instead |
| `warnings.warn()` between imports | Placed warn between stdlib and package imports | Breaks E402 (module-level import not at top) | Move `warnings.warn()` AFTER all imports |
| Wrong subprocess mock path in tests | `patch("subprocess.run", ...)` | Does not intercept calls when module uses `subprocess` as module object | Use `patch("<package>.model_validation.subprocess.run", ...)` |
| Duplicate type annotation for `scheduler` | `scheduler: Any = None` then `scheduler: Any = ...` in if-branch | mypy error: duplicate type annotation | Single bare annotation before branches: `scheduler: Any` then assign in branches |
