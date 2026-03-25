# Session Notes: Tensor[dtype] Native Ops Inversion

## Date: 2026-03-22

## Context

Following the ExTensor → AnyTensor migration (issue #4998), all core operations had thin
Tensor[dtype] wrappers that round-tripped through AnyTensor: `a.as_any() → op → .as_tensor[dt]()`.
The user requested inverting this so typed implementations are the core.

## Session Flow

1. **Strict repository audit** (repo-analyze-strict) identified 8 major issues:
   - Circular dependency between shared/tensor/ and shared/core/
   - 4,769-line any_tensor.mojo god file (SRP violation)
   - 153 dtype branches + 230 bitcasts remaining in AnyTensor
   - Module trait limitation forcing AnyTensor round-trips
   - No test coverage measurement
   - Missing exports for typed ops

2. **Skills registry search** (`/advise`) found 7 relevant prior skills:
   - `mojo-method-wrapper-circular-import` — local-scope imports pattern
   - `mojo-setitem-lvalue-semantics` — Mojo `[i]=` uses __getitem__ lvalue
   - `mojo-sequential-parametric-containers` — Sequential2/3 pattern
   - `extensor-bfloat16-fix` — two-step BFloat16 cast required

3. **Plan design** with user Q&A:
   - User chose "Native typed ops" (invert pattern, not just add wrappers)
   - User chose "Separate prerequisite PR" for base/ extraction
   - User chose "Separate follow-up" for AnyTensor file splitting
   - User specified: "outer layer is AnyTensor, then dispatch table, then type-specific implementation"

4. **Implementation** — 8 PRs via sub-agents with worktree isolation:
   - PR 1: shared/base/ extraction (mechanical, ~250 lines)
   - PR 2: Arithmetic typed ops (established the pattern, ~1,000 lines)
   - PRs 3-4: Elementwise/activation + matrix/reduction (parallelized)
   - PR 5: Shape/comparison/remaining
   - PR 6: AnyTensor delegation (highest risk)
   - PR 7: Audit minor fixes
   - PR 8: 51 test functions across 6 files

5. **Rebasing** — Multiple rounds of rebasing as PRs merged to main:
   - PR 5033 had import conflict (shared.base vs relative imports) — resolved
   - PR 5034 had __init__.mojo export list conflicts — resolved by keeping all
   - PRs 5032, 5035 rebased cleanly

## Key Decisions

- **3-layer architecture**: AnyTensor API → ordinal dispatch → Tensor[dtype] core
- **Local-scope imports** in any_tensor.mojo to avoid circular deps
- **Sequential PR ordering**: Typed ops first (PRs 2-5), AnyTensor delegation last (PR 6)
- **AnyTensor file NOT split** during this work (separate follow-up)
- **Backward functions left on AnyTensor** (use GradientPair which is AnyTensor-based)
- **Collection ops left on AnyTensor** (concatenate/stack/split use List[AnyTensor])

## Metrics

- 8 PRs total
- ~6,450 lines changed
- 51 new test functions
- 6 PRs merged, 2 open at session end
- PRs 3+4 parallelized successfully (different files, no conflicts)
- 3 rebase conflict resolutions needed

## What Went Well

- Sub-agent with worktree isolation worked perfectly for parallel PRs
- The existing `_broadcast_binary[dtype, op]()` pattern was a perfect foundation
- Establishing the pattern in PR 2 (arithmetic) made PRs 3-5 straightforward
- Local-scope imports cleanly solved the circular dependency problem
- 4-stage agent workflow (implementation in worktree isolation) per user preference

## What Could Improve

- PR 5034 (audit fixes) touched __init__.mojo which conflicted with PR 4's exports
- Background agents don't know about each other's changes — sequential would avoid conflicts
- The 4,769-line any_tensor.mojo should be split before further work (separate follow-up)
