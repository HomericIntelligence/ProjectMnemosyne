---
name: "Fix YAML Config Propagation"
description: "Debug pattern for fixing YAML config fields that aren't propagating to execution, plus eliminating DRY violations in config dataclasses"
category: debugging
date: 2026-02-05
user-invocable: false
---
# Fix YAML Config Propagation

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-05 |
| Objective | | Field | Value | |-------|-------| | Date | 2026-02-05 | | Objective | Fix T0 subtest 00 missing `--system-prompt ""` flag due to YAML config not ... |
| Outcome | Operational |


## Session Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-05 |
| Objective | Fix T0 subtest 00 missing `--system-prompt ""` flag due to YAML config not propagating to command building |
| Outcome | ✅ SUCCESS - Fixed config propagation + eliminated DRY violation |
| Root Cause | Config field defined in YAML but not parsed/stored/used in dataclass chain |
| Bonus | Discovered and removed duplicate `system_prompt_mode` from `TierConfig` |

## When to Use This Skill

Use this debugging pattern when:

1. **Config defined in YAML but not working**:
   - Field exists in YAML file
   - Feature/behavior doesn't work as expected
   - Commands or execution don't reflect YAML values

2. **Symptoms**:
   - Different subtests behave identically when they should differ
   - CLI flags missing from generated commands
   - Hardcoded values override user configuration

3. **DRY violation indicators**:
   - Same config field in multiple dataclasses
   - Hardcoded overrides that match field defaults
   - Comments saying "determined per X, not per Y" but field exists in Y

## Verified Workflow

### Step 1: Trace the Data Flow

**Identify all locations** where the config should flow:

```bash
# 1. Find where config is defined
grep -r "system_prompt_mode" tests/claude-code/shared/subtests/

# 2. Find where it's parsed
grep -n "system_prompt_mode" scylla/e2e/tier_manager.py

# 3. Find where it's stored
grep -n "system_prompt_mode" scylla/e2e/models.py

# 4. Find where it's used
grep -n "system_prompt_mode" scylla/e2e/subtest_executor.py
grep -n "system_prompt_mode" scylla/adapters/
```

**Expected flow**:
1. YAML file defines value
2. Parser reads YAML and extracts field
3. Dataclass stores field
4. Executor uses field when building commands/running logic

### Step 2: Find the Broken Link

Check each stage:

```python
# ❌ BROKEN: Parser ignores field
# tier_manager.py:143
resources: dict[str, Any] = config_data.get("resources", {})
# Missing: system_prompt_mode = config_data.get("system_prompt_mode", "custom")

# ❌ BROKEN: Dataclass lacks field
# models.py:164
agent_teams: bool = False
# Missing: system_prompt_mode: str = "custom"

# ❌ BROKEN: Wrong source used
# subtest_executor.py:1045
tier_config.system_prompt_mode,  # Uses tier-level (hardcoded)
# Should be: subtest.system_prompt_mode
```

### Step 3: Fix Each Broken Link

**Parse the field**:
```python
# tier_manager.py:178
system_prompt_mode = config_data.get("system_prompt_mode", "custom")
```

**Store in dataclass**:
```python
# models.py:165
system_prompt_mode: str = "custom"  # "none", "default", "custom"

# models.py:179 (in to_dict)
"system_prompt_mode": self.system_prompt_mode,
```

**Use correct source**:
```python
# subtest_executor.py:1045
subtest.system_prompt_mode,  # Use subtest-level, not tier-level
```

**Pass to constructor**:
```python
# tier_manager.py:192
SubTestConfig(
    ...,
    system_prompt_mode=system_prompt_mode,
)
```

### Step 4: Eliminate DRY Violations (Bonus)

If you find duplicates during tracing:

```bash
# Find all uses of the field
grep -n "system_prompt_mode" scylla/e2e/*.py

# Identify which is the source of truth
# - SubTestConfig: Parsed from YAML, used in execution ✅
# - TierConfig: Hardcoded to "custom", only used for logging ❌
```

**Remove the duplicate**:
1. Delete field from unnecessary dataclass
2. Update all references to use correct source
3. Mark deprecated code paths
4. Update tests

### Step 5: Add Tests

**Unit tests for dataclass**:
```python
def test_system_prompt_mode(self) -> None:
    """Test that system_prompt_mode is correctly stored and serialized."""
    config_none = SubTestConfig(
        id="00",
        name="Empty",
        description="No system prompt",
        system_prompt_mode="none",
    )
    assert config_none.system_prompt_mode == "none"
    assert config_none.to_dict()["system_prompt_mode"] == "none"
```

