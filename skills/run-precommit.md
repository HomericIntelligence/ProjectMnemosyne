---
name: run-precommit
description: Run pre-commit hooks locally or in CI to validate code quality before committing. Use when: (1) before committing code, (2) testing if CI will pass, (3) after making code changes, (4) troubleshooting commit failures, (5) setting up CI pre-commit checks.
category: ci-cd
date: 2025-12-30
version: 2.0.0
---

# Run Pre-commit Hooks

Validate code quality with pre-commit hooks before committing, and in CI pipelines.

## Overview

| Date | Objective | Outcome |
| ---- | --------- | ------- |
| 2025-12-30 | Catch issues before CI | Faster feedback, fewer CI failures |
| 2026-03-25 | CI integration patterns | GitHub Actions workflow documented |

## When to Use

- (1) Before committing code
- (2) Testing if CI will pass
- (3) After making code changes
- (4) Troubleshooting commit failures
- (5) Configuring pre-commit in CI pipelines

## Verified Workflow

1. **Install hooks** (one-time): `pre-commit install`
2. **Make changes**: Edit code files
3. **Run hooks**: `pre-commit run --all-files`
4. **Stage fixes**: If hooks auto-fixed files, stage them with `git add .`
5. **Commit**: Create commit with all fixes applied

### Quick Reference

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

# Run on specific file
pre-commit run --files src/file.mojo

# Update hook versions
pre-commit autoupdate

# Skip specific hook if broken (document reason)
SKIP=hook-name git commit -m "message"
```

### First Time Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test
pre-commit run --all-files
```

### Daily Workflow

```bash
# Make changes
# ...

# Commit (hooks run automatically)
git commit -m "feat: new feature"

# If hooks auto-fix files, stage and re-commit
git add .
git commit -m "feat: new feature"
```

### Before PR

```bash
# Verify all files pass
pre-commit run --all-files

# If passing, create PR
gh pr create --issue 42
```

## Hook Configuration

Configured in `.pre-commit-config.yaml`. Common hooks:

### Mojo Format

```yaml
- id: mojo-format
  name: Mojo Format
  entry: mojo format
  language: system
  files: \.(mojo|🔥)$
```

### Trailing Whitespace

```yaml
- id: trailing-whitespace
  name: Trim Trailing Whitespace
```

### End of File Fixer

```yaml
- id: end-of-file-fixer
  name: Fix End of Files
```

### YAML Check

```yaml
- id: check-yaml
  name: Check YAML
```

### Large Files Check

```yaml
- id: check-added-large-files
  name: Check for Large Files
  args: ['--maxkb=1000']
```

### Mixed Line Ending

```yaml
- id: mixed-line-ending
  name: Fix Mixed Line Endings
```

### Hook Behavior Summary

| Hook | Purpose | Auto-Fix |
| ---- | ------- | -------- |
| `mojo-format` | Format Mojo code | Yes |
| `trailing-whitespace` | Remove trailing spaces | Yes |
| `end-of-file-fixer` | Add final newline | Yes |
| `check-yaml` | Validate YAML syntax | No |
| `check-added-large-files` | Prevent large files | No |
| `mixed-line-ending` | Fix line endings | Yes |

**Check-only hooks** (`check-yaml`, `check-added-large-files`) report errors but don't fix — fix manually and re-commit.

## CI Integration

Pre-commit runs in CI via GitHub Actions:

```yaml
name: Pre-commit Checks

on: [push, pull_request]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pre-commit
      - run: pre-commit run --all-files
```

## Common Issues

### Hooks Fail on Commit — Auto-Fixed Files Not Staged

```bash
$ git commit -m "message"
Trim Trailing Whitespace....Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing file.md
```

**Fix**: Files were fixed but not staged — stage and re-commit:

```bash
git add .
git commit -m "message"
```

### YAML Validation Fails

```text
Check YAML...Failed
- hook id: check-yaml
- exit code: 1

Syntax error in .github/workflows/test.yml
```

**Fix**: Correct the YAML syntax.

### Large File Detected

```text
Check for Large Files...Failed
- hook id: check-added-large-files
- exit code: 1

large_file.bin (1500 KB) exceeds 1000 KB
```

**Fix**: Don't commit large files; use Git LFS if needed; add to `.gitignore`.

### Error Reference

| Error | Solution |
| ----- | -------- |
| Hooks not installed | Run `pre-commit install` |
| Hooks not running | Verify `.pre-commit-config.yaml` exists |
| All files modified after hook | Stage fixes and re-commit |
| Specific hook broken | Use `SKIP=hook-id git commit` (document why) |

## Hook Bypass Policy

**STRICT: `--no-verify` is PROHIBITED.**

If hooks fail:

1. Read the error — hook output explains what's wrong
2. Fix your code — update to pass the check
3. Re-run hooks — verify with `pre-commit run`
4. Commit again — let hooks validate

`SKIP=hook-name` is permitted only when a hook has a known bug or incompatibility (e.g., `SKIP=mojo-format` on hosts with GLIBC version mismatch). Document the reason.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |

## Results & Parameters

### Commands

```bash
# Full run
pre-commit run --all-files

# Targeted
pre-commit run <hook-id> --all-files
pre-commit run --files <path>

# Maintenance
pre-commit autoupdate
pre-commit clean
```

### Scripts Available

- `scripts/run_precommit.sh` — Run all hooks
- `scripts/install_precommit.sh` — Install hooks
- `scripts/update_precommit.sh` — Update hook versions

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | Pre-commit validation workflow | Generic patterns applicable to any project |

## References

- Pre-commit docs: <https://pre-commit.com/>
- See validate-workflow for workflow validation
- See fix-ci-failures for debugging CI
