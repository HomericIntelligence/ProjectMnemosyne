# Session Notes: mypy-precommit-hook-pixi

## Context

- **Project**: ProjectOdyssey (Mojo-based AI research platform)
- **Issue**: #3159 — [P3-5] Add mypy to pre-commit hooks for Python type checking
- **PR**: #3364
- **Date**: 2026-03-05
- **Branch**: 3159-auto-impl

## Issue Spec

The issue asked for:
1. Add mypy hook to `.pre-commit-config.yaml` (provided exact YAML in issue)
2. Run mypy on existing scripts and fix any errors
3. Add `mypy` to `pixi.toml` dev dependencies if not already present
4. Verify `just pre-commit-all` passes

## What Was Already in Place

- `mypy = ">=1.19.1,<2"` already in `pixi.toml` — no change needed
- `types-PyYAML = ">=6.0"` already in `pixi.toml` — but NOT sufficient for mirrors-mypy hook

## Errors Encountered

### Error 1: Module found twice
```
scripts/generators/templates.py: error: Source file found twice under different
module names: "generators.templates" and "scripts.generators.templates"
```
**Fix**: Add `--explicit-package-bases` flag.

### Error 2: X | Y union syntax
```
scripts/generators/generate_training_script.py:301: error: X | Y syntax for
unions requires Python 3.10  [syntax]
        batch_size: int | None = None,
```
6 errors across 3 files. **Fix**: Add `--python-version 3.10`.

### Error 3: var-annotated (after fixing above)
```
scripts/generators/templates.py:66: error: Need type annotation for "missing"
(hint: "missing: List[<type>] = ...")  [var-annotated]
        missing = []
scripts/validation.py:91: error: Need type annotation for "missing"
```
**Fix**: Annotate as `missing: list[str] = []` in both files.

### Error 4: import-untyped (in mirrors-mypy hook)
```
scripts/validate_test_coverage.py:25: error: Library stubs not installed for "yaml"
scripts/agents/tests/conftest.py:14: error: Library stubs not installed for "yaml"
scripts/agents/agent_utils.py:25: error: Library stubs not installed for "yaml"
scripts/agents/check_frontmatter.py:29: error: Library stubs not installed for "yaml"
```
Even though `types-PyYAML` is in pixi.toml, the `mirrors-mypy` hook runs in its own
isolated virtualenv. **Fix**: Add `additional_dependencies: [types-PyYAML]` to the hook config.

## Files Changed

- `.pre-commit-config.yaml` — added mypy hook (9 lines)
- `scripts/generators/templates.py:66` — `missing: list[str] = []`
- `scripts/validation.py:91` — `missing: list[str] = []`

## Final Working Config

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      files: ^scripts/.*\.py$
      args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --python-version, "3.10"]
      additional_dependencies: [types-PyYAML]
```

## Verification

```bash
pixi run pre-commit run mypy --all-files
# mypy...Passed

pixi run pre-commit run --all-files
# All hooks Passed
```
