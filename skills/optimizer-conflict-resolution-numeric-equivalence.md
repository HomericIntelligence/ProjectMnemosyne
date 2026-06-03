---
name: optimizer-conflict-resolution-numeric-equivalence
description: "Resolve merge-conflicted numerical/optimizer PRs (Mojo, but generalizes) where main independently merged its own version of a shared module after the branch was cut — WITHOUT silently merging wrong math. Adapt dependent call-sites to main's changed API while PROVING and documenting numeric equivalence, test the math, and DEFER provably-broken algorithms instead of merging stubs. Use when: (1) a feature PR adding an optimizer/numerical kernel is DIRTY because main merged its own version of a shared module (e.g. muon.mojo) after the branch was cut → add/add conflict; (2) the conflicted PR imports a function whose signature CHANGED on main (e.g. muon_step(momentum=...) vs muon_step(momentum_beta=...)) so dropping the PR copy breaks dependent code; (3) a PR's tests assert numeric thresholds that encoded its now-superseded implementation's hyperparameter defaults; (4) you must decide whether a conflicted optimizer is salvageable vs provably broken (defer it); (5) resolving a multi-optimizer PR where one optimizer is sound and another is broken — ship the sound one, defer the broken one."
category: architecture
date: 2026-06-02
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - optimizer
  - conflict-resolution
  - numeric-equivalence
  - mojo
  - merge-conflict
  - muon
  - defer-broken-math
---

