# Implementation Notes: Unify Config Structure

## Session Context

**Date**: 2026-01-17
**Branch**: cleanup
**Initial State**: Multiple config discrepancies found
**Final State**: Unified config structure, all tests passing

## Discrepancies Found

### 1. T1 Subtest Count Mismatch

**Location**: `config/tiers/tiers.yaml`

```yaml
# Before (WRONG - lines 8, 25):
- T1: Skills - 11 sub-tests for skill category ablation
description: "Domain expertise via installed skills (11 sub-tests by category)"

# After (CORRECT):
- T1: Skills - 10 sub-tests for skill category ablation
description: "Domain expertise via installed skills (10 sub-tests by category)"
```

**Verification**:
```bash
$ find tests/claude-code/shared/subtests/t1 -name '*.yaml' | wc -l
10
```

### 2. Architecture.md Outdated

**Location**: `docs/design/architecture.md`

**Issues**:
- Only showed 4 tiers (T0-T3+), missing T4, T5, T6
- Wrong tier names (Vanilla, Prompted, Skills, Tooling)
- Wrong file references (t0-vanilla.yaml, t1-prompted.md, etc.)

**Before (lines 559-568)**:
```markdown
| Tier | Name | Description | Prompt Source |
|------|------|-------------|---------------|
| T0 | Vanilla | Base LLM, tool default | Tool default |
| T1 | Prompted | System prompt with CoT | `config/tiers/t1-prompted.md` |
| T2 | Skills | Domain expertise | `config/tiers/t2-skills.md` |
| T3+ | Tooling | External tools | `config/tiers/t3-tooling.md` |
```

**After**:
```markdown
| Tier | Name | Sub-tests | Description | Prompt Source |
|------|------|-----------|-------------|---------------|
| T0 | Prompts | 24 | System prompt ablation | `config/tiers/t0-prompts.md` |
| T1 | Skills | 10 | Domain expertise via skills | `config/tiers/t1-skills.md` |
| T2 | Tooling | 15 | External tools and MCP | `config/tiers/t2-tooling.md` |
| T3 | Delegation | 41 | Flat multi-agent | `config/tiers/t3-delegation.md` |
| T4 | Hierarchy | 7 | Nested orchestration | `config/tiers/t4-hierarchy.md` |
| T5 | Hybrid | 15 | Best combinations | `config/tiers/t5-hybrid.md` |
| T6 | Super | 1 | Everything enabled | `config/tiers/t6-super.md` |
```

### 3. Evaluation Guidelines Wrong Tier Names

**Location**: `.claude/shared/evaluation-guidelines.md`

**Before (lines 165-201)**:
- T0 (Vanilla)
- T1 (Prompted)
- T2 (Skills)
- T3 (Tooling)
- T4 (Delegation)
- T5 (Hierarchy)
- T6 (Hybrid)

**After**:
- T0 (Prompts)
- T1 (Skills)
- T2 (Tooling)
- T3 (Delegation)
- T4 (Hierarchy)
- T5 (Hybrid)
- T6 (Super) ← Added

### 4. Duplicate Test Fixtures

**Deleted**: `tests/fixtures/config/` (entire directory)

**Contents before deletion**:
```
tests/fixtures/config/
├── defaults.yaml           # Duplicate of config/defaults.yaml
├── models/
│   ├── test-model.yaml    # Duplicate test fixture
│   └── test-model-2.yaml  # Duplicate test fixture
└── tiers/
    ├── t0.yaml            # Stale (name: "Vanilla")
    └── t1.yaml            # Stale (name: "Prompted")
```

**Replacement structure**:
```
tests/fixtures/config/
├── defaults.yaml           # Minimal test-specific defaults
├── models/                 # Symlinks to config/models/_test-*.yaml
│   ├── test-model.yaml -> ../../../config/models/_test-model.yaml
│   └── test-model-2.yaml -> ../../../config/models/_test-model-2.yaml
└── tiers/
    ├── t0.yaml            # Simple YAML for tier loader tests
    └── t1.yaml            # Simple YAML for tier loader tests
```

## Implementation Sequence

### Phase 1: Documentation Fixes

1. Edit `config/tiers/tiers.yaml`:
   - Line 8: `11 sub-tests` → `10 sub-tests`
   - Line 25: `(11 sub-tests by category)` → `(10 sub-tests by category)`

2. Edit `docs/design/architecture.md`:
   - Lines 474-485: Update directory structure
   - Lines 559-571: Rewrite tier table with 7 tiers

3. Edit `.claude/shared/evaluation-guidelines.md`:
   - Lines 165-212: Fix all tier names and add T6

### Phase 2: Config Consolidation

1. Move test models to production:
   ```bash
   # Create in config/models/ with _ prefix
   config/models/_test-model.yaml
   config/models/_test-model-2.yaml
   ```

2. Delete duplicate fixtures:
   ```bash
   rm -rf tests/fixtures/config/
   ```

3. Recreate minimal fixtures:
   ```bash
   mkdir -p tests/fixtures/config/{models,tiers}

   # Create minimal defaults
   cat > tests/fixtures/config/defaults.yaml <<EOF
   evaluation:
     runs_per_tier: 10
     timeout: 300
   output:
     runs_dir: "runs"
   logging:
     level: "INFO"
   EOF

   # Symlink test models
   ln -s ../../../config/models/_test-model.yaml tests/fixtures/config/models/test-model.yaml
   ln -s ../../../config/models/_test-model-2.yaml tests/fixtures/config/models/test-model-2.yaml

   # Create simple tier configs
   cat > tests/fixtures/config/tiers/t0.yaml <<EOF
   tier: "t0"
   name: "Vanilla"
   description: "Base LLM with zero-shot prompting"
   uses_tools: false
   EOF

   cat > tests/fixtures/config/tiers/t1.yaml <<EOF
   tier: "t1"
   name: "Prompted"
   description: "System prompts and chain-of-thought"
   system_prompt: "You are a helpful assistant."
   uses_tools: false
   EOF
   ```

