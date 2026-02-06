# Implementation Notes: Experimental Feature Sub-tests

## Session Context

**Date**: 2026-02-05
**Objective**: Add T4 agent teams sub-tests to evaluate experimental Agent Teams feature
**PR**: #350

## Detailed Implementation Steps

### Step 1: Data Model Changes

**File**: `scylla/e2e/models.py`

Added two fields:
1. `SubTestConfig.agent_teams: bool = False` - marks test as using experimental feature
2. `ExperimentConfig.skip_agent_teams: bool = False` - CLI flag to filter tests

Both fields added to `to_dict()` and `load()` methods for serialization.

### Step 2: Discovery-Time Filtering

**File**: `scylla/e2e/tier_manager.py`

Modified three methods:

1. `load_tier_config()` - added `skip_agent_teams` parameter
2. `_discover_subtests()` - added filtering logic and parameter
3. `_create_settings_json()` - added env var injection

**Critical Code**:
```python
# Parse agent_teams flag
agent_teams = config_data.get("agent_teams", False)

# Skip if agent_teams is enabled but we're filtering them out
if skip_agent_teams and agent_teams:
    continue
```

### Step 3: Settings.json Environment Variable

**Location in code**: `tier_manager.py:_create_settings_json()`

**Order matters**: Add env section AFTER MCP servers but BEFORE writing file.

```python
# Add experimental agent teams environment variable
if subtest.agent_teams:
    if "env" not in settings:
        settings["env"] = {}
    settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
```

### Step 4: YAML Configuration Files

**Location**: `tests/claude-code/shared/subtests/t4/08-14.yaml`

**Template**:
```yaml
name: {orchestrator-name}-teams
description: 'L{level} orchestrator with agent teams: {orchestrator-name}'
extends_previous: true
agent_teams: true  # KEY FIELD
resources:
  agents:
    levels:
    - {0 or 1}
```

**Files Created**:
- 08-chief-architect-teams.yaml (L0)
- 09-agentic-workflows-orchestrator-teams.yaml (L1)
- 10-cicd-orchestrator-teams.yaml (L1)
- 11-foundation-orchestrator-teams.yaml (L1)
- 12-papers-orchestrator-teams.yaml (L1)
- 13-shared-library-orchestrator-teams.yaml (L1)
- 14-tooling-orchestrator-teams.yaml (L1)

### Step 5: CLI Integration

**Files Modified**:
1. `scripts/run_e2e_experiment.py` - parse args
2. Pass through to `ExperimentConfig`
3. Pass through to `tier_manager.load_tier_config()`

**Argument Position**: Added after `--max-subtests` and before `--use-containers`.

## Verification Scripts

### Script 1: Subtest Discovery

**Path**: `scratchpad/verify_subtests.py`

**Purpose**: Verify that discovery finds correct count with/without filtering.

**Key Checks**:
- Total count with all tests = 14
- Total count with filtering = 7
- Agent teams flag set correctly on variant tests
- No agent teams flag on baseline tests

### Script 2: Settings.json Generation

**Path**: `scratchpad/verify_settings.py`

**Purpose**: Verify env var injection in settings.json.

**Key Checks**:
- Regular tests have NO env section
- Agent teams tests HAVE env section
- Env var value is "1"
- settings.json is valid JSON

## Testing Results

### Unit Tests
```bash
pixi run pytest tests/unit/e2e/test_tier_manager.py -v
# Result: 34 passed in 0.50s
```

### Discovery Verification
```
✓ Expected 14 total subtests, got 14: PASS
✓ Expected 7 non-teams subtests, got 7: PASS
✓ Expected 7 agent_teams subtests, got 7: PASS
✓ No agent_teams in skip mode: PASS
```

### Settings.json Verification
```
✓ Regular subtest has NO env var: PASS
✓ Agent teams subtest has env var = "1": PASS
```

## Pre-commit Hook Issues

### Issue 1: Line Length

**File**: `scripts/run_e2e_experiment.py:298`

**Original**:
```python
help="Skip agent teams sub-tests (default: False, runs all sub-tests including agent teams)",
```

**Fixed** (101 chars → 91 chars):
```python
help="Skip agent teams sub-tests (default: False, runs all including agent teams)",
```