# Optimizer Conflict Resolution: Numeric Equivalence Over Silent Merges

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Objective** | Resolve add/add merge conflicts on numerical/optimizer PRs where `main` independently merged its own version of a shared module after the branch was cut — adapting dependent call-sites to main's changed API while PROVING numeric equivalence, and DEFERRING provably-broken algorithms instead of merging wrong math |
| **Outcome** | Successful — NorMuon's 8 tests passed after adapting to main's `muon_step` API and PR pushed (ProjectOdyssey #5485, merged-pending); Lion shipped with 6 tests passing (#5487); Shampoo correctly deferred to follow-up issue #5491 |
| **Verification** | verified-ci |

When `main` merges its own copy of a shared numerical module (e.g. `muon.mojo`) after your feature branch was cut, you get an `add/add` conflict on that file. The naive fix — drop the PR's copy, keep main's — *compiles* but can be silently WRONG, because main's version of the shared function usually has a different signature (renamed kwargs, changed defaults, added params) and possibly a different numerical recipe. The correct method: classify each conflicted file (DUPLICATE vs NEW), adapt the dependent call-site to main's API while reasoning about and DOCUMENTING numeric equivalence, test the actual math, fix wrong-target assertions with derived values (never by loosening), and DEFER any optimizer whose core math is a broken stub.

Core principle: **compiling ≠ correct.** Every conflict resolution that touches numerics must answer "is the new call numerically equivalent to what the PR intended?" in a code comment before merge.

## When to Use

- A feature PR adding an optimizer/numerical-kernel is DIRTY because `main` merged its own version of a shared module (e.g. `muon.mojo`) after the branch was cut → `add/add` conflict on that file.
- The conflicted PR imports a function whose signature CHANGED on main (e.g. `muon_step(momentum=...)` on the PR vs `muon_step(momentum_beta=...)` on main) — dropping the PR's copy in favor of main's breaks the dependent code.
- A PR's tests assert numeric outputs/thresholds that encoded the PR's now-superseded implementation's hyperparameter defaults.
- You must decide whether a conflicted optimizer is salvageable vs provably broken (defer it).
- Resolving a multi-optimizer PR where one optimizer is sound and another is broken — ship the sound one, defer the broken one.

## Verified Workflow

### Quick Reference

```bash
# 1. Classify each conflicted file: DUPLICATE (main already has it) vs NEW (PR-only).
#    Diff the PR's file against origin/main; if main has an equivalent, DROP the PR's duplicate.
diff <(git show origin/main:src/.../muon.mojo) <(git show origin/<branch>:src/.../muon.mojo)

# 2. Find the API contract: compare the shared function's signature on the PR vs on main.
git show origin/main:src/.../muon.mojo      | grep -n "fn muon_step"
git show origin/<branch>:src/.../muon.mojo  | grep -n "fn muon_step"

# 3. Adapt the dependent call-site to main's API, PRESERVING intended numerics.
#    Example (NorMuon): main's Muon applies a single GLOBAL scale that NorMuon's
#    per-axis L2-normalization divides out → only DIRECTION matters, so this is equivalent:
#        muon_step(momentum_beta=momentum, weight_decay=0.0, nesterov=False)
#    Put the equivalence justification in a CODE COMMENT.

# 4. TEST THE MATH (register new test files in the CI matrix if the repo enforces it).
pixi run mojo --Werror -debug-level=line-tables -I src -I . \
  tests/projectodyssey/training/optimizers/test_normuon.mojo

# 5. Wrong-target assertion? Fix the ASSERTION with a DERIVED value, never by loosening.
#    Lion moves exactly `lr` per step: floor after N from 1.0 is max(0, 1 - N*lr).
#    lr=0.01, N=50 → 0.5; a `< 0.5` assert is unreachable → `< 0.55` (still proves descent).

# 6. DEFER provably-broken algorithms — remove from PR, file a follow-up issue, ship the rest.
git rm src/.../shampoo.mojo tests/.../test_shampoo.mojo
# ... note the scope reduction in a PR comment ...

# 7. Sign, force-with-lease push (auto-merge stays armed), clean up the worktree.
git commit -S -m "fix(optimizers): resolve muon.mojo conflict, adapt NorMuon to main API"
git push --force-with-lease origin HEAD:<branch>
```

### Detailed Steps

1. **Classify each conflicted file as DUPLICATE vs NEW.** Diff the PR's file against `origin/main` (`diff <(git show origin/main:path) <(git show origin/<branch>:path)`). If main already has an independently-merged equivalent, DROP the PR's duplicate (keep main's — it's usually the canonical/standard implementation) and keep only the PR's genuinely-new files. Reconcile `__init__`/exports to expose BOTH.
2. **Find the API contract the PR was written against.** Read the PR's version of the shared function's signature AND main's current signature. Identify every keyword/default that differs (name changes like `momentum`→`momentum_beta`, default changes like weight_decay 0.0 vs 0.01, added params like `nesterov`).
3. **Adapt the dependent call-site to main's API while PRESERVING THE INTENDED NUMERICS — and document the equivalence.** Don't just rename kwargs to compile. Reason about whether the new call is numerically equivalent to what the PR intended. WORKED EXAMPLE: NorMuon calls `muon_step(...)` then L2-normalizes the resulting delta per axis. With `lr=1.0, weight_decay=0.0`, main's Muon returns `p − scale·NS(β·m+grad)` where `scale` is a single GLOBAL scalar; NorMuon's per-axis normalization DIVIDES OUT that global scale, so NorMuon's update depends only on the DIRECTION of the orthogonalized momentum. Therefore mapping `momentum=`→`momentum_beta=`, forcing `weight_decay=0.0`, and choosing `nesterov=False` (to match the PR's plain heavy-ball momentum, not main's default look-ahead) preserves NorMuon's invariant. Two remaining recipe differences (heavy-ball `m=β·m+g` vs EMA `m=β·m+(1−β)·g`; basic cubic vs Jordan-2024 quintic Newton-Schulz) are also global-scalar / superior-orthogonalizer differences that the per-axis normalization absorbs. Put this justification in a CODE COMMENT.
4. **TEST THE MATH.** Run the PR's own numeric tests against the adapted code (`pixi run mojo --Werror -debug-level=line-tables -I src -I . tests/.../test_<name>.mojo`). Register new test files in the CI matrix if the repo enforces it (e.g. `.github/workflows/comprehensive-tests.yml` + a `validate-test-coverage` pre-commit hook). Fix current-language syntax drift in the test files (Mojo examples: `except Error as e:`→`except e:`, `e.__str__()`→`String(e)`, `ones_like(...)*x`→`full([...], x, dtype)`, bind unused results to `_` for `--Werror`, `var x = List[Int](1,2)`→`var x: List[Int] = [1,2]`).
5. **If a test asserts an unreachable target, fix the ASSERTION with justification, not by loosening.** Lion's signed update moves exactly `lr` per step, so the floor after N steps from 1.0 is `max(0, 1−N·lr)` (e.g. lr=0.01, N=50 → 0.5); a `< 0.5` assert is unreachable → change to `< 0.55` (still proves genuine descent). Never just relax a bound to make a wrong test pass.
6. **DEFER provably-broken algorithms — do not merge wrong math.** If an optimizer's defining case crashes or its core math is a stub, REMOVE it from the PR, file a follow-up issue, and ship the rest. WORKED EXAMPLE (Shampoo): its `shampoo_step` kept element-wise (gradient-shaped) EMA state but the API/docs/tests treat L/R as (n,n)/(m,m) matrices — the non-square case (`params [2,3], L [2,2], R [3,3]`) raises "Shapes are not broadcast-compatible"; its Newton-Schulz helper was an admitted damped-identity no-op; descent tests asserted unreachable targets. Correct Shampoo needs real two-sided matrix preconditioning = a reimplementation, not a conflict fix → deleted Shampoo from the PR, filed a follow-up issue, shipped Lion only. (This reduces PR scope vs its title — note it in a PR comment.)
7. **Signed commit, `git push --force-with-lease origin HEAD:<branch>`** (auto-merge stays armed). Clean up the worktree.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Dropped the PR's duplicate module and kept main's — "done" | Broke the dependent code because main's API differs (kwarg renamed `momentum`→`momentum_beta`, default and params changed); the call-site no longer compiled / called the wrong contract | Check the shared-function SIGNATURE before swapping implementations; you must adapt the call-site, not just delete the duplicate. |
| 2 | Renamed kwargs until it compiled | Compiles but the numerics could be silently wrong — different recipe (heavy-ball vs EMA momentum, look-ahead nesterov default, cubic vs quintic Newton-Schulz) | Compiling ≠ correct. Reason about equivalence (what cancels: global scalars under per-axis normalization, etc.) and DOCUMENT it in a code comment before merging. |
| 3 | Made the failing numeric test pass by loosening the bound | Hides a real defect — the test no longer guards anything meaningful | Fix the assertion only with a DERIVED/justified value (Lion floor = max(0, 1−N·lr) → `< 0.55`); never relax a bound just to make a wrong test green. |
| 4 | Tried to resolve Shampoo's conflict and merge it | Its core math was a broken stub: no-op (damped-identity) Newton-Schulz preconditioner and a non-square crash ("Shapes are not broadcast-compatible") in its defining case | DEFER provably-broken algorithms — remove from the PR, file a follow-up issue, ship the sound optimizers; don't merge wrong math to satisfy a PR title. |

## Results & Parameters

**Test command:**

```bash
pixi run mojo --Werror -debug-level=line-tables -I src -I . \
  tests/projectodyssey/training/optimizers/test_<name>.mojo
```

**Per-optimizer outcomes:**

| Optimizer | Resolution | Result |
|-----------|-----------|--------|
| NorMuon | Adapted call to `muon_step(momentum_beta=momentum, weight_decay=0.0, nesterov=False)`; per-axis L2-normalization divides out main's global scale → equivalent | 8 tests passed |
| Lion | Fixed one unreachable descent assert (`< 0.5` → `< 0.55`, derived from `max(0, 1−N·lr)` with lr=0.01, N=50) | 6 tests passed; shipped |
| Shampoo | Provably broken (no-op preconditioner + non-square crash) → removed from PR, follow-up issue filed | Deferred to issue #5491 |

**Key numeric-equivalence facts (NorMuon):**

- main's Muon update with `lr=1.0, weight_decay=0.0`: `p − scale·NS(β·m+grad)`, where `scale` is a single GLOBAL scalar.
- NorMuon L2-normalizes the resulting delta PER AXIS → the global `scale` cancels → the update depends only on the DIRECTION of the orthogonalized momentum.
- Therefore the recipe differences absorbed by per-axis normalization: heavy-ball `m=β·m+g` vs EMA `m=β·m+(1−β)·g` (global-scalar difference), and basic cubic vs Jordan-2024 quintic Newton-Schulz (superior orthogonalizer, same direction).
- `nesterov=False` chosen to match the PR's plain heavy-ball momentum rather than main's default look-ahead.

**Mojo current-language syntax drift fixed in test files:** `except Error as e:`→`except e:`; `e.__str__()`→`String(e)`; `ones_like(...)*x`→`full([...], x, dtype)`; bind unused results to `_` for `--Werror`; `var x = List[Int](1,2)`→`var x: List[Int] = [1,2]`.

## Verified On

ProjectOdyssey PRs #5485 (NorMuon, merged-pending), #5487 (Lion shipped / Shampoo deferred → issue #5491). Session: ecosystem drive-prs-green drain, 2026-06-02.
