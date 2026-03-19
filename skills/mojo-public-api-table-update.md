---
name: mojo-public-api-table-update
description: 'Update the public API comment table in a Mojo __init__.mojo to distinguish
  available-now exports from pending-implementation symbols. Use when: (1) live exports
  were added but the API table still lists them as pending, (2) a flat pending list
  needs splitting into available-now vs pending sections, (3) a newly-added symbol
  is missing from the ASCII table of top-level exports.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Objective** | Keep `shared/__init__.mojo` API documentation consistent with actual live exports |
| **Outcome** | Success — comment-only PR merged via auto-merge with no test impact |
| **Issue** | ProjectOdyssey #3751 (follow-up from #3220) |

## When to Use

- A `shared/__init__.mojo` has a flat "will be available once implementation completes" comment
  block that has grown stale after some symbols were actually implemented and exported.
- Newly added live exports (e.g. `ConfusionMatrix`, `CSVMetricsLogger`) appear in `from
  shared.training.metrics import ...` lines but are absent from the ASCII box-drawing table.
- A reviewer requests that the API table distinguish "importable today" from "future".

## Verified Workflow

### Quick Reference

```bash
# 1. Read the file, identify the flat list and the ASCII table
# 2. Split the flat list into two labelled sections
# 3. Add any missing symbols to the ASCII table rows
# 4. Commit as docs(shared): ... — no tests needed, comment-only
SKIP=mojo-format just pre-commit   # mojo-format skipped due to GLIBC; all others pass
git add shared/__init__.mojo
git commit -m "docs(shared): update public API table in shared/__init__.mojo"
```

### Step-by-step

1. **Read `shared/__init__.mojo`** in full. Identify:
   - The flat "pending" comment block (typically ~15 lines after `# Public API`)
   - The ASCII box-drawing table (typically after `# Convenience: Make subpackages accessible`)
   - The actual live `from shared.X import Y` lines (these are "available now")

2. **Determine the live-vs-pending split**:
   - "Available now": any symbol that has a real (uncommented) `from ... import` statement
     in the file, plus subpackage imports (`from shared import core`) and compile-time aliases
     (`comptime Accuracy = AccuracyMetric`).
   - "Pending": any symbol still sitting in a commented-out `# from .core.layers import ...`
     block.

3. **Rewrite the flat list** as two labelled sections:

   ```mojo
   # Available now (importable from `shared` today):
   # Version info: VERSION, AUTHOR, LICENSE
   # Training - Metrics: LossTracker, AccuracyMetric, Accuracy (alias), ConfusionMatrix,
   #   CSVMetricsLogger
   # Testing: GRADIENT_CHECK_EPSILON_FLOAT32
   # Subpackages: core, training, data, utils, autograd, testing
   #
   # Pending implementation (available once core modules are complete):
   # Core - Layers: Linear, Conv2D, ReLU, MaxPool2D, Dropout, Flatten
   # ... etc
   ```

4. **Update the ASCII table** to include every live symbol. For multi-symbol rows, use
   continuation lines to avoid column overflow:

   ```mojo
   # │ LossTracker, AccuracyMetric,    │ shared.training.metrics                │
   # │   ConfusionMatrix,              │                                        │
   # │   CSVMetricsLogger              │                                        │
   ```

5. **Run pre-commit** (skip mojo-format if GLIBC-incompatible):

   ```bash
   SKIP=mojo-format just pre-commit
   ```

6. **Commit and PR** as documentation-only; no tests are needed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4786, issue #3751 | [notes.md](../../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Including `Autograd` in "Available now" | Listed `autograd` subpackage alongside `core` etc. | `autograd` subpackage is imported via `from shared import autograd` so it IS live — not a failure, but it's easy to forget it. | Cross-check every `from shared import X` line, not just the ones in the `# Core Exports` section. |
| Leaving `ConfusionMatrix`/`CSVMetricsLogger` out of ASCII table | They were present in the flat list but the table only mentioned `LossTracker, AccuracyMetric` | Table row exceeded column width; continuation lines were needed | Use two or three continuation rows for long symbol lists rather than widening the column. |

## Results & Parameters

- **Change type**: comment-only — no code, no tests, no CI risk
- **Pre-commit**: `SKIP=mojo-format just pre-commit` passes on GLIBC-incompatible hosts
- **Label**: `documentation`
- **Auto-merge**: enable with `gh pr merge --auto --rebase` immediately after PR creation
- **Commit format**: `docs(shared): update public API table in shared/__init__.mojo`
