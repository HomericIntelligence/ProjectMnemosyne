---
name: git-rebase-signing-ci
description: "Rebase and sign commits to pass CI pr-policy checks. Use when: (1) CI pr-policy fails on unsigned commits, (2) need to re-sign all PR commits after rebase, (3) force push signed commits to update a PR."
category: tooling
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [git, signing, rebase, ci, gpg]
---

# Git Rebase Signing for CI

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Sign all PR commits to pass CI pr-policy checks that require GPG signatures |
| **Outcome** | Successful — all commits show 'G' (good signature) after rebase |
| **Verification** | verified-ci |

## When to Use

- CI `pr-policy` check fails with "every commit is signed" requirement
- Commits were created without `-S` flag and need to be retroactively signed
- After rebasing, need to verify all commits are signed

## Verified Workflow

### Quick Reference

```bash
# Rebase all PR commits onto latest base with signing
git rebase --exec 'git commit --amend --no-edit -S' origin/main

# Verify all commits are signed (G = good)
git log --format='%h %G? %s' origin/main..HEAD

# Force push to update PR
git push --force-with-lease origin <branch>
```

### Detailed Steps

1. **Identify unsigned commits**: `git log --format='%h %G? %s' origin/main..HEAD` — look for `N` (no signature) or `U` (unknown validity).
2. **Rebase with signing**: `git rebase --exec 'git commit --amend --no-edit -S' origin/main` — this replays each commit and re-signs it with your GPG key.
3. **Verify**: Re-run `git log --format='%h %G? %s' origin/main..HEAD` — all should show `G`.
4. **Force push**: `git push --force-with-lease origin <branch>` — the `--force-with-lease` is safer than `--force` as it rejects if the remote has changes you haven't fetched.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git commit --amend -S` per commit | Manual signing of each commit | Tedious and error-prone with multiple commits | Use `--exec` flag to sign all commits in one rebase |
| `git push --force` | Force push without lease check | Could overwrite remote changes from other collaborators | Use `--force-with-lease` for safety |

## Results & Parameters

- **Signing key**: GPG key configured in git (`git config user.signingkey`)
- **Base branch**: `origin/main` (or `origin/master` depending on repo)
- **Verification output**: `G` = good signature, `N` = no signature, `U` = unknown validity

## Verified On

| Project | Context | Details |
|---------|---------|-------|
| HomericIntelligence/ProjectHephaestus | PR #1171 — show-prompt CLI | 4 commits rebased and signed, pr-policy passes |
| LLM360/Inference360 | PR #82 — Move inference360 module | Commits signed for pr-policy compliance |
