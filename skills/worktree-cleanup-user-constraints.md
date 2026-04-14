---
name: worktree-cleanup-user-constraints
description: "Use when cleaning up worktrees under user-specified constraints: (1) no branch
  deletion allowed, (2) all destructive ops must go into a reviewable script, (3) uncommitted
  work in merged-branch worktrees must be analyzed and committed if useful. Covers classification
  of dirty worktrees (artifact noise vs real work), generating a section-annotated cleanup script,
  and handling files left orphaned in merged-branch working trees."
category: tooling
date: 2026-04-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [worktree, cleanup, script, branches, artifacts, safety, merged-branch, circuit-breaker]
---

# Worktree Cleanup Under User Constraints

## Overview

| Field | Value |
|-------|-------|
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

**Red flags that trigger this pattern:**
- `git worktree list | wc -l` > 15
- `git branch -v | grep '\[gone\]' | wc -l` > 10
- Any worktree with `dirty > 10` files (could be artifacts or could be real work)

## Verified Workflow

### Quick Reference

```bash
# 1. Classify every dirty worktree
for wt in <dirty-worktrees>; do
  echo "=== $wt ===" && git -C "$wt" status --short
done

# 2. For each non-artifact file: check if on main
git -C "$wt" diff HEAD -- "$f" | head -20
git show main:"$f" 2>&1 | head -3        # path as-is
git show main:"src/$f" 2>&1 | head -3    # src-layout alternate

# 3. For merged branches: check cherry
git cherry origin/main <branch> | grep "^+" | wc -l   # 0 = superseded

# 4. Generate script, hand to user — do not execute
# 5. User runs: bash -x /tmp/cleanup.sh 2>&1 | tee /tmp/cleanup.log
```

### Phase 0 — Read-Only Inventory

Run before touching anything:

```bash
git fetch --prune origin

git worktree list --porcelain | awk '/^worktree /{print $2}' | tail -n +2 | while read wt; do
  br=$(git -C "$wt" branch --show-current 2>/dev/null || echo "(detached)")
  ahead=$(git rev-list --count origin/main.."$br" 2>/dev/null || echo "?")
  dirty=$(git -C "$wt" status --short 2>/dev/null | wc -l)
  echo "$wt | branch=$br | ahead=$ahead | dirty=$dirty"
done | tee /tmp/wt-inventory.txt
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
|---------|----------------|---------------|----------------|
| Assume large dirty count = artifacts | 187 files dirty → assumed `__pycache__` noise | Agent-a117bab3 had 32 real modified Python files (real uncommitted work) on a merged branch | Always inspect `git status --short` output per-file; never assume based on count alone |
| Present branch deletion list to user | Plan Phase 5 proposed deletions for user to approve | User explicitly rejected — branches must never be deleted | No branch deletion at all, even with user confirmation; branches are permanent |
| Execute destructive ops via tool calls | Initial plan executed `git worktree remove` directly | User rejected — wants a script to review first | All destructive ops go into a script file; only read-only analysis runs directly |
| Assume all dirty files in merged-branch worktree are noise | issue-1529 (PR MERGED): treated 188 dirty files as abandoned | Two files (`circuit_breaker.py`, `test_circuit_breaker.py`) were genuinely new work not on main | Check every potentially-real file vs main even on merged branches |
| Trust `[gone]` status as sole triage signal | Tried to use `ahead=0` + `[gone]` to classify all worktrees | Doesn't reveal uncommitted working-tree changes; must still inspect `git status` | `[gone]` = branch tracking gone, NOT = working tree clean; always check dirty count |
| `git worktree remove --force` | Planned to use `--force` for stubborn cases | Safety Net blocks `--force` | Clean stray files individually first, then `git worktree remove` without `--force` |

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

| Worktrees | Dirty | Approach | Script size |
|-----------|-------|----------|-------------|
| 36 | 6 dirty | Sequential script | 7 sections, ~120 lines |
| 20-35 | Mixed | Same pattern | Adjust WORKTREES array |

### Real work found in merged-branch worktrees (this session)

- `issue-1529` (PR #1760 MERGED): `src/scylla/automation/circuit_breaker.py` + `tests/unit/automation/test_circuit_breaker.py` — both NOT on main, subsequently ported to ProjectHephaestus

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | 36 worktrees, 6 dirty, 26 `[gone]` branches | Script at `/tmp/scylla-worktree-cleanup.sh`; execution pending |
