---
name: dependency-resolver-public-api-seam
description: "Use when a dependency resolver owns a graph or edge store but call sites bypass the public API and mutate internals directly, especially in pipeline admission or topological-order code."
category: architecture
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [automation, dependency-resolution, resolver, public-api, regression-test, ci]
---

# Dependency Resolver Public API Seam

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Fix a CI regression by restoring a stable public seam for dependency-edge insertion in the automation pipeline, rather than letting admission code reach into resolver internals. |
| **Outcome** | CI went green after adding `DependencyResolver.add_dependency()` and routing admission/order handling through it, with regression coverage that fails if callers touch `resolver.graph` directly. |
| **Verification** | verified-ci |

## When to Use

- A resolver, coordinator, or scheduler owns a graph or edge store and a caller is mutating that internal object directly.
- A topological ordering or admission path needs dependency edges inserted through one canonical method.
- You want a regression test that fails if future code bypasses the public seam and reaches into internals.
- A fix needs to preserve existing ordering semantics while tightening encapsulation.

## Verified Workflow

### Quick Reference

```python
class FakeDependencyResolver:
    class Graph:
        def add_dependency(self, *_args):
            pytest.fail("call DependencyResolver.add_dependency()")
```

### Detailed Steps

1. Add a public edge-insertion method on the resolver, such as `add_dependency(issue_number, depends_on)`.
2. Make any internal edge setup in `add_issue()` delegate to that public method so all edge creation goes through one path.
3. Update admission/order code to call `resolver.add_dependency(...)` instead of mutating `resolver.graph` directly.
4. Keep the ordering guard focused on in-set dependencies only, so out-of-queue edges remain fail-open.
5. Add a regression test that monkeypatches or fakes the resolver and fails if a caller reaches into `graph.add_dependency()` directly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Call `resolver.graph.add_dependency(...)` from admission | Reached directly into the resolver's internal graph object | Bypassed the public seam and made the admission layer depend on internal structure | Expose a public resolver method and route all callers through it |
| Keep one edge path in `add_issue()` and another in admission | Left edge insertion split across two code paths | Duplicated logic drifts and makes future refactors brittle | Centralize dependency-edge insertion in one public API |
| Test only the final order | Asserted sort order without guarding the seam | The order can stay correct even if future code bypasses the resolver API again | Add a regression test that fails on direct graph access |

## Results & Parameters

- `DependencyResolver.add_dependency(issue_number, depends_on)` is the canonical edge-insertion API.
- `DependencyResolver(skip_closed=False)` remains the right constructor for implementation ordering, because the queue is ordering in-memory issue metadata rather than filtering closed-state behavior.
- `order_for_implementation()` still drops dependencies that are outside the current issue set, which preserves the existing fail-open behavior.
- The regression test uses a fake resolver whose `graph.add_dependency()` fails the test, so the seam is enforced instead of only implied.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1994 / issue #1915 | Admission and dependency-ordering refactor that reached green CI after the public resolver seam was restored |
