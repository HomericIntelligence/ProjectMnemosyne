# Skill: Experiment Recovery Tools

| Property | Value |
|----------|-------|
| **Date** | 2026-01-29 |
| **Objective** | Build scripts to selectively re-run failed/incomplete agents and judges in E2E experiments |
| **Outcome** | ✅ Created `rerun_agents.py` and `rerun_judges.py` with 5-status classification system |
| **Category** | tooling |
| **Key Innovation** | Fine-grained status classification allowing selective re-execution without full experiment reruns |

## When to Use This Skill

Use this approach when building tools for:

1. **Recovering from interrupted experiments** - Resume from where you left off
2. **Selective re-execution** - Re-run only failed/incomplete runs, not entire experiments
3. **Status-based filtering** - Different actions based on run completion state
4. **Regenerating missing metadata** - Rebuild files from existing logs without re-execution

### Trigger Patterns

- User asks to "re-run failed runs" or "resume experiment"
- Need to identify which runs need re-execution in a large experiment
- Want to regenerate missing result files without running agents/judges again
- Experiment was interrupted and needs completion

## Verified Workflow

### 1. Status Classification System

Create distinct enums for different execution phases:

**Agent Status (RunStatus)**:
- `completed` - Agent + judge + run_result.json all exist
- `results` - Agent finished but missing result files (regenerate only)
- `failed` - Agent ran but failed
- `partial` - Agent started but incomplete
- `missing` - Run never started

**Judge Status (JudgeStatus)**:
- `complete` - Agent + judge both valid
- `missing` - Agent succeeded but judge never ran
- `failed` - Judge ran but failed
- `partial` - Judge started but incomplete
- `agent_failed` - Agent failed, cannot judge

### 2. File-Based Classification Logic

Determine status by examining file existence and content:

```python
def _classify_run_status(run_dir: Path) -> RunStatus:
    if not run_dir.exists():
        return RunStatus.MISSING

    agent_dir = run_dir / "agent"
    agent_output = agent_dir / "output.txt"
    agent_result = agent_dir / "result.json"  # CRITICAL: Must check this!
    agent_timing = agent_dir / "timing.json"
    agent_command_log = agent_dir / "command_log.json"
    judge_dir = run_dir / "judge"
    run_result = run_dir / "run_result.json"

    # Check all required files exist
    if (agent_output.exists() and agent_output.stat().st_size > 0
        and agent_result.exists() and judge_dir.exists()
        and run_result.exists()):
        return RunStatus.COMPLETED

    # Agent complete but missing results
    if (agent_output.exists() and agent_output.stat().st_size > 0
        and agent_timing.exists() and agent_command_log.exists()
        and (not run_result.exists() or not agent_result.exists())):
        return RunStatus.RESULTS

    # ... other statuses
```

**CRITICAL**: Always check for `agent/result.json` - it contains token stats and cost data!

### 3. CLI Design Pattern

Use consistent interface across both scripts:

```bash
# Common flags
--dry-run              # Preview without executing
--status <status>      # Filter by status (can repeat)
--tier <tier>          # Filter by tier
--subtest <subtest>    # Filter by subtest
--runs <nums>          # Filter by run numbers (comma-separated)
-v, --verbose          # Verbose logging
```

### 4. Regenerating Missing Files

For `results` status (agent complete, files missing), regenerate from logs:

```python
# Read existing logs
stdout = (agent_dir / "stdout.log").read_text()
with open(agent_dir / "command_log.json") as f:
    cmd_log = json.load(f)

# Parse Claude Code JSON output
stdout_json = json.loads(stdout.strip())
usage = stdout_json.get("usage", {})

# Extract and save
result_data = {
    "exit_code": cmd_log["commands"][0]["exit_code"],
    "stdout": stdout,
    "stderr": stderr,
    "token_stats": {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
    },
    "cost_usd": stdout_json.get("total_cost_usd", 0.0),
    "api_calls": 1,
}

with open(agent_dir / "result.json", "w") as f:
    json.dump(result_data, f, indent=2)
```

**Key**: This is FAST because it's just JSON manipulation, no agent execution!

### 5. Integration with Existing Systems

For actual re-execution, leverage existing infrastructure:

```python
# For agent re-runs: Use SubTestExecutor._execute_single_run()
executor = SubTestExecutor(config, tier_id, tier_config, ...)
run_result = executor._execute_single_run(subtest_config, run_number)

# For judge re-runs: Use regenerate_experiment(rejudge=True)
from scylla.e2e.regenerate import regenerate_experiment
regen_stats = regenerate_experiment(
    experiment_dir=experiment_dir,
    rejudge=True,  # Only re-judge, don't rebuild everything
    judge_model=effective_judge_model,
)
```

## Failed Attempts & Lessons Learned

### ❌ Failed: Initial Classification Didn't Check agent/result.json

**What we tried**: Only checked for `agent/output.txt`, `timing.json`, and `run_result.json`

**Why it failed**: Missed that `agent/result.json` is a critical file containing:
- Token statistics
- API cost
- Exit code
- Full stdout/stderr

**Symptom**: 1,091 runs classified as "complete" when they were actually missing metadata

**Fix**: Added `agent_result.exists()` check to classification logic

**Lesson**: Always verify ALL required files, not just the obvious ones. The `paths.py` module defines canonical file paths - use it!

### ❌ Failed: Used config.judge_model Instead of config.judge_models

**What we tried**: Accessed `config.judge_model` (singular) in multiple places

