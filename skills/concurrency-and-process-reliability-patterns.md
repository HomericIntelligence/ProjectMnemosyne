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
  clone fails with transient network errors, (11) a multi-agent fan-out (e.g. a Myrmidon swarm)
  OOM-hangs a WSL host because concurrent Claude agent sessions are unthrottled, (12) a
  ThreadPoolExecutor max_workers cap fails to limit concurrent agent sessions and you need an
  asyncio.Semaphore agent cap, (13) you need a ulimit -v wrapper around pixi/cmake/podman so an
  over-budget process dies as a recoverable MemoryError instead of an uncatchable OOM-SIGKILL,
  (14) a worker pool leaks a runaway child subprocess after shutdown because
  ThreadPoolExecutor.shutdown(cancel_futures=True) does NOT kill an already-running subprocess and
  you need a process-group registry + os.killpg to reap it."
category: debugging
date: 2026-07-12
version: "1.2.0"
user-invocable: false
verification: verified-local
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
  - agent
  - fan-out
  - wsl
  - host-exhaustion
  - swap
  - threadpoolexecutor
  - killpg
  - start-new-session
  - process-group-registry
  - subprocess-leak
  - worker-pool-shutdown
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
- a multi-agent fan-out (Myrmidon swarm, `claude-myrmidon-multi.py`) hangs the whole WSL VM —
  syslog shows `Free swap = 0kB`, high `pgmajfault`, and many "Time jumped backwards" lines
- a ThreadPoolExecutor `max_workers=N` does NOT limit the number of concurrent Claude **agent**
  sessions and you need a real per-agent `asyncio.Semaphore` cap
- per-agent `cmake --build -j$(nproc)` × N agents oversubscribes all cores N times
- you want pixi/cmake/podman to die as a recoverable `MemoryError` (via `ulimit -v`) instead of
  an uncatchable OOM-SIGKILL that hangs the host
- a worker pool's `shutdown()` returns but a child subprocess (e.g. a `claude` CLI reviewer) keeps
  running for minutes afterward and holds the interpreter open — because
  `ThreadPoolExecutor.shutdown(wait=False, cancel_futures=True)` only cancels UN-started futures and
  never signals a subprocess already blocked inside `subprocess.run` on a non-daemon worker thread

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

### Pattern 10 — Multi-Agent Host Exhaustion on WSL

**Symptom**: A multi-repo agent fan-out (e.g. a 16-repo Myrmidon swarm via
`e2e/claude-myrmidon-multi.py`) hangs the **entire WSL VM**, not just one process. `journalctl`/syslog
shows `Free swap = 0kB`, a high `pgmajfault` count (e.g. `pgmajfault: 13255`), dozens of
`Time jumped backwards` lines (scheduler starvation), and journal corruption. The host only recovers
after the OOM-killer reaps the agent processes.

**Root Cause**: On a WSL2 host with no `[wsl2] memory=` cap in `.wslconfig`, the VM gets ~50% of host
RAM (on a 16 GB / 8-core box → ~8 GB usable + 16 GB swap). A fan-out dispatches ~16 **concurrent**
Claude agent sessions with no spawn throttle. Each agent runs heavy work — `pixi install`/`pixi lock`
(a conda+pypi SAT solve, ~0.5–1 GB each) plus a C++ build (`cmake --build -j$(nproc)` → all 8 cores,
1.5–3 GB each). Peak demand (~18–40 GB) far exceeds RAM+swap → swap hits 0 → the scheduler starves →
the whole VM locks up.

**Critical misconception**: A `ThreadPoolExecutor(max_workers=N)` inside ONE Python process does
**not** cap the number of concurrent agent **sessions** — each agent is its own process tree. Setting
hephaestus's `max_workers=3` did nothing to stop 16 agents from running at once. `max_workers` is a
red herring for host-exhaustion.

**Fix** — four independent controls, all needed together:

1. **Cap concurrent agents with a real `asyncio.Semaphore(N)`** around the heavy per-agent invocation.
   Wrap the blocking call in `asyncio.to_thread` *under* the semaphore — otherwise a blocking sync call
   serializes the loop and the semaphore becomes a no-op. Lazy-create the semaphore so it binds the
   *running* loop (constructing at import time has no loop yet).

   ```python
   import asyncio

   _agent_sem: asyncio.Semaphore | None = None
   MAX_CONCURRENT_AGENTS = 3   # ~one heavy ~3 GB op per slot + headroom on a 16 GB/8-core box

   def _get_agent_sem() -> asyncio.Semaphore:
       global _agent_sem
       if _agent_sem is None:          # lazy: bind the running loop, not import-time (no loop)
           _agent_sem = asyncio.Semaphore(MAX_CONCURRENT_AGENTS)
       return _agent_sem

   async def bounded_invoke_claude(*args, **kwargs):
       async with _get_agent_sem():
           # to_thread matters: a blocking sync call here would serialize the loop
           # and the semaphore would never actually throttle anything.
           return await asyncio.to_thread(invoke_claude, *args, **kwargs)
   ```

   Verified: 10 agents fired, peak in-flight capped at exactly 3.

2. **Cap build parallelism per agent.** `-j$(nproc)` × N agents = N×cores oversubscription. Use `-j2`
   or export `CMAKE_BUILD_PARALLEL_LEVEL=2` so N agents stay within the core budget.

3. **Memory-bound each heavy op with `ulimit -v`** via a wrapper script, generalizing the pytest
   Pattern 5 to pixi/cmake/podman and to the multi-agent case. The subshell makes the cap local to
   that one process; an over-budget process then dies as a recoverable `MemoryError` rather than an
   uncatchable OOM-SIGKILL that hangs the VM (verified: the parent shell survives).

   ```bash
   #!/usr/bin/env bash
   # run-bounded.sh — cap virtual memory for one heavy command
   ( ulimit -v 5242880; exec "$@" )   # 5 GiB (5*1024*1024 KiB); subshell keeps the cap local
   # usage: ./run-bounded.sh pixi install
   #        ./run-bounded.sh cmake --build build -j2
   ```

4. **Operational rule**: on this host keep **≤3 concurrent heavy (pixi/cmake/podman) agents**. Prefer
   a concurrency-capped Workflow/wave over fire-and-forget parallel agent spawns, and check `free -h`
   *before* launching a swarm.

### Pattern 11 — ThreadPoolExecutor.shutdown(cancel_futures=True) Does NOT Kill Running Subprocesses

**Symptom**: A worker pool's `shutdown()` returns, but a child subprocess (e.g. a `claude` CLI
reviewer) keeps running for many minutes afterward — one leaked ~19 minutes past shutdown — holding
the Python interpreter open so the whole program cannot exit.

**Root Cause**: `concurrent.futures.ThreadPoolExecutor.shutdown(wait=False, cancel_futures=True)`
cancels only **un-started** futures. A job already blocked inside `subprocess.run(...)` /
`Popen.communicate()` on a non-daemon worker thread keeps running to completion or timeout. Because
executor workers are **non-daemon** and `concurrent.futures` registers an `atexit` join, the
interpreter blocks on exit until the runaway child finishes. `cancel_futures` ≠ terminate running
work — there is no built-in way to reap an in-flight subprocess through the executor API.

**Fix** — spawn each child as its own process-group leader, track live groups in a thread-safe
registry, and `os.killpg` them on teardown. Four independent ingredients, all needed:

1. **Spawn each child in its own session** so it leads its own process group. Replace
   `subprocess.run(cmd, ...)` with `Popen(cmd, ..., start_new_session=True)` + `communicate(...)`.
   With `start_new_session=True`, `pid == pgid`, so signaling the group hits the whole tree (the
   child AND its grandchildren like `gh`/`git`).

2. **Track the live process group for the duration of the blocking call** via a thread-safe registry
   — a module-level `set[int]` guarded by a `threading.Lock`, populated by a context manager that
   registers `os.getpgid(pid)` on enter and discards it on exit. A normally-finishing child never
   leaves a stale pgid behind.

3. **On teardown, `os.killpg(pgid, SIGTERM)` every tracked group**, then clear the set. This frees
   the wedged worker thread promptly so the interpreter can exit.

4. **Gate everything on `hasattr(os, "killpg") and hasattr(os, "getpgid")`** so Windows / no-killpg
   platforms no-op and fall back to prior behavior.

