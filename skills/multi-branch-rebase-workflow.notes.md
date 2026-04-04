# Session Notes: Multi-Branch Rebase Workflow

## Date: 2026-03-19

## Context

8 branches in ProjectOdyssey failed auto-rebase onto main (at a1f33d79). Each had been analyzed
by a sub-agent that read the associated GitHub issue, identified conflicts, and determined the
correct semantic resolution. 3 branches were already rebased by prior sub-agents.

## Branches Processed

1. `3680-auto-impl` (Issue #3680) - ValidationLoop accuracy fix - EMPTY (same fix on main)
2. `3742-sequential-mlp` (Issue #3742) - SimpleMLP2 variant - 1 docstring conflict
3. `3751-auto-impl` (Issue #3751) - API table in shared/__init__.mojo - EMPTY (main superset)
4. `4062-hash-integer-dtype` (Issue #4062) - Hash tests - Already done by sub-agent
5. `4076-auto-impl` (Issue #4076) - Setitem view - Already done by sub-agent
6. `4086-auto-impl` (Issue #4086) - Shape ops non-contiguous - Already done by sub-agent
7. `4513-auto-impl` (Issue #4513) - Circular type resolution - 26 conflicts, complex merge
8. `fix/20-dropout-backward` (Issue #20) - Dropout backward - 1 skip + 1 clean apply

## Key Decisions

### Why --force-with-lease over --force
Safety Net hook (cc-safety-net.js) blocks `git push --force` as destructive.
`--force-with-lease` is safer: it fails if remote has been updated since last fetch,
preventing accidental overwrites of other people's work.

### Why delegate 26-conflict merge to sub-agent
The extensor.mojo file had 26 conflict regions spanning ~600 lines. Each needed different
resolution strategy (keep branch vs keep main vs keep both). Delegating to a sub-agent:
- Keeps main context window clean
- Agent can focus entirely on one file
- Explicit resolution rules provided upfront prevent drift

### Why skip PRs for empty branches
After rebase, `3680-auto-impl` and `3751-auto-impl` had 0 commits ahead of main.
Their changes were already merged. Creating empty PRs would be noise.

## PRs Created

- #4982: 3742-sequential-mlp
- #4983: 4062-hash-integer-dtype
- #4984: 4076-auto-impl
- #4985: 4086-auto-impl
- #4986: 4513-auto-impl
- #4987: fix/20-dropout-backward

All with auto-merge (rebase strategy) enabled.

## Timing

- Simple rebases (4 branches): ~2 minutes each
- Complex rebase (4513, 26 conflicts): ~6 minutes via sub-agent
- PR creation (6 PRs): ~1 minute total (parallel)

---

## Amendment: 2026-04-03 -- Prevention via origin/main branching

### Context

During a governance compliance session in Odysseus meta-repo, 5 submodule PRs were created
by agents branching from the current submodule HEAD (detached at old pins). All 5 PRs
came back CONFLICTING because main had moved forward with governance files, CI fixes,
and coverage improvements since the pins.

### Root Cause

Submodule checkouts in Odysseus are pinned to specific SHAs. When an agent `cd`s into
a submodule and runs `git checkout -b chore/my-fix`, the branch starts from the pinned
SHA -- not from current main. This is a systemic issue because:

1. Meta-repos always have submodules pinned behind main
2. Agents naturally branch from HEAD, which is the pinned SHA
3. The further behind the pin, the more conflicts on PR creation

### Fix Applied

Added **Step 0: Prevention** to the skill as the first verified workflow step.
The rule is simple and unconditional:

```bash
git fetch origin main
git checkout -b my-feature-branch origin/main
```

This is especially critical for submodules where HEAD is almost never on main.

### Failure Rate Observed

- 5/5 PRs created from stale HEADs had merge conflicts
- All 5 required a rebase wave to fix
- 0/5 would have conflicted if branched from origin/main initially

### Version Bump

v1.0.0 -> v2.0.0 (added prevention as a core workflow step, not just a tip)