# Skill: Fix CI Test Failures

| Property | Value |
|----------|-------|
| **Date** | 2026-01-17 |
| **Objective** | Fix 6 unit tests passing locally but failing in CI due to environment differences |
| **Outcome** | ✅ All 6 tests fixed - absolute symlinks → relative, mock bypassed methods |
| **Context** | PR #191 had CI failures; all tests passed locally but 6 failed in GitHub Actions |

## When to Use This Skill

Use this skill when:
- Tests pass locally but fail in CI/GitHub Actions
- Error messages mention "file not found" for symlinked files
- Mock objects aren't being used despite being configured
- Docker images or executables are missing in CI environment
- Absolute paths appear in test fixtures or configuration

**Key Indicators**:
- Same test suite: 1037 tests pass locally, 1031 pass in CI (6 failures)
- Error: `Unable to find image 'scylla-runner:latest'` (but test uses mocks)
- Error: `assert False` where `False = isinstance(None, ModelConfig)` (file not found)

## Verified Workflow

### 1. Identify Root Causes

**Compare local vs CI failures:**
```bash
# Check CI logs
gh pr checks <pr-number>
gh run view <run-id> --log-failed | grep "FAILED"

# Check if main branch has same failures (pre-existing issues)
gh run list --branch main --limit 3
```

**Common patterns**:
- Symlinks with absolute paths (`/home/user/...`)
- Mocks on wrong method (mocking `executor.run()` when code calls `_run_with_volumes()`)
- Missing Docker images in CI environment

### 2. Fix Symlink Issues

**Problem**: Absolute symlinks break in CI
```bash
# Before (broken in CI)
/home/mvillmow/ProjectScylla/config/models/_test-model.yaml

# After (works everywhere)
../../../../config/models/_test-model.yaml
```

**Fix**:
```bash
cd tests/fixtures/config/models
rm test-model.yaml test-model-2.yaml
ln -s ../../../../config/models/_test-model.yaml test-model.yaml
ln -s ../../../../config/models/_test-model-2.yaml test-model-2.yaml

# Verify symlink works
cat test-model.yaml  # Should show file content
```

### 3. Fix Mock Bypass Issues

**Problem**: Test mocks `executor.run()` but code calls `_run_with_volumes()` directly

**Diagnosis**:
```python
# Code inspection reveals bypass
def run_judge(self, config):
    # This bypasses self.executor!
    result = self._run_with_volumes(...)
```

**Fix**:
```python
# Before (doesn't work)
mock_executor = MagicMock()
mock_executor.run.return_value = ContainerResult(...)
manager = JudgeContainerManager(executor=mock_executor)

# After (works)
@patch.object(JudgeContainerManager, "_run_with_volumes")
def test_run_success(self, mock_run_with_volumes: MagicMock, tmp_path: Path):
    mock_run_with_volumes.return_value = ContainerResult(...)
    manager = JudgeContainerManager()
    result = manager.run_judge(config)
```

### 4. Verify Fixes

```bash
# Test all previously failing tests
pixi run pytest \
  tests/unit/executor/test_judge_container.py::TestJudgeContainerManagerRunJudge::test_run_success \
  tests/unit/executor/test_judge_container.py::TestJudgeContainerManagerRunJudge::test_run_timeout \
  tests/unit/test_config_loader.py::TestConfigLoaderModel::test_load_model \
  tests/unit/test_config_loader.py::TestConfigLoaderModel::test_load_all_models \
  tests/unit/test_config_loader.py::TestConfigLoaderMerged::test_load_merged_with_model \
  tests/unit/test_config_loader.py::TestConfigLoaderMerged::test_load_merged_with_test_override \
  -v

# Expected: 6 passed in <1s
```

### 5. Create Separate PR

```bash
git checkout -b fix/ci-test-failures
git add <fixed-files>
git commit -m "fix(tests): fix 6 CI test failures"
git push -u origin fix/ci-test-failures
gh pr create --title "fix(tests): fix 6 CI test failures" --body "..."
```

## Failed Attempts

### ❌ Attempt 1: Ignore the failures (assumed pre-existing)
**What we tried**: Check if main branch has same failures, assume they're pre-existing issues

**Why it failed**: While main DID have the same failures, this doesn't mean we shouldn't fix them. The PR should improve the codebase, not perpetuate existing issues.

**Lesson**: Pre-existing CI failures should be fixed in a separate PR, not ignored.

### ❌ Attempt 2: Mock the executor instead of the actual method
**What we tried**: Mock `executor.run()` to avoid Docker calls

**Why it failed**: The code doesn't use `self.executor.run()` - it calls `self._run_with_volumes()` directly via subprocess.

**Lesson**: Read the actual implementation to see what methods are called, don't assume based on the constructor parameter.

### ❌ Attempt 3: Skip tests when Docker image missing
**What we considered**: Add `@pytest.mark.skipif` to skip tests when `scylla-runner:latest` doesn't exist

**Why we didn't**: These are unit tests that should work with mocks. Skipping them would reduce test coverage. Proper mocking is the correct solution.

**Lesson**: Unit tests should never depend on external resources like Docker images.

## Results & Parameters

### Symlink Fixes
**Files changed**:
- `tests/fixtures/config/models/test-model.yaml`
- `tests/fixtures/config/models/test-model-2.yaml`

**Before**:
```bash
$ readlink tests/fixtures/config/models/test-model.yaml
/home/mvillmow/ProjectScylla/config/models/_test-model.yaml
```

**After**:
```bash
$ readlink tests/fixtures/config/models/test-model.yaml
../../../../config/models/_test-model.yaml
```

### Mock Fixes
**File changed**: `tests/unit/executor/test_judge_container.py`

**Before**:
```python
def test_run_success(self, tmp_path: Path) -> None:
    mock_executor = MagicMock()
    mock_executor.run.return_value = ContainerResult(...)
    manager = JudgeContainerManager(executor=mock_executor)
    result = manager.run_judge(config)
```

**After**:
```python
@patch.object(JudgeContainerManager, "_run_with_volumes")
def test_run_success(self, mock_run_with_volumes: MagicMock, tmp_path: Path) -> None:
    mock_run_with_volumes.return_value = ContainerResult(...)
    manager = JudgeContainerManager()
    result = manager.run_judge(config)
```

### Test Results
```
====== 6 passed in 0.27s ======
```

All tests now pass in both local and CI environments.

## Key Takeaways

1. **Symlinks must be relative** - Absolute paths break when workspace location changes
2. **Mock the actual method called** - Don't assume what gets called; read the code
3. **Separate PRs for separate concerns** - Don't mix feature work with CI fixes
4. **Pre-existing failures should be fixed** - Don't perpetuate technical debt
5. **Unit tests shouldn't depend on external resources** - Use mocks, not real Docker/images

## Port to ProjectMnemosyne

After merging this skill to ProjectScylla, copy to team knowledge base:

```bash
# Copy skill to ProjectMnemosyne
cp -r .claude-plugin/skills/fix-ci-test-failures \
  ../build/ProjectMnemosyne/skills/testing/

# Create PR in ProjectMnemosyne
cd ../build/ProjectMnemosyne
git checkout -b skill/testing/fix-ci-test-failures
git add skills/testing/fix-ci-test-failures
git commit -m "feat(skills): Add fix-ci-test-failures from ProjectScylla"
gh pr create --title "feat(skills): Add fix-ci-test-failures skill"
```
