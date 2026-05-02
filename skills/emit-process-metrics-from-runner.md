---
name: emit-process-metrics-from-runner
description: Emitting process_metrics, progress_tracking, and changes blocks to run_result.json
  from the E2E runner stage pipeline
category: evaluation
date: 2026-02-27
version: 1.0.0
---
# Emit process_metrics from E2E Runner Stage Pipeline

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Project** | ProjectScylla |
| **Issue** | #1133 |
| **Objective** | Populate and write `process_metrics`, `progress_tracking`, and `changes` blocks to `run_result.json` at run completion using git diff output and judge scores |
| **Outcome** | ✅ Success — 51 new tests, all 3308 pass, 78.39% coverage |
| **Impact** | Medium — Enables loader to use pre-computed process_metrics path for R_Prog, Strategic Drift, CFP, PR Revert Rate |
| **PR** | https://github.com/HomericIntelligence/ProjectScylla/pull/1177 |

## When to Use This Skill

Use this skill when:

1. **Populating process_metrics from git diff** in any stage-based E2E pipeline
2. **Deriving structured tracking data mechanically** from git diff/status output rather than live agent hooks
3. **Extending `run_result.json`** with extra blocks beyond the frozen Pydantic model
4. **Hooking into stage pipelines** between `stage_capture_diff` and `stage_finalize_run`
5. **Writing TDD-first E2E stage tests** with mocked subprocess and mocked `detect_rate_limit`

**Triggers**:
- "The loader reads X but nothing writes it"
- "Populate process_metrics / progress_tracking / changes in run_result.json"
- "Derive change tracking from git diff output"
- "Write process metrics at run completion"

## Verified Workflow

### 1. Design Principle: Mechanical Derivation, Not LLM Classification

The key architectural decision is to derive all process metrics **mechanically from git diff output** rather than making additional LLM calls:

- **`changes` block**: Each file in `git diff --stat` → one `ChangeResult`
- **`progress_tracking` block**: Each file in `_get_workspace_state()` → one `ProgressStep`
- **`process_metrics` block**: Computed by `calculate_process_metrics()` from the above

This is faster, cheaper, and reproducible.

### 2. Stage Pipeline Hook Points

The two stage functions that matter:

```
AGENT_COMPLETE → stage_capture_diff()   # git diff available; judge not yet run
                                         # → populate preliminary ctx.progress_steps,
                                         #   ctx.change_results
JUDGE_COMPLETE → stage_finalize_run()   # judge score/passed now known
                                         # → finalize structs, compute ProcessMetrics,
                                         #   write extended run_result.json
```

**Critical**: populate preliminary data in `stage_capture_diff` (when diff is fresh),
finalize with actual judge outcome in `stage_finalize_run`.

### 3. RunContext Field Pattern

Add two new optional fields to `RunContext` dataclass:

```python
@dataclass
class RunContext:
    # ... existing fields ...

    # Process metrics tracking (populated by stage_capture_diff, finalized in stage_finalize_run)
    progress_steps: list[ProgressStep] | None = None
    change_results: list[ChangeResult] | None = None
```

Use `None` as default (not empty list) so callers can distinguish "not yet populated"
from "populated but empty".

### 4. _get_diff_stat() Implementation

```python
def _get_diff_stat(workspace: Path) -> dict[str, tuple[int, int]]:
    """Run git diff --stat HEAD and return per-file (insertions, deletions)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD", "--", ".",
             ":(exclude)CLAUDE.md", ":(exclude).claude"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}
        return _parse_diff_stat_output(result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        return {}
```

**Key patterns**:
- Always exclude test framework files (`CLAUDE.md`, `.claude/`)
- Return `{}` on any error — never raise
- Separate parser function `_parse_diff_stat_output()` for testability

**Parser logic** (handles `git diff --stat` format `path/to/file.py | 5 ++---`):

