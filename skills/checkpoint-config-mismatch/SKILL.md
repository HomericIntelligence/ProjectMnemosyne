# Skill: Fixing Checkpoint Config Mismatch and Data Loss

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-22 |
| **Objective** | Fix checkpoint resume failures and recover lost worker progress data |
| **Outcome** | ✅ Successfully fixed config validation, recovered 590 lost runs, prevented future data loss |
| **Time to Resolution** | ~1 hour (analysis + implementation + verification) |

## Problem Statement

When resuming E2E experiments from checkpoints, two critical issues occurred:

1. **Config Mismatch Error**: Resume failed with "Config has changed since checkpoint" even when configs were identical
2. **Lost Worker Progress**: Checkpoint showed `completed_runs: {}` despite 590 `run_result.json` files existing on disk

## When to Use This Skill

Use this approach when:

- ✅ Checkpoint resume fails with "Config has changed" error despite matching configuration
- ✅ Checkpoint shows empty `completed_runs` but result files exist on disk
- ✅ Experiment interrupts (SIGINT) appear to lose worker progress
- ✅ Config hash validation is too strict for legitimate resume scenarios
- ✅ Need to rebuild checkpoint state from scattered result files

## Root Cause Analysis

### Issue 1: Config Hash Mismatch

**Problem**: CLI args were hashed and validated against checkpoint hash, but user couldn't remember exact original args.

**Root Cause**: Design assumed user would provide identical CLI args on resume, but checkpoint already has the correct config saved.

**Why It Failed**:
- Original experiment used 3 judge models: `opus, sonnet, haiku`
- Resume command only specified 2 judges
- Hash validation rejected resume despite checkpoint having full config stored

### Issue 2: Lost Worker Progress (CRITICAL BUG)

**Problem**: 590 completed runs existed as `run_result.json` files, but checkpoint showed `completed_runs: {}`.

**Root Cause**: Race condition in interrupt handler:

```python
# runner.py:380-385 (BUGGY CODE)
finally:
    if is_shutdown_requested() and self.checkpoint:
        self.checkpoint.status = "interrupted"
        save_checkpoint(self.checkpoint, checkpoint_path)  # ⚠️ OVERWRITES WORKER PROGRESS
```

**What Happened**:
1. Worker processes complete runs and save checkpoint with `completed_runs` populated
2. User presses Ctrl+C (SIGINT)
3. Main process catches SIGINT in `finally` block
4. Main process saves `self.checkpoint` which has **stale** `completed_runs: {}`
5. **All worker progress is overwritten!**

### Issue 3: Incomplete Serialization

**Problem**: `thinking_mode`, `max_subtests`, and `use_containers` were missing from `ExperimentConfig.to_dict()`.

**Impact**: Config couldn't be fully restored from saved JSON, causing subtle bugs.

## Verified Workflow

### Step 1: Create Repair Script

Created `scripts/repair_checkpoint.py` to rebuild `completed_runs` from existing result files:

```python
# Scan for all run_result.json files
for run_result_file in experiment_dir.rglob("run_result.json"):
    # Parse path: T0/00/run_01/run_result.json
    tier_id, subtest_id, run_dir = parse_path(run_result_file)
    run_num = int(run_dir.split("_")[1])

    # Load result and determine status
    with open(run_result_file) as f:
        run_data = json.load(f)
    status = "passed" if run_data.get("judge_passed") else "failed"

    # Rebuild nested structure
    completed_runs[tier_id][subtest_id][run_num] = status
```

**Result**: Recovered 590 lost runs across 5 tiers

### Step 2: Fix Config Loading

Modified `runner.py:191-219` to load config from checkpoint instead of validating CLI args:

```python
if checkpoint_path and not self._fresh:
    self.checkpoint = load_checkpoint(checkpoint_path)
    self.experiment_dir = Path(self.checkpoint.experiment_dir)

    # Load config from checkpoint's saved experiment.json
    saved_config_path = self.experiment_dir / "config" / "experiment.json"
    if saved_config_path.exists():
        logger.info(f"📋 Loading config from checkpoint: {saved_config_path}")
        self.config = ExperimentConfig.load(saved_config_path)
        # Now CLI args don't matter - checkpoint config wins!
```

**Why This Works**:
- Checkpoint always references the correct config via `experiment_dir`
- No need for user to remember exact CLI args
- Config hash validation becomes a sanity check only (fallback path)

### Step 3: Fix Interrupt Handler

Modified `runner.py:379-413` to reload checkpoint before saving:

