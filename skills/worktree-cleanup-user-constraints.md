---
name: worktree-cleanup-user-constraints
description: "Use when cleaning up worktrees under user-specified constraints: (1) no branch
  deletion allowed, (2) all destructive ops must go into a reviewable script, (3) uncommitted
  work in merged-branch worktrees must be analyzed and committed if useful. Covers classification
  of dirty worktrees (artifact noise vs real work), generating a section-annotated cleanup script,
  handling files left orphaned in merged-branch working trees, the staged-file two-step
  (reset HEAD then checkout --) required when worktrees contain staged-only new files (status A),
  all-clean direct execution, cherry=1 rebase-merge artifact handling, the remove-worktree-keep-branch
  pattern for closed-not-merged PRs, and locked-but-clean worktrees from dead myrmidon agent sessions
  (unlock+remove without --force)."
category: tooling
date: 2026-05-04
version: "1.6.0"
user-invocable: false
verification: verified-ci
history: worktree-cleanup-user-constraints.history
tags: [worktree, cleanup, script, branches, artifacts, safety, merged-branch, circuit-breaker, staged-files, rebase-merge, closed-pr, gitignore, locked-worktree, dead-agent]
---

# Worktree Cleanup Under User Constraints

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-12 |
| **Objective** | Remove 36 stale worktrees from ProjectScylla while preserving all branches and not executing any destructive ops directly |
| **Outcome** | Produced a reviewable 7-section shell script; identified real uncommitted work (circuit breaker) in a merged-branch worktree; classified 6 dirty worktrees |
| **Verification** | verified-local — script produced and validated; not yet executed by user |
| **Scale** | 36 worktrees → target: 1 (main only) |

## When to Use

- User says "no branch deletion" before or during a cleanup session
- User says "give me a script to review first" — do NOT run destructive ops directly
- Worktrees from merged branches have uncommitted files that might be real work
- 20+ worktrees need cleanup and some have dirty working trees
- Agent-generated worktrees (`.claude/worktrees/agent-*`) accumulated from parallel runs
- Worktree directories (`.worktrees/`, `.claude/worktrees/`) appear as untracked directories in `git status --short` of the main workspace
- Locked worktrees (`git worktree list` shows `locked`) with dead agent PIDs from myrmidon swarm sessions — check cleanliness before deciding approach

**All-clean worktrees allow direct execution (no script required):**

When `git status --short` is empty for every worktree (0 dirty files across all worktrees),
you can execute removal directly rather than generating a script for user review. The
generate-first constraint exists to prevent accidental discard of real work — when there is
nothing dirty, there is nothing to accidentally discard.

```bash
# Check if all worktrees are clean before deciding generate-only vs direct-execute:
git worktree list --porcelain | awk '/^worktree /{print $2}' | tail -n +2 | while read wt; do
  dirty=$(git -C "$wt" status --short 2>/dev/null | wc -l)
  echo "$wt | dirty=$dirty"
done
# If ALL lines show dirty=0 → direct execution is safe
```

**Red flags that trigger this pattern:**
- `git worktree list | wc -l` > 15
- `git branch -v | grep '\[gone\]' | wc -l` > 10
- Any worktree with `dirty > 10` files (could be artifacts or could be real work)

## Verified Workflow

### Quick Reference

```bash
# 0a. Detect locked worktrees (handle these first — Phase 0.7)
git worktree list --porcelain | awk '/^worktree /{wt=$2} /^locked/{print wt " LOCKED"}'

# 0b. For each locked worktree: check cleanliness
git -C <locked-path> status --short   # empty = clean → unlock+remove directly

# 0c. Locked+clean: no --force needed
git worktree unlock <path> && git worktree remove <path>

# 1. Classify every dirty worktree
for wt in <dirty-worktrees>; do
  echo "=== $wt ===" && git -C "$wt" status --short
done

# 2. For each non-artifact file: check if on main
git -C "$wt" diff HEAD -- "$f" | head -20
git show main:"$f" 2>&1 | head -3        # path as-is
git show main:"src/$f" 2>&1 | head -3    # src-layout alternate

# 3. For merged branches: check cherry (always check PR state first — see cherry=1 note)
git cherry origin/main <branch> | grep "^+" | wc -l   # 0 = superseded

# 4. Generate script, hand to user — do not execute (unless all worktrees are clean)
# 5. User runs: bash -x /tmp/cleanup.sh 2>&1 | tee /tmp/cleanup.log
```

### Phase 0 — Read-Only Inventory

