---
name: "Fix Tests After Config Refactor"
description: "Fix Tests After Config Refactor"
category: testing
date: 2026-01-17
user-invocable: false
---
# Fix Tests After Config Refactor

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-17 |
| Objective | | Field | Value | |-------|-------| | **Date** | 2026-01-17 | | **Objective** | Fix failing unit tests after config structure refactoring | |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| **Date** | 2026-01-17 |
| **Objective** | Fix failing unit tests after config structure refactoring |
| **Outcome** | ✅ SUCCESS - Fixed 5 failing tests in tier_manager |
| **Impact** | Unblocked 2 PRs with CI test failures |

## When to Use This Skill

Use this skill when:

1. **CI tests fail after merging a refactoring PR** that changes:
   - Configuration file structure or location
   - Directory organization
   - Path resolution logic
   - Centralized vs distributed configs

2. **Test failures show `assert 0 == 1` or `assert len([]) == 1`** patterns
   - Tests expecting to find files/configs but finding nothing
   - Discovery/search methods returning empty results

3. **Tests are creating temporary directory structures** that need updating:
   - Old structure no longer matches new code paths
   - Hardcoded path assumptions broken by refactoring

4. **Multiple PRs fail with same test failures** after base branch update:
   - Indicates tests need updating for merged changes
   - Not specific to any PR's changes

## Problem Indicators

### Symptoms
- CI tests pass on old commits but fail on new ones
- Local tests pass on `main` before pull, fail after pull
- Multiple unrelated PRs suddenly have same test failures
- Error messages show discovery/loading methods finding nothing

### Example Error Pattern
```python
def test_root_level_tools_mapped(self, tmp_path: Path) -> None:
    ...
    subtests = manager._discover_subtests(TierID.T5, tier_dir)

>   assert len(subtests) == 1
E   assert 0 == 1
E    +  where 0 = len([])
```

### Root Cause Investigation
1. Check recent merge commits on main branch
2. Look for architecture/refactoring changes
3. Compare old vs new directory structures
4. Trace path resolution in updated code

## Verified Workflow

### 1. Identify the Breaking Change

**Check recent commits:**
```bash
git log --oneline -10
```

**Look for refactoring commits:**
- "refactor:", "feat(architecture):", "fix(structure):" prefixes
- Changes to config loading, path resolution, directory structure

**Example from this session:**
```
6f2a828 feat(architecture): unify config structure and fix documentation
```

### 2. Understand the Structural Change

**Compare directory structures:**
```bash
# Old structure (before refactor)
tests/fixtures/tests/test-XXX/
  ├── t0/
  │   ├── 00-empty/
  │   │   └── config.yaml
  │   └── 01-vanilla/
  │       └── config.yaml

# New structure (after refactor)
tests/claude-code/shared/subtests/
  ├── t0/
  │   ├── 00-empty.yaml
  │   └── 01-vanilla.yaml
```

**Key differences:**
- Centralized vs distributed locations
- File naming: `NN-name.yaml` vs `NN-name/config.yaml`
- Path navigation changes in discovery code

### 3. Trace Path Resolution in Code

**Find the discovery/loading method:**
```bash
grep -n "def _discover_subtests" scylla/e2e/tier_manager.py
```

**Analyze path construction:**
```python
def _get_shared_dir(self) -> Path:
    """Get path to the shared resources directory."""
    # Navigate from tiers_dir to shared
    return self.tiers_dir.parent.parent.parent / "claude-code" / "shared"
```

**Understand navigation:**
- `tiers_dir` = `tests/fixtures/tests/test-001`
- `.parent.parent.parent` = `tests/`
- Result: `tests/claude-code/shared/`

### 4. Update Test Setup to Match New Structure

**Before (broken):**
```python
def test_root_level_tools_mapped(self, tmp_path: Path) -> None:
    # Create OLD structure
    tier_dir = tmp_path / "t5"
    tier_dir.mkdir()
    subtest_dir = tier_dir / "01-test"
    subtest_dir.mkdir()

    # Write config to OLD location
    config_file = subtest_dir / "config.yaml"
    config_file.write_text(yaml.safe_dump({...}))

    # This fails - can't find configs in OLD structure
    manager = TierManager(tmp_path)
    subtests = manager._discover_subtests(TierID.T5, tier_dir)
```

