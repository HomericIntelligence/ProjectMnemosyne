---
name: persist-process-metrics-resume
description: 'TRIGGER CONDITIONS: Persisting process_metrics (progress_steps, change_results)
  through a resume scenario when a run crashes between DIFF_CAPTURED and RUN_FINALIZED
  in ProjectScylla''s 16-stage pipeline. Use when a stage needs to reload previously-computed
  data from a JSON artifact when ctx fields are None on resume.'
category: evaluation
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# persist-process-metrics-resume

How to persist intermediate stage data through crash-resume cycles in ProjectScylla's 16-stage E2E pipeline, using `run_result.json` as the persistence source.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | When a run resumes into `stage_finalize_run` after a crash between JUDGE_COMPLETE and RUN_FINALIZED, reload `progress_steps` and `change_results` from a prior `run_result.json` instead of silently producing empty process_metrics |
| Outcome | Success — 20 new tests, 3530 total passing, 79.6% unit coverage, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1179 |
| PR | HomericIntelligence/ProjectScylla#1296 |

## When to Use

- A stage function uses `ctx.field or []` / `ctx.field or {}` as a fallback for a field that should have been populated by an earlier stage
- A crash/interrupt can leave the field `None` in a resume scenario, producing silently-degraded output
- The missing data was already written to a JSON artifact on disk in a previous (partial) run
- Pattern: "load from JSON if `ctx.field is None` and the artifact exists"

## Architecture: 16-Stage Pipeline Resume Invariant

```
PENDING → DIR_STRUCTURE_CREATED → WORKTREE_CREATED → SYMLINKS_APPLIED
→ CONFIG_COMMITTED → BASELINE_CAPTURED → PROMPT_WRITTEN → REPLAY_GENERATED
→ AGENT_COMPLETE → DIFF_CAPTURED ← (populates ctx.progress_steps + ctx.change_results)
→ JUDGE_PIPELINE_RUN → JUDGE_PROMPT_BUILT → JUDGE_COMPLETE
→ stage_finalize_run ← (writes run_result.json including progress_tracking + changes)
→ RUN_FINALIZED → REPORT_WRITTEN → CHECKPOINTED → WORKTREE_CLEANED
```

**Crash scenario**: If the process dies after `DIFF_CAPTURED` but before `stage_finalize_run` **saves** its output, the next resume starts at `JUDGE_COMPLETE`. `stage_capture_diff` is skipped, so `ctx.progress_steps` and `ctx.change_results` are `None`.

**Old behaviour**: `ctx.change_results or []` silently returns `[]` → empty `process_metrics` block.

**New behaviour**: Check if a partial `run_result.json` exists from the previous partial run and reload the data.

## Verified Workflow

### Step 1: Identify the crash window and the artifact

The crash window is between the stage that **writes** the field and the stage that **needs** it. In this case:
- `stage_capture_diff` (AGENT_COMPLETE → DIFF_CAPTURED): writes `ctx.progress_steps`, `ctx.change_results`
- `stage_finalize_run` (JUDGE_COMPLETE → RUN_FINALIZED): reads and writes `run_result.json`

If an earlier partial run completed `stage_finalize_run`, the data is available in `run_result.json` under `progress_tracking` and `changes` keys.

### Step 2: Write a focused loader helper

Add a private helper just before the first function that needs the data:

```python
def _load_process_metrics_from_run_result(
    run_dir: Path,
) -> tuple[list[ProgressStep] | None, list[ChangeResult] | None]:
    """Load progress_steps and change_results from a previously-saved run_result.json.

    Returns (None, None) if the file does not exist, is invalid, or lacks the
    required keys. Callers must guard against None before using.
    """
    run_result_path = run_dir / "run_result.json"
    if not run_result_path.exists():
        return None, None
    try:
        data = json.loads(run_result_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None, None

    progress_steps: list[ProgressStep] | None = None
    changes: list[ChangeResult] | None = None

    raw_steps = data.get("progress_tracking")
    if isinstance(raw_steps, list):
        progress_steps = [
            ProgressStep(
                step_id=s["step_id"],
                description=s["description"],
                weight=s.get("weight", 1.0),
                completed=s.get("completed", False),
                goal_alignment=s.get("goal_alignment", 1.0),
            )
            for s in raw_steps
            if isinstance(s, dict) and "step_id" in s and "description" in s
        ]

    raw_changes = data.get("changes")
    if isinstance(raw_changes, list):
        changes = [
            ChangeResult(
                change_id=c["change_id"],
                description=c["description"],
                succeeded=c.get("succeeded", True),
                caused_failure=c.get("caused_failure", False),
                reverted=c.get("reverted", False),
            )
            for c in raw_changes
            if isinstance(c, dict) and "change_id" in c and "description" in c
        ]

    return progress_steps, changes
```

### Step 3: Add resume guard at the top of the consuming stage

