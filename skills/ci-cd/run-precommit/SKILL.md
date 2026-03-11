---
name: run-precommit
description: "Run pre-commit hooks locally to validate code quality before committing. Use to ensure commits meet quality standards."
category: ci
user-invocable: false
---

# Run Pre-commit Hooks Skill

Validate code quality with pre-commit hooks before committing.

## When to Use

- Before committing code
- Testing if CI will pass
- Troubleshooting commit failures

## Quick Reference

```bash
# Run on all files
pixi run pre-commit run --all-files

# Run on staged files
pixi run pre-commit run

# NEVER use --no-verify to bypass hooks
```

## Configured Hooks

| Hook | Purpose | Auto-Fix |
|------|---------|----------|
| `ruff` | Python linting/formatting | Yes |
| `trailing-whitespace` | Remove trailing spaces | Yes |
| `end-of-file-fixer` | Add final newline | Yes |
| `check-yaml` | Validate YAML syntax | No |
| `check-added-large-files` | Prevent large files | No |

## Hook Bypass Policy

**STRICT POLICY: `--no-verify` is PROHIBITED.**

**What to do when hooks fail:**

1. **Read the error** - Hook output explains what's wrong
2. **Fix your code** - Update to pass the check
3. **Re-run hooks** - Verify the fix
4. **Commit again** - Let hooks validate

**Exception for broken hooks:**

```bash
SKIP=hook-id git commit -m "fix: skip broken hook (see issue #123)"
```

## References

- [Git Commit Policy](../../shared/git-commit-policy.md)
- Related skill: `quality-run-linters`
