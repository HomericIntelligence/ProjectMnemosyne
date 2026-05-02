# Template Migration Session Notes

## Session Context

**Date:** 2026-02-15
**Issue:** #648 - Consider parameterizing script templates instead of string interpolation
**Branch:** 648-auto-impl
**PR:** #719

## Problem Statement

All 7 extracted functions in `scylla/e2e/llm_judge.py` used f-string templates for bash script generation. This had limitations:

1. Hard to validate script correctness at development time
2. Difficult to reuse script fragments across different contexts
3. No syntax highlighting or shell script linting
4. Changes require modifying Python code

## Solution Implemented

Moved script templates to separate `.sh.template` files in `scylla/e2e/templates/` using Python's built-in `string.Template` for parameter substitution.

## Implementation Steps

### 1. Created Template Directory Structure

```bash
mkdir -p scylla/e2e/templates
```

Created 13 template files:

- `python_check.sh.template`
- `python_format.sh.template`
- `python_test.sh.template`
- `mojo_build.sh.template`
- `mojo_build_modular.sh.template`
- `mojo_format.sh.template`
- `mojo_format_modular.sh.template`
- `mojo_format_standalone_subdir.sh.template`
- `mojo_test.sh.template`
- `mojo_test_modular.sh.template`
- `precommit.sh.template`
- `run_all_python.sh.template`
- `run_all_mojo.sh.template`

### 2. Created Template Loader Module

File: `scylla/e2e/template_loader.py`

Key functions:

- `load_template(template_name: str) -> Template`
- `render_template(template_name: str, **kwargs: str) -> str`
- `write_script(output_path: Path, template_name: str, executable: bool = True, **kwargs: str) -> Path`

Decision: Used `string.Template` instead of Jinja2 to avoid adding a new dependency.

### 3. Migrated Script Generation Functions

Updated 7 functions in `scylla/e2e/llm_judge.py`:

- `_create_python_scripts()`
- `_create_mojo_build_script()`
- `_create_mojo_format_script()`
- `_create_mojo_test_script()`
- `_create_precommit_script()`
- `_create_run_all_script()`

Pattern used:

```python
# Before
def _create_python_scripts(commands_dir: Path, workspace: Path) -> None:
    build_script = commands_dir / "python_check.sh"
    build_script.write_text(f"""...""")
    build_script.chmod(0o755)
    # ... repeat for each script

# After
def _create_python_scripts(commands_dir: Path, workspace: Path) -> None:
    write_script(
        commands_dir / "python_check.sh",
        "python_check.sh.template",
        workspace=str(workspace),
    )
    # Single line per script
```

### 4. Added Shellcheck Validation

Added to `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/shellcheck-py/shellcheck-py
  rev: v0.9.0.6
  hooks:
    - id: shellcheck
      name: ShellCheck
      files: \.(sh|bash|sh\.template)$
      types: [text]
```

Created `.shellcheckrc`:

```bash
# Disable checks for template variables (false positives)
disable=SC2034,SC2154,SC1036,SC1088
```

### 5. Created Test Suite

File: `tests/e2e/test_template_loader.py`

32 tests covering:

- Template directory existence
- Template loading
- Template rendering with substitution
- Script writing with permissions
- All templates exist
- All templates have proper shebangs

## Technical Challenges & Solutions

### Challenge 1: Variable Escaping

**Problem:** `string.Template` tries to substitute ALL `$variable` occurrences, including bash variables like `$WORKSPACE`.

**Solution:** Escape bash variables with `$$`:

- `$WORKSPACE` → `$$WORKSPACE` (becomes `$WORKSPACE` in output)
- `$workspace` → stays as `$workspace` (substituted by Python)

**Implementation:**

```bash
sed -i 's/"\$WORKSPACE"/"$$WORKSPACE"/g' scylla/e2e/templates/*.template
```

### Challenge 2: Shellcheck False Positives

**Problem:** Shellcheck reports errors on template syntax:

