---
name: parallel-pr-worktree-workflow
description: "Use when: (1) launching 2+ parallel rebase agents that need isolated git state to avoid branch collision, (2) implementing 5+ independent fixes in parallel PRs using git worktrees, (3) bulk-merging skill PRs with CI fixes and conflict resolution, (4) batching 10+ PRs across parallel sub-agents for maximum throughput, (5) launching >=2 concurrent sub-agents that each commit/push to the same git repo, (6) sub-agents report file bleed-over or unexpected `git checkout` reverts mid-task, (7) RESCUE pattern when parallel dispatch across distinct branches has already produced cross-contaminated commits — consolidate worker PRs into ONE branch via cherry-pick and close individual PRs, (8) doing ANY multi-fix work in a shared checkout that a concurrent foreign session/automation may also touch — use dedicated worktrees from the start so a foreign session cannot move your HEAD/branch, (9) arming auto-merge on a STACKED PR (base is another open/feature branch) — retarget to main BEFORE arming or it squash-merges into the intermediate base and can ORPHAN the change, (10) recovering an orphaned stacked merge (PR state=MERGED but content stranded on a dead intermediate branch) via cherry-pick onto a fresh main branch, (11) triaging GitHub PR CI where current-head checks are stale, absent, or blocked by merge conflicts — inspect job logs plus PR rollup/mergeability before editing and use one worktree per PR branch, (12) diagnosing Inference360 PRs where stale green checks coexist with `mergeStateStatus=DIRTY` and `mergeable=CONFLICTING` — rebase before waiting on validate, (13) diagnosing Inference360 validate failures after CLI simplification where endpoint-only InferenceX benchmark dry-runs should not auto-detect clusters and validate workflow commands may still reference removed top-level CLIs, (14) rescuing stale automation PR branches whose CI fails because the branch predates a merged trunk workflow/dependency fix — inspect live PR state and logs, rebase detached temporary worktrees from remote PR heads onto current main, verify focused tests/signatures/trailers, then push with an explicit force-with-lease against the old head."
category: ci-cd
date: 2026-07-01
version: "1.8.0"
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
when a worktree is shared or dirty), `git-worktree-parallel-execution-lifecycle`,
`parallel-agent-swarm-dispatch-patterns`, and
`pr-ci-failure-triage-preexisting-vs-introduced`.

## When to Use

- Launching 2+ background agents to mass-rebase branches in parallel (each needs isolated git state)
- Agents use `git switch`/`git checkout` and would leave rebase-in-progress state in shared working tree
- Safety Net blocks `git branch -D` or `git reset --hard` in the shared working tree
- Implementing 5+ independent fixes in parallel, each with its own PR
- Bulk-merging accumulated skill PRs (10+) with a mix of passing/failing CI
- Delegating fixes for several failing GitHub PRs where each branch needs separate log triage,
  focused tests, pushes, and current-head CI polling
- Main conversation needs to commit while background agents are running
- Issues are independent (not interdependent) and benefit from parallel development
- **(v1.3.0, verified-local)** ANY other session/automation may touch the shared checkout — do ALL multi-fix work in dedicated worktrees from the start, never in the primary checkout. A concurrent foreign session can move your branch and commit under you (see Phase 3c)
- **(v1.4.0, verified-local)** Arming auto-merge on a STACKED PR (one whose base is another open/feature branch). RETARGET to `main` first — arming a still-stacked PR squash-merges it into the intermediate base, NOT main, and can ORPHAN the change if that base is later closed unmerged (see Phase 3d)
- **(v1.5.0, verified-ci)** `gh pr checks` shows stale failures, or a required `validate`
  check disappears after a push. Inspect PR rollup, commits, mergeability, and rebase conflicted
  branches before assuming the workflow was skipped (see Phase 1b).
- **(v1.6.0, verified-ci)** Inference360 PRs report `mergeStateStatus=DIRTY` and
  `mergeable=CONFLICTING` even though visible checks are stale green. Rebase before waiting for
  `validate`, resolve only real conflict blocks, and treat post-push `mergeable=UNKNOWN` with green
  rollup as GitHub recomputation (see Phase 1b).
- **(v1.7.0, verified-ci)** Inference360 `validate` fails after CLI simplification on
  endpoint-only InferenceX benchmark tests or stale workflow commands. Pair PR checks with PR
  mergeability/head metadata, read the full failing job log, guard endpoint-only dry-runs from
  cluster auto-detection, and update `.github/workflows/validate.yml` to current console commands
  (see Phase 1c).
- **(v1.8.0, verified-ci)** ProjectHephaestus automation PRs fail CI collection with missing
  dependencies after a trunk workflow/dependency fix has already merged. Confirm the branch is
  stale relative to `origin/main`, rebase detached temporary worktrees from the remote PR heads,
  preserve only real conflict intent, verify focused tests plus signed commits/trailers, and push
  with an explicit old-head `--force-with-lease` (see Phase 1d).

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

