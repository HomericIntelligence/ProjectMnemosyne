---
name: quality-run-linters
description: "Run all configured linters including ruff and mypy. Use before committing code to ensure quality standards are met."
category: quality
user-invocable: false
---

# Run Linters Skill

Run all configured linters to ensure code quality.

## When to Use

- Before committing code
- CI/CD quality checks
- Pre-PR validation

### Quick Reference

```bash
# Run Python linter
pixi run lint

# Run type checker
pixi run typecheck

# Run all checks
pixi run lint && pixi run typecheck
```

## Configured Linters

| Linter | Purpose | Auto-Fix |
|--------|---------|----------|
| `ruff` | Python linting and formatting | Yes (`ruff format`, `ruff check --fix`) |
| `mypy` | Python type checking | No |

## Workflow

```bash
# 1. Run linters
pixi run lint

# 2. Fix auto-fixable issues
ruff check --fix .
ruff format .

# 3. Stage changes
git add .

# 4. Commit
git commit -m "fix: address linting issues"
```

## Common Issues

| Error | Linter | Fix |
|-------|--------|-----|
| Import sorting | ruff | `ruff check --fix --select I .` |
| Unused import | ruff | Remove the import |
| Type error | mypy | Add/fix type annotations |
| Formatting | ruff | `ruff format .` |

## References

- Related skill: `run-precommit` for pre-commit hooks
