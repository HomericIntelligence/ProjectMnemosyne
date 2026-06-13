---
name: git-unmerged-branch-file-access
description: "Access files that exist only on non-main git branches. Use when: (1) Read/Glob/Grep return not-found for a file that should exist, (2) fixing a file introduced in a feature branch not yet merged to main, (3) planning PRs that must target a feature branch rather than main."
category: tooling
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Git Unmerged Branch File Access

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Read and plan fixes for files that exist only on non-main feature branches |
| **Outcome** | Approach documented; not yet validated end-to-end |
| **Verification** | unverified |

## When to Use

- `Read`, `Glob`, or `Grep` returns "not found" for a file you expect to exist
- An issue references a file introduced in a feature branch that has not been merged to main
- A PR fix must target a feature branch (e.g., `1210-auto-impl`) instead of `main`
- Planning a fix for code visible in a PR diff but absent from the working tree

## Verified Workflow

> **Note:** This workflow is **unverified** — documented from planning artifacts only and has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Find commits related to an issue number (searches all branches)
git log --all --oneline --grep=<issue-number>

# 2. Identify which branch holds a specific commit
git branch --all --contains <sha>

# 3. Read a file from a specific commit or branch
git show <sha>:path/to/file.py
git show origin/<branch-name>:path/to/file.py

# 4. List files changed in a commit
git show --stat <sha>

# 5. Find which branch a file exists on
git log --all --oneline -- path/to/file.py
```

### Detailed Steps

1. **Detect the problem**: If `Read`, `Glob`, or `Grep` returns not-found for a file that an issue or PR references, the file likely lives on a feature branch not yet merged to main.

2. **Find the commit**: Search all branches for commits related to the issue:
   ```bash
   git log --all --oneline --grep=<issue-number>
   ```

3. **Identify the branch**: Check which branch(es) contain the commit:
   ```bash
   git branch --all --contains <sha>
   ```

4. **Read the file**: Use `git show` to access the file content without switching branches:
   ```bash
   git show <sha>:path/to/file.py
   # or using branch reference directly:
   git show origin/<branch-name>:path/to/file.py
   ```

5. **Target the correct PR base**: When creating a PR for a fix, set the base to the feature branch, NOT `main`. The fix branch should fork from the feature branch so it can be merged there:
   ```bash
   git checkout -b fix/<description> <feature-branch>
   # ... make changes ...
   gh pr create --base <feature-branch> --title "fix: ..."
   ```

## Results & Parameters

When the file is found via `git show`, note:
- The SHA of the commit where it lives
- The branch name (visible in `git branch --all --contains <sha>`)
- Whether the branch is a remote tracking branch (`origin/<branch>`) or local

For PR targeting:
- If file only exists on `origin/<feature-branch>`, the fix PR **must** base off that feature branch
- Use `gh pr create --base <feature-branch>` — not `--base main`
- The merged feature branch PR will bring the fix along when it eventually merges to main

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct Read tool | Used Read/Glob/Grep with the expected file path | File not found — silently returns nothing because file only exists on feature branch | File read tools operate on the working tree (checked-out branch); they cannot see files on other branches |
| Assuming file should exist on main | Proceeded as if file was missing from repo entirely | Wasted planning cycles trying to understand why a referenced file didn't exist | Always check `git log --all` before concluding a file is absent |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1300 planning (severity_label.py GITHUB_REPOSITORY KeyError) | File existed only on 1210-auto-impl branch; discovered via git log --all |
