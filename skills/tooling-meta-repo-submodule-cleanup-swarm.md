---
name: tooling-meta-repo-submodule-cleanup-swarm
description: "Clean up dirty submodule state across a meta-repo using a myrmidon swarm of parallel agents in multiple waves. Use when: (1) many submodules have untracked generated files, stale checkouts, or WIP changes, (2) cleanup requires per-submodule branches/commits/PRs, (3) dependent work (pin updates) must wait for independent work (gitignore, commits) to complete."
category: tooling
date: 2026-04-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [meta-repo, submodules, myrmidon-swarm, git-worktrees, multi-wave, cleanup]
---

# Tooling: Meta-Repo Submodule Cleanup Swarm

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-03 |
| **Objective** | Clean up dirty submodule state across 15 submodules in the Odysseus meta-repo using a myrmidon swarm of 8 agents in 2 waves |
| **Outcome** | 5 PRs created across 5 repos, 1 merged immediately, 2 worktrees removed, 2 submodule pins updated |
| **Verification** | verified-local (all agents completed successfully; PRs pushed and CI/merge pending) |

## When to Use

- A meta-repo's `git status` shows many submodules as dirty (modified, untracked content, or new commits)
- Dirty state falls into distinct categories requiring different handling: untracked generated files, real WIP changes, stale local checkouts
- Cleanup work is parallelizable across submodules but some tasks depend on others (e.g., pin updates depend on PR merges)
- You need to avoid pinning submodules to non-main commits from unmerged feature branches

## Verified Workflow

### Quick Reference

```bash
# 1. Triage submodule dirty state
git submodule foreach --quiet 'echo "$name: $(git status --porcelain | head -3)"'
git submodule foreach --quiet 'echo "$name: $(git log --oneline -1) branch=$(git rev-parse --abbrev-ref HEAD)"'

# 2. Categorize into buckets
# Bucket A: Untracked generated files (CMakeUserPresets.json, pixi.lock) → gitignore fix
# Bucket B: Real WIP changes (CMakeLists.txt mods) → commit on feature branch, PR
# Bucket C: Stale checkouts (behind origin/main) → fast-forward only if on main

# 3. Wave 1: Independent per-submodule work (parallel agents)
# Haiku agents for gitignore tasks (simple, mechanical)
# Sonnet agents for WIP commit tasks (need judgment)

# 4. Wave 2: Dependent work (after Wave 1 completes)
# Worktree cleanup agent
# Submodule pin update agent (only pins submodules whose main moved forward)

# 5. Pin updates in parent repo
git -C path/to/submodule fetch origin
git -C path/to/submodule checkout origin/main
git add path/to/submodule
git commit -m "chore: update submodule pins for ..."
```

### Detailed Steps

1. **Triage all submodules**: Run `git submodule foreach` to collect dirty state. For each submodule, note: (a) untracked files, (b) modified files, (c) current branch, (d) commits ahead/behind origin/main. Group into the three buckets above.

2. **Categorize dirty state**:
   - **Untracked generated files** (CMakeUserPresets.json, pixi.lock, build/): These need `.gitignore` entries. Assign to Haiku agents — the work is mechanical.
   - **Real WIP changes** (CMakeLists.txt modifications, source edits): These need proper branches, commits, and PRs. Assign to Sonnet agents — they need judgment about commit messages and PR descriptions.
   - **Stale local checkouts** (detached HEAD or behind origin/main): Fast-forward to origin/main if the submodule is on the main branch. Do NOT update if on a feature branch.

3. **Design wave execution plan**:
   - **Wave 1** handles all independent per-submodule work in parallel. Each agent works inside one submodule's git context: creates branch, commits, pushes, creates PR.
   - **Wave 2** handles work that depends on Wave 1 results: worktree cleanup (removing worktrees created during earlier work) and submodule pin updates in the parent repo.

4. **Execute Wave 1**: Launch parallel agents. Each submodule agent:
   - `cd` into the submodule directory
   - `git checkout -b chore/fix-description`
   - Makes changes (add .gitignore entries, commit WIP)
   - `git push origin chore/fix-description`
   - `gh pr create -R org/repo --head chore/fix-description`
   - Attempts `gh pr merge --auto --rebase` (handle gracefully if auto-merge is disabled)

5. **Execute Wave 2**: After Wave 1 completes:
   - Remove any stale worktrees with `git worktree remove` (preserves branches — satisfies "never delete branches" constraint)
   - Update submodule pins ONLY for submodules whose `main` branch moved forward (e.g., after a PR was merged). Never pin to a feature branch commit.

6. **Commit pin updates in parent repo**: Stage updated submodule references with `git add path/to/submodule` and commit in the parent repo.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Compose `profiles: ["disabled"]` for Nestor | Set nestor to disabled profile in overlay | argus-exporter `depends_on` nestor caused "undefined service" error | `depends_on` is merged additively in compose overlays; use a busybox stub with `healthcheck: test: ["CMD", "true"]` instead |
| Committing submodule changes from parent | Tried `git add` for files inside submodule from Odysseus root | "Pathspec is in submodule" error | Submodule commits must happen inside the submodule's own git context |
| Pinning submodules on feature branches | Considered updating all submodule pins after Wave 1 | Would pin Odysseus to non-main commits for unmerged PRs | Only pin submodules whose `main` branch actually moved forward |

## Results & Parameters

### Swarm configuration

| Parameter | Value |
| ----------- | ------- |
| **Wave 1 agents** | 4 Haiku (gitignore tasks) + 2 Sonnet (WIP commit tasks) = 6 parallel |
| **Wave 2 agents** | 1 Haiku (worktree cleanup) + 1 Sonnet (pin updates) = 2 after Wave 1 |
| **Total agents** | 8 agents across 2 waves |
| **PRs created** | 5 across 5 repos, 1 merged immediately |
| **Worktrees removed** | 2 |
| **Submodule pins updated** | 2 (Hermes, Myrmidons) |

### Submodule dirty state categories

| Category | Example Files | Agent Tier | Action |
| ---------- | --------------- | ------------ | -------- |
| Untracked generated files | CMakeUserPresets.json, pixi.lock | Haiku | Add to .gitignore, commit, PR |
| Real WIP changes | CMakeLists.txt modifications | Sonnet | Commit on feature branch, PR |
| Stale local checkouts | Behind origin/main | N/A (Wave 2) | Fast-forward if on main branch |

### Compose overlay `depends_on` workaround

When disabling a service in a docker-compose overlay, `depends_on` from the base file is MERGED with the overlay, not replaced. Setting `profiles: ["disabled"]` does not remove the service from other services' `depends_on`. Solution:

```yaml
# Instead of profiles: ["disabled"], use a lightweight stub:
nestor:
  image: busybox:latest
  command: ["true"]
  healthcheck:
    test: ["CMD", "true"]
    interval: 1s
    retries: 1
```

### Auto-merge handling

Some repos have auto-merge disabled at the repository level. Agents should:
1. Attempt `gh pr merge --auto --rebase`
2. If it fails, report the PR number and URL — do not fail the agent
3. Optionally enable it: `gh api -X PATCH repos/org/repo --field allow_auto_merge=true`

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | 15 submodules, 8 agents, 2 waves | Verified-local — 5 PRs created, 2 pins updated, 2 worktrees removed |
