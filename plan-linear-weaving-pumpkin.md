# Plan: Add Language-Specific Build Pipelines for Judge System

## Problem Statement

The E2E test framework's build pipeline is hardcoded to run Mojo tooling (`mojo build`, `mojo format`, `mojo test`) for all tests. test-001 is Python-based (creates `hello.py`), causing pipeline failures when trying to run Mojo commands on a Python workspace.

## Root Cause

- `src/scylla/e2e/llm_judge.py:139-220` - `_run_build_pipeline()` only runs Mojo commands
- `BuildPipelineResult` dataclass (lines 72-96) has only Mojo-specific fields
- No language configuration exists in test.yaml schema

## Solution: Explicit Language Configuration

Add a `language` field to test.yaml that determines which build pipeline to run.

---

## Implementation Steps

### Step 1: Update Test Schema with Language Field

**File**: `tests/fixtures/tests/test-001/test.yaml`

Add `language: python` field:
```yaml
id: "test-001"
name: "Hello World Task"
language: python  # NEW: Specifies pipeline type
...
```

### Step 2: Create Language-Agnostic BuildPipelineResult

**File**: `src/scylla/e2e/llm_judge.py`

Replace Mojo-specific `BuildPipelineResult` with language-agnostic version:

```python
@dataclass
class BuildPipelineResult:
    """Results from running build/lint pipeline."""

    language: str  # "python" or "mojo"
    build_passed: bool
    build_output: str
    format_passed: bool
    format_output: str
    test_passed: bool
    test_output: str
    precommit_passed: bool
    precommit_output: str
    all_passed: bool
```

### Step 3: Add Python Build Pipeline

**File**: `src/scylla/e2e/llm_judge.py`

Add `_run_python_pipeline()` function:
```python
def _run_python_pipeline(workspace: Path) -> BuildPipelineResult:
    """Run Python build/lint pipeline."""
    results = {"language": "python"}

    # Python syntax check
    # ruff check .
    # pytest (if tests exist)
    # pre-commit run --all-files
```

### Step 4: Create Pipeline Router

**File**: `src/scylla/e2e/llm_judge.py`

Modify `_run_build_pipeline()` to accept language parameter:
```python
def _run_build_pipeline(workspace: Path, language: str = "mojo") -> BuildPipelineResult:
    if language == "python":
        return _run_python_pipeline(workspace)
    else:
        return _run_mojo_pipeline(workspace)
```

### Step 5: Update run_llm_judge() Signature

**File**: `src/scylla/e2e/llm_judge.py`

Add `language` parameter:
```python
def run_llm_judge(
    workspace: Path,
    task_prompt: str,
    agent_output: str,
    language: str = "mojo",  # NEW
    ...
) -> JudgeResult:
```

### Step 6: Update BuildPipelineResult.to_context_string()

**File**: `src/scylla/e2e/llm_judge.py`

Make output language-aware:
```python
def to_context_string(self) -> str:
    if self.language == "python":
        # Format Python output (ruff, pytest)
    else:
        # Format Mojo output (mojo build, mojo format, mojo test)
```

### Step 7: Pass Language Through Call Chain

**Files to modify**:
- `src/scylla/e2e/subtest_executor.py` - Read language from test config
- `src/scylla/e2e/models.py` - Add language field to TestConfig if needed
- `src/scylla/config/loader.py` - Load language field from test.yaml

### Step 8: Update All Test Fixtures

For each test in `tests/fixtures/tests/test-XXX/test.yaml`:
- Add `language: mojo` for Mojo tests (most)
- Keep `language: python` for test-001

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `src/scylla/e2e/llm_judge.py` | Add Python pipeline, language routing |
| `tests/fixtures/tests/test-001/test.yaml` | Add `language: python` |
| `src/scylla/e2e/subtest_executor.py` | Pass language to judge |
| `src/scylla/config/loader.py` | Load language field |

---

## Verification

1. **Unit Tests**: Run existing tests to ensure no regressions
   ```bash
   pixi run pytest tests/unit/judge/ -v
   ```

2. **Integration Test**: Run test-001 with new Python pipeline
   ```bash
   python scripts/run_e2e_experiment.py \
     --tiers-dir tests/fixtures/tests/test-001 \
     --tiers T0 \
     --subtests 01-empty \
     --runs 1
   ```

3. **Verify Pipeline Output**: Check judge logs show Python commands instead of Mojo
   ```bash
   cat results/*/T0/01-empty/run_01/judge_01/prompt.md | grep -A5 "Build Pipeline"
   ```

4. **Run Pre-commit**: Ensure all formatting passes
   ```bash
   pre-commit run --all-files
   ```
