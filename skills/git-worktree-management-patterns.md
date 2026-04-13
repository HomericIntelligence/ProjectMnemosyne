---
name: git-worktree-management-patterns
description: "Use when: (1) creating isolated git worktrees for parallel development on multiple issues, (2) switching between worktrees without stashing, (3) syncing feature branches with main, (4) cleaning up single or multiple stale worktrees after PRs merge, (5) removing all worktrees in bulk after parallel development sessions, (6) fixing file edits that landed in the wrong worktree, (7) parsing git worktree list --porcelain output programmatically, (8) fixing worktree creation failures due to stale origin/HEAD or missing origin/main, (9) fixing branch name collisions in parallel E2E test runs, (10) enforcing branch deletion policy — always defer branch deletion to user, (11) avoiding repeated permission prompts in sandboxed harnesses by running git from inside the worktree instead of driving every command through `git -C <path>`, (12) cleaning stale /tmp/mnemosyne-skill-* worktree directories before parallel /learn sub-agents, (13) cleaning 20+ mixed worktrees using myrmidon swarm wave parallelization, (14) batch-fixing end-of-file newline violations across multiple branches, (15) worktrees with uncommitted skill documentation requiring a 2-commit markdownlint pattern."
category: tooling
date: 2026-04-06
version: "2.4.0"
user-invocable: false
verification: unverified
history: git-worktree-management-patterns.history
tags: []
---
# git-worktree-management-patterns

Consolidated skill for all git worktree patterns: creation, switching, syncing, cleanup (single and mass), correct file edit placement, programmatic path detection from porcelain output, stale origin/HEAD fallback fixes, branch name collision fixes in parallel automation, and workdir-first operation in sandboxed harnesses.

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-04-06 |
| Objective | Consolidated skill covering all git worktree creation, use, and cleanup patterns — including branch deletion policy |
| Outcome | v2.4.0: Merged git-worktree-cleanup.md — added myrmidon wave parallelization, Phase 4 (uncommitted skill docs / 2-commit markdownlint), Phase 5 (batch EOF fixing), model tier table, artifact patterns, verified-on table |
| Verification | unverified |
| History | [changelog](./git-worktree-management-patterns.history) |

## When to Use

- Starting work on a new issue in parallel with other ongoing work
- Need to work on multiple issues simultaneously without stashing
- After parallel wave execution where agents used worktree isolation
- `git worktree list` shows worktrees for merged PR branches
- Cleaning up nested agent-in-agent worktrees (depth 2 or 3)
- File edits landed in main instead of the intended feature branch
- `git push` rejected on feature branch due to diverged remote
- Parsing `git worktree list --porcelain` output to find paths by branch name
- `git worktree add` fails with exit 128 referencing `origin/main`
- `git symbolic-ref refs/remotes/origin/HEAD --short` returns "not a symbolic ref"
- Branch name collisions in parallel E2E test runs (`fatal: A branch named '...' already exists`)
- After mass parallel auto-implementation sessions leaving 20+ worktrees
- Any time you would normally run `git branch -d` or `git branch -D` — defer to user instead
- Git commands run from a parent harness keep triggering permission prompts or `*.lock` errors while the actual edits live inside a dedicated worktree
- Before spawning parallel `/hephaestus:learn` sub-agents, need to clean stale `/tmp/mnemosyne-skill-*` directories left by prior `/learn` invocations that failed to clean up
- Pool of 20+ worktrees with mixed categories (stale, unreleased, conflict-heavy) — use Myrmidon wave pattern
- Multiple branches failing pre-commit `end-of-file-fixer` hook on the same file
- Worktrees with uncommitted skill docs (SKILL.md + plugin.json) that need a PR before removal
- `git worktree list` has entries with `[gone]` remote branches
- 5+ worktrees with uncommitted changes (skill docs, registrations, etc.)

## Verified Workflow

### Quick Reference

```bash
# Create worktree for new issue
git worktree add .worktrees/issue-<N> -b <N>-feature-name

# List all worktrees
git worktree list

# Switch to worktree (just cd) and stay there for day-to-day git operations
cd <repo>/.worktrees/issue-<N>
git branch --show-current
git status
git add <files>
git commit -m "type(scope): summary"
git push -u origin <branch>

# Sync feature branch with main from inside the worktree
git fetch origin
git rebase origin/main

# Remove single worktree
cd <repo>
git worktree remove .worktrees/issue-<N>

# Prune stale entries
git worktree prune

# Fix stale origin/HEAD
git fetch origin && git remote set-head origin --auto
```

### Operating Inside The Worktree (Sandbox-Friendly Default)

When an agent or harness already has a dedicated worktree, treat that worktree as
the command root for normal git operations.

**Default pattern:**

```bash
# Parent repo: create or inspect worktrees
git worktree add .worktrees/issue-123 -b issue-123-fix
git worktree list

# Then enter the worktree and stay there
cd .worktrees/issue-123
git branch --show-current
git status
git add <files>
git commit -m "fix: example"
git push -u origin issue-123-fix
```

Use `git -C <path>` sparingly for parent-repo orchestration tasks such as:

- creating worktrees
- listing or pruning worktrees
- auditing many worktrees from one control shell

