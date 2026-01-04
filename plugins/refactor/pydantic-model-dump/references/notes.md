# Pydantic Model Dump - Implementation Notes

## Context

ProjectScylla E2E experiments were crashing with:
```
AttributeError: 'AdapterTokenStats' object has no attribute 'to_dict'
  File ".../subtest_executor.py", line 109, in _save_agent_result
    "token_stats": result.token_stats.model_dump(),
```

## Root Cause Analysis

1. `AdapterTokenStats` is defined as Pydantic BaseModel:
   ```python
   # src/scylla/adapters/base.py:31
   class AdapterTokenStats(BaseModel):
       input_tokens: int = Field(default=0)
       output_tokens: int = Field(default=0)
       # ...
   ```

2. Code was using `.to_dict()` which doesn't exist in Pydantic v2:
   ```python
   # src/scylla/e2e/subtest_executor.py:109
   "token_stats": result.token_stats.to_dict(),  # FAILS
   ```

## Solution

Changed to `.model_dump()`:
```python
"token_stats": result.token_stats.model_dump(),  # WORKS
```

## Audit Results

Searched for all `.to_dict()` calls:
- `runner.py:457` - `result.to_dict()` on `TierResult` - ✅ OK (custom method)
- `subtest_executor.py:713` - `run_result.to_dict()` - ✅ OK (custom method)
- `models.py` - Multiple `.to_dict()` on dataclasses - ✅ OK (custom methods)

Only Pydantic models needed updating.

## Testing

Ran E2E experiment after fix:
```bash
pixi run python scripts/run_e2e_experiment.py
```

Previously crashed at first agent save, now completes successfully.

## PR Details

- **Branch**: `135-fix-to-dict-attributeerror`
- **Files Changed**: `src/scylla/e2e/subtest_executor.py` (1 line)
- **Tests**: Pre-commit hooks passed
- **Status**: Merged to main
