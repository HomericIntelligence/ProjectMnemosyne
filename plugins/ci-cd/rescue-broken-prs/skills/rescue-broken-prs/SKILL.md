---
name: "Rescue Broken PRs"
description: "Rescue Broken PRs"
category: ci-cd
date: 2026-02-06
user-invocable: false
---
# Rescue Broken PRs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-06 |
| **Objective** | Fix 4 failing PRs with pre-commit and test failures |
| **Outcome** | ✅ All 4 PRs fixed and passing CI |
| **Success Rate** | 100% (4/4 PRs rescued) |
| **Time to Resolution** | ~30 minutes |

## When to Use This Skill

Use this skill when:
- Multiple PRs are failing CI checks simultaneously
- Pre-commit hooks (ruff, formatting) are blocking merges
- Tests are failing due to refactoring or API changes
- Constructor bugs or method signature changes break tests
- Need to systematically diagnose and fix PR failures

**Trigger phrases:**
- "Fix failing PRs"
- "These PRs are failing CI"
- "Pre-commit checks are blocking"
- "Tests are broken after refactoring"

## Verified Workflow

### 1. Triage All Failures First

**Before fixing anything**, get a complete picture:

```bash
# Check all PR statuses in parallel
for pr in 356 359 360 361; do
  echo "=== PR $pr ===";
  gh pr checks $pr 2>&1 | head -4;
done
```

**Create a triage table:**

| PR | Branch | Pre-commit | Tests | Issue Summary |
|----|--------|-----------|-------|---------------|
| 356 | pr1-discovery-library | FAIL | PASS | 5 docstrings missing blank line |
| 359 | pr4-document-recovery-scripts | FAIL | PASS | 1 line too long |
| 360 | pr5-subtest-provider | FAIL | FAIL | Constructor bug + lint |
| 361 | pr6-test-fixture-dataclass | FAIL | PASS | 2 long lines + unused var |

**Priority order:**
1. PRs with test failures (critical bugs)
2. PRs with simple lint fixes (quick wins)
3. PRs with complex formatting issues

### 2. Get Detailed Error Messages

For each failing PR:

```bash
# Get the latest failing run
gh pr checks <PR_NUMBER>

# Get detailed logs
gh run view <RUN_ID> --log-failed

# Focus on the actual errors (not the stack trace)
gh run view <RUN_ID> --log-failed | grep -A 20 "hook id"
```

**Key patterns to look for:**
- Ruff errors: `D102 Missing docstring`, `F841 Local variable ... never used`
- Line length: `E501 line too long (108 > 100 characters)`
- Formatting: `files were modified by this hook`
- Test failures: `AttributeError`, `FAILED tests/...`

### 3. Fix Pre-commit Issues Systematically

#### Pattern 1: Docstring Blank Lines (D102)

**Error:**
```
D102 Missing docstring in public method
   --> file.py:33:9
```

**Fix:**
```python
# BEFORE
def method():
    """Docstring text.

    More text.
    """

# AFTER
def method():
    """Docstring text.

    More text.

    """  # <- Add blank line before closing """
```

#### Pattern 2: Line Too Long (E501)

**Error:**
```
E501 line too long (108 > 100 characters)
```

**Fix:**
```python
# BEFORE
    - rerun_judges.py --regenerate-only: Regenerate consensus from existing judges (overlapping functionality)

# AFTER
    - rerun_judges.py --regenerate-only: Regenerate consensus
      from existing judges (overlapping functionality)
```

#### Pattern 3: Unused Variables (F841)

**Error:**
```
F841 Local variable `tier_dir` is assigned to but never used
```

**Fix:**
```python
# BEFORE
tier_dir = tiers_dir / "t5"  # Legacy parameter, not used
subtests = manager.discover_subtests(TierID.T5)

# AFTER
subtests = manager.discover_subtests(TierID.T5)  # Remove unused variable
```

#### Pattern 4: Formatting Changes

If ruff-format-python modifies files, run locally:

```bash
pixi run pre-commit run --all-files ruff-format-python
git add -u
git commit -m "style: apply ruff formatting"
```

### 4. Fix Test Failures from Refactoring

**Common scenario:** Method moved from class to provider/helper

