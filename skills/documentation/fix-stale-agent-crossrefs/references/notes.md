# Session Notes: Fix Stale Agent Cross-References

## Context

- **PR**: #3319
- **Issue**: #3144
- **Branch**: `3144-auto-impl`
- **Date**: 2026-03-05

## What Was Done

PR #3319 consolidated 13 review specialists into 5. The consolidation correctly deleted the
specialist files but left stale `Coordinates With` links in 4 remaining agent configs.

### Files Fixed

1. `.claude/agents/mojo-language-review-specialist.md:131-132`
   - Deleted: `performance-review-specialist.md`, `safety-review-specialist.md`
   - Replaced with: `general-review-specialist.md`

2. `.claude/agents/numerical-stability-specialist.md:117-118`
   - Deleted: `algorithm-review-specialist.md`, `performance-review-specialist.md`
   - Replaced with: `general-review-specialist.md`

3. `.claude/agents/security-review-specialist.md:93`
   - Deleted: `dependency-review-specialist.md`
   - Replaced with: `general-review-specialist.md`

4. `.claude/agents/test-review-specialist.md:95-96`
   - Deleted: `algorithm-review-specialist.md`, `implementation-review-specialist.md`
   - Replaced with: `general-review-specialist.md`

## Environment Issues Encountered

- `just` not installed: use `pre-commit run --all-files` directly
- GLIBC too old for `mojo` binary (requires GLIBC 2.32+, host has older): mojo-format hook
  fails on all files but is pre-existing and unrelated to `.md` changes
- `npx` / `markdownlint-cli2` not in PATH outside pixi env: rely on pre-commit hook

## Line Length Issue

First attempt at merging two lines used a long description (127 chars). Fixed by shortening:

- Too long: "Suggests numerical/gradient tests and notes untested code paths" (line 127 chars)
- Fixed: "Coordinates on tests and untested code paths" (line 109 chars)

## Validation Results

- `validate_configs.py`: 35/35 PASS, 0 errors (60 pre-existing warnings)
- pre-commit (on commit): all hooks passed for `.md` files
- mojo-format: skipped automatically (no `.mojo` files staged)
