---
name: tooling-dagger-sdk-v020-breaking-changes
description: "Migrate Dagger SDK from v0.9.x to v0.20+. Use when: (1) CI TypeScript typecheck fails after a dagger SDK bump, (2) upgrading dagger from 0.9 to 0.20+, (3) seeing 'Container.build is not a function' or similar type errors after a dependabot dagger upgrade PR."
category: tooling
date: 2026-04-28
version: "1.0.0"
user-invocable: false
tags: [dagger, ci-cd, typescript, breaking-changes, dependabot, migration]
---

# Dagger SDK v0.20.x Breaking API Changes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Migrate Dagger SDK usage from v0.9.x to v0.20+ after the removal of `Container.build()`. |
| **Outcome** | TypeScript typecheck and CI pass after replacing `dag.container().build(context)` with `context.dockerBuild()` and updating all package manifests. |
| **Observed In** | HomericIntelligence/ProjectProteus PR #79 (2026-04-28) |
| **Verification** | `verified-ci` — Proteus PR #79 merged successfully after applying these fixes |

## When to Use

- CI TypeScript typecheck job fails after a dependabot PR bumps `@dagger.io/dagger` to `^0.20.x`
- You see a type error referencing `Container.build` or `build` not existing on `Container`
- Upgrading a Dagger-based CI pipeline from dagger v0.9.x to v0.20+
- A dependabot PR has bumped the SDK but the TypeScript source still uses the old API

## Verified Workflow

### Quick Reference

```bash
# 1. Update dagger/package.json versions
# 2. Update dagger/dagger.json engineVersion
# 3. Regenerate dagger/package-lock.json
# 4. Fix TypeScript source: Container.build() → context.dockerBuild()
# 5. Switch CI to: npm ci (reproducible installs)
```

### Detailed Steps

#### 1. Update `dagger/package.json`

```json
// Before (dagger 0.9.x)
{
  "dependencies": {
    "@dagger.io/dagger": "^0.9.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0"
  }
}

// After (dagger 0.20+)
{
  "dependencies": {
    "@dagger.io/dagger": "^0.20.6"
  },
  "devDependencies": {
    "@types/node": "^25.6.0"
  }
}
```

#### 2. Update `dagger/dagger.json`

```json
// Before
{ "engineVersion": "v0.9.0" }

// After
{ "engineVersion": "v0.20.6" }
```

#### 3. Regenerate `dagger/package-lock.json`

```bash
cd dagger && npm install
```

The lockfile must be regenerated after the version bump. Commit the updated lockfile.

#### 4. Fix TypeScript Source — the Critical API Change

```typescript
// OLD (dagger 0.9.x) — BROKEN in v0.20+
const ctr = dag.container().build(context)

// NEW (dagger 0.20+)
const ctr = context.dockerBuild()
```

`Container.build(context)` was removed. The build entry point moved to the
`Directory` object: call `dockerBuild()` on the context directory instead.

#### 5. Switch CI to `npm ci`

In `.github/workflows/ci.yml` (or equivalent), replace `npm install` with `npm ci`:

```yaml
# Before
- run: npm install
  working-directory: dagger

# After
- run: npm ci
  working-directory: dagger
```

`npm ci` uses the lockfile exactly, producing reproducible installs across CI runs.

### Root Cause in CI

When a dependabot PR bumps `@dagger.io/dagger` to `^0.20.6`, the merge commit
contains the new SDK but the TypeScript source still calls the removed
`Container.build()` API. The typecheck job fails on the merge commit even though
the PR branch alone passes (it has neither the old nor new code changed in isolation).

The fix must be applied atomically: update the SDK version AND the TypeScript source
in the same commit so neither half is broken independently.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Version bump only | Updated `package.json` and `dagger.json` without touching TypeScript source | TypeScript type errors remained: `Container` has no `build` method in v0.20 SDK typings | SDK version and source changes must be co-located in the same commit |
| `npm install` in CI | Used `npm install` instead of `npm ci` | Non-reproducible installs: resolved versions differ between local and CI environments, masking lockfile drift | Always use `npm ci` in CI pipelines; `npm install` is for local development |

## Results & Parameters

### API Change Summary

| v0.9.x API | v0.20+ API | Notes |
|-----------|-----------|-------|
| `dag.container().build(context)` | `context.dockerBuild()` | Entry point moved from `Container` to `Directory` |
| `Container.build(dir: Directory)` | `Directory.dockerBuild()` | Method removed from `Container` entirely |

### Files to Update

| File | Change |
|------|--------|
| `dagger/package.json` | `@dagger.io/dagger`: `^0.9.0` → `^0.20.6`; `@types/node`: `^20.0.0` → `^25.6.0` |
| `dagger/dagger.json` | `engineVersion`: `v0.9.0` → `v0.20.6` |
| `dagger/package-lock.json` | Regenerate with `npm install` after version change |
| `dagger/*.ts` | `dag.container().build(context)` → `context.dockerBuild()` |
| `.github/workflows/ci.yml` | `npm install` → `npm ci` |

### Verification Checklist

- [ ] `cd dagger && npm ci && npx tsc --noEmit` passes locally
- [ ] CI typecheck job passes on the PR
- [ ] No remaining `dag.container().build(` calls in TypeScript source (`grep -r 'container().build' dagger/`)
- [ ] `dagger/package-lock.json` committed alongside `package.json` changes

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectProteus | PR #79 (2026-04-28) | Dependabot bumped `@dagger.io/dagger` to `^0.20.6`; TypeScript CI failed until source and manifest were co-updated |
