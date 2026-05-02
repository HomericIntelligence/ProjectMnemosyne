# Token Stats Aggregation - Raw Notes

## Session Context

- **Date**: 2026-01-03
- **Project**: ProjectScylla
- **Branch**: refactor/filter-test-config-files-and-linting
- **PR**: #125

## Problem Statement

E2E test reports only tracked basic input/output tokens, missing critical cache token information needed for:
- Understanding prompt caching efficiency
- Accurate cost analysis
- Comparing cache hit rates across configurations

## Implementation Details

### TokenStats Dataclass Location

`src/scylla/e2e/models.py`

```python
@dataclass
class TokenStats:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
```

### AdapterTokenStats Location

`src/scylla/adapters/base.py`

```python
class AdapterTokenStats(BaseModel):
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cache_creation_tokens: int = Field(default=0)
    cache_read_tokens: int = Field(default=0)

    def to_token_stats(self) -> TokenStats:
        return TokenStats(...)
```

### Parsing Token Stats from Claude Code JSON

`src/scylla/adapters/claude_code.py:_parse_token_stats()`

```python
def _parse_token_stats(self, stdout: str, stderr: str) -> AdapterTokenStats:
    try:
        data = json.loads(stdout.strip())
        usage = data.get("usage", {})
        return AdapterTokenStats(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
        )
    except (json.JSONDecodeError, AttributeError):
        # Fallback to regex parsing for text output
        ...
```

### Aggregation Pattern

```python
from functools import reduce

token_stats = reduce(
    lambda a, b: a + b,
    [r.token_stats for r in runs],
    TokenStats(),
)
```

## Test Failures Encountered

### Failure 1: AdapterResult Parameter Names

```
TypeError: AdapterResult.__init__() got an unexpected keyword argument 'tokens_input'
```

**Fix**: Use `token_stats=AdapterTokenStats(...)` instead of `tokens_input=...`

### Failure 2: Log Directory Assertions

```
AssertionError: assert False
 +  where False = exists()
 +    where exists = PosixPath('/tmp/tmpXXX/logs').exists
```

**Fix**: Change from `tmppath / "logs" / "stdout.log"` to `tmppath / "stdout.log"`

### Failure 3: Method Rename

```
AttributeError: 'ClaudeCodeAdapter' object has no attribute '_parse_token_counts'
```

**Fix**: Rename test class and update method calls to `_parse_token_stats`

## Files Modified

1. `src/scylla/e2e/models.py` - TokenStats, RunResult, SubTestResult, TierResult, ExperimentResult
2. `src/scylla/adapters/base.py` - AdapterTokenStats, AdapterResult
3. `src/scylla/adapters/claude_code.py` - _parse_token_stats()
4. `src/scylla/adapters/cline.py` - token_stats usage
5. `src/scylla/adapters/opencode.py` - token_stats usage
6. `src/scylla/adapters/openai_codex.py` - token_stats usage
7. `src/scylla/e2e/subtest_executor.py` - aggregation
8. `src/scylla/e2e/runner.py` - aggregation
9. `src/scylla/e2e/run_report.py` - enhanced reports
10. `tests/unit/adapters/test_base.py` - token_stats tests
11. `tests/unit/adapters/test_claude_code.py` - token_stats tests
12. `tests/unit/adapters/test_cline.py` - log directory fix
13. `tests/unit/adapters/test_opencode.py` - log directory fix
14. `tests/unit/adapters/test_openai_codex.py` - log directory fix
15. `tests/unit/e2e/test_models.py` - token_stats tests

## Test Results

```
============================= 923 passed in 0.81s ==============================
```

## Report Enhancement Summary

### Run Report
- Token breakdown table (input, output, cache_read, cache_create, total)

### Subtest Report
- Runs overview table with token columns
- Per-criteria comparison table across runs
- Aggregated token statistics

### Tier Report
- Subtests overview table with token columns
- Per-criteria comparison table across subtests
- Aggregated token statistics

### Experiment Report
- Tiers overview table with token columns
- Per-criteria comparison table across tiers
- Aggregated token statistics
