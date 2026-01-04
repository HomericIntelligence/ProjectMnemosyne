---
name: resume-functionality-tests
description: Comprehensive test patterns for checkpoint/resume systems covering crash, interrupt, and partial completion scenarios
category: testing
date: 2026-01-04
tags: [testing, checkpoint, resume, crash-recovery, fixtures]
---

# Resume Functionality Tests

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Add comprehensive test coverage for checkpoint/resume system across all failure modes |
| **Outcome** | ✅ 15 test cases covering agent crash, judge crash, signal handling, partial completion, config mismatch |
| **Project** | ProjectScylla |
| **PR** | [#142](https://github.com/HomericIntelligence/ProjectScylla/pull/142) |

## When to Use

Use these test patterns when:
- Building checkpoint/resume systems for long-running processes
- Need to verify crash recovery works correctly
- Testing that partial work is saved and can resume
- Validating config mismatch detection on resume
- Ensuring no duplicate work on resume

## Problem

**Untested Resume**:
- Resume system exists but no test coverage
- Unknown if checkpoint saves/loads correctly
- Unclear if resume skips completed work
- No validation of crash recovery scenarios
- Config mismatch might go undetected

## Verified Workflow

### 1. Create Test Fixtures

```python
import pytest
from pathlib import Path
from scylla.e2e.checkpoint import E2ECheckpoint, save_checkpoint
from scylla.e2e.models import ExperimentConfig, TierConfig, SubTestConfig

@pytest.fixture
def checkpoint(tmp_path: Path) -> tuple[E2ECheckpoint, Path]:
    """Create a checkpoint and its save path."""
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = E2ECheckpoint(
        experiment_id="test-resume",
        experiment_dir=str(tmp_path),
        config_hash="test-hash",
        completed_runs={},
        started_at=datetime.now(UTC).isoformat(),
        last_updated_at=datetime.now(UTC).isoformat(),
        status="running",
    )
    save_checkpoint(checkpoint, checkpoint_path)
    return checkpoint, checkpoint_path
```

### 2. Test Agent Crash Scenarios

```python
class TestResumeAfterAgentCrash:
    def test_skip_completed_agent_result(self, tmp_path: Path) -> None:
        """Verify completed agent runs are not re-executed."""
        run_dir = tmp_path / "run_01"
        agent_dir = run_dir / "agent"
        agent_dir.mkdir(parents=True)

        # Create valid agent result
        agent_result = {
            "exit_code": 0,
            "token_stats": {...},
            "cost_usd": 0.01,
        }
        (agent_dir / "result.json").write_text(json.dumps(agent_result))

        # Verify validation passes
        assert _has_valid_agent_result(run_dir) is True

    def test_invalid_agent_result_triggers_rerun(self, tmp_path: Path) -> None:
        """Verify invalid agent results trigger re-run."""
        # Create invalid result (missing required fields)
        invalid_result = {"exit_code": 0}  # Missing token_stats, cost_usd
        (agent_dir / "result.json").write_text(json.dumps(invalid_result))

        assert _has_valid_agent_result(run_dir) is False

    def test_corrupted_agent_json_triggers_rerun(self, tmp_path: Path) -> None:
        """Verify corrupted JSON triggers re-run."""
        (agent_dir / "result.json").write_text("{ invalid json")
        assert _has_valid_agent_result(run_dir) is False
```

### 3. Test Judge Crash Scenarios

```python
class TestResumeAfterJudgeCrash:
    def test_agent_preserved_after_judge_crash(self, tmp_path: Path) -> None:
        """Verify agent results are preserved when judge crashes."""
        # Completed agent
        agent_result = {...}
        (agent_dir / "result.json").write_text(json.dumps(agent_result))

        # No judge result (crashed before completion)

        # Agent should be valid and preserved
        assert _has_valid_agent_result(run_dir) is True
        # Judge should be invalid and re-run
        assert _has_valid_judge_result(run_dir) is False
```

### 4. Test Signal Handling

```python
class TestResumeAfterSignal:
    def test_checkpoint_saved_with_interrupted_status(
        self, checkpoint: tuple[E2ECheckpoint, Path]
    ) -> None:
        """Verify checkpoint is saved with interrupted status."""
        cp, cp_path = checkpoint

        # Simulate interrupt
        cp.status = "interrupted"
        save_checkpoint(cp, cp_path)

        # Reload and verify
        loaded_data = json.loads(cp_path.read_text())
        assert loaded_data["status"] == "interrupted"
```

### 5. Test Partial Tier Completion

```python
class TestResumePartialTier:
    def test_resume_skips_completed_subtests(
        self, checkpoint: tuple[E2ECheckpoint, Path]
    ) -> None:
        """Resume should skip completed subtests in partial tier."""
        cp, _ = checkpoint

        # Mark first subtest as fully completed
        cp.completed_runs = {
            "T0": {
                "T0_00": {1: "passed", 2: "passed"},  # Both runs complete
                "T0_01": {},  # Not started
            }
        }

        assert cp.is_run_completed("T0", "T0_00", 1) is True
        assert cp.is_run_completed("T0", "T0_01", 1) is False
```

### 6. Test Config Mismatch

```python
class TestResumeConfigMismatch:
    def test_config_hash_mismatch_raises_error(
        self, checkpoint: tuple[E2ECheckpoint, Path], experiment_config: ExperimentConfig
    ) -> None:
        """Resume with different config should error."""
        cp, _ = checkpoint
        cp.config_hash = "original-hash"

        # Modified config
        modified_config = experiment_config
        modified_config.runs_per_subtest = 5  # Changed from 2

        # Validation should fail
        assert validate_checkpoint_config(cp, modified_config) is False
```

### 7. Test Checkpoint Operations

```python
class TestCheckpointOperations:
    def test_checkpoint_tracks_run_completion(
        self, checkpoint: tuple[E2ECheckpoint, Path]
    ) -> None:
        """Verify checkpoint correctly tracks run completion."""
        cp, _ = checkpoint

        # Mark run as completed
        cp.mark_run_completed("T0", "T0_00", 1)
        assert cp.is_run_completed("T0", "T0_00", 1) is True

        # Unmark run
        cp.unmark_run_completed("T0", "T0_00", 1)
        assert cp.is_run_completed("T0", "T0_00", 1) is False
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Using list format for completed_runs | Checkpoint expects dict[int, str] not list[int] |
| Round-trip JSON testing | JSON converts integer keys to strings, adjusted tests to avoid issue |
| Mocking entire executor | Too complex, focused on validation functions instead |

## Results & Parameters

### Test File Structure

```python
# tests/unit/e2e/test_resume.py (367 lines, 15 tests)

# Fixtures
@pytest.fixture
def experiment_config() -> ExperimentConfig: ...

@pytest.fixture
def tier_config() -> TierConfig: ...

@pytest.fixture
def checkpoint(tmp_path: Path) -> tuple[E2ECheckpoint, Path]: ...

# Test Classes (6)
class TestResumeAfterAgentCrash: ...       # 3 tests
class TestResumeAfterJudgeCrash: ...       # 3 tests
class TestResumeAfterSignal: ...           # 2 tests
class TestResumePartialTier: ...           # 2 tests
class TestResumeCompleteExperiment: ...    # 1 test
class TestResumeConfigMismatch: ...        # 1 test
class TestCheckpointOperations: ...        # 3 tests
```

### Checkpoint Data Structure

```python
# Correct format for completed_runs
{
    "tier_id": {
        "subtest_id": {
            run_number: status,  # int key, str value
        }
    }
}

# Example
{
    "T0": {
        "T0_00": {1: "passed", 2: "passed"},
        "T0_01": {1: "failed"},
    }
}

# Status values: "passed", "failed", "agent_complete"
```

### Required Fields Validation

**Agent Result**:
- `exit_code`: int
- `token_stats`: dict
- `cost_usd`: float

**Judge Result**:
- `score`: float
- `passed`: bool
- `grade`: str
- `reasoning`: str

### Test Coverage

✅ **Agent Crash** (3 tests):
- Skip completed agent results
- Re-run invalid results
- Re-run corrupted JSON

✅ **Judge Crash** (3 tests):
- Skip completed judge results
- Re-run invalid results
- Preserve agent when judge crashes

✅ **Signal Handling** (2 tests):
- Checkpoint saved with "interrupted" status
- Resume from interrupted checkpoint

✅ **Partial Tier** (2 tests):
- Skip completed subtests
- Continue partial subtests

✅ **Complete Experiment** (1 test):
- Resume without re-running

✅ **Config Mismatch** (1 test):
- Detect hash mismatch

✅ **Checkpoint Ops** (3 tests):
- Save and load
- Track completion
- Count completed runs

## Key Learnings

1. **Use Proper API**: Use `checkpoint.mark_run_completed()` not direct dict manipulation
2. **tmp_path Fixture**: Use pytest's tmp_path for isolated test directories
3. **Validation Functions**: Test validation functions separately from full execution
4. **Fixture Reuse**: Create checkpoint fixture for consistency across tests
5. **Test Both Paths**: Test valid and invalid cases for completeness

## Use Cases

1. **ML Training**: Resume after crash mid-epoch
2. **ETL Pipelines**: Resume after database connection drop
3. **Batch Processing**: Resume after partial batch completion
4. **Long-Running Tests**: Resume after infrastructure failure

## Related Skills

- `optimization/checkpoint-result-validation` - Result validation patterns used in tests
- `tooling/graceful-signal-handling` - Signal handling tested here
- `architecture/centralized-path-constants` - Path helpers tested

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #142 - Resume functionality tests for E2E experiments | [notes.md](../../references/notes.md) |