```python
def _parse_diff_stat_output(stat_output: str) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for line in stat_output.splitlines():
        if "|" not in line:
            continue
        if "file" in line and "changed" in line:  # Skip summary line
            continue
        file_part, _, change_part = line.partition("|")
        filepath = file_part.strip()
        change_str = change_part.strip()
        tokens = change_str.split()
        markers = tokens[1] if len(tokens) > 1 else ""
        insertions = markers.count("+")
        deletions = markers.count("-")
        result[filepath] = (insertions, deletions)
    return result
```

### 5. _build_progress_steps() Implementation

Parse `_get_workspace_state()` string output (lines like `- \`filepath\` (status)`):

```python
def _build_progress_steps(
    workspace_state: str,
    *,
    judge_score: float,
    diff_stat: dict[str, tuple[int, int]],
) -> list[ProgressStep]:
    entries: list[tuple[str, str]] = []
    for line in workspace_state.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- `"):
            continue
        try:
            path_end = stripped.index("`", 3)
            filepath = stripped[3:path_end]
            status_start = stripped.index("(", path_end) + 1
            status_end = stripped.index(")", status_start)
            status = stripped[status_start:status_end]
        except ValueError:
            continue
        if filepath:
            entries.append((filepath, status))

    if not entries:
        return []

    # Normalize weights by line delta
    deltas = {fp: max(1, ins + dels) for fp, (ins, dels) in diff_stat.items()}
    file_deltas = [deltas.get(fp, 1) for fp, _ in entries]
    total_delta = sum(file_deltas)

    return [
        ProgressStep(
            step_id=filepath,
            description=f"{status} {filepath}",
            weight=delta / total_delta if total_delta > 0 else 1.0,
            completed=True,  # agent actually changed it
            goal_alignment=judge_score,  # proxy; finalized later
        )
        for (filepath, status), delta in zip(entries, file_deltas)
    ]
```

**Weight normalization**: `weight = file_delta / total_delta`. Single-file case normalizes to 1.0.

### 6. Finalize Helpers (Immutable Pattern)

Both finalize helpers return **new lists** (never mutate input):

```python
def _finalize_change_results(
    change_results: list[ChangeResult],
    *,
    judge_passed: bool,
    pipeline_passed: bool,
) -> list[ChangeResult]:
    return [
        ChangeResult(
            change_id=cr.change_id,
            description=cr.description,
            succeeded=judge_passed,
            caused_failure=not pipeline_passed,
            reverted=cr.reverted,
        )
        for cr in change_results
    ]


def _finalize_progress_steps(
    progress_steps: list[ProgressStep],
    *,
    judge_score: float,
) -> list[ProgressStep]:
    return [
        ProgressStep(
            step_id=ps.step_id,
            description=ps.description,
            weight=ps.weight,
            completed=ps.completed,
            goal_alignment=judge_score,
        )
        for ps in progress_steps
    ]
```

### 7. stage_finalize_run Extension (Extended Dict Pattern)

The `E2ERunResult` Pydantic model is frozen — do NOT add new fields to it.
Instead, extend the serialized dict after calling `to_dict()`:

```python
# Compute final process metrics
pipeline_passed = (
    ctx.judge_pipeline_result.all_passed if ctx.judge_pipeline_result is not None else True
)
final_change_results = _finalize_change_results(
    ctx.change_results or [], judge_passed=run_result.judge_passed,
    pipeline_passed=pipeline_passed,
)
final_progress_steps = _finalize_progress_steps(
    ctx.progress_steps or [], judge_score=run_result.judge_score
)
tracker = ProgressTracker(
    expected_steps=final_progress_steps,
    achieved_steps=[s for s in final_progress_steps if s.completed],
)
pm = calculate_process_metrics(tracker=tracker, changes=final_change_results)

# Extend the serialized dict (not the model)
result_dict = run_result.to_dict()
result_dict["process_metrics"] = {
    "r_prog": pm.r_prog,
    "strategic_drift": pm.strategic_drift,
    "cfp": pm.cfp,
    "pr_revert_rate": pm.pr_revert_rate,
}
result_dict["progress_tracking"] = [dataclasses.asdict(s) for s in final_progress_steps]
result_dict["changes"] = [dataclasses.asdict(c) for c in final_change_results]

