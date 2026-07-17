---
name: hephaestus-automation-loop-branch-sync-drive-green
description: "Diagnose and fix ProjectHephaestus automation-loop completion failures by enforcing fresh branch/worktree sync before implementation, limiting each worker's drive-green scope to its owned issue/PR, and running a final catch-all drive-green pass. Also: how to drive all existing open PRs to green — use --drive-green-all, NOT --phases drive-green (which crashes with KeyError on the uninitialized REPO stage). Use when: (1) automation loops leave planned issues or PRs unfinished, (2) existing issue worktrees or branches are reused across runs, (3) drive-green acts on unrelated PRs, (4) Codex-authored commits must satisfy signed and Signed-off-by policy gates, (5) you want to drive existing open PRs to green without planning/implementing new issues, (6) --drive-green-all logs 'ci:None: PR #N lacks state:implementation-go; regressing to pr_review' and swept-in PRs are dropped instead of driven, (7) a single failed drive-green attempt durably tags issues state:skip (--max-merge-attempts default 1; replaced by --drive-green-loops default 5)."
category: tooling
date: 2026-07-17
version: "1.2.0"
user-invocable: false
verification: verified-local
history: hephaestus-automation-loop-branch-sync-drive-green.history
tags:
  - projecthephaestus
  - automation-loop
  - drive-green
  - git-worktree
  - branch-sync
  - codex
  - signed-commits
  - dco
  - pr-scope
---

# Hephaestus Automation Loop Branch Sync and Drive-Green Scope

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-11 |
| **Objective** | Make automation-loop workers finish their owned issue/PR reliably instead of reusing stale branches, ignoring review/comment state, or letting broad drive-green phases act on unrelated PRs — and invoke a repo-wide "drive all open PRs to green" run correctly. |
| **Outcome** | Core fix landed in ProjectHephaestus PR #1646 for issue #1645 (merged 2026-06-26, verified-ci). v1.1.0 adds the `--drive-green-all` vs `--phases drive-green` invocation finding (verified-local: dry-run caught the crash; `--drive-green-all` confirmed on a live ~3-minute run driving 14 open PRs). |
| **Verification** | verified-ci (core); verified-local (v1.1.0 drive-green-all invocation finding) |
| **History** | [changelog](./hephaestus-automation-loop-branch-sync-drive-green.history) |

## When to Use

- A ProjectHephaestus automation loop reports progress but leaves issues, implementation PRs, or review-thread work unfinished.
- An implementation worker reuses an existing issue branch or worktree from a previous run.
- A branch/worktree appears to contain the intended work, but it was not rebased against current `origin/main` before the worker resumed.
- A drive-green phase is scoped by intent to one issue/PR but logs or touches unrelated open PRs.
- A final status sweep shows green-but-unarmed, stale, or review-blocked PRs after per-worker phases finish.
- Codex is the selected agent and commits must satisfy both signed-commit and `Signed-off-by` policy checks.
- You want to drive all **existing open PRs** to green (rebase + fix CI on PRs that already exist) without planning or implementing new issues from scratch.
- An attempt to run only the drive-green stage via `--phases drive-green` crashes with `KeyError: <StageName.REPO: 'repo'>` and reports the item "poisoned at repo".

## v1.2.0 findings (2026-07-17)

### Orphan PRs swept by --drive-green-all were dropped, not driven (fixed: PR #2254)

