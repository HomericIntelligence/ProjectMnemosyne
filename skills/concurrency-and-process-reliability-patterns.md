---
name: concurrency-and-process-reliability-patterns
description: "Debugging and fixing concurrency bugs and process-level reliability failures in
  Python. Use when: (1) batch/parallel workers hang on exit or ignore Ctrl+C, (2) subprocess
  stdin blocks because DEVNULL is missing, (3) os.setpgrp() or os.setsid() breaks terminal
  signal delivery, (4) stty called from a worker thread blocks the main thread, (5) global
  parallelism control needed across multiple ProcessPoolExecutors, (6) pytest OOM-kills the
  shell with no traceback, (7) pytest hangs due to unmocked Monte Carlo simulations,
  (8) nats-py optional import guard fires silently due to an enum import inside the try block,
  (9) nats-py printing stack traces instead of clean connection state, (10) subprocess git
  clone fails with transient network errors."
category: debugging
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: concurrency-and-process-reliability-patterns.history
tags:
  - subprocess
  - signal
  - process-group
  - semaphore
  - multiprocessing
  - pytest
  - oom
  - ulimit
  - monte-carlo
  - mock
  - nats
  - asyncio
  - retry
  - transient-errors
  - threading
---

# Concurrency and Process Reliability Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Theme** | Diagnosing failure modes that only surface under concurrent execution or resource exhaustion |
| **Languages** | Python 3.10+ |
| **Key Tools** | subprocess, threading, signal, multiprocessing, pytest, nats-py, asyncio |
| **Absorbed Skills** | batch-subprocess-signal-hang, bisect-pytest-oom-with-ulimit, global-semaphore-parallelism, mock-expensive-simulations, nats-optional-import-guard-deliver-policy, nats-py-connection-resilience-patterns, retry-transient-errors |

## When to Use

- ThreadPoolExecutor or ProcessPoolExecutor workers hang on exit even though work completed
- `Ctrl+C` has no effect after `os.setpgrp()` or `os.setsid()` was called
- `subprocess.run()` blocks for seconds — missing `stdin=subprocess.DEVNULL`
- `stty sane` called from a worker thread blocks terminal restoration
- `--parallel N` creates N workers **per tier** instead of N workers globally
- pytest run kills the shell, freezes WSL2, or exits with code 137 (SIGKILL) and zero traceback
- pytest hangs partway through a run due to unmocked Monte Carlo / bootstrap simulations
- nats subscriber tests show `mock_js.subscribe.call_count == 0` after adding a new argument
- nats-py prints full stack traces on connection failure instead of clean status
- git clone fails intermittently with "curl 56", "Connection reset by peer", or "early EOF"

## Verified Workflow

### Pattern 1 — Subprocess Stdin Blocking

**Symptom**: Non-interactive subprocess call blocks for 3–30 s.

**Fix**: Always pass `stdin=subprocess.DEVNULL` to non-interactive subprocess calls.

```python
# BEFORE (blocks waiting for stdin)
result = subprocess.run(["cmd", "--flag"], capture_output=True, text=True, timeout=30)

# AFTER (returns immediately)
result = subprocess.run(
    ["cmd", "--flag"],
    capture_output=True,
    text=True,
    timeout=30,
    stdin=subprocess.DEVNULL,
)
```

### Pattern 2 — os.setpgrp() Breaks Ctrl+C

**Symptom**: Pressing Ctrl+C has no effect; process ignores SIGINT entirely.

**Root Cause**: `os.setpgrp()` / `os.setsid()` moves the process into a new process group.
The terminal sends SIGINT to the **foreground process group** only.

**Fix**: Remove `os.setpgrp()`. Use explicit signal handlers and `os.killpg()` only as a
second-signal force-kill handler.

### Pattern 3 — stty from Worker Threads Hangs

**Symptom**: ThreadPoolExecutor workers hang on cleanup after all work completes.

**Fix**: Guard terminal restoration to main thread only.

```python
import threading

def restore_terminal() -> None:
    import contextlib
    with contextlib.suppress(Exception):
        if threading.current_thread() is not threading.main_thread():
            return  # Only the main thread owns the controlling terminal
        if sys.stdin.isatty():
            subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
```

### Pattern 4 — Global Semaphore for Cross-Process Parallelism

**Symptom**: `--parallel 6` with 5 tiers spawns 30 concurrent agents instead of 6.

**Fix**: Use `Manager().Semaphore()` (NOT `multiprocessing.Semaphore()`) so the semaphore
survives serialization across ProcessPoolExecutor boundaries.

