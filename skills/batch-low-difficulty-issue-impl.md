---
name: batch-low-difficulty-issue-impl
description: 'Classify, deduplicate, and batch-implement GitHub issues in a large swarm
  session (24+ waves, 200+ issues). Use when: (1) a large backlog of open issues needs
  triage, (2) many issues are pure doc/text or infra-only changes, (3) duplicate issues
  need closing before implementation. Includes worktree-safe grep pattern for ALREADY-DONE
  verification, correct pre-filter order, ci.yml conflict avoidance, EASY queue exhaustion
  detection, Docker inline comment parse error pattern, parallel-agent add/add rebase
  conflict resolution when multiple agents create the same package independently,
  pre-launch repo-capability checks (autoMergeAllowed, lockfile, pre-commit config),
  hot-file serialization for shared scripts (apply.sh/reconcile.sh), pre-swarm
  existing-PR audit, close-before-delegate pattern, and C++20/Conan/pixi-specific
  guards (libssl-dev, TSan+concurrentqueue blocker, enable_shared_from_this diamond
  inheritance, CMakeLists.txt single-agent anchor, asyncio_mode auto decorator check).'
category: tooling
date: 2026-04-26
version: "1.10.0"
user-invocable: false
verification: verified-local
history: batch-low-difficulty-issue-impl.history
---
# Batch Low-Difficulty Issue Implementation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Classify, deduplicate, and batch-implement low-difficulty GitHub issues using worktree-isolated agents |
| **Outcome** | Verified: worktree isolation works correctly; correct pre-filter order; ALREADY-DONE grep must exclude worktrees; pre-launch repo-capability checks required; C++20/Conan/pixi-specific guards required for C++ projects |
| **Verification** | verified-local |
| **History** | [changelog](./batch-low-difficulty-issue-impl.history) |

### Session (2026-04-25) — ProjectKeystone 180-Issue C++20 Swarm

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-25 | Implement 180 open ProjectKeystone issues (C++20 transport library) using 7 EASY waves + 9 MEDIUM waves | 7 new C++20/Conan/pixi-specific failure modes discovered; libssl-dev missing in Dockerfile blocked builds; TSan+concurrentqueue classified as hard blocker; CMakeLists.txt double-agent conflict despite grouping rules; enable_shared_from_this diamond inheritance trap |

### Session (2026-04-24) — Myrmidons shellcheck-warnings Swarm

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-24 | Implement shellcheck warning fixes across Myrmidons repo using wave-based myrmidon swarm with hot-file serialization | All PRs merged, main CI green at 333b40d; Wave 1 = verification sweep; hot-file serialization prevented apply.sh/reconcile.sh conflicts |

### Session (2026-04-25) — ProjectProteus 43-Issue Swarm

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-25 | Implement 43 open HomericIntelligence/ProjectProteus issues (CI/CD pipeline hub repo) using myrmidon swarm | ~20 EASY issues implemented, 14 PRs created, ~8 merged; auto-merge disabled (branch protection requires reviews); no lockfile committed (used npm install not npm ci); pre-commit hooks absent (skipped in all agent prompts) |

### Session (2026-04-23) — ProjectScylla 15-Issue Medium/High Myrmidon Swarm

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-23 | Fix 15 GitHub issues (LOW to HIGH difficulty) across 5 parallel waves (max 5 agents/wave) using `isolation: "worktree"` | 12 PRs merged; 3 issues were ALREADY-DONE; add/add rebase conflicts on `scylla/agamemnon/` package from two agents creating it independently in Wave 1 |

### Session (2026-04-23) — AchaeanFleet 235-Issue Myrmidon Swarm (Waves 1-24+)

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-23 | Implement 235 open HomericIntelligence/AchaeanFleet issues (infra-only Docker/Nomad repo) using 24+ waves of ≤5 Haiku agents each | 202 issues closed, 91 PRs merged (verified-ci), 33 remaining (all MEDIUM/HARD). EASY queue exhausted at ~76% of total. |

### Session (2026-04-23) — HomericIntelligence/Odysseus 35-Issue Triage

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-04-23 | Classify 35 open Odysseus issues, implement all SIMPLE ones as 1-issue-per-PR using Myrmidon swarm (Haiku agents with isolation=worktree) | 19 issues resolved (17 PRs + 2 ALREADY-DONE closures), 13 merged; remaining auto-merging. Meta-repo with 12 submodule symlinks. |

### Prior session (2026-03-06)

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-06 | Classify 165 open issues, close 9 duplicates, implement 22 LOW issues | 15 PRs merged, 11 issues closed (9 dup + 2 already-done), 0 pre-commit failures |

## When to Use

- (1) Repository has 30+ open issues without PRs and a sprint/cleanup session is planned
- (2) A significant fraction of issues are doc-only changes (README updates, comment fixes, docstring additions) or infra-only changes (Dockerfile edits, CI/CD yaml)
- (3) You suspect duplicate issues exist that should be closed before work begins
- (4) Issues span many different files with minimal cross-file dependencies
- (5) CI pre-commit hooks are stable (no known broken hooks)
- (6) Pre-existing CI failures are blocking merges — create a `fix-test-failures` fix branch first
- (7) Before launch: check `gh repo view --json autoMergeAllowed`, `.pre-commit-config.yaml` existence, and `package-lock.json` / `pixi.lock` existence — these affect agent prompt templates (auto-merge flag, pre-commit steps, npm ci vs npm install)
- (8) When multiple agents may touch the same "hot file" (e.g., `scripts/apply.sh`, `scripts/lib/reconcile.sh`): at most one agent per sub-wave may touch each hot file — serialize hot-file issues across sub-waves
- (9) Before classifying issues: run `gh pr list --state open` first — many issues may have PRs already open from prior swarm runs; close issues already covered before delegating
- (10) For C++20/CMake/Conan projects: run C++20/Conan/pixi-specific guard checks before dispatching agents (see "C++20/Conan/pixi Project-Specific Guards" in Results & Parameters)

