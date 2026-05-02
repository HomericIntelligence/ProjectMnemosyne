---
name: dryrun3-completion
description: 'Complete interrupted dryrun experiments: diagnose broken/partial runs, clean stale git worktrees, re-run broken experiments, repair partial experiments, build loader-compatible symlink tree, generate full analysis pipeline output, and produce Go/NoGo assessment with run classification script.'
category: evaluation
date: 2026-03-14
version: 1.0.0
user-invocable: true
---
# Dryrun3 Completion: Diagnose, Repair, and Analyze Interrupted Batch Experiments

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-04 (updated 2026-03-14) |
| Objective | Complete all 47 experiments in ~/dryrun3/ to 7/7 run_results each, then generate full analysis pipeline output |
| Outcome | Operational — 47/47 experiments complete, 329 total runs, $148.64 API cost, 34.3% pass-rate |
| Key Learning | Stale git worktrees in shared repos block `--fresh` re-runs; `--retry-errors` batch skip logic ignores `--max-subtests` expansion; full-ablation tests must never use `--max-subtests` |

## When to Use This Skill

Use this workflow when:

- A batch dryrun left some experiments with 0/7 run_results (broken) and others with partial results
- `--retry-errors` reports "All tests already completed" even though `--max-subtests` was increased
- Stale git worktrees or branches from old broken runs exist in `~/dryrun3/repos/<hash>/`
- You need to build a loader-compatible `~/fullruns/dryrun3/` symlink tree from timestamped experiment directories
- You need to run `generate_all_results.py` to produce figures, tables, and stats from a complete dataset
- You need a Go/NoGo completion assessment across all 47 tests with run classification (COMPLETE/INFRA_ERROR/ORPHAN/INTERMEDIATE)
- Full-ablation tests were accidentally capped with `--max-subtests` and need expansion to all subtests (e.g., T3/29-41 missing after `--max-subtests 24`)

## Verified Workflow

### Phase 0: Diagnose Experiment State

Before doing anything, categorize all experiments:

```bash
# Count run_results per experiment directory
for dir in ~/dryrun3/2026-*-test-*/; do
  test_name=$(basename "$dir" | grep -oE 'test-[0-9]+$')
  count=$(find "$dir" -name run_result.json 2>/dev/null | wc -l)
  echo "$test_name: $count/7 $(basename $dir)"
done | sort

# Summarize: broken (0), partial (1-6), complete (7)
for dir in ~/dryrun3/2026-*-test-*/; do
  count=$(find "$dir" -name run_result.json 2>/dev/null | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "BROKEN: $(basename $dir)"
  elif [ "$count" -lt 7 ]; then
    echo "PARTIAL ($count/7): $(basename $dir)"
  fi
done
```

Expected outputs:
- **Complete**: 28/47 experiments with exactly 7/7 run_results
- **Partial**: 3/47 experiments with 1-6 run_results (specific tiers missing)
- **Broken**: 16/47 experiments with 0 run_results (entire experiment failed)

### Phase 1: Clean Stale Worktrees Before Re-running Broken Experiments

**This step is critical and must be done before any `--fresh` re-runs.**

The `--fresh` flag creates a new timestamped directory but does NOT clear old worktrees or branches from the shared `~/dryrun3/repos/<hash>/` directories. These stale references cause the new run to fail immediately when it tries to create worktrees with the same branch names.

```bash
# Identify which repos have stale worktrees
for repo_dir in ~/dryrun3/repos/*/; do
  wt_count=$(git -C "$repo_dir" worktree list 2>/dev/null | grep -v "bare\|$(pwd)" | wc -l)
  if [ "$wt_count" -gt 0 ]; then
    echo "=== $repo_dir ==="
    git -C "$repo_dir" worktree list 2>/dev/null
  fi
done

# Remove stale worktrees for specific broken experiments
# Replace the test-NNN pattern with the actual broken test IDs
BROKEN_TESTS="test-001|test-003|test-007|test-012|test-019"  # example
for repo_dir in ~/dryrun3/repos/*/; do
  # Remove stale worktrees matching broken test IDs
  git -C "$repo_dir" worktree list 2>/dev/null | \
    grep -E "($BROKEN_TESTS)/" | awk '{print $1}' | while read wt_path; do
      echo "Removing worktree: $wt_path"
      git -C "$repo_dir" worktree remove --force "$wt_path" 2>/dev/null || true
    done

  # Prune leftover references
  git -C "$repo_dir" worktree prune 2>/dev/null || true

  # Remove stale branches matching broken test IDs
  git -C "$repo_dir" branch 2>/dev/null | \
    grep -E "($BROKEN_TESTS)_" | sed 's/[+* ]*//' | while read branch; do
      echo "Deleting branch: $branch"
      git -C "$repo_dir" branch -D "$branch" 2>/dev/null || true
    done
done
```