## Key Insights

### Insight 1: Discovery-Time vs Runtime Filtering

**Decision**: Filter at discovery time in `_discover_subtests()`

**Rationale**:
- Cleaner architecture
- Consistent result paths
- Easier to debug (logs show what was discovered)
- No wasted config loading

### Insight 2: Numbering Convention

**Pattern**: Sequential numbering after baseline tests

**Benefits**:
- 01-07: Baseline hierarchy tests
- 08-14: Agent teams variants
- Clear 1:1 mapping (01↔08, 02↔09, etc.)
- Easy to identify in results directories

### Insight 3: Environment Variables in settings.json

**Discovery**: settings.json supports `env` section for environment variables

**Application**: Enables feature flags without modifying agent code

**Format**:
```json
{
  "alwaysThinkingEnabled": false,
  "env": {
    "VARIABLE_NAME": "value"
  }
}
```

## Extensibility

This pattern can be extended to other experimental features:

**Example 1: Extended Thinking Variants**
```yaml
# 15-chief-architect-ultrathink.yaml
name: chief-architect-ultrathink
agent_teams: false
ultra_think: true  # New flag
```

**Example 2: Different Model Variants**
```yaml
# 22-chief-architect-opus.yaml
name: chief-architect-opus
agent_teams: false
model_override: "claude-opus-4-5-20251101"
```

**Required Changes**:
1. Add boolean field to `SubTestConfig`
2. Parse from YAML in `_discover_subtests()`
3. Apply in `_create_settings_json()` or workspace setup
4. Add CLI flag for filtering (optional)
5. Create variant YAML files

## Documentation Updates

### CLAUDE.md

**Before**:
```markdown
| T4 | Hierarchy | 7 | Nested orchestration with orchestrator agents |
```

**After**:
```markdown
| T4 | Hierarchy | 14 | Nested orchestration with orchestrator agents (7 hierarchy + 7 agent teams) |
```

### tiers.yaml

**Before**:
```yaml
# - T4: Hierarchy - 7 sub-tests for orchestrator ablation
```

**After**:
```yaml
# - T4: Hierarchy - 14 sub-tests for orchestrator ablation (7 hierarchy + 7 agent teams)
```

Total count updated from ~114 to ~121 sub-tests.

## Commit Message Structure

```
feat(t4): add agent teams sub-tests to T4 hierarchy tier

Add 7 new T4 sub-tests (08-14) to evaluate Claude Code's experimental
"Agent Teams" feature alongside existing hierarchy tests (01-07).

Changes:
- Add agent_teams field to SubTestConfig dataclass
- Parse agent_teams from YAML configs in tier_manager
- Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS env var in settings.json
- Create 7 new YAML files for agent teams variants
- Add --skip-agent-teams CLI option to disable these tests
- Update documentation to reflect 14 total T4 sub-tests

Verification:
- All 34 unit tests pass
- Subtest discovery correctly finds 14 tests (7 regular + 7 teams)
- settings.json correctly sets env var for agent teams tests
- --skip-agent-teams correctly filters to 7 regular tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## PR Checklist

- [x] Create feature branch
- [x] Modify data models
- [x] Update tier_manager discovery and settings
- [x] Create variant YAML files
- [x] Add CLI option
- [x] Update documentation
- [x] Run unit tests
- [x] Write verification scripts
- [x] Fix pre-commit issues (line length)
- [x] Create commit
- [x] Push branch
- [x] Create PR with detailed description
- [x] Enable auto-merge

## Time Breakdown

- Planning and design: 10 minutes
- Data model changes: 5 minutes
- Tier manager updates: 10 minutes
- YAML file creation: 5 minutes
- CLI integration: 10 minutes
- Documentation updates: 5 minutes
- Verification scripts: 15 minutes
- Testing and debugging: 10 minutes
- PR creation: 5 minutes

**Total**: ~75 minutes

## Future Improvements

1. **Auto-generate variant YAMLs**: Script to create variants from baseline tests
2. **Comparison reporting**: Automatic baseline vs variant comparison in results
3. **Feature flag registry**: Central registry of all experimental features
4. **A/B test analysis**: Statistical significance testing for variant performance
