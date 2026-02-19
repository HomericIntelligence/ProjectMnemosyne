# Fair Evaluation Baseline

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2025-02-15 |
| **Objective** | Implement baseline pipeline regression validation to distinguish agent-introduced failures from pre-existing issues |
| **Outcome** | ✅ Successfully implemented with 367 additions across 8 files, 100% test pass rate |
| **Context** | E2E evaluation framework (ProjectScylla) |
| **Duration** | ~2 hours |

## Problem Statement

E2E evaluation pipelines run build/lint/test **only after** the agent completes, with no "before" snapshot. This creates unfair evaluation where:

- Agent that **breaks** a passing build gets same penalty as
- Agent that **inherits** a pre-existing failure

Without baseline comparison, judges cannot distinguish regressions (agent broke it) from pre-existing failures (it was already broken).

## When to Use This Skill

Use this approach when:

- ✅ Building evaluation frameworks that test agents against existing codebases
- ✅ Need to distinguish agent-introduced failures from inherited issues
- ✅ Want fair evaluation that doesn't penalize agents for pre-existing problems
- ✅ Implementing pipeline state comparison (before/after)
- ✅ Designing LLM judge systems that need regression context

Don't use when:

- ❌ Evaluating against clean-slate environments (no pre-existing state)
- ❌ Only care about absolute pass/fail (not regression detection)
- ❌ Pipeline execution is too expensive to run twice

## Solution Architecture

### Core Pattern: Capture → Persist → Compare → Instruct

```
1. CAPTURE: Run pipeline before agent touches code
2. PERSIST: Save baseline to {results_dir}/pipeline_baseline.json
3. COMPARE: Present both baseline and post-agent results to judge
4. INSTRUCT: Guide judge on regression vs pre-existing vs improvement
```

### Key Design Decisions

**Decision 1: Single Capture, Multiple Runs**

- Baseline captured **once** before first run
- Reused across all runs in subtest (not re-captured per run)
- Rationale: Baseline state is constant, saves execution time

**Decision 2: Checkpoint-Aware Persistence**

- Save baseline immediately after capture
- Load on checkpoint resume (skip re-capture if file exists)
- Rationale: Avoid re-running expensive pipeline operations

**Decision 3: Judge Instruction vs Code Enforcement**

- Put regression logic in **judge system prompt**, not in scoring code
- Rationale: Flexible, allows judge to use reasoning, easier to iterate

**Decision 4: Defensive Optional Parameter**

- `baseline_pipeline_str` remains optional in code
- Judge prompt assumes it's always present
- Rationale: Code stays defensive, judge instructions stay clear

## Verified Workflow

### Phase 1: Data Model Extension

Add baseline summary field to result model:

```python
# scylla/e2e/models.py
class E2ERunResult(BaseModel):
    # ... existing fields ...
    baseline_pipeline_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            # ... existing fields ...
            "baseline_pipeline_summary": self.baseline_pipeline_summary,
        }
```

**Pattern**: Add optional field with sensible default (None)

### Phase 2: Persistence Helpers

Create module-level helpers for save/load:

```python
# scylla/e2e/subtest_executor.py

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scylla.e2e.llm_judge import BuildPipelineResult

def _save_pipeline_baseline(results_dir: Path, result: "BuildPipelineResult") -> None:
    """Save pipeline baseline result to JSON."""
    baseline_path = results_dir / "pipeline_baseline.json"
    baseline_path.write_text(json.dumps(result.model_dump(), indent=2))
    logger.info(f"Saved pipeline baseline to {baseline_path}")

def _load_pipeline_baseline(results_dir: Path) -> "BuildPipelineResult | None":
    """Load pipeline baseline result from JSON."""
    from scylla.e2e.llm_judge import BuildPipelineResult

    baseline_path = results_dir / "pipeline_baseline.json"
    if not baseline_path.exists():
        return None

    try:
        data = json.loads(baseline_path.read_text())
        return BuildPipelineResult(**data)
    except Exception as e:
        logger.warning(f"Failed to load baseline: {e}")
        return None
```

**Pattern**: Forward-declare type with TYPE_CHECKING to avoid circular imports

### Phase 3: Baseline Capture in Executor

Capture once before first run, after workspace setup:

```python
# scylla/e2e/subtest_executor.py - in run_subtest()

# Track baseline (captured once before first run)
pipeline_baseline: "BuildPipelineResult | None" = None

for run_num in range(1, self.config.runs_per_subtest + 1):
    # ... checkpoint resume logic ...

    # Setup workspace
    _setup_workspace(...)
    _commit_test_config(workspace)

    # Capture baseline once
    if pipeline_baseline is None:
        # Try checkpoint resume first
        pipeline_baseline = _load_pipeline_baseline(results_dir)

        # Capture if not found
        if pipeline_baseline is None:
            from scylla.e2e.llm_judge import _run_build_pipeline

            _phase_log("BASELINE", "Capturing pipeline baseline")
            pipeline_baseline = _run_build_pipeline(
                workspace=workspace,
                language=tier_config.language,
            )

            # Save for checkpoint resume
            _save_pipeline_baseline(results_dir, pipeline_baseline)

            # Log status
            baseline_status = (
                "ALL PASSED ✓" if pipeline_baseline.all_passed
                else "SOME FAILED ✗"
            )
            logger.info(f"Pipeline baseline: {baseline_status}")

    # Execute run with baseline
    run_result = self._execute_single_run(
        # ... other params ...
        pipeline_baseline=pipeline_baseline,
    )
```

**Pattern**: Checkpoint-aware lazy initialization

### Phase 4: Thread Through Execution Pipeline

Add `pipeline_baseline` parameter at each level:

```python
# scylla/e2e/subtest_executor.py
def _execute_single_run(
    self,
    # ... existing params ...
    pipeline_baseline: "BuildPipelineResult | None" = None,
) -> RunResult:
    # ... execute agent ...

    # Pass to judge
    judgment, judges = _run_judge(
        # ... other params ...
        pipeline_baseline=pipeline_baseline,
    )

    # Convert to summary for result
    baseline_summary = None
    if pipeline_baseline:
        baseline_summary = {
            "all_passed": pipeline_baseline.all_passed,
            "build_passed": pipeline_baseline.build_passed,
            "format_passed": pipeline_baseline.format_passed,
            "test_passed": pipeline_baseline.test_passed,
        }

    return RunResult(
        # ... other fields ...
        baseline_pipeline_summary=baseline_summary,
    )
```

```python
# scylla/e2e/judge_runner.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scylla.e2e.llm_judge import BuildPipelineResult

def _run_judge(
    # ... existing params ...
    pipeline_baseline: "BuildPipelineResult | None" = None,
) -> tuple[dict, list[JudgeResultSummary]]:
    judge_result = run_llm_judge(
        # ... other params ...
        pipeline_baseline=pipeline_baseline,
    )
```

```python
# scylla/e2e/llm_judge.py
def run_llm_judge(
    # ... existing params ...
    pipeline_baseline: "BuildPipelineResult | None" = None,
) -> JudgeResult:
    # Format baseline
    baseline_pipeline_str = None
    if pipeline_baseline:
        baseline_status = (
            "ALL PASSED ✓" if pipeline_baseline.all_passed
            else "SOME FAILED ✗"
        )
        baseline_pipeline_str = (
            f"**Overall Status**: {baseline_status}\n\n"
            f"{pipeline_baseline.to_context_string()}"
        )

    # Build judge prompt
    judge_prompt = build_task_prompt(
        # ... other params ...
        baseline_pipeline_str=baseline_pipeline_str,
    )
```

**Pattern**: Thread optional parameter through call stack, format at final layer

### Phase 5: Prompt Construction

Add baseline section before post-agent section:

```python
# scylla/judge/prompts.py
def build_task_prompt(
    # ... existing params ...
    baseline_pipeline_str: str | None = None,
) -> str:
    sections = []

    # ... rubric, task, output, workspace sections ...

    # Baseline BEFORE post-agent
    if baseline_pipeline_str:
        sections.append(
            f"## Baseline Pipeline Results (Before Agent)\n\n"
            f"*This shows the build/lint/test status BEFORE the agent "
            f"made any changes. Use this to distinguish regressions "
            f"(things that got worse) from pre-existing failures.*\n\n"
            f"{baseline_pipeline_str}"
        )

    # Post-agent results
    if pipeline_result_str:
        sections.append(
            f"## Build/Lint/Test Pipeline Results (After Agent)\n\n"
            f"{pipeline_result_str}"
        )

    return "\n\n".join(sections)
```

**Pattern**: Optional sections with explanatory context

### Phase 6: Judge Instructions

Add regression handling section to system prompt:

```markdown
<!-- config/judge/system_prompt.md -->

<baseline_regression>
Baseline pipeline results (before agent) and post-agent pipeline results
are provided. Evaluate pipeline failures based on whether they are
regressions, pre-existing, or improvements:

__Regressions__ (passed in baseline → failed after agent): These are NEW
failures introduced by the agent's changes. Penalize these heavily as the
agent broke previously working functionality. This indicates the agent did
not properly validate their changes.

__Pre-existing failures__ (failed in baseline → failed after agent): These
failures existed before the agent started. Mark the corresponding rubric
items as N/A and do not penalize the agent for them, unless the task
explicitly required fixing these failures.

__Improvements__ (failed in baseline → passed after agent): The agent fixed
a pre-existing failure. Recognize this positively in your evaluation,
especially if the task did not explicitly require fixing pipeline issues.

When evaluating build_pipeline rubric items, check the baseline first to
determine if failures are regressions or pre-existing before scoring.
</baseline_regression>
```

**Pattern**: Clear categorization with explicit actions for each scenario

### Phase 7: Rubric Updates (Optional)

Update rubric items to reference regression behavior:

```yaml
# tests/fixtures/tests/test-001/expected/rubric.yaml
build_pipeline:
  weight: 0.10
  scoring_type: "checklist"
  items:
    - id: B1
      check: "Python build/syntax check passes (or was already failing in baseline)"
      points: 1.0
      na_condition: "Build already failed in baseline"

    - id: B2
      check: "Python format check passes (or was already failing in baseline)"
      points: 1.0
      na_condition: "ruff not available OR lint already failed in baseline"
```

**Pattern**: Informational only - judge follows system prompt instructions

## Testing Strategy

### Unit Test Coverage

Create comprehensive test file covering all integration points:

```python
# tests/unit/e2e/test_baseline_regression.py

# 1. Prompt rendering with baseline
def test_build_task_prompt_with_baseline():
    """Baseline section rendered when provided."""

# 2. Prompt rendering without baseline
def test_build_task_prompt_without_baseline():
    """No baseline section when None (backward compat)."""

# 3. Section ordering
def test_build_task_prompt_baseline_section_before_post_agent():
    """Baseline appears before post-agent."""

# 4. Persistence round-trip
def test_save_load_pipeline_baseline():
    """Save and load baseline from JSON."""

# 5. Missing file handling
def test_load_pipeline_baseline_missing_file():
    """Returns None when file doesn't exist."""

# 6. Invalid JSON handling
def test_load_pipeline_baseline_invalid_json():
    """Returns None and logs warning for bad JSON."""

# 7. Result model field inclusion
def test_run_result_baseline_field():
    """E2ERunResult.to_dict() includes baseline_pipeline_summary."""

# 8. Result model field optional
def test_run_result_baseline_field_none():
    """baseline_pipeline_summary can be None."""

# 9. Summary conversion
def test_baseline_summary_conversion():
    """BuildPipelineResult correctly converted to summary dict."""
```

**Test Result**: 9/9 passing, 100% success rate

### Integration Test Strategy

Run existing test suites to verify no regressions:

```bash
# New baseline tests
pixi run python -m pytest tests/unit/e2e/test_baseline_regression.py -v

# Existing e2e tests (verify no breakage)
pixi run python -m pytest tests/unit/e2e/ -v

# Existing prompt tests (verify backward compat)
pixi run python -m pytest tests/unit/judge/test_prompts.py -v

# Code quality
pre-commit run --all-files
```

**Result**: 454 e2e tests + 39 prompt tests + 9 new tests = 502 total passing

## Failed Attempts

### ❌ Attempt 1: Import BuildPipelineResult from scylla.e2e.pipeline

**What we tried:**

```python
from scylla.e2e.pipeline import BuildPipelineResult
```

**Error:**

```
ModuleNotFoundError: No module named 'scylla.e2e.pipeline'
```

**Why it failed:**
`BuildPipelineResult` lives in `scylla.e2e.llm_judge`, not in a separate `pipeline` module. We assumed based on the class name that it would be in a dedicated pipeline module.

**Solution:**

```python
from scylla.e2e.llm_judge import BuildPipelineResult
```

**Lesson**: Always verify actual module structure with `grep` before assuming based on class names.

### ❌ Attempt 2: Using PipelineCheckResult class

**What we tried:**

```python
from scylla.e2e.llm_judge import BuildPipelineResult, PipelineCheckResult

mock_result = BuildPipelineResult(
    build_result=PipelineCheckResult(passed=True, exit_code=0, ...),
    lint_result=PipelineCheckResult(passed=False, exit_code=1, ...),
    # ...
)
```

**Error:**

```
ImportError: cannot import name 'PipelineCheckResult' from 'scylla.e2e.llm_judge'
```

**Why it failed:**
We invented a class (`PipelineCheckResult`) that doesn't exist. The actual `BuildPipelineResult` has a flatter structure with direct boolean fields:

