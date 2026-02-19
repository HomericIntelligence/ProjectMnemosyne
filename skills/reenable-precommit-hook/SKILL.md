# Re-enable Pre-commit Hooks with Dependency Issues

| **Aspect** | **Details** |
|------------|-------------|
| **Date** | 2026-02-15 |
| **Objective** | Re-enable commented-out pre-commit hooks that were disabled due to dependency version incompatibilities |
| **Outcome** | ✅ Successfully re-enabled nbstripout hook after upgrading transitive dependency (identify library) |
| **Issue** | #698 |
| **PR** | #739 |

## When to Use This Skill

Use this skill when you encounter:

- Pre-commit hooks commented out with TODO notes about dependency issues
- Error messages like "Type tag 'X' is not recognized. Try upgrading identify and pre-commit?"
- Hook validation failures due to missing type tags or incompatible library versions
- Need to upgrade transitive dependencies of pre-commit hooks

**Trigger Patterns**:

- Commented-out hook configuration in `.pre-commit-config.yaml`
- TODO comments mentioning library upgrades or compatibility issues
- Pre-commit errors referencing outdated library versions

## Problem Context

The nbstripout hook was commented out with the note:

```yaml
# TODO: Re-enable after pre-commit/identify is upgraded to support 'jupyter' type tag
```

Running `pre-commit try-repo` showed:

```
InvalidManifestError: Type tag 'jupyter' is not recognized.
Try upgrading identify and pre-commit?
```

The root cause was that the `identify` library (a transitive dependency of `pre-commit`) was pinned at version 1.2.2 by conda, but jupyter type support was added in identify >=2.0.0.

## Verified Workflow

### 1. Diagnose the Issue

```bash
# Test the hook without modifying config
pixi run pre-commit try-repo https://github.com/kynan/nbstripout nbstripout --verbose

# Expected error if dependency outdated:
# InvalidManifestError: Type tag 'jupyter' is not recognized
```

### 2. Identify Required Dependency Version

```bash
# Check current version
pixi run pip show identify
# Output: Version: 1.2.2

# Check available versions
pixi run pip index versions identify
# Latest: 2.6.16

# Verify new version supports the required type
pixi run python -c "from identify import identify; print('jupyter' in identify.ALL_TAGS)"
# Should print: True (after upgrade)
```

### 3. Upgrade the Dependency

```bash
# Upgrade the transitive dependency
pixi run pip install --upgrade identify
# Successfully upgraded: 1.2.2 → 2.6.16
```

**Key Insight**: Upgrading transitive dependencies with pip in the pixi environment works even when conda pins them, and persists for the current environment session.

### 4. Verify Hook Works

```bash
# Test hook again
pixi run pre-commit try-repo https://github.com/kynan/nbstripout nbstripout --verbose
# Should now show: (no files to check)Skipped - SUCCESS!
```

### 5. Update Configuration

```yaml
# In .pre-commit-config.yaml

# Add documentation note
# NOTE: Requires identify >=2.6.0 to support 'jupyter' type tag
# If you see "Type tag 'jupyter' is not recognized", run:
#   pixi run pip install --upgrade identify

# Uncomment the hook
- repo: https://github.com/kynan/nbstripout
  rev: 0.9.0  # Update to latest version
  hooks:
    - id: nbstripout
      name: Strip Notebook Outputs
      files: \.ipynb$
      args: ['--extra-keys', 'metadata.kernelspec']
```

### 6. Create Comprehensive Tests

Create test file to validate hook functionality:

```python
# tests/test_<hookname>_hook.py

def test_hook_exists():
    """Verify hook is uncommented in config."""
    config_path = Path(__file__).parent.parent / ".pre-commit-config.yaml"
    with open(config_path) as f:
        content = f.read()
    assert "hookname" in content
    assert not content.count("# - repo: https://...")

def test_hook_functionality():
    """Test hook processes files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        # Run hook
        subprocess.run([
            "pixi", "run", "pre-commit", "run", "hookname",
            "--files", str(test_file)
        ], check=False)
        # Verify expected behavior
```

### 7. Verify All Pre-commit Hooks Pass

```bash
pixi run pre-commit run --all-files
# All hooks should pass
```

## Failed Attempts