**Preserve the `subprocess.run(check=True, timeout=...)` exception contract** in the Popen wrapper:
raise `subprocess.CalledProcessError(returncode, cmd, output, stderr)` on nonzero exit; re-raise
`subprocess.TimeoutExpired` on timeout (kill + reap the child first to avoid a zombie).

```python
import os
import signal
import subprocess
import threading
from contextlib import contextmanager

_HAS_PGID = hasattr(os, "killpg") and hasattr(os, "getpgid")


class ProcessGroupRegistry:
    """Thread-safe set of live process-group ids so teardown can killpg them."""

    def __init__(self) -> None:
        self._pgids: set[int] = set()
        self._lock = threading.Lock()

    @contextmanager
    def track_process_group(self, pid: int):
        """Register the child's pgid for the life of a blocking call; discard on exit."""
        pgid = None
        if _HAS_PGID:
            try:
                pgid = os.getpgid(pid)
            except ProcessLookupError:
                pgid = None
            if pgid is not None:
                with self._lock:
                    self._pgids.add(pgid)
        try:
            yield
        finally:
            if pgid is not None:
                with self._lock:
                    self._pgids.discard(pgid)

    def terminate_all(self) -> None:
        """SIGTERM every tracked process group, then clear. Call from shutdown()."""
        if not _HAS_PGID:
            return
        with self._lock:
            pgids = list(self._pgids)
            self._pgids.clear()
        for pgid in pgids:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass


def run_tracked(cmd, registry, *, input=None, timeout=None, check=True):
    """Popen(start_new_session=True) wrapper preserving subprocess.run's exception contract."""
    kwargs = {"start_new_session": True} if _HAS_PGID else {}
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, **kwargs,
    )
    with registry.track_process_group(proc.pid):
        try:
            out, err = proc.communicate(input=input, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # reap — avoid a zombie
            raise
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, out, err)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


# In WorkerPool.shutdown(): reap in-flight children BEFORE joining the executor.
#   registry.terminate_all()
#   executor.shutdown(wait=False, cancel_futures=True)
```

**Critical test-design lesson** (itself a key learning): a test using an inline/fake worker pool
CANNOT prove the leak is fixed — asserting `shutdown_calls == 1` proves the CALL happens, not that a
subprocess dies. The regression test MUST spawn a **real OS subprocess** (swap the target binary for
`sys.executable -c "import time; time.sleep(60)"` through the real spawn path), call the **real**
`shutdown()`, and assert completion arrives well under the sleep (e.g. `< 15 s`). Verify the test
**FAILS** (queue-timeout / hang) when the `terminate_all()` call is removed — that proves it actually
exercises the kill path.

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
| Rely on ThreadPoolExecutor `max_workers` to cap agents | Set hephaestus `max_workers=3` expecting it to limit concurrent agent sessions in a 16-repo fan-out | `max_workers` bounds threads inside ONE process; each Claude agent is its own process tree, so 16 agents still ran at once and exhausted the WSL host | A ThreadPoolExecutor `max_workers=N` is a red herring for host-exhaustion — it does NOT cap concurrent AGENT sessions; throttle the per-agent invocation itself |
| `asyncio.Semaphore` around a blocking sync call | Wrapped `invoke_claude(...)` directly in `async with sem:` without `asyncio.to_thread` | The blocking sync call serialized the event loop; only one ran at a time so the semaphore never gated anything (no-op) | Put the heavy call in `asyncio.to_thread(...)` *inside* the `async with sem:` so the slots are real concurrency, not loop-serialized |
| Construct the Semaphore at import time | `_agent_sem = asyncio.Semaphore(3)` at module top level | No running event loop exists at import; the semaphore binds the wrong/absent loop and fails or silently mis-throttles | Lazy-create the Semaphore on first use so it binds the running loop |
| Leave `-j$(nproc)` per agent | Each agent built with `cmake --build -j$(nproc)` | N agents × all cores = N×core oversubscription → scheduler starvation, "Time jumped backwards", VM lockup | Cap build parallelism per agent (`-j2` / `CMAKE_BUILD_PARALLEL_LEVEL=2`) so N agents fit the core budget |
| Let pixi/cmake run uncapped and rely on the OOM-killer | Ran heavy ops with no `ulimit -v`, assuming the OOM-killer would reap just the offender | The uncatchable OOM-SIGKILL fired only after swap hit 0 kB and the whole WSL VM had already hung; recovery required the kernel to reap agents | Wrap each heavy op in `( ulimit -v <N>GiB; exec "$@" )` so it dies as a recoverable `MemoryError` first; the shell/host survive (generalizes pytest Pattern 5 to pixi/cmake/podman) |
| `executor.shutdown(wait=False, cancel_futures=True)` alone to stop a runaway child | Called shutdown expecting `cancel_futures=True` to terminate an in-flight `subprocess.run` on a worker | It only cancels UN-started futures; a subprocess already blocked in `communicate()` is never signaled and keeps the non-daemon worker (and the `atexit` join) alive — a `claude` child ran ~19 min past shutdown | `cancel_futures` ≠ terminate running work; to reap an in-flight subprocess you must signal its process group yourself (`start_new_session=True` + registry + `os.killpg`) |
| Assert `pool.shutdown()` was called via a fake-pool counter | Regression test used an inline fake worker pool with a `shutdown_calls` counter and asserted `== 1` | Proved the CALL, not the EFFECT; the fake ran jobs inline with no real thread/subprocess to leak, so it stayed green even when the kill path was broken | A leak-fix test must spawn a REAL OS subprocess (`sys.executable -c "time.sleep(60)"`) through the real spawn path and assert completion `< 15 s`; confirm it FAILS/hangs when `terminate_all()` is removed |

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

