---
name: enable-yaml-markdown-linting
description: Enable yamllint and markdownlint-cli2 pre-commit hooks with proper configuration
  for GitHub Actions and documentation quality
category: ci-cd
date: 2026-02-14
version: 1.0.0
user-invocable: false
---
# Enable YAML and Markdown Linting in Pre-commit

| Aspect | Details |
| -------- | --------- |
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

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
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
