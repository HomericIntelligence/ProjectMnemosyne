# Raw Session Notes

## Timeline

1. **Initial Problem**: T0 subtest 00 should use `--system-prompt ""` but flag was missing
2. **Root Cause Analysis**: Traced data flow from YAML → Parser → Dataclass → Executor
3. **Fix**: Added `system_prompt_mode` to `SubTestConfig` and propagated through chain
4. **User Observation**: Noticed DRY violation with duplicate `system_prompt_mode` fields
5. **Cleanup**: Removed `TierConfig.system_prompt_mode` entirely

## Code Flow Discovery

```
YAML Definition
  ↓
tests/claude-code/shared/subtests/t0/00-empty.yaml:4
  system_prompt_mode: none
  ↓
Parser (tier_manager.py:178)
  system_prompt_mode = config_data.get("system_prompt_mode", "custom")
  ↓
Dataclass Storage (models.py:165)
  system_prompt_mode: str = "custom"
  ↓
Constructor (tier_manager.py:192)
  SubTestConfig(..., system_prompt_mode=system_prompt_mode)
  ↓
Usage (subtest_executor.py:1045)
  cmd = self.adapter._build_command(..., subtest.system_prompt_mode, ...)
  ↓
Command Building (claude_code.py:200)
  if system_prompt_mode == "none":
      cmd.extend(["--system-prompt", ""])
```

## DRY Violation Found

**Duplicate Field**:
- `TierConfig.system_prompt_mode` (models.py:200) - hardcoded to "custom"
- `SubTestConfig.system_prompt_mode` (models.py:165) - parsed from YAML

**Why TierConfig version was wrong**:
1. Hardcoded to "custom" (tier_manager.py:80)
2. Only used for logging (runner.py:650)
3. Used in deprecated code path that's never called (subtest_executor.py:893)
4. Comment said: "determined per sub-test, not per tier"

## Commits

1. `0cda14f` - fix(e2e): propagate system_prompt_mode from subtest YAML to command building
2. `2de6322` - refactor(e2e): remove duplicate system_prompt_mode from TierConfig

## Testing Results

All 51 tests pass:
- 14 model tests
- 37 tier manager tests

New tests added:
- `test_system_prompt_mode()` - Unit test for field storage
- `test_parse_system_prompt_mode_none()` - Integration test for YAML parsing
- `test_parse_system_prompt_mode_default()` - Integration test for default mode
- `test_system_prompt_mode_defaults_to_custom()` - Integration test for fallback

## Key Files

**Modified**:
- scylla/e2e/models.py
- scylla/e2e/tier_manager.py
- scylla/e2e/subtest_executor.py
- scylla/e2e/runner.py
- tests/unit/e2e/test_models.py
- tests/unit/e2e/test_tier_manager.py

**Analyzed**:
- tests/claude-code/shared/subtests/t0/00-empty.yaml
- tests/claude-code/shared/subtests/t0/01-vanilla.yaml
- scylla/adapters/claude_code.py
- scylla/executor/tier_config.py
- config/tiers/tiers.yaml

## Verification Commands

```bash
# Check YAML configs
grep -r "system_prompt_mode" tests/claude-code/shared/subtests/

# Trace through code
grep -n "system_prompt_mode" scylla/e2e/*.py

# Verify no duplication in configs
grep -r "system_prompt_mode" config/

# Run tests
python -m pytest tests/unit/e2e/test_models.py tests/unit/e2e/test_tier_manager.py -v
```

## Learning: Two-Phase Fix

**Phase 1: Fix the Bug**
- Add missing field to dataclass
- Parse from YAML
- Use in execution code
- Add tests

**Phase 2: Eliminate Tech Debt**
- Identify DRY violations
- Remove duplicate fields
- Update all references
- Mark deprecated paths
- Update tests

This two-phase approach ensures:
1. Bug is fixed correctly
2. Root cause is eliminated
3. Future maintenance is easier
4. No hidden duplicates remain
