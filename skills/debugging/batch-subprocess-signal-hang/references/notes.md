# Session Notes: Batch Subprocess & Signal Hang Debugging

## Date: 2026-03-20

## Context
ProjectScylla E2E experiment runner had three interacting bugs that caused:
1. Process hangs in batch mode (ThreadPoolExecutor workers never exit)
2. Ctrl+C completely non-functional
3. ~15s delay per tier due to redundant subprocess pre-flight checks

## Timeline

### Phase 1: Initial Plan Implementation
- Removed per-tier `check_api_rate_limit_status()` from `tier_action_builder.py`
- Added single pre-flight check in `runner.py:_action_exp_repo_cloned()`
- Added `set_log_context()` calls at tier and subtest entry points
- Removed SIGTSTP `_kill_group` handler from `manage_experiment.py`
- Updated stale transition descriptions in `tier_state_machine.py`

### Phase 2: Discovered Batch Mode Hang
- Running with `--threads 1` still caused process to hang
- Sub-agent exploration traced the call chain:
  - `cmd_run()` → `_run_batch()` → `ThreadPoolExecutor` → `run_one_test()` → `terminal_guard()` → `restore_terminal()` → `stty sane`
- Root cause: `restore_terminal()` calls `subprocess.run(["stty", "sane"], stdin=sys.stdin)` from worker threads
- Fix: Added `threading.current_thread() is not threading.main_thread()` guard

### Phase 3: Discovered Ctrl+C Not Working
- User reported Ctrl+C still hangs (many ^C characters with no effect)
- Root cause: `os.setpgrp()` at line 873 of `manage_experiment.py` moved process to new process group
- Terminal sends SIGINT to foreground process group — process was no longer in it
- Fix: Removed `os.setpgrp()` entirely, along with the now-dead `_kill_group` handler and unused imports

### Phase 4: Also Fixed subprocess stdin blocking
- `check_api_rate_limit_status()` spawns `claude --print ping` without `stdin=subprocess.DEVNULL`
- Claude CLI waits for stdin, causing 3-30s delay
- Fix: Added `stdin=subprocess.DEVNULL` to the subprocess.run() call

## Key Debugging Insights

### Pipe buffering masks real behavior
When debugging with `command | tail -30` or `command | grep pattern`, pipe buffering causes output to appear stuck even when the process is running fine. Use `PYTHONUNBUFFERED=1` or redirect to a file instead.

### os.setpgrp() is a footgun in interactive tools
It was originally added to enable `os.killpg()` for killing child processes. But it breaks ALL terminal signal delivery (SIGINT, SIGTSTP, SIGQUIT). The correct approach is to use signal handlers for graceful shutdown and let the OS handle process group management.

### Three bugs interacted to create one symptom
The user saw "process hangs" but the root causes were:
1. stty blocking from worker thread (hang on exit)
2. os.setpgrp() preventing SIGINT (can't interrupt)
3. Per-tier subprocess check adding latency (appears slow)
Each individually would cause problems; together they made the tool unusable.
