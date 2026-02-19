# Template Migration Pattern: F-Strings to Template Files

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-15 |
| **Issue** | #648 |
| **Objective** | Migrate bash script generation from f-string interpolation to external template files with parameter substitution |
| **Outcome** | ✅ Success - All 7 functions migrated, 463 tests pass, shellcheck validation enabled |
| **PR** | #719 |

## When to Use This Skill

Use this pattern when you need to:

1. **Extract inline scripts to separate files** for better maintainability
2. **Enable linting/validation** of embedded code (shell, SQL, HTML, etc.)
3. **Improve syntax highlighting** and editor support for embedded languages
4. **Separate concerns** between host language logic and embedded code
5. **Reuse script fragments** across multiple contexts
6. **Version control embedded code** more effectively

**Trigger conditions:**

- Multiple functions generating similar scripts with f-strings
- Need to lint embedded shell scripts with shellcheck
- Scripts becoming complex enough to benefit from separate files
- Want syntax highlighting for embedded language

## Verified Workflow

### Phase 1: Extract Templates

1. **Create template directory structure:**

   ```bash
   mkdir -p <module>/templates/
   ```

2. **Extract each script variant to a template file:**
   - Copy the f-string content verbatim
   - Replace Python variable interpolation `{variable}` with template syntax `$variable`
   - Escape bash variables: `$VAR` → `$$VAR` (for `string.Template`)
   - Use `.template` extension for clarity

   **Example transformation:**

   ```python
   # Before (f-string)
   script = f"""#!/usr/bin/env bash
   WORKSPACE="{workspace}"
   cd "$WORKSPACE"
   python -m compileall -q .
   """

   # After (template file: python_check.sh.template)
   #!/usr/bin/env bash
   WORKSPACE="$workspace"
   cd "$$WORKSPACE"
   python -m compileall -q .
   ```

3. **Key escaping rules for `string.Template`:**
   - `$variable` → Substituted by Python
   - `$$variable` → Literal `$variable` in output
   - Bash variables must use `$$` prefix

### Phase 2: Create Template Loader

1. **Use Python's built-in `string.Template`** (no dependencies):

   ```python
   from pathlib import Path
   from string import Template

   TEMPLATE_DIR = Path(__file__).parent / "templates"

   def load_template(template_name: str) -> Template:
       template_path = TEMPLATE_DIR / template_name
       if not template_path.exists():
           raise FileNotFoundError(f"Template not found: {template_path}")
       return Template(template_path.read_text())

   def render_template(template_name: str, **kwargs: str) -> str:
       template = load_template(template_name)
       return template.substitute(**kwargs)

   def write_script(
       output_path: Path,
       template_name: str,
       executable: bool = True,
       **kwargs: str,
   ) -> Path:
       script_content = render_template(template_name, **kwargs)
       output_path.write_text(script_content)
       if executable:
           output_path.chmod(0o755)
       return output_path
   ```

2. **Type hints are critical:**
   - All parameters and returns should be type-hinted
   - Use `str` for template variables (converted via `str()` if needed)

### Phase 3: Migrate Functions

1. **Replace multi-line f-strings with template calls:**

   ```python
   # Before
   def _create_python_scripts(commands_dir: Path, workspace: Path) -> None:
       build_script = commands_dir / "python_check.sh"
       build_script.write_text(f"""...""")
       build_script.chmod(0o755)

   # After
   def _create_python_scripts(commands_dir: Path, workspace: Path) -> None:
       write_script(
           commands_dir / "python_check.sh",
           "python_check.sh.template",
           workspace=str(workspace),
       )
   ```

2. **Handle conditional templates:**

   ```python
   # Before: if/else with different f-strings
   if is_modular:
       script.write_text(f"""...""")
   else:
       script.write_text(f"""...""")

   # After: select template, then render
   template_name = (
       "mojo_build_modular.sh.template"
       if is_modular
       else "mojo_build.sh.template"
   )
   write_script(build_script, template_name, workspace=str(workspace))
   ```

3. **Convert Path objects to strings for substitution:**
   - `string.Template` only accepts strings
   - Always use `workspace=str(workspace)` not `workspace=workspace`

### Phase 4: Add Validation

1. **Add linter to pre-commit config:**

   ```yaml
   - repo: https://github.com/shellcheck-py/shellcheck-py
     rev: v0.9.0.6
     hooks:
       - id: shellcheck
         name: ShellCheck
         description: Lint shell scripts and templates
         files: \.(sh|bash|sh\.template)$
         types: [text]
   ```

2. **Create `.shellcheckrc` for template-specific exclusions:**

   ```bash
   # Disable checks for template variables (false positives)
   # SC2034: Variable appears unused (template vars)
   # SC2154: Variable referenced but not assigned ($workspace)
   # SC1036/SC1088: $$ escaping syntax
   disable=SC2034,SC2154,SC1036,SC1088
   ```

3. **Verify templates pass shellcheck:**

   ```bash
   pre-commit run shellcheck --files <templates>/*.sh.template
   ```

