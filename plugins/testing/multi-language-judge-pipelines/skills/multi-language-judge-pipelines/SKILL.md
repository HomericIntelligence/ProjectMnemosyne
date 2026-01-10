---
name: multi-language-judge-pipelines
description: Add language-specific build pipelines to E2E test judge systems
category: testing
date: 2026-01-09
user-invocable: false
---

# Multi-Language Judge Pipelines

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-09 |
| Objective | Add language-specific build pipeline support (Python/Mojo) to E2E test judge system |
| Outcome | Successfully implemented language routing with required field validation across 47 test fixtures |
| Context | ProjectScylla E2E evaluation framework |

## When to Use This Skill

Use this skill when:

1. **Test infrastructure needs multi-language support** - E2E or judge systems that evaluate code in multiple programming languages
2. **Different languages require different tooling** - Python (ruff, pytest) vs Mojo (mojo build, mojo format, mojo test)
3. **Pipeline routing based on configuration** - Need to select appropriate build/test pipeline based on test metadata
4. **Making fields required without backward compatibility** - Converting optional fields to required with clear validation errors
5. **Bulk updating test fixtures** - Need to add required configuration to many test files systematically

## Verified Workflow

### 1. Make Language-Agnostic Pipeline Infrastructure

**Problem**: Existing pipeline hardcoded to Mojo-specific fields (`mojo_build_passed`, `mojo_format_passed`)

**Solution**: Create generic pipeline result model
```python
@dataclass
class BuildPipelineResult:
    language: str  # "python" or "mojo"
    build_passed: bool
    build_output: str
    format_passed: bool
    format_output: str
    test_passed: bool
    test_output: str
    # ... other fields
```

### 2. Implement Language-Specific Pipeline Functions

**Pattern**: Separate functions for each language, router function for dispatch

```python
def _run_mojo_pipeline(workspace: Path) -> BuildPipelineResult:
    """Run Mojo pipeline: mojo build, mojo format --check, mojo test"""
    results = {"language": "mojo"}
    # Run mojo commands
    return BuildPipelineResult(**results)

def _run_python_pipeline(workspace: Path) -> BuildPipelineResult:
    """Run Python pipeline: python -m compileall, ruff, pytest"""
    results = {"language": "python"}
    # Run python commands (with optional tool checks)
    return BuildPipelineResult(**results)

def _run_build_pipeline(workspace: Path, language: str) -> BuildPipelineResult:
    if language == "python":
        return _run_python_pipeline(workspace)
    else:
        return _run_mojo_pipeline(workspace)
```

**Key Pattern**: Optional tool handling
```python
try:
    result = subprocess.run(["ruff", "check", "."], ...)
    results["format_passed"] = result.returncode == 0
except FileNotFoundError:
    # Tool not installed - skip gracefully
    results["format_passed"] = True
    results["format_output"] = "ruff not available, skipping"
```

### 3. Thread Language Through Call Chain

**Pattern**: Add language parameter at each level

1. **Configuration Model** (required field, no default):
   ```python
   @dataclass
   class ExperimentConfig:
       # Required fields BEFORE optional fields (Python dataclass requirement)
       experiment_id: str
       task_repo: str
       task_commit: str
       task_prompt_file: Path
       language: str  # REQUIRED - no default
       # Optional fields with defaults
       models: list[str] = field(default_factory=...)
   ```

2. **Config Loader** (load from test.yaml):
   ```python
   config = yaml.safe_load(test_yaml)
   return {
       "language": config.get("language"),  # Required, no default
       # ... other fields
   }
   ```

3. **Validation** (fail early with clear message):
   ```python
   if not config_dict["language"]:
       raise ValueError(
           "Language required: must be set in test.yaml (e.g., 'language: python')"
       )
   ```

4. **Execution** (pass through to judge):
   ```python
   judge_result = run_llm_judge(
       workspace=workspace,
       language=self.config.language,  # From ExperimentConfig
       # ... other params
   )
   ```

### 4. Update All Test Fixtures Programmatically

**Pattern**: Script to add required field to all test.yaml files

