# Skill: Fix Pydantic Required Fields in Test Fixtures

| Attribute | Value |
|-----------|-------|
| Date | 2026-01-11 |
| Category | testing |
| Objective | Fix test failures caused by missing required fields in Pydantic model fixtures after data model evolution |
| Outcome | Successfully fixed all unit and integration tests by adding `language` field to ExperimentConfig and EvalCase fixtures |
| Status | ✅ Verified |

## When to Use This Skill

Use this skill when:

1. **Pydantic validation errors appear in tests** after adding required fields to data models
2. **Test fixtures are out of sync** with model requirements
3. **Multiple test files fail** with `missing 1 required positional argument` errors
4. **Model evolution breaks existing tests** that were written before new required fields were added
5. **Integration tests fail** because YAML/JSON fixtures don't include new required fields

**Trigger Pattern**: `TypeError: ModelName.__init__() missing 1 required positional argument: 'field_name'`

## Context

This session fixed test failures in PR #172 that emerged after rebasing against main. The main branch had been updated with a new required field (`language`) in both `ExperimentConfig` and `EvalCase` models, causing all tests using these models to fail.

**Key Learning**: When data models evolve to add required fields, ALL test fixtures (Python instantiations AND YAML/JSON data) must be updated to provide those fields.

## Verified Workflow

### Step 1: Identify the Missing Required Field

```bash
# Run tests to see the error
pixi run pytest tests/unit/e2e/test_models.py -v

# Error output will show:
# TypeError: ExperimentConfig.__init__() missing 1 required positional argument: 'language'
```

**What to look for**:
- Error message identifies the model class (`ExperimentConfig`)
- Error message identifies the missing field name (`language`)
- Multiple test failures with the same missing field indicates systematic fixture issue

### Step 2: Locate the Model Definition

```bash
# Find where the model is defined
grep -r "class ExperimentConfig" src/

# Read the model to understand the new field
# Look for the field definition and any comments about its purpose
```

In this case:
- Model: `src/scylla/e2e/models.py:588`
- Field: `language: str  # REQUIRED: Programming language for build pipeline`
- Purpose: Determines which build pipeline to use (Python vs Mojo)

### Step 3: Update Python Test Fixtures

**Pattern**: Find all test files that instantiate the affected model and add the missing parameter.

```python
# BEFORE (fails):
config = ExperimentConfig(
    experiment_id="test-001",
    task_repo="https://github.com/test/repo",
    task_commit="abc123",
    task_prompt_file=Path("prompt.md"),
    tiers_to_run=[TierID.T0, TierID.T1],
)

# AFTER (passes):
config = ExperimentConfig(
    experiment_id="test-001",
    task_repo="https://github.com/test/repo",
    task_commit="abc123",
    task_prompt_file=Path("prompt.md"),
    language="python",  # ADDED - required field for build pipeline
    tiers_to_run=[TierID.T0, TierID.T1],
)
```

**Files updated in this session**:
- `tests/unit/e2e/test_models.py` - 2 test methods
- `tests/unit/e2e/test_resume.py` - 1 pytest fixture

### Step 4: Update YAML/JSON Test Fixtures

**Pattern**: Find all YAML or JSON fixtures that serialize the affected model and add the missing field.

```python
# BEFORE (fails):
test_yaml.write_text("""
id: "001-test"
name: "Test Case"
description: "A test case for testing"
source:
  repo: "https://github.com/octocat/Hello-World"
  hash: "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
task:
  prompt_file: "prompt.md"
  timeout_seconds: 60
tiers:
  - T0
validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"
""")

# AFTER (passes):
test_yaml.write_text("""
id: "001-test"
name: "Test Case"
description: "A test case for testing"
language: mojo  # ADDED - required field for build pipeline
source:
  repo: "https://github.com/octocat/Hello-World"
  hash: "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
task:
  prompt_file: "prompt.md"
  timeout_seconds: 60
tiers:
  - T0
validation:
  criteria_file: "expected/criteria.md"
  rubric_file: "expected/rubric.yaml"
""")
```

**Files updated in this session**:
- `tests/integration/test_orchestrator.py` - 2 test_env fixtures (lines 103-119, 218-236)