**Why it failed**: `ExperimentConfig` uses `judge_models` (plural, list) for consensus voting

**Error**: `AttributeError: 'ExperimentConfig' object has no attribute 'judge_model'`

**Locations fixed**:
1. `regenerate.py` line 93: `config.judge_model` → `config.judge_models[0]`
2. `regenerate.py` line 458: `[config.judge_model]` → `config.judge_models` (already a list!)

**Fix**:
```python
# WRONG
effective_judge_model = config.judge_model

# RIGHT
effective_judge_model = config.judge_models[0] if config.judge_models else "claude-opus-4-5-20251101"

# WRONG
select_best_subtest(subtest_results, [config.judge_model], ...)

# RIGHT
select_best_subtest(subtest_results, config.judge_models, ...)  # Already a list!
```

**Lesson**: Always check the actual data model structure. The config evolved from single judge to multiple judges (consensus voting), but old code wasn't updated.

### ❌ Failed: Calling regenerate_experiment() for --status results

**What we tried**: Used `regenerate_experiment(rejudge=True)` to handle `results` status

**Why it failed**:
- `regenerate_experiment()` does FULL regeneration (judges + results + reports)
- User wanted ONLY to regenerate missing `agent/result.json` files
- Script was re-running judges unnecessarily (slow + errors)

**Error**: User reported "this is not supposed to be running judges"

**Fix**: Inline JSON regeneration logic directly in rerun script:
```python
# Instead of calling regenerate_experiment()...
# Directly regenerate agent/result.json from logs
for run_info in needs_regenerate:
    # Extract from stdout.log + command_log.json
    # Write agent/result.json
    # No judges, no rebuilding, just file creation
```

**Lesson**: Functions like `regenerate_experiment()` have broad scope. For targeted operations, implement inline to avoid unwanted side effects.

### ❌ Failed: Verbose Status Names

**What we tried**: Initially used verbose names like:
- `agent-complete-missing-results`
- `agent-failed`
- `agent-partial`
- `never-started`

**Why it changed**: User requested simplified names

**Fix**: Simplified to single words:
- `results` (was `agent-complete-missing-results`)
- `failed` (was `agent-failed`)
- `partial` (was `agent-partial`)
- `missing` (was `never-started`)
- `completed` (was `complete`)

**Lesson**: CLI flags should be concise and memorable. Users type them repeatedly - shorter is better.

## Results & Parameters

### Files Created

1. **Core Modules**:
   - `src/scylla/e2e/rerun.py` (570 lines) - Agent rerun logic
   - `src/scylla/e2e/rerun_judges.py` (467 lines) - Judge rerun logic

2. **CLI Scripts**:
   - `scripts/rerun_agents.py` (229 lines) - Agent rerun CLI
   - `scripts/rerun_judges.py` (229 lines) - Judge rerun CLI
   - `scripts/regenerate_agent_results.py` (175 lines) - Standalone regenerator

3. **Documentation**:
   - `docs/dev/rerun-agents-guide.md` - Comprehensive agent rerun guide
   - `docs/dev/rerun-judges-guide.md` - Comprehensive judge rerun guide

### Performance Metrics

**Regenerating agent/result.json files (results status)**:
- **Before**: Would try to run full regeneration (judges + results) → slow, error-prone
- **After**: Direct JSON generation from logs
- **Speed**: 1,130 files in ~4 seconds
- **No execution**: No agents, no judges, just file I/O

**Status classification**:
- Scans 1,130 runs in ~1 second
- File-based detection (no process execution)
- Accurate classification based on file existence and content

### Example Usage

```bash
# Agent Recovery
pixi run python scripts/rerun_agents.py ~/fullruns/experiment/ --dry-run
pixi run python scripts/rerun_agents.py ~/fullruns/experiment/ --status failed
pixi run python scripts/rerun_agents.py ~/fullruns/experiment/ --status results  # Fast!
pixi run python scripts/rerun_agents.py ~/fullruns/experiment/ --status partial --status missing

# Judge Recovery
pixi run python scripts/rerun_judges.py ~/fullruns/experiment/ --dry-run
pixi run python scripts/rerun_judges.py ~/fullruns/experiment/ --status missing
pixi run python scripts/rerun_judges.py ~/fullruns/experiment/ --status failed --judge-model opus

# Filters
pixi run python scripts/rerun_agents.py ~/fullruns/experiment/ --tier T0 --status failed
pixi run python scripts/rerun_judges.py ~/fullruns/experiment/ --runs 1,3,5
```

### Default Judge Model Change

Updated default from Sonnet to Opus:
- `scripts/run_e2e_experiment.py`: `--judge-model default="opus"`
- `src/scylla/e2e/regenerate.py`: Fallback to `claude-opus-4-5-20251101`
- `src/scylla/e2e/models.py`: Already defaulted to Opus ✓

## Key Takeaways

1. **Status-based classification** enables selective re-execution without full experiment reruns
2. **File existence checks** provide fast, accurate status determination
3. **Inline regeneration** faster than calling broad-scope functions for targeted operations
4. **Consistent CLI design** across related tools improves usability
5. **Always validate required files** - missing metadata files can appear "complete"
6. **Check data model evolution** - single → plural fields require code updates throughout

## Related Skills

- `evaluation` - E2E experiment execution and judging infrastructure
- `debugging` - Identifying and fixing failed runs
- `ci-cd` - Automated recovery in CI pipelines

## Tags

`rerun`, `recovery`, `status-classification`, `experiment-management`, `cli-tools`, `selective-execution`