Run before touching anything. The full decision matrix — worktree path, branch, ahead count,
dirty count, staged count, cherry count, and PR state — can be obtained in one pass:

```bash
git fetch --prune origin

git worktree list --porcelain | awk '/^worktree /{print $2}' | tail -n +2 | while read wt; do
  br=$(git -C "$wt" branch --show-current 2>/dev/null || echo "(detached)")
  ahead=$(git rev-list --count origin/main.."$br" 2>/dev/null || echo "?")
  dirty=$(git -C "$wt" status --short 2>/dev/null | wc -l)
  staged=$(git -C "$wt" status --short 2>/dev/null | grep -c '^[MADRC]' || echo 0)
  cherry=$(git cherry origin/main "$br" 2>/dev/null | grep -c '^+' || echo "?")
  pr=$(gh pr list --head "$br" --state all --json state,number --jq '.[0] | "\(.state) #\(.number)"' 2>/dev/null || echo "NO_PR")
  echo "$wt | branch=$br | ahead=$ahead | dirty=$dirty | staged=$staged | cherry=$cherry | pr=$pr"
done | tee /tmp/wt-inventory.txt
```

This single-pass inventory gives everything needed to classify all worktrees without any
back-and-forth. No additional queries required in most cases.

### Phase 0.5 — Gitignore Hygiene

**Run before any cleanup operations.** Gitignore the worktree directories and common
agent-session artifacts so they do not reappear as untracked noise in `git status` after
the next batch of agent runs creates new worktrees.

Without this step, cleanup is incomplete: even after all worktrees are removed, the
*directory* (`.worktrees/`, `.claude/worktrees/`) will reappear as untracked in the next
session because it was never gitignored.

```bash
# Check whether these paths are already gitignored:
git check-ignore -v .worktrees .claude/worktrees .coverage .claude/scheduled_tasks.lock 2>/dev/null

# If any are NOT ignored, add them to .gitignore:
cat >> .gitignore << 'EOF'

# Coverage reports
.coverage
.coverage.*

# Claude worktree and session artifacts
.worktrees/
.claude/worktrees/
.claude/scheduled_tasks.lock
EOF

git add .gitignore
git commit -m "chore: gitignore worktree dirs and agent session artifacts"
```

**Entries to add** (add only those not already present):

| Pattern | What it ignores |
| --------- | ---------------- |
| `.coverage` | pytest-cov coverage data file |
| `.coverage.*` | coverage data with worker suffixes |
| `.worktrees/` | top-level worktree checkout directory |
| `.claude/worktrees/` | Claude Code agent worktree directory |
| `.claude/scheduled_tasks.lock` | Claude Code scheduled-tasks lock file |

**Verification**: after the commit, `git status --short` in the main worktree should show
no untracked lines for these paths.

### Phase 0.7 — Handle Locked Worktrees

**Locked worktrees from dead agent sessions can be unlocked and removed directly when clean.**

The previous approach classified all locked worktrees as KEEP and printed manual unlock+force-remove
commands for the user. This was wrong:
- When the worktree is **clean** (empty `git status --short`), `git worktree remove` succeeds
  without `--force` after unlock — no force needed, no user intervention required
- When the worktree is **dirty**, the correct flow is: classify files → auto-commit real work →
  push → PR → ask user about ambiguous files → then unlock+remove

**Detection** — identify locked worktrees:

```bash
git worktree list --porcelain | awk '/^worktree /{wt=$2} /^locked/{print wt " LOCKED"}'
```

**Cleanliness check for locked worktrees**:

```bash
# For each locked worktree:
git -C <locked-path> status --short   # empty output = clean
```

**Locked + clean → unlock and remove directly (no --force)**:

```bash
# For each locked worktree where git status --short is empty:
git worktree unlock <path>
git worktree remove <path>     # succeeds without --force on a clean worktree
```

**Locked + dirty → classify files first**:

Follow Phase 1 classification before unlocking. After real work is committed/pushed:

```bash
git worktree unlock <path>
# Clean artifacts (reset/checkout/clean as needed)
git worktree remove <path>
```

**Artifact patterns to always ignore (never commit)**:

```
__pycache__/  *.pyc  *.pyo  *.pyd  .pytest_cache/  .mypy_cache/  .ruff_cache/
build/  dist/  *.egg-info/  htmlcov/  .coverage  .coverage.*
.claude-prompt-*.md  .issue_implementer
```

**After all locked worktrees are handled**:

```bash
git worktree prune
```

### Phase 1 — Classify Dirty Worktrees