```python
for test_dir in test_dirs:
    test_yaml = test_dir / "test.yaml"

    # Determine language (test-001 is python, rest are mojo)
    lang = "python" if test_dir.name == "test-001" else "mojo"

    # Read, insert language field before 'source:', write back
    with open(test_yaml) as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.strip().startswith("source:"):
            lines.insert(i, f"language: {lang}\n")
            lines.insert(i, "\n")  # Blank line
            break

    with open(test_yaml, 'w') as f:
        f.writelines(lines)
```

### 5. Update Serialization Methods

**Critical**: Update `to_dict()` and `load()` for all config classes

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "experiment_id": self.experiment_id,
        # ... other fields
        "language": self.language,  # ADD to serialization
    }

@classmethod
def load(cls, path: Path) -> ExperimentConfig:
    with open(path) as f:
        data = json.load(f)
    return cls(
        experiment_id=data["experiment_id"],
        # ... other fields
        language=data["language"],  # ADD to deserialization
    )
```

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| Adding `language` field with default value | Python dataclass error: "non-default argument 'language' follows default argument 'timeout_seconds'" | Required fields MUST come before optional fields in dataclass definition |
| Using backward-compatible defaults (`language: str = "mojo"`) | User explicitly requested NO backward compatibility | When making breaking changes, fail fast with clear error messages rather than silent defaults |
| Forgetting to update `to_dict()` method | Test failures: `KeyError: 'language'` when loading from JSON | Every config class needs serialization updated in 3 places: field definition, `to_dict()`, and `load()` |
| Line-too-long linting errors | Validation error messages exceeded 100 char limit | Break long strings across multiple lines or simplify messages |

## Results & Parameters

### Python Pipeline Commands

```python
# Syntax check
python -m compileall -q .

# Linting (optional if ruff installed)
ruff check .

# Tests (optional if pytest installed)
pytest -v

# Pre-commit hooks (runs on all)
pre-commit run --all-files
```

### Mojo Pipeline Commands

```python
# Build
mojo build .

# Format check
mojo format --check .

# Tests
mojo test

# Pre-commit hooks
pre-commit run --all-files
```

### Configuration Schema

**test.yaml** (required field):
```yaml
id: "test-001"
name: "Test Name"
description: "Test description"
language: python  # REQUIRED: "python" or "mojo"

source:
  repo: "https://github.com/..."
  hash: "abc123"
```

**ExperimentConfig** (field ordering):
```python
@dataclass
class ExperimentConfig:
    # REQUIRED fields first (no defaults)
    experiment_id: str
    task_repo: str
    task_commit: str
    task_prompt_file: Path
    language: str

    # OPTIONAL fields last (with defaults)
    models: list[str] = field(default_factory=...)
    runs_per_subtest: int = 10
```

### Validation Pattern

```python
# In build_config()
if not config_dict["language"]:
    raise ValueError(
        "Language required: must be set in test.yaml (e.g., 'language: python')"
    )
```

## Implementation Checklist

- [ ] Create language-agnostic pipeline result model
- [ ] Implement separate pipeline functions for each language
- [ ] Add router function with language parameter
- [ ] Update config models (required field, correct ordering)
- [ ] Add validation to fail if language not set
- [ ] Thread language parameter through call chain
- [ ] Update all serialization methods (`to_dict()`, `load()`)
- [ ] Update all test fixtures with language field
- [ ] Update test files (fixtures, unit tests)
- [ ] Run pre-commit and tests to verify

## Key Takeaways

1. **Dataclass field ordering matters** - Required fields must come before optional fields
2. **Fail fast with clear errors** - Better than silent defaults when making breaking changes
3. **Update serialization everywhere** - Config changes need updates in definition, `to_dict()`, and `load()`
4. **Programmatic bulk updates** - Use Python scripts to update many test files consistently
5. **Optional tool handling** - Gracefully skip tools that aren't installed (e.g., ruff, pytest)
6. **Pipeline abstraction** - Generic field names (`build_passed` vs `mojo_build_passed`) enable multi-language support

## References

- [Project Context](../references/notes.md)
