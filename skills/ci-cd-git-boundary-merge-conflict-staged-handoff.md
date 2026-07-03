---
name: ci-cd-git-boundary-merge-conflict-staged-handoff
description: "Resolve a PR merge conflict when the agent may not commit (orchestrator owns signed commits). Use when: (1) an independent PR reviewer returns CONFLICT / mergeStateStatus=DIRTY inside an implement-review loop where the implementing agent operates under a MANDATORY git boundary (may edit files and run tests, must NOT run git commit or git push — the orchestrator creates the signed, DCO signed-off commit with `git commit -S -s` after the turn), (2) the reviewer's literal instruction is 'rebase onto origin/main and commit the resolution (signed)' but a literal rebase is impossible under the boundary (rebase creates commits or strands REBASE_HEAD state that a plain `git commit -S -s` cannot finish), (3) sibling PRs of a convention/ecosystem rollout wave race on the same shared doc lines (README/CLAUDE.md CI bullet lists, branch-protection required-check tables) and one lands on main first. Mechanism: `git merge origin/main --no-commit --no-ff`, resolve keeping BOTH sides, stage everything, re-run gates on the merged tree, and end the turn with MERGE_HEAD still set — the orchestrator's plain `git commit -S -s` then automatically finalizes the signed merge-resolution commit."
category: ci-cd
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - merge-conflict
  - git-boundary
  - orchestrator-handoff
  - merge-no-commit
  - MERGE_HEAD
  - signed-commit
  - dco
  - rebase-alternative
  - review-loop
  - parallel-pr-race
  - staged-handoff
  - mergestatestatus-dirty
  - convention-rollout
  - union-resolution
---

# Git-Boundary Merge Conflict: Staged `--no-commit` Merge Handoff to the Orchestrator

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Make a DIRTY PR branch mergeable when the implementing agent is forbidden to commit/push and the orchestrator owns the signed (`git commit -S -s`) commit |
| **Outcome** | Conflicts resolved via `git merge --no-commit --no-ff`, union-of-both resolution, all gates green on the merged tree, turn ended with everything staged and MERGE_HEAD set for the orchestrator to finalize |
| **Verification** | verified-local |
| **Context** | Myrmidons issue #751 implement-review loop (branch `751-auto-impl`), ProjectHephaestus orchestrator, 2026-07-03 |
| **History** | initial version |

## When to Use

