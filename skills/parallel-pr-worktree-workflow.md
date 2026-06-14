---
name: parallel-pr-worktree-workflow
description: "Use when: (1) launching 2+ parallel rebase agents that need isolated git state to avoid branch collision, (2) implementing 5+ independent fixes in parallel PRs using git worktrees, (3) bulk-merging skill PRs with CI fixes and conflict resolution, (4) batching 10+ PRs across parallel sub-agents for maximum throughput, (5) launching >=2 concurrent sub-agents that each commit/push to the same git repo, (6) sub-agents report file bleed-over or unexpected `git checkout` reverts mid-task, (7) RESCUE pattern when parallel dispatch across distinct branches has already produced cross-contaminated commits — consolidate worker PRs into ONE branch via cherry-pick and close individual PRs, (8) doing ANY multi-fix work in a shared checkout that a concurrent foreign session/automation may also touch — use dedicated worktrees from the start so a foreign session cannot move your HEAD/branch."
category: ci-cd
date: 2026-06-13
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: parallel-pr-worktree-workflow.history
tags: []
---
# Parallel PR Worktree Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Parallel workflow tooling pattern — git worktrees for agent isolation, batching PRs per agent, bulk PR triage and merge |
| **Outcome** | Consolidated from 4 source skills |

**See also:** `tooling-stage-only-your-own-files-in-shared-worktree` (the staging-scope companion
when a worktree is shared or dirty), `git-worktree-parallel-execution-lifecycle`, and
`parallel-agent-swarm-dispatch-patterns`.

## When to Use

- Launching 2+ background agents to mass-rebase branches in parallel (each needs isolated git state)
- Agents use `git switch`/`git checkout` and would leave rebase-in-progress state in shared working tree
- Safety Net blocks `git branch -D` or `git reset --hard` in the shared working tree
- Implementing 5+ independent fixes in parallel, each with its own PR
- Bulk-merging accumulated skill PRs (10+) with a mix of passing/failing CI
- Main conversation needs to commit while background agents are running
- Issues are independent (not interdependent) and benefit from parallel development
- **(v1.3.0, verified-local)** ANY other session/automation may touch the shared checkout — do ALL multi-fix work in dedicated worktrees from the start, never in the primary checkout. A concurrent foreign session can move your branch and commit under you (see Phase 3c)

**Do NOT use when:**
- Issues are interdependent (use sequential PRs from `batch-pr-rebase-conflict-resolution-workflow`)
- Codebase is unstable (fix stability first)
- Limited CI resources (parallel PRs can overwhelm CI)
- Single sub-agent on a short task: the worktree setup overhead isn't worth it; just use the parent repo
- Sub-agents that are pure-research (no commits): no isolation needed
- A sub-agent that legitimately needs to read other branches' state: use the parent repo. Worktrees are for write isolation, not read

## Verified Workflow

### Quick Reference

```bash
# Create worktree for agent isolation
git worktree add worktrees/<name> <branch>

# Agent batch split (example for 13 PRs)
# Batch 1: 4 PRs → agent with worktrees/rebase-batch1
# Batch 2: 4 PRs → agent with worktrees/rebase-batch2
# Batch 3: 3 PRs → agent with worktrees/rebase-batch3

# Cleanup
git worktree remove worktrees/<name>
git worktree prune
```

### Phase 1: Triage PRs into Groups

```bash
# List all open PRs with CI status
gh pr list --state open --json number,title,headRefName,mergeStateStatus --limit 100

# Check individual PR checks
gh pr checks <PR_NUMBER>
```

Identify:
- **Group A (immediate)**: PRs with passing CI → merge immediately
- **Group B (fix needed)**: PRs with failing CI → fix first, then merge
- **Group C (rebase needed)**: PRs with DIRTY/CONFLICTING state → rebase first

Order Group A by PR number (oldest first) to minimize rebase conflicts:
```bash
for pr in <PR_NUMBERS_IN_ORDER>; do
  echo "=== Merging PR #$pr ==="
  gh pr merge $pr --rebase --delete-branch 2>&1
done
```

**Note**: With `strict: false` on branch protection, PRs don't need to be up-to-date with main before merging. Merge all without rebasing between each one.

**Watch for**: `GraphQL: Pull Request is not mergeable` — PR became conflicted during batch. Handle in Phase 4.

### Phase 2: Plan Dependency Groups for Parallel Work

When implementing multiple independent fixes in parallel:

