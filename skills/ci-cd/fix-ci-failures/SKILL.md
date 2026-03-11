---
name: fix-ci-failures
description: "Diagnose and fix CI/CD failures by analyzing logs, reproducing locally, and applying fixes. Use when CI checks fail on pull requests."
category: ci
---

# Fix CI Failures Skill

Diagnose and fix CI failures systematically.

## When to Use

- CI checks fail on PR
- Workflow runs fail
- Tests pass locally but fail in CI

## Quick Reference

```bash
# View PR checks
gh pr checks <pr-number>

# View specific run details
gh run view <run-id> --log-failed

# Reproduce locally
pixi run test
```

## Workflow

1. **Check status** - View failed PR checks
2. **Get logs** - Download or view failure details
3. **Reproduce** - Run same commands locally
4. **Fix issue** - Apply necessary changes
5. **Verify** - Test passes locally with `pixi run test`
6. **Push** - Commit and push fix
7. **Monitor** - Check CI passes

## Common Failures

| Failure | Command | Fix |
|---------|---------|-----|
| Test failure | `pixi run test` | Fix code, re-run tests |
| Lint error | `pixi run lint` | Fix linting issues |
| Type error | `pixi run typecheck` | Fix type annotations |
| Build error | Check imports/deps | Update pyproject.toml |

## References

- Related skill: `quality-run-linters` for linting
- Related skill: `run-precommit` for pre-commit hooks
