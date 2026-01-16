# Skill: Claude Code Settings Configuration for E2E Tests

| Field | Value |
|-------|-------|
| **Date** | 2026-01-16 |
| **Objective** | Configure Claude Code settings.json per test workspace to control thinking mode via API rather than prompt injection |
| **Outcome** | ✅ Successfully implemented settings.json creation with proper thinking mode control |
| **Context** | E2E evaluation framework needed proper workspace-level configuration for Claude Code |

## When to Use This Skill

Use this skill when:
- You need to configure Claude Code settings for test workspaces
- You want to control thinking mode programmatically via workspace settings
- You're implementing per-test configuration in the E2E framework
- You need to ensure `.claude/settings.json` is created for every test run

## Problem Statement

The E2E evaluation framework was controlling thinking mode by injecting keywords into prompts (e.g., "ultrathink"), which is not the proper way to control Claude Code's thinking feature. The framework needed to:

1. Create `.claude/settings.json` for every test workspace
2. Set `alwaysThinkingEnabled` based on the `--thinking` CLI flag
3. Handle special cases (T0/00 and T0/01) where `.claude/` is normally removed
4. Ensure consistent behavior across all tiers and subtests

## Verified Workflow

### Step 1: Add settings.json Creation Method

**File**: `src/scylla/e2e/tier_manager.py`

Add the `json` import:
```python
import json
```

Add method to create settings.json:
```python
def _create_settings_json(
    self,
    workspace: Path,
    thinking_enabled: bool = False,
) -> None:
    """Create .claude/settings.json for workspace configuration.

    Args:
        workspace: Target workspace directory
        thinking_enabled: Whether to enable thinking mode

    """
    settings = {
        "alwaysThinkingEnabled": thinking_enabled,
    }

    settings_dir = workspace / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
```

### Step 2: Update prepare_workspace Signature

**File**: `src/scylla/e2e/tier_manager.py`

Update the signature to accept `thinking_enabled`:
```python
def prepare_workspace(
    self,
    workspace: Path,
    tier_id: TierID,
    subtest_id: str,
    baseline: TierBaseline | None = None,
    thinking_enabled: bool = False,  # NEW
) -> None:
```

### Step 3: Handle T0 Special Cases

**File**: `src/scylla/e2e/tier_manager.py`

Update T0/00 and T0/01 special cases to create settings.json before returning:
```python
if tier_id == TierID.T0:
    claude_md = workspace / "CLAUDE.md"
    claude_dir = workspace / ".claude"

    if subtest_id == "00":
        # 00-empty: Remove all configuration (no system prompt)
        if claude_md.exists():
            claude_md.unlink()
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        # Still create settings.json for thinking control
        self._create_settings_json(workspace, thinking_enabled)
        return
    elif subtest_id == "01":
        # 01-vanilla: Use tool defaults (no CLAUDE.md)
        if claude_md.exists():
            claude_md.unlink()
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        # Still create settings.json for thinking control
        self._create_settings_json(workspace, thinking_enabled)
        return
```

Add settings.json creation at the end of normal flow:
```python
# Step 2: Overlay sub-test configuration
self._overlay_subtest(workspace, subtest)

# Create settings.json with thinking configuration
self._create_settings_json(workspace, thinking_enabled)
```

### Step 4: Pass thinking_enabled from Executor

**File**: `src/scylla/e2e/subtest_executor.py`

Compute thinking_enabled and pass to tier_manager:
```python
# Prepare tier configuration in workspace
thinking_enabled = (
    self.config.thinking_mode is not None
    and self.config.thinking_mode != "None"
)
self.tier_manager.prepare_workspace(
    workspace=workspace,
    tier_id=tier_id,
    subtest_id=subtest.id,
    baseline=baseline,
    thinking_enabled=thinking_enabled,
)
```

## Failed Attempts

### ❌ Attempt 1: Running Tests Without pixi

**What was tried**: Running E2E tests directly with `python scripts/run_e2e_experiment.py`

**Why it failed**: Missing dependencies (pydantic not found) because the script needs to run within the pixi environment

**Lesson**: Always use `pixi run python` for scripts that require project dependencies

### ❌ Attempt 2: Using json.dumps without write

**What was tried**: Initially used `.write_text(json.dumps(settings, indent=2))`

**Why it failed**: While this worked, using a context manager with `json.dump()` is more idiomatic and safer

**Lesson**: Use `with open() as f: json.dump()` for writing JSON files

## Results & Parameters

### Verification Commands

**Test with thinking disabled (default)**:
```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 --runs 1 --max-subtests 1 -v
```

**Test with thinking enabled**:
```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 --runs 1 --max-subtests 1 --thinking UltraThink --fresh -v
```

**Verify settings.json creation**:
```bash
find results -name "settings.json" -exec echo "File: {}" \; -exec cat {} \;
```

### Expected Output

**Thinking disabled**:
```json
{
  "alwaysThinkingEnabled": false
}
```

**Thinking enabled**:
```json
{
  "alwaysThinkingEnabled": true
}
```

### Test Results

| Test | CLI Flag | Result | Score | Cost | Duration |
|------|----------|--------|-------|------|----------|
| Thinking Disabled | Default | ✅ PASS | 0.950 | $0.0888 | 65.0s |
| Thinking Enabled | `--thinking UltraThink` | ✅ PASS | 0.930 | $0.0910 | 62.8s |

## Key Insights

1. **Priority hierarchy**: CLI `--thinking` flag takes global priority over per-test configuration
2. **Special case handling**: T0/00 and T0/01 remove `.claude/` directory but still need settings.json
3. **Settings location**: `.claude/settings.json` must be created in workspace root
4. **API control**: Using workspace settings is the proper way to control Claude Code features (not prompt injection)

## Files Modified

| File | Changes |
|------|---------|
| `src/scylla/e2e/tier_manager.py` | Added `json` import, `_create_settings_json()` method, updated `prepare_workspace()` signature and logic |
| `src/scylla/e2e/subtest_executor.py` | Pass `thinking_enabled` parameter to tier_manager |

## Related Documentation

- [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings)
- [Thinking Mode Configuration](.claude/shared/thinking-mode.md)
- [E2E Framework Bug Fixes Skill](../e2e-framework-bug-fixes/)
