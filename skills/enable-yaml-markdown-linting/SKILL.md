# Enable YAML and Markdown Linting in Pre-commit

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-14 |
| **Objective** | Enable yamllint and markdownlint-cli2 pre-commit hooks with proper configuration for GitHub Actions workflows |
| **Outcome** | ✅ Success - Both linters enabled and passing on all files |
| **Issue** | #603 |
| **PR** | #653 |

## Overview

Enable YAML and Markdown linting in pre-commit hooks while handling GitHub Actions-specific syntax requirements and maintaining compatibility with existing test fixtures.

## When to Use This Skill

Use this skill when you need to:

- Enable yamllint in a repository with GitHub Actions workflows
- Configure yamllint for projects with flexible YAML formatting needs
- Set up YAML linting that works with intentionally invalid test fixtures
- Enable markdown linting alongside YAML linting in pre-commit hooks
- Troubleshoot yamllint failures related to GitHub Actions syntax

**Trigger phrases**:

- "Enable YAML linting"
- "Add yamllint to pre-commit"
- "Configure yamllint for GitHub Actions"
- "Fix yamllint errors in workflows"

## Verified Workflow

### 1. Add yamllint dependency

```bash
# Add to pixi.toml [feature.dev.dependencies]
yamllint = ">=1.35.0"

# Install
pixi install
```

### 2. Create .yamllint.yaml configuration

**Key configuration choices**:

```yaml
---
extends: default

rules:
  line-length:
    max: 120
    level: warning  # Don't fail on long lines
  indentation:
    spaces: 2
    indent-sequences: whatever  # CRITICAL: Allows flexible list indentation
  comments:
    min-spaces-from-content: 1
  comments-indentation: {}
  truthy:
    allowed-values: ['true', 'false', 'yes', 'no', 'on', 'off']  # CRITICAL: GitHub Actions needs 'on'/'off'
  document-start: disable  # Don't require --- at start
  braces:
    max-spaces-inside: 1  # CRITICAL: GitHub Actions uses spaces in ${{ }}

ignore: |
  .pixi/
  build/
  .git/
  node_modules/
  tests/fixtures/invalid/  # Exclude intentionally broken test files
```

**Why these settings matter**:

- `indent-sequences: whatever` - Prevents 30+ errors in files with flexible list indentation
- `truthy: ['on', 'off']` - GitHub Actions workflows use `on:` as trigger keyword
- `braces: max-spaces-inside: 1` - Allows `${{ expression }}` syntax in GitHub Actions
- `tests/fixtures/invalid/` exclusion - Allows testing with intentionally broken YAML

### 3. Enable pre-commit hook

In `.pre-commit-config.yaml`:

```yaml
  # YAML linting
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.1
    hooks:
      - id: yamllint
        name: YAML Lint
        description: Lint YAML files for syntax and style
        args: ['--config-file', '.yamllint.yaml']
        exclude: ^(\.pixi|build)/
```

**Note**: Do NOT use `--strict` flag - it prevents warnings from being warnings.

### 4. Test and verify

```bash
# Test manually first
pixi run yamllint --config-file .yamllint.yaml .

# Test via pre-commit
pre-commit run yamllint --all-files

# Run all hooks
pre-commit run --all-files
```

## Failed Attempts

### ❌ Attempt 1: Strict sequence indentation

**What we tried**:

```yaml
indentation:
  spaces: 2
  indent-sequences: true  # Too strict
```

**Why it failed**:

- Generated 30+ errors in test YAML files with patterns like:

  ```yaml
  resources:
    agents:
      levels:
      - 3  # yamllint expected 6 spaces, got 4
  ```

- The strict rule expects sequence items to be indented relative to their parent key
- Many existing files use a more compact style

**Lesson**: Use `indent-sequences: whatever` for flexibility unless strict alignment is a project requirement.

### ❌ Attempt 2: Default truthy values

**What we tried**:

```yaml
truthy:
  allowed-values: ['true', 'false', 'yes', 'no']  # Missing 'on'/'off'
```

**Why it failed**:

- GitHub Actions workflows use `on:` as a trigger keyword:

  ```yaml
  on:  # yamllint error: truthy value should be one of [false, no, true, yes]
    push:
      branches: [main]
  ```

- The word "on" is interpreted as a boolean by YAML parsers
- GitHub Actions specifically chose this keyword despite the YAML ambiguity

**Lesson**: Always include `'on'` and `'off'` in truthy allowed values for repositories with GitHub Actions.

### ❌ Attempt 3: Default braces spacing

**What we tried**:

```yaml
# Using default braces rule (max-spaces-inside: 0)
```

**Why it failed**:

- GitHub Actions uses `${{ expression }}` syntax with spaces:

  ```yaml
  if: ${{ github.event_name == 'push' }}  # yamllint: too many spaces inside braces
  ```

- The default rule expects `${{expression}}` with no spaces
- GitHub Actions documentation consistently shows spaces in examples

**Lesson**: Set `braces: max-spaces-inside: 1` to allow GitHub Actions expression syntax.

## Results & Validation

### Final Configuration (.yamllint.yaml)

Copy-paste ready configuration:

```yaml
---
extends: default

rules:
  line-length:
    max: 120
    level: warning
  indentation:
    spaces: 2
    indent-sequences: whatever
  comments:
    min-spaces-from-content: 1
  comments-indentation: {}
  truthy:
    allowed-values: ['true', 'false', 'yes', 'no', 'on', 'off']
  document-start: disable
  braces:
    max-spaces-inside: 1

ignore: |
  .pixi/
  build/
  .git/
  node_modules/
  tests/fixtures/invalid/
```

### Validation Results

```bash
$ pre-commit run --all-files
YAML Lint................................................................Passed
Markdown Lint............................................................Passed
# All other hooks also passed
```

**Remaining warnings** (acceptable):

- 2 line-length warnings in test fixture rubric files (228 characters)
- These are warnings only and don't block commits

### Pre-commit Hook Integration

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/adrienverge/yamllint
  rev: v1.35.1
  hooks:
    - id: yamllint
      name: YAML Lint
      description: Lint YAML files for syntax and style
      args: ['--config-file', '.yamllint.yaml']
      exclude: ^(\.pixi|build)/
```

## Impact

- ✅ Enforces YAML quality standards without breaking existing workflows
- ✅ Compatible with GitHub Actions syntax requirements
- ✅ Allows intentionally invalid test fixtures
- ✅ Auto-runs on every commit via pre-commit hooks
- ✅ Zero errors, minimal warnings (2 acceptable long-line warnings)

## Related Skills

- `quality-run-linters` - Complete linting workflow including markdownlint
- `run-precommit` - Pre-commit hook best practices
- `validate-workflow` - GitHub Actions workflow validation

## References

- yamllint documentation: <https://yamllint.readthedocs.io/>
- GitHub Actions syntax: <https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions>
- Pre-commit hooks: <https://pre-commit.com/>