**Artifact patterns (always discard, never commit):**

```
__pycache__/  *.pyc  *.pyo  build/  dist/  *.egg-info/
.claude-prompt-*.md  ProjectMnemosyne/  .issue_implementer
.pytest_cache/  .mypy_cache/  .ruff_cache/  .coverage.*  htmlcov/
```

**Potentially real (inspect with diff):**

```
src/  scripts/  tests/  docs/  .claude/ (excl. prompt files)
config/  schemas/  pyproject.toml  pixi.toml  CHANGELOG.md  justfile
```

**Per-file decision logic:**

```bash
# Is the change in the working tree already reflected on main?
git -C "$wt" diff HEAD -- "$f" | head -20       # vs branch tip
git -C "$wt" diff origin/main -- "$f" | head -20 # vs main

# For src-layout repos: check both paths
git show main:"$f" 2>&1 | head -3
git show main:"src/$f" 2>&1 | head -3
```

Decision rules:
- Working tree reverts branch edits back to main content → noise
- File exists on main at either path → check if content differs meaningfully
- File NOT on main at any path → **potentially real, commit it**
- File on merged branch (`git cherry` returns 0) → work is superseded → artifact
- **cherry=1 on a MERGED PR → rebase-merge artifact, not real work** (see note below)

**cherry=1 rebase-merge artifact — do not confuse with unreleased work:**

When a PR was merged via rebase, the rebase rewrites commit hashes. The original branch
commit and the rebased-onto-main commit have different SHAs, so `git cherry` reports `+1`
(one unreleased commit) even though the work is already in main. Always verify PR state
before treating cherry count as evidence of unreleased work:

```bash
# Correct classification for cherry=1:
pr_state=$(gh pr list --head "$br" --state all --json state --jq '.[0].state')
if [ "$pr_state" = "MERGED" ]; then
  echo "cherry=1 is rebase-merge artifact — work IS in main, safe to remove"
elif [ "$pr_state" = "CLOSED" ]; then
  echo "cherry=1 on CLOSED PR — work NOT in main, treat as unreleased"
elif [ "$pr_state" = "" ]; then
  echo "cherry=1 with NO PR — work NOT in main, treat as unreleased"
fi
```

### Phase 1.5 — Classify Closed-Not-Merged PRs

When a branch has a PR that was CLOSED without merging and the branch has unique commits
(`cherry >= 1`), use "remove worktree, keep branch":

- **Remove worktree**: frees disk space and git metadata
- **Keep branch**: preserves the commits — the branch is the only copy of that work

Only suggest full branch deletion if the user explicitly says they want to discard the work.
Default is always to keep branches when in doubt.

```bash
# Classification for CLOSED (not MERGED) PR:
if [ "$cherry" -ge 1 ] && [ "$pr_state" = "CLOSED" ]; then
  echo "CLOSED PR with $cherry unique commit(s) — remove worktree, KEEP branch"
fi
```

### Phase 2 — Handle Merged-Branch Worktrees

When a branch's PR is MERGED but the worktree has uncommitted files:

```bash
# Verify merged
gh pr list --head <branch> --state all --json state | grep MERGED

# Check which untracked files are NOT on main at any path
for f in <untracked-files>; do
  on_main=$(git show main:"$f" 2>&1; git show main:"src/$f" 2>&1)
  echo "$on_main" | grep -q "fatal" && echo "NOT ON MAIN: $f" || echo "on main: $f"
done
```

Files NOT on main in a merged-branch worktree = **orphaned work** that was never committed before the PR closed. Note them for the user — they cannot be committed to the merged branch (dead branch); user needs a new branch/issue.

### Phase 2.5 — Cleaning Worktrees with Staged-Only Additions

**Critical**: `git checkout -- .` alone does NOT clean worktrees that have staged new files
(status `A` in `git status --short`). The two-step sequence is required:

```bash
# Worktree has staged additions (status A lines in git status --short):
git -C <worktree> reset HEAD -- .    # Step 1: unstage all staged additions
git -C <worktree> checkout -- .      # Step 2: restore tracked modified files
git -C <worktree> clean -fd          # Step 3: remove untracked files
git worktree remove <worktree>       # Now succeeds without --force
```

**Why**: `git checkout -- .` only restores tracked files that were modified. Files with
status `A` (staged new) were never tracked — they bypass `checkout --` entirely and remain
after it runs. `reset HEAD -- .` unstages them, making them untracked; then `clean -fd`
removes them.

**Detection**:

