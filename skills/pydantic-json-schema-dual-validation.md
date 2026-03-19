---
name: pydantic-json-schema-dual-validation
description: 'TRIGGER CONDITIONS: Enforcing a cross-field semantic constraint (e.g.,
  field A=true requires field B=true) in a config model loaded from YAML. Use when:
  (1) a domain invariant exists between two boolean capability flags, (2) the codebase
  uses both Pydantic models AND JSON Schema for config validation, (3) you need to
  catch the violation at both schema validation and model instantiation time.'
category: validation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# pydantic-json-schema-dual-validation

Pattern for enforcing cross-field semantic constraints at two layers: JSON Schema `if/then` and Pydantic `model_validator`.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Enforce that `uses_hierarchy=true` requires `uses_delegation=true` in `TierConfig` — caught at both JSON Schema and Pydantic layers |
| Outcome | Success — dual-layer validation, 8 new tests, all 4463 unit tests pass, 80.25% coverage |

## When to Use

- A domain invariant exists between two boolean fields (e.g., `uses_hierarchy` implies `uses_delegation`)
- Config is loaded via a pipeline that validates JSON Schema first, then constructs a Pydantic model
- You want the same constraint enforced at both layers so the error is caught regardless of which layer runs first

## Verified Workflow

### Step 1 — Add `if/then` to JSON Schema (draft-07)

```json
{
  "if": {
    "properties": {"uses_hierarchy": {"const": true}},
    "required": ["uses_hierarchy"]
  },
  "then": {
    "properties": {"uses_delegation": {"const": true}},
    "required": ["uses_delegation"]
  }
}
```

Add this at the top level of the schema object (peer to `properties`/`required`).

### Step 2 — Add `model_validator` to Pydantic model

```python
from pydantic import model_validator

class TierConfig(BaseModel):
    uses_delegation: bool = False
    uses_hierarchy: bool = False

    @model_validator(mode="after")
    def validate_hierarchy_requires_delegation(self) -> "TierConfig":
        """Enforce that uses_hierarchy=True requires uses_delegation=True."""
        if self.uses_hierarchy and not self.uses_delegation:
            raise ValueError(
                f"uses_hierarchy=true requires uses_delegation=true (tier={self.tier!r})"
            )
        return self
```

Use `mode="after"` so all fields are already validated and coerced before the cross-field check runs.

### Step 3 — Fix any existing fixtures with the invalid combination

Check all YAML fixture files. Any file with the invalid combination must be corrected — it's the bug, not a test case.

### Step 4 — Test all four combinations

```python
# Invalid — must raise
def test_hierarchy_without_delegation_raises(self) -> None:
    with pytest.raises(ValidationError, match="uses_hierarchy"):
        TierConfig(tier="t4", name="Invalid", uses_hierarchy=True, uses_delegation=False)

# Valid combos
def test_hierarchy_with_delegation_is_valid(self) -> None:
    config = TierConfig(tier="t4", name="Hierarchy", uses_hierarchy=True, uses_delegation=True)

def test_hierarchy_false_delegation_false_is_valid(self) -> None:
    config = TierConfig(tier="t0", name="Baseline", uses_hierarchy=False, uses_delegation=False)

def test_hierarchy_false_delegation_true_is_valid(self) -> None:
    config = TierConfig(tier="t3", name="Delegation", uses_hierarchy=False, uses_delegation=True)
```

### Step 5 — Test JSON Schema layer separately

```python
def test_rejects_hierarchy_without_delegation(self, schema):
    with pytest.raises(jsonschema.ValidationError):
        check_schema({"tier": "t4", "name": "Invalid", "uses_hierarchy": True, "uses_delegation": False}, schema)

def test_accepts_hierarchy_with_delegation(self, schema):
    check_schema({"tier": "t4", "name": "Hierarchy", "uses_hierarchy": True, "uses_delegation": True}, schema)
```

### Step 6 — Loader integration test (no regex match on error message)

```python
def test_load_tier_hierarchy_without_delegation_raises_configuration_error(self, tmp_path):
    tiers_dir = tmp_path / "config" / "tiers"
    tiers_dir.mkdir(parents=True)
    (tiers_dir / "t4.yaml").write_text(
        "tier: 't4'\nname: 'Invalid Hierarchy'\nuses_hierarchy: true\nuses_delegation: false\n"
    )
    loader = ConfigLoader(tmp_path)
    with pytest.raises(ConfigurationError):
        loader.load_tier("t4")
```

**Do NOT use `match=` on the ConfigurationError** — see Failed Attempts.

## Failed Attempts

| Attempt | What happened | Why it failed |
|---------|--------------|---------------|
| `pytest.raises(ConfigurationError, match="uses_delegation")` in loader test | Test failed: `AssertionError: Regex pattern did not match. Actual message: 'True was expected'` | jsonschema `if/then` error message is `"True was expected"` (from `const: true` check), not the field name. The JSON Schema layer runs before Pydantic, so the Pydantic message never appears. |

## Results & Parameters

| Layer | Mechanism | Error type |
|-------|-----------|-----------|
| JSON Schema | `if/then` with `const: true` | `jsonschema.ValidationError` → `ConfigurationError` (loader wraps it) |
| Pydantic | `@model_validator(mode="after")` | `pydantic.ValidationError` → `ConfigurationError` (loader wraps it) |

**Key insight**: The jsonschema `if/then` `const` violation message is `"True was expected"`, not a field-name message. When testing the loader (which runs schema validation first), do not assert on the specific error message string.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1460, issue #1434 | `TierConfig.uses_hierarchy` → `uses_delegation` constraint; 4463 tests pass |
