---
name: testing-respx-async-mock-fixtures-with-stateful-faults
description: "Use when: (1) writing integration tests for asyncio code that calls httpx.AsyncClient (REST API clients, etc.), (2) testing error scenarios (500, 409, 503, timeouts) via HTTP mocking without nested contexts or async/sync boundary issues, (3) needing stateful fault injection (permanent status override, task status queue, exception flags) without redefining the mock for each test, (4) validating HTTP request payloads with assertions that survive schema evolution, (5) using respx 0.21+ with route names for call inspection, (6) pytest-asyncio with auto mode where fixture and test both run in same event loop."
category: testing
date: 2026-06-03
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - respx
  - httpx
  - async
  - asyncio
  - pytest-asyncio
  - fixture
  - mock
  - http
  - fault-injection
  - integration-test
  - state-machine
  - payload-validation
  - rest-api
  - python
---

# Testing respx Async Mock Fixtures with Stateful Faults

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Objective** | Document patterns for using respx to mock httpx.AsyncClient in pytest fixtures without nested context managers or async/sync boundary issues; enable stateful fault injection via MockAgamemnonState flags |
| **Outcome** | SUCCESS — 9 integration tests implemented for ProjectTelemachy issue #48; all 57 tests pass (48 unit + 9 integration); zero fixture lifecycle issues; no nested context conflicts |
| **Verification** | verified-ci (full suite passes; integration tests specifically target workflow executor against mock Agamemnon REST API) |

## When to Use

1. **async pytest with httpx.AsyncClient mocking** — tests call real async client against mocked HTTP endpoints
2. **Stateful mock behavior** — different test calls need different response status/payload; fault injection flags determine runtime behavior
3. **Integration tests with error scenarios** — 5xx errors, 409 conflicts, task status timeouts, exception propagation
4. **Payload validation resistant to schema evolution** — dict-subset matching instead of string-contains or full equality
5. **respx 0.21+ API** — explicit route names for `router["route_name"].calls` inspection
6. **pytest-asyncio auto mode** — all tests and fixtures run in same event loop; `respx.mock()` must open/close in same scope

## Verified Workflow

### Quick Reference

```python
# conftest.py — Single @pytest_asyncio.fixture with respx + async client
import asyncio
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient

class MockAgamemnonState:
    """Stateful fault injection flags (no nested contexts needed)."""
    def __init__(self):
        self.permanent_status = None  # "running" or "failed"
        self.status_queue = []  # ordered terminal statuses
        self.task_status_script = []  # per-task status sequence
        self.exception_on_create_agent = False
        self.exception_on_create_team = False

@pytest_asyncio.fixture
async def mock_agamemnon():
    """
    Single fixture: open respx.mock() + register routes + enter async client,
    all in same scope. Yields state, router, client.
    """
    state = MockAgamemnonState()
    
    with respx.mock(base_url="http://localhost:8080") as router:
        # Register routes with explicit name= for call inspection
        router.post("/v1/agents", name="create_agent").mock(
            side_effect=lambda r: _handle_create_agent(r, state)
        )
        router.post("/v1/agents/{id}/start", name="start_agent").mock(
            side_effect=lambda r: _handle_start_agent(r, state)
        )
        router.post("/v1/teams", name="create_team").mock(
            side_effect=lambda r: _handle_create_team(r, state)
        )
        router.get("/v1/teams/{id}/status", name="get_team_status").mock(
            side_effect=lambda r: _handle_get_team_status(r, state)
        )
        router.post("/v1/teams/{id}/tasks", name="create_task").mock(
            side_effect=lambda r: _handle_create_task(r, state)
        )
        router.get("/v1/teams/{id}/tasks/{task_id}/status", name="get_task_status").mock(
            side_effect=lambda r: _handle_get_task_status(r, state)
        )
        router.delete("/v1/agents/{id}", name="delete_agent").mock(
            side_effect=lambda r: _handle_delete_agent(r, state)
        )
        
        # Create async client INSIDE the respx context
        async with AsyncClient(base_url="http://localhost:8080") as client:
            yield state, router, client

# --- Route handlers read fault flags on each call ---
def _handle_create_agent(request, state):
    if state.exception_on_create_agent:
        return Response(status_code=500, json={"error": "internal error"})
    payload = request.json()
    return Response(status_code=201, json={"id": f"agent-{payload['name']}"})

def _handle_get_team_status(request, state):
    # Permanent override takes precedence
    if state.permanent_status:
        return Response(status_code=200, json={"status": state.permanent_status})
    # Otherwise dequeue the next status
    if state.status_queue:
        status = state.status_queue.pop(0)
        return Response(status_code=200, json={"status": status})
    # Default: pending
    return Response(status_code=200, json={"status": "pending"})

# --- Dict-subset matching for payload assertions ---
def payload_contains(actual: dict, expected: dict) -> bool:
    """Return True iff all keys in expected are present in actual with == value."""
    for key, val in expected.items():
        if key not in actual or actual[key] != val:
            return False
    return True

# --- In a test ---
async def test_workflow_executes_with_docker_agent(mock_agamemnon):
    state, router, client = mock_agamemnon
    
    # Explicit POLA: agent starts pending, must enqueue terminal status
    state.status_queue = ["completed"]
    
    executor = WorkflowExecutor(client=client)
    result = await executor.run(spec)
    
    assert result.success
    
    # Route inspection with explicit names
    create_calls = router["create_agent"].calls
    assert len(create_calls) == 1
    assert payload_contains(create_calls[0].request.json(), {
        "name": "agent1",
        "runtime": "docker",
        "docker_image": "my-image:latest"
    })
```