### Phase 1b (v1.5.0, verified-ci): Current-Head CI Triage Before Editing

When rescuing multiple failing PRs, do the GitHub diagnosis before editing any branch. A stale
red check from an older SHA can send the wrong sub-agent to the wrong file, and an absent
`validate` run can mean GitHub could not create the pull-request merge ref because the PR is
conflicted.

```bash
REPO=LLM360/Inference360
PR=155
BRANCH=claude-config
WT=/tmp/Inference360-claude-config

# 1. Get the visible check summary.
gh pr checks "$PR" --repo "$REPO"

# 2. Confirm live mergeability and the current PR head before editing.
gh pr view "$PR" --repo "$REPO" \
  --json headRefOid,mergeStateStatus,mergeable,statusCheckRollup,url

# 3. If a visible check is actually failing, open the real failing job log.
gh run view --repo "$REPO" --job <job-id> --log

# 4. For broader assignment/debugging, include branch and commit metadata.
gh pr view "$PR" --repo "$REPO" \
  --json headRefName,headRefOid,mergeable,mergeStateStatus,statusCheckRollup,commits \
  --jq '{branch:.headRefName, head:.headRefOid, mergeable, mergeStateStatus,
         latestCommit:(.commits[-1].oid // null),
         checks:[.statusCheckRollup[] | {name,state,conclusion,detailsUrl}]}'
```

Interpretation:

- `gh run view --job --log` names the actual failing gate. Fix that, not the first nearby
  symptom in the PR diff.
- If the latest current-head `validate` check fails on Ruff, fix formatting or undefined names
  first, push, then expect the next gate (often coverage) to surface.
- If `validate` is missing after a push and the PR reports `mergeable: CONFLICTING`, rebase the
  branch. The workflow is not skipped; GitHub cannot synthesize the pull-request merge ref.
- If `gh pr checks` is green but `mergeStateStatus=DIRTY` and `mergeable=CONFLICTING`, treat the
  merge conflict as the blocker and rebase first. The green check summary can be stale for the old
  head.
- After a rebase push, GitHub may move from `mergeable=MERGEABLE` while checks run to
  `mergeable=UNKNOWN` after all rollups are green. That is mergeability recomputation, not a CI
  failure; keep polling instead of editing.

Per-PR worktree recovery:

```bash
PR=155
BRANCH=claude-config
WT=/tmp/Inference360-claude-config

git fetch origin master "$BRANCH"
git worktree add "$WT" "$BRANCH"  # or reuse an existing PR worktree
cd "$WT"
git rebase origin/master
# Resolve conflicts, preserving current master behavior and the PR's intended behavior.
git -c core.editor=true rebase --continue
# Run focused tests/checks for the changed surface, then:
git push --force-with-lease origin "$BRANCH"
```

Conflict-resolution examples from the verified Inference360 follow-up:

- PR #155: conflict in `scripts/endpoint_status.py` around `_positive_int`; keep master's current
  error message wording and the PR's docstring.
- PR #254: remove obsolete top-level duplicate server command parsers and do not revive the removed
  dry-run parser; preserve master's `check preview`/`status` surface and the PR's unified
  `start`/`stop` behavior.
- Linked worktrees write metadata under the main repo's `.git/worktrees`. If sandboxing blocks the
  Git operation, rerun that Git operation with the appropriate filesystem escalation; do not abandon
  the worktree strategy.

Delegation shape:

1. Create or reuse exactly one worktree per PR branch.
2. Give each sub-agent only its PR number, branch, failing check log, expected local tests, and
   the instruction not to touch the main checkout or other worktrees.
3. After each push, the parent session polls `gh pr checks` and validates with `gh pr view
   --json headRefOid,mergeable,mergeStateStatus,statusCheckRollup,commits`.
4. Stop only when GitHub shows checks for the current head SHA and the required gate is green.

Full local suites can fail for environment reasons (`portpicker.NoFreePortFoundError`, broken
`just`, submodule HEAD mismatch). Record those separately, but use focused tests plus GitHub CI
as the source of truth for the PR rescue.

### Phase 1c (v1.7.0, verified-ci): Inference360 Endpoint-Only InferenceX and Workflow Drift

Use this when an Inference360 PR has a current-head `validate` failure after CLI simplification,
especially when tests exercise `inferencex-benchmark --endpoint ... --dry-run` without a manifest.
Endpoint-only benchmark mode does not need H200 Slurm cluster manifests, so it must not trigger
cluster auto-detection.