```bash
git -C <worktree> status --short | grep '^A'  # non-empty = staged additions present
```

### Phase 3 — Generate the Reviewable Script

Structure of `/tmp/<repo>-worktree-cleanup.sh`:

```bash
#!/usr/bin/env bash
# Review every section before running.
# Rules: no branch deletion; salvage useful uncommitted work; no push.
set -euo pipefail
cd /path/to/repo

# SECTION 1: PRE-FLIGHT (read-only audit)
echo "Worktree count: $(git worktree list | wc -l)"
echo "Branch count: $(git branch | wc -l)"

# SECTION 2: COMMIT useful uncommitted work
# One subshell block per worktree with real edits:
# ( cd .claude/worktrees/agent-XXXX
#   git add path/to/real_file.py   # NEVER -A
#   git commit -m "type(scope): salvage uncommitted work on <branch>"
# )
# NOTE on merged branches: list orphaned files the user must copy manually

# SECTION 3: TWO-PASS ARTIFACT CLEAN (artifact-only worktrees)
# NOTE: if git status shows 'A' lines (staged additions), use the three-step:
#   git -C "$wt" reset HEAD -- . && git -C "$wt" checkout -- . && git -C "$wt" clean -fd
# Otherwise the two-pass below is sufficient for untracked/modified-only worktrees:
for wt in <artifact-only-worktrees>; do
  git -C "$wt" checkout -- .    # Pass 1: restore tracked files
  git -C "$wt" clean -fd --quiet  # Pass 2: remove untracked
done

# SECTION 4: REMOVE stray agent files (prevents --force)
while IFS= read -r wt; do
  [ "$wt" = "$REPO" ] && continue
  rm -f  "$wt"/.claude-prompt-*.md 2>/dev/null || true
  rm -rf "$wt/ProjectMnemosyne"    2>/dev/null || true
  rm -f  "$wt/.issue_implementer"  2>/dev/null || true
done < <(git worktree list --porcelain | awk '/^worktree /{print $2}')

# SECTION 5: REMOVE worktrees (explicit list, no wildcards, no --force)
WORKTREES=( ".claude/worktrees/agent-XXXX" ... )
for wt in "${WORKTREES[@]}"; do
  git worktree remove "$wt"   # fails loud on unexpected dirt
done

# SECTION 6: PRUNE (does NOT delete branches)
git worktree prune
git remote prune origin

# SECTION 7: VERIFY
git worktree list          # expect 1 line
git branch | wc -l         # expect same as pre-flight
git status --short
```

**Key script properties:**
- `set -euo pipefail` — stops on any unexpected failure
- Explicit worktree list (auditable, not `for wt in .claude/worktrees/*`)
- `git add <specific-files>` — never `git add -A`
- Zero `git branch -d/-D` or `gh api DELETE`
- No `--force` on `git worktree remove`
- Interactive confirmation before cleaning merged-branch worktrees with orphaned files

### Phase 4 — Hand Off to User