Avoid `git -C <worktree>` as the default for repeated `status`, `add`, `commit`,
`push`, and `rebase` steps in sandboxed harnesses. In permission-gated
environments, those commands often still write through the shared worktree
metadata under the base repo, which can trigger repeated approval prompts or
`*.lock` failures even though the real work belongs to one isolated worktree.

### Branch Deletion Policy

**CRITICAL: Never delete branches autonomously. Always defer to the user.**

Deleting a branch with `-D` is irreversible (without `git reflog`). Agents must never run `git branch -d` or `git branch -D` on their own. Instead:

1. Check which branches are safe to delete:
   ```bash
   # Branches whose remote is gone (merged/closed PR):
   git branch -v | grep '\[gone\]'

   # Verify content already in main:
   git cherry origin/main <branch>
   # Lines with '-' = in main (safe); Lines with '+' = not in main (keep)
   ```

2. Present a summary to the user:
   ```
   Branches safe to delete (content confirmed in main):
     - 123-feature (PR #456 MERGED, [gone])
     - worktree-agent-abc ([gone])

   Branches to keep (open PR or unconfirmed):
     - 789-wip (PR #101 OPEN)

   To delete: git branch -d 123-feature worktree-agent-abc
   Or ask me to delete specific branches after reviewing.
   ```

3. Wait for user confirmation before running any branch deletion command.

**For remote branch deletion** (also user-confirmed only): Use `gh api` — NOT `git push origin --delete` (which triggers pre-push hooks):
```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api --method DELETE "repos/$REPO/git/refs/heads/<branch-name>"
```

### Worktree Cleanup Completion Requirement

**Always clean up all worktrees before reporting work complete.** Do not declare a task done until:

```bash
git worktree list   # must show only the main working tree
```

Cleanup sequence:
```bash
# 1. Remove each non-main worktree (deepest-nested first)
rm -rf "<path>/ProjectMnemosyne"   # clean untracked dirs first if present
git worktree remove "<path>"

# 2. Prune stale metadata
git worktree prune

# 3. Verify
git worktree list   # should show only main
```

### Creating Worktrees

```bash
# Create worktree on new branch
git worktree add .worktrees/issue-<N> -b <N>-auto-impl

# Create worktree tracking existing remote branch
git worktree add .worktrees/issue-<N> <branch-name>

# List all worktrees
git worktree list
```

**Best practices:**
- One worktree per issue — do not share branches
- Naming: `.worktrees/issue-<N>` for issue-based work, `.claude/worktrees/agent-<id>` for agent isolation
- Each branch can only be checked out in ONE worktree at a time

**Example directory structure:**
```
repo/
├── (main worktree — main branch)
├── .worktrees/
│   ├── issue-42/    (42-feature branch)
│   └── issue-73/    (73-bugfix branch)
```

### Switching Between Worktrees

```bash
# List all worktrees
git worktree list

# Switch (simple cd — no stash needed)
cd <repo>/.worktrees/issue-<N>

# Verify current branch
git branch --show-current

# Quick navigation with fzf (if installed)
cd $(git worktree list | fzf | awk '{print $1}')
```

Terminal aliases for convenience:
```bash
alias wt='git worktree list'
alias wtcd='cd $(git worktree list | fzf | awk "{print \$1}")'
```

### Syncing Feature Branches with Main

```bash
# From inside the feature worktree
git fetch origin

# Rebase feature branch (preferred — linear history)
git rebase origin/main

# Force push after rebase (required)
git push --force-with-lease origin <branch>

# If conflicts during rebase
git status  # see conflicted files
# ... fix files ...
git add .
git rebase --continue

# Abort if needed
git rebase --abort
```

### Correct File Edit Placement

**Problem**: File edits made to absolute paths land in whichever worktree contains those paths — which may not be the intended feature branch.

**Before editing, always verify the target branch:**
```bash
git -C <worktree-path> branch --show-current
# Must print the feature branch name, e.g. 3086-auto-impl
```

**Edit files inside the worktree path:**
```bash
# WRONG (lands on main if main repo is at /repo)
/repo/shared/core/file.mojo

# CORRECT
/repo/.worktrees/issue-N/shared/core/file.mojo
```

**If edits went to the wrong location:**
```bash
WORKTREE="/repo/.worktrees/issue-N"
FILES="shared/core/file.mojo tests/shared/core/test_file.mojo"

# Copy to correct worktree
for f in $FILES; do cp "/repo/$f" "$WORKTREE/$f"; done

# Revert main
git -C /repo checkout -- $FILES

# Verify
git -C "$WORKTREE" diff --stat
```

**If push is rejected due to diverged remote:**
```bash
git -C <worktree> fetch origin <branch>
git -C <worktree> log --oneline HEAD..origin/<branch>  # inspect remote commits
git -C <worktree> reset --hard HEAD~1  # drop local duplicate
git -C <worktree> pull --rebase origin <branch>
```

Do NOT force-push — fetch and rebase instead.

### Single Worktree Cleanup

Remove deepest-nested first (depth 3 → 2 → 1):