**Verify cleanup succeeded:**
```bash
for repo_dir in ~/dryrun3/repos/*/; do
  remaining=$(git -C "$repo_dir" worktree list 2>/dev/null | grep -v "bare" | wc -l)
  echo "$repo_dir: $remaining worktrees remaining"
done
```

### Phase 2: Re-run Broken Experiments with --fresh

After cleaning stale worktrees, re-run all broken experiments using `--fresh`. The `--fresh` flag creates a new timestamped directory, avoiding conflicts with the old (broken) directory.

```bash
# List all broken test config paths
BROKEN_CONFIGS=(
  tests/fixtures/tests/test-001
  tests/fixtures/tests/test-003
  # ... add all broken tests
)

# Run all broken experiments together (batch mode)
pixi run python scripts/manage_experiment.py run \
  "${BROKEN_CONFIGS[@]/#/--config }" \
  --model claude-haiku-4-5-20251001 \
  --judge-model claude-haiku-4-5-20251001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --max-subtests 1 \
  --results-dir ~/dryrun3 \
  --fresh --threads 2

# Alternative: pass all configs as a directory if all tests are under one parent
pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests \
  --model claude-haiku-4-5-20251001 \
  --judge-model claude-haiku-4-5-20251001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --max-subtests 1 \
  --results-dir ~/dryrun3 \
  --fresh --threads 2
```

**Key flags:**
- `--fresh`: Creates a new timestamped directory, never resumes the old broken one
- `--threads 2`: Limits parallelism to avoid rate limit errors during API-heavy phases

### Phase 3: Repair Partial Experiments with --retry-errors

For experiments that have some tiers complete but others missing, use surgical repair:

```bash
# Identify which tier is missing in partial experiment
for dir in ~/dryrun3/2026-*-test-014/; do
  for tier in T0 T1 T2 T3 T4 T5 T6; do
    count=$(find "$dir/$tier" -name run_result.json 2>/dev/null | wc -l)
    echo "  $tier: $count run_results"
  done
done

# Repair by running only the missing tier
pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-014 \
  --model claude-haiku-4-5-20251001 \
  --judge-model claude-haiku-4-5-20251001 \
  --tiers T4 \
  --runs 1 --max-subtests 1 \
  --results-dir ~/dryrun3 \
  --retry-errors
```

**Important**: If rate limits were hit during Phase 2, wait for Phase 2 to fully complete before starting Phase 3 repairs. Running `--retry-errors` while Phase 2 is consuming API will cause model validation to retry 4x with ~60s backoff per attempt (~8 minutes just for validation).

### Phase 4: Build Loader-Compatible Symlink Tree

The analysis loader (`scylla/analysis/loader.py`) expects the structure:
```
data_dir/<experiment_name>/<timestamp>/T*/NN/run_*/run_result.json
```

Build this from the flat timestamped experiment directories in `~/dryrun3/`:

```bash
mkdir -p ~/fullruns/dryrun3

for dir in ~/dryrun3/2026-*-test-*/; do
  entry=$(basename "$dir")
  # Extract test name (e.g., "test-014") from directory name like "2026-03-04T12-00-00-test-014"
  test_name=$(echo "$entry" | grep -oE 'test-[0-9]+$')
  if [ -n "$test_name" ]; then
    mkdir -p ~/fullruns/dryrun3/$test_name
    ln -sf "$dir" ~/fullruns/dryrun3/$test_name/$entry
  fi
done

# Verify structure
echo "Experiments in fullruns:"
ls ~/fullruns/dryrun3/ | wc -l
echo "Sample structure:"
ls ~/fullruns/dryrun3/test-001/
```