**After (fixed):**
```python
def test_root_level_tools_mapped(self, tmp_path: Path) -> None:
    # Create NEW structure matching TierManager expectations
    tiers_dir = tmp_path / "tests" / "fixtures" / "tests" / "test-001"
    tiers_dir.mkdir(parents=True)

    # Create shared directory
    shared_dir = tmp_path / "tests" / "claude-code" / "shared" / "subtests" / "t5"
    shared_dir.mkdir(parents=True)

    # Write config to NEW location with NEW naming
    config_file = shared_dir / "01-test.yaml"
    config_file.write_text(yaml.safe_dump({...}))

    # This works - configs in NEW structure
    manager = TierManager(tiers_dir)
    tier_dir = tiers_dir / "t5"  # Legacy param, not used
    subtests = manager._discover_subtests(TierID.T5, tier_dir)
```

### 5. Apply Pattern to All Failing Tests

**Fix all tests in the affected class:**
```bash
# Run the failing test class
pixi run pytest tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping -xvs

# Fix each test method with same pattern
# All need: proper tiers_dir path + shared directory structure
```

### 6. Verify Fixes Locally

**Test the specific class:**
```bash
pixi run pytest tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping -xvs
```

**Expected output:**
```
============================= test session starts ==============================
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_tools_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_mcp_servers_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_agents_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_skills_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_resources_field_takes_precedence PASSED

============================== 5 passed in 0.21s ===============================
```

### 7. Update All Affected PRs

**For each PR with test failures:**
```bash
# Switch to PR branch
git switch <pr-branch>

# Add the test fixes
git add tests/unit/e2e/test_tier_manager.py

# Commit with clear message
git commit -m "fix(tests): update tier_manager tests for new config structure"

# Push to update PR
git push
```

**Or cherry-pick from main:**
```bash
# After merging fix to main
git switch <pr-branch>
git cherry-pick <fix-commit-hash>
git push
```

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Attempt 1: Creating Files in tmp_path Directly

**What was tried:**
```python
# Just create files in tmp_path expecting TierManager to find them
shared_dir = tmp_path / "tests" / "claude-code" / "shared" / "subtests" / "t5"
shared_dir.mkdir(parents=True)

manager = TierManager(tmp_path)  # ❌ Wrong: tmp_path isn't a valid tiers_dir
```

**Why it failed:**
- `TierManager._get_shared_dir()` navigates from `tiers_dir` using `.parent.parent.parent`
- When `tiers_dir = tmp_path`, navigation goes outside the test directory
- Method looks for `tmp_path.parent.parent.parent / "claude-code"` which doesn't exist

**Lesson learned:**
Must create the FULL directory structure that matches what the code expects, including the intermediate directories used for navigation.

### ❌ Attempt 2: Only Fixing One Test

**What was tried:**
- Fixed `test_root_level_tools_mapped`
- Left other 4 tests in same class unchanged

**Why it failed:**
- All 5 tests had the same issue
- CI still failed because other tests in class still broken
- Partial fix doesn't help PR status

**Lesson learned:**
When multiple tests fail for the same reason, fix all of them together in one commit.

### ❌ Attempt 3: Assuming Docker Tests Were Related

**What was tried:**
- Spent time investigating `test_judge_container.py` failures
- Tried to understand why mock wasn't working

**Why it failed:**
- These were separate pre-existing failures
- Not related to config structure changes
- Not blocking the PRs (were already failing on main)

**Lesson learned:**
Distinguish between:
- **PR-specific failures**: Only fail on this PR, must fix
- **Pre-existing failures**: Already fail on main, not this PR's responsibility
- Test on main branch first to identify pre-existing issues

## Results & Parameters

### Tests Fixed

**File**: `tests/unit/e2e/test_tier_manager.py`

| Test | Status | Changes |
|------|--------|---------|
| `test_root_level_tools_mapped` | ✅ PASS | Updated directory structure |
| `test_root_level_mcp_servers_mapped` | ✅ PASS | Updated directory structure |
| `test_root_level_agents_mapped` | ✅ PASS | Updated directory structure |
| `test_root_level_skills_mapped` | ✅ PASS | Updated directory structure |
| `test_resources_field_takes_precedence` | ✅ PASS | Updated directory structure |

### Directory Structure Pattern

