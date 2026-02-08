# Raw Session Notes: Checkpoint Config Mismatch

## Session Context

**Date**: 2026-01-22
**Duration**: ~1 hour
**Issue**: Checkpoint resume failing + 590 lost completed runs

## User's Initial Problem Statement

> Implement the following plan:
>
> # Plan: Fix Checkpoint Config Mismatch & Resume E2E Experiment
>
> Two distinct issues identified:
>
> ### Issue 1: Config Hash Mismatch
> ```
> Failed to resume from checkpoint: Config has changed since checkpoint. Use --fresh to start over.
> ```
>
> **Root Cause**: Original used 3 judges (opus, sonnet, haiku), your command only had 2.
>
> ### Issue 2: `completed_runs: {}` Despite 590 Completed Runs (CRITICAL BUG)

## Plan Phases

The user provided a complete plan with 4 steps:

1. **Repair Script**: Rebuild completed_runs from run_result.json files
2. **Config Override**: Make checkpoint config override CLI args
3. **Interrupt Fix**: Reload checkpoint before saving on SIGINT
4. **Serialization Fix**: Add missing thinking_mode field

## Implementation Timeline

### Phase 1: Repair Script (15 min)

Created `scripts/repair_checkpoint.py`:

- Scans experiment_dir for all `run_result.json` files
- Parses paths to extract tier/subtest/run info
- Loads each result to check `judge_passed` status
- Rebuilds nested `completed_runs` dict structure
- Saves backup before overwriting checkpoint

**Execution Result**:
```
✅ Checkpoint repaired successfully!
   Original completed_runs: 0
   Rebuilt completed_runs:  590
   Difference:              +590
```

### Phase 2: Config Loading Fix (20 min)

Modified `runner.py:191-219`:

**Before**:
```python
# Validate config match (strict validation)
if not validate_checkpoint_config(self.checkpoint, self.config):
    raise ValueError("Config has changed")
```

**After**:
```python
# Load config from checkpoint's saved experiment.json
saved_config_path = self.experiment_dir / "config" / "experiment.json"
if saved_config_path.exists():
    self.config = ExperimentConfig.load(saved_config_path)
    # CLI args now ignored - checkpoint config wins!
```

### Phase 3: Interrupt Handler Fix (15 min)

Modified `runner.py:379-413`:

**Before** (BUGGY):
```python
finally:
    if is_shutdown_requested() and self.checkpoint:
        self.checkpoint.status = "interrupted"
        save_checkpoint(self.checkpoint, checkpoint_path)  # ⚠️ Stale data!
```

**After** (FIXED):
```python
finally:
    if is_shutdown_requested() and checkpoint_path:
        # Reload from disk to get worker progress
        current_checkpoint = load_checkpoint(checkpoint_path)
        current_checkpoint.status = "interrupted"
        save_checkpoint(current_checkpoint, checkpoint_path)
```

### Phase 4: Serialization Fix (10 min)

Added missing fields to `ExperimentConfig`:

**Added to `to_dict()`**:
- `thinking_mode`
- `max_subtests`
- `use_containers`

**Added to `load()`**:
- Same fields with appropriate defaults

## Verification Steps

1. **Repair Script**: Successfully recovered 590 runs
2. **Config Loading**: Log showed "Loading config from checkpoint"
3. **Resume Test**: User confirmed "i manually tested, it worked"

## Linter Issues Encountered

Multiple rounds of linter fixes:

1. **E501**: Line too long (>100 chars) in docstring example
2. **D401**: Docstring not in imperative mood
3. **D301**: Missing `r"""` for raw string with backslashes

**Solution**: Used raw string literal and split long example across lines:
```python
r"""...
Example:
    python scripts/repair_checkpoint.py \
        ~/fullruns/.../checkpoint.json
"""
```

## Key Code Patterns

### Pattern 1: Rebuilding Nested Dict from Filesystem

```python
completed_runs = {}
for file in experiment_dir.rglob("run_result.json"):
    tier_id, subtest_id, run_num = parse_path(file)

    # Build nested structure
    if tier_id not in completed_runs:
        completed_runs[tier_id] = {}
    if subtest_id not in completed_runs[tier_id]:
        completed_runs[tier_id][subtest_id] = {}

    completed_runs[tier_id][subtest_id][run_num] = status
```

### Pattern 2: Reload-Before-Save for Shared State

```python
finally:
    # Don't save stale in-memory state!
    try:
        current_state = load_from_disk(path)  # Get latest
        current_state.status = "interrupted"
        save_to_disk(current_state, path)
    except Exception:
        # Fallback: save what we have (better than nothing)
        save_to_disk(self.state, path)
```

