# Raw Session Notes: Fix Rerun Completion Failures

## Session Timeline

### Initial Problem Analysis

User provided plan with three distinct issues:

1. **rerun_agents.py** - T5/13/run_10 with RESULTS status (1 run)
   - Has `agent/result.json` and `judge/result.json`
   - Missing `run_result.json`
   - Regeneration only handled missing `agent/result.json`

2. **rerun_judges.py** - T1/10/run_09 + T4/07/run_09 judge_01 (2 slots)
   - Missing workspace causes `FileNotFoundError` in `subprocess.run(cwd=...)`
   - Fallback judge doesn't save `judgment.json` → infinite retry

3. **regenerate_results.py** - Downstream of Issue 1
   - Can't find missing `run_result.json` in scan

### Implementation Order

Followed plan recommendation:
1. Fix `llm_judge.py` (Fix 2a + 2b) - judge reruns
2. Fix `rerun.py` (Fix 1) - agent RESULTS regeneration
3. Skip optional diagnostic in `regenerate.py`

### Fix 2a: Workspace Handling (lines 988-1006)

Original code:
```python
cwd = workspace if workspace else None
```

Changed to:
```python
cwd = None
if workspace and workspace.exists():
    cwd = workspace
```

### Fix 2b: Fallback Judgment Persistence (lines 921-953)

Key change: Call `_fallback_judge()` BEFORE writing timing, then save both timing.json and judgment.json with fallback metadata.

Added fields to judgment.json:
- `"fallback": True`
- `"fallback_reason": str(e)`

### Fix 1: run_result.json Regeneration (lines 673-770)

**Critical Bug Found During Implementation**: Initial token calculation was wrong.

Original attempt:
```python
"tokens_input": (
    agent_result.get("token_stats", {}).get("input_tokens", 0)
    + agent_result.get("token_stats", {}).get("cache_read_input_tokens", 0)  # WRONG
)
```

Field name should be `cache_read_tokens` not `cache_read_input_tokens`.

Token stats structure from actual files:
```json
{
  "input_tokens": 33,
  "output_tokens": 960,
  "cache_creation_tokens": 4022,
  "cache_read_tokens": 195735
}
```

Fixed calculation:
```python
token_stats = agent_result.get("token_stats", {})
"tokens_input": (
    token_stats.get("input_tokens", 0)
    + token_stats.get("cache_read_tokens", 0)  # CORRECT
)
```

Result: 33 + 195735 = 195768 ✓

### Reconstruction Process

run_result.json structure requires:
- `run_number` - from run_info
- `exit_code`, `token_stats`, `cost_usd` - from `agent/result.json`
- `tokens_input`, `tokens_output` - calculated from token_stats
- `duration_seconds` - sum of agent + judge durations
- `agent_duration_seconds` - from `agent/timing.json`
- `judge_duration_seconds` - sum from all `judge_NN/timing.json`
- `judge_score`, `judge_passed`, `judge_grade`, `judge_reasoning` - from `judge/result.json`
- `judges` - array built from `judge_NN/` subdirectories
- `workspace_path`, `logs_path`, `command_log_path` - constructed from paths
- `criteria_scores` - from `judge/result.json`

### Judges Array Construction

For each `judge_NN/` directory:
1. Read `judgment.json` for score/passed/grade/reasoning
2. Parse `MODEL.md` to extract model name
3. Extract judge number from directory name
4. Build entry with all fields

MODEL.md format:
```markdown
# Judge Model Information

**Model**: claude-opus-4-5-20251101
**Claude Code Version**: 2.1.29 (Claude Code)
**Timestamp**: 2026-02-01T19:14:02.617385+00:00
```

Extract line starting with `**Model**:` and parse value after colon.

## Test Results

### Initial Test Run (After Implementation)

```bash
pixi run python -m pytest tests/unit/e2e/ -x -q
```

Result: 160 passed, 1 skipped ✓

### Agent Regeneration Test

```bash
pixi run python scripts/rerun_agents.py <exp_dir> --status results -v
```

Output showed regeneration but status still showed "results: 1" in same execution.

**Key Learning**: Classification happens once per execution at scan time. Need fresh dry-run to see updated status.

### Verification Commands

```bash
# Before fix
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run
# completed: 1129, results: 1

# After fix
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run
# completed: 1130, results: 0

# Judge status before
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run
# complete: 3388, failed: 2

# Judge rerun with workspace fix
pixi run python scripts/rerun_judges.py <exp_dir> --status failed -v
# Warnings: "Error getting workspace state: [Errno 2] No such file or directory"
# But succeeded anyway (graceful fallback)

# Judge status after
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run
# complete: 3390, failed: 0
```

## Code Formatting Issues

Pre-commit hook caught line length violations:
- Line 698: 103 chars (judge_duration_seconds line)
- Line 734: 107 chars (total_duration calculation)
- Line 770: 101 chars (error message)

Ruff-format automatically fixed by breaking into multi-line expressions.

## Final PR Creation

Branch: `fix-rerun-completion-failures`
PR: https://github.com/HomericIntelligence/ProjectScylla/pull/339

Files changed:
- `src/scylla/e2e/llm_judge.py`: +28 lines (workspace check + fallback persistence)
- `src/scylla/e2e/rerun.py`: +122 lines (run_result.json regeneration)

Total: 2 files changed, 128 insertions(+), 6 deletions(-)

## Lessons Learned

1. **Check actual data structures** - Don't assume field names
2. **Classification timing matters** - Scan-time vs runtime
3. **Graceful degradation** - Judge can work without workspace access
4. **Persist all results** - Including fallback paths
5. **Test edge cases** - Missing directories, missing files
6. **Follow the plan** - Implementation order matters for dependencies

## Questions Answered

Q: Why does tokens_input differ from just input_tokens?
A: tokens_input includes both fresh input tokens and cache read tokens, representing total tokens processed.

Q: Why can judge work without workspace access?
A: Judge prompt contains full evaluation context (workspace state dump, patchfile, pipeline results), so it has all information needed.

Q: Why does fallback judge need to save judgment.json?
A: Without persistence, next rerun sees missing judgment.json and tries again → infinite loop.

Q: How to verify regenerated run_result.json is valid?
A: Check tokens_input calculation (should be input + cache_read, not just input), judges array length, and all required fields present.