`--drive-green-all` seeds orphan open PRs (no tracked issue) into the CI stage as PR-only items
(`issue=None`). The CI entry gate regressed any PR lacking `state:implementation-go` to pr_review —
but pr_review terminates PR-only items ("no issue number"), so every swept-in PR logged
`ci:None: PR #N lacks state:implementation-go; regressing to pr_review` and died without one rebase
or CI fix. Fix (verified-ci, and confirmed live: the restarted loop logs
`orphan PR #N ... proceeding with drive-green (no issue-flow gate)`): PR-only items skip the
implementation-go gate and proceed to REBASE_WAIT. Merge containment is unchanged
(`defer_auto_merge` + fail-closed merge_wait, #2054).

**Known residual gap (under watch, unfixed):** orphan PRs reach REBASE_WAIT with no item worktree
(they never passed through implementation) and log
`ci:N: mechanical rebase requires an item worktree; failing back to implementation` — verify on a
live run whether the fallback completes before relying on --drive-green-all end-to-end.

### --max-merge-attempts replaced by --drive-green-loops (PR #2249)

`--max-merge-attempts` defaulted to 1, so ONE transient drive-green failure durably tagged the
issue `state:skip` — a single overnight run (2026-07-11) skip-parked 76 issues org-wide this way.
The option is REMOVED; use `--drive-green-loops N` (default 5), which feeds the same `merge`
budget. Old invocations passing `--max-merge-attempts` now fail argparse.

## Verified Workflow

### Quick Reference

```bash
# 1. Before each implementation worker resumes or reuses an issue branch/worktree:
git fetch origin
git -C <issue-worktree> status --short --branch
git -C <issue-worktree> rebase origin/main
git -C <issue-worktree> status --short --branch

# 2. Verify the worker owns exactly one issue/PR scope before drive-green:
gh issue view <issue> --json state,labels
gh pr list --state open --search "<issue> in:body" --json number,headRefName,state
hephaestus-automation-loop --issues <issue> --agent <agent>

# 3. Keep drive-green scoped to the owned issue/PR inside the worker:
hephaestus-merge-prs --issues <issue> --agent <agent>

# 4. After all per-worker runs, run one explicit catch-all pass:
hephaestus-merge-prs --agent <agent>

# 5. Verify commit policy before pushing or arming auto-merge:
git log origin/main..HEAD --pretty=format:'%h %G? %s'
git log origin/main..HEAD --format=%B | grep -q '^Signed-off-by: '

# 6. To drive ALL existing open PRs to green (rebase + fix CI on PRs that already
#    exist) WITHOUT planning/implementing new issues — use --drive-green-all,
#    which runs the full loop bootstrap first so the REPO stage is seeded:
pixi run hephaestus-automation-loop \
  --repos <Repo> --drive-green-all --max-workers 4 --parallel-repos 1 --model <model>

# DO NOT use `--phases drive-green` standalone — it CRASHES because the drive-green
# stage dereferences the REPO StageQueue, which --phases drive-green never seeds:
#   KeyError: <StageName.REPO: 'repo'>   (item "poisoned at repo")
# Always --dry-run a novel flag combination first to surface this before a live run.
```

### Detailed Steps

1. **Refresh the base before doing anything else.** Run `git fetch origin` and ensure the worker branch/worktree is rebased onto current `origin/main` before implementation starts. Treat a reused branch as suspect until it has been rebased and its diff is re-inspected.

2. **Do not preserve stale local commits just because the branch name matches the issue.** If a local issue branch/worktree was created before the current `origin/main`, inspect `git log HEAD..origin/main`, `git diff --stat origin/main...HEAD`, and the PR/issue state. Rebase first, then apply or rerun the implementation. A stale branch can contain revert-shaped or incomplete work that looks plausible by commit subject.

3. **Make worktree ownership explicit.** Each implementation worker should own one issue and the PR that closes it. If the worker discovers an existing PR, sync to that PR head and account for comments, reviews, and thread state before deciding the implementation is done.

4. **Scope drive-green inside a worker to the owned issue/PR.** A per-issue worker should not run a broad repo-wide drive-green phase that can fail because of unrelated PRs, arm unrelated PRs, or attribute unrelated CI failures back to the worker's issue. Pass the issue/PR scope through all worker-local drive-green calls.

5. **Run a final catch-all drive-green pass after all workers finish.** The catch-all pass belongs at the end of the orchestration, not inside every worker. It catches repo-level stragglers, newly green PRs that still need arming, and state that legitimately requires a broad sweep after all per-issue work has settled.

6. **Handle Codex commit policy explicitly.** When Codex is the selected agent, ensure commits satisfy the repo policy for both signed commits and `Signed-off-by` trailers. Verify the commit range before pushing or enabling auto-merge, and repair the commit history if either policy gate would fail.

7. **Use live GitHub state as the completion gate.** Before reporting the loop complete, check the issue state, PR state, required checks, review/thread state, and auto-merge state live from GitHub. Local success logs are not enough.

8. **To drive all existing open PRs to green, use `--drive-green-all` — never `--phases drive-green` standalone.** When the goal is to shepherd already-open PRs (rebase + fix CI on PRs that exist) rather than plan/implement new issues from scratch, use `--drive-green-all` with no `--phases`:

   ```bash
   pixi run hephaestus-automation-loop \
     --repos <Repo> --drive-green-all --max-workers 4 --parallel-repos 1 --model <model>
   ```

   `--drive-green-all` runs the full loop bootstrap first, which initializes the `StageName.REPO` StageQueue, and only then executes the drive-green stage. In contrast, `--phases drive-green` attempts to run ONLY the drive-green stage and skips the repo-stage bootstrap; the drive-green stage then dereferences the uninitialized REPO stage key and crashes with `KeyError: <StageName.REPO: 'repo'>`, reporting the item "poisoned at repo". The REPO stage is a **prerequisite**, not an independently runnable phase — `--phases` does not compose freely across all subsets. Prefer the purpose-built flag over hand-composing phases.

9. **Expect a correct `--drive-green-all` run to be FAST, and read a non-zero exit code carefully.** A correct run shepherds existing PRs (review + route to CI) rather than planning/implementing from scratch, so short runtime is normal (observed: ~3 minutes over 14 open PRs — 7 reviews requested, 5 already-GO'd PRs adopted → CI, 0 new GO verdicts). A short run is EXPECTED, not a sign of a no-op. An `exit_code=1` in this mode typically reflects item-level review non-GOs, not a crash — distinguish it from the `--phases drive-green` KeyError crash above.

10. **Dry-run any novel flag combination first.** A `--dry-run` of `--phases drive-green` surfaces the `KeyError` before any live invocation. Always dry-run an unfamiliar flag combination to catch stage-seeding crashes before they poison a live run.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rerunning issues after stale merged-PR close detection | The loop detected that a closing PR had merged or that the issue looked stale, then reran the issue without first ensuring the branch/worktree was on current `origin/main`. | The worker could resume against stale local state and miss the actual current mainline or review/comment context. | Treat every reused issue branch/worktree as untrusted until fetched, rebased, and rechecked against live GitHub state. |
| Broad drive-green over multiple PRs from inside workers | Worker-local drive-green ran over the broader repository instead of the owned issue/PR. | Unrelated PRs could be armed, fail, or affect the worker's return code, making one issue's worker responsible for repo-wide state. | Keep worker-local drive-green scoped to the issue/PR; reserve broad drive-green for a final catch-all pass. |
| Preserving stale local commits instead of rebasing | Existing local branch commits were treated as work to preserve because their subjects looked relevant. | Stale branches can be based on old main, miss required files or comments, or carry partial/revert-shaped changes. | Rebase onto `origin/main` before implementation; inspect the post-rebase diff and live PR state before deciding what to keep. |
| Fake or local-only substitutes for externally required tools | Local stand-ins were used for checks that the real external workflow or policy gate would enforce. | The local result did not prove the automation path would pass required CI, signing, review, or GitHub policy gates. | Use the real tool path for required external gates, or mark the result unverified. For this workflow, rely on required CI and live PR evidence. |
| Codex commits without explicit policy verification | Codex-generated commits were allowed to proceed without checking both cryptographic signature state and `Signed-off-by` trailers. | Required policy checks can reject commits even when the code and tests are correct. | Verify `git log origin/main..HEAD --pretty=format:'%h %G? %s'` and scan commit bodies for `Signed-off-by:` before push/auto-merge. |
| Running only the drive-green stage via `--phases drive-green` | Ran `hephaestus-automation-loop --phases drive-green` to shepherd existing open PRs without planning/implementing new issues. | Crashed with `KeyError: <StageName.REPO: 'repo'>`; the item was "poisoned at repo". The drive-green stage dereferences the REPO StageQueue, which `--phases drive-green` never seeds because it skips the repo-stage bootstrap. | Use `--drive-green-all` (no `--phases`) to drive existing PRs to green; it runs the full bootstrap first so the REPO stage is seeded. Dry-run novel flag combos to surface this before a live run. |
| Assuming `--phases` composes freely across any subset | Expected any subset of phases (e.g. just `drive-green`) to run standalone. | The repo stage is a required prerequisite for later stages, not an independently runnable phase; skipping it leaves a downstream stage referencing an uninitialized key. | Some phases are prerequisites, not independently runnable. Prefer the purpose-built flag (`--drive-green-all`) over hand-composing `--phases` subsets. |

## Results & Parameters

### Public Evidence

- ProjectHephaestus issue: #1645.
- ProjectHephaestus fix PR: #1646.
- Merge date: 2026-06-26.
- Required Checks run: 28256238895 succeeded.
- Test workflow run: 28256151963 succeeded.
- Squash merge commit: `2a0cd2adc2570264c1bd2c45df96c75246bac433`.

### Driving All Open PRs to Green (v1.1.0, verified-local)

Correct invocation — drives existing open PRs to green (rebase + fix CI on PRs that
already exist) without planning/implementing new issues:

```bash
pixi run hephaestus-automation-loop \
  --repos <Repo> --drive-green-all --max-workers 4 --parallel-repos 1 --model <model>
```

Broken invocation — crashes before doing any work:

```bash
# --phases drive-green skips the repo-stage bootstrap; the drive-green stage then
# dereferences the uninitialized REPO StageQueue:
#   KeyError: <StageName.REPO: 'repo'>   (item reported "poisoned at repo")
pixi run hephaestus-automation-loop --repos <Repo> --phases drive-green   # DO NOT USE
```

Observed behavior of a correct `--drive-green-all` run:

- FAST: a ~3-minute run over 14 open PRs.
- Of those 14: 7 reviews requested, 5 already-GO'd PRs adopted → routed to CI, 0 new GO verdicts granted.
- Short runtime is EXPECTED — drive-green shepherds existing PRs (review + route to CI) rather than planning/implementing from scratch.
- `exit_code=1` reflects item-level review non-GOs, not a crash. Distinguish it from the `--phases drive-green` KeyError crash.

Upstream improvement (low priority): `--phases drive-green` should either error
clearly ("drive-green requires the repo stage; use --drive-green-all") or
auto-include the repo bootstrap, rather than KeyError-poisoning the item. The
`--drive-green-all` workaround is reliable, so this is low priority.

### Completion Checklist

```bash
# Branch/worktree freshness
git fetch origin
git -C <issue-worktree> rebase origin/main
git -C <issue-worktree> diff --stat origin/main...HEAD

# Live issue/PR ownership
gh issue view <issue> --json state,labels
gh pr list --state all --search "<issue> in:body" --json number,state,headRefName,mergeStateStatus

# Worker-local convergence
hephaestus-automation-loop --issues <issue> --agent <agent>
hephaestus-merge-prs --issues <issue> --agent <agent>

# Final repo-level sweep after all workers finish
hephaestus-merge-prs --agent <agent>

# Commit-policy guard for Codex or any agent path
git log origin/main..HEAD --pretty=format:'%h %G? %s'
git log origin/main..HEAD --format=%B | grep -q '^Signed-off-by: '
```

### Expected Result

- Each worker starts from a current branch/worktree.
- Each worker implements, reviews, addresses review state, and drives only the PR it owns.
- Unrelated PR state cannot make one worker appear failed or complete.
- The final broad drive-green pass is explicit and intentionally repo-level.
- The PR can satisfy required CI plus signed and signed-off commit policy gates.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1645 / PR #1646 | verified-ci; Required Checks run 28256238895 succeeded; Test workflow run 28256151963 succeeded; merged 2026-06-26 as `2a0cd2adc2570264c1bd2c45df96c75246bac433` |
| ProjectHephaestus | `--drive-green-all` vs `--phases drive-green` (2026-07-11) | verified-local; `--dry-run` of `--phases drive-green` surfaced `KeyError: <StageName.REPO: 'repo'>` (item "poisoned at repo"); `--drive-green-all` confirmed working on a live ~3-minute run driving 14 open PRs (7 reviews requested, 5 already-GO'd PRs → CI, 0 new GO). |
