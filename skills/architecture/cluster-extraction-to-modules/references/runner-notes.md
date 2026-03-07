# Implementation Notes: runner.py Class-Based Cluster Extraction

## Session Context

- **Date**: 2026-03-07
- **Project**: ProjectScylla
- **Issue**: #1445 — Decompose runner.py (1,220 lines) — cross-file deps resolved
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1468
- **Branch**: `1445-auto-impl`

## Target File

`scylla/e2e/runner.py` — 1,230 lines before, 999 lines after

The file contained `E2ERunner`, a class orchestrating the complete E2E experiment lifecycle.
It mixed several concerns, with two extractable clusters identified:

## Cluster Analysis

### Cluster 1: Filesystem Setup → ExperimentSetupManager (~200 lines saved)

**Methods extracted**: `_create_experiment_dir`, `_copy_grading_materials`, `_save_config`,
`_capture_experiment_baseline`, `_write_pid_file`, `_cleanup_pid_file`

**New file**: `scylla/e2e/experiment_setup_manager.py`

**Why class-based (not function-based)**:
- Methods share `self.config` and `self.results_base_dir` — these form a natural pairing
- `capture_baseline` also needs `workspace_manager` passed as parameter
- The methods form a coherent "setup" lifecycle

**Shared state mapping**:
- `self.config` → `self.config` (stored on collaborator)
- `self.results_base_dir` → `self.results_base_dir` (stored on collaborator)
- `self.workspace_manager` → passed as `workspace_manager: WorkspaceManager` parameter

**Factory method in E2ERunner**:
```python
def _setup_manager(self) -> ExperimentSetupManager:
    return ExperimentSetupManager(self.config, self.results_base_dir)
```

### Cluster 2: Checkpoint Lifecycle → CheckpointFinalizer (~90 lines saved)

**Methods extracted**: `_find_existing_checkpoint`, `_handle_experiment_interrupt`,
`_validate_filesystem_on_resume`, `_mark_checkpoint_completed`

**New file**: `scylla/e2e/checkpoint_finalizer.py`

**Why class-based**:
- Methods share `self.config` (for experiment_id) and `self.results_base_dir`
- The methods form a coherent "experiment boundaries" lifecycle

**Factory method in E2ERunner**:
```python
def _finalizer(self) -> CheckpointFinalizer:
    return CheckpointFinalizer(self.config, self.results_base_dir)
```

## Line Count Progression

| After step | Lines |
|-----------|-------|
| Original | 1,230 |
| After Cluster 1 extraction | 1,017 |
| After removing unused `_STATUS_INTERRUPTED/COMPLETED` constants | 1,015 |
| After inlining `_create_experiment_dir`/`_save_config`/`_copy_grading_materials` | 1,001 |
| After removing comment line | 1,000 |
| After adding back `_write_pid_file`/`_cleanup_pid_file` delegation shells | 1,001 |
| After removing one more comment | 999 ✅ |

## Failures and Fixes

### 1. `object` type for workspace_manager

**Problem**: Used `workspace_manager: object` to avoid importing `WorkspaceManager`.
**Error**: `mypy: "object" has no attribute "create_worktree"`
**Fix**: Added `TYPE_CHECKING` guard:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scylla.e2e.workspace_manager import WorkspaceManager
```
Then used `WorkspaceManager` as the type. Since `TYPE_CHECKING` is `False` at runtime, no circular import risk.

### 2. Removed `_write_pid_file` broke 9 existing tests

**Problem**: Inlined `_write_pid_file` call in `_initialize_or_resume_experiment` and removed the method.
**Error**: `AttributeError: <E2ERunner object> does not have the attribute '_write_pid_file'`
**Root cause**: Tests used `patch.object(runner, "_write_pid_file")` (9 occurrences in `test_runner.py`)
**Fix**: Restored `_write_pid_file` and `_cleanup_pid_file` as thin delegation shells. The 8-line cost
is worth backward compatibility. Both `_initialize_or_resume_experiment` and `run()` call these methods.

### 3. Logger patch path after extraction

**Problem**: `test_warns_when_experiment_dir_missing` in `test_runner.py` patched
`scylla.e2e.runner.logger` to capture filesystem validation warnings.
**Error**: After extraction, warnings are emitted from `scylla.e2e.checkpoint_finalizer.logger`
so the patch captured nothing; assertion failed.
**Fix**: Updated test to `patch("scylla.e2e.checkpoint_finalizer.logger")`.

### 4. `_create_fresh_experiment` inlining

**Approach**: Inlined `_create_experiment_dir` and `_save_config` calls directly in
`_create_fresh_experiment` using the setup manager:
```python
# Before
self.experiment_dir = self._create_experiment_dir()
self._save_config()

