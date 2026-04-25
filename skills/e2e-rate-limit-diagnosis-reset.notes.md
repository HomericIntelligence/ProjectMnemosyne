# E2E Rate Limit Diagnosis and Reset - Raw Session Notes

## Session Context

**Date**: 2026-04-25
**Project**: ProjectScylla
**Initial Request**: Debug why test-001 experiment showed "garbage results" for T4-T6 tiers
**Verification**: verified-local (script executed successfully, reset applied, rerun pending)

## Problem Discovery

### Initial Symptoms

User observed a large data gap in test-001 experiment results:
- T0-T2 tiers had normal results
- T3 had partial results (subtests 01-15 OK, 16-41 failed)
- T4-T6 showed near-total failure ("garbage results")

### Investigation Steps

**Step 1**: Analyzed aggregate data in `docs/arxiv/haiku/data/`
- `runs.csv` showed the cliff pattern: pass rates dropping to near-zero for later tiers
- `summary.json` confirmed the data quality issue

**Step 2**: Traced to experiment results at `results/2026-03-30T04-09-50-test-001/`
- Examined tier-level directories to understand the scope of failures

**Step 3**: Read `agent/result.json` for individual failed runs
- Found the definitive 429 error: `"api_error_status": 429`
- Error message: `"You've hit your org's monthly usage limit"`

**Step 4**: Confirmed the timeline by mapping costs:
- T0-T2 succeeded: ~$5.53 total
- T3/01-15 succeeded: ~$3.64 additional
- Rate limit hit at approximately $10.28 total spend
- Everything after that point failed with zero tokens

### Key Finding

The root cause was **Anthropic API monthly usage limit exhaustion**, not any code bug, tier design issue, or infrastructure problem.

## Diagnosis Pitfalls (Time Wasted)

1. **Initially assumed tier design problem**: Spent time investigating whether T4-T6 configurations were broken. The aggregate data pattern (later tiers fail) was misleading -- it looked like a tier complexity issue.

2. **Assumed infrastructure crash**: Looked for Docker/system errors before checking the actual agent output. No infra errors were present.

3. **Trusted checkpoint state**: The checkpoint showed `tier_states="failed"` for T4, but this was ambiguous -- it could mean "all runs failed with bad grades" or "runs couldn't execute at all." The actual data for T4 runs that DID complete showed 97.3% pass rate.

**Lesson**: Always go to `agent/result.json` first when diagnosing unexpected failures. The actual error message is definitive; aggregate statistics and checkpoint states are not.

## Reset Script Details

### Created: `scripts/reset_rate_limited_runs.py`

**Design decisions**:

1. **Dry-run by default**: `--apply` flag required to actually make changes. This prevents accidental data loss.

2. **Backup**: Original `checkpoint.json` saved as `checkpoint.json.bak` before modification.

3. **Detection logic**: Checks both `agent/result.json` (for `api_error_status: 429`) and `run_result.json` (for judge failures on rate-limited agent output). Both need to be cleaned.

4. **Artifact cleanup**: Removes `run_result.json`, `report.json`, `report.md`, and `judge/` directory contents. These contain invalid results from the rate-limited run.

5. **Checkpoint cascade**: When resetting a run, must also reset:
   - `run_states[tier][subtest][run]` -> `"pending"`
   - Remove from `completed_runs[tier][subtest][run]`
   - `subtest_states[tier][subtest]` -> `"pending"`
   - `tier_states[tier]` -> `"pending"`
   - `experiment_state` -> `"tiers_running"`

6. **Run number format**: `run_states` uses string run numbers WITHOUT zero-padding: `"1"`, `"2"`, `"3"` -- NOT `"01"`, `"02"`, `"03"`.

### Why manage_experiment.py resume doesn't handle this

The `_reset_non_completed_runs()` function in `manage_experiment.py` only auto-resets runs in these states:
- `run_states="failed"` (infra crash -- unhandled exception)
- `run_states="rate_limited"` (detected rate limit with RateLimitError)

It does NOT reset `run_states="worktree_cleaned"` runs. Rate-limited runs that were not detected as rate limits during execution end up at `worktree_cleaned` with `completed_runs="failed"` -- the system considers them legitimately completed runs with bad grades.

This is the gap: the real-time rate limit detection (`e2e-rate-limit-detection` skill) handles per-minute rate limits. Monthly quota exhaustion uses a different error format (`api_error_status: 429` with "monthly usage limit" message) that may not trigger the same detection path, causing these runs to be treated as normal completions.

## Checkpoint Structure Reference

From actual test-001 checkpoint:

```json
{
  "experiment_state": "complete",
  "tier_states": {
    "T0": "complete",
    "T1": "complete",
    "T2": "complete",
    "T3": "complete",
    "T4": "failed",
    "T5": "complete",
    "T6": "complete"
  },
  "run_states": {
    "T3": {
      "16": {
        "1": "worktree_cleaned",
        "2": "worktree_cleaned",
        "3": "worktree_cleaned"
      }
    },
    "T4": {
      "01": {
        "1": "worktree_cleaned"
      }
    }
  },
  "completed_runs": {
    "T3": {
      "16": {
        "1": "failed",
        "2": "failed",
        "3": "failed"
      }
    },
    "T4": {
      "01": {
        "1": "failed"
      }
    }
  }
}
```

Note: T4 `tier_states="failed"` but the runs that completed without rate limiting had 97.3% pass rate. The "failed" tier state just means at least one run failed, not that the tier design is broken.

## Recovery Workflow

After applying the reset script:

```bash
# 1. Verify the reset (check checkpoint)
python -c "
import json
with open('results/<experiment>/checkpoint.json') as f:
    cp = json.load(f)
print('Experiment state:', cp['experiment_state'])
for tier, state in cp['tier_states'].items():
    print(f'  {tier}: {state}')
"

# 2. Re-run affected tiers
pixi run python scripts/manage_experiment.py run \
  --config <experiment_dir> \
  --tiers T3 T4 T5 T6

# 3. Verify results after rerun
# Check that previously rate-limited runs now have real results
```

## Related Sessions

- 2026-01-04: `e2e-rate-limit-detection` -- Fixed real-time rate limit parsing from JSON
- 2026-03-06: `batch-retry-errors-checkpoint-reset` -- Fixed batch mode retry to check checkpoints
- 2026-03-14: `always-retry-infra-failures` -- Made retry unconditional, fixed state semantics
