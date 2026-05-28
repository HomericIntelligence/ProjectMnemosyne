---
name: mock-and-test-isolation-patterns
description: "Use when: (1) writing chaos/fault injection tests where a mock service must simulate latency, kill, or queue-starvation side effects — not just record the fault command, (2) a FastAPI/Pydantic endpoint test expects a specific HTTP status code (e.g. 503) but receives 500 because MagicMock attributes fail Pydantic response serialization, (3) tests pass individually but fail together due to mock pollution across test files and real file I/O with tmp_path is a cleaner alternative, (4) a test name says 'and' but only one side is asserted — a patch.object is missing 'as mock_X' and assert_called_once(), (5) a test bypasses the runner entry point and calls an internal delegate directly, leaving the full path untested, (6) adding unit tests for a class that constructs collaborators internally — patch the instance attribute after construction, (7) testing RuntimeError precondition guards (if-None, subprocess returncode, or _is_setup state) with parametrize or side_effect lists, (8) testing closure guards inside action-builder methods without a full state machine, (9) tests pass in isolation but fail when run after a test that calls importlib.reload() — patch.object on a module-imported object becomes stale after reload; use patch() string form instead."
category: testing
date: 2026-05-28
version: "1.1.0"
user-invocable: false
history: mock-and-test-isolation-patterns.history
tags:
  - mock
  - test-isolation
  - pydantic
  - magicmock
  - fastapi
  - chaos-testing
  - fault-injection
  - tmp-path
  - patch-object
  - runtime-error
  - guard-tests
  - instance-attribute-patching
  - subprocess
  - importlib-reload
  - stale-reference
  - string-patch
---

# Mock and Test Isolation Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Canonical collection of correct mock usage and test isolation patterns for Python unit tests |
| **Outcome** | Merged from 9 skills covering mock fidelity, Pydantic serialization, file I/O vs mocks, missing assertions, entry-point coverage, instance attribute patching, and RuntimeError guard testing |
| **Verification** | verified-ci |

## When to Use

Use this skill when any of the following apply:

1. **Chaos/fault injection mocks** — mock service has `/inject_fault` or `/v1/chaos/*` but tests only assert the inject call returns 200, not that later endpoints show chaotic behavior.
2. **Pydantic + MagicMock 500 errors** — endpoint test expects a specific error code (e.g. 503) but gets 500; server logs show `ValidationError` during response serialization.
3. **Mock pollution between test files** — tests pass individually but fail together; `clear_patches` autouse fixture does not fully prevent cross-module leakage; real file I/O with `tmp_path` is cleaner.
4. **Missing mock assertion** — test name contains "and" but only one branch is asserted; a `patch.object` call has `return_value=X` but no `as mock_X` handle.
5. **Runner entry point untested** — test calls an internal delegate directly (e.g. `ResumeManager.handle_zombie()`) instead of the parent runner method.
6. **Instance attribute patching** — class constructor builds collaborator internally (`self.x = SomeClass(arg)`); passing a `MagicMock()` as the constructor arg creates a real collaborator, not a mock.
7. **RuntimeError precondition guards** — testing `if x is None: raise RuntimeError(...)`, `result.returncode != 0`, or `_is_setup` state guards; multi-guard functions with sequential `subprocess.run` calls.
8. **Closure guards in action builders** — guards inside closures returned from `_build_experiment_actions` or `TierActionBuilder.build()` cannot be tested through the state machine; call the builder, get the closure dict, invoke the key directly.
9. **Stale logger/object after importlib.reload** — tests use `patch.object(imported_logger, "error")` but a different test file called `importlib.reload(module)`, replacing the module-level logger with a new instance; the patch targets the old object while the code uses the new one; mock.called stays False even though the log appears in captured output.

## Verified Workflow

### Quick Reference