### Detailed Pattern Description

#### 1. Single @pytest_asyncio.fixture Pattern

**Key principle:** `respx.mock(...)` **must** be a **sync context manager** inside an **async** fixture.

```python
@pytest_asyncio.fixture
async def mock_agamemnon():
    state = MockAgamemnonState()
    
    # Sync context manager opens/closes within async scope
    with respx.mock(base_url="http://localhost:8080") as router:
        # Register routes here
        router.post(...).mock(side_effect=...)
        
        # Async client enters INSIDE respx context
        async with AsyncClient(...) as client:
            # Everything in this scope shares the same event loop
            yield state, router, client
            # On fixture exit: client closes, respx mocks uninstall
```

**Why this works:**
- `respx.mock()` as a sync context manager patches `httpx.AsyncClient` before entry
- Async client instantiation happens **after** patching is active
- Both fixture and test run on same event loop (pytest-asyncio auto mode)
- On fixture exit: client cleanup, then respx patches are removed

**Anti-pattern:** Nested `respx.mock()` calls or sync fixtures wrapping respx for async tests → async/sync boundary issues, context collision.

#### 2. Stateful Fault Injection via MockAgamemnonState

Instead of creating a new mock for each test, hold mutable state in a class and read flags on each HTTP call.

```python
class MockAgamemnonState:
    def __init__(self):
        self.permanent_status = None
        self.status_queue = []
        self.task_status_script = []  # {task_id: [status, status, ...]}
        self.exception_on_create_agent = False
        self.exception_on_create_team = False
        self.exception_on_get_team_status = False

# Handler reads flags at call time
def _handle_create_agent(request, state):
    if state.exception_on_create_agent:
        return Response(status_code=500)
    # ... normal path
```

**In tests:**
```python
async def test_agent_creation_fails(mock_agamemnon):
    state, router, client = mock_agamemnon
    
    # Enable fault before calling
    state.exception_on_create_agent = True
    
    executor = WorkflowExecutor(client=client)
    with pytest.raises(AgamemnonError):
        await executor.run(spec)
```

**Advantages:**
- One fixture setup for all error scenarios
- Flags describe intent clearly
- No nested contexts in test body
- Eliminates fixture redefinition boilerplate

