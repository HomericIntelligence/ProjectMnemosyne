---
name: pytest-async-mock-isolation-patterns
description: "Use when: (1) pytest CI step times out or hangs due to asyncio event loops, epoll blocking, or runaway retry loops caused by sleep mocks; (2) an asyncio coroutine internally reassigns a global Event making pre-set fixtures ineffective; (3) writing integration tests for asyncio code that calls httpx.AsyncClient and need stateful fault injection (500/503/timeouts) via respx without nested context issues; (4) tests pass individually but fail together due to module-level singleton state (circuit breaker, cache, registry) not reset between tests; (5) a class-level patch.object becomes stale after importlib.reload() — use patch() string form; (6) FastAPI Depends() ignores a patched get_settings because the function reference was captured at import time; (7) an automation/agent-orchestration unit test reaches an invoke_claude subprocess gate that is absent in CI; (8) tests pass in isolation but fail when run after a test that mutates shared asyncio objects; (9) a mock service must simulate latency, kill, or queue-starvation side effects — not just record the fault command; (10) a test name says 'and' but only one assertion is made and a mock assertion is missing; (11) a ThreadPoolExecutor in one test spawns worker threads that outlive that test and open _GH_BREAKER after the next test's conftest autouse reset has already run — conftest reset is necessary but NOT sufficient against background threads."
category: testing
date: 2026-06-07
version: "1.1.0"
user-invocable: false
history: pytest-async-mock-isolation-patterns.history
tags:
  - pytest
  - asyncio
  - mock
  - test-isolation
  - hang
  - timeout
  - epoll
  - event-loop
  - AsyncMock
  - patch
  - time-sleep
  - oom
  - respx
  - httpx
  - fault-injection
  - circuit-breaker
  - singleton
  - module-singleton
  - autouse-fixture
  - conftest-scope
  - importlib-reload
  - stale-reference
  - string-patch
  - fastapi
  - pydantic-settings
  - claude-cli
  - agent-orchestration
  - subprocess
  - full-suite-before-green
  - cross-test-contamination
  - python
  - threadpool
  - background-threads
  - ThreadPoolExecutor
---

# Pytest Async, Mock, and Test Isolation Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Consolidate recurring pytest pitfalls for asyncio code, HTTP/service mocking, and cross-test isolation: event-loop hangs, sleep-mock OOM, respx stateful fault injection, module-level singleton reset, importlib.reload patch staleness, FastAPI DI isolation, and agent-subprocess CI gates |
| **Outcome** | SUCCESS — six skills merged; patterns verified across ProjectKeystone, ProjectHephaestus, ProjectScylla, ProjectHermes, ProjectTelemachy, ProjectCharybdis |
| **Verification** | verified-ci |

## When to Use

1. **CI job times out (no test failure output)** — asyncio tests hang in `epoll.poll(-1)` because an event never fires, or a non-async sibling test blocks on a real `subprocess`/`time.sleep`
2. **`pytest-timeout` fires but the test keeps running** — default signal method cannot interrupt a blocked C-level syscall
3. **A coroutine reassigns a global `asyncio.Event` internally** — pre-setting the module variable is silently overwritten
4. **`patch("module.time.sleep")` causes OOM or runaway loops** — the patch leaks to all callers in the process
5. **`Depends(get_settings)` ignores a patched `get_settings`** — the function reference was captured at import time
6. **Writing async integration tests against `httpx.AsyncClient`** — need stateful fault injection (500/503/409/timeouts) via respx without nested contexts or async/sync boundary issues
7. **Tests pass individually but fail together** — module-level singleton state (circuit breaker, cache, registry, asyncio Lock/Event) not reset between tests
8. **A `patch.object` becomes stale after `importlib.reload()`** — the patch targets the old object; use the `patch()` string form
9. **An automation/agent-orchestration unit test reaches an `invoke_claude`/`_run_advise`/`_run_learn` subprocess gate** — green locally (claude on PATH) but red in CI (binary absent)
10. **A mock service must simulate latency/kill/queue-starvation side effects** — not just record the fault command
11. **A test name says "and" but only one assertion is made** — a `patch.object` is missing `as mock_X` and `assert_called_once()`
12. **The same test fails identically on multiple Python versions in CI (3.10–3.13)** — a fingerprint of order-dependent shared state
13. **`GitHubUnavailableError: GitHub API circuit breaker is open` in test B, but test B never calls a real `gh`** — test A's `ThreadPoolExecutor` workers are still running and open the breaker after the conftest autouse reset for test B has already fired