```bash
# For nested agent worktrees: remove children before parents
git worktree remove ".claude/worktrees/agent-A/.claude/worktrees/agent-B/.claude/worktrees/agent-C"
git worktree remove ".claude/worktrees/agent-A/.claude/worktrees/agent-B"
git worktree remove ".claude/worktrees/agent-A"

# For issue worktrees with untracked ProjectMnemosyne dirs
rm -rf ".worktrees/issue-N/ProjectMnemosyne"  # clean first, avoids --force
git worktree remove ".worktrees/issue-N"

# Prune stale metadata
git worktree prune

# Verify clean state
git worktree list   # should show only main
git branch -v       # review branch state — present to user for deletion decision
```

**Do NOT delete branches here.** Use the Branch Deletion Policy above — present the list and defer to user.

**Safety Net interaction**: `git worktree remove --force` is blocked when untracked files are present. Delete untracked directories first, then remove without `--force`.

### Mass Cleanup (20+ worktrees)

```bash
# Phase 1: Audit
git worktree list
git branch -v  # [gone] = remote deleted = merged

# Phase 2: Remove stale worktrees (merged PRs) — branch deletion deferred to user
STALE="3033 3061 3062 3063"
for issue in $STALE; do
  rm -rf ".worktrees/issue-$issue/ProjectMnemosyne" \
         ".worktrees/issue-$issue/.issue_implementer"
  git worktree remove ".worktrees/issue-$issue" 2>/dev/null || true
  # Do NOT delete branches here — report to user after cleanup
done

# Phase 3: Check active worktrees for uncommitted changes
ACTIVE="3071 3077 3083"
for issue in $ACTIVE; do
  wt=".worktrees/issue-$issue"
  status=$(git -C "$wt" status --short 2>&1)
  if [ -n "$status" ]; then
    echo "=== $issue has changes ==="
    echo "$status"
  fi
done

# Phase 4: Remove active worktrees
for issue in $ACTIVE; do
  wt=".worktrees/issue-$issue"
  rm -rf "$wt/ProjectMnemosyne"
  git worktree remove "$wt" 2>/dev/null || \
    git worktree remove --force "$wt"
done

# Phase 5: Final cleanup
git worktree prune
git fetch --prune
git checkout main && git pull origin main

# Verify worktrees are clean
git worktree list    # should show only main repo
git status           # clean
ls .worktrees/       # empty

# Report stale branches to user — do NOT delete autonomously
echo "Branches with deleted remotes ([gone]) — safe to delete after confirming:"
git branch -v | grep '\[gone\]'
# Present this list to the user and ask them to confirm before deleting
```

**Key insight**: Rebase-merged PRs require `-D` (not `-d`) because rebase leaves no merge commit, so `-d` refuses with "not fully merged". However, still defer this to the user — present the list and let them run the deletion after reviewing.

### Myrmidon Wave Parallelization (20+ Mixed Worktrees)

Use when `git worktree list` shows 20+ entries with heterogeneous states. Deploy a three-wave myrmidon swarm.

Do NOT use the full myrmidon pattern when:
- Only a few worktrees need cleanup (use the Mass Cleanup section directly)
- All worktrees are already classified (go straight to the appropriate wave)
- Worktrees contain conflicting changes that require human decision-making

#### Step 0: Triage — Categorize All Worktrees

Run this audit before dispatching any agents. Do not skip — incorrect triage leads to over-deletion.

```bash
# Full worktree + branch status audit
git worktree list --porcelain

for branch in $(git branch | tr -d ' *'); do
  ahead=$(git rev-list --count origin/main.."$branch" 2>/dev/null || echo 0)
  pr_state=$(gh pr list --head "$branch" --state all --json state,number \
    -q '.[0] | "\(.state) #\(.number)"' 2>/dev/null || echo "NONE")
  echo "  $branch: ahead=$ahead pr=$pr_state"
done

# Alternative: check for [gone] branches
git branch -v | grep '\[gone\]'
```

**Triage categories:**

| Category | Criteria | Wave | Executor |
|----------|----------|------|----------|
| A — Stale/Merged | 0 commits ahead of main, OR `[gone]` remote, OR merged PR | Wave 1 | Haiku |
| B — Unreleased | 1+ commits ahead, no merged PR (open, closed-without-merge, or NONE) | Wave 2a | Sonnet |
| C — Stale-PR conflict | Closed PR + suspected conflicts with main | Wave 2b | Haiku |

**Conflict pre-check before rebase (Category B/C):**
```bash
# Test rebase without committing (dry-run check)
git fetch origin
git rebase --onto origin/main origin/main <branch> --no-commit 2>&1 | grep -E "CONFLICT|error"
git rebase --abort 2>/dev/null

# Alternative: check if content is already on main
git cherry origin/main <branch> | grep "^+" | wc -l
# 0 lines = all commits already in main
```

If conflicts arise on a branch with a **closed PR**: the fixes were likely superseded by main. Mark it Category C and keep the PR closed — do not rebase.

**Pre-cleanup: remove agent artifacts that block `git worktree remove`:**
```bash
wt="/path/to/worktree"
rm -f "$wt"/.claude-prompt-*.md     # Claude Code session files
rm -rf "$wt/ProjectMnemosyne"        # Cloned knowledge base
rm -f "$wt/.issue_implementer"       # Agent state files
git worktree remove "$wt"            # now succeeds without --force
```