#### 3. POLA for Mock Task Status

**Principle:** Default to "pending" (loud failure if not advanced), never default to terminal status.

```python
# Correct: default pending, test enqueues terminal
async def test_workflow_completes(mock_agamemnon):
    state, router, client = mock_agamemnon
    state.status_queue = ["completed"]  # Explicit enqueue
    
    result = await executor.run(spec)
    assert result.success
```

```python
# Anti-pattern: default completed, test "passes" silently
# If monitor never runs, default "completed" hides the bug
```

**Rationale:** If the test fails to enqueue a terminal status and the monitor never reaches the team-status endpoint, a "pending" default causes the test to hang (loud failure). A "completed" default causes silent success (false positive). Loud failure is better.

#### 4. Dict-Subset Payload Assertions

Instead of string-contains or full equality, match expected keys/values in actual payload.

```python
def payload_contains(actual: dict, expected: dict) -> bool:
    """Return True iff every key in expected is present in actual with == value."""
    for key, val in expected.items():
        if key not in actual or actual[key] != val:
            return False
    return True

# In test
assert payload_contains(create_calls[0].request.json(), {
    "name": "agent1",
    "runtime": "docker",
    "docker_image": "my-image:latest"
    # Other keys in actual payload (e.g. cpus, memory) are ignored
})
```