```
Group A (parallel from main — no dependencies):
  - PR1: Independent fix A
  - PR2: Independent fix B
  - PR3: Independent fix C

Group B (after Group A merges — pull updated main first):
  - PR4: Depends on PR1
  - PR5: Depends on PR2
```

**Key decision**: Group issues by dependencies to maximize parallelism while maintaining correctness. Wait for dependencies to merge before creating dependent worktrees.

### Phase 3: Worktree Setup for Parallel Implementation

```bash
# Pull latest main
git checkout main && git pull

# Create worktrees for Group A (all parallel from same main)
git worktree add worktrees/fix-issue-123 -b issue-123-fix-config main
git worktree add worktrees/fix-issue-124 -b issue-124-remove-dead-code main
git worktree add worktrees/fix-issue-125 -b issue-125-update-docs main

# After Group A merges, create Group B worktree from updated main
git checkout main && git pull
git worktree add worktrees/fix-issue-126 -b issue-126-depends-on-pr1 main
```

**Critical:** Always create worktrees from the correct base branch. For dependent PRs, wait for the dependency to merge and pull main first.

**Always place worktrees inside `worktrees/` subdirectory** (per repo convention):
```
worktrees/rebase-batch1/   ← batch 1 agent
worktrees/rebase-batch2/   ← batch 2 agent
worktrees/fix-pr-rebase/   ← main conversation overflow work
```

### Phase 3b (v1.3.0, verified-local): Prereq-Stacking for a Fan-Out Sharing a Common Blocker