#### Wave 1: Remove Category A (Haiku, Parallel)

Dispatch Haiku sub-agents in parallel. Each agent handles one or a small batch of stale worktrees.

```bash
# Per Haiku agent: remove stale worktree + clean up
wt="<path>"
rm -f "$wt"/.claude-prompt-*.md
rm -rf "$wt/ProjectMnemosyne"
rm -f "$wt/.issue_implementer"
git worktree remove "$wt"

# If worktree has no associated branch to keep, also delete the local branch:
git branch -d <branch-name>
```

**Safety constraint**: Never use `git worktree remove --force`. Remove stray files individually first, then call remove without --force.

Haiku agents can batch multiple stale worktrees in one task (5-10 per agent). No ordering constraints — all are independent.

#### Wave 2a: Rebase + PR for Category B (Sonnet, Per-Branch)

Dispatch one Sonnet sub-agent per Category B branch. Sonnet is required — needs to read the actual diff to write a meaningful PR description.

```bash
cd /path/to/main/repo
git fetch origin

# Check if content is already on main (superseded)
cherry_count=$(git cherry origin/main <branch> | grep "^+" | wc -l)
if [ "$cherry_count" -eq 0 ]; then
  echo "Branch <branch> is superseded — all commits already on main. Skipping PR."
  git branch -d <branch>
  exit 0
fi

# Create isolated worktree for rebase
git worktree add /tmp/rebase-<branch> <branch>
cd /tmp/rebase-<branch>
git rebase origin/main
git push --force-with-lease origin <branch>

# Create PR (Sonnet must read git diff origin/main...HEAD before writing this)
gh pr create \
  --title "<type>(<scope>): <description based on actual changes>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet summarizing what the branch actually implements>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
gh pr merge --auto --rebase

# Cleanup worktree
cd /path/to/main/repo
git worktree remove /tmp/rebase-<branch>
```

#### Wave 2b: Conflict Check for Category C (Haiku, Parallel with 2a)

Run concurrently with Wave 2a.

```bash
cd /path/to/main/repo
git fetch origin

conflict_output=$(git rebase --onto origin/main origin/main <branch> --no-commit 2>&1)
git rebase --abort 2>/dev/null

if echo "$conflict_output" | grep -qE "CONFLICT|error"; then
  echo "Branch <branch>: CONFLICTS DETECTED — work is superseded by main. Keep PR closed."
else
  echo "Branch <branch>: no conflicts — could potentially be resurrected."
  # Escalate to Sonnet if value is suspected
fi
```

**Decision rule**: If a closed PR branch has conflicts with main, do not attempt to fix them. The work is superseded.

#### Wave 3: Prune + Final Cleanup (Haiku)

```bash
git worktree prune
git fetch --prune origin
git branch -v | grep '\[gone\]'  # Verify no orphaned tracking branches remain
git worktree list
git branch -v
```

**Orchestration pattern:**
```
Wave 1: Spawn N Haiku agents (parallel) — one per stale worktree batch
         Wait for ALL Wave 1 agents to complete

Wave 2: SIMULTANEOUSLY spawn:
         - Sonnet agents for Category B (one per branch, parallel)
         - Haiku agents for Category C conflict-check (one per branch, parallel)
         Wait for ALL Wave 2 agents to complete

Wave 3: Spawn 1 Haiku agent for prune + verification
```

### Worktrees with Uncommitted Changes (Skill Documentation)

For worktrees with pending skill documentation (SKILL.md + plugin.json entries):

```bash
# Assess changes
cd .worktrees/<worktree-name> && git status --short

# Categorize by content:
# - Skill files (SKILL.md + plugin.json entry): Commit as skill registration PR
# - Implementation files: Commit as feature PR
# - Merge conflicts: Resolve manually, then proceed

# Commit pattern (with pre-commit hooks — no --no-verify)
git add .claude-plugin/skills/<name>/ .claude-plugin/plugin.json
git commit -m "feat(skills): add <skill-name> skill retrospective"
# NOTE: markdownlint may rewrite .md files — expect 2 commit attempts (see Failed Attempts)
git add <linter-modified-files>
git commit -m "fix(lint): apply markdownlint fixes"

# Push explicitly (branch tracking may not be set up in auto-generated worktrees)
git push origin HEAD:<branch-name>

# Create PR with auto-merge
gh pr create --title "feat(skills): add <skill-name> skill" \
  --body "Closes #<issue-number>" \
  --head <branch-name>
gh pr merge --auto --rebase <pr-number>

# Remove worktree after PR creation
git worktree remove .worktrees/<worktree-name>
```

### Batch EOF Fixing

For multiple branches failing pre-commit `end-of-file-fixer` on the same file (e.g., `.claude-plugin/plugin.json`):

**For each branch with EOF violation:**