**Error pattern:**
```python
FAILED tests/test_file.py::test_name - AttributeError: 'ClassName' object has no attribute '_old_method'
```

**Investigation:**
```bash
# Find the old method calls
grep -n "_old_method" tests/test_file.py

# Find the new API
grep "def old_method" scylla/**/*.py
```

**Fix:**
```python
# BEFORE (refactored code moved _discover_subtests to SubtestProvider)
subtests = manager._discover_subtests(TierID.T5, tier_dir)

# AFTER (use new API)
subtests = manager.subtest_provider.discover_subtests(TierID.T5)
```

**Bulk replacement:**
```bash
# Use Edit tool with replace_all=true for consistent changes
Edit(file_path="tests/test_file.py",
     old_string="manager._discover_subtests(TierID.T5, tier_dir)",
     new_string="manager.subtest_provider.discover_subtests(TierID.T5)",
     replace_all=true)
```

### 5. Fix Constructor/Initialization Bugs

**Error pattern:**
```
AttributeError: 'TierManager' object has no attribute '_shared_dir'
```

**Root cause:** Accessing instance variable before it's set

**Investigation:**
```python
# BROKEN CODE
if shared_dir is None:
    shared_dir = self._shared_dir  # ❌ _shared_dir doesn't exist yet!
self._shared_dir = shared_dir
```

**Fix:**
```python
# FIXED CODE
if shared_dir is None:
    shared_dir = self._get_shared_dir()  # ✅ Call method to compute path
self._shared_dir = shared_dir
```

### 6. Workflow for Each PR

```bash
# 1. Checkout branch
git checkout <branch-name>

# 2. Pull latest (in case of divergence)
git pull origin <branch-name>

# 3. Apply fixes using Read + Edit tools
Read(file_path="path/to/file.py")
Edit(file_path="path/to/file.py", old_string="...", new_string="...")

# 4. Run pre-commit locally (optional but helpful)
pixi run pre-commit run --all-files

# 5. Commit with descriptive message
git add <files>
git commit -m "fix(scope): description

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 6. Push
git push

# 7. Move to next PR
```

### 7. Rebase Against Main (If Requested)

```bash
# Fetch latest main
git fetch origin main

# For each open PR branch
git checkout <branch-name>
git rebase origin/main
git push --force-with-lease

# Return to main
git checkout main
```

## Failed Attempts & Lessons Learned

### ❌ Failed: Using `git reset --hard` Without Checking State

**What happened:** Tried to sync branch with remote using `git reset --hard origin/branch`

**Error:**
```
BLOCKED by Safety Net
Reason: git reset --hard destroys all uncommitted changes permanently
```

**Why it failed:** Safety hooks prevented destructive operation

**Solution:** Use `git pull origin <branch>` instead for safe sync

---

### ❌ Failed: Incomplete Regex Replacement

**What happened:** Used `Edit(replace_all=true)` but pattern didn't match all variants

**Example:**
```python
# Replaced these:
manager._discover_subtests(TierID.T5, tier_dir)

# But missed these (different tier, different formatting):
manager._discover_subtests(TierID.T2, tiers_dir / "t2")
manager._discover_subtests(TierID.T0, tiers_dir / "t0")
```

**Why it failed:** Pattern was too specific (hard-coded tier ID and variable name)

**Solution:** Use multiple `Edit` calls with `replace_all=true` for each variant:
```python
Edit(..., old_string='manager._discover_subtests(TierID.T5, tier_dir)', ...)
Edit(..., old_string='manager._discover_subtests(TierID.T2, tier_dir)', ...)
Edit(..., old_string='manager._discover_subtests(TierID.T0, tiers_dir / "t0")', ...)
```

---

### ❌ Failed: Not Removing Associated Dead Code

**What happened:** Fixed API call but left unused variables

**Example:**
```python
# Fixed the API call
subtests = manager.subtest_provider.discover_subtests(TierID.T5)

# But left this orphaned variable
tier_dir = tiers_dir / "t5"  # ❌ Now unused!
```

**Error:**
```
F841 Local variable `tier_dir` is assigned to but never used
```

**Why it failed:** Focused on fixing the method call, didn't check for dead code

