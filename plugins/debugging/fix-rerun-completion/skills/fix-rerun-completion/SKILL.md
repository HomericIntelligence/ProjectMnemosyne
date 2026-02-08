---
name: "Skill: Fix Rerun Completion Failures"
description: "Skill: Fix Rerun Completion Failures"
category: debugging
date: 2026-02-02
user-invocable: false
---
# Skill: Fix Rerun Completion Failures

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-02 |
| **Objective** | Fix three critical issues preventing rerun scripts from completing all remaining cases in experiment directories |
| **Outcome** | ✅ All 1130 agent runs and 3390 judge slots completed successfully |
| **Files Modified** | `src/scylla/e2e/rerun.py`, `src/scylla/e2e/llm_judge.py` |
| **Tests** | 160 passed, 1 skipped |

## When to Use This Skill

Use this skill when:

1. **Rerun scripts don't complete all cases** - Dry-run shows incomplete runs/judges after rerun execution
2. **Missing result files** - `run_result.json` missing despite agent/judge data existing
3. **Judge reruns fail with FileNotFoundError** - Workspace directory has been cleaned up
4. **Infinite judge retry loops** - Fallback judge succeeds but judgment.json not persisted

**Trigger Pattern**:
```bash
# Agent reruns show incomplete
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run
# Output: "⚠ results: N" instead of "✓ completed: N"

# Judge reruns show failed slots
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run
# Output: "✗ failed: N" instead of "✓ complete: N"
```

## Problem Diagnosis

### Issue 1: Missing run_result.json Not Regenerated

**Symptom**: Agent shows RESULTS status (agent/result.json + judge/result.json exist, but run_result.json missing)

**Root Cause**: `rerun.py` only handled missing `agent/result.json`, not missing `run_result.json`

**Detection**:
```bash
# Find runs with agent/judge data but no run_result.json
find <exp_dir> -type f -name "result.json" -path "*/agent/result.json" \
  -exec sh -c 'dir=$(dirname $(dirname "$1")); [ ! -f "$dir/run_result.json" ] && echo "$dir"' _ {} \;
```

### Issue 2: Judge Crashes on Missing Workspace

**Symptom**: Judge reruns fail with `FileNotFoundError` in subprocess.run

**Root Cause**: `subprocess.run(cwd=workspace)` fails when workspace directory cleaned up

**Detection**:
```bash
# Check judge logs for FileNotFoundError
grep -r "FileNotFoundError.*workspace" <exp_dir>/*/*/run_*/judge/judge_*/stderr.log
```

### Issue 3: Fallback Judge Infinite Retry

**Symptom**: Judge slot marked as failed despite fallback executing successfully

**Root Cause**: Fallback judge returns result but doesn't save `judgment.json`, so next rerun treats it as missing

**Detection**:
```bash
# Find judge directories with timing.json but no judgment.json
find <exp_dir> -type d -name "judge_*" -exec sh -c \
  '[ -f "$1/timing.json" ] && [ ! -f "$1/judgment.json" ] && echo "$1"' _ {} \;
```

## Verified Workflow

### Fix 1: Regenerate run_result.json from Existing Data

**Location**: `src/scylla/e2e/rerun.py` lines 673-770

**Implementation**:
1. Add `elif` block after agent/result.json regeneration
2. Check if `run_result.json` missing but `agent/result.json` exists
3. Reconstruct from:
   - `agent/result.json` → exit_code, token_stats, cost_usd
   - `judge/result.json` → score, passed, grade, reasoning, criteria_scores
   - `agent/timing.json` → agent_duration_seconds
   - `judge/judge_NN/timing.json` → sum for judge_duration_seconds
   - `judge/judge_NN/judgment.json` + `MODEL.md` → judges array

**Key Details**:
- Token calculation: `tokens_input = input_tokens + cache_read_tokens`
- Token stats uses `cache_creation_tokens` and `cache_read_tokens` (not `cache_creation_input_tokens`)
- Extract model from MODEL.md: `**Model**: <model-name>` line
- Extract judge number from directory: `judge_01` → 1

