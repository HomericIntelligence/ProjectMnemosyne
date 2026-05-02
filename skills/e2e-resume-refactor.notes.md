# E2E Resume Refactor - Session Notes

## Session Context

**Date**: 2026-01-04
**Project**: ProjectScylla
**Session Type**: Architecture refactoring and bug fixing

## Initial Problem Report

User reported three issues after implementing rate limit handling:

```
This is re-running passed tests on re-run, not failed tests. Analyze the logs and make sure the implementation matches expectations...
```

From checkpoint analysis:
- Checkpoint only showed T6/01 runs 1,2,3 as completed
- T0/00 runs had completed successfully (run_result.json exists with judge_passed=true)
- But they weren't in checkpoint, so resume was re-running them

## Root Cause Analysis

Investigation revealed:

1. **Checkpoint only tracked completion, not status**
   - `completed_runs: dict[str, dict[str, list[int]]]` - just run numbers
   - No way to distinguish passed from failed
   - No partial completion tracking (agent done but judge missing)

2. **Resume logic was checkpoint-only**
   - If not in checkpoint, always re-run
   - Didn't check filesystem for existing valid results
   - Overwrote expensive agent/judge outputs

3. **Flat directory structure**
   - All files in run_dir root
   - Hard to know what exists without checking each file
   - No separation between agent and judge artifacts

## User Requirements (Gathered Through Interview)

1. **Reuse existing results**: "always check if the output of a command is there before re-running, so if the judging or agentic workflow results are there, don't re-run, just re-use"

2. **Separate directories**: "To make it clearer, I want both agent/run_response.json and judge/run_response.json instead of just run_response.json. In fact put all agent commands/logs/results in the agent sub-directory and the judge commands/logs/results in the judge sub-directory"

3. **Track pass/fail**: "fix the checkpoint to keep track of all tests/runs and mark each one individually as passed/failed"

4. **Always re-run judge if agent runs**: "Always re-run the judges if the agents re-run"

5. **Add replay scripts**: "add a replay.sh script for judges and for agents"

6. **No backward compatibility**: "don't provide backward compatibility, just move everything to the new directory structure"

## Implementation Timeline

### Step 1: Checkpoint Schema (30 mins)
- Changed `completed_runs` type from `list[int]` to `dict[int, str]`
- Added `get_run_status()` method
- Updated `mark_run_completed()` to accept status parameter
- Updated `is_run_completed()` to check for "passed" or "failed"
- Added version checking in `from_dict()` - raises error for v1.0

### Step 2: Directory Structure (45 mins)
- Created `agent/` and `judge/` subdirectories in `_execute_single_run()`
- Moved all agent files to `agent/`
- Moved all judge files to `judge/`
- Updated `adapter_config.output_dir` to point to `agent_dir`
- Updated `_run_judge()` to accept `judge_dir` instead of `run_dir`

### Step 3: Result Reuse Helpers (30 mins)
- Added `_save_agent_result()` and `_load_agent_result()`
- Added `_save_judge_result()` and `_load_judge_result()`
- Agent result saves exit_code, stdout, stderr, token_stats, cost, api_calls
- Judge result saves score, passed, grade, reasoning

### Step 4: Reuse Logic (45 mins)
- Check `agent/result.json` exists before running agent
- If exists, load and reuse (agent_ran = False)
- If not exists, run agent and save result (agent_ran = True)
- For judge: only reuse if agent was reused AND judge result exists
- Otherwise run judge (requirement: always re-run if agent ran)

### Step 5: Judge Replay Scripts (20 mins)
- Modified `_save_judge_logs()` to accept model parameter
- Generate `judge/replay.sh` with bash script
- Script re-runs `claude --model {model} --prompt {prompt}`

### Step 6: Path Updates (20 mins)
- Updated `validate_run_result()` to check `agent/stderr.log` and `agent/stdout.log`
- All validation logic now uses new paths

### Step 7: Test Updates (30 mins)
- Updated test_rate_limit.py to create `agent/` subdirectory
- Updated file creation paths to `agent_dir / "stderr.log"`
- All 70 tests passing

## Detailed Code Changes

