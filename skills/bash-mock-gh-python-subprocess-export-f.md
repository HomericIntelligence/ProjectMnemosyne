---
name: bash-mock-gh-python-subprocess-export-f
description: "Pattern for mocking a bash CLI tool (e.g., gh) as a bash function in Python subprocess tests using export -f. Use when: (1) testing a bash script that calls an external CLI tool like gh, (2) tests run via Python subprocess.run('bash -c ...'), (3) you need to control the CLI tool's stdout/exit code per test case."
category: testing
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Mocking bash CLI Tools in Python Subprocess Tests: export -f Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Mock the `gh` CLI (or any bash binary) in Python integration tests that run bash scripts via `subprocess.run` |
| **Outcome** | Proposed pattern — not yet validated in CI |
| **Verification** | unverified |

## When to Use

- Testing a bash script that calls `gh`, `curl`, `aws`, or another external CLI tool
- Tests run the script via Python `subprocess.run(["bash", "-c", "..."])` or similar
- You need to assert on stdout/exit code without hitting the real external service
- You want a lightweight alternative to creating a fake binary on `$PATH`
- Bash version ≥4.2 is available (required for `export -f` function export support)

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end in CI. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
import subprocess

def _run_with_mock_gh(json_response: str, script_args: str) -> subprocess.CompletedProcess:
    """Run a bash script with a mock gh function injected via export -f."""
    bash_script = f"""
gh() {{
  echo '{json_response}'
  return 0
}}
export -f gh

source ./scripts/my_script.sh
choose_merge_flag {script_args}
"""
    return subprocess.run(
        ["bash", "-c", bash_script],
        capture_output=True,
        text=True,
    )

def test_rebase_chosen():
    result = _run_with_mock_gh(
        json_response='[{{"rebaseMergeAllowed":true,"squashMergeAllowed":false,"mergeCommitAllowed":false}}]',
        script_args="owner repo 123",
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "--rebase"
```

### Detailed Steps

1. **Define the mock as a bash function** — define it with `function_name() { ... }` syntax inside the `bash -c` string. Use `echo` to emit the desired JSON/text stdout.
2. **Export the function** — `export -f function_name` makes the function available to child processes and to scripts sourced within the same bash session.
3. **Source the script under test** — `. ./scripts/my_script.sh` (dot-source) loads the script's functions into the current bash session. The mock function defined before sourcing takes precedence over any real binary.
4. **Call the function under test** — invoke the specific function from the sourced script with the desired arguments.
5. **Wrap in a Python helper** — `_run_with_mock_gh(json_response, script_args)` keeps test bodies clean.

### Why export -f Works

When bash evaluates `bash -c "..."`, the entire string runs in a single bash session. A function defined in that session shadows any binary of the same name. `export -f` is needed only if child processes (subshells) also need the mock — for most bash scripts that don't spawn subshells, `export -f` is defensive but harmless.

The mock function overrides `gh` by name resolution order: bash checks functions before PATH binaries.

### Fragility: JSON in f-string single-quote wrapping

**The pattern `echo '${json_response}'` is fragile**:

- If `json_response` contains single quotes, the bash string terminates early and the command fails silently or errors
- If `json_response` contains backslashes, they may be interpreted differently
- **Safe alternative**: write the JSON to a temp file and have the mock `cat` it:

```python
import tempfile, os

def _run_with_mock_gh_safe(json_response: str, script_args: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json_response)
        tmp_path = f.name
    try:
        bash_script = f"""
gh() {{
  cat {tmp_path}
  return 0
}}
export -f gh

source ./scripts/my_script.sh
choose_merge_flag {script_args}
"""
        return subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)
    finally:
        os.unlink(tmp_path)
```

The simple f-string pattern is safe only when the JSON body contains no single quotes or backslashes — safe for literal test fixtures, fragile for dynamic/user-supplied content.

### Bash Version Requirement

`export -f` (exporting bash functions to child processes) was introduced/standardized in bash 4.2. Most modern Linux CI environments (Ubuntu 20.04+) ship bash 5.x. Verify with:

```bash
bash --version
```

If the CI environment uses bash <4.2 or uses `dash` as `/bin/sh`, `export -f` will silently fail. The test helper uses `bash -c` explicitly, so `/bin/sh` is irrelevant — but CI environments that substitute `bash` with an older version could break the mock.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fake binary on PATH | Create a temp `gh` script, prepend to `$PATH` in the subprocess env | Requires file creation + cleanup; harder to parameterize per test; works but verbose | `export -f` is lighter for tests that already use `bash -c` |
| Python `unittest.mock.patch` on subprocess | Mock at the Python level to intercept `gh` calls | Doesn't work — the real `gh` is called by the bash subprocess, not by Python code; Python mock intercepts Python calls only | Bash scripts called via `subprocess.run` need bash-level mocking |
| JSON with single quotes in f-string | `echo '{"key": "it's value"}'` | Single quote inside the value terminates the bash string — syntax error | Always validate test JSON is free of single quotes when using the simple f-string pattern; prefer temp file for complex JSON |

## Results & Parameters

**Regression test for stderr noise**:

A dedicated test validates that the fix (separating stderr) actually guards against regression:

```python
def test_shell_helper_handles_gh_stderr_noise():
    """Verify that gh stderr output does not corrupt jq parsing of stdout."""
    bash_script = """
gh() {
  echo '[{"rebaseMergeAllowed":true,"squashMergeAllowed":false,"mergeCommitAllowed":false}]'
  echo "WARNING: gh update available" >&2   # simulate stderr noise
  return 0
}
export -f gh

source ./scripts/choose_merge_flag.sh
choose_merge_flag owner repo 123
"""
    result = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "--rebase"
    # stderr noise must NOT appear in stdout
    assert "WARNING" not in result.stdout
```

This test is the correct regression guard for the `2>&1` bug. A general happy-path test that also passes is insufficient — it only catches the regression if the mock gh actually writes to stderr.

**Source**: Planning notes for ProjectHephaestus issue #1125 (`test_choose_merge_flag_sh.py` integration tests).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1125 planning — integration tests for `scripts/choose_merge_flag.sh` | Pattern designed, not yet CI-validated |
