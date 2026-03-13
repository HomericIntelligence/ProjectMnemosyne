# Skill: git-worktree-collision-fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Branch | fix/e2e-framework-bugs |
| PR | #864 |
| Objective | Fix E2E batch runner where all 47 tests returned ERROR in parallel runs |
| Outcome | Success — framework errors eliminated; FAILs are now legitimate agent failures |
| Category | testing |

## When to Use

Trigger this skill when:

- E2E batch runner produces ERROR (not FAIL) for every test in a run
- Git error like `fatal: A branch named 'T0_00_run_01' already exists` appears in worktree logs
- Judge phase crashes with `float() argument must be a string or a real number, not 'NoneType'`
- Judge phase crashes with `ValueError` / conversational text instead of JSON
- A single tier failure in parallel execution aborts all other tiers
- CI pre-commit fails with `fatal: ambiguous argument 'origin/main..HEAD'`
- `ImportError: cannot import name 'JudgmentInfoBase' from 'scylla.core.results'`

## Root Causes and Fixes

### Bug 1: Git worktree branch name collisions

**Symptom**: `fatal: A branch named 'T0_00_run_01' already exists` in worktree_create.sh output. The old `git branch -D` fix in commit `56a281d` didn't work because you cannot delete a branch that is checked out in a live worktree — even after `git worktree prune`.

**Root cause**: Branch names like `T0_00_run_01` are not experiment-scoped. Multiple experiments running the same tier/subtest against the same base repo will collide.

**Fix** (`scylla/e2e/workspace_setup.py` + `scylla/e2e/subtest_executor.py`):

```python
# workspace_setup.py — add experiment_id parameter
def _setup_workspace(
    ...
    experiment_id: str = "",
) -> None:
    exp_prefix = experiment_id[:8] if experiment_id else ""
    if exp_prefix:
        branch_name = f"{exp_prefix}_{tier_id.value}_{subtest_id}_run_{run_number:02d}"
    else:
        branch_name = f"{tier_id.value}_{subtest_id}_run_{run_number:02d}"

# subtest_executor.py — pass experiment_id at call site
_setup_workspace(
    ...
    experiment_id=self.config.experiment_id,
)
```

### Bug 2: Judge crashes on invalid/null JSON from LLM

**Symptom A**: `ValueError: Judge response does not contain valid JSON` — Haiku returns conversational text instead of structured JSON. Previously re-raised and killed the entire run.

**Fix** (`scylla/e2e/judge_runner.py`): Catch all non-`RateLimitError` exceptions, append a `JudgeResultSummary(score=0.0, passed=False, is_valid=False)` and continue to the next judge. After the loop, if `consensus_score is None` (all judges failed), return a zero-score dict instead of raising:

```python
except RateLimitError:
    raise  # Must propagate for backoff

except Exception as e:
    # Record failed summary and continue — do not crash the run
    judges.append(JudgeResultSummary(
        model=model, score=0.0, passed=False, grade="F",
        reasoning=f"Judge failed: {e}", judge_number=judge_num,
        is_valid=False, criteria_scores={},
    ))

# After loop:
if consensus_score is None:
    return {"score": 0.0, "passed": False, "grade": "F",
            "reasoning": "All judges failed", "is_valid": False,
            "criteria_scores": {}}, judges
```

**Symptom B**: `float() argument must be a string or a real number, not 'NoneType'` — Haiku returns valid JSON but with `"score": null`. `dict.get("score", 0.0)` returns `None` when the key *exists* with a null value.

**Fix** (`scylla/e2e/llm_judge.py` + `scylla/judge/evaluator.py`): Use `or` fallback instead of `.get(key, default)`:

```python
# WRONG — default ignored when key exists with null value
score = float(data.get("score", 0.0))

# CORRECT — null treated same as missing
score = float(data.get("score") or 0.0)
passed = bool(data.get("passed") or False)
reasoning = str(data.get("reasoning") or "No reasoning provided")
```

Apply the same `or` pattern in `evaluator.py` for `requirements`, `categories`, and `summary` sections.

### Bug 3: Single tier failure aborts parallel tier group

**Symptom**: One tier raises an exception inside `_execute_parallel_tier_group()` → `raise` on line 476 kills all in-flight sibling tiers.

**Fix** (`scylla/e2e/runner.py`): Collect errors, only raise if ALL tiers failed:

```python
errors: dict[TierID, Exception] = {}
for future in as_completed(futures):
    tier_id = futures[future]
    try:
        tier_result = future.result()
        tier_results[tier_id] = tier_result
        self._save_tier_result(tier_id, tier_result)
    except Exception as e:
        errors[tier_id] = e  # collect, don't re-raise

if errors and not tier_results:
    raise RuntimeError(f"All tiers failed. First: {next(iter(errors.values()))}") \
        from next(iter(errors.values()))
elif errors:
    for tid, err in errors.items():
        logger.warning(f"Tier {tid.value} failed but others succeeded: {err}")
```

### Bug 4: Missing base classes in `scylla/core/results.py`

**Symptom**: `ImportError: cannot import name 'JudgmentInfoBase' from 'scylla.core.results'` breaks `tests/unit/cli/test_cli.py` collection.

**Root cause**: `scylla/reporting/result.py` imported `JudgmentInfoBase` and `MetricsInfoBase` that were never added to `core/results.py`.

**Fix**: Add both classes. Note: `MetricsInfoBase.cost_usd` must have `default=0.0` (not `...`) — existing tests construct it without `cost_usd`:

```python
class JudgmentInfoBase(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed: bool = Field(..., description="Whether the run passed evaluation")
    impl_rate: float = Field(default=0.0, description="Implementation rate (0.0-1.0)")

class MetricsInfoBase(BaseModel):
    model_config = ConfigDict(frozen=True)
    tokens_input: int = Field(..., description="Number of input tokens consumed")
    tokens_output: int = Field(..., description="Number of output tokens generated")
    cost_usd: float = Field(default=0.0, description="Total cost in USD")  # default, not required
```

### Bug 5: CI pre-commit fails with `ambiguous argument 'origin/main..HEAD'`

**Symptom**: GitHub Actions pre-commit workflow fails with `fatal: ambiguous argument 'origin/main..HEAD': unknown revision or path not in the working tree`.

**Root cause**: `actions/checkout@v4` defaults to `fetch-depth: 1` (shallow clone). `origin/main` doesn't exist as a fetchable ref, so `pre-commit run --from-ref origin/main --to-ref HEAD` fails.

**Fix** (`.github/workflows/pre-commit.yml`):

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history so origin/$BASE_REF always exists
```

## Verified Workflow

1. Run baseline dry run: `pixi run python scripts/run_e2e_batch.py --tiers T0 --model haiku --judge-model haiku --runs 1 --max-subtests 1 --fresh -v --threads 1 --results-dir /tmp/e2e-verify`
2. Analyze results — distinguish framework ERRORs from legitimate agent FAILs by reading `judge/judge_01/timing.json` (has `"failed": true` key) and `run_result.json`
3. Run parallel dry run: `--tiers T0 T1 --threads 2 --max-subtests 2` to verify no branch collisions
4. All 2219+ unit tests must pass before pushing

## Failed Attempts

### Proactive `git branch -D` before worktree creation

**What was tried**: `56a281d` added `git branch -D $branch_name` before `git worktree add`. This works for branches that are not checked out anywhere, but **fails silently** when the branch is still checked out in a live (or stale-but-not-pruned) worktree. The worktree add then fails because the branch still exists.

**Why it failed**: `git branch -D` cannot delete a branch that is currently checked out in a worktree, even after `git worktree prune` (prune only removes stale metadata, not live worktrees). The correct solution is to make branch names globally unique per experiment, eliminating the need for cleanup entirely.

### Using `dict.get("field", default)` as null guard

**What was tried**: The original code used `data.get("score", 0.0)` assuming the default covers null values. This is a Python gotcha: `.get(key, default)` only uses the default when the key is **absent**. When the key exists with value `null` (Python `None`), `.get()` returns `None`. `float(None)` raises `TypeError`.

**Correct pattern**: `data.get("key") or default` — the `or` catches both missing keys and null/falsy values.

## Key Observations

- **T0 tier F-grades are expected**: T0 runs agents with empty system prompt by design. Haiku with no context defaults to asking clarifying questions. These are correct baseline measurements, not bugs.
- **Judge baseline context IS present**: The judge prompt includes a `## Baseline Pipeline Results (Before Agent)` section. The judge correctly marks pre-existing failures as N/A rather than penalizing the agent. This plumbing works correctly.
- **Rate limit is a separate concern**: `RateLimitError` must always propagate immediately. Never swallow it in the judge error handler.
