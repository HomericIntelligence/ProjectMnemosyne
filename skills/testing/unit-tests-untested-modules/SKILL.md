# Skill: Unit Tests for Untested Source Modules

| Property | Value |
|----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Add unit tests for 6 source modules with no test file (agent_runner, parallel_executor, judge_runner, workspace_setup, config/validation, curses_ui) |
| **Outcome** | ✅ 133 new tests added, all pass; coverage 74.93% (threshold 73%) |
| **Context** | Issue #850 — quality audit identified modules with zero test coverage; 2 were HIGH priority core execution paths |

## When to Use This Skill

Use this skill when:
- A quality audit identifies source modules with no corresponding test file
- Coverage threshold is at risk because of missing test files
- An issue requests adding unit tests for a list of specific modules
- Execution path modules (agents, judges, executors) lack test coverage

**Key Indicators**:
- `tests/unit/e2e/` or `tests/unit/<module>/` directory exists but no `test_<name>.py`
- Coverage report shows 0% for a source file
- Issue body lists specific modules with a Priority column

## Verified Workflow

### 1. Audit What Already Exists

Before writing anything, check the test directory for existing files:

```bash
ls tests/unit/e2e/
ls tests/unit/config/
ls tests/unit/automation/
```

**Critical**: Some files listed in the issue may already have partial test files.
- If `test_workspace_setup.py` already exists → extend it, don't replace it
- If `test_validation.py` already exists → add new test classes at the bottom

### 2. Read Source Files Before Writing Tests

Read each source module fully before writing tests. Key things to capture:

- **Function signatures** — exact parameter names, types, defaults
- **Return types** — what does the function return on success vs failure?
- **Error conditions** — what raises? what returns False/None?
- **Dependencies** — what does the function call internally? (subprocess, json, Path)
- **Constants** — `RESULT_FILE`, `AGENT_DIR`, `JUDGE_DIR` from `paths.py`

```bash
# Also check the path constants
cat scylla/e2e/paths.py
```

### 3. Decide Mock Strategy Per Module

| Module Type | Mock Strategy |
|------------|---------------|
| File I/O (save/load) | Use `tmp_path` pytest fixture — write real files |
| Subprocess calls | `patch("subprocess.run")` with `MagicMock(returncode=0)` |
| External API calls | `patch("module.function_name", return_value=mock_result)` |
| multiprocessing.Manager | Use real `Manager()` in a `with Manager() as mgr:` context |
| curses | `patch("curses.wrapper")`, `patch("curses.endwin")` |

**Rule**: Prefer real filesystem I/O with `tmp_path` over `mock_open`. It's more reliable and tests the actual serialization.

### 4. Check If Existing Test File Needs Extending

```python
# If test_validation.py exists but is missing functions:
# 1. Read the existing file to understand current imports
# 2. Add the missing functions to the import line
# 3. Append new test classes at the bottom
```

**NEVER replace an existing test file.** Extend it.

### 5. Write Tests in Priority Order

Start with HIGH priority modules. For each function:

1. **Happy path** — valid inputs produce expected output
2. **Error path 1** — missing file / malformed data
3. **Error path 2** — specific invalid state (e.g., exit_code=-1 + zero tokens)
4. **Parametrized edge cases** — boundary conditions

```python
class TestHasValidAgentResult:
    """Tests for _has_valid_agent_result()."""

    def test_returns_false_when_no_result_file(self, tmp_path: Path) -> None:
        """False when result.json does not exist."""
        ...

    def test_returns_false_for_incomplete_execution(self, tmp_path: Path) -> None:
        """False for exit_code=-1 with all-zero token stats."""
        ...

    @pytest.mark.parametrize("missing_field", ["exit_code", "token_stats", "cost_usd"])
    def test_returns_false_for_each_missing_required_field(
        self, tmp_path: Path, missing_field: str
    ) -> None:
        ...
```

### 6. Handle multiprocessing.Manager Tests Carefully

`RateLimitCoordinator` uses `multiprocessing.Manager` for shared state. Do NOT mock it — use a real manager:

```python
def test_not_paused_initially(self) -> None:
    with Manager() as mgr:
        coordinator = RateLimitCoordinator(mgr)
        assert coordinator.check_if_paused() is False
```

**Critical**: `check_if_paused()` blocks if the pause event is set and the resume event is not set. Always set the resume event before triggering the pause in tests:

```python
# WRONG — will block forever
coordinator.signal_rate_limit(info)
result = coordinator.check_if_paused()

# RIGHT — pre-set resume to unblock
coordinator._resume_event.set()
coordinator.signal_rate_limit(info)
```

### 7. Handle Timing-Sensitive Thread Tests

Thread lifecycle tests (CursesUI start/stop) are prone to race conditions when curses.wrapper is mocked (it returns instantly, so `running` becomes False before assertions):

```python
# WRONG — race condition: thread may finish before second start() call
def test_start_is_idempotent(self) -> None:
    ui.start()
    first_thread = ui.thread
    ui.start()  # thread may already be done
    assert first_thread is ui.thread  # may fail

# RIGHT — manually set state to avoid timing dependency
def test_start_does_not_start_second_thread_when_already_running(self) -> None:
    ui.running = True
    ui.thread = threading.Thread(target=lambda: None)
    first_thread = ui.thread
    ui.start()  # no-op since running=True
    assert first_thread is ui.thread
```

