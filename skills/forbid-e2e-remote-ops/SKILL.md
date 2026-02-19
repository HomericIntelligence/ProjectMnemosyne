# Skill: Forbid Remote Operations in E2E Tests

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Objective** | Prevent agents from performing remote Git operations during e2e tests and optimize worktree creation |
| **Outcome** | ✅ Success - Remote operations blocked, worktree creation optimized from 2 to 1 subprocess call |
| **PR** | [#643](https://github.com/HomericIntelligence/ProjectScylla/pull/643) |

## When to Use

Use this skill when:

- E2E test agents are pushing to remote repositories or creating real PRs during test runs
- You need to enforce test environment isolation and prevent unintended remote side effects
- Test workspaces need explicit safety constraints to prevent remote writes
- You want to optimize git worktree creation by reducing subprocess calls

**Trigger Conditions:**

- Agents running in test environments with `--dangerously-skip-permissions`
- Test CLAUDE.md files contain instructions that encourage git push/PR workflows
- Need to ensure test isolation without modifying core prompt blocks (for ablation studies)

## Problem Context

During e2e test execution, Claude Code agents were:

1. Pushing to remote branches (`git push origin <branch>`)
2. Creating real pull requests on GitHub (`gh pr create`)
3. Potentially modifying issues and PRs

This happened because:

- Test workspaces included CLAUDE.md prompt blocks (B02, B18) with "correct workflow" instructions
- Agents with `--dangerously-skip-permissions` followed these instructions literally
- No explicit test environment constraints existed to override workflow instructions

Additionally, worktree creation used a two-step process:

1. `git worktree add -b <branch> <path>`
2. `git checkout <commit>` (separate subprocess)

This was inefficient when git supports passing the commit directly to worktree add.

## Verified Workflow

### 1. Add Test Environment Constraints to Resource Suffix

**File:** `scylla/e2e/tier_manager.py` (~line 609)

**Approach:** Inject safety constraints into the resource suffix (appended to every composed CLAUDE.md)

```python
# Test environment constraints (always applied)
test_constraints = (
    "\n\n## Test Environment Constraints\n\n"
    "**CRITICAL: This is a test environment. "
    "The following WRITE operations are FORBIDDEN:**\n\n"
    "- DO NOT run `git push` or push to any remote repository\n"
    "- DO NOT create pull requests (`gh pr create` or similar)\n"
    "- DO NOT comment on or modify GitHub issues or PRs\n"
    "- DO NOT delete remote branches (`git push origin --delete`)\n"
    "- All changes must remain LOCAL to this workspace - no remote writes\n"
    "- Read-only remote operations (`git fetch`, `git pull`) are permitted\n"
)

# Append to resource suffix
return base_message + test_constraints + cleanup_instructions
```

**Why This Works:**

- Appended to resource suffix, not embedded in prompt blocks
- Preserves prompt blocks for ablation testing
- Universal application to all test workspaces
- Explicit and prominent (CRITICAL warning)

### 2. Optimize Worktree Creation (Single Step)

**Files:**

- `scylla/e2e/workspace_setup.py` (line 142-192)
- `scylla/e2e/workspace_manager.py` (line 264-296)

**Before (2 subprocess calls):**

```python
# Step 1: Create worktree
worktree_cmd = ["git", "-C", str(base_repo), "worktree", "add", "-b", branch_name, str(workspace_abs)]
subprocess.run(worktree_cmd, ...)

# Step 2: Checkout commit separately
if task_commit:
    checkout_cmd = ["git", "-C", str(workspace_abs), "checkout", task_commit]
    subprocess.run(checkout_cmd, ...)
```

**After (1 subprocess call):**

```python
# Single step: Create worktree at specific commit
worktree_cmd = ["git", "-C", str(base_repo), "worktree", "add", "-b", branch_name, str(workspace_abs)]
if task_commit:
    worktree_cmd.append(task_commit)  # git worktree add supports start-point
subprocess.run(worktree_cmd, ...)
```

**Benefits:**

- 50% reduction in subprocess calls per worktree
- Simpler code (fewer conditional branches)
- Atomic operation (less chance of partial state)
- Works in both normal and recovery paths

### 3. Update Tests to Verify New Behavior

**File:** `tests/unit/e2e/test_tier_manager.py`

```python
# Define constants for test assertions
TEST_CONSTRAINTS = (
    "\n\n## Test Environment Constraints\n\n"
    "**CRITICAL: This is a test environment. "
    "The following WRITE operations are FORBIDDEN:**\n\n"
    # ... full text ...
)

CLEANUP_INSTRUCTIONS = (
    "\n\n## Cleanup Requirements\n\n"
    # ... full text ...
)

SUFFIX_TAIL = TEST_CONSTRAINTS + CLEANUP_INSTRUCTIONS

# Update all test assertions
expected = "Maximize usage of all available tools to complete this task." + SUFFIX_TAIL
```

**File:** `tests/unit/e2e/test_workspace_manager.py`

```python
# Rename: test_worktree_separate_checkout → test_worktree_includes_commit
def test_worktree_includes_commit(self, tmp_path: Path) -> None:
    """Test that git worktree add includes commit hash directly."""
    # ...
    assert mock_run.call_count == 1  # Only 1 subprocess call
    worktree_cmd = mock_run.call_args_list[0][0][0]
    assert "abc123" in worktree_cmd  # Commit in worktree command
```

## Failed Attempts

### ❌ Attempt 1: Modify Prompt Blocks Directly

**What was tried:** Considered adding test constraints inside CLAUDE.md prompt blocks (B02, B18)

**Why it failed:**

- Would contaminate ablation study by modifying prompt content
- Different tiers use different prompt blocks - would need tier-specific logic
- Defeats the purpose of testing prompt effectiveness in isolation

**Lesson:** Safety constraints should be universal and separate from experimental variables

### ❌ Attempt 2: Use Git Hooks to Block Remote Operations

**What was considered:** Configure git hooks in test workspaces to reject push attempts

**Why it wasn't pursued:**

- Hooks run after the command is attempted (not preventive enough)
- Doesn't prevent `gh pr create` or GitHub API calls
- Harder to debug when hooks silently fail
- Better to prevent at the instruction level than execution level

**Lesson:** Explicit instructions are clearer than implicit enforcement mechanisms

## Results & Parameters

### Verification Commands

```bash
# Run unit tests
pixi run python -m pytest tests/unit/e2e/test_tier_manager.py -v
pixi run python -m pytest tests/unit/e2e/test_workspace_manager.py -v

# Run pre-commit hooks
pre-commit run --all-files

# Verify suffix output
python3 -c "
from pathlib import Path
from scylla.e2e.models import SubTestConfig
from scylla.e2e.tier_manager import TierManager

subtest = SubTestConfig(id='01', name='Test', description='Test', resources={'tools': {'enabled': 'all'}})
manager = TierManager(Path('/tmp'))
print(manager.build_resource_suffix(subtest))
"
```

### Test Results

- ✅ All 56 unit tests passed
- ✅ Pre-commit hooks passed (formatting, linting)
- ✅ Manual verification confirmed test constraints in output
- ✅ Worktree commands verified to include commit hash

### Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Subprocess calls per worktree | 2 | 1 | 50% reduction |
| Lines of code (worktree logic) | ~60 | ~20 | 67% reduction |
| Test coverage | 100% | 100% | Maintained |

### Configuration

**Files Modified:**

- `scylla/e2e/tier_manager.py` - Add test constraints to suffix
- `scylla/e2e/workspace_setup.py` - Optimize worktree creation
- `scylla/e2e/workspace_manager.py` - Optimize worktree creation
- `tests/unit/e2e/test_tier_manager.py` - Update test constants
- `tests/unit/e2e/test_workspace_manager.py` - Update worktree test

**Key Design Decision:**
Append constraints to resource suffix (not prompt blocks) to preserve ablation study integrity while ensuring universal safety.

## Key Takeaways

1. **Separation of Concerns:** Test safety constraints should be separate from experimental variables (prompt blocks)
2. **Explicit > Implicit:** Clear instructions work better than hidden enforcement mechanisms
3. **Read the Docs:** Git worktree supports start-point argument - RTFM saves refactoring
4. **Test Constants:** Extract expected strings to constants to avoid duplication and ensure consistency
5. **Atomic Operations:** Single-step operations are simpler and more reliable than multi-step processes

## Related Skills

- `centralize-repo-clones` - Centralized repository management for e2e tests
- `git-worktree-management` - General git worktree best practices
- `e2e-test-safety` - Broader e2e test isolation patterns

## References

- Git worktree documentation: `git worktree add --help`
- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/643>
- Commit: `faaa6f4` - feat(e2e): Forbid remote operations in tests and optimize worktree creation
