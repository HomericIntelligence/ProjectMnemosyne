# Session Notes: Dryrun3 Completion

## Context

Working on completing dryrun3 — a batch run of 47 experiments against `~/dryrun3/` using
`claude-haiku-4-5-20251001` as both the agent model and judge model. Each experiment runs
7 tiers (T0–T6), 1 run per tier, 1 subtest per tier = 7 run_results per experiment = 329 total runs.

The batch run had previously been interrupted, leaving:
- 28/47 experiments fully complete (7/7 run_results)
- 3/47 experiments partially complete (1-6 run_results, missing specific tiers)
- 16/47 experiments broken (0/7 run_results, entire experiment failed to start or was interrupted immediately)

## Timeline

### Phase 0: Diagnosis (30 minutes)

Used `find` and counting to categorize all 47 experiment directories:

```bash
for dir in ~/dryrun3/2026-*-test-*/; do
  test_name=$(basename "$dir" | grep -oE 'test-[0-9]+$')
  count=$(find "$dir" -name run_result.json 2>/dev/null | wc -l)
  echo "$test_name: $count/7 $(basename $dir)"
done | sort
```

Results confirmed 16 broken, 3 partial, 28 complete. Identified which specific tiers were
missing in the 3 partial experiments by iterating T0–T6 subdirectories.

### Phase 1: Stale Worktree Cleanup (15 minutes)

Discovered that `~/dryrun3/repos/8aa4a018a8230463/` contained stale branches like
`test-029_T1_01_run_01` from old broken runs. Running `--fresh` without cleaning these
caused immediate git failures:

```
fatal: 'test-029_T1_01_run_01' already exists
```

Cleaned all stale worktrees and branches:

```bash
for repo_dir in ~/dryrun3/repos/*/; do
  git -C "$repo_dir" worktree prune
  git -C "$repo_dir" branch | grep -E "test-" | sed 's/[+* ]*//' | \
    xargs -r git -C "$repo_dir" branch -D
done
```

Verified: 0 stale worktrees remaining across all repos.

### Phase 2: Fresh Re-runs for 16 Broken Experiments (4 hours)

Ran all 16 broken experiments with `--fresh --threads 2`. The 2-thread limit was necessary
to avoid overwhelming the rate limits (each run consumes significant API quota during the
model validation and judgment phases).

Attempted to also run the 3 partial repairs simultaneously — this was a mistake (see Failed
Attempts). Eventually serialized: Phase 2 first, Phase 3 after.

### Phase 3: Partial Experiment Repairs (45 minutes)

Three partial experiments each had a single tier missing. Used `--tiers <missing>` and
`--retry-errors` to run only the missing tier in each case:

- test-014: Missing T4
- test-031: Missing T2
- test-038: Missing T6

### Phase 4: Build Fullruns Symlink Tree (5 minutes)

The analysis loader requires `data_dir/<exp>/<timestamp>/...`. Built symlinks:

```bash
mkdir -p ~/fullruns/dryrun3
for dir in ~/dryrun3/2026-*-test-*/; do
  entry=$(basename "$dir")
  test_name=$(echo "$entry" | grep -oE 'test-[0-9]+$')
  mkdir -p ~/fullruns/dryrun3/$test_name
  ln -sf "$dir" ~/fullruns/dryrun3/$test_name/$entry
done
```

Verified 47 experiment directories, each containing a single symlink to the actual results.

### Phase 5: Generate Analysis (20 minutes)

```bash
pixi run python scripts/generate_all_results.py \
  --data-dir ~/fullruns/dryrun3 \
  --output-dir docs/arxiv/dryrun3
```

Completed successfully. Outputs: 4 CSVs, 2 JSONs, 56 figures, 10 tables.

## Error Messages Encountered

### Stale Worktree Error (Phase 1 prerequisite)

```
fatal: 'test-029_T1_01_run_01' already exists
```

Appeared during `manage_experiment.py run --fresh` before stale worktree cleanup.

### Rate Limit Backoff During Overlapping Phases

```
[model_validation] Rate limit exceeded. Retrying in 60s... (attempt 2/4)
[model_validation] Rate limit exceeded. Retrying in 60s... (attempt 3/4)
[model_validation] Rate limit exceeded. Retrying in 60s... (attempt 4/4)
```

Appeared when Phase 3 repair started while Phase 2 was still running. Each experiment's
`--retry-errors` repair had to wait ~4 minutes just for model validation.