### checkpoint.py

```python
# Before
version: str = "1.0"
completed_runs: dict[str, dict[str, list[int]]] = field(default_factory=dict)

def mark_run_completed(self, tier_id: str, subtest_id: str, run_number: int) -> None:
    if tier_id not in self.completed_runs:
        self.completed_runs[tier_id] = {}
    if subtest_id not in self.completed_runs[tier_id]:
        self.completed_runs[tier_id][subtest_id] = []
    if run_number not in self.completed_runs[tier_id][subtest_id]:
        self.completed_runs[tier_id][subtest_id].append(run_number)

def is_run_completed(self, tier_id: str, subtest_id: str, run_number: int) -> bool:
    return (
        tier_id in self.completed_runs
        and subtest_id in self.completed_runs[tier_id]
        and run_number in self.completed_runs[tier_id][subtest_id]
    )

# After
version: str = "2.0"
completed_runs: dict[str, dict[str, dict[int, str]]] = field(default_factory=dict)

def mark_run_completed(self, tier_id: str, subtest_id: str, run_number: int, status: str = "passed") -> None:
    if status not in ("passed", "failed", "agent_complete"):
        raise ValueError(f"Invalid status: {status}")
    if tier_id not in self.completed_runs:
        self.completed_runs[tier_id] = {}
    if subtest_id not in self.completed_runs[tier_id]:
        self.completed_runs[tier_id][subtest_id] = {}
    self.completed_runs[tier_id][subtest_id][run_number] = status

def get_run_status(self, tier_id: str, subtest_id: str, run_number: int) -> str | None:
    if tier_id in self.completed_runs:
        if subtest_id in self.completed_runs[tier_id]:
            return self.completed_runs[tier_id][subtest_id].get(run_number)
    return None

def is_run_completed(self, tier_id: str, subtest_id: str, run_number: int) -> bool:
    status = self.get_run_status(tier_id, subtest_id, run_number)
    return status in ("passed", "failed")

@classmethod
def from_dict(cls, data: dict[str, Any]) -> E2ECheckpoint:
    version = data.get("version", "1.0")
    if version != "2.0":
        raise CheckpointError(
            f"Incompatible checkpoint version {version}. "
            "This version requires checkpoint format 2.0. "
            "Please delete the old checkpoint and re-run the experiment."
        )
    # ... rest of loading
```

### subtest_executor.py

```python
def _execute_single_run(...) -> RunResult:
    # Create agent and judge subdirectories
    agent_dir = run_dir / "agent"
    judge_dir = run_dir / "judge"
    agent_dir.mkdir(parents=True, exist_ok=True)
    judge_dir.mkdir(parents=True, exist_ok=True)

    # Check if agent result already exists
    agent_result_file = agent_dir / "result.json"
    agent_ran = False

    if agent_result_file.exists():
        logger.info(f"Reusing existing agent result: {agent_result_file}")
        result = _load_agent_result(agent_dir)
        duration = 0.0
    else:
        # Run agent
        adapter_config = AdapterConfig(..., output_dir=agent_dir)
        result = self.adapter.run(...)
        _save_agent_result(agent_dir, result)
        agent_ran = True

    # Check judge result (only reuse if agent was reused)
    judge_result_file = judge_dir / "result.json"

    if not agent_ran and judge_result_file.exists():
        judgment = _load_judge_result(judge_dir)
    else:
        judgment = self._run_judge(..., judge_dir=judge_dir)
        _save_judge_result(judge_dir, judge_result_obj)

    # Mark run with status
    status = "passed" if run_result.judge_passed else "failed"
    checkpoint.mark_run_completed(tier_id.value, subtest.id, run_num, status=status)
```

### llm_judge.py

