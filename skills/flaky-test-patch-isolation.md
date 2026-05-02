---
name: flaky-test-patch-isolation
description: Fix flaky tests caused by class-level mock state leakage via patch.object(__class__,
  ...). Adds autouse teardown fixture with patch.stopall() to isolate test classes.
category: testing
date: '2026-03-19'
version: 1.0.0
---
# Skill: Flaky Test — Class-Level Patch Isolation

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-03 |
| Category | testing |
| Objective | Fix intermittent test failure caused by class-level mock state leakage |
| Outcome | Success — autouse teardown fixture with `patch.stopall()` eliminated flakiness |
| Issue | HomericIntelligence/ProjectScylla#1131 |

## When to Use

Apply this pattern when:
- A test is **flaky only in the full suite** (passes in isolation or smaller subsets)
- The test suite has classes with `patch.object(SomeClass, "method", ...)` (class-level patching)
- Flakiness correlates with **test ordering** or **suite size**
- A test class modifies class attributes via mocks and a test sometimes fails mid-patch

## Root Cause Pattern

`patch.object(obj.__class__, "method", ...)` patches the **class** (not the instance). If the context manager exits abnormally (test fails inside `with patch.object(...)`), the patch remains active on the class for all subsequent tests — even those in different test classes.

```python
# DANGEROUS: patches ConfigLoader class-level _load_yaml
with patch.object(orchestrator.loader.__class__, "_load_yaml", wraps=...):
    ...  # if this fails, ConfigLoader._load_yaml stays patched
```

## Verified Workflow

### 1. Identify the leak

Look for `patch.object(instance.__class__, ...)` patterns in test classes that run before the flaky test.

```bash
grep -rn "patch.object.*__class__" tests/
```

### 2. Add autouse teardown to the leaking class

```python
from collections.abc import Generator
from unittest.mock import patch

class TestWithClassLevelPatches:
    @pytest.fixture(autouse=True)
    def _isolate(self) -> Generator[None, None, None]:
        """Ensure no class-level mock state bleeds into subsequent tests."""
        yield
        patch.stopall()
```

`patch.stopall()` stops **all** patches started via `patch()`, `patch.object()`, etc. that haven't been explicitly stopped. It is safe to call even when no patches are active.

### 3. Move imports to module level

Remove redundant per-method `from unittest.mock import patch` imports:

```python
# Before (in each test method):
def test_something(self):
    from unittest.mock import patch
    with patch(...):
        ...

# After (module level):
from unittest.mock import patch

def test_something(self):
    with patch(...):
        ...
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts / Alternatives Considered

| Approach | Why Rejected |
| ---------- | ------------- |
| Use `patch.object(instance, "method", ...)` | Would fix the root cause but was out of scope — the test predated this session |
| Add teardown only to `TestEvalOrchestratorEndToEnd` | Wrong class — the leak originates in `TestEvalOrchestratorWithFixture` |
| `unittest.mock.patch` as a decorator | No benefit over context manager; doesn't address class-level leak |

## Key Code

```python
# In the class that does class-level patching:
class TestEvalOrchestratorWithFixture:
    @pytest.fixture(autouse=True)
    def _isolate(self) -> Generator[None, None, None]:
        """Ensure no class-level mock state bleeds into subsequent tests.

        Uses unittest.mock.patch's stopall to clean up any patches that may
        have been left active if a test fails mid-context-manager, preventing
        class-level attribute leakage into TestEvalOrchestratorEndToEnd.
        """
        yield
        patch.stopall()
```

## Results

- All 3799 tests pass (was: intermittent failure under load)
- 67.96% combined coverage (above 9% threshold)
- Pre-commit (ruff, mypy, black) all pass
- Fix is minimal: 13 insertions, 9 deletions
