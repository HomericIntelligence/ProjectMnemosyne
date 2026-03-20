---
name: resolve-skipped-tests
description: 'Skill: resolve-skipped-tests. Use when working with resolve skipped
  tests.'
category: testing
date: 2026-01-01
version: 1.0.0
user-invocable: false
---
# Skill: Resolve Skipped Tests

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-15 |
| **Category** | testing |
| **Objective** | Remove pytest.skip guards by fixing underlying test configuration issues |
| **Outcome** | ✅ Successfully resolved 2 skipped integration tests |
| **Context** | Issue #670 - Clean up test suite by resolving skipped tests |

## When to Use This Skill

Use this skill when:

- ✅ You encounter `pytest.skip()` calls in test files
- ✅ Tests are conditionally skipped based on file existence checks
- ✅ Test configs are missing required fields (ValidationError from Pydantic models)
- ✅ Integration tests fail due to incorrect path calculations
- ✅ You need to clean up test suite to achieve zero skipped tests

**Don't use when:**

- Tests are legitimately platform-specific (e.g., Windows-only tests on Linux)
- Tests require external resources that may not be available (databases, APIs)
- Tests are marked for future implementation (xfail is more appropriate)

## Verified Workflow

### 1. Identify Skipped Tests

```bash
# Find all pytest.skip calls
grep -r "pytest.skip" tests/

# Run tests with skip summary
python3 -m pytest tests/ -v -rs
```

### 2. Analyze Root Causes

**Common patterns:**

| Pattern | Root Cause | Solution |
|---------|------------|----------|
| `if not file.exists(): pytest.skip()` | Missing config files or wrong paths | Fix paths or create missing files |
| `try: ... except Error: pytest.skip()` | Incomplete configs causing validation errors | Add missing required fields |
| Path calculation errors | Too few/many `.parent` calls | Count directory levels carefully |

### 3. Fix Configuration Issues

**Example 1: Missing Pydantic Model Fields**

```yaml
# BEFORE (causes ValidationError)
id: "001-test"
name: "Test Name"
# Missing 'language' field

# AFTER
id: "001-test"
name: "Test Name"
language: python  # Required by EvalCase model
```

**Example 2: Incorrect Path Calculation**

```python
# BEFORE - Resolves to tests/config/ (wrong)
config_dir = Path(__file__).parent.parent.parent / "config"

# AFTER - Resolves to project_root/config/ (correct)
config_dir = Path(__file__).parent.parent.parent.parent / "config"
```

**Verification technique:**

```python
# Add temporary debug to verify path
print(f"Config path: {config_dir}")
print(f"Exists: {config_dir.exists()}")
print(f"Expected file: {(config_dir / 'tiers' / 'tiers.yaml').exists()}")
```

### 4. Remove Skip Guards

**Pattern to remove:**

```python
# REMOVE THIS PATTERN
if not (config_dir / "file.yaml").exists():
    pytest.skip("Config not available")

# OR THIS PATTERN
try:
    result = load_config(...)
except ConfigError:
    pytest.skip("Config not available")
```

**Replace with direct assertions:**

```python
# Direct test - will fail if config is actually missing
result = load_config(...)
assert result.field == expected_value
```

### 5. Verify All Tests Pass

```bash
# Run specific modified tests
python3 -m pytest tests/unit/test_config_loader.py -v
python3 -m pytest tests/unit/executor/test_tier_config.py -v

# Verify no skips remain
grep -r "pytest.skip" tests/ || echo "No skips found ✅"
```

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Files Modified

```
tests/001-justfile-to-makefile/test.yaml
tests/unit/executor/test_tier_config.py
tests/unit/test_config_loader.py
```

### Test Results

```
# Before
- 2 tests conditionally skipped via pytest.skip()

# After
✅ tests/unit/test_config_loader.py - 32/32 passed
✅ tests/unit/executor/test_tier_config.py - 19/19 passed
✅ Zero pytest.skip calls remain
```

### Key Fixes

1. **Added missing Pydantic field:**

   ```yaml
   language: python  # Required by EvalCase model
   ```

2. **Fixed path calculation:**

   ```python
   # Changed from 3 to 4 .parent calls
   config_dir = Path(__file__).parent.parent.parent.parent / "config"
   ```

3. **Removed defensive skip guards:**
   - Removed try/except with pytest.skip
   - Removed existence checks before assertions

## Related Skills

- `fix-test-configs` - General test configuration troubleshooting
- `pydantic-validation` - Debugging Pydantic model validation errors
- `path-calculation-debug` - Troubleshooting Path.parent calculations

## References

- Issue #670: <https://github.com/HomericIntelligence/ProjectScylla/issues/670>
- PR #688: <https://github.com/HomericIntelligence/ProjectScylla/pull/688>
- Pydantic validation docs: <https://docs.pydantic.dev/latest/errors/validation_errors/>
