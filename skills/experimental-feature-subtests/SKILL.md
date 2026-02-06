# Skill: Experimental Feature Sub-tests

| Metadata | Value |
|----------|-------|
| **Date** | 2026-02-05 |
| **Category** | evaluation |
| **Objective** | Add A/B testing for experimental features in evaluation tiers |
| **Outcome** | ✅ Successfully added 7 agent teams sub-tests to T4 tier with CLI filtering |
| **PR** | #350 |

## Overview

This skill documents how to add experimental feature variants as parallel sub-tests within evaluation tiers. This pattern enables A/B testing of experimental features against standard implementations without disrupting existing baselines.

**Use Case**: Claude Code's experimental "Agent Teams" feature needed evaluation alongside standard hierarchy tests.

**Solution**: Add parallel sub-tests (08-14) that mirror existing tests (01-07) but enable the experimental feature via environment variable.

## When to Use This Skill

Use this pattern when:
- **Testing experimental features** that need comparison to baseline
- **A/B testing** different configurations in the same tier
- **Feature flags** controlled via environment variables
- **Parallel evaluation** of multiple variants without branching tiers

Don't use when:
- Feature is stable enough to replace baseline (use direct modification)
- Feature requires completely different task setup (use new tier)
- Variants are mutually exclusive at runtime (use separate runs)

## Verified Workflow

### 1. Add Feature Flag Field to Data Models

**File**: `scylla/e2e/models.py`

Add boolean field to `SubTestConfig`:

```python
@dataclass
class SubTestConfig:
    # ... existing fields ...
    agent_teams: bool = False  # Enable experimental agent teams

    def to_dict(self) -> dict[str, Any]:
        return {
            # ... existing fields ...
            "agent_teams": self.agent_teams,
        }
```

Also add to `ExperimentConfig` for CLI control:

```python
@dataclass
class ExperimentConfig:
    # ... existing fields ...
    skip_agent_teams: bool = False  # Skip agent teams sub-tests
```

### 2. Parse Flag from YAML Configs

**File**: `scylla/e2e/tier_manager.py`

In `_discover_subtests()` method:

```python
# Parse agent_teams flag
agent_teams = config_data.get("agent_teams", False)

# Skip if filtering is enabled
if skip_agent_teams and agent_teams:
    continue

subtests.append(
    SubTestConfig(
        # ... existing fields ...
        agent_teams=agent_teams,
    )
)
```

Add filtering parameter to `load_tier_config()`:

```python
def load_tier_config(self, tier_id: TierID, skip_agent_teams: bool = False) -> TierConfig:
    subtests = self._discover_subtests(tier_id, tier_dir, skip_agent_teams)
```

### 3. Set Environment Variable in settings.json

**File**: `scylla/e2e/tier_manager.py`

In `_create_settings_json()` method (after MCP servers section):

```python
# Add experimental agent teams environment variable
if subtest.agent_teams:
    if "env" not in settings:
        settings["env"] = {}
    settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
```

### 4. Create Variant Sub-test Configurations

**Location**: `tests/claude-code/shared/subtests/t4/`

Create YAML files mirroring existing tests with `agent_teams: true`:

```yaml
# 08-chief-architect-teams.yaml
name: chief-architect-teams
description: 'L0 orchestrator with agent teams: chief-architect'
extends_previous: true
agent_teams: true  # Enable experimental feature
resources:
  agents:
    levels:
    - 0
```

**Pattern**: Number variants sequentially after existing tests (01-07 → 08-14).

### 5. Add CLI Filtering Option

**File**: `scripts/run_e2e_experiment.py`

Add argument:

```python
parser.add_argument(
    "--skip-agent-teams",
    action="store_true",
    help="Skip agent teams sub-tests (default: False, runs all including agent teams)",
)
```

Pass through to config:

```python
ExperimentConfig(
    # ... existing fields ...
    skip_agent_teams=args.skip_agent_teams,
)
```

Pass through to runner:

```python
# In runner.py
tier_config = self.tier_manager.load_tier_config(tier_id, self.config.skip_agent_teams)
```

### 6. Update Documentation

**Files**: `CLAUDE.md`, `config/tiers/tiers.yaml`

Update tier description to reflect new total count:

```yaml
T4:
  description: "Nested orchestration with orchestrator agents (14 sub-tests: 7 hierarchy + 7 agent teams)"
```

