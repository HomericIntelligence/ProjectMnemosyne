# Skill: config-default-model-drift

## Overview

| Field       | Value                                                                  |
|-------------|------------------------------------------------------------------------|
| Date        | 2026-02-20                                                             |
| Issue       | #793                                                                   |
| PR          | #838                                                                   |
| Objective   | Eliminate hardcoded model-ID literals that silently drift from config  |
| Outcome     | Success — single source of truth in `config/defaults.yaml`            |
| Category    | architecture                                                           |

## When to Use

Trigger when you see any of the following:

- Hardcoded model-ID string literals (e.g. `"claude-opus-4-5-20251101"`) in CLI or orchestrator code
- `model or "<literal>"` fallback patterns instead of reading from config
- Follow-up issues noting that a previous refactor missed a stale literal
- A new default model has been adopted but code still references the old one
- Audit findings of literals that will "silently fall out of sync" with a config file

## Verified Workflow

### 1. Locate every hardcoded literal

```bash
grep -rn "claude-opus-4-5" scylla/
```

Expect: `scylla/cli/main.py` and `scylla/orchestrator.py` (possibly docstrings too).

### 2. Add `default_model` to `config/defaults.yaml`

```yaml
# Default model used when no --model flag is provided
default_model: "claude-opus-4-5-20251101"
```

Place it at the top level (not nested under a section).

### 3. Add the Pydantic field to `DefaultsConfig`

In `scylla/config/models.py`, inside `DefaultsConfig`:

```python
default_model: str = Field(
    default="claude-opus-4-5-20251101",
    description="Default model ID when none is specified",
)
```

The Python-level default keeps backward-compat for callers that don't supply the YAML key
(e.g. test fixtures that use a trimmed `defaults.yaml`).

### 4. Update the CLI

In `scylla/cli/main.py`:

```python
# Before (stale literal)
model_id = model or "claude-opus-4-5-20251101"

# After (reads from config)
from scylla.config import ConfigLoader
model_id = model or ConfigLoader().load_defaults().default_model
```

`ConfigLoader()` with no arguments resolves relative to `Path(".")` (the cwd at runtime).

### 5. Update docstrings / examples

In `scylla/orchestrator.py` the class docstring had a copy of the literal as an example.
Replace with `ConfigLoader().load_defaults().default_model` to keep it consistent
and searchable.

### 6. Write the test

Add to `tests/unit/cli/test_cli.py`:

```python
def test_run_default_model_from_config(self) -> None:
    """Default model_id is read from ConfigLoader, not a hardcoded literal."""
    sentinel_model = "test-model-from-config"

    mock_defaults = MagicMock()
    mock_defaults.default_model = sentinel_model

    mock_loader_instance = MagicMock()
    mock_loader_instance.load_defaults.return_value = mock_defaults

    captured: dict[str, str] = {}

    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run_batch.return_value = []

    def capture_config(config: object) -> MagicMock:
        captured["model"] = getattr(config, "model", None)
        return mock_orchestrator_instance

    runner = CliRunner()
    with (
        patch("scylla.cli.main.ConfigLoader", return_value=mock_loader_instance),
        patch("scylla.cli.main.EvalOrchestrator", side_effect=capture_config),
    ):
        runner.invoke(cli, ["run", "001-test", "--tier", "T0", "--runs", "1"])

    assert captured.get("model") == sentinel_model
```

Key points:
- Mock `scylla.cli.main.ConfigLoader` (the import in the module under test, not the source).
- Capture `OrchestratorConfig.model` via `side_effect=capture_config` on `EvalOrchestrator`.
- The test is independent of `config/defaults.yaml` on disk — it proves the wiring, not the value.

### 7. Update the test fixture if needed

`tests/fixtures/config/defaults.yaml` does **not** need to be updated because `DefaultsConfig`
has a Python-level Pydantic default for `default_model`. Existing fixture-based tests keep passing.

### 8. Run validation

```bash
pixi run python -m pytest tests/ --no-cov    # all tests pass
pre-commit run --all-files                    # all hooks pass
```

## Failed Attempts

None in this session — the pattern was clean and straightforward.

## Results & Parameters

| Parameter         | Value                        |
|-------------------|------------------------------|
| Files changed     | 5                            |
| Lines added       | 41                           |
| Lines removed     | 2                            |
| Tests added       | 1                            |
| Total tests       | 2267 (all passing)           |
| Pre-commit hooks  | 13 / 13 passing              |

### Files Modified

| File                             | Change                                                  |
|----------------------------------|---------------------------------------------------------|
| `config/defaults.yaml`           | Added `default_model` key                               |
| `scylla/config/models.py`        | Added `default_model` field to `DefaultsConfig`         |
| `scylla/cli/main.py`             | Replaced literal with `ConfigLoader().load_defaults()…` |
| `scylla/orchestrator.py`         | Updated docstring example                               |
| `tests/unit/cli/test_cli.py`     | Added `test_run_default_model_from_config`              |

## Key Insight

When `ConfigLoader()` is instantiated without a `base_path`, it defaults to `Path(".")`.
This is fine at CLI runtime (cwd is the project root) but would fail in a unit test without
mocking. Always mock `scylla.cli.main.ConfigLoader` (the reference in the module, not the
original import path) when testing CLI code that calls `ConfigLoader()` at the module level.
