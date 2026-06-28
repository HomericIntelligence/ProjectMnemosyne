---
name: test-worktree-parents-path-resolves-wrong-tree
description: "A repo-scanning test that locates the tree it scans via Path(__file__).parents[N] / 'subdir' resolves to the WRONG checkout when pytest is run from a different directory than the test file's repo — e.g. invoking pytest at the MAIN repo root against test files living in a git worktree under build/.worktrees/<x>/. parents[N] anchors to the file's branch, but a cwd mismatch means a local 'FAILURE' may have scanned the main checkout (a different branch with different code), producing false failures (or false passes) that CI does not reproduce. Use when: (1) a repo-scanning guard/assertion test fails locally but you suspect a worktree/cwd artifact, (2) validating a worktree branch by running pytest from the main checkout root, (3) a test passes in CI but fails locally with offenders you cannot find on the branch."
category: testing
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - testing
  - git-worktree
  - cwd
  - path-resolution
  - pathlib-parents
  - repo-scanning
  - false-failure
  - pytest
---

# Testing: Worktree parents[N] Path Resolves to the Wrong Tree

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-27 |
| **Objective** | Diagnose a repo-scanning guard test that "FAILED" locally with 54 offenders the branch did not actually contain |
| **Outcome** | Successful — confirmed FALSE FAILURE caused by a worktree/cwd mismatch, not a code reversion |
| **Verification** | verified-local |

## When to Use

- A repo-scanning test (one that walks a tree via `Path(__file__).parents[N] / "subdir"` and asserts something about the files it finds) FAILS locally but you suspect the failure is a path/cwd artifact rather than a real defect.
- You are validating a git WORKTREE branch (checked out under `build/.worktrees/<x>/`) by running pytest from the MAIN repo root instead of from the worktree root.
- A test passes in CI (which checks out only the branch) but fails locally, reporting offenders you cannot find anywhere on the branch.
- You catch yourself "hunting" for a reversion that the branch's actual tree does not contain.

## Verified Workflow

### Quick Reference

```bash
# When a repo-scanning test "fails" locally but you suspect a worktree/cwd artifact:
# 1. Check what tree the test actually scanned — print its computed root:
python3 -c "from pathlib import Path; print(Path('<test_file>').resolve().parents[3])"
# If that path is the MAIN checkout (not your worktree), the failure is a cwd artifact.
# 2. Re-run the test with the WORKTREE as cwd (what CI does — it checks out only the branch):
cd <worktree-root> && pixi run pytest <test_path> -q --no-cov
# 3. Confirm by running the test's scan logic directly against the worktree tree.
# 4. To avoid the false signal entirely when validating a worktree branch locally, ALWAYS run
#    the FULL test suite with cwd == the worktree root, not the main checkout root.
```

### Detailed Steps

1. **Print the tree the test actually scanned.** Reproduce the test's root computation outside pytest. For a test that does `Path(__file__).parents[3] / "hephaestus/automation"`:

   ```bash
   python3 -c "from pathlib import Path; print(Path('tests/unit/automation/test_atomic_write_guard.py').resolve().parents[3])"
   ```

   If the printed path is the MAIN checkout root (e.g. `/home/mvillmow/Projects/ProjectHephaestus`) rather than your worktree (`.../build/.worktrees/fix-impl-1657`), the scan ran against the wrong checkout — a different branch with potentially different code. The "failure" is a cwd artifact.

2. **Re-run the test from the worktree root** — this matches what CI does, since CI checks out only the branch:

   ```bash
   cd <worktree-root>
   pixi run pytest tests/unit/automation/test_atomic_write_guard.py -q --no-cov
   ```

   A pass here while the main-root run "fails" confirms the artifact.

3. **Confirm by running the scan logic directly** against the worktree tree (e.g. the guard's AST walk over `hephaestus/automation`). Zero offenders on the worktree tree proves the branch is clean.

4. **Prevent the false signal entirely.** When validating a worktree branch locally, ALWAYS run the FULL suite with `cwd == the worktree root`, never from the main checkout root. `parents[N]` anchors to `__file__` (the branch the file is ON), but pytest invocation/cwd does not change `__file__`; the trap is treating a local "FAILED" as equivalent to a CI failure when the two ran against different checkouts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ran `pixi run pytest <worktree>/tests/...` from the MAIN repo root to validate a worktree branch | The guard test computed its scan root via `Path(__file__).parents[3]` which resolved to the MAIN checkout (a different branch), reporting 54 false offenders | Run repo-scanning tests with cwd == the worktree root; `parents[N]` is relative to the file, but the test's INTENT is the repo it belongs to — a mismatched cwd breaks that |
| Trusted the local "FAILED" and started hunting for raw `write_text` reversions in the branch | The branch genuinely had 0 offenders; the failure was a path-resolution artifact, wasting time | Before fixing, verify the test scanned the RIGHT tree (print `parents[N]`); re-run with the worktree cwd; a CI-only-clean test that "fails" locally is often a cwd artifact |

## Results & Parameters

Concrete evidence — ProjectHephaestus #1657 (2026-06-27): `tests/unit/automation/test_atomic_write_guard.py` walks `Path(__file__).parents[3] / "hephaestus/automation"` asserting zero raw `write_text` calls remain. Run from a worktree at `build/.worktrees/fix-impl-1657/` but with pytest invoked from the MAIN repo root `/home/mvillmow/Projects/ProjectHephaestus`, `parents[3]` resolved to the MAIN checkout root (on a different branch with older code) and reported 54 raw-write offenders — a FALSE FAILURE. The branch's actual tree had 0 offenders. Proof: running the same test with the worktree as cwd (`cd <worktree> && pixi run pytest tests/unit/automation/test_atomic_write_guard.py`) PASSED, and running the guard's AST logic directly on the worktree tree found 0 offenders. CI — which checks out only the branch — passes correctly; the failure was a local cwd/path artifact only.

General rule: `Path(__file__).parents[N]` anchors to the FILE, which is correct for the branch the file is ON, but pytest's cwd / how you invoke it does not change `__file__`. The real trap is assuming a local failure == a CI failure when the two ran against different checkouts. The robust fix for the TEST itself is fine as-is (parents-anchored, not cwd-anchored); the discipline that matters is the VALIDATION habit: run the full suite from the worktree root, not the main checkout root.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1657 (2026-06-27) — `test_atomic_write_guard.py` raw-write guard | verified-local: false 54-offender failure from main-root cwd; worktree-root run passed with 0 offenders |
