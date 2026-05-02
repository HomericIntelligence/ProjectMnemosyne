# E2E Agent/Judge Timing - Implementation Notes

## Session Context

**Date**: 2026-01-04
**Project**: ProjectScylla
**Branch**: 134-resume-tests
**PR**: #143

## User Request

> I want the time it takes to run a stage/test/run added to the reports/logs

After clarification:

> I want the time it takes to run agents/judges and not per-stage, so that it is possible to rank equivalently produced results by time taken as a tiebreaker

## Skills Registry Research

Used `/advise` to search ProjectMnemosyne for prior learnings:

### Found Skills

1. **execution-stage-logging** (tooling) - Perfect match for stage-by-stage timing
   - Pattern: `_stage_log(worker_id, stage, status, elapsed)`
   - Format: `[worker_id] Stage: STAGE - status (timing)`
   - Benefits: Visibility, performance data, debugging

2. **e2e-resume-refactor** (architecture) - Checkpoint with timing
   - Duration tracking in checkpoint for resume
   - Separate agent/judge directories

3. **e2e-checkpoint-resume** (evaluation) - Duration in experiment runs
   - `duration_seconds` in RunResult for total timing

### Key Finding from execution-stage-logging

**What Worked**:
- Track overall timing AND per-stage timing
- Log both start and complete events
- Include elapsed time in completion logs
- Use structured format: `timestamp [id] Stage: NAME - status (Xs)`

