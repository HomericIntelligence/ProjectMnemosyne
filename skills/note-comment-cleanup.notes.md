# Session Notes: note-comment-cleanup

## Session Context

- **Date**: 2026-03-05
- **Issue**: HomericIntelligence/ProjectOdyssey #3074
- **Branch**: `3074-auto-impl`
- **PR**: HomericIntelligence/ProjectOdyssey #3288

## What Was Done

Implemented GitHub issue #3074: "[Cleanup] Review miscellaneous reference NOTEs".

The issue plan (from `gh issue view 3074 --comments`) specified:

1. Remove 2 stale `get_plan_dir() removed` markers from `scripts/common.py` and `scripts/regenerate_github_issues.py`
2. Update `shared/__init__.mojo` NOTE referencing closed issue #49 (verified closed via `gh issue view 49`)
3. Convert 6 `NOTE:` prefixes inside docstrings to plain prose:
   - `shared/training/trainer.mojo` (3 locations)
   - `shared/training/trainer_interface.mojo` (1 location)
   - `shared/utils/config.mojo` (2 locations)
4. Normalize `# Note:` → `# NOTE:` in all `shared/` source files

## Discovery Process

Started with broad grep across all .mojo files:

```
Grep pattern: "# NOTE:|# Note:|# note:|# NOTE "
Path: worktree root
Glob: **/*.mojo
```

Got ~100+ matches. Then read the issue comments to get the plan which pre-categorized
the dispositions. This saved significant analysis time.

## Files Modified

```
scripts/common.py
scripts/regenerate_github_issues.py
shared/__init__.mojo
shared/autograd/__init__.mojo
shared/core/__init__.mojo
shared/core/activation_simd.mojo
shared/core/attention.mojo
shared/data/__init__.mojo
shared/data/_datasets_core.mojo
shared/testing/layer_testers.mojo
shared/training/__init__.mojo
shared/training/callbacks.mojo
shared/training/checkpoint.mojo
shared/training/optimizers/adamw.mojo
shared/training/schedulers/lr_schedulers.mojo
shared/training/trainer.mojo
shared/training/trainer_interface.mojo
shared/utils/__init__.mojo
shared/utils/config.mojo
shared/utils/file_io.mojo
shared/utils/profiling.mojo
shared/utils/toml_loader.mojo
shared/utils/training_args.mojo
```

## Pre-Commit Behavior

- `mojo-format`: FAILS with GLIBC version errors (local machine has GLIBC < 2.32, mojo requires >= 2.32)
- `ruff-format-python`: Auto-reformatted 1 file on first run (this was in the background task that completed after commit)
- All other hooks: PASS

The GLIBC issue is a known environment limitation. CI runs in Docker with correct GLIBC.

## Tooling Notes

- `just` is NOT on PATH in this environment — use `pixi run pre-commit run --all-files`
- `TaskOutput` with `block: true` requires boolean type; polling requires waiting and re-reading output file
- Background pre-commit tasks write to `/tmp/claude-1000/<worktree-hash>/tasks/<task-id>.output`
- Edit tool requires file to have been Read in the current conversation session