## Verified Workflow

### Quick Reference

```python
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import asyncio, pytest

# --- A: Patch the COROUTINE FUNCTION, not its internals ---
@patch("mymodule.daemon.run", new_callable=AsyncMock, return_value=0)
def test_main_starts(mock_run):
    assert main(["--log-level", "INFO"]) == 0
    mock_run.assert_called_once()
# asyncio.run() registers SIGINT internally — use assert_any_call for signals:
mock_signal.assert_any_call(signal.SIGTERM, ANY)

# --- B: Patch asyncio.Event CONSTRUCTOR when the coroutine reassigns the global ---
mock_event = asyncio.Event(); mock_event.set()  # pre-set so wait() returns immediately
with patch("mymodule.daemon.asyncio.Event", return_value=mock_event):
    result = await mymodule.daemon.run(settings)

# --- C: pytest-timeout thread method (pyproject.toml) — BOTH flags required ---
# addopts = "--timeout=30 --timeout-method=thread"

# --- D: Patch the wait HELPER, not time.sleep (process-wide leak / OOM) ---
with patch("mymodule.wait_until") as mock_wait:
    _call_that_retries(max_retries=2)
mock_wait.assert_called_once()
# If you MUST patch sleep, patch at the import path and assert call values:
with patch("mymodule.retry.time.sleep") as mock_sleep:
    decorated()
mock_sleep.assert_any_call(0.1)

# --- E: FastAPI / pydantic-settings — env vars + cache_clear, NOT name patch ---
os.environ.update(overrides); get_settings.cache_clear()
try:
    client = TestClient(app)   # SlowAPIMiddleware MUST be registered for rate limits
finally:
    get_settings.cache_clear()

# --- F: respx async fixture — sync ctx manager INSIDE async fixture ---
@pytest_asyncio.fixture
async def mock_api():
    state = MockState()
    with respx.mock(base_url="http://localhost:8080") as router:
        router.post("/v1/agents", name="create_agent").mock(
            side_effect=lambda r: _handle(r, state))
        async with AsyncClient(base_url="http://localhost:8080") as client:
            yield state, router, client

# --- G: Reset module-level singleton (breaker) in package conftest, BOTH sides ---
@pytest.fixture(autouse=True)
def _reset_breaker():
    github_api._GH_BREAKER.reset()   # reset the BOUND instance, not the registry
    yield
    github_api._GH_BREAKER.reset()

# --- H: Reset asyncio objects in autouse fixture with LAZY import ---
@pytest.fixture(autouse=True)
def reset_server_state():
    from myapp.server import app           # lazy import avoids import-order coupling
    app.state.shutdown_event = asyncio.Event()
    app.state.inflight_lock = asyncio.Lock()
    yield
    app.state.shutdown_event = asyncio.Event()
    app.state.inflight_lock = asyncio.Lock()

# --- I: Stale object after importlib.reload — use string patch form ---
# WRONG: with patch.object(imported_logger, "error") as m: ...  # stale after reload
with patch("mypkg.helpers.logger.error") as mock_err:           # resolves at runtime
    run_subprocess(["false"]); assert mock_err.called

# --- J: Agent gate OFF in shared fixture; patch every agent call on the path ---
opts = _make_ci_driver_options(enable_advise=False)  # gate OFF by default
with patch.object(driver, "_run_advise") as m_advise:
    driver.run_fix_session()
m_advise.assert_not_called()
```

### Detailed Steps

#### A — Patch the Coroutine Function Itself

1. **Trace the call chain from `main()`** to find what `asyncio.run()` directly invokes:
   `return asyncio.run(run(settings))` → `run()` is the coroutine to patch.
2. **Patch `run` with `AsyncMock`**, not internal helpers `main()` never calls directly. Patching a helper the entry point never calls is a silent no-op; the real coroutine runs and hangs.
3. **Audit log assertions** — remove assertions for logs emitted inside the mocked coroutine.
4. **Switch `assert_called_once_with` to `assert_any_call`** on `signal.signal` — `asyncio.runners.Runner` registers SIGINT internally, so the count is 2 not 1.

