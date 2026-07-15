---
name: hephaestus-slurm-verification-shared-worktree
description: "Run long ProjectHephaestus verification safely on Slurm. Use when jobs need the submitted script and Git worktree after allocation, or when recovering changes from a pruned temporary worktree."
category: testing
date: 2026-07-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [hephaestus, slurm, verification, git-worktree, pixi]
---

# Hephaestus Slurm Verification in a Shared Worktree

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-15 |
| **Objective** | Run complete ProjectHephaestus verification without losing the job script or source worktree after Slurm allocation. |
| **Outcome** | Use ignored repository storage rather than `/tmp`; recover a pruned temporary worktree by byte-comparing its tracked edits into a new shared worktree. |
| **Verification** | verified-local — complete unit suite: 6,226 passed, 24 skipped, 85.28% coverage. |

## When to Use

- A ProjectHephaestus verification run is too long for an interactive shell and must run on Slurm.
- A Slurm job starts on a node that cannot read a submission script or Git worktree located in `/tmp`.
- A temporary linked worktree has been pruned, but its ordinary source files remain and must be preserved exactly.
- A complete verification command needs Pixi tasks after the unit suite.

## Verified Workflow

### Quick Reference

```bash
# Keep both the Slurm script and worktree in ignored, shared repository storage.
git worktree add build/.verification-worktrees/issue-<number> -b issue-<number>-verify origin/main

# Submit a script stored under build/ (not /tmp) and make it cd to that shared path.
sbatch build/verification/issue-<number>-full.sbatch

# ProjectHephaestus Pixi task already provides mypy paths; add no positional path.
pixi run mypy
```

### Detailed Steps

1. Inspect mount visibility from the Slurm execution node before committing to a location. Treat `/tmp` as node-local and ephemeral; it can differ from the submit host.
2. Create the verification worktree in an ignored shared location such as `build/.verification-worktrees/`. Store the `.sbatch` script beneath `build/verification/` as well, with an absolute `cd` to the shared worktree.
3. Submit the shared script and verify the allocation reaches its `cd` and test command in Slurm output. A job that fails before `cd` has not tested the code.
4. If a `/tmp` linked worktree is pruned while its files are still present, create a fresh shared worktree from the intended base. Compare each changed tracked file byte-for-byte (`cmp -s`) and copy only the exact matching intended edits into the new worktree. Re-run `git diff --check` before testing.
5. Run the full unit suite in the shared worktree. In this session it completed with `6226 passed, 24 skipped` and `85.28%` coverage.
6. Run follow-on Pixi tasks separately. Read `pixi.toml` first: ProjectHephaestus's `mypy` task already expands `hephaestus/ scripts/ tests/`, so use `pixi run mypy`, not `pixi run mypy hephaestus/`.
7. Retain the Slurm log and job exit status as verification evidence. Only commit after the complete requested sequence succeeds.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `/tmp` submission assets | Submitted a long verification job whose script and linked worktree were under `/tmp`. | Compute nodes could not access the submit host's `/tmp` script or worktree; jobs failed before executing tests. | Put Slurm scripts and worktrees in shared ignored storage. |
| Trusting temporary worktree metadata | Continued to rely on a `/tmp` linked worktree after cleanup activity. | Git metadata was pruned even though source files remained on disk. | Recreate a shared worktree and recover only byte-compared tracked edits. |
| Adding a mypy path to a Pixi task | Ran `pixi run mypy hephaestus/`. | The task already supplies package, script, and test paths, producing duplicate-module errors. | Inspect task definitions and run `pixi run mypy` with no extra target. |

## Results & Parameters

```text
Shared locations:
  build/.verification-worktrees/issue-<number>
  build/verification/issue-<number>-full.sbatch

Verified local unit result:
  6226 passed, 24 skipped
  coverage: 85.28%

Type-check invocation:
  pixi run mypy
```

The shared `build/` paths must be ignored or otherwise excluded from a product PR. They are execution infrastructure, not source changes.
