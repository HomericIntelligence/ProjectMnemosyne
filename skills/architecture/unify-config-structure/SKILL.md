# Skill: Unify Config Structure

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-17 |
| **Objective** | Consolidate tier/config structure to establish single source of truth and fix documentation inconsistencies |
| **Outcome** | ✅ Success - Unified config structure, fixed all docs, 45/45 tests passing |
| **Category** | Architecture |
| **Tags** | config-management, documentation, test-fixtures, single-source-of-truth |

## When to Use This Skill

Use this skill when you encounter:

- **Duplicate config files** across multiple directories (e.g., `config/` and `tests/fixtures/config/`)
- **Documentation drift** where multiple docs describe different tier counts, names, or structures
- **Inconsistent naming** between config files, code references, and documentation
- **Test fixture bloat** where test fixtures fully duplicate production configs
- **Unclear authority** about which config file is the "source of truth"

**Trigger phrases:**
- "Config files are duplicated in multiple places"
- "Documentation doesn't match actual tier structure"
- "Tests break when I update production config"
- "Which config file should I edit?"

## Verified Workflow

### Phase 1: Audit Current State

1. **Identify all config locations**:
   ```bash
   find . -name "*.yaml" -path "*/config/*" -o -name "tiers.yaml"
   find . -name "*.md" -path "*/docs/*" | xargs grep -l "tier\|Tier"
   ```

2. **Count actual resources** (e.g., subtests):
   ```bash
   for t in t0 t1 t2 t3 t4 t5 t6; do
     echo "$t: $(find tests/claude-code/shared/subtests/$t -name '*.yaml' | wc -l)"
   done
   ```

3. **Document discrepancies** in a plan file:
   - Config file mismatches (count differences, naming inconsistencies)
   - Documentation drift (wrong tier names, missing tiers, outdated file references)
   - Duplicate fixtures vs production configs

### Phase 2: Fix Documentation First

**Critical**: Always fix documentation before moving files - establishes target state.

1. **Update master config** (e.g., `config/tiers/tiers.yaml`):
   - Fix resource counts to match reality
   - Ensure descriptions are accurate
   - Document all tiers/resources

2. **Update architecture docs** (e.g., `docs/design/architecture.md`):
   - Rewrite tier tables with correct counts
   - Fix file references in directory structure diagrams
   - Update tier range (e.g., "T0-T3+" → "T0-T6")

3. **Update usage guides** (e.g., `.claude/shared/evaluation-guidelines.md`):
   - Fix tier names throughout
   - Add missing tiers
   - Update descriptions to match master config

### Phase 3: Consolidate Config Files

1. **Move test fixtures to production location**:
   ```bash
   # Use _ prefix to mark test-only configs
   mv tests/fixtures/config/models/test-model.yaml config/models/_test-model.yaml
   ```

2. **Delete duplicate directories**:
   ```bash
   rm -rf tests/fixtures/config/
   ```

3. **Create minimal test fixtures**:
   - Keep test isolation by creating minimal fixtures
   - Use symlinks for shared test resources
   - Only include fields needed for specific tests

   Example minimal fixture:
   ```yaml
   # tests/fixtures/config/defaults.yaml
   evaluation:
     runs_per_tier: 10
     timeout: 300

   output:
     runs_dir: "runs"

   logging:
     level: "INFO"
   ```

### Phase 4: Verify and Test

1. **Run config-specific tests**:
   ```bash
   pixi run pytest tests/unit/test_config_loader.py tests/unit/config/ -v
   ```

2. **Verify production code loads**:
   ```bash
   pixi run python -c "from scylla.e2e.tier_manager import TierManager; print('OK')"
   ```

3. **Re-verify resource counts**:
   ```bash
   for t in t0 t1 t2 t3 t4 t5 t6; do
     echo "$t: $(find tests/claude-code/shared/subtests/$t -name '*.yaml' | wc -l)"
   done
   ```

## Failed Attempts

### ❌ Attempt 1: Delete fixtures entirely without replacement

**What was tried:**
- Deleted `tests/fixtures/config/` directory completely
- Expected tests to use production `config/` directly

**Why it failed:**
- ConfigLoader uses `base_path / "config" / "models"` pattern
- Tests need isolated fixtures at `tests/fixtures/` base path
- Breaking test isolation principle

**Lesson learned:**
- Test fixtures serve a different purpose than production configs
- Tests need minimal, isolated, stable configs
- Production configs can change without breaking tests

### ❌ Attempt 2: Use production tier markdown files for tests

**What was tried:**
- Tried to make tests load `t0-prompts.md`, `t1-skills.md` directly
- Expected tier loader to parse markdown for test configs