```python
# --- Pattern 1: Chaos mock — simulate side effects, not just record ---
def _apply_fault_effects(state):
    if (f := state.active_faults.get("latency")):
        time.sleep(f.get("delay_ms", 0) / 1000)

@app.get("/v1/health")
def health():
    if state.active_faults.get("kill"):
        return Response(status_code=503, content=b'{"status":"degraded"}',
                        media_type="application/json")
    _apply_fault_effects(state)
    return {"status": "ok"}

# --- Pattern 2: Pydantic + MagicMock — set typed attributes explicitly ---
mock_publisher = MagicMock()
mock_publisher.reconnect_count = 0   # int, not MagicMock
mock_publisher.last_error = ""       # str, not MagicMock
mock_publisher.is_connected = False  # bool, not MagicMock

# --- Pattern 3: Real file I/O instead of mock ---
def test_fig01(sample_runs_df, tmp_path):
    fig01_score_variance_by_tier(sample_runs_df, tmp_path, render=False)
    assert (tmp_path / "fig01_score_variance_by_tier.vl.json").exists()
    assert (tmp_path / "fig01_score_variance_by_tier.csv").exists()

# --- Pattern 4: Capture ALL mock handles ---
with (
    patch.object(runner, "_setup_workspace_and_scheduler",
                 return_value=mock_scheduler) as mock_setup,
    patch.object(runner, "_capture_experiment_baseline") as mock_baseline,
):
    runner._action_exp_dir_created(scheduler_ref)
mock_setup.assert_called_once()
mock_baseline.assert_called_once()

# --- Pattern 5: Instance attribute patching after construction ---
runner = E2ERunner(mock_config, MagicMock(), Path("/tmp"))
mock_tier_manager = MagicMock()
runner.tier_manager = mock_tier_manager  # override the real one

# --- Pattern 6: RuntimeError guard — parametrized multi-guard ---
@pytest.mark.parametrize("field,expected_match", [
    ("agent_result", r"agent_result"),
    ("judgment", r"judgment"),
])
def test_raises_when_field_is_none(self, stage_context, field, expected_match):
    # Set all fields valid first, then null the one under test
    stage_context.agent_result = AdapterResult(exit_code=0, ...)
    stage_context.judgment = {"score": 0.9, ...}
    setattr(stage_context, field, None)
    with pytest.raises(RuntimeError, match=expected_match):
        stage_finalize_run(stage_context)

# --- Pattern 7: Sequential subprocess guard ---
with patch("subprocess.run", side_effect=[fetch_ok, checkout_fail]):
    with pytest.raises(RuntimeError, match="Failed to checkout commit abc123"):
        manager._checkout_commit()

# --- Pattern 8: Closure guard in action builder ---
actions = runner._build_experiment_actions(
    tier_groups=[[TierID.T0]], scheduler=None,
    tier_results={}, start_time=datetime.now(timezone.utc),
)
with pytest.raises(RuntimeError, match="experiment_dir must be set"):
    actions[ExperimentState.TIERS_COMPLETE]()

# --- Pattern 9: Stale logger after importlib.reload — use string patch form ---
# WRONG: patch.object resolves the object at import time; reload replaces it
with patch.object(imported_logger, "error") as mock_err:
    run_subprocess(["false"])
    # mock_err.called == False even though log appears in captured output!

# CORRECT: string form resolves module-level logger at patch time (runtime)
with patch("hephaestus.utils.helpers.logger.error") as mock_err:
    run_subprocess(["false"])
    assert mock_err.called  # Works even after importlib.reload(helpers)
```

### Pattern 1: Chaos Mock — Simulate Side Effects

Chaos tests must verify that the system *observes* a fault, not just that the fault was recorded.

1. Implement `/v1/chaos/inject` to store fault config in `state.active_faults[fault_id]`.
2. Define `_apply_fault_effects()` that reads `state.active_faults` and performs the side effect (sleep, status code change, skip queue advancement).
3. Call `_apply_fault_effects()` at the **top** of every response handler (cross-cutting faults like latency).
4. For targeted faults (kill, queue-starve), add conditional branches inside the specific affected endpoints.
5. Implement `/v1/chaos/reset` to clear `state.active_faults`.
6. Each chaos test: (1) POST to inject, (2) call a **different** endpoint, (3) assert that endpoint shows the chaos effect.

| Fault | Affected Endpoint | Simulation |
|-------|-------------------|------------|
| `latency` | All | `time.sleep(delay_ms / 1000)` at handler start |
| `kill` / `unavailable` | Health/readiness | Return 503 + `{"status": "degraded"}` |
| `queue-starve` | Task dequeue | Skip the queue advancement step |
| `error-rate` | All responses | Return 500 with probability `p` |
| `clock-skew` | Timestamp endpoints | Add fixed offset to `now()` |

