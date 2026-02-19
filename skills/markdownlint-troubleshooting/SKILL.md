# Markdownlint Troubleshooting and CI Unblocking

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Objective** | Fix CI failures on PRs #665, #666, #667 caused by markdownlint issues in main branch |
| **Outcome** | ✅ **Fixed main, unblocked 3 PRs**: All PRs passing CI after fixing markdown formatting in main |
| **Status** | Completed - PR #669 merged, all affected PRs rebased and passing |

## When to Use This Skill

Apply this pattern when:

1. **Multiple PRs failing CI** with the same pre-commit hook error (markdownlint, black, ruff, etc.)
2. **CI failures NOT caused by PR changes** but by files already on main branch
3. **Pre-commit hooks running with --fix flag** that modify files and exit non-zero
4. **Blocking situation** where no PRs can merge until main is fixed
5. **Linter issues in recently merged code** that affect all subsequent PRs

**Do NOT use** when:

- CI failures are specific to individual PR changes (fix in each PR instead)
- Linter is not running with --fix (different error pattern)
- Only one PR is affected (investigate PR-specific issues first)

## Verified Workflow

### 1. Diagnose the Problem

```bash
# Check CI failures on multiple PRs
gh pr checks 665
gh pr checks 666
gh pr checks 667

# All show same failure pattern:
# "Markdown Lint............................................................Failed"
# "files were modified by this hook"
```

**Key indicator**: Same hook failing across multiple PRs that touch different files.

### 2. Identify the Root Cause

```bash
# Run the hook locally on main branch
git checkout main
git pull origin main
pre-commit run markdownlint-cli2 --all-files

# Hook will auto-fix issues and exit 1 (fail)
# Output shows which files were modified
```

**Root cause pattern**: Files on main have formatting issues that the hook auto-fixes, but exits non-zero because files were modified.

### 3. Create Fix Branch from Main

```bash
# MUST branch from main, not from a failing PR
git checkout main
git checkout -b fix/markdownlint-<description>
```

**Critical**: Branch from main to fix the source of the problem.

### 4. Run Hook and Review Auto-Fixes

```bash
# Let the hook auto-fix all issues
pre-commit run markdownlint-cli2 --all-files

# Review what was changed
git diff
```

**For markdownlint**, common auto-fixes:

- **MD032**: Add blank lines before lists
- **MD034**: Wrap bare URLs in angle brackets (`<https://...>`)
- **MD009**: Remove trailing spaces
- **MD010**: Replace tabs with spaces in content

### 5. Verify and Commit

```bash
# Verify hook now passes
pre-commit run markdownlint-cli2 --all-files
# Should show: "Passed" with no file modifications

# Commit the auto-fixes
git add <modified-files>
git commit -m "fix(lint): Fix markdownlint violations in <files>

Auto-fixed MD032, MD034 violations that were causing CI failures
for all PRs. Changes made by markdownlint-cli2 --fix.

Fixes CI for PRs #665, #666, #667
"
```

### 6. Create PR and Merge to Main

```bash
# Push and create PR
git push -u origin fix/markdownlint-<description>

gh pr create \
  --title "fix(lint): Fix markdownlint violations in main" \
  --body "Fixes markdownlint issues blocking PRs #665, #666, #667..." \
  --label "bug"

# Enable auto-merge
gh pr merge <number> --auto --rebase

# Wait for CI to pass and merge
gh pr checks <number>
```

### 7. Rebase Affected PRs

```bash
# Update local main
git checkout main
git pull origin main

# Rebase each affected PR
for branch in 637-fix-opus-model-config 654-add-github-templates 655-add-codeowners; do
  git checkout $branch
  git rebase main
  git push --force-with-lease
done

# Verify CI now passes
for pr in 665 666 667; do
  gh pr checks $pr
done
```

## Failed Attempts

### ❌ Attempt 1: Trying to Fix Issues in Each PR Separately

**What we tried:**

Fixing the markdown issues within each failing PR (editing the docker-multistage-build files in each PR branch).

**Why it failed:**

- The files with issues (`docker-multistage-build/SKILL.md`, `docker-multistage-build/references/notes.md`) were NOT part of the PR changes
- Modifying files outside the PR scope creates noise and confusion
- Does not fix the root cause - main branch still has the issues
- Every new PR would continue to fail until main is fixed

**Solution:**

Always fix linting issues in the branch where they were introduced (main), not in PRs that happen to encounter them.

### ❌ Attempt 2: Disabling or Skipping the Pre-commit Hook

**What we considered:**

Using `--no-verify` or disabling the markdownlint hook temporarily to let PRs merge.

**Why this is wrong:**