**Template for test setup:**
```python
def test_something(self, tmp_path: Path) -> None:
    # 1. Create tiers_dir matching expected path structure
    tiers_dir = tmp_path / "tests" / "fixtures" / "tests" / "test-001"
    tiers_dir.mkdir(parents=True)

    # 2. Create shared directory for configs
    shared_dir = tmp_path / "tests" / "claude-code" / "shared" / "subtests" / "<tier>"
    shared_dir.mkdir(parents=True)

    # 3. Write config with new naming convention
    config_file = shared_dir / "NN-name.yaml"  # NOT NN-name/config.yaml
    config_file.write_text(yaml.safe_dump({...}))

    # 4. Create TierManager with proper tiers_dir
    manager = TierManager(tiers_dir)  # NOT tmp_path

    # 5. Call discovery method
    tier_dir = tiers_dir / "<tier>"  # Legacy param
    results = manager._discover_subtests(TierID.<TIER>, tier_dir)
```

### Commits Created

| Branch | Commit | Status |
|--------|--------|--------|
| `skill/architecture/unify-config-structure` | `caa34c1` | Merged to main |
| `skill/debugging/e2e-path-resolution-fix` | `b57fce8` | Cherry-picked |

### PRs Unblocked

- **PR #186**: fix(e2e): resolve workspace paths to absolute before subprocess execution
- **PR #187**: feat(skills): add e2e-path-resolution-fix debugging skill

## Key Insights

### 1. Path Navigation Dependencies

When code navigates paths using `.parent` chains, tests MUST create the full directory structure:
```python
# If code does: tiers_dir.parent.parent.parent / "claude-code"
# Tests must create: tmp_path / "tests" / "fixtures" / "tests" / "test-001"
# So navigation works: test-001 -> tests -> fixtures -> tests -> claude-code
```

### 2. Test Isolation vs Structure Realism

Balance between:
- **Test isolation**: Using `tmp_path` for clean test environment
- **Structure realism**: Matching real directory hierarchy for path navigation

Solution: Create realistic structure INSIDE `tmp_path`

### 3. Config Migration Patterns

When centralizing configs, update both:
1. **Production code**: New discovery/loading logic
2. **Test code**: New directory structure in test setup

Don't forget tests!

### 4. Pre-existing Failure Identification

Always test on main branch first:
```bash
git switch main
git pull
pixi run pytest <failing-test> -xvs
```

If it fails on main → Pre-existing, not your PR's fault
If it passes on main → Your PR introduced it, must fix

### 5. Cherry-Pick for Multiple PRs

When same fix needed across multiple PRs:
```bash
# Fix on one branch
git switch pr-branch-1
# ... make fixes ...
git commit -m "fix: ..."
git push

# Cherry-pick to other branches
git switch pr-branch-2
git cherry-pick <commit-hash>
git push
```

## Related Skills

- `e2e-path-resolution-fix` - Fixing path resolution bugs in E2E framework
- `unify-config-structure` - The refactoring that required these test fixes
- `debug-evaluation-logs` - Patterns for diagnosing test failures

## Testing Commands

### Run Specific Test Class
```bash
pixi run pytest tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping -xvs
```

### Run Single Test
```bash
pixi run pytest tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_tools_mapped -xvs
```

### Check Test on Main Branch
```bash
git switch main
git pull
pixi run pytest <test-path> -xvs
```

### View CI Logs for Failed Tests
```bash
gh pr checks <pr-number> --watch=false
gh run view <run-id> --log-failed | grep -A 50 "FAILED"
```

## Prevention

### For Refactoring PRs

When making structural changes:
1. **Identify affected tests** before committing
2. **Update tests in same PR** as the refactoring
3. **Run full test suite** before pushing
4. **Document structure changes** in PR description

### For Test Maintainability

1. **Avoid hardcoded paths** in tests when possible
2. **Use helper functions** for common directory structures
3. **Document path assumptions** in test comments
4. **Keep tests close to production** structure

### Example Helper Function

```python
def create_tier_test_structure(tmp_path: Path, tier_id: str) -> tuple[Path, Path]:
    """Create standard directory structure for tier tests.

    Returns:
        (tiers_dir, shared_dir) tuple for test setup
    """
    tiers_dir = tmp_path / "tests" / "fixtures" / "tests" / "test-001"
    tiers_dir.mkdir(parents=True)

    shared_dir = tmp_path / "tests" / "claude-code" / "shared" / "subtests" / tier_id
    shared_dir.mkdir(parents=True)

    return tiers_dir, shared_dir
```

Usage:
```python
def test_something(self, tmp_path: Path) -> None:
    tiers_dir, shared_dir = create_tier_test_structure(tmp_path, "t5")
    config_file = shared_dir / "01-test.yaml"
    # ... rest of test
```