**Code Pattern**:
```python
# Read from all sources
agent_result = json.load(open(agent_dir / "result.json"))
judge_result = json.load(open(judge_dir / "result.json"))
agent_timing = json.load(open(agent_dir / "timing.json"))

# Sum judge timings
judge_duration_total = sum(
    json.load(open(jdir / "timing.json")).get("judge_duration_seconds", 0.0)
    for jdir in sorted(judge_dir.glob("judge_*"))
    if (jdir / "timing.json").exists()
)

# Build judges array
judges = []
for judge_subdir in sorted(judge_dir.glob("judge_*")):
    if (judge_subdir / "judgment.json").exists() and (judge_subdir / "MODEL.md").exists():
        # Extract from files and append to judges
```

### Fix 2: Graceful Workspace Handling

**Location**: `src/scylla/e2e/llm_judge.py` lines 1002-1006

**Implementation**:
```python
# Before (crashes if workspace deleted)
cwd = workspace if workspace else None

# After (graceful fallback)
cwd = None
if workspace and workspace.exists():
    cwd = workspace
```

**Rationale**: Judge prompt already contains full evaluation context (workspace state, patchfile, pipeline results), so judge can evaluate without workspace file access.

### Fix 3: Persist Fallback Judgment

**Location**: `src/scylla/e2e/llm_judge.py` lines 921-953

**Implementation**:
1. Get fallback result BEFORE writing timing
2. Save timing.json with `"fallback": True` flag
3. Save judgment.json with:
   - Fallback result fields (score, passed, grade, reasoning)
   - `"fallback": True` flag
   - `"fallback_reason": str(exception)` for debugging

**Code Pattern**:
```python
except Exception as e:
    fallback_result = _fallback_judge(agent_output)

    if actual_judge_dir:
        # Save timing with fallback flag
        json.dump({
            "judge_duration_seconds": judge_duration,
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "failed": True,
            "fallback": True,
        }, open(actual_judge_dir / "timing.json", "w"), indent=2)

        # Save judgment with fallback metadata
        judgment_data = fallback_result.to_dict()
        judgment_data["fallback"] = True
        judgment_data["fallback_reason"] = str(e)
        json.dump(judgment_data, open(actual_judge_dir / "judgment.json", "w"), indent=2)

    return fallback_result
```

## Failed Attempts

### ❌ Initial Token Calculation Error

**What Was Tried**: Used `cache_read_input_tokens` instead of `cache_read_tokens`

**Why It Failed**:
- Token stats structure uses `cache_read_tokens` (not `cache_read_input_tokens`)
- Resulted in `tokens_input = 33` instead of `195768` (missing cache reads)

**Lesson**: Always verify field names by reading actual data files, not assuming from memory

**Fix**: Changed to `token_stats.get("cache_read_tokens", 0)`

### ❌ Assumed run_result.json Would Self-Classify as Complete

**What Was Tried**: Expected regenerated run_result.json to immediately show as "completed" status

**Why It Failed**:
- First run showed "⚠ results: 1" before regeneration
- After regeneration still showed "⚠ results: 1" in same execution
- Classification happens at scan time, not after regeneration

**Lesson**: Rerun statistics classification happens once per execution. Need fresh dry-run to see updated status.

**Fix**: Ran separate `--dry-run` after regeneration to verify completion

## Verification Steps

### 1. Verify File Structure

```bash
# Check regenerated run_result.json structure
cat <exp_dir>/T5/13/run_10/run_result.json | jq '{run_number, tokens_input, judge_score, judges: (.judges | length)}'

# Expected output:
{
  "run_number": 10,
  "tokens_input": 195768,  # NOT 33 (input_tokens alone)
  "judge_score": 0.9866666666666667,
  "judges": 3  # All judges present
}
```

### 2. Verify Agent Completion