### Step 5: Verify All Tests Pass

```bash
# Run unit tests
pixi run pytest tests/unit/e2e/test_models.py -v
pixi run pytest tests/unit/e2e/test_resume.py -v

# Run integration tests
pixi run pytest tests/integration/test_orchestrator.py -v

# Run all tests
pixi run pytest tests/ -v
```

**Expected output**: All tests should pass with no Pydantic validation errors.

### Step 6: Commit and Push

```bash
# Commit the fixes
git add tests/unit/e2e/test_models.py tests/unit/e2e/test_resume.py
git commit -m "fix(tests): Add language field to unit test fixtures"

git add tests/integration/test_orchestrator.py
git commit -m "fix(tests): Add language field to integration test fixtures"

# Push to feature branch
git push origin <branch-name>
```

## Failed Attempts

### ❌ Failed Attempt 1: Trying to Trigger CI Without Fixing Tests

**What we tried**:
- Close/reopen PR
- Add empty commits
- Add comments to PR

**Why it failed**:
- Tests were fundamentally broken due to missing required fields
- No amount of workflow triggering would make broken tests pass
- Need to fix the root cause (missing fields) not the symptoms (failing CI)

**Lesson**: Always run tests locally first before trying to trigger CI workflows.

### ❌ Failed Attempt 2: Using `language="mojo"` in Unit Test Fixtures

**What we tried**:
- Initially considered using `language="mojo"` for all test fixtures to match integration tests

**Why it failed**:
- Unit tests for `ExperimentConfig` should be language-agnostic
- Using `"python"` is more conventional for unit tests (simpler, more common)
- Integration tests use `"mojo"` because they test Mojo-specific workflows

**Lesson**: Choose appropriate field values based on test context:
- Unit tests: Use simple, common values (`"python"`)
- Integration tests: Use realistic values matching actual usage (`"mojo"`)

## Results & Parameters

### Test Files Modified

**Unit Tests**:
```python
# tests/unit/e2e/test_models.py
# Lines: 231, 252 (2 ExperimentConfig instantiations)
# Added: language="python"

# tests/unit/e2e/test_resume.py
# Lines: 28 (experiment_config fixture)
# Added: language="python"
```

**Integration Tests**:
```yaml
# tests/integration/test_orchestrator.py
# Lines: 107, 222 (2 test_env YAML fixtures)
# Added: language: mojo
```

### CI Results

All checks passed after fixes:
- ✅ pre-commit - PASSED
- ✅ test (unit, tests/unit) - PASSED
- ✅ test (integration, tests/integration) - PASSED

### Key Parameters

**ExperimentConfig required fields** (as of 2026-01-11):
- `experiment_id: str`
- `task_repo: str`
- `task_commit: str`
- `task_prompt_file: Path`
- `language: str` ← NEW (added in PR #174)

**EvalCase required fields** (as of 2026-01-11):
- `id: str`
- `name: str`
- `description: str`
- `language: str` ← NEW (added in PR #174)
- `source: SourceConfig`
- `task: TaskConfig`
- `tiers: List[str]`
- `validation: ValidationConfig`

## Prevention Strategy

To prevent this issue in the future:

1. **When adding required fields to Pydantic models**:
   - Immediately run full test suite: `pixi run pytest tests/ -v`
   - Identify all failing tests
   - Update ALL test fixtures (Python + YAML + JSON) before committing

2. **Use CI to catch fixture issues**:
   - Pre-commit hooks ensure tests run before commit
   - Never skip pre-commit with `--no-verify`

3. **Document required fields**:
   - Add comments to model definitions explaining purpose
   - Example: `language: str  # REQUIRED: Programming language for build pipeline`

4. **Consider backwards compatibility**:
   - Use `Optional[str]` with defaults instead of required fields when possible
   - Only make fields required if they're truly essential
   - Example: `language: str = "python"` (default) vs `language: str` (required)

## Related Skills

- [test-fixture-patterns] - General pytest fixture patterns
- [pydantic-model-evolution] - Strategies for evolving Pydantic models
- [ci-test-debugging] - Debugging CI test failures

## Tags

`#testing` `#pydantic` `#pytest` `#fixtures` `#validation-errors` `#data-models` `#model-evolution`
