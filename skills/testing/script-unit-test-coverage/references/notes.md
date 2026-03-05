# script-unit-test-coverage — Raw Session Notes

## Context

- **Project**: ProjectScylla
- **Issue**: #1358 — test(scripts): Add tests for 12 untested scripts
- **Branch**: `1358-auto-impl`
- **PR**: #1383

## Scripts Tested

12 scripts previously lacking any test coverage:
- `check_defaults_filename.py`
- `docker_build_timing.py`
- `export_data.py`
- `generate_all_results.py`
- `generate_figures.py`
- `generate_tables.py`
- `get_stats.py`
- `implement_issues.py`
- `lint_configs.py`
- `migrate_skills_to_mnemosyne.py`
- `plan_issues.py`
- `validation.py`

## Key Technical Notes

### pythonpath in pyproject.toml
```toml
pythonpath = [".", "scripts"]
```
This is why `from <script_name> import ...` works without any `sys.path` manipulation in tests.

### Module-level constant patching
`check_defaults_filename.py` sets `_REPO_ROOT = Path(__file__).parent.parent` at module load time.
To test `main()` with a different root: `patch("check_defaults_filename._REPO_ROOT", tmp_path)`.
The patched value replaces the module attribute for the duration of the `with` block.

### Sequential subprocess mocking
`get_stats.py` calls `subprocess.run` twice (total count, then open/merged count).
Use `side_effect=[mock1, mock2]` — each call consumes the next mock from the list.

### Heavy dependency isolation strategy
For scripts that import the full scylla analysis stack (`export_data`, `generate_figures`,
`generate_tables`), focus tests on:
1. Pure utility functions that don't need scylla (e.g., `json_nan_handler`)
2. Module-level registries (e.g., `FIGURES` dict) — just structural checks
3. `main()` orchestration with all scylla calls mocked out

### Pre-commit issues encountered
- ruff F841: unused mock aliases (`as mock_fh` without asserting on `mock_fh`)
- mypy var-annotated: `config = {"x": {}}` needs `config: dict[str, object] = {"x": {}}`
- mypy attr-defined + unused-ignore: `capsys: object` wrong type; use `pytest.CaptureFixture[str]`
- ruff format: auto-fixed on first run; re-stage and re-commit

## Pre-commit Run Count
2 runs needed: first run had 3 issues (F841 ×2, var-annotated, capsys type)
