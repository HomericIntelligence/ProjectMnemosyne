# Implementation Notes: Multi-Language Judge Pipelines

## Session Context

**Date**: 2026-01-09
**Project**: ProjectScylla E2E Testing Framework
**Objective**: Fix test-001 failures by adding Python pipeline support to judge system

## Problem Statement

The E2E test framework's judge system had hardcoded Mojo build pipelines:
- `mojo build .`
- `mojo format --check .`
- `mojo test`

test-001 is Python-based (creates `hello.py`), causing failures when judge tried to run Mojo commands on Python code.

## Initial State

```python
# BuildPipelineResult was Mojo-specific
@dataclass
class BuildPipelineResult:
    mojo_build_passed: bool
    mojo_build_output: str
    mojo_format_passed: bool
    mojo_format_output: str
    # ... only Mojo fields
```

## User Requirements

1. **No backward compatibility** - Make language field required, fail if not present
2. **Update all test fixtures** - Add language field to all 47 test.yaml files based on content
3. **Proper pipeline routing** - Python tests get Python pipeline, Mojo tests get Mojo pipeline

## Files Modified

### Core Pipeline Infrastructure
- `src/scylla/e2e/llm_judge.py` (235 lines changed)
  - Renamed BuildPipelineResult fields (mojo_* → generic)
  - Added `_run_mojo_pipeline()` - original Mojo logic
  - Added `_run_python_pipeline()` - new Python logic
  - Added `_run_build_pipeline(language)` - router
  - Updated `to_context_string()` to be language-aware
  - Updated all helper functions with language parameter

### Configuration Models
- `src/scylla/config/models.py`
  - Made `language` required in EvalCase
- `src/scylla/e2e/models.py`
  - Made `language` required in ExperimentConfig (moved before optional fields)
  - Updated `to_dict()` and `load()` methods

### Execution Flow
- `src/scylla/e2e/subtest_executor.py`
  - Added language parameter to `_run_judge()`
  - Passed `self.config.language` through to judge

### Configuration Loading
- `scripts/run_e2e_experiment.py`
  - Load language from test.yaml
  - Added validation to fail if language not set
  - Pass language to ExperimentConfig constructor

### Test Fixtures
- Updated all 47 test.yaml files in `tests/fixtures/tests/test-*/`
  - test-001: `language: python`
  - test-002 through test-047: `language: mojo`

### Unit Tests
- `tests/unit/e2e/test_models.py` - Added language to ExperimentConfig tests
- `tests/unit/e2e/test_resume.py` - Added language to experiment_config fixture

## Python Pipeline Details

```python
def _run_python_pipeline(workspace: Path) -> BuildPipelineResult:
    results = {"language": "python"}

    # Syntax check (always available)
    python -m compileall -q .

    # Linting (optional - graceful fallback if not installed)
    try:
        ruff check .
    except FileNotFoundError:
        # Skip if ruff not installed
        pass

    # Tests (optional - graceful fallback if not installed)
    try:
        pytest -v
    except FileNotFoundError:
        # Skip if pytest not installed
        pass

    # Pre-commit (runs on all)
    pre-commit run --all-files
```

## Mojo Pipeline Details

```python
def _run_mojo_pipeline(workspace: Path) -> BuildPipelineResult:
    results = {"language": "mojo"}

    # All Mojo tools are expected to be available
    mojo build .
    mojo format --check .
    mojo test
    pre-commit run --all-files
```

## Key Technical Decisions

### 1. Required vs Optional Field

**Decision**: Make language required with no default
**Rationale**: User explicitly requested no backward compatibility - fail fast with clear error

### 2. Field Ordering in Dataclass

**Issue**: `TypeError: non-default argument 'language' follows default argument 'timeout_seconds'`
**Solution**: Move `language` before all optional fields

```python
# BEFORE (failed)
timeout_seconds: int = 3600
language: str  # ERROR

# AFTER (works)
language: str
timeout_seconds: int = 3600
```

### 3. Optional Tool Handling

**Decision**: Gracefully skip optional tools (ruff, pytest) if not installed
**Rationale**: Python projects may not have all tools, don't want to force installation

### 4. Language Detection Strategy

**Options Considered**:
1. Auto-detect from files (.py vs .mojo)
2. Explicit field in test.yaml
3. Both (explicit with fallback)

**Chosen**: Explicit field in test.yaml
**Rationale**: User preference - clearer, no ambiguity

## Test Results

### Pre-commit
✅ ruff passed
✅ ruff-format passed

### Unit Tests
✅ 27/28 tests passed in test_models.py and test_resume.py
❌ 1 unrelated test failure in test_rate_limit.py (pre-existing)

### Test Fixtures
✅ All 47 test.yaml files updated with language field
✅ test-001: python
✅ test-002 through test-047: mojo

## Lessons Learned

1. **Dataclass gotcha**: Required fields must come before optional fields
2. **Serialization requires 3 updates**: field definition, `to_dict()`, `load()`
3. **Breaking changes**: Clear validation errors > silent defaults
4. **Bulk updates**: Use Python scripts for systematic file updates
5. **Pipeline abstraction**: Generic field names enable multi-language support

## Command Examples

### Running test-001 (Python)
```bash
python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 \
  --subtests 01-empty \
  --runs 1
```

### Expected Judge Output
```markdown
### Python Build (PASSED)
```
Python syntax check passed
```

### Python Format Check (PASSED)
```
ruff check .
All checks passed!
```

### Python Test (PASSED)
```
pytest -v
collected 0 items
```
```

## Future Enhancements

1. **More languages**: Add support for Rust, Go, etc.
2. **Custom pipelines**: Allow test.yaml to specify custom commands
3. **Pipeline caching**: Cache tool availability checks across runs
4. **Parallel execution**: Run pipeline steps in parallel where safe
