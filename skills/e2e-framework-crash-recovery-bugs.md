---
name: e2e-framework-crash-recovery-bugs
description: "Fix E2E framework crash-recovery bugs including checkpoint thread-safety race conditions, resume state machine AssertionError on tier_config=None, LLM judge returning conversational text instead of JSON, _restore_run_context() missing run_result and judgment loading, progressive resume failures (file path mismatches), and --until stepping bugs (TierState naming confusion). Use when: (1) FileNotFoundError on checkpoint.tmp.*.json, (2) AssertionError tier_ctx.tier_config is not None on resume, (3) judge silently produces no score, (4) Phase 3 resume crashes with run_result must be set, (5) experiment works first time but fails on Nth resume, (6) No sub-test results to select from on --until stepping."
category: debugging
date: 2026-02-23
version: 1.4.0
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
- restore-run-context
- file-path-mismatch
- until-stepping
- tier-state
- pytest-fixtures
absorbed:
- e2e-resume-restore-run-context
- resume-crash-debugging
- resume-functionality-tests
- until-resume-debugging
---
# E2E Framework Crash Recovery Bugs

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-02-23 |
| **Objective** | Fix critical bugs causing test failures in E2E checkpoint/resume system |
| **Outcome** | Fixed — 2975 tests pass, 77.94% coverage, all pre-commit hooks pass |
| **Project** | ProjectScylla |
| **PR** | [#1080](https://github.com/HomericIntelligence/ProjectScylla/pull/1080), [#1546](https://github.com/HomericIntelligence/ProjectScylla/pull/1546), [#142](https://github.com/HomericIntelligence/ProjectScylla/pull/142) |

## When to Use

Use this skill when you encounter any of the following symptoms in the E2E evaluation framework:

- `FileNotFoundError: [Errno 2] No such file or directory: 'checkpoint.tmp.*.json'` during concurrent tier execution
- `AssertionError: tier_ctx.tier_config is not None` when resuming an experiment mid-run
- LLM judge silently producing no score because Haiku returns conversational text instead of JSON
- Tests in `tier_states` showing `FAILED` with ENOENT errors despite correct input data
- `ValueError: Could not parse judge response` on retry-less judge calls
- Resume from a state past `JUDGE_COMPLETE` or `RUN_FINALIZED` crashes with missing `ctx.run_result` or `ctx.judgment`
- Phase 3 retry after partial judge execution leaves stale artifacts (judge dirs, run_result.json, reports)
- Progressive resume failures: experiment works first time, fails on Nth resume
- `FileNotFoundError: judgment.json` or similar file not found errors after 3rd–4th resume
- Reports showing 0.000 scores but individual `run_result.json` files have correct data
- "No sub-test results to select from" on second `--until` invocation
- "agent_result must be set before finalize_run" or "judgment must be set before finalize_run" on resume
- `assert adapter_config is not None` when resuming from `replay_generated`

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
| N/A (Bugs 1–3) | Direct approach worked | N/A | Solution was straightforward |
| Direct `E2ERunResult.model_validate(data)` | Load run_result.json directly into Pydantic model | `ConfigDict(frozen=True)` without `extra="ignore"` rejects extra keys (`process_metrics`, `progress_tracking`, `changes`) | Always check Pydantic model config before deserialization; `stage_finalize_run()` adds extra keys beyond the model schema |
| **Hypothesis: Aggregation bug** | Assumed zeros in reports meant aggregation logic was broken | User's actual error was FileNotFoundError, not aggregation | Always get the actual error traceback before diagnosing |
| **Hypothesis: Checkpoint out of sync** | Thought checkpoint was marking complete before files saved | Actual bug was file path mismatch in loading function | File path bugs can look like state sync issues |
| **Exploring aggregation code first** | Launched agents to understand report generation pipeline | Needed error traceback to find root cause, not exploration | For crashes, start with the error, not architecture exploration |

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
| ProjectScylla | haiku-2 experiment Phase 3 resume failure | PR #1546, 7 tests cleaned, 1597 unit tests pass |
| ProjectScylla | PR #142 - Resume functionality tests for E2E experiments | [notes.md](../../references/notes.md) |

---

## _restore_run_context() Loading Fix for Phase 3 Resume

*Absorbed from: e2e-resume-restore-run-context (2026-03-25)*

### Problem

When resuming past `JUDGE_COMPLETE` or `RUN_FINALIZED`, `stage_write_report()` fails with "run_result must be set before write_report". `_restore_run_context()` loaded `agent_result` (past AGENT_COMPLETE) and `judge_prompt` (past JUDGE_PROMPT_BUILT) but NOT `judgment` or `run_result` for later states.

### Quick Reference

```python
# In _restore_run_context() (subtest_executor.py), after judge_prompt loading:

# Load judgment for states past JUDGE_COMPLETE
if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and ctx.judgment is None:
    from scylla.e2e.judge_runner import _has_valid_judge_result, _load_judge_result
    from scylla.e2e.paths import get_judge_dir
    judge_dir = get_judge_dir(ctx.run_dir)
    if _has_valid_judge_result(ctx.run_dir):
        ctx.judgment = _load_judge_result(judge_dir)

# Load run_result for states past RUN_FINALIZED
if is_at_or_past_state(run_state, RunState.RUN_FINALIZED) and ctx.run_result is None:
    run_result_path = ctx.run_dir / "run_result.json"
    if run_result_path.exists():
        ctx.run_result = _load_run_result(run_result_path)
```

```python
# _load_run_result helper — filter extra keys before model_validate
def _load_run_result(run_result_path: Path) -> Any:
    from scylla.e2e.models import E2ERunResult
    data = json.loads(run_result_path.read_text())
    known_fields = set(E2ERunResult.model_fields.keys())
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return E2ERunResult.model_validate(filtered)
```

### Restore Coverage Matrix

| Field | Loaded By | For States Past |
| ------- | ----------- | ----------------- |
| `ctx.agent_result` | `_restore_run_context()` | `AGENT_COMPLETE` |
| `ctx.judge_prompt` | `_restore_run_context()` | `JUDGE_PROMPT_BUILT` |
| `ctx.judgment` | `_restore_run_context()` (NEW) | `JUDGE_COMPLETE` |
| `ctx.run_result` | `_restore_run_context()` (NEW) | `RUN_FINALIZED` |
| `ctx.judgment` | `stage_capture_diff()` | `DIFF_CAPTURED` (replay only, agent not re-run) |

### Run State Machine (Judge Phase)

```
DIFF_CAPTURED → JUDGE_PIPELINE_RUN → JUDGE_PROMPT_BUILT → JUDGE_COMPLETE
    → RUN_FINALIZED → REPORT_WRITTEN → CHECKPOINTED → WORKTREE_CLEANED
```

### Cleanup Script Pattern for Stale Phase 3 Data

```python
# Reset states past judge phase back to diff_captured
JUDGE_AND_BEYOND = {"judge_pipeline_run", "judge_prompt_built", "judge_complete",
                     "run_finalized", "report_written", "checkpointed", "worktree_cleaned"}

# For each run in checkpoint:
if state in JUDGE_AND_BEYOND or state == "failed":
    runs[run_num_str] = "diff_captured"

# Clear completed_runs (contains judge pass/fail status)
cp["completed_runs"] = {}

# Reset subtest/tier/experiment states
# subtest: aggregated/failed → runs_in_progress
# tier: complete/failed/etc → config_loaded
# experiment: → tiers_running
```

**Cleanup deletes**: `judge/` dirs, `run_result.json`, `report.md`, `report.json` at run level, plus report files at subtest/tier/experiment levels.

### Key Files

| File | Role |
| ------ | ------ |
| `scylla/e2e/subtest_executor.py:115-197` | `_restore_run_context()` — the only place RunContext fields are restored on resume |
| `scylla/e2e/stage_finalization.py:447-483` | `stage_write_report()` — requires `ctx.run_result`, `ctx.agent_result`, `ctx.judgment` |
| `scylla/e2e/stage_finalization.py:316-444` | `stage_finalize_run()` — creates `E2ERunResult`, writes `run_result.json` |
| `scylla/e2e/stages.py:709-746` | `stage_capture_diff()` — loads judgment on replay through DIFF_CAPTURED (not past it) |
| `scylla/e2e/models.py:85-120` | `RunState` enum — sequential states from PENDING to WORKTREE_CLEANED |

---

## Progressive Resume Failures Debugging Methodology

*Absorbed from: resume-crash-debugging (2026-01-08)*

### Problem Pattern

Experiments work on first run but crash on Nth resume (e.g., 4th resume) with `FileNotFoundError`. Root cause is typically a **file path mismatch** between validation and loading functions.

### Phase 1: Gather Evidence

**Don't assume the hypothesis - get the actual error**:

```bash
# Run the failing scenario and capture FULL traceback
pixi run python scripts/run_e2e_experiment.py --tiers T0 --runs 1 2>&1 | tee error.log

# Resume multiple times to reproduce
# Resume 1: may work
# Resume 2: may work
# Resume 3: may work
# Resume 4: CRASH with traceback
```

**Critical**: Get the exact file path and line number from traceback, don't speculate.

### Phase 2: Ask User Clarifying Questions

- "When you see zero values, which files show zeros?" (console only / all report files / some files)
- "Do the run_result.json files have correct data?" (yes / no / haven't checked)

**What this reveals**:
- If `run_result.json` has correct data but reports show 0.000 → aggregation bug or crash before report gen
- If console shows 0.000 but files are correct → console reads stale data
- If all files show 0.000 → checkpoint/loading bug

### Phase 3: Trace File Path Mismatches

**Pattern**: Validation and loading must use the SAME file path.

```python
# Validation example:
def _has_valid_judge_result(run_dir: Path) -> bool:
    result_file = get_judge_result_file(run_dir)  # → judge/result.json
    return result_file.exists()

# Loading — BUG: hardcoded path differs from validation:
def _load_judge_result(judge_dir: Path) -> dict:
    with open(judge_dir / "judgment.json") as f:  # → judge/judgment.json (WRONG!)
        data = json.load(f)
```

**Fix pattern**:

```python
def _load_judge_result(judge_dir: Path) -> dict:
    """Load judge evaluation result from judge/result.json."""
    import json
    result_file = judge_dir / RESULT_FILE  # Use SAME constant as validation
    with open(result_file) as f:
        data = json.load(f)
    return data
```

### Phase 4: Verify the Fix

1. Run fresh experiment
2. Resume 4+ times (the scenario that previously crashed)
3. Verify NO FileNotFoundError
4. Verify reports show correct values

### Additional Fix: Judge Output Capture

While debugging, also added missing output files to judge directories:

```python
def _save_judge_logs(..., raw_stdout: str = "", raw_stderr: str = ""):
    # Save raw subprocess output (NEW)
    if raw_stdout:
        (judge_dir / "stdout.log").write_text(raw_stdout)
    if raw_stderr:
        (judge_dir / "stderr.log").write_text(raw_stderr)
```

### Key Learnings

1. **Get the actual error first** — don't hypothesize, get the traceback
2. **Ask user for file-level details** — which files have correct data? which show zeros?
3. **Check validation/loading consistency** — they must use the same file path
4. **Progressive failures suggest state mismatch** — works 1st time, fails Nth time
5. **File path bugs can masquerade as state bugs** — "checkpoint says complete but file missing" might be path mismatch
6. **Test resume multiple times** — bug might only appear on 3rd or 4th resume

---

## Pytest Fixture Patterns for Checkpoint/Resume Testing

*Absorbed from: resume-functionality-tests (2026-01-04, PR #142)*

### 15-Test Structure

```python
# tests/unit/e2e/test_resume.py (367 lines, 15 tests)

# Fixtures
@pytest.fixture
def experiment_config() -> ExperimentConfig: ...

@pytest.fixture
def tier_config() -> TierConfig: ...

@pytest.fixture
def checkpoint(tmp_path: Path) -> tuple[E2ECheckpoint, Path]: ...

# Test Classes (6)
class TestResumeAfterAgentCrash: ...       # 3 tests
class TestResumeAfterJudgeCrash: ...       # 3 tests
class TestResumeAfterSignal: ...           # 2 tests
class TestResumePartialTier: ...           # 2 tests
class TestResumeCompleteExperiment: ...    # 1 test
class TestResumeConfigMismatch: ...        # 1 test
class TestCheckpointOperations: ...        # 3 tests
```

### Core Fixture

```python
import pytest
from pathlib import Path
from scylla.e2e.checkpoint import E2ECheckpoint, save_checkpoint

@pytest.fixture
def checkpoint(tmp_path: Path) -> tuple[E2ECheckpoint, Path]:
    """Create a checkpoint and its save path."""
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = E2ECheckpoint(
        experiment_id="test-resume",
        experiment_dir=str(tmp_path),
        config_hash="test-hash",
        completed_runs={},
        started_at=datetime.now(UTC).isoformat(),
        last_updated_at=datetime.now(UTC).isoformat(),
        status="running",
    )
    save_checkpoint(checkpoint, checkpoint_path)
    return checkpoint, checkpoint_path
```

### Key Test Patterns

```python
class TestResumeAfterAgentCrash:
    def test_skip_completed_agent_result(self, tmp_path: Path) -> None:
        """Verify completed agent runs are not re-executed."""
        agent_result = {"exit_code": 0, "token_stats": {...}, "cost_usd": 0.01}
        (agent_dir / "result.json").write_text(json.dumps(agent_result))
        assert _has_valid_agent_result(run_dir) is True

    def test_invalid_agent_result_triggers_rerun(self, tmp_path: Path) -> None:
        invalid_result = {"exit_code": 0}  # Missing token_stats, cost_usd
        assert _has_valid_agent_result(run_dir) is False

    def test_corrupted_agent_json_triggers_rerun(self, tmp_path: Path) -> None:
        (agent_dir / "result.json").write_text("{ invalid json")
        assert _has_valid_agent_result(run_dir) is False

class TestResumeAfterJudgeCrash:
    def test_agent_preserved_after_judge_crash(self, tmp_path: Path) -> None:
        """Verify agent results are preserved when judge crashes."""
        assert _has_valid_agent_result(run_dir) is True
        assert _has_valid_judge_result(run_dir) is False  # No judge result yet

class TestResumeAfterSignal:
    def test_checkpoint_saved_with_interrupted_status(
        self, checkpoint: tuple[E2ECheckpoint, Path]
    ) -> None:
        cp, cp_path = checkpoint
        cp.status = "interrupted"
        save_checkpoint(cp, cp_path)
        loaded_data = json.loads(cp_path.read_text())
        assert loaded_data["status"] == "interrupted"

class TestResumePartialTier:
    def test_resume_skips_completed_subtests(
        self, checkpoint: tuple[E2ECheckpoint, Path]
    ) -> None:
        cp, _ = checkpoint
        cp.completed_runs = {
            "T0": {
                "T0_00": {1: "passed", 2: "passed"},  # Both runs complete
                "T0_01": {},  # Not started
            }
        }
        assert cp.is_run_completed("T0", "T0_00", 1) is True
        assert cp.is_run_completed("T0", "T0_01", 1) is False

class TestResumeConfigMismatch:
    def test_config_hash_mismatch_raises_error(
        self, checkpoint: tuple[E2ECheckpoint, Path], experiment_config: ExperimentConfig
    ) -> None:
        cp, _ = checkpoint
        cp.config_hash = "original-hash"
        modified_config = experiment_config
        modified_config.runs_per_subtest = 5  # Changed from 2
        assert validate_checkpoint_config(cp, modified_config) is False
```

### Checkpoint Data Format

```python
# Correct format for completed_runs
{
    "T0": {
        "T0_00": {1: "passed", 2: "passed"},
        "T0_01": {1: "failed"},
    }
}
# Status values: "passed", "failed", "agent_complete"
```

### Required Fields Validation

**Agent Result**: `exit_code` (int), `token_stats` (dict), `cost_usd` (float)

**Judge Result**: `score` (float), `passed` (bool), `grade` (str), `reasoning` (str)

### Key Testing Learnings

1. **Use Proper API**: Use `checkpoint.mark_run_completed()` not direct dict manipulation
2. **tmp_path Fixture**: Use pytest's `tmp_path` for isolated test directories
3. **Validation Functions**: Test validation functions separately from full execution
4. **Fixture Reuse**: Create checkpoint fixture for consistency across tests
5. **Test Both Paths**: Test valid and invalid cases for completeness

---

## TierState Naming Confusion and --until Stepping Bugs

*Absorbed from: until-resume-debugging (2026-02-25)*

### Critical: TierState Naming Confusion

**`TierState.SUBTESTS_RUNNING` does NOT mean "subtests are running."** It means "subtests have finished, now select best." The actual subtest execution happens in the action for `CONFIG_LOADED → SUBTESTS_RUNNING`. When resetting a tier for re-execution, always reset to `config_loaded`, never to `subtests_running`.

```
CONFIG_LOADED     → SUBTESTS_RUNNING   # action: run_tier_subtests_parallel() ← actual execution here
SUBTESTS_RUNNING  → SUBTESTS_COMPLETE  # action: select_best_subtest()
```

**Warning**: The linter has been observed reverting `config_loaded` back to `subtests_running` after this fix was committed. Always verify runner.py around the tier-reset logic after linter runs.

### Live E2E --until Stepping Command Sequence

```bash
BASE="pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-NNN --runs 1 --max-subtests 1 \
  --filter-subtest 00 --tiers T0 --results-dir /home/mvillmow/dryrun_step_testN \
  --skip-judge-validation -v --threads 1 --model haiku --judge-model haiku"

# Batch A: fresh start through all free pre-agent stages
$BASE --fresh --until replay_generated

# Step 7: agent execution (costs ~$0.01 haiku)
$BASE --until agent_complete

# Batch B: post-agent free stages through judge prompt
$BASE --until judge_prompt_built

# Step 11: judge execution (costs ~$0.01 haiku)
$BASE --until judge_complete

# Batch C: finalize, report, checkpoint, clean
$BASE --until worktree_cleaned

# Step 16: final completion (no --until)
$BASE
```

### Expected State Progression

| Step | run_state | subtest_state | Notes |
| ------ | ----------- | --------------- | ------- |
| Batch A | `replay_generated` | `runs_in_progress` | regression check |
| Step 7 | `agent_complete` | `runs_in_progress` | regression check |
| Batch B | `judge_prompt_built` | `runs_in_progress` | regression check |
| Step 11 | `judge_complete` | `runs_in_progress` | regression check |
| Batch C | `worktree_cleaned` | `aggregated` | terminal — subtest aggregates |
| Step 16 | `worktree_cleaned` | `aggregated` | no-op, already complete |

**Critical regression check**: subtest must stay `runs_in_progress` until `worktree_cleaned`.

### --until Bug 1: Tier Reset to Wrong State (runner.py STEP 4)

**Symptom**: "No sub-test results to select from" on second `--until` invocation.

**Root cause**: STEP 4 (`_initialize_or_resume_experiment`) reset tiers to `subtests_running` instead of `config_loaded`. Since `SUBTESTS_RUNNING` maps to the "select best subtest" action (not "run subtests"), `subtest_results` was empty when selection ran.

**Fix** (`scylla/e2e/runner.py`):
```python
# WRONG — subtests_running = "select best", not "run subtests"
self.checkpoint.tier_states[tier_id_str] = "subtests_running"

# CORRECT — config_loaded triggers action_config_loaded which runs subtests
self.checkpoint.tier_states[tier_id_str] = "config_loaded"
```
Also add `"subtests_running"` to the set of trigger states that get reset.

### --until Bug 2: Failed Run States Not Reset on Crash (runner.py STEP 3)

**Symptom**: After a crash leaves `run_states.T0.00.1=failed`, next resume skips the run (it's terminal) and aggregates with zero results.

**Root cause**: STEP 3 (experiment_state=failed handler) reset failed tiers → `pending` and failed subtests → `pending`, but did NOT reset failed run states.

**Fix** (`scylla/e2e/runner.py`):
```python
# Add after subtest reset in STEP 3:
for tier_id in self.checkpoint.run_states:
    for subtest_id in self.checkpoint.run_states[tier_id]:
        for run_id, run_state in self.checkpoint.run_states[tier_id][subtest_id].items():
            if run_state == "failed":
                self.checkpoint.run_states[tier_id][subtest_id][run_id] = "pending"
```

### --until Bug 3: RunContext Not Restored on Mid-Sequence Resume

**Symptom**: "agent_result must be set before finalize_run" or "judgment must be set before finalize_run" when resuming from `judge_complete`. Also: assert on `adapter_config is not None` when resuming from `replay_generated`.

**Fix 1** — lazy `adapter_config` reconstruction (`scylla/e2e/stages.py`):
```python
# In stage_execute_agent, replace assert with:
if adapter_config is None:
    from scylla.adapters.base import AdapterConfig
    adapter_config = AdapterConfig(
        model=ctx.config.models[0],
        prompt_file=ctx.run_dir / "task_prompt.md",
        workspace=ctx.workspace,
        output_dir=agent_dir,
        timeout=ctx.config.timeout_seconds,
    )
    ctx.adapter_config = adapter_config
```

**Fix 2** — `restore_run_context()` function (`scylla/e2e/stages.py`):
```python
def restore_run_context(ctx: RunContext, current_state: RunState) -> None:
    """Load persisted agent_result and judgment from disk when resuming mid-sequence."""
    from scylla.e2e.agent_runner import _has_valid_agent_result, _load_agent_result
    from scylla.e2e.judge_runner import _load_judge_result

    agent_dir = get_agent_dir(ctx.run_dir)
    judge_dir = get_judge_dir(ctx.run_dir)

    _NEEDS_AGENT_RESULT = {DIFF_CAPTURED, JUDGE_PIPELINE_RUN, JUDGE_PROMPT_BUILT,
                           JUDGE_COMPLETE, RUN_FINALIZED, REPORT_WRITTEN,
                           CHECKPOINTED, WORKTREE_CLEANED}
    _NEEDS_JUDGMENT = {JUDGE_COMPLETE, RUN_FINALIZED, REPORT_WRITTEN,
                       CHECKPOINTED, WORKTREE_CLEANED}

    if ctx.agent_result is None and current_state in _NEEDS_AGENT_RESULT:
        if _has_valid_agent_result(ctx.run_dir):
            ctx.agent_result = _load_agent_result(agent_dir)
            ctx.agent_ran = False

    if ctx.judgment is None and current_state in _NEEDS_JUDGMENT:
        judge_result_file = judge_dir / "result.json"
        if judge_result_file.exists():
            ctx.judgment = _load_judge_result(judge_dir)
```

**Fix 3** — call `restore_run_context` after RunContext construction (`scylla/e2e/subtest_executor.py`):
```python
# After ctx = RunContext(...), before build_actions_dict:
from scylla.e2e.stages import restore_run_context
from scylla.e2e.models import RunState as _RS
if sm:
    _current = sm.get_state(tier_id.value, subtest.id, run_num)
    if _current != _RS.PENDING:
        restore_run_context(ctx, _current)
```

### Key Files for --until Debugging

| File | Role |
| ------ | ------ |
| `scylla/e2e/runner.py` | STEP 3 (failed reset) and STEP 4 (incomplete run re-entry) |
| `scylla/e2e/stages.py` | `stage_execute_agent`, `stage_finalize_run`, `restore_run_context()` |
| `scylla/e2e/subtest_executor.py` | RunContext creation + `restore_run_context` call |
| `scylla/e2e/tier_state_machine.py` | TierState enum and transition registry |
| `scylla/e2e/state_machine.py` | RunState enum and `advance_to_completion()` |
| `tests/unit/e2e/test_runner.py` | `TestInitializeOrResumeExperimentFailedReset` class |

### Notes

- Judge prompt is empty when `--skip-judge-validation` is used with haiku and the agent produces no output — this is expected; the system falls back to zero-score consensus and continues normally.
- `worktree_cleaned` is the last RunState; when `--until worktree_cleaned` is used, the run is terminal so the subtest correctly advances to `aggregated` (not `runs_in_progress`).