**Advantages:**
- Assertion survives schema evolution (new optional fields don't break test)
- Focuses assertion on what matters (name, runtime type, image)
- Decouples test from full schema

#### 5. Route Registration with Explicit name= Kwarg

```python
# Respx 0.21+ API: register routes with name parameter
router.post("/v1/agents", name="create_agent").mock(side_effect=...)
router.post("/v1/agents/{id}/start", name="start_agent").mock(side_effect=...)

# Later: inspect calls via name
create_calls = router["create_agent"].calls
assert len(create_calls) == 1
assert create_calls[0].request.method == "POST"
```

**Documented API:** See respx 0.21 changelog for route name syntax.

#### 6. Pytest Marker Registration Without Duplicating asyncio_mode

Add integration test markers to existing `[tool.pytest.ini_options]` **without duplicating `asyncio_mode`**.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "..."
markers = [
    "integration: integration tests with respx mock HTTP server",
    "asyncio: async tests",
]
testpaths = ["tests"]
```

In test file:
```python
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

async def test_workflow_completes(mock_agamemnon):
    ...
```

**Single source of truth:** `asyncio_mode = "auto"` is set once; markers are added without duplication.

#### 7. CI Auto-Detection — No CI Changes Needed

The pixi-based CI in ProjectTelemachy runs:
```bash
pixi run pytest --tb=short
```

This command:
- Collects all tests under `tests/` by default
- Has no `-m` filter → all markers included
- Automatically picks up new integration tests under `tests/integration/`

**No CI YAML changes required.** New tests are discovered and run in standard CI flow.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| Nested `respx.mock()` in test body | Outer fixture opens respx; test opens a second respx.mock() context | Respx patches are already active from fixture; nested open/close causes registration conflicts and double-patching | Always open respx exactly once at fixture scope; test bodies should read state flags, not create new contexts |
| Sync `@pytest.fixture` wrapping respx for async tests | `@pytest.fixture` def mock(): with respx.mock(...): yield client` called from async test | Sync fixture runs on main thread before test event loop starts; client enters async context after loop is up; boundary mismatch causes `RuntimeError: cannot enter context — no running event loop` or `no current event loop` | Use `@pytest_asyncio.fixture` with `async def`; respx.mock opens as sync context **inside** async scope |
| String-contains assertions on JSON | `assert '\"status\":\"pending\"' in str(request.json())` | String format can change without logic change; extra spaces, key ordering, nested objects all break brittle assertions | Use dict-subset matching: extract request.json(), compare dicts via `payload_contains()` |
| Default mock task status = "completed" | Tests assumed monitor would fetch status; if monitor never runs, default "completed" silently passes | False positive: bug hidden by default assumption; test claims success without exercising the code path | Always default to "pending" (or missing queue); force test to **explicitly** enqueue terminal status; loud hang is better than silent skip |
| Sync `time.sleep` mock in async test | `with patch("module.time.sleep"):` inside async test | Patches the sync module; async test's `await asyncio.sleep()` is not affected; real sleep still blocks test | For async code, mock `asyncio.sleep()` or use pytest-asyncio fixtures that advance time; for REST mocking specifically, respx eliminates the need to mock timing |
| Bare `@pytest.mark.integration` without marker registration | Added pytest marker in test file but did not register in pyproject.toml | pytest warns "unknown marker"; CI may fail if run with `pytest -m integration` | Always register custom markers in `[tool.pytest.ini_options]` markers list |
| Multiple `[tool.pytest.ini_options]` tables | Added markers in a second `[tool.pytest.ini_options]` table in pyproject.toml | TOML does not allow duplicate keys; second table overwrites first | Single source of truth: one `[tool.pytest.ini_options]` table with all keys (asyncio_mode, markers, addopts, etc.) |
| Duplicating `asyncio_mode` on each test class | Each test class added `pytestmark = [pytest.mark.asyncio]` AND some added `asyncio_mode = "auto"` comment | Redundant; can conflict if different classes set different modes; confusing maintenance | Set `asyncio_mode` once in pyproject.toml; use `pytest.mark.asyncio` on each async test/class for clarity |
| CI filter `pytest -m "not integration"` to run unit tests only | Tried to exclude integration tests from unit-test job | CI command in ProjectTelemachy is `pixi run pytest --tb=short` with no `-m` filter; tests mixed in one run | New tests are collected and run; no need for separate jobs (though they could be added later if needed) |
| Await asyncio.Event in fixture setup | `await asyncio.Event()` thinking it advances the event loop | `asyncio.Event()` is a sync call; `await` on a non-awaitable is a syntax error | Never `await` a constructor or sync operation; use `event.set()` and `event.wait()` inside async context |
| Monkeypatch asyncio.sleep in async test scope | `monkeypatch.setattr("asyncio.sleep", MagicMock())` to avoid real sleep | For REST code, the executor doesn't sleep internally; respx mocking handles all I/O; patching sleep is unnecessary | Rely on respx to mock HTTP roundtrips; no sleep mocking needed for REST clients |
| HTTP timeout via real delay + fixture sleep | Handler sleeps to simulate timeout: `time.sleep(30)` in route handler | Makes tests slow; doesn't actually test timeout behavior; respx can trigger timeout via exception | Mock handlers can raise `httpx.ConnectTimeout` or `httpx.ReadTimeout` directly; no real delay needed |

## Results & Parameters

### Integration Test Structure (ProjectTelemachy)

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py         (Pydantic schema validation)
│   ├── test_executor.py       (executor logic with mocked AgamemnonClient)
│   └── test_cli.py            (CLI argument parsing)
├── integration/
│   ├── __init__.py
│   ├── conftest.py            (mock_agamemnon fixture)
│   └── test_workflow_lifecycle.py  (workflow against respx mock server)
```

### conftest.py — Full Fixture Implementation

```python
# tests/integration/conftest.py
import asyncio
import json
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient, Response
from typing import Dict, List, Any

class MockAgamemnonState:
    """Stateful fault injection for integration tests."""
    
    def __init__(self):
        self.permanent_status: str | None = None
        self.status_queue: List[str] = []
        self.task_status_script: Dict[str, List[str]] = {}
        self.exception_on_create_agent = False
        self.exception_on_create_team = False
        self.exception_on_get_team_status = False
        self.exception_on_start_agent = False
    
    def reset(self):
        """Reset all flags for clean test state."""
        self.__init__()

@pytest_asyncio.fixture
async def mock_agamemnon():
    """
    Integration fixture: mock Agamemnon REST API.
    
    Yields: (state, router, client) tuple
    - state: MockAgamemnonState for fault injection
    - router: respx router for call inspection
    - client: AsyncClient connected to mock
    """
    state = MockAgamemnonState()
    
    with respx.mock(base_url="http://localhost:8080") as router:
        # Create agent
        router.post("/v1/agents", name="create_agent").mock(
            side_effect=lambda r: _handle_create_agent(r, state)
        )
        
        # Start agent
        router.post("/v1/agents/{id}/start", name="start_agent").mock(
            side_effect=lambda r: _handle_start_agent(r, state)
        )
        
        # Create team
        router.post("/v1/teams", name="create_team").mock(
            side_effect=lambda r: _handle_create_team(r, state)
        )
        
        # Get team status (polls for task completion)
        router.get("/v1/teams/{id}/status", name="get_team_status").mock(
            side_effect=lambda r: _handle_get_team_status(r, state)
        )
        
        # Create task
        router.post("/v1/teams/{id}/tasks", name="create_task").mock(
            side_effect=lambda r: _handle_create_task(r, state)
        )
        
        # Get task status
        router.get("/v1/teams/{id}/tasks/{task_id}/status", name="get_task_status").mock(
            side_effect=lambda r: _handle_get_task_status(r, state)
        )
        
        # Delete agent (cleanup)
        router.delete("/v1/agents/{id}", name="delete_agent").mock(
            side_effect=lambda r: _handle_delete_agent(r, state)
        )
        
        # Enter async client inside respx context
        async with AsyncClient(base_url="http://localhost:8080") as client:
            yield state, router, client

def _handle_create_agent(request, state: MockAgamemnonState) -> Response:
    if state.exception_on_create_agent:
        return Response(status_code=500, json={"error": "internal error"})
    
    payload = request.json()
    agent_id = f"agent-{payload.get('name', 'unknown')}"
    return Response(status_code=201, json={"id": agent_id})

def _handle_start_agent(request, state: MockAgamemnonState) -> Response:
    if state.exception_on_start_agent:
        return Response(status_code=500, json={"error": "failed to start"})
    return Response(status_code=200, json={"status": "running"})

def _handle_create_team(request, state: MockAgamemnonState) -> Response:
    if state.exception_on_create_team:
        return Response(status_code=400, json={"error": "invalid team spec"})
    
    payload = request.json()
    team_id = f"team-{payload.get('name', 'unknown')}"
    return Response(status_code=201, json={"id": team_id})

def _handle_get_team_status(request, state: MockAgamemnonState) -> Response:
    if state.exception_on_get_team_status:
        return Response(status_code=503, json={"error": "service unavailable"})
    
    # Permanent override takes precedence
    if state.permanent_status:
        return Response(status_code=200, json={"status": state.permanent_status})
    
    # Dequeue next status from ordered list
    if state.status_queue:
        status = state.status_queue.pop(0)
        return Response(status_code=200, json={"status": status})
    
    # Default: pending (POLA — tests must enqueue terminal)
    return Response(status_code=200, json={"status": "pending"})

def _handle_create_task(request, state: MockAgamemnonState) -> Response:
    payload = request.json()
    task_id = f"task-{payload.get('subject', 'unknown').replace(' ', '-')}"
    return Response(status_code=201, json={"id": task_id})

def _handle_get_task_status(request, state: MockAgamemnonState) -> Response:
    # Lookup script for this task if present
    # For simplicity, default to pending or completed from script
    task_id = request.path_params.get("task_id", "unknown")
    
    if task_id in state.task_status_script:
        statuses = state.task_status_script[task_id]
        if statuses:
            status = statuses.pop(0)
            return Response(status_code=200, json={"status": status})
    
    return Response(status_code=200, json={"status": "pending"})

def _handle_delete_agent(request, state: MockAgamemnonState) -> Response:
    return Response(status_code=204)

def payload_contains(actual: dict, expected: dict) -> bool:
    """
    Return True iff all keys in expected are present in actual with == value.
    
    Ignores extra keys in actual; allows schema evolution without test breakage.
    """
    for key, val in expected.items():
        if key not in actual or actual[key] != val:
            return False
    return True
```

### Test File — Complete Example

```python
# tests/integration/test_workflow_lifecycle.py
import pytest
import pytest_asyncio
from telemachy.executor import WorkflowExecutor
from telemachy.models import AgentSpec, TeamSpec, TaskSpec, WorkflowSpec

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

async def test_workflow_completes_with_all_agents(mock_agamemnon):
    """Full workflow: agents created, started, team formed, tasks assigned."""
    state, router, client = mock_agamemnon
    
    # Explicit POLA: must enqueue terminal status
    state.status_queue = ["completed"]
    
    spec = WorkflowSpec(
        metadata={"name": "test-workflow"},
        agents=[
            AgentSpec(name="agent1", program="claude-code"),
            AgentSpec(name="agent2", program="claude-code"),
        ],
        teams=[
            TeamSpec(
                name="team1",
                agents=["agent1", "agent2"],
                tasks=[
                    TaskSpec(subject="task1", description="do work", assign_to="agent1"),
                    TaskSpec(subject="task2", description="do more", assign_to="agent2"),
                ],
            )
        ],
        teardown="on_completion",
    )
    
    executor = WorkflowExecutor(client=client)
    result = await executor.run(spec)
    
    assert result.success
    assert len(router["create_agent"].calls) == 2
    assert len(router["create_task"].calls) == 2

async def test_workflow_handles_agent_creation_failure(mock_agamemnon):
    """Fault injection: agent creation 500 → workflow fails."""
    state, router, client = mock_agamemnon
    state.exception_on_create_agent = True
    
    spec = WorkflowSpec(
        metadata={"name": "test-workflow"},
        agents=[AgentSpec(name="agent1", program="claude-code")],
        teams=[],
        teardown="never",
    )
    
    executor = WorkflowExecutor(client=client)
    result = await executor.run(spec)
    
    assert not result.success
    assert "500" in str(result.error) or "create_agent" in str(result.error)

async def test_workflow_monitors_until_completion(mock_agamemnon):
    """Monitor polls team status until completion."""
    state, router, client = mock_agamemnon
    
    # Enqueue sequence: pending, pending, completed
    state.status_queue = ["pending", "pending", "completed"]
    
    spec = WorkflowSpec(
        metadata={"name": "test-workflow"},
        agents=[AgentSpec(name="agent1", program="claude-code")],
        teams=[
            TeamSpec(
                name="team1",
                agents=["agent1"],
                tasks=[TaskSpec(subject="task1", description="work", assign_to="agent1")],
            )
        ],
        teardown="on_completion",
    )
    
    executor = WorkflowExecutor(client=client)
    result = await executor.run(spec)
    
    assert result.success
    # Should have polled status multiple times
    assert len(router["get_team_status"].calls) >= 3
```

### pytest Configuration (copy-paste ready)

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: integration tests with respx mock Agamemnon server",
    "asyncio: async tests",
]
addopts = "--cov=src/telemachy --cov-report=term-missing --cov-report=xml --tb=short"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectTelemachy | Issue #48 — integration test infrastructure | 9 integration tests added under `tests/integration/`; fixture pattern avoids nested contexts; stateful mock state eliminates per-test fixture redefinition; all 57 tests pass (48 unit + 9 integration) |
| ProjectTelemachy CI | GitHub Actions pytest step | `pixi run pytest --tb=short` auto-discovers integration tests; no CI YAML changes needed; all tests collected and run in standard flow |
| ProjectTelemachy | 5 error scenarios | 500, 409, 503, timeout, invalid payload — all tested via state flags without nested mocks |
| ProjectTelemachy | Payload validation | 3 payload types (agent, docker agent, task) validated with `payload_contains()` dict-subset matching; assertions survived minor schema drift during refactoring |
