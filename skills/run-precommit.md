---
name: run-precommit
description: Run pre-commit hooks locally to validate code quality before committing
category: ci-cd
date: 2025-12-30
version: 1.0.0
---
# Run Pre-commit Hooks

Validate code quality with pre-commit hooks before committing.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Catch issues before CI | Faster feedback, fewer CI failures |

## When to Use

- (1) Before committing code
- (2) Testing if CI will pass
- (3) After making code changes
- (4) Troubleshooting commit failures

## Verified Workflow

1. **Install hooks** (one-time): `pre-commit install`
2. **Make changes**: Edit code files
3. **Run hooks**: `pre-commit run --all-files`
4. **Stage fixes**: If hooks auto-fixed files, stage them
5. **Commit**: Create commit with all fixes applied

## Results

Copy-paste ready commands:

```bash
# Install pre-commit hooks (one-time)
pip install pre-commit
pre-commit install

# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run trailing-whitespace --all-files

# Update hook versions
pre-commit autoupdate

# Skip specific hook if broken (document reason)
SKIP=hook-name git commit -m "message"
```

### Common Hooks

| Hook | Purpose | Auto-Fix |
|------|---------|----------|
| `trailing-whitespace` | Remove trailing spaces | Yes |
| `end-of-file-fixer` | Add final newline | Yes |
| `check-yaml` | Validate YAML syntax | No |
| `check-added-large-files` | Prevent large files | No |
| `mixed-line-ending` | Fix line endings | Yes |

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Error Handling

| Error | Solution |
|-------|----------|
| Hooks not installed | Run `pre-commit install` |
| Hooks not running | Verify `.pre-commit-config.yaml` exists |
| All files modified after hook | Stage fixes and re-commit |
| Specific hook broken | Use `SKIP=hook-id git commit` (document why) |

## Hook Bypass Policy

**STRICT: `--no-verify` is PROHIBITED.**

If hooks fail:
1. Read the error - Hook output explains what's wrong
2. Fix your code - Update to pass the check
3. Re-run hooks - Verify with `pre-commit run`
4. Commit again - Let hooks validate

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Pre-commit validation workflow | Generic patterns applicable to any project |

## References

- Pre-commit docs: https://pre-commit.com/
- See validate-workflow for workflow validation
- See fix-ci-failures for debugging CI
