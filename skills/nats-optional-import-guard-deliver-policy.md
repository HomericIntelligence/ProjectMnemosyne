---
name: nats-optional-import-guard-deliver-policy
description: "Debugging pattern for nats-py optional import guard failures caused by enum conversion. Use when: (1) nats subscriber tests show mock_js.subscribe.call_count == 0, (2) adding an enum/type conversion from nats.js.api inside _subscribe_loop, (3) CI shows 'nats-py is not installed' error when nats IS mocked."
category: debugging
date: 2026-04-12
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - nats
  - optional-dependency
  - import-guard
  - lazy-import
  - DeliverPolicy
  - nats-py
  - python
  - asyncio
---

# nats-py Optional Import Guard: DeliverPolicy Enum Pitfall

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Objective** | Pass `deliver_policy` from NATSConfig to `js.subscribe()` in ProjectScylla (issue #1654) |
| **Outcome** | Successful — PR #1784 merged; fix avoids triggering optional import guard by passing string directly |
| **Verification** | verified-ci |

## When to Use

- nats subscriber tests are showing `mock_js.subscribe.call_count == 0` after adding a new `js.subscribe()` argument
- Adding a type or enum from `nats.js.api` (e.g. `DeliverPolicy`, `AckPolicy`, `ReplayPolicy`) inside `_subscribe_loop` or any function that has an optional-dependency lazy import guard
- CI logs show `"nats-py is not installed. Install with: pip install 'scylla[nats]'"` even though nats IS mocked in the test
- A new import from an optional package was placed inside an existing `try/except ImportError` block

## Verified Workflow

### Quick Reference

```python
# WRONG — triggers import guard on environments without nats-py installed
from nats.js.api import DeliverPolicy  # placed inside try block

sub = await js.subscribe(
    subject=subject,
    durable=durable,
    stream=self._config.stream,
    deliver_policy=DeliverPolicy(self._config.deliver_policy),  # enum conversion
)

# CORRECT — pass string directly; nats-py accepts str at runtime
sub = await js.subscribe(
    subject=subject,
    durable=durable,
    stream=self._config.stream,
    deliver_policy=self._config.deliver_policy,  # plain string, no import needed
)
```

### Detailed Steps

1. **Identify the symptom**: Test fails with `assert 0 == 3` on `mock_js.subscribe.call_count`. Check for `"nats-py is not installed"` in test log output — this confirms the guard triggered.

2. **Locate the import guard pattern** in the subscriber code:

   ```python
   async def _subscribe_loop(self) -> None:
       try:
           import nats as nats_client  # lazy import — nats-py is optional
       except ImportError:
           logger.error("nats-py is not installed. Install with: pip install 'scylla[nats]'")
           return  # ← exits early
   ```

3. **Find the problematic enum import** — look for any `from nats.*` import placed INSIDE the `try` block after the initial `import nats`:

   ```python
   try:
       import nats as nats_client
       from nats.js.api import DeliverPolicy  # ← this is the culprit
   except ImportError:
       logger.error("nats-py is not installed.")
       return
   ```

4. **Understand why it fails**: In test environments, `import nats` may succeed (mocked) but `from nats.js.api import DeliverPolicy` raises `ImportError` because the mock doesn't define that submodule. The `except ImportError` catches it and calls `return` — so `js.subscribe()` is never reached.

5. **Apply the fix**: Remove the enum import entirely. Pass the config field as a plain string. nats-py's `js.subscribe()` accepts string values for `deliver_policy` at runtime:

   ```python
   # Remove: from nats.js.api import DeliverPolicy
   sub = await js.subscribe(
       subject=subject,
       durable=durable,
       stream=self._config.stream,
       deliver_policy=self._config.deliver_policy,  # str, not DeliverPolicy enum
   )
   ```

6. **If mypy complains** about `str` vs `DeliverPolicy`: add `# type: ignore[arg-type]` on the line, or use an `Optional[str]` type annotation that matches the config model. Do not re-introduce the enum import to satisfy mypy.

7. **Verify**: Run the affected unit tests. `mock_js.subscribe.call_count` should now equal the expected value.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Enum conversion inside try block | `from nats.js.api import DeliverPolicy` placed inside the `try:` after `import nats`, used as `DeliverPolicy(self._config.deliver_policy)` | Mock does not define `nats.js.api` submodule → `ImportError` → guard's `return` fires → `js.subscribe()` never called | Any import from an optional dependency inside a try/except ImportError guard will trigger early return if that import fails, even if previous imports in the same block succeeded |
| Enum conversion before try block | Placing `from nats.js.api import DeliverPolicy` at module top level | Causes `ImportError` at import time in environments without nats-py, breaking the optional-dependency contract entirely | Optional dependency imports must always be deferred inside the guard, not placed at module level |

## Results & Parameters

**Correct pattern — no enum import, plain string passthrough:**

```python
async def _subscribe_loop(self) -> None:
    try:
        import nats as nats_client  # lazy import — nats-py is optional
    except ImportError:
        logger.error(
            "nats-py is not installed. Install with: pip install 'scylla[nats]'"
        )
        return

    # ... setup code ...

    sub = await js.subscribe(
        subject=subject,
        durable=durable,
        stream=self._config.stream,
        deliver_policy=self._config.deliver_policy,  # str from config — no enum needed
    )
```

**CI failure signature (before fix):**

```
ERROR scylla.nats.subscriber:subscriber.py:109 nats-py is not installed. Install with: pip install 'scylla[nats]'
AssertionError: assert 0 == 3  (mock_js.subscribe.call_count)
FAILED tests/unit/nats/test_subscribe_multi.py::TestMultiSubjectSubscription::test_subscribes_to_all_subjects
```

**General rule**: Any `from <optional-package>.*` import placed inside a `try/except ImportError` block will silently trigger that guard if the submodule is absent or not mocked — even when the top-level package import succeeds.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectScylla | PR #1784, fix for issue #1654 (pass deliver_policy to js.subscribe) | 2026-04-12 — CI passed |