with open(ctx.run_dir / "run_result.json", "w") as f:
    json.dump(result_dict, f, indent=2)
```

**Key**: `ctx.change_results or []` handles the `None` default gracefully.

### 8. stage_capture_diff — Resume Branch

When judge is already done (resume case), set empty lists:

```python
if not ctx.agent_ran and _has_valid_judge_result(ctx.run_dir):
    # ... load judgment ...
    ctx.diff_result = {}
    ctx.progress_steps = []   # ← ADD THIS
    ctx.change_results = []   # ← ADD THIS
    return
```

Without this, the fields remain `None` and `stage_finalize_run` falls back to empty gracefully via `ctx.change_results or []`.

### 9. TDD Test Strategy

**Mock pattern for `_get_diff_stat`**:
```python
def test_parses_modified_file(self, tmp_path: Path) -> None:
    stat_output = " foo/bar.py | 5 ++---\n 1 file changed, 2 insertions(+), 3 deletions(-)\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=stat_output, stderr="")
        result = _get_diff_stat(tmp_path)
    assert "foo/bar.py" in result
    insertions, deletions = result["foo/bar.py"]
    assert insertions == 2
    assert deletions == 3
```

**Mock pattern for `stage_finalize_run`** — patch at the module where `detect_rate_limit` is imported (lazy import inside stage function):
```python
# CORRECT: patch the module that contains it
with patch("scylla.e2e.rate_limit.detect_rate_limit", return_value=None):
    stage_finalize_run(ctx)

# WRONG: stages.py imports it lazily, so this won't work
with patch("scylla.e2e.stages.detect_rate_limit", return_value=None):
    stage_finalize_run(ctx)  # AttributeError!
```

**Test for weight normalization**:
```python
def test_weights_sum_to_one_with_multiple_files(self) -> None:
    workspace_state = (
        "Files modified/created by agent:\n- `a.py` (modified)\n- `b.py` (created)"
    )
    diff_stat = {"a.py": (5, 0), "b.py": (15, 0)}
    result = _build_progress_steps(workspace_state, judge_score=0.8, diff_stat=diff_stat)
    total_weight = sum(s.weight for s in result)
    assert total_weight == pytest.approx(1.0, abs=1e-9)
```

## Failed Attempts & Lessons Learned

| Attempt | Issue | Resolution |
|---------|-------|------------|
| `patch("scylla.e2e.stages.detect_rate_limit")` | AttributeError — lazy import in stage function | Patch `scylla.e2e.rate_limit.detect_rate_limit` instead |
| Using `dataclasses` import without adding it | `dataclasses.asdict()` needed for ProgressStep/ChangeResult serialization | Add `import dataclasses` at top of file |
| `-> dict` return type annotation | mypy `[type-arg]` error | Use `-> dict[str, Any]` with `from typing import Any` |
| Counting `+`/`-` from raw stat number | `git diff --stat` shows `5 ++---` (marker string) | Count `+` chars in marker string, not parse the integer |

### ❌ Attempt 1: Patching detect_rate_limit at wrong module path

**What we tried**:
```python
with patch("scylla.e2e.stages.detect_rate_limit", return_value=None):
    stage_finalize_run(ctx)
```

**Why it failed**:
```
AttributeError: <module 'scylla.e2e.stages' ...> does not have the attribute 'detect_rate_limit'
```

**Root cause**: `stage_finalize_run` uses a lazy local import inside the function body:
```python
def stage_finalize_run(ctx: RunContext) -> None:
    from scylla.e2e.rate_limit import RateLimitError, detect_rate_limit  # ← lazy
    ...
```

Lazy imports don't become module-level attributes, so `patch()` on the importing module fails.

**Fix**: Patch the source module:
```python
with patch("scylla.e2e.rate_limit.detect_rate_limit", return_value=None):
    stage_finalize_run(ctx)
```

**Lesson**: When a function uses lazy/local imports, always patch the **source module**, never the importing module.

### ❌ Attempt 2: Untyped `-> dict` return annotation

**What we tried**:
```python
def _make_judgment(self, passed: bool = True, score: float = 0.8) -> dict:
```

**Why it failed**: mypy `[type-arg]` error — generic `dict` needs type parameters.

**Fix**:
```python
from typing import Any