### Phase 5: Testing

1. **Create comprehensive test suite:**
   - Test directory structure exists
   - Test loading each template
   - Test rendering with substitution
   - Test write_script creates executable files
   - Parametrize tests for all templates
   - Verify shebangs in all templates

2. **Run existing tests to verify no regressions:**

   ```bash
   pytest tests/ -v
   ```

3. **Verify output equivalence** (optional but recommended):
   - Generate scripts with old method
   - Generate scripts with new method
   - Compare outputs are identical

## Failed Attempts & Lessons Learned

### ❌ First attempt: Forgot to escape bash variables

**What happened:**

- Created templates with `$WORKSPACE` instead of `$$WORKSPACE`
- `string.Template` tried to substitute `WORKSPACE` variable
- Got `KeyError: 'WORKSPACE'` during rendering

**Why it failed:**

- `string.Template` treats ALL `$var` as substitution targets
- Bash variables in the output script need `$$` escaping

**Solution:**

- Used `sed` to batch-update all templates: `sed -i 's/"\$WORKSPACE"/"$$WORKSPACE"/g' *.template`
- Manually fixed path concatenations: `$WORKSPACE/mojo` → `$$WORKSPACE/mojo`

**Lesson:** When migrating to `string.Template`, audit ALL dollar signs in templates.

### ⚠️ Shellcheck template validation challenges

**Challenge:**

- Shellcheck reports false positives on template syntax
- `$workspace` flagged as "referenced but not assigned"
- `$$VARIABLE` flagged as invalid syntax

**Solution:**

- Created `.shellcheckrc` to disable specific checks globally
- Documented why each check is disabled (template-specific pattern)

**Alternative considered:**

- Could use `# shellcheck disable=SC2154` inline comments
- Decided global config is cleaner for template files

## Results & Parameters

### Metrics

- **Code reduction:** 226 lines deleted, 424 lines added (net +198 for infrastructure)
- **Maintainability:** 7 functions simplified from ~30 lines each to ~5 lines each
- **Template count:** 13 bash script templates
- **Test coverage:** 32 new tests, all 463 existing tests pass
- **Validation:** 100% of templates pass shellcheck

### Files Created

```
scylla/e2e/
├── template_loader.py              # Template rendering utilities
└── templates/                      # Template directory
    ├── python_check.sh.template
    ├── python_format.sh.template
    ├── python_test.sh.template
    ├── mojo_build.sh.template
    ├── mojo_build_modular.sh.template
    ├── mojo_format.sh.template
    ├── mojo_format_modular.sh.template
    ├── mojo_format_standalone_subdir.sh.template
    ├── mojo_test.sh.template
    ├── mojo_test_modular.sh.template
    ├── precommit.sh.template
    ├── run_all_python.sh.template
    └── run_all_mojo.sh.template

tests/e2e/
└── test_template_loader.py         # Comprehensive test suite

.shellcheckrc                        # Shellcheck config for templates
.pre-commit-config.yaml              # Added shellcheck hook
```

### Key Configuration

**Template loader (`template_loader.py`):**

```python
from pathlib import Path
from string import Template

TEMPLATE_DIR = Path(__file__).parent / "templates"

def write_script(
    output_path: Path,
    template_name: str,
    executable: bool = True,
    **kwargs: str,
) -> Path:
    template = Template((TEMPLATE_DIR / template_name).read_text())
    script_content = template.substitute(**kwargs)
    output_path.write_text(script_content)
    if executable:
        output_path.chmod(0o755)
    return output_path
```

**Shellcheck config (`.shellcheckrc`):**

```bash
# Disable template-specific false positives
disable=SC2034,SC2154,SC1036,SC1088
```

**Pre-commit hook:**

```yaml
- repo: https://github.com/shellcheck-py/shellcheck-py
  rev: v0.9.0.6
  hooks:
    - id: shellcheck
      files: \.(sh|bash|sh\.template)$
      types: [text]
```

## When NOT to Use This Pattern

**Don't use this pattern if:**

1. **Scripts are trivial** (< 5 lines, no logic)
2. **Only one script exists** (no duplication to eliminate)
3. **Script changes frequently with code logic** (tight coupling is intentional)
4. **Team unfamiliar with templating** (training cost > benefit)
5. **No linting needed** (scripts are simple enough)

**Alternative approaches:**

- **Inline f-strings:** Fine for simple, one-off scripts
- **Jinja2 templates:** Better for complex conditionals/loops in templates
- **Heredocs in bash:** If generating from bash instead of Python
- **Subprocess with direct bash:** Skip intermediate script files entirely

## Related Skills

- `dry-consolidation-workflow` - Extract → Verify → Delete pattern
- `centralized-path-constants` - Single source of truth for paths
- `shared-fixture-migration` - Similar file extraction pattern
- `validate-workflow` - CI validation patterns

## References

- Issue: #648
- PR: #719
- Related: `scylla/e2e/llm_judge.py` (functions migrated)
- Pattern source: `dry-consolidation-workflow` (team knowledge)
