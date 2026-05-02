---
name: state-machine-wiring
description: "Wire hierarchical state machines (Experiment \u2192 Tier \u2192 Run)\
  \ into a production runner using closure-based action maps. Use when refactoring\
  \ a monolithic execution loop into resumable, checkpoint-backed discrete states."
category: architecture
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# State Machine Wiring: Hierarchical Closure-Based Action Maps

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-02-22 |
| Branch | `1008-state-machine-refactor` |
| Objective | Wire ExperimentStateMachine + TierStateMachine into E2ERunner production code |
| Outcome | SUCCESS — 2676 tests pass, 76.11% coverage, all hooks pass |

## When to Use

- You have a monolithic execution function with scattered `checkpoint.state = X` assignments
- You want each state to be independently resumable from a checkpoint
- You need multi-level state control (e.g., `--until-tier`, `--until-experiment` CLI flags)
- You're extracting utility functions from scripts to library modules (with backward compat)
- You need to validate filesystem state on checkpoint resume

## Verified Workflow

### 1. Add ephemeral config fields for `--until-*` controls

Add to your config dataclass (excluded from serialization/hash):
```python
# Ephemeral --until controls (not saved to experiment.json / not in config_hash)
until_run_state: RunState | None = None
until_tier_state: TierState | None = None
until_experiment_state: ExperimentState | None = None
```

Exclude in `to_dict()` by simply not including these fields.

### 2. Pre-seed mutable state before building action map

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

### 3. Build action map with closures and mutable namespace

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

For tier-level closures with multiple shared variables, use a namespace dict:
```python
tier_ns: dict[str, Any] = {}  # shared mutable state across tier closures

def action_pending() -> None:
    tier_ns["config"] = load_tier_config(tier_id)

def action_config_loaded() -> None:
    cfg = tier_ns["config"]
    tier_ns["results"] = run_subtests(cfg)
```

### 4. Wire state machine into runner

```python
esm = ExperimentStateMachine(self.checkpoint, checkpoint_path)
actions = self._build_experiment_actions(...)
esm.advance_to_completion(actions, until_state=self.config.until_experiment_state)
```

### 5. Extract utilities to library modules with backward compat

```python
# scylla/e2e/model_validation.py — new home
def validate_model(model: str, ...) -> bool: ...
def is_rate_limit_error(output: str) -> tuple[bool, int | None]: ...

# scripts/run_e2e_experiment.py — old home, re-export for compat
from scylla.e2e.model_validation import is_rate_limit_error, validate_model  # noqa: F401
warnings.warn("deprecated, use manage_experiment.py", DeprecationWarning, stacklevel=1)
```

**Important**: Place `warnings.warn()` AFTER all imports to avoid E402 ruff errors.

### 6. Replace sys.argv mutation with explicit argv parameter

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

### 7. Filesystem cross-validation on resume (warn, don't fail)

```python
def _validate_filesystem_on_resume(self, state: ExperimentState) -> None:
    if self.experiment_dir and not self.experiment_dir.exists():
        logger.warning(f"Resuming from {state.value} but experiment_dir missing: {self.experiment_dir}")
```

## Failed Attempts (Critical)

### Camelcase alias triggers N814 ruff violation
`from scylla.e2e.models import ExperimentState as _ES` triggers `N814 Camelcase 'ExperimentState' imported as constant '_ES'`.
**Fix**: Use `ExperimentState` directly — no alias needed.

### State transition docstrings on inner functions trigger D401 violation
`"""INITIALIZING -> DIR_CREATED: ..."""` on a closure triggers D401 (not imperative mood).
**Fix**: Use `# INITIALIZING -> DIR_CREATED: ...` inline comments instead.

### `warnings.warn()` between imports triggers E402 violation
Placing `warnings.warn(...)` between stdlib imports and scylla imports breaks E402.
**Fix**: Move `warnings.warn()` AFTER all imports.

### Wrong subprocess mock path in tests
`patch("subprocess.run", ...)` does NOT intercept calls when the module imports `subprocess` as a module object.
**Fix**: `patch("scylla.e2e.model_validation.subprocess.run", ...)`.

### Unused `time` import after function extraction
After moving `validate_model()` (which used `time.sleep`) to a new module, `import time` remains in the old file.
**Fix**: Remove unused import.

### Duplicate type annotation triggers mypy error
```python
scheduler: Any = None
if ...:
    scheduler: Any = ...  # Error: duplicate annotation
```
**Fix**: Single bare annotation before branches:
```python
scheduler: Any
if ...:
    scheduler = self._setup_workspace_and_scheduler()
else:
    scheduler = None
```

## Results & Parameters

| Metric | Value |
| -------- | ------- |
| Tests | 2676 passed |
| Coverage | 76.11% (threshold: 73%) |
| Pre-commit | All hooks pass |
| State levels | 3 (Experiment -> Tier -> Run) |
| Scripts deleted | 5 (deprecated) |
| New modules | 4 (experiment_sm, tier_sm, model_validation, stages) |

## Key Code Patterns

### State machine advance loop (already implemented)
```python
def advance_to_completion(
    self,
    actions: dict[State, Callable],
    until_state: State | None = None,
) -> State:
    while not self.is_complete():
        current = self.get_state()
        if until_state is not None and current == until_state:
            break
        self.advance(actions)
    return self.get_state()
```

### Timing in advance()
```python
if action is not None:
    _t0 = time.monotonic()
    action()
    _elapsed = time.monotonic() - _t0
    logger.info(f"[experiment] {current.value} -> {transition.to_state.value}: {description} ({_elapsed:.1f}s)")
```
