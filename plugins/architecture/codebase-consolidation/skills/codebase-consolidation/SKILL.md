---
name: codebase-consolidation
description: Systematic approach to finding and consolidating duplicate code
category: architecture
date: 2026-01-02
---

# Codebase Consolidation

Systematic approach to finding duplicate code, unifying implementations, and documenting intentional variations.

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Objective | Consolidate duplicate code and align implementations to consistent patterns |
| Outcome | 5 consolidation PRs merged; established patterns for backward compatibility |

## When to Use

- Analyzing a codebase for duplicate implementations
- Unifying functions/types across multiple modules
- Creating backward-compatible refactors with type aliases
- Documenting intentionally different implementations
- Centralizing configuration (pricing, grading scales, etc.)

**Trigger phrases**: "find duplicates", "consolidate code", "unify implementations", "tech debt cleanup", "pattern alignment"

## Verified Workflow

### Phase 1: Discovery

Search for duplicate patterns across the codebase:

```bash
# Find duplicate function names
grep -r "def calculate_mean\|def calculate_median" src/

# Find duplicate class names
grep -r "class RunResult\|class ExecutionInfo" src/

# Find similar implementations
grep -r "tokens_input.*tokens_output" src/
```

### Phase 2: Categorization

Categorize duplicates into two types:

| Type | Example | Action |
|------|---------|--------|
| True duplicates | Same function in 3 files | Consolidate to single source |
| Intentional variants | 4 RunResult types for different domains | Document with cross-references |

### Phase 3: Issue Planning

Create GitHub issues with implementation plans BEFORE coding:

```markdown
## Objective
Reduce duplication of X by creating unified base types.

## Problem
### X - N separate definitions:
| Location | Purpose | Key Fields |
|----------|---------|------------|
| file1.py:L-L | Purpose A | field1, field2 |
| file2.py:L-L | Purpose B | field1, field3 |

## Implementation Plan
1. Create shared module with base types
2. Update each file to import from shared module
3. Add type aliases for backward compatibility
```

### Phase 4: Dependency-Ordered Execution

Execute in dependency order (lower deps first):

```
statistics.py (no deps)
    ↓
grading.py (uses statistics)
    ↓
aggregator.py (uses grading + statistics)
    ↓
pricing.py (used by adapters)
    ↓
result types (documentation only)
```

### Phase 5: Backward-Compatible Patterns

Use these patterns to avoid breaking changes:

**Type Alias for Renamed Types:**
```python
# In the new location
from scylla.metrics.statistics import Statistics

# In the old location (aggregator.py)
from scylla.metrics.statistics import Statistics
AggregatedStats = Statistics  # Backward-compatible alias
```

**Function Alias for Moved Functions:**
```python
# In judge/evaluator.py
from scylla.metrics.grading import assign_letter_grade
assign_grade = assign_letter_grade  # Backward-compatible alias
```

**Cross-Reference Docstrings for Intentional Variants:**
```python
class RunResult:
    """Result for statistical aggregation.

    This is a simplified result type used for aggregation.
    For detailed execution results, see:
    - executor/runner.py:RunResult (execution tracking)
    - e2e/models.py:RunResult (E2E test results)
    - reporting/result.py:RunResult (persistence)
    """
```

## Failed Attempts

| Attempt | Why It Failed |
|---------|---------------|
| Forcing all RunResult types into one class | Different domains need different fields; forced inheritance added complexity |
| Removing old class names immediately | Broke existing imports; backward-compatible aliases needed |
| Consolidating without issues first | Lost track of what to change; issues provide checklist |
| Using shorthand /advise command | Full prefix required: `/skills-registry-commands:advise` |
| git reset --hard after accidental commit | Safety net blocked; files were harmless so left as-is |

## Results & Parameters

### Consolidation Statistics

| Category | Before | After |
|----------|--------|-------|
| Statistics functions | 3 copies | 1 source + 2 imports |
| Grade assignment functions | 5 implementations | 1 canonical + aliases |
| Pricing implementations | 2 (different units) | 1 centralized (per-million) |
| Result types | 4 undocumented variants | 4 cross-referenced variants |

### Standard Thresholds (Industry-Aligned)

```yaml
grade_scale:
  S: 1.00   # Amazing - exceptional
  A: 0.80   # Excellent - production ready
  B: 0.60   # Good - minor improvements
  C: 0.40   # Acceptable - functional with issues
  D: 0.20   # Marginal - significant issues
  F: 0.00   # Failing
```

### Pricing Configuration Template

```python
class ModelPricing(BaseModel):
    model_id: str
    input_cost_per_million: float   # Always use per-million
    output_cost_per_million: float
    cached_cost_per_million: float = 0.0

MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-20250514": ModelPricing(
        model_id="claude-sonnet-4-20250514",
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
    ),
}
```

## Related Skills

- `industry-grading-scale` - Detailed grading scale design
- `implementation-theory-alignment` - Aligning implementation with design docs