#### B — Patch asyncio.Event Constructor for Internal Reassignment

A coroutine that does `global _shutdown_event; _shutdown_event = asyncio.Event(); await _shutdown_event.wait()` overwrites any pre-set module variable. Patch the constructor in the module's namespace with a pre-set event:

```python
mock_event = asyncio.Event(); mock_event.set()
with patch("mymodule.daemon.asyncio.Event", return_value=mock_event):
    result = await mymodule.daemon.run(settings)
```

Diagnose via the timeout stack trace — `epoll.poll(timeout=-1)` at the bottom confirms the loop is blocked on an unset Event.

#### C — Fix pytest-timeout Not Interrupting Epoll

`--timeout-method=signal` (the default) delivers SIGALRM only when the blocked `epoll.poll(-1)` syscall returns — which never happens with no fd events. The `thread` method uses `thread.interrupt_main()`, delivering a `KeyboardInterrupt` even inside a C-level syscall. **Both flags are required together:**

```toml
[tool.pytest.ini_options]
addopts = "--timeout=30 --timeout-method=thread"
```

#### D — time.sleep Mock Hazard and the Unmocked-Wait Hang

`patch("module.time.sleep")` replaces `sleep` on the **shared singleton `time` module** — neutralising it for every caller. A background `while True: time.sleep(N)` then spins at full CPU and can OOM the host. Safe alternatives:

1. Patch the dedicated wait helper (`wait_until`, `poll_for`) instead of `time.sleep`.
2. Patch probe functions at their **source namespace** (where defined), not via re-export.
3. If patching `time.sleep`, use the module's import path (`"mymodule.retry.time.sleep"`).
4. Add a defensive iteration cap to any `while True` loop in production code.
5. Replace wall-clock `assert elapsed >= N` with `mock_sleep.assert_any_call(N)`.

**The non-async sibling: unmocked-wait hang.** When you add a blocking call (real `subprocess` + real `time.sleep` bounded by a long timeout) into a hot path, the module's own targeted tests may pass (they mock the new method) while a **sibling `run()`-level test** drives the path unmocked and blocks for the full timeout. Diagnose by comparing the CI job duration to the baseline on main (4× baseline = hang, not variance), reproduce with the exact CI flags + faulthandler:

```bash
PYTHONFAULTHANDLER=1 timeout --signal=ABRT 120 \
  python -X faulthandler -m pytest tests/unit -p no:cacheprovider
```

**Fix:** every test that reaches the path must mock the *actual blocking call*, not just the trigger:
```python
patch.object(driver, "_wait_for_pr_terminal", return_value="MERGED")
```

#### E — FastAPI / pydantic-settings Test Isolation

`Depends(get_settings)` captures the **function object** at import time — patching the module-level name has no effect on FastAPI's DI. Instead:

1. **Set env vars** so the real `get_settings` returns the desired values.
2. **Call `get_settings.cache_clear()`** before and after (required with `@lru_cache`).
3. **Register `SlowAPIMiddleware`** — `@limiter.limit()` alone does not enforce limits.
4. **Use `AsyncMock(side_effect=asyncio.TimeoutError())`** instead of patching `asyncio.wait_for`.

#### F — respx Stateful Async Mock Fixtures

**Key principle:** `respx.mock(...)` is a **sync context manager opened INSIDE an async fixture**, with the `AsyncClient` entered inside the respx context so both share the event loop (pytest-asyncio auto mode). Never nest `respx.mock()` in the test body and never wrap respx in a sync fixture for async tests.

Hold mutable fault flags in a state object read on each call; one fixture covers all error scenarios:

```python
class MockState:
    def __init__(self):
        self.permanent_status = None      # override all status reads
        self.status_queue = []            # ordered terminal statuses
        self.exception_on_create = False  # fault flag

def _handle_status(request, state):
    if state.permanent_status:
        return Response(200, json={"status": state.permanent_status})
    if state.status_queue:
        return Response(200, json={"status": state.status_queue.pop(0)})
    return Response(200, json={"status": "pending"})  # POLA: loud hang, not silent pass
```

