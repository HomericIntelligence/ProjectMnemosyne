# Session Notes: delete-placeholder-docs

## Context

- **Date**: 2026-03-05
- **Issue**: HomericIntelligence/ProjectOdyssey#3142
- **Branch**: 3142-auto-impl
- **PR**: HomericIntelligence/ProjectOdyssey#3308

## Objective

Delete 17 (listed as 18 in title, 17 in body) empty placeholder documentation files containing
only "Content here." text. Update all docs that link to the deleted stubs. Part of a YAGNI
cleanup pass (PR-B in the improvement plan).

## Files Deleted

**docs/advanced/** (6): custom-layers.md, debugging.md, distributed-training.md, integration.md,
performance.md, visualization.md

**docs/core/** (8): agent-system.md, configuration.md, mojo-patterns.md, paper-implementation.md,
project-structure.md, shared-library.md, testing-strategy.md, workflow.md

**docs/dev/** (3): api-reference.md, architecture.md, ci-cd.md

## Files Updated

1. `docs/index.md` - Removed Core Documentation section (8 links), removed 6 stub links from
   Advanced Topics, removed 3 stub links from Development Guides. Kept:
   benchmarking.md, troubleshooting.md, release-process.md.

2. `docs/README.md` - Updated directory tree to reflect actual structure, removed 2 broken
   links from Next Steps section.

3. `docs/glossary.md` - Removed 2 links from See Also section (mojo-patterns, api-reference).

4. `docs/advanced/troubleshooting.md` - Removed 4 plain-text path references from Quick
   Reference Links section.

5. `docs/getting-started/first_model.md` - Removed 4 stub links from Learn More section,
   removed 2 stub links from Related Documentation section.

## Key Decisions

- Kept non-stub files linked from the same sections: `benchmarking.md`, `troubleshooting.md`,
  `release-process.md`, `build.md`
- Removed entire "Core Documentation" section from index.md (all 8 entries were stubs)
- Simplified "Advanced Topics" to only substantive files
- Replaced missing performance/custom-layers links in first_model.md with benchmarking.md

## Environment Issues

- `just` not in PATH - used `pixi run pre-commit run --all-files` instead
- `mojo-format` pre-commit hook fails due to GLIBC version mismatch on this host machine
  (not a code issue) - used `SKIP=mojo-format` for verification
- All other hooks (markdown lint, ruff, yaml, etc.) passed cleanly

## Verification

```bash
grep -rl "custom-layers\|advanced/performance\|core/mojo-patterns\|..." docs/
# Returns: No files found
```