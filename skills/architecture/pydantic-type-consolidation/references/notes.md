# Session Notes: ExecutionInfo Consolidation (Issue #658)

## Context

Follow-up to RunResult consolidation (#604). Applied the same Pydantic-based inheritance pattern to ExecutionInfo types.

## Initial State

Found 3 ExecutionInfo variants:

1. `executor/runner.py:ExecutionInfo` - Detailed (container_id, stdout, stderr, timestamps)
2. `reporting/result.py:ExecutionInfo` - Minimal (status, duration, exit_code)
3. `core/results.py:BaseExecutionInfo` - Base dataclass (exit_code, duration, timed_out)

## Implementation Timeline

### Step 1: Create Base Pydantic Model

- Added `ExecutionInfoBase` to `core/results.py`
- Used `ConfigDict(frozen=True)` for immutability
- Made `duration_seconds` and `timed_out` optional with defaults

### Step 2: Update Module Exports

- Added `ExecutionInfoBase` to `scylla/core/__init__.py`
- Kept `BaseExecutionInfo` for backward compatibility

### Step 3: Create Domain-Specific Subtypes

- `ExecutorExecutionInfo` in `executor/runner.py`
- `ReportingExecutionInfo` in `reporting/result.py`
- Added type aliases for backward compatibility

### Step 4: Fix Immutability Issues

- Initially tried to mutate frozen models in `_execute_in_container_with_timing()`
- Fixed by using `model_copy(update={...})` pattern

### Step 5: Testing

- Created `tests/unit/core/test_execution_info.py` (22 tests)
- Updated `tests/unit/core/test_results.py` (11 new tests)
- Verified all existing tests still pass (56/56)

### Step 6: Code Quality

- All pre-commit hooks pass
- Type checking with mypy passes
- Import verification successful

## Debugging Notes

### Issue: Validation Error for duration_seconds

```
ValidationError: Field required [type=missing, input_value={...}]
```

**Root cause**: Made `duration_seconds` required with `Field(...)`
**Fix**: Changed to `Field(default=0.0)` for backward compatibility

### Issue: Frozen Instance Error

```
ValidationError: Instance is frozen [type=frozen_instance]
```

**Root cause**: Tried to mutate frozen Pydantic model
**Code**:

```python
execution_info.started_at = start_time.isoformat()  # ❌ Fails
```

**Fix**: Use `model_copy(update={...})`:

```python
return execution_info.model_copy(
    update={
        "started_at": start_time.isoformat(),
        "ended_at": end_time.isoformat(),
        "duration_seconds": duration,
    }
)
```

## Test Results

```
tests/unit/core/test_execution_info.py::TestExecutionInfoBase ............. 9 passed
tests/unit/core/test_execution_info.py::TestExecutorExecutionInfo ......... 4 passed
tests/unit/core/test_execution_info.py::TestReportingExecutionInfo ........ 4 passed
tests/unit/core/test_execution_info.py::TestBackwardCompatibility ......... 2 passed
tests/unit/core/test_execution_info.py::TestInheritanceHierarchy .......... 3 passed
tests/unit/core/test_results.py::TestExecutionInfoBase ................... 7 passed
tests/unit/core/test_results.py::TestBaseExecutionInfoBackwardCompatibility 2 passed
tests/unit/executor/test_runner.py .................................... 26 passed
tests/unit/reporting/test_result.py ................................... 30 passed

Total: 104 tests, 100% passing
```

## Files Changed

| File | Lines Added | Lines Deleted | Purpose |
|------|-------------|---------------|---------|
| scylla/core/results.py | +53 | -8 | Added ExecutionInfoBase, marked BaseExecutionInfo deprecated |
| scylla/core/**init**.py | +1 | -0 | Exported ExecutionInfoBase |
| scylla/executor/runner.py | +29 | -15 | Created ExecutorExecutionInfo, added type alias, fixed immutability |
| scylla/reporting/result.py | +20 | -5 | Created ReportingExecutionInfo, added type alias |
| tests/unit/core/test_execution_info.py | +344 | -0 | New comprehensive test file |
| tests/unit/core/test_results.py | +80 | -0 | Added backward compatibility tests |

## Commit Message

```
feat(core): Standardize ExecutionInfo types with inheritance hierarchy

Consolidate the three ExecutionInfo variants into a unified Pydantic-based
inheritance hierarchy, following the same pattern established for RunResult
in issue #604.

Changes:
- Add ExecutionInfoBase Pydantic model in core/results.py as the base class
- Create ExecutorExecutionInfo (executor/runner.py) - detailed container execution
- Create ReportingExecutionInfo (reporting/result.py) - minimal persistence
- Mark BaseExecutionInfo dataclass as deprecated with migration guidance
- Add backward-compatible type aliases (ExecutionInfo) in both modules
- Export ExecutionInfoBase from scylla.core module
- Update module docstrings with hierarchy documentation
- Add comprehensive tests for new Pydantic models and inheritance
- Verify backward compatibility with existing tests

Implementation details:
- Use Pydantic BaseModel with frozen=True for immutability
- Provide sensible defaults for duration_seconds (0.0) and timed_out (False)
- Use model_copy(update={}) pattern for immutable model updates in runner.py
- All domain-specific types inherit common fields from ExecutionInfoBase
- Maintain 100% backward compatibility via type aliases

All tests pass with full backward compatibility maintained.

Closes #658
```

## PR Summary

**Title**: feat(core): Standardize ExecutionInfo types with inheritance hierarchy

**Labels**: enhancement

**Auto-merge**: Enabled (rebase strategy)

**URL**: <https://github.com/HomericIntelligence/ProjectScylla/pull/726>

## Lessons Learned

1. **Frozen Pydantic models require `model_copy()`** - Can't mutate them directly
2. **Optional fields need defaults** - Even if the original had defaults
3. **Type aliases are crucial for backward compatibility** - Let old code work unchanged
4. **Deprecation warnings should show migration path** - Help developers transition
5. **Test both new and legacy types** - Ensure nothing breaks during migration
6. **Cross-reference documentation** - Make hierarchy discoverable

## Next Steps (Potential)

- Consider consolidating other duplicate types (e.g., MetricsInfo, JudgmentInfo)
- Create a general "type consolidation" CLI tool
- Add migration guide to developer docs
- Track deprecation usage and eventually remove BaseExecutionInfo
