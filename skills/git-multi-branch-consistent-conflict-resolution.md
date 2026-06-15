---
name: git-multi-branch-consistent-conflict-resolution
description: "Resolve the same merge conflict across multiple branches using Python regex scripts. Use when: (1) rebasing N branches that all conflict on the same files/lines, (2) conflict markers follow a predictable pattern, (3) manual resolution per-branch is too slow."
category: tooling
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, rebase, conflict-resolution, multi-branch, automation]
---

# Multi-Branch Consistent Conflict Resolution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Rebase 9 PR branches onto origin/master where all branches share the same conflict pattern from a common ancestor commit |
| **Outcome** | Successfully rebased all 9 branches, validated, and pushed |
| **Verification** | verified-local |

## When to Use

- You have N branches forked from the same ancestor that all conflict on the same files/lines after the target branch advanced
- The conflict pattern is predictable (same conflict markers, same resolution strategy)
- Manual per-branch resolution would be tedious and error-prone
- The conflicts appear in files like AGENTS.md, justfile, or config files where one side is always the superset

## Verified Workflow

### Quick Reference

```bash
# Resolve same conflict across multiple branches using Python regex
for branch in branch-01 branch-02 branch-03; do
  git checkout "$branch"
  python3 << 'PYEOF'
import re
for fname in ["conflicting-file-1.md", "conflicting-file-2.py"]:
    with open(fname) as f:
        content = f.read()
    m = re.search(r"<<<<<<< HEAD.*?>>>>>>> [^(]+ \\(specific-pattern\\)", content, re.DOTALL)
    if m:
        old = m.group()
        new = old.split("=======")[0].replace("<<<<<<< HEAD\n", "").rstrip("\n")
        content = content.replace(old, new, 1)
        with open(fname, "w") as f:
            f.write(content)
        print(f"Fixed {fname}")
PYEOF
  git add conflicting-file-1.md conflicting-file-2.py
  GIT_EDITOR=true git rebase --continue
done
```

### Detailed Steps

1. **Identify the common conflict pattern**: Run `git rebase origin/master` on the first branch and note which files conflict and the conflict marker pattern
2. **Write a Python regex script** that:
   - Reads each conflicted file
   - Uses `re.search(r"<<<<<<< HEAD.*?>>>>>>> [^(]+ \\(PATTERN\\)", content, re.DOTALL)` to find the conflict
   - Keeps the desired side (usually HEAD/origin/master which is the superset)
   - Writes the resolved content back
3. **Loop through all branches**: For each branch, checkout, run the regex resolution script, stage, continue rebase
4. **Validate each branch**: Run `just validate` or equivalent after each rebase
5. **Push all branches**: `git push --force-with-lease origin "$branch"`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Manual resolution | Resolve conflicts manually per-branch | Too slow for 9 branches, inconsistent resolutions | Automate with regex when pattern is predictable |
| Shell heredoc with conflict markers | Use bash heredoc to write resolution script | Conflict markers `<<<<<<<` break shell quoting | Use Python script via heredoc delimiter to avoid shell escaping issues |
| Single sed command | Use sed to resolve conflicts | Sed regex is too greedy for multi-line conflict blocks | Python with re.DOTALL flag handles multi-line conflicts correctly |

## Results & Parameters

- **Number of branches rebased**: 9
- **Common conflict files**: AGENTS.md, justfile, scripts/inference360.py
- **Conflict cause**: All branches forked from older commit; origin/master added inferenceX benchmark references
- **Resolution strategy**: Keep origin/master superset content in all cases
- **Regex pattern**: `r"<<<<<<< HEAD.*?>>>>>>> [^(]+ \\(fix: add inferenceX benchmark\\)"`
- **Time saved**: ~45 minutes of manual resolution across 9 branches

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | PR #98-#107 rebase onto origin/master | 9 branches rebased, validated, pushed |
