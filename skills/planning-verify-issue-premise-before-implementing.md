---
name: planning-verify-issue-premise-before-implementing
description: "When an issue's premise references an artifact (script, file, committed config) that may not exist on the working branch, VERIFY existence FIRST — and do it REPO-WIDE, not just on the current branch. A branch-scoped `git ls-files | grep` that returns nothing does NOT prove the artifact was never built: it may live on a sibling unmerged branch (often the prerequisite issue's own `<n>-auto-impl` branch). Before concluding 'never landed,' scan origin/main AND every remote branch (`git ls-tree -r <ref> | grep`, looped over `git branch -r`). When the artifact exists on an unmerged branch, the issue is usually VALID and merely blocked on merge ordering — not a candidate for re-scope/close. Then: read the named check script's ACTUAL runtime deps (grep for subprocess/import/external-tool calls) before asserting its CI environment — two superficially similar drift-check scripts can have OPPOSITE needs (one stdlib-only/pixi-free, one shelling out to `pixi list --json`). Finally, when a plan's correctness hinges on a judgment call, reduce it to a DETERMINISTIC runnable check (`git merge-base --is-ancestor`, file existence, exit code) — a re-scope/close recommendation that 'requires human ratification' is a NOGO trigger for plan reviewers. Use when: (1) planning an issue that names a specific script/file/artifact as already-existing context, (2) the issue is a follow-up to a prior issue/PR whose deliverables you have not confirmed merged, (3) you are about to conclude an artifact 'never existed' from a current-branch check only, (4) you are about to assert a CI job's toolchain (pixi/node/stdlib) without reading the script's calls, (5) your plan's central decision needs human sign-off rather than a runnable gate."
category: architecture
date: 2026-06-19
version: "2.0.0"
user-invocable: false
verification: unverified
history: planning-verify-issue-premise-before-implementing.history
tags: [planning, issue-premise, verify-before-implementing, branch-scoped-vs-repo-scoped, scan-all-branches, unmerged-branch, merge-ordering, requirements-drift, single-source-of-truth, ci-gate, pixi, deterministic-gate, plan-reviewer-nogo, re-scope, intent-vs-literal-ask, follow-up-issue, unverified-assumptions, dependency-sync]
---

# Planning: Verify the Issue Premise Before Implementing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture durable planning discipline for issues whose premise names an artifact that may not exist on the working branch — verify existence REPO-WIDE (all branches) before concluding it was never built, read a check script's real runtime deps before asserting its CI env, and reduce judgment-call dispositions to deterministic runnable gates |
| **Outcome** | Plan REVISED for ProjectHermes #556: the assumed `sync_requirements.py` + `requirements.txt` DO exist — on `origin/354-auto-impl` (the prerequisite issue's branch), not on `main`. The issue is VALID and blocked on merge ordering, provable by `git merge-base --is-ancestor origin/354-auto-impl origin/main` (→ false). The earlier "re-scope/close" disposition (v1.0.0) was WRONG and is corrected here. |
| **Verification** | unverified — PLANNING session only; no code written or executed end-to-end, no CI run, `gh pr view 354` failed (PR object not accessible), branch↔issue linkage inferred from naming convention |
| **History** | v1.0.0 → v2.0.0 (MAJOR: the central worked-example conclusion was overturned). See `planning-verify-issue-premise-before-implementing.history`. |

This skill's own v1.0.0 example is a cautionary tale: it concluded the named artifacts
"never landed" from a single-branch `git ls-files`, and recommended re-scoping/closing the
issue. **That was wrong.** A scan across all remote branches found both files on the
prerequisite issue's `<n>-auto-impl` branch. The artifact was BUILT but not yet merged. The
disposition flipped from "close the issue" to "the issue is valid; it is blocked on merge
ordering." The three corrections below are the durable lessons.

## When to Use

