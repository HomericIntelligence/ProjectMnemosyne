# E2E Resume Refactor: Directory Structure & Checkpoint v2.0

| Aspect | Details |
|--------|---------|
| **Date** | 2026-01-04 |
| **Objective** | Fix E2E test resume behavior to avoid re-running completed tests and track pass/fail status |
| **Outcome** | ✅ Success - All 70 E2E tests passing |
| **Root Cause** | Checkpoint only tracked "completed" status, no filesystem awareness, flat directory structure |
| **Solution** | Checkpoint v2.0 with pass/fail tracking, agent/judge subdirectories, result reuse logic |

## Problem Statement

After implementing rate limit handling, the E2E test framework had three critical issues:

1. **Valid runs re-run on resume**: Runs that completed successfully weren't in checkpoint (only T6/01 marked), so resume would re-run everything
2. **Results overwritten**: Existing agent/judge outputs would get overwritten instead of reused
3. **No pass/fail distinction**: Checkpoint used `list[int]` so couldn't track whether runs passed or failed

## When to Use This Skill

Use this pattern when:
- Building test frameworks with long-running tests that need resume capability
- Implementing checkpoint systems that need to track detailed status (not just "done")
- Separating outputs from different execution phases (agent vs judge, build vs test, etc.)
- Avoiding expensive re-computation by reusing valid cached results
- Need to validate cached results before trusting them

## Verified Workflow

### Phase 1: Checkpoint Schema Upgrade

**File**: `src/scylla/e2e/checkpoint.py`

```python
# OLD (v1.0): Only tracks which runs completed
completed_runs: dict[str, dict[str, list[int]]]  # tier -> subtest -> [run_nums]

# NEW (v2.0): Tracks status of each run
completed_runs: dict[str, dict[str, dict[int, str]]]  # tier -> subtest -> {run_num: status}
# status: "passed", "failed", "agent_complete"
```

**Key Changes**:
1. Bumped version from "1.0" to "2.0"
2. Added `get_run_status(tier_id, subtest_id, run_num) -> str | None`
3. Updated `mark_run_completed()` to accept `status: str` parameter
4. Updated `is_run_completed()` to only return `True` for "passed" or "failed" (not "agent_complete")
5. Added version checking in `from_dict()` that raises `CheckpointError` for v1.0 checkpoints

**No Backward Compatibility**: User explicitly requested no fallback to old paths/formats.

### Phase 2: Directory Restructure

**Old Structure**:
```
run_01/
├── stdout.log, stderr.log          # Agent output
├── output.txt                       # Agent stdout
├── command_log.json                 # Agent commands
├── judge_prompt.md                  # Judge input
├── judge_response.txt               # Judge output
├── judgment.json                    # Judge result
├── run_result.json                  # Combined result
└── report.md, report.json           # Reports
```

**New Structure**:
```
run_01/
├── agent/
│   ├── stdout.log, stderr.log
│   ├── output.txt
│   ├── command_log.json
│   ├── result.json                  # NEW: Agent-specific result
│   └── replay.sh                    # Agent replay script (already existed)
├── judge/
│   ├── prompt.md                    # Renamed from judge_prompt.md
│   ├── response.txt                 # Renamed from judge_response.txt
│   ├── result.json                  # NEW: Judge-specific result
│   ├── judgment.json                # Full judgment with criteria
│   └── replay.sh                    # NEW: Judge replay script
├── run_result.json                  # Combined result (top-level)
├── task_prompt.md                   # Task given to agent
└── report.md, report.json           # Per-run reports
```

**Implementation** (`src/scylla/e2e/subtest_executor.py:_execute_single_run()`):
```python
# Create subdirectories
agent_dir = run_dir / "agent"
judge_dir = run_dir / "judge"
agent_dir.mkdir(parents=True, exist_ok=True)
judge_dir.mkdir(parents=True, exist_ok=True)

# Update adapter config
adapter_config = AdapterConfig(
    output_dir=agent_dir,  # Changed from run_dir
    ...
)

# Update judge call
judgment = self._run_judge(
    judge_dir=judge_dir,  # Changed from run_dir
    ...
)
```

### Phase 3: Result Reuse Logic

**Helper Functions** (added to `subtest_executor.py`):

```python
def _save_agent_result(agent_dir: Path, result: AdapterResult) -> None:
    """Save agent execution result to agent/result.json."""
    result_data = {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "token_stats": result.token_stats.to_dict(),
        "cost_usd": result.cost_usd,
        "api_calls": result.api_calls,
    }
    with open(agent_dir / "result.json", "w") as f:
        json.dump(result_data, f, indent=2)

def _load_agent_result(agent_dir: Path) -> AdapterResult:
    """Load agent result from agent/result.json."""
    # Reconstruct AdapterResult from saved JSON
    ...

def _save_judge_result(judge_dir: Path, result: JudgeResult) -> None:
    """Save judge result to judge/result.json."""
    ...

def _load_judge_result(judge_dir: Path) -> dict:
    """Load judge result from judge/judgment.json."""
    # Load full judgment with criteria_scores
    ...
```

**Reuse Logic in `_execute_single_run()`**:

