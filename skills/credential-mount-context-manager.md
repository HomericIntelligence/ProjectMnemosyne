---
name: credential-mount-context-manager
description: 'TRIGGER CONDITIONS: Temp credential dirs leaking in home after Docker
  runs; silent rmtree failures in finally blocks on WSL2; need to safely mount host
  credentials into Docker containers with guaranteed cleanup.'
category: architecture
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# credential-mount-context-manager

Extract Docker credential temp-dir lifecycle into a context manager with retry
cleanup to fix silent resource leaks caused by Docker mount-release race conditions on WSL2.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-22 |
| Objective | Fix `.scylla-temp-creds-*` directory leak — 498 credential copies accumulating in `~/` |
| Outcome | ✅ Success — 0 leaked dirs after fix; 498 existing dirs cleaned up via recovery utility |

## When to Use

- Directories like `~/.app-temp-creds-<uuid>` or `~/.app-temp-<uuid>` accumulate in home after container runs
- `shutil.rmtree()` in a `finally` block silently fails (bare `except Exception: pass`) for temp dirs used as Docker volumes
- On WSL2, Docker may hold mount references briefly after container exit, causing `rmtree()` to race
- A temp credential/config dir is created before `_run_with_volumes()` but the gap between creation and the `finally` block is not covered by `try`
- Multiple container managers duplicate the same temp-dir creation + cleanup pattern

## Verified Workflow

### Phase 1: Identify the Leak Pattern

Look for this anti-pattern:

```python
# ANTI-PATTERN: temp dir created in _build_volumes(), cleaned in _run_with_volumes() finally
def _build_volumes(self, config):
    temp_dir = Path.home() / f".app-temp-creds-{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir()
    volumes[str(temp_dir)] = {
        "bind": "/mnt/creds",
        "mode": "ro",
        "temp_cleanup": str(temp_dir),   # sentinel — fragile
    }
    return volumes

def _run_with_volumes(self, config, volumes):
    temp_dirs = [v["temp_cleanup"] for v in volumes.values() if "temp_cleanup" in v]
    try:
        ...
    finally:
        for d in temp_dirs:
            try:
                shutil.rmtree(d)
            except Exception:
                pass  # SILENT FAILURE — leak source
```

**Why it leaks on WSL2**: Docker's `--rm` flag removes the container but kernel mount references
may linger a few hundred ms. `rmtree()` races against that release and loses, silently.

**Second leak source**: If an exception occurs between `_build_volumes()` (line N) and the `try`
in `_run_with_volumes()` (line N+7), the temp dir is created but never covered by any `finally`.

### Phase 2: Create `credential_mount.py` Module

```python
# <project-root>/<package>/executor/credential_mount.py
import contextlib
import logging
import shutil
import time
import uuid
from collections.abc import Generator
from pathlib import Path

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def temporary_credential_mount() -> Generator[Path | None, None, None]:
    """Context manager for temporary credential directory lifecycle.

    Creates a temp dir with credentials, yields its path for volume mounting,
    and ensures cleanup with retry logic to handle Docker mount release delays.

    Yields:
        Path to the temporary credential directory, or None if no credentials
        file exists at ~/.claude/.credentials.json.
    """
    credentials_path = Path.home() / ".claude" / ".credentials.json"
    if not credentials_path.exists():
        yield None
        return

    temp_dir = Path.home() / f".scylla-temp-creds-{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(exist_ok=True)
    temp_dir.chmod(0o755)

    temp_creds = temp_dir / ".credentials.json"
    temp_creds.write_text(credentials_path.read_text())
    temp_creds.chmod(0o644)

    try:
        yield temp_dir
    finally:
        _cleanup_temp_dir(temp_dir)


def _cleanup_temp_dir(temp_dir: Path, retries: int = 3, delay: float = 0.5) -> None:
    """Clean up temp dir with retry for Docker mount release race."""
    for attempt in range(retries):
        try:
            shutil.rmtree(temp_dir)
            return
        except OSError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.warning(
                    "Failed to clean up temp credentials dir after %d attempts: %s",
                    retries,
                    temp_dir,
                )


def cleanup_stale_credential_dirs() -> int:
    """Remove any leftover temp cred dirs from home. Returns count removed."""
    count = 0
    for path in Path.home().glob(".scylla-temp-creds-*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            count += 1
    return count
```

Adapt the glob pattern to match your project's temp dir naming convention.

