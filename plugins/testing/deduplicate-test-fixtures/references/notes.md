# Session Notes: deduplicate-test-fixtures

## Date: 2026-01-02

## Problem Statement

Test fixtures in ProjectScylla contained massive CLAUDE.md duplication:
- 1,034 CLAUDE.md files duplicated across T0 tier directories
- Each of 47 tests had ~22 copies of similar CLAUDE.md content
- Total fixture size: 56MB

## Key Findings

1. **Actual duplication was different than reported**:
   - User mentioned `implementation-review-specialist.md` duplicated 66 times
   - Analysis revealed only 1 copy exists
   - Real duplication was CLAUDE.md files in T0 tier directories

2. **Existing infrastructure existed but wasn't used**:
   - `tier_manager.py` already had `_compose_claude_md()` method
   - Prior commit added infrastructure but never ran migration
   - T1-T6 were already migrated, only T0 remained

3. **Block-based composition pattern**:
   - 18 shared blocks (B01-B18) in `tests/claude-code/shared/blocks/`
   - Directory naming pattern maps to block composition

## Solution Summary

Used runtime block-based composition:
1. Map directory names to block compositions
2. Update config.yaml with `resources.claude_md.blocks` specification
3. Delete duplicated CLAUDE.md files
4. tier_manager composes at runtime from shared blocks

## Results

| Metric | Before | After |
|--------|--------|-------|
| CLAUDE.md files in T0 | 1034 | 0 |
| Fixture size | 56MB | 47MB |
| Lines removed | 0 | 239,888 |
| Config files updated | 0 | 1128 |

## Key Files Modified

- `scripts/migrate_t0_to_blocks.py` - Migration script
- `src/scylla/e2e/tier_manager.py` - Runtime composition (`_compose_claude_md()`)
- `tests/claude-code/shared/blocks/` - Shared block files (B01-B18)

## Key Learnings

1. **Always verify actual duplication source** - Run hash analysis before planning
2. **Check for existing infrastructure** - Prior work may have added mechanism but not executed
3. **Set clear scope boundaries** - Focus on largest source, defer smaller sources