### 8. Fix Patch Targets for Imported Functions

When a module does `from scylla.utils.terminal import restore_terminal`, patch the source, not the importer:

```python
# WRONG
patch("scylla.automation.curses_ui.restore_terminal")

# RIGHT — patch where the function is defined
patch("scylla.utils.terminal.restore_terminal")
```

### 9. Run Tests and Fix Pre-commit Issues

```bash
# Run only new tests first
pixi run python -m pytest tests/unit/e2e/test_agent_runner.py -v --no-cov

# Run full suite with coverage check
pixi run python -m pytest tests/unit/ -q

# Fix formatting/linting
pre-commit run --files <new_test_files>
```

**Common pre-commit issue**: Docstrings > 100 chars trigger `E501`. Shorten them.

### 10. Commit and PR

```bash
git add tests/unit/e2e/test_agent_runner.py \
        tests/unit/e2e/test_judge_runner.py \
        tests/unit/e2e/test_parallel_executor.py \
        tests/unit/config/test_validation.py \
        tests/unit/automation/test_curses_ui.py

git commit -m "test(unit): Add unit tests for N untested source modules"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

### ❌ Attempt 1: Patch `restore_terminal` at import site
**What we tried**: `patch("scylla.automation.curses_ui.restore_terminal")`

**Why it failed**: `curses_ui.py` imports `restore_terminal` inline inside a method (`from scylla.utils.terminal import restore_terminal`), so the module-level attribute doesn't exist.

**Fix**: Patch the source: `patch("scylla.utils.terminal.restore_terminal")`

### ❌ Attempt 2: Thread-based idempotency test with timing
**What we tried**: Start UI, capture thread, call start() again, assert same thread.

**Why it failed**: With `curses.wrapper` mocked to a no-op, the background thread completes instantly and sets `running=False`. The second `start()` call sees `running=False` and creates a new thread rather than returning early.

**Fix**: Manually set `ui.running = True` and `ui.thread = threading.Thread(...)` to simulate the running state without depending on thread timing.

### ❌ Attempt 3: Calling `check_if_paused()` after `signal_rate_limit()` without pre-setting resume
**What we tried**: Signal rate limit, then call check_if_paused() to verify pause detection.

**Why it failed**: `check_if_paused()` calls `self._resume_event.wait()` which blocks indefinitely when the resume event is not set.

**Fix**: Set `coordinator._resume_event.set()` before calling `check_if_paused()` so the wait returns immediately.

## Results & Parameters

### Test Count by Module

| Module | Test File | Tests |
|--------|-----------|-------|
| `agent_runner.py` | `test_agent_runner.py` | 23 |
| `judge_runner.py` | `test_judge_runner.py` | 27 |
| `parallel_executor.py` | `test_parallel_executor.py` | 14 |
| `config/validation.py` | `test_validation.py` (extended) | +22 |
| `automation/curses_ui.py` | `test_curses_ui.py` | 20 |
| **Total new** | | **106** |

### Coverage Results

```
Before: ~73% (at threshold boundary)
After:  74.93% (threshold: 73%)
Tests:  2535 passed, 0 failed, 8 warnings
```

### Mock Pattern for Agent/Judge Result Files

```python
def _write_result_json(agent_dir: Path, data: dict) -> None:
    """Write result.json to agent_dir."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / RESULT_FILE).write_text(json.dumps(data))

def test_returns_true_for_valid_success_result(self, tmp_path: Path) -> None:
    agent_dir = tmp_path / AGENT_DIR
    agent_dir.mkdir(parents=True)
    _write_result_json(agent_dir, {
        "exit_code": 0,
        "token_stats": {"input_tokens": 100, "output_tokens": 50},
        "cost_usd": 0.01,
    })
    assert _has_valid_agent_result(tmp_path) is True
```

### Mock Pattern for RateLimitCoordinator

```python
def test_signal_rate_limit_sets_pause(self) -> None:
    with Manager() as mgr:
        coordinator = RateLimitCoordinator(mgr)
        info = RateLimitInfo(source="agent", retry_after_seconds=60.0,
                             error_message="rate limited", detected_at="...")

        # Pre-set resume so check_if_paused doesn't block
        coordinator._resume_event.set()
        coordinator.signal_rate_limit(info)

        assert coordinator._pause_event.is_set()
```

## Key Takeaways

1. **Always check if test file already exists** before creating a new one — extend, don't replace
2. **Read source before writing tests** — especially to find path constants (`RESULT_FILE`, `AGENT_DIR`)
3. **Use `tmp_path` for file I/O tests** — real files are more reliable than `mock_open`
4. **multiprocessing.Manager: use a real one** — don't mock it, use `with Manager() as mgr:`
5. **Pre-set blocking events before triggering them** — avoid deadlocks in coordinator tests
6. **Thread timing tests are fragile** — simulate state directly rather than relying on thread scheduling
7. **Patch at the definition site** — `from X import Y` means patch `X.Y`, not the importer
8. **Docstrings must be ≤100 chars** — ruff E501 will fail on long docstrings
