---
name: automation-reuse-repo-clone-with-worktree-per-pr
description: "Use when: (1) code clones the SAME repo once per PR/branch/item inside a loop,
  (2) a fleet/batch tool re-clones a repo for every item causing redundant network+disk I/O
  that scales with item count, (3) refactoring a per-item-clone hot loop to a single clone +
  git worktree per item, (4) a per-item working dir is created in a temp subdir via full
  `git clone`, (5) you need isolated per-item checkouts of one repo for rebase/conflict/agent
  work."
category: tooling
date: 2026-06-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [git-worktree, clone-reuse, fleet-sync, batch-automation, performance, per-pr-checkout,
  idempotent-clone, dry-run-real-step, github-automation]
---
# Automation: Reuse One Repo Clone with a Git Worktree Per PR

## Overview

| Field | Value |
| ------ | ----- |
| **Date** | 2026-06-06 |
| **Objective** | Replace re-cloning the SAME repo once per PR/item in a loop with a single clone reused across items, plus a `git worktree` per item for isolated checkouts |
| **Outcome** | `hephaestus/github/fleet_sync.py` now clones each repo at most once and adds/removes a worktree per PR; eliminates O(N) redundant clones (a conflicted PR previously cloned twice) |
| **Verification** | verified-ci — fix merged to ProjectHephaestus main (PR #1045, closed #1044) |

When a loop processes many items (PRs, branches, refs) against the SAME repo, clone the repo
ONCE and use `git worktree add` per item. Worktrees share the object store (cheap), whereas a
full `git clone` per item is expensive network+disk I/O that scales linearly with item count.

## When to Use

- A batch/fleet tool loops `for pr in prs:` and each iteration runs a full `git clone` of the
  same repo into a fresh per-item temp directory.
- A conflicted/outdated item triggers MULTIPLE clones of the same repo within one run.
- The clone lives only in a per-run `tempfile.TemporaryDirectory`, so nothing is reused across
  items and nothing persists across runs.
- You need isolated per-item checkouts of one repo for rebase, conflict resolution, or agent
  work, without the items stepping on each other's working tree or branch.
- You are refactoring a per-item-clone hot loop and want the clone created lazily (only when an
  item actually needs a checkout — e.g. READY PRs that merge via `gh` never need one).

## Verified Workflow

The anti-pattern: `process_repo` looped `for pr in prs:`, and both `rebase_and_resign` and
`resolve_conflict_with_agent` ran `git clone --filter=blob:none` into a fresh per-PR temp
subdir. A repo with N outdated/conflicted PRs was cloned N times — a CONFLICTED PR cloned
TWICE. Nothing was reused across the PRs of a repo; nothing persisted across runs.

The fix is three small idempotent helpers — clone once, worktree per item, remove worktree in
a `finally` (leaving the shared clone intact). The clone is created LAZILY via a closure helper
in `process_repo`, so READY-only repos never clone at all.

### Quick Reference

```python
def ensure_repo_clone(repo: str, clone_dir: Path) -> Path:
    """Clone ONCE on first use; fetch --prune on reuse. Idempotent."""
    dest = clone_dir / repo
    if (dest / ".git").exists():
        _git(["fetch", "--prune", "origin"], cwd=dest)   # reuse: refresh, don't re-clone
    else:
        _git(["clone", "--filter=blob:none",
              f"https://github.com/{org}/{repo}.git", str(dest)])  # first use only
    return dest


def add_pr_worktree(repo_clone: Path, work: Path, branch: str, base: str) -> Path:
    """Isolated per-PR checkout off the SHARED clone. Idempotent (removes stale worktree)."""
    remove_worktree(repo_clone, work)                    # clear any stale worktree at path
    _git(["fetch", "origin", branch], cwd=repo_clone)    # need the PR head ...
    _git(["fetch", "origin", base], cwd=repo_clone)      # ... and the base to rebase onto
    _git(["worktree", "add", "--force", "-B", branch, str(work),
          f"origin/{branch}"], cwd=repo_clone)
    return work


def remove_worktree(repo_clone: Path, work: Path) -> None:
    """Drop the per-PR worktree; leave the shared clone intact. No-op if path absent."""
    if not work.exists():
        return                                           # nothing to remove
    _git(["worktree", "remove", "--force", str(work)], cwd=repo_clone)
```

```python
# process_repo: clone LAZILY via a nonlocal closure — only when a PR needs a checkout.
def process_repo(repo, prs, ...):
    _clone: Path | None = None
    def repo_clone() -> Path:
        nonlocal _clone
        if _clone is None:
            _clone = ensure_repo_clone(repo, clone_dir)   # first PR that needs it
        return _clone

    for pr in prs:
        if pr.merge_state == "READY":
            merge_via_gh(pr)                               # never touches a clone
            continue
        work = clone_dir / repo / f"wt-{pr.number}"
        try:
            add_pr_worktree(repo_clone(), work, pr.head, pr.base)
            ...                                            # rebase / resolve conflicts
        finally:
            remove_worktree(repo_clone(), work)           # always clean up the worktree
```

**Dry-run subtlety worth keeping:** the conflict resolver needs a REAL checkout even under
`--dry-run` — only the agent SPAWN is gated, not the rebase that surfaces the conflicts. So it
force-creates a real (idempotent) clone. Preserve such "must run for real even in dry-run"
steps when refactoring: gate the side-effecting action (agent spawn, push), not the inspection
that the gate decision depends on.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Full `git clone` per PR | Each PR iteration ran `git clone --filter=blob:none` into a fresh per-PR temp subdir | O(N) re-clones of the SAME repo; a conflicted PR cloned twice — network+disk scaled with PR count | Clone once per repo; add a `git worktree` per PR (worktrees share the object store, near-free) |
| Clone into per-run temp dir only | Clone lived in a per-run `tempfile.TemporaryDirectory` | Nothing reused across the repo's PRs; nothing persisted across runs | Keep ONE clone per repo in a stable `clone_dir`; `git fetch --prune` on reuse instead of re-cloning |
| Honor `--dry-run` on the conflict-resolver clone | Skipped the clone when `--dry-run` was set | Conflict inspection needs a real checkout to surface conflicts; with no clone the resolver had nothing to inspect | Force a real idempotent clone there; gate only the agent SPAWN under dry-run, not the rebase/inspection |
| Test cleanup without pre-creating the work dir | Asserted `remove_worktree` ran by mocking `_git` and checking for a `worktree remove` call | `remove_worktree` no-ops when the path is absent, so the test never exercised removal | Pre-create the work dir in the test so the no-op guard passes and the removal path actually runs |

## Results & Parameters

- **Clones per repo per run:** N (one per non-READY PR, +1 for each conflicted PR) → 1.
- **READY-only repos:** never clone — lazy closure means the clone is created only when a PR
  needs a checkout.
- **Helpers (all idempotent):**
  - `ensure_repo_clone(repo, clone_dir)` — clone on first use; `fetch --prune origin` on reuse
    (checks `<repo>/.git` exists).
  - `add_pr_worktree(repo_clone, work, branch, base)` — runs `fetch origin <branch>` and
    `fetch origin <base>`, then `worktree add --force -B <branch> <work> origin/<branch>`;
    removes any stale worktree at the path first.
  - `remove_worktree(repo_clone, work)` — `worktree remove --force` in a `finally`; no-op if the
    path is absent.
- **Testing (these PR-handling functions had NO direct tests before):** mock `_git` to record
  calls and assert:
  - clone-once-when-absent → `clone` present, no `fetch`;
  - reuse-via-fetch-when-present → `fetch --prune` present, no `clone`;
  - worktree add fetches head + base and adds off the clone;
  - the handler NEVER clones and cleans up its worktree;
  - `process_repo` clones exactly once for 3 PRs;
  - `process_repo` skips cloning entirely for READY-only repos.
- **Test gotchas:** `remove_worktree` no-ops on a missing path — pre-create the work dir so the
  cleanup test actually exercises removal. The `PRInfo` dataclass field order matters —
  construct with keyword args / a helper, not positionally.
- **General lesson:** loop over many items against the SAME repo → clone once, `git worktree add`
  per item; never re-clone per item.
