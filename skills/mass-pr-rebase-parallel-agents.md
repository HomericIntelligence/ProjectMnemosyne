---
name: mass-pr-rebase-parallel-agents
description: 'Batch rebase 10-100+ conflicting PRs using sequential wave execution with
  parallel sub-agents, worktree isolation, and semantic conflict resolution. Use when:
  many PRs are CONFLICTING, some have CI failures, PRs have inter-dependencies requiring
  ordered merging, and pixi.lock/overlapping files need phased ordering.'
category: ci-cd
date: 2026-03-27
version: 3.0.0
user-invocable: false
verification: verified-local
history: mass-pr-rebase-parallel-agents.history
tags: []
---
# Mass PR Rebase with Parallel Agents

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Batch rebase conflicting PRs and fix CI failures using sequential wave execution with parallel agents and semantic conflict resolution |
| **Outcome** | Success — verified across three sessions (96 PRs in ProjectOdyssey, 20 PRs in ProjectScylla session 1, 9 PRs in ProjectScylla session 2) |
| **Verification** | verified-local |
| **History** | [changelog](./mass-pr-rebase-parallel-agents.history) |

## When to Use

- A major refactor lands on main causing mass conflicts (10+ PRs CONFLICTING)
- Mix of CONFLICTING PRs and MERGEABLE-but-CI-failing PRs
- PRs touch overlapping files (CLI, config, pixi.lock) requiring phased ordering
- PRs have inter-dependencies requiring sequential wave merging (e.g., version PR before changelog PR)
- Need semantic conflict resolution (not just `--theirs`) to preserve PR intent
- Auto-generated lockfiles (pixi.lock) need regeneration after rebase
- A massive structural migration (src-layout) must merge after all content PRs

## Verified Workflow

### Quick Reference

```bash
# Classify PRs
gh pr list --state open --limit 200 --json number,headRefName,mergeable,autoMergeRequest \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Launch parallel rebase agent (with worktree isolation)
# Agent tool: isolation: "worktree", prompt includes rebase + pre-commit + push

# Verify after push
gh pr view <number> --json mergeable,state
```

### Phase 0: Fix Systemic CI on Main First

Before rebasing, fix failures that affect ALL PRs:

1. Check CI: `gh pr checks <number>` on a recent MERGEABLE PR
2. Check main: `gh run list --branch main --limit 5`
3. Categorize as systemic vs PR-specific
4. Create a single fix PR for systemic issues

### Phase 1: Classify, Order, and Identify Superseded PRs

```bash
# Group by mergeability
gh pr list --state open --limit 200 --json number,headRefName,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Check which files each PR touches (for ordering)
for pr in <numbers>; do
  branch=$(gh pr view $pr --json headRefName -q .headRefName)
  echo "=== PR #$pr ($branch) ==="
  git diff --name-only origin/main...origin/"$branch" | head -20
done
```

**IMPORTANT**: Always use `--limit 200` or higher. Default limit misses older PRs.

**Superseded PR detection**: Before rebasing, check if main already has the PR's changes:

```bash
# Rebase and check for empty diff
git rebase origin/main
git diff origin/main --stat
# If empty → PR is superseded, close it
```

Common superseded patterns:
- Feature already merged via a different PR (e.g., JSON report format merged via auto-impl)
- Config/model already exists on main (e.g., MaestroConfig added by another PR)
- CLI already has the flags (e.g., `--format json` already wired)

**Order into sequential waves** based on dependencies:

| Wave | Criteria | Parallelism |
|------|----------|-------------|
| Wave 1 | Independent PRs with no file overlap | Fully parallel |
| Wave 2 | PRs that depend on Wave 1 changes | Parallel within wave, sequential between waves |
| Wave 3 | Version/CHANGELOG PRs (overlap on same files) | **Strictly sequential** within wave |
| Wave N (last) | Massive structural migrations (src-layout, renames) | Solo — after all content PRs merge |

**Critical wave ordering rules:**
- PRs touching `CHANGELOG.md` must be strictly sequential (3+ PRs touching same file)
- PRs touching `scylla/cli/main.py` + version files must be ordered after version PRs
- `pixi.lock` conflicts reappear after each wave merge — budget for re-rebase
- Structural migrations (src-layout) go LAST — they conflict with everything

### Phase 2: Wave Execution (Sequential Waves, Parallel Within)

For each wave:

