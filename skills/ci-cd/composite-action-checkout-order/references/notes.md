# Session Notes: composite-action-checkout-order

## Context

- **Repo**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3346 (follow-up from #3149)
- **Branch**: 3346-auto-impl
- **PR**: #3983
- **Date**: 2026-03-07

## Problem Statement

Local composite actions (`uses: ./.github/actions/X`) are resolved from the repository on disk.
GitHub Actions reads the composite action YAML directly from the cloned workspace. If
`actions/checkout` has not run yet, the workspace is empty and the runner fails with:

```
Cannot find action './.github/actions/setup-pixi'
```

All existing workflows already had checkout first, but there was no enforcement mechanism
to prevent future regressions.

## Files Created

| File | Purpose |
|------|---------|
| `scripts/validate_workflow_checkout_order.py` | Python script: scans workflow YAML, reports violations |
| `.github/workflows/validate-workflows.yml` | CI workflow: runs script on PRs touching `.github/**` |
| `.github/workflows/README.md` (modified) | Added "Composite Action Checkout Invariant" section |
| `tests/scripts/test_validate_workflow_checkout_order.py` | 22 pytest tests |

## Implementation Details

### Core logic

```python
checked_out = False
for idx, step in enumerate(steps):
    if _is_checkout_step(step):
        checked_out = True
        continue
    if _is_composite_action_step(step):
        if not checked_out:
            violations.append(Violation(...))
```

### Checkout detection

Covers any form: `actions/checkout@v4`, `actions/checkout@v3`, pinned SHAs like
`actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8`.

### Test coverage

- 7 clean workflows (checkout before composite, no composite, pinned hash, multi-job, empty jobs, non-workflow YAML, composite at end)
- 5 violation cases (before checkout, no checkout, multiple violations, one bad job, step name captured)
- 5 collection helpers (directory globbing, YAML extension, explicit file, deduplication, missing path warning)
- 5 main() integration tests (clean dir, violation dir, no files, real workflows, multiple paths)

## Pitfalls

1. **pixi background tasks are slow**: `pixi run python -m pytest` takes >2 min to activate the environment.
   Use `python -m pytest` directly when the pixi shell is already active.

2. **Pre-commit auto-fixes require re-staging**: Ruff reformatted a long ternary on first run.
   The commit hook failed (hooks modified files), requiring re-stage + re-run before committing.

3. **Inline ternary line length**: The pattern
   `step.get("name", f"...") if isinstance(step, dict) else f"..."` exceeded ruff's line limit.
   Ruff reformatted it to a parenthesized multi-line expression automatically.
