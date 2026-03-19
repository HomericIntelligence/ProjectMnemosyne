# Session Notes: E2E Runner Hang and Signal Handling Fixes

## Context

User ran:
```bash
pixi run python scripts/manage_experiment.py run --judge-model opus --add-judge sonnet \
  --add-judge haiku --threads 2 --parallel 1 --results-dir ~/fullruns/haiku-2/ \
  --tiers T0 T1 T2 T3 T4 T5 T6 --runs 3 --max-subtests 50 \
  --config tests/fixtures/tests/ --model haiku --until replay_generated
```

Command hung at:
```
ParallelismScheduler initialized: high=2, med=4, low=8
Starting 5 tiers in parallel: ['T0', 'T1', 'T2', 'T3', 'T4']
Tier T0: 24 sub-tests
Tier T1: 10 sub-tests
...
```

Ctrl+C and Ctrl+Z had no effect.

## Root Cause Analysis

6 compounding bugs prevented signal-based interruption:

1. **`as_completed()` + `future.result()` blocks forever** (3 call sites)
   - parallel_tier_runner.py:149 — tier-level parallelism
   - parallel_executor.py:265 — subtest-level parallelism
   - manage_experiment.py:842 — batch mode
   - Main thread blocks in `future.result()` with no timeout; `is_shutdown_requested()` never checked

2. **`proc.communicate(timeout=3600)` blocks thread**
   - stages.py:559 — agent subprocess execution
   - Shutdown flag checked only AFTER communicate returns (up to 1 hour later)

3. **stdin not DEVNULL in Popen**
   - stages.py:550 — agent subprocess inherits parent stdin
   - Interactive prompts can hang the process

4. **Rate limit sleep ignores shutdown**
   - rate_limit.py:300-304 — `time.sleep()` loop has no `is_shutdown_requested()` check

5. **`_resume_event.wait()` blocks forever**
   - parallel_executor.py:100 — no timeout on threading.Event.wait()
   - If main thread crashes during rate limit, workers hang forever

6. **SIGTSTP handler conflict**
   - terminal.py:74-76 registers SIGTSTP as graceful handler
   - manage_experiment.py:889 registers SIGTSTP as force-kill handler
   - terminal_guard() at line 1173 overwrites the force-kill handler

## Files Modified

### Source Changes
- `scylla/e2e/stages.py` — Bugs 2,3: add stdin=DEVNULL, extract _communicate_with_shutdown_check
- `scylla/e2e/parallel_tier_runner.py` — Bug 1: replace as_completed with wait() polling
- `scylla/e2e/parallel_executor.py` — Bugs 1,5: replace as_completed, add resume_event timeout
- `scylla/e2e/rate_limit.py` — Bug 4: add shutdown check in sleep loop
- `scylla/utils/terminal.py` — Bug 6: remove SIGTSTP handler
- `scripts/manage_experiment.py` — Bug 1 + logging: batch polling, log format with context
- `scylla/e2e/log_context.py` — NEW: thread-local ContextFilter for structured logging
- `scylla/e2e/subtest_executor.py` — Set log context at run entry point

### Test Changes
- `tests/unit/e2e/test_parallel_tier_runner.py` — 2 new tests
- `tests/unit/e2e/test_parallel_executor.py` — 3 new tests
- `tests/unit/e2e/test_stages.py` — 2 new tests
- `tests/unit/e2e/test_rate_limit.py` — 2 new tests
- `tests/unit/utils/test_terminal.py` — 1 new test
- `tests/unit/e2e/test_log_context.py` — NEW: 4 tests

## Prior Skills Referenced

- `state-machine-interrupt-handling` — ShutdownInterruptedError pattern
- `e2e-state-machine-bugs` — terminal_guard() disconnected handler fix
- `python-subprocess-terminal-corruption` — stdin=subprocess.DEVNULL pattern

## PR

- ProjectScylla PR #1515
- Branch: `fix-experiment-hang-signal-handling`
- 4924 tests pass, 77.74% coverage
