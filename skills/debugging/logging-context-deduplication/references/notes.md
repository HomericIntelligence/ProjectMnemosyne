# Session Notes: Logging Context Deduplication

## Date: 2026-03-18

## Context

ProjectScylla's E2E experiment runner uses a hierarchical state machine (experiment -> tier -> subtest -> run) with parallel execution via ThreadPoolExecutor. Logging uses Python's standard `logging` module with a `ContextFilter` that injects thread-local tier/subtest/run context into every log record.

## Problem 1: Duplicated prefixes

The `ContextFilter` in `log_context.py` injects `tier_id`, `subtest_id`, and `run_num` into log records. The format string in `manage_experiment.py` renders these as `[T5/12/1]`. But the state machine code ALSO manually prefixed every log message with `[T5/12/run_01]` via f-strings. Result: both appeared on every line.

### Files with manual prefixes removed

- `state_machine.py`: 5 log messages (debug, info with timing, until-target, shutdown-interrupted, error)
- `subtest_state_machine.py`: 5 log messages (debug, info with timing, until-target, until-halt, shutdown-interrupted)
- `tier_state_machine.py`: 5 log messages (debug, info with timing, until-target, shutdown-interrupted, rate-limit)
- `experiment_state_machine.py`: 3 log messages (debug, info with timing, until-target)

## Problem 2: [//] artifact

When log messages are emitted outside of any tier/subtest scope (e.g., experiment-level messages, startup), all three context fields are empty strings. The format `[%(tier_id)s/%(subtest_id)s/%(run_num)s]` renders as `[//]`.

### Fix: composite log_context_tag

Added a computed `log_context_tag` field to `ContextFilter.filter()`:
- When any context is set: ` [T5/12/1]` (with leading space for formatting)
- When no context is set: `""` (empty string, nothing rendered)

The format string uses `%(log_context_tag)s` instead of the static `[%(tier_id)s/%(subtest_id)s/%(run_num)s]`.

Smart part-omission: if `run_num` is None but `tier_id`/`subtest_id` are set, renders ` [T5/12]` (no trailing slash).

## Problem 3: Thread ID readability

`%(thread)d` renders as `[T:134028120278720]` — a raw memory address from `threading.get_ident()`. Changed to `%(threadName)s` which renders as `[MainThread]`, `[Thread-1]`, etc.

## Problem 4: Signal handling (separate fix in same session)

`os.setpgrp()` at `manage_experiment.py:898` created a new process group, detaching from the terminal's foreground group. Ctrl+C (SIGINT) and Ctrl+Z (SIGTSTP) go to the terminal's foreground group, which no longer included the Python process.

Fix: Removed `os.setpgrp()` (children already use `start_new_session=True`), simplified `_kill_group` to `_force_exit` (calls `restore_terminal()` + `os._exit()`), moved SIGTSTP registration before batch-mode early return.

## Test verification

- 171 unit tests pass (58 state machine + 113 manage_experiment)
- 6 log_context tests pass (updated assertions for `log_context_tag`)
- Pre-commit hooks pass on all modified files
