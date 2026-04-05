---
name: multi-repo-pr-orchestration-swarm-pattern
description: "Orchestrate PR management across all HomericIntelligence repos using myrmidon swarm. Use when: (1) multiple repos have open PRs that need merging, conflict resolution, or CI fixes, (2) Odysseus submodule pins need updating after cross-repo PR merges, (3) coordinating parallel waves of agents across 5+ repos with sequential-within-repo merge ordering."
category: ci-cd
date: 2026-04-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [multi-repo, PR, merge, submodule, myrmidon-swarm, cross-repo, orchestration, odysseus]
---

# Multi-Repo PR Orchestration with Myrmidon Swarm

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-04 |
| **Objective** | Use myrmidon swarm to scan all HomericIntelligence repos, merge open PRs, resolve conflicts, fix CI failures, and update Odysseus submodule pins -- all in parallel waves |
| **Outcome** | Successful -- 5 repos had PRs merged, submodule pins updated, Odysseus rebased on main |
| **Verification** | verified-local |

## When to Use

- Multiple HomericIntelligence repositories have open PRs that need merging simultaneously
- After a batch of feature work lands across repos and Odysseus submodule pins are stale
- You need to merge PRs across repos in parallel but sequentially within each repo to avoid conflicts
- CI failures block merges and need triage/fix agents before PRs can land
- Coordinating Dependabot, feature, and fix PRs across the full ecosystem in one session

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Scan all repos for open PRs
REPOS="ProjectAgamemnon ProjectNestor ProjectKeystone ProjectCharybdis ProjectArgus ProjectHermes ProjectHephaestus ProjectOdyssey ProjectScylla ProjectMnemosyne ProjectProteus ProjectTelemachy Myrmidons AchaeanFleet"
for repo in $REPOS; do
  echo "=== $repo ==="
  gh pr list --repo HomericIntelligence/$repo --state open --limit 20
done

# Phase 2: Wave 1 -- merge clean PRs (haiku agents, parallel across repos)
# One agent per repo, merge PRs oldest-first within each repo

# Phase 3: Wave 1b -- fix conflicts (sonnet agents)
# git fetch origin && git rebase origin/main && git push --force-with-lease

# Phase 4: Wave 1c -- fix CI failures (sonnet agents)
# Read CI logs, fix code, push, wait for green

# Phase 5: Wave 2 -- update Odysseus submodule pins
cd /home/mvillmow/Odysseus
for sub in control/ProjectAgamemnon control/ProjectNestor provisioning/ProjectKeystone testing/ProjectCharybdis; do
  git -C "$sub" fetch origin
  git -C "$sub" checkout origin/main
done
git add control/ provisioning/ testing/
git commit -m "chore: update submodule pins after cross-repo PR merges"
```

### Phase 1: Scan All Repos for Open PRs

Enumerate every HomericIntelligence repository and list open PRs:

```bash
REPOS=$(gh repo list HomericIntelligence --limit 30 --json name --jq '.[].name')
for repo in $REPOS; do
  count=$(gh pr list --repo HomericIntelligence/$repo --state open --json number --jq 'length')
  [ "$count" -gt 0 ] && echo "$repo: $count open PRs"
done
```

For each repo with open PRs, gather details:

```bash
gh pr list --repo HomericIntelligence/$repo --state open \
  --json number,title,headRefName,mergeStateStatus,statusCheckRollup \
  --jq '.[] | "\(.number)\t\(.mergeStateStatus)\t\(.title)"'
```

Classify each PR:
- **MERGEABLE + CI green**: ready for Wave 1 merge
- **DIRTY/CONFLICTING**: needs rebase in Wave 1b
- **BLOCKED (CI failing)**: needs CI fix in Wave 1c
- **Dependabot**: merge with `gh pr merge --rebase` (no `--admin`)

### Phase 2: Wave 1 -- Merge Clean PRs (Parallel Across Repos)

Launch one **haiku agent** per repo. Each agent merges PRs oldest-first within its repo:

```bash
# Agent instructions (per repo):
# 1. List open PRs sorted by number ascending (oldest first)
gh pr list --repo HomericIntelligence/$REPO --state open --json number --jq '.[].number' | sort -n

# 2. For each PR, attempt merge
gh pr merge $PR_NUM --repo HomericIntelligence/$REPO --rebase