**Integration tests for parsing**:
```python
def test_parse_system_prompt_mode_none(self, tmp_path: Path) -> None:
    """Test that system_prompt_mode='none' is parsed from T0 YAML."""
    config_file.write_text(
        yaml.safe_dump({
            "name": "Empty System Prompt",
            "system_prompt_mode": "none",
        })
    )

    subtests = manager._discover_subtests(TierID.T0, tier_dir)
    assert subtests[0].system_prompt_mode == "none"
```

### Step 6: Verify End-to-End

```bash
# After fix, check that commands have correct flags
grep -- "--system-prompt ''" results/*/T0/00/*/agent/replay.sh  # Should match
grep -- "--system-prompt" results/*/T0/01/*/agent/replay.sh     # Should NOT match
```

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Initial Assumption: Tier-Level Config

**What we tried**: Initially assumed `tier_config.system_prompt_mode` should be used

**Why it failed**:
- `TierConfig.system_prompt_mode` was hardcoded to `"custom"` for all tiers
- Comment in code said: *"system_prompt_mode is determined per sub-test, not per tier"*
- This was a legacy field that wasn't actually used

**Learning**: When you see hardcoded values that override config, check if the field is even needed

### ❌ Only Fixing the Symptom

**What we tried**: Could have just changed `tier_config.system_prompt_mode` to use subtest value

**Why it's wrong**:
- Would leave duplicate fields in both `TierConfig` and `SubTestConfig`
- Violates DRY principle
- Creates confusion about source of truth

**Learning**: When fixing config propagation bugs, check for DRY violations and eliminate duplicates

## Results & Parameters

### Files Modified

**Core fix** (3 files):
1. `scylla/e2e/models.py:165` - Added `system_prompt_mode` to `SubTestConfig`
2. `scylla/e2e/tier_manager.py:178` - Parse from YAML
3. `scylla/e2e/subtest_executor.py:1045` - Use `subtest.system_prompt_mode`

**DRY cleanup** (5 files):
1. `scylla/e2e/models.py:184-203` - Removed from `TierConfig`
2. `scylla/e2e/tier_manager.py:71-85` - Removed hardcoded assignment
3. `scylla/e2e/runner.py:648` - Removed from logging
4. `scylla/e2e/subtest_executor.py:860-895` - Marked legacy method as deprecated
5. `tests/unit/e2e/test_models.py:107-122` - Updated test

### Tests Added

**Unit tests** (2 files):
1. `tests/unit/e2e/test_models.py:73-103` - `SubTestConfig.system_prompt_mode` field tests
2. `tests/unit/e2e/test_tier_manager.py:512-542` - YAML parsing tests

**Test coverage**: 51 tests pass ✅

### Key Code Patterns

**Parsing from YAML**:
```python
# tier_manager.py:178-179
system_prompt_mode = config_data.get("system_prompt_mode", "custom")
```

**Storing in dataclass**:
```python
# models.py:165
system_prompt_mode: str = "custom"  # "none", "default", "custom"
```

**Using in command building**:
```python
# subtest_executor.py:1045
cmd = self.adapter._build_command(
    adapter_config,
    str(agent_prompt_file.resolve()),
    None,
    subtest.system_prompt_mode,  # ✅ Use subtest-level
    agent_name,
)
```

### YAML Config Format

```yaml
# tests/claude-code/shared/subtests/t0/00-empty.yaml
name: Empty System Prompt
description: No system prompt - absolute baseline
system_prompt_mode: none  # ← Key field

# tests/claude-code/shared/subtests/t0/01-vanilla.yaml
name: Vanilla System Prompt
description: Use Claude Code default
system_prompt_mode: default  # ← Key field
```

## Debugging Checklist

- [ ] YAML file has the field defined
- [ ] Parser function reads the field with `config_data.get("field_name")`
- [ ] Dataclass has field defined with correct type
- [ ] Dataclass `to_dict()` includes the field for serialization
- [ ] Constructor call passes the parsed value
- [ ] Execution code uses the correct dataclass field (not a duplicate)
- [ ] No hardcoded overrides that ignore the config
- [ ] Tests verify parsing, storage, and serialization
- [ ] No DRY violations (same field in multiple places)
- [ ] Deprecated code paths are marked and documented

## Related Skills

- `debug-config-data-flow` - Methodology for tracing config through system
- `eliminate-dry-violations` - Pattern for identifying duplicate config
- `yaml-to-dataclass-mapping` - Best practices for config parsing

## References

- Conversation: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/*.jsonl`
- Original issue: T0 subtest 00 missing `--system-prompt ""` flag
- Root cause: `system_prompt_mode` not propagated from YAML to command building
- Bonus fix: Eliminated `TierConfig.system_prompt_mode` duplicate field
