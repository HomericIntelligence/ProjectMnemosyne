---
name: mojo-version-migration-strategy
description: "Strategy for migrating a large Mojo codebase across versions. Use when: (1) planning a Mojo version upgrade across many files, (2) coordinating multi-agent migration work, (3) deciding fix order for cascading compile errors."
category: architecture
date: 2026-04-08
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, migration, version-upgrade, agent-coordination, strategy]
---

# Mojo Version Migration Strategy

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Objective** | Provide a repeatable strategy for migrating large Mojo codebases across major version boundaries |
| **Outcome** | Strategy extracted from 0.26.1 → 0.26.3 migration attempt on ~525 .mojo files (ProjectOdyssey) |
| **Verification** | unverified — migration in progress; CI validation pending |

## When to Use

- Planning a Mojo version upgrade on a codebase with >50 `.mojo` files
- Coordinating multiple agents working on the same migration
- Deciding which files to fix first when errors cascade across dependencies
- Choosing between workaround and proper fix for a breaking change

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end (verification: unverified). Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Step 1: Get unique error categories (not per-file noise)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Step 2: Get error counts per category to prioritize
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sed 's/.*error: //' | sort | uniq -c | sort -rn | head -20

# Step 3: Fix shared/ core types first
# Step 4: Verify package builds
pixi run mojo package -I . shared -o /tmp/shared.mojopkg

# Step 5: Fix tests/ and examples/
pixi run mojo test tests/

# Step 6: Check deprecation warnings separately (they don't block)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | sort -u
```

### Detailed Steps

#### Phase 1: Triage (do this before touching any code)

1. Run `mojo package ... 2>&1 | grep ": error:" | sort -u` on the core package
2. Categorize errors by type (see `mojo-026-breaking-changes` skill for catalog)
3. Separate hard errors (block compilation) from deprecation warnings (don't block)
4. Identify which errors affect core types vs peripheral files

#### Phase 2: Fix in Dependency Order

Fix errors bottom-up — types used by everything else must be fixed first:

```
shared/core/         ← Fix first (types used everywhere)
shared/tensor/       ← Fix second (depends on core)
shared/layers/       ← Fix third (depends on tensor)
tests/               ← Fix last (nothing depends on tests)
examples/            ← Fix last (nothing depends on examples)
```

Within each directory, fix in this order:
1. Struct definition changes (`@register_passable`, `ImplicitlyCopyable`, field types)
2. Import changes (scope restrictions, stdlib renaming)
3. Method signature changes (`String.__getitem__`, math constraints)
4. Closure/nested function changes (`@escaping`, `unified`)

#### Phase 3: Verify Incrementally

After fixing each directory:
```bash
# Verify the package still builds before moving on
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:"
```

#### Phase 4: Address Warnings (separate pass)

Deprecation warnings don't block CI — address them in a separate PR after hard errors are fixed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| API probing via test files | Created small test .mojo files to discover correct API behavior | Slow (each requires a full compile cycle); distracts from actual migration | Fetch official docs at `https://docs.modular.com/mojo/std/` instead — always authoritative |
| Multiple agents on overlapping files | Ran several sub-agents fixing different files simultaneously without file locks | Caused merge conflicts when agents modified the same shared type | Assign agents to non-overlapping directories; one agent per directory subtree |
| Removing `ImplicitlyCopyable` to fix `List` field | Dropped the trait from `AnyTensor` as the "easy" fix | Caused 62-file cascade of implicit copy errors across the entire codebase | Prefer `InlineArray` field replacement; map cascade depth before choosing approach |
| `sed` bulk `fn` → `def` | Used sed to replace `fn` keyword globally | Replaces `fn` inside comments, strings, and identifiers (e.g., `fn_count`) | Use targeted regex matching `^fn` or `\bfn\b` only at definition sites; or skip since `fn` is only a warning, not an error in 0.26.3 |
| Workaround helper functions | Added `str_slice(s, start, end)` helper to hide new String API | User explicitly rejected as engineering debt | Use the new API directly at callsites (`String(s[byte=start:end])`); document the new pattern |
| `just package` for compilation | Used `just package` (which writes to `build/debug/`) | Permission issues with the build directory | Use `pixi run mojo package -I . shared -o /tmp/shared.mojopkg` directly |

## Results & Parameters

### Agent Coordination Pattern (Non-Overlapping)

When using multiple agents for a bulk migration, assign by directory to avoid conflicts:

```
Agent 1: shared/core/           (types, tensor, memory)
Agent 2: shared/layers/         (neural network layers)
Agent 3: shared/training/       (optimizers, loss functions)
Agent 4: tests/ + examples/     (only after Agents 1-3 complete)
```

Sequential constraint: Agents 2-4 must wait for Agent 1 to complete before starting.
Agents 2 and 3 can run in parallel after Agent 1. Agent 4 runs last.

### ImplicitlyCopyable + List Decision Tree

```
Does the struct have List[T] fields AND declare ImplicitlyCopyable?
├─ YES → How widely is implicit copy used?
│   ├─ Few callsites (< 10 files affected) → Remove ImplicitlyCopyable, fix callsites
│   └─ Many callsites (> 10 files affected) → Replace List[T] with InlineArray[T, MAX_N]
│       └─ For ML tensors: MAX_DIMS = 8 is sufficient
└─ NO → No action needed
```

### Verification Commands After Migration

```bash
# Full package build (should exit 0 with no errors)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg
echo "Exit: $?"

# Run tests (use pixi run, not just mojo test — environment matters)
pixi run mojo test tests/shared/

# Check warnings count (track reduction over time)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | wc -l
```

### When to Fetch Docs vs Probe

| Situation | Action |
|-----------|--------|
| Unknown new API signature | Fetch from `https://docs.modular.com/mojo/std/<module>/` |
| API behavior ambiguous from docs | Write a minimal test file (last resort) |
| Error message is clear | Fix directly without probing |
| Deprecated API, need replacement | Check changelog at `https://docs.modular.com/mojo/changelog/` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 migration, ~525 .mojo files, 7807 fn definitions | Migration in progress; strategy developed from first migration attempt |
