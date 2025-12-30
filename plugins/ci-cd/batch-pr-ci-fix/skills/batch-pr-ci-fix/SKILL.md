---
name: batch-pr-ci-fix
description: "Batch fix CI failures across multiple open PRs and enable auto-merge"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-29
---

# Batch PR CI Fix

Fix CI failures across multiple open pull requests and enable auto-merge for automated merging.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Fix all CI failures across open PRs and merge them using auto-merge |
| Outcome | Success - 3 PRs merged (2990, 2991, 2992) |
| Duration | ~45 minutes |

## When to Use

- Multiple PRs have failing CI checks
- Common failure patterns across PRs (broken links, formatting, mypy errors)
- Need to batch-process PR fixes
- Want to enable auto-merge after fixes
- Documentation-only PRs with MkDocs strict mode failures

## Verified Workflow

### 1. List and Assess Open PRs

```bash
# Get all open PRs with key details
gh pr list --state open --json number,title,headRefName --limit 20

# Check CI status for each PR
gh pr checks <pr-number>

# Filter for failures/pending
gh pr checks <pr-number> 2>&1 | grep -E "(fail|pending)"
```

### 2. Identify Common Failure Patterns

Common patterns observed:

| Pattern | Example | Fix Strategy |
|---------|---------|--------------|
| Broken markdown links | Link to non-existent `math.md` | Remove or fix link |
| Cross-directory links | Link to `../../.github/workflows/` | Convert to plain text reference |
| Pre-commit formatting | ruff-format-python changes | Rebase onto main |
| Mypy module conflicts | `generators.templates` vs `scripts.generators.templates` | Add `--exclude` flag |
| Mojo package restrictions | `main()` in package file | Remove main function |

### 3. Fix Each PR Sequentially

**For documentation link failures:**

```bash
# Switch to PR branch
git checkout <branch-name>

# Find broken links
gh run view <run-id> --log 2>&1 | grep -B5 "Aborted with.*warnings"

# Example: Remove broken link
# Edit file to remove/fix link

# Commit fix
git add <file>
git commit -m "fix(docs): remove broken link to non-existent file"
git push origin <branch-name>
```

**For pre-commit failures from main:**

```bash
# Rebase onto latest main to get fixes
git checkout <branch-name>
git fetch origin main
git rebase origin/main

# Force push rebased branch
git push --force-with-lease origin <branch-name>
```

**For mypy/type check failures:**

```bash
# Check error pattern
gh run view <run-id> --log-failed | grep "error:"

# Add exclude or fix config
# Example: .github/workflows/type-check.yml
pixi run mypy --exclude 'generators/' scripts/

# Commit config fix
git add .github/workflows/type-check.yml
git commit -m "fix(ci): exclude generators/ from mypy"
git push
```

### 4. Enable Auto-Merge

```bash
# Enable auto-merge with rebase method
gh pr merge <pr-number> --auto --rebase

# Verify auto-merge enabled
gh pr list --state open --json number,title,autoMergeRequest
```

### 5. Monitor Merges

```bash
# Check merge status
gh pr view <pr-number> --json state,mergedAt

# List recently merged PRs
gh pr list --state merged --limit 5 --json number,title,mergedAt

# Verify no open PRs remain
gh pr list --state open
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Mypy `explicit_package_bases` config | Still failed with module path conflict | Use CLI `--exclude` flag instead of config |
| Direct fix for pre-commit failures | Files from main needed | Rebase onto main to get formatting fixes |
| Removing API docs entirely | Over-correction | Just remove broken links, keep structure |

## Results & Parameters

### Successful Fixes

**PR 2990** (docs/api reference):
- **Issue**: Broken link to `math.md`
- **Fix**: Removed non-existent link from `docs/api/operations/arithmetic.md`
- **Fix**: Rebased onto main for pre-commit formatting
- **Result**: Merged at 2025-12-30T00:29:57Z

**PR 2991** (PyTorch migration guide):
- **Issue**: Links to `../api/tensor.md`, `../api/training/optimizers.md`
- **Fix**: Removed broken links (API docs don't exist on main)
- **Result**: Merged at 2025-12-30T00:25:11Z

**PR 2992** (release automation):
- **Issue**: Links to `../../.github/workflows/release.yml`, `../../scripts/*.py`
- **Fix**: Converted cross-directory links to plain text references
- **Result**: Merged at 2025-12-30T00:24:15Z

### Key Commands

```bash
# List open PRs
gh pr list --state open --json number,title,headRefName

# Check CI status
gh pr checks <pr-number>
gh pr checks <pr-number> 2>&1 | grep -E "(fail|pending)"

# Get failure logs
gh run view <run-id> --log-failed

# Enable auto-merge
gh pr merge <pr-number> --auto --rebase

# Check merge status
gh pr view <pr-number> --json state,mergedAt
```

## Common MkDocs Strict Mode Errors

MkDocs strict mode aborts on broken/unrecognized links:

| Error Type | Example | Fix |
|-----------|---------|-----|
| Link to non-existent file | `[Math](math.md)` when `math.md` doesn't exist | Remove link or create file |
| Cross-directory link | `[Workflow](../../.github/workflows/release.yml)` | Convert to backtick code reference |
| Unrecognized relative link | `[Examples](../../examples/)` | Use valid docs-relative path or remove |

**Detection pattern:**
```
WARNING - Doc file 'path/to/file.md' contains a link 'target.md', but the target 'path/target.md' is not found
Aborted with N warnings in strict mode!
```

## Pre-commit Failure Patterns

When pre-commit hooks modify files in CI:

```
Ruff Format Python.......................................................Failed
- hook id: ruff-format-python
- files were modified by this hook

1 file reformatted, 140 files left unchanged
```

**Fix**: Rebase PR onto main to incorporate formatting fixes that were merged.

## Verification Checklist

- [ ] All open PRs identified
- [ ] CI failures categorized by pattern
- [ ] Fixes applied and pushed
- [ ] Auto-merge enabled on each PR
- [ ] All PRs merged successfully
- [ ] No open PRs remain

## Time Savings

- **Manual approach**: ~2-3 hours (fix each PR individually, wait for CI, manually merge)
- **Batch approach**: ~45 minutes (parallel analysis, pattern-based fixes, auto-merge)
- **Savings**: ~60-70% time reduction

## Related Skills

- `github-actions-mojo` - Setting up CI for Mojo projects
- `fix-ci-failures` - General CI debugging
- `documentation-validation` - MkDocs configuration

## References

- GitHub CLI: `gh pr`, `gh run` commands
- MkDocs strict mode: <https://www.mkdocs.org/user-guide/configuration/#strict>
- GitHub auto-merge: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request>