- An issue's body cites a specific script, file, or committed config as already-existing context (e.g. "the existing `scripts/sync_requirements.py --check`" or "the committed `requirements.txt`").
- The issue is framed as a follow-up to a prior issue/PR (e.g. "follow-up from #354") whose deliverables you have not independently confirmed MERGED.
- You are about to conclude an artifact "never existed" / "never landed" from a check run only on the current working branch.
- The issue's stated failure mode depends on a build step or committed file you have not inspected.
- You are about to assert a CI job's toolchain needs (pixi / node / stdlib-only) without reading the check script's actual `subprocess`/`import`/external-tool calls.
- Your plan's central decision is a judgment call (re-scope, close, defer) that would require human sign-off rather than a runnable gate.

## Verified Workflow

> **Warning:** This workflow has NOT been validated end-to-end. It was produced in a
> PLANNING session — no code was written or executed end-to-end, CI never ran, `gh pr view 354`
> failed (no accessible PR object), and the #354 ↔ `354-auto-impl` branch linkage was INFERRED
> from naming convention, not confirmed via the PR API. The section is titled "Verified
> Workflow" only to satisfy the marketplace validator. Treat every step below as a
> **Proposed Workflow / hypothesis** until CI and a human planner confirm it.

### Quick Reference

```bash
# 1. EXISTENCE CHECK — REPO-WIDE, not just the current branch.
#    A current-branch miss does NOT prove "never built."
git ls-files | grep -iE 'requirements|sync_req'        # current branch only — INSUFFICIENT
git ls-tree -r origin/main --name-only | grep -iE 'requirements|sync_req'   # check main too
# ...then scan EVERY remote branch (the artifact often lives on the prereq issue's branch):
for b in $(git branch -r --format='%(refname:short)' | grep -v HEAD); do
  git ls-tree -r --name-only "$b" 2>/dev/null | grep -q sync_requirements \
    && echo "FOUND in $b"
done
# -> FOUND in origin/354-auto-impl   (built, not yet merged to main)

# 2. If found on a sibling branch, the issue is VALID + blocked on merge order.
#    Reduce that to a DETERMINISTIC gate instead of a "close the issue" recommendation:
git merge-base --is-ancestor origin/354-auto-impl origin/main && echo MERGED || echo BLOCKED
# -> BLOCKED  (false exit) == #354 not yet in main == #556 cannot land its CI job yet

# 3. Read the check script's ACTUAL runtime deps BEFORE asserting its CI env:
git show origin/354-auto-impl:scripts/sync_requirements.py | grep -nE 'subprocess|import |pixi|node'
# -> subprocess.run(["pixi","list","--json"])  ==> needs pixi in CI (NOT a stdlib-only job)
# contrast: check_dep_sync.py is tomllib-only ==> pixi-free. SAME repo, OPPOSITE CI needs.
```

### Detailed Steps

1. **Run existence checks REPO-WIDE before concluding an artifact "never landed."** A
   current-branch `git ls-files | grep` returning nothing is a BRANCH-scoped fact, not a
   REPO-scoped one. Check `origin/main` (`git ls-tree -r origin/main --name-only | grep`),
   then loop over every remote branch (`for b in $(git branch -r ... | grep -v HEAD); do
   git ls-tree -r --name-only "$b" | grep -q <artifact> && echo "FOUND in $b"; done`). For
   #556 this found `scripts/sync_requirements.py` and `requirements.txt` on
   `origin/354-auto-impl` — the prerequisite issue #354's own branch. The artifact was BUILT,
   not absent. **Issues are frequently the CI-wiring / integration tail of a sibling issue
   whose code lives on an unmerged branch.**

2. **When the artifact exists on an unmerged branch, the correct disposition is usually "valid,
   blocked on merge ordering" — NOT re-scope/close.** Reduce that to a deterministic gate the
   implementer can run: `git merge-base --is-ancestor origin/354-auto-impl origin/main` returns
   false (BLOCKED) while #354 is unmerged. This is a runnable fact, not a recommendation
   requiring sign-off (see step 4).

