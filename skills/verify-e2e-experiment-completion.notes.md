# Session Notes: Verify Experiment Completion

## Context

Working on finalizing two full experiment runs for analysis paper:
- test001-nothinking (Sonnet 4.5)
- test001-nothinking-haiku (Haiku 4.5)

Initial belief: Experiments were complete based on high run_result.json counts
Reality: Experiments had missing runs and missing judge aggregations

## Timeline

1. **Initial Assessment** (Planning Phase)
   - Checked run_result.json counts: 1130 (Sonnet), 1133 (Haiku)
   - Assumed complete based on counts
   - Plan focused on regenerating reports only

2. **Bug Discovery** (Regeneration Attempt)
   - Tried `regenerate_results.py` on Haiku experiment
   - Discovered 5 critical bugs preventing regeneration
   - Fixed bugs in PR #355

3. **Validation Testing** (E2E Resumption)
   - Tested e2e script on completed directories
   - Discovered script correctly detects incomplete work
   - Found script was trying to run judges (not just aggregate)

4. **Critical Discovery** (Judge Analysis)
   - Individual judge results exist (judge_01/, judge_02/, judge_03/)
   - BUT aggregated judge/result.json is missing
   - Sonnet: 1,188/1,227 missing (96.8%)
   - Haiku: 39/1,164 missing (3.4%)

5. **Shocking Discovery** (Missing Runs)
   - While monitoring, saw NEW agent runs being executed
   - Haiku T4: Only 80/110 agent directories exist
   - Experiments were NOT actually complete!

## Key Commands Used

### Verification Commands

```bash
# Count run results
find ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001 -name "run_result.json" | wc -l

# Check checkpoint status
jq -r .status ~/fullruns/test001-nothinking-haiku/*/checkpoint.json

# Count missing judge aggregations
find ~/fullruns/test001-nothinking/2026-01-20T06-50-26-test-001 -type d -name "judge" | \
  while read dir; do [ ! -f "$dir/result.json" ] && echo "missing"; done | wc -l
```

### Test Commands

```bash
# Test e2e resumption
cd ~/ProjectScylla && pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --results-dir ~/fullruns/test001-nothinking-haiku \
  --tiers T0 \
  --runs 1 \
  --model haiku \
  -v
```

## Error Messages Encountered

### regenerate_results.py Errors

1. `TierResult.__init__() got an unexpected keyword argument 'total_runs'`
2. `ExperimentResult.__init__() got an unexpected keyword argument 'best_cost_of_pass'`
3. `[Errno 21] Is a directory: '/home/mvillmow/fullruns/.../experiment'`
4. `'ExperimentResult' object has no attribute 'items'`
5. `generate_tier_summary_table() missing 1 required positional argument`

### rerun_judges.py Error

```
Could not auto-detect tiers directory. Please ensure the experiment was created
with a valid test fixture directory.
```

## Observations

### Checkpoint Staleness

The checkpoint.json showed:
- Haiku: status="interrupted" (accurate)
- Sonnet: status="completed" (INACCURATE - missing 1,188 judge aggregations!)

This proved that checkpoint status cannot be trusted alone.

### E2E Resumption Behavior

The e2e script correctly:
- Detected existing agent results and skipped re-running
- Detected missing judge aggregations and regenerated them
- Detected completely missing runs and executed new agents
- Used filesystem state, not checkpoint state

### Judge Directory Structure

Complete run:
```
judge/
├── judge_01/
│   ├── judgment.json
│   └── ...
├── judge_02/
│   ├── judgment.json
│   └── ...
├── judge_03/
│   ├── judgment.json
│   └── ...
├── result.json      # ← AGGREGATED RESULT
└── timing.json
```

Incomplete run (missing aggregation):
```
judge/
├── judge_01/
│   ├── judgment.json
│   └── ...
├── judge_02/
│   ├── judgment.json
│   └── ...
├── judge_03/
│   ├── judgment.json
│   └── ...
└── timing.json      # ← NO result.json!
```

## Lessons Learned

1. **High file count ≠ Complete**: 1133 run_result.json files seemed complete, but was misleading
2. **Verify distribution**: Need to check runs per tier/subtest, not just total count
3. **Checkpoint can lie**: Status="completed" doesn't mean all work is done
4. **Individual vs Aggregated**: Judge results can exist individually but be missing aggregation
5. **Test before trusting**: Always test resumption on a small tier first

## Code Fixes Applied

All fixes in `scylla/e2e/regenerate.py`:

```python
# Fix 1: Remove total_runs
tier_result = TierResult(
    tier_id=tier_id,
    subtest_results=subtest_results,
    best_subtest=best_subtest_id,
    best_subtest_score=best_subtest.median_score,
    total_cost=sum(s.total_cost for s in subtest_results.values()),
-   total_runs=sum(len(s.runs) for s in subtest_results.values()),  # REMOVED
)

# Fix 2: Correct ExperimentResult fields
return ExperimentResult(
    config=config,
    tier_results=tier_results,
    best_overall_tier=best_tier,
-   best_cost_of_pass=best_cop if best_cop != float("inf") else None,
+   frontier_cop=best_cop,
+   frontier_cop_tier=best_tier,
)

# Fix 3: Add filename to save()
- result.save(experiment_dir)
+ result.save(experiment_dir / "result.json")

# Fix 4: Pass correct parameter type
- summary_md = generate_experiment_summary_table(result)
+ summary_md = generate_experiment_summary_table(result.tier_results)

# Fix 5: Include all required parameters
- tier_summary_md = generate_tier_summary_table(tier_result)
+ tier_summary_md = generate_tier_summary_table(tier_id.value, tier_result.subtest_results)
```

## Final Status

Both experiments need to complete:
- User will run the provided commands in separate terminals
- E2E script will skip completed work
- Only missing runs and aggregations will be generated
- Full dataset will be ready for paper once complete
