# Session Notes: credential-mount-context-manager

## Verified Examples

### Example 1: ProjectScylla

**Date**: 2026-02-22
**Context**: PR #1010 — 498 `.scylla-temp-creds-*` directories leaked in `~/`

**Root Cause Investigation**:

Both `agent_container.py` and `judge_container.py` followed this pattern:
1. `_build_volumes()` created `~/.scylla-temp-creds-{uuid}` and returned path via `"temp_cleanup"` sentinel
2. `_run_with_volumes()` collected the sentinel and cleaned up in `finally` block
3. Cleanup used bare `except Exception: pass` — silent failure on WSL2

The gap between `_build_volumes()` (line 281) and the `try` in `run_judge()` (line 287) also
meant any exception in that 6-line window leaked the temp dir with no cleanup.

**Files Modified**:

| File | Action |
| ------ | -------- |
| `scylla/executor/credential_mount.py` | Created — context manager + retry + stale cleanup |
| `scylla/executor/agent_container.py` | Modified — `run()` uses context manager |
| `scylla/executor/judge_container.py` | Modified — `run_judge()` uses context manager |
| `scylla/executor/__init__.py` | Modified — export new symbols |
| `tests/unit/executor/test_credential_mount.py` | Created — 6 tests |

**Specific Commands Used**:

```bash
# Verify all tests pass
pixi run python -m pytest tests/unit/executor/ -v

# Run full suite for coverage check (must hit 73%)
pixi run python -m pytest tests/ -v --tb=short -q

# Pre-commit validation
pre-commit run --all-files

# One-time cleanup of existing leaked dirs
pixi run python -c "
from scylla.executor.credential_mount import cleanup_stale_credential_dirs
count = cleanup_stale_credential_dirs()
print(f'Cleaned up {count} stale credential directories')
"
```

**Output from recovery**:
```
Cleaned up 498 stale credential directories
```

**Test Results**:
- 6 new tests: all passed
- 2454 total tests: all passed
- Coverage: 74.28% (above 73% threshold)
- Pre-commit: all hooks passed

**Links**:
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/1010
- Commit: 931d0b6c

---

## Raw Findings

### WSL2 Docker Mount Race — Technical Detail

On WSL2, when a container exits with `--rm`, Docker removes the container filesystem but kernel
mount namespaces may retain references to host-mounted directories for 200–800ms. During this
window, `shutil.rmtree()` on the mounted host dir fails with `OSError: [Errno 16] Device or
resource busy`. The failure was silent because the code used `except Exception: pass`.

The retry pattern (3× with 0.5s delay) covers the typical release window without adding
meaningful latency to the happy path.

### Test Isolation Pattern for `Path.home()`

Since `temporary_credential_mount()` calls `Path.home()` internally, tests need to patch it:

```python
@pytest.fixture()
def fake_home(tmp_path: Path) -> Path:
    return tmp_path

@pytest.fixture()
def home_with_credentials(fake_home: Path) -> Path:
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir()
    creds = claude_dir / ".credentials.json"
    creds.write_text('{"token": "fake-token"}')
    return fake_home

def test_...(home_with_credentials):
    with patch("scylla.executor.credential_mount.Path.home", return_value=home_with_credentials):
        with temporary_credential_mount() as creds_dir:
            ...
```

### `_run_with_volumes()` Simplification

After removing the `finally` cleanup block from `_run_with_volumes()`, the `import shutil` at the
top of the function became unused and was removed. Pre-commit (ruff) auto-fixed the unused import.

### Why `ContainerError` Re-raise Was Added

In `judge_container.py`'s `run_judge()`, the original code caught all exceptions and wrapped
them in `ContainerError`. After restructuring to use the context manager, a bare `except Exception`
would also catch `ContainerError` raised by `_run_with_volumes()` and double-wrap it. Added
`except ContainerError: raise` before the generic handler to preserve the original exception type.

## External References

- Python contextlib: https://docs.python.org/3/library/contextlib.html
- WSL2 Docker mount docs: https://docs.docker.com/desktop/wsl/
- Related skill: `debugging/pydantic-none-coercion-pattern` (same silent-failure anti-pattern with `except Exception: pass`)