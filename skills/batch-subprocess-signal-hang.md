---
name: batch-subprocess-signal-hang
description: "Debugging batch mode hangs caused by subprocess stdin blocking, signal group isolation, and worker-thread terminal calls. Use when: (1) batch/parallel workers hang on exit, (2) Ctrl+C stops working after os.setpgrp(), (3) subprocess.run blocks waiting for stdin."
category: debugging
date: 2026-03-20
version: "1.0.0"
user-invocable: false
---

# Batch Subprocess & Signal Hang Debugging

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Python batch runners hang indefinitely or ignore Ctrl+C |
| **Root Causes** | 3 distinct bugs: stdin blocking, process group isolation, worker-thread stty |
| **Languages** | Python 3.10+ |
| **Key Tools** | subprocess, threading, signal, os |

## When to Use

- ThreadPoolExecutor workers hang on exit even though work completed
- `Ctrl+C` has no effect (SIGINT not delivered)
- `subprocess.run()` blocks for seconds waiting for input
- `stty sane` called from non-main thread blocks or corrupts terminal
- Process hangs after calling `os.setpgrp()` or `os.setsid()`

## Verified Workflow

### Bug 1: subprocess.run() blocks waiting for stdin

**Symptom**: A subprocess call like `subprocess.run(["claude", "--print", "ping"])` blocks for 3-30 seconds.

**Root Cause**: The CLI tool waits for stdin. Without `stdin=subprocess.DEVNULL`, it inherits the parent's stdin and blocks.

**Fix**:
```python
# BEFORE (blocks)
result = subprocess.run(["claude", "--print", "ping"], capture_output=True, text=True, timeout=30)

# AFTER (returns immediately)
result = subprocess.run(["claude", "--print", "ping"], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
```

**Rule**: Always pass `stdin=subprocess.DEVNULL` to non-interactive subprocess calls, especially in batch/background contexts.

### Bug 2: os.setpgrp() breaks Ctrl+C

**Symptom**: Pressing Ctrl+C has no effect. The process ignores SIGINT entirely.

**Root Cause**: `os.setpgrp()` moves the process into a new process group. The terminal sends SIGINT to the **foreground process group** only. Since the process is no longer in it, SIGINT never arrives.

**Fix**: Remove `os.setpgrp()`. If you need to kill child processes on exit, use `signal.signal(SIGINT, handler)` to propagate signals manually, or use `os.killpg()` only as a second-signal force-kill handler.

**Rule**: Never call `os.setpgrp()` or `os.setsid()` in interactive CLI tools unless you also set up explicit signal forwarding. The process will become invisible to terminal job control.

### Bug 3: stty from worker threads hangs

**Symptom**: ThreadPoolExecutor workers hang on cleanup. The program never exits after all work completes.

**Root Cause**: A `terminal_guard()` context manager calls `subprocess.run(["stty", "sane"], stdin=sys.stdin)` in its `__finally__` block. When called from a worker thread (not the main thread), the `stty` process blocks trying to access the controlling terminal.

**Fix**: Guard terminal restoration with a main-thread check:
```python
import threading

def restore_terminal() -> None:
    with contextlib.suppress(Exception):
        if threading.current_thread() is not threading.main_thread():
            return  # Only main thread owns the controlling terminal
        if sys.stdin.isatty():
            subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
```

**Rule**: Never call `stty` or other terminal-manipulation commands from worker threads. The controlling terminal is owned by the main thread only.

### Diagnostic Checklist

1. **Hang on exit?** → Check for non-daemon threads, stty calls from workers, ThreadPoolExecutor not shutting down
2. **Ctrl+C ignored?** → Check for `os.setpgrp()`, `os.setsid()`, or signal handlers that swallow SIGINT
3. **Subprocess slow?** → Check for missing `stdin=subprocess.DEVNULL`
4. **Per-iteration slowness?** → Check for redundant subprocess pre-flight checks that should run once

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Move rate limit check from per-tier to once-per-experiment only | Initial fix removed per-tier check but didn't add stdin=DEVNULL | The subprocess still blocked for 3s waiting for stdin even when called once | Always add stdin=subprocess.DEVNULL for non-interactive subprocesses |
| Remove SIGTSTP handler only, keep os.setpgrp() | Thought SIGTSTP kill handler was the only signal problem | os.setpgrp() itself was the root cause — it isolated the process from terminal SIGINT delivery | os.setpgrp() affects ALL signals from terminal, not just the ones you handle |
| Add noqa comment to unused import instead of removing it | Tried to keep rate_limit imports in tier_action_builder.py with noqa:F401 | Unnecessary complexity — the import should just be removed when the function call is removed | Clean up imports immediately when removing call sites |
| Debug with piped output (grep/tail) | Used `command 2>&1 \| tail -30` and `\| grep` to filter output | Pipe buffering made it appear the process was hung when it was actually running fine | Always use PYTHONUNBUFFERED=1 or redirect to file when debugging hangs |

## Results & Parameters

### Environment
- Python 3.10+ with ThreadPoolExecutor for parallel batch execution
- CLI subprocess calls (`claude --print ping`) for rate limit pre-flight checks
- `stty sane` for terminal restoration after agent runs

### Configuration Pattern
```python
# Safe subprocess call (non-interactive)
subprocess.run(
    ["command", "--flag", "arg"],
    capture_output=True,
    text=True,
    timeout=30,
    stdin=subprocess.DEVNULL,  # ALWAYS for non-interactive
)

# Safe terminal restoration (main thread only)
def restore_terminal():
    if threading.current_thread() is not threading.main_thread():
        return
    if sys.stdin.isatty():
        subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)

# Signal handling (no process group isolation)
# Do NOT call os.setpgrp() in interactive CLI tools
signal.signal(signal.SIGINT, graceful_handler)   # First Ctrl+C
signal.signal(signal.SIGTERM, graceful_handler)   # systemd/docker stop
```

### Files Modified (ProjectScylla)
- `scylla/utils/terminal.py` — main-thread guard for stty
- `scylla/e2e/rate_limit.py` — stdin=subprocess.DEVNULL
- `scylla/e2e/runner.py` — single pre-flight rate limit check
- `scylla/e2e/tier_action_builder.py` — removed per-tier rate limit check
- `scripts/manage_experiment.py` — removed os.setpgrp() and dead signal handlers