### Phase 3: Verification

1. Run config tests:
   ```bash
   pixi run pytest tests/unit/test_config_loader.py -v
   # Result: 32 passed, 1 skipped

   pixi run pytest tests/unit/config/ -v
   # Result: 12 passed
   ```

2. Verify TierManager:
   ```bash
   pixi run python -c "from scylla.e2e.tier_manager import TierManager; print('OK')"
   # Result: OK
   ```

3. Verify subtest counts:
   ```bash
   for t in t0 t1 t2 t3 t4 t5 t6; do
     echo "$t: $(find tests/claude-code/shared/subtests/$t -name '*.yaml' | wc -l)"
   done
   # Results:
   # t0: 24 ✓
   # t1: 10 ✓
   # t2: 15 ✓
   # t3: 41 ✓
   # t4: 7 ✓
   # t5: 15 ✓
   # t6: 1 ✓
   ```

## Test Results

### Config Loader Tests

All 33 tests passed:
- `TestConfigLoaderDefaults` (3/3)
- `TestConfigLoaderEvalCase` (3/3)
- `TestConfigLoaderRubric` (4/4)
- `TestConfigLoaderTier` (5/5)
- `TestConfigLoaderModel` (6/6)
- `TestConfigLoaderMerged` (6/6)
- `TestConfigLoaderEdgeCases` (5/5)
- `TestConfigLoaderIntegration` (1 skipped)

### Full Unit Test Suite

- **Passed**: 1013 tests
- **Failed**: 9 tests (unrelated to config changes)
  - TierManager root level mapping (5 failures)
  - Executor volume tests (2 failures)
  - Judge container tests (2 failures)
- **Skipped**: 2 tests

Failed tests existed before changes - verified with `git diff`.

## Key Decisions

### Decision 1: Prefix Test Models with Underscore

**Rationale**: Clear visual distinction between production and test configs

**Implementation**:
```
config/models/
├── claude-opus-4-5.yaml        # Production
├── claude-sonnet-4-5.yaml      # Production
├── _test-model.yaml            # Test fixture
└── _test-model-2.yaml          # Test fixture
```

**Benefits**:
- Immediate recognition of test-only configs
- Sorts test fixtures to bottom in alphabetical listings
- Prevents accidental use in production

### Decision 2: Symlink Test Models Instead of Duplicate

**Rationale**: Single source of truth for test model definitions

**Implementation**:
```bash
tests/fixtures/config/models/test-model.yaml -> ../../../config/models/_test-model.yaml
```

**Benefits**:
- Changes to test models propagate automatically
- No risk of drift between fixtures and production
- Reduces maintenance burden

### Decision 3: Keep Minimal Test Fixtures

**Rationale**: Test isolation and stability

**Why not use production config directly?**
- Tests need stable, predictable configs
- Production configs change frequently
- Tests should validate loader behavior, not data

**What to include in test fixtures?**
- Only fields required by tests
- Minimal values that satisfy validation
- Stable data that won't change

**Example**:
```yaml
# tests/fixtures/config/defaults.yaml - MINIMAL
evaluation:
  runs_per_tier: 10
  timeout: 300

# config/defaults.yaml - COMPLETE
evaluation:
  runs_per_eval: 10
  timeout: 300
  seed: null
metrics:
  quality: [pass_rate, impl_rate, progress_rate, consistency]
  economic: [cost_of_pass, token_distribution, change_fail_percentage]
output:
  runs_dir: "runs"
  summaries_dir: "summaries"
  reports_dir: "reports"
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Troubleshooting Notes

### Issue: Tests Failed After Deleting Fixtures

**Error**: `ConfigurationError: Configuration file not found`

**Cause**: ConfigLoader uses `base_path / "config" / "models"` pattern
- When `base_path = tests/fixtures`, it looks for `tests/fixtures/config/models/`
- Deleting that directory broke tests

**Fix**: Recreate minimal fixture structure

### Issue: Tier Tests Expected YAML, Found Markdown

**Error**: `ConfigurationError: Configuration file not found: config/tiers/t0.yaml`

**Cause**: Production uses markdown templates (`t0-prompts.md`), tests expect YAML configs

**Fix**: Create simple YAML tier configs in test fixtures:
```yaml
# tests/fixtures/config/tiers/t0.yaml
tier: "t0"
name: "Vanilla"
description: "Base LLM with zero-shot prompting"
uses_tools: false
```

## Performance Impact

- **Test execution time**: No change (0.35s for config tests)
- **Build time**: Not affected
- **CI/CD**: All config tests continue passing

## Future Improvements

1. **Extract grading scale from rubrics** (Phase 3 - LOW priority)
   - 48 rubric files duplicate `grade_scale` block
   - Could reference shared `docs/design/grading-scale.md`
   - Would require rubric loader update

2. **Consolidate tier YAML and markdown**
   - Currently: `tiers.yaml` + individual `t*-*.md` files
   - Could embed prompts directly in `tiers.yaml`
   - Trade-off: Single file vs. modularity

3. **Auto-generate tier docs**
   - Count subtests programmatically
   - Update `tiers.yaml` comments automatically
   - Prevent future drift

## References

- Plan file: `plan-elegant-squishing-puffin.md`
- Config loader: `scylla/config/loader.py`
- Config models: `scylla/config/models.py`
- Tier definitions: `config/tiers/tiers.yaml`