**Verify loader can read the structure:**
```bash
# Each experiment dir should contain T0-T6 subdirectories
for test_dir in ~/fullruns/dryrun3/*/; do
  test_name=$(basename "$test_dir")
  latest=$(ls -t "$test_dir" | head -1)
  tier_count=$(ls "$test_dir/$latest/" 2>/dev/null | grep -cE '^T[0-6]$' || echo 0)
  echo "$test_name: $tier_count tiers"
done
```

### Phase 5: Generate Full Analysis Pipeline Output

```bash
pixi run python scripts/generate_all_results.py \
  --data-dir ~/fullruns/dryrun3 \
  --output-dir docs/arxiv/dryrun3

# Verify outputs
echo "CSVs:"
find docs/arxiv/dryrun3 -name "*.csv" | wc -l
echo "JSONs:"
find docs/arxiv/dryrun3 -name "*.json" | wc -l
echo "Figures:"
find docs/arxiv/dryrun3 -name "*.png" -o -name "*.svg" | wc -l
echo "Tables:"
find docs/arxiv/dryrun3 -name "Table_*.tex" -o -name "Table_*.md" | wc -l
```

Expected outputs for 47 experiments / 7 tiers:
- 4 CSV files
- 2 JSON files
- 56 figures
- 10 tables

### Phase 6: Go/NoGo Assessment with Analysis Script (2026-03-14)

When a new retry run is needed (e.g., full-ablation tests were capped with `--max-subtests`),
use `scripts/analyze_dryrun3.py` to get a status report and Go/NoGo verdict before and after retrying.

```bash
pixi run python scripts/analyze_dryrun3.py --results-dir ~/dryrun3
```

**Run classification logic** (key to understanding completion state):

```python
TIER_SUBTEST_COUNTS = {"T0": 24, "T1": 10, "T2": 15, "T3": 41, "T4": 14, "T5": 15, "T6": 1}
TERMINAL_ERROR_STATES = {"failed", "rate_limited"}

# For each run in checkpoint.run_states:
# effective_max = min(max_subtests, tier_total) if max_subtests else tier_total
# sub_index = int(sub_id)
# is_orphan = sub_index >= effective_max
if is_orphan:                        -> ORPHAN      (exclude from all metrics)
elif state == "worktree_cleaned":    -> COMPLETE    (never retry, even if bad grade)
elif state in TERMINAL_ERROR_STATES: -> INFRA_ERROR (reset to pending, retry from scratch)
else:                                -> INTERMEDIATE (resume from current state)
```

**Go/NoGo criteria** (all 4 must pass):
1. All 47 tests have checkpoints
2. `infra_error + intermediate == 0`
3. No missing subtests per tier (coverage check)
4. ≥ 95% of complete runs have valid `run_result.json`

**Subtest coverage check** detects checkpoint gaps (e.g., T3/29-41 missing after `--max-subtests 24`):
```python
active = sum(1 for sub_id in run_states.get(tier_id, {}) if int(sub_id) < effective_max)
if active < effective_max:  # missing subtests not yet created
    flag(tier_id, actual=active, expected=effective_max)
```

### Phase 7: Fix `--max-subtests` Cap for Full-Ablation Tests (2026-03-14)

Full-ablation tests (test-001/002/003) must run ALL subtests (120 total: T0=24, T1=10, ..., T3=41, ...).
Using `--max-subtests 24` caps T3 at 24 subtests; T3/25-41 are never created in the checkpoint.

**Fix**: Remove `--max-subtests` flag for full-ablation tests entirely:

```bash
# WRONG: caps at 24 — T3/25-41 never created (107 runs instead of 360)
pixi run python scripts/manage_experiment.py run \
  --config "tests/fixtures/tests/test-001" \
  --max-subtests 24 --results-dir ~/dryrun3 --threads 2

# CORRECT: no cap — runner detects missing subtests via _tier_has_missing_subtests()
pixi run python scripts/manage_experiment.py run \
  --config "tests/fixtures/tests/test-001" \
  --results-dir ~/dryrun3 --threads 2
```

The runner's `_tier_has_missing_subtests()` detects checkpoint gaps and creates T3/29-41 on resume.
T3/25-28 (orphaned from the capped run) will be picked up as INTERMEDIATE runs.

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results and Parameters

### Experiment Statistics

| Metric | Value |
| -------- | ------- |
| Total experiments | 47 |
| Experiments broken (0/7 run_results) | 16 |
| Experiments partial (1-6/7 run_results) | 3 |
| Experiments complete (7/7 run_results) | 28 |
| Total runs after completion | 329 (47 x 7 tiers) |
| Total API cost | $148.64 |
| Overall pass-rate | 34.3% |
| Model used | claude-haiku-4-5-20251001 |

