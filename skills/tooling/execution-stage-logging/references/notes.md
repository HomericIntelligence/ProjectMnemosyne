# Execution Stage Logging - Implementation Notes

## Context

ProjectScylla E2E experiments showed:
- 27-second gaps in logs between agent start and completion
- Unclear which workers were running vs stuck
- Users thought process had hung
- No timing data per stage

Example from results.log:
```
Line 18-19: Agent starts at 08:33:49
Line 20: Next tier starts at 08:34:16 (27 seconds gap!)
```

## Solution

Added structured stage logging with timing:

1. **ExecutionStage enum**:
   ```python
   class ExecutionStage(str, Enum):
       WORKTREE = "WORKTREE"
       AGENT = "AGENT"
       JUDGE = "JUDGE"
       CLEANUP = "CLEANUP"
       COMPLETE = "COMPLETE"
   ```

2. **_stage_log() helper**:
   ```python
   def _stage_log(
       subtest_id: str,
       stage: ExecutionStage,
       status: str,
       elapsed: float | None = None
   ) -> None:
       timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
       elapsed_str = f" ({elapsed:.1f}s)" if elapsed is not None else ""
       logger.info(f"{timestamp} [{subtest_id}] Stage: {stage.value} - {status}{elapsed_str}")
   ```

3. **Stage markers in _execute_single_run()**:
   - AGENT Starting / Complete (with duration)
   - JUDGE Starting / Complete (with duration)
   - COMPLETE All stages complete (with total time)

## Example Output

```
2026-01-04T19:30:15.234Z [T0_00] Stage: AGENT - Starting
2026-01-04T19:30:28.456Z [T0_00] Stage: AGENT - Complete (13.2s)
2026-01-04T19:30:29.123Z [T0_00] Stage: JUDGE - Starting
2026-01-04T19:30:35.789Z [T0_00] Stage: JUDGE - Complete (6.7s)
2026-01-04T19:30:35.890Z [T0_00] Stage: COMPLETE - All stages complete (20.7s)
```

## Files Changed

- `src/scylla/e2e/subtest_executor.py`:
  - Added ExecutionStage enum (11 lines)
  - Added _stage_log() function (14 lines)
  - Added stage markers in _execute_single_run() (5 locations)
  - Added timing tracking (start_time, agent_start, judge_start)

## Benefits

1. **Visibility**: Always know which stage each worker is in
2. **Performance Data**: Timing identifies slow stages
3. **Debugging**: Easy to spot stuck workers
4. **Foundation for #129**: Progress indicators can parse these logs

## PR Details

- **Branch**: `131-worker-stage-reporting`
- **Files Changed**: 1 modified
- **Lines**: +48, -2
- **Status**: Awaiting merge