# 3. If merge fails due to CI, skip to next PR (will handle in Wave 1c)
# 4. If merge fails due to conflicts, skip (will handle in Wave 1b)
```

**Critical rule**: Merge PRs **sequentially within a repo** (oldest-first) to avoid conflicts. PRs are parallelized **across** repos, not within.

**Model tier selection**:
- **Haiku**: sufficient for clean merges (mechanical: check status, run `gh pr merge`)
- **Sonnet**: escalate for conflict resolution or CI investigation
- **Opus**: orchestrator only, not needed for per-repo work

**Wave sizing**: One agent per repo with open PRs. Typically 4-6 parallel agents.

### Phase 3: Wave 1b -- Fix Merge Conflicts (Sonnet Agents)

After Wave 1, some PRs will have conflicts because their base changed when earlier PRs merged. Launch **sonnet agents** for these:

```bash
# Per-PR conflict resolution:
gh pr checkout $PR_NUM
git fetch origin main
git rebase origin/main

# Resolve conflicts (see batch-pr-rebase-conflict-resolution-workflow for strategies)
# For pixi.lock: rm pixi.lock && pixi install
# For CI files: git checkout --ours .github/workflows/
# For source code: semantic merge

git push --force-with-lease
# GitHub auto-merge will pick it up if previously enabled
```

**Key pattern**: Always `git fetch origin` before rebasing to get the latest main after Wave 1 merges.

### Phase 4: Wave 1c -- Fix CI Failures (Sonnet Agents)

For PRs blocked by CI failures, launch **sonnet agents** to investigate and fix:

```bash
# 1. Read CI failure logs
gh pr checks $PR_NUM --repo HomericIntelligence/$REPO
gh run view $RUN_ID --log-failed

# 2. Common CI failure categories:
#    - clang-format violations: run clang-format -i on affected files
#    - clang-tidy warnings: fix flagged code patterns
#    - test coverage drops: add missing tests or adjust thresholds
#    - pre-commit failures: run pre-commit run --all-files and commit fixes

# 3. Push fix and wait for CI
git add <fixed-files>
git commit -m "fix: resolve CI failures for <description>"
git push

# 4. Poll for CI completion
for i in $(seq 1 30); do
  STATE=$(gh pr checks $PR_NUM --repo HomericIntelligence/$REPO 2>&1)
  echo "$STATE" | grep -q "pass" && break
  sleep 30
done

# 5. Merge once green
gh pr merge $PR_NUM --repo HomericIntelligence/$REPO --rebase
```

### Phase 5: Wave 2 -- Update Odysseus Submodule Pins

After all PRs are merged across repos, update the Odysseus meta-repo submodule pins:

```bash
cd /home/mvillmow/Odysseus

# For each submodule whose main moved forward:
git submodule foreach --quiet '
  git fetch origin main 2>/dev/null
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main 2>/dev/null)
  if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$name: $LOCAL -> $REMOTE"
    git checkout origin/main
  fi
'

# Stage and commit updated pins
git add -A  # Only submodule refs change, safe here
git commit -m "chore: update submodule pins after cross-repo PR merges"
```

**Warning**: Only pin submodules whose `main` branch moved forward. Never pin to feature branch commits from unmerged PRs.

### Phase 6: Verification

```bash
# Verify all repos have no remaining open PRs (or only intentionally deferred ones)
for repo in $REPOS; do
  count=$(gh pr list --repo HomericIntelligence/$repo --state open --json number --jq 'length')
  [ "$count" -gt 0 ] && echo "REMAINING: $repo has $count open PRs"
done

# Verify Odysseus submodule pins are current
cd /home/mvillmow/Odysseus
git submodule foreach --quiet '
  git fetch origin main 2>/dev/null
  BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null)
  [ "$BEHIND" -gt 0 ] && echo "$name: $BEHIND commits behind origin/main"
'

# Verify Odysseus is clean
git status
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Parallel PR merges within same repo | Merged PRs #4, #5, #6 in parallel targeting the same branch | PR #6 got conflicts because its base changed when #4 and #5 merged | Must merge sequentially within a repo (oldest-first); parallelize only across repos |
| Using `--admin` flag to bypass CI | `gh pr merge --admin` to force-merge when branch protection blocks | User explicitly requested not using `--admin`, preferring proper CI flow | Respect CI gates; fix failures rather than bypassing them |
| First attempt at Charybdis merge | Attempted merge with failing CI | clang-format, clang-tidy, and coverage checks were failing | Must spawn a Sonnet agent to investigate and fix CI before merge is possible |
| Nestor PR rebase after other PRs merged | PR #3 in Nestor conflicted after other Nestor PRs merged to main | Base branch moved forward, invalidating the PR's diff | Always rebase onto fresh origin/main after each merge within the same repo |
| Pre-existing CI failures on main | Investigated Hephaestus Py3.10 test failure thinking it blocked Dependabot PR | Failure was pre-existing on main, unrelated to the Dependabot PR | Check if CI failures exist on main before attributing them to the PR |

