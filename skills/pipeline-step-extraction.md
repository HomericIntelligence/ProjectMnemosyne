---
name: pipeline-step-extraction
description: "Skill: Pipeline Step Extraction (CC>15 Reduction)"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Pipeline Step Extraction (CC>15 Reduction)

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-06 |
| Category | refactoring |
| Objective | Reduce cyclomatic complexity of three `llm_judge.py` functions from CC>15 to CC≤8 by extracting private pipeline step helpers |
| Outcome | Success — all three `# noqa: C901` directives removed; 28 new unit tests; 4591 tests pass at 76% coverage |
| Issue | HomericIntelligence/ProjectScylla#1430 |
| PR | HomericIntelligence/ProjectScylla#1457 |

## When to Use

Use this skill when:
- A module-level function executes 4+ sequential pipeline stages, each with `if not installed → (False, True, "")` and `if failed → (False, False, output)` branches
- The function carries a `# noqa: C901` suppression because its CC exceeds the project threshold (12)
- Two parallel pipelines (e.g., mojo + python) share identical step shapes but differ in the subprocess call
- A top-level function has a long context-gathering preamble followed by a retry loop that could be separated

**Companion skills**: See `ruff-c901-mccabe-complexity` for enabling C901 enforcement; `extract-method-to-private-methods` for closure extraction from class methods.

## Verified Workflow

### 1. Identify the step shape

Each pipeline step in `_run_mojo_pipeline` / `_run_python_pipeline` follows this shape:

```python
# Before (inline, 6–10 lines per step)
if not shutil.which("mojo"):
    return BuildPipelineResult(..., passed=False, na=True, ...)
result = _run_subprocess(["mojo", "build", ...], workspace)
if not result.passed:
    return BuildPipelineResult(..., passed=False, ...)
```

Extract each step into a `_run_<pipeline>_<stage>_step` function returning `(passed, na, output)`:

```python
def _run_mojo_build_step(workspace: Path, is_modular: bool) -> tuple[bool, bool, str]:
    if not shutil.which("magic" if is_modular else "mojo"):
        return False, True, ""
    result = _run_subprocess(["mojo", "build", ...], workspace)
    return result.passed, False, result.output
```

### 2. Return-tuple contract

All step helpers use a consistent 3-tuple:

| Position | Type | Meaning |
| ---------- | ------ | --------- |
| 0 | `bool` | `passed` — step succeeded |
| 1 | `bool` | `na` — step not applicable (tool not installed) |
| 2 | `str` | `output` — stdout/stderr from the subprocess |

The pipeline function unpacks and early-returns on failure:

```python
passed, na, output = _run_mojo_build_step(workspace, is_modular)
if na:
    return BuildPipelineResult(build=StepResult(passed=False, output="", na=True), ...)
if not passed:
    return BuildPipelineResult(build=StepResult(passed=False, output=output), ...)
```

### 3. Extract shared steps across pipelines

When two pipelines share an identical step (e.g., pre-commit), extract a single shared helper
with a generic name (no pipeline prefix):

```python
# Shared by both _run_mojo_pipeline and _run_python_pipeline
def _run_precommit_step(
    workspace: Path, env: dict[str, str] | None = None
) -> tuple[bool, bool, str]:
    if not shutil.which("pre-commit"):
        return False, True, ""
    result = _run_subprocess(["pre-commit", "run", "--all-files"], workspace, env=env)
    return result.passed, False, result.output
```

### 4. Decompose large orchestrator functions (two-phase split)

For functions like `run_llm_judge` that mix context gathering with retry execution:

**Phase 1 — context gathering** (`_gather_judge_context`):
- Accepts all input parameters
- Returns `(judge_prompt: str, pipeline_result: BuildPipelineResult | None)`
- Handles: file reading, baseline formatting, rubric loading, pipeline execution

**Phase 2 — retry execution** (`_execute_judge_with_retry`):
- Accepts: `judge_prompt, model, workspace, judge_dir, judge_start, language`
- Returns: `JudgeResult`
- Handles: LLM call loop, retry on rate-limit/empty, timeout, logging

```python
# After decomposition
def run_llm_judge(...) -> JudgeResult:
    judge_start = time.time()
    judge_prompt, _pipeline_result = _gather_judge_context(...)
    return _execute_judge_with_retry(judge_prompt, model, workspace, judge_dir, judge_start, language)
```

### 5. Promote inline imports to module level

Functions with inline imports (`import time`, `from datetime import datetime, timezone`) hide
dependencies and inflate per-call complexity. Move them to module level before extracting helpers —
otherwise extracted helpers that need them will require their own inline imports.

```python
# Remove from function bodies; add once at module top
import time
from datetime import datetime, timezone
```

### 6. Verify CC is resolved

```bash
pixi run ruff check --select C901 scylla/e2e/llm_judge.py
# Expected: "All checks passed!"
```

Then remove the `# noqa: C901` directives from all three functions.

### 7. Fix RUF059 (unpacked variables never used) in tests and source

When unpacking the 3-tuple in tests or callers, prefix unused fields with `_`:

```python
# Test: only asserting on `passed`
passed, _na, _output = _run_mojo_build_step(workspace, is_modular=False)
assert passed is False

# Test: asserting on `output`
_passed, _na, output = _run_precommit_step(workspace)
assert "not available" in output

# Source: pipeline_result not used after context gathering
judge_prompt, _pipeline_result = _gather_judge_context(...)
```

**Exception**: keep `output` (not `_output`) when the variable IS used in an assertion. RUF059
flags variables that are completely unused in the rest of the scope.

### 8. Write step-helper unit tests

Each step helper needs three test cases:

| Test | Setup | Assert |
| ------ | ------- | -------- |
| tool not installed | `mock_which.return_value = None` | `passed=False`, `na=True`, `output=""` |
| tool installed, step fails | `mock_which.return_value = "/usr/bin/mojo"`, subprocess returns failure | `passed=False`, `na=False` |
| tool installed, step passes | `mock_which.return_value = "/usr/bin/mojo"`, subprocess returns success | `passed=True`, `na=False` |

Use `unittest.mock.patch` with `side_effect` for subprocess, `wraps` is unnecessary.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### CC before and after

| Function | CC Before | CC After |
| ---------- | ----------- | ---------- |
| `_run_mojo_pipeline` | ~18 | ~6 |
| `_run_python_pipeline` | ~16 | ~6 |
| `run_llm_judge` | ~17 | ~8 |

### New helpers added

| Helper | Shared? | Returns |
| -------- | --------- | --------- |
| `_run_mojo_build_step` | no | `tuple[bool, bool, str]` |
| `_run_mojo_format_step` | no | `tuple[bool, bool, str]` |
| `_run_mojo_test_step` | no | `tuple[bool, bool, str]` |
| `_run_precommit_step` | yes (mojo+python) | `tuple[bool, bool, str]` |
| `_execute_python_scripts` | no | `list[str]` |
| `_run_python_build_step` | no | `tuple[bool, bool, str]` |
| `_run_python_format_step` | no | `tuple[bool, bool, str]` |
| `_run_python_test_step` | no | `tuple[bool, bool, str]` |
| `_gather_judge_context` | no | `tuple[str, BuildPipelineResult \| None]` |
| `_execute_judge_with_retry` | no | `JudgeResult` |

### Test results

- 28 new unit tests across 3 new test classes
- 4591 total tests pass (76% unit coverage, above 75% threshold)
- All pre-commit hooks pass (ruff format, ruff check, mypy)
- `ruff check --select C901 scylla/e2e/llm_judge.py` → "All checks passed!"
