---
name: centralized-path-constants
description: "Create central path constants module to prevent hardcoded path inconsistencies. Use when: (1) multiple files construct the same paths inline, (2) directory structure changes require updating many files, (3) a directory structure has phases (e.g., in_progress/completed) that must be routed at a single point."
category: architecture
date: 2026-03-28
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: centralized-path-constants.history
tags:
  - paths
  - refactoring
  - consistency
  - constants
  - dry-principle
  - phase-routing
---

# Centralized Path Constants

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Eliminate hardcoded path construction; create single source of truth for directory structure including phase-based routing |
| **Outcome** | ✅ v1.0.0: basic centralization. v2.0.0: phase-routed paths (in_progress/completed split) |
| **Verification** | verified-ci |
| **History** | [changelog](./centralized-path-constants.history) |
| **Project** | ProjectScylla |
| **PRs** | [#137](https://github.com/HomericIntelligence/ProjectScylla/pull/137), [#1738](https://github.com/HomericIntelligence/ProjectScylla/pull/1738) |

## When to Use

- Multiple files construct the same paths with hardcoded strings
- Path logic is duplicated across modules
- Refactoring directory structure requires changes in many places
- Resume/checkpoint logic needs to validate path existence
- Risk of typos in path strings (e.g., `"agent"` vs `"agents"`)
- **NEW**: The directory structure has phases (e.g., `in_progress/` vs `completed/`) — routing must be centralized or bypass violations will appear at every path construction site

## Verified Workflow

### Quick Reference

```python
# paths.py — minimal structure
from pathlib import Path
import shutil

# Phase constants (if using phase-split)
IN_PROGRESS_DIR = "in_progress"
COMPLETED_DIR = "completed"

# Sub-directory constants
AGENT_DIR = "agent"
JUDGE_DIR = "judge"
RESULT_FILE = "result.json"

# Basic helpers
def get_agent_dir(run_dir: Path) -> Path:
    return run_dir / AGENT_DIR

def get_judge_dir(run_dir: Path) -> Path:
    return run_dir / JUDGE_DIR

# Phase-routed helpers (keyword-only completed= for safety)
def get_tier_dir(experiment_dir: Path, tier_id: str, *, completed: bool = False) -> Path:
    phase = COMPLETED_DIR if completed else IN_PROGRESS_DIR
    return experiment_dir / phase / tier_id

def get_subtest_dir(experiment_dir, tier_id, subtest_id, *, completed=False):
    return get_tier_dir(experiment_dir, tier_id, completed=completed) / subtest_id

def get_run_dir(experiment_dir, tier_id, subtest_id, run_num, *, completed=False):
    return get_subtest_dir(experiment_dir, tier_id, subtest_id, completed=completed) / f"run_{run_num:02d}"

def get_experiment_dir_from_run(run_dir: Path) -> Path:
    """Reverse derivation — 4 levels up: run -> subtest -> tier -> phase -> experiment."""
    return run_dir.parent.parent.parent.parent

def promote_run_to_completed(experiment_dir, tier_id, subtest_id, run_num) -> Path:
    src = get_run_dir(experiment_dir, tier_id, subtest_id, run_num, completed=False)
    dst = get_run_dir(experiment_dir, tier_id, subtest_id, run_num, completed=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    # IMPORTANT: copy (not move) shared baseline so sibling runs can also be promoted
    baseline = src.parent / "pipeline_baseline.json"
    if baseline.exists():
        shutil.copy2(str(baseline), str(dst.parent / "pipeline_baseline.json"))
    return dst
```

### Detailed Steps

#### Basic Centralization (v1.0.0 pattern)

1. **Create `paths.py`** with directory name constants and helper functions
2. **Import in callers** — replace every `run_dir / "agent"` with `get_agent_dir(run_dir)`
3. **Use constants for filenames** — `RESULT_FILE` not `"result.json"`
4. **Write tests** verifying helper return values

#### Phase-Routed Paths (v2.0.0 addition)

1. **Add `IN_PROGRESS_DIR`/`COMPLETED_DIR`** constants
2. **Add `completed=False` parameter** (keyword-only with `*`) to all phase-sensitive helpers
3. **Default to `in_progress`** — callers doing active work don't need to change
4. **Callers doing read/report work** explicitly pass `completed=True`
5. **Run pre-merge audit** to catch bypass violations before merging

### Pre-Merge Audit (CRITICAL for directory structure changes)

```bash
# Find all sites that bypass paths.py and construct paths directly
# Run before merging any PR that changes directory structure
grep -rn "experiment_dir / \|experiment_dir/" src/ scripts/ \
  | grep -v "paths.py" \
  | grep -v "# noqa" \
  | grep -v "__pycache__" \
  | grep -v ".pyc"
```

**Expected output:** Zero hits. Any hit is a bypass violation that must be fixed.

**When to run:** Before every PR that adds or changes a path-level constant in `paths.py`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Basic string paths | Direct `run_dir / "agent"` in every file | Typos (`"agents"` vs `"agent"`) caused silent failures | Use constants from paths.py even for short strings |
| Phase split without audit | Added in_progress/completed split but didn't audit all callers | 17 files post-merge still used `experiment_dir / tier_id` directly — silent wrong-dir reads | ALWAYS run the pre-merge audit grep before merging a directory structure change |
| `shutil.move` for shared baseline | Moved `pipeline_baseline.json` with the first run during promotion | Second run in same subtest can't find baseline — it was moved away | Use `shutil.copy2` for files shared across sibling runs; only move the run directory itself |
| Stale fallback after refactor | Left `elif` fallback pointing to old path | `best_subtest.json` in new `completed/` was never reached; fallback silently returned wrong data | Delete stale fallbacks entirely; don't leave "just in case" code pointing at wrong locations |

## Results & Parameters

### Bypass Violation Count by Category (2026-03-28 experience)

When the `in_progress/completed` split was added, **17 bypass violations** were found post-merge across:

| Module | Violations | Fix |
|--------|-----------|-----|
| `tier_manager.py` | 3 | `get_tier_dir(..., completed=True)` |
| `parallel_tier_runner.py` | 1 | `get_subtest_dir(..., completed=True)` |
| `regenerate.py` | 3 | `get_run_dir/get_tier_dir/get_subtest_dir(completed=True)` |
| `manage_experiment.py` | 2 | Check both `completed/` and `in_progress/` |
| `resume_manager.py` | 2 | `get_run_dir` + frozenset update |
| `tier_action_builder.py` | 1 | Remove stale fallback |
| Test fixtures | 5+ | Update to use `completed/` prefix |

**Lesson:** The pre-merge grep would have found all 17 in 5 seconds.

### `completed=` Routing Decision Table

| Site | `completed=` | Reason |
|------|-------------|--------|
| Active run execution (PENDING to DIFF_CAPTURED) | `False` | Work is in-flight |
| Judging and reporting (PROMOTED_TO_COMPLETED+) | `True` | Only completed runs are judged |
| Rehydration / resume scanning | `True` | Completed runs have stable data |
| Aggregation, analysis, loader | `True` | Must only aggregate finished runs |
| Repair / reconcile commands | Both | Run may be in either phase |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #137 — initial path standardization | Basic constants and helpers |
| ProjectScylla | PRs #1738/#1739 — in_progress/completed split | Phase-routed paths, 17 post-merge bypass violations found and fixed |