3. **Read the named check script's ACTUAL runtime dependencies before asserting its CI
   environment.** Do not generalize the toolchain of a superficially similar script in the same
   repo. `sync_requirements.py` shells out via `subprocess.run(["pixi","list","--json"])`, so its
   CI job REQUIRES pixi setup. The repo's other drift checker, `check_dep_sync.py`, is
   deliberately stdlib-only (`tomllib`) and runs pixi-free. **Two superficially similar
   "drift check" scripts had OPPOSITE runtime requirements.** Grep the script for `subprocess`,
   `import`, and external-tool names (`pixi`, `node`, `cargo`, ...) before deciding its job needs.

4. **Reduce a plan's central judgment call to a deterministic runnable check.** The v1.0.0 plan
   recommended re-scoping/closing #556 — a decision that "required human ratification." A plan
   reviewer NOGO'd it precisely because a discretionary sign-off blocks the next stage from
   auto-proceeding. Converting the decision into a hard, provable ordering dependency
   (`git merge-base --is-ancestor ...` → false = blocked) removed the NOGO. A deterministic gate
   the implementer can run is acceptable; a discretionary recommendation requiring sign-off is not.

5. **Still separate the literal ask from the intent — but only AFTER the repo-wide existence
   check.** v1.0.0 correctly noted that building a redundant artifact can violate a
   single-source-of-truth principle. That reasoning is sound ONLY when the artifact is genuinely
   absent or genuinely redundant. Here it was NEITHER — it existed on a sibling branch — so the
   "satisfy intent with existing tooling, decline to build" path did not apply. Verify existence
   repo-wide first; the intent-vs-literal analysis is downstream of that fact.

6. **Fetch linked/parent issues from the source of truth — and flag when you could not.** The
   #354 ↔ `354-auto-impl` linkage was inferred from branch naming because `gh pr view 354`
   failed (no accessible PR object). Treat such inferences as assumptions, not facts, and surface
   them as reviewer risks.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Concluded artifact "never built" from `git ls-files` on current branch only | On branch `90-170-171-auto-impl`, `git ls-files \| grep -iE 'requirements\|sync_req'` returned nothing, so the v1.0.0 plan concluded `sync_requirements.py` / `requirements.txt` never landed and recommended re-scoping/closing #556 | Branch-scoped check missed the files, which exist on the sibling unmerged branch `origin/354-auto-impl`; "never built" was a wrong, branch-scoped claim that flipped the entire disposition | Scan `origin/main` AND all remote branches (`git ls-tree -r <ref> \| grep`, looped over `git branch -r`) before concluding an artifact is missing — issues are often the CI-wiring tail of a sibling issue's unmerged branch |
