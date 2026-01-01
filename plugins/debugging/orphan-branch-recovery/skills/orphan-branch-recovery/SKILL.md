---
name: orphan-branch-recovery
description: Diagnose and fix branches with no common ancestor that cannot be merged
---

# Orphan Branch Recovery

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Objective | Fix a branch that completely diverged from main with no common history |
| Outcome | Identified branch was pushed from wrong repo, extracted content, deleted and recreated |

## When to Use

- `git merge-base` returns nothing between branch and main
- Error: "fatal: refusing to merge unrelated histories"
- Branch appears to have completely different commit history
- Suspicion that branch was pushed from wrong repository
- PR shows massive unexpected file changes

## Verified Workflow

### Step 1: Diagnose the Problem

```bash
# Check if branches share common history
git fetch origin <branch-name>
git merge-base origin/main origin/<branch-name>

# If no output, branches have no common ancestor
```

### Step 2: Understand the Divergence

```bash
# Commits on branch not in main
git log --oneline origin/main..origin/<branch-name> | head -20

# Commits on main not in branch
git log --oneline origin/<branch-name>..origin/main | head -20

# Check oldest commits on branch (reveals origin)
git log --oneline origin/<branch-name> | tail -10
```

### Step 3: Inspect Branch Contents

```bash
# List top-level files (reveals if wrong repo)
git ls-tree --name-only origin/<branch-name> | head -20

# Show what the tip commit added
git show origin/<branch-name> --name-only --oneline
```

### Step 4: Extract Valuable Content

```bash
# Extract specific files from the branch
git show origin/<branch-name>:<path/to/file> > /tmp/extracted-file

# Example: Extract plugin files
git show origin/<branch>:plugins/category/name/.claude-plugin/plugin.json > /tmp/plugin.json
git show origin/<branch>:plugins/category/name/skills/name/SKILL.md > /tmp/SKILL.md
```

### Step 5: Delete and Recreate

```bash
# Delete the broken remote branch
git push origin --delete <branch-name>

# Create new branch from main
git checkout main
git pull origin main
git checkout -b <branch-name>

# Add extracted files and commit
mkdir -p <plugin-path>
cp /tmp/extracted-files <plugin-path>/
git add .
git commit -m "feat: add skill (recreated from broken branch)"
git push -u origin <branch-name>
```

## Failed Attempts

| Attempt | What Failed | Why |
|---------|-------------|-----|
| Merging directly | "refusing to merge unrelated histories" | No common ancestor exists |
| Rebasing onto main | Creates duplicate commits, history becomes confusing | Rebase replays commits but doesn't fix the root cause |
| Using `--allow-unrelated-histories` | Works but creates messy history with duplicate content | Only use as last resort |

## Results & Parameters

### Diagnostic Commands

```bash
# Quick check for orphan branch
git merge-base origin/main origin/<branch> || echo "ORPHAN: No common ancestor"

# Show file diff (will be massive if wrong repo)
git diff --stat origin/main...origin/<branch> | tail -5
```

### Signs of Wrong-Repo Push

1. `git log --oneline <branch> | tail -5` shows unfamiliar "Initial commit"
2. `git ls-tree --name-only <branch>` shows unexpected files (e.g., `.mojo-version` in a Python project)
3. Massive number of commits ahead/behind main
4. Commit messages reference different project

### Recovery Checklist

- [ ] Verify branch has no merge-base with main
- [ ] Identify valuable content on branch tip
- [ ] Extract files before deletion
- [ ] Delete remote branch
- [ ] Create new branch from main
- [ ] Add extracted content
- [ ] Push and create PR
