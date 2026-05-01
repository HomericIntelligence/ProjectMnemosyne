---
name: e2e-rate-limit-diagnosis-reset
description: 'Diagnose experiment data quality issues caused by Anthropic API monthly
  usage limits (HTTP 429) and reset affected runs for retry. Use when: experiment
  results show unexplained failures in later tiers, runs have zero tokens/cost with
  exit_code=1, or checkpoint marks rate-limited runs as successfully completed with
  F grades.'
category: debugging
date: 2026-04-25
version: 1.0.0
user-invocable: false
tags:
- rate-limit
- "429"
- experiment-diagnosis
- checkpoint-reset
- data-quality
- e2e-testing
---
# E2E Rate Limit Diagnosis and Experiment Reset

## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Experiment results show "garbage data" in later tiers (T3-T6) -- all runs fail with zero tokens, zero cost, ~8-10s duration |
| **Root cause** | Anthropic API monthly usage limit (HTTP 429) hit mid-experiment; later tiers disproportionately affected because they run after earlier tiers consume quota |
| **Fix** | Diagnose via result.json inspection, then reset affected runs in checkpoint for retry using `scripts/reset_rate_limited_runs.py` |
| **Language** | Python 3.10+ |
| **Project** | ProjectScylla |

## When to Use

Use this skill when:

1. **Experiment data shows a "cliff"** -- early tiers succeed but later tiers have mass failures
2. **Runs have zero tokens and zero cost** -- `total_tokens=0, cost_usd=0.0, exit_code=1, duration ~8-10s`
3. **Checkpoint marks failed runs as complete** -- `run_states="worktree_cleaned"` with `completed_runs="failed"` for rate-limited runs (the system treated them as valid F-grade results)
4. **You suspect API quota exhaustion** rather than a code bug or tier design issue
5. **You need to selectively reset runs** in a completed experiment without re-running everything

**Key differentiator from `e2e-rate-limit-detection`**: That skill covers real-time detection/parsing of rate limits during execution. This skill covers post-hoc diagnosis when rate limits were NOT properly handled and corrupted experiment data.

## Verified Workflow

### Step 1: Identify the Failure Signature

Start with aggregate data, not individual runs:

```bash
# Check summary statistics
cat results/<experiment>/docs/arxiv/haiku/data/summary.json | python -m json.tool

# Look at runs.csv for patterns
# Key columns: tier, pass_rate, total_tokens, cost_usd, exit_code
head -50 docs/arxiv/haiku/data/runs.csv
```

**Failure signature to look for**:
- `exit_code=1` (agent crashed)
- `api_calls=1` (only one API call before failure)
- `total_tokens=0` (no tokens consumed)
- `cost_usd=0.0` (no cost)
- `duration` in 8-10 second range (just enough for one failed API roundtrip)
- Concentrated in later tiers (T3 second half, T4, T5, T6)

### Step 2: Confirm the Root Cause in result.json

Do NOT assume the cause from aggregate data alone. Check actual error messages:

```bash
# Find a failed run and read its result.json
cat results/<experiment>/T4/01/run_01/agent/result.json | python -m json.tool
```

**Confirmation**: Look for these fields in the JSON:
```json
{
  "is_error": true,
  "result": "You've hit your org's monthly usage limit",
  "api_error_status": 429,
  "total_cost_usd": 0,
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

**The `api_error_status: 429` field is definitive.** If you see this, the run failed due to rate limiting, not a code bug.

### Step 3: Map the Failure Timeline

Understand which tiers/subtests were affected:

```bash
# Check which tiers have rate-limited runs
for tier in T0 T1 T2 T3 T4 T5 T6; do
  echo "=== $tier ==="
  grep -rl "api_error_status.*429\|monthly usage limit" \
    results/<experiment>/$tier/*/run_*/agent/result.json 2>/dev/null | wc -l
done
```

**Typical pattern for monthly quota exhaustion**:
- T0-T2: Succeed (~$5-6 total cost)
- T3/01-15: Succeed (~$3-4 additional)
- T3/16-41: Rate limited (quota hit at ~$10 total)
- T4: All rate limited (runs after T3)
- T5: All rate limited (depends on T0-T4 completing first)
- T6: All rate limited (depends on T5)

### Step 4: Reset Affected Runs

Use the reset script (or create one if it does not exist):

```bash
# Dry run first (default mode)
pixi run python scripts/reset_rate_limited_runs.py \
  --experiment-dir results/<experiment-dir>

# Apply the reset
pixi run python scripts/reset_rate_limited_runs.py \
  --experiment-dir results/<experiment-dir> \
  --apply
```

**What the reset script does**:
1. Scans `completed/` directory for runs with 429 errors in `agent/result.json`
2. Also checks `run_result.json` for judge failures on rate-limited agent output
3. Cleans result artifacts: `run_result.json`, `report.json`, `report.md`, `judge/` contents
4. Cleans subtest-level and experiment-level reports
5. Updates `checkpoint.json`:
   - Resets `run_states` from `"worktree_cleaned"` to `"pending"`
   - Removes affected runs from `completed_runs`
   - Cascades: sets affected subtest states and tier states back to `"pending"`
   - Sets `experiment_state` back to `"tiers_running"`
6. Backs up original checkpoint as `checkpoint.json.bak`

### Step 5: Re-run Affected Tiers

```bash
pixi run python scripts/manage_experiment.py run \
  --config <experiment_dir> \
  --tiers T3 T4 T5 T6
