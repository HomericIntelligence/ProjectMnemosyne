---
name: expand-tier-fixture-coverage
description: Expand YAML fixture files and test parametrize lists when adding new
  tiers to the testing tier registry. Use when tier count assertions or schema parametrize
  lists are out of sync with fixture files.
category: testing
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Expand Tier Fixture Coverage

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-04 |
| Objective | Add YAML fixture files for tiers t2–t6 and update tests to cover the full tier range |
| Outcome | Success — 7 fixtures, 4331 tests passing, 75.17% unit coverage |

## When to Use

- A new tier is added to the ablation study framework and needs a fixture file
- `test_load_all_tiers` asserts a hardcoded count that is smaller than the actual tier set
- `test_real_tier_fixture_is_valid` parametrize list does not include the new fixture files
- `tests/fixtures/config/tiers/` has fewer YAML files than tiers defined in the tier taxonomy

## Verified Workflow

### 1. Check what fixtures exist

```bash
ls tests/fixtures/config/tiers/
```

### 2. Read existing fixtures to learn the field schema

```bash
# Confirm required fields: tier, name, description, uses_tools, uses_delegation, uses_hierarchy
cat tests/fixtures/config/tiers/t0.yaml
cat tests/fixtures/config/tiers/t1.yaml
```

### 3. Create one fixture per missing tier

Each fixture **must**:
- Set `tier:` to the filename stem (e.g. `"t2"` for `t2.yaml`) — mismatch raises `ConfigurationError`
- Include all required fields: `tier`, `name`, `description`, `uses_tools`, `uses_delegation`, `uses_hierarchy`
- Exercise a **distinct** boolean flag to differentiate the tier

| Tier | Name | Distinguishing flag |
|------|------|---------------------|
| t2 | Tooling | `uses_tools: true` |
| t3 | Delegation | `uses_delegation: true` |
| t4 | Hierarchy | `uses_hierarchy: true` |
| t5 | Hybrid | `uses_tools: true`, `uses_delegation: true` |
| t6 | Super | all three flags `true` |

Example `t2.yaml`:

```yaml
# Test fixture: Tier 2 (Tooling)
tier: "t2"
name: "Tooling"
description: "External tools and MCP servers"
uses_tools: true
uses_delegation: false
uses_hierarchy: false
```

### 4. Update `test_config_loader.py` — count assertion

Find `assert len(tiers) == <old_count>` in `test_load_all_tiers` and update it to the new total.
Add name assertions for each new tier:

```python
assert len(tiers) == 7
assert "t2" in tiers
assert tiers["t2"].name == "Tooling"
# ... repeat for t3–t6
```

### 5. Update `test_json_schemas.py` — parametrize list

```python
@pytest.mark.parametrize(
    "fixture_file",
    ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"],
)
```

### 6. Verify

```bash
pixi run python -m pytest tests/unit/config/test_config_loader.py tests/unit/config/test_json_schemas.py -v
pixi run python -m pytest tests/unit/ -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

- Fixtures directory: `tests/fixtures/config/tiers/`
- Config loader test: `tests/unit/config/test_config_loader.py`
- Schema validation test: `tests/unit/config/test_json_schemas.py`
- Test count after change: 4331 passed (from 4316 before adding 5 new fixtures × 3 parametrized test cases)
- Coverage: 75.17% unit (required floor: 75%)

## References

- `validate-tier-id-filename-consistency` — explains the `tier:` == filename stem invariant
- `fix-tests-after-config-refactor` — general pattern for updating count assertions after structural changes
- CLAUDE.md > Testing Tiers for the canonical t0–t6 taxonomy
