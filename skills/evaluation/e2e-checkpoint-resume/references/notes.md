# E2E Checkpoint/Resume Implementation Notes

## Session Context

**Date**: 2026-01-03
**Project**: ProjectScylla
**Session Type**: Feature implementation
**Duration**: ~2 hours

## Initial Request

User wanted to enable E2E testing to pause when rate limits are hit and restart when the time limit expires, allowing overnight test runs without manual intervention. The subtest/test/run that was running should be restarted on resume.

## Planning Phase

Started with `/advise` command to search skills registry for relevant patterns:
- Found skills about rate limiting, retry logic, and E2E testing
- No exact match for checkpoint/resume with rate limit handling

Entered plan mode and conducted detailed interview to clarify requirements:

### Requirements Gathered

| Decision Point | Options Considered | Final Choice | Rationale |
|----------------|-------------------|--------------|-----------|
| Resume Granularity | Tier/Subtest/Run-level | Run-level | Most comprehensive, smallest unit of work |
| Wait Strategy | Fixed/Exponential/Retry-After | Honor Retry-After + 10% buffer | Respects API guidance |
| Detection Scope | Agent/Judge/Both | Both | Rate limits can come from either source |
| Checkpoint Location | Separate/Experiment/Temp | Experiment directory | Keeps everything together |
| Detection Method | Exit code/stderr/JSON | JSON + stderr patterns | Most reliable, multiple signals |
| Status Signaling | Log only/Checkpoint/PID | Log + checkpoint + PID | Multiple monitoring options |
| Parallel Behavior | Pause individual/all | Pause ALL workers | Prevents wasted API calls |
| Checkpoint Timing | During run/after run | After each run completes | Atomic, consistent state |
| Run Numbering | Skip/Overwrite | Same run number on retry | Overwrite failed run |
| Resume Invocation | Manual/Auto/Choice | Auto-resume, --fresh flag | User-friendly default |
| Config Validation | Allow/Strict/Warn | Strict match required | Prevent config drift bugs |

## Implementation Sequence

### Phase 1: Foundation - New Files

1. **Created `checkpoint.py`** (330 lines)
   - `E2ECheckpoint` dataclass with version, status, progress tracking
   - `save_checkpoint()` with atomic write (temp file + rename)
   - `load_checkpoint()` with validation
   - `compute_config_hash()` excluding non-critical fields
   - `validate_checkpoint_config()` for strict matching

2. **Created `rate_limit.py`** (190 lines)
   - `RateLimitInfo` dataclass
   - `RateLimitError` exception
   - `detect_rate_limit()` with JSON + stderr pattern detection
   - `parse_retry_after()` for extracting wait time
   - `wait_for_rate_limit()` with periodic status logging

### Phase 2: Detection - Adapter Integration

3. **Modified `claude_code.py`**
   - Added rate limit detection BEFORE parsing metrics
   - Ensures early detection and exception raising
   - Writes logs before raising exception

4. **Modified `llm_judge.py`**
   - Added rate limit detection after judge API call
   - Checks both stdout and stderr

### Phase 3: Coordination - Parallel Workers

5. **Modified `subtest_executor.py`** (+200 lines)
   - Added `RateLimitCoordinator` class (142 lines)
   - Uses `multiprocessing.Manager` for cross-process Events
   - Implements pause-all-workers pattern
   - Modified `run_subtest()` to support checkpoint/resume
   - Skip completed runs, load from `run_result.json`
   - Save checkpoint after each successful run
   - Workspace optimization (skip setup if all runs completed)

### Phase 4: Auto-Resume Logic

6. **Modified `runner.py`** (+150 lines)
   - Added `fresh` parameter to `__init__()`
   - `_find_existing_checkpoint()` - searches for most recent
   - Auto-resume logic with config validation
   - `_write_pid_file()` and `_cleanup_pid_file()`
   - `_mark_checkpoint_completed()` on successful completion
   - Pass checkpoint to `run_tier_subtests_parallel()`

### Phase 5: CLI Integration

7. **Modified `run_e2e_experiment.py`**
   - Added `--fresh` argument to parser
   - Passed `fresh` flag to `run_experiment()` call

## Technical Challenges & Solutions

### Challenge 1: Loading Completed Runs on Resume

**Problem**: Tried to load from `report.json`, got KeyError: 'exit_code'

**Investigation**:
- Checked actual `report.json` structure - only has simplified fields
- `RunResult` needs full data including token_stats, workspace_path, etc.
- No `from_dict()` method exists on `RunResult`