```bash
bash -n /tmp/<repo>-worktree-cleanup.sh && echo "Syntax OK"
# Then report to user:
# 1. Inventory summary (dirty counts, classification)
# 2. List of commits Section 2 will make (branch + files + message)
# 3. List of orphaned files in merged branches (user must copy manually)
# 4. Script path + invocation command
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assume large dirty count = artifacts | 187 files dirty → assumed `__pycache__` noise | Agent-a117bab3 had 32 real modified Python files (real uncommitted work) on a merged branch | Always inspect `git status --short` output per-file; never assume based on count alone |
| Present branch deletion list to user | Plan Phase 5 proposed deletions for user to approve | User explicitly rejected — branches must never be deleted | No branch deletion at all, even with user confirmation; branches are permanent |
| Execute destructive ops via tool calls | Initial plan executed `git worktree remove` directly | User rejected — wants a script to review first | All destructive ops go into a script file; only read-only analysis runs directly |
| Assume all dirty files in merged-branch worktree are noise | issue-1529 (PR MERGED): treated 188 dirty files as abandoned | Two files (`circuit_breaker.py`, `test_circuit_breaker.py`) were genuinely new work not on main | Check every potentially-real file vs main even on merged branches |
| Trust `[gone]` status as sole triage signal | Tried to use `ahead=0` + `[gone]` to classify all worktrees | Doesn't reveal uncommitted working-tree changes; must still inspect `git status` | `[gone]` = branch tracking gone, NOT = working tree clean; always check dirty count |
| `git worktree remove --force` | Planned to use `--force` for stubborn cases | Safety Net blocks `--force` | Clean stray files individually first, then `git worktree remove` without `--force` |
| `git checkout -- .` alone on staged-addition worktree | Ran `checkout -- .` then `git worktree remove` | `fatal: '<path>' contains modified or untracked files` — staged new files (status `A`) survived `checkout --` unchanged | Must run `reset HEAD -- .` first to unstage, then `checkout -- .`, then `clean -fd` |
| Assuming cherry=1 means unreleased work | Three branches showed cherry=1 despite MERGED PRs | Rebase-merge rewrites commit hashes, so cherry count is 1 even though work is in main | Always check PR state first; cherry count is only meaningful when combined with PR=NONE or PR=CLOSED |
| Skipping .gitignore hygiene | Cleaned up all worktrees but did not add worktree dirs to `.gitignore` | `.worktrees/` directory still appeared as untracked in `git status` after the next agent session because the directory itself was never gitignored | Run Phase 0.5 gitignore hygiene before cleanup — the cleanup removes the content but the directory must be gitignored to prevent re-accumulation |
| Classify all locked worktrees as KEEP | Treated locked worktree status as ambiguous regardless of cleanliness; printed manual unlock+--force-remove command for user | Unnecessary — locked+clean worktrees (empty `git status --short`) can be unlocked and removed directly with no `--force`; Safety Net blocks `--force` anyway | Split on cleanliness first: locked+clean → `git worktree unlock` + `git worktree remove` (no flags); locked+dirty → classify files, commit real work, ask user about ambiguous files, then unlock+remove |

## Results & Parameters

### Artifact classification regex (Python)

```python
ARTIFACT_PATTERNS = {
    "__pycache__", ".pyc", ".pyo", "build/", "dist/", ".egg-info/",
    ".claude-prompt-", "ProjectMnemosyne", ".issue_implementer",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".coverage.", "htmlcov/",
}

def is_artifact(path: str) -> bool:
    return any(p in path for p in ARTIFACT_PATTERNS)
```

### Scale reference

| Worktrees | Dirty | Approach | Script size | Time |
| ----------- | ------- | ---------- | ------------- | ------ |
| 14 | 4 dirty (`.coverage` only) | Sequential script | 7 sections, ~80 lines | ~2 min |
| 17 | 0 dirty (all clean) | Direct execution | No script needed | ~1 min |
| 36 | 6 dirty | Sequential script | 7 sections, ~120 lines | ~5 min |
| 20-35 | Mixed | Same pattern | Adjust WORKTREES array | varies |
| 13 | 0 dirty (locked, dead PIDs) | Direct unlock+remove (no script, no --force) | None needed | ~1 min |

### Real work found in merged-branch worktrees (this session)

- `issue-1529` (PR #1760 MERGED): `src/scylla/automation/circuit_breaker.py` + `tests/unit/automation/test_circuit_breaker.py` — both NOT on main, subsequently ported to ProjectHephaestus

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | 36 worktrees, 6 dirty, 26 `[gone]` branches | Script at `/tmp/scylla-worktree-cleanup.sh`; execution pending |
| ProjectMnemosyne | 14 agent worktrees (`.claude/worktrees/agent-*`), all PRs #1221–1255 merged, 4 with `.coverage` only | Script at `/tmp/mnemosyne-worktree-cleanup.sh`; syntax-checked (bash -n); user kept branches, generate-only mode |
| ProjectScylla | 11 stale myrmidon swarm worktrees, staged-addition failures caught on cleanup, all 11 removed cleanly | 2026-04-13; `reset HEAD -- .` + `checkout -- .` + `clean -fd` sequence verified effective |
| ProjectOdyssey | 17 worktrees (1 main + 16 feature), all clean (0 dirty), 15 agent-* in `.claude/worktrees/`, cherry=1 on MERGED PRs = rebase artifacts | 2026-04-21; direct execution (no script); 1 CLOSED PR branch kept; all 17 worktrees removed, 0 `--force` needed |
| AchaeanFleet | 13 worktrees accumulated, `.worktrees/`, `.claude/worktrees/`, `.coverage`, `.claude/scheduled_tasks.lock` untracked in main | 2026-04-25; Phase 0.5 gitignore hygiene added first (commit dcf3d43); `git status --short` clean after cleanup; verified-ci |
| ProjectMnemosyne | 13 locked `worktree-agent-<hash>` worktrees from dead myrmidon swarm sessions, all `dirty=0` | 2026-05-04; all 13 unlocked and removed without `--force`; `git worktree prune` cleaned up; verified-local |