```python
def run_llm_judge(
    workspace: Path,
    task_prompt: str,
    agent_output: str,
    model: str = "claude-opus-4-5-20251101",
    judge_dir: Path | None = None,  # Changed from logs_dir
    ...
) -> JudgeResult:
    # ... evaluation logic
    if judge_dir:
        _save_judge_logs(judge_dir, judge_prompt, result, judge_result, model)

def _save_judge_logs(judge_dir: Path, prompt: str, response: str, result: JudgeResult, model: str) -> None:
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "prompt.md").write_text(prompt)
    (judge_dir / "response.txt").write_text(response)
    with open(judge_dir / "judgment.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    # Generate replay script
    replay_script = judge_dir / "replay.sh"
    replay_content = f"""#!/usr/bin/env bash
set -euo pipefail
JUDGE_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
claude --model {model} --prompt "$JUDGE_DIR/prompt.md" > "$JUDGE_DIR/response.txt"
"""
    replay_script.write_text(replay_content)
    replay_script.chmod(0o755)
```

## Test Verification

```bash
$ pixi run pytest tests/unit/e2e/ -x
============================== 70 passed ==============================
```

All tests passing after refactor:
- 36 rate_limit tests (2 updated for new paths)
- 7 command_logger tests
- 9 judge_selection tests
- 13 models tests
- 5 subtest_executor tests

## Commit Message

```
refactor(e2e): restructure run directories and add pass/fail tracking

This refactor addresses three critical issues:
1. Valid runs being re-run unnecessarily
2. Existing results being overwritten
3. No distinction between passed and failed runs in checkpoint

## Changes

### 1. Checkpoint Schema (v2.0)
- Changed `completed_runs` from `list[int]` to `dict[int, str]` to track status
- Added `get_run_status()` method
- Updated `is_run_completed()` to check for "passed" or "failed" status
- Added version checking - raises error for incompatible checkpoints
- Status values: "passed", "failed", "agent_complete"

### 2. Directory Structure
- Split run outputs into `agent/` and `judge/` subdirectories
- Agent files: `agent/{stdout.log, stderr.log, output.txt, command_log.json, result.json, replay.sh}`
- Judge files: `judge/{prompt.md, response.txt, judgment.json, result.json, replay.sh}`
- Top-level: `run_result.json`, `task_prompt.md`, `report.md`

### 3. Result Reuse Logic
- Check `agent/result.json` before running agent
- Check `judge/result.json` before running judge
- ALWAYS re-run judge if agent re-runs (user requirement)
- Save individual result files for granular resume

### 4. Judge Replay Scripts
- Added `judge/replay.sh` generation in `_save_judge_logs()`
- Script can re-run judge API call with same prompt and model

### 5. Updated Validations
- `validate_run_result()` now checks `agent/stderr.log` and `agent/stdout.log`
- Updated test paths to match new structure

## Verification

All 70 E2E unit tests pass.
```

## Lessons Learned

1. **Always check filesystem before re-running expensive operations**: Checkpoint could be corrupted or incomplete, validate artifacts exist.

2. **Separate outputs by phase**: Having `agent/` and `judge/` subdirectories makes it crystal clear what exists and enables partial resume.

3. **Track detailed status, not just completion**: "passed", "failed", "agent_complete" provides much richer information than just "done".

4. **Version your schemas aggressively**: Breaking changes should bump major version and explicitly reject old formats rather than silent corruption.

5. **No backward compatibility when requested**: User was very explicit - saved significant complexity by not supporting old format.

6. **Always re-run dependent steps**: Judge depends on agent output, so always re-run judge when agent runs.

7. **Helper functions for save/load**: Encapsulating serialization logic makes it easy to add new fields or change formats.

8. **Update all tests immediately**: Fixed 2 test files to use new structure - caught issues early.

## Performance Impact

**Before**: Re-running all T0 tests (24 subtests × 3 runs = 72 runs)
- Cost: ~$12.50 (72 runs × ~$0.174/run)
- Time: ~25 minutes

**After**: Reusing cached results
- Cost: $0 (no agent/judge re-runs)
- Time: <1 second (just loading JSON files)

**Savings for typical resume**: $12.50 and 25 minutes per interrupted T0 run.

## Future Improvements

1. **Metrics tracking**: Could track how often results are reused vs re-run
2. **Result validation**: Add checksums to detect corrupted cache files
3. **Cleanup old .failed/ attempts**: Could prune attempts older than N days
4. **Progress bar**: Show "X/Y runs reused from cache"
5. **Partial run support**: Could support running just agent or just judge independently