## Failed Attempts

### ❌ Attempt 1: Runtime Filtering Instead of Discovery-Time

**What we tried**: Initially considered filtering agent teams tests at runtime after loading all configs.

**Why it failed**:
- Would load unnecessary configs into memory
- Harder to track which tests were skipped in logs
- Results directory structure would be inconsistent

**What we learned**: Filter during discovery (`_discover_subtests`) for cleaner architecture and consistent result paths.

### ❌ Attempt 2: Using `--dry-run` Flag for Verification

**What we tried**: Used `--dry-run` flag to verify subtest discovery.

**Why it failed**: The flag doesn't exist in `run_e2e_experiment.py`.

**What we learned**: Write custom verification scripts instead of relying on non-existent CLI flags. Created two verification scripts:
- `verify_subtests.py` - Check subtest discovery
- `verify_settings.py` - Check settings.json generation

## Results & Parameters

### Subtest Discovery Verification

```bash
pixi run python verify_subtests.py
```

Output:
```
T4 Subtest Discovery Verification
============================================================
1. All subtests (agent_teams included):
   Total subtests: 14
   - 01-07: [regular hierarchy tests]
   - 08-14: [agent teams variants] [AGENT_TEAMS]

2. Subtests with --skip-agent-teams:
   Total subtests: 7
   - 01-07: [regular hierarchy tests only]

✓ Expected 14 total subtests, got 14: PASS
✓ Expected 7 non-teams subtests, got 7: PASS
✓ Expected 7 agent_teams subtests, got 7: PASS
✓ No agent_teams in skip mode: PASS
```

### Settings.json Verification

```bash
pixi run python verify_settings.py
```

Sample output for agent teams test:
```json
{
  "alwaysThinkingEnabled": false,
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Usage Examples

**Run all T4 tests including agent teams**:
```bash
python scripts/run_e2e_experiment.py --tiers T4 --runs 10
```

**Skip agent teams (baseline only)**:
```bash
python scripts/run_e2e_experiment.py --tiers T4 --runs 10 --skip-agent-teams
```

**Compare results**:
```bash
# Run baseline
python scripts/run_e2e_experiment.py --tiers T4 --runs 10 --skip-agent-teams

# Run with agent teams
python scripts/run_e2e_experiment.py --tiers T4 --runs 10

# Compare results in results/T4/{01-07} vs results/T4/{08-14}
```

## Key Design Patterns

### Pattern 1: Boolean Flag + YAML Config

**Structure**:
```
Data Model (agent_teams: bool)
    ↓
YAML Config (agent_teams: true/false)
    ↓
Discovery Filter (skip if skip_agent_teams)
    ↓
Settings.json (env var if enabled)
```

**Benefits**:
- Declarative configuration
- Easy to extend to other features
- Clear separation of concerns

### Pattern 2: Mirror Numbering for Variants

**Baseline**: 01-07 (standard tests)
**Variant**: 08-14 (experimental tests)

**Benefits**:
- Clear relationship between baseline and variant
- Sequential numbering preserves order
- Easy to identify variant tests in results

### Pattern 3: Environment Variable Feature Flags

**Location**: `.claude/settings.json`

```json
{
  "env": {
    "FEATURE_FLAG_NAME": "1"
  }
}
```

**Benefits**:
- Standard mechanism for feature flags
- Works with any tool reading settings.json
- Easy to verify in results

## Testing Checklist

- [ ] Unit tests pass (`pixi run pytest tests/unit/e2e/test_tier_manager.py`)
- [ ] Subtest discovery finds correct count (verify with custom script)
- [ ] settings.json has env var for experimental tests
- [ ] settings.json has NO env var for baseline tests
- [ ] CLI filtering works (`--skip-agent-teams`)
- [ ] Documentation updated (CLAUDE.md, tiers.yaml)
- [ ] Pre-commit hooks pass

## Related Skills

- `tier-ablation-testing` - Methodology for tier ablation studies
- `shared-fixture-migration` - Centralized fixture management
- `claude-code-settings-config` - Settings.json generation patterns

## References

- PR #350: feat(t4): add agent teams sub-tests to T4 hierarchy tier
- Issue: N/A (internal improvement)
- Related discussions: Agent Teams experimental feature evaluation