## Verified Workflow

### Phase 0: Pre-existing CI Failures — fix-test-failures Branch

If CI is already broken on main before the swarm starts, swarm PRs will auto-close but
never merge. Create a dedicated fix branch first and accumulate all CI fixes there:

```bash
git checkout -b fix-test-failures origin/main
# Fix each CI failure (inline comment, lock file sync, SHA pinning, etc.)
git push -u origin fix-test-failures
gh pr create --title "fix(ci): repair pre-existing CI failures blocking swarm" --body "..."
# Accumulate fixes here until CI is green, then merge before final swarm waves
```

**Items that accumulate in fix-test-failures branches (AchaeanFleet pattern):**
- Docker inline comment parse errors (see Failed Attempts)
- pixi.lock staleness
- hadolint `DL3006` suppressions
- Bare `${WORKSPACE_ROOT}` variable references
- Unpinned FROM digests
- Nomad vault-policy.hcl guard conditions
- npm CVE suppressions
- Trivy action SHA corrections

### Phase 0.5: Pre-Swarm Existing-PR Audit

Before classifying issues or dispatching any agents, audit the repo for existing open PRs.
Prior swarm runs may have already created PRs covering many issues — launching duplicate agents
wastes time and creates conflicts.

```bash
# Check for existing open PRs before any work
gh pr list --state open --json number,title,headRefName,mergeStateStatus

# Also check recently merged PRs to confirm ALREADY-DONE candidates
gh pr list --state merged --limit 20 --json number,title,mergeStateStatus
```

**Pattern (Myrmidons 2026-04-24)**: Launched swarm without auditing first. Discovered 8 existing
open PRs covering most of the target issues. Avoided most duplicate work only because prior run
was checked mid-session. Always audit first.

**Close-before-delegate**: When an issue already has an open PR that covers it, close the issue
with a reference to the PR before delegating any agent to that issue:
```bash
gh issue close <N> --comment "Covered by PR #<M> — closing to avoid duplicate delegation."
```

### Phase 1: Classify Issues (30-60 min)

Use an Explore sub-agent to read and classify all open issues:

```bash
# Get full list with labels
gh issue list --state open --limit 200 --json number,title,labels,body | head -300

# For batches, read 20-30 at a time
gh issue list --state open --limit 30 --skip 0 --json number,title,labels
```

**Classification tiers** (apply pre-filters in this order: DUPLICATE → ALREADY-DONE → verify-before-fix → LOW):

| Tier | Criteria | Action |
| ------ | ---------- | -------- |
| DUPLICATE | Same change as another open issue | `gh issue close N --comment "Duplicate of #M"` |
| ALREADY-DONE | Change already in codebase | Grep (with worktree exclusion) to verify, then close with comment |
| EASY | Single-file doc/text/comment/infra edit, no logic | Implement in batch with Haiku agents |
| MEDIUM | Test additions, audits, single-module refactor, design decisions | Defer |
| HARD | New features, multi-repo coordination, multi-phase rollout | Defer |

**Pre-filter order matters**: Close DUPLICATEs and ALREADY-DONEs first to keep the final EASY count accurate. Run a verify-before-fix pass as a distinct phase — not as part of Haiku classification — before launching fix agents.

**EASY difficulty signals**:
- Title starts with "Update", "Fix typo", "Add note", "Document", "Remove stale", "Pin", "Suppress"
- Issue body says "change X to Y" or "add one line to docstring"
- Affects only `.md`, `README.md`, docstring lines, or single Dockerfile/yaml stanza (not function logic)
- Expected diff: < 20 lines
- No design decision required

**MEDIUM/HARD signals (defer these)**:
- Title contains "evaluate", "investigate", "arm64", "Phase 6", cross-repo references
- Issue body requires a design decision or multi-phase rollout
- Requires coordination with another repository

**EASY queue exhaustion**: For infra-only repos (~235 issues), expect EASY queue to exhaust at ~76% of total issues. Remaining 24% are MEDIUM/HARD. Recognizable when: remaining issues all contain "evaluate", "investigate", "arm64", "Phase 6", or cross-repo references.

### Phase 2: Close Duplicates First

Batch close duplicates before any implementation. This prevents wasted work and keeps
issue count accurate:

```bash
# Close all duplicates in one pass (run in parallel if possible)
gh issue close 3331 --comment "Duplicate of #3321 (both update the historical note in agents/hierarchy.md)"
gh issue close 3256 --comment "Duplicate of #3273 (both add __hash__ tests)"
# ... etc
```

**Duplicate detection pattern**: Look for pairs of issues with nearly identical titles.
Group by target file — issues touching the same file with similar descriptions are usually duplicates.

### Phase 3: Group by Target File (Critical for ci.yml)

**CRITICAL — Branch base check before dispatching agents:**

Before spawning any worktree-isolated agents, verify the main conversation is on `main`:
```bash
git branch --show-current  # Must be 'main'; if not, worktrees will inherit wrong base
```

If L0 is on a feature branch, include this as **step 1** in every Haiku agent prompt:
```bash
git fetch origin
git checkout -B <issue-number>-<slug> origin/main  # Explicit base, not inherited
```