```python
# Check if agent result already exists
agent_result_file = agent_dir / "result.json"
agent_ran = False

if agent_result_file.exists():
    # Reuse existing agent result
    logger.info(f"Reusing existing agent result: {agent_result_file}")
    result = _load_agent_result(agent_dir)
    duration = 0.0
else:
    # Run agent and save result
    result = self.adapter.run(...)
    _save_agent_result(agent_dir, result)
    agent_ran = True

# CRITICAL REQUIREMENT: Always re-run judge if agent ran
judge_result_file = judge_dir / "result.json"

if not agent_ran and judge_result_file.exists():
    # Only reuse if agent was also reused
    judgment = _load_judge_result(judge_dir)
else:
    # Run judge (either agent ran, or judge missing)
    judgment = self._run_judge(...)
    _save_judge_result(judge_dir, judge_result_obj)
```

**User Requirement**: "Always re-run the judges if the agents re-run"

### Phase 4: Judge Replay Scripts

**File**: `src/scylla/e2e/llm_judge.py:_save_judge_logs()`

```python
def _save_judge_logs(judge_dir: Path, prompt: str, response: str, result: JudgeResult, model: str) -> None:
    # Save prompt, response, judgment.json...

    # Generate replay script
    replay_script = judge_dir / "replay.sh"
    replay_content = f"""#!/usr/bin/env bash
# Replay judge evaluation
set -euo pipefail

JUDGE_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

# Re-run Claude CLI with same prompt and model
claude \\
  --model {model} \\
  --prompt "$JUDGE_DIR/prompt.md" \\
  > "$JUDGE_DIR/response.txt"

echo "Judge response saved to $JUDGE_DIR/response.txt"
"""
    replay_script.write_text(replay_content)
    replay_script.chmod(0o755)
```

### Phase 5: Update Validations

**File**: `src/scylla/e2e/rate_limit.py:validate_run_result()`

```python
def validate_run_result(run_dir: Path) -> tuple[bool, str | None]:
    # OLD paths
    # stderr_file = run_dir / "stderr.log"
    # stdout_file = run_dir / "stdout.log"

    # NEW paths
    agent_dir = run_dir / "agent"
    stderr_file = agent_dir / "stderr.log"
    stdout_file = agent_dir / "stdout.log"

    # Check agent stderr/stdout for rate limit patterns
    ...
```

### Phase 6: Update Tests

**Pattern**: Update all test file paths to use new structure

```python
# Before
run_dir.mkdir()
(run_dir / "stderr.log").write_text("...")

# After
run_dir.mkdir()
agent_dir = run_dir / "agent"
agent_dir.mkdir(parents=True)
(agent_dir / "stderr.log").write_text("...")
```

## Failed Attempts

### Attempt 1: Backward Compatibility

**What was tried**: Initially considered checking both old and new paths during transition period.

**Why it failed**: User explicitly stated "don't provide backward compatibility, just move everything to the new directory structure". Simplified implementation by removing all compatibility checks.

**Lesson**: When user gives explicit architectural direction, follow it exactly rather than second-guessing.

### Attempt 2: Validating Checkpointed Runs Without Filesystem Check

**What was tried**: Resume logic initially only checked `checkpoint.is_run_completed()` to skip runs.

**Why it failed**: Checkpoint could be corrupted or incomplete (T0/00 completed but not in checkpoint). Need to validate filesystem artifacts exist and are valid.

**Solution**: Keep the validation logic that checks `run_result.json` exists and validates it, but now also check for partial completion (agent done but judge missing).

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **No backward compatibility** | User requirement - clean break from v1.0 |
| **Separate agent/judge directories** | Enables granular resume (run only judge if agent cached) |
| **dict[int, str] for status** | Can track "passed", "failed", or "agent_complete" |
| **Always re-run judge if agent runs** | User requirement - judge depends on agent output |
| **Version check raises error** | Forces users to delete old checkpoints rather than silent corruption |

## Implementation Checklist

When implementing similar refactors:

- [ ] Bump schema version and add version checking
- [ ] Update all file path references (search for old patterns)
- [ ] Create helper functions for save/load operations
- [ ] Update validation functions to check new paths
- [ ] Update ALL tests to use new structure
- [ ] Add comprehensive logging for reuse decisions
- [ ] Document the new structure clearly
- [ ] Consider partial completion states
- [ ] Verify no silent failures from missing files

## Results & Parameters

**Files Modified**:
1. `src/scylla/e2e/checkpoint.py` - Schema v2.0 (125 lines changed)
2. `src/scylla/e2e/subtest_executor.py` - Directory structure, reuse logic (193 lines changed)
3. `src/scylla/e2e/llm_judge.py` - Judge directory, replay script (48 lines changed)
4. `src/scylla/e2e/rate_limit.py` - Path updates (14 lines changed)
5. `tests/unit/e2e/test_rate_limit.py` - Test updates (10 lines changed)

**Test Results**:
- All 70 E2E unit tests passing
- No regression in existing functionality

**Commit**: `refactor(e2e): restructure run directories and add pass/fail tracking`

## References

- Original issue: "This is re-running passed tests on re-run, not failed tests"
- User requirements:
  1. Reuse existing results if they exist
  2. Separate agent/ and judge/ directories
  3. Track pass/fail status in checkpoint
  4. Add replay scripts for both agent and judge
  5. Always re-run judge if agent re-runs
  6. No backward compatibility