**Solution**:
- Save dual files: `report.json` (human-readable) + `run_result.json` (full data)
- Add save code after `RunResult` creation
- Manually reconstruct `RunResult` from JSON on resume

### Challenge 2: Workspace Already Exists on Resume

**Problem**: RuntimeError: Failed to create worktree: '/path' already exists

**Investigation**:
- `_setup_workspace()` creates git worktree
- On resume, workspace from previous run still exists
- Git worktree fails if directory exists

**Solution**:
- Check if ALL runs are completed before workspace setup
- If all completed, skip setup and just use existing path
- Optimization: saves time on resume

### Challenge 3: Config Hash Should Exclude Testing Params

**Decision**: Exclude `parallel_subtests` and `max_subtests` from hash

**Rationale**:
- These are testing/debugging parameters
- Don't affect actual experiment configuration
- Allows resume with different parallelism settings

## Testing Results

### Test 1: Fresh Run
```bash
Duration: 67.6s
Cost: $0.1111
Checkpoint created with 1 completed run
```

### Test 2: Auto-Resume
```bash
Duration: 0.2s (67.4s saved!)
Cost: $0.1111 (no new API calls)
Successfully loaded completed run from checkpoint
```

### Test 3: --fresh Flag
```bash
Created new experiment directory
Ignored existing checkpoint
Started from scratch
```

## Code Patterns Established

### 1. Atomic Checkpoint Write
```python
temp_path = checkpoint_path.with_suffix(".tmp")
with open(temp_path, "w") as f:
    json.dump(checkpoint.to_dict(), f, indent=2)
temp_path.rename(checkpoint_path)  # Atomic on POSIX
```

### 2. Cross-Process Coordination
```python
# Shared state via Manager
self._pause_event = manager.Event()
self._resume_event = manager.Event()
self._rate_limit_info = manager.dict()

# Worker blocks if paused
if self._pause_event.is_set():
    self._resume_event.wait()
```

### 3. Idempotent Workspace Setup
```python
all_completed = all(
    checkpoint.is_run_completed(tier, subtest, run)
    for run in range(1, runs_per_subtest + 1)
)

if not all_completed:
    setup_workspace(...)  # Only if needed
```

### 4. Config Hash Calculation
```python
# Only hash critical fields
hash_input = {
    "experiment_id": config.experiment_id,
    "task_repo": config.task_repo,
    # ... but exclude parallel_subtests, max_subtests
}
return hashlib.sha256(json.dumps(hash_input, sort_keys=True).encode()).hexdigest()[:16]
```

## Files Created/Modified

### New Files (520 lines)
- `src/scylla/e2e/checkpoint.py` - 330 lines
- `src/scylla/e2e/rate_limit.py` - 190 lines

### Modified Files
- `src/scylla/adapters/claude_code.py` - +10 lines
- `src/scylla/e2e/llm_judge.py` - +7 lines
- `src/scylla/e2e/subtest_executor.py` - +200 lines
- `src/scylla/e2e/runner.py` - +150 lines
- `scripts/run_e2e_experiment.py` - +8 lines
- `src/scylla/e2e/__init__.py` - Updated exports

### Total Impact
- 1091 insertions, 52 deletions
- 8 files changed

## Deployment

Created PR #126 with:
- Comprehensive description
- Usage examples
- Test results
- Auto-merge enabled

## Future Enhancements

Potential improvements identified but not implemented:

1. **Resume from specific tier** - Currently resumes entire experiment
2. **Checkpoint compression** - For large experiments with many runs
3. **Multiple checkpoint versions** - Keep history of checkpoints
4. **Status dashboard** - Web UI for monitoring checkpoint status
5. **Configurable retry strategies** - Beyond Retry-After header
6. **Checkpoint migration** - Handle version upgrades

## Lessons Learned

1. **Interview first, code second** - Prevented multiple rounds of rework
2. **Dual persistence strategy** - Human-readable + machine-readable formats
3. **Idempotency is critical** - Check work is done before executing
4. **Test serialization roundtrip** - Don't assume from_dict() exists
5. **Atomic operations matter** - Temp file + rename for crash safety
6. **Exclude non-critical from hash** - Testing params shouldn't break resume
7. **Pause-all-workers pattern** - Prevents wasted API calls on rate limit

## Related Patterns

- Checkpoint/resume systems
- Rate limit handling
- Multiprocessing coordination
- Atomic file operations
- Config validation
- State persistence

## References

- Implementation PR: https://github.com/HomericIntelligence/ProjectScylla/pull/126
- Plan file: `/home/mvillmow/.claude/plans/nested-painting-hoare.md`
- Main commit: `ffd33b5`