**Use this when** a fan-out of N independent fixes all share a common prerequisite — e.g. a
repo-wide format-drift fix that otherwise blocks *every* commit (pre-commit reformats files you
didn't touch). Branching all N off `main` first means every commit is blocked by the unfixed
shared prerequisite.

Pattern (this is how 6 fixes shipped cleanly as a stack in ProjectHephaestus, 2026-06-13):

1. **Land the prerequisite as its OWN branch/PR FIRST.** This is the shared blocker fix.
2. **Branch each fix worktree off the PREREQUISITE branch**, not `main`:

   ```bash
   git fetch origin
   git worktree add /tmp/<repo-stem>-wt-fixA -b <fixA-branch> origin/<prereq-branch>
   git worktree add /tmp/<repo-stem>-wt-fixB -b <fixB-branch> origin/<prereq-branch>
   ```

3. **Target each fix PR at the prereq branch:**

   ```bash
   gh pr create --base <prereq-branch> --title "..." --body "...Depends on #<prereq-pr>..."
   ```

   GitHub **auto-retargets** the fix PRs to `main` once the prereq merges — no manual rebase
   needed for the common case.
4. **A fix that itself depends on ANOTHER fix** (e.g. it reuses a helper the other fix adds) is
   branched off THAT fix's branch instead of the prereq branch, and its PR targets that fix's
   branch with `--base <other-fix-branch>`.
5. **Document the dependency in each PR body** (`Depends on #<n>`) so reviewers and auto-retarget
   logic stay coherent.

This keeps every commit green: the prereq is already present in each fix's base, so pre-commit
and CI don't trip over the shared blocker.

### Phase 3c (v1.3.0, verified-local): Recovery — Work Tangled on the Wrong Branch (Foreign-Session Hijack)

**Symptom:** while implementing fixes directly in the MAIN repo checkout (not a worktree), a
SEPARATE automation/agent session running in the same repo committed to the working directory and
switched the branch out from under you. `git branch --show-current` returns a branch you didn't
switch to; a HEAD commit by a different author appears (the other session opened its own PR); your
staged changes are intact but on the wrong branch.

**Root cause:** branch state IS the working tree. The primary checkout shares one HEAD/index; any
concurrent session can move it. A worktree gives you an independent HEAD/index a foreign session
cannot move — so the durable fix is to never do multi-fix work in the primary checkout (Phase 3 /
3b). The patch-export below is the recovery when you're already tangled.

```bash
# 1. Export your staged diff to a patch — this is your safety net
git diff --cached > /tmp/work.patch

# 2. Clean the hijacked branch: unstage, then stash (recoverable — do NOT git checkout --)
git restore --staged .
git stash push -- <your-files>        # NOT `git checkout -- <files>` (Safety Net blocks it)

# 3. Create the correct branch in a FRESH worktree off the intended base
git fetch origin
git worktree add /tmp/<repo-stem>-wt-recover -b <correct-branch> origin/<intended-base>
cd /tmp/<repo-stem>-wt-recover

# 4. Verify the patch applies cleanly, THEN apply it
git apply --check /tmp/work.patch     # dry run first
git apply /tmp/work.patch

# 5. Commit on the correct branch
git add -A && git commit -S -m "..."
```

The patch is the safety net; combined with the stash, nothing is lost. Leave the stash undropped
(see Safety-Net Friction below) rather than forcing `git stash drop`.

### Phase 4: Agent Isolation for Parallel Rebase

When launching parallel agents to rebase many PRs, each agent MUST get its own worktree:

**Key instruction to include in each agent prompt:**
```
CRITICAL: Use a dedicated git worktree to avoid colliding with other agents.

Create your worktree FIRST before doing any rebase work:
  git worktree add worktrees/rebase-batch-N <stable-branch>
  cd worktrees/rebase-batch-N

Do ALL rebase work from inside the worktree. When done:
  cd /path/to/repo
  git worktree remove worktrees/rebase-batch-N
```

**Optimal batching strategy**:
```yaml
# Batch 3-4 PRs per agent (sequential within agent, parallel across agents)
# Avoids excessive agent spawn overhead (5-agent-per-wave limit)
agents: 4
prs_per_agent: 3-4
total_prs: 13
waves: 1  # All agents launch simultaneously
```

**Temp branch naming convention** (use unique batch ID to avoid collision):
```
Batch 1 agent: tmp-b1-<issue-number>
Batch 2 agent: tmp-b2-<issue-number>
Main conversation: tmp-<issue-number>
```

#### Sub-Agent Brief Template (Wave Orchestration)

When launching N concurrent sub-agents that each commit and push from the same repo:

```bash
# Per concurrent sub-agent: create an isolated worktree off the integration base
git -C <repo> fetch origin
git -C <repo> worktree add -B <feature-branch> /tmp/<repo-stem>-wt-<task> origin/<integration-base>
```

Brief the sub-agent with the worktree path explicitly:

```
Your dedicated working directory is /tmp/<repo-stem>-wt-<task>.
All git operations must happen inside that directory.
Do NOT touch <parent-repo-path> or any other /tmp/<repo-stem>-wt-* worktree —
those are concurrent sub-agents.

Open the PR with: gh pr create --base <integration-base> ...
Then arm auto-merge: gh pr merge --auto --squash
```

**Brief sizing**: ~80-120 line prompts per sub-agent work well. Less than ~50 lines and the agent guesses; more than ~150 and it skims. Always include in the brief: explicit worktree path, explicit "do NOT touch other worktrees" warning, the `--base <integration-base>` invocation, the auto-merge command, and the verification commands (test + lint + security scan).

#### Integration Base Branch Pattern

For long PR series (10+ PRs across waves):

1. Establish ONE integration base branch that all parallel PRs target (e.g. `fix/<area>-v0.X.Y-<theme>`).
2. Each PR opens with `--base <integration-base>` and auto-squash-merges into it.
3. The integration base merges to `main` once at the end via a single review.

This avoids N separate PRs each requiring their own main rebase as concurrent merges land.

#### Trust-but-Verify Sub-Agent Reports

After every sub-agent reports done, the integrator (parent session) MUST verify against the GitHub API. Sub-agent reports describe intent; the API tells you reality:

```bash
gh pr view <#> --repo <org/repo> \
  --json state,mergedAt,baseRefName,additions,deletions,files,mergeable,mergeStateStatus \
  --jq '{state, mergedAt, base: .baseRefName, mergeable, mergeStateStatus, additions, deletions, files: [.files[].path]}'
```

This single call confirms scope (no surprise files), merge state, and conflict status. If `mergeable: CONFLICTING`, a concurrently-merged PR rewrote a line your branch also touched. Resolve in the worktree: `cd /tmp/<path> && git rebase origin/<integration-base>`, force-push, re-arm auto-merge.

#### Submodule Wrinkle

`git -C <submodule-path> worktree add` works correctly but `git worktree list` shows the worktree under `.git/modules/<submodule>/...` rather than the visible submodule path. The submodule's `.git` is a `gitdir:` indirection file pointing into the parent's modules dir. This is fine — don't be surprised by the list output, and use the visible submodule path when scripting `git -C` commands.

#### Per-PR Worktree Cleanup

After each PR merges, tear down its worktree:

```bash
git -C <repo> worktree remove --force /tmp/<repo-stem>-wt-<task>
git -C <repo> worktree prune
```

Cleanup is cheap. Re-creating a worktree from `origin/<base>` takes seconds and gives a clean state. Do NOT reuse a worktree path across sub-agents — give each sub-agent its own.

#### Dispatch Hygiene (v1.3.0, verified-local)

The dispatch shape that shipped 5 root-cause fixes in parallel with zero cross-contamination
(ProjectHephaestus, 2026-06-13):

- **One issue + one worktree + one sub-agent per independent fix.** Do not multiplex.
- **Create all worktrees UP FRONT** before launching any agent:
  `git worktree add <dir> -b <branch> <base>` for each fix.
- **Launch all sub-agents in ONE message** for true concurrency (one tool block, N agent calls).
- **Each agent's brief gets:** its worktree path, the issue number, the base branch (the
  prereq/stack base from Phase 3b, not always `main`), the exact root-cause trace, and the shared
  rules — signed commit (`git commit -S`), `Closes #N` in the PR body, NEVER `--no-verify`, do
  NOT pre-arm auto-merge before the repo's go-label gate if it has one, and the stacked-PR `--base`.