After the guard assertions (before main logic), check and reload:

```python
def stage_finalize_run(ctx: RunContext) -> None:
    if ctx.agent_result is None:
        raise RuntimeError("agent_result must be set before finalize_run")
    if ctx.judgment is None:
        raise RuntimeError("judgment must be set before finalize_run")

    # Resume guard: if progress_steps/change_results were not populated this
    # session (e.g., crash between DIFF_CAPTURED and JUDGE_COMPLETE skipped
    # stage_capture_diff), try to reload from a previously-saved run_result.json.
    if ctx.progress_steps is None or ctx.change_results is None:
        loaded_steps, loaded_changes = _load_process_metrics_from_run_result(ctx.run_dir)
        if ctx.progress_steps is None:
            ctx.progress_steps = loaded_steps
        if ctx.change_results is None:
            ctx.change_results = loaded_changes

    # ... rest of stage
```

**Critical**: Use `is None` not `not ctx.field` — an **empty list `[]`** from `stage_capture_diff`
(agent made no changes) must NOT be overwritten by disk data. `not []` is `True`, which would
incorrectly trigger the reload.

### Step 4: Write tests covering all boundary cases

Create `tests/unit/e2e/test_<feature>_resume.py` with two test classes:

**Class 1: `TestLoadHelper`** — pure unit tests for the loader:
- Returns `(None, None)` when file is missing
- Returns `(None, None)` on invalid JSON
- Returns `(None, None)` on `OSError`
- Returns `(None, None)` when JSON has no relevant keys
- Loads `ProgressStep` instances correctly (field values + defaults)
- Loads `ChangeResult` instances correctly (field values + defaults)
- Skips malformed entries missing required fields
- Returns empty lists `[]` (not `None`) when keys exist but arrays are empty
- Loads both simultaneously when both keys present

**Class 2: `TestStageFinalizeRunResume`** — integration tests with a `minimal_run_context` fixture:
- `None` ctx field → data reloaded from disk
- `[]` ctx field → data NOT overwritten (empty list preserved)
- Fresh ctx data → NOT overwritten even when disk has different data
- No disk file + `None` ctx field → graceful (no crash, result is empty lists)
- Loaded data produces non-zero `r_prog` in process_metrics output
- Partial-None: only `change_results` is `None` → only that field reloaded, `progress_steps` preserved

### Step 5: Verify

```bash
# New test file only
pixi run python -m pytest tests/unit/e2e/test_<feature>_resume.py -v

# Full e2e unit suite (no-coverage)
pixi run python -m pytest tests/unit/e2e/ --override-ini="addopts=" -v

# Full unit suite with 75% threshold
pixi run python -m pytest tests/unit/ --override-ini="addopts=" --cov=scylla --cov-fail-under=75 -q

# Pre-commit on changed files
pre-commit run --files scylla/e2e/stages.py tests/unit/e2e/test_<feature>_resume.py
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Used `not ctx.progress_steps` as reload guard | `[]` is falsy — this would overwrite a valid empty list from `stage_capture_diff` when agent made no changes | Always use `is None` to distinguish "not set" from "set but empty" |
| Added `# type: ignore[type-arg]` to fixture return type | Mypy flagged it as unused — `RunContext` is not generic | Remove type ignore comments that mypy itself rejects as unused |
| Placing reload logic in `restore_run_context()` (centralized helper) | Would affect all resume paths; only `stage_finalize_run` needs the reload; consistent with existing inline-per-stage resume pattern | Keep resume guards inline at the stage that needs them — don't centralize unless multiple stages share the same pattern |

## Results & Parameters

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| `is None` guard (not `not ctx.field`) | Preserves `[]` set by `stage_capture_diff` when agent made no changes |
| Return `(None, None)` not `([], [])` on error | Lets the existing `or []` fallbacks in `stage_finalize_run` handle the empty case naturally |
| Skip malformed entries (filter, not raise) | Partial data is better than a crash on resume |
| Inline guard in `stage_finalize_run` (not centralized) | Consistent with per-stage resume pattern in all other stage functions |
| Helper placed just before `_build_change_results` | Co-location with other process-metrics helpers in the same file section |

### Test count breakdown

| File | Tests | Focus |
|------|-------|-------|
| `test_stage_finalize_run_resume.py` | 20 | Helper (13) + integration (6) + partial-None (1) |

### Coverage impact

- Unit coverage after change: 79.6% (above 75% threshold)
- Combined floor (9%): unaffected

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1179, PR #1296 | Follow-up from #1133 (process metrics initial implementation) |

## References

- Related skills: `additive-resume-integration-tests`, `wire-figure-pipeline`
- Production file: `scylla/e2e/stages.py`
- Test file: `tests/unit/e2e/test_stage_finalize_run_resume.py`
- Follow-up from: HomericIntelligence/ProjectScylla#1133