### Silent Skip Bug (Attempt 3)

```
All 47 tests already completed. Nothing to do.
```

Appeared when re-running with `--max-subtests 3` and `--retry-errors` after completing
experiments with `--max-subtests 1`. No error was raised — the tool simply exited with
a success message, having done nothing.

## Bug Details: Batch Skip Logic (PR #1404)

File: `scripts/manage_experiment.py`
Location: ~line 597 (batch mode skip logic in `cmd_run()`)

**Before fix:**
```python
# Load batch summary for this experiment
batch_summary_path = exp_results_dir / "batch_summary.json"
if batch_summary_path.exists():
    with open(batch_summary_path) as f:
        summary = json.load(f)
    if summary.get("status") == "complete":
        log.info(f"Skipping {exp_id}: already complete")
        continue
```

**After fix:**
```python
# Load batch summary for this experiment
batch_summary_path = exp_results_dir / "batch_summary.json"
if batch_summary_path.exists():
    with open(batch_summary_path) as f:
        summary = json.load(f)
    if summary.get("status") == "complete":
        # If --max-subtests was specified, check if expansion is needed
        if max_subtests is not None:
            checkpoint_path = exp_results_dir / "checkpoint.json"
            if checkpoint_path.exists():
                with open(checkpoint_path) as f:
                    checkpoint = json.load(f)
                subtest_states = checkpoint.get("subtest_states", {})
                needs_expansion = False
                for tier_id, tier_subtests in subtest_states.items():
                    completed = sum(
                        1 for state in tier_subtests.values()
                        if state == "aggregated"
                    )
                    if completed < max_subtests:
                        needs_expansion = True
                        break
                if not needs_expansion:
                    log.info(f"Skipping {exp_id}: already complete with {max_subtests} subtests")
                    continue
                log.info(f"Re-queuing {exp_id}: needs subtest expansion to {max_subtests}")
            else:
                log.info(f"Skipping {exp_id}: already complete")
                continue
        else:
            log.info(f"Skipping {exp_id}: already complete")
            continue
```

## Key Observations

### --fresh Flag Behavior

`--fresh` in `manage_experiment.py` creates a new timestamped subdirectory under `--results-dir`:
```
~/dryrun3/2026-03-04T15-30-00-test-029/   # new --fresh directory
~/dryrun3/2026-02-28T09-15-00-test-029/   # old broken directory (left as-is)
```

It does NOT touch `~/dryrun3/repos/<hash>/` at all. That shared repo directory accumulates
worktrees and branches across all runs for the same task repo. The old broken run's worktrees
(`test-029_T1_01_run_01`) remain in the repo until manually removed.

### Rate Limit Patterns

Model validation (`--model claude-haiku-4-5-20251001`) hits rate limits when too many
`manage_experiment.py` processes run simultaneously. With `--threads 2`, a single batch
of 16 experiments rarely hits rate limits. With `--threads 4+`, rate limits are frequent.

The repair phase is more sensitive because each `--retry-errors` invocation validates the
model independently and doesn't share a single validation result across all experiments
in the batch.

### Loader Directory Structure Requirements

`scylla/analysis/loader.py` walks the directory tree expecting:
```
data_dir/
  <experiment_name>/           # e.g., "test-001"
    <timestamp>/               # e.g., "2026-03-04T12-00-00-test-001"
      T0/
        00/
          run_01/
            run_result.json
          run_02/
            run_result.json
      T1/
        ...
```

The timestamp directory name is arbitrary (loader just picks the newest one). The experiment
name directory must exist as a parent. Raw `~/dryrun3/` directories have the timestamp as the
top-level name — the symlink tree inverts this by putting `<test_name>/<timestamp>` as the
hierarchy.

## Final Results

- 47/47 experiments complete
- 329 total runs (47 experiments × 7 tiers × 1 run × 1 subtest)
- $148.64 total API cost
- 34.3% overall pass-rate (Haiku 4.5, all 7 tiers combined)
- 4 CSVs, 2 JSONs, 56 figures, 10 tables generated

## Related Skills

- `evaluation/verify-experiment-completion` — Single-experiment verification (not batch)
- `evaluation/e2e-checkpoint-resume` — Low-level checkpoint resume mechanics
- `evaluation/resume-from-failed-experiment` — Resume workflow for individual failed experiments
