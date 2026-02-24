# Session Notes: Forbid E2E Remote Operations

## Session Context

**Date:** 2026-02-14
**Duration:** ~1 hour
**Objective:** Implement plan to forbid remote Git operations in e2e tests and fix worktree commit checkout

## Implementation Log

### Phase 1: Understanding Current State (10 min)

Read key files to understand implementation:

- `scylla/e2e/tier_manager.py:609-617` - Resource suffix generation
- `scylla/e2e/workspace_setup.py:142-192` - Worktree creation logic
- `scylla/e2e/workspace_manager.py:264-296` - Workspace manager worktree
- `tests/unit/e2e/test_tier_manager.py` - Suffix tests
- `tests/unit/e2e/test_workspace_manager.py:413-447` - Worktree tests

**Key Observations:**

- Resource suffix was only appending cleanup instructions
- Worktree creation had explicit comments saying "Do NOT add commit to worktree command"
- Tests expected 2 subprocess calls (worktree add + checkout)

### Phase 2: Add Test Environment Constraints (15 min)

**Change 1:** Modified `tier_manager.py:build_resource_suffix()`

Added test constraints section before cleanup instructions:

```python
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
```

**Rationale:** Appending to suffix keeps prompt blocks pure for ablation testing while adding universal safety.

### Phase 3: Optimize Worktree Creation (20 min)

**Change 2:** Modified worktree creation in 3 files

**workspace_setup.py:**

- Line 142-152: Added commit to worktree_cmd if task_commit exists
- Line 172-192: Removed separate checkout subprocess call
- Line 246-258: Removed checkout from recovery path

**workspace_manager.py:**

- Line 264-273: Added commit to worktree_cmd if self.commit exists
- Line 287-296: Removed separate checkout subprocess call

**Key Insight:** Git worktree supports `git worktree add -b <branch> <path> <commit>` syntax natively

### Phase 4: Update Tests (15 min)

**Change 3:** Updated test files

**test_tier_manager.py:**

- Added TEST_CONSTRAINTS constant
- Created SUFFIX_TAIL = TEST_CONSTRAINTS + CLEANUP_INSTRUCTIONS
- Replaced all CLEANUP_INSTRUCTIONS with SUFFIX_TAIL in assertions

**test_workspace_manager.py:**

- Renamed test_worktree_separate_checkout → test_worktree_includes_commit
- Changed assertion from 2 subprocess calls to 1
- Verified commit is in worktree command (not separate checkout)

### Phase 5: Verification (10 min)

**Tests:**

```bash
# Unit tests - 56/56 passed
pixi run python -m pytest tests/unit/e2e/test_tier_manager.py -v  # 37 passed
pixi run python -m pytest tests/unit/e2e/test_workspace_manager.py -v  # 19 passed

# Pre-commit hooks - all passed
pre-commit run --all-files
```

**Manual Verification:**

```python
# Verified test constraints in suffix output
python3 -c "from scylla.e2e.tier_manager import TierManager; ..."
# Output included "Test Environment Constraints" section ✓

# Verified worktree command structure
python3 -c "worktree_cmd = [...]; if commit: worktree_cmd.append(commit)"
# Output: git -C /base worktree add -b branch /path abc123 ✓
```

### Phase 6: Code Quality (5 min)

**Linting Issue:** Line too long in tier_manager.py:612

```python
# Before (105 chars)
"**CRITICAL: This is a test environment. The following WRITE operations are FORBIDDEN:**\n\n"

# After (split into 2 lines)
"**CRITICAL: This is a test environment. "
"The following WRITE operations are FORBIDDEN:**\n\n"
```

Updated both implementation and test constant to match.

## Technical Details

### Git Worktree Command Syntax

**Before (2 steps):**

```bash
git worktree add -b my-branch /path/to/workspace
cd /path/to/workspace && git checkout abc123
```

**After (1 step):**

```bash
git worktree add -b my-branch /path/to/workspace abc123
```

The `<commit-ish>` argument is supported natively by git worktree add.

### Test Constraint Placement

**Why append to suffix instead of modifying prompt blocks?**

1. **Ablation Study Integrity:** Prompt blocks (B02, B18) are experimental variables
2. **Universal Application:** Suffix is appended to ALL composed CLAUDE.md files
3. **Clear Separation:** Safety constraints separate from experimental content
4. **Maintainability:** Single location for test environment rules

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `scylla/e2e/tier_manager.py` | +13 | Add test constraints to suffix |
| `scylla/e2e/workspace_setup.py` | -44 +4 | Optimize worktree creation |
| `scylla/e2e/workspace_manager.py` | -12 +2 | Optimize worktree creation |
| `tests/unit/e2e/test_tier_manager.py` | +18, ~12 | Add constants, update assertions |
| `tests/unit/e2e/test_workspace_manager.py` | -16 +7 | Update worktree test |

**Net Change:** +52 insertions, -85 deletions (33 lines removed)

## Commit & PR

**Branch:** `forbid-remote-ops-e2e-tests`

**Commit:** `faaa6f4`

```
feat(e2e): Forbid remote operations in tests and optimize worktree creation

1. Add test environment constraints to prevent remote operations
2. Optimize worktree creation to single-step process
3. Update tests to match new behavior

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**PR:** [#643](https://github.com/HomericIntelligence/ProjectScylla/pull/643)

- Auto-merge enabled (rebase)
- Will merge when CI passes

## Lessons Learned

1. **RTFM First:** Could have saved time by checking git worktree docs upfront
2. **Test Constants Matter:** Extracting SUFFIX_TAIL constant made tests cleaner and more maintainable
3. **Safety > Convenience:** Explicit prohibitions prevent unintended side effects
4. **Separation of Concerns:** Keep experimental variables separate from safety constraints
5. **Atomic Operations:** Single-step operations are simpler and less error-prone

## Next Steps

If this pattern works well, consider:

- Adding similar constraints for other risky operations (database writes, API calls to production)
- Creating a general "test environment safety framework" skill
- Documenting test isolation patterns in developer guide
