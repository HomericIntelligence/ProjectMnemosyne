# Session Notes: Extend Workflow Smoke Tests

## Context

- **Project**: ProjectOdyssey
- **Issue**: #3948 — "Extend workflow-smoke-test.yml to cover other critical workflows"
- **PR**: #4838
- **Follow-up from**: Issue #3318 / PR #3945 (original workflow-smoke-tests skill)
- **Date**: 2026-03-15

## Objective

The existing `workflow-smoke-test.yml` only validated `security.yml`. Issue #3948 requested
regression protection for three additional workflows:

- `pre-commit.yml` — should trigger on `pull_request`
- `comprehensive-tests.yml` — matrix coverage of all test groups
- `validate-configs.yml` — agent config validation on all PRs

## Files Created/Modified

### New files

- `tests/smoke/test_pre_commit_workflow_properties.py`
- `tests/smoke/test_comprehensive_tests_workflow_properties.py`
- `tests/smoke/test_validate_configs_workflow_properties.py`

### Modified files

- `.github/workflows/workflow-smoke-test.yml` — 8 new `paths:` entries + `smoke-test-other-workflows` job

## Key Properties Tested

### pre-commit.yml

1. `pull_request` trigger present
2. `push` trigger present
3. "Run mojo format" step has `continue-on-error: true` (advisory due to Mojo 0.26.1 bugs)
4. Main hook run uses `SKIP=mojo-format`
5. `__matmul__` enforcement step present
6. `__matmul__` enforcement step does NOT have `continue-on-error: true`

### comprehensive-tests.yml

1. `pull_request` trigger present
2. `push` trigger present
3. `fail-fast: false` in matrix strategy
4. "Core Tensors" test group in matrix
5. "Core Gradient" test group in matrix
6. "Models" test group in matrix
7. `test-mojo-comprehensive` depends on `mojo-compilation`
8. `test-mojo-comprehensive` depends on `validate-test-coverage`

### validate-configs.yml

1. `pull_request` trigger present
2. `push` trigger present
3. `yamllint` present
4. `configs/defaults/training.yaml` check present

## Test Results

All 26 smoke tests pass in ~0.08s:

```
26 passed in 0.08s
```

## Implementation Notes

### Scoping step block assertions with DOTALL

When checking properties of a specific step (e.g., does "Run mojo format" have
`continue-on-error: true`?), use:

```python
step_pattern = re.compile(
    r"-\s+name:\s+Run mojo format.*?(?=\n\s*-\s+name:|\Z)",
    re.DOTALL,
)
match = step_pattern.search(content)
assert match is not None
block = match.group(0)
assert "continue-on-error: true" in block
```

The `(?=\n\s*-\s+name:|\Z)` lookahead stops at the next step header, scoping the
assertion to just the target step.

### Job dependency assertions for matrix jobs

```python
job_pattern = re.compile(
    r"test-mojo-comprehensive:.*?(?=\n\w|\Z)",
    re.DOTALL,
)
job_match = job_pattern.search(content)
job_block = job_match.group(0)
assert "mojo-compilation" in job_block
```

### CI job design: fast grep before heavy setup

The `smoke-test-other-workflows` CI job structure mirrors the security job:
1. Checkout (fast)
2. `grep` checks (fail in ~5s if wrong)
3. `setup-pixi` (heavy, ~2-3 min)
4. `pytest` (comprehensive)

This ensures regressions are caught quickly without waiting for pixi to set up.
