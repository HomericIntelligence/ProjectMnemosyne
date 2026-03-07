---
name: mass-pr-ci-fix
description: "Fix CI failures across many open PRs systematically. Use when: many PRs share a common CI failure, pre-commit mojo format fails after codebase changes, Mojo trait API breaks compilation across branches."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Purpose** | Systematically fix CI failures across many open PRs |
| **Primary trigger** | 40+ PRs all failing the same required check |
| **Key insight** | Fix the root blocker on main first, then rebase all PRs |
| **Time saved** | Hours of individual PR debugging |

## When to Use

- Many PRs all failing `pre-commit` with the same file reformatted
- A Mojo API change (trait signature, keyword rename) breaks compilation
- ADR-009 heap crashes appearing across many CI runs
- Need to mass-rebase after a fix lands on main

## Verified Workflow

### Phase 1: Identify Root Blocker

```bash
# Check what pre-commit reformats on any failing PR
gh run view <run_id> --log-failed 2>&1 | grep "reformatted"

# Check which file has the format issue
# Then check what's over 88 chars (code limit) or 120 chars (markdown limit)
awk 'length > 88 {print NR": "length": "$0}' <file> | head -20
```

### Phase 2: Fix Root on Main (via PR)

1. Create branch from main, fix the formatting/API issue
2. Push, create PR, enable auto-merge: `gh pr merge --auto --rebase`
3. Wait for it to merge

### Phase 3: Mass Rebase All PRs

```bash
# Get all open PR branch names
gh pr list --state open --json headRefName --jq '.[].headRefName' > branches.txt

# For each branch:
for branch in $(cat branches.txt); do
  git fetch origin $branch
  git checkout -b temp-$branch origin/$branch
  git rebase origin/main
  git push --force-with-lease origin temp-$branch:$branch
  git checkout -
  git branch -D temp-$branch
done
```

If rebase hits conflicts:
```bash
# For files where branch version should win:
git checkout --theirs <conflicted-file>
git add <conflicted-file>
GIT_EDITOR=true git rebase --continue

# For files where main version should win (e.g. format fixes):
git checkout --ours <conflicted-file>
git add <conflicted-file>
GIT_EDITOR=true git rebase --continue
```

### Phase 4: Fix Compilation Errors (Mojo Trait API)

**Mojo `Hashable` trait (v0.26.1+)** requires:
```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    hasher.write(value1)
    hasher.write(value2)
```

NOT the old API: `fn __hash__(self) -> UInt`
NOT old keyword: `inout hasher` (use `mut hasher`)
NOT old method: `hasher.update()` (use `hasher.write()`)

Error message that signals this:
```
error: 'MyStruct' does not implement all requirements for 'Hashable'
note: no '__hash__' candidates have type 'fn[H: Hasher](self: ..., mut hasher: H) -> None'
```

### Phase 5: Handle ADR-009 Heap Crashes

ADR-009 = intermittent `mojo: error: execution crashed` in CI.
These are NOT real test failures. Fix: rerun failed jobs.

```bash
# Rerun failed jobs on all open PRs
gh pr list --state open --limit 60 --json number --jq '.[].number' | while read pr; do
  run_id=$(gh pr checks $pr 2>&1 | grep "Test Report" | grep "fail" | grep -oP 'runs/\K[0-9]+' | head -1)
  if [ -n "$run_id" ]; then
    gh run rerun $run_id --failed 2>&1 | tail -1
  fi
done
```

### Phase 6: Fix Remaining Format Violations

Common mojo format issues (line limit = 88 chars for code):

**1. Long struct trait declaration:**
```mojo
# Before (>88 chars):
struct Foo(Copyable, Movable, Sized, Stringable, Representable, Hashable):

# After (mojo format wraps to):
struct Foo(
    Copyable, Movable, Sized, Stringable, Representable, Hashable
):
```

**2. Extra blank lines between top-level definitions:**
```mojo
# Before (3 blank lines - wrong):
fn foo():
    pass



fn bar():

# After (2 blank lines - correct):
fn foo():
    pass


fn bar():
```

**3. Old keyword renamed:**
- `inout` → `mut` (mojo format auto-converts)

**4. Long markdown lines** (limit = 120 chars):
- Wrap bullet points and table cells at natural boundaries

### Phase 7: Fix Test Coverage Validation

If `validate-test-coverage` pre-commit hook fails after CI matrix consolidation:
- The hook checks every `.mojo` test file is listed in some CI group pattern
- Add missing files to appropriate groups in `comprehensive-tests.yml`
- Or add a catch-all group with `test_*.mojo` pattern

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run mojo format locally | `pixi run mojo format <file>` | GLIBC version mismatch on local machine | Can't run mojo format locally; use CI logs to identify what changed |
| `git checkout origin/$branch -b temp` | Single command to create tracking branch | Git syntax error: can't update paths and switch simultaneously | Use `git fetch origin $branch && git checkout -b temp origin/$branch` |
| Using `inout` keyword in `__hash__` | `fn __hash__[H: Hasher](self, inout hasher: H)` | Mojo v0.26.1+ renamed `inout` to `mut`; causes syntax error | Always use `mut` for mutable parameters |
| Using `hasher.update()` | Called `.update()` on Hasher | Mojo's Hasher trait uses `.write()` not `.update()` | Check Mojo stdlib trait method names in CI error messages |
| Return-based `__hash__` | `fn __hash__(self) -> UInt` | New Mojo Hashable trait is Hasher-protocol based, not return-value based | Read the exact error: "no candidates have type 'fn[H: Hasher](self, mut hasher: H) -> None'" |
| GraphQL PR status query | `gh pr list --json statusCheckRollup` | 504 Gateway Timeout under load from 40+ simultaneous CI runs | Fall back to per-PR `gh pr checks <number>` calls |

## Results & Parameters

### Key Numbers (Session: 2026-03-06/07)

- PRs fixed: 40+ open PRs → cascaded to ~20 auto-merged
- Root fix: 3 long lines in `layer_testers.mojo` (ternary expressions >88 chars)
- Compilation errors: `__hash__` signature wrong in 3 PRs (#3232, #3372, #3373)
- ADR-009 reruns: 38 runs restarted with `--failed`

### Identifying Root Blocker Pattern

```bash
# Find which file fails format on any PR
gh run view <run_id> --log-failed 2>&1 | grep "reformatted"

# Check the file's long lines
awk 'length > 88 {print NR": "length}' <file> | head -20

# For markdown files (limit is 120):
awk 'length > 120 {print NR": "length}' <file> | head -20
```

### Mojo format long ternary fix pattern

```mojo
# Before (exceeds 88 chars):
var epsilon = GRADIENT_CHECK_EPSILON_FLOAT32 if dtype == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER

# After (mojo format output):
var epsilon = (
    GRADIENT_CHECK_EPSILON_FLOAT32 if dtype
    == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER
)
```

### Required check names (branch protection)

```
build-docs, build-mojo, build-python, build-validation,
pre-commit, security-report, Test Report,
Mojo Package Compilation, Code Quality Analysis, secret-scan
```
