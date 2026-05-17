---
name: parallel-remediation-file-disjointness-check
description: "Before dispatching new parallel remediation work atop N in-flight PRs, verify the proposed cluster's files are DISJOINT from every open PR's diff. File-overlap is the only reliable proxy for merge-conflict risk. Use when: (1) >=5 PRs already in flight with auto-merge waiting on green CI, (2) about to dispatch a new swarm wave or remediation cluster mid-cascade, (3) deciding whether work can safely run in parallel or must queue, (4) prior dispatch produced rebase chaos from same-file collisions."
category: tooling
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - parallel-pr
  - merge-cascade
  - disjoint-files
  - remediation-phasing
  - swarm-conflict-avoidance
  - in-flight-prs
  - dispatch-gate
  - file-overlap
---

# Parallel Remediation — File Disjointness Check Against In-Flight PRs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-17 |
| **Objective** | Codify a pre-dispatch gate that prevents parallel remediation work from colliding with PRs already in the merge cascade |
| **Outcome** | On ProjectAgamemnon 2026-05-17, Phase F-1 cluster (OpenAPI + Python SDK + `routes.cpp` enum constants) was selected against 14 in-flight PRs after file-level disjointness verification — zero overlap confirmed before dispatch |
| **Verification** | verified-local — disjointness check verified manually; PR dispatch not yet observed end-to-end through merge |
| **History** | n/a (initial version) |

## When to Use

- About to dispatch a new remediation cluster while >=5 PRs sit open in the cascade
- Auto-merge is enabled on in-flight PRs and they are waiting on CI green
- Choosing between several candidate remediation clusters and need a tiebreaker
- Prior parallel attempt on the same file produced a rebase storm (lesson: same-file = serialize)
- Companion check after applying the runner-pool concurrency cap (`github-actions-runner-pool-saturation-swarm-concurrency-cap`)

## Verified Workflow

### Quick Reference

```bash
# 1. Enumerate files touched by every in-flight PR (yours)
gh pr list --state open --author "@me" \
  --json number,files \
  --jq '.[] | "PR#\(.number):" + (.files | map(.path) | join(","))'

# 2. List the files the proposed remediation cluster will touch
#    (gather from the cluster plan — OpenAPI spec, client SDK, src/ files, etc.)

# 3. Compute overlap (manual diff of the two file sets)
#    - file-level overlap  -> DO NOT dispatch in parallel; queue after cascade
#    - any src/ overlap    -> queue (line-level overlap is still risky)
#    - zero overlap        -> SAFE to dispatch in parallel
```

### Detailed Steps

1. **Snapshot in-flight PR file sets.** Run the `gh pr list` query above and
   save the per-PR file lists. Treat this snapshot as the constraint set.
2. **Enumerate proposed cluster files.** List every file the new cluster
   plans to touch — including generated artifacts, lockfiles, and any
   workflow YAML.
3. **Compute file-level overlap.** Any shared path means "queue, do not
   dispatch." Do not attempt to argue that line ranges differ — rebases
   still serialize on file granularity.
4. **Apply category heuristics** (below) to flag borderline cases as if
   they were overlap.
5. **Re-check before dispatch.** PRs merge fast under auto-merge; rerun the
   `gh pr list` query immediately before launching the swarm so the
   constraint set reflects current state.
6. **Apply concurrency cap.** Even with zero overlap, the runner-pool cap
   from `github-actions-runner-pool-saturation-swarm-concurrency-cap`
   (~5-7 concurrent PRs) still applies.

### Category Heuristics

| File class | Default risk | Action |
|------------|--------------|--------|
| `src/**`, core C++/Mojo source | High | Treat as overlap-prone; serialize if any in-flight PR touches `src/` |
| `.github/workflows/*.yml` | Very high during CI-fix cascades | Every CI fix touches these — always queue |
| `docs/**`, OpenAPI specs (`docs/api/openapi.yaml`) | Low | Usually safe to parallelize; in-flight cascades rarely touch docs |
| Client SDK packages (`clients/python/`, `clients/ts/`) | Low | Usually safe; SDK regen is typically its own PR family |
| Lockfiles (`pixi.lock`, `Cargo.lock`, `package-lock.json`) | High | Serialize — auto-regen produces churn that conflicts trivially |
| Enum / constant additions (single-line, append-only) | Medium | Safer than mid-file edits, but still queue if any other PR touches the file |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Dispatched `routes.cpp` PUT/PATCH dedup fix in parallel with an in-flight `routes.cpp` PATCH-handler addition (same session, earlier) | Both PRs edited overlapping regions of `routes.cpp`; second PR required two manual rebases before merge | Same-file = serialize, even if the planned line ranges look disjoint |
| 2 | Used "different functions in same file" as a justification to parallelize | Auto-merge rebases serialize at file granularity, not function granularity; second PR still hit conflict markers | File-level disjointness is the only reliable signal |
| 3 | Skipped the `gh pr list` re-check and dispatched off a 30-min-old snapshot | Two in-flight PRs had merged in the interim and a new wave member now touched a file the new cluster claimed | Re-snapshot in-flight PRs IMMEDIATELY before dispatch |

## Results & Parameters

### Verified disjointness check (ProjectAgamemnon Phase F-1, 2026-05-17)

**In-flight PR file set (14 PRs):** primarily `src/routes.cpp`, `src/handlers/*.cpp`,
`include/agamemnon/*.hpp`, `tests/cpp/**`, `.github/workflows/ci.yml`,
`scripts/*.sh`, `pixi.lock`.

**Proposed Phase F-1 cluster files:**

```text
docs/api/openapi.yaml
docs/api/README.md
clients/python/src/agamemnon_client/client.py
clients/python/src/agamemnon_client/models.py
clients/python/src/agamemnon_client/config.py
src/routes.cpp:93-95          # enum constants, append-only
```

**Overlap analysis:**

| Cluster file | In-flight overlap? | Decision |
|--------------|--------------------|----------|
| `docs/api/openapi.yaml` | None | Safe |
| `docs/api/README.md` | None | Safe |
| `clients/python/src/agamemnon_client/*.py` | None (no in-flight PR touches `clients/python/`) | Safe |
| `src/routes.cpp` (lines 93-95) | **YES — 4 in-flight PRs touch `routes.cpp`** | **Carve out** — drop the enum-constant edit from this cluster; queue it after the routes.cpp cascade drains |

**Outcome:** Cluster trimmed to docs + Python SDK only. Truly disjoint
against all 14 in-flight PRs. Safe to dispatch under the
~5-7-concurrent-PR cap.

### Companion rules

- **Runner-pool cap:** `github-actions-runner-pool-saturation-swarm-concurrency-cap` — even disjoint, don't exceed ~5-7 concurrent PRs.
- **Drain-first on resume:** `myrmidon-swarm-resume-drain-in-flight-prs-first` — at session start, drain to 0 before any new dispatch (this skill applies mid-cascade, not at resume).
- **Worktree isolation:** `parallel-pr-worktree-workflow` — once disjointness is verified, each parallel agent still needs its own worktree.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | 2026-05-17 audit-remediation Phase F-1 dispatch decision | Cluster selected after disjointness check against 14 in-flight PRs |