# After — direct calls through factory method
setup = self._setup_manager()
self.experiment_dir = setup.create_experiment_dir()
setup.save_config(self.experiment_dir)
```
Then removed the `_create_experiment_dir`, `_copy_grading_materials`, and `_save_config` delegation
shells (these were not mocked by any test). This saved ~12 lines.

## Pre-commit Issues Encountered

### Round 1: ruff auto-fixed 3 issues
- Import ordering

### Round 2: mypy errors (2 errors in experiment_setup_manager.py)
- `Unused "type: ignore" comment` on `create_worktree` call
- `"object" has no attribute "create_worktree"`
- Fix: Added `TYPE_CHECKING` guard; removed `# type: ignore[union-attr]` comments

### Round 3: All pass ✅

## New Tests Written

**test_experiment_setup_manager.py** (20 tests):
- `TestCreateExperimentDir`: directory creation, timestamp prefix, judge_prompt.md
- `TestCopyGradingMaterials`: prompt copy, criteria/rubric symlinks, missing files
- `TestSaveConfig`: delegates to `ExperimentConfig.save()`
- `TestCaptureBaseline`: idempotency, worktree create/cleanup, pipeline failure handling
- `TestPidFile`: write creates file with PID, cleanup removes file, noop when missing

**test_checkpoint_finalizer.py** (19 tests):
- `TestFindExistingCheckpoint`: missing dir, no match, no checkpoint, found, most recent
- `TestHandleExperimentInterrupt`: sets interrupted on disk, noop when missing, fallback to memory
- `TestValidateFilesystemOnResume`: no warning for non-TIERS_RUNNING, warns on missing dirs
- `TestMarkCheckpointCompleted`: sets completed, merges run/subtest/tier states, fallback on error

**Patch target pattern for lazy imports** (inside method body):
```python
# capture_baseline uses: from scylla.e2e.llm_judge import _run_build_pipeline
# Correct patch target:
patch("scylla.e2e.llm_judge._run_build_pipeline")
# NOT: patch("scylla.e2e.experiment_setup_manager._run_build_pipeline")
```

## Test Results

```
4,602 passed, 1 skipped (full unit + integration suite)
76.24% coverage (threshold: 75% unit, 9% combined)
All pre-commit hooks pass
```

## Commands Used

```bash
# Check line count at each step
wc -l scylla/e2e/runner.py

# Smoke tests
pixi run python -c "from scylla.e2e.runner import E2ERunner; print('OK')"
pixi run python -c "from scylla.e2e.experiment_setup_manager import ExperimentSetupManager; print('OK')"
pixi run python -c "from scylla.e2e.checkpoint_finalizer import CheckpointFinalizer; print('OK')"

# Run new tests only
pixi run python -m pytest tests/unit/e2e/test_experiment_setup_manager.py \
  tests/unit/e2e/test_checkpoint_finalizer.py -v --no-cov

# Pre-commit
pre-commit run --files \
  scylla/e2e/runner.py \
  scylla/e2e/experiment_setup_manager.py \
  scylla/e2e/checkpoint_finalizer.py \
  tests/unit/e2e/test_experiment_setup_manager.py \
  tests/unit/e2e/test_checkpoint_finalizer.py \
  tests/unit/e2e/test_runner.py

# Full test suite
pixi run python -m pytest tests/unit/ -q --tb=short
```