- **Violates project policy**: `--no-verify` is ABSOLUTELY PROHIBITED per CLAUDE.md
- Bypasses code quality checks
- Allows broken code to accumulate in main
- Creates technical debt
- Sets bad precedent for future contributors

**Solution:**

Never skip pre-commit hooks. If a hook is failing, fix the underlying issue.

### ❌ Attempt 3: Waiting for CI to "Eventually Pass"

**What we observed:**

CI was taking 7-11+ minutes per run, so we initially waited to see if it would eventually pass.

**Why it failed:**

- The hook deterministically fails because files are modified
- No amount of waiting will change the outcome
- Wasted time (multiple 10+ minute waits across 3 PRs)
- Blocked all development progress

**Solution:**

When you see "files were modified by this hook", the hook will never pass without fixing the files. Don't wait - investigate immediately.

## Results & Parameters

### Markdownlint Violations Fixed

**MD032 - Blank lines before lists** (14 locations):

```markdown
# Before
**Do NOT use** when:
- Item 1

# After
**Do NOT use** when:

- Item 1
```

**MD034 - Bare URLs** (9 locations):

```markdown
# Before
- Docker Docs: https://docs.docker.com/build/multi-stage/

# After
- Docker Docs: <https://docs.docker.com/build/multi-stage/>
```

### Files Modified

```bash
.claude-plugin/skills/docker-multistage-build/SKILL.md
.claude-plugin/skills/docker-multistage-build/references/notes.md
```

### Timeline

| Event | Duration | Notes |
|-------|----------|-------|
| Diagnosis | 5 min | Checked multiple PRs, identified pattern |
| Local reproduction | 2 min | Ran hook on main, saw failures |
| Fix creation | 10 min | Created branch, made edits, verified |
| PR #669 creation | 2 min | Created PR, enabled auto-merge |
| PR #669 CI | 7 min | Pre-commit hook passed |
| Rebase 3 PRs | 3 min | Rebased all affected branches |
| Final CI verification | 21 min | 3 PRs × 7 min each |
| **Total** | **50 min** | From detection to all PRs passing |

### Verification Commands

```bash
# Check if hook passes on main
pre-commit run markdownlint-cli2 --all-files

# Check individual PR CI status
gh pr checks <number>

# View recent workflow runs
gh run list --limit 10

# Check if files were auto-modified
git diff
```

## Common Markdownlint Rules

| Rule | Description | Auto-fix |
|------|-------------|----------|
| MD032 | Lists should be surrounded by blank lines | ✅ Yes |
| MD034 | Bare URL used | ✅ Yes (wraps in `<>`) |
| MD009 | Trailing spaces | ✅ Yes |
| MD010 | Hard tabs | ✅ Yes |
| MD012 | Multiple consecutive blank lines | ✅ Yes |
| MD022 | Headings should be surrounded by blank lines | ✅ Yes |
| MD031 | Fenced code blocks surrounded by blank lines | ✅ Yes |

## Implementation Checklist

When fixing markdownlint CI failures, verify:

- [ ] Multiple PRs failing with same markdownlint error
- [ ] Error message says "files were modified by this hook"
- [ ] Create fix branch from main (not from failing PR)
- [ ] Run `pre-commit run markdownlint-cli2 --all-files` locally
- [ ] Review auto-fixes with `git diff`
- [ ] Verify hook passes after fixes
- [ ] Create PR to main with clear description
- [ ] Enable auto-merge on fix PR
- [ ] Wait for fix PR to merge to main
- [ ] Rebase all affected PRs onto updated main
- [ ] Verify CI passes on all rebased PRs

## Related Skills

- **run-precommit** (ci-cd) - Running pre-commit hooks for validation
- **fix-ci-failures** (ci-cd) - General CI troubleshooting patterns
- **parallel-pr-workflow** (workflow) - Managing multiple PRs efficiently

## References

- PR #669: <https://github.com/HomericIntelligence/ProjectScylla/pull/669>
- Affected PRs: #665, #666, #667
- Markdownlint Rules: <https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md>
- Pre-commit Framework: <https://pre-commit.com/>

## Team Knowledge

**Key Learning:** When pre-commit hooks fail with "files were modified by this hook" across multiple PRs, the issue is in main, not in the PRs. Fix main first, then rebase PRs.

**Common Pitfall:** Trying to fix linter issues within failing PRs instead of fixing the root cause in main. This creates scope creep and doesn't solve the underlying problem.

**Best Practice:** Always run `pre-commit run --all-files` on main after merging to catch issues before they block other PRs. Consider adding this to your post-merge checklist or CI pipeline.

**Time Saver:** If you see the same CI failure across 3+ PRs, immediately check if main has the issue. Don't debug each PR individually.
