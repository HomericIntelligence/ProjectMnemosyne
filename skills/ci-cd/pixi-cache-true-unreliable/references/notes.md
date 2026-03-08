# Session Notes — pixi-cache-true-unreliable

## Session Context

- **Date**: 2026-03-08
- **Project**: ProjectOdyssey (ML Odyssey, Mojo-based AI research platform)
- **Issue**: #3155 — [P3-1] Remove duplicate Pixi caching in CI workflows
- **PR**: #4464

## What Was Done

Issue #3155 required consolidating 14+ independent Pixi setup blocks across CI workflows.
The prerequisite composite action (`.github/actions/setup-pixi/action.yml`) from issue #3149
already existed but was using the broken `cache: true` built-in option.

### State at Start of Session

- Composite action existed at `.github/actions/setup-pixi/action.yml`
- All 19 workflow references already used `./.github/actions/setup-pixi`
- The composite action itself used `cache: true` (the problematic pattern)
- No inline `prefix-dev/setup-pixi` calls remained in individual workflow files

### Changes Made

**File 1**: `.github/actions/setup-pixi/action.yml`
- Removed `cache: true` from the `prefix-dev/setup-pixi` step
- Added explicit `actions/cache@v5` step caching `.pixi` and `~/.cache/rattler/cache`
- Changed cache key from `pixi.toml` hash to `pixi.lock` hash

**File 2**: `.github/workflows/README.md`
- Updated documentation example from inline `cache: true` pattern to composite action reference
- Fixed malformed code block (was `\`\`\`text` as closing tag instead of `\`\`\``)

## Key Discovery

The issue description mentioned "14 workflows with independent Pixi caching" but the actual
state was already consolidated — all workflows used the composite action. The composite action
itself was the remaining problem. This is a common pattern:

1. First PR (#3149): Creates composite action, migrates workflows to use it
2. Second PR (#3155): Fixes the composite action's own caching strategy

## Verification Commands Used

```bash
# Confirm no inline setup-pixi in workflows
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml
# → no output (good)

# Confirm all workflows use composite
grep -rn "\.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
# → 19

# Confirm no cache: true in actions
grep -rn "cache: true" .github/actions/
# → no output (good)
```

## Team Learnings Referenced

The implementation plan referenced `github-actions-ci-speedup` skill plugin which documented:
- `cache: true` causes "Saved cache with ID -1" failure
- Both `.pixi` AND `~/.cache/rattler/cache` must be cached
- `pixi.lock` is preferred over `pixi.toml` as cache key hash source