### Pattern 3: Config Precedence Hierarchy

```python
# 1. Try checkpoint's saved config
if checkpoint_config_exists():
    config = load_checkpoint_config()

# 2. Fallback to CLI validation
else:
    if not validate_cli_config():
        raise ConfigMismatch()
```

## Error Messages Seen

### Original Error
```
Failed to resume from checkpoint: Config has changed since checkpoint.
Use --fresh to start over.
Checkpoint: /home/mvillmow/fullruns/.../checkpoint.json
```

### After Fix (Success)
```
2026-01-22 07:17:17 [INFO] 📂 Resuming from checkpoint
2026-01-22 07:17:17 [INFO] 📋 Loading config from checkpoint: .../experiment.json
2026-01-22 07:17:17 [INFO]    Previously completed: 590 runs
```

## Race Condition Details

**Scenario**: Multi-process experiment with shared checkpoint file

```
Time  | Main Process                  | Worker Process
------|-------------------------------|---------------------------
T0    | checkpoint = {}               |
T1    |                               | Completes run #1
T2    |                               | save_checkpoint({run1: ...})
T3    |                               | Completes run #2
T4    |                               | save_checkpoint({run1, run2})
T5    | User presses Ctrl+C           |
T6    | SIGINT handler fires          |
T7    | save_checkpoint(self.checkpoint)  ← OVERWRITES WORKER PROGRESS!
```

**Fix**: Reload from disk at T7 to get latest worker state

## Metrics

- **Lines of Code Changed**: ~70 (excluding new repair script)
- **New Files**: 1 (repair script, 138 lines)
- **Data Recovered**: 590 completed runs
- **Time to Resolution**: ~1 hour (plan provided by user)
- **Pre-commit Hook Failures**: 3 rounds of linter fixes

## Questions That Arose

1. **Q**: Why not embed full config in checkpoint object?
   **A**: Redundant - experiment_dir already has config/experiment.json

2. **Q**: Should we validate CLI args at all?
   **A**: Keep as fallback when checkpoint config missing (backward compat)

3. **Q**: What if reload fails during interrupt?
   **A**: Fallback to saving stale checkpoint (better than crashing)

## User Feedback

> i manually tested, it worked

Positive confirmation that the fix resolved the issue.

## PR Details

- **Branch**: `first-run` (created from plan mode)
- **PR Number**: #204
- **Auto-merge**: Enabled (rebase strategy)
- **Files Changed**: 3 (runner.py, models.py, repair_checkpoint.py)
- **Commit Message**: Detailed with problem/solution/changes breakdown

## Follow-up Items

From the plan's "Unit Tests to Add" section:

1. **test_checkpoint_config_overrides_cli()**
   - Setup: Create checkpoint with specific config
   - Run: Resume with different CLI args
   - Assert: Uses checkpoint config, not CLI

2. **test_interrupt_preserves_worker_completions()**
   - Setup: Mock worker completing runs
   - Run: Simulate SIGINT
   - Assert: Checkpoint contains worker completions

These tests were NOT implemented in this session (out of scope).

## References

- Original plan transcript: `/home/mvillmow/.claude/projects/.../a69f8a47-2561-40e8-8f31-15495bd4f700.jsonl`
- Checkpoint location: `~/fullruns/test001-nothinking/2026-01-20T06-50-26-test-001/`
- Result files: 590 `run_result.json` files across 5 tiers

## Architecture Notes

### Checkpoint Structure

```json
{
  "experiment_id": "test-001",
  "experiment_dir": "/path/to/experiment",
  "config_hash": "abc123...",
  "completed_runs": {
    "T0": {
      "00": {1: "passed", 2: "failed", ...},
      "01": {...}
    },
    "T1": {...}
  },
  "status": "running" | "interrupted" | "completed",
  "started_at": "ISO8601",
  "last_updated_at": "ISO8601"
}
```

### Directory Structure

```
experiment_dir/
├── config/
│   └── experiment.json          ← Source of truth for config
├── checkpoint.json              ← State snapshot
├── T0/
│   ├── 00/
│   │   ├── run_01/
│   │   │   ├── run_result.json  ← Individual run result
│   │   │   └── workspace/
│   │   ├── run_02/...
```

## Design Lessons

1. **Single Source of Truth**: Config lives in one place (experiment.json), checkpoint references it
2. **Idempotent Recovery**: Repair script can be run multiple times safely (creates backup first)
3. **Graceful Degradation**: If reload fails, save what we have (don't crash)
4. **Complete Serialization**: Every field must round-trip through JSON
5. **Filesystem as Database**: Result files serve as durable transaction log