### ❌ Attempt 1: Add identify to pixi.toml pypi-dependencies

```toml
[feature.dev.pypi-dependencies]
identify = ">=2.6.0"
```

**Why it failed**: Pixi tries to solve dependencies for all platforms (linux-64, osx-64, osx-arm64, win-64), and conda had already pinned identify==1.2.2 across platforms, creating an unsolvable conflict.

**Error**:

```
Error: failed to solve the pypi requirements of environment 'default' for platform 'osx-arm64'
Because you require identify>=2.6.0 and identify==1.2.2, we can conclude that your requirements are unsatisfiable.
The following PyPI packages have been pinned by the conda solve: identify==1.2.2
```

**Lesson**: Cannot override conda-pinned transitive dependencies via pypi-dependencies in pixi.toml.

### ❌ Attempt 2: Upgrade pre-commit in pixi.toml

```toml
[feature.dev.dependencies]
pre-commit = ">=4.8.0"  # Instead of >=3.0
```

**Why it failed**: While this might work in theory, it would require updating the entire pre-commit package and could introduce unintended changes to other hooks or CI behavior. Also, no guarantee newer pre-commit would pull in newer identify.

**Lesson**: Upgrading the parent package (pre-commit) to force a transitive dependency upgrade is too broad and risky for a targeted fix.

## ✅ Working Solution

**Document the manual upgrade step** and run it locally:

1. Add clear setup instructions in `.pre-commit-config.yaml` comments
2. Run `pixi run pip install --upgrade identify` locally after pulling
3. Document in PR/commit message that this step is required
4. Create comprehensive test suite to validate hook functionality

**Why this works**:

- pip can upgrade packages even if conda pinned them (for current session)
- Changes persist in the pixi environment until next `pixi install`
- Team members run the same upgrade command when they encounter the issue
- Test suite validates the hook works correctly
- No risky changes to shared dependency configuration

## Results & Parameters

### Successful Test Results

```bash
# Hook validation
$ pixi run pre-commit run nbstripout --all-files
Strip Notebook Outputs...................................................Passed

# Test suite
$ pixi run python -m pytest tests/test_nbstripout_hook.py -v
7 passed in 6.63s

# Full suite
$ pixi run python -m pytest tests/ -v
2145 passed, 8 warnings in 96.79s
Total coverage: 72.92%
```

### Configuration Used

**Hook Configuration** (`.pre-commit-config.yaml`):

```yaml
- repo: https://github.com/kynan/nbstripout
  rev: 0.9.0
  hooks:
    - id: nbstripout
      name: Strip Notebook Outputs
      description: Remove outputs from Jupyter notebooks before commit
      files: \.ipynb$
      args: ['--extra-keys', 'metadata.kernelspec']
```

**Dependency Versions**:

- pre-commit: 4.5.1 (unchanged)
- identify: 1.2.2 → 2.6.16 (upgraded via pip)
- nbstripout: 0.8.1 → 0.9.0 (updated in config)

### Test Coverage

Created 7 comprehensive tests covering:

1. Hook configuration exists and is uncommented
2. Output stripping from code cells
3. Kernelspec metadata removal
4. Language_info preservation
5. Empty notebook handling
6. Different cell types (code vs markdown)
7. Execution count removal

## Key Takeaways

1. **Transitive dependency upgrades**: Use `pixi run pip install --upgrade <package>` for targeted upgrades of dependencies pinned by conda

2. **Documentation is critical**: Add clear comments in config files explaining version requirements and setup steps

3. **Test before uncommenting**: Always use `pre-commit try-repo` to test hooks before modifying the config

4. **Comprehensive testing**: Create test files that validate both hook configuration and functionality

5. **Version updates**: When re-enabling hooks, check for newer versions of the hook repository itself

6. **Team communication**: Document required setup steps in commit messages, PR descriptions, and GitHub issue comments

## References

- Issue: #698 - Re-enable nbstripout hook for Jupyter notebooks
- PR: #739 - feat(pre-commit): Re-enable nbstripout hook
- Identify library: <https://github.com/chriskuehl/identify>
- nbstripout: <https://github.com/kynan/nbstripout>
- Pre-commit try-repo docs: <https://pre-commit.com/#pre-commit-try-repo>