## Results & Parameters

### Agent Tier Assignment

| Task | Agent Tier | Rationale |
|------|-----------|-----------|
| Merge clean PRs | Haiku | Mechanical: check status, run merge command |
| Fix merge conflicts | Sonnet | Requires understanding code context for rebase resolution |
| Fix CI failures | Sonnet | Requires reading logs, diagnosing issues, writing code fixes |
| Update submodule pins | Sonnet | Requires judgment about which submodules moved forward |
| Orchestrate waves | Opus | Top-level coordination, wave sequencing, escalation decisions |

### Wave Execution Model

```text
Phase 1: Scan          [Opus orchestrator]
  |
  v
Phase 2: Wave 1        [Haiku agents x N repos, parallel across repos]
  |                      Merge clean PRs, oldest-first within each repo
  v
Phase 3: Wave 1b       [Sonnet agents, parallel across repos]
  |                      Fix conflicts from Wave 1 merges
  v
Phase 4: Wave 1c       [Sonnet agents, parallel across repos]
  |                      Fix CI failures blocking remaining PRs
  v
Phase 5: Wave 2        [Sonnet agent, single]
  |                      Update Odysseus submodule pins
  v
Phase 6: Verify         [Opus orchestrator]
                         Confirm all repos clean, pins current
```

### Merge Ordering Rules

| Rule | Description |
|------|-------------|
| **Sequential within repo** | Merge PRs oldest-first to avoid conflicts from base changes |
| **Parallel across repos** | Different repos are independent; agents work simultaneously |
| **Rebase after each merge** | If multiple PRs target same repo, rebase remaining after each merge |
| **CI before merge** | Never bypass CI with `--admin`; fix failures properly |
| **Pins after all merges** | Update Odysseus submodule pins only after all repo PRs are merged |

### Session Scale Reference

| Scale | Agents | Estimated Time |
|-------|--------|----------------|
| 2-3 repos, 1-2 PRs each | 3 Haiku | ~10-15 min |
| 5 repos, 2-4 PRs each | 5 Haiku + 2 Sonnet | ~30-45 min |
| 10+ repos, mixed PRs | 6 Haiku + 4 Sonnet + pin agent | ~1-2 hours |

### Key Commands

```bash
# Scan all repos
gh repo list HomericIntelligence --limit 30 --json name --jq '.[].name'

# List open PRs for a repo
gh pr list --repo HomericIntelligence/$REPO --state open

# Merge a PR (prefer rebase, no --admin)
gh pr merge $PR_NUM --repo HomericIntelligence/$REPO --rebase

# Rebase a PR branch after conflicts
gh pr checkout $PR_NUM
git fetch origin main && git rebase origin/main
git push --force-with-lease

# Update submodule pin
git -C path/to/submodule fetch origin && git -C path/to/submodule checkout origin/main
git add path/to/submodule

# Check CI status
gh pr checks $PR_NUM --repo HomericIntelligence/$REPO
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence ecosystem | 5 repos (Agamemnon, Nestor, Keystone, Charybdis, Hephaestus) with open PRs, myrmidon swarm orchestration, 2026-04-04 | Wave 1: 4 Haiku agents merged clean PRs; Wave 1b: Sonnet agents fixed conflicts; Wave 1c: Sonnet agent fixed Charybdis CI; Wave 2: Odysseus submodule pins updated |

## References

- [multi-repo-pr-triage](multi-repo-pr-triage.md) -- CI failure diagnosis across repos (complements Phase 1c)
- [batch-pr-rebase-myrmidon-wave-execution](batch-pr-rebase-myrmidon-wave-execution.md) -- Single-repo wave execution (detailed conflict strategies)
- [batch-pr-rebase-conflict-resolution-workflow](batch-pr-rebase-conflict-resolution-workflow.md) -- Comprehensive rebase/conflict patterns
- [tooling-meta-repo-submodule-cleanup-swarm](tooling-meta-repo-submodule-cleanup-swarm.md) -- Submodule cleanup swarm (complements Phase 5)
- [ci-cd-cross-repo-skill-maintenance](ci-cd-cross-repo-skill-maintenance.history) -- Cross-repo coordinated PRs