def _make_judgment(self, passed: bool = True, score: float = 0.8) -> dict[str, Any]:
```

**Lesson**: mypy in this project enforces `[type-arg]` on all generic types. Always add type parameters for `dict`, `list`, `tuple`, etc.

## Results & Parameters

### Files Modified

| File | Lines Added | Purpose |
|------|-------------|---------|
| `scylla/e2e/stages.py` | +303 | New helper functions, RunContext fields, stage updates |
| `tests/unit/e2e/test_stage_process_metrics.py` | +649 (new) | 51 unit tests for all helpers and integration |

### Test Results

```
3308 passed, 9 warnings
Coverage: 78.39% (threshold: 75%)
All pre-commit hooks pass (ruff format, ruff check, mypy, markdown lint, etc.)
```

### Helper Function Summary

| Function | Input | Output | Errors |
|----------|-------|--------|--------|
| `_get_diff_stat(workspace)` | `Path` | `dict[str, tuple[int, int]]` | `{}` on any error |
| `_parse_diff_stat_output(text)` | `str` | `dict[str, tuple[int, int]]` | skips bad lines |
| `_build_change_results(diff_stat, *, judge_passed, pipeline_passed)` | dict + bools | `list[ChangeResult]` | `[]` for empty input |
| `_build_progress_steps(workspace_state, *, judge_score, diff_stat)` | str + float + dict | `list[ProgressStep]` | `[]` for no file entries |
| `_finalize_change_results(changes, *, judge_passed, pipeline_passed)` | list + bools | `list[ChangeResult]` (new) | `[]` for empty input |
| `_finalize_progress_steps(steps, *, judge_score)` | list + float | `list[ProgressStep]` (new) | `[]` for empty input |

### process_metrics JSON Schema (written to run_result.json)

```json
{
  "process_metrics": {
    "r_prog": 0.85,
    "strategic_drift": 0.15,
    "cfp": 0.0,
    "pr_revert_rate": 0.0
  },
  "progress_tracking": [
    {
      "step_id": "src/module.py",
      "description": "modified src/module.py",
      "weight": 0.7,
      "completed": true,
      "goal_alignment": 0.85
    }
  ],
  "changes": [
    {
      "change_id": "src/module.py",
      "description": "Modified src/module.py",
      "succeeded": true,
      "caused_failure": false,
      "reverted": false
    }
  ]
}
```

## Best Practices

1. **Never modify frozen Pydantic models** — extend the serialized dict after `to_dict()`
2. **Separate parsing from subprocess calls** — `_parse_diff_stat_output()` is independently testable
3. **Graceful error handling** — return `{}` / `[]` on any git error, never raise
4. **Immutable finalize helpers** — return new lists, never mutate input
5. **Patch lazy imports at source** — `patch("module.where.defined")` not `patch("module.that.imports")`
6. **Two-phase population** — preliminary data at diff-capture time, finalized at run-finalize time
7. **None sentinel** — use `None` default (not `[]`) so callers can detect "not yet populated"
8. **Type annotations** — always use `dict[K, V]` not bare `dict` to satisfy mypy `[type-arg]`

## Related Skills

- `e2e-checkpoint-resume` — run_result.json dual-persistence pattern
- `parallel-metrics-integration` — extended-dict approach over Pydantic model modification
- `e2e-framework-bug-fixes` — git diff usage in E2E context
- `state-machine-wiring` — RunContext ephemeral field pattern

## References

- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/1177
- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/1133
- Implementation: `scylla/e2e/stages.py` (`_get_diff_stat`, `_build_change_results`, `_build_progress_steps`, `_finalize_change_results`, `_finalize_progress_steps`)
- Tests: `tests/unit/e2e/test_stage_process_metrics.py`
- Loader (reads the blocks): `scylla/analysis/loader.py:625`
- ProcessMetrics types: `scylla/metrics/process.py`