All 5 agents succeeded in parallel because each had an isolated worktree — the path IS the
isolation boundary.

#### Safety-Net Friction to Expect (v1.3.0, verified-local)

A CC Safety Net may BLOCK these as destructive. Plan recovery around the safe alternatives:

| Blocked command | Safe alternative | Why it's safe |
| ----------------- | ------------------ | --------------- |
| `git checkout -- <files>` | `git stash push -- <files>` | Stash is recoverable; checkout discards |
| `git branch -D <branch>` | `git branch -d <branch>` | Safe-delete; works when the branch has no unmerged unique commits |
| `git stash drop` | leave the stash undropped | Avoids forcing a destructive op; stashes are cheap to keep |

### Phase 5: Implementation Pattern (Per Worktree)

For each worktree implementing a fix:

```bash
cd worktrees/fix-issue-123

# 1. Make focused changes (only the issue in this PR — no scope creep)

# 2. Run pre-commit hooks
pre-commit run --all-files
# OR: pixi run pre-commit run --all-files

# 3. Run relevant tests
pixi run pytest tests/unit/path/to/relevant -v

# 4. Stage auto-fixed files if pre-commit made changes
git status --short
git add <changed-files>

# 5. Commit with conventional commits
git commit -m "type(scope): brief description

Fixes #123

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# 6. Push and create PR with auto-merge
git push -u origin issue-123-fix-config
gh pr create \
  --title "type(scope): Brief description" \
  --body "Closes #123

## Summary
Brief explanation

## Changes
- Change 1

## Verification
Tests pass, pre-commit hooks pass"

# 7. Enable auto-merge (CRITICAL for parallel workflow)
gh pr merge --auto --rebase
```

### Phase 6: Rebase Per-PR Inside Worktree (For Rebase Agents)

```bash
cd worktrees/rebase-batch-N

for entry in "4833 3937-auto-impl" "4836 3940-auto-impl"; do
  pr=$(echo $entry | cut -d' ' -f1)
  branch=$(echo $entry | cut -d' ' -f2)

  git fetch origin $branch -q
  git switch -c tmp-b1-$pr origin/$branch -q

  result=$(git rebase origin/main 2>&1)
  if echo "$result" | grep -q "CONFLICT"; then
    echo "CONFLICT PR#$pr - needs manual resolution"
    git rebase --abort
  else
    git push --force-with-lease origin HEAD:$branch -q && echo "OK PR#$pr"
  fi

  git switch <stable-branch> -q
  git branch -d tmp-b1-$pr 2>/dev/null
done
```

Conflict resolution strategies — see `batch-pr-rebase-conflict-resolution-workflow` for full details.

### Phase 7: Fix Group B — Common CI Failures in Skill PRs

#### Common failure: Missing `plugin.json`

```bash
git switch skill/<category>/<name>
```

Create `.claude-plugin/plugin.json` using the SKILL.md frontmatter as source:

```json
{
  "name": "<from SKILL.md frontmatter>",
  "version": "1.0.0",
  "description": "<from SKILL.md frontmatter>",
  "category": "<from directory path>",
  "tags": ["<relevant>", "<tags>"],
  "date": "<from SKILL.md frontmatter>",
  "user-invocable": false
}
```

#### Common failure: Missing `version` field
Add `"version": "1.0.0"` to the existing `plugin.json`.

#### Common failure: Invalid category
Valid categories: `architecture`, `ci-cd`, `debugging`, `documentation`, `evaluation`, `optimization`, `testing`, `tooling`, `training`

```bash
# Edit plugin.json and SKILL.md frontmatter, then:
git add <files>
git commit -m "fix: change invalid category '<wrong>' to '<valid>'"
git push
```