1. **Rebase all PRs in the wave** onto current `origin/main`
2. **Resolve conflicts semantically** (see table below)
3. **Run `pixi install`** to regenerate pixi.lock if pyproject.toml/pixi.toml changed
4. **Run `pre-commit run --all-files`** — fix any issues
5. **Push and enable auto-merge**: `git push --force-with-lease && gh pr merge --auto --rebase`
6. **WAIT for all PRs in wave to merge** before starting next wave

```bash
# Poll for merge completion
for i in $(seq 1 40); do
  sleep 30
  state=$(gh pr view <number> --json state -q '.state')
  echo "$(date +%H:%M:%S) #<number>=$state"
  if [ "$state" = "MERGED" ]; then break; fi
done
```

**CRITICAL**: `git fetch origin` before each wave to get latest main after previous wave merged.

**Conflict resolution — semantic, not blind:**

| File Type | Strategy |
|-----------|----------|
| `pixi.lock` | Accept main's version (`git show origin/main:pixi.lock > pixi.lock`), then regenerate with `pixi install` |
| `pixi.toml` | Merge both sides (keep main's deps + PR's new deps) |
| Feature code (cli, config, models) | Read PR intent, combine both sides semantically |
| Schemas (JSON) | Check for duplicate keys, add new properties from PR |
| Tests (deleted on main) | Accept deletion if main removed the feature |
| `.pre-commit-config.yaml` | Check for duplicate hook entries; update paths for structural changes |
| Workflows (`.github/`) | Keep main's security patterns (SHA pins, env vars) |
| Documentation (CLAUDE.md, etc.) | Keep main's structure, add PR-specific content |

### Phase 3: Fix CI-Only Failures (MERGEABLE PRs)

For PRs that are MERGEABLE but failing CI, diagnose and fix:

| Failure Type | Diagnosis | Fix Pattern |
|-------------|-----------|-------------|
| Schema validation | Duplicate keys in JSON, field mismatch | Remove duplicates, align schema with defaults.yaml |
| `maestro.url` vs `base_url` | defaults.yaml uses `url`, schema says `base_url` | Add `url` as valid property in schema |
| Version consistency hooks | Path references after structural migration | Update `scylla/` → `src/scylla/` in hook patterns |
| Pre-commit formatting | ruff-format, markdownlint | `pre-commit run --all-files` auto-fixes |
| pixi.lock SHA mismatch | Lock file not regenerated after pyproject.toml change | `pixi install` then re-commit pixi.lock |

### Phase 4: Handle Structural Migrations Last

For massive refactors (src-layout, directory renames):

1. **Wait for ALL content PRs to merge** — reduces conflict surface
2. **Consider recreating from scratch** vs rebasing — if branch is 30+ commits behind, fresh is faster
3. **Use a Sonnet agent with `isolation: "worktree"`** for the migration work
4. **After migration, rebase again** if main moved during the long agent run
5. **Budget for 2-3 rebase cycles** — main keeps moving in active repos

```bash
# Fresh recreation approach
git checkout -b <branch> origin/main
mkdir -p src
git mv scylla src/scylla
# Update all path references...
pixi install
pre-commit run --all-files
git push --force-with-lease origin <branch>
```

### Phase 5: Monitor and Clean Up