- **POLA default = "pending"** — never default to a terminal status (silent false positive). A missing enqueue should cause a loud hang.
- **Dict-subset payload matching** survives schema evolution: assert only the keys you care about, ignore extra keys.
- **Respx 0.21+** uses `name=` on routes for `router["name"].calls` inspection.
- Register custom markers (`integration`) once in a single `[tool.pytest.ini_options]` table; do not duplicate `asyncio_mode`.

#### G — Module-Level Singleton Isolation (Circuit Breaker, Cache, Registry)

A module-level singleton (`_GH_BREAKER = CircuitBreaker(fail_max=5, ...)`) keeps internal state (fail counter, OPEN/CLOSED) across tests for the life of the process. Reset rules:

1. **Reset the held instance directly** (`github_api._GH_BREAKER.reset()`), NOT via a registry-clearing helper — `reset_all_circuit_breakers()` does `_registry.clear()`, which orphans the import-time-bound instance so it keeps accumulating state.
2. **Put the autouse reset in `conftest.py` at the broadest scope** covering any contaminating test — a fixture in a single `test_*.py` does not protect sibling files.
3. **Reset both before and after** (`yield` pattern) so a crashed test cannot leak state.
4. **For new fail-fast tests**, call `module._GH_BREAKER.reset()` at the test top — every raised exception (even a fail-fast 422) counts as one breaker failure; a few new failure tests can push a shared breaker OPEN and turn unrelated siblings red.
5. **Classify deterministic errors as non-transient** (HTTP 422, GraphQL schema errors) so they fail fast on attempt 1 — retrying wastes ~31s and adds breaker failures.
6. **The conftest autouse reset is necessary but NOT sufficient against `ThreadPoolExecutor` workers.** The timing hazard: (a) conftest resets `_GH_BREAKER` before test B starts; (b) test A's ThreadPoolExecutor workers are still running after that reset; (c) those workers hit network errors in the CI sandbox and open the breaker; (d) test B fails with `GitHubUnavailableError: GitHub API circuit breaker is open` even though it never made a `gh` call. **The only reliable fix is to prevent the threads from spawning at all.** When testing `driver.run()` (or any method that dispatches work via a ThreadPoolExecutor), mock the per-item worker (`_drive_issue`) alongside `_discover_prs` and `_sweep_orphaned_arming_records`:

   ```python
   with patch.object(driver, "_discover_prs", return_value={661: 661}):
       with patch.object(driver, "_sweep_orphaned_arming_records"):
           with patch.object(driver, "_drive_issue", return_value=None):
               driver.run()
   ```

   Mocking only the outer helpers (`_discover_prs`, `_sweep_orphaned_arming_records`) is insufficient: `run()` still dispatches `_drive_issue` into a `ThreadPoolExecutor`. A partial mock leaves real worker threads running past the test boundary.

**Run the FULL suite before declaring green.** A passing subset (`pytest tests/unit/automation` → 1174 passed) is misleading because a shared breaker's threshold is only crossed at full scope. Run what CI runs (`pytest tests/unit`). When a function gains a NEW side-effecting call (a `gh`/network/db call), audit EVERY existing test that reaches it and add the mock — an unmocked real call fails in CI's no-network sandbox, trips the shared breaker, and cascades `CircuitBreakerOpenError` into unrelated tests. Treat that cascade as a SYMPTOM: find the EARLIEST non-breaker failure (the real root cause). Background long runs rather than skipping them.

| Where the singleton is tripped | Where the autouse reset belongs |
|--------------------------------|---------------------------------|
| Multiple files in one package  | `tests/<package>/conftest.py`   |
| Multiple packages / unit+integration | `tests/conftest.py` (top-level) |

#### H — Asyncio Fixture State Reset (Lock, Event) with Lazy Import

Module-level or `app.state` asyncio objects (Lock, Event, Queue, Semaphore) hold state across tests with no automatic reset. Use a function-scoped `autouse=True` fixture that **replaces** each instance (asyncio.Lock has no `clear()`), with a **lazy import inside the fixture body** to avoid import-order coupling, resetting on **both** sides of `yield`. Use `scope="function"` (default), not module scope, or tests in one module share state.