```bash
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run

# Expected final state:
# Total expected runs:     1130
#   ✓ completed:           1130
#   ⚠ results:             0
#   ✗ failed:              0
```

### 3. Verify Judge Completion

```bash
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run

# Expected final state:
# Total expected judge slots: 3390
#   judge_01: ✓ complete: 1130    ✗ failed: 0
#   judge_02: ✓ complete: 1130    ✗ failed: 0
#   judge_03: ✓ complete: 1130    ✗ failed: 0
```

### 4. Verify Fallback Judgments

```bash
# Find fallback judgments
find <exp_dir> -name "judgment.json" -exec sh -c \
  'jq -e ".fallback == true" "$1" > /dev/null 2>&1 && echo "$1"' _ {} \;

# Check fallback contains required fields
jq '{fallback, fallback_reason, score, passed, grade}' <fallback_judgment.json>
```

## Results & Parameters

### Test Environment

- **Experiment**: `~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001/`
- **Total Runs**: 1130 (7 tiers × 10 tests × variable runs)
- **Total Judge Slots**: 3390 (1130 runs × 3 judges)
- **Python Version**: 3.14
- **Mojo Version**: 0.26.1

### Before Fixes

| Metric | Status |
|--------|--------|
| Agent runs completed | 1129/1130 |
| Agent runs RESULTS | 1 (T5/13/run_10) |
| Judge slots complete | 3388/3390 |
| Judge slots failed | 2 (T1/10/run_09 judge_01, T4/07/run_09 judge_01) |

### After Fixes

| Metric | Status |
|--------|--------|
| Agent runs completed | 1130/1130 ✅ |
| Agent runs RESULTS | 0 ✅ |
| Judge slots complete | 3390/3390 ✅ |
| Judge slots failed | 0 ✅ |
| E2E tests | 160 passed, 1 skipped ✅ |

### Specific Fixes Verified

1. **T5/13/run_10**: run_result.json regenerated with correct token calculations
   - tokens_input: 195768 (33 input + 195735 cache_read)
   - judge_score: 0.9866666666666667
   - judges array: 3 entries with full metadata

2. **T1/10/run_09 judge_01**: Completed after workspace handling fix
   - judgment.json created despite missing workspace
   - score: 0.76, passed: True, grade: B

3. **T4/07/run_09 judge_01**: Completed after workspace handling fix
   - judgment.json created despite missing workspace
   - score: 0.88, passed: True, grade: A

## Related Commands

```bash
# Regenerate missing agent/result.json (original functionality)
pixi run python scripts/rerun_agents.py <exp_dir> --status results -v

# Rerun failed judge slots
pixi run python scripts/rerun_judges.py <exp_dir> --status failed -v

# Check for missing run_result.json files
pixi run python scripts/regenerate_results.py <exp_dir>

# Run e2e tests
pixi run python -m pytest tests/unit/e2e/ -x -q
```

## Key Insights

1. **Always check file existence before using as subprocess cwd** - Workspaces may be cleaned up during rerun cycles

2. **Fallback paths must persist results** - Silent successes without persistence cause infinite retry loops

3. **Token calculation requires understanding actual field names** - Don't assume field names match patterns from other contexts

4. **Classification happens at scan time** - Need fresh execution to see updated status after regeneration

5. **Verify all data sources exist before reconstruction** - Missing timing.json or judgment.json files should be handled gracefully

## Prevention

To prevent similar issues in the future:

1. **Add regeneration for all result file types** - Not just agent/result.json
2. **Always check path existence before filesystem operations** - Especially for cleaned-up directories
3. **Persist all success/failure states** - Don't rely on memory-only results
4. **Test edge cases in unit tests**:
   - Missing workspace directories
   - Missing intermediate result files
   - Fallback paths

## References

- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/339
- Affected files: `src/scylla/e2e/rerun.py`, `src/scylla/e2e/llm_judge.py`
- Test suite: `tests/unit/e2e/`