```bash
REPO=LLM360/Inference360
PR=255

# 1. Separate current-head validate failures from stale/conflicting merge failures.
gh pr checks "$PR" --repo "$REPO"
gh pr view "$PR" --repo "$REPO" \
  --json mergeStateStatus,mergeable,commits,statusCheckRollup

# 2. Read the full failing job log, then filter around pytest failures.
gh run view <run-id> --repo "$REPO" --job <job-id> --log

# Useful local filter once the full log is saved.
rg -C 8 "FAILED|Traceback|ManifestError|_detect_cluster|inferencex-benchmark" <log-file>
```

Interpretation from PR #255:

- Current head was `6c457ca`; only `validate` was failing and other checks passed.
- Truncated logs pointed at a stale `--manifest` parser theory, but the full traceback showed
  `inference360/__init__.py` calling `_detect_cluster()` from `main()` because `args.cluster`
  was omitted.
- The failing tests were endpoint-only `inferencex-benchmark --endpoint ... --dry-run` cases:
  `tests/test_inferencex_integration.py::test_inferencex_benchmark_cli_endpoint_only_dry_run_defaults_to_tmp_perfhc`
  and
  `tests/test_inferencex_integration.py::test_inferencex_benchmark_cli_endpoint_discovery_failure_is_actionable`.
- Hosts with `<REDACTED_INFRA_PATH>` can hide the bug; GitHub runners without `<REDACTED_INFRA_PATH>` or `<REDACTED_INFRA_PATH>`
  fail closed with `ManifestError: could not auto-detect cluster`.

Durable fix pattern:

1. Guard cluster auto-detection so it skips endpoint-only InferenceX benchmark runs:
   `args.command == "inferencex-benchmark" and not args.manifest`.
2. Add regression tests that monkeypatch `inference360._detect_cluster` to `pytest.fail(...)`
   in endpoint-only tests. The assertion is not just the CLI output; it proves endpoint-only mode
   never touches cluster detection.
3. Keep `.github/workflows/validate.yml` drift tests so CI keeps using current CLI commands after
   CLI simplification.
4. If `validate.yml` still calls removed top-level commands, replace them with current console
   commands:

   ```bash
   .venv/bin/inference360 control generate slurm --cluster m1 \
     --manifest examples/manifests/h200-moe-sglang-production.yaml \
     > artifacts/generated/h200-moe-sglang-production.slurm.sh

   .venv/bin/inference360 check preview --cluster m1 \
     --production examples/manifests/h200-moe-sglang-production.yaml \
     --experimental examples/manifests/h200-moe-vllm-experimental.yaml \
     > artifacts/generated/control-preview.json
   ```

5. Rename generated-artifact docs from Slurm/HAProxy previews to Slurm/control-node previews.
   HAProxy config generation should use live control-server state, not a stale registry or a
   manifest-only validation workflow.

### Phase 1d (v1.8.0, verified-ci): Stale Automation Branch Predates Trunk CI Dependency Fix

Use this when multiple automation-authored PRs fail during CI collection or environment setup,
and the failure appears unrelated to the branch diff. The common signature from ProjectHephaestus
PRs #1731 and #1732 was `ModuleNotFoundError: No module named 'pydantic'` while collecting
automation unit/integration tests; both PR heads predated a merged `main` fix that installed the
automation extra in CI.

```bash
REPO=HomericIntelligence/ProjectHephaestus
PR=1731

# 1. Inspect live PR state and keep the old head for an explicit lease.
gh pr view "$PR" --repo "$REPO" \
  --json number,title,state,isDraft,headRefName,headRefOid,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,url

# 2. Inspect the failed job log before editing branch code.
gh run view <run-id> --repo "$REPO" --log-failed

# 3. Confirm the suspected fix is already on trunk.
gh pr view 1730 --repo "$REPO" --json state,mergedAt,mergeCommit
git fetch origin main <pr-branch>

# 4. If the branch is checked out elsewhere or local state is stale, avoid switching it.
git worktree add --detach /tmp/ProjectHephaestus-pr1731 origin/<pr-branch>
cd /tmp/ProjectHephaestus-pr1731
git rebase origin/main

# 5. Verify locally, preserving CI's addopts override when relevant.
PIXI_CACHE_DIR=/tmp/pixi-cache-pr1731 pixi run pytest <focused-tests> --override-ini=addopts=.
git log --format='%h %G? %s%n%b' origin/main..HEAD

# 6. Push only if the remote head is still the old head observed in step 1.
git push --force-with-lease=refs/heads/<pr-branch>:<old-head-oid> \
  origin HEAD:refs/heads/<pr-branch>

# 7. Watch current-head checks and confirm mergeability.
gh pr checks "$PR" --repo "$REPO" --watch --interval 30
gh pr view "$PR" --repo "$REPO" --json mergeable,mergeStateStatus,headRefOid,statusCheckRollup
```

Interpretation:

- If the log fails in collection before branch-specific tests run, look for missing trunk workflow
  or dependency changes before editing product code.
- If the trunk fix is merged and the PR head predates it, rebasing is the fix; do not cherry-pick
  the workflow/dependency change unless rebase is impossible.
