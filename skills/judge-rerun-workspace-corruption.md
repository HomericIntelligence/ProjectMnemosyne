---
name: judge-rerun-workspace-corruption
description: Fix judge reruns producing incorrect results due to workspace corruption
category: architecture
date: 2026-02-09
version: 1.0.0
user-invocable: false
---
# Judge Rerun Workspace Corruption Fix

| Field | Value |
|-------|-------|
| Date | 2026-02-09 |
| Objective | Fix judge reruns that were judging against reset/empty workspaces instead of original agent work |
| Root Cause | Judge reruns rebuilt prompts from workspace state, which was corrupted/reset by agent rerun scripts |
| Outcome | ✅ Judges now reuse saved `judge_prompt.md` from original run; workspace recreation blocked for completed runs |
| Files Changed | `scylla/e2e/llm_judge.py`, `rerun_judges.py`, `rerun.py`, `subtest_executor.py`, `regenerate.py` |

## When to Use This Skill

Use this pattern when:
- Judge evaluations are producing incorrect results after workspace operations
- Rerun scripts are destroying agent work before re-judging
- You need to preserve evaluation context across multiple script invocations
- Fallback mechanisms are masking real failures with synthetic scores

## Problem Context

### The Workspace Corruption Issue

When running `rerun_agents.py` followed by `rerun_judges.py`:
1. Agent rerun script recreated git worktrees, destroying agent's work
2. Judge rerun script rebuilt judge prompts from the now-empty workspace
3. Judges correctly gave F-grades for empty workspaces (not the original agent work)

### The Fallback Judge Masking Issue

When LLM judges hit rate limits or errors:
1. Fallback judge gave blanket 0.7/grade-C scores regardless of actual work
2. Produced 2307/3600 (64%) garbage judgments in test001-nothinking
3. Masked the workspace corruption issue by giving passing grades to empty workspaces

## Verified Architecture Pattern

### 1. Save Judge Context at Execution Time

**Where**: `scylla/e2e/llm_judge.py:1409`

```python
# Save the prompt to run level (shared by all judges) - write once
run_dir = judge_dir.parent.parent
judge_prompt_path = run_dir / "judge_prompt.md"
if not judge_prompt_path.exists():
    judge_prompt_path.write_text(prompt)
```

**Why**: Captures workspace state at the moment of agent execution, before any subsequent operations.

### 2. Reuse Saved Context During Reruns

**Where**: `scylla/e2e/rerun_judges.py:342-390`

```python
# Check if saved judge_prompt.md exists (from original run)
saved_judge_prompt_path = run_dir / "judge_prompt.md"

if saved_judge_prompt_path.exists():
    judge_prompt = saved_judge_prompt_path.read_text()

    # Call lower-level functions directly to bypass prompt rebuilding
    from scylla.e2e.llm_judge import _call_claude_judge, _parse_judge_response

    stdout, stderr, result = _call_claude_judge(judge_prompt, model, workspace)
    judge_result = _parse_judge_response(result)
    # ... save logs and timing
else:
    logger.warning("Saved judge_prompt.md not found, rebuilding (may be inaccurate)")
    # Fallback to run_llm_judge() which rebuilds from workspace
```

**Why**: Uses original evaluation context even if workspace was subsequently modified or reset.

### 3. Block Workspace Recreation for Completed Runs

**Where**: `scylla/e2e/rerun.py:320-330`

```python
# Safety check: don't destroy workspaces for completed or results-only runs
if run_info.status in (RunStatus.COMPLETED, RunStatus.RESULTS):
    logger.error(
        f"Refusing to rerun {tier_id}/{subtest_id}/run_{run_number:02d}: "
        f"status is {run_info.status.value}, which should not require agent re-execution. "
        f"Use regenerate.py for RESULTS status or rerun_judges.py for COMPLETED status."
    )
    return None
```

**Why**: Prevents accidental workspace destruction for runs that only need metadata regeneration or re-judging.

### 4. Remove Fallback Mechanisms That Mask Failures

**Where**: `scylla/e2e/llm_judge.py:886-919`

