---
name: extend-workflow-smoke-tests
description: 'Extend an existing workflow-smoke-test CI workflow to cover additional
  GitHub Actions workflows. Use when: (1) smoke tests exist for one workflow and need
  expansion, (2) pre-commit/test-matrix/config-validation workflows need regression
  protection, (3) a second CI job should verify properties of multiple workflow files.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Extend Workflow Smoke Tests

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Extend `workflow-smoke-test.yml` to protect `pre-commit.yml`, `comprehensive-tests.yml`, and `validate-configs.yml` |
| Outcome | Operational — applied in ProjectOdyssey PR #4838 (issue #3948) |

The original `workflow-smoke-tests` skill covers creating smoke tests for a *single* workflow
(typically `security.yml`). This skill covers the follow-up: extending that CI gate to protect
additional critical workflows, each with their own test class and fast-fail grep checks.

## When to Use

- An existing `workflow-smoke-test.yml` only covers one workflow file and more need protection
- `pre-commit.yml` properties need regression protection (trigger, advisory flags, enforcement steps)
- `comprehensive-tests.yml` matrix coverage needs a guard (fail-fast, test groups, job dependencies)
- `validate-configs.yml` validation steps need a guard (trigger, yamllint, required file checks)
- A second CI job (`smoke-test-other-workflows`) should run fast-fail grep checks + pytest

## Verified Workflow

### Quick Reference

| Workflow | Key Properties to Test |
|----------|------------------------|
| `pre-commit.yml` | `pull_request` trigger, mojo-format `continue-on-error: true`, `SKIP=mojo-format`, `__matmul__` enforcement is blocking (no `continue-on-error`) |
| `comprehensive-tests.yml` | `pull_request` trigger, `fail-fast: false`, Core Tensors/Core Gradient/Models groups present, `test-mojo-comprehensive` needs `mojo-compilation` + `validate-test-coverage` |
| `validate-configs.yml` | `pull_request` trigger, `yamllint` present, required defaults check present |

### Step 1: Read each target workflow before writing tests

Read the actual workflow files first to understand exactly what properties are present and
what names/patterns are used:

```bash
cat .github/workflows/pre-commit.yml
cat .github/workflows/comprehensive-tests.yml
cat .github/workflows/validate-configs.yml
```

This prevents writing tests that immediately fail due to mismatched step names or patterns.

### Step 2: Create one test file per workflow

Follow the existing `test_security_workflow_properties.py` pattern exactly:

```python
#!/usr/bin/env python3
"""Smoke tests for <workflow> properties.

Validates that .github/workflows/<workflow>.yml has correct trigger coverage and
<key properties>, preventing regression of:
  1. pull_request trigger is present
  2. <property 2>
  3. <property 3>
"""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "<workflow>.yml"


@pytest.fixture(scope="module")
def workflow_content() -> str:
    """Read the workflow file once for all tests in this module."""
    assert WORKFLOW.exists(), f"<workflow>.yml not found at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


class TestTriggers:
    def test_pull_request_trigger_present(self, workflow_content: str) -> None:
        """<workflow>.yml must trigger on pull_request events."""
        assert re.search(r"^\s+pull_request\b", workflow_content, re.MULTILINE), (
            "<workflow>.yml is missing a pull_request trigger."
        )
```

Group tests by concern (triggers, specific steps, job dependencies). Use `re.DOTALL` when
extracting multi-line step blocks.

### Step 3: Write meaningful assertion messages

Each assertion message should explain:
1. What is missing/wrong
2. **Why it matters** (what breaks without it)
3. How to fix it

```python
assert re.search(r"fail-fast:\s*false", workflow_content), (
    "comprehensive-tests.yml is missing 'fail-fast: false' in the matrix strategy. "
    "Without this, a single failing test group will cancel all other groups, "
    "hiding which tests pass and making failures harder to diagnose."
)
```

### Step 4: For multi-line step blocks, use DOTALL with a step boundary lookahead

```python
step_pattern = re.compile(
    r"-\s+name:\s+<Step Name>.*?(?=\n\s*-\s+name:|\Z)",
    re.DOTALL,
)
match = step_pattern.search(workflow_content)
assert match is not None, "Could not find '<Step Name>' step"
step_block = match.group(0)
assert "continue-on-error: true" in step_block, "..."
```