#### I — Stale Object After importlib.reload

**Symptom:** `mock.called == False` but the side effect (log line, file write) visibly occurred; passes alone, fails in the full suite. **Cause:** another test file calls `importlib.reload(module)`, replacing `module.logger` with a new object; a `patch.object(imported_logger, ...)` patches the old reference. **Fix:** use the string form `patch("pkg.module.obj.attr")`, which resolves the attribute at patch time (runtime), surviving reloads. Suspect a stale reference whenever a mock's `called` is `False` but its side effect happened.

#### J — Agent Subprocess CI Gate (claude absent in CI)

Automation/orchestration tests pass locally (claude on `~/.local/bin`) but fail in CI (binary absent) when an unpatched agent call (`invoke_claude_with_session`, `_run_advise`, `_run_learn`) shells out to a real `claude`. A downstream `mock.assert_called_once()` that never fires means an upstream agent call short-circuited.

1. **Default the agent gate OFF** (`enable_advise=False`) in the shared options/config fixture.
2. **Patch every agent-invoking method** on each test's path — not just the obvious downstream ones.
3. **Add gated-behavior coverage** (enabled → runs once + findings reach downstream; disabled → skipped).
4. **Reproduce CI locally** by hiding `~/.local/bin` from PATH while keeping pixi + gh:

```bash
CLEAN_PATH="$(dirname "$(which pixi)"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PATH="$CLEAN_PATH" which claude || echo "claude hidden (good)"
PATH="$CLEAN_PATH" pixi run pytest tests/unit/automation/ -q --no-cov
```

Do NOT blank PATH entirely — pixi itself may live under `/tmp/pixi-.../bin` and disappear.

#### K — Mock Fidelity and Missing-Assertion Patterns

