---
name: rebase-stale-automation-pr-onto-refactored-main
description: "Semantic conflict-resolution classes when replaying a stale automation-authored PR onto a main that a large refactor has restructured. Use when: (1) a queued/DIRTY PR was branched many commits behind and now conflicts after a big landed refactor (e.g. Hephaestus #2280 loop-owned-approval), (2) a PR routes to a pipeline stage/symbol the refactor DELETED (verify against the enum, not the branch), (3) a merge-queue crawls because stale-base PRs fail the new zizmor gate and re-validate the whole tail, (4) an automation 'update' created a DCO-less merge commit that fails pr-policy, (5) security hardening (persist-credentials:false) auto-merged only into pre-existing jobs and a PR's NEW job trips zizmor artipacked, (6) two PRs claim the same ADR number, (7) an AST-guard registry (dontAsk / allowed-tools scopes) conflicts because the refactor renamed the call-site symbol, (8) deciding whether a PR is genuinely superseded vs. merely mentioning pixi in stale test boilerplate."
category: ci-cd
date: 2026-07-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - rebase
  - merge-conflict
  - stale-base
  - refactor-collision
  - merge-queue-drain
  - zizmor
  - artipacked
  - persist-credentials
  - deleted-stage-routing
  - adr-collision
  - ast-guard-registry
  - dco-merge-commit
  - superseded-pr
  - pixi-boilerplate
  - homericintelligence
  - hephaestus
---

# Rebasing a Stale Automation PR onto a Heavily-Refactored Main

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-18 |
| **Objective** | Drive a backlog of automation-authored PRs to mergeable after a large refactor (Hephaestus #2280, "loop-owned PR approval") landed on `main` and left ~7 PRs DIRTY and the merge queue crawling. |
| **Outcome** | Successful. Every DIRTY PR rebased to MERGEABLE + armed (or closed as genuinely superseded); the queue-crawl root cause was eliminated. Each rebase verified by the repo's own guard tests passing on the resolved tree. |
| **Verification** | verified-ci (each PR reached MERGEABLE with 0 conflicts; pipeline/AST-guard/doc-guard suites passed on every resolved tree; commits stayed `verified==true` + DCO). |

## When to Use

Reach for this when a **single** stale PR must be replayed onto a `main` that a
large refactor restructured — a different problem from a multi-repo backlog
sweep (see `automation-multi-repo-pr-sweep-rebase-resolve` for that). The value
here is the **catalog of semantic conflict classes** the refactor creates and
how to resolve each faithfully.

## Verified Workflow

Core insight: **the conflict text is a distraction; resolve against the CURRENT
code/enum on `main`, never against what the stale branch assumed.** An
automation branch encodes the world as it was N commits ago. After a big
refactor, "take theirs" or "take ours" are both usually wrong — you must map the
branch's *intent* onto `main`'s *new structure*.

### The merge-queue-crawl diagnosis (do this first)

A GitHub merge queue that barely advances is usually NOT runner starvation and
NOT queue config. Check, in order:

1. `gh run list --workflow=<required>.yml` — are `merge_group` runs stuck
   `queued` (runner starvation) or **completing `failure`**? A failing entry is
   far worse than a slow one.
2. If failing: `gh run view <id> --json jobs --jq '.jobs[]|select(.conclusion=="failure").name'`.
   A recurring `lint` + `security/workflow-scan` failure across MANY entries
   means a **gate that landed on `main` now scans files the stale PRs still
   carry in an old form**.
3. Confirm the stale base: `behind=$(git rev-list --count $(git merge-base origin/main origin/<branch>)..origin/main)`.
   A PR ~6+ behind, whose `_required.yml`/`contract.yml` differs from `main`, will
   FAIL the new gate in its `merge_group` — then GitHub ejects it after a full
   ~20-min matrix and **re-validates every entry behind it**. That cascade, not
   runners, is the crawl. **Fix = rebase the stale PRs onto current `main`** (which
   pulls in the hardened workflow files). Re-enqueuing without rebasing just
   re-poisons the queue.

### The conflict classes (resolve each this way)

- **DCO-less merge commit** — an automation "update main into branch" created a
  `Merge remote-tracking branch ...` commit with no `Signed-off-by` trailer;
  `pr-policy` rejects it. **Rebase onto `origin/main`** — this DROPS the merge
  commit entirely, replaying only the real (already-signed+DCO) work commit. Do
  not try to amend a merge commit. (Commit-signing remediation proper lives in
  `pr-compliance-dco-and-rebase-fix`.)

- **zizmor `artipacked` on a NEW job** — the landed security PR added
  `persist-credentials: false` to every *pre-existing* checkout, but the stale
  PR *introduces a new job* whose checkout git-auto-merged in WITHOUT that line.
  Finding points at `release.yml:<new-job-checkout>`. Fix: add
  `persist-credentials: false` to the new job's `actions/checkout`. Verify
  locally: `uv run zizmor --no-online-audits --min-severity medium <file>` →
  "No findings".

- **Routing to a DELETED stage/symbol** — the stale PR routes to
  `StageName.CI` (or any symbol) that the refactor removed. **Verify against the
  enum on `main`, not the branch**: read `routing.py`'s `StageName` members. If
  the target is gone, map the branch's intent to a surviving member (e.g. a
  legacy issue-level label → `PR_REVIEW`, not the deleted `CI`). Routing to a
  nonexistent member reintroduces the exact `KeyError` a prior fix closed.

