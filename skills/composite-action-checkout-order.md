---
name: composite-action-checkout-order
description: 'Enforce that actions/checkout precedes ./.github/actions/ references
  in every GitHub Actions job. Use when: adding checkout-order validation CI, auditing
  workflows for composite action ordering bugs, or documenting the checkout-first
  invariant.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Local composite actions (`uses: ./.github/actions/X`) are resolved from disk. If `actions/checkout` has not yet run in a job, GitHub cannot find the action and fails with `Cannot find action`. |
| **Solution** | A Python script that parses workflow YAML files and reports any job where a `./.github/actions/` step appears before (or without) `actions/checkout`. A CI workflow runs this check on every PR touching `.github/`. |
| **Scope** | GitHub Actions YAML workflows; Python 3.7+; `pyyaml` |
| **Issue** | #3346 (follow-up from #3149) |

## When to Use

- Adding a new CI check that enforces workflow structural invariants
- Auditing existing workflows to verify composite actions are not referenced before checkout
- Documenting the checkout-first rule so future contributors understand the constraint
- Any project that uses local composite actions (`uses: ./.github/actions/`)

## Verified Workflow

### 1. Create the validation script (`scripts/validate_workflow_checkout_order.py`)

Key design decisions:

- Parse each job's `steps` list in order, tracking a `checked_out` boolean
- `actions/checkout` (any version or pinned SHA) sets `checked_out = True`
- Any `uses: ./.github/actions/` step before `checked_out` is a `Violation`
- Return a typed `NamedTuple` (`Violation`) for easy testing
- Accept file paths or directories; deduplicate; skip files > 1 MB
- Exit 0 on clean, exit 1 on violations

```python
class Violation(NamedTuple):
    workflow_file: Path
    job_name: str
    step_index: int
    step_name: str
    composite_action: str

def _is_checkout_step(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    uses = step.get("uses", "")
    return isinstance(uses, str) and uses.startswith("actions/checkout")

def _is_composite_action_step(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    uses = step.get("uses", "")
    return isinstance(uses, str) and uses.startswith("./.github/actions/")
```

### 2. Create the CI workflow (`.github/workflows/validate-workflows.yml`)

```yaml
name: Validate Workflow Checkout Order

on:
  push:
    branches: [main]
    paths:
      - '.github/**'
      - 'scripts/validate_workflow_checkout_order.py'
  pull_request:
    branches: [main]
    paths:
      - '.github/**'
      - 'scripts/validate_workflow_checkout_order.py'
  workflow_dispatch:

jobs:
  validate-checkout-order:
    name: Enforce Composite Action Checkout-First Ordering
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install PyYAML
        run: pip install pyyaml

      - name: Validate checkout-first ordering for composite actions
        run: python3 scripts/validate_workflow_checkout_order.py .github/workflows/
```

### 3. Document the invariant in `.github/workflows/README.md`

Add a "Composite Action Checkout Invariant" section under Common Patterns with:

- Why the rule exists (composite actions read from disk, require prior checkout)
- Correct and incorrect YAML examples
- Local run command: `python3 scripts/validate_workflow_checkout_order.py .github/workflows/`
- Reference to the CI workflow

### 4. Write tests (`tests/scripts/test_validate_workflow_checkout_order.py`)

Use `pytest` with `tmp_path` fixtures to write inline YAML and assert violations:

```python
def write_workflow(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(textwrap.dedent(content))
    return f

# Violation detected
def test_composite_before_checkout(tmp_path):
    wf = write_workflow(tmp_path, "bad.yml", """
        jobs:
          build:
            steps:
              - name: Setup pixi
                uses: ./.github/actions/setup-pixi
              - uses: actions/checkout@v4
    """)
    violations = validate_workflow(wf)
    assert len(violations) == 1
    assert violations[0].job_name == "build"

# Integration test against real workflows
def test_main_real_workflows():
    repo_root = Path(__file__).resolve().parent.parent.parent
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        pytest.skip(".github/workflows not found")
    result = main([str(workflows_dir)])
    assert result == 0
```

22 tests total: 7 clean paths, 5 violation paths, 5 collection helpers, 5 `main()` integration.

### 5. Run pre-commit — ruff auto-fixes

Ruff reformatted a long inline ternary in the violation-recording block. Re-stage and re-run hooks:

```bash
git add <files>
pixi run pre-commit run --files <files>
# All pass on second run
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| First pre-commit run | Committed with long inline ternary expression | Ruff auto-reformatted it (line too long) | Stage → pre-commit → if hooks auto-fix files, re-stage → re-run → then commit |
| pixi-based test run (background) | `pixi run python -m pytest ...` in background task | Took >2 min to resolve pixi environment; TaskOutput timed out | Use `python -m pytest` directly (pixi env already active) for faster feedback |

## Results & Parameters

### Script parameters

```bash
# Default: scans .github/workflows/ relative to repo root
python3 scripts/validate_workflow_checkout_order.py

# Explicit directory
python3 scripts/validate_workflow_checkout_order.py .github/workflows/

# Explicit files
python3 scripts/validate_workflow_checkout_order.py .github/workflows/benchmark.yml .github/workflows/coverage.yml
```

### Exit codes

| Code | Meaning |
| ------ | --------- |
| 0 | All workflows pass; no violations |
| 1 | One or more violations found |

### Error output format

```
ERROR: .github/workflows/bad.yml :: job 'build' :: step 1 uses './.github/actions/setup-pixi'
       but actions/checkout is not a preceding step.
       Composite actions require the repository to be checked out first.

Found 1 violation(s) in 5 file(s).
```

### Test run

```
22 passed in 1.52s
```