**Solution:** After fixing API calls, grep for related variables and remove them:
```bash
grep -n "tier_dir = " tests/test_file.py
# Then remove all those lines
```

---

### ❌ Failed: Forgetting Protocol Method Docstrings

**What happened:** Added docstrings to implementations but not to Protocol

**Error:**
```
D102 Missing docstring in public method
   --> subtest_provider.py:33:9
    |
33 |     def discover_subtests(
   |         ^^^^^^^^^^^^^^^^^
```

**Why it failed:** Ruff requires docstrings on Protocol methods too, not just implementations

**Solution:**
```python
class SubtestProvider(Protocol):
    def discover_subtests(
        self, tier_id: TierID, skip_agent_teams: bool = False
    ) -> list[SubTestConfig]:
        """Discover subtests for a given tier."""  # ✅ Add docstring
        ...
```

---

### ⚠️ Warning: Files Modified by Linter

**What happened:** After `Edit` tool modified file, got error:

```
File has been modified since read, either by the user or by a linter
```

**Why it happened:** Pre-commit hooks or IDE auto-formatters changed the file

**Solution:** Re-read the file before the next `Edit`:
```python
Read(file_path="path/to/file.py")  # Refresh the file state
Edit(file_path="path/to/file.py", ...)  # Now this will work
```

## Results & Verification

### Final PR Status

All 4 PRs rescued successfully:

```bash
gh pr list --state all --limit 10 --json number,state,headRefName
```

| PR | Status | Commits Added | Issues Fixed |
|----|--------|---------------|--------------|
| 356 | ✅ PASSING | 2 | 8 docstring blank lines |
| 359 | ✅ PASSING | 1 | 1 line length issue |
| 360 | ✅ PASSING | 6 | Constructor bug, 11 test updates, lint |
| 361 | ✅ PASSING | 1 | 2 line lengths, 1 unused var |

### Key Metrics

- **PRs Fixed:** 4/4 (100%)
- **Test Failures Fixed:** 38 tests (PR 360)
- **Lint Issues Fixed:** 18 across all PRs
- **Commits Created:** 10 total
- **Time to Green CI:** ~5 minutes per PR after fixes

### CI Verification Commands

```bash
# Check all PR statuses
for pr in 356 359 360 361; do
  echo "=== PR $pr ===";
  gh pr checks $pr 2>&1 | head -3;
  echo;
done

# Output should show:
# pre-commit   pass
# test (unit)  pass
```

## Parameters & Configuration

### Tools Used

- **GitHub CLI:** `gh` for PR checks and run logs
- **Git Operations:** Pull, rebase, force-with-lease
- **Pre-commit:** Ruff formatting and linting
- **Test Runner:** pytest via GitHub Actions

### Commit Message Format

```
<type>(<scope>): <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types used:**
- `fix`: Bug fixes (constructor, test API updates)
- `style`: Formatting changes (ruff auto-format)
- `refactor`: Code improvements without behavior change

### Git Force Push Strategy

**Always use `--force-with-lease`:**
```bash
git push --force-with-lease
```

**Why:** Protects against overwriting someone else's commits

**When needed:**
- After rebasing against main
- After amending commits
- After interactive rebase

## Related Skills

- `/fix-ci-failures` - General CI debugging
- `/gh-review-pr` - PR review workflows
- `/quality-run-linters` - Pre-commit checks
- `/mojo-test-runner` - Test execution patterns

## Next Steps After Rescue

1. ✅ All checks passing → Enable auto-merge
   ```bash
   gh pr merge --auto --rebase
   ```

2. Monitor for merge completion:
   ```bash
   gh pr view <PR_NUMBER>
   ```

3. Clean up local branches after merge:
   ```bash
   git branch -d <branch-name>
   ```

## Maintainer Notes

**Testing this skill:**
1. Find PRs with failing checks: `gh pr list --state open`
2. Identify failure patterns: `gh run view <RUN_ID> --log-failed`
3. Apply fixes systematically using this workflow
4. Verify all checks pass before moving to next PR

**Common edge cases:**
- PRs already merged (check with `gh pr list --state all`)
- Diverged branches (use `git pull --rebase`)
- Multiple rounds of CI failures (commit incrementally)
- Safety hooks blocking operations (use safer alternatives)