```python
from multiprocessing import Manager

# In main runner
manager = Manager()
global_semaphore = manager.Semaphore(config.parallel_subtests)

# In worker process — acquire before expensive work
if global_semaphore:
    global_semaphore.acquire()
try:
    # ... run agent / expensive work ...
finally:
    if global_semaphore:
        global_semaphore.release()
```

**Key rules**:
- Acquire **inside the worker process**, not in the main process (avoids blocking submission).
- Always wrap in `try/finally` to guarantee release even on exceptions.

### Pattern 5 — Bisect Pytest OOM with ulimit

**Symptom**: pytest run kills the shell or exits 137 with no traceback.

**Fix**: Set `ulimit -v` BEFORE invoking pytest so the kernel raises `MemoryError` inside
Python instead of SIGKILLing the entire process tree.

#### Quick Reference

```bash
# Phase 1 — cap memory before pytest
ulimit -v 4194304   # 4 GiB virtual memory
ulimit -t 180       # 180 CPU-seconds

# Phase 2 — bisect at file level (-v shows last test ID before OOM)
pytest <test-file> --no-cov --cov-fail-under=0 -p no:cacheprovider -v 2>&1 | tee /tmp/diag.log

# Phase 3 — bulk per-test loop
pytest <file> --collect-only -q --no-cov --cov-fail-under=0 | grep '::' > /tmp/tests.lst
while read -r t; do
  printf '%s ... ' "$t"
  timeout 30 pytest "$t" --no-cov --cov-fail-under=0 -p no:cacheprovider -q > /tmp/one.log 2>&1
  case $? in
    0)   echo PASS ;;
    124) echo TIMEOUT ;;
    137) echo OOM ;;
    *)   echo "FAIL($?)" ;;
  esac
done < /tmp/tests.lst | tee /tmp/per-test.txt

# Phase 4 — tracemalloc attribution (outside pytest)
python -X tracemalloc=10 - <<'PY'
import tracemalloc
tracemalloc.start()
# reproduce test logic here
for s in tracemalloc.take_snapshot().statistics('lineno')[:5]:
    print(s)
PY
```

### Pattern 6 — Mock Expensive Simulations (pytest hangs at fixed %)

**Symptom**: pytest hangs at a fixed percentage; tests only assert structural correctness.

**Fix**: Add an `autouse` fixture in the relevant `conftest.py`. Patch **both** the caller
namespace (for `from X import Y` imports) **and** the origin namespace.

```python
from unittest.mock import patch
import pytest

@pytest.fixture(autouse=True)
def mock_slow_computations():
    """Mock any function with O(N*simulations) runtime."""
    with (
        patch("caller_module.expensive_fn", return_value=0.5, create=True),
        patch("origin.package.expensive_fn", return_value=0.5),
    ):
        yield
```

**Notes**:
- `create=True` is needed when the caller module is loaded via `sys.path.insert` (scripts/),
  not a proper package.
- Always patch the caller namespace when `from X import Y` is used (names are already bound).
- Diagnose with `git bisect` + `timeout 60 pytest <file> --no-cov -q` to find the
  introducing commit.

### Pattern 7 — nats-py Optional Import Guard: Enum Pitfall

**Symptom**: `mock_js.subscribe.call_count == 0`; CI shows "nats-py is not installed" even
though nats IS mocked.

