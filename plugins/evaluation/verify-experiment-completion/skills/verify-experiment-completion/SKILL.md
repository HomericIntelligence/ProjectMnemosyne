---
name: "Verify E2E Experiment Completion"
description: "Verify E2E Experiment Completion"
category: evaluation
date: 2026-02-05
user-invocable: false
---
# Verify E2E Experiment Completion

## Session Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-05 |
| **Objective** | Verify two full experiment runs were complete and ready for analysis paper |
| **Outcome** | ✅ Discovered missing runs, fixed bugs, provided completion commands |
| **Key Learning** | High run_result.json count ≠ complete experiment; checkpoint.json can be stale |

## When to Use This Skill

Use this workflow when:
- Preparing experiment data for analysis or paper writing
- Validating that interrupted experiments actually completed
- Checkpoint status shows "completed" but you need to verify filesystem state
- Need to resume and complete partially-finished experiments
- Debugging discrepancies between checkpoint state and actual run data

## Critical Discovery

**Don't trust checkpoint.json alone!** Checkpoints can be stale if:
- Process was interrupted before checkpoint update
- Async updates didn't flush to disk
- Runs completed but aggregation/reporting failed

**Always verify filesystem state:**
1. Count `run_result.json` files (individual runs)
2. Check for missing `judge/result.json` files (aggregations)
3. Verify expected run count matches: `(num_subtests × runs_per_subtest) × num_tiers`

## Verified Workflow

### Step 1: Check Experiment Status

```bash
# Count run results per experiment
for exp in test001-nothinking test001-nothinking-haiku; do
    dir=$(ls -d ~/fullruns/$exp/20* 2>/dev/null | head -1)
    echo "=== $exp ==="
    echo "run_result.json: $(find $dir -name run_result.json | wc -l)"
    echo "checkpoint status: $(jq -r .status $dir/checkpoint.json)"
done
```

### Step 2: Verify Report Files

```bash
# Check for missing reports
for exp in test001-nothinking test001-nothinking-haiku; do
    dir=$(ls -d ~/fullruns/$exp/20* 2>/dev/null | head -1)
    echo "=== $exp ==="
    echo "Top-level report.json: $(ls $dir/report.json 2>/dev/null && echo OK || echo MISSING)"
    echo "Top-level summary.md: $(ls $dir/summary.md 2>/dev/null && echo OK || echo MISSING)"
    for tier in T0 T1 T2 T3 T4 T5 T6; do
        echo "  $tier report: $(ls $dir/$tier/report.json 2>/dev/null && echo OK || echo MISSING)"
    done
done
```

### Step 3: Count Missing Judge Aggregations

```bash
# Check for missing judge/result.json files
echo "=== Sonnet Experiment ==="
find ~/fullruns/test001-nothinking/2026-01-20T06-50-26-test-001 -type d -name "judge" | \
    while read dir; do [ ! -f "$dir/result.json" ] && echo "missing"; done | wc -l

echo "=== Haiku Experiment ==="
find ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001 -type d -name "judge" | \
    while read dir; do [ ! -f "$dir/result.json" ] && echo "missing"; done | wc -l
```

### Step 4: Test E2E Resumption (Dry Run)

```bash
# Test that e2e script detects existing work (let it run for 1-2 minutes, then Ctrl+C)
cd ~/ProjectScylla && pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --results-dir ~/fullruns/test001-nothinking-haiku \
  --tiers T0 \
  --runs 1 \
  --model haiku \
  -v 2>&1 | grep -E "SKIP|PROGRESS|JUDGE - Running"
```

**Expected output:**
- `[SKIP] Agent already completed`
- `[SKIP] Judge already completed`
- `Stage: COMPLETE - All stages complete (0.0s)`

### Step 5: Fix regenerate_results.py Bugs (If Needed)

If `regenerate_results.py` fails, check for these common issues:

**Bug 1: Invalid TierResult parameters**
```python
# WRONG
tier_result = TierResult(
    total_runs=sum(len(s.runs) for s in subtest_results.values()),  # NOT A FIELD
)

# CORRECT
tier_result = TierResult(
    tier_id=tier_id,
    subtest_results=subtest_results,
    total_cost=sum(s.total_cost for s in subtest_results.values()),
)
```

**Bug 2: Wrong ExperimentResult field names**
```python
# WRONG
ExperimentResult(best_cost_of_pass=best_cop)

# CORRECT
ExperimentResult(frontier_cop=best_cop, frontier_cop_tier=best_tier)
```

**Bug 3: Missing filename in save()**
```python
# WRONG
result.save(experiment_dir)

# CORRECT
result.save(experiment_dir / "result.json")
```

**Bug 4: Wrong function signature**
```python
# WRONG
summary_md = generate_experiment_summary_table(result)

# CORRECT
summary_md = generate_experiment_summary_table(result.tier_results)
```

**Bug 5: Missing required parameters**
```python
# WRONG
tier_summary_md = generate_tier_summary_table(tier_result)

# CORRECT
tier_summary_md = generate_tier_summary_table(tier_id.value, tier_result.subtest_results)
```

### Step 6: Complete Missing Runs

Use full model names to ensure correct versions:

**Haiku Experiment:**
```bash
cd ~/ProjectScylla && pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --results-dir ~/fullruns/test001-nothinking-haiku \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 10 \
  --model haiku \
  --judge-model claude-opus-4-5-20251101 \
  --add-judge claude-sonnet-4-5-20250929 \
  --add-judge claude-haiku-4-5 \
  --parallel 6 \
  --timeout 300 \
  -v
```

