---
name: testing-mock-fault-injection-must-simulate-side-effects-not-just-record
description: "Mock services for chaos/fault injection tests must simulate the actual side effects of each fault (slow responses, degraded health, stalled queues) — not just record or acknowledge the fault command. Use when: (1) writing or debugging chaos integration tests, (2) mock has a /inject_fault or /v1/chaos/* endpoint, (3) tests pass at 'fault was recorded' level but fail at 'system observed faulty behavior'."
category: testing
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Testing: Mock Fault Injection Must Simulate Side Effects, Not Just Record

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-10 |
| **Objective** | Fix chaos integration tests R02/R03/R04/R05 that failed because the mock Agamemnon server only recorded fault injections without simulating their effects |
| **Outcome** | All 4 chaos tests (latency, kill, queue-starve) passed after adding side-effect simulation to the mock |
| **Verification** | verified-ci |
| **Source** | ProjectCharybdis PR #88 — CI integration tests with NATS + mock Agamemnon |

## When to Use

- Writing or debugging chaos tests / fault injection integration tests
- Mock service has a `/inject_fault`, `/v1/chaos/*`, or similar fault-injection endpoint
- Tests pass at "fault was recorded" level but fail at "system observed faulty behavior"
- Designing a test double for a service that is expected to emit chaotic behavior
- CI shows chaos tests failing even though the `/inject` call returns 200

## Verified Workflow

### Quick Reference

```python
# GOOD — mock records AND simulates the resulting behavior

def _apply_fault_effects(state):
    """Call at the start of every response handler."""
    if (f := state.active_faults.get("latency")):
        time.sleep(f.delay_ms / 1000)

@app.get("/v1/health")
def health():
    if state.active_faults.get("kill"):
        return Response(status_code=503, content={"status": "degraded"})
    _apply_fault_effects(state)
    return {"status": "ok"}

@app.get("/v1/tasks")
def tasks():
    _apply_fault_effects(state)
    if not state.active_faults.get("queue-starve"):
        _advance_queue(state)   # skip advancement under starvation
    return state.tasks
```

### Detailed Steps

1. Implement the `/v1/chaos/inject` endpoint to store the fault config in `state.active_faults[fault_id]`.
2. Define a shared `_apply_fault_effects()` helper that checks `state.active_faults` and performs the appropriate side effect.
3. Call `_apply_fault_effects()` at the **top** of every response handler (for cross-cutting faults like latency).
4. For fault types with targeted effects (kill, queue-starve), add conditional branches inside the specific affected endpoints.
5. Implement a `/v1/chaos/reset` endpoint that clears `state.active_faults` so tests can restore the mock to normal behavior.
6. For each chaos test: (1) inject the fault via POST, (2) call a **different** endpoint, (3) assert that endpoint's response shows the chaos effect.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Mock `/v1/chaos/inject` accepts and stores fault config, returns 200. No actual side effect on subsequent requests. | Tests asserted on observed chaos: slow responses, 503 health checks, stalled queue. Mock never produced any of those effects, so R02–R05 failed despite the inject call succeeding. | Recording the intent of a fault is not the same as simulating its effects. The mock must change behavior of OTHER endpoints based on active faults. |
| 2 | Implement the latency fault only, skip kill / queue-starve | Tests R03 and R05 still failed because they asserted on health degradation and queue stall respectively. | Each fault type needs its own simulation. There is no generic fault effect — each one has a specific side effect the mock must encode. |
| 3 | Apply fault effects only to designated "chaos endpoints", not all handlers | Some tests asserted that ALL endpoints slow down during a latency fault. Restricting effects to select endpoints gave false greens in isolation but wrong results in full suite. | Cross-cutting fault effects (latency, error-rate) should be applied via a shared middleware or `_apply_fault_effects()` helper called at the top of every handler. |

## Results & Parameters

### Fault Type Reference Table

| Fault | Where Effect Manifests | How to Simulate |
|-------|------------------------|-----------------|
| `latency` | All endpoints | `time.sleep(delay_ms / 1000)` at start of every handler |
| `kill` / `unavailable` | Health / readiness endpoints | Return `503` + `{"status": "degraded"}` JSON body |
| `queue-starve` | Task-fetching / dequeue endpoints | Skip the "advance state" step |
| `error-rate` | All response endpoints | With probability `p`, return `500` |
| `clock-skew` | Endpoints that emit timestamps | Add fixed offset to `now()` |

### Test Pattern

Each chaos test should follow this structure:

```python
def test_latency_fault(mock_agamemnon, client):
    # 1. Inject fault
    client.post("/v1/chaos/inject", json={"id": "latency", "delay_ms": 500})

    # 2. Call a DIFFERENT endpoint
    start = time.time()
    resp = client.get("/v1/tasks")
    elapsed = time.time() - start

    # 3. Assert the chaos effect was observed
    assert elapsed >= 0.5, f"Expected latency >= 500ms, got {elapsed*1000:.0f}ms"
    assert resp.status_code == 200
```

### Full Mock Skeleton

```python
import time
from dataclasses import dataclass, field
from typing import Dict, Any
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

def _advance_queue():
    for t in state.tasks:
        if t.get("status") == "pending":
            t["status"] = "completed"
            break
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectCharybdis | PR #88 — CI integration tests with NATS + mock Agamemnon | Chaos tests R02/R03/R04/R05 all green after fix |