### Pattern 2: Pydantic Response Model + MagicMock

When an endpoint uses a Pydantic response model and you mock the object whose attributes populate the model:

1. Identify which Pydantic model is used (`response_model=` decorator or explicit `return MyModel(...)`).
2. List every field and its type annotation.
3. For each field populated from a mock attribute, **explicitly set** a concrete value of the correct Python type on the mock before the test call.
4. Use `TestClient(app, raise_server_exceptions=False)` to get the actual HTTP status code rather than a re-raised exception.

Root cause: `MagicMock()` auto-attributes return `MagicMock` instances. Pydantic v2 rejects `MagicMock` for `int`, `str`, `bool` fields, raising `ValidationError` at serialization time — which the framework catches and returns as 500, masking the intended status code.

### Pattern 3: Real File I/O Instead of Mocks

Prefer `tmp_path` over mocking `save_figure` or similar I/O functions when:
- Tests pass individually but fail together (mock pollution)
- Content verification is needed (reading CSV is simpler than `mock.call_args[0][3]`)

Conversion steps:
1. Replace `mock_save_figure` parameter with `tmp_path`.
2. Remove `with patch()` blocks entirely.
3. Replace `assert mock.called` with `assert (tmp_path / "filename.ext").exists()`.
4. For content verification: `pd.read_csv(tmp_path / "filename.csv")` instead of `mock.call_args`.
5. Remove `mock_save_figure` and `clear_patches` fixtures from `conftest.py`.
6. Remove `from unittest.mock import patch` imports from test files.

### Pattern 4: Capture All Mock Handles (Missing Assertion Fix)

Detection heuristic:

```bash
grep -A 20 "def test_calls_.*_and_" tests/ -r | grep "assert_called_once"
# If count of "and" clauses > count of assert_called_once → missing assertion
```

Fix: add `as mock_X` to every `patch.object` call that needs to be asserted, then add `mock_X.assert_called_once()` after the context.

### Pattern 5: Runner Entry Point Testing

When an issue requirement says "calls `runner.X()`", tests that call an internal delegate directly leave the discovery/wiring chain untested. Always add a runner-level test that:

1. Creates the minimal filesystem fixture required by the discovery methods.
2. Instantiates the runner and calls the entry-point method directly.
3. Asserts on the runner state after the call.

### Pattern 6: Instance Attribute Patching After Construction

When a class constructs a collaborator in `__init__` from a primitive (e.g. `tiers_dir: Path`):

```python
# Passing MagicMock() as tiers_dir satisfies the constructor but runner.tier_manager
# is still a real TierManager. Always reassign after construction:
runner = E2ERunner(mock_config, MagicMock(), Path("/tmp"))
runner.tier_manager = MagicMock()
runner.experiment_dir = Path("/results/exp")  # plain attrs: assign directly
```

- Direct attribute assignment is simpler than `patch.object(runner, "attr", ...)` as a context manager for instance attributes.
- Use `==` for Pydantic model equality; use `is` only when verifying the exact same object reference.

### Pattern 9: Stale Module Reference After importlib.reload

**Symptom:** `mock_error.called` is `False` but the log message appears in `Captured stdout`. Tests pass when run alone but fail in the full suite.

**Root cause:** Another test file calls `importlib.reload(module)` to test env-var overrides. After reload, `module.logger` is a new object. The test file imported `logger` at module load time, so `patch.object(logger, "error")` patches the **old** object. The production code uses the **new** `module.logger` — the mock is invisible to it.

**Diagnosis:** Run the failing test in isolation (passes) vs. after the reload test (fails). Check for `importlib.reload` calls in other test files that reload the same module.

**Fix:** Replace `patch.object(imported_obj, "attr")` with `patch("package.module.obj.attr")`. The string form looks up `module.obj` at patch execution time (runtime), not import time, so it always targets the current object regardless of any intervening reloads.

```python
# Wrong — imports logger once at module load; stale after reload
from hephaestus.utils.helpers import logger
with patch.object(logger, "error") as mock_err: ...

# Correct — resolves hephaestus.utils.helpers.logger at test runtime
with patch("hephaestus.utils.helpers.logger.error") as mock_err: ...
```

