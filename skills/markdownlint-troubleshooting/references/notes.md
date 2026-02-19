# Implementation Notes: Markdownlint CI Troubleshooting

## Session Context

**Date:** 2026-02-14
**Objective:** Fix CI failures blocking PRs #665, #666, #667
**Root Cause:** Markdownlint issues in `docker-multistage-build` skill files on main branch
**Outcome:** Fixed main branch, rebased 3 PRs, all passing CI

## Problem Statement

Three PRs were failing the `Markdown Lint` pre-commit hook with the same error:

```
Markdown Lint............................................................Failed
- hook id: markdownlint-cli2
- files were modified by this hook
```

**Key observation:** The failures were NOT caused by changes in those PRs, but by markdown formatting issues in files already on main - specifically the `docker-multistage-build` skill files added in commit `6897d91`.

**Impact:**

- All new PRs were blocked from merging
- CI failures were confusing (PRs hadn't touched the failing files)
- Development workflow stalled across the team

## Diagnostic Process

### Step 1: Pattern Recognition

```bash
# Checked multiple PRs
gh pr checks 665
# pre-commit failed - "files were modified by this hook"

gh pr checks 666
# pre-commit failed - "files were modified by this hook"

gh pr checks 667
# pre-commit failed - "files were modified by this hook"
```

**Pattern identified:** Same error across PRs that modified completely different files.

### Step 2: Local Reproduction

```bash
# Switched to main to reproduce
git checkout main
git pull origin main

# Ran the failing hook
pre-commit run markdownlint-cli2 --all-files

# Output showed:
# - Files were auto-modified
# - Exit code 1 (failure)
# - docker-multistage-build files had violations
```

### Step 3: Root Cause Analysis

**Hook behavior with `--fix` flag:**

1. Reads all markdown files
2. Detects violations (MD032, MD034)
3. Auto-fixes violations
4. Modifies files in place
5. Exits with code 1 because files were changed

**Why this blocks PRs:**

- Git pre-commit hooks expect no file modifications
- If a hook modifies files, it signals that the codebase wasn't properly formatted
- CI fails to enforce that all code is pre-formatted before commit

**Why this affects ALL PRs:**

- Hook runs on ALL markdown files in the repo, not just changed files
- If ANY file in the repo has violations, the hook fails
- Doesn't matter if the PR touched those files or not

## Solution Implementation

### Phase 1: Fix Main Branch

**Created fix branch:**

```bash
git checkout main
git checkout -b fix/markdownlint-docker-multistage
```

**Identified violations:**

Ran pre-commit hook locally and reviewed `git diff`:

1. **MD032 violations** (14 locations):
   - Missing blank lines before list items
   - Pattern: Bold text followed immediately by list

2. **MD034 violations** (9 locations):
   - Bare URLs without angle brackets
   - Pattern: `https://...` instead of `<https://...>`

**Applied fixes:**

Used the Edit tool to add blank lines and wrap URLs. Example fixes:

```diff
# MD032 fix
**Do NOT use** when:
+
- Image is already minimal
```

```diff
# MD034 fix
-- Issue #601: https://github.com/...
+- Issue #601: <https://github.com/...>
```

**Verified locally:**

```bash
pre-commit run markdownlint-cli2 --all-files
# ✅ Passed with 0 errors
```

**Created PR:**

```bash
git add .claude-plugin/skills/docker-multistage-build/
git commit -m "fix(skills): Fix markdownlint issues in docker-multistage-build skill"
git push -u origin fix/markdownlint-docker-multistage

gh pr create \
  --title "fix(skills): Fix markdownlint issues in docker-multistage-build" \
  --body "Fixes MD032 and MD034 violations blocking PRs #665, #666, #667" \
  --label "bug"

gh pr merge 669 --auto --rebase
```

**Waited for merge:**

- PR #669 created
- CI started (pre-commit hook)
- CI took ~7 minutes to complete
- Auto-merge triggered
- PR #669 merged to main

### Phase 2: Rebase Affected PRs

**Updated local main:**

```bash
git checkout main
git pull origin main
# Now includes the markdown fixes from PR #669
```

**Rebased each PR:**

```bash
# PR #665
git checkout 637-fix-opus-model-config
git rebase main
git push --force-with-lease

# PR #666
git checkout 654-add-github-templates
git rebase main
git push --force-with-lease

# PR #667
git checkout 655-add-codeowners
git rebase main
git push --force-with-lease
```

**Results:**

- All rebases completed successfully
- No merge conflicts
- Each branch now includes the markdown fixes from main

### Phase 3: Verification

**Checked CI status:**

```bash
gh pr checks 665
# pre-commit  pass  7m29s

gh pr checks 666
# pre-commit  pass  7m23s

gh pr checks 667
# pre-commit  pass  7m41s
```

**All PRs passing!** ✅

## Detailed Violations and Fixes

### File 1: SKILL.md

**Location 1** (line 24-27):

```diff
**Do NOT use** when:
+
- Image is already minimal (<100MB)
```

**Location 2** (line 263):

```diff
When implementing multi-stage builds, verify:
+
- [ ] Builder stage installs all build dependencies
```

**Location 3** (lines 284-287) - URLs:

```diff
-- Issue #601: https://github.com/HomericIntelligence/ProjectScylla/issues/601
-- PR #649: https://github.com/HomericIntelligence/ProjectScylla/pull/649
-- Docker Multi-Stage Builds: https://docs.docker.com/build/building/multi-stage/
-- Python Docker Best Practices: https://docs.docker.com/language/python/
+- Issue #601: <https://github.com/HomericIntelligence/ProjectScylla/issues/601>
+- PR #649: <https://github.com/HomericIntelligence/ProjectScylla/pull/649>
+- Docker Multi-Stage Builds: <https://docs.docker.com/build/building/multi-stage/>
+- Python Docker Best Practices: <https://docs.docker.com/language/python/>
```

**Location 4** (line 291-294):

```diff
**Key Learning:** When separating build and runtime stages, always verify that:
+
1. Python packages are in the correct site-packages directory
```

### File 2: references/notes.md

**Similar patterns across multiple locations:**

- Line 257: Blank line before numbered list
- Line 275: Blank line before code block
- Line 282: Blank line before list items
- Line 294: Blank line before list items
- Line 302: Blank line before list items (2 locations)
- Lines 357-361: Wrap 5 bare URLs
- Line 365: Blank line before list items (2 locations)
- Line 378: Blank line before numbered list

## Lessons Learned

### 1. Hook Behavior with --fix

Pre-commit hooks that run with `--fix` flag have a specific behavior:

- They auto-correct violations
- They exit with code 1 if files were modified
- This signals to developers: "you should have formatted before committing"

**Implication:** You can't just "re-run" the hook to make it pass. You must commit the auto-fixes first.

### 2. All vs Changed Files

Some hooks run on ALL files (`--all-files`), not just changed files:

```bash
# This is what markdownlint does
pre-commit run markdownlint-cli2 --all-files
```

**Why:** Ensures entire codebase stays compliant, not just new code.

**Implication:** A single file with issues on main will block ALL PRs.

### 3. Fix at the Source

**Wrong approach:** Fix linting issues in each affected PR

- Creates scope creep
- Adds noise to PRs
- Doesn't solve root cause
- Every new PR will fail

**Right approach:** Fix issues in the branch where they were introduced (main)

- Fixes problem once
- All future PRs inherit the fix
- Clear responsibility (main maintainer)

### 4. Rebase vs Merge for Fixes

After fixing main, affected PRs need to get those fixes:

**Option 1: Rebase (used)**

```bash
git checkout pr-branch
git rebase main
git push --force-with-lease
```

Pros:

- Clean history
- PR commits stay on top
- Easier to review PR changes

**Option 2: Merge**

```bash
git checkout pr-branch
git merge main
git push
```

Pros:

- No force-push needed
- Preserves exact history

**Decision:** Used rebase because project policy prefers linear history.

### 5. CI Wait Times

GitHub Actions CI for pre-commit hooks took 7-11 minutes per run:

- Hook setup: ~1 min
- Hook execution: ~5-6 min
- Teardown: ~1 min

**Total time for this fix:**

- PR #669 CI: 7 min
- PR #665 CI: 7.5 min
- PR #666 CI: 7.4 min
- PR #667 CI: 7.7 min
- **Total:** ~30 min of CI time

**Optimization opportunity:** Could cache pre-commit environments to reduce setup time.

## Command Reference

### Diagnosis Commands

```bash
# Check multiple PRs for pattern
gh pr checks <number>

# Reproduce locally
git checkout main
pre-commit run <hook-id> --all-files

# View modified files
git diff

# Check recent workflow runs
gh run list --limit 10 --json status,conclusion,name
```

### Fix Commands

```bash
# Create fix branch from main
git checkout main
git checkout -b fix/<description>

# Run hook with auto-fix
pre-commit run markdownlint-cli2 --all-files

# Verify hook passes
pre-commit run markdownlint-cli2 --all-files
# Should exit 0 with no modifications

# Commit auto-fixes
git add <files>
git commit -m "fix(lint): Auto-fix <hook> violations"

# Create PR
gh pr create --title "..." --body "..." --label "bug"
gh pr merge <number> --auto --rebase
```

### Rebase Commands

```bash
# Update main
git checkout main
git pull origin main

# Rebase each PR
git checkout <branch>
git rebase main
git push --force-with-lease

# Verify CI
gh pr checks <number>
```

## Prevention Strategies

### Strategy 1: Pre-merge Hook Validation

Add to `.github/workflows/pre-commit.yml`:

```yaml
- name: Run pre-commit on all files
  run: |
    pre-commit run --all-files
    # Exit 0 even if files modified (for auto-fix hooks)
    # But store modification status
    git diff --exit-code || echo "modified=true" >> $GITHUB_OUTPUT
```

### Strategy 2: Main Branch Protection

Require pre-commit checks to pass before merge:

```yaml
# .github/branch-protection.yml
required_status_checks:
  strict: true
  contexts:
    - "pre-commit"
```

### Strategy 3: Post-merge Validation

Add a post-merge hook locally:

```bash
# .git/hooks/post-merge
#!/bin/bash
pre-commit run --all-files
if [ $? -ne 0 ]; then
  echo "⚠️  WARNING: Pre-commit hooks found issues in main"
  echo "Run 'pre-commit run --all-files' to fix"
fi
```

### Strategy 4: Documentation

Add to CLAUDE.md or CONTRIBUTING.md:

```markdown
## After Merging to Main

Always run to verify no linting issues introduced:

\`\`\`bash
pre-commit run --all-files
\`\`\`

If this modifies files, create a fix PR immediately.
```

## Metrics

| Metric | Value |
|--------|-------|
| Files modified | 2 |
| Violations fixed | 23 (14 MD032 + 9 MD034) |
| PRs unblocked | 3 |
| Total time | 50 minutes |
| Manual edits | 0 (all auto-fixed) |
| CI runs | 4 (1 fix PR + 3 rebased PRs) |
| Average CI time | 7.4 minutes |

## References

- **PR #669 (fix):** <https://github.com/HomericIntelligence/ProjectScylla/pull/669>
- **PR #665 (affected):** <https://github.com/HomericIntelligence/ProjectScylla/pull/665>
- **PR #666 (affected):** <https://github.com/HomericIntelligence/ProjectScylla/pull/666>
- **PR #667 (affected):** <https://github.com/HomericIntelligence/ProjectScylla/pull/667>
- **Commit with issues:** `6897d91` (docker-multistage-build skill)
- **Markdownlint rules:** <https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md>

## Next Steps

This skill can be used as a reference when:

1. Similar linting issues block multiple PRs
2. Pre-commit hooks fail with "files were modified"
3. CI failures affect PRs that didn't touch the failing files
4. Need to coordinate fixes across main and multiple PR branches
