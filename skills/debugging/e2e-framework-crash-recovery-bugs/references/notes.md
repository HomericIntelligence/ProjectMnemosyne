# Notes: E2E Framework Crash Recovery Bugs

## Source Session

- **Date**: 2026-02-23
- **Project**: ProjectScylla
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1080
- **Trigger**: dryrun3 batch analysis revealed 21 ENOENT errors and checkpoint failures

## Diagnosis Methodology

### Step 1 — Identify failure signatures

From batch logs:
- `$0 cost + 8-22s + zero tokens` = Pydantic ValidationError or framework crash on resume
- `FileNotFoundError: checkpoint.tmp.{pid}.json` = thread-safety race condition
- `AssertionError` in `action_config_loaded` = missing tier config on resume
- `ValueError: Could not parse judge response` = Haiku returning conversational text

### Step 2 — Trace the checkpoint race

Inspected `save_checkpoint()`:
```python
# BEFORE (buggy):
temp_path = path.parent / f"{path.stem}.tmp.{os.getpid()}{path.suffix}"
with open(temp_path, "w") as f:
    json.dump(checkpoint.model_dump(), f, indent=2)
temp_path.replace(path)
# No lock — multiple threads overwrite the same temp file
```

### Step 3 — Trace the resume AssertionError

State machine in `_run_tier()`:
1. On fresh run: state = PENDING → `action_pending()` sets `tier_ctx.tier_config`
2. On resume: state = CONFIG_LOADED → `action_pending()` skipped → `action_config_loaded()` asserts non-None → CRASH

Fix: detect non-PENDING/COMPLETE/FAILED state at `_run_tier()` entry and preload config.

### Step 4 — Trace the Haiku judge JSON failures

Haiku (`claude-haiku-4-5-20251001`) intermittently replies conversationally:
- "I appreciate you sharing the context, but I need more info to evaluate this."
- "Here is my assessment: ..." (prose, no JSON)

The `_parse_judge_response()` function raises `ValueError` on non-JSON output. Without retry, the entire judge call fails.

## Key File Locations (ProjectScylla)

| File | Role |
|------|------|
| `scylla/e2e/checkpoint.py` | Bug 1 fix: thread-safe temp file naming + lock |
| `scylla/e2e/runner.py` | Bug 2 fix: preload tier config on resume |
| `scylla/e2e/llm_judge.py` | Bug 3 fix: retry loop with JSON reminder |
| `tests/unit/e2e/test_checkpoint.py` | Bug 1 tests: thread safety |
| `tests/unit/e2e/test_runner.py` | Bug 2 tests: resume preload |
| `tests/unit/e2e/test_llm_judge.py` | Bug 3 tests: judge retry |

## Test Results

- 2975 tests passing
- 77.94% coverage
- All pre-commit hooks pass (ruff, mypy, black)