### Analysis Pipeline Outputs

| Output Type | Count |
| ------------- | ------- |
| CSV files | 4 |
| JSON files | 2 |
| Figures (PNG/SVG) | 56 |
| Tables (TeX/Markdown) | 10 |

### Key Parameters

```yaml
model: claude-haiku-4-5-20251001
judge-model: claude-haiku-4-5-20251001
tiers: [T0, T1, T2, T3, T4, T5, T6]
runs: 1
max-subtests: 1
threads: 2
results-dir: ~/dryrun3
```

## Key Learnings

1. **`--fresh` does not clean shared repos.** The `--fresh` flag only creates a new timestamped results directory. Stale worktrees and branches in `~/dryrun3/repos/<hash>/` from old broken runs must be cleaned manually before re-running. Always clean stale worktrees before any `--fresh` batch run.

2. **Rate limits cascade across simultaneous batch runs.** Running `--retry-errors` for partial experiments while `--fresh` re-runs are consuming API quota causes validation retries with exponential backoff. Serialize Phase 2 (broken re-runs) and Phase 3 (partial repairs) — do not overlap them.

3. **Batch skip logic ignores `--max-subtests` expansion (pre-PR #1404).** The batch mode in `manage_experiment.py` checked only `batch_summary.json` status. After completing experiments with `--max-subtests 1`, re-running with `--max-subtests 3` and `--retry-errors` would silently skip all experiments. The fix reads each experiment's checkpoint to compare actual subtest count against the requested maximum.

4. **Loader expects a specific symlink tree structure.** `scylla/analysis/loader.py` requires `data_dir/<exp>/<timestamp>/T*/NN/run_*/run_result.json`. Timestamped experiment directories from `~/dryrun3/` must be symlinked into `~/fullruns/dryrun3/<test_name>/<timestamp>` before running the analysis pipeline.

5. **Diagnose before acting.** Count run_results per experiment and categorize into broken/partial/complete before starting any repair. Using different strategies (fresh re-run vs. retry-errors) for different failure modes is more efficient and less risky than applying a single strategy to all experiments.

6. **Full-ablation tests must never use `--max-subtests` (2026-03-14).** T3 has 41 subtests — using `--max-subtests 24` silently caps T3 at 24, leaving 17 subtests uncreated. Full ablation = no flag. Standard tests use `--max-subtests 3`.

7. **Run classification needs four categories, not two (2026-03-14).** COMPLETE (`worktree_cleaned`) is never retried even with a bad grade. INFRA_ERROR (`failed`/`rate_limited`) is reset to `pending`. INTERMEDIATE (any other state) resumes from current position. ORPHAN (sub_index >= effective_max) is excluded entirely from metrics.

8. **Subtest coverage check must account for orphan vs active (2026-03-14).** When `--max-subtests 24` was used, subtests 25-28 are in the checkpoint but are orphans; subtests 29-41 are missing. The coverage check must use `int(sub_id) < effective_max` to distinguish active vs orphan entries.

## Files and References

| File | Role |
| ------ | ------ |
| `scripts/manage_experiment.py` | Batch experiment runner; contains batch skip logic bug fixed in PR #1404 |
| `scylla/analysis/loader.py` | Analysis data loader; expects `data_dir/<exp>/<timestamp>/T*/NN/run_*/run_result.json` |
| `scripts/generate_all_results.py` | Master analysis pipeline; produces figures, tables, CSVs, JSONs |
| `~/dryrun3/repos/` | Shared git repos for worktrees; can accumulate stale branches between runs |
| `~/fullruns/dryrun3/` | Loader-compatible symlink tree built from `~/dryrun3/` timestamped directories |
| `scripts/analyze_dryrun3.py` | Go/NoGo analysis script; classifies runs, checks subtest coverage, reports verdict |
| `retry_dryrun3.sh` | Batch retry script; full-ablation tests must omit `--max-subtests` |

**PRs**:
- #1404 — Fix batch skip logic to respect `--max-subtests` expansion
- #1491 — Add `scripts/analyze_dryrun3.py` analysis script + fix `retry_dryrun3.sh` to remove `--max-subtests` cap for full-ablation tests