This prevents "This branch can't be rebased" errors caused by unrelated commits from the L0's current branch silently appearing in agent branches.

Before branching, group EASY issues by which file they edit. Issues sharing a file
**must go in the same PR** (to avoid merge conflicts):

```
PR 1: agents/hierarchy.md → closes #3321, #3322
PR 2: CLAUDE.md           → closes #3325, #3326, #3367, #3216
PR 3: .github/workflows/ci.yml → closes #all-ci-issues-in-this-wave
```

**CRITICAL — ci.yml conflict avoidance**: Multiple issues often touch `.github/workflows/ci.yml` per wave. Batch ALL ci.yml-touching issues into ONE agent per wave. Never dispatch two agents with the same target file in the same wave — guaranteed merge conflict. Use Sonnet (not Haiku) for ci.yml batches due to multi-issue interdependencies.

**CRITICAL — Hot-file serialization**: Some scripts are "hot files" that many issues touch simultaneously (e.g., `scripts/apply.sh`, `scripts/lib/reconcile.sh` in Myrmidons-style repos). Apply the same one-agent-per-wave rule:
- At most one agent per sub-wave touches each hot file
- Issues that both require a hot file must be put in different sub-waves
- Use Sonnet (not Haiku) for hot-file issues due to structural complexity
- Document the hot-file serialization order in the wave plan so reviewers understand the dependency chain

```
# Example hot-file wave split:
Sub-wave A1: Agent 1 (apply.sh change for issue #X), Agent 2 (reconcile.sh change for #Y)
Sub-wave A2: Agent 3 (apply.sh change for issue #Z) — must wait for A1 to merge first
```

Issues touching different files can be implemented in parallel.

### Phase 4: Stash-Based Multi-File Workflow

When sub-agents modify the main worktree (not isolated worktrees), use git stash
to separate changes into per-issue branches:

```bash
# 1. Let agents edit all files in main worktree
# 2. Stash all changes together
git stash

# 3. For each issue:
git checkout -b NNNN-auto-impl origin/main
git checkout stash -- path/to/changed/file.mojo
pixi run pre-commit run --all-files
git add path/to/changed/file.mojo
git commit -m "type(scope): description\n\nCloses #NNNN\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin NNNN-auto-impl
gh pr create --title "..." --body "Closes #NNNN"
gh pr merge --auto --rebase
```

### Phase 5: Per-PR Workflow (Standard)

For files not in the stash, create branches directly:

```bash
git fetch origin && git checkout -b NNNN-auto-impl origin/main
# read file BEFORE editing
# make edit
pixi run pre-commit run --all-files  # must pass
git add <file>
git commit -m "type(scope): description

Closes #NNNN

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin NNNN-auto-impl
gh pr create --title "type(scope): description" --body "Closes #NNNN"
gh pr merge --auto --rebase
```

### Phase 6: Verify Already-Done Issues

For issues claiming a change is needed, grep first — and always exclude worktrees:

```bash
# CORRECT: exclude worktrees, issue_implementer, claude, and git internals
grep -rn "pattern" /path/to/repo/ \
  --include="*.py" --include="*.toml" --include="*.yml" \
  --exclude-dir=".git" \
  --exclude-dir=".worktrees" \
  --exclude-dir=".issue_implementer" \
  --exclude-dir=".claude"

# WRONG: plain grep picks up stale worktree content — gives false "still present" signals
grep -rn "pattern" /path/to/repo/
```

Stale worktrees contain old branch state from prior work. If you grep without excluding them:
- An issue that claims "remove stale `--cov` flag" may appear as still present because the flag exists in a worktree from a prior branch — but is already gone from main.
- A dependency pin done via direct curl (not in a config file) may not appear in `pixi.toml` but the worktree shows an old pinned version string.

**ALREADY-DONE detection rate**: ~12% of issues in a large backlog are already implemented. Detect with grep before dispatching. Most common: CI checks already added by earlier waves, Dockerfile pins already applied.

```bash
# If no matches in main tree → change already done → close with verification comment
gh issue close NNNN --comment "Verified: already resolved. [pattern] not found in main tree. Closing."
```

### Phase 7: Wave Ground-Truth Reconciliation

After each wave completes, always run:
```bash
gh pr list --author "@me" --state all --limit 50
```

Never trust agent-reported PR numbers — agents report stale in-flight views. This is the only reliable source of truth for wave reconciliation.

### Quick Reference

```bash
# Wave sizing: ≤5 agents/wave optimal for infra repos
# Model routing:
#   Haiku: single-file mechanical EASY issues
#   Sonnet: batched ci.yml issues, multi-file or multi-issue PRs

# Exact branch name imperative in every agent prompt:
# "Run: git checkout -B <N>-auto-impl origin/main"

# STOP escape hatches in every agent prompt:
# "If the issue is already implemented, STOP and report ALREADY-DONE"
# "If the spec is unclear, STOP and report BLOCKED"

# After each wave:
gh pr list --author "@me" --state all --limit 50
```

### Diagnosing CI Failures

When `gh pr checks` shows failures, check the underlying job conclusion before touching code:

```bash
# Distinguish cancelled (runner exhaustion) from failure (real bug)
gh run view <run-id> --json jobs --jq '.jobs[] | {name, conclusion}'
```

- `conclusion: "cancelled"` → runner exhaustion; fix is retrigger, not code change
- `conclusion: "failure"` → real failure; read the logs