- SC2034: WORKSPACE appears unused (because it's a Python variable)
- SC2154: workspace referenced but not assigned (template variable)
- SC1036/SC1088: $$ escaping syntax not recognized

**Solution:** Created `.shellcheckrc` to globally disable these checks for template files. Documented why each check is disabled.

### Challenge 3: Path Type Conversion

**Problem:** `string.Template.substitute()` only accepts strings, but we pass `Path` objects.

**Solution:** Always convert to string: `workspace=str(workspace)`

## Testing Results

### Unit Tests

```bash
pixi run python -m pytest tests/e2e/test_template_loader.py -v
# Result: 32 passed in 0.17s
```

### Integration Tests

```bash
pixi run python -m pytest tests/unit/e2e/ -v --no-cov
# Result: 463 passed in 8.96s
```

### Shellcheck Validation

```bash
pre-commit run shellcheck --files scylla/e2e/templates/*.sh.template
# Result: Passed
```

### Pre-commit Hooks

All hooks passed:

- Check for shell=True (Security)
- Ruff Format Python
- Ruff Check Python
- Mypy Type Check Python
- YAML Lint
- ShellCheck
- Trailing Whitespace
- End of Files
- Large Files
- Mixed Line Endings

## Code Metrics

- **Files created:** 18 (13 templates + 1 loader + 1 test + 2 config + 1 prompt)
- **Lines added:** 424
- **Lines deleted:** 226
- **Net change:** +198 lines (infrastructure investment)
- **Functions simplified:** 7 functions (from ~30 lines each to ~5 lines each)
- **Code reduction in llm_judge.py:** ~175 lines removed

## Benefits Achieved

1. **Validation:** Scripts can now be validated with shellcheck in CI
2. **Maintainability:** Scripts easier to review and modify independently
3. **Syntax Highlighting:** Proper shell script highlighting in editors
4. **Reusability:** Script fragments can be shared across contexts
5. **Separation:** Script logic separate from Python code
6. **No Dependencies:** Used built-in `string.Template` instead of Jinja2

## Commit & PR

**Commit hash:** 145cb52

**Commit message:**

```
refactor(e2e): Parameterize script templates for maintainability

Migrate bash script generation from f-string interpolation to template
files with parameter substitution. This improves maintainability, enables
shellcheck validation in CI, provides syntax highlighting, and makes
scripts easier to review and modify independently of Python code.

Changes:
- Extract 13 bash script templates to scylla/e2e/templates/
- Create template_loader.py using Python's built-in string.Template
- Update all 7 script generation functions in llm_judge.py
- Add shellcheck to pre-commit config for template validation
- Create comprehensive test suite for template loading
- Add .shellcheckrc to handle template-specific patterns

Benefits:
- Scripts can be validated with shellcheck in CI
- Syntax highlighting in editors for shell scripts
- Easier to reuse script fragments across contexts
- Changes don't require modifying Python code
- Centralized script management in templates directory

Closes #648
```

**PR #719:**

- Status: Open
- Auto-merge: Enabled (rebase)
- URL: <https://github.com/HomericIntelligence/ProjectScylla/pull/719>

## Lessons Learned

1. **Always audit dollar signs** when migrating to `string.Template` - both Python variables (`$var`) and bash variables (`$$var`) need correct escaping

2. **Linter false positives are expected** for template files - create configuration to suppress them with clear documentation

3. **Type conversion matters** - `string.Template` is strict about string types, convert `Path` objects explicitly

4. **Test exhaustively** - parametrized tests for all templates caught the escaping issues early

5. **Batch operations are efficient** - using `sed` to fix escaping across all templates saved time

6. **Built-in tools often sufficient** - `string.Template` was simpler than Jinja2 for this use case

## Related Team Knowledge

Referenced these patterns:

- `dry-consolidation-workflow` - Extract → Verify → Delete pattern
- `centralized-path-constants` - Single source of truth principle
- `shared-fixture-migration` - Similar file extraction approach
- `refactor-for-extensibility` - Optional parameters with smart defaults

## Follow-up Considerations

Potential future improvements:

1. Add template inheritance/composition for shared fragments
2. Consider template validation in CI (syntax check before runtime)
3. Document template variable schema (what variables each template expects)
4. Add template versioning if script formats evolve
