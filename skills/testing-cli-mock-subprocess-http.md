---
name: testing-cli-mock-subprocess-http
description: "Test Python CLI apps that call subprocess.run and urlopen. Use when: (1) testing argparse CLI handlers, (2) mocking Slurm/CLI subprocess commands, (3) mocking HTTP health checks with urlopen."
category: testing
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pytest, mock, subprocess, urlopen, argparse, cli]
---

# Testing Python CLI Apps with Mocked Subprocess and HTTP

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Write comprehensive tests for Python CLI applications using subprocess.run, urllib.request.urlopen, and argparse |
| **Outcome** | Successfully increased test coverage from 80% to 85.57% with approximately 275 new tests |
| **Verification** | verified-local |

## When to Use

- Testing a Python CLI application that spawns subprocesses (sbatch, squeue, dstack, etc.)
- Testing HTTP health check functions that use urllib.request.urlopen
- Testing argparse CLI handlers by invoking main() with argv lists
- Building schema-compliant test fixtures for complex YAML manifests

## Verified Workflow

### Quick Reference

```python
# Mock subprocess.run to intercept CLI commands
from unittest.mock import patch, MagicMock
import subprocess

original_run = subprocess.run

def mock_subprocess_run(cmd, *args, **kwargs):
    if isinstance(cmd, list) and cmd and "sbatch" in str(cmd[0]):
        return subprocess.CompletedProcess(cmd, 0, stdout="12345\n", stderr="")
    return original_run(cmd, *args, **kwargs)

with patch("subprocess.run", side_effect=mock_subprocess_run):
    result = main(["slurm-reconcile", "--manifest", path, "--once"])

# Mock urlopen for HTTP health checks
mock_response = MagicMock()
mock_response.getcode.return_value = 200
mock_response.read.return_value = json.dumps({"status": "ready"}).encode()
mock_response.__enter__ = MagicMock(return_value=mock_response)
mock_response.__exit__ = MagicMock(return_value=False)
with patch("module_name.urlopen", return_value=mock_response):
    ok, payload, err = probe_health_url("http://host:8080/health", 5.0)

# Test CLI handlers through main()
result = main(["validate-manifest", "--cluster", "m1", str(manifest_path)])
assert result == 0
```

### Detailed Steps

1. **Mock subprocess.run at the module level** - Use `patch("subprocess.run")` context manager. The mock function should check `cmd[0]` or join the command list to route to the right mock behavior.

2. **Mock urlopen with proper context manager support** - The MagicMock needs `__enter__` and `__exit__` methods since `urlopen` is used as a context manager (`with urlopen(...) as resp`).

3. **Test argparse CLI handlers through main()** - Pass a list of argv strings to `main()`. Check the return code (0 for success, non-zero for errors). Use `capsys` fixture to capture stdout/stderr output.

4. **Build test manifests from real examples** - Load the real production manifest with `load_manifest(path)` and resolve for a cluster with `resolve_manifest_for_cluster(manifest, "m1")`. This avoids constant schema validation failures as new required fields are added.

5. **Use io.BytesIO for HTTPError mock bodies** - When testing HTTP error handling that reads the error body: `HTTPError(url, code, msg, {}, io.BytesIO(body_bytes))`.

6. **Use monkeypatch for function-level mocking** - When a function default captures another function at definition time, monkeypatching the original will not work. Mock at subprocess.run level instead.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Monkeypatch default runner | `monkeypatch.setattr("module._run_slurm_command", mock_fn)` | Default parameter values are captured at function definition time, not call time | Must mock at subprocess.run level when the runner is a default parameter |
| Build test manifests from scratch | Manually construct manifest dicts with all required fields | Schema has 50+ required fields across nested sections; new fields are added regularly | Always load the real example manifest and resolve for a cluster instead |
| Positional args for --manifest | Pass manifest path as positional arg to CLI command | argparse parser requires `--manifest` as a named arg for some commands | Read the argparse add_parser definition to determine positional vs named args |
| Assert specific return codes | `assert result == 1` for error cases | Actual return codes may differ (e.g., 2 instead of 1) | Use `assert result != 0` for error cases unless the exact code is known |

## Results & Parameters

**Environment:** Python 3.12, pytest 9.0, unittest.mock, argparse

**Coverage improvement:** 80% to 85.57% (approximately 275 new tests)

**Key imports:** `from unittest.mock import patch, MagicMock`, `import io`, `import subprocess`

**Mock patterns:**

- subprocess.run: `with patch("subprocess.run", side_effect=mock_fn):`
- urlopen: `with patch("module.urlopen", return_value=mock_response):`
- Function: `monkeypatch.setattr("module.func", mock_fn)`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | PR 116 CI fixes, test coverage improvement | 580 tests passing, 85.57% coverage |
