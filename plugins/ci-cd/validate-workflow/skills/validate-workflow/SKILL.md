---
name: validate-workflow
description: "Validate GitHub Actions workflow files for syntax and correctness"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-30
---

# Validate GitHub Actions Workflows

Validate workflow files for syntax, best practices, and correctness.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Catch workflow errors before commit | Fewer CI failures, faster iteration |

## When to Use

- (1) Creating or modifying workflows
- (2) Workflow syntax errors occur
- (3) Before committing workflow changes
- (4) Debugging failing workflows

## Verified Workflow

1. **Edit workflow**: Make changes to `.github/workflows/*.yml`
2. **Validate YAML**: Run yamllint
3. **Lint with actionlint**: Check GitHub Actions specific issues
4. **Review in GitHub**: Use `gh workflow view`
5. **Commit if valid**: Proceed with changes

## Results

Copy-paste ready commands:

```bash
# List workflows
gh workflow list

# View workflow details
gh workflow view <workflow-name>

# Validate YAML syntax
yamllint .github/workflows/*.yml

# Lint with actionlint (GitHub Actions specific)
actionlint .github/workflows/*.yml

# Install actionlint
pip install actionlint
```

### Validation Workflow

```bash
# 1. Edit workflow
vim .github/workflows/test.yml

# 2. Validate YAML
yamllint .github/workflows/test.yml

# 3. Lint with actionlint
actionlint .github/workflows/test.yml

# 4. Review in GitHub
gh workflow view test.yml

# 5. Commit if valid
git add .github/workflows/test.yml
git commit -m "ci: update workflow"
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used invalid action version `@v99` | Workflow failed with "action not found" | Always verify action versions exist before using |
| Missing comma in `on: [push pull_request]` | YAML syntax error, workflow not triggered | Add commas between array elements |
| Used `${{ job.status }}` in wrong context | Context expression failed | Verify context variables are valid for that location |
| Forgot `runs-on` in job definition | Workflow failed immediately | Every job must specify `runs-on` |

## Common Issues

| Issue | Example | Fix |
|-------|---------|-----|
| Syntax error | `on: [push pull_request]` | Add comma: `on: [push, pull_request]` |
| Invalid action version | `uses: actions/checkout@v99` | Use valid version: `@v4` |
| Missing required field | Job missing `runs-on` | Add `runs-on: ubuntu-latest` |
| Invalid context | `${{ job.status }}` in wrong place | Move to correct context |

## Workflow Checklist

- [ ] Valid YAML syntax
- [ ] `on` trigger configured correctly
- [ ] All jobs have `runs-on`
- [ ] All steps have `run` or `uses`
- [ ] Action versions are specific (not @main)
- [ ] All secrets/vars available
- [ ] Timeouts set appropriately
- [ ] Permissions configured correctly

## Error Handling

| Error | Fix |
|-------|-----|
| "Invalid YAML" | Fix YAML syntax errors |
| "Unknown action" | Check action name and version |
| "Missing field" | Add required fields (run, uses, etc.) |
| "Invalid context" | Use correct context expression syntax |

## References

- GitHub Actions docs: https://docs.github.com/en/actions
- See fix-ci-failures for debugging failures
- See run-precommit for pre-commit validation