**Alternative (if you must use patch.object):** Use `importlib.import_module` inside the test to get the current module reference:

```python
import importlib
helpers = importlib.import_module("hephaestus.utils.helpers")
with patch.object(helpers.logger, "error") as mock_err: ...
```

### Pattern 7: RuntimeError Guard Tests

**Single guard (simple form):**

```python
def test_raises_when_field_is_none(self, my_fixture):
    my_fixture.field = None
    with pytest.raises(RuntimeError, match=r"field"):
        my_function(my_fixture)
```

**Multi-guard (parametrize):** Set all fields to valid values first, then null out only the field under test. This ensures the specific guard fires, not an earlier one.

**Runner-level guard:** Patch the side-effect method that normally sets the field as a no-op, then call the method and let the guard fire.

**Subprocess failure guard:** Use `side_effect=[ok_result, fail_result]` to simulate sequential `subprocess.run` calls where the second fails.

**State guard (`_is_setup`):** The default value is `False` — no mock needed. For later guards behind the state check, set `manager._is_setup = True` to bypass the first guard.

**Local-import patch target rule:**

```python
# runner.py uses: from scylla.e2e.health import HeartbeatThread (inside run())
# WRONG: patch("scylla.e2e.runner.HeartbeatThread", ...)  # AttributeError
# CORRECT: patch("scylla.e2e.health.HeartbeatThread", ...)
```

Always patch `defining_module.ClassName`, not `caller_module.ClassName` for local imports.

**Closure guard (action builder):** Call the builder method to get the closure dict, null the required attribute, then invoke `actions[StateKey]()` directly — no state machine required.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Chaos mock records fault via `/inject`, returns 200. No side effects on subsequent requests. | Tests asserted on observed chaos (slow responses, 503 health, stalled queue). Mock never produced those effects, so chaos tests failed despite inject returning 200. | Recording the intent of a fault is not the same as simulating its effects. The mock must change behavior of OTHER endpoints based on active faults. |
| 2 | Implement only the latency chaos fault, skip kill and queue-starve. | Tests for health degradation and queue stall still failed. Each fault type has its own simulation. | Each fault type needs its own side-effect simulation — there is no generic fault effect. |
| 3 | Apply cross-cutting fault effects (latency) only to designated "chaos endpoints". | Some tests asserted ALL endpoints slow down. Restricted effects gave false greens in isolation but wrong results in the full suite. | Cross-cutting fault effects must be applied via a shared helper called at the top of every handler. |
| 4 | Assumed a 500 response came from `connect.side_effect = OSError(...)` in application logic. | The OSError was handled — the 500 came from Pydantic `ValidationError` at serialization time, not from the connect call. | Always check where in the request lifecycle a 500 originates: application logic errors vs. response serialization errors are distinct failure points. |
| 5 | Used `clear_patches` autouse fixture in `conftest.py` to prevent mock leakage between test files. | `patch.stopall()` does not prevent cross-module pollution when the same module is imported and mocked in multiple test files. | Complete removal of mocks and switching to real I/O with `tmp_path` is easier and more reliable than partial isolation fixes. |
| 6 | Passed `MagicMock()` as the `tiers_dir` constructor argument to avoid instantiating a real `TierManager`. | The constructor accepts it without crashing, but `runner.tier_manager` is still a real `TierManager` — not a mock. Method calls on it fail or produce unexpected results. | Always reassign `runner.tier_manager` (and similar constructed collaborators) directly on the instance after construction. |
| 7 | Patched `scylla.e2e.runner.HeartbeatThread` to control the heartbeat in `run()`. | `runner.py` uses a local import (`from scylla.e2e.health import HeartbeatThread` inside `run()`), so `scylla.e2e.runner` has no `HeartbeatThread` attribute — patch raises `AttributeError`. | For local imports inside function bodies, patch the defining module (`scylla.e2e.health.HeartbeatThread`), not the caller's namespace. |
| 8 | Tested closure guard by setting up the full state machine and driving it to the target state. | State machine setup was complex and fragile; intermediate states required many mocks. | Call the action-builder method directly to get the closure dict, set the attribute to `None`, and invoke the closure key — no state machine needed. |
| 9 | Used `patch.object(imported_logger, "error")` to assert that `run_subprocess` logs errors; tests passed in isolation but all 3 mock assertions failed when the full suite ran. | A sibling test file calls `importlib.reload(helpers)` to test env-var timeout overrides. Reload replaces `helpers.logger` with a new `ContextLogger` instance. The imported `logger` reference is stale; `run_subprocess` uses the new instance, so the patch is invisible. The log message still appears in captured stdout (confirming the code ran) but `mock_err.called` stays `False`. | Use the string form `patch("package.module.obj.attr")` which resolves the module attribute at patch time rather than at import time. Always suspect stale references when a mock's `called` is `False` but the side-effect (log line, file write) visibly occurred. |

