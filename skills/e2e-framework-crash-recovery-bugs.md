---
name: e2e-framework-crash-recovery-bugs
description: Fix E2E framework crash-recovery bugs including checkpoint thread-safety
  race conditions, resume state machine AssertionError on tier_config=None, and LLM
  judge returning conversational text instead of JSON
category: debugging
date: 2026-02-23
version: 1.0.0
user-invocable: false
tags:
- checkpoint
- threading
- resume
- judge
- haiku
- race-condition
- e2e
- state-machine
- json-parse
---
# E2E Framework Crash Recovery Bugs

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-02-23 |
| **Objective** | Fix three critical bugs causing test failures in dryrun3 batch analysis |
| **Outcome** | Fixed — 2975 tests pass, 77.94% coverage, all pre-commit hooks pass |
| **Project** | ProjectScylla |
| **PR** | [#1080](https://github.com/HomericIntelligence/ProjectScylla/pull/1080) |

## When to Use

Use this skill when you encounter any of the following symptoms in the E2E evaluation framework:

- `FileNotFoundError: [Errno 2] No such file or directory: 'checkpoint.tmp.*.json'` during concurrent tier execution
- `AssertionError: tier_ctx.tier_config is not None` when resuming an experiment mid-run
- LLM judge silently producing no score because Haiku returns conversational text instead of JSON
- Tests in `tier_states` showing `FAILED` with ENOENT errors despite correct input data
- `ValueError: Could not parse judge response` on retry-less judge calls

## Verified Workflow

### Bug 1 — Checkpoint Thread-Safety Race Condition

**File**: `<project-root>/scylla/e2e/checkpoint.py`

**Root Cause**: `save_checkpoint()` used a PID-only temp filename (`checkpoint.tmp.{pid}.json`). Multiple threads in the same process share the same PID, so concurrent writes collide:

1. Thread A writes to `checkpoint.tmp.1234.json`
2. Thread B opens the same path, truncates it, writes its data
3. Thread A calls `rename()` — succeeds, but wrote Thread B's data
4. Thread B calls `rename()` — ENOENT (file already renamed by Thread A)

**Fix**:

```python
# Add at module level:
import threading
_checkpoint_write_lock = threading.Lock()

# In save_checkpoint():
tid = threading.get_ident()
temp_path = path.parent / f"{path.stem}.tmp.{os.getpid()}.{tid}{path.suffix}"
with _checkpoint_write_lock:
    with open(temp_path, "w") as f:
        json.dump(checkpoint.model_dump(), f, indent=2)
    temp_path.replace(path)
```

**Impact**: Caused 21 ENOENT errors in dryrun3, leading to test-021, test-010, test-038 failures.

### Bug 2 — Resume AssertionError on tier_config = None

**File**: `<project-root>/scylla/e2e/runner.py`

**Root Cause**: When resuming from a checkpoint where a tier is already past `PENDING` state (e.g., `CONFIG_LOADED`), `action_pending()` is skipped by the state machine. `action_config_loaded()` then asserts `tier_ctx.tier_config is not None` — which fails because `TierContext` is freshly constructed on every `_run_tier()` call with `tier_config=None`.

**Fix** (add before `actions = self._build_tier_actions(...)`):

```python
_tier_resume_state = tsm.get_state(tier_id.value)
if _tier_resume_state not in (TierState.PENDING, TierState.COMPLETE, TierState.FAILED):
    logger.info(
        f"Resuming {tier_id.value} from {_tier_resume_state.value} "
        "— pre-loading tier config for resume"
    )
    _resume_tier_config = self.tier_manager.load_tier_config(
        tier_id, self.config.skip_agent_teams
    )
    if self.config.max_subtests is not None:
        _resume_tier_config.subtests = _resume_tier_config.subtests[: self.config.max_subtests]
    tier_ctx.tier_config = _resume_tier_config
    if self.experiment_dir:
        tier_ctx.tier_dir = self.experiment_dir / tier_id.value
```

**Key Insight**: `TierID.T0.value` is `"T0"` (uppercase). Checkpoint `tier_states` keys must use uppercase (e.g., `"T0"`, not `"t0"`) to match. Using lowercase causes `get_tier_state()` to return `"pending"` (the default), silently skipping the preload block.

### Bug 3 — Haiku Judge Returns Conversational Text Instead of JSON

**File**: `<project-root>/scylla/e2e/llm_judge.py`

**Root Cause**: When `claude-haiku-4-5-20251001` is used as judge, it frequently returns conversational responses instead of structured JSON (e.g., "I appreciate you sharing the context, but I need more info.").

**Fix** (replace single call with a retry loop):

```python
_max_judge_attempts = 3
_json_reminder = (
    "\n\n**IMPORTANT**: Your response MUST be a valid JSON object only. "
    "Do not include any text, explanation, or markdown before or after the JSON. "
    "Start your response with `{` and end with `}`."
)
last_parse_error: Exception | None = None
for _attempt in range(_max_judge_attempts):
    _prompt = judge_prompt if _attempt == 0 else judge_prompt + _json_reminder
    if _attempt > 0:
        logger.warning(
            f"Judge parse failure on attempt {_attempt}/{_max_judge_attempts - 1}, "
            f"retrying with JSON reminder (model={model})"
        )
    stdout, stderr, result = _call_claude_judge(_prompt, model, workspace)
    try:
        judge_result = _parse_judge_response(result)
        break
    except ValueError as e:
        last_parse_error = e
else:
    assert last_parse_error is not None  # noqa: S101
    raise last_parse_error
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Tests Written

### Bug 1: `TestSaveCheckpointThreadSafety` in `tests/unit/e2e/test_checkpoint.py`

| Test | Assertion |
| ------ | ----------- |
| `test_concurrent_saves_do_not_raise` | 20 threads writing concurrently, none raise |
| `test_no_stale_tmp_files_after_concurrent_saves` | No `.tmp.*.json` leftovers after 10 concurrent writes |
| `test_sequential_saves_still_work` | Regression: single-threaded save still works |

### Bug 2: `TestResumeTierConfigPreload` in `tests/unit/e2e/test_runner.py`

| Test | Assertion |
| ------ | ----------- |
| `test_tier_ctx_populated_when_resuming_from_config_loaded` | `load_tier_config` called for `CONFIG_LOADED` state |
| `test_tier_ctx_not_preloaded_for_pending_state` | `PENDING` state skips preload |
| `test_tier_ctx_not_preloaded_for_complete_state` | `COMPLETE` state skips preload |

### Bug 3: `TestRunLlmJudgeRetry` in `tests/unit/e2e/test_llm_judge.py`

| Test | Assertion |
| ------ | ----------- |
| `test_first_attempt_success_no_retry` | Clean JSON on first try = 1 call total |
| `test_retry_on_conversational_response` | Bad then good = 2 calls, second has JSON reminder |
| `test_succeeds_on_third_attempt` | Bad, bad, good = 3 calls |
| `test_raises_after_all_attempts_exhausted` | All bad = `ValueError` raised |
| `test_first_attempt_prompt_has_no_reminder` | First prompt is clean (no IMPORTANT tag) |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Max judge retry attempts | 3 |
| Thread lock scope | Module-level (`_checkpoint_write_lock`) |
| Temp file naming | `{stem}.tmp.{pid}.{thread_id}{suffix}` |
| States that skip preload | `PENDING`, `COMPLETE`, `FAILED` |
| States that trigger preload | Everything else (e.g., `CONFIG_LOADED`, `RUNNING`) |
| JSON reminder injection | On attempt 2+ (0-indexed attempt >= 1) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1080, dryrun3 batch analysis | [notes.md](../../references/notes.md) |