```bash
# Create temporary worktree
git worktree add /tmp/fix-<PR-NUMBER> <branch-name>

# Verify the violation
python3 -c "
filepath = '/tmp/fix-<PR-NUMBER>/.claude-plugin/plugin.json'
data = open(filepath, 'rb').read()
last_byte = data[-1:]
print(f'Last byte: {last_byte.hex()}', 'OK' if last_byte == b'\x0a' else 'MISSING NEWLINE')
"

# Add trailing newline using Python (NOT bash echo — unreliable with code blocks)
python3 -c "open('/tmp/fix-<PR-NUMBER>/.claude-plugin/plugin.json','ab').write(b'\n')"

# Commit with pre-commit hooks (no --no-verify)
cd /tmp/fix-<PR-NUMBER>
git add .claude-plugin/plugin.json
git commit -m "fix: add trailing newline to plugin.json"
git push

# Cleanup
git worktree remove /tmp/fix-<PR-NUMBER>
```

### Worktree Status Check Loop

```bash
for dir in .worktrees/issue-*; do
  if [ -d "$dir" ]; then
    count=$(git -C "$dir" status --short | wc -l)
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD)
    echo "$dir ($branch): $count changes"
  fi
done
```

### Programmatic Path Detection from Porcelain Output

`git worktree list --porcelain` outputs multi-line blocks:
```text
worktree /home/user/repo/.worktrees/issue-3198
HEAD 38f3c196...
branch refs/heads/3198-auto-impl
```

**Wrong** — extracts the ref, not the path:
```bash
WORKTREE_PATH=$(git worktree list --porcelain | grep "branch.*/$BRANCH$" | awk '{print $2}')
# Returns: refs/heads/3198-auto-impl  ← WRONG
```

**Correct** — tracks preceding worktree line:
```bash
WORKTREE_PATH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v branch="$BRANCH" '/^worktree /{path=$2} /^branch / && $2 ~ "/" branch "$" {print path}')
# Returns: /home/user/repo/.worktrees/issue-3198  ← CORRECT
```

Extracting branch name from worktree path:
```bash
WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
```

### Automated Stale Worktree Cleanup Pattern

Safe cleanup loop (checks dirty state and open PRs before removing):

```bash
while IFS= read -r WT_PATH; do
    [ -z "$WT_PATH" ] && continue
    [ "$WT_PATH" = "$MAIN_REPO_ROOT" ] && continue

    WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
      awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
    [ -z "$WT_BRANCH" ] && continue

    # Skip if dirty
    [ -n "$(git -C "$WT_PATH" status --porcelain 2>/dev/null)" ] && continue

    # Skip if has open PR
    OPEN_PRS=$(gh pr list --head "$WT_BRANCH" --state open --json number 2>/dev/null)
    [ -n "$OPEN_PRS" ] && [ "$OPEN_PRS" != "[]" ] && continue

    # Safe to remove worktree
    git worktree remove "$WT_PATH" 2>/dev/null
    # Do NOT delete branch — collect for user review
    SAFE_TO_DELETE_BRANCHES+=("$WT_BRANCH")
done < <(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')

git worktree prune 2>/dev/null

# Present branch list to user for their deletion decision:
echo "Worktrees removed. The following branches may be safe to delete:"
printf '  - %s\n' "${SAFE_TO_DELETE_BRANCHES[@]}"
echo "Review each, then: git branch -d <branch>  (or -D for rebase-merged PRs)"
```

### Fixing Stale origin/HEAD and Missing origin/main

**Symptoms**: `git worktree add -b <name> <path> origin/main` fails with exit 128; `WorktreeManager` logs "Could not auto-detect base branch"; repos renamed from `master` to `main` on GitHub but local clone only tracks `origin/master`.

```bash
# Fix single repo
git -C "$HOME/<repo>" fetch origin
git -C "$HOME/<repo>" remote set-head origin --auto
git -C "$HOME/<repo>" symbolic-ref refs/remotes/origin/HEAD --short  # verify: "origin/main"
git -C "$HOME/<repo>" checkout main

# Bulk fix for multiple repos
for repo in Repo1 Repo2 Repo3; do
    git -C "$HOME/$repo" fetch origin
    git -C "$HOME/$repo" remote set-head origin --auto
    git -C "$HOME/$repo" checkout main
    git -C "$HOME/$repo" branch -d master 2>/dev/null || true
done
```

**Diagnostic commands:**
```bash
# Check if origin/HEAD is set
git symbolic-ref refs/remotes/origin/HEAD --short 2>&1
# Success: "origin/main"
# Failure: "fatal: ref refs/remotes/origin/HEAD is not a symbolic ref"

# Check what remote branches exist locally
git branch -r

# Check GitHub's actual default branch
gh api repos/<OWNER>/<REPO> --jq '.default_branch'
```

**WorktreeManager hardening** — replace hardcoded `"origin/main"` fallback with branch probing:
```python
if base_branch is None:
    try:
        result = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"], ...)
        base_branch = result.stdout.strip()
    except Exception:
        for candidate in ("origin/main", "origin/master"):
            try:
                run(["git", "rev-parse", "--verify", candidate], ...)
                base_branch = candidate
                break
            except Exception:
                continue
        if base_branch is None:
            base_branch = "origin/main"
```

### Fixing Branch Name Collisions in Parallel E2E Runs

**Symptom**: `fatal: A branch named 'T0_00_run_01' already exists` — branch names are not experiment-scoped; parallel runs collide.

**Fix**: Prefix branch names with experiment ID:

```python
# workspace_setup.py
def _setup_workspace(..., experiment_id: str = "") -> None:
    exp_prefix = experiment_id[:8] if experiment_id else ""
    if exp_prefix:
        branch_name = f"{exp_prefix}_{tier_id.value}_{subtest_id}_run_{run_number:02d}"
    else:
        branch_name = f"{tier_id.value}_{subtest_id}_run_{run_number:02d}"

# subtest_executor.py — pass experiment_id at call site
_setup_workspace(..., experiment_id=self.config.experiment_id)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit files via absolute path in main repo | Used Read/Edit on main repo path from session rooted in worktree | Changes landed on main branch, not feature branch | Always verify CWD branch with `git -C <dir> branch --show-current` before editing |
| Push feature branch after editing wrong location | Ran `git push` without copying changes to correct worktree | Push rejected: remote had commits the local branch lacked | Check `git diff --stat` in worktree before pushing |
| Force-push to fix diverged branch | Considered `git push --force` | Would overwrite legitimate remote commits | Fetch remote, inspect, then `reset --hard` + `pull --rebase` |
| `git branch -d` on rebase-merged branches | Used safe delete flag | "not fully merged" error — rebase leaves no merge commit | Always use `git branch -D` when remote branch is confirmed deleted |
| `git worktree remove` without cleaning untracked dirs | Tried removing worktrees containing `ProjectMnemosyne/` | "contains modified or untracked files" error | Pre-clean `rm -rf $wt/ProjectMnemosyne` before `git worktree remove` |
| grep + awk on branch line of porcelain output | `grep "branch.*/$BRANCH$" \| awk '{print $2}'` | Extracts the git ref, not the filesystem path | Path is on the preceding `worktree` line; use awk to track it |
| `git branch -D` in stale cleanup automation | Force-delete in cleanup script | Too aggressive — deletes unmerged branches silently | Use `git branch -d` (safe delete) in automation to preserve unmerged branches |
| Repeated `git -C <worktree>` for add/commit/push | Drove day-to-day git operations from a parent harness instead of the worktree itself | Permission-gated harnesses kept asking for approvals and Git wrote locks through shared worktree metadata | Once the worktree exists, use that directory as `cwd`/`workdir` and run plain `git ...` commands there |
| merge-base without `-C` repo context | `git merge-base --is-ancestor main "$BRANCH"` without `-C` | Runs in wrong repo context when CWD is a worktree | Always use `git -C "$WORK_DIR"` for explicit context |
| `git -C path` piped to `head` | Used `head` to limit output of `git -C` subcommand | `head` doesn't accept `-C` as git does | Don't pipe `git -C` subcommands to `head`; use separate commands |
| Direct worktree creation without fetching | `git worktree add -b name path origin/main` on stale clone | `origin/main` did not exist locally (only `origin/master`) | Always fetch origin before referencing remote refs in worktree commands |
| Auto-detect via symbolic-ref on fresh clone | `git symbolic-ref refs/remotes/origin/HEAD --short` | `origin/HEAD` is never set automatically on clone | Requires explicit `git remote set-head origin --auto` |
| Remove parent nested worktree before children | Removed depth-1 worktree that contained depth-2 entries | Left orphaned entries in git tracking | Remove deepest-nested first (depth 3 → 2 → 1) |
| Autonomous branch deletion during cleanup | Agent ran `git branch -D` for all `[gone]` branches without asking | Destructive — `-D` is irreversible without reflog; user may not have intended those branches to be gone | Always present the list and defer deletion to the user |
| Reporting completion with worktrees still present | Agent declared task done without removing agent worktrees | Orphaned worktrees accumulate; subsequent runs detect stale entries | Always verify `git worktree list` shows only main before reporting done |
| Stale `/tmp/mnemosyne-skill-*` path | Parallel `/learn` sub-agents used predictable `/tmp` paths from prior session | `git worktree add` refused: directory already exists; Safety Net blocked `rm -rf` inside sub-agent | Orchestrator must clean stale paths before spawning sub-agents; use timestamp suffix for guaranteed uniqueness |
| `git push origin --delete <branch>` | Used standard push to delete remote branch | Triggers local pre-push hook which runs the full test suite | Use `gh api --method DELETE "repos/$REPO/git/refs/heads/<branch>"` instead |
| `find + rm -rf __pycache__` | Deleted pycache dirs directly | Tracked `.pyc` files showed as "D" (deleted) in git status | Deleting tracked files from disk makes git report them as deleted — use `git checkout -- .` to restore |
| Single-pass `git clean -fd` | Ran clean on all artifacts in one pass | Only removes untracked files; tracked `.pyc` still show as deleted after rm | Use two passes: `git checkout -- .` first (restore tracked), then `git clean -fd` (remove untracked) |
| `git checkout -- '**/__pycache__/'` with glob | Tried glob pattern to restore tracked files | Glob patterns in git checkout don't reliably match nested paths | Use `git checkout -- .` to restore all tracked files |
| `git reset --hard origin/<branch>` | Tried to sync diverged local branch | Safety Net blocks `reset --hard` | Use `git pull --rebase origin/<branch>` instead |
| Over-broad Wave 1 removal (myrmidon) | Removed all `worktree-agent-*` branches in Wave 1 before checking for unreleased work | Discarded branches that could have been rebased and PRed | Categorize first (A/B/C triage), then remove only Category A in Wave 1; Wave 2 handles rebase+PR |
| Rebase of stale-PR branches without conflict pre-check | Attempted `git rebase origin/main` on branches with closed PRs | All had conflicts — indicates superseded work | Run conflict pre-check (`git rebase --no-commit` or `git cherry`) before attempting any rebase; conflicts on closed-PR branches = superseded, keep closed |
| `git worktree remove` without cleaning `.claude-prompt-*.md` | Tried to remove worktrees with lingering Claude session files | Safety Net blocked removal due to untracked files | Always `rm -f <wt>/.claude-prompt-*.md` before `git worktree remove` in agent-generated worktrees |
| Haiku for Category B rebase+PR | Attempted to use Haiku agents for the rebase+PR wave | Haiku wrote generic/inaccurate PR descriptions without analyzing the actual diff | Sonnet required for Category B: needs to read the diff and write meaningful PR title/body |
| Sequential Wave 2 | Ran rebase+PR and conflict-check sequentially | Doubled the time for Wave 2 when both subtasks are fully independent | Run Wave 2a (Sonnet rebase+PR) and Wave 2b (Haiku conflict-check) in parallel |
| `git worktree remove --force` without analysis | Force-removed worktree that had uncommitted skill documentation | Silently lost SKILL.md files that were part of completed work | Always run `git status --short` first; if untracked files exist, commit before removal |
| Bash `echo` for newline addition | `echo "" >> .claude-plugin/plugin.json` | Works for plain text but fails with files containing backtick code blocks or nested structures | Use Python `open(..., 'ab').write(b'\n')` — atomic, position-accurate, no shell interpretation |
| Bare `git push` in worktree | `git push` in auto-generated worktree | "upstream branch does not match local branch name" error | Always push explicitly: `git push origin HEAD:<branch-name>` |
| Markdown linting loop (single commit attempt) | `git add skills/ plugin.json && git commit -m "..."` | Pre-commit markdownlint rewrites .md files; first commit fails | Expect 2 commit attempts: add linter-modified files and commit again (will pass on second attempt) |
| Shellcheck `A && B \|\| C` pattern | `git branch -d "$branch" 2>/dev/null && log_info "Deleted" \|\| true` | Shellcheck SC2015: `\|\|` doesn't guarantee proper if-then-else; if log_info fails, `\|\| true` hides it | Use explicit if-then: `if git branch -d "$branch" 2>/dev/null; then log_info "..."; fi` |
| Bulk-delete remote branches in one push | `git push origin --delete branch1 branch2 branch3` | GitHub branch protection rules block deleting more than 2 branches in a single push | Delete remote branches one at a time |

## Results & Parameters

### Worktree nesting patterns from agent waves

| Pattern | Path depth | Occurs when |
|---------|-----------|-------------|
| Simple wave | `.claude/worktrees/agent-XXXXXXXX` | Agent spawned from main session |
| Nested depth-2 | `.claude/worktrees/agent-A/.claude/worktrees/agent-B` | Wave-2 agent spawned another agent |
| Nested depth-3 | `agent-A/.../agent-B/.../agent-C` | Wave-2 agent's agent spawned yet another agent |

### Safety Net interaction

| Operation | Blocked? | Workaround |
|-----------|----------|------------|
| `git worktree remove --force` (untracked files) | Yes | Delete untracked files first, then remove without `--force` |
| `git branch -D` | No | Allowed |
| `git reset --hard` | Yes | N/A — use `pull --rebase` instead |
| `rm -rf /tmp/mnemosyne-skill-*` inside sub-agent | Yes | Run from orchestrator (main conversation) before spawning sub-agents |

### Stale /tmp/mnemosyne-skill-* cleanup before parallel /learn sub-agents

When spawning multiple parallel sub-agents for `/hephaestus:learn`, each sub-agent creates a worktree at a predictable path like `/tmp/mnemosyne-skill-<name>`. If a prior session left stale directories (due to agent timeout, Safety Net blocking cleanup, or session interrupt), `git worktree add` fails with `fatal: '/tmp/mnemosyne-skill-<name>' already exists`.

**Orchestrator pre-cleanup (run in main conversation before spawning sub-agents):**
```bash
# Clean all stale mnemosyne skill worktrees before launching /learn sub-agents
rm -rf /tmp/mnemosyne-skill-* 2>/dev/null || true
git -C "$HOME/.agent-brain/ProjectMnemosyne" worktree prune
```

**Alternative — unique paths per invocation (eliminates collisions, harder to target for cleanup):**
```bash
WORKTREE_DIR="/tmp/mnemosyne-$(date +%s)-e2e-homeric"
```

**Sub-agent preferred cleanup order:**
1. `git -C "$MNEMOSYNE_DIR" worktree remove "$WORKTREE_DIR"` (preferred — updates git registry)
2. Fall back to `rm -rf "$WORKTREE_DIR"` only if `worktree remove` fails

### Scale reference for mass cleanup

| Worktrees | Time | Notes |
|-----------|------|-------|
| 33 worktrees | ~3 min | All removed successfully |
| 20 stale (merged) | ~1 min | No --force needed after cleaning untracked dirs |
| 13 active | ~1 min | 2 needed --force for modified tracked files |

### Scale reference for myrmidon wave pattern

| Worktree Count | Approach | Expected Duration |
|----------------|----------|-------------------|
| < 10 | Sequential, skip myrmidon | 10-20 min |
| 10-20 | Myrmidon waves, 3-5 agents/wave | 15-25 min |
| 20-35 | Myrmidon waves, 5-10 agents/wave | 20-45 min |
| 35+ | Myrmidon waves, sub-batch per agent | 45-90 min |

### Key numbers from reference sessions

- 55 worktrees removed (29 agent + 26 closed-issue) in one session — ProjectOdyssey
- 29 local branches deleted with `-d` (all worked)
- 15 remote branches deleted via `gh api`
- 23 worktrees cleaned in ~2 minutes (two-pass method) — zero data loss
- 32 → 4 worktrees; 3 PRs created from previously-unsubmitted work — ProjectHephaestus (45 min)
- 32 → 1 worktrees (main only) in ~20 minutes using 3-wave myrmidon

### Myrmidon Wave Session Results (2026-04-05, ProjectHephaestus)

| Wave | Executor | Category | Count | Action | Outcome |
|------|----------|----------|-------|--------|---------|
| 1 | Haiku (parallel) | A — stale/merged | 13 | Direct removal | All removed cleanly |
| 2a | Sonnet (parallel) | B — unreleased | 10 (`worktree-agent-*`) | Rebase + PR | 3 PRs (#262–#264) created; 7 superseded by main |
| 2b | Haiku (parallel with 2a) | C — stale-PR | 3 (closed PRs #29, #31, #32) | Conflict-check | All had conflicts; work superseded; kept closed |
| 3 | Haiku | — | — | prune + fetch --prune | Orphaned metadata eliminated |

### Model tier assignment

| Task | Tier | Reason |
|------|------|--------|
| Remove stale worktrees + artifact cleanup | Haiku | Mechanical, no analysis needed |
| Conflict pre-check (closed-PR branches) | Haiku | Binary output: conflicts or no conflicts |
| Final prune + verification | Haiku | Mechanical, single command sequence |
| Rebase + analyze unique work + create PR | Sonnet | Requires diff analysis, meaningful PR description |

### Artifact patterns to clean

```bash
ARTIFACT_PATTERNS="__pycache__ .pyc build/ dist/ *.egg-info .claude-prompt-*.md ProjectMnemosyne/ .issue_implementer"
```

### Harness-aware git operation split

| Task type | Preferred context | Why |
|-----------|-------------------|-----|
| Worktree creation, listing, prune, fleet-wide audit | Parent repo | These are genuinely repo-wide orchestration steps |
| `status`, `add`, `commit`, `push`, `rebase`, conflict resolution for one issue branch | Inside that worktree | Avoids repeated permission prompts and shared metadata lock failures in sandboxed harnesses |
| Cross-worktree inspection from one control shell | Parent repo with targeted `git -C <path>` | Fine for read-mostly audits; don't use it as the default write loop |

### Identifying [gone] branches

```bash
# List all branches with gone remotes — present to user, do NOT delete autonomously
git branch -v | grep '\[gone\]'
```

**Do NOT run bulk delete automatically.** Present the list to the user. If user confirms, they can run:
```bash
git branch -v | grep '\[gone\]' | awk '{print $1}' | xargs git branch -D
```

### Key porcelain verification

```bash
# Verify worktree path extraction
git worktree list --porcelain | awk '/^worktree /{path=$2} /^branch / {print path, $2}'
```

### Branch delete flag reference

| Flag | Use when |
|------|----------|
| `-d` (safe) | Remote branch still exists OR automation scripts (safety net) |
| `-D` (force) | Remote branch confirmed deleted (PR merged, `[gone]` in `git branch -v`) |

### Repo rename affected repos (as of 2026-03-24)

| Repo | Had origin/main locally? | Had origin/HEAD? |
|------|--------------------------|-------------------|
| Odysseus | No (only master) | No |
| ProjectHermes | No (only master) | No |
| ProjectKeystone | No (only master) | No |
| AchaeanFleet | Yes | No |
| ProjectHephaestus | Yes | Yes |
| ProjectMnemosyne | Yes | Yes |
| ProjectOdyssey | Yes | Yes |
| ProjectScylla | Yes | Yes |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Parallel wave execution cleanup — 55 worktrees, 29 branches | worktree-branch-cleanup session 2026-03-02 |
| ProjectOdyssey | 23 worktrees bulk artifact cleanup | worktree-bulk-artifact-cleanup session 2026-03-10 |
| ProjectScylla | 20 worktrees, EOF fixes (PRs #783, #764, #826), 4 skill registration PRs | skill-batch-eof-worktree-cleanup session 2026-02-20 |
| ProjectHephaestus | Myrmidon wave parallelization — 32 → 4 worktrees; 3 PRs from unreleased work | myrmidon-wave session 2026-04-05 |
| ProjectHephaestus | 31 agent+issue worktrees, 3-wave myrmidon swarm | myrmidon-waves-worktree-cleanup session 2026-04-05, 32→1 worktrees |