- Detached worktrees are appropriate for rescue work when the local branch may be stale, locked by
  another worktree, or carrying state you do not own.
- Resolve only real conflicts. For PR #1731, `hephaestus/automation/pr_manager.py` needed to keep
  `main`'s `DEFAULT_GIT_MESSAGE_AGENT_TIMEOUT` import while preserving the PR's local secret
  pattern constants after deleting `_secret_patterns.py`.
- After rebase, verify commits still have good signatures and required `Signed-off-by` trailers.
- Use the full refspec form of `--force-with-lease` so the push fails if another actor updated the
  PR branch since the live-state read.

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

### Phase 3d (v1.4.0, verified-local): NEVER Arm Auto-Merge on a Still-Stacked PR — It Merges Into the Intermediate Base and Can ORPHAN the Change

**The hazard:** when a PR's base is another open/feature branch (a stacked PR) and you arm
`gh pr merge --auto --squash`, GitHub fires the merge against that INTERMEDIATE base the moment
it is eligible — squashing the change onto the intermediate branch, NOT `main`. If that
intermediate base is later closed UNMERGED, the change is stranded on a dead branch (the PR shows
`state=MERGED` but its content never reaches `main`). Observed this session (ProjectHephaestus
/myrmidon-swarm driving a stack of PRs): two PRs (RC2, RC6) were armed while still based on
intermediate branches. RC6 was harmless — its base was another open PR that itself merges to main,
so RC6 folded into it. RC2's base (`chore-ruff-format-drift`) belonged to a CLOSED PR, so RC2's
change merged onto a dead branch and was ORPHANED from main.

**Critical timing facts about GitHub stacked-PR retargeting:**

- GitHub does NOT auto-retarget a stacked PR to `main` until its base PR actually **MERGES**.
- If the base PR is **CLOSED (not merged)**, the dependent is STRANDED — it is not auto-retargeted.
- Once a PR has merged into a now-dead base, `gh pr edit N --base main` FAILS with
  `Cannot change the base branch of a closed pull request`. There is no in-place fix; you must
  recover the commit (below).

**Prevention — before arming auto-merge on any stacked PR:**

```bash
# 1. Confirm the base content is ALREADY on main (the base PR merged, OR the base is a no-op
#    already upstream — e.g. rebase silently drops it as "patch contents already upstream").
# 2. Retarget the dependent to main FIRST:
gh pr edit N --base main
# 3. Re-rebase the dependent onto main to drop the now-redundant base commit and surface only
#    the real change:
cd /tmp/<repo-stem>-wt-<task> && git rebase origin/main && git push --force-with-lease
# 4. Only AFTER it is mergeable against main, arm auto-merge:
gh pr merge N --auto --squash
```

**NEVER arm a PR whose base is an intermediate branch you intend to close/abandon.** Order
matters for a fan-out: retarget + rebase ALL dependents to main first, arm LAST.

#### Recovering an ORPHANED stacked merge (v1.4.0, verified-local)

**Detect:**

```bash
gh pr view N --json state,baseRefName,mergedAt
# state=MERGED but baseRefName is an intermediate/closed branch == orphaned.
```

The change lives as a commit on that intermediate branch:

```bash
git log origin/main..origin/<intermediate-branch> --oneline
```

**Recover** by cherry-picking that commit onto a fresh `main` branch and opening a NEW PR to main:

```bash
git worktree add /tmp/recover origin/main -b <name>-v2
cd /tmp/recover
git cherry-pick -S <orphaned-sha>          # -S keeps it signed
git log origin/main..HEAD --oneline        # verify it is NOT a no-op
# run the affected tests, then push + open a NEW PR to main (--base main)
```

This restores the lost change with a clean lineage on `main`.

#### Prevention for a fan-out of stacked PRs (v1.4.0, verified-local)

When a base branch becomes a **NO-OP** (its content already merged to main via a sibling — confirm
via a rebase that silently drops it with "patch contents already upstream"):

1. CLOSE that base PR.
2. RETARGET all its dependents to `main` BEFORE arming any of them (`gh pr edit N --base main`).
3. Re-rebase each dependent onto `main` to drop the redundant base commit and surface only the
   real change.
4. Only arm (`--auto --squash`) after each is MERGEABLE against main.

