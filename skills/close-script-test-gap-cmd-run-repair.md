---
name: close-script-test-gap-cmd-run-repair
description: Pattern for extending existing CLI test files to cover command-handler argument flow and repair edge cases using mocks only
category: testing
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Close Script Test Gap: cmd_run() and cmd_repair() Edge Cases

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-27 |
| **Objective** | Close 87.5% script test gap by adding `cmd_run()` and `cmd_repair()` unit tests to `manage_experiment.py` test file |
| **Outcome** | ✅ 5 new tests added, 119 total passing, 78.36% project coverage (above 75% threshold) |
| **Context** | ProjectScylla issue #1113 — `scripts/manage_experiment.py` (1,515 lines) lacked tests for its two primary command handlers despite 114 existing parser tests |

## When to Use This Skill

Use this pattern when:

1. **An existing test file covers parser/argument parsing** but not the actual command handler functions
2. **You need to verify CLI argument → config flow** (e.g., `--tiers`, `--max-subtests`, `--until`)
3. **A repair/recovery function has an "if existing" skip path** that needs testing
4. **Exception handling paths in loops** need coverage (e.g., corrupt JSON continue)
5. **The script is the primary entry point** for a system with no dedicated handler tests

**Trigger phrases**:
- "tests only cover argument parsing, not what the command actually does"
- "the repair function has an `if existing is None` branch that's not tested"
- "need to verify `--flag` actually flows through to the config object"
- "command handler exception path not covered"

## Verified Workflow

### Step 1: Audit Existing Coverage

Read the existing test file's module docstring — it lists what IS covered. Compare against
the actual command handler to find genuine gaps:

```bash
grep -n "^class Test" tests/unit/e2e/test_manage_experiment.py
# Identify: parser tests, validation tests, flow tests
# Look for: missing tiers_to_run, max_subtests, "if existing" branches
```

**Key questions**:
- Does any test assert on `config.tiers_to_run`?
- Does any test assert on `config.max_subtests`?
- Is there a test where `completed_runs` already has an entry and repair is called?
- Is there a test with corrupt JSON in a result file?

### Step 2: Identify the Correct Patch Path

The patch path must match the `from ... import` inside the command handler function, **not**
where the function is defined:

```python
# In manage_experiment.py cmd_run():
from scylla.e2e.runner import run_experiment   # → patch at "scylla.e2e.runner.run_experiment"
from scylla.e2e.model_validation import validate_model  # → "scylla.e2e.model_validation.validate_model"
```

Wrong path = mock silently ignored, test calls real code.

### Step 3: Capture the Config Object

Use a closure to capture what config was passed to the mocked function:

```python
captured_configs: list[Any] = []

def mock_run_experiment(config, tiers_dir, results_dir, fresh):
    captured_configs.append(config)
    return {"T0": {}}

with patch("scylla.e2e.runner.run_experiment", side_effect=mock_run_experiment):
    result = cmd_run(args)

assert captured_configs[0].tiers_to_run == [TierID.T0, TierID.T2]
assert captured_configs[0].max_subtests == 3
```

### Step 4: Test the "Skip Existing" Path in Repair

To test that `cmd_repair()` does NOT overwrite an existing entry:

```python
# Checkpoint already has "passed" for run 1
completed_runs={"T0": {"00-empty": {"1": "passed"}}}

# run_result.json says "failed"
(run_dir / "run_result.json").write_text(json.dumps({"judge_passed": False}))

# After repair, must still be "passed" (not overwritten)
assert updated.completed_runs["T0"]["00-empty"][1] == "passed"
```

### Step 5: Test the Exception-Continue Path

Write invalid JSON to trigger the `except Exception` branch:

```python
(run_dir / "run_result.json").write_text("{ not valid json }")
result = cmd_repair(args)
assert result == 0               # Must not crash
assert updated.completed_runs == {}  # No entry added
```

### Step 6: Use `--skip-judge-validation` for cmd_run Tests

All `cmd_run()` tests that don't test model validation should pass
`--skip-judge-validation` to avoid needing to mock the model validation path:

```python
args = parser.parse_args([
    "run", "--config", str(config_dir),
    "--tiers", "T0", "T2",
    "--skip-judge-validation",   # ← eliminates validate_model mock requirement
])
```

### Step 7: Append to End of Existing Test File

Since the file is large (4000+ lines), append new classes rather than inserting:

```bash
cat >> tests/unit/e2e/test_manage_experiment.py << 'PYTHON_EOF'

class TestCmdRunTiersAndMaxSubtests:
    ...

class TestCmdRepairEdgeCases:
    ...
PYTHON_EOF
```

Also update the module docstring at the top to document new coverage.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test Classes Added

```python
class TestCmdRunTiersAndMaxSubtests:
    """3 tests: tiers flow, max_subtests flow, default tiers non-empty"""
    # Patch: "scylla.e2e.runner.run_experiment"
    # Use: --skip-judge-validation to avoid second mock

class TestCmdRepairEdgeCases:
    """2 tests: skip-existing entry, corrupt JSON continue"""
    # No mocks needed — uses real checkpoint load/save with tmp_path
```

### Minimal Test Directory Fixture

```python
def _make_test_dir(self, path: Path) -> None:
    import yaml
    path.mkdir(parents=True, exist_ok=True)
    (path / "test.yaml").write_text(yaml.dump({
        "task_repo": "https://github.com/test/repo",
        "task_commit": "abc123",
        "experiment_id": "test-exp",
        "timeout_seconds": 3600,
        "language": "python",
    }))
    (path / "prompt.md").write_text("test prompt")
```

### Minimal Checkpoint Fixture

```python
def _make_checkpoint_file(self, path, run_states, completed_runs):
    data = {
        "version": "3.1", "experiment_id": "test-exp",
        "experiment_dir": str(path), "config_hash": "abc123",
        "started_at": "2024-01-01T00:00:00+00:00",
        "last_updated_at": "2024-01-01T00:00:00+00:00",
        "status": "interrupted",
        "run_states": run_states, "completed_runs": completed_runs,
    }
    cp = path / "checkpoint.json"
    cp.write_text(json.dumps(data))
    return cp
```

### Coverage Impact

| Metric | Before | After |
|--------|--------|-------|
| Tests in file | 114 | 119 |
| Full suite tests | 3185 | 3190 |
| Project coverage | ~78% | 78.36% |
| cmd_run() flow coverage | gaps | tiers + max_subtests verified |
| cmd_repair() branch coverage | missing | skip-existing + corrupt-JSON covered |
