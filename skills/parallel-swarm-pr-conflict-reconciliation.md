---
name: parallel-swarm-pr-conflict-reconciliation
description: "Detect and reconcile overlapping PRs produced by a parallel issue-implementation swarm, where several PRs independently touch the same files so only one squash-merges cleanly and the rest go CONFLICTING. Use when: (1) you launched one-PR-per-issue across a backlog and multiple PRs auto-merge-race on the same paths, (2) a CONFLICTING PR must be rebased onto an already-merged sibling rather than merging main into it, (3) a pure-deletion/extraction PR keeps failing because the retained code is still coupled to the deleted module or the destination port is incomplete, (4) several PRs implement the same end-state and you must pick a canonical superset to land and close the subsumed ones, (5) Edit-tool exact-match fails on conflict markers in files with em-dashes or alignment whitespace."
category: architecture
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [parallel-swarm, pr-conflict, rebase, file-overlap, extraction, superset-pr, force-with-lease, nats]
---

# Reconciling Overlapping PRs from a Parallel Issue-Implementation Swarm

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | When many issues are implemented in parallel (one PR each) and several independently touch the SAME files, only one PR squash-merges cleanly; reconcile the rest that go CONFLICTING |
| **Outcome** | Successful — Odysseus PR#43 rebased onto already-merged PR#32, conflict on `configs/nats/server.conf` + `leaf.conf` resolved keeping main's real TLS, signed, force-pushed, PR went DIRTY/CONFLICTING → MERGEABLE with auto-merge re-armed |
| **Verification** | verified-local — one reconciliation (Odysseus #43) completed end-to-end locally; the Keystone extraction root-cause analysis is verified-by-inspection |

## When to Use

- You launched a swarm of one-PR-per-issue across an issue backlog and several PRs touch the same paths — only the first auto-merges, the rest stall `CONFLICTING`
- A CONFLICTING PR needs reconciling against a sibling that already landed on `main`
- A pure-deletion / "extract X from repo A, it lives in repo B" PR keeps failing or deferring (e.g. an ADR-driven extraction stuck at "Phase 4")
- Multiple PRs implement the same end-state and you must consolidate to one canonical PR
- The Edit tool cannot exact-match conflict markers because the file has em-dashes or alignment whitespace

## Verified Workflow

### Quick Reference

```bash
# 1. Detect file-overlap clusters among the planned/open swarm PRs.
#    Group issues by the files their plans name; flag clusters touching the same paths.
gh pr list --json number,headRefName,files --jq \
  '.[] | {n:.number, files:[.files[].path]}'   # then group by shared path

# 2. Reconcile a CONFLICTING PR by REBASING ITS BRANCH onto current origin/main
#    (NEVER merge main into it — keep history linear).
git fetch origin
REMOTE_SHA=$(git rev-parse origin/<branch>)          # verify nobody pushed since you started
git switch -c <branch>-rebase origin/<branch>
git rebase origin/main
# ... resolve in favor of what already landed on main; preserve this PR's UNIQUE additions ...

# 3. If Edit can't exact-match the markers (em-dashes / alignment whitespace), Python regex hunk-replace:
python3 - <<'PY'
import re
p = "configs/nats/server.conf"
s = open(p).read()
# keep HEAD (main's real change), drop the PR's redundant side:
s = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> [^\n]+\n',
           lambda m: m.group(1) + "\n", s, flags=re.DOTALL)
open(p,"w").write(s)
PY
grep -c '^<<<\|^>>>\|^===' configs/nats/server.conf   # must be 0

# 4. Validate the configs still parse, then sign + force-push-with-lease + re-arm auto-merge.
nats-server -t -c configs/nats/server.conf            # only "cert file not found" = valid syntax
export GPG_TTY=$(tty)
git add -A && git commit -S -m "fix: rebase onto main, keep real TLS, drop redundant scaffold"
git push --force-with-lease origin HEAD:<branch>      # confirm REMOTE_SHA unchanged first
gh pr merge <N> --auto --squash                       # use --squash if rebase-merge disabled
```

### Detailed Steps

1. **Detect overlap BEFORE and AFTER launching.** Group the planned issues by the files their plans name; flag clusters that touch the same paths. At scale, expect clusters — e.g. multiple issues all removing the same module, or one issue adding what another deletes. Serialize or consolidate a cluster instead of letting all its PRs auto-merge-race.

2. **Reconcile a CONFLICTING PR by rebasing its branch onto current `origin/main`** — never merge `main` into the branch (keep history linear). Resolve in favor of the change already landed on `main`. Before force-pushing, verify nobody pushed since you started by comparing the remote branch SHA to the PR head you began from.

   Concrete example (Odysseus PR#43 vs already-merged PR#32 on `configs/nats/server.conf` + `leaf.conf`): #32 had REAL active NATS TLS; #43 had a REDUNDANT commented-out TLS scaffold. Resolution = keep main's real TLS (the HEAD side), drop #43's redundant scaffold, but PRESERVE #43's unique non-conflicting additions (monitoring-auth note, dependabot config, yamllint, gitignore secrets). The PR went from DIRTY/CONFLICTING to MERGEABLE.

3. **When the Edit tool can't exact-match a conflict marker** (files with em-dashes or alignment whitespace defeat literal matching), resolve with a Python regex replace on the `<<<<<<< HEAD ... ======= ... >>>>>>>` hunks instead.

4. **Validate the result parses** before committing. For NATS configs: `nats-server -t -c <file>` — only a "cert file not found" error means the syntax is valid (it parsed far enough to look for the cert).

5. **Sign, force-push-with-lease, re-arm auto-merge.** `export GPG_TTY=$(tty)`, commit `-S`, `git push --force-with-lease` (after re-confirming the remote SHA), then re-arm `gh pr merge <N> --auto` with the repo's allowed method (`--squash` if rebase-merge is disabled).

### Extraction ≠ Deletion (root-cause for stuck "delete X, it lives in repo B" PRs)

A pure-deletion PR keeps failing or deferring because of one or both of:

- **(a) The retained code in the SOURCE repo is still COUPLED to the to-be-deleted code.** Example: Keystone's transport `MessageBus` held a `shared_ptr<agents::AgentCore>` via `i_agent_registry.hpp` — deleting the agents module breaks the transport that must remain.
- **(b) The DESTINATION port is incomplete** — the code was never actually moved into repo B, so deletion would lose it.

Fix order:

- **Part A — decouple** the retained code via a NEW interface that owns nothing from the deleted module (e.g. a transport-only registry interface).
- **Part B — verify/port** the code into the destination repo so nothing is lost.
- **Part C — only THEN delete** from the source, ordering deletions: build-refs → test-registrations → example/bench refs → source files.

### Consolidating PRs that implement the same end-state

Pick the canonical SUPERSET PR to land. Close the subsumed ones with explanatory comments. Salvage any UNIQUE bits (e.g. one PR also carried audit fixes) into a follow-up PR. CLOSE PRs that CONTRADICT the agreed end-state (e.g. ones that re-add what should be removed) — only file follow-ups if real value would otherwise be lost.

### Cleaning up the reconciliation worktree

`git worktree remove --force` is blocked by a safety net while work is uncommitted. Commit and push everything first, then plain (non-force) `git worktree remove <path>` succeeds; finish with `git worktree prune`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Race all overlapping auto-merge PRs | Let every swarm PR keep `--auto` and merge whenever CI passed | Only the first PR in a file-overlap cluster merged; the rest went CONFLICTING and stalled | Detect file-overlap clusters before/after launch and serialize or consolidate them — don't let a cluster race |
| Pure-deletion without decoupling | Opened an extraction PR that just deleted module X from the source repo | Retained code still held `shared_ptr<agents::AgentCore>` via `i_agent_registry.hpp`; branch didn't build, "Phase 4" perpetually deferred | Decouple the retained code via a transport-only interface (Part A), and verify the destination port (Part B), BEFORE deleting (Part C). Extraction ≠ deletion |
| Exact-string Edit on conflict markers | Used the Edit tool to replace `<<<<<<< HEAD ... >>>>>>>` hunks in `configs/nats/*.conf` | Files contained em-dashes and alignment whitespace, so literal matching never matched | Use a Python regex hunk-replace on the conflict markers instead of exact-string Edit |
| Merge main into the conflicting branch | Considered `git merge origin/main` to clear the conflict | Pollutes history with a merge commit; squash-merge then bundles unrelated diff | Rebase the branch onto `origin/main` (linear history), resolve toward what landed, force-push-with-lease |
| `git worktree remove --force` to clean up | Tried to force-remove the reconciliation worktree mid-work | Blocked by a worktree safety net because work was uncommitted | Commit/push everything first, then plain (non-force) `git worktree remove` works; then `git worktree prune` |

## Results & Parameters

### Session outcome (2026-05-29)

| PR | Conflict | Resolution | Before → After |
|----|----------|------------|----------------|
| Odysseus #43 (vs merged #32) | `configs/nats/server.conf` + `leaf.conf`: #32 real active TLS vs #43 redundant commented TLS scaffold | Keep main's real TLS (HEAD), drop #43 scaffold, preserve #43's unique adds (monitoring-auth note, dependabot, yamllint, gitignore secrets) | DIRTY/CONFLICTING → MERGEABLE, auto-merge re-armed |
| Keystone agents extraction | Pure-deletion deferred at "Phase 4" | Decouple transport via new interface (A) → verify/port to repo B (B) → delete source in order build-refs → test-regs → example/bench → sources (C) | verified-by-inspection (root-cause identified) |

### Key parameters

```yaml
reconcile_strategy: rebase onto origin/main   # never merge main into the branch
resolution_bias: keep what already landed on main (HEAD side); preserve PR's unique non-conflicting adds
push_flag: --force-with-lease                  # re-verify remote SHA == PR head you started from
conflict_marker_resolution: python regex hunk-replace when Edit can't exact-match (em-dashes/whitespace)
nats_validate: nats-server -t -c <file>        # only "cert file not found" == valid syntax
sign: git commit -S  (export GPG_TTY=$(tty))
auto_merge_method: --squash if rebase-merge disabled in repo settings
extraction_order: build-refs -> test-registrations -> example/bench refs -> source files
worktree_cleanup: commit+push first, then plain (non-force) git worktree remove, then prune
```

### Overlap-detection heuristic

```
For each planned/open swarm PR:
  record the set of file paths its plan/PR touches.
Group PRs that share ≥1 path into a cluster.
For each cluster of size > 1:
  - one PR will squash-merge cleanly; the rest will go CONFLICTING.
  - decide: serialize (rebase each onto the prior winner) OR
            consolidate into a canonical superset PR and close the others.
Watch specifically for:
  - multiple issues removing the SAME module
  - one issue ADDING what another DELETES (contradictory end-states → close the contradicting one)
```