Order matters: retarget + rebase FIRST, arm LAST. See also
`github-auto-merge-ci-gating-merge-method` (the arming/gating companion) and
`pr-rebase-conflict-resolution-patterns` (the rebase silent-drop / superseded-PR detection used to
find no-op bases).

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
| Arm auto-merge on a stacked PR still based on an intermediate branch (ProjectHephaestus, 2026-06-14, verified-local) | Ran `gh pr merge --auto --squash` on a PR whose base was still an intermediate feature branch (`chore-ruff-format-drift`) rather than `main` | GitHub fired the merge against the INTERMEDIATE base the moment it was eligible — squashed the change onto the intermediate branch; that base belonged to a CLOSED PR, so the change was ORPHANED from main (PR showed `state=MERGED` but content was on a dead branch) | Retarget the dependent to `main` and confirm the base content is ALREADY on main BEFORE arming (`gh pr edit N --base main`, rebase onto main, THEN `--auto --squash`). Never arm a PR whose base you intend to close/abandon (Phase 3d) |
| Assume GitHub auto-retargets a stacked PR to main when its base closes (ProjectHephaestus, 2026-06-14, verified-local) | Expected the dependent PR to retarget to `main` automatically once its base branch's PR was closed | GitHub only auto-retargets when the base PR actually MERGES; a CLOSED (unmerged) base STRANDS the dependent, and after it merges into the dead base `gh pr edit --base main` fails with "Cannot change the base branch of a closed pull request" | Retarget dependents to `main` manually BEFORE the base is closed; if already orphaned, recover by cherry-picking the orphaned SHA onto a fresh main branch and opening a NEW PR (Phase 3d recovery) |
| Treat the first Ruff failure as the complete PR fix (LLM360/Inference360, 2026-06-17, verified-ci) | Fixed Ruff format and `F821` undefined-name failures in the first `validate` log, then expected CI to go green | The next current-head `validate` run failed coverage because the new script had too little direct test coverage | After each push, poll current-head CI again. A first failure can mask the next gate; add focused tests for newly introduced scripts or behavior before declaring the PR rescued |
| Trust stale `gh pr checks` output after a force-push (LLM360/Inference360, 2026-06-17, verified-ci) | Read `gh pr checks` as the live truth even though it still showed failed `validate` runs from earlier SHAs | The visible failure did not necessarily apply to the current head commit | Use `gh pr view --json headRefOid,mergeable,mergeStateStatus,statusCheckRollup,commits` to connect check state to the current PR head before assigning or editing |
| Assume a missing `validate` check means the workflow was skipped (LLM360/Inference360, 2026-06-17, verified-ci) | Waited for a current-head `validate` run that never appeared after pushing fixes | The PR was `mergeable: CONFLICTING`; GitHub could not create the `pull_request` merge ref, so the required validate workflow never started | Inspect mergeability when a required check disappears. Rebase the branch onto current `origin/master`, resolve conflicts in its worktree, then `git push --force-with-lease`; validate appears after the merge ref is synthesizeable |
| Wait for `validate` before rebasing (LLM360/Inference360 PRs #155/#254, 2026-06-19, verified-ci) | Saw visible checks that were green or stale and waited for GitHub to settle | `mergeStateStatus=DIRTY` and `mergeable=CONFLICTING` meant the PR could not be merged regardless of the visible check summary | Query mergeability before editing. If the PR is conflicting, fetch trunk and branch, rebase onto `origin/master` in an isolated worktree, then push with `--force-with-lease` |
| Use `gh pr checks` alone for conflict triage (LLM360/Inference360 PRs #155/#254, 2026-06-19, verified-ci) | Treated the visible checks table as authoritative | `gh pr checks` can show stale green results from the old head while the live PR state remains `DIRTY`/`CONFLICTING` | Pair `gh pr checks <n>` with `gh pr view <n> --json headRefOid,mergeStateStatus,mergeable,statusCheckRollup,url` before deciding what to fix |
| Treat post-push `mergeable=UNKNOWN` as failure (LLM360/Inference360 PRs #155/#254, 2026-06-19, verified-ci) | Considered launching another fix pass after checks were green but mergeability returned `UNKNOWN` | GitHub was recomputing mergeability after the push/check transition | If `statusCheckRollup` is green and no failure is present, keep polling. Do not invent a CI failure from `UNKNOWN` alone |
| Change strategy when linked-worktree Git writes are sandbox-blocked | A linked worktree operation needed to update metadata under the main repo `.git/worktrees` | The filesystem block is an execution-environment issue, not a reason to stop using worktrees | Rerun the same Git operation with the appropriate filesystem escalation and keep the isolated `/tmp` worktree workflow |
| Trust truncated logs for Inference360 PR #255 validate | Read a shortened failure excerpt and chased a stale `--manifest` parser hypothesis | The full pytest traceback showed `inference360/__init__.py` calling `_detect_cluster()` because `args.cluster` was omitted | Pull the full job log with `gh run view --job <job-id> --log`, then filter around `FAILED`, `Traceback`, and the command under test |
| Let endpoint-only InferenceX benchmark dry-runs auto-detect clusters | Treated all `inferencex-benchmark` invocations as needing cluster-specific manifests | Endpoint-only `--endpoint ... --dry-run` mode does not need cluster manifests; GitHub runners lack `<REDACTED_INFRA_PATH>` and `<REDACTED_INFRA_PATH>`, so `_detect_cluster()` fails with `ManifestError` | Skip cluster auto-detection when `args.command == "inferencex-benchmark" and not args.manifest`; prove it with tests that monkeypatch `_detect_cluster` to `pytest.fail(...)` |
| Keep removed top-level commands in `.github/workflows/validate.yml` | Continued using `.venv/bin/python -m inference360 generate-slurm` and `generate-haproxy` after CLI simplification | CI exercised dead command surfaces rather than the current console script, so workflow validation drifted from the product CLI | Use `.venv/bin/inference360 control generate slurm ...` and `.venv/bin/inference360 check preview ...`; backstop with workflow drift tests |
| Treat a local `<REDACTED_INFRA_PATH>` host as enough validation for endpoint-only mode | Ran locally on a host where cluster auto-detection succeeds because `<REDACTED_INFRA_PATH>` exists | The bug is environment-sensitive and only appears on runners without known cluster mounts | Add explicit no-autodetect regression tests and verify on GitHub CI, not only on a cluster-like local host |
| Treat the full local suite as the single source of truth (LLM360/Inference360, 2026-06-17, verified-ci) | Tried to use the entire local suite as the final readiness signal while fixing PR branches | Local environment failures such as `portpicker.NoFreePortFoundError`, broken `just`, or submodule HEAD mismatch were not the PR's CI gate | Run focused tests that cover the edited surface locally, record unrelated environment failures, and use current-head GitHub CI as the PR rescue source of truth |
| Diagnose stale automation PRs by editing branch code first (ProjectHephaestus PRs #1731/#1732, 2026-07-01, verified-ci) | Started from failing unit/integration collection and could have chased automation imports in the PR diff | Both branches simply predated merged PR #1730, which installed the automation extra in CI; the branch code was not the immediate cause of `ModuleNotFoundError: No module named 'pydantic'` | Inspect live PR head, failed logs, and trunk history first. If the fix is already on `origin/main`, rebase the stale branch before changing code |
| Switch local stale PR branches directly for rescue work | Local branches/worktrees may be stale, checked out elsewhere, or carrying state from automation | Switching or overwriting them risks clobbering unrelated work and can fail with branch-in-use errors | Create detached temporary worktrees from `origin/<pr-branch>` for rebase rescue, then push `HEAD` back to the remote branch with an explicit old-head lease |
| Use bare `--force-with-lease` after rebasing automation PR heads | The default lease may not protect the exact old PR head observed during triage if refs moved or were not fetched as expected | A concurrent automation/user push could be overwritten | Capture `headRefOid` from `gh pr view` and push with `--force-with-lease=refs/heads/<branch>:<old-head-oid>` |

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

### Current-Head CI Rescue Parameters (v1.5.0)

```bash
# One PR branch per isolated worktree.
git fetch origin master <pr-branch>
git worktree add -B <pr-branch> /tmp/<repo-stem>-pr-<number> origin/<pr-branch>

# Identify the real failing gate, not just the first red summary line.
gh pr checks <number> --repo <org/repo>
gh run view --repo <org/repo> --job <job-id> --log

# Verify the rollup applies to the current head and diagnose missing checks.
gh pr view <number> --repo <org/repo> \
  --json headRefName,headRefOid,mergeable,mergeStateStatus,statusCheckRollup,commits

# If validate disappears because the PR is conflicted:
cd /tmp/<repo-stem>-pr-<number>
git rebase origin/master
git push --force-with-lease origin HEAD:<pr-branch>
```

### Inference360 Mergeability Rebase-Before-Validate Parameters (v1.6.0)

```bash
# Live-state check before editing. Do not rely on gh pr checks alone.
gh pr view <number> --repo LLM360/Inference360 \
  --json headRefOid,mergeStateStatus,mergeable,statusCheckRollup,url
gh pr checks <number> --repo LLM360/Inference360

# Rebase the conflicting PR branch before waiting for validate.
git fetch origin master <branch>
git worktree add /tmp/Inference360-<branch-or-pr> <branch>
cd /tmp/Inference360-<branch-or-pr>
git rebase origin/master

# After resolving only real conflict blocks:
git -c core.editor=true rebase --continue
git push --force-with-lease origin <branch>
```

Observed focused validation from the verified follow-up:

| PR | Branch | Focused local validation | GitHub result |
| --- | --- | --- | --- |
| #155 | `claude-config` | `.venv/bin/python -m pytest tests/test_endpoint_status.py tests/test_ifm_cli.py -q` -> `54 passed`; Ruff check/format on touched files passed; `bash -n scripts/setup_ifm_tool.sh` passed | Head `b24c97c`; `validate`, `python-sca`, `sast`, `secrets`, and CodeQL green |
| #254 | server command parser branch | Focused CLI/control lifecycle pytest -> `343 passed, 7 skipped`; Ruff check/format passed; `bash -n scripts/multi_model_ifm_launch.sh` passed | Head `4086627`; `validate`, `python-sca`, `sast`, `secrets`, and CodeQL green |

Inference360 branch mapping from the verified session:

| PR | Branch | Final CI result |
| --- | --- | --- |
| #149 | `feat/endpoint-status` | All GitHub checks passed at `c8b7a06`; PR open and mergeable clean |
| #155 | `claude-config` | All GitHub checks passed at `23fe471`; PR open and mergeable clean |
| #156 | `code-cleanup` | CI validate passed at `66db8ac`; PR merged |
| #157 | `move-inference360-module` | CI passed after TOML coverage config fix; PR merged |

### Inference360 Endpoint-Only InferenceX Validate Parameters (v1.7.0)

```bash
# Targeted regression for endpoint-only autodetect and workflow drift.
.venv/bin/pytest \
  tests/test_inferencex_integration.py::test_inferencex_benchmark_cli_endpoint_only_dry_run_defaults_to_tmp_perfhc \
  tests/test_inferencex_integration.py::test_inferencex_benchmark_cli_endpoint_discovery_failure_is_actionable \
  tests/test_ci_workflow.py -q
# Result: 6 passed in 0.10s

# Smoke: Slurm generation uses the current console command.
.venv/bin/inference360 control generate slurm --cluster m1 \
  --manifest examples/manifests/h200-moe-sglang-production.yaml
# Result: emitted valid Slurm script.

# Smoke: control-node preview replaces stale HAProxy manifest-only generation.
.venv/bin/inference360 check preview --cluster m1 \
  --production examples/manifests/h200-moe-sglang-production.yaml \
  --experimental examples/manifests/h200-moe-vllm-experimental.yaml
# Result: emitted JSON with "status": "ok" and "target": "preview".

# Full host validation.
INFERENCE360=.venv/bin/inference360 PYTHON=.venv/bin/python scripts/validate.sh
# Result: 749 passed, 8 skipped; coverage 81.69%.
```

Additional PR #255 verification:

| Check | Result |
| --- | --- |
| Podman-backed `just validate` | Not runnable on the host because Podman was not installed |
| Fix commit | `4d87527 fix(ci): align validation workflow with simplified cli` |
| GitHub checks after push | `gh pr checks 255 --repo LLM360/Inference360` showed all pass, including `validate` |
| Mergeability after push | `gh pr view 255 --repo LLM360/Inference360 --json mergeStateStatus,mergeable,url` returned `mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`, URL `https://github.com/LLM360/Inference360/pull/255` |

### ProjectHephaestus Stale Automation PR Rebase Parameters (v1.8.0)

```bash
# Live-state shape used before rebasing.
gh pr view <pr> --repo HomericIntelligence/ProjectHephaestus \
  --json number,title,state,isDraft,headRefName,headRefOid,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,url

# Failed log inspection.
gh run view <run-id> --repo HomericIntelligence/ProjectHephaestus --log-failed

# Detached worktrees from remote PR heads.
git worktree add --detach /tmp/ProjectHephaestus-pr1731 origin/1442-auto-impl
git worktree add --detach /tmp/ProjectHephaestus-pr1732 origin/1432-auto-impl

# Rebase rescue and protected push.
git rebase origin/main
PIXI_CACHE_DIR=/tmp/pixi-cache-pr1731 pixi run pytest <focused-tests> --override-ini=addopts=.
git push --force-with-lease=refs/heads/<branch>:<old-head-oid> origin HEAD:refs/heads/<branch>
```

Observed verification:

| PR | Branch | Rebased head | Focused local validation | GitHub result |
| --- | --- | --- | --- | --- |
| #1731 | `1442-auto-impl` | `eccf63c7aa302426e21d556cb14a77c60b5f4bd6` | `82 passed` | All checks passing; `MERGEABLE`/`CLEAN` |
| #1732 | `1432-auto-impl` | `07818ce1154bf79d8dbb081dd44ba7cac20dbb2c` | `24 passed` | All checks passing; `MERGEABLE`/`CLEAN` |

Additional checks from the verified session:

- PR #1730 was already merged and `origin/main` contained the CI workflow/dependency fix that
  installs the automation extra.
- Rebased commits remained signed and retained `Signed-off-by` trailers.
- Temporary detached worktrees for PR #1731 and #1732 were removed after the pushes and CI
  verification completed.

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
| Mnemosyne | 30 open skill PRs bulk merged, 2026-03-03 | bulk-skill-pr-merge source |
| HomericIntelligence/ProjectArgus | Atlas v0.2.1 patch series; 17 PRs landed across 6 waves (PRs #463-#474). Wave-1 used a shared tree and hit working-tree-revert bleed-over; waves 2-6 used per-sub-agent `/tmp/<repo>-wt-<task>` worktrees with zero state interference. 1 mid-flight conflict caught via `gh pr view --json mergeable`; 1 false "auto-merge armed" report caught the same way (rebase forbidden, switched to `--squash`). | Sub-agent PR isolation amendment (v1.1.0) |
| ProjectOdyssey | Phase G EASY-tier 8-issue swarm consolidation, PR #5363 (2026-05-09). Eight cross-contaminated worker PRs collapsed into one consolidation branch via cherry-pick; individual worker PRs closed-not-merged; 67/68 substantive checks green. | Phase 10b RESCUE pattern (v1.2.0) |
| ProjectHephaestus | output.log root-cause fixes, 2026-06-13 (verified-local). 6 root-cause fix PRs shipped as a stack — a shared format-drift prerequisite landed first, 5 independent fixes dispatched to 5 parallel sub-agents in dedicated worktrees branched off the prereq (one stacked on another fix). Surfaced a concurrent foreign-session hijack of the shared main checkout (recovered via patch-export + fresh worktree) and CC Safety-Net friction on `git checkout --` / `git branch -D` / `git stash drop`. Zero cross-contamination across the 5 worktree agents. | Phase 3b/3c + Dispatch Hygiene + Safety-Net Friction (v1.3.0) |
| ProjectHephaestus | /myrmidon-swarm driving a stack of PRs to merge, 2026-06-14 (verified-local). Two PRs (RC2, RC6) were armed for auto-merge while still based on intermediate branches. They squash-merged into those intermediate bases, NOT main. RC6 folded harmlessly into an open base PR; RC2's base (`chore-ruff-format-drift`) was a CLOSED PR, so RC2's change was ORPHANED from main (`state=MERGED`, content on a dead branch). Recovered RC2 by cherry-picking the orphaned SHA onto a fresh main branch (`git cherry-pick -S`) and opening a NEW PR to main. Confirmed GitHub only auto-retargets stacked PRs when the base MERGES, not when it closes unmerged. | Phase 3d stacked-PR auto-merge hazard + orphan recovery (v1.4.0) |
| LLM360/Inference360 | GitHub PR CI rescue session, 2026-06-17. Four failing PRs (#149 `feat/endpoint-status`, #155 `claude-config`, #156 `code-cleanup`, #157 `move-inference360-module`) were fixed in isolated PR worktrees using log-first triage, focused local tests, and current-head CI polling. #149/#155 needed rebase after `validate` disappeared because `mergeable: CONFLICTING` prevented the pull-request merge ref; #156/#157 merged after CI passed. | Phase 1b current-head CI triage + per-PR worktree rescue (v1.5.0, verified-ci) |
| LLM360/Inference360 | PR merge-conflict/mergeability triage follow-up, 2026-06-19. PR #155 (`claude-config`) and PR #254 were failing because GitHub reported merge conflicts against `origin/master`; `gh pr checks` could be stale green while `mergeStateStatus=DIRTY` and `mergeable=CONFLICTING`. Rebased each branch in an isolated `/tmp` worktree, resolved only true conflict blocks, ran focused local validation, pushed with `--force-with-lease`, and verified GitHub checks green at heads `b24c97c` and `4086627`. | Rebase-before-validate mergeability triage (v1.6.0, verified-ci) |
| LLM360/Inference360 | PR #255 validate failure after CLI simplification, 2026-06-22. Current head `6c457ca` had only `validate` failing; full logs showed endpoint-only `inferencex-benchmark --endpoint ... --dry-run` tests calling `_detect_cluster()` and failing on GitHub runners without `<REDACTED_INFRA_PATH>` or `<REDACTED_INFRA_PATH>`. Fixed by skipping cluster auto-detection for endpoint-only runs, adding `_detect_cluster` fail-fast regressions, replacing stale `generate-slurm`/`generate-haproxy` workflow commands with `control generate slurm` and `check preview`, and verifying GitHub checks all passed after commit `4d87527`. | InferenceX endpoint-only autodetect and validate workflow drift (v1.7.0, verified-ci) |
| HomericIntelligence/ProjectHephaestus | PRs #1731 (`1442-auto-impl`) and #1732 (`1432-auto-impl`), 2026-07-01. Both CI runs failed during unit/integration collection with `ModuleNotFoundError: No module named 'pydantic'` because the branch heads predated merged PR #1730, which installed the automation extra in CI. Each PR was rebased from a detached temporary worktree onto `origin/main`, focused tests passed (`82 passed` for #1731, `24 passed` for #1732), signed/trailered commits were verified, pushes used explicit old-head force-with-lease, and GitHub reported all checks passing with `mergeable=MERGEABLE` and `mergeStateStatus=CLEAN` at heads `eccf63c7aa302426e21d556cb14a77c60b5f4bd6` and `07818ce1154bf79d8dbb081dd44ba7cac20dbb2c`. | Stale automation branch dependency-fix rebase rescue (v1.8.0, verified-ci) |