```

The resume logic in `manage_experiment.py` will pick up only the `"pending"` runs.

## Key Checkpoint Structure Facts

Understanding these is critical for manual debugging or script development:

```python
# run_states uses string run numbers (NOT zero-padded)
checkpoint["run_states"]["T3"]["16"]["1"]  # correct
checkpoint["run_states"]["T3"]["16"]["01"]  # WRONG

# completed_runs status values
"passed"          # judge_passed=True (good grade)
"failed"          # judge_passed=False (bad grade OR rate-limited -- ambiguous!)
"agent_complete"  # agent ran, judge never evaluated

# Terminal states that WON'T be auto-retried by manage_experiment.py:
# - run_states="worktree_cleaned" -- considered DONE regardless of grade
# The auto-reset in _reset_non_completed_runs() only resets:
# - run_states="failed" (infra crash)
# - run_states="rate_limited" (detected rate limit)
# It does NOT reset "worktree_cleaned" runs that happened to be rate-limited
# but were not detected as such (the detection gap this skill addresses)

# Tier/subtest state cascade
# When resetting runs, you MUST also reset:
# - subtest_states[tier][subtest] -> "pending"
# - tier_states[tier] -> "pending"
# - experiment_state -> "tiers_running"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assumed tier design problem | Investigated whether T4-T6 tier configs were broken | Aggregate data alone does not reveal root cause | Always check actual error messages in `agent/result.json` before hypothesizing |
| Assumed infrastructure crash | Looked for Docker/system errors | No infra errors present | Rate limits can masquerade as clean failures with exit_code=1 |
| Checked only checkpoint state | Read checkpoint.json tier_states | Checkpoint said "failed" for T4 but actual pass rate was 97.3% on non-rate-limited runs | Checkpoint state does not always reflect data quality; inspect run-level data |

## Pitfalls

1. **Rate-limited runs look like valid F-grade results**: The checkpoint marks them as `worktree_cleaned` + `completed_runs="failed"`. The system treats this as "the agent ran and got a bad grade" rather than "the agent could not run at all."

2. **T4 checkpoint "failed" vs actual data quality**: A tier can show `tier_states="failed"` in the checkpoint while the runs that DID complete have a 97%+ pass rate. The "failed" state reflects the presence of any failed runs, not the overall quality.

3. **Dependency chain amplifies quota exhaustion**: T5 depends on T0-T4 completing; T6 depends on T5. If quota runs out during T3, everything downstream is guaranteed to fail.

4. **Monthly vs per-minute rate limits**: Monthly quota (HTTP 429 with "monthly usage limit") is fundamentally different from per-minute rate limits (HTTP 429 with "Retry-After" header). The existing rate limit detection handles per-minute limits with pause/resume but does NOT handle monthly quota exhaustion (there is nothing to wait for).

## Results & Parameters

### Detection Patterns (Copy-Paste Ready)

**Rate-limited run indicators in result.json**:
```python
# Definitive: API error status
data.get("api_error_status") == 429

# Supportive: error message
"monthly usage limit" in data.get("result", "")
"hit your org's monthly usage limit" in data.get("result", "")

# Supportive: zero-cost signature
data.get("total_cost_usd") == 0
data.get("usage", {}).get("input_tokens") == 0
data.get("usage", {}).get("output_tokens") == 0
```

### Reset Script Location

`scripts/reset_rate_limited_runs.py` in ProjectScylla

### Related Commands

```bash
# Check experiment cost before hitting limit
grep -o '"cost_usd":[0-9.]*' results/<experiment>/*/run_result.json | \
  awk -F: '{sum+=$2} END {printf "Total: $%.2f\n", sum}'

# Count rate-limited vs successful runs per tier
for tier in T0 T1 T2 T3 T4 T5 T6; do
  total=$(find results/<experiment>/$tier -name result.json -path "*/agent/*" 2>/dev/null | wc -l)
  limited=$(grep -rl "api_error_status.*429" results/<experiment>/$tier/*/run_*/agent/result.json 2>/dev/null | wc -l)
  echo "$tier: $limited/$total rate-limited"
done
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | test-001 experiment (2026-03-30) | T4-T6 garbage results diagnosed as monthly API quota exhaustion; reset script created and applied successfully |

## Related Skills

- `e2e-rate-limit-detection` -- Real-time rate limit detection during execution (code-level parsing fix)
- `always-retry-infra-failures` -- Making retry logic unconditional; distinguishing infra crash vs bad grade
- `batch-retry-errors-checkpoint-reset` -- Batch mode checkpoint reset for failed/rate-limited runs

## Tags

`debugging` `rate-limit` `429` `experiment-diagnosis` `checkpoint-reset` `data-quality` `e2e-testing` `monthly-quota` `api-errors`