**Why it failed:**
- Tests expect YAML tier configs (e.g., `t0.yaml`, `t1.yaml`)
- Production uses markdown prompt templates, not YAML configs
- ConfigLoader tier loading expects specific YAML structure

**Lesson learned:**
- Test fixtures can have different structure than production
- Use simple YAML for tests, complex templates for production
- Tests validate the loader, not the production data format

## Results & Parameters

### Final Structure

```
config/                              # AUTHORITATIVE (production)
├── defaults.yaml                    # Global defaults
├── models/                          # All model configs
│   ├── claude-*.yaml               # Production models
│   └── _test-*.yaml                # Test fixtures (prefixed with _)
└── tiers/
    ├── tiers.yaml                   # Master tier definitions
    └── t0-prompts.md ... t6-super.md  # Tier prompt templates

tests/fixtures/config/               # Test-specific minimal fixtures
├── defaults.yaml                    # Minimal test defaults
├── models/                          # Symlinks to _test-* models
└── tiers/                           # Simple YAML for tier tests
    ├── t0.yaml                      # Minimal tier config
    └── t1.yaml                      # Minimal tier config
```

### Tier Configuration

| Tier | Name | Sub-tests | Description |
|------|------|-----------|-------------|
| T0 | Prompts | 24 | System prompt ablation |
| T1 | Skills | 10 | Domain expertise via skills |
| T2 | Tooling | 15 | External tools and MCP |
| T3 | Delegation | 41 | Flat multi-agent |
| T4 | Hierarchy | 7 | Nested orchestration |
| T5 | Hybrid | 15 | Best combinations |
| T6 | Super | 1 | Everything enabled |

**Total**: 113 subtests across 7 tiers

### Test Results

- Config loader tests: 33/33 passed ✅
- All config tests: 45/45 passed ✅
- TierManager loads: ✅
- Subtest counts verified: ✅

### Files Modified

| File | Change Type | Lines Modified |
|------|-------------|----------------|
| `config/tiers/tiers.yaml` | Fix counts | 2 (lines 8, 25) |
| `docs/design/architecture.md` | Rewrite tier section | ~20 (lines 474-485, 559-571) |
| `.claude/shared/evaluation-guidelines.md` | Fix tier names | ~50 (lines 165-212) |
| `config/models/_test-model.yaml` | Created | New file |
| `config/models/_test-model-2.yaml` | Created | New file |
| `tests/fixtures/config/defaults.yaml` | Created | New file |
| `tests/fixtures/config/tiers/t0.yaml` | Created | New file |
| `tests/fixtures/config/tiers/t1.yaml` | Created | New file |

### Commands Used

```bash
# Verify subtest counts
for t in t0 t1 t2 t3 t4 t5 t6; do
  echo "$t: $(find tests/claude-code/shared/subtests/$t -name '*.yaml' | wc -l)"
done

# Delete duplicate fixtures
rm -rf tests/fixtures/config/

# Create fixture structure
mkdir -p tests/fixtures/config/{models,tiers}

# Run tests
pixi run pytest tests/unit/test_config_loader.py -v
pixi run pytest tests/unit/config/ -v

# Verify production code
pixi run python -c "from scylla.e2e.tier_manager import TierManager; print('OK')"
```

## Key Principles

1. **Single Source of Truth**: Production config in `config/`, not duplicated elsewhere
2. **Test Isolation**: Minimal fixtures in `tests/fixtures/` for stable, isolated tests
3. **Documentation First**: Fix docs before moving files to establish target state
4. **Verify Counts**: Always count actual resources, never trust comments
5. **Prefix Test Configs**: Use `_` prefix for test-only production configs (e.g., `_test-model.yaml`)
6. **Symlinks for Sharing**: When tests need production test fixtures, symlink them

## Lessons Learned

### What Worked

- **Audit first, then fix**: Counting actual subtests revealed the T1 mismatch
- **Documentation establishes truth**: Fixing docs first created clear target state
- **Minimal test fixtures**: Tests don't need full production config complexity
- **Symlinks reduce duplication**: Test models in production, symlinked to fixtures
- **Prefixing convention**: `_test-*.yaml` clearly marks test-only configs

### What to Avoid

- **Don't delete fixtures without replacement**: Tests need isolation
- **Don't assume test fixtures match production**: Different purposes, different structures
- **Don't skip verification**: Always re-count and re-test after changes
- **Don't batch fixes**: Fix docs → consolidate configs → verify, sequentially

## Related Skills

- `testing/test-fixture-management` - Managing test data and fixtures
- `documentation/docs-sync` - Keeping documentation in sync with code
- `architecture/config-hierarchy` - Designing config priority systems

## References

See `references/notes.md` for detailed implementation notes and conversation transcript excerpts.
