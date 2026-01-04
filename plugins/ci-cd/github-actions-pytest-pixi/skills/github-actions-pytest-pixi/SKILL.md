---
name: github-actions-pytest-pixi
description: GitHub Actions CI setup for pytest projects using pixi with parallel test execution
category: ci-cd
date: 2026-01-04
---

# GitHub Actions for Pytest + Pixi Projects

| Field | Value |
|-------|-------|
| **Date** | 2026-01-04 |
| **Project** | ProjectScylla |
| **Objective** | Set up automated testing in CI for pytest projects using pixi package manager |
| **Outcome** | ✅ Success - Parallel test execution with coverage reporting |
| **Impact** | High - Automated testing on every PR prevents regressions |

## When to Use This Skill

Use this skill when:

1. **Setting up CI/CD** for a Python project that uses pixi for dependency management
2. **Adding automated testing** to an existing repository with pytest
3. **Need parallel test execution** to reduce CI runtime
4. **Want coverage reporting** integrated into CI workflow
5. **Migrating from manual testing** to automated CI
6. **Following `/advise` recommendations** for CI/CD test setup

**Key Indicator**: Project has `pixi.toml` with pytest configured, needs GitHub Actions workflows.

## Verified Workflow

### 1. Create Test Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test

on:
  pull_request:
    paths:
      - '**/*.py'
      - 'pyproject.toml'
      - 'pixi.toml'
      - '.github/workflows/test.yml'
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    strategy:
      fail-fast: false
      matrix:
        test-group:
          - { name: "unit", path: "tests/unit" }
          - { name: "integration", path: "tests/integration" }

    steps:
      - uses: actions/checkout@v4

      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.8.1
        with:
          pixi-version: v0.39.5
          cache: true

      - name: Run ${{ matrix.test-group.name }} tests
        run: |
          pixi run pytest ${{ matrix.test-group.path }} -v --cov=<package> --cov-report=term-missing --cov-report=xml

      - name: Upload coverage
        if: matrix.test-group.name == 'unit'
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: ${{ matrix.test-group.name }}
```

**Key Features**:
- ✅ **Path filtering** - only runs when Python code changes
- ✅ **Matrix strategy** - parallel execution for unit/integration tests
- ✅ **Pixi caching** - speeds up subsequent runs
- ✅ **Coverage reporting** - uploads to Codecov for unit tests
- ✅ **fail-fast: false** - see all test failures, not just first
- ✅ **Timeout** - prevents stuck jobs

### 2. Create Pre-commit Workflow

**File**: `.github/workflows/pre-commit.yml`

```yaml
name: Pre-commit

on:
  pull_request:
  push:
    branches: [main]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - uses: pre-commit/action@v3.0.0
```

**Purpose**: Enforce code quality standards (formatting, linting) before merge.

### 3. Verify Locally Before Pushing

```bash
# Run tests locally first
pixi run pytest tests/unit -v
pixi run pytest tests/integration -v

# Verify pre-commit hooks pass
pre-commit run --all-files

# Commit and push
git add .github/workflows/
git commit -m "ci: add GitHub Actions workflows"
git push
```

### 4. Monitor CI Runs

```bash
# Watch current CI runs
gh run list --branch <branch-name>
gh run watch

# Check PR status
gh pr view <pr-number> --json statusCheckRollup
```

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| Single monolithic test job | 30+ minute runtime for all tests | Use matrix strategy to parallelize |
| No path filtering | Wasted CI on non-code changes (docs) | Filter on `**/*.py`, config files only |
| Missing pixi cache | Slow environment reinstall every run | Enable `cache: true` in setup-pixi |
| `fail-fast: true` | Only saw first failure, missed others | Use `fail-fast: false` to see all issues |
| No timeout | Jobs can hang indefinitely | Set `timeout-minutes: 30` |

## Results & Parameters

### Complete Test Workflow (Copy-Paste Ready)

Replace `<package>` with your Python package name:

```yaml
name: Test

on:
  pull_request:
    paths:
      - '**/*.py'
      - 'pyproject.toml'
      - 'pixi.toml'
      - '.github/workflows/test.yml'
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    strategy:
      fail-fast: false
      matrix:
        test-group:
          - { name: "unit", path: "tests/unit" }
          - { name: "integration", path: "tests/integration" }

    steps:
      - uses: actions/checkout@v4

      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.8.1
        with:
          pixi-version: v0.39.5
          cache: true

      - name: Run ${{ matrix.test-group.name }} tests
        run: |
          pixi run pytest ${{ matrix.test-group.path }} -v --cov=<package> --cov-report=term-missing --cov-report=xml

      - name: Upload coverage
        if: matrix.test-group.name == 'unit'
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: ${{ matrix.test-group.name }}
```

### Pytest Configuration (pyproject.toml)

Ensure your project has pytest configured:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --strict-markers"
```

### Pixi Configuration (pixi.toml)

```toml
[tasks]
test = "pytest"

[dependencies]
pytest = ">=7.0"
pytest-cov = ">=4.0"
```

## Workflow Behavior

### When CI Triggers

**Pull Requests**:
- ✅ Any `.py` file changes
- ✅ `pyproject.toml` or `pixi.toml` changes
- ✅ Workflow file changes
- ❌ Only markdown changes (skipped)

**Main Branch**:
- ✅ All pushes (regardless of paths)

### Parallel Execution

Jobs run concurrently:
```
unit tests (tests/unit)     ─┐
                              ├─ Both run in parallel
integration tests (tests/integration) ─┘
```

**Typical Runtime**:
- Single job: 15-20 minutes
- Parallel (2 jobs): 8-10 minutes

## Security Notes

**Safe Pattern** (used in workflow):
- Matrix values are hardcoded (`{ name: "unit", path: "tests/unit" }`)
- No untrusted user input in `run:` commands
- All variables are from GitHub's built-in matrix context

**Unsafe Pattern** (avoid):
```yaml
# NEVER use untrusted input directly in run:
run: echo "${{ github.event.issue.title }}"  # VULNERABLE
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E testing with 31 rate limit tests | [Full notes](../references/notes.md) |

## Related Skills

- `run-precommit` - Running pre-commit hooks locally
- `github-actions-mojo` - GitHub Actions for Mojo projects (similar pattern)
- `ci-failure-workflow` - Debugging CI failures
- `validate-workflow` - Validate workflow YAML syntax

## Tags

`github-actions` `pytest` `pixi` `ci-cd` `testing` `matrix` `coverage` `automation`
