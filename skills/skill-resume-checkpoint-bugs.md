---
name: 'Skill: Resume Checkpoint Bugs'
description: 'Fix experiment runner resume bugs: uppercase INTERRUPTED state, max_subtests
  ephemeral handling, missing-subtest detection, and tier state reset target selection'
category: debugging
date: 2026-02-26
version: 1.0.0
user-invocable: false
---
# Skill: Fixing Experiment Runner Resume/Checkpoint Bugs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Objective** | Fix three bugs preventing correct behavior when re-running experiments with changed CLI args |
| **Outcome** | All three bugs fixed, 3175 tests passing, PR #1109 merged |
| **Category** | debugging |
| **Project** | ProjectScylla |

## When to Use This Skill

Trigger this skill when:
- An experiment resumed with different `--max-subtests` doesn't execute new subtests
- A Ctrl+C interrupted experiment doesn't reset properly on next run
- Pipeline baseline differs between runs of the same experiment
- Checkpoint state machine appears to skip STEP 3 (failed/interrupted reset)
- Tier stays COMPLETE even though new subtests should run

## Verified Workflow

### Diagnosing Resume Bugs

1. **Check interrupt state casing first** — the cheapest bug to find:
   ```python
   # In _handle_experiment_interrupt, look for string literals
   current_checkpoint.experiment_state = "INTERRUPTED"  # BUG: uppercase
   # vs
   current_checkpoint.experiment_state = ExperimentState.INTERRUPTED.value  # CORRECT
   ```
   STEP 3 in `_initialize_or_resume_experiment` only matches lowercase values.

2. **Check ephemeral field handling** — which fields always override vs non-None-only:
   - `--until-*` fields: non-None only (omitting keeps saved value)
   - `--max-subtests`: ALWAYS override; `None` = "no limit" (clears saved value)
   - Pattern: scope-limiting fields need `None`-clearing; run-mode fields don't

3. **Check tier needs-execution detection** — does it see _all_ subtests?
   - `_check_tiers_need_execution()` originally only checked `run_states` (existing runs)
   - Missing subtests (not yet in checkpoint) were invisible — extend to compare config vs checkpoint subtest sets

4. **Check tier state reset target**:
   - Has incomplete runs → reset to `"subtests_running"`
   - Has missing subtests → reset to `"pending"` (so `action_pending()` reloads full list)

### Pattern: Ephemeral CLI Field Handling on Resume

```python
# STEP 2: Restore ephemeral CLI args after checkpoint load
# max_subtests: always restore (None clears saved limit)
self.config = self.config.model_copy(
    update={"max_subtests": _cli_ephemeral["max_subtests"]}
)
# Other ephemeral fields: only restore if CLI provided a value
non_none_rest = {
    k: v for k, v in _cli_ephemeral.items()
    if k != "max_subtests" and v is not None
}
if non_none_rest:
    self.config = self.config.model_copy(update=non_none_rest)
```

### Pattern: Detecting Missing Subtests in Checkpoint

```python
# In _check_tiers_need_execution, after checking run states:
tier_config = self.tier_manager.load_tier_config(tier_id, self.config.skip_agent_teams)
config_subtests = {s.id for s in tier_config.subtests}
if self.config.max_subtests is not None:
    config_subtests = {s.id for s in tier_config.subtests[:self.config.max_subtests]}
checkpoint_subtests = set(self.checkpoint.subtest_states.get(tid, {}).keys())
if config_subtests - checkpoint_subtests:
    needs_work.add(tid)
```

### Pattern: Tier State Reset for Missing Subtests

```python
# Detect missing subtests before choosing reset target
_has_missing_subtests = False
try:
    _tc = self.tier_manager.load_tier_config(TierID(tier_id_str), ...)
    _config_subs = {s.id for s in _tc.subtests}
    _ckpt_subs = set(self.checkpoint.subtest_states.get(tier_id_str, {}).keys())
    _has_missing_subtests = bool(_config_subs - _ckpt_subs)
except Exception:
    pass

if _has_missing_subtests:
    self.checkpoint.tier_states[tier_id_str] = "pending"  # re-run action_pending
else:
    self.checkpoint.tier_states[tier_id_str] = "subtests_running"  # skip to subtest exec
```