**Root Cause**: An enum import (`from nats.js.api import DeliverPolicy`) placed inside the
`try:` block causes `ImportError` (mock doesn't define submodule) → guard's `return` fires.

**Fix**: Pass config field as a plain string — nats-py accepts strings at runtime.

```python
# WRONG — triggers import guard in test environments
from nats.js.api import DeliverPolicy  # inside try block
deliver_policy=DeliverPolicy(self._config.deliver_policy)

# CORRECT — no import needed
deliver_policy=self._config.deliver_policy  # plain string from config
```

If mypy complains, add `# type: ignore[arg-type]` rather than re-introducing the import.

### Pattern 8 — nats-py Connection Resilience

**Symptom**: nats-py prints full tracebacks on every failed connection attempt.

**Fix**: Suppress nats logger, use `allow_reconnect=False`, wrap with `asyncio.wait_for`,
and manage retries externally with an interruptible sleep.

```python
import asyncio, logging, nats as nats_mod

logging.getLogger("nats").setLevel(logging.CRITICAL)  # suppress internal tracebacks
RETRY_INTERVAL = 5

async def run(nats_url: str):
    stop = asyncio.Event()

    async def disconnected_cb(): print("[DISCONNECTED]")
    async def reconnected_cb():  print("[RECONNECTED]")
    async def closed_cb():       print("[CLOSED]")

    while not stop.is_set():
        try:
            nc = await asyncio.wait_for(
                nats_mod.connect(
                    nats_url,
                    allow_reconnect=False,   # fail fast — manage retries externally
                    connect_timeout=3,
                    disconnected_cb=disconnected_cb,
                    reconnected_cb=reconnected_cb,
                    closed_cb=closed_cb,
                ),
                timeout=5,
            )
            print(f"[CONNECTED] {nats_url}")
            while not nc.is_closed:
                await asyncio.sleep(0.1)
            print("[DISCONNECTED] Connection lost")
        except (OSError, asyncio.TimeoutError, Exception) as e:
            print(f"[DISCONNECTED] {type(e).__name__}: {e}")

        if not stop.is_set():
            print(f"[RECONNECTING] Retrying in {RETRY_INTERVAL}s...")
            try:
                await asyncio.wait_for(stop.wait(), timeout=RETRY_INTERVAL)
            except asyncio.TimeoutError:
                pass
```

**Key rules**:
- All nats-py callbacks (`disconnected_cb`, `reconnected_cb`, `closed_cb`, `error_cb`) must
  be `async def` coroutines.
- `connect_timeout` only covers the TCP socket; wrap with `asyncio.wait_for` for a hard
  ceiling.
- Poll `nc.is_closed` (not `nc.is_connected`) when `allow_reconnect=False`.

### Pattern 9 — Retry Transient Subprocess / Network Errors

**Symptom**: `git clone` fails with "curl 56 Recv failure: Connection reset by peer" or
"early EOF".

**Fix**: Exponential backoff retry (3 attempts, 1 s / 2 s / 4 s). Fail immediately on
permanent errors (auth, 404, permission denied).

```python
import time

TRANSIENT_PATTERNS = [
    "connection reset", "connection refused",
    "network unreachable", "network is unreachable",
    "temporary failure", "could not resolve host",
    "curl 56", "timed out", "early eof", "recv failure",
]

max_retries, base_delay = 3, 1.0

for attempt in range(max_retries):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        break

    stderr = result.stderr.lower()
    is_transient = any(p in stderr for p in TRANSIENT_PATTERNS)

    if not is_transient or attempt == max_retries - 1:
        raise RuntimeError(f"Operation failed: {result.stderr}")

    delay = base_delay * (2 ** attempt)
    logger.warning(f"Retry {attempt+1}/{max_retries} in {delay}s: {result.stderr.strip()}")
    time.sleep(delay)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Missing `stdin=DEVNULL` for non-interactive subprocess | Called `subprocess.run(["claude", "--print", "ping"])` without stdin redirect | CLI tool waited for stdin; process blocked 3–30 s | Always add `stdin=subprocess.DEVNULL` for non-interactive subprocess calls |
| Remove SIGTSTP handler but keep `os.setpgrp()` | Thought only the SIGTSTP kill handler was the signal problem | `os.setpgrp()` itself isolates the process from ALL terminal signals, including SIGINT | `os.setpgrp()` affects every terminal signal, not just the ones you explicitly handle |
| Call `stty sane` from worker threads | Terminal restoration in `__finally__` of context manager ran in ThreadPoolExecutor workers | Worker threads do not own the controlling terminal; `stty` blocked forever | Guard all terminal-manipulation commands with a main-thread check |
| `multiprocessing.Semaphore()` for cross-process sharing | Used direct `multiprocessing.Semaphore()` instead of `Manager().Semaphore()` | Direct semaphore cannot be serialized across ProcessPoolExecutor boundaries | `Manager().Semaphore()` creates a server process that hosts the semaphore and allows cross-process sharing |
| Acquire semaphore in main process before `pool.submit()` | Tried to rate-limit submission from the main thread | Blocked the main thread and prevented all remaining tasks from being queued | Acquire inside the worker process — lets the pool queue all tasks, then throttles at execution |
| Watch terminal for OOM test isolation | Ran pytest without ulimit and observed last printed test ID | OOM-killer reaped the parent shell too; terminal disappeared with no output | Always set `ulimit -v` before pytest so the kernel kills only pytest, not the shell |
| Trust tee logs after OOM | Piped pytest output to `tee /tmp/diag.log` and read the file post-mortem | Under WSL2 the buffered file ended up zero bytes — writer was reaped before flush | tee is not OOM-safe; ulimit converts SIGKILL to MemoryError which unwinds normally |
| Rely on `--tb=long` to catch OOM | Expected pytest's long traceback to show the leak | Kernel SIGKILL is uncatchable; Python never unwinds | Convert SIGKILL to MemoryError via `ulimit -v` before any traceback can help |
| Enum import inside optional-dependency try block | Placed `from nats.js.api import DeliverPolicy` inside `try:` after `import nats` | Mock did not define `nats.js.api` submodule → `ImportError` → guard's `return` fired → `js.subscribe()` never called | Any `from <optional-package>.*` inside a `try/except ImportError` guard silently triggers early return if the submodule is absent or not mocked |
| Enum import at module top level | Placed `from nats.js.api import DeliverPolicy` at module level outside the guard | `ImportError` at import time in environments without nats-py, breaking the optional-dependency contract | Optional dependency imports must always be deferred inside the guard block, never at module level |
| `allow_reconnect=True` with `max_reconnect_attempts=-1` | Let nats-py handle reconnection internally with infinite retries | `connect()` never returns when NATS is down — hangs in internal retry loop with no status output | Use `allow_reconnect=False` and manage retries externally for control over status messages |
| Non-async nats-py callbacks | Used `def disconnected_cb():` (regular function) | nats-py validates with `asyncio.iscoroutinefunction()` and raises "callbacks must be coroutine functions" | All nats-py lifecycle callbacks must be `async def` coroutines |
| `connect_timeout` alone to cap nats connect | Set `connect_timeout=3` expecting it to limit overall connect duration | `connect_timeout` only applies to the TCP socket; internal reconnection logic adds additional time | Wrap `connect()` with `asyncio.wait_for()` for a hard overall timeout guarantee |
| Pattern matching too narrow for transient errors | Matched `"network unreachable"` | Actual error was `"Network is unreachable"` (with "is"); case-sensitive miss | Use `stderr.lower()` and include common phrase variations in the pattern list |
| Debug hangs with piped output | Used `command 2>&1 \| tail -30` to filter output | Pipe buffering made the process appear hung when it was running fine | Use `PYTHONUNBUFFERED=1` or redirect to a file when debugging hangs |

## Results & Parameters

### Quick Reference — All Copy-Paste Patterns

```python
# Subprocess (non-interactive)
subprocess.run(cmd, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)

# Terminal restoration (main thread only)
def restore_terminal():
    if threading.current_thread() is not threading.main_thread():
        return
    if sys.stdin.isatty():
        subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)