```python
class BuildPipelineResult(BaseModel):
    language: str
    build_passed: bool
    build_output: str
    format_passed: bool
    format_output: str
    test_passed: bool
    test_output: str
    all_passed: bool
```

**Solution:**

```python
mock_result = BuildPipelineResult(
    language="python",
    build_passed=True,
    build_output="Build successful",
    format_passed=False,
    format_output="Lint errors found",
    test_passed=True,
    test_output="All tests passed",
    all_passed=False,
)
```

**Lesson**: Read the actual model definition before creating test fixtures. Don't assume nested structure.

### ❌ Attempt 3: Using lint_passed field name

**What we tried:**

```python
baseline_summary = {
    "all_passed": pipeline_baseline.all_passed,
    "build_passed": pipeline_baseline.build_passed,
    "lint_passed": pipeline_baseline.lint_passed,  # Wrong field name
    "test_passed": pipeline_baseline.test_passed,
}
```

**Error:**

```
AttributeError: 'BuildPipelineResult' object has no attribute 'lint_passed'.
Did you mean: 'test_passed'?
```

**Why it failed:**
The field is actually named `format_passed`, not `lint_passed`. We assumed "lint" because that's the common term, but the codebase uses "format" to represent the format/lint check.

**Solution:**

```python
baseline_summary = {
    "all_passed": pipeline_baseline.all_passed,
    "build_passed": pipeline_baseline.build_passed,
    "format_passed": pipeline_baseline.format_passed,  # Correct field name
    "test_passed": pipeline_baseline.test_passed,
}
```

**Lesson**: When working with existing models, always check field names in the model definition. Don't assume based on common terminology.

### ❌ Attempt 4: Circular import in module-level import

**What we tried:**

```python
# scylla/e2e/subtest_executor.py (top of file)
from scylla.e2e.llm_judge import BuildPipelineResult

def _save_pipeline_baseline(results_dir: Path, result: BuildPipelineResult) -> None:
    ...
```

**Error:**

```
Ruff: F821 Undefined name `BuildPipelineResult`
Mypy: error: Name "BuildPipelineResult" is not defined
```

**Why it failed:**
Circular import issue - `llm_judge.py` likely imports from `subtest_executor.py` (or transitively), creating a cycle. Python's import system can't resolve it.

**Solution:**

```python
# scylla/e2e/subtest_executor.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scylla.e2e.llm_judge import BuildPipelineResult

def _save_pipeline_baseline(results_dir: Path, result: "BuildPipelineResult") -> None:
    """Save pipeline baseline result to JSON."""
    baseline_path = results_dir / "pipeline_baseline.json"
    baseline_path.write_text(json.dumps(result.model_dump(), indent=2))

def _load_pipeline_baseline(results_dir: Path) -> "BuildPipelineResult | None":
    """Load pipeline baseline result from JSON."""
    from scylla.e2e.llm_judge import BuildPipelineResult  # Local import

    baseline_path = results_dir / "pipeline_baseline.json"
    if not baseline_path.exists():
        return None
    # ...
```

**Pattern**: Use TYPE_CHECKING for type hints, runtime import inside function

**Lesson**: For circular imports, use TYPE_CHECKING + string annotations for type hints, and import at runtime inside the function that actually uses the class.

### ❌ Attempt 5: Line too long in prompt string

**What we tried:**

```python
sections.append(
    f"## Baseline Pipeline Results (Before Agent)\n\n"
    f"*This shows the build/lint/test status BEFORE the agent made any changes. "
    f"Use this to distinguish regressions (things that got worse) from pre-existing failures.*\n\n"
    f"{baseline_pipeline_str}"
)
```

**Error:**

```
E501 Line too long (107 > 100)
```

**Why it failed:**
The second f-string line exceeded the 100-character limit enforced by Ruff.

**Solution:**

```python
sections.append(
    f"## Baseline Pipeline Results (Before Agent)\n\n"
    f"*This shows the build/lint/test status BEFORE the agent made any changes. "
    f"Use this to distinguish regressions (things that got worse) "
    f"from pre-existing failures.*\n\n"
    f"{baseline_pipeline_str}"
)
```

**Lesson**: Break long f-strings across multiple lines at natural phrase boundaries. The formatter won't auto-fix these.

## Results & Metrics

### Implementation Metrics

| Metric | Value |
|--------|-------|
| **Files Changed** | 8 files |
| **Lines Added** | 367 |
| **Lines Removed** | 9 |
| **Test Coverage** | 9 new tests, 100% pass rate |
| **Existing Tests** | 502 tests, 0 regressions |
| **Pre-commit Status** | All hooks passing |

