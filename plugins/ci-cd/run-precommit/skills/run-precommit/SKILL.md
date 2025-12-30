---
name: run-precommit
description: "Run pre-commit hooks locally to validate code quality before committing"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-30
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

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `--no-verify` to skip hooks | CI still failed, wasted time | Never bypass hooks - fix the underlying issue |
| Forgot to stage auto-fixed files | Commit succeeded but files weren't included | Run `git add .` after hooks auto-fix |
| Ran hooks on unstaged files only | Missed issues in staged changes | Use `--all-files` or ensure changes are staged |
| Skipped pre-commit install on new clone | Hooks didn't run, CI failed | Always run `pre-commit install` on fresh clones |

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

## References

- Pre-commit docs: https://pre-commit.com/
- See validate-workflow for workflow validation
- See fix-ci-failures for debugging CI
