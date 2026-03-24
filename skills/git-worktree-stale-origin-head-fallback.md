---
name: git-worktree-stale-origin-head-fallback
description: "Fix git worktree creation failures caused by stale local clones missing origin/main and unset origin/HEAD symref. Use when: (1) git worktree add fails with exit 128 referencing origin/main, (2) WorktreeManager auto-detect falls back to hardcoded origin/main, (3) repos were renamed from master to main on GitHub but local clones are stale."
category: debugging
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: []
---

# Git Worktree Stale Origin HEAD Fallback

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Debug and fix `work_all_repos.sh` bulk issue worker failing across all repos with `git worktree add` exit 128 |
| **Outcome** | Successful — identified two compounding issues: stale local git state and missing `origin/HEAD` symref |

## When to Use

- `git worktree add -b <name> <path> origin/main` fails with exit status 128
- ProjectScylla `WorktreeManager` logs: "Could not auto-detect base branch, using origin/main"
- `git symbolic-ref refs/remotes/origin/HEAD --short` returns "not a symbolic ref"
- Repos were renamed from `master` to `main` on GitHub but local clones still only track `origin/master`
- Bulk automation (`work_all_repos.sh`) fails uniformly across multiple repos

## Verified Workflow

### Quick Reference

```bash
# Step 1: Fetch latest refs so origin/main exists locally
git -C "$HOME/<repo>" fetch origin

# Step 2: Set origin/HEAD symref so auto-detect works
git -C "$HOME/<repo>" remote set-head origin --auto

# Step 3: Verify
git -C "$HOME/<repo>" symbolic-ref refs/remotes/origin/HEAD --short
# Expected: origin/main

# Step 4: Switch local branch from stale master/ecosystem-audit-remediation to main
git -C "$HOME/<repo>" checkout main

# Bulk fix for all affected repos:
for repo in Odysseus ProjectHermes ProjectKeystone ProjectTelemachy AchaeanFleet Myrmidons; do
    echo "Fixing $repo..."
    git -C "$HOME/$repo" fetch origin
    git -C "$HOME/$repo" remote set-head origin --auto
    git -C "$HOME/$repo" checkout main
    git -C "$HOME/$repo" branch -d master 2>/dev/null || true
done
```

### Detailed Steps

1. **Diagnose**: Check `git branch -r` in the failing repo — if only `origin/master` appears and no `origin/main`, the local clone is stale
2. **Verify GitHub state**: Run `gh api repos/OWNER/REPO --jq '.default_branch'` — if it returns `main`, the rename already happened on GitHub
3. **Fetch**: Run `git fetch origin` to pull down the new `origin/main` ref
4. **Set HEAD**: Run `git remote set-head origin --auto` to create the `refs/remotes/origin/HEAD` symref pointing to `origin/main`
5. **Switch branch**: Run `git checkout main` to track the correct branch locally
6. **Clean up**: Optionally `git branch -d master` to remove stale local tracking branch
7. **Harden code**: In `WorktreeManager.worktree_manager.py`, replace the hardcoded `"origin/main"` fallback with a probe that checks which branch actually exists via `git rev-parse --verify`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct worktree creation | `git worktree add -b 29-auto-impl .worktrees/issue-29 origin/main` | `origin/main` did not exist locally — only `origin/master` was fetched | Always verify remote refs exist locally before referencing them in worktree commands |
| Auto-detect via symbolic-ref | `git symbolic-ref refs/remotes/origin/HEAD --short` | `origin/HEAD` was never set — returns "not a symbolic ref" | `origin/HEAD` is not automatically set on clone; requires `git remote set-head origin --auto` |
| Assuming fallback is correct | WorktreeManager hardcodes `"origin/main"` as fallback | Branch name was correct but ref didn't exist locally due to stale clone | Fallback should probe for branch existence with `git rev-parse --verify` rather than assuming |

## Results & Parameters

### Diagnostic commands

```bash
# Check if origin/HEAD is set
git symbolic-ref refs/remotes/origin/HEAD --short 2>&1
# Success: "origin/main"
# Failure: "fatal: ref refs/remotes/origin/HEAD is not a symbolic ref"

# Check what remote branches exist locally
git branch -r

# Check GitHub's actual default branch
gh api repos/HomericIntelligence/<repo> --jq '.default_branch'
```

### Affected repos (as of 2026-03-24)

| Repo | Had origin/main locally? | Had origin/HEAD? | GitHub default |
|------|--------------------------|-------------------|----------------|
| Odysseus | No (only master) | No | main |
| ProjectHermes | No (only master) | No | main |
| ProjectKeystone | No (only master) | No | main |
| ProjectTelemachy | No (only master) | No | main |
| AchaeanFleet | Yes | No | main |
| Myrmidons | Yes | No | main |
| ProjectHephaestus | Yes | Yes | main |
| ProjectMnemosyne | Yes | Yes | main |
| ProjectOdyssey | Yes | Yes | main |
| ProjectScylla | Yes | Yes | main |

### WorktreeManager hardening (ProjectScylla)

```python
# File: ~/ProjectScylla/scylla/automation/worktree_manager.py (lines 40-52)
# Replace hardcoded fallback with branch probing:
if base_branch is None:
    try:
        result = run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
            cwd=self.repo_root,
            capture_output=True,
        )
        base_branch = result.stdout.strip()
    except Exception:
        for candidate in ("origin/main", "origin/master"):
            try:
                run(
                    ["git", "rev-parse", "--verify", candidate],
                    cwd=self.repo_root,
                    capture_output=True,
                )
                base_branch = candidate
                break
            except Exception:
                continue
        if base_branch is None:
            base_branch = "origin/main"
    logger.debug(f"Using base branch: {base_branch}")
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence ecosystem | Debugging work_all_repos.sh bulk failure across 12 repos | All repos use GitHub default branch `main`; 6 had stale local state |
