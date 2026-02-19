# Fix implement_issues.py Automation Pipeline

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Objective** | Fix failing automation pipeline for GitHub issue implementation |
| **Outcome** | ✅ Fully robust pipeline with fallback logic |
| **PR** | #624 (6 commits) |

## Overview

The `implement_issues.py` script automates GitHub issue implementation by:

1. Creating git worktrees
2. Running Claude Code to implement the issue
3. Creating commits and PRs

Multiple failure modes were discovered and fixed through iterative debugging.

## When to Use This Skill

Invoke when:

- `implement_issues.py` fails with git errors
- Claude Code exits with non-zero status
- Worktree creation fails with "branch already exists"
- Files show truncated paths in git operations
- PR creation fails after successful implementation

## Verified Workflow

### 1. Fix Git Status Parsing Bug

**Problem**: Filenames truncated (`ests/unit/...` instead of `tests/unit/...`)

**Root Cause**: `line[3:].strip()` - the `.strip()` removed first character

**Solution**:

```python
# WRONG:
filename_part = line[3:].strip()  # Removes first char!

# RIGHT:
filename_part = line[3:]  # Position 3 is start of filename
```

**Git status format**: `"XY filename"` where X/Y are status codes, position 2 is space, position 3+ is filename.

### 2. Reuse Existing Branches on Retry

**Problem**: `git worktree add -b branch` fails if branch exists from previous run

**Solution**:

```python
# Check if branch exists first
result = run(
    ["git", "rev-parse", "--verify", branch_name],
    capture_output=True,
    check=False,
)
branch_exists = result.returncode == 0

if branch_exists:
    # Reuse existing branch (no -b flag)
    run(["git", "worktree", "add", worktree_path, branch_name])
else:
    # Create new branch
    run(["git", "worktree", "add", "-b", branch_name, worktree_path, base_branch])
```

### 3. Add Robust Fallback Logic

**Problem**: Pipeline failed if Claude didn't push or create PR

**Solution**: Verify-and-fallback pattern

```python
def _ensure_pr_created(issue_number, branch_name, worktree_path):
    # 1. Verify commit exists (MUST have this)
    if not commit_exists:
        raise RuntimeError("No commit created")

    # 2. Push if not already pushed (FALLBACK)
    if not branch_on_remote:
        run(["git", "push", "-u", "origin", branch_name])

    # 3. Create PR if doesn't exist (FALLBACK)
    if not pr_exists:
        pr_number = self._create_pr(issue_number, branch_name)

    return pr_number
```

**Key insight**: Only fail on truly unrecoverable errors (no commit). Everything else can be fixed automatically.

### 4. Move Git Operations to Claude Agent

**Updated Prompt**:

```markdown
**Git Workflow:**
After implementation is complete and tests pass:
1. Create a git commit using the /commit-commands:commit skill
2. Push the changes to origin
3. Create a pull request using the /commit-commands:commit-push-pr skill
```

**File Handling Guidelines**:

```markdown
**File Handling:**
- DO NOT create backup files (.orig, .bak, .swp, etc.)
- Clean up any backup files before finishing
```

### 5. Add Critical CLI Flags

**Required flags** for `claude` command:

```python
[
    "claude",
    prompt_file,
    "--output-format", "json",
    "--permission-mode", "dontAsk",  # CRITICAL: Prevents hanging
    "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",  # CRITICAL: Explicit permissions
]
```

### 6. Fix Import Errors

**Problem**: `cannot import name 'gh_call'`

**Solution**: Use private function `_gh_call` and parse JSON:

```python
from .github_api import _gh_call

result = _gh_call(["pr", "list", "--head", branch_name, "--json", "number"])
pr_data = json.loads(result.stdout)  # Must parse stdout
```

## Failed Attempts

### ❌ Strict Verification Without Fallbacks

**What we tried**:

```python
# Fail if branch not pushed
if not branch_on_remote:
    raise RuntimeError("Branch not pushed")
```

**Why it failed**: Claude sometimes completes implementation but forgets to push/create PR. This made the pipeline too fragile.

**Lesson**: Automation should be resilient. If we can fix it automatically, do it.

### ❌ Filtering Backup Files in Script

**What we tried**: Skip `.orig`, `.bak` files in git status parsing

**Why it failed**: Added complexity to parsing logic. Also didn't prevent files from being created.

**Lesson**: Better to instruct Claude in the prompt to not create backup files than to filter them after the fact.

### ❌ Using `.strip()` on Git Status Output

**What we tried**: `line[3:].strip()` to clean up filenames

**Why it failed**: `.strip()` removes leading whitespace, but when filename starts immediately (no leading space), it removes the first character.

**Lesson**: Understand the exact format before parsing. Git status is predictable - don't add unnecessary operations.

## Results & Parameters

**All tests pass**: 199 automation tests ✅

**Key configurations**:

```python
# Worktree settings
base_dir = repo_root / ".worktrees"
branch_name = f"{issue_number}-auto-impl"

# Claude Code timeout
timeout = 1800  # 30 minutes

# Permission mode (CRITICAL)
--permission-mode dontAsk

# Allowed tools (CRITICAL)
--allowedTools Read,Write,Edit,Glob,Grep,Bash
```

**Error logging added**:

```python
except subprocess.CalledProcessError as e:
    logger.error(f"Claude Code failed")
    logger.error(f"Exit code: {e.returncode}")
    if e.stdout:
        logger.error(f"Stdout: {e.stdout[:1000]}")
    if e.stderr:
        logger.error(f"Stderr: {e.stderr[:1000]}")
```

## Implementation Files Changed

- `scylla/automation/implementer.py` - Main automation logic
- `scylla/automation/worktree_manager.py` - Branch reuse logic
- `scylla/automation/prompts.py` - Claude instructions
- `scylla/automation/models.py` - Added `body` field to IssueInfo
- `scylla/automation/github_api.py` - Used existing `_gh_call`
- `tests/unit/automation/test_*.py` - Updated tests

## Related Skills

- None (this is a new pattern for ProjectScylla)

## Future Improvements

1. Add retry logic for transient git failures
2. Cache PR existence checks to avoid repeated gh calls
3. Add metrics collection (time per phase, success rate)
4. Support for stacked PRs (multiple dependent issues)
