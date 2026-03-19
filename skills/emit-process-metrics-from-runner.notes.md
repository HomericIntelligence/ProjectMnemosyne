# Raw Notes: emit-process-metrics-from-runner

## Session Context

- **Date**: 2026-02-27
- **Issue**: #1133 — Emit process_metrics block from EvalOrchestrator/runner
- **Branch**: `1133-auto-impl`
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1177

## Key Files

### Source Files
- `scylla/e2e/stages.py` — Main implementation (helper functions + stage modifications)
- `scylla/metrics/process.py` — ChangeResult, ProgressStep, ProcessMetrics, calculate_process_metrics
- `scylla/e2e/llm_judge.py:562` — `_get_workspace_state()` parses git status --porcelain
- `scylla/analysis/loader.py:625` — Reads process_metrics from run_result.json (pre-existing)

### Test Files
- `tests/unit/e2e/test_stage_process_metrics.py` — 51 new tests

## Implementation Timeline

1. Read issue and plan from `gh issue view 1133 --comments`
2. Explored: `scylla/metrics/process.py`, `scylla/e2e/stages.py`, `scylla/e2e/models.py`
3. Wrote test file first (TDD)
4. Added imports + RunContext fields to stages.py
5. Implemented helper functions in stages.py
6. Modified stage_capture_diff
7. Modified stage_finalize_run
8. Fixed test: wrong mock path for detect_rate_limit
9. Fixed test: missing `Any` type annotation on `_make_judgment`
10. Pre-commit passed (ruff format auto-fixed some spacing)
11. Commit + push + PR

## Design Decisions

### Why git diff --stat (not git diff --numstat)?
`--stat` format (` path | 5 ++---`) is more commonly used in the codebase.
`--numstat` gives exact counts but the `++---` marker counting is simpler to parse
for our purposes (we only need relative weights, not exact counts).

Actually: `--stat` shows marker strings like `++---`, NOT exact numbers.
The summary line has the actual count ("2 insertions(+), 3 deletions(-)").
Our parser counts `+` and `-` chars in the marker string, which gives approximate
relative weights — good enough for weight normalization.

### Why two-phase (capture + finalize)?
Judge score is not known at diff-capture time. We need the judge score for
`goal_alignment` in ProgressSteps and `succeeded` in ChangeResults.
Solution: store preliminary data, finalize in stage_finalize_run.

### Why not modify E2ERunResult Pydantic model?
It's a frozen model. Adding new fields would break the existing `to_dict()` contract
and potentially the loader. The extended-dict pattern (augmenting the serialized dict)
is already used for `baseline_pipeline_summary` and is established project pattern.

### pipeline_passed determination
`ctx.judge_pipeline_result.all_passed` if available, else True (defensive default).
The judge pipeline runs after diff capture, so it's available in stage_finalize_run.

## Workspace State String Format

`_get_workspace_state()` returns lines like:
```
Files modified/created by agent:
- `path/to/file.py` (modified)
- `path/to/other.py` (created)
- `path/to/deleted.py` (deleted)
(no changes detected)
```

Our parser: look for lines starting with `- \`` and extract path + status.

## git diff --stat Output Format

```
 path/to/file.py | 5 ++---
 another/file.py | 3 +++
 2 files changed, 8 insertions(+), 3 deletions(-)
```

Key: `|` separates path from change markers. Summary line has "file" + "changed".
Marker string: `++---` means 2 insertions, 3 deletions (count `+` and `-` chars).
Leading/trailing whitespace on path must be stripped.

## Test Count

- `TestGetDiffStat`: 9 tests
- `TestBuildChangeResults`: 8 tests
- `TestBuildProgressSteps`: 11 tests
- `TestFinalizeChangeResults`: 6 tests
- `TestFinalizeProgressSteps`: 5 tests
- `TestStageFinalizeRunProcessMetrics`: 8 tests (integration)
- **Total**: 51 new tests