# Pydantic Type Consolidation Pattern

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-15 |
| **Objective** | Consolidate duplicate type definitions into a unified Pydantic-based inheritance hierarchy |
| **Outcome** | ✅ Successfully standardized ExecutionInfo types with full backward compatibility |
| **Issue** | #658 |
| **PR** | #726 |
| **Pattern** | Dataclass → Pydantic inheritance hierarchy with type aliases |

## When to Use This Skill

Use this pattern when you encounter:

- Multiple similar type definitions across the codebase (e.g., `ExecutionInfo` in 3+ modules)
- Need to migrate from dataclasses to Pydantic models
- Want to establish a type hierarchy while maintaining backward compatibility
- Following DRY principle for shared data structures
- Need validation and serialization consistency via Pydantic

**Trigger phrases**:

- "consolidate these types"
- "standardize [Type] across modules"
- "create inheritance hierarchy for [Type]"
- "migrate from dataclass to Pydantic"

## Verified Workflow

### 1. Discovery Phase

Identify all variants of the type:

```bash
# Find all class definitions with the same name
grep -rn "class ExecutionInfo" scylla/

# Results:
# executor/runner.py:ExecutionInfo (detailed with container info)
# reporting/result.py:ExecutionInfo (minimal for persistence)
# core/results.py:BaseExecutionInfo (base dataclass)
```

### 2. Design Phase

Create a base Pydantic model with common fields:

```python
from pydantic import BaseModel, ConfigDict, Field

class ExecutionInfoBase(BaseModel):
    """Base execution information type for all execution results.

    Note: Fields have sensible defaults to support incremental result
    construction in different execution contexts.
    """

    model_config = ConfigDict(frozen=True)

    # Required fields
    exit_code: int = Field(..., description="Process/container exit code (0 = success)")

    # Optional fields with defaults
    duration_seconds: float = Field(default=0.0, description="Total execution duration in seconds")
    timed_out: bool = Field(default=False, description="Whether execution timed out")
```

**Key decisions**:

- ✅ Use `frozen=True` for immutability
- ✅ Provide sensible defaults (0.0, False) for incremental construction
- ✅ Use `Field(...)` for required fields, `Field(default=X)` for optional
- ✅ Add descriptive field descriptions

### 3. Domain-Specific Subtypes

Create specialized variants that inherit from base:

```python
# executor/runner.py
class ExecutorExecutionInfo(ExecutionInfoBase):
    """Detailed execution information for container runs.

    Inherits common fields (exit_code, duration_seconds, timed_out)
    from ExecutionInfoBase.
    """

    container_id: str = Field(..., description="Docker container ID")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    started_at: str = Field(default="", description="ISO timestamp of start")
    ended_at: str = Field(default="", description="ISO timestamp of end")

# Backward-compatible type alias
ExecutionInfo = ExecutorExecutionInfo
```

```python
# reporting/result.py
class ReportingExecutionInfo(ExecutionInfoBase):
    """Execution metadata for result persistence.

    Inherits common fields (exit_code, duration_seconds, timed_out)
    from ExecutionInfoBase.
    """

    status: str = Field(..., description="Execution status")

# Backward-compatible type alias
ExecutionInfo = ReportingExecutionInfo
```

### 4. Deprecate Legacy Types

Mark the old dataclass as deprecated with migration guidance:

```python
@dataclass
class BaseExecutionInfo:
    """Base execution information shared across all result types.

    .. deprecated::
        Use ExecutionInfoBase (Pydantic model) instead. This dataclass is kept
        for backward compatibility only. New code should use ExecutionInfoBase
        and its domain-specific subtypes (ExecutorExecutionInfo, ReportingExecutionInfo).

    For the new Pydantic-based hierarchy, see:
    - ExecutionInfoBase (this module) - Base Pydantic model
    - ExecutorExecutionInfo (executor/runner.py) - Container execution
    - ReportingExecutionInfo (reporting/result.py) - Result persistence
    """

    exit_code: int
    duration_seconds: float
    timed_out: bool = False
```

### 5. Export Base Type

Update module exports:

```python
# scylla/core/__init__.py
from scylla.core.results import (
    BaseExecutionInfo,      # Legacy (deprecated)
    ExecutionInfoBase,      # New base type
)

__all__ = [
    "BaseExecutionInfo",
    "ExecutionInfoBase",
]
```

### 6. Update Documentation

Add hierarchy documentation to module docstring:

```python
"""
ExecutionInfo inheritance hierarchy (Issue #658):
- ExecutionInfoBase (this module) - Base Pydantic model with common fields
  ├── ExecutorExecutionInfo (executor/runner.py) - Container execution (detailed)
  └── ReportingExecutionInfo (reporting/result.py) - Result persistence (minimal)

Legacy dataclass (deprecated):
- BaseExecutionInfo - Kept for backward compatibility, use ExecutionInfoBase instead
"""
```

### 7. Testing Strategy

Create comprehensive tests:

```python
# tests/unit/core/test_execution_info.py

class TestExecutionInfoBase:
    """Tests for ExecutionInfoBase Pydantic model."""

    def test_construction_success(self):
        info = ExecutionInfoBase(exit_code=0, duration_seconds=10.5)
        assert info.exit_code == 0

    def test_immutability(self):
        info = ExecutionInfoBase(exit_code=0, duration_seconds=10.0)
        with pytest.raises(ValidationError):
            info.exit_code = 1

    def test_model_dump(self):
        info = ExecutionInfoBase(exit_code=0, duration_seconds=10.5)
        data = info.model_dump()
        assert data == {"exit_code": 0, "duration_seconds": 10.5, "timed_out": False}

class TestInheritanceHierarchy:
    """Tests for the ExecutionInfo inheritance hierarchy."""

    def test_executor_is_execution_info_base(self):
        info = ExecutorExecutionInfo(container_id="abc123", exit_code=0)
        assert isinstance(info, ExecutionInfoBase)

class TestBackwardCompatibility:
    """Tests for backward compatibility via type aliases."""

    def test_executor_type_alias(self):
        from scylla.executor.runner import ExecutionInfo
        info = ExecutionInfo(container_id="abc123", exit_code=0)
        assert isinstance(info, ExecutorExecutionInfo)
```