# Global semaphore (cross-process)
from multiprocessing import Manager
manager = Manager()
global_semaphore = manager.Semaphore(N)   # use Manager(), not multiprocessing.Semaphore()

# ulimit before pytest
ulimit -v 4194304   # 4 GiB
ulimit -t 180       # 180 CPU-seconds

# nats-py connection config
{"allow_reconnect": False, "connect_timeout": 3}
logging.getLogger("nats").setLevel(logging.CRITICAL)

# Retry (transient subprocess errors)
max_retries, base_delay = 3, 1.0
delay = base_delay * (2 ** attempt)   # 1 s, 2 s, 4 s
```

### Transient Error Patterns (for subprocess retry)

```python
TRANSIENT_PATTERNS = [
    "connection reset", "connection refused",
    "network unreachable", "network is unreachable",
    "temporary failure", "could not resolve host",
    "curl 56", "timed out", "early eof", "recv failure",
]
```

### ulimit Recommendations

| Setting | Value | Purpose |
| --------- | ------- | --------- |
| `ulimit -v` | `4194304` (4 GiB) | Virtual memory cap; adjust to ~50% of host RAM |
| `ulimit -t` | `180` | CPU-seconds; kills runaway tight loops |

### nats-py Configuration

| Parameter | Value | Reason |
| ----------- | ------- | --------- |
| `allow_reconnect` | `False` | Fail fast; manage retries externally |
| `connect_timeout` | `3` | TCP socket timeout (seconds) |
| `asyncio.wait_for` timeout | `5` | Hard ceiling on overall connect duration |
| Retry interval | `5` | Seconds between reconnection attempts |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #151 — global semaphore + AttributeError + FileNotFoundError fixes | 2026-01-08 |
| ProjectScylla | Batch subprocess / signal / stty hang fixes | 2026-03-20 |
| ProjectScylla | Mock expensive simulations in conftest.py | 2026-02-23 |
| ProjectScylla | PR #1784 — nats optional import guard fix (issue #1654) | 2026-04-12 |
| Odysseus | odysseus-console.py NATS event viewer resilience | 2026-04-05 |
| ProjectHephaestus | PR #412 — ulimit bisection pinpointed OOM test | 2026-05-15 |
| ProjectScylla | PR #146 — git clone transient retry logic | 2026-01-04 |