- **ADR-number collision** — both the stale PR and a landed PR claimed
  `0012`. Renumber the incoming one: edit the README index row, `git mv` the
  file to the next free number, fix the ADR's own `# ADR-NNNN` header, and update
  EVERY reference (runbook links AND prose "per ADR-NNNN" mentions AND any
  guard-test assertion that hardcodes the number). Grep the whole tree for the
  old number to be sure.

- **AST-guard registry realignment** — a test that AST-scans call sites (e.g.
  `dontAsk` permission scopes, `allowed_tools`) conflicts because the refactor
  renamed the function the scope attaches to. Resolve by matching the registry
  to the ACTUAL post-rebase code: for each entry, `grep` the real symbol name
  and its literal scope in the source, then write exactly that. The guard test
  itself re-validates your resolution — run it.

- **Superseded vs. pixi-boilerplate** — a PR whose *substance* is done by a
  landed PR (same issue, same file, older base whose diff would REVERT newer
  work) is genuinely superseded → close it, resolve its issue. But a PR that
  merely mentions `pixi run` in its stale testing-boilerplate section is NOT
  pixi-specific — check `git diff --name-only` for actual `pixi*` file touches;
  if none, its substance is real → rebase it, don't close it.

### Quick Reference

```bash
# 1. Diagnose a crawling merge queue: are merge_group runs FAILING (not just slow)?
gh run list --workflow=_required.yml --limit 20 \
  --json event,conclusion,headBranch \
  --jq '.[]|select(.event=="merge_group" and .conclusion=="failure")|.headBranch'
gh run view <id> --json jobs \
  --jq '.jobs[]|select(.conclusion=="failure").name'   # -> lint, security/workflow-scan

# 2. Confirm stale base carries an old workflow file the new gate rejects
BR=<branch>; BASE=$(git merge-base origin/main origin/$BR)
git rev-list --count "$BASE"..origin/main                       # how far behind
diff <(git show origin/main:.github/workflows/_required.yml) \
     <(git show origin/$BR:.github/workflows/_required.yml) >/dev/null \
     && echo "fresh" || echo "STALE workflow -> will fail zizmor in merge_group"

# 3. Rebase in an ISOLATED worktree; a DCO-less merge commit is dropped automatically
git worktree add /tmp/rb-$BR "$BR"
cd /tmp/rb-$BR && git fetch origin main "$BR" && git rebase origin/main
# ...resolve each conflict class per the sections above...
git log origin/main..HEAD                    # expect ONLY real work commits, no merge commit

# 4. Before routing decisions, read the ACTUAL enum on main (never the branch)
git show origin/main:hephaestus/automation/pipeline/routing.py | grep -A12 'class StageName'

# 5. Verify with the repo's OWN guards on the resolved tree, then push signed
uv run pytest <affected pipeline/AST-guard/doc-guard suites> --override-ini="addopts=" -q
uv run zizmor --no-online-audits --min-severity medium .github/workflows/<changed>.yml
git push --force-with-lease origin "$BR"     # PR ejected from queue first if it was queued
gh pr merge <n> --auto                        # queue owns merge method; do NOT pass --squash
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Diagnosed the slow queue as runner starvation and waited | Runners were fine; the real cause was stale-base PRs FAILING the new zizmor gate in `merge_group`, ejecting after a 20-min matrix and re-validating the whole tail | Check `merge_group` run *conclusion*, not just runner counts. A failing entry poisons everything behind it. |
| 2 | On the release-workflow rebase, took the incoming branch's `StageName.CI` route | The refactor had DELETED the CI stage from the enum; the resolution would have crashed (the `KeyError` a prior fix closed) | Resolve routing against the CURRENT enum on `main`, not the branch's assumption. Read `routing.py`. |
| 3 | Took the branch's side wholesale on an AST-guard `dontAsk`/`allowed_tools` registry | The branch predated a scope change AND renamed the call-site symbol; blind "take theirs" would desync the registry from the real code | Match the registry to the actual post-rebase symbols+scopes (`grep` them); let the guard test re-validate. |
| 4 | Left a docstring note "the FOLLOWUP_WAIT state was retired" after removing the state | A retirement guard test did a plain substring `"FOLLOWUP_WAIT" not in source` and failed on the note | When a guard is a substring check, even a historical mention trips it — reword to avoid the literal token. |
| 5 | Passed `gh pr merge <n> --auto --squash` to re-enqueue | "The merge strategy for main is set by the merge queue" — rejected | On merge-queue repos, arm with `--auto` and NO strategy flag; the queue supplies SQUASH. |
| 6 | Considered closing PRs that mention `pixi run` as pixi-specific | The `pixi run` was only stale testing boilerplate; the PRs' substance (SLOs, NATS DLQ, docs) touched no pixi files and was still valid | Judge by `git diff --name-only` (does it touch `pixi*`?), not by a boilerplate string. |

## Results & Parameters

- **Scale:** one session cleared all DIRTY PRs after a large refactor landed; each reached MERGEABLE + armed or was closed as genuinely superseded (with its issue resolved).
- **Verification signal:** the repo's OWN guard tests are the oracle — an AST-scanning `dontAsk` registry test and a doc/ADR retirement test each *pass only if* the resolution matches the real code. Run them on the resolved tree before pushing.
- **Queue mechanics:** `maximumEntriesToMerge` is not the throughput limit when entries FAIL; a failing entry ejects after a full matrix and re-stacks the tail. Throughput recovers only after the stale bases are rebased away.
- **Merge-method:** merge-queue repos reject `gh pr merge --squash`; arm with bare `--auto`.
- **Signatures:** rebasing re-signs replayed commits automatically when the GPG key is configured; verify `git log --show-signature` shows Good + `Signed-off-by` before pushing. Sign with `4211002+mvillmow@users.noreply.github.com`.

### Related skills (cross-links)

- `pr-compliance-dco-and-rebase-fix` — the commit-signing/DCO/pr-policy remediation proper (whole-range rewrite); this entry's DCO-less-merge-commit case is the "drop it via rebase" sibling.
- `automation-multi-repo-pr-sweep-rebase-resolve` — the multi-repo backlog-sweep orchestration this single-PR conflict catalog complements.
- `hephaestus-automation-loop-branch-sync-drive-green` — driving open PRs to green via the loop, and the `--drive-green-all` vs `--phases drive-green` KeyError.
- `prompt-loader-rebuild-race` — the `__file__`-loader fix that was one of the landed PRs in this wave.
- `adr-authoring-indexing-and-maintenance` — ADR index/landing mechanics (this entry adds the collision-renumber-on-rebase case).
