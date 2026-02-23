# Raw Notes: Unit Tests for Untested Modules (Issue #850)

## Session Details

- **Date**: 2026-02-22
- **Issue**: #850 — testing: Add unit tests for 6 untested source modules
- **PR**: #975 (ProjectScylla)
- **Branch**: `850-auto-impl`

## Source Modules Analyzed

### scylla/e2e/agent_runner.py
- 4 functions: `_save_agent_result`, `_load_agent_result`, `_create_agent_model_md`, `_has_valid_agent_result`
- Key constant: `RESULT_FILE` from `scylla.e2e.paths`
- Agent dir structure: `run_dir / "agent" / "result.json"`
- Invalid result detection: `exit_code == -1 AND all token stats == 0`

### scylla/e2e/judge_runner.py
- 6 functions: `_save_judge_result`, `_load_judge_result`, `_has_valid_judge_result`, `_compute_judge_consensus`, `_run_judge`, `_phase_log`
- `_compute_judge_consensus`: average score, majority vote for passed, grade from `assign_letter_grade`
- `_run_judge`: raises ValueError if no judge_models; RateLimitError propagates immediately; other exceptions create zero-score failed summaries
- `JudgeResultSummary` has `is_valid` field that gates consensus inclusion

### scylla/e2e/parallel_executor.py
- `RateLimitCoordinator`: uses `manager.Event()` and `manager.dict()` for cross-process sync
- `check_if_paused()` calls `self._resume_event.wait()` — BLOCKS until resume set
- `signal_rate_limit()` updates shared dict AND sets pause event
- `resume_all_workers()` clears pause, sets resume
- `run_tier_subtests_parallel()` is complex — not unit tested here (integration concern)

### scylla/config/validation.py
- Existing test file covered `extract_model_family` and `validate_name_model_family_consistency`
- Missing: `get_expected_filename` (colon → dash), `validate_filename_model_id_consistency`, `validate_model_config_referenced`
- `validate_model_config_referenced` scans `.yaml` and `.py` files, skips self-reference

### scylla/automation/curses_ui.py
- `LogBuffer`: deque-based, thread-safe via lock
- `ThreadLogManager`: dict of thread_id → LogBuffer
- `CursesUI`: uses `curses.wrapper` in background thread, atexit cleanup
- `_emergency_cleanup` imports `restore_terminal` inline (affects patch target)

## Path Constants (from scylla/e2e/paths.py)

```python
AGENT_DIR = "agent"
JUDGE_DIR = "judge"
RESULT_FILE = "result.json"

get_agent_result_file(run_dir) -> run_dir / "agent" / "result.json"
get_judge_result_file(run_dir) -> run_dir / "judge" / "result.json"
```

## Key Model Signatures

### AdapterResult (scylla/adapters/base.py)
```python
class AdapterTokenStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

class AdapterResult(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    token_stats: AdapterTokenStats = AdapterTokenStats()
    cost_usd: float = 0.0
    api_calls: int = 0
```

### JudgeResultSummary (scylla/e2e/models.py)
```python
class JudgeResultSummary(BaseModel):
    model: str
    score: float | None = None
    passed: bool | None = None
    grade: str | None = None
    reasoning: str | None = None
    judge_number: int = 1
    is_valid: bool = True
    criteria_scores: dict | None = None
```

### RateLimitInfo (scylla/e2e/rate_limit.py)
```python
class RateLimitInfo(BaseModel):
    source: str  # must be "agent" or "judge" (validated)
    retry_after_seconds: float | None
    error_message: str
    detected_at: str
```

## Bugs/Pitfalls Found During Implementation

1. **`restore_terminal` patch path**: The function is imported inline inside `_emergency_cleanup()`:
   ```python
   def _emergency_cleanup(self):
       try:
           curses.endwin()
       except Exception:
           pass
       from scylla.utils.terminal import restore_terminal
       restore_terminal()
   ```
   Must patch `scylla.utils.terminal.restore_terminal`, not `scylla.automation.curses_ui.restore_terminal`.

2. **`check_if_paused()` deadlock risk**: Calling after `signal_rate_limit()` without pre-setting `_resume_event` blocks forever.

3. **Thread timing race in CursesUI.start() idempotency test**: With mocked `curses.wrapper`, the background thread completes synchronously, setting `running=False` before the test can call `start()` again. Solution: set state manually.

4. **`RateLimitInfo` source validation**: Must be `"agent"` or `"judge"` — using `"test"` raises `ValueError` from Pydantic validator.

## Test Count Summary

```
test_agent_runner.py:     23 tests
test_judge_runner.py:     27 tests
test_parallel_executor.py: 14 tests
test_validation.py:       +22 tests (extended existing file)
test_curses_ui.py:        20 tests
Total new tests:          106
Full suite:               2535 passed, 0 failed
Coverage:                 74.93% (threshold: 73%)
```