```python
finally:
    if is_shutdown_requested() and checkpoint_path and checkpoint_path.exists():
        # CRITICAL: Reload from disk to get worker-saved completions
        try:
            logger.info("🔄 Reloading checkpoint from disk...")
            current_checkpoint = load_checkpoint(checkpoint_path)
            current_checkpoint.status = "interrupted"
            save_checkpoint(current_checkpoint, checkpoint_path)
        except Exception as reload_error:
            # Fallback: save stale copy (better than nothing)
            logger.error(f"⚠️  Failed to reload: {reload_error}")
            if self.checkpoint:
                self.checkpoint.status = "interrupted"
                save_checkpoint(self.checkpoint, checkpoint_path)
```

**Why This Works**:
- Workers write their progress to disk continuously
- Main process reloads latest checkpoint state before saving
- Worker progress is preserved even during interrupt

### Step 4: Fix Serialization

Added missing fields to `ExperimentConfig.to_dict()` and `load()`:

```python
def to_dict(self) -> dict[str, Any]:
    return {
        # ... existing fields ...
        "thinking_mode": self.thinking_mode,      # ← Added
        "max_subtests": self.max_subtests,        # ← Added
        "use_containers": self.use_containers,    # ← Added
    }

@classmethod
def load(cls, path: Path) -> ExperimentConfig:
    # ... load data ...
    return cls(
        # ... existing fields ...
        thinking_mode=data.get("thinking_mode", "None"),
        max_subtests=data.get("max_subtests"),
        use_containers=data.get("use_containers", False),
    )
```

## Failed Attempts

### ❌ Attempt 1: Manually Match Original CLI Args

**Tried**: Asked user to remember exact original command with 3 judges.

**Why It Failed**: User didn't remember exact args, and this approach doesn't scale. Users shouldn't need to track original commands.

**Lesson**: Don't require users to remember CLI args - checkpoint should be self-contained.

### ❌ Attempt 2: Considered Adding Config to Checkpoint Object

**Tried**: Thought about embedding full config dict in checkpoint itself.

**Why We Didn't**: Checkpoint already references `experiment_dir`, which contains `config/experiment.json`. No need to duplicate data.

**Lesson**: Leverage existing data structures before adding new ones.

## Results & Parameters

### Repair Script Execution

```bash
$ python scripts/repair_checkpoint.py ~/fullruns/test001-nothinking/2026-01-20T06-50-26-test-001/checkpoint.json

📂 Loading checkpoint: .../checkpoint.json
📊 Current completed_runs count: 0
🔍 Scanning for run_result.json files...
📁 Found 590 run_result.json files
💾 Backing up original checkpoint to: checkpoint.json.backup
💾 Saving repaired checkpoint

✅ Checkpoint repaired successfully!
   Original completed_runs: 0
   Rebuilt completed_runs:  590
   Difference:              +590

📊 Breakdown by tier:
   T0: 149 runs
   T1: 45 runs
   T2: 102 runs
   T3: 229 runs
   T4: 65 runs
```

### Resume Verification

```bash
$ pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 \
  --results-dir ~/fullruns/test001-nothinking \
  --runs 1 -v

# Output (key lines):
2026-01-22 07:17:17 [INFO] scylla.e2e.runner: 📂 Resuming from checkpoint
2026-01-22 07:17:17 [INFO] scylla.e2e.runner: 📋 Loading config from checkpoint: .../config/experiment.json
2026-01-22 07:17:17 [INFO] scylla.e2e.runner:    Previously completed: 590 runs
```

**Verified by User**: Full resume test worked correctly ✅

## Files Modified

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/repair_checkpoint.py` | NEW (138 lines) | Rebuild completed_runs from run_result.json files |
| `src/scylla/e2e/runner.py` | 191-219 | Load config from checkpoint's experiment.json |
| `src/scylla/e2e/runner.py` | 379-413 | Reload checkpoint from disk before saving on interrupt |
| `src/scylla/e2e/models.py` | 634, 669-671 | Add missing fields to serialization |

## Key Takeaways

1. **Checkpoints Should Be Self-Contained**: Don't require users to remember CLI args - load from saved config
2. **Beware Race Conditions**: Main process and workers can have different checkpoint states
3. **Always Reload Before Overwriting**: When saving shared state, reload from disk first
4. **Complete Serialization**: Every field in dataclass should be in `to_dict()` and `load()`
5. **Build Repair Tools**: When data loss happens, create tools to recover from scattered artifacts

## Prevention

To prevent similar issues:

1. **Add Unit Test**: Test interrupt handler doesn't lose worker progress
2. **Add Integration Test**: Test resume with any CLI args (checkpoint config wins)
3. **Serialization Linter**: Verify all dataclass fields are in `to_dict()` and `load()`
4. **Checkpoint Validation**: On load, verify `completed_runs` count matches filesystem

## Related Issues

- Issue #203 (hypothetical): "Resume fails with config mismatch"
- Related to parallel execution with shared state
- Similar to database transaction isolation issues

## PR

**Pull Request**: #204 - https://github.com/HomericIntelligence/ProjectScylla/pull/204
