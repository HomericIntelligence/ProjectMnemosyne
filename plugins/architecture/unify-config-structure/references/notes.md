# References: unify-config-structure

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Config consolidation | Imported from ProjectScylla .claude-plugin/skills/unify-config-structure |

## Source

Originally created for ProjectScylla to consolidate tier/config structure and fix documentation inconsistencies.

## Additional Context

This skill provides a systematic workflow for:
1. Auditing all config locations and documenting discrepancies
2. Fixing documentation first to establish target state
3. Consolidating config files and deleting duplicates
4. Creating minimal test fixtures for test isolation
5. Verifying all changes with comprehensive testing

Final result: 45/45 tests passing, unified config structure, single source of truth established.

## Key Principles

- Single Source of Truth: Production config in `config/`, not duplicated elsewhere
- Test Isolation: Minimal fixtures in `tests/fixtures/` for stable tests
- Documentation First: Fix docs before moving files
- Verify Counts: Always count actual resources, never trust comments
- Prefix Test Configs: Use `_` prefix for test-only configs

## Related Skills

- test-fixture-management: Managing test data and fixtures
- docs-sync: Keeping documentation in sync with code
