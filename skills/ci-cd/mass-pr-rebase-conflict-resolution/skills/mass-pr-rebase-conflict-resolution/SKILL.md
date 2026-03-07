---
name: mass-pr-rebase-conflict-resolution
description: "Rebase multiple DIRTY/CONFLICTING PRs against main, resolve merge conflicts, and fix pre-commit format CI failures without local mojo format. Use when: (1) many PRs show DIRTY merge state after main advances, (2) mojo format fails in CI but can't run locally due to GLIBC incompatibility, (3) same files conflict across many PRs."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Trigger** | Multiple PRs in DIRTY/CONFLICTING merge state |
| **Complexity** | High — requires reading CI diffs and manually applying format fixes |
| **Time** | ~2-3 minutes per PR (20 PRs = ~1 hour) |
| **Risk** | Medium — force-with-lease pushes, no data loss if done correctly |

## When to Use

- `gh pr list --json mergeStateStatus` shows many PRs with `DIRTY` status
- CI pre-commit hook fails with `reformatted <file>.mojo` but `mojo format` can't run locally
- A core file (like `extensor.mojo`) is being modified by many concurrent PRs with diverging method implementations
- You need to batch-rebase 10+ PRs and each one conflicts with main

## Verified Workflow

### Step 0: Triage PRs by status

```bash
gh pr list --json number,title,mergeStateStatus,headRefName --limit 50 | python3 -c "
import json, sys
prs = json.load(sys.stdin)
for pr in sorted(prs, key=lambda x: x['number']):
    print(f\"PR #{pr['number']:4d} [{pr['mergeStateStatus']:12s}] {pr['headRefName']}\")
"
```

Categories:
- `DIRTY` → needs rebase
- `BLOCKED` → CI failing (check which checks, may be format-only)
- `UNKNOWN` → CI pending or passing, let auto-merge handle it

### Step 1: Fix pre-commit format failures without local mojo format

When `mojo format` can't run locally (GLIBC incompatibility), read the exact diff from CI logs:

```bash
# Get the workflow run ID from gh pr checks
gh pr checks <PR_NUMBER> 2>&1 | grep "pre-commit"

# Get the exact diff from CI logs
gh api repos/<ORG>/<REPO>/actions/jobs/<JOB_ID>/logs 2>&1 | grep -A 30 "All changes made by hooks"
```

The diff shows exactly what `mojo format` would change. Apply manually with Edit tool.

**Common format patterns needing fixes:**
- Long docstring on one line → closing `"""` must be on its own line
- Long `assert_*` calls → wrap with trailing argument on next line + `)` on line after
- `assert_false(a.is_contiguous(), "msg")` over 88 chars → multiline

### Step 2: Distinguish ADR-009 heap crashes from real test failures

```bash
gh api repos/<ORG>/<REPO>/actions/jobs/<JOB_ID>/logs 2>&1 | grep -E "FAILED|crashed"
```

If output shows `mojo: error: execution crashed`, it is ADR-009 — NOT a real failure. Re-run:

```bash
gh run rerun <RUN_ID> --failed
```

Real failures show actual assertion errors or compilation errors, not "execution crashed".

### Step 3: Rebase DIRTY branches — use temp branch pattern

```bash
git fetch origin <branch>
git checkout -b temp-<branch> origin/<branch>
git rebase origin/main
# ... resolve conflicts ...
git push --force-with-lease origin temp-<branch>:<branch>
git checkout main
git branch -D temp-<branch>
```

**Critical**: Use `--force-with-lease` not `--force`. This aborts if remote has changed.

### Step 4: Conflict resolution strategy for core files

When a central file (e.g. `extensor.mojo`) is modified by many PRs:

**Strategy A — Take theirs** (for cleanup PRs, docs PRs, test-only PRs):
```bash
git checkout --theirs <file>
git add <file>
```

**Strategy B — Keep ours** (when HEAD already has the feature the branch adds):
```bash
git checkout --ours <file>
git add <file>
```

**Strategy C — Manual merge** (when both sides add distinct new content):

Example: HEAD has `__str__`/`__repr__`, branch adds `__hash__[H: Hasher]`:
1. Keep HEAD's `__str__` and `__repr__` implementations intact
2. Add the branch's new methods (`__hash__`, `__int__`, `__float__`, `contiguous()`) after `__repr__`
3. Verify no duplicate method definitions: `grep -n "fn __hash__" extensor.mojo`
4. Confirm zero conflict markers: `grep -c "<<<<<<\|>>>>>>" extensor.mojo`

### Step 5: Handle the Mojo Hashable trait correctly

When resolving `__hash__` conflicts, the CORRECT signature (Mojo v0.26.1+) is:

```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    hasher.write(value1)
    hasher.write(value2)
```