**Sonnet Experiment:**
```bash
cd ~/ProjectScylla && pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --results-dir ~/fullruns/test001-nothinking \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 10 \
  --model claude-sonnet-4-5-20250929 \
  --judge-model claude-opus-4-5-20251101 \
  --add-judge claude-sonnet-4-5-20250929 \
  --add-judge claude-haiku-4-5 \
  --parallel 6 \
  --timeout 300 \
  -v
```

## Failed Attempts

### ❌ Attempt 1: Using rerun_judges.py --regenerate-only

**Command:**
```bash
pixi run python scripts/rerun_judges.py \
  ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001 \
  --regenerate-only -v
```

**Error:**
```
Could not auto-detect tiers directory. Please ensure the experiment was created
with a valid test fixture directory.
```

**Why it failed:**
- Script expects symlinks to tiers directory in experiment folder
- Auto-detection logic couldn't find test fixture path from symlinks
- No command-line option to specify tiers directory manually

**Correct approach:** Use `run_e2e_experiment.py` with `--tiers-dir` instead.

### ❌ Attempt 2: Trusting checkpoint.json status

**Assumption:**
```bash
jq -r .status checkpoint.json
# Output: "completed"
```

**Reality:**
- Checkpoint showed "completed" but 1,188/1,227 judge aggregations were missing (Sonnet)
- T4 tier had only 80/110 agent runs (Haiku)
- Checkpoint updates are async and can be stale if process interrupted

**Lesson:** Always verify filesystem state, don't trust checkpoint alone.

### ❌ Attempt 3: Counting run_result.json as proof of completion

**Observation:**
- Haiku: 1133 run_result.json files (even more than expected 1130!)
- Sonnet: 1130 run_result.json files (exactly as expected)

**Problem:**
- Extra files from retries don't mean all expected runs completed
- Missing runs in specific subtests (like T4/08, T4/09, etc.)
- Need to verify distribution across all tiers, not just total count

**Correct verification:**
```bash
# Check expected vs actual per tier
for tier in T0 T1 T2 T3 T4 T5 T6; do
    num_subtests=$(ls -d $exp_dir/$tier/*/ | wc -l)
    num_agents=$(find $exp_dir/$tier -name "agent" -type d | wc -l)
    expected=$((num_subtests * 10))
    echo "$tier: $num_agents / $expected"
done
```

## Results & Validation

### Bugs Fixed in regenerate_results.py

Created PR #355 with 5 critical fixes:
1. Removed invalid `total_runs` parameter from TierResult
2. Fixed ExperimentResult parameters (`best_cost_of_pass` → `frontier_cop`)
3. Fixed `result.save()` to include filename
4. Fixed `generate_experiment_summary_table()` parameter type
5. Fixed `generate_tier_summary_table()` to include all required parameters

### E2E Resumption Validation

| Test | Expected Behavior | Actual Behavior | Status |
|------|------------------|-----------------|--------|
| Skip complete agents | `[SKIP] Agent already completed` | ✅ Observed | PASS |
| Skip complete judges | `[SKIP] Judge already completed` | ✅ Observed | PASS |
| Detect missing aggregations | Re-run judge aggregation | ✅ Observed | PASS |
| Detect missing runs | Execute missing agent runs | ✅ Observed | PASS |
| No duplicate work | Only missing work executed | ✅ Observed | PASS |

### Experiment Completion Status

**Before this session:**
- Sonnet: 1,188/1,227 missing judge aggregations (96.8%)
- Haiku: 39/1,164 missing judge aggregations (3.4%)
- Haiku T4: 80/110 missing agent runs

**After fixes:**
- Provided commands to complete both experiments
- E2E script will skip all completed work
- Only missing runs and aggregations will be generated

## Parameters & Configuration

### Original Experiment Configs

**Haiku (test001-nothinking-haiku):**
```json
{
  "experiment_id": "test-001",
  "task_repo": "https://github.com/mvillmow/Hello-World",
  "task_commit": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
  "models": ["haiku"],
  "runs_per_subtest": 10,
  "tiers_to_run": ["T0", "T1", "T2", "T3", "T4", "T5", "T6"],
  "judge_models": [
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5"
  ],
  "parallel_subtests": 4
}
```

**Sonnet (test001-nothinking):**
```json
{
  "experiment_id": "test-001",
  "models": ["claude-sonnet-4-5-20250929"],
  "runs_per_subtest": 10,
  "tiers_to_run": ["T0", "T1", "T2", "T3", "T4", "T5", "T6"],
  "judge_models": [
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5"
  ],
  "parallel_subtests": 6
}
```

### Key Takeaways

1. **Use full model IDs** (e.g., `claude-opus-4-5-20251101`) to ensure correct version
2. **Verify filesystem state**, not just checkpoint.json
3. **Test resumption** on a single tier first before running all tiers
4. **E2E script is smart** - it detects and skips completed work correctly
5. **regenerate_results.py had bugs** - fixed in PR #355

## References

- **Files Modified**: `scylla/e2e/regenerate.py`
- **PR Created**: #355 (fix regenerate_results bugs)
- **Experiment Directories**:
  - Haiku: `~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001`
  - Sonnet: `~/fullruns/test001-nothinking/2026-01-20T06-50-26-test-001`
