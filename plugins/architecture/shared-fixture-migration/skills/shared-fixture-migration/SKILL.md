# Skill: shared-fixture-migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-03 |
| **Category** | architecture |
| **Objective** | Migrate duplicated test fixture configs to a centralized shared location with runtime loading |
| **Outcome** | SUCCESS - Reduced fixture size from 47MB to 1.4MB (97% reduction), eliminated 5355 duplicate files |

## When to Use

Use this skill when:

- Test fixtures contain config files duplicated across many test directories
- The same config content is repeated for each test but is actually test-independent
- Running `find tests -name "*.yaml" | xargs md5sum | sort | uniq -c` shows high duplication (10+)
- You want a single source of truth for shared configurations
- Test directories follow a pattern like `test-XXX/tierY/subtestZ/config.yaml`

Trigger conditions:

- `find | md5sum | uniq -c | sort -rn` shows files duplicated 40+ times
- Configs define tier/subtest properties that are identical across all tests
- A shared resources directory exists or can be created

## Verified Workflow

### Step 1: Quantify the Duplication

```bash
# Find most duplicated files by content hash
find tests/fixtures/tests -type f -name "config.yaml" | xargs md5sum | awk '{print $1}' | sort | uniq -c | sort -rn | head -30

# Count total duplicates
find tests/fixtures/tests -type f -name "config.yaml" | xargs md5sum | awk '{print $1}' | sort | uniq -c | awk '$1 > 1 {sum += $1; count++} END {print "Groups:", count, "Files:", sum}'
```

**Session finding**: 5361 config.yaml files, 5355 duplicates across 119 unique patterns.

### Step 2: Create Shared Directory Structure

```bash
# Create tier subdirectories in shared location
mkdir -p tests/claude-code/shared/subtests/t{0,1,2,3,4,5,6}
```

### Step 3: Copy Canonical Configs from One Test

```bash
# Use test-001 as the canonical source
for tier in t0 t1 t2 t3 t4 t5 t6; do
  for dir in tests/fixtures/tests/test-001/$tier/*/; do
    subtest=$(basename "$dir")
    if [ -f "$dir/config.yaml" ]; then
      cp "$dir/config.yaml" "tests/claude-code/shared/subtests/$tier/$subtest.yaml"
    fi
  done
done
```

**Key insight**: Rename `NN-subtest/config.yaml` to `NN-subtest.yaml` since subtests don't need subdirectories - they're just config files.

### Step 4: Modify the Config Loader

Update the loader (e.g., `tier_manager.py`) to:

1. **First** load from shared directory (`shared/subtests/tN/*.yaml`)
2. **Then** overlay any test-specific overrides (rare)

```python
def _discover_subtests(self, tier_id: TierID, tier_dir: Path) -> list[SubTestConfig]:
    # Load from shared first
    shared_subtests_dir = self._get_shared_dir() / "subtests" / tier_id.value.lower()
    subtests = self._load_shared_subtests(tier_id, shared_subtests_dir)

    # Overlay test-specific (if any)
    subtest_by_id = {s.id: s for s in subtests}
    if tier_dir.exists():
        self._overlay_test_specific(subtest_by_id, tier_dir, tier_id)

    return list(subtest_by_id.values())
```

### Step 5: Create Migration Script

Create a script that:

- Verifies shared configs exist
- Deletes per-test tier directories
- Supports `--dry-run` mode

```bash
# Dry-run first
python scripts/migrate_subtests_to_shared.py tests/fixtures/tests/ --dry-run

# Execute migration
python scripts/migrate_subtests_to_shared.py tests/fixtures/tests/
```

### Step 6: Validate the Migration

```bash
# Run validation script
python scripts/validate_tier_manager.py

# Or quick validation
python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'src')
from scylla.e2e.tier_manager import TierManager
from scylla.e2e.models import TierID

manager = TierManager(Path('tests/fixtures/tests/test-001'))
for tier_id in TierID:
    config = manager.load_tier_config(tier_id)
    print(f'{tier_id.value}: {len(config.subtests)} subtests')
"
```

## Failed Attempts

### 1. Assuming Wrong Source of Duplication

**What happened**: Initial assumption (from prior session) was that agent markdown files like `implementation-review-specialist.md` were duplicated 66 times.

**Actual situation**: The duplication was config.yaml files in tier directories (5355 copies), not agent files.

**Lesson**: Always run hash analysis first (`find | md5sum | uniq -c`) to identify the actual source of duplication before planning a solution.

### 2. Initial T0 Migration Left Other Tiers Untouched

**What happened**: Prior commit (d7dfeb9) migrated T0 CLAUDE.md files to block-based composition but left T1-T6 config.yaml files duplicated.

**Actual situation**: The config.yaml duplication in T1-T6 was a separate, larger problem (5355 files vs 1034 CLAUDE.md files).

**Lesson**: When tackling duplication, check ALL file types, not just the one initially identified.

### 3. Per-Test Tier Directories Were Unnecessary

**What happened**: Initially thought each test needed its own tier directory structure.

**Actual situation**: Tier/subtest configurations are test-independent - they define what components to load (skills, agents, blocks), not test-specific settings.

**Lesson**: Identify what's truly test-specific vs. shared. Only test-specific data (prompts, expected results, rubrics) needs to be per-test.

## Results & Parameters

### Before/After Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Fixture size | 47MB | 1.4MB | 97% reduction |
| config.yaml files | 5,361 | 160 | 97% reduction |
| Tier directories per test | 7 | 0 | 100% |
| Subtest directories | 5,361 | 0 | 100% (now YAML files) |
| Lines of code deleted | - | 120,735 | - |

### Final Directory Structure

```text
tests/
├── claude-code/shared/
│   └── subtests/             # Centralized configs
│       ├── t0/
│       │   ├── 00-empty.yaml
│       │   ├── 01-vanilla.yaml
│       │   └── ... (24 files)
│       ├── t1/
│       │   └── ... (10 files)
│       └── t{2-6}/          # Total: 113 shared configs
└── fixtures/tests/
    ├── test-001/
    │   ├── test.yaml         # Test definition
    │   ├── config.yaml       # Test-specific overrides (timeout, etc.)
    │   ├── prompt.md         # Test prompt
    │   └── expected/         # Validation rubrics
    └── test-{002-047}/       # Same minimal structure
```

### Config File Format

```yaml
# Shared subtest config (e.g., t1/04-github.yaml)
name: GitHub Skills
description: 10 skills from the github category
extends_previous: true
resources:
  skills:
    categories:
      - github
```

## Related Files

- `scripts/migrate_subtests_to_shared.py` - Migration script
- `scripts/validate_tier_manager.py` - Validation script
- `src/scylla/e2e/tier_manager.py` - Modified loader
- `tests/claude-code/shared/subtests/` - Centralized configs
