---
name: pydantic-model-dump
description: Fix Pydantic v2 model serialization using .model_dump() instead of .to_dict()
category: refactor
date: 2026-01-04
tags: [pydantic, serialization, migration, python, bug-fix]
---

# Pydantic v2 Model Serialization Fix

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Fix AttributeError when serializing Pydantic BaseModel objects to JSON |
| **Outcome** | ✅ Successfully migrated from `.to_dict()` to `.model_dump()` |
| **Project** | ProjectScylla |
| **PR** | [#136](https://github.com/HomericIntelligence/ProjectScylla/pull/136) |

## When to Use

Use this skill when you encounter:
- `AttributeError: 'ModelName' object has no attribute 'to_dict'`
- Pydantic v2 BaseModel serialization errors
- Migration from Pydantic v1 to v2
- JSON serialization crashes in code using Pydantic models

## Problem

Pydantic v2 changed the serialization API:
- **v1**: `.dict()` and custom `.to_dict()` methods
- **v2**: `.model_dump()` for serialization

Code using `.to_dict()` on Pydantic BaseModel objects will crash with:
```python
AttributeError: 'AdapterTokenStats' object has no attribute 'to_dict'
```

## Verified Workflow

### 1. Identify Pydantic Models
```python
# Check if a class is a Pydantic BaseModel
from pydantic import BaseModel

class AdapterTokenStats(BaseModel):  # ← Pydantic v2 model
    input_tokens: int = 0
    output_tokens: int = 0
```

### 2. Find All `.to_dict()` Calls
```bash
# Search for problematic calls
grep -r "\.to_dict()" src/

# Filter to Pydantic models only (check class definitions)
grep -B 5 "class.*BaseModel" src/
```

### 3. Replace with `.model_dump()`
```python
# Before (FAILS):
"token_stats": result.token_stats.to_dict()

# After (WORKS):
"token_stats": result.token_stats.model_dump()
```

### 4. Verify Dataclass `.to_dict()` is OK
```python
# Dataclasses with custom .to_dict() are fine
@dataclass
class TokenStats:
    def to_dict(self) -> dict:  # ← Custom method, not Pydantic
        return {"field": self.field}

# This is OK:
result = token_stats.to_dict()
```

### 5. Test the Fix
```bash
# Run the code that was crashing
python scripts/run_e2e_experiment.py

# Should now complete without AttributeError
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Using `.dict()` method | Pydantic v2 deprecated `.dict()`, use `.model_dump()` instead |
| Adding custom `.to_dict()` to BaseModel | Overriding Pydantic methods breaks model functionality |
| Type checking before call | Doesn't solve the problem, just detects it |

## Results & Parameters

### Fix Pattern

```python
# Audit checklist:
# 1. Find all .to_dict() calls
# 2. Identify if object is Pydantic BaseModel
# 3. Replace with .model_dump()
# 4. Leave dataclass .to_dict() unchanged

# Example from ProjectScylla:
# File: src/scylla/e2e/subtest_executor.py:109

# Before:
result_data = {
    "token_stats": result.token_stats.to_dict(),  # ❌ FAILS
}

# After:
result_data = {
    "token_stats": result.token_stats.model_dump(),  # ✅ WORKS
}
```

### Verification Command

```bash
# Find remaining .to_dict() on Pydantic models:
rg "\.to_dict\(\)" src/ | while read line; do
  # Check if it's a BaseModel
  echo "$line"
done
```

## Key Learnings

1. **Pydantic v2 Migration**: Always use `.model_dump()` for BaseModel serialization
2. **Selective Replacement**: Only replace `.to_dict()` on Pydantic models, not dataclasses
3. **Audit All Occurrences**: Search entire codebase to prevent future crashes
4. **Pre-commit Saves Time**: Ruff/mypy can catch these if properly configured

## Related Skills

- `debugging/attribute-error-debugging` - General AttributeError troubleshooting
- `refactor/api-migration` - Handling breaking API changes

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #136 - E2E runner crash fix | [notes.md](../../references/notes.md) |
