---
name: logging-context-deduplication
description: 'Fix duplicated context prefixes in structured logging pipelines. Use
  when: log lines show the same context twice, or empty context renders as [//].'
category: debugging
date: 2026-03-18
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Log lines show duplicated context (e.g., `[T5/12/1]` from filter AND `[T5/12/run_01]` from f-string) |
| **Root Cause** | Logging filter injects fields into records, but message f-strings also manually prefix the same info |
| **Secondary Bug** | When no context is set, format string renders `[//]` instead of being omitted |
| **Scope** | 4 state machine files, 1 logging filter, 1 format string |

## When to Use

- Log output contains the same tier/subtest/run identifier twice per line
- A `logging.Filter` injects context fields that message strings also include manually
- Log lines outside of a scoped context show empty delimiters like `[//]` or `[/]`
- Thread ID fields show raw memory addresses (e.g., `[T:134028120278720]`) instead of human-readable names

## Verified Workflow

### Quick Reference

| Layer | What to change | Pattern |
| ------- | --------------- | --------- |
| Filter | Add composite `log_context_tag` field | Empty when no context, `[T0/00/1]` when set |
| Format string | Use `%(log_context_tag)s` | Replaces `[%(tier_id)s/...]` |
| Log messages | Remove manual `[tier/sub/run]` prefixes | Keep only the message content |
| Thread field | `%(threadName)s` not `%(thread)d` | Human-readable names |

### Step 1: Identify the duplication sources

Trace the logging pipeline to find where context is injected:

1. **Filter-level injection**: A `ContextFilter` (or similar `logging.Filter`) that sets `record.tier_id`, `record.subtest_id`, `record.run_num` from thread-local storage
2. **Format string**: `"%(tier_id)s/%(subtest_id)s/%(run_num)s"` in `logging.basicConfig()` format
3. **Message-level prefixes**: f-strings in log calls like `logger.info(f"[{tier_id}/{subtest_id}/run_{run_num:02d}] ...")`

### Step 2: Remove manual prefixes from log messages

Strip the `[tier/subtest/run]` prefix from all f-string log messages in state machine code. The filter already handles this.

**Before:**
```python
logger.info(
    f"[{tier_id}/{subtest_id}/run_{run_num:02d}] "
    f"{current.value} -> {transition.to_state.value}: {transition.description} ({elapsed:.1f}s)"
)
```

**After:**
```python
logger.info(
    f"{current.value} -> {transition.to_state.value}: {transition.description} ({elapsed:.1f}s)"
)
```

### Step 3: Fix empty-context rendering with composite tag

Replace the always-rendered format field with a composite tag that is empty when no context is set:

**In the ContextFilter:**
```python
def filter(self, record):
    tier_id = getattr(_context, "tier_id", "")
    subtest_id = getattr(_context, "subtest_id", "")
    run_num = getattr(_context, "run_num", None)

    record.tier_id = tier_id
    record.subtest_id = subtest_id
    record.run_num = str(run_num) if run_num is not None else ""

    if tier_id or subtest_id or run_num is not None:
        parts = [tier_id, subtest_id]
        if run_num is not None:
            parts.append(str(run_num))
        record.log_context_tag = " [" + "/".join(parts) + "]"
    else:
        record.log_context_tag = ""
    return True
```

**In the format string:**
```python
# Before: " [%(tier_id)s/%(subtest_id)s/%(run_num)s]"  -> renders "[//]" when empty
# After:  "%(log_context_tag)s"                          -> renders "" when empty
format="%(asctime)s [%(levelname)s] [%(threadName)s]%(log_context_tag)s %(name)s: %(message)s"
```

### Step 4: Use threadName instead of thread ID

Replace `%(thread)d` with `%(threadName)s` for human-readable thread identification:
- `[T:134028120278720]` becomes `[MainThread]` or `[Thread-1]`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Keep manual prefixes, remove filter | Would require updating every log call site to include context | Hundreds of log sites across the codebase; filter approach is the right abstraction | Use filters for cross-cutting concerns, not per-message formatting |
| Conditional format string with `%(tier_id)s` | Format string is static; can't conditionally include/exclude sections | Python's `logging.Formatter` doesn't support conditional sections | Build the conditional logic in the Filter, emit a single composite field |
| Use `os.setpgrp()` for signal handling | Creates new process group, detaching from terminal's foreground group | Kernel sends Ctrl+C/Ctrl+Z to terminal's foreground group, which is now empty | Child processes already use `start_new_session=True`; parent doesn't need its own group |

## Results & Parameters

### Log output comparison

**Before:**
```
2026-03-18 20:10:16 [INFO] [T:136414484813504] [//] scylla.e2e.runner: Experiment completed
2026-03-18 20:10:16 [INFO] [T:136414484813504] [T5/12/1] scylla.e2e.state_machine: [T5/12/run_01] dir_structure_created -> worktree_created: Create git worktree (2.8s)
```

**After:**
```
2026-03-18 20:10:16 [INFO] [MainThread] scylla.e2e.runner: Experiment completed
2026-03-18 20:10:16 [INFO] [Thread-1] [T5/12/1] scylla.e2e.state_machine: dir_structure_created -> worktree_created: Create git worktree (2.8s)
```

### Files modified

| File | Change |
| ------ | -------- |
| `scylla/e2e/log_context.py` | Added composite `log_context_tag` field to ContextFilter |
| `scripts/manage_experiment.py` | Updated format string to use `%(log_context_tag)s` and `%(threadName)s` |
| `scylla/e2e/state_machine.py` | Removed `[tier/sub/run]` prefixes from 5 log messages |
| `scylla/e2e/subtest_state_machine.py` | Removed `[tier/sub]` prefixes from 5 log messages |
| `scylla/e2e/tier_state_machine.py` | Removed `[tier]` prefixes from 5 log messages |
| `scylla/e2e/experiment_state_machine.py` | Removed `[experiment]` prefixes from 3 log messages |
