---
name: mojo-reexport-chain-wiring
description: "Wire Mojo structs through a multi-level __init__.mojo re-export chain and expose canonical type aliases at the package root. Use when: (1) a struct exists in a leaf module but is missing from parent package imports, (2) plan-canonical names differ from implementation struct names."
category: architecture
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Project | ProjectOdyssey |
| Objective | Expose `LossTracker` and `AccuracyMetric` at the `shared` package root via re-export chain |
| Outcome | Success — 2 files modified, pre-commit passes, PR #3748 created |
| Issue | HomericIntelligence/ProjectOdyssey#3221 |
| PR | HomericIntelligence/ProjectOdyssey#3748 |

## When to Use

- A Mojo struct is implemented in `pkg/subpkg/module.mojo` but not importable as `from pkg import Struct`
- A `shared/__init__.mojo` has a commented-out line like `# from .training.metrics import Accuracy, LossTracker`
- A plan specifies a canonical name (e.g. `Accuracy`) but the implementation uses a different name (`AccuracyMetric`)
- You need to add symbols to an intermediate `__init__.mojo` (e.g. `shared/training/__init__.mojo`) before the root

**Do NOT use** when the struct itself is missing — this skill is only for wiring existing implementations.

## Verified Workflow

### Step 1 — Confirm the leaf module exports the symbol

```bash
grep -n "^struct\|^from\|^alias" shared/training/metrics/__init__.mojo
```

Verify `LossTracker`, `AccuracyMetric` etc. are already exported from the metrics `__init__.mojo`.

### Step 2 — Add re-exports to the intermediate `__init__.mojo`

In `shared/training/__init__.mojo`, add a block near other exports:

```mojo
# Export training metrics (Issue #XXXX)
from shared.training.metrics import (
    LossTracker,
    Statistics,
    ComponentTracker,
    AccuracyMetric,
    top1_accuracy,
    topk_accuracy,
    per_class_accuracy,
)
```

**Placement**: After other `from shared.training.X import ...` blocks, before any struct definitions.

### Step 3 — Add re-exports + alias to the root `__init__.mojo`

In `shared/__init__.mojo`, replace any commented-out metrics line:

```mojo
# Training metrics (most commonly used) — Issue #XXXX
from shared.training.metrics import LossTracker, AccuracyMetric

# Expose plan-canonical alias: Accuracy = AccuracyMetric
alias Accuracy = AccuracyMetric
```

**Key**: Import directly from the leaf (`shared.training.metrics`), not from the intermediate
(`shared.training`), to avoid Mojo re-export resolution issues with deeply nested chains.

### Step 4 — Verify pre-commit passes

```bash
pixi run pre-commit run --files shared/__init__.mojo shared/training/__init__.mojo
```

Mojo format and syntax hooks will catch any issues. If `mojo build` is unavailable locally
(GLIBC mismatch on older hosts), rely on CI Docker for compilation verification.

### Step 5 — Commit and PR

```bash
git add shared/__init__.mojo shared/training/__init__.mojo
git commit -m "feat(shared): add LossTracker and AccuracyMetric as top-level shared exports

Closes #XXXX"
gh pr create --title "feat(shared): ..." --body "Closes #XXXX" --label "implementation"
gh pr merge --auto --rebase
```

## Results & Parameters

### Files modified in ProjectOdyssey#3748

| File | Change |
|------|--------|
| `shared/training/__init__.mojo` | Added 10-line re-export block for metrics symbols |
| `shared/__init__.mojo` | Replaced 1 commented line with 3 live lines (import + alias) |

### Alias pattern for plan-canonical names

When a plan specifies `Accuracy` but the struct is `AccuracyMetric`:

```mojo
# In shared/__init__.mojo
from shared.training.metrics import AccuracyMetric

alias Accuracy = AccuracyMetric  # plan-canonical name, zero breaking changes
```

This exposes BOTH names — existing callers using `AccuracyMetric` are unaffected.

### Import depth decision

| Approach | Works? | Notes |
|----------|--------|-------|
| `from shared.training.metrics import X` in root `__init__.mojo` | Yes | Direct — bypasses intermediate chain |
| `from shared.training import X` in root `__init__.mojo` | Sometimes | May fail if Mojo re-export resolution is incomplete for that chain |

Prefer direct leaf imports at the root to avoid resolution surprises.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `mojo build shared/` locally | Executed `pixi run mojo build shared/` | GLIBC version mismatch on host (requires 2.32+, host has older) | Mojo compiler requires modern GLIBC; local build only works in Docker/CI environment |
| Running `just build` | Executed `just build` | `just` not in PATH on this host | Always try `pixi run <cmd>` prefix; fall back to checking CI for compilation |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3221, PR #3748 | [notes.md](../references/notes.md) |
