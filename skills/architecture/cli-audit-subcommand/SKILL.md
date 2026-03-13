# Skill: cli-audit-subcommand

## Overview

| Field     | Value                                                              |
|-----------|--------------------------------------------------------------------|
| Date      | 2026-02-20                                                         |
| Issue     | #791                                                               |
| PR        | #836                                                               |
| Objective | Add `scylla audit models` CLI subcommand for config validation      |
| Outcome   | Success — 8 new tests, all 2283 unit tests pass, pre-commit clean  |

## When to Use

- Adding a new `scylla audit <resource>` subcommand to the Click CLI
- Exposing an existing validation function as a discoverable, scriptable command
- Making a validation tool CI/pre-commit compatible via non-zero exit codes
- Adding a Click group with subcommands to an existing CLI

## Verified Workflow

### 1. Identify the existing validation logic

The validation already existed in `scylla/config/validation.py`. The CLI command is a
thin wrapper — it calls the library function, formats the output, and sets the exit code.
Do not duplicate validation logic in the CLI layer.

### 2. Add a Click group + subcommand

```python
# scylla/cli/main.py

@cli.group()
def audit() -> None:
    """Audit configuration files for consistency issues."""


@audit.command("models")
@click.option(
    "--config-dir",
    default=".",
    show_default=True,
    help="Project root directory (must contain config/models/).",
)
def audit_models(config_dir: str) -> None:
    """Audit model config files for filename/model_id mismatches.

    Exits non-zero if any mismatches are detected, making it suitable for
    use in pre-commit hooks or CI pipelines.

    Examples:
        scylla audit models

        scylla audit models --config-dir /path/to/project

    """
    from scylla.config import ConfigLoader
    from scylla.config.validation import validate_filename_model_id_consistency

    loader = ConfigLoader(Path(config_dir))
    models_dir = loader.base_path / "config" / "models"

    if not models_dir.exists():
        click.echo(f"ERROR: models directory not found: {models_dir}", err=True)
        sys.exit(1)

    mismatches: list[str] = []
    for config_path in sorted(models_dir.glob("*.yaml")):
        if config_path.stem.startswith("_"):
            continue
        try:
            model_config = loader.load_model(config_path.stem)
        except Exception:
            continue
        if model_config is None:
            continue
        warnings = validate_filename_model_id_consistency(config_path, model_config.model_id)
        for warning in warnings:
            mismatch_line = f"MISMATCH: {config_path.name} → {warning}"
            mismatches.append(mismatch_line)
            click.echo(mismatch_line)

    if mismatches:
        click.echo(f"\n{len(mismatches)} mismatch(es) detected.", err=True)
        sys.exit(1)
    else:
        click.echo("OK: all model config filenames match their model_id.")
```

**Key design decisions:**

- Use local imports inside the command function — matches existing CLI pattern in `list_models`
- `err=True` on the summary error line sends it to stderr; mismatch lines go to stdout
  (so `scylla audit models 2>/dev/null` still shows the MISMATCH lines for scripting)
- `sys.exit(1)` for non-zero exit — Click's `ctx.exit()` is an alternative but `sys.exit`
  is simpler and matches the existing CLI pattern
- Skip `_`-prefixed files — consistent with `validate_filename_model_id_consistency()`

### 3. Test with Click's CliRunner + tmp_path

Use `tmp_path` (pytest built-in fixture) to create isolated YAML fixtures.
Use `CliRunner.invoke()` — no subprocess overhead, captures stdout/stderr separately is
not needed here since `mix_stderr=True` is the default.

```python
class TestAuditModelsCommand:

    def test_audit_models_exit_zero_on_clean(self, tmp_path: Path) -> None:
        models_dir = tmp_path / "config" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "claude-opus-4-1.yaml").write_text(
            "model_id: claude-opus-4-1\ncost_per_1k_input: 0.015\ncost_per_1k_output: 0.075\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "models", "--config-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "OK: all model config filenames match their model_id." in result.output

    def test_audit_models_exit_nonzero_on_mismatch(self, tmp_path: Path) -> None:
        models_dir = tmp_path / "config" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "wrong-name.yaml").write_text(
            "model_id: claude-opus-4-1\ncost_per_1k_input: 0.015\ncost_per_1k_output: 0.075\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "models", "--config-dir", str(tmp_path)])
        assert result.exit_code == 1
        assert "MISMATCH" in result.output
```

Test cases to cover:

- Clean pass → exit 0
- Single mismatch → exit 1, `MISMATCH` in output
- `_`-prefixed file with mismatch → exit 0 (skipped)
- Missing `config/models/` dir → exit 1, `ERROR` in output
- Multiple mismatches → exit 1, count matches
- Parametrized: multiple valid model_id/filename pairs → exit 0

### 4. Inline YAML in test fixtures

For simple models, inline the YAML as a string rather than creating fixture files.
Minimum required fields for `ModelConfig`:

```yaml
model_id: claude-opus-4-1
cost_per_1k_input: 0.015
cost_per_1k_output: 0.075
```

Keep long inline YAML strings under 100 chars per line (ruff E501):

```python
# BAD — 105 chars
"model_id: claude-sonnet-4-5-20250929\ncost_per_1k_input: 0.003\ncost_per_1k_output: 0.015\n"

# GOOD — split across string literals
"model_id: claude-sonnet-4-5-20250929\n"
"cost_per_1k_input: 0.003\ncost_per_1k_output: 0.015\n"
```

### 5. Pre-commit hook compatibility

The command exits non-zero on any mismatch, making it directly usable as a pre-commit hook:

```yaml
- id: scylla-audit-models
  name: Scylla Audit Models
  entry: scylla audit models
  language: system
  files: ^config/models/.*\.yaml$
  pass_filenames: false
```

## Failed Attempts

### Importing ConfigLoader at module level

Attempted to add `from scylla.config import ConfigLoader` to the top-level imports
in `main.py`. This works but is inconsistent with the existing `list_models` pattern
which uses a local import inside the function. Reverted to match the existing pattern.

### Using `err=True` for MISMATCH lines

Initially considered routing all output to stderr. Changed to stdout for MISMATCH lines
so they are captured when piped (`scylla audit models | grep MISMATCH`), with only the
summary count on stderr.

## Results & Parameters

| Metric            | Value                                               |
|-------------------|-----------------------------------------------------|
| Files changed     | `scylla/cli/main.py`, `tests/unit/cli/test_cli.py`  |
| Tests added       | 8 (TestAuditModelsCommand)                          |
| Tests total       | 2283                                                |
| Pre-commit        | All hooks pass (ruff, mypy, type-alias, security)   |
| Exit code clean   | 0                                                   |
| Exit code mismatch| 1                                                   |
| Command           | `scylla audit models [--config-dir DIR]`            |

## Invocation

```bash
# Validate current project
scylla audit models

# Validate a specific project root
scylla audit models --config-dir /path/to/project

# Use in pre-commit
pre-commit run validate-model-configs --all-files
```