## Failed Attempts & Solutions

### ❌ Attempt 1: Making duration_seconds Required

**What we tried**:

```python
class ExecutionInfoBase(BaseModel):
    exit_code: int = Field(..., description="Exit code")
    duration_seconds: float = Field(..., description="Duration")  # Required!
```

**Why it failed**:

- Existing tests created `ExecutionInfo` without `duration_seconds`
- Broke backward compatibility
- Error: "Field required [type=missing, input_value={...}]"

**Solution**:

```python
duration_seconds: float = Field(default=0.0, description="Duration")
```

### ❌ Attempt 2: Mutating Frozen Pydantic Models

**What we tried**:

```python
# In _execute_in_container_with_timing()
execution_info = self._run_in_container(...)
execution_info.started_at = start_time.isoformat()  # ❌ Fails!
execution_info.duration_seconds = duration
```

**Why it failed**:

- Pydantic models with `frozen=True` are immutable
- Error: "Instance is frozen [type=frozen_instance]"

**Solution**: Use `model_copy(update={})`:

```python
return execution_info.model_copy(
    update={
        "started_at": start_time.isoformat(),
        "ended_at": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
    }
)
```

### ❌ Attempt 3: Omitting Backward-Compatible Type Aliases

**What we tried**:

- Just rename `ExecutionInfo` to `ExecutorExecutionInfo` everywhere
- Update all imports manually

**Why it failed**:

- Would break existing code that imports `ExecutionInfo`
- Not backward compatible
- Requires coordinated changes across codebase

**Solution**: Add type aliases in each module:

```python
# executor/runner.py
ExecutionInfo = ExecutorExecutionInfo

# reporting/result.py
ExecutionInfo = ReportingExecutionInfo
```

This allows:

- Old code: `from scylla.executor.runner import ExecutionInfo` ✅
- New code: `from scylla.executor.runner import ExecutorExecutionInfo` ✅

## Results & Parameters

### Test Coverage

```bash
# New tests created
tests/unit/core/test_execution_info.py ............ 22 tests
  - TestExecutionInfoBase ...................... 9 tests
  - TestExecutorExecutionInfo .................. 4 tests
  - TestReportingExecutionInfo ................. 4 tests
  - TestBackwardCompatibility .................. 2 tests
  - TestInheritanceHierarchy ................... 3 tests

# Updated tests
tests/unit/core/test_results.py ................ 11 new tests
  - TestExecutionInfoBase ...................... 7 tests
  - TestBaseExecutionInfoBackwardCompatibility . 2 tests

# Existing tests (unchanged, still passing)
tests/unit/executor/test_runner.py ............. 26 tests
tests/unit/reporting/test_result.py ............ 30 tests

Total: 104 tests, 100% passing
```

### Verification Commands

```bash
# Import verification
pixi run python -c "from scylla.core.results import ExecutionInfoBase; print('OK')"
pixi run python -c "from scylla.executor.runner import ExecutorExecutionInfo, ExecutionInfo; print('OK')"
pixi run python -c "from scylla.reporting.result import ReportingExecutionInfo, ExecutionInfo; print('OK')"

# Inheritance verification
pixi run python -c "
from scylla.executor.runner import ExecutorExecutionInfo
from scylla.core.results import ExecutionInfoBase
info = ExecutorExecutionInfo(container_id='test', exit_code=0)
print(f'isinstance: {isinstance(info, ExecutionInfoBase)}')
print(f'Serialization: {info.model_dump()}')
"

# Backward compatibility verification
pixi run python -c "from scylla.core.results import BaseExecutionInfo; print('Legacy dataclass OK')"
```

### Code Quality

```bash
# All pre-commit hooks pass
pre-commit run --all-files
  ✅ Ruff Format Python
  ✅ Ruff Check Python
  ✅ Mypy Type Check Python
  ✅ Trim Trailing Whitespace
  ✅ Fix End of Files
```

### Files Modified

- `scylla/core/results.py` - Added ExecutionInfoBase, marked BaseExecutionInfo as deprecated
- `scylla/core/__init__.py` - Exported ExecutionInfoBase
- `scylla/executor/runner.py` - Created ExecutorExecutionInfo with type alias
- `scylla/reporting/result.py` - Created ReportingExecutionInfo with type alias
- `tests/unit/core/test_execution_info.py` - New test file (22 tests)
- `tests/unit/core/test_results.py` - Updated with backward compat tests (11 new tests)

## Key Takeaways

1. **Always provide defaults for optional fields** - Enables incremental construction
2. **Use `model_copy(update={})` for frozen models** - Don't try to mutate them
3. **Type aliases preserve backward compatibility** - Old code continues working
4. **Mark deprecated types with clear migration paths** - Help developers migrate
5. **Cross-reference in docstrings** - Document the full hierarchy in each type
6. **Test both new types and backward compatibility** - Ensure nothing breaks

## Related Skills

- `codebase-consolidation` - Finding and categorizing duplicates
- `dry-consolidation-workflow` - General consolidation process
- `pydantic-model-dump` - Using `.model_dump()` instead of `.to_dict()`

## References

- Issue: <https://github.com/HomericIntelligence/ProjectScylla/issues/658>
- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/726>
- Previous pattern: RunResult consolidation (#604)
- Pydantic docs: <https://docs.pydantic.dev/latest/>
