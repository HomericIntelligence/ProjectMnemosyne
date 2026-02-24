---
name: token-stats-aggregation
description: Pattern for tracking detailed token statistics with cache tokens across hierarchical E2E report levels
category: evaluation
date: 2026-01-03
---

# Token Stats Aggregation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-03 |
| Objective | Track detailed token statistics (input, output, cache_read, cache_creation) with hierarchical aggregation across E2E report levels |
| Outcome | Success - implemented TokenStats dataclass with aggregation, enhanced reports at all levels |
| Source PR | ProjectScylla #125 |

## When to Use

Invoke this skill when:

- Adding token tracking to an evaluation framework
- Need to aggregate metrics across hierarchical levels (run -> subtest -> tier -> experiment)
- Bridging adapter layer (Pydantic) and domain layer (dataclass) data models
- Adding new fields while maintaining backwards compatibility
- Creating comparison tables in hierarchical reports

## Verified Workflow

### Step 1: Create Aggregatable Dataclass

Create a dataclass with `__add__` method for summing across multiple instances:

```python
@dataclass
class TokenStats:
    """Detailed token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_input(self) -> int:
        """Total input tokens including cache reads."""
        return self.input_tokens + self.cache_read_tokens

    @property
    def total_tokens(self) -> int:
        """Total all tokens processed."""
        return self.total_input + self.output_tokens + self.cache_creation_tokens

    def __add__(self, other: TokenStats) -> TokenStats:
        """Enable summing TokenStats."""
        return TokenStats(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens + other.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
        }
```

### Step 2: Create Bridge Class for Layer Boundaries

When adapter layer uses Pydantic and domain layer uses dataclass:

```python
class AdapterTokenStats(BaseModel):
    """Pydantic model for adapter layer."""
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cache_creation_tokens: int = Field(default=0)
    cache_read_tokens: int = Field(default=0)

    def to_token_stats(self) -> TokenStats:
        """Convert to domain layer dataclass."""
        return TokenStats(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens,
        )
```

### Step 3: Add Legacy Properties for Backwards Compatibility

When replacing individual fields with a composite object:

```python
@dataclass
class RunResult:
    token_stats: TokenStats  # New field

    # Legacy properties for backwards compatibility
    @property
    def tokens_input(self) -> int:
        """Total input tokens (legacy)."""
        return self.token_stats.total_input

    @property
    def tokens_output(self) -> int:
        """Output tokens (legacy)."""
        return self.token_stats.output_tokens
```

### Step 4: Aggregate Using functools.reduce

At each hierarchy level, aggregate from children:

```python
from functools import reduce

# In subtest aggregation (from runs)
token_stats = reduce(
    lambda a, b: a + b,
    [r.token_stats for r in runs],
    TokenStats(),  # Identity element
)

# In tier aggregation (from subtests)
token_stats = reduce(
    lambda a, b: a + b,
    [s.token_stats for s in subtest_results.values()],
    TokenStats(),
)
```

### Step 5: Update Tests Systematically

Pattern for updating tests when API changes:

```python
# Old (broken)
result = AdapterResult(
    tokens_input=100,
    tokens_output=50,
)

# New (fixed)
result = AdapterResult(
    token_stats=AdapterTokenStats(
        input_tokens=100,
        output_tokens=50,
    ),
)
# Legacy properties still work
assert result.tokens_input == 100
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Solution |
|---------|----------------|---------------|----------|
| Direct field replacement | Replaced `tokens_input` and `tokens_output` fields directly with `token_stats` object | Broke existing code and tests that accessed the old field names directly | Add `@property` decorators that compute legacy values from the new structure |
| Single test file fix | Fixed one test file (test_claude_code.py) and expected others to pass | Other adapter tests (cline, opencode, openai_codex) had identical issues with old parameter names and logs directory assertions | Check all similar test files and apply consistent fixes across the entire test suite |
| Wrong log directory | Tests expected logs at `output_dir/logs/stdout.log` | Implementation writes directly to `output_dir/stdout.log` (no subdirectory) | Update test assertions to match actual implementation path |

## Results & Parameters

### Token Statistics Available from Claude Code JSON

```json
{
  "usage": {
    "input_tokens": 15,
    "output_tokens": 422,
    "cache_creation_input_tokens": 27655,
    "cache_read_input_tokens": 82278
  }
}
```

### Report Enhancement Pattern

At each report level, add:
1. **Overview table** with token columns: `| In | Out | Cache R | Cache W |`
2. **Per-criteria comparison table** showing scores from each child unit
3. **Token statistics summary table** with totals

### Files Modified (Reference)

| File | Changes |
|------|---------|
| `models.py` | Add TokenStats dataclass, update RunResult/SubTestResult/TierResult/ExperimentResult |
| `adapters/base.py` | Add AdapterTokenStats, update AdapterResult |
| `adapters/*.py` | Use token_stats in all adapters |
| `subtest_executor.py` | Aggregate token stats from runs |
| `runner.py` | Aggregate token stats from subtests and tiers |
| `run_report.py` | Enhanced reports with token tables and per-criteria comparisons |

## Key Learnings

1. **Always provide backwards compatibility** when changing data models - use properties
2. **Check all similar test files** when fixing one - patterns repeat
3. **Use `__add__` for aggregatable dataclasses** - enables clean reduce patterns
4. **Bridge layer boundaries explicitly** - Pydantic adapters need conversion methods to domain dataclasses
5. **Run full test suite after changes** - related tests often fail together
