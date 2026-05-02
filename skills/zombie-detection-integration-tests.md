---
name: zombie-detection-integration-tests
description: "Integration test patterns for zombie experiment detection and reset\
  \ in ProjectScylla \u2014 validates the full path from dead PID + stale heartbeat\
  \ through ResumeManager.handle_zombie() to checkpoint.status='interrupted' with\
  \ real disk I/O."
category: testing
date: '2026-03-19'
version: 1.0.0
---
# Skill: Integration Tests for Zombie Detection + Resume Flow

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Add integration test exercising the full zombie detection path: dead PID + stale heartbeat → `reset_zombie_checkpoint()` → `checkpoint.status='interrupted'` |
| Outcome | Success — 11/11 tests pass, full suite 3595 passed, 67.46% coverage |
| Issue | HomericIntelligence/ProjectScylla#1224 |
| PR | HomericIntelligence/ProjectScylla#1312 |

## When to Use

Use this skill when:
- Writing integration tests for zombie detection or health monitoring paths
- Testing `ResumeManager.handle_zombie()` or `reset_zombie_checkpoint()` with real disk I/O
- Validating that checkpoint state (run/subtest/tier) is preserved during a zombie reset
- Testing the no-op case (`experiment_dir=None` or non-running status)
- Need to test dead-PID scenarios without mocking `os.kill`

## Key Architectural Insight: Zombie Detection Three-Condition Check

`is_zombie()` in `scylla/e2e/health.py` requires **all three** conditions to be true:

1. `checkpoint.status == "running"`
2. The PID referenced in `checkpoint.pid` (or `experiment.pid` file) is dead
3. `checkpoint.last_heartbeat` is stale (older than `heartbeat_timeout_seconds`, default 120s)

If any condition fails, the checkpoint is **not** treated as a zombie. This means:
- A fresh heartbeat bypasses zombie detection even for dead PIDs (process restarted, heartbeat was written recently)
- A non-running status (`interrupted`, `completed`, `failed`) is never a zombie

## Verified Workflow

### Dead PID Technique — No Mocking Required

Use a guaranteed-dead PID value to avoid mocking `os.kill`:

```python
# Linux's max PID is 4,194,304. A value well above this is always dead.
_DEAD_PID = 999_999_999

cp = make_checkpoint(
    status="running",
    pid=_DEAD_PID,
    last_heartbeat=_stale_heartbeat(),
    experiment_dir=str(tmp_path),
)
```

This is cleaner than `@patch("os.kill", side_effect=OSError)` and works on any Linux system.

### Timestamp Helpers

```python
from datetime import datetime, timedelta, timezone

_STALE_HEARTBEAT_AGE = 300   # well past 120s default
_FRESH_HEARTBEAT_AGE = 10    # well within 120s default

def _stale_heartbeat() -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=_STALE_HEARTBEAT_AGE)).isoformat()

def _fresh_heartbeat() -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=_FRESH_HEARTBEAT_AGE)).isoformat()
```

### Integration Test Pattern (Real Disk I/O)

Unlike unit tests that mock file operations, integration tests use `tmp_path` and real
`save_checkpoint` / `load_checkpoint` calls to validate the full round-trip:

```python
from scylla.e2e.checkpoint import E2ECheckpoint, load_checkpoint, save_checkpoint
from scylla.e2e.resume_manager import ResumeManager

def test_status_is_interrupted_after_handle_zombie(self, tmp_path: Path) -> None:
    cp = make_checkpoint(
        status="running",
        pid=_DEAD_PID,
        last_heartbeat=_stale_heartbeat(),
        experiment_dir=str(tmp_path),
    )
    cp_path = tmp_path / "checkpoint.json"
    save_checkpoint(cp, cp_path)           # Write initial checkpoint

    rm = _make_resume_manager(cp)
    _, updated_cp = rm.handle_zombie(
        checkpoint_path=cp_path,
        experiment_dir=tmp_path,
        heartbeat_timeout_seconds=120,
    )

    assert updated_cp.status == "interrupted"           # In-memory check
    on_disk = load_checkpoint(cp_path)
    assert on_disk.status == "interrupted"              # Disk persistence check
```

### Minimal ResumeManager Construction

`ResumeManager` requires `config` and `tier_manager` collaborators. For tests that only
exercise `handle_zombie()`, mock them with `MagicMock(spec=...)`:

```python
from unittest.mock import MagicMock
from scylla.e2e.models import ExperimentConfig
from scylla.e2e.resume_manager import ResumeManager

def _make_resume_manager(checkpoint: E2ECheckpoint) -> ResumeManager:
    config = MagicMock(spec=ExperimentConfig)
    tier_manager = MagicMock()
    return ResumeManager(checkpoint, config, tier_manager)
```

### Disk-Not-Modified Check

To verify a no-op path (fresh heartbeat, `experiment_dir=None`) doesn't write to disk,
use `st_mtime` before and after:

```python
original_mtime = cp_path.stat().st_mtime
rm.handle_zombie(checkpoint_path=cp_path, experiment_dir=tmp_path)
assert cp_path.stat().st_mtime == original_mtime
```

For the `experiment_dir=None` case, assert the checkpoint file was never created:

```python
# Do NOT write checkpoint to disk first
cp_path = tmp_path / "checkpoint.json"
rm.handle_zombie(checkpoint_path=cp_path, experiment_dir=None)
assert not cp_path.exists()
```

### Test Class Organization

Organize tests into 4 logical classes covering all code paths:

```python
class TestZombieResetsStatusToInterrupted:    # Core zombie → interrupted
class TestZombieResetPreservesStateData:      # State data survives reset
class TestNonZombieCheckpointUnchanged:       # Not a zombie → no change
class TestExperimentDirNoneIsNoop:            # Guard against None dir
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test counts (11 total)

| Class | Count |
| ------- | ------- |
| `TestZombieResetsStatusToInterrupted` | 2 |
| `TestZombieResetPreservesStateData` | 4 |
| `TestNonZombieCheckpointUnchanged` | 3 |
| `TestExperimentDirNoneIsNoop` | 2 |

### Coverage behavior

Running only integration tests hits ~8.27% combined coverage (below the 9% floor).
Always run with `--override-ini="addopts="` to suppress the coverage floor when
running integration tests in isolation:

```bash
pixi run python -m pytest tests/integration/ -v --override-ini="addopts="
```

The 9% floor is only meaningful when the full test suite runs together.

### Key constants

```python
_DEAD_PID = 999_999_999          # Guaranteed dead on Linux (max is 4,194,304)
_STALE_HEARTBEAT_AGE = 300       # 5 minutes — well past 120s default timeout
_FRESH_HEARTBEAT_AGE = 10        # 10 seconds — well within 120s default timeout
```

### pytestmark

```python
pytestmark = pytest.mark.integration
# Run with: pixi run python -m pytest tests/integration/ -v --override-ini="addopts="
```

### Zombie detection source

- `scylla/e2e/health.py` — `is_zombie()`, `reset_zombie_checkpoint()`, `DEFAULT_HEARTBEAT_TIMEOUT_SECONDS`
- `scylla/e2e/resume_manager.py` — `ResumeManager.handle_zombie()`
- `tests/integration/e2e/test_zombie_resume.py` — the integration test file