# Multi-agent cap (NOT ThreadPoolExecutor max_workers — that does not gate agent sessions)
_agent_sem = None                                    # lazy: bind the running loop
def _get_agent_sem():
    global _agent_sem
    if _agent_sem is None:
        _agent_sem = asyncio.Semaphore(3)            # <=3 heavy agents on a 16 GB/8-core box
    return _agent_sem
async def bounded_invoke_claude(*a, **k):
    async with _get_agent_sem():
        return await asyncio.to_thread(invoke_claude, *a, **k)   # to_thread -> real concurrency

# Reap in-flight subprocesses on worker-pool shutdown (cancel_futures does NOT do this):
# 1) spawn each child as its own pgroup leader; 2) track pgid for the blocking call;
# 3) killpg all tracked groups in shutdown() BEFORE joining the executor.
_HAS_PGID = hasattr(os, "killpg") and hasattr(os, "getpgid")
proc = subprocess.Popen(cmd, start_new_session=True, ...)   # pid == pgid
with registry.track_process_group(proc.pid):               # set[int] + threading.Lock
    proc.communicate(input=..., timeout=...)
# WorkerPool.shutdown():
registry.terminate_all()                                    # os.killpg(pgid, SIGTERM) for each
executor.shutdown(wait=False, cancel_futures=True)
```

```bash
# Cap per-agent build parallelism (N agents * nproc oversubscribes cores)
export CMAKE_BUILD_PARALLEL_LEVEL=2        # or: cmake --build build -j2

# run-bounded.sh — memory-bound any heavy op so it dies as MemoryError, not OOM-SIGKILL
( ulimit -v 5242880; exec "$@" )           # 5 GiB; usage: ./run-bounded.sh pixi install
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
| Odysseus | `e2e/claude-myrmidon-multi.py` 16-repo fan-out hung WSL host `hermes` (16 GB/8-core, `Free swap = 0kB`); fixed with `asyncio.Semaphore(3)` agent cap + `-j2` builds + `ulimit -v` wrapper — verified 10 fired, peak in-flight capped at 3 | verified-local 2026-06-29 |
| ProjectHephaestus | PR #2061 — a `claude` CLI reviewer child leaked ~19 min past `WorkerPool.shutdown()` because `ThreadPoolExecutor.shutdown(cancel_futures=True)` never reaps an in-flight subprocess; fixed with `start_new_session=True` + thread-safe pgid registry + `os.killpg` in `terminate_all()`. Regression test spawns a REAL `sys.executable -c "time.sleep(60)"` child and asserts completion `< 15 s` (fails/hangs if `terminate_all()` removed). | verified-ci 2026-07-12 — GO strict review, all 137 affected tests pass |