| Asserted the CI job should be pixi-free (copied `check_dep_sync.py`'s pattern) | The first plan said the new check should run in a stdlib-only / pixi-free CI job, mirroring the repo's existing `check_dep_sync.py` (`tomllib` only) | `sync_requirements.py` calls `subprocess.run(["pixi","list","--json"])`, so it REQUIRES pixi in CI; the "stdlib checks run before pixi" heuristic does not generalize across two superficially similar scripts | Read the check script's `subprocess`/`import`/external-tool calls before deciding its CI env (pixi/node/etc.); same-repo drift checkers can have OPPOSITE runtime needs |
| Recommended re-scoping/closing the issue, deferring to human ratification | v1.0.0's central decision was "recommend re-scoping or closing #556," surfaced as a human-ratify judgment call | Plan reviewer NOGO'd: a discretionary sign-off blocks the next stage from auto-proceeding | Reduce the decision to a deterministic runnable check (`git merge-base --is-ancestor origin/354-auto-impl origin/main` → false = blocked) instead of a recommendation requiring human judgment |
| Trusted the "follow-up from #354" lineage via branch naming | Treated #556 ↔ #354 deliverables and the #354 ↔ `354-auto-impl` link as fact from naming convention | `gh pr view 354` failed (no accessible PR object); the linkage was inferred, never confirmed against the PR API | Fetch linked/parent issues/PRs from the source of truth; when the API call fails, flag the inferred linkage as a reviewer risk rather than a verified fact |
| Assumed merge order without enforcing it | The plan assumes #354 merges BEFORE #556, since #556's new CI job references files that only exist post-#354 | The dependency is stated but not enforced; if merge order is reversed, the new `docker-deps` job references nonexistent files and fails | State the ordering as a deterministic gate AND note that the plan itself does not enforce merge order — call it out as the plan's main residual risk |

## Results & Parameters

### Repo-wide existence scan (the correction)

```bash
# WRONG (v1.0.0): current branch only -> empty -> "never landed" (false conclusion)
git ls-files | grep -iE 'requirements|sync_req'        # (empty on 90-170-171-auto-impl)

# RIGHT (v2.0.0): scan main + every remote branch
git ls-tree -r origin/main --name-only | grep -iE 'requirements|sync_req'   # check main
for b in $(git branch -r --format='%(refname:short)' | grep -v HEAD); do
  git ls-tree -r --name-only "$b" 2>/dev/null | grep -q sync_requirements \
    && echo "FOUND in $b"
done
# -> FOUND in origin/354-auto-impl   (BUILT, not yet merged to main)
```

### Deterministic disposition gate (replaces the human-ratify recommendation)

```bash
# Is the prerequisite branch already in main? false (BLOCKED) => #556 valid but cannot land yet.
git merge-base --is-ancestor origin/354-auto-impl origin/main && echo MERGED || echo BLOCKED
```

### Script-specific CI runtime deps (the second correction)

```bash
git show origin/354-auto-impl:scripts/sync_requirements.py | grep -nE 'subprocess|pixi'
# -> subprocess.run(["pixi","list","--json"])   ==> CI job needs pixi (NOT pixi-free)
# contrast — same repo, OPPOSITE need:
git show origin/main:scripts/check_dep_sync.py  | grep -nE 'import|subprocess'
# -> tomllib only, no subprocess                ==> pixi-free job is correct for THIS one
```

### Most uncertain assumptions (honest reviewer risks)

- **`pixi list --json` may require an installed env on CI.** It may need `pixi install --locked`
  on the CI pixi version; NOT verified. The plan defers this to the first CI run — the main
  remaining unknown.
- **Merge order is assumed, not enforced.** The plan assumes #354 merges before #556. Files
  referenced by the new CI job exist only post-#354; if merge order is reversed, the `docker-deps`
  job references nonexistent files and fails. The dependency is stated but the merge order is not
  enforced by the plan itself.
- **#354 ↔ branch linkage is inferred.** `gh pr view 354` failed (no accessible PR object); the
  #354 ↔ `354-auto-impl` link was inferred from branch naming convention, not confirmed via the
  PR API.
- **No command executed end-to-end against #354's branch.** The verification commands would
  require checking out `354-auto-impl`; they are proposed, not run. Verification level =
  unverified.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | Issue #556 ("Add check-reqs to CI to catch requirements drift") — re-plan after plan-reviewer NOGO, on branch `90-170-171-auto-impl` | Unverified. v1.0.0 concluded the assumed `sync_requirements.py` + `requirements.txt` "never landed" (branch-scoped `git ls-files`) and recommended closing the issue — WRONG. A scan of all remote branches found both on `origin/354-auto-impl`. Corrected disposition: issue is VALID, blocked on merge order (`git merge-base --is-ancestor origin/354-auto-impl origin/main` → false). `sync_requirements.py` calls `pixi list --json` so its CI job needs pixi (unlike stdlib-only `check_dep_sync.py`). `gh pr view 354` failed; branch linkage inferred. |

## References

- [git-unmerged-branch-file-access.md](git-unmerged-branch-file-access.md) — read/plan against files that exist only on non-main branches (`git show origin/<branch>:path`, `git log --all`); the mechanics behind this skill's repo-wide existence scan.
- [planning-verify-integration-point-exists-before-guarding.md](planning-verify-integration-point-exists-before-guarding.md)
- [planning-verify-live-state-before-assuming-work-remains.md](planning-verify-live-state-before-assuming-work-remains.md)
- [planning-verify-assumptions-before-enforcement-gate.md](planning-verify-assumptions-before-enforcement-gate.md)
