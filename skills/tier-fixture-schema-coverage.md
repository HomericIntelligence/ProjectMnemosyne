---
name: tier-fixture-schema-coverage
description: 'TRIGGER CONDITIONS: Use when schema validation tests parametrize over
  tier fixture files but only early tiers exist (e.g. t0/t1), or when new tier-specific
  boolean fields need coverage across the full tier range.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# tier-fixture-schema-coverage

How to extend schema coverage by adding YAML fixture files for each testing tier with distinct field combinations.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Add fixture files for t2-t6 so schema tests parametrize over the full tier range, each exercising distinct boolean capability fields |
| Outcome | Success — 7 fixture files (t0-t6) all validate against tier.schema.json; 505 tier-related tests pass |

## When to Use

- Schema validation tests use `@pytest.mark.parametrize("fixture_file", ["t0.yaml", "t1.yaml"])` and need expansion
- New tier-specific boolean fields (`uses_tools`, `uses_delegation`, `uses_hierarchy`) are added to the schema
- `tests/fixtures/config/tiers/` has gaps (missing t2-t6) while t0/t1 exist
- You want each tier fixture to exercise a distinct combination of capability flags

## Verified Workflow

### Step 1 — Check which fixtures are missing

```bash
ls tests/fixtures/config/tiers/
# If only t0.yaml and t1.yaml exist, proceed
```

### Step 2 — Create one fixture per tier with distinct field combinations

Each fixture should set tier-specific boolean flags to exercise distinct schema paths:

```yaml
# t2.yaml — Tooling tier: only uses_tools
tier: "t2"
name: "Tooling"
description: "External tools and MCP servers"
uses_tools: true
uses_delegation: false
uses_hierarchy: false
```

```yaml
# t3.yaml — Delegation tier: only uses_delegation
tier: "t3"
name: "Delegation"
description: "Flat multi-agent with specialist agents"
uses_tools: false
uses_delegation: true
uses_hierarchy: false
```

```yaml
# t4.yaml — Hierarchy tier: only uses_hierarchy
tier: "t4"
name: "Hierarchy"
description: "Nested orchestration with orchestrator agents"
uses_tools: false
uses_delegation: false
uses_hierarchy: true
```

```yaml
# t5.yaml — Hybrid tier: tools + delegation
tier: "t5"
name: "Hybrid"
description: "Best combinations and permutations"
uses_tools: true
uses_delegation: true
uses_hierarchy: false
```

```yaml
# t6.yaml — Super tier: all enabled
tier: "t6"
name: "Super"
description: "Everything enabled at maximum capability"
uses_tools: true
uses_delegation: true
uses_hierarchy: true
```

### Step 3 — Expand the parametrize list in the schema test

```python
# Before
@pytest.mark.parametrize("fixture_file", ["t0.yaml", "t1.yaml"])

# After
@pytest.mark.parametrize("fixture_file", ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"])
```

### Step 4 — Run tests to verify

```bash
pixi run python -m pytest tests/ -v -k "tier"
# Expect all tests to pass
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Boolean flag coverage matrix** (ensures each tier exercises unique schema paths):

| Tier | uses_tools | uses_delegation | uses_hierarchy |
|------|-----------|----------------|----------------|
| t0   | —         | —              | —              |
| t1   | —         | —              | —              |
| t2   | true      | false          | false          |
| t3   | false     | true           | false          |
| t4   | false     | false          | true           |
| t5   | true      | true           | false          |
| t6   | true      | true           | true           |

**File layout:**
```
tests/fixtures/config/tiers/
├── t0.yaml   # Vanilla (no capability flags)
├── t1.yaml   # Prompted (no capability flags)
├── t2.yaml   # Tooling (uses_tools only)
├── t3.yaml   # Delegation (uses_delegation only)
├── t4.yaml   # Hierarchy (uses_hierarchy only)
├── t5.yaml   # Hybrid (tools + delegation)
└── t6.yaml   # Super (all enabled)
```

**Test reference:** `tests/unit/config/test_json_schemas.py:154` — `test_real_tier_fixture_is_valid`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1381, PR #1423 | [notes.md](../references/notes.md) |