- An automated TASK/PLAN/REVIEW loop where the implementing agent runs under a **mandatory git boundary**: it may edit files and run tests, but must NOT run `git commit` or `git push`; the orchestrator creates a cryptographically signed, DCO signed-off commit (`git commit -S -s`) and pushes AFTER the agent's turn.
- The independent PR reviewer returns **CONFLICT**: the PR head branch is DIRTY vs `origin/main` (`mergeStateStatus=DIRTY`) and the reviewer literally demands "rebase onto origin/main, resolve every conflict, then commit the resolution (signed)".
- A literal rebase is **impossible** under the boundary: `git rebase` either creates commits (boundary violation, and they would be unsigned/non-DCO) or must be abandoned mid-rebase (`REBASE_HEAD` state), which is an unsafe handoff — the orchestrator's plain `git commit -S -s` does not correctly finish a rebase.
- The conflict source is a **parallel ecosystem-rollout race**: sibling PRs of a convention rollout edit the SAME doc lines (e.g. CLAUDE.md CI/CD bullet list, `docs/branch-protection.md` required-check tables) and one sibling (here PR #754, canonical `install` check) merged to main first.

## Verified Workflow

Translate the reviewer's INTENT (make the PR mergeable with a signed resolution) into a boundary-compatible mechanism. A merge commit clears `mergeStateStatus=DIRTY` exactly as a rebase would.

1. **Fetch and inspect divergence.** `git fetch origin main`; compare the branch and `origin/main` to identify what landed on main (here: sibling PR #754 editing the same doc lines the PR touches). Expect union-shaped conflicts in rollout waves.
2. **Merge without committing.** `git merge origin/main --no-commit --no-ff` — surfaces every conflict WITHOUT creating a commit, keeping the boundary intact.
3. **Resolve keeping BOTH sides' intent.** In convention-rollout races siblings append to the same lists; the correct resolution is almost always union-of-both, not ours/theirs (here: main's updated "On PR" bullet naming the new `install` job + the PR's new `release` bullet).
4. **Stage and sweep for markers.** `git add` the resolutions; verify NO conflict markers remain in ANY merged file, including auto-merged ones: `grep -rn '<<<<<<<\|>>>>>>>' <changed files>`.
5. **Re-run the project gates on the MERGED tree** before ending the turn (here: doc-drift check 0 errors, 106/106 bats tests). The merged combination is a new state nobody has tested.
6. **End the turn with everything STAGED and MERGE_HEAD still set.** Key git mechanic: when `MERGE_HEAD` exists, a subsequent plain `git commit -S -s` (run by the orchestrator) automatically produces the signed merge-resolution commit — git picks up `MERGE_HEAD`/`MERGE_MSG`. The reviewer's "commit the resolution (signed)" is satisfied by the orchestrator without the agent violating the boundary.

### Quick Reference

```bash
# 1. Fetch and inspect what main gained
git fetch origin main
git log --oneline HEAD..origin/main
git diff HEAD...origin/main --stat

# 2. Merge WITHOUT committing (boundary-safe)
git merge origin/main --no-commit --no-ff

# 3. Resolve each conflicted file keeping BOTH sides' intent (union, not ours/theirs)
git status --porcelain | grep '^UU'
#   ...edit files...

# 4. Stage and verify no markers remain anywhere in the merged set
git add <resolved files>
grep -rn '<<<<<<<\|>>>>>>>' <changed files>   # must return nothing

# 5. Re-run project gates on the merged tree
#   (project-specific: doc-drift check, bats suite, etc.)

# 6. STOP. Leave everything staged with MERGE_HEAD set.
#    Orchestrator's plain `git commit -S -s` finalizes the signed merge commit.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Literal `git rebase origin/main` per the reviewer's wording | Requires the agent to create commits — violates the non-negotiable git boundary, and the commits would be unsigned/non-DCO | Translate the reviewer's INTENT (make the PR mergeable with a signed resolution) into a boundary-compatible mechanism |
| 2 | Leaving a mid-rebase (interrupted) state for the orchestrator | The orchestrator's `git commit -S -s` does not continue a rebase; broken handoff | `MERGE_HEAD` is the only in-progress git state that a plain `git commit` cleanly finalizes |
| 3 | Resolving with ours/theirs shortcuts | Would drop either the PR's feature docs or main's sibling-PR docs | In convention-rollout waves siblings append to the same lists; resolution = keep both |

## Results & Parameters

Exact command sequence used (Myrmidons `751-auto-impl`, 2026-07-03):

```bash
git fetch origin main
git merge origin/main --no-commit --no-ff
# resolved CLAUDE.md CI/CD bullet list + docs/branch-protection.md required-check tables,
# keeping main's `install` bullet AND the PR's `release` bullet (union-of-both)
git add CLAUDE.md docs/branch-protection.md
grep -rn '<<<<<<<\|>>>>>>>' CLAUDE.md docs/branch-protection.md   # clean
# gates on the merged tree: doc-drift check → 0 errors; bats → 106/106 pass
# turn ended: all resolutions staged, MERGE_HEAD set
```

- **The MERGE_HEAD / `git commit -S -s` mechanic:** with `MERGE_HEAD` present, git treats the next plain `git commit` as the merge-resolution commit and pre-fills `MERGE_MSG`; the orchestrator's `-S -s` flags add the cryptographic signature and DCO sign-off. No `git merge --continue` or rebase machinery needed on the orchestrator side.
- **Honesty about verification level:** local gates passed (doc-drift 0 errors, 106/106 bats tests on the merged tree), but the orchestrator-side signed merge commit and the PR's `mergeStateStatus` flip to mergeable were **pending at capture time** — hence `verification: verified-local`, not `verified-ci`.

## Verified On

- **Project:** Myrmidons (HomericIntelligence), issue #751 review loop, branch `751-auto-impl`
- **Date:** 2026-07-03
- **Environment:** ProjectHephaestus orchestrator-driven implement-review loop; orchestrator owns `git commit -S -s` + push
- **Conflicting sibling:** PR #754 (canonical `install` check) racing the PR's canonical `release` check on shared doc surfaces