**WRONG** signatures to discard during conflict resolution:
- `fn __hash__(self) -> UInt:` — old API, not `Hashable` trait compliant
- `fn __hash__[H: Hasher](self, inout hasher: H):` — `inout` is deprecated, use `mut`
- `hasher.update(...)` — wrong method name, use `hasher.write(...)`

### Step 6: Struct trait declarations with multiple traits

When two branches both add traits to a struct:
- HEAD: `struct ExTensor(Copyable, Representable, Sized, Stringable)`
- Branch: `struct ExTensor(Copyable, Hashable, Sized)`

**Merge**: combine alphabetically on wrapped lines:
```mojo
struct ExTensor(
    Copyable, Hashable, ImplicitlyCopyable, Movable, Representable, Sized, Stringable
):
```

### Step 7: Handle binary pyc conflicts

For `tests/**/__pycache__/*.pyc` conflicts, always take theirs:
```bash
git status --short | grep "^UU\|^AA" | awk '{print $2}' | while read f; do
  git checkout --theirs "$f" && git add "$f"
done
```

### Step 8: Prune and verify

```bash
git remote prune origin
git worktree prune
git branch  # Should show only main
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo format` locally | Tried to format files to fix pre-commit | GLIBC_2.32/2.33/2.34 not found on dev machine | Read CI logs instead; the diff shows exact changes needed |
| `gh run rerun` on still-running workflow | Tried to rerun ADR-009 crashes before new push | "run cannot be rerun; This workflow is already running" | Pushing a new commit triggers fresh CI automatically — no manual rerun needed |
| Using `--ours` for extensor.mojo when branch adds new methods | Kept HEAD version thinking it already had everything | HEAD was missing `__hash__[H: Hasher]` — the correct trait impl | Always check what new content the branch adds; don't blindly use `--ours` |
| `git checkout --theirs extensor.mojo` for all hash-related PRs | Took branch version to get `__hash__` | Branch had old `fn __hash__(self) -> UInt` or `inout hasher` — both wrong | Manually merge: keep HEAD's `__str__`/`__repr__`, add branch's hash body but fix to correct API |
| Adding `Hashable` to struct without `Representable` | Took branch struct declaration that dropped `Representable` | Struct missing `Representable` breaks `__repr__` trait satisfaction | Always merge trait lists from both sides; check what traits HEAD has that branch dropped |
| Using `gh run rerun` for PR #3224 before checking if new CI started | Tried to rerun the ADR-009 crash run | Got "run cannot be rerun" — new CI was already triggered by our rebase push | Check if new workflow runs are already in progress before rerunning old ones |

## Results & Parameters

### PR volume successfully handled

```
16 DIRTY branches rebased in ~60 minutes
3 format fixes applied manually from CI diffs
1 PR merged automatically (PR #3354, Test Report was pending)
0 real test failures — all were ADR-009 heap crashes
```

### Conflict frequency by file

```
extensor.mojo     — 9 PRs conflicting (highest — core struct)
agents/hierarchy.md — 4 PRs conflicting
CLAUDE.md         — 2 PRs conflicting
test_conv.mojo    — 3 PRs conflicting
test_utility.mojo — 4 PRs conflicting
__pycache__/*.pyc — 1 PR (always take --theirs)
```

### Format fix patterns (copy-paste)

```python
# Docstring closing quote on its own line (>88 chars)
# BEFORE:
"""Create a DataLoader with n_batches * 4 samples, batch_size=4, feature_dim=10."""
# AFTER:
"""Create a DataLoader with n_batches * 4 samples, batch_size=4, feature_dim=10.
"""

# Long assert call wrapping
# BEFORE:
assert_false(a.is_contiguous(), "Column-major tensor should not be contiguous")
# AFTER:
assert_false(
    a.is_contiguous(), "Column-major tensor should not be contiguous"
)
```

### Decision tree for extensor.mojo conflicts

```
Is the conflict in __str__ or __repr__?
├── YES → Keep HEAD (HEAD always has these from earlier merged PR)
└── NO

Is the conflict adding __hash__[H: Hasher](self, mut hasher: H)?
├── YES → Keep/add this version (correct Hashable trait API)
└── NO

Is the conflict adding fn __hash__(self) -> UInt?
├── YES → DISCARD — this is the old wrong API
└── NO

Is the conflict adding __int__, __float__, contiguous()?
└── YES → Add from branch if not already in HEAD
```

### Verification after each rebase

```bash
# Zero conflict markers
grep -c "<<<<<<\|>>>>>>" <file> || echo "0 — clean"

# No duplicate methods
grep -n "fn __hash__\|fn __str__\|fn __repr__" shared/core/extensor.mojo

# Push succeeded
git push --force-with-lease origin temp-<branch>:<branch>
```
