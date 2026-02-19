# Pre-commit Maintenance Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Issue** | #678 - Enable YAML and markdown linting in pre-commit |
| **Objective** | Enable and verify YAML/markdown linting hooks, update versions |
| **Outcome** | ✅ Success - Hooks already enabled, versions updated |

## When to Use

Use this skill when:

- Enabling or verifying linting hooks in pre-commit configuration
- Updating pre-commit hook versions to latest releases
- Troubleshooting why linting hooks appear to be disabled
- Verifying all files pass linting checks after enabling hooks

## Verified Workflow

### 1. Verify Current Hook Status

**Don't assume hooks are disabled** - check the actual configuration first:

```bash
# Read the pre-commit config to see current state
cat .pre-commit-config.yaml

# Check which hooks are currently enabled
pre-commit run --all-files
```

**Key Finding**: Issue descriptions may reference outdated line numbers or assume hooks are disabled when they're actually already enabled.

### 2. Update Hook Versions

Use `pre-commit autoupdate` to check for and apply version updates:

```bash
# Check for and update all hooks to latest versions
pre-commit autoupdate
```

**Expected Output**:

```
[https://github.com/adrienverge/yamllint] updating v1.35.1 -> v1.38.0
[https://github.com/pre-commit/pre-commit-hooks] updating v4.5.0 -> v6.0.0
```

### 3. Verify All Hooks Pass

After updating versions, verify everything still works:

```bash
# Run all hooks on all files
pre-commit run --all-files
```

**All hooks should pass**. If any fail, fix the issues before committing.

### 4. Configuration Files to Check

Verify these configuration files exist and are properly set up:

- `.markdownlint.json` - Markdown linting rules
- `.yamllint.yaml` - YAML linting rules

### 5. Commit and Push

```bash
git add .pre-commit-config.yaml
git commit -m "chore(ci): Update pre-commit hook versions

Update yamllint (vX.X.X → vY.Y.Y) and pre-commit-hooks (vA.A.A → vB.B.B)

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push -u origin <branch-name>
```

## Failed Attempts

### Attempt 1: Assuming hooks need to be uncommented

**What was tried**: Looking for commented-out hooks at specific line numbers mentioned in the issue

**Why it failed**: The issue description referenced line numbers from an older version of the file. The hooks were already enabled in the current codebase.

**Lesson**: Always verify the current state before making changes. Issue descriptions may be outdated or based on earlier file versions.

### Attempt 2: Using the commit skill in don't ask mode

**What was tried**: Using `/commit-commands:commit` skill to create the commit

**Why it failed**: Skill requires user permission in don't ask mode

**Lesson**: In don't ask mode, use standard git commands directly instead of delegating to skills

## Results & Parameters

### Hook Versions Updated

```yaml
# yamllint
- repo: https://github.com/adrienverge/yamllint
  rev: v1.38.0  # Updated from v1.35.1

# pre-commit-hooks
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0  # Updated from v4.5.0
```

### Hooks Verified as Enabled

```yaml
# Markdown linting (lines 46-53)
- repo: https://github.com/DavidAnson/markdownlint-cli2
  rev: v0.20.0
  hooks:
    - id: markdownlint-cli2
      args: ['--config', '.markdownlint.json', '--fix']

# YAML linting (lines 56-63)
- repo: https://github.com/adrienverge/yamllint
  rev: v1.38.0
  hooks:
    - id: yamllint
      args: ['--config-file', '.yamllint.yaml']
```

### All Hooks Passing

```
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Mypy Type Check Python...................................................Passed
Markdown Lint............................................................Passed
YAML Lint................................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

## Key Takeaways

1. **Verify before assuming** - Check current state instead of trusting issue descriptions
2. **Use autoupdate** - `pre-commit autoupdate` is the standard way to update hook versions
3. **Test after updates** - Always run `pre-commit run --all-files` after version updates
4. **Document actual changes** - PR descriptions should reflect what was actually done, not what was expected to be needed
5. **Line numbers drift** - Issue descriptions referencing specific line numbers may become outdated as files evolve

## Related

- Issue #678: Enable YAML and markdown linting in pre-commit
- PR #696: Update pre-commit hook versions
- Issue #594: Code Quality Audit (parent issue)