**Retrigger recipe** (when conclusion is cancelled):
```bash
git fetch origin
git rebase origin/main          # preserves GPG signatures when no conflict
git push --force-with-lease     # triggers fresh CI on available runners
```

**`pending` vs `queued`** in `gh pr checks` output:
- `pending` = runner accepted the job (healthy)
- `queued` = waiting for an available runner (pool exhausted)

After a retrigger, seeing `pending` instead of `queued` confirms runners have recovered.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Sub-agent isolation with `isolation="worktree"` parameter (2026-03-06) | Launched 5 parallel agents expecting each to work in its own worktree | Agents edited files in the main worktree, not isolated worktrees; all 5 changes landed in the main worktree | The `isolation="worktree"` parameter does not guarantee sub-agents work in separate git worktrees; they share the working directory. Use git stash to separate their changes post-facto. (Note: this failure did NOT occur in the 2026-04-12 session — may be environment-specific; see Results.) |
| Sub-agents completing full git workflow (2026-03-06) | Asked sub-agents to create branches, commit, push, and create PRs | Agents completed the file edits but did not execute the git commands (output descriptions instead) | Sub-agents reliably edit files but frequently skip the git+PR workflow. Always execute git operations in the main agent after sub-agents return. (Note: NOT observed in 2026-04-12 session with worktree isolation — all 12 agents completed full git workflow.) |
| Reading files after `git checkout -b` from stash | Assumed `git checkout stash -- file` would have the correct content immediately | The `git checkout stash` command works correctly but the branch check showed "branch already exists" because a previous stash attempt created it | Check for existing branches with `git branch --list` before creating; use `git checkout existing-branch` if it exists. |
| Running `pixi run pre-commit run <specific-file>` | Tried to run hooks on only the changed file | Hook IDs don't match file paths — the command fails with "No hook with id path/to/file" | Always run `pixi run pre-commit run --all-files`, never by file path. |
| Grepping for ALREADY-DONE without worktree exclusion (2026-04-12) | Plain `grep -rn pattern /repo/` to detect whether issue content still exists | Worktrees contain stale branch state — gave false "still present" for #1655 (nats-server) and #1671 (--cov refs) | Always pass `--exclude-dir=.worktrees --exclude-dir=.issue_implementer --exclude-dir=.claude --exclude-dir=.git` when grepping for ALREADY-DONE verification |
| Running verify-before-fix as part of Haiku classification (2026-04-12) | Expected Haiku to catch all ALREADY-DONE issues during the classification pass | Haiku missed 2 ALREADY-DONE issues (4.7% miss rate) where implementation was in a different location than the issue title implied | Always run verify-before-fix as a distinct separate phase after Haiku classification, not as part of it |
| Haiku agents with `isolation: "worktree"` dispatched while L0 was on a non-main branch (`15-exporter-port-9101`) | Agents created worktrees and checked out branches, which inherited the L0's current branch as base | Worktrees start from the current HEAD of the base repo — not from `origin/main` — so each branch silently included 4-5 unrelated commits. GitHub refused rebase merge: "This branch can't be rebased." | Always verify L0 is on `main` before dispatching worktree agents, OR explicitly include `git fetch origin && git checkout -B <branch> origin/main` as step 1 in every agent prompt instead of relying on worktree inheritance |
| PR number collision from parallel agents (2026-04-23) | Two parallel agents working in HomericIntelligence/Odysseus simultaneously both reported "PR #120" in their output | Agents report their own in-flight view of PR numbers, which can be stale when two agents race to create PRs in the same repo; both PRs existed but with different numbers | Always run `gh pr list --author "@me" --state all` after each wave to get ground-truth PR numbers — never trust agent-reported PR numbers |
| Worktree creation failure on symlink-heavy repo (2026-04-23) | Agent for issue #58 failed during worktree creation with "Updating files: X%" timeout error | HomericIntelligence/Odysseus has 12 submodule symlinks; worktree checkout can time out on repos with many symlinks when many files must be resolved | Fallback: `git checkout -b <branch> origin/main` in main worktree directly, push the branch, then `git checkout <original-branch>` to return afterward |
| Agent branch naming drift (2026-04-23) | Agent for issue #18 used branch `18-fix-runbook` instead of the specified `18-auto-impl` convention | Haiku agents sometimes derive branch names from the issue title rather than following the `<N>-auto-impl` convention when the convention is only mentioned as a note rather than an explicit command | Explicitly spell out the exact branch name in every agent prompt as an imperative: "Run: git checkout -b 18-auto-impl origin/main" — never rely on the agent interpreting a naming convention |
| Two agents merging into same PR branch (2026-04-23) | Agents for #50 and #53 (both in Wave A1 parallel) both committed to branch `50-auto-impl` | Parallel worktree agents targeting similar branch names in the same repo; the worktrees may have been assigned the same directory, causing both agents to commit to the same branch | Use distinct, non-overlapping branch names per agent; verify each agent's branch with `gh pr list` after the wave; both issues still closed correctly but PR was messy |
| Docker inline comment inside multi-line RUN block (AchaeanFleet 2026-04-23) | Wrote `RUN curl \ # download step` or `wget \ # comment` inside a `RUN` backslash-continuation block | Docker parser interprets the comment text as a new instruction; emits "unknown instruction: wget" or "unknown instruction: comment" parse error | Move comments BEFORE the RUN block entirely: `# download step\nRUN curl \` — never put comments inside multi-line RUN backslash blocks |
| Two agents dispatched to the same ci.yml file in the same wave (AchaeanFleet 2026-04-23) | Multiple issues touched `.github/workflows/ci.yml`; separate Haiku agents dispatched per issue | Guaranteed merge conflict — both agents produce PRs touching ci.yml in overlapping locations; only one can merge automatically | Batch ALL ci.yml issues within a wave into ONE agent. Use Sonnet for this agent due to multi-issue interdependencies |
| Trivy action SHA pinning with unverified SHAs (AchaeanFleet 2026-04-23) | Agents generated plausible-looking SHAs for `aquasecurity/trivy-action` version pins | Some agent-generated SHAs were non-existent (fabricated). CI failed on `uses: aquasecurity/trivy-action@<bad-sha>` | Always verify pinned SHAs exist on GitHub before accepting. Correct SHA for aquasecurity/trivy-action v0.35.0: `57a97c7e7821a5776cebc9bb87c984fa69cba8f1` |
| pixi.lock not committed after pixi.toml change (AchaeanFleet 2026-04-23) | Agent updated `pixi.toml` (added/changed dependency) without also committing updated `pixi.lock` | CI fails with "lock-file not up-to-date with workspace" — pixi enforces lock-file consistency in CI | After any `pixi.toml` change, run `pixi install` to regenerate `pixi.lock`, then commit both files together |
| Two parallel agents creating the same new package independently (ProjectScylla 2026-04-23) | Wave 1 agents for separate issues both needed a new `src/scylla/agamemnon/` package; each agent created `__init__.py` and package files independently in their worktrees | On rebase, both PRs added the same files — second PR rebase produced add/add conflicts on `scylla/agamemnon/__init__.py` and other package files | When multiple Wave 1 agents may create a shared package, batch them into one agent OR use the superset-of-both-sides strategy: accept all files from both sides, keeping the union. The second PR author should cherry-pick non-conflicting changes on top of the first merged PR. |
| validate_model decorator dead-parameter pattern (ProjectScylla 2026-04-23) | Used `@retry_with_backoff(max_retries=3, initial_delay=60)` at the decorator call site, then callers passed `(max_retries=1, base_delay=5)` as function arguments expecting them to control retry behavior | The decorator captured `max_retries=3, initial_delay=60` at decoration time and ignored the function's own `max_retries`/`base_delay` parameters entirely; callers got 3 retries at 60/120/240s (7+ min stall) instead of the intended 1 retry at 5s | When a function accepts retry parameters that callers must be able to control, build the decorator dynamically inside the function body using the caller's parameter values instead of hardcoding at decoration time. Pattern: `decorator = retry_with_backoff(max_retries=max_retries, base_delay=base_delay); return decorator(fn)(*args, **kwargs)` |
| `npm ci` in typecheck job without lockfile (ProjectProteus 2026-04-25) | Added a `typecheck` CI job using `npm ci` as the install step, then dispatched implementation PRs that included this job definition | `npm ci` requires a `package-lock.json` (or npm-shrinkwrap.json with lockfileVersion >= 1). The repo had no lockfile committed (issue #21 was open). CI failed immediately on the install step with "The `npm ci` command can only install with an existing package-lock.json" | When adding CI jobs that install npm deps, check whether a lockfile exists first: `ls package-lock.json`. If absent, use `npm install` instead of `npm ci` until the lockfile issue is resolved. Add a comment in the workflow: `# TODO: switch to npm ci once package-lock.json is committed (issue #NN)` |
| Auto-merge disabled on target repo (ProjectProteus 2026-04-25) | All agent prompts included `gh pr merge <NUMBER> --auto --rebase` as the final step | The repository had `enablePullRequestAutoMerge` disabled at the repo settings level. The command either silently failed or returned an error, leaving PRs open | Before launching waves, check if auto-merge is enabled: `gh repo view --json autoMergeAllowed --jq '.autoMergeAllowed'`. If `false`, remove `--auto` from all agent prompts and note that PRs require manual merge or reviewer approval. Do not assume auto-merge works across all repos. |
| Pre-commit hooks absent in target repo (ProjectProteus 2026-04-25) | Standard agent prompt template included `pre-commit run --files <changed-files>` steps | ProjectProteus had no `.pre-commit-config.yaml` (issue #25 was requesting it). Running pre-commit in agents is a no-op or errors out | Before generating agent prompts, check `ls .pre-commit-config.yaml`. If absent, remove pre-commit steps from all agent prompts entirely. Reinstate them after the hooks issue is resolved. |
| Launching ≤5 agents without checking for existing PRs (Myrmidons 2026-04-24) | Dispatched first wave of swarm agents without running `gh pr list --state open` first | Discovered 8 existing open PRs from a prior run covering most target issues; wasted context in initial wave analysis | Always run `gh pr list --state open` before any wave dispatch; audit PR titles against issue list; close issues covered by existing PRs before delegating |
| Two agents touching `scripts/apply.sh` in the same sub-wave (Myrmidons 2026-04-24) | Dispatched parallel agents for issues #187 and #195 in the same sub-wave; both touched `scripts/apply.sh` | Guaranteed merge conflict — both PRs modified the same function block; second PR rebase required manual resolution | Apply hot-file serialization: identify all "hot files" before wave planning; at most one agent per hot file per sub-wave; issues touching the same hot file must be in different sub-waves |
| Delegating an issue to an agent when it was already covered by an open PR (Myrmidons 2026-04-24) | Issue #211 had an open PR from a prior run; dispatched a new agent without checking | Two PRs covering the same issue; one was abandoned creating noise in the PR list | Use close-before-delegate: close the issue with a reference to the existing PR, then skip dispatching a new agent |
| Conan + cnats (nats.c) build failure: missing libssl-dev in Dockerfile builder stage (ProjectKeystone 2026-04-25) | Conan resolved nats.c and its transitive OpenSSL dependency; Dockerfile builder stage lacked `libssl-dev` | Conan downloads sources and compiles them, but the compiler still needs system OpenSSL headers. CMake build failed with `openssl/ssl.h: No such file or directory` even though Conan install succeeded | Add `libssl-dev` to the apt-get install block in every Dockerfile builder stage when any Conan dependency (direct or transitive) uses OpenSSL. This is non-obvious from `conanfile.py` since Conan resolves transitive deps silently |
| TSan build added to project using concurrentqueue (ProjectKeystone 2026-04-25) | Attempted to add `-fsanitize=thread` build to verify thread safety; concurrentqueue (moodycamel) lock-free atomics were in use | concurrentqueue triggers TSan false positives by design — the library uses intentional relaxed-ordering patterns that TSan cannot distinguish from real races. Tests fail spuriously under TSan | TSan + concurrentqueue (or any similar lock-free lib using intentional relaxed ordering) is a hard blocker. Classify any issue requiring TSan + concurrentqueue as HARD — cannot be resolved without replacing the dependency. Never attempt to add TSan builds to projects with concurrentqueue |
| enable_shared_from_this diamond inheritance on derived class (ProjectKeystone 2026-04-25) | When fixing use-after-free via `weak_ptr` capture, added `std::enable_shared_from_this<T>` to a derived class (e.g., `TaskAgent`) to call `weak_from_this()` | Base class `AgentCore` already inherited `enable_shared_from_this<AgentCore>`. Derived class inheriting it again caused diamond inheritance compile error: "ambiguous base class 'enable_shared_from_this'" | Before adding `enable_shared_from_this<T>` to any class, run `grep -rn enable_shared_from_this` across all base classes in the hierarchy. If base already has it, the derived class can call `weak_from_this()` directly without re-inheriting |
| Two agents both modifying CMakeLists.txt in the same wave (ProjectKeystone 2026-04-25) | Despite same-file grouping rules, two different agents both modified `CMakeLists.txt` for separate SPDX/spdlog fixes (PRs #392 and #395) in the same wave because the changes appeared unrelated | Second PR could not auto-merge cleanly; one became a duplicate requiring manual resolution | Treat `CMakeLists.txt` as a hard file-grouping anchor: any issue touching it must be batched into ONE agent per wave, regardless of how different the individual changes appear. Apply the same rule as ci.yml: batch all CMakeLists.txt issues into a single Sonnet agent per wave |
| Adding @pytest.mark.asyncio when asyncio_mode='auto' set in pyproject.toml (ProjectKeystone 2026-04-25) | Agent wrote new Python test files and added `@pytest.mark.asyncio` decorators to async test functions | `pyproject.toml` already had `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`. With auto mode, pytest-asyncio automatically treats all async test functions as async tests — the decorator is redundant and produces deprecation warnings or errors | Before writing Python test files, check: `grep -A5 "pytest.ini_options" pyproject.toml \| grep asyncio_mode`. If`asyncio_mode = "auto"` is present, omit all `@pytest.mark.asyncio` decorators |
| Trusting agent-reported PR numbers without verification (ProjectKeystone 2026-04-25) | In 3 out of 16 waves, accepted agent's final output ("PR #403") as the authoritative PR number for wave reconciliation | Agents report their in-flight view of PR numbers, which can be stale or incorrect when races occur or the agent mistakes a draft PR number. 3/16 waves had wrong agent-reported PR numbers | After every wave, always verify PR numbers with `gh pr list --author "@me" --state all --limit 50`. Never trust agent-reported PR numbers as ground truth |
| CI cancelled mistaken for failure | Diagnosed PR checks showing 'fail' for Python Tests and codeql-analysis after rebase+push | Job conclusion was `cancelled` (runner exhaustion from 28-PR swarm), not `failure` — CI Summary gate treats `cancelled != "success"` and exits 1 | Run `gh run view <id> --json jobs --jq '.jobs[] \| {name, conclusion}'` before assuming code is broken; if all are `cancelled`, rebase+force-push to retrigger — do not change code |

## Results & Parameters

### C++20/Conan/pixi Project-Specific Guards

Run these checks **before dispatching any agents** to a C++20/CMake/Conan project:

| # | Guard Check | Command | Action if Fails |
| --- | ------------- | --------- | ----------------- |
| 1 | Dockerfile has `libssl-dev` if any Conan dep uses OpenSSL | `grep libssl-dev Dockerfile* docker/*/Dockerfile 2>/dev/null` | Add `libssl-dev` to the apt-get install block in every builder stage |
| 2 | No concurrentqueue (or similar lock-free lib) if TSan build planned | `grep -rn "concurrentqueue\|moodycamel" CMakeLists.txt conanfile.py pixi.toml 2>/dev/null` | Classify any TSan-requiring issues as HARD; skip TSan build addition |
| 3 | Check base class hierarchy for `enable_shared_from_this` before adding to derived | `grep -rn "enable_shared_from_this" src/ include/ 2>/dev/null` | If base has it, derived must call `weak_from_this()` directly, not re-inherit |
| 4 | CMakeLists.txt is treated as hard file-grouping anchor | Manual wave planning check | Batch ALL CMakeLists.txt issues into ONE agent per wave (like ci.yml rule) |
| 5 | Check pyproject.toml for `asyncio_mode` before writing Python tests | `grep -A5 "pytest.ini_options" pyproject.toml 2>/dev/null \| grep asyncio_mode` | If `asyncio_mode = "auto"`, omit all `@pytest.mark.asyncio` decorators |
| 6 | Verify PR numbers after each wave | `gh pr list --author "@me" --state all --limit 50` | Never trust agent-reported PR numbers; always verify with this command |

```bash
# C++20 pre-swarm checklist (run once before any wave dispatch):

# 1. Dockerfile libssl-dev check
grep -rn "libssl-dev" Dockerfile* docker/ 2>/dev/null || echo "WARN: libssl-dev not found — check if Conan deps use OpenSSL"

# 2. TSan + concurrentqueue blocker check
grep -rn "concurrentqueue\|moodycamel" CMakeLists.txt conanfile.py pixi.toml 2>/dev/null && echo "WARN: concurrentqueue in use — do NOT add TSan builds"

# 3. enable_shared_from_this hierarchy check (run before any weak_ptr fix)
grep -rn "enable_shared_from_this" src/ include/ 2>/dev/null

# 4. CMakeLists.txt — enforce single-agent-per-wave in wave planning (manual)

# 5. asyncio_mode auto check
grep -A5 "pytest.ini_options" pyproject.toml 2>/dev/null | grep asyncio_mode

# 6. Post-wave PR verification (after each wave)
gh pr list --author "@me" --state all --limit 50
```

### Session Statistics (2026-04-25) — ProjectKeystone 180-Issue C++20 Swarm

| Metric | Value |
| -------- | ------- |
| Starting open issues | 180 |
| Wave architecture | 7 EASY waves + 9 MEDIUM waves |
| C++20-specific failure modes discovered | 7 |
| Dockerfile libssl-dev failures | Yes — blocked builds until fix applied |
| TSan+concurrentqueue issues classified HARD | Yes — classified as hard blockers |
| CMakeLists.txt double-agent conflicts | 1 (PRs #392 and #395 — one duplicate) |
| enable_shared_from_this diamond inheritance | 1 compile error caught during implementation |
| asyncio_mode decorator noise | Yes — decorators omitted after pyproject.toml check |
| Agent-reported wrong PR numbers | 3 out of 16 waves |
| Verification | verified-local |

### Session Statistics (2026-04-24) — Myrmidons shellcheck-warnings Swarm

| Metric | Value |
| -------- | ------- |
| Target issues | ~25 shellcheck warnings (issues #187-#211) |
| Wave architecture | EASY(Haiku) → MEDIUM(Sonnet) → HARD(Opus) |
| Hot files serialized | scripts/apply.sh, scripts/lib/reconcile.sh (1 agent per sub-wave each) |
| Wave 1 | Verification sweep — closed ALREADY-DONE issues before implementation |
| Pre-swarm PR discovery | 8 existing open PRs found; most issues already covered |
| CHANGELOG tracking | Each agent commented their entry; Wave 6 consolidated |
| CI result | All PRs merged, main CI green at 333b40d |
| Verification | verified-ci |

### Session Statistics (2026-04-25) — ProjectProteus 43-Issue Swarm

| Metric | Value |
| -------- | ------- |
| Starting open issues | 43 |
| ALREADY-DONE closed | 4 (#16, #18, #22, #26) |
| DUPLICATE closed | 1 (#13 → #6) |
| EASY implemented | ~20 issues |
| PRs created | 14 |
| PRs merged | ~8 (rest pending review — auto-merge disabled) |
| MEDIUM deferred | 12 |
| HARD deferred | 6 |
| Auto-merge enabled | NO — branch protection requires reviews |
| Pre-commit hooks | Absent — skipped in all agent prompts |
| Lockfile present | NO — used `npm install` not `npm ci` in CI jobs |

### Session Statistics (2026-04-23) — ProjectScylla 15-Issue Medium/High Swarm

| Metric | Value |
| -------- | ------- |
| Starting issues | 15 (LOW to HIGH difficulty) |
| ALREADY-DONE detections | 3 |
| PRs merged (verified-ci) | 12 |
| Waves | 5 (max 5 agents/wave) |
| Wave size | ≤5 agents |
| Worktree isolation | isolation="worktree" — worked correctly |
| add/add conflict rate | 1 package (scylla/agamemnon/) from 2 independent creators |
| Resolution | superset of both sides |

### Session Statistics (2026-04-23) — AchaeanFleet 235-Issue Swarm

| Metric | Value |
| -------- | ------- |
| Starting open issues | 235 |
| Ending open issues | 33 |
| Issues closed/implemented | 202 |
| PRs merged (verified-ci) | 91 |
| PRs still pending CI | 7 |
| Waves | 24+ |
| Wave size | ≤5 agents |
| ALREADY-DONE rate | ~12% (25+ of 235) |
| EASY queue exhaustion | ~76% of total (180 of 235) |
| Remaining issues | 33 — all MEDIUM/HARD |
| Total wall-clock time | Multi-day session |

### Session Statistics (2026-03-06) — ProjectOdyssey

| Metric | Value |
| -------- | ------- |
| Issues triaged | 165 |
| Duplicates closed | 9 |
| Already-done closed | 2 (#3227, #3195) |
| LOW PRs created | 15 |
| PRs failing pre-commit | 0 |
| Issues combined into single PR | 6 (two multi-issue PRs) |
| Total wall-clock time | ~90 minutes |

### Session Statistics (2026-04-12) — ProjectScylla 64-Issue Pass

| Metric | Value |
| -------- | ------- |
| Issues classified by Haiku | 64 |
| Haiku ALREADY-DONE miss rate | 4.7% (3 false negatives) |
| ALREADY-DONE caught by verify-before-fix pass | 3 (including #1655, #1671 caught by worktree-excluded grep) |
| Waves | 4 |
| PRs created | 12 |
| PRs merged CI-green | 11 |
| Agent git-op failures | 0 — all 12 Sonnet agents completed full branch/commit/push/PR/auto-merge |
| Worktree isolation failures | 0 — agents worked in isolated worktrees, not main tree |

**Note on `isolation="worktree"` reliability**: In this session on ProjectScylla (Python/pixi repo), `Task(isolation="worktree")` worked correctly — agents created branches and PRs in isolated worktrees without polluting the main worktree. The failure mode documented in the 2026-03-06 session (agents editing main worktree) did NOT occur. Hypothesis: the failure may be environment-specific. Always verify that each PR was created from the correct branch, not from main.

### Deferred MEDIUM/HARD Categories (AchaeanFleet Infra-Repo Pattern)

These categories consistently remain after EASY queue exhausts in infra-only repos:

| Category | Signal | Why MEDIUM/HARD |
| ---------- | -------- | ----------------- |
| Artifact pipeline refactor | "push-to-registry", "reuse build-vessels output" | Multi-step architecture change |
| Multi-arch support | "arm64", "QEMU", "multi-arch matrix" | CI matrix expansion + QEMU setup |
| New test functions | "dagger testVesselTools()", "add test for X" | Requires understanding tool API |
| Compose overlay design | "depends_on", "service ordering" | Cross-service dependency design |
| Nomad TLS/cert distribution | "Phase 6", "cert rotation" | Multi-phase future work |

### Branch Naming Convention

```
NNNN-auto-impl   (where NNNN = primary issue number)
```

### Commit Message Template

```
type(scope): brief description

Closes #NNNN
[Closes #MMMM if combined PR]

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Issue Classification Heuristics

```
EASY if ALL of:
  - Title has: "Update", "Document", "Fix typo", "Remove stale", "Add note", "Pin", "Suppress"
  - Body has: single file target
  - Expected diff: < 20 lines
  - No logic/behavior change (only text/comments/docs/infra stanza)

DUPLICATE if:
  - Same target file as another open issue
  - Same or nearly same description
  - No unique work required beyond the kept issue

ALREADY-DONE if:
  - Issue says "remove X" → grep for X → not found
  - Issue says "add Y to Z" → grep for Y in Z → already present

MEDIUM/HARD if:
  - Requires design decision or "evaluate"/"investigate" verb
  - Cross-repo coordination required
  - "arm64", "Phase 6", multi-phase rollout
```

### Haiku Prompt Template (validated at scale)

```
You are implementing GitHub issue #<N> in repo <REPO>.

Issue: <title>
Body: <body>

Steps:
1. Run: git checkout -B <N>-auto-impl origin/main
2. [implementation steps specific to issue]
3. Run pre-commit and fix any failures
4. Commit with message: "type(scope): description\n\nCloses #<N>\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
5. Push and create PR with `gh pr create --title "..." --body "Closes #<N>"`
6. Run: gh pr merge <PR_NUMBER> --auto --rebase

STOP and report ALREADY-DONE if the change described in the issue is already present in the codebase.
STOP and report BLOCKED if the spec is unclear or requires a design decision.
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/ProjectKeystone | 180-issue C++20 swarm, 7 EASY + 9 MEDIUM waves (2026-04-25) | 7 C++20/Conan/pixi-specific failure modes discovered; libssl-dev Dockerfile gap; TSan+concurrentqueue hard blocker; CMakeLists.txt double-agent; enable_shared_from_this diamond inheritance; asyncio_mode='auto' decorator check; agent PR number unreliability |
| HomericIntelligence/Myrmidons | shellcheck-warnings swarm (~25 issues #187-#211), all PRs merged CI-green (2026-04-24) | Wave-based with hot-file serialization; 8 existing PRs discovered pre-swarm; CHANGELOG consolidation in Wave 6 |
| HomericIntelligence/ProjectProteus | 43-issue swarm, 14 PRs created, ~8 merged (2026-04-25) | Auto-merge disabled; no lockfile (npm install); no pre-commit config; 4 ALREADY-DONE; 1 DUPLICATE |
| ProjectOdyssey | 165-issue backlog cleanup, March 2026 | [notes.md](../references/notes.md) |
| ProjectScylla | 64-issue myrmidon swarm pass, 4 waves, 12 PRs (2026-04-12) | 11/12 PRs merged CI-green; worktree isolation worked correctly; verify-before-fix caught 3 ALREADY-DONE issues |
| HomericIntelligence/Odysseus | 35-issue triage, 19 resolved (17 PRs + 2 ALREADY-DONE), meta-repo with 12 submodule symlinks (2026-04-23) | 0 git-op failures; worktree creation timeout on symlink-heavy repo (fallback to main worktree); parallel agents reported colliding PR numbers; Haiku branch naming drift to title-slug form |
| HomericIntelligence/AchaeanFleet | 235-issue myrmidon swarm, 24+ waves, 91 PRs merged verified-ci (2026-04-23) | 202/235 issues closed; EASY queue exhausted at 76%; Docker inline comment parse error; ci.yml conflict avoidance; trivy SHA pinning; pixi.lock sync |
| ProjectScylla | 15-issue medium/high swarm, 5 waves, 12 PRs merged (2026-04-23) | 3 ALREADY-DONE; add/add conflicts from parallel package creation; validate_model dead-parameter pattern |