### Code Distribution

```
scylla/e2e/subtest_executor.py    +89  (baseline capture & persistence)
tests/unit/e2e/test_baseline_regression.py  +230  (comprehensive tests)
scylla/judge/prompts.py           +12  (baseline section rendering)
config/judge/system_prompt.md    +12  (regression instructions)
scylla/e2e/llm_judge.py           +9   (baseline formatting)
scylla/e2e/judge_runner.py        +7   (parameter threading)
scylla/e2e/models.py              +2   (baseline_pipeline_summary field)
tests/fixtures/test-001/rubric.yaml  +6   (example rubric updates)
```

### Performance Characteristics

| Aspect | Impact |
|--------|--------|
| **Baseline Capture** | Single execution per subtest (before first run) |
| **Checkpoint Resume** | Skips re-capture if baseline file exists |
| **Memory** | Minimal - single BuildPipelineResult object per subtest |
| **Disk** | ~2KB per subtest (pipeline_baseline.json) |
| **Execution Time** | +1 pipeline execution per subtest (~10-30s depending on language) |

### Key Parameters

```python
# Baseline capture location
results_dir / "pipeline_baseline.json"

# Baseline summary structure
{
    "all_passed": bool,
    "build_passed": bool,
    "format_passed": bool,
    "test_passed": bool,
}

# Judge prompt sections (in order)
1. Rubric
2. Task
3. Agent Output
4. Workspace State
5. Baseline Pipeline Results (Before Agent)  # NEW
6. Build/Lint/Test Pipeline Results (After Agent)  # RENAMED
7. Evaluation instruction
```

## Common Pitfalls

1. **Circular Import**: Don't import `BuildPipelineResult` at module level in `subtest_executor.py`
   - ✅ Use TYPE_CHECKING + string annotations
   - ✅ Import at runtime inside functions

2. **Field Names**: The format check field is `format_passed`, not `lint_passed`
   - ✅ Always check actual model definition
   - ❌ Don't assume based on common terminology

3. **Model Structure**: `BuildPipelineResult` has flat structure, not nested check results
   - ✅ Read model definition before creating test fixtures
   - ❌ Don't invent non-existent classes

4. **Module Location**: `BuildPipelineResult` is in `llm_judge.py`, not a separate pipeline module
   - ✅ Use grep to find actual import paths
   - ❌ Don't assume based on class names

5. **Line Length**: F-strings in multi-line constructs need manual breaking
   - ✅ Split at natural phrase boundaries
   - ❌ Don't rely on auto-formatter for f-strings

## Extensions & Variations

### Variation 1: Multi-Level Baselines

For more granular regression detection:

```python
# Capture baselines at different stages
pre_agent_baseline = _run_build_pipeline(workspace)
post_install_baseline = _run_build_pipeline(workspace)  # After deps install
post_change_baseline = _run_build_pipeline(workspace)  # After code change

# Compare: pre-agent → post-install → post-change
# Identify: which stage introduced the failure?
```

### Variation 2: Baseline Diff Visualization

Generate visual diff in judge prompt:

```
## Pipeline Regression Analysis

| Check  | Baseline | After Agent | Status      |
|--------|----------|-------------|-------------|
| Build  | ✅       | ✅          | No change   |
| Lint   | ❌       | ❌          | Pre-existing|
| Test   | ✅       | ❌          | REGRESSION  |
```

### Variation 3: Severity-Weighted Regression

Not all regressions are equal:

```python
REGRESSION_SEVERITY = {
    "build": 1.0,      # Breaking build is critical
    "test": 0.8,       # Breaking tests is serious
    "format": 0.3,     # Format issues are minor
    "precommit": 0.5,  # Hook failures are moderate
}

regression_penalty = sum(
    REGRESSION_SEVERITY[check]
    for check in failed_checks
    if baseline[check] == "passed"
)
```

## References

- **PR**: <https://github.com/HomericIntelligence/ProjectScylla/pull/705>
- **Commit**: 0871e6b - feat(e2e): Add baseline pipeline regression validation
- **Related Files**:
  - `scylla/e2e/llm_judge.py` - BuildPipelineResult definition
  - `scylla/e2e/subtest_executor.py` - Baseline capture logic
  - `config/judge/system_prompt.md` - Regression evaluation instructions

## Tags

`#evaluation` `#baseline` `#regression-detection` `#fair-evaluation` `#pipeline` `#e2e` `#llm-judge` `#checkpoint-resume` `#type-checking`