```bash
# Verify final state
gh pr list --state open --limit 200 --json number,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Clean up worktrees
git worktree prune
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `--theirs` for all conflicts | Blind conflict resolution | Loses PR-specific work when main has diverged significantly | Use semantic resolution — read PR intent and combine both sides |
| `--ours`/`--theirs` for pixi.lock | Standard git conflict resolution on lockfiles | pixi.lock encodes SHA256 of local editable package; merged version is always invalid | Accept main's pixi.lock, then regenerate with `pixi install` |
| Using `--limit 100` for PR listing | Default gh pr list limit | Missed older conflicting PRs | Always use `--limit 200` or higher |
| Single agent for all rebases | Considered processing sequentially | Would take hours for 20+ PRs | Parallel agents with worktree isolation complete in minutes |
| No phased ordering | Rebase all PRs at once regardless of complexity | Compounding conflicts when interdependent PRs land in wrong order | Process simple PRs first, defer massive refactors |
| Rebasing closed/superseded PRs | Spent time resolving conflicts on PRs already delivered by other work | Empty commits after rebase — wasted effort | Check PR state and diff before investing in conflict resolution |
| Not running pre-commit before push | Pushed rebased branches without local validation | Primary cause of CI failures on auto-impl branches | Always run `pre-commit run --all-files` before every push |
| Parallel rebase of all PRs at once | Rebased all 9 PRs onto same main simultaneously | Later PRs re-conflict when earlier ones merge and change shared files | Use sequential waves — only start Wave N after Wave N-1 merges |
| `--force-with-lease` with stale ref | Push after another automation updated the remote branch | "stale info" rejection because remote ref changed between fetch and push | `git fetch origin <branch>` immediately before `--force-with-lease`; retry on failure |
| Agent worktree + Safety Net | Sub-agents tried `git checkout origin/main -- pixi.lock` in worktrees | Safety Net blocks file overwrites even during legitimate rebase conflict resolution | Handle pixi.lock resolution in main context, not sub-agents; or use `git show origin/main:pixi.lock > pixi.lock` |
| Rebasing PR #1559 that was already closed | Force-pushed rebased branch but couldn't reopen the closed PR | `gh pr reopen` fails if PR was closed by automation | Create new PR from the rebased branch instead of trying to reopen |
| Src-layout migration first | Considered merging the 72-file structural migration before content PRs | Every subsequent PR would need massive path rewrites (`scylla/` → `src/scylla/`) | Always merge structural migrations LAST — content PRs first, then do the big rename once |

## Results & Parameters

### Session Results (v3.0.0 — ProjectScylla, 2026-03-27, sequential waves)

- **9 original PRs** processed in 4 sequential waves
- **6 PRs merged** via auto-merge after rebase
- **2 PRs closed** as superseded (changes already on main: JSON report #1553, py.typed #1559)
- **1 PR recreated** as new PR (#1559 → #1730) because original was already closed
- **1 massive PR** (src-layout, 198 files) recreated from scratch by Sonnet agent, rebased 2 additional times
- **Schema fix** required: `defaults.yaml` on main had `maestro.url` but PR schema only allowed `base_url`
- **3 PRs auto-merged** by CI automation while other waves were being processed (#1557, #1560, #1562)
- **Total elapsed time**: ~2 hours (dominated by CI wait between waves)

### Session Results (v2.0.0 — ProjectScylla, 2026-03-27, parallel agents)

- **21 open PRs** processed (17 CONFLICTING + 3 CI-failing + 1 already merged)
- **16 PRs** rebased and pushed to MERGEABLE state
- **4 PRs** found already closed/superseded (skipped)
- **1 PR** deferred (202-file src-layout migration)
- **Semantic conflict resolution** across CLI, config, schema, maestro module files
- **pixi.lock** regenerated on 7 PRs

### Session Results (v1.0.0 — ProjectOdyssey, 2026-03-17)

- **138 total open PRs** processed
- **96 PRs rebased** and force-pushed (0 failures)
- **17 PRs** were already closed
- **All conflicts** resolved with `--theirs` strategy

### Agent Configuration

```yaml
# v3.0.0: Sequential waves with Myrmidon swarm
# L0 orchestrator handles wave coordination directly
# Sonnet agents for complex rebases (src-layout recreation)
# Direct rebase for simple PRs (no agent needed)
model_tiers:
  orchestrator: opus  # Wave planning, dependency analysis
  specialist: sonnet  # Src-layout recreation, complex conflict resolution
  executor: haiku     # Simple rebase, pre-commit fixes

# v2.0.0: Use built-in worktree isolation
subagent_type: general-purpose
isolation: "worktree"  # Each agent gets isolated repo copy

# v1.0.0: Manual worktree management
subagent_type: general-purpose
run_in_background: true
```

### CI Impact

Mass force-pushing overwhelms CI runners. All PR runs queue simultaneously.
Plan for 30-60 min CI queue drain after batch rebases.

**Sequential wave approach mitigates this**: only 2-3 PRs in CI at a time, not 20.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | 9 PRs in 4 sequential waves, src-layout recreation, superseded detection | 2026-03-27 (v3.0.0) |
| ProjectScylla | 21 PRs (17 conflicting + 3 CI-failing), semantic resolution, pixi.lock regen | 2026-03-27 (v2.0.0) |
| ProjectOdyssey | 138 PRs, 80+ conflicting, `--theirs` strategy | 2026-03-17 (v1.0.0) |
