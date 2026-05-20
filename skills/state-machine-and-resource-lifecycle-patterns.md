---
name: state-machine-and-resource-lifecycle-patterns
description: "Use when: (1) a resumable state machine's advance() leaves a subtest\
  \ stuck in the prior state after a sentinel exception fires before the state update;\
  \ (2) Ctrl+C/SIGINT must leave long-running agent runs resumable instead of FAILED\
  \ across a 4-level SM hierarchy; (3) global mutable semaphores leak or hang on\
  \ shutdown and need replacing with a dependency-injected ResourceManager; (4) temp\
  \ credential dirs accumulate in home after Docker runs due to silent rmtree failures;\
  \ (5) ProcessPoolExecutor hangs on Python 3.14t free-threaded and workers only\
  \ run external subprocesses."
category: architecture
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: state-machine-and-resource-lifecycle-patterns.history
tags:
  - state-machine
  - resumable
  - interrupt-handling
  - sigint
  - resource-manager
  - semaphore
  - context-manager
  - credentials
  - multiprocessing
  - threading
  - python
---
# State Machine and Resource Lifecycle Patterns

## Overview

| Field | Value |
| ------- | ------- |
| Theme | Design resumable state machines, interrupt-safe handlers, and dependency-injected resource managers for long-running agents |
| Absorbed | resumable-state-machine-until-halt, state-machine-interrupt-handling, resource-manager-pattern, credential-mount-context-manager, multiprocess-to-multithread-conversion |
| Outcome | All patterns verified in production (ProjectScylla PRs #1010, #1107, #1109) |

## When to Use

- A state machine's `advance()` updates checkpoint state **after** executing the action, so a sentinel exception leaves the subtest stuck in the prior state on resume
- `--until` semantics must stop cleanly and leave state resumable (not `FAILED`)
- Ctrl+C sends SIGINT to the OS process group; `subprocess.run()` returns **normally** (no Python exception), but the run must not advance to a broken `AGENT_COMPLETE` state
- A multi-level SM hierarchy (run→subtest→tier→experiment) must propagate an interrupt sentinel through all `except Exception` blocks without any level marking `FAILED`
- Module-level `threading.Semaphore` globals leak on crash/shutdown or hang when `ShutdownInterruptedError` bypasses `finally` blocks
- Temp credential/config dirs accumulate in home after container runs because `rmtree()` races Docker mount release on WSL2
- `ProcessPoolExecutor` hangs silently on Python 3.14t (free-threaded) because `forkserver` cannot serialize `Manager().Semaphore()` proxies

## Verified Workflow

### Pattern 1 — Sentinel Exception + State Transition (`--until` Semantics)

#### Quick Reference

```python
# In state-machine module (NOT executor — avoids circular import)
class UntilHaltError(Exception):
    """Sentinel: stop-but-don't-fail. advance() catches, transitions, re-raises."""

# In advance():
halt_error: UntilHaltError | None = None
try:
    action()
except UntilHaltError as _e:
    halt_error = _e          # Catch but still transition state below

# State update — runs even when UntilHaltError was raised
self.checkpoint.set_subtest_state(tier_id, subtest_id, transition.to_state.value)
save_checkpoint(...)

if halt_error is not None:
    raise halt_error         # Re-raise so advance_to_completion stops the loop

# In advance_to_completion():
except UntilHaltError as e:
    logger.info(f"[{tier_id}/{subtest_id}] {e}")  # NOT FAILED — intentional stop
```

#### Key Invariants

1. **Sentinel must transition state before re-raising** — otherwise the machine is stuck in the prior state and re-executes on resume.
2. **Ephemeral CLI fields excluded from config hash** — `until_run_state`, `until_tier_state`, `until_experiment_state`, `max_subtests` must survive config reload from checkpoint.
3. **Additive tier merge** — move `tiers_to_run` merge outside `if experiment_state in ("failed", "interrupted")` so it fires for all checkpoint states.
4. **Skip-already-at logic** — in the run loop, check if a run is already at `until_run_state` before executing it.

#### Restore Ephemeral CLI Args After Config Reload

```python
def _initialize_or_resume_experiment(self):
    _cli_tiers = list(self.config.tiers_to_run)
    _cli_ephemeral = {
        "until_run_state": self.config.until_run_state,
        "until_tier_state": self.config.until_tier_state,
        "until_experiment_state": self.config.until_experiment_state,
        "max_subtests": self.config.max_subtests,
    }
    _load_checkpoint_and_config(...)   # overwrites self.config
    non_none_ephemeral = {k: v for k, v in _cli_ephemeral.items() if v is not None}
    if non_none_ephemeral:
        self.config = self.config.model_copy(update=non_none_ephemeral)
```

#### Exclude `tiers_to_run` from Config Hash

```python
# checkpoint.py — compute_config_hash()
config_dict = self.config.model_dump()
config_dict.pop("tiers_to_run", None)  # Tiers are additive across resumes
```

### Pattern 2 — SIGINT / Ctrl+C Interrupt Handling Across All SM Levels

#### Quick Reference

```python
# runner.py — owns the shutdown flag
class ShutdownInterruptedError(Exception):
    """Raised after subprocess.run() returns with SIGINT exit code.
    Caught BEFORE except Exception at every SM level — run stays at last good state."""

_shutdown_requested = False

def is_shutdown_requested() -> bool:
    return _shutdown_requested
```

#### Step-by-Step: Four SM Levels

**Run level** — catch before `except Exception`, leave state unchanged:

```python
# StateMachine.advance_to_completion()
except ShutdownInterruptedError:
    current = self.get_state(tier_id, subtest_id, run_num)
    logger.warning(f"Shutdown interrupted at {current.value} — run left resumable")
    raise  # propagate
except Exception as e:
    self.checkpoint.set_run_state(..., RunState.FAILED.value)
    save_checkpoint(...)
    raise
```

**Subtest level** — re-raise without setting FAILED:

```python
except ShutdownInterruptedError:
    current = self.get_state(tier_id, subtest_id)
    logger.warning(f"[{tier_id}/{subtest_id}] Shutdown interrupted — resumable")
    raise
except Exception:
    self.checkpoint.set_subtest_state(..., SubtestState.FAILED.value)
    save_checkpoint(...)
    raise
```

**Tier level** — reset to `CONFIG_LOADED` (not `SUBTESTS_RUNNING`):

```python
except Exception as e:
    from <package>.runner import ShutdownInterruptedError
    if isinstance(e, ShutdownInterruptedError):
        self.checkpoint.set_tier_state(tier_id, TierState.CONFIG_LOADED.value)
        save_checkpoint(...)
        raise
    self.checkpoint.set_tier_state(tier_id, TierState.FAILED.value)
    save_checkpoint(...)
    raise
```

**Experiment level** — mark `INTERRUPTED` (resumable), not `FAILED`:

```python
if isinstance(e, (RateLimitError, ShutdownInterruptedError)):
    self.checkpoint.experiment_state = ExperimentState.INTERRUPTED.value
else:
    self.checkpoint.experiment_state = ExperimentState.FAILED.value
save_checkpoint(...)
raise
```

#### Check Shutdown Flag After `subprocess.run()`

```python
result = subprocess.run(["bash", str(replay_script.resolve())], ...)
# subprocess.run() returns NORMALLY even when killed by SIGINT
from <package>.runner import ShutdownInterruptedError, is_shutdown_requested
if is_shutdown_requested():
    raise ShutdownInterruptedError(f"Shutdown during agent execution for run {ctx.run_number}")
```

#### Re-raise From `ProcessPoolExecutor` Safe Wrapper

```python
def _run_subtest_in_process_safe(...) -> SubTestResult:
    try:
        return _run_subtest_in_process(...)
    except Exception as e:
        from <package>.runner import ShutdownInterruptedError
        if isinstance(e, ShutdownInterruptedError):
            raise  # Do NOT convert to SubTestResult
        return SubTestResult(selection_reason=f"WorkerError: {type(e).__name__}: {e}", ...)
```

### Pattern 3 — Dependency-Injected ResourceManager

#### Quick Reference

```python
# resource_manager.py
class ResourceManager:
    def __init__(self, max_workspaces, max_agents):
        self._workspace_sem = threading.Semaphore(max_workspaces)
        self._agent_sem = threading.Semaphore(max_agents)
        self._pipeline_lock = threading.Lock()

    @contextlib.contextmanager
    def workspace_slot(self, timeout=300):
        if not self._workspace_sem.acquire(timeout=timeout):
            raise TimeoutError("No workspace slots available")
        try:
            yield
        finally:
            self._workspace_sem.release()  # GUARANTEED on any exception

    @contextlib.contextmanager
    def agent_slot(self, timeout=600):
        if not self._agent_sem.acquire(timeout=timeout):
            raise TimeoutError("No agent slots available")
        try:
            yield
        finally:
            self._agent_sem.release()
```

**Create once, pass to all** — do not use globals:

```python
# Entry point (runner.py or _run_batch())
resource_manager = ResourceManager(
    max_workspaces=cpu_count * 2,
    max_agents=min(threads, cpu_count),
)
# Wrap entire run execution with workspace slot
ws_ctx = resource_manager.workspace_slot() if resource_manager else contextlib.nullcontext()
with ws_ctx:
    sm.advance_to_completion(...)
```

**Checkpoint write lock** — prevents concurrent write data loss:

```python
# checkpoint.py
_checkpoint_write_lock = threading.Lock()

def save_checkpoint(checkpoint, path):
    with _checkpoint_write_lock:
        # serialize + atomic write (temp file + rename)
```

### Pattern 4 — Credential Context Manager with Retry Cleanup

#### Quick Reference

```python
@contextlib.contextmanager
def temporary_credential_mount() -> Generator[Path | None, None, None]:
    credentials_path = Path.home() / ".claude" / ".credentials.json"
    if not credentials_path.exists():
        yield None
        return
    temp_dir = Path.home() / f".app-temp-creds-{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(exist_ok=True)
    # ... copy credentials ...
    try:
        yield temp_dir
    finally:
        _cleanup_temp_dir(temp_dir)  # retry 3× with 0.5s delay

def _cleanup_temp_dir(temp_dir: Path, retries: int = 3, delay: float = 0.5) -> None:
    for attempt in range(retries):
        try:
            shutil.rmtree(temp_dir)
            return
        except OSError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.warning("Failed to clean up temp credentials dir after %d attempts: %s",
                               retries, temp_dir)
```

**Update container managers** — context manager owns the lifecycle:

```python
def run(self, config):
    with temporary_credential_mount() as creds_dir:
        volumes = self._build_volumes(config, creds_dir=creds_dir)
        return self._run_with_volumes(config, volumes)
```

**One-time stale cleanup:**

```bash
rm -rf ~/.app-temp-creds-*  # adapt glob to your naming convention
```

### Pattern 5 — ProcessPoolExecutor to ThreadPoolExecutor Conversion

#### Quick Reference

```bash
# Find all affected files
grep -rn "ProcessPoolExecutor\|from multiprocessing import Manager\|BrokenProcessPool\|SyncManager" src/
```

**Core substitutions:**

| Before | After |
| ------- | ------- |
| `ProcessPoolExecutor` | `ThreadPoolExecutor` |
| `Manager().Event()` | `threading.Event()` |
| `Manager().Semaphore(n)` | `threading.Semaphore(n)` |
| `manager.dict()` | `{}` (threads share memory) |
| `BrokenProcessPool` handler | Remove |
| Disk-merge in `save_checkpoint` | Remove (threads share one object) |
| `from_existing()` classmethods | Delete |

**Key decision** — threads are sufficient when workers run external CLI subprocesses (`subprocess.run()`/`Popen()`), because the GIL is released during I/O and the real work happens in external processes.

**Semantic rebase strategy** when the final commit subsumes earlier incremental fixes:

```bash
# Edit rebase todo to drop superseded intermediate commits
git rebase -i origin/main
# In editor: change 'pick' to 'drop' for intermediate commits
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Define `UntilHaltError` in executor module | `subtest_executor` would need to import `subtest_state_machine`, which needs to import `subtest_executor` | Circular import | Define sentinel in the state-machine module; use lazy import in executor |
| No state transition on `UntilHaltError` | Exception propagated past `set_state()` call | State stays at prior state; re-executes on resume | Catch sentinel, still update state, then re-raise |
| Tier-merge only inside `if experiment_state in ("failed", "interrupted")` | CLI tiers not merged when experiment was previously `"complete"` | Move tier-merge outside the failed/interrupted block | State-conditional merge misses the resume-with-new-tiers case |
| Remove `# type: ignore[arg-type]` before testing | After fix, mypy emits `unused-ignore` error | Remove suppressions only after the underlying incompatibility is fixed | Fix code first, then clean up ignores |
| Catch `KeyboardInterrupt` in state machine | Signal handler sets `_shutdown_requested = True`; `subprocess.run()` returns normally, not via exception | Check `is_shutdown_requested()` after `subprocess.run()` returns | `subprocess.run()` does NOT raise on SIGINT |
| Catch `ShutdownInterruptedError` only at run level | Upper levels' `except Exception` marked tier/experiment FAILED | Add `except ShutdownInterruptedError` before `except Exception` at **all four** SM levels | One unhandled level undoes the whole pattern |
| Reset tier to `SUBTESTS_RUNNING` on interrupt | `SUBTESTS_RUNNING` expects aggregated results to already be present | Reset to `CONFIG_LOADED` instead | `SUBTESTS_RUNNING` = select best subtest, not re-run |
| Put `ShutdownInterruptedError` in `state_machine.py` | Circular import: `state_machine.py` imports `runner.py`; `runner.py` already imports `state_machine.py` | Define in `runner.py` (which owns the shutdown flag) | Put sentinel in the module that owns the flag |
| Let `ShutdownInterruptedError` propagate through safe wrapper | `except Exception` in wrapper converts it to `WorkerError SubTestResult`, swallowing the signal | Explicitly re-raise inside the wrapper | Safe wrappers must carve out the sentinel |
| Global semaphores with `configure_resource_limits()` | Module-level `_workspace_semaphore` init with global keyword; no reset between runs, race condition in init | PLW0603, stale state, race | Never use mutable module-level globals for concurrency primitives |
| Split acquire/release across stages | Acquire in stage 2, release in stage 15 | `ShutdownInterruptedError` bypassed release, leaking slot permanently | Always pair acquire/release in the same scope via context manager |
| Import global from another module for release | `from stages import _workspace_semaphore` in finalization | If global was reassigned, import gets stale reference | Pass resources via dependency injection, not module imports |
| Atomic checkpoint writes without write lock | PID+TID temp file + atomic rename | Two threads serialize simultaneously; last rename wins and first thread's state is lost | Atomic rename prevents corruption but not data loss from concurrent serialization |
| `shutil.rmtree()` in `finally` with bare `except Exception: pass` | Cleanup silently failed on WSL2 Docker mount release race | 498 directories leaked | Retry with delay; log warning on final failure — never silently swallow cleanup errors |
| Temp dir created in `_build_volumes()`, cleaned in `_run_with_volumes()` finally | Gap between creation and `try` block — any exception in that window leaks the dir | Move temp dir lifecycle into a single context manager | Context manager eliminates the unguarded gap |
| Incremental lock fixes for multiprocessing | Added `filelock.FileLock` for pipeline serialization, then removed it | Each fix addressed a symptom, not the root cause | When fixing serialization issues in multiprocessing, consider whether threads eliminate the entire problem class |
| Keeping `_checkpoint_write_lock` after thread conversion | Threading.Lock retained after converting to threads | Unnecessary — threads share one checkpoint object, merge locks unneeded | Identify which synchronization primitives exist solely because of process boundaries |
| Making scheduler serializable for `forkserver` | Made scheduler serializable | Still failed because `Manager().Semaphore()` proxies contained `AuthenticationString` | The real fix is switching to threads, not making everything serializable |
| Rebase with all intermediate commits | Tried to rebase 7 commits onto main | Cascading conflicts since each commit partially undid the previous one | When commits form a superseding chain, drop intermediates and keep only the final result |
| CamelCase alias for state enum | `from package.models import ExperimentState as _ES` | Triggers ruff N814 | Use `ExperimentState` directly — no alias |
| `warnings.warn()` between imports | Placed warn between stdlib and package imports | Breaks E402 (module-level import not at top) | Move `warnings.warn()` after all imports |

## Results & Parameters

### Timeout Defaults (Tuned for 16GB WSL2, 8-core, --threads 15)

```python
ResourceManager(
    max_workspaces=cpu_count * 2,   # e.g., 16 for 8-core
    max_agents=min(threads, cpu_count),  # e.g., 8 for 8-core, 15 threads
)
workspace_slot(timeout=300)    # 5 min — worktree creation is fast
agent_slot(timeout=600)        # 10 min — agent execution can queue
pipeline_slot()                # No timeout — Lock() blocks until available
```

### Credential Cleanup Retry (WSL2 Docker)

```python
retries: int = 3       # 3 attempts covers typical mount release window
delay: float = 0.5     # 0.5s between attempts = max 1s extra latency on failure
temp_dir.chmod(0o755)  # directory: world-readable+executable
temp_creds.chmod(0o644)  # file: world-readable
```

### Test Coverage Outcomes

| Skill | Tests | Coverage | Branch |
| ------- | ------- | ---------- | ------- |
| resumable-state-machine-until-halt | 3108 pass (+14 new) | 78.27% | 1067-additive-cli-args-checkpoint |
| state-machine-interrupt-handling | 3121 pass (+4 new) | 78.10% | fix-resume-issues-triple-bug |
| resource-manager-pattern | 4788 pass | — | — |
| credential-mount-context-manager | 2454 pass (+6 new) | 74.28% | PR #1010 |
| multiprocess-to-multithread-conversion | 4802 pass (~600 lines removed) | 77.51% | — |

### Anti-Patterns to Avoid

```python
# BAD: Global mutable semaphore
_sem: threading.Semaphore | None = None
def configure():
    global _sem       # PLW0603
    if _sem is None:  # Race condition
        _sem = threading.Semaphore(N)

# BAD: Split acquire/release across functions
def start(): _sem.acquire()
def end(): _sem.release()  # What if exception between start() and end()?

# BAD: Import global from another module to release it
from other_module import _sem
_sem.release()  # Stale reference if _sem was reassigned

# BAD: Bare except swallowing cleanup failure
try:
    shutil.rmtree(d)
except Exception:
    pass  # Silent leak!
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1107 — additive CLI args + --until fix | resumable-state-machine-until-halt |
| ProjectScylla | PR #1109 — Ctrl+C interrupt handling | state-machine-interrupt-handling |
| ProjectScylla | PR #1010 — 498 leaked `.scylla-temp-creds-*` dirs fixed | credential-mount-context-manager |
| ProjectScylla | ProcessPool → ThreadPool for Python 3.14t | multiprocess-to-multithread-conversion |
