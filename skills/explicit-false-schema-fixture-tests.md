---
name: explicit-false-schema-fixture-tests
description: "Skill: Explicit-False Schema Fixture Tests"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Explicit-False Schema Fixture Tests

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Add explicit-false capability field tests to t0/t1 fixture schema and loader tests |
| Outcome | Success — 11 new tests added, all 4575 unit tests pass, coverage 75.85% |
| PR | HomericIntelligence/ProjectScylla#1459 |
| Issue | HomericIntelligence/ProjectScylla#1435 |

## When to Use

Use this pattern when:

- A schema defines optional boolean fields with `default=false` (field absence is valid)
- Fixture YAML files for lower tiers (baseline configs) explicitly set those fields to `false` for documentation/consistency
- You want test coverage that distinguishes the **explicit-false path** from the **field-absent (default) path**
- A follow-up issue asks to add tests for a previously untested code path in schema validation

## Problem Solved

When optional boolean schema fields have `default=false`, tests that only check field-absence implicitly cover the default but never exercise explicit `false` values. This means:

1. The schema's `boolean` type constraint for those fields is not exercised
2. The loader's handling of explicit `false` vs. absent is not verified
3. Schema completeness tests only pass because `additionalProperties: false` wasn't triggered — not because the field values were validated

## Verified Workflow

### 1. Identify the gap

Check fixture YAML files for the affected tiers:

```bash
cat tests/fixtures/config/tiers/t0.yaml
cat tests/fixtures/config/tiers/t1.yaml
```

Verify the fields are present with explicit `false` values (not just absent).

### 2. Add schema tests (parametrized)

In `TestTierSchema` (or equivalent schema test class), add:

```python
@pytest.mark.parametrize("field", ["uses_tools", "uses_delegation", "uses_hierarchy"])
def test_capability_field_explicit_false(self, schema: dict[str, Any], field: str) -> None:
    """Schema accepts capability fields explicitly set to false."""
    check_schema({"tier": "t0", "name": "Vanilla", field: False}, schema)

@pytest.mark.parametrize("field", ["uses_tools", "uses_delegation", "uses_hierarchy"])
def test_capability_field_explicit_true(self, schema: dict[str, Any], field: str) -> None:
    """Schema accepts capability fields explicitly set to true."""
    check_schema({"tier": "t4", "name": "Hierarchy", field: True}, schema)

def test_capability_fields_absent(self, schema: dict[str, Any]) -> None:
    """Schema accepts tier when all capability fields are absent (default-false path)."""
    check_schema({"tier": "t0", "name": "Vanilla"}, schema)

def test_capability_fields_all_explicit_false(self, schema: dict[str, Any]) -> None:
    """Schema accepts t0/t1 fixture pattern: all three capability fields explicitly false."""
    check_schema(
        {
            "tier": "t0",
            "name": "Vanilla",
            "description": "Base LLM with zero-shot prompting",
            "uses_tools": False,
            "uses_delegation": False,
            "uses_hierarchy": False,
        },
        schema,
    )
```

### 3. Add loader tests (parametrized + tmp_path)

In `TestConfigLoaderTier` (or equivalent loader test class), add three tests:

```python
@pytest.mark.parametrize("tier_id", ["t0", "t1"])
def test_load_tier_capability_fields_explicit_false(self, tier_id: str) -> None:
    """t0 and t1 fixture files have explicit false capability fields that load correctly."""
    loader = ConfigLoader(base_path=FIXTURES_PATH)
    tier = loader.load_tier(tier_id)

    assert tier.uses_tools is False
    assert tier.uses_delegation is False
    assert tier.uses_hierarchy is False

def test_load_tier_explicit_false_fields_via_tmp_path(self, tmp_path: Path) -> None:
    """Explicit-false capability fields in a tier YAML load as False (not absent-default)."""
    tiers_dir = tmp_path / "config" / "tiers"
    tiers_dir.mkdir(parents=True)
    (tiers_dir / "t0.yaml").write_text(
        "tier: t0\nname: Vanilla\ndescription: Test\n"
        "uses_tools: false\nuses_delegation: false\nuses_hierarchy: false\n"
    )

    loader = ConfigLoader(base_path=tmp_path)
    tier = loader.load_tier("t0")

    assert tier.uses_tools is False
    assert tier.uses_delegation is False
    assert tier.uses_hierarchy is False

def test_load_tier_default_false_when_absent(self, tmp_path: Path) -> None:
    """Absent capability fields in a tier YAML default to False."""
    tiers_dir = tmp_path / "config" / "tiers"
    tiers_dir.mkdir(parents=True)
    (tiers_dir / "t0.yaml").write_text("tier: t0\nname: Vanilla\n")

    loader = ConfigLoader(base_path=tmp_path)
    tier = loader.load_tier("t0")

    assert tier.uses_tools is False
    assert tier.uses_delegation is False
    assert tier.uses_hierarchy is False
```

### 4. Verify no production code changes needed

Check that:
- Fixture YAML files already have the explicit fields (or add them)
- The Pydantic model already defines `default=False` for the fields
- No schema changes required (fields should already be optional booleans)

### 5. Run tests and pre-commit

```bash
pixi run python -m pytest tests/unit/config/ -v
pre-commit run --all-files
```

## Key Insight: Two Distinct Test Paths

| Path | What it tests |
|------|--------------|
| Field absent | Pydantic default kicks in; schema `additionalProperties` not triggered |
| Field explicit `false` | Schema `boolean` type constraint exercised; loader correctly parses YAML `false` as Python `False` |

Both paths should be covered. The explicit-false path is the one that t0/t1 fixtures use for documentation clarity.

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results

- 11 new tests added (8 schema, 3 loader — parametrized = 11 test IDs)
- 0 production code changes
- Full unit suite: 4575 passed, 1 skipped
- Coverage: 75.85% (above 75% threshold)
- Pre-commit: all hooks passed
