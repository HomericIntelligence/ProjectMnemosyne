---
name: github-ssh-commit-signing-fix-unknown-key-verification
description: "Resolve GitHub SSH commit signing failures and unknown_key verification errors. Use when: (1) a PR is blocked by required signed commits, (2) GitHub reports commit.verification.reason as unknown_key, (3) you need a dedicated SSH signing key and a re-sign workflow for an existing branch."
category: tooling
date: 2026-04-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - git
  - ssh
  - commit-signing
  - pull-requests
---

# GitHub SSH Commit Signing: Fix Unknown Key Verification

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-02 |
| **Objective** | Unblock a GitHub PR gated by required signed commits and fix `unknown_key` verification failures |
| **Outcome** | Successful — a dedicated SSH signing key produced `verified: true` on GitHub for the amended PR commits |
| **Verification** | verified-local |

## When to Use

- A GitHub PR is blocked by a required signed-commit rule
- `gh api repos/<OWNER>/<REPO>/commits/<SHA> --jq '.commit.verification'` returns `reason: "unknown_key"` or `reason: "unsigned"`
- You want to use SSH-based commit signing instead of GPG
- You need to re-sign an existing commit already pushed to a PR branch

## Verified Workflow

### Quick Reference

```bash
ssh-keygen -t ed25519 -a 64 \
  -f ~/.ssh/github_signing_ed25519 \
  -C "github-radiance-signing"

gh ssh-key add ~/.ssh/github_signing_ed25519.pub \
  --type signing \
  --title "GitHub Radiance commit signing"

git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/github_signing_ed25519.pub
git config --global commit.gpgsign true

git commit --amend --no-edit -S
git push --force-with-lease

gh api repos/<OWNER>/<REPO>/commits/$(git rev-parse HEAD) --jq '.commit.verification'
```

### Detailed Steps

1. Inspect the PR blocker and verify whether signing is the issue:
   ```bash
   gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json mergeStateStatus,url
   gh api repos/<OWNER>/<REPO>/commits/$(git rev-parse HEAD) --jq '.commit.verification'
   ```
   If GitHub reports `reason: "unsigned"` or `reason: "unknown_key"`, the branch still fails the signed-commit rule.

2. Generate a dedicated SSH signing key rather than reusing an existing SSH auth key:
   ```bash
   ssh-keygen -t ed25519 -a 64 \
     -f ~/.ssh/github_signing_ed25519 \
     -C "github-radiance-signing"
   ```

3. Register the public key with GitHub as a **signing** key:
   ```bash
   gh ssh-key add ~/.ssh/github_signing_ed25519.pub \
     --type signing \
     --title "GitHub Radiance commit signing"
   ```
   If you use the web UI instead, add it under `Settings -> SSH and GPG keys` with `Key type` set to `Signing Key`.

4. Configure git to use SSH signing for future commits:
   ```bash
   git config --global gpg.format ssh
   git config --global user.signingkey ~/.ssh/github_signing_ed25519.pub
   git config --global commit.gpgsign true
   ```

5. Re-sign the existing PR commit:
   ```bash
   git checkout <branch>
   git commit --amend --no-edit -S
   git push --force-with-lease
   ```

6. Re-check GitHub verification:
   ```bash
   gh api repos/<OWNER>/<REPO>/commits/$(git rev-parse HEAD) --jq '.commit.verification'
   gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json mergeStateStatus,url
   ```
   The important success signal is `verified: true`.

7. If you cannot or do not want to persist repo config, use a one-shot signed amend:
   ```bash
   git -c gpg.format=ssh \
     -c user.signingkey=/Users/<USER>/.ssh/github_signing_ed25519.pub \
     commit --amend --no-edit -S
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Reused an existing SSH key that was not yet registered on GitHub as a signing key | GitHub saw the SSH signature but returned `reason: "unknown_key"` because the public key was not mapped to a signing key on the account at verification time | GitHub commit verification depends on the exact public key being uploaded as a **signing** key, not just any SSH key |
| Attempt 2 | Ran `git commit -S` in an environment that defaulted to GPG signing | The shell tried to invoke `gpg`, which was unavailable, so the signed commit failed before it could be written | For SSH signing, set `gpg.format=ssh` and point `user.signingkey` at the `.pub` key |
| Attempt 3 | Tried to update repo-local git config inside a sandboxed worktree whose git metadata lived outside the writable root | Git could not lock the external `.git/config` path, so config writes failed | Use global config outside the sandbox or a one-shot `git -c ... commit -S` invocation when repo-local config is blocked |

## Results & Parameters

**Key naming that worked well**:

```text
Private key: ~/.ssh/github_signing_ed25519
Public key:  ~/.ssh/github_signing_ed25519.pub
Key comment: github-radiance-signing
GitHub title: GitHub Radiance commit signing
```

**Expected successful verification output**:

```json
{
  "reason": "valid",
  "verified": true
}
```

**Useful diagnostics**:

```bash
# Commit verification details
gh api repos/<OWNER>/<REPO>/commits/<SHA> --jq '.commit.verification'

# PR mergeability snapshot
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json mergeStateStatus,url

# Current signing config
git config --get gpg.format
git config --get user.signingkey
git config --get commit.gpgsign
```

**Decision rule**:

- `reason: "unsigned"` → no signature was attached
- `reason: "unknown_key"` → signature exists but GitHub cannot match the public key to a signing key on the account
- `reason: "valid"` with `verified: true` → commit-signing requirement is satisfied

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Radiance | PR #33 signed-commit remediation | Re-signed two commits on `codex/radiance-docs-architecture`, verified them with GitHub commit API, and unblocked the signed-commit rule |
