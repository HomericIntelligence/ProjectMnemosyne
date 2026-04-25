---
name: testing-asyncio-await-task-bot-false-positive
description: "Identifies and dismisses the GitHub code-quality bot false positive where `await <task>` in asyncio test code is flagged as 'Statement has no effect'. Use when: (1) github-code-quality[bot] flags `await <task>` as a no-effect statement, (2) an asyncio.Task stored in a local variable is awaited as cleanup after test assertions, (3) a PR review contains bot comments about awaiting a Task variable."
category: testing
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - asyncio
  - python
  - false-positive
  - github-code-quality-bot
  - await-task
  - pytest-asyncio
  - static-analysis
---

# GitHub Code-Quality Bot False Positive: `await task` in asyncio Tests

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Identify the GitHub code-quality bot false positive on `await <asyncio.Task>` and confirm no code change is needed |
| **Outcome** | False positive confirmed — the `await` is correct cleanup boilerplate; bot comment is noise |
| **Verification** | unverified |

## When to Use

- `github-code-quality[bot]` posts an inline comment on a PR at a line containing `await <local_var>` with the message **"Statement has no effect."**
- An `asyncio.Task` is created via `asyncio.create_task(...)` or `asyncio.get_event_loop().create_task(...)` and stored in a local variable
- The task is later `await`ed as a cleanup step after the test's main assertions
- You need to decide whether a bot PR comment requires a code change or can be dismissed

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
# Pattern that triggers the false positive:
advance_task = asyncio.get_event_loop().create_task(some_coroutine())

# ... test assertions here ...

await advance_task   # <-- bot flags this as "Statement has no effect"
                     # Bot is WRONG. Do NOT remove this line.
```

```bash
# No code change needed.
# Simply dismiss or ignore the bot comment.
```

### Detailed Steps

1. **Identify the flagged line**: The bot comment will reference a line like `await <variable_name>` where the variable holds an `asyncio.Task`.

2. **Confirm the pattern**: Check how `<variable_name>` was created. If it is created via `asyncio.create_task(...)` or `loop.create_task(...)`, this is the known false positive.

3. **Why the `await` is correct** — the `await` on an `asyncio.Task`:
   - Blocks the coroutine until the background task completes (required for test determinism)
   - Propagates any exception the task raised (skipping this silently swallows background errors)
   - Prevents dangling tasks: without `await`, test teardown may print `RuntimeWarning: Task was destroyed but it is pending!`

4. **Why the bot is wrong**: The GitHub code-quality static analyzer does not model Python's awaitable protocol. It sees `await expr` where `expr` is a local variable reference and (incorrectly) concludes the expression result is unused — identical to a bare `x` statement. However, `await` on a `Task` is an active operation with side effects.

5. **Action**: Do nothing. Leave the code as-is. The `await` is correct and necessary. Add a reviewer comment on the PR explaining the false positive if needed (e.g., "Bot false positive — `await advance_task` is required cleanup to prevent dangling tasks and surface background exceptions").

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Remove `await` | Removing `await advance_task` to silence the bot | Would cause `RuntimeWarning: Task was destroyed but it is pending!` and silently swallow background exceptions | Never remove asyncio task awaits to satisfy a static analysis bot |
| Assign away result | `_ = await advance_task` to suppress the "no effect" warning | The bot flags the `await` expression, not the assignment; also stylistically misleading | The assignment does not affect whether the bot flags the line |
| `# noqa` comment | Adding `# noqa` or inline suppression | The GitHub code-quality bot does not respect Python `# noqa` directives | Bot suppression requires different mechanisms (e.g., config file exclusions), but the correct response is dismissal not suppression |

## Results & Parameters

**Pattern fingerprint**:
```
File: tests/<any_test_file>.py
Line N: await <task_variable>
Bot message: "Statement has no effect."
Task variable created by: asyncio.create_task(...) or loop.create_task(...)
```

**Correct response**:
- No code change required
- Dismiss bot comment as false positive
- PR is valid as-is

**Distinguishing true positives from false positives**:

| Situation | Bot Correct? | Action |
|-----------|-------------|--------|
| `await asyncio.Task` stored in local var | No — false positive | Dismiss, keep code |
| `x` (bare expression, non-awaitable) | Yes — true positive | Remove dead statement |
| `await coroutine_function()` (result unused) | Sometimes — depends on side effects | Review intent |

**RuntimeWarning that appears without proper `await`**:
```
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
Task was destroyed but it is pending!
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PR #428, `tests/test_task_claimer.py:283` | `await advance_task` flagged as "Statement has no effect" by `github-code-quality[bot]` |
