# Raw Notes: pydantic-none-coercion-pattern

## Session Context

- **Date**: 2026-02-19
- **Project**: ProjectScylla
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/760
- **Branch**: `fix-criteria-scores-none-propagation`
- **Trigger**: 2026-02-14 dry run of 47 E2E tests — 13 tests produced incorrect results ($0 cost, 8-22s, zero tokens)

## Root Cause Discovery

The bug was tracked to `criteria_scores=None` entering `E2ERunResult` which types the field as non-Optional:

```python
# E2ERunResult (scylla/e2e/models.py:310)
criteria_scores: dict[str, dict[str, Any]] = Field(default_factory=dict)  # NOT Optional

# JudgeResult (scylla/e2e/llm_judge.py:48)
criteria_scores: dict[str, dict[str, Any]] | None = None  # Optional

# JudgeResultSummary (scylla/e2e/models.py:247)
criteria_scores: dict[str, dict[str, Any]] | None = None  # Optional
```

The Pydantic error was:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for RunResult
criteria_scores
  Input should be a valid dictionary [type=dict_type, input_value=None, input_url=...]
```

## Complete Vulnerability Map (All 9 Sites)

### Site 1: subtest_executor.py:360 (checkpoint resume)
```python
# BEFORE:
criteria_scores=report_data.get("criteria_scores", {}),
# AFTER:
criteria_scores=report_data.get("criteria_scores") or {},
```

### Site 2: subtest_executor.py:858 (live run after judging)
```python
# BEFORE:
criteria_scores=judgment.get("criteria_scores", {}),
# AFTER:
criteria_scores=judgment.get("criteria_scores") or {},
```

### Site 3: regenerate.py:210 (scan/load path)
```python
# BEFORE:
criteria_scores=data.get("criteria_scores", {}),
# AFTER:
criteria_scores=data.get("criteria_scores") or {},
```

### Site 4: regenerate.py:400 (rejudge path, direct assignment)
```python
# BEFORE:
run.criteria_scores = judge_result.criteria_scores
# AFTER:
run.criteria_scores = judge_result.criteria_scores or {}
```

### Site 5: rerun.py:740 (rerun experiment path)
```python
# BEFORE:
"criteria_scores": judge_result.get("criteria_scores", {}),
# AFTER:
"criteria_scores": judge_result.get("criteria_scores") or {},
```

### Site 6: rerun_judges.py:606 (MISSING write in update function)
```python
# BEFORE (missing line):
run_data["judge_score"] = consensus_score
run_data["judge_passed"] = passed
run_data["judge_grade"] = grade
run_data["judge_reasoning"] = representative_reasoning
# criteria_scores NOT written — stale value persists!

# AFTER (added line):
run_data["judge_score"] = consensus_score
run_data["judge_passed"] = passed
run_data["judge_grade"] = grade
run_data["judge_reasoning"] = representative_reasoning
run_data["criteria_scores"] = representative_criteria or {}  # NEW
```

### Site 7: judge_runner.py:246 (consensus from closest judge)
```python
# BEFORE:
primary_criteria_scores = closest_judge.criteria_scores
# AFTER:
primary_criteria_scores = closest_judge.criteria_scores or {}
```

### Site 8: judge_runner.py:249 (single-judge fallback)
```python
# BEFORE:
primary_criteria_scores = judges[0].criteria_scores if judges else None
# AFTER:
primary_criteria_scores = (judges[0].criteria_scores if judges else None) or {}
```

### Site 9: models.py (defense-in-depth Pydantic validator)
```python
# ADDED to E2ERunResult class:
@field_validator("criteria_scores", mode="before")
@classmethod
def coerce_none_criteria_scores(cls, v: Any) -> dict:
    """Coerce None to empty dict — judges may return None for criteria_scores."""
    return v if v is not None else {}
```

## Tests Added (7 new tests)

### test_models.py (3 tests in TestE2ERunResult)
- `test_criteria_scores_coerces_none_to_empty_dict` — validator coerces None → {}
- `test_criteria_scores_accepts_empty_dict` — {} passthrough
- `test_criteria_scores_accepts_populated_dict` — populated dict preserved

### test_subtest_executor.py (2 tests in TestCheckpointResumeWithNullCriteriaScores)
- `test_criteria_scores_null_in_report_data` — null value in stored JSON
- `test_criteria_scores_missing_key_in_report_data` — key absent from stored JSON

### test_rerun_judges.py (2 standalone tests)
- `test_regenerate_consensus_writes_criteria_scores_to_run_result_json` — write is present
- `test_regenerate_consensus_writes_empty_criteria_scores_when_null` — null becomes {}

## Test Results
- All 71 tests in targeted files passed
- `pre-commit run --all-files` — all hooks passed (ruff, mypy, black, etc.)

## Why `rerun_judges.py` Was the Hardest to Find

The missing write in `rerun_judges.py` was the only site that was NOT a `.get()` pattern issue.
It was a **logic gap**: the function updated `judge_score`, `judge_passed`, `judge_grade`,
`judge_reasoning` in `run_result.json` but simply never updated `criteria_scores`. This meant:
- Old `criteria_scores` persisted in `run_result.json` even after re-judging
- If the original run had `null` criteria_scores, re-judging wouldn't fix it
- The bug was invisible until you checked `run_result.json` after a re-judge run

## Analysis Tool That Found All Sites

Three parallel sub-agents were launched to audit the codebase:
1. `feature-dev:code-explorer` — read all relevant source files and mapped type definitions
2. `feature-dev:code-explorer` (second instance) — deep sweep of all criteria_scores references
3. `feature-dev:code-explorer` (third instance) — audited judge error handling paths

The combination of all three reports produced the complete 9-site vulnerability map.