### Phase 8: Identify Required Checks Before Diagnosing Failures

After rebase, CI often fails for reasons beyond staleness:

```bash
# ALWAYS identify required checks first
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'

# Only fix required checks — non-required failures (e.g., Docker pull errors) don't block merge
gh run view <run-id> --log-failed 2>&1 | grep "error:" | head -10
```

Failure categories:
- **Build errors**: Missing trait methods, type mismatches, duplicate functions, docstring format
- **Pre-commit**: Formatting changes (trailing lines, line length), grandfathered file lists
- **Security scans**: Action config differences (detect vs protect mode, exit-code flags)

CI checks run sequentially — later checks only run after earlier ones pass. Expect 2-3 fix rounds.

### Phase 9: Handle "Branch Already Used by Worktree" Error

When main conversation tries to switch to a branch locked by a background agent's worktree:

```bash
# Error: fatal: 'fix-baseline-ci-errors' is already used by worktree at '...'

# Option A: Create separate worktree for your own work
git worktree add worktrees/main-work origin/my-branch

# Option B: Work directly in the agent's worktree path
cd worktrees/rebase-batch2  # do your commit here
cd /repo
```

### Phase 10: Monitor CI and Handle Iterative Fix Loops

Each fix round can expose new failures (build fix reveals pre-commit issue; pre-commit fix reveals security issue):

```bash
# Monitor all PRs
gh pr list --author "@me" --state open --json number,title,statusCheckRollup \
  --jq '.[] | {number, title, status: (.statusCheckRollup | map(.conclusion) | unique)}'

# When CI fails — go to failing PR's worktree, fix, push
cd worktrees/fix-issue-123
# ... make changes ...
git add <files>
git commit -m "fix: address CI failure"
git push
# Auto-merge will trigger once CI passes
```

### Phase 10b (v1.2.0): RESCUE — Consolidate Cross-Contaminated Worker PRs into One

**Use this when** parallel dispatch across N distinct branches (e.g., haiku/sonnet swarm on
EASY-tier issues) has already produced cross-contaminated commits — multiple agents committed
to whichever branch the parent repo's working tree had checked out instead of their own
assigned worktree branch. Symptom: sibling agents report `please run git restore CLAUDE.md`,
or `git log` on each worker branch shows commits from sibling agents' work.

**Foundation:** ProjectOdyssey Phase G EASY-tier swarm consolidation, PR #5363 (2026-05-09).
Eight worker PRs (one per EASY-tier issue) collapsed into a single consolidated branch.
67/68 substantive checks green. Result: 8 issues closed via one PR, individual worker PRs
closed-not-merged.

**Step 1 — Audit each worker branch's commits:**

```bash
for pr in <worker-prs>; do
  branch=$(gh pr view "$pr" --json headRefName --jq '.headRefName')
  echo "=== PR #$pr ($branch) ==="
  git fetch origin "$branch" --quiet
  git log --oneline "origin/$branch" "^origin/main"
done
```