- **Chaos/fault mocks must simulate side effects, not just record them.** Store fault config in `state.active_faults`, then a shared `_apply_fault_effects()` at the top of every handler performs the effect (sleep for latency, 503 for kill, skip dequeue for queue-starve). Each chaos test injects, calls a *different* endpoint, and asserts that endpoint shows the effect.
- **Pydantic + MagicMock 500s:** `MagicMock()` auto-attributes are `MagicMock` instances; Pydantic v2 rejects them for `int`/`str`/`bool` fields, raising `ValidationError` at serialization → 500 masking the intended status. Set concrete typed values on the mock; use `TestClient(app, raise_server_exceptions=False)` to see the real status code.
- **Real file I/O over mocks:** prefer `tmp_path` + `assert (tmp_path/"f").exists()` over patching `save_figure` when tests pollute each other or need content checks.
- **Capture every mock handle:** a test whose name contains "and" must assert both branches — add `as mock_X` + `mock_X.assert_called_once()`.
- **Instance attribute patching after construction:** passing `MagicMock()` as a constructor primitive still builds a real collaborator; reassign `runner.tier_manager = MagicMock()` after construction.
- **Local-import patch target:** patch `defining_module.ClassName`, not `caller_module.ClassName`, for imports done inside a function body.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Patch a helper the entry point never calls | `@patch("mymodule.daemon.run_routing_loop")` | `main()` never calls it; silent no-op; real coroutine runs and hangs | Trace the actual call chain from the entry point before choosing a patch target |
| Patch `asyncio.run` | `@patch("...asyncio.run", return_value=0)` | Coroutine body never runs; log assertions inside it silently fail | Only safe when no assertions depend on coroutine-internal side effects |
| `assert_called_once_with(signal.SIGTERM, ...)` | Exact-count assertion on `signal.signal` | `asyncio.runners.Runner` registers SIGINT internally → count is 2 | Use `assert_any_call` for signals when `asyncio.run()` is involved |
| Pre-set module-level event variable | `mymodule._shutdown_event.set()` before `run()` | `run()` overwrites it with a fresh `asyncio.Event()` | Patch the `asyncio.Event` constructor instead |
| Default `--timeout-method=signal` | `--timeout=30` only | SIGALRM fires only when `epoll.poll(-1)` returns — never with no events | Set `--timeout` AND `--timeout-method=thread` together |
| `patch("module.time.sleep")` globally | Patched `time.sleep` in a retry test | Leaked to every module sharing the `time` singleton; runaway loop OOMed the host | `patch("module.time.sleep")` is process-wide, not module-scoped — patch the wait helper |
| Wall-clock timing assertion | `assert elapsed >= 0.3` | Flaky under CPU/scheduler/coverage jitter | Replace with `mock_sleep.assert_any_call(N)` |
| Module-only test run, declared done | Ran only the module that mocks the new wait | Hang lived in a sibling `run()`-level test the isolated run never covered | Run the full dir the way CI does before claiming green |
| Mocked the trigger, not the blocking call | Patched `_enable_auto_merge=True`, left `_wait_for_pr_terminal` real | Green path still reached the real `gh pr view` + `time.sleep` and blocked | Mock the actual blocking call, not the trigger that precedes it |
| `patch("server.get_settings", ...)` | Patched the module-level name bound by `Depends()` | `Depends()` captured the original function at import time; DI ignores the patch | Set env vars + `get_settings.cache_clear()` instead |
| `@limiter.limit()` without middleware | Added the decorator, no `SlowAPIMiddleware` | Limit never evaluated; requests returned 202 | `SlowAPIMiddleware` is mandatory for enforcement |
| Patched `asyncio.wait_for` with a real coroutine | `async def _t(): raise TimeoutError` + `patch(..., side_effect=_t)` | `RuntimeWarning: coroutine never awaited` | Use `AsyncMock(side_effect=asyncio.TimeoutError())` |
| Nested `respx.mock()` in test body | Outer fixture opens respx; test opens a second context | Already-active patches → registration conflicts / double-patching | Open respx exactly once at fixture scope; tests read state flags |
| Sync `@pytest.fixture` wrapping respx for async tests | Sync fixture yields client to an async test | Boundary mismatch → `RuntimeError: no running event loop` | Use `@pytest_asyncio.fixture` (async); open respx as a sync ctx INSIDE |
| Default mock task status = "completed" | Assumed the monitor would fetch status | If the monitor never runs, default "completed" silently passes (false positive) | Default to "pending" (POLA); force tests to enqueue terminal status |
| String-contains JSON assertions | `assert '"status":"pending"' in str(json)` | Spacing/ordering/nesting break brittle string checks | Use dict-subset matching (`payload_contains`) |
| Clearing the registry to reset a breaker | `reset_all_circuit_breakers()` (does `_registry.clear()`) | Orphans the import-time-bound `_GH_BREAKER`; it keeps OPEN state | Reset the held instance directly: `module._GH_BREAKER.reset()` |
| Autouse reset in a single test file | Fixture only in `test_github_api.py` | Sibling files inherited OPEN-breaker state; failed identically on Py 3.10–3.13 in CI | Put the autouse reset in `conftest.py` at the broadest contaminating scope |
| Running only the new fail-fast test in isolation | Confirmed it passes alone | Shared-breaker pollution only manifests when the whole class runs in order | "Passes in isolation" is the trap, not the proof — run the full class/module |
| Ran only the changed subdirectory, declared green | `pytest tests/unit/automation` → 1174 passed | Full `tests/unit` (3391) crossed the breaker threshold; cascade in CI only | Run the FULL unit suite before green; stateful singletons make subsets misleading |
| Left a new side-effecting `gh` call unmocked in existing tests | Added `gh_pr_resolve_thread` to a validator existing tests exercised | Real `gh` calls fail in CI's no-network sandbox → tripped shared breaker → `CircuitBreakerOpenError` cascade | Mock the new collaborator in EVERY reaching test; the cascade is a symptom — find the earliest real failure |
| `patch.object(imported_logger, "error")` | Asserted subprocess error logging | A sibling test's `importlib.reload()` replaced the logger; the patch targeted the stale object | Use the string form `patch("pkg.module.logger.error")` (resolves at runtime) |
| Mock `_discover_prs` + `_sweep_orphaned_arming_records` only when testing `driver.run()` | Expected those two patches to fully contain `run()` side effects | `run()` still dispatches `_drive_issue` into a `ThreadPoolExecutor`; workers outlived the test boundary and opened `_GH_BREAKER` after the next test's conftest reset | Mock the per-item worker (`_drive_issue`) too — prevent threads from spawning entirely; the conftest autouse reset is not enough against background threads (PR #1060, commit 4ac2263) |
| Manual per-test asyncio Lock init | Each test re-creates `app.state.lock` in its body | Easy to forget on new tests; forgotten tests inherit dirty state | Use `@pytest.fixture(autouse=True)` in conftest |
| `app.state.inflight_lock.clear()` | Tried to "clear" an asyncio.Lock | asyncio.Lock has no `clear()` method | Replace the instance: `app.state.inflight_lock = asyncio.Lock()` |
| Module-scope fixture for async state | `scope="module"` | Lock held by test 1 still held when test 2 runs | Use default function scope with `autouse=True` |
| Top-level import in fixture | `from app.server import app` at conftest module scope | Circular import / module-load-order fragility | Lazy import inside the fixture body |
| Trusted local green for agent tests | Pushed after a local pass | Local `claude` on PATH masked the missing-binary CI behavior | Re-run with `claude` hidden from PATH before pushing |
| Patched only obvious downstream agent calls | Patched `_get_failing_ci_logs`, not new `_run_advise` | The unpatched upstream agent call hit a real `claude` and short-circuited | Default gates OFF AND patch every agent-invoking method on the path |
| Blanked PATH to simulate "no claude" | `PATH=""` / `PATH=/usr/bin` | `pixi` itself disappeared; suite could not start | Keep pixi's dir + gh on PATH; only drop `~/.local/bin` |
| New `enable_advise` gate defaulted `True` | Left the new gate on in the shared fixture | Every pre-existing test reached the agent call and went red in CI | New agent gates default `False`; only gate-specific tests flip it on |
| Chaos mock records fault, no side effects | `/inject` returns 200, no behavior change | Tests asserting observed chaos (slow responses, 503) failed | Simulate effects on OTHER endpoints, not just record the fault |
| Passed `MagicMock()` as constructor primitive | `E2ERunner(cfg, MagicMock(), path)` | `runner.tier_manager` is still a real collaborator | Reassign the attribute after construction |
| `clear_patches` autouse fixture for leakage | `patch.stopall()` across files | Does not prevent cross-module pollution | Switch to real `tmp_path` I/O |