### Phase 3: Update Container Managers

**Before** (each manager creates + cleans up its own temp dir):

```python
def run(self, config):
    volumes = self._build_volumes(config)   # creates temp dir internally
    return self._run_with_volumes(config, volumes)  # cleans up in finally
```

**After** (context manager owns the lifecycle):

```python
def run(self, config):
    with temporary_credential_mount() as creds_dir:
        volumes = self._build_volumes(config, creds_dir=creds_dir)
        return self._run_with_volumes(config, volumes)
        # context manager cleans up temp dir here — inside the with block
```

Update `_build_volumes()` signature:

```python
def _build_volumes(self, config, creds_dir: Path | None = None):
    volumes = { ... }  # existing mounts
    if creds_dir is not None:
        volumes[str(creds_dir)] = {"bind": "/mnt/claude-creds", "mode": "ro"}
    return volumes
```

Remove from `_run_with_volumes()`:
- The `temp_dirs` collection loop
- The `finally` cleanup block
- The `"temp_cleanup"` sentinel dict key

### Phase 4: Add Tests

```python
# tests/unit/<module>/test_credential_mount.py

def test_temporary_credential_mount_creates_and_cleans_up(home_with_credentials):
    with patch("...Path.home", return_value=home_with_credentials):
        with temporary_credential_mount() as creds_dir:
            assert creds_dir is not None
            assert creds_dir.exists()
        assert not creds_dir.exists()   # cleaned up

def test_temporary_credential_mount_no_credentials(fake_home):
    with patch("...Path.home", return_value=fake_home):
        with temporary_credential_mount() as creds_dir:
            assert creds_dir is None

def test_cleanup_retries_on_failure(tmp_path):
    # mock rmtree to fail twice then succeed
    ...

def test_cleanup_logs_warning_on_final_failure(tmp_path):
    # mock rmtree to always fail, verify logger.warning called
    ...

def test_cleanup_stale_credential_dirs(fake_home):
    # create 2 stale dirs + 1 unrelated, verify count=2 and correct dirs removed
    ...

def test_context_manager_cleans_up_on_exception(home_with_credentials):
    # verify temp dir removed even when exception raised inside with block
    ...
```

### Phase 5: Recovery Cleanup (One-Time)

```python
from <package>.executor.credential_mount import cleanup_stale_credential_dirs
count = cleanup_stale_credential_dirs()
print(f"Cleaned up {count} stale credential directories")
```

Or via shell:

```bash
rm -rf ~/.scylla-temp-creds-*  # adapt glob to your naming convention
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Add `time.sleep(1)` before `shutil.rmtree()` in `finally` | Adds latency to every run even when cleanup succeeds; doesn't fix the race for long mounts | Use retry loop with sleep only on failure |
| Catch `Exception` broadly and log | Catches non-OSError failures that shouldn't be silenced (e.g., PermissionError on bad paths) | Catch `OSError` specifically |
| Use `/tmp` instead of `~` for temp dirs | WSL2 doesn't expose `/tmp` contents to Docker by default without explicit bind | Use home dir or a known Docker-accessible path |
| Pass `temp_cleanup` sentinel in volume dict and collect in `_run_with_volumes()` | Dict leak between creation and try; sentinel is fragile and couples volume config to cleanup logic | Decouple lifecycle via context manager |
| Move cleanup to `__del__` on container manager | Not guaranteed to run; GC timing unpredictable | Use explicit context manager with `finally` |

## Results & Parameters

### Retry Parameters (Tuned for WSL2 Docker)

```python
retries: int = 3      # 3 attempts covers typical mount release window
delay: float = 0.5    # 0.5s between attempts = max 1s extra latency on failure
```

### File Permissions for Container Access

```python
temp_dir.chmod(0o755)           # directory: world-readable+executable
temp_creds.chmod(0o644)         # file: world-readable
```

These permissions allow the container user (often a non-root UID) to read the credentials.

### Pattern for Multiple Managers

When multiple container managers (e.g., `agent_container.py`, `judge_container.py`) share the same
credential mounting need, extract to a single shared module — don't copy-paste into each manager.
One module → one context manager → imported by all managers.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1010 — Fixed 498 leaked `.scylla-temp-creds-*` dirs | [notes.md](../references/notes.md) |

## References

- Python `contextlib.contextmanager` docs: https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager
- Related skills: `debugging/pydantic-none-coercion-pattern` (similar silent-failure pattern)