## Results & Parameters

### Chaos Mock Full Skeleton

```python
import time
from dataclasses import dataclass, field
from typing import Any, Dict
from fastapi import FastAPI, Response

app = FastAPI()

@dataclass
class MockState:
    active_faults: Dict[str, Any] = field(default_factory=dict)
    tasks: list = field(default_factory=list)

state = MockState()

def _apply_fault_effects():
    if (f := state.active_faults.get("latency")):
        time.sleep(f.get("delay_ms", 0) / 1000)

@app.post("/v1/chaos/inject")
def inject(req: dict):
    state.active_faults[req["id"]] = req
    return {"status": "ok"}

@app.post("/v1/chaos/reset")
def reset():
    state.active_faults.clear()
    return {"status": "ok"}

@app.get("/v1/health")
def health():
    if state.active_faults.get("kill"):
        return Response(status_code=503, content=b'{"status":"degraded"}',
                        media_type="application/json")
    _apply_fault_effects()
    return {"status": "ok"}

@app.get("/v1/tasks")
def tasks():
    _apply_fault_effects()
    if not state.active_faults.get("queue-starve"):
        _advance_queue()
    return {"tasks": state.tasks}
```

### Mock Conversion Table (file I/O)

| Pattern | Before | After |
|---------|--------|-------|
| Fixture | `mock_save_figure` | `tmp_path` |
| Path arg | `Path("/tmp")` | `tmp_path` |
| Assert | `assert mock.called` | `assert (tmp_path / "file.vl.json").exists()` |
| Content check | `mock.call_args[0][3]` | `pd.read_csv(tmp_path / "file.csv")` |
| Import | `from unittest.mock import patch` | (remove) |

### Guard Match Pattern Convention

Guards follow `raise RuntimeError(f"{field_name} must be set before {function_name}")`,
so `match=r"field_name"` always matches. For f-string guards with runtime values,
include a unique fragment: `match="Failed to checkout commit abc123"`.

### Pydantic Response Model — Field Typing Checklist

When mocking objects whose attributes populate a Pydantic response model:
- `int` fields → set to `0` or a concrete integer
- `str` fields → set to `""` or a concrete string
- `bool` fields → set to `True` or `False`
- Use `TestClient(app, raise_server_exceptions=False)` to capture actual HTTP status codes

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectCharybdis | PR #88 — chaos integration tests with NATS + mock Agamemnon | Chaos tests R02/R03/R04/R05 all green after adding side-effect simulation |
| ProjectHermes | PR #300 — NATS publisher health endpoint test | `test_lifespan_degraded_health_returns_503` fixed by typing mock attributes |
| ProjectScylla | PR #353 — analysis figure test mock removal | 332 tests passing after switching to `tmp_path` real I/O |
| ProjectScylla | PR #1313 — review feedback, missing assertion | 18 tests pass after adding `mock_setup.assert_called_once()` |
| ProjectScylla | PR #1312 — review feedback, runner path untested | Runner-level zombie test added, 12 tests pass |
| ProjectScylla | PR #819 — internal method unit tests (issue #773) | 3 tests added for `_select_best_baseline_from_group`, all 2208 pass |
| ProjectScylla | PR #1210 — RuntimeError guard tests (issue #1144) | 8 new guard tests, 3265 passed, 78.42% coverage |
| ProjectScylla | PR #1310 — WorkspaceManager guard tests (issue #1215) | 3 new guard tests, 25 module tests pass |
| ProjectHephaestus | PR #644 — timeout= on subprocess calls; test_constants.py reload poisoned test_general_utils.py logger mocks | 2601 unit tests pass after switching to `patch("hephaestus.utils.helpers.logger.error")` |