### Pattern: Idempotent Experiment-Level Baseline Capture

```python
def _capture_experiment_baseline(self) -> None:
    baseline_path = self.experiment_dir / "pipeline_baseline.json"
    if baseline_path.exists():
        return  # Idempotent — skip on resume

    worktree_path = self.experiment_dir / "_baseline_worktree"
    try:
        self.workspace_manager.create_worktree(worktree_path)
        result = _run_build_pipeline(workspace=worktree_path, language=self.config.language)
        _save_pipeline_baseline(self.experiment_dir, result)
    finally:
        self.workspace_manager.remove_worktree(worktree_path, branch_name)
```

### Pattern: Shared Resource Load Order in Stage Functions

```python
def stage_capture_baseline(ctx):
    if ctx.pipeline_baseline is not None:
        return  # already set (shared by runs in SubTestExecutor)

    # Preferred: experiment-level (set once for whole experiment)
    if ctx.experiment_dir is not None:
        ctx.pipeline_baseline = _load_pipeline_baseline(ctx.experiment_dir)

    if ctx.pipeline_baseline is None:
        # Backward compat: subtest-level from older checkpoints
        ctx.pipeline_baseline = _load_pipeline_baseline(ctx.run_dir.parent)

    if ctx.pipeline_baseline is None:
        # Fallback: inline capture (should not happen in normal flow)
        ctx.pipeline_baseline = _run_build_pipeline(...)
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| Computing `experiment_dir` from `run_dir.parent.parent.parent` | `stage_capture_baseline` tests failed with wrong directory | Test fixtures for `stage_capture_baseline` don't use the full 4-level directory hierarchy. Path arithmetic assumes fixed depth that tests don't replicate. Use `ctx.experiment_dir` directly. |
| Resetting COMPLETE tier to `"subtests_running"` when subtests are missing | New subtests still didn't run | `"subtests_running"` skips `action_pending()`. `action_config_loaded()` uses `tier_ctx.tier_config` pre-populated at resume time — limited to the old `max_subtests` count. Must reset to `"pending"` so `action_pending()` re-runs with full list. |
| Treating `test_sets_experiment_state_to_interrupted` (asserting `"INTERRUPTED"`) as correct | Fixing production code caused test failure | The test was documenting the bug. When a test documents behavior that seems wrong, check if it's documenting a bug rather than correct behavior. |

## Results and Parameters

### Checkpoint State Flow (resume with expanded subtests)

```
Before fix:
  experiment_state=complete -> STEP 3 skips (not failed/interrupted)
  needs_execution={} -> empty because _check_tiers_need_execution missed subtests
  Result: experiment stays 'complete', new subtests never run

After fix:
  experiment_state=complete -> STEP 3 skips (correct, experiment wasn't interrupted)
  needs_execution={"T0"} -> detects config_subtests - checkpoint_subtests
  experiment_state reset to "tiers_running"
  T0 reset to "pending" -> action_pending reloads full subtest list
```

### Key Files

| File | Role |
|------|------|
| `<project-root>/scylla/e2e/runner.py` | Ephemeral CLI field handling (STEP 2), `_check_tiers_need_execution()`, tier state reset logic, `_capture_experiment_baseline()`, `_handle_experiment_interrupt()` INTERRUPTED fix |
| `<project-root>/scylla/e2e/stages.py` | `stage_capture_baseline()` load order |
| `<project-root>/tests/unit/e2e/test_runner.py` | INTERRUPTED test update + new tests for ephemeral handling and missing subtest detection |
| `<project-root>/tests/unit/e2e/test_stages.py` | Baseline tests split into experiment-level + backward-compat |

### Test Patterns

```python
# Testing ephemeral field clearing
cli_config = ExperimentConfig(..., max_subtests=None)
saved_config = ExperimentConfig(..., max_subtests=2)
# After resume: runner.config.max_subtests must be None

# Testing missing subtest detection
# tier_manager mock returns 4 subtests, checkpoint has 2
runner.tier_manager.load_tier_config.return_value = TierConfig(subtests=[...4 items...])
# After resume: tier_states["T0"] == "pending"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1109 | [notes.md](../../references/notes.md) |
