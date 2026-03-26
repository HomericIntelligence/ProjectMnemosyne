---
name: testing-package-module-mock-coverage
description: "Add comprehensive mock-based unit tests for installed Python package modules
  with subprocess/shutil calls. Use when: (1) a hephaestus/ module has no tests or
  low coverage, (2) the module uses subprocess.run or shutil.which, (3) you need >85%
  coverage without real command execution."
category: testing
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mock
  - subprocess
  - coverage
  - hephaestus
  - package-module
---

# Testing Package Modules with Mock Coverage

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add comprehensive unit tests for installed Python package modules that use subprocess/shutil, achieving >85% coverage |
| **Outcome** | 99% coverage of `readme_commands.py` with 65 tests, all mocked |
| **Verification** | verified-local |

## When to Use

- A module under `hephaestus/` (installed package, not scripts/) has no or low test coverage
- The module calls `subprocess.run`, `shutil.which`, or other external process functions
- You need to mock at the module import path (not stdlib level) to prevent real execution
- An issue or audit identifies coverage gaps in validation/utility modules

## Verified Workflow

### Quick Reference

```bash
# Run module-specific tests with coverage
pixi run python -m pytest tests/unit/validation/test_readme_commands.py -v \
  --cov=hephaestus.validation.readme_commands --cov-report=term-missing --no-cov-on-fail

# Run full suite to verify no regressions
pixi run pytest tests/unit -v
```

### Detailed Steps

1. **Read the source module** to understand all public methods, subprocess calls, and error handling paths
2. **Read the existing test file** (if any) to avoid duplicating tests
3. **Organize tests into one class per public method/concept**:
   - `TestCodeBlock` for dataclass methods
   - `TestExtractCodeBlocks` for file parsing
   - `TestCommandClassification` for is_blocked/is_allowed/is_safe
   - `TestValidateSyntax` for mocked subprocess syntax checks
   - `TestValidateExecution` for mocked subprocess execution
   - `TestGenerateReport` for output formatting
4. **Mock at the module import path**, not at stdlib:
   ```python
   # CORRECT - mocks the module's reference
   @patch("hephaestus.validation.readme_commands.subprocess.run")

   # WRONG - mocks globally, may miss the target
   @patch("subprocess.run")
   ```
5. **Mock all external dependencies per method**:
   - `subprocess.run` for validate_syntax, validate_execution
   - `shutil.which` for validate_availability
   - `get_repo_root` for validate_execution (returns Path)
6. **Use `@pytest.mark.parametrize`** for exhaustive pattern lists (e.g., all BLOCKED_PATTERNS)
7. **Cover all error paths**: TimeoutExpired, OSError, non-zero return codes
8. **Python 3.14 compatibility**: Construct `subprocess.TimeoutExpired` with positional `cmd` and `timeout` only:
   ```python
   exc = subprocess.TimeoutExpired(cmd="bash", timeout=5)
   mock_run.side_effect = exc
   ```
9. **Run module-specific coverage** with `--no-cov-on-fail` to see line coverage even when project threshold isn't met
10. **Run ruff check + format** before committing

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Importing unused constants | Imported `BLOCKED_PATTERNS`, `EXECUTE_LANGUAGES`, `SKIP_MARKERS` for documentation purposes | ruff F401 auto-removed them in pre-commit | Only import symbols actually used in assertions |
| Running coverage without `--no-cov-on-fail` | Used default `--cov=hephaestus` from pyproject.toml | Coverage fails at 12% overall since only one module's tests ran | Use `--cov=hephaestus.validation.readme_commands --no-cov-on-fail` to see module-specific coverage |
| Writing multi-line strings in test fixture | Used multi-line string with explicit newlines for markdown content | ruff format collapsed them to single-line concatenation | Let ruff format handle it; the single-line version is equivalent and passes formatting |

## Results & Parameters

### Mock Pattern Templates

**Mocking subprocess.run (success)**:
```python
@patch("hephaestus.validation.readme_commands.subprocess.run")
def test_valid_syntax(self, mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
    result = ReadmeValidator().validate_syntax("echo hello")
    assert result.passed is True
    mock_run.assert_called_once()
```

**Mocking subprocess.run (failure)**:
```python
@patch("hephaestus.validation.readme_commands.subprocess.run")
def test_invalid_syntax(self, mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=2, stderr="syntax error", stdout="")
    result = ReadmeValidator().validate_syntax("echo 'unterminated")
    assert result.passed is False
    assert result.error_message == "syntax error"
```

**Mocking subprocess.run (timeout)**:
```python
@patch("hephaestus.validation.readme_commands.subprocess.run")
def test_timeout(self, mock_run: MagicMock) -> None:
    exc = subprocess.TimeoutExpired(cmd="bash", timeout=5)
    mock_run.side_effect = exc
    result = ReadmeValidator().validate_syntax("echo hang")
    assert result.passed is False
    assert "timed out" in (result.error_message or "").lower()
```

**Mocking shutil.which**:
```python
@patch("hephaestus.validation.readme_commands.shutil.which")
def test_binary_found(self, mock_which: MagicMock) -> None:
    mock_which.return_value = "/usr/bin/echo"
    result = ReadmeValidator().validate_availability("echo test")
    assert result.passed is True
    mock_which.assert_called_once_with("echo")
```

**Stacking multiple mocks (validate_execution needs both subprocess.run and get_repo_root)**:
```python
@patch("hephaestus.validation.readme_commands.get_repo_root")
@patch("hephaestus.validation.readme_commands.subprocess.run")
def test_execution(self, mock_run: MagicMock, mock_root: MagicMock) -> None:
    mock_root.return_value = Path("/repo")
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    result = ReadmeValidator().validate_execution("echo hello")
    assert result.passed is True
```

### Coverage Results

| Module | Before | After | Tests |
|--------|--------|-------|-------|
| `hephaestus/validation/readme_commands.py` | ~0% | 99% | 65 |

### Key pyproject.toml Settings

```toml
[tool.pytest.ini_options]
addopts = ["--cov=hephaestus", "--cov-report=term-missing", "--cov-fail-under=80"]
```

Override for module-specific runs:
```bash
pixi run python -m pytest tests/unit/validation/test_readme_commands.py \
  --cov=hephaestus.validation.readme_commands --cov-report=term-missing --no-cov-on-fail
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #51: Add test coverage for readme_commands.py | 65 tests, 99% coverage, PR #94 |
