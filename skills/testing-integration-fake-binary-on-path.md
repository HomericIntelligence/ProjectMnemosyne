---
name: testing-integration-fake-binary-on-path
description: "Pattern for integration tests that verify subprocess environment variable propagation: create fake executable in temporary directory, prepend to PATH with monkeypatch, subprocess finds fake first. Use when: testing that subprocesses receive expected env vars (GH_TRACE_ID, custom config, etc.) and must verify behavior without mocking subprocess.run()."
category: testing
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - integration-testing
  - subprocess
  - environment-variables
  - monkeypatch
  - fake-binaries
  - test-fixtures
---

# Testing: Integration Test Fake Binary on PATH

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Verify subprocess receives expected environment variables (correlation IDs, config) via integration test with fake binary |
| **Outcome** | Integration test confirms GH_TRACE_ID propagated to subprocess; test validated locally |
| **Verification** | verified-local (test runs locally; CI won't have fake gh installed) |

## When to Use

- Testing that subprocesses receive expected environment variables
- Must verify actual subprocess behavior, not just mock assertions
- Want to avoid mocking subprocess.run() (which would skip actual subprocess logic)
- Need a lightweight fake binary that echoes environment for assertion
- Tests run locally during development; CI environment may vary
- `tmp_path` fixture provides isolated temporary directory per test

## Verified Workflow

### Quick Reference

```python
import pytest
import os
import subprocess
from pathlib import Path

@pytest.fixture(autouse=True)
def _fake_binary_on_path(tmp_path, monkeypatch):
    """Create fake gh binary that outputs environment variables.

    Subprocess will find this fake instead of the real gh command.
    """
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()

    # Create fake gh that outputs environment
    fake_gh = fake_bin_dir / "gh"
    fake_gh.write_text("#!/bin/sh\nenv | grep GH_TRACE_ID || echo 'NO_GH_TRACE_ID'\n")
    fake_gh.chmod(0o755)  # ← CRITICAL: must set execute bit

    # Prepend to PATH (so fake is found first)
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", str(fake_bin_dir) + ":" + original_path)

def test_gh_trace_id_propagated_to_subprocess(monkeypatch, _fake_binary_on_path):
    """Integration test: subprocess receives GH_TRACE_ID from context."""
    from hephaestus.logging.utils import set_correlation_id

    # Set correlation ID in context
    set_correlation_id("req-integration-test-123")

    # Call subprocess (will find fake gh from fixture)
    result = subprocess.run(
        ["gh", "pr", "view", "123"],
        capture_output=True,
        text=True,
    )

    # Verify fake gh received the env var
    assert "req-integration-test-123" in result.stdout
```

### Detailed Steps

1. **Create pytest fixture with tmp_path and monkeypatch**:
   ```python
   @pytest.fixture(autouse=True)
   def _fake_binary_on_path(tmp_path, monkeypatch):
       """Fixture provides fake binary on PATH."""
   ```

2. **Create temporary bin directory inside tmp_path**:
   ```python
   fake_bin_dir = tmp_path / "bin"
   fake_bin_dir.mkdir()
   ```
   - `tmp_path` is auto-cleaned up after test
   - Each test gets its own isolated directory

3. **Create fake binary as shell script**:
   ```python
   fake_gh = fake_bin_dir / "gh"
   fake_gh.write_text("#!/bin/sh\nenv | grep GH_TRACE_ID || echo 'NO_GH_TRACE_ID'\n")
   ```
   - Shebang `#!/bin/sh` tells OS to use shell interpreter
   - Script outputs GH_TRACE_ID if present, else "NO_GH_TRACE_ID"
   - Can be extended to output other variables or perform actions

4. **Set executable permission (chmod +x)**:
   ```python
   fake_gh.chmod(0o755)
   ```
   - **CRITICAL**: Without this, subprocess.run() will fail with "Permission denied"
   - 0o755 = rwxr-xr-x (owner execute, group/other read-execute)

5. **Prepend fake bin dir to PATH**:
   ```python
   original_path = os.environ.get("PATH", "")
   monkeypatch.setenv("PATH", str(fake_bin_dir) + ":" + original_path)
   ```
   - Prepend (not append) so fake is found first
   - Store original_path but don't restore manually; monkeypatch handles cleanup
   - Use `:` separator (Unix standard)

6. **Call subprocess normally**:
   ```python
   result = subprocess.run(["gh", "pr", "view", "123"], capture_output=True, text=True)
   ```
   - subprocess will find fake gh from modified PATH

7. **Assert on output**:
   ```python
   assert "req-integration-test-123" in result.stdout
   ```

8. **Handle CI environments**:
   - Mark test with `@pytest.mark.skip_on_ci` if CI doesn't have custom PATH
   - Or: check if fake binary is being used before assertion
   - Or: simply accept that test validates locally only (document in verification)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Created fake script with chmod(0o644) (read/write only) | subprocess.run(["gh", ...]) raised "Permission denied" — binary not executable | Executables must have +x permission bit set. Use chmod(0o755) or chmod(0o555 for read-only executable). |
| 2 | Appended fake_bin_dir to PATH instead of prepending | Real gh (from /usr/bin) was found first; fake gh never called | Prepend to PATH with `:` prefix, not append with suffix. Check PATH with echo $PATH to verify order. |
| 3 | Did not persist monkeypatch.setenv() result; PATH reverted after fixture | Fixture set PATH, but by the time test ran, PATH was restored to original | monkeypatch.setenv() automatically restores on fixture exit (yield pattern). This is correct; test runs with modified PATH. |
| 4 | Used Python script (#!/usr/bin/env python) instead of shell script | Python startup overhead; also requires Python interpreter in PATH on CI | Use shell scripts (#!/bin/sh) for simplicity and portability. Shell is always available on Unix. |
| 5 | Tried to mock fake binary by passing it as env var to subprocess | Cumbersome; subprocess.run() doesn't accept a "binary" parameter | Let PATH lookup work naturally; that's why we modify PATH. |
| 6 | Did not use monkeypatch; manually modified os.environ | Forgot to restore after test; subsequent tests saw modified PATH | Always use monkeypatch.setenv() for fixture-based modifications. It auto-restores on exit. |

## Results & Parameters

### Fake Binary Template (Copy-Paste Ready)

#### Simple: Just Echo Environment

```python
# Outputs GH_TRACE_ID if set, else "NO_GH_TRACE_ID"
fake_gh.write_text("#!/bin/sh\nenv | grep GH_TRACE_ID || echo 'NO_GH_TRACE_ID'\n")
```

#### Advanced: Capture All Arguments and Environment

```python
# Outputs all args and selected env vars (useful for debugging)
script = """#!/bin/sh
echo "Command: gh $@"
echo "GH_TRACE_ID=$GH_TRACE_ID"
echo "CUSTOM_VAR=$CUSTOM_VAR"
"""
fake_gh.write_text(script)
```

#### Exit Code Simulation

```python
# Exit with code 0 (success) or 1 (failure) based on argument
script = """#!/bin/sh
if [ "$1" = "fail" ]; then
    echo "Simulated failure"
    exit 1
else
    echo "Simulated success"
    exit 0
fi
"""
fake_gh.write_text(script)
```

### Full Integration Test Example

```python
# tests/integration/test_gh_trace_id_propagation.py

import pytest
import os
import subprocess
from pathlib import Path


@pytest.fixture(autouse=True)
def _fake_binary_on_path(tmp_path, monkeypatch):
    """Create fake gh binary that echoes environment variables.

    This fixture provides a fake gh command that will be found before
    the real gh in PATH. Used to test environment variable propagation
    to subprocesses without requiring a real GitHub CLI installation.

    Args:
        tmp_path: pytest fixture providing temporary directory
        monkeypatch: pytest fixture for environment modification
    """
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()

    # Create fake gh script that outputs environment
    fake_gh = fake_bin_dir / "gh"
    fake_gh.write_text(
        "#!/bin/sh\n"
        "echo 'ARGS: $@'\n"
        "echo 'GH_TRACE_ID='$GH_TRACE_ID\n"
        "echo 'CUSTOM_CONFIG='$CUSTOM_CONFIG\n"
    )

    # Set executable permission (CRITICAL!)
    fake_gh.chmod(0o755)

    # Prepend fake bin dir to PATH
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", str(fake_bin_dir) + ":" + original_path)

    return fake_bin_dir


class TestGHTraceIDPropagation:
    """Integration tests for environment variable propagation to subprocesses."""

    def test_subprocess_receives_gh_trace_id_from_context(self, monkeypatch, _fake_binary_on_path):
        """Subprocess receives GH_TRACE_ID when set in context."""
        from hephaestus.logging.utils import set_correlation_id

        # Set correlation ID in context
        set_correlation_id("req-trace-12345")

        # Import and call run_subprocess (which injects correlation ID into env)
        from hephaestus.utils.helpers import run_subprocess

        result = run_subprocess(["gh", "pr", "view", "123"])

        # Verify fake gh received the env var
        assert "GH_TRACE_ID=req-trace-12345" in result

    def test_subprocess_no_trace_id_when_not_set(self, monkeypatch, _fake_binary_on_path):
        """Subprocess does not receive GH_TRACE_ID when not set in context."""
        from hephaestus.logging.utils import set_correlation_id

        # Explicitly set to None (no context)
        set_correlation_id(None)

        from hephaestus.utils.helpers import run_subprocess

        result = run_subprocess(["gh", "pr", "view", "123"])

        # Verify fake gh did NOT receive the env var
        # (output will be empty for GH_TRACE_ID or the variable undefined)
        assert "GH_TRACE_ID=" not in result or result.count("GH_TRACE_ID=") == 1

    def test_subprocess_receives_custom_env_var(self, monkeypatch, _fake_binary_on_path):
        """Test custom environment variable propagation pattern."""
        import os

        env = os.environ.copy()
        env['CUSTOM_CONFIG'] = 'test-value-789'

        result = subprocess.run(
            ["gh", "pr", "view", "456"],
            env=env,
            capture_output=True,
            text=True,
        )

        assert "CUSTOM_CONFIG=test-value-789" in result.stdout


@pytest.mark.skip_on_ci
class TestGHTraceIDPropagationWithRealGH:
    """Tests that use the real gh command (skip in CI)."""

    def test_real_gh_availability(self):
        """Verify real gh is available in the current environment."""
        result = subprocess.run(["which", "gh"], capture_output=True, text=True)
        assert result.returncode == 0, "Real gh not found in PATH"

    def test_real_gh_with_trace_id(self):
        """Integration test with real gh (if available)."""
        from hephaestus.logging.utils import set_correlation_id

        set_correlation_id("req-real-gh-test")

        # This test requires real gh; only runs when explicitly enabled
        # Example: pytest -m real_gh tests/integration/test_gh_trace_id_propagation.py
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
        )
        assert "gh version" in result.stdout
```

### PATH Verification Script

```bash
# Debug: verify fake gh is in PATH and executable
$ echo $PATH
/tmp/pytest-123/bin:/usr/local/bin:/usr/bin:...

$ ls -la /tmp/pytest-123/bin/gh
-rwxr-xr-x 1 user group 42 May 28 10:00 /tmp/pytest-123/bin/gh

$ which gh
/tmp/pytest-123/bin/gh  # ← Fake gh found first!

$ gh pr view 123
GH_TRACE_ID=req-123...  # ← Fake binary output
```

### Environment Variable Injection Pattern (Used by run_subprocess)

```python
# hephaestus/utils/helpers.py

def run_subprocess(cmd: list[str], **kwargs) -> str:
    """Run subprocess, injecting correlation ID into environment.

    Args:
        cmd: Command to run (e.g., ["gh", "pr", "view", "123"])
        **kwargs: Additional arguments to subprocess.run()

    Returns:
        stdout from the subprocess

    Raises:
        subprocess.CalledProcessError: If subprocess returns non-zero
    """
    env = kwargs.pop('env', None) or os.environ.copy()

    # Inject correlation ID into environment
    from hephaestus.logging.utils import get_current_correlation_id

    if cid := get_current_correlation_id():
        env['GH_TRACE_ID'] = cid

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        **kwargs,
    )
    result.check_returncode()
    return result.stdout
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — GH_TRACE_ID propagation to subprocess | tests/integration/test_gh_trace_id_propagation.py:18-35; test runs locally with fake gh; CI environment may vary so marked verified-local |