Identify which commits belong to which worker. If commits are tangled (worker A's commit
appears on worker B's branch), pick the commits intended for the consolidated PR.

**Step 2 — Create consolidation branch:**

```bash
git checkout main && git pull --ff-only
git checkout -b <epic>-consolidated
```

**Step 3 — Cherry-pick the intended commits:**

```bash
for branch in <worker-1-branch> <worker-2-branch> ... <worker-N-branch>; do
  git fetch origin "$branch" --quiet
  # Pick the head commit (most workers had a single squashable change)
  git cherry-pick "origin/$branch"
  # If conflict: resolve, run pre-commit, git cherry-pick --continue
done
```

For workers whose pushed branch contained multiple commits (one good, one accidentally
from sibling): use `git cherry-pick <specific-sha>` rather than the branch tip.

**Step 4 — Open ONE consolidated PR with all `Closes #N` lines:**

```bash
gh pr create --title "feat(<epic>): consolidate EASY-tier batch (N issues)" \
  --body "$(cat <<'EOF'
## Summary

Consolidates N worker PRs into one branch after parallel-dispatch branch contamination.

Closes #A
Closes #B
Closes #C
Closes #D
...

## Why one PR

Parallel `Task isolation=worktree` agents on N distinct branches cross-contaminated each
other's branches via shared parent `.git/index`/`HEAD`. Cherry-picking each worker's
intended commit into a single consolidated branch is the recovery path.

## Verification

- All N original issue acceptance criteria satisfied (see individual file diffs)
- pre-commit run --all-files: green
- CI: <X>/<Y> substantive checks green
EOF
)"
```

**Use separate `Closes #N` lines, not comma-separated** (GitHub only auto-closes the first
when comma-separated).

**Step 5 — Close individual worker PRs with reference to consolidated PR:**

```bash
for pr in <worker-prs>; do
  gh pr close "$pr" --comment "Consolidated into #<consolidated-pr> via cherry-pick. Closing as not-merged."
done
```

**Step 6 — Enable auto-merge on the consolidated PR:**

```bash
gh pr merge <consolidated-pr> --auto --squash
```

**Decision: when to consolidate vs re-dispatch?**

| Condition | Action |
|-----------|--------|
| Worker commits are clean and on correct branches | Merge each worker PR independently |
| 1-2 workers contaminated, others clean | Force-push corrected branches; merge individually |
| 3+ workers contaminated OR commits tangled | **Consolidate via cherry-pick** (this phase) |
| Worker commits are unrecoverable (wrong file edits) | Discard branches, re-dispatch SERIALLY |

### Phase 11: Cleanup

```bash
# After all PRs merge, remove all worktrees
for wt in worktrees/rebase-batch1 worktrees/rebase-batch2; do
  git worktree remove $wt 2>/dev/null || true
done

# Prune stale references
git worktree prune

# Verify clean state
git worktree list  # Should show only main repo

# Pull all merged changes
git checkout main && git pull
```

Close any orphaned issues:
```bash
gh issue close <issue-number> --comment "Fixed in PR #<number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Launch 2 parallel agents without worktree isolation | Both agents used the same working tree, switching branches with `git switch` | Agents left stale rebase-in-progress state (`.git/rebase-merge/`) from each other's abandoned rebases; commits landed on wrong branches | Always assign each parallel rebase agent a dedicated `git worktree` |
| `git branch -D` to delete temp branches | Safety Net hook blocked force-delete | Safety Net treats `-D` as destructive | Use `git branch -d` (safe delete); verify content is on remote before asking to force-delete |
| `git reset --hard origin/<branch>` to sync | Safety Net blocked the command | `reset --hard` is classified as destructive | Use `git pull --rebase origin/<branch>` instead |
| Commit while batch agent was switching branches | Commit landed on `tmp-rebase-3956` instead of `fix-baseline-ci-errors` | Agent switched branches between our `git add` and `git commit` | When agents are switching branches in shared worktree, do your work in a separate worktree |
| Agent used same temp branch prefix as other agent | Two agents used same temp branch names (`tmp-r2-*`) | First agent created `tmp-r2-4096`, second agent tried to create same name | Include unique batch ID in temp branch prefix: `tmp-b1-<N>`, `tmp-b2-<N>` |
| Spawned agents while parent was in plan mode | Agents completed analysis but couldn't execute any writes | Plan mode is INHERITED by sub-agents — they can only read files | Always exit plan mode BEFORE spawning execution agents |
| Creating all worktrees upfront | Created all 14 worktrees at the start | Some PRs depended on others; had to rebase worktrees later | Create worktrees in dependency groups; wait for dependencies to merge |
| Editing files without reading them first | Edit tool failed: "File has not been read yet" | Edit tool requires reading files first to establish context | Always Read before Edit |
| Not updating test mocks after code changes | PR failed CI because tests expected old behavior | Changed production code but forgot to update corresponding tests | After changing code, grep for related tests and update expectations |
| Pre-commit hook auto-fixes | Committed code; pre-commit auto-fixed formatting causing commit to fail | Hook modified files after staging but before commit | Run `pre-commit run --all-files` manually first, then `git add -A`, then commit |
| Round 1 rebase-only (no code verification) | Simple rebase and push for all 10 PRs | 9/10 failed CI — rebasing alone didn't fix code issues in PR branches | Rebase fixes staleness but not code correctness; verify compilation after rebase |
| Assumed Docker test failures blocked merge | Investigated Docker pull errors affecting all PRs | These weren't required checks — PR merged despite Docker failures | Always check `required_status_checks` first before investigating failures |
| gitleaks action with default mode | PR switched from manual gitleaks binary to `gitleaks-action` | Action defaults to `protect` (git-log) scan mode, finding historical secrets | When replacing a CI tool with its GitHub Action equivalent, match the scan mode/flags exactly |
| Grandfathered file list missing entries | Added test-count guard hook with allowlist | Missed `DISABLED_test_batchnorm.mojo` which has 14 tests | When adding validation hooks, run against ALL files first to build a complete allowlist |
| 1 PR per agent for 13 PRs | Spawned 13 individual agents | Excessive agent spawn overhead; 5-agent-per-wave limit means 3 waves minimum | Batch 3-4 PRs per agent (sequential within agent) — 4 agents handle 13 PRs in 1 wave |
| Sequential PRs instead of parallel | Processed all PRs one at a time | 3-4x slower than parallel worktree approach | Use git worktrees + auto-merge for 5+ independent fixes |
| Wave-1 shared tree across two sub-agents | Two sub-agents (CI hygiene + rollback runbook) both ran `git checkout` on the same physical clone | Sub-agent A's `git checkout` reverted sub-agent B's working tree mid-edit. B reported "the working tree was twice reverted to the parent branch's state (a different process switched branches)" and had to commit defensively after each edit, then `git reset --soft HEAD~2 && commit` to merge them | Two `git checkout` operations on the same working tree race. Branch state IS the working tree. Always assign per-sub-agent worktrees, NEVER share |
| Trusting sub-agent "auto-merge armed" reports without API verification | Took the sub-agent at its word that auto-merge was set | One PR reported "auto-squash armed" but was actually `mergeable: CONFLICTING` because a concurrent PR had rewritten the same lines. The repo also forbids rebase merges; what looked like "armed" was a no-op error | Always `gh pr view <#> --json mergeable,mergeStateStatus,state` after a sub-agent reports done. Sub-agents narrate intent; the API tells you reality. If rebase-merge is forbidden, use `--squash` |
| Skipping per-PR worktree cleanup | Left worktrees around after PRs merged thinking they'd be reused | Disk usage grew (each worktree is a full ~170-file copy) and stale branch tips accumulated | Cleanup is cheap (`worktree remove --force` + `worktree prune`) and re-creating a worktree from `origin/<base>` takes seconds. Tear down per PR |
| Brief too short (<50 lines) | Sent compact prompts to sub-agents to "save tokens" | Sub-agent guessed at file paths, branch names, integration base; ~30% rework rate | ~80-120 line briefs hit the sweet spot. Include explicit worktree path, "don't touch other worktrees" warning, exact `--base` flag, auto-merge command, and verification commands |
| Reusing worktree path across sub-agents | Removed worktree A after agent A finished, gave agent B the same path | Subtle git-state contamination from leftover index/refs even after `worktree remove` | Each sub-agent gets a unique path. The path IS the isolation boundary; the branch is just a label |
| Trying to salvage 8 cross-contaminated worker PRs by force-pushing each branch separately (ProjectOdyssey #5363) | After parallel haiku/sonnet swarm contaminated each other's branches via shared parent `.git/`, attempted per-branch cleanup with selective `git reset` and force-push | Commits were tangled across branches — fixing one branch broke another; cleanup was O(N^2) | Consolidate ALL worker commits into ONE branch via cherry-pick (Phase 10b), open a single PR with multiple `Closes #N` lines, and close worker PRs with a reference comment |
| Implement multi-fix work directly in the shared main checkout (ProjectHephaestus, 2026-06-13, verified-local) | Made fixes in the primary repo checkout instead of a worktree while a separate automation/agent session was active in the same repo | The concurrent foreign session committed and switched the branch out from under the work — staged changes landed on the wrong branch and a foreign commit appeared (the other session opened its own PR) | Always use a dedicated worktree per fix from the start; the worktree's independent HEAD/index cannot be moved by a foreign session. Recover via `git diff --cached > patch` + stash + fresh worktree + `git apply` (Phase 3c) |
| Branch all N fixes off main when they share a common blocker (ProjectHephaestus, 2026-06-13, verified-local) | Created all N fix worktrees off `main` when every fix needed the same prerequisite (a repo-wide format-drift fix) | Every commit was blocked by the unfixed shared prerequisite — pre-commit reformatted untouched files and failed each commit | Land the prerequisite as its OWN PR first, branch each fix off the prereq branch, target each PR with `--base <prereq-branch>`; GitHub auto-retargets to main once the prereq merges (Phase 3b) |

## Results & Parameters

### Key Commands Reference

```bash
# Check current worktrees
git worktree list

# Create worktree
git worktree add worktrees/<name> <branch>

# Remove worktree
git worktree remove worktrees/<name>
git worktree prune

# Check required status checks
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'

# Monitor all open PRs
gh pr list --state open --json number,title,mergeStateStatus --limit 100

# Enable auto-merge
gh pr merge --auto --rebase

# Merge with delete
gh pr merge <number> --rebase --delete-branch

# Verify all target PRs merged
for pr in <SPACE_SEPARATED_PR_NUMBERS>; do
  echo "PR #$pr: $(gh pr view $pr --json state --jq '.state')"
done
```

### Agent Configuration

```yaml
# Optimal for parallel rebase with worktree isolation
subagent_type: general-purpose
isolation: "worktree"  # Each agent gets isolated repo copy (automatic)
# OR manual: agent creates worktrees/rebase-batchN before doing any work

# Batch sizing
agents: 4
prs_per_agent: 3-4  # Sequential within agent
total_prs: 13
waves: 1  # All agents launch simultaneously

# Model tiers (Myrmidon swarm)
orchestrator: opus   # Wave planning, dependency analysis
specialist: sonnet   # Complex conflict resolution
executor: haiku      # Simple rebase, pre-commit fixes
```

### Parallel PR Efficiency Metrics

| Method | PRs | Time | CI Overhead |
| -------- | ----- | ------ | ------------- |
| Sequential PRs | Any | 3-4x baseline | Minimal |
| Parallel worktrees (independent) | 5-9 | 70% faster | Parallel CI runs |
| 4 parallel agents (3-4 PRs each) | 13 | ~7 minutes | Parallel CI runs |
| 3 parallel agents | 70 | ~45 minutes | Parallel CI runs |

### Skill PR Common Failures

| Error type | Count (reference) | Fix |
| ----------- | ------- | ----- |
| Missing `.claude-plugin/plugin.json` | 4 | Create with name/version/description/category/tags/date |
| Invalid category (e.g., `automation`) | 1 | Change to `tooling` in plugin.json and SKILL.md |
| Missing `version` field | 1 | Add `"version": "1.0.0"` |

### Success Metrics (Reference Sessions)

| Session | PRs | Result |
| --------- | ----- | -------- |
| 13 PRs in 4 batched agents (v1.1) | 13 | ~7 min, 5 conflicts resolved semantically |
| 70 PRs with 3 parallel agents (v1.0) | 70 | ~45 min, 0 DIRTY remaining |
| 9 parallel worktrees (independent fixes) | 9 | All merged, 1,500+ lines removed |
| 30 skill PRs bulk merge | 30 | All merged, 6 CI fixes, 2 rebases |
| 10 stale PRs (3 fix rounds) | 9/10 | 21 agents across 3 rounds |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | 70 PRs rebased with 3 parallel agents, 2026-03-15 | parallel-rebase-agent-worktree-isolation v1.0 |
| ProjectScylla | 13 PRs rebased with 4 batched agents, 2026-03-27 | parallel-rebase-agent-worktree-isolation v1.1 |
| ProjectScylla | 9/10 stale PRs fixed in 3 iterative rounds | parallel-pr-rebase-fix source |
| ProjectScylla | 9 parallel worktrees, 24 fixes, 1,500+ lines removed | parallel-pr-workflow source |
| ProjectMnemosyne | 30 open skill PRs bulk merged, 2026-03-03 | bulk-skill-pr-merge source |
| HomericIntelligence/ProjectArgus | Atlas v0.2.1 patch series; 17 PRs landed across 6 waves (PRs #463-#474). Wave-1 used a shared tree and hit working-tree-revert bleed-over; waves 2-6 used per-sub-agent `/tmp/<repo>-wt-<task>` worktrees with zero state interference. 1 mid-flight conflict caught via `gh pr view --json mergeable`; 1 false "auto-merge armed" report caught the same way (rebase forbidden, switched to `--squash`). | Sub-agent PR isolation amendment (v1.1.0) |
| ProjectOdyssey | Phase G EASY-tier 8-issue swarm consolidation, PR #5363 (2026-05-09). Eight cross-contaminated worker PRs collapsed into one consolidation branch via cherry-pick; individual worker PRs closed-not-merged; 67/68 substantive checks green. | Phase 10b RESCUE pattern (v1.2.0) |
| ProjectHephaestus | output.log root-cause fixes, 2026-06-13 (verified-local). 6 root-cause fix PRs shipped as a stack — a shared format-drift prerequisite landed first, 5 independent fixes dispatched to 5 parallel sub-agents in dedicated worktrees branched off the prereq (one stacked on another fix). Surfaced a concurrent foreign-session hijack of the shared main checkout (recovered via patch-export + fresh worktree) and CC Safety-Net friction on `git checkout --` / `git branch -D` / `git stash drop`. Zero cross-contamination across the 5 worktree agents. | Phase 3b/3c + Dispatch Hygiene + Safety-Net Friction (v1.3.0) |
