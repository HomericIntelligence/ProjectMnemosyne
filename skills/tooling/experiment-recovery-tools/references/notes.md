# Experiment Recovery Tools - Session Notes

## Session Overview

**Date**: 2026-01-29
**Duration**: ~2 hours
**Objective**: Create scripts to selectively re-run failed/incomplete agents and judges

## Timeline of Events

### Initial Request
User wanted to distinguish between different failure modes and selectively re-run only specific categories.

### Iteration 1: Basic Rerun Script
- Created initial `rerun_agents.py` with basic classification
- Identified runs as: complete, failed, partial, never-started, agent-complete-missing-results

### Iteration 2: Missing agent/result.json Discovery
User pointed out that `agent/result.json` was missing from a run that appeared complete.

**Investigation revealed**:
- The file contains critical metadata (token stats, cost, exit code)
- 1,091 runs were missing this file
- Classification logic needed updating

**Solution**:
- Updated `_classify_run_status()` to check `agent/result.json`
- Created standalone `regenerate_agent_results.py` script
- Regenerated 1,121 files from existing logs

### Iteration 3: Simplified Status Names
User requested simplification:
- `agent-complete-missing-results` → `results`
- `agent-failed` → `failed`
- `agent-partial` → `partial`
- `never-started` → `missing`
- `complete` → `completed`

**Changes**:
- Updated `RunStatus` enum
- Updated all CLI arguments
- Updated documentation
- Updated all examples

### Iteration 4: Default Judge Model Change
User requested changing default judge from Sonnet to Opus.

**Locations updated**:
1. `scripts/run_e2e_experiment.py`:
   - `--judge-model default="opus"`
   - `--add-judge const="opus"`
   - Help text examples

2. `src/scylla/e2e/regenerate.py`:
   - Fallback: `"claude-opus-4-5-20251101"`

3. `src/scylla/e2e/models.py`:
   - Already correct: `["claude-opus-4-5-20251101"]`

### Iteration 5: AttributeError Fixes
Encountered `'ExperimentConfig' object has no attribute 'judge_model'`

**Root cause**: Config uses `judge_models` (plural list), code used `judge_model` (singular)

**Fixes**:
1. `regenerate.py` line 93: `config.judge_models[0]`
2. `regenerate.py` line 458: `config.judge_models` (already a list)

### Iteration 6: Unwanted Judge Execution
User reported: "this is not supposed to be running judges" when using `--status results`

**Problem**: Script was calling `regenerate_experiment(rejudge=True)` which:
- Ran judges
- Rebuilt tier results
- Did full regeneration

**Fix**: Inline JSON regeneration for `results` status:
- Read stdout.log, command_log.json
- Extract token stats and cost
- Write agent/result.json directly
- No judges, no rebuilding

**Result**: 1,130 files regenerated in ~4 seconds

### Iteration 7: Judge Rerun Script
User requested: "update the rerun judge script to have the same behavior as the re-run agents, but instead of validating agents, it does it for judges"

**Created**:
1. `src/scylla/e2e/rerun_judges.py` - Judge-specific rerun logic
2. `scripts/rerun_judges.py` - Judge rerun CLI
3. `docs/dev/rerun-judges-guide.md` - Comprehensive guide

**Judge Status Categories**:
- `complete` - Agent + judge both valid
- `missing` - Agent succeeded, judge never ran
- `failed` - Judge ran but failed
- `partial` - Judge started but incomplete
- `agent_failed` - Agent failed, cannot judge (special)

## Code Snippets

### Classification Logic Pattern

```python
def _classify_status(run_dir: Path) -> Status:
    # Check existence first
    if not run_dir.exists():
        return Status.MISSING

    # Check required files
    required_files = [
        run_dir / "agent" / "output.txt",
        run_dir / "agent" / "result.json",  # Don't forget this!
        run_dir / "agent" / "timing.json",
        run_dir / "judge" / "result.json",
        run_dir / "run_result.json",
    ]

    # Complete case
    if all(f.exists() for f in required_files):
        if (run_dir / "agent" / "output.txt").stat().st_size > 0:
            return Status.COMPLETED

    # Handle other cases...
```

### Regeneration Pattern

```python
# Fast regeneration from logs (no execution)
stdout = (agent_dir / "stdout.log").read_text()
stdout_json = json.loads(stdout.strip())

result_data = {
    "exit_code": cmd_log["commands"][0]["exit_code"],
    "token_stats": {
        "input_tokens": stdout_json["usage"]["input_tokens"],
        "output_tokens": stdout_json["usage"]["output_tokens"],
        # ...
    },
    "cost_usd": stdout_json["total_cost_usd"],
}

with open(agent_dir / "result.json", "w") as f:
    json.dump(result_data, f, indent=2)
```

### CLI Filtering Pattern

```python
# Consistent across both scripts
parser.add_argument("--status", action="append", choices=[...])
parser.add_argument("--tier", action="append")
parser.add_argument("--subtest", action="append")
parser.add_argument("--runs", type=str)  # Comma-separated
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("-v", "--verbose", action="store_true")
```

## Testing Results

### Test 1: Regenerate agent/result.json
```
Before:
  ⚠ results: 1130

After regeneration:
  ✓ completed: 1130

Time: ~4 seconds
No agents run, no judges run, just JSON creation
```

### Test 2: Judge classification
```
Total expected runs: 1130
  ✓ complete:      0
  ○ missing:       0
  ✗ failed:        0
  ⋯ partial:       1092
  ⊗ agent_failed:  38
```

## Lessons for Future Skills

1. **Always validate ALL required files** - Don't assume completeness based on subset
2. **Check data model evolution** - Singular → plural changes require updates everywhere
3. **Inline targeted operations** - Broad functions have side effects
4. **User-driven simplification** - Listen when users find names verbose
5. **File-based classification is fast** - No need to execute processes to check status
6. **Dry-run is essential** - Users need to preview before execution
7. **Consistent CLI design** - Similar tools should have similar interfaces

## Files Modified

### New Files
- `src/scylla/e2e/rerun.py`
- `src/scylla/e2e/rerun_judges.py`
- `scripts/rerun_agents.py`
- `scripts/rerun_judges.py`
- `scripts/regenerate_agent_results.py`
- `docs/dev/rerun-agents-guide.md`
- `docs/dev/rerun-judges-guide.md`

### Modified Files
- `src/scylla/e2e/regenerate.py` (fixed judge_model references)
- `scripts/run_e2e_experiment.py` (changed default judge to opus)

## Performance Characteristics

| Operation | Time | Execution |
|-----------|------|-----------|
| Scan 1,130 runs | ~1s | File checks only |
| Regenerate 1,130 agent/result.json | ~4s | JSON I/O only |
| Re-run single agent | ~30s | Claude Code execution |
| Re-run single judge | ~20s | Judge evaluation |

## Commands for Reference

```bash
# Agent operations
pixi run python scripts/rerun_agents.py ~/fullruns/exp/ --dry-run
pixi run python scripts/rerun_agents.py ~/fullruns/exp/ --status results
pixi run python scripts/rerun_agents.py ~/fullruns/exp/ --status failed
pixi run python scripts/rerun_agents.py ~/fullruns/exp/ --tier T0 --runs 1,3,5

# Judge operations
pixi run python scripts/rerun_judges.py ~/fullruns/exp/ --dry-run
pixi run python scripts/rerun_judges.py ~/fullruns/exp/ --status missing
pixi run python scripts/rerun_judges.py ~/fullruns/exp/ --status failed --judge-model opus

# Direct regeneration
pixi run python scripts/regenerate_agent_results.py ~/fullruns/exp/
```