This correctly scopes assertions to the target step, not the whole file.

### Step 5: Extend workflow-smoke-test.yml paths: trigger

Add all new workflow and test files to the `paths:` filter under the `push:` trigger:

```yaml
on:
  pull_request:
  push:
    branches:
      - main
    paths:
      - '.github/workflows/security.yml'
      - 'tests/smoke/test_security_workflow_properties.py'
      - '.github/workflows/pre-commit.yml'              # NEW
      - 'tests/smoke/test_pre_commit_workflow_properties.py'  # NEW
      - '.github/workflows/comprehensive-tests.yml'     # NEW
      - 'tests/smoke/test_comprehensive_tests_workflow_properties.py'  # NEW
      - '.github/workflows/validate-configs.yml'        # NEW
      - 'tests/smoke/test_validate_configs_workflow_properties.py'    # NEW
  workflow_dispatch:
```

### Step 6: Add a second CI job with fast-fail grep checks + pytest

Add `smoke-test-other-workflows` as a separate job (not combined with the security job)
so failures are isolated and diagnosable:

```yaml
  smoke-test-other-workflows:
    name: Other Workflow Property Checks
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout code
        uses: actions/checkout@<pinned-sha>

      # Fast grep checks BEFORE pixi setup (fail in 30s instead of 3 min)
      - name: Check pre-commit pull_request trigger present
        run: |
          if ! grep -qP '^\s+pull_request\b' .github/workflows/pre-commit.yml; then
            echo "ERROR: pre-commit.yml is missing pull_request trigger"
            exit 1
          fi
          echo "OK: pull_request trigger present in pre-commit.yml"

      - name: Check comprehensive-tests fail-fast is false
        run: |
          if ! grep -q 'fail-fast: false' .github/workflows/comprehensive-tests.yml; then
            echo "ERROR: comprehensive-tests.yml is missing fail-fast: false"
            exit 1
          fi
          echo "OK: fail-fast: false present in comprehensive-tests.yml"

      - name: Check validate-configs uses yamllint
        run: |
          if ! grep -q 'yamllint' .github/workflows/validate-configs.yml; then
            echo "ERROR: validate-configs.yml does not use yamllint"
            exit 1
          fi
          echo "OK: yamllint present in validate-configs.yml"

      # Full pytest run for comprehensive assertions
      - name: Set up Pixi
        uses: ./.github/actions/setup-pixi

      - name: Run other workflow smoke tests
        run: |
          pixi run python -m pytest \
            tests/smoke/test_pre_commit_workflow_properties.py \
            tests/smoke/test_comprehensive_tests_workflow_properties.py \
            tests/smoke/test_validate_configs_workflow_properties.py \
            -v
```

### Step 7: Run tests locally before committing

```bash
pixi run python -m pytest tests/smoke/ -v
```

All tests should pass before committing. The full suite runs in under 1 second.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Writing tests without reading the workflow first | Assumed step names from memory | Step was named "Run mojo format (advisory - non-blocking)" not "Run mojo format" — regex didn't match | Always read the actual workflow file before writing tests; don't assume names |
| Single combined CI job for all workflows | Considered merging security and other checks into one job | Would make it harder to diagnose which workflow has a regression when the job fails | Keep separate jobs per concern area: `smoke-test-security-workflows` + `smoke-test-other-workflows` |
| Testing `continue-on-error` absence on `__matmul__` step globally | Checked the whole file for `continue-on-error: true` absence | The mojo-format step legitimately has `continue-on-error: true`, so the global check would always fail | Scope `continue-on-error` assertions to the specific step block using DOTALL regex |

## Results & Parameters

Applied to ProjectOdyssey issue #3948, PR #4838:

- `tests/smoke/test_pre_commit_workflow_properties.py`: 6 assertions in 3 test classes
- `tests/smoke/test_comprehensive_tests_workflow_properties.py`: 8 assertions in 3 test classes
- `tests/smoke/test_validate_configs_workflow_properties.py`: 4 assertions in 2 test classes
- `.github/workflows/workflow-smoke-test.yml`: 8 new path entries + new `smoke-test-other-workflows` job
- All 26 smoke tests pass in ~0.08s total

**Test run command**:

```bash
pixi run python -m pytest tests/smoke/ -v
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4838, issue #3948, follow-up to #3318 | [notes.md](../references/notes.md) |