```python
# BEFORE: try/except that catches everything and falls back
try:
    judge_result = run_llm_judge(...)
except Exception as e:
    fallback_result = _fallback_judge(agent_output)  # Blanket 0.7 score
    return fallback_result

# AFTER: Let exceptions propagate for proper error handling
stdout, stderr, result = _call_claude_judge(judge_prompt, model, workspace)
judge_result = _parse_judge_response(result)
# ... save logs
return judge_result  # Exception propagates if judge fails
```

**Why**: Makes failures visible so they can be properly debugged and retried, rather than masked by synthetic scores.

### 5. Add Exception Handling at Caller Sites

**Where**: `scylla/e2e/subtest_executor.py:1487`, `regenerate.py:310`

```python
try:
    judge_result = run_llm_judge(...)
    judges.append(judge_summary)
except Exception as e:
    # Log error with full context
    logger.error(f"Judge {judge_num} failed with model {model}: {e}", exc_info=True)

    # Save error artifacts
    timing_file = judge_specific_dir / "timing.json"
    with open(timing_file, "w") as f:
        json.dump({
            "judge_duration_seconds": 0.0,
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "failed": True,
            "error": str(e),
        }, f, indent=2)

    error_file = judge_specific_dir / "error.log"
    error_file.write_text(f"Judge failed: {e}\n")

    # Re-raise to mark run as failed (subtest_executor)
    # OR continue to next (regenerate.py)
    raise  # or continue
```

**Why**: Saves debugging artifacts before failing, enables retry logic at appropriate level.

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Verified Workflow

Steps that worked:
1. Step 1
2. Step 2

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Key Parameters

### Run Status Classifications

| Status | Definition | Requires Agent Rerun? | Requires Judge Rerun? |
|--------|------------|----------------------|----------------------|
| COMPLETED | Agent + judge + run_result.json exist | ❌ No | Maybe (if judge failed) |
| RESULTS | Agent finished, missing result files | ❌ No (regenerate only) | ✅ Yes |
| FAILED | Agent ran but failed (stderr, no output) | ✅ Yes | ✅ Yes (after agent) |
| PARTIAL | Agent started but incomplete | ✅ Yes | ✅ Yes (after agent) |
| MISSING | Run directory doesn't exist | ✅ Yes | ✅ Yes (after agent) |

### File Locations

| File | Purpose | Scope |
|------|---------|-------|
| `run_dir/judge_prompt.md` | Full judge evaluation context | Per-run (shared by all judges) |
| `run_dir/judge/judge_01/judgment.json` | Individual judge result | Per-judge |
| `run_dir/judge/judge_01/timing.json` | Judge execution timing + error info | Per-judge |
| `run_dir/workspace/` | Git worktree with agent's work | Per-run |
| `run_dir/agent/result.json` | Agent execution result | Per-run |

### Script Coordination

| Script | Purpose | Workspace Handling |
|--------|---------|-------------------|
| `rerun_agents.py` | Re-run failed/incomplete agents | Recreates workspace for FAILED/PARTIAL/MISSING |
| `rerun_judges.py` | Re-run failed judge evaluations | Reuses existing workspace + saved judge_prompt.md |
| `regenerate.py` | Rebuild result.json from logs | Reuses existing workspace (no recreation) |

## Testing

```bash
# 1. Run e2e tests to ensure no regressions
pixi run python -m pytest tests/unit/e2e/ -x -q

# 2. Verify _fallback_judge is fully removed
grep -r "_fallback_judge" scylla/e2e/

# 3. Verify no "fallback" references remain in judge logic
grep -rn "fallback" scylla/e2e/llm_judge.py
```

## References

- Original issue: F-grade failures in `~/fullruns/test001-nothinking` from destroyed workspaces
- Fallback judge produced 2307/3600 (64%) garbage judgments
- Plan transcript: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/9bfdc6b7-e7ea-4558-a17e-188ded1a7188.jsonl`

## Related Patterns

- [Error Handling](.claude/shared/error-handling.md) - Retry strategy, timeout handling, escalation
- [Evaluation Guidelines](.claude/shared/evaluation-guidelines.md) - Evaluation methodology best practices
- [Metrics Definitions](.claude/shared/metrics-definitions.md) - Complete metrics definitions

---

**Last Updated**: 2026-02-09
**Tested On**: Mojo 0.26.1, Python 3.12