**What Failed**:
- Logging only start OR only completion (can't tell duration)
- Progress bars (don't work with parallel workers)
- Polling worker state (race conditions)

## Implementation Steps

### 1. Model Changes

**File**: `src/scylla/e2e/models.py:184-230`

Added fields to RunResult:
```python
agent_duration_seconds: float
judge_duration_seconds: float
```

Updated `to_dict()` to serialize both fields.

### 2. Execution Tracking

**File**: `src/scylla/e2e/subtest_executor.py`

**Agent timing** (lines 710-730):
```python
agent_start = datetime.now(UTC)
result = self.adapter.run(...)
duration = (datetime.now(UTC) - agent_start).total_seconds()
```

**Judge timing** (lines 768-781):
```python
if not agent_ran and _has_valid_judge_result(run_dir):
    judgment = _load_judge_result(judge_dir)
    judge_duration = 0.0  # Not tracked for reused
else:
    judge_start = datetime.now(UTC)
    judgment = self._run_judge(...)
    judge_duration = (datetime.now(UTC) - judge_start).total_seconds()
```

**RunResult creation** (lines 818-834):
```python
run_result = RunResult(
    duration_seconds=duration + judge_duration,
    agent_duration_seconds=duration,
    judge_duration_seconds=judge_duration,
    ...
)
```

### 3. Checkpoint Resume

**File**: `src/scylla/e2e/subtest_executor.py:541-562`

Added loading of timing fields:
```python
run_result = RunResult(
    duration_seconds=report_data["duration_seconds"],
    agent_duration_seconds=report_data["agent_duration_seconds"],
    judge_duration_seconds=report_data["judge_duration_seconds"],
    ...
)
```

### 4. Report Generation

**File**: `src/scylla/e2e/run_report.py`

**Function signature** (lines 25-45):
```python
def generate_run_report(
    duration_seconds: float,
    agent_duration_seconds: float | None = None,
    judge_duration_seconds: float | None = None,
    ...
)
```

**Report output** (lines 94-121):
```python
lines = [
    f"| Duration (Total) | {duration_seconds:.2f}s |",
]

if agent_duration_seconds is not None and judge_duration_seconds is not None:
    lines.extend([
        f"| - Agent | {agent_duration_seconds:.2f}s |",
        f"| - Judge | {judge_duration_seconds:.2f}s |",
    ])
```

**Updated save_run_report()** (lines 345-397):
Added parameters and passed through to `generate_run_report()`.

**Updated call sites** (subtest_executor.py:845-866):
```python
save_run_report(
    duration_seconds=duration + judge_duration,
    agent_duration_seconds=duration,
    judge_duration_seconds=judge_duration,
    ...
)
```

### 5. Tests

**File**: `tests/unit/e2e/test_models.py:97-129`

Updated `TestRunResult::test_to_dict`:
```python
result = RunResult(
    duration_seconds=15.5,
    agent_duration_seconds=12.0,
    judge_duration_seconds=3.5,
    ...
)

assert d["duration_seconds"] == 15.5
assert d["agent_duration_seconds"] == 12.0
assert d["judge_duration_seconds"] == 3.5
```

## Design Decisions

### 1. Required vs Optional Fields

**Decision**: Made fields required (not `float | None`)

**Rationale**:
- User explicitly said "ignore old formats, don't need to worry about compatibility"
- Clean break prevents null-handling complexity
- All new runs will have timing data

### 2. Cached Result Timing

**Decision**: Set `duration = 0.0` for cached results

**Rationale**:
- Consistent with existing pattern for cached agent results
- Clear semantics: 0.0 = "no execution time because cached"
- Prevents misleading timing data in reports

### 3. Total Duration Calculation

**Decision**: `duration_seconds = agent_duration + judge_duration`

**Rationale**:
- Maintains backward compatibility for code expecting single duration field
- Easy to verify: total should equal sum of parts
- Enables both aggregate and component-level analysis

### 4. Optional in Reports

**Decision**: Made timing breakdown optional in `generate_run_report()`

**Rationale**:
- Allows gradual rollout if needed
- Graceful degradation if timing data missing
- Doesn't break existing report consumers

## Testing

### Test Execution

```bash
pixi run pytest tests/unit/e2e/ -v
```

**Results**: ✅ All 97 tests passing

### Failed Test (Fixed)

**Initial failure**:
```
TypeError: RunResult.__init__() missing 2 required positional arguments:
'agent_duration_seconds' and 'judge_duration_seconds'
```

**File**: `tests/unit/e2e/test_models.py:101`

**Fix**: Added timing fields to test RunResult instantiation

## Commit Message

```
feat(e2e): add separate agent and judge timing to RunResult

Adds agent_duration_seconds and judge_duration_seconds fields to track
execution time separately for agents and judges. This enables using
timing as a tiebreaker metric when ranking equivalent results.

Changes:
- Add agent_duration_seconds and judge_duration_seconds to RunResult model
- Update duration_seconds to be total (agent + judge)
- Update reports to show timing breakdown in Summary table
- Update checkpoint resume to load timing fields
- Set judge_duration=0.0 when reusing cached results
- Update tests to include new timing fields
```

## Example Output

### run_result.json

```json
{
  "run_number": 1,
  "duration_seconds": 23.45,
  "agent_duration_seconds": 18.20,
  "judge_duration_seconds": 5.25,
  "judge_score": 0.85,
  ...
}
```

### report.md

```markdown
| Metric | Value |
|--------|-------|
| Score | 0.850 |
| Grade | B |
| Status | ✓ PASS |
| Cost | $0.1234 |
| Duration (Total) | 23.45s |
| - Agent          | 18.20s |
| - Judge          | 5.25s  |
| Tokens | 12,345 in / 1,234 out |
```

## Use Case: Tiebreaker Ranking

When comparing results with identical scores:

```python
# Both have score=0.85
run_1 = {"score": 0.85, "duration_seconds": 18.5}
run_2 = {"score": 0.85, "duration_seconds": 23.2}

# Prefer run_1 (faster)
winner = min([run_1, run_2], key=lambda r: (1-r["score"], r["duration_seconds"]))
```

Can also use component timing for analysis:
```python
# Find slowest component
if run.agent_duration_seconds > run.judge_duration_seconds:
    print("Agent is the bottleneck")
else:
    print("Judge is the bottleneck")
```

## Related PRs

- **PR #143**: This implementation
- **PR #139**: Execution stage logging (execution-stage-logging skill)
- **PR #126**: E2E checkpoint/resume (e2e-checkpoint-resume skill)