## Results & Parameters

### pytest Configuration (copy-paste ready)

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--cov=src/<package> --cov-report=term-missing --cov-report=xml --timeout=30 --timeout-method=thread"
testpaths = ["tests"]
markers = [
    "integration: integration tests with respx mock HTTP server",
    "asyncio: async tests",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9",
    "pytest-asyncio>=0.24,<1",
    "pytest-cov>=6.0,<7",
    "pytest-timeout>=2.3,<3",
    "respx>=0.21",
]
```

### Timeout Value Guidelines

| Scenario | Recommended `--timeout` |
|----------|--------------------------|
| Unit tests only | 10–30 s |
| Integration tests with I/O | 30–60 s |
| Tests involving network calls | 60–120 s |
| Full daemon startup (with coroutine patching) | 30 s |

### Diagnostic Stack Trace (epoll hang signature)

```
File ".../asyncio/selector_events.py", in _run_once
    event_list = self._selector.select(timeout)
File ".../selectors.py", in select
    fd_event_list = self._selector.poll(timeout, max_ev)
```

`timeout=-1` at the bottom = the loop waits forever — signature of an unset `asyncio.Event`.

### Async Daemon Test Pattern

```python
class TestMain:
    @patch("mymodule.daemon.run", new_callable=AsyncMock, return_value=0)
    def test_main_returns_zero(self, mock_run):
        assert main(["--log-level", "INFO"]) == 0
        mock_run.assert_called_once()

class TestRun:
    async def test_run_returns_zero(self):
        mock_event = asyncio.Event(); mock_event.set()
        with patch("mymodule.daemon.asyncio.Event", return_value=mock_event):
            assert await mymodule.daemon.run(Settings(shutdown_timeout=0.1)) == 0
```

### respx Fixture + Dict-Subset Assertion

```python
def payload_contains(actual: dict, expected: dict) -> bool:
    return all(k in actual and actual[k] == v for k, v in expected.items())

async def test_workflow(mock_api):
    state, router, client = mock_api
    state.status_queue = ["completed"]                 # POLA: explicit terminal
    result = await WorkflowExecutor(client=client).run(spec)
    assert result.success
    assert payload_contains(router["create_agent"].calls[0].request.json(),
                            {"name": "agent1", "runtime": "docker"})
```

### Circuit Breaker Reset Fixture (package conftest)

```python
# tests/unit/automation/conftest.py
import pytest
from hephaestus.automation import github_api

@pytest.fixture(autouse=True)
def _reset_circuit_breakers():
    github_api._GH_BREAKER.reset()   # reset the BOUND instance, not the registry
    yield
    github_api._GH_BREAKER.reset()
```

```bash
# Full suite before green (what CI runs) — NOT the changed subdirectory:
pixi run pytest tests/unit            # ✅  (subset like tests/unit/automation hides cascades)
```

### Agent Gate CI Reproduction (claude hidden)

```bash
CLEAN_PATH="$(dirname "$(which pixi)"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PATH="$CLEAN_PATH" which claude || echo "claude hidden (good)"   # must be hidden
PATH="$CLEAN_PATH" which pixi                                     # must resolve
PATH="$CLEAN_PATH" pixi run pytest tests/unit/automation/ -q --no-cov
```

### Stale-Reference / Bot False-Positive Reference

| Situation | Action |
|-----------|--------|
| `mock.called == False` but side effect occurred | Suspect stale ref after `importlib.reload`; use `patch("pkg.mod.obj.attr")` |
| `await <asyncio.Task>` flagged "no effect" | False positive; keep the await (cleanup, exception propagation) |
| Pydantic 500 instead of expected status | Set concrete typed values on the mock; `TestClient(raise_server_exceptions=False)` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PRs #451, #535, #541, #428 — daemon coroutine patch + Event constructor + timeout-method + bot false positive | 9 hanging daemon tests fixed; `--timeout-method=thread` revealed the epoll stack; CI green |
| ProjectHephaestus | PR #412 — time.sleep OOM fix | 113 tests pass in 2.6 s after fix vs 30 s + OOM before |
| ProjectHephaestus | PRs #633/#707/#1042/#1084 — circuit-breaker isolation (v1.0–v1.3 of source) | Conftest-scope fix; fail-fast reset; 422/GraphQL non-transient classifier; full-suite-before-green + mock-every-new-call (fix commits `3e4bc10`, `83d5aaf`) |
| ProjectHephaestus | PR #644 — stale logger after importlib.reload | 2601 unit tests pass after switching to `patch("hephaestus.utils.helpers.logger.error")` |
| ProjectHephaestus | PRs #677/#679 — agent-subprocess CI gate | `_run_advise` on the fix path; gated `enable_advise=False` + patched all agent calls; 845 tests pass with claude hidden; CI cleared |
| ProjectScylla | PRs #353/#819/#1210/#1310/#1313/#1312/#1217 — mock removal, guard tests, missing assertions, flaky sleep | 3265 pass at 78.42% coverage; wall-clock assertions replaced with mocks; runner-level paths covered |
| ProjectHermes | tests/conftest.py + webhook tests — asyncio Lock/Event reset + FastAPI isolation | 541 tests pass at 97.84% coverage; all five FastAPI/pydantic isolation patterns confirmed |
| ProjectTelemachy | Issue #48 — respx integration infrastructure | 9 integration tests; stateful fault injection (500/409/503/timeout/invalid); 57 tests pass; no nested-context issues |
| ProjectCharybdis | PR #88 — chaos integration tests (NATS + mock Agamemnon) | Chaos tests R02–R05 green after adding side-effect simulation |
| HomericIntelligence | CI — `_wait_for_pr_terminal` unmocked-wait hang | Full `pytest tests/unit` hung ~16 min vs ~4 min baseline; patched the wait in all green-path tests → 1003 passed in 93 s |
| ProjectHephaestus | PR #1060, commit 4ac2263 — ThreadPoolExecutor worker lifetime crosses test boundary; `_drive_issue` must be mocked when testing `CIDriver.run()` | `test_run_gate_does_not_abort_with_prs` was opening `_GH_BREAKER` in sibling tests via executor workers; mocking `_drive_issue` eliminated the threads; verified-ci |
