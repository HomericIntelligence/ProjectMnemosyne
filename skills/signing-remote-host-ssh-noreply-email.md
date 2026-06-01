---
name: signing-remote-host-ssh-noreply-email
description: "Make GitHub-VALID (verification.verified==true) signed commits from a remote/headless build host (e.g. aeolus in the HomericIntelligence mesh swarm) using an SSH signing key. Covers: (a) generating an ed25519 SSH signing keypair on the host and wiring git's gpg.format=ssh config + allowed_signers file; (b) registering the PUBLIC key as a SIGNING key on GitHub via `gh ssh-key add --type signing`, which REQUIRES the PAT scope admin:ssh_signing_key (granted interactively, not headlessly); (c) the email-privacy push block where a commit authored with the real private email is REJECTED with 'push declined due to email privacy restrictions', fixed by authoring with the <id>+<login>@users.noreply.github.com email; (d) the finding that GitHub does NOT auto-sign PAT-authored commits made via the Contents REST API. Use when: (1) setting up commit signing on a fresh remote/headless/CI host, (2) commits land Unverified despite a key being added (key added auth-only, missing --type signing), (3) `git push` is rejected for email privacy restrictions even though signing is correct, (4) you need the GitHub noreply email derivation, (5) `gh api user/ssh_signing_keys` returns 404 for missing admin:ssh_signing_key scope, (6) API-authored commits report verification.reason=unsigned."
category: ci-cd
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - git
  - ssh-signing
  - commit-signing
  - github
  - noreply-email
  - email-privacy
  - headless
  - remote-host
  - gh-cli
  - admin-ssh-signing-key
---

# Signed Commits From a Remote Host: SSH Signing Key + noreply Email

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-31 |
| **Objective** | Make GitHub-VALID signed commits (`verification.verified == true`) from a remote/headless build host (e.g. `aeolus` in the HomericIntelligence mesh swarm), where the commit author must satisfy GitHub's email-privacy push block AND every commit must verify against a registered SSH signing key |
| **Outcome** | Successful — generated an ed25519 SSH signing key on the host, registered it as a SIGNING key (`gh ssh-key add --type signing`), set the author to the `<id>+<login>@users.noreply.github.com` email, pushed a scratch commit, and confirmed `gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified` returned `true` |
| **Verification** | verified-ci — commits were pushed and GitHub returned `verification.verified == true` |

## When to Use

- Setting up commit signing for the first time on a fresh remote / headless / CI build host (no GUI, no existing key)
- Commits land **Unverified** on GitHub even though a key was added — usually the key was registered auth-only (missing `--type signing`)
- `git push` is **rejected** with `push declined due to email privacy restrictions` even though the commit IS correctly signed
- You need the exact GitHub noreply email derivation (`<numeric-id>+<login>@users.noreply.github.com`)
- `gh api --method POST user/ssh_signing_keys` returns HTTP 404 because the token lacks the `admin:ssh_signing_key` scope
- You tried to author commits via the GitHub Contents REST API expecting auto-signing, and they come back `verification.reason=unsigned`
- You want to validate end-to-end that signing works before trusting a whole batch of commits

## Verified Workflow

### Quick Reference

```bash
# 1. Generate an SSH signing keypair on the remote host (no passphrase for headless use)
ssh-keygen -t ed25519 -f ~/.ssh/id_signing_ed25519 -N ""

# 2. Configure git globally to sign with SSH
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub
git config --global commit.gpgsign true
mkdir -p ~/.config/git
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
EMAIL="$(gh api user --jq '.id')+$(gh api user --jq '.login')@users.noreply.github.com"
printf '%s %s\n' "$EMAIL" "$(cat ~/.ssh/id_signing_ed25519.pub)" >> ~/.config/git/allowed_signers

# 3. Author commits with the noreply email (bypasses the email-privacy push block AND still verifies)
git config --global user.email "$EMAIL"   # e.g. 4211002+mvillmow@users.noreply.github.com

# 4. Grant the scope the gh token lacks, then register the PUBLIC key as a SIGNING key
gh auth refresh -h github.com -s admin:ssh_signing_key   # interactive: human approves device-code/browser flow
gh ssh-key add ~/.ssh/id_signing_ed25519.pub --type signing --title "$(hostname)-signing"

# 5. Verify end-to-end on a throwaway branch BEFORE trusting a batch
git checkout -b verify-signing-scratch
git commit --allow-empty -S -m "verify signing"
git push -u origin verify-signing-scratch
SHA=$(git rev-parse HEAD)
gh api repos/<owner>/<repo>/commits/$SHA --jq .commit.verification.verified   # must print: true
git push origin --delete verify-signing-scratch   # clean up the scratch branch
```

### Detailed Steps

1. **Generate the keypair on the host.** Use ed25519 and an empty passphrase so the headless host can sign non-interactively:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_signing_ed25519 -N ""
   ```
   This is a **signing** key, kept distinct from any auth key on the host.

2. **Wire git's SSH-signing config (global).**
   ```bash
   git config --global gpg.format ssh
   git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub
   git config --global commit.gpgsign true
   git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
   ```
   The `gpg.format ssh` line is what switches git from GPG to SSH signing. `user.signingkey` points at the **public** key file for SSH signing (unlike GPG, where it is a key ID).

3. **Populate the allowed_signers file** so local `git log --show-signature` can verify (one line per signer):
   ```bash
   mkdir -p ~/.config/git
   EMAIL="$(gh api user --jq '.id')+$(gh api user --jq '.login')@users.noreply.github.com"
   printf '%s %s\n' "$EMAIL" "$(cat ~/.ssh/id_signing_ed25519.pub)" >> ~/.config/git/allowed_signers
   ```
   Format: `<email> <pubkey-type> <pubkey-body>` (pasting the whole `.pub` line after the email works).

4. **Set the commit author to the GitHub noreply email — CRITICAL.** Derivation:
   ```
   <numeric-id>+<login>@users.noreply.github.com
   # e.g. 4211002+mvillmow@users.noreply.github.com
   ```
   ```bash
   git config --global user.email "$(gh api user --jq '.id')+$(gh api user --jq '.login')@users.noreply.github.com"
   ```
   If the GitHub account has **"Block command-line pushes that expose my email"** enabled, pushing a commit authored with the real private (gmail) email is **rejected** — even with correct signing. The noreply email BOTH bypasses the push block AND still verifies against the registered key.

5. **Grant the missing scope, then register the PUBLIC key as a SIGNING key.** The default `gh` token lacks `admin:ssh_signing_key`; registering the key via the API returns HTTP 404 without it. Grant it interactively (a human must approve the device-code / browser flow — **cannot be done headlessly**):
   ```bash
   gh auth refresh -h github.com -s admin:ssh_signing_key
   gh ssh-key add ~/.ssh/id_signing_ed25519.pub --type signing --title "$(hostname)-signing"
   ```
   The `--type signing` flag is **essential**. Without it the key registers as an **auth** key, and commits stay **Unverified** on GitHub even though they are locally signed.

6. **Verify end-to-end on a throwaway branch before trusting a batch.** Signature validity is checkable via the REST API independently of any push policy:
   ```bash
   git checkout -b verify-signing-scratch
   git commit --allow-empty -S -m "verify signing"
   git push -u origin verify-signing-scratch
   SHA=$(git rev-parse HEAD)
   gh api repos/<owner>/<repo>/commits/$SHA --jq .commit.verification.verified   # expect: true
   git push origin --delete verify-signing-scratch
   ```
   Only after `true` is returned should you proceed with the real batch of signed commits.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Author commits via the GitHub Contents REST API expecting auto-sign | `POST` commits through the Contents API on the assumption GitHub would sign them server-side | Returned `verification.verified=false, reason=unsigned` — GitHub does NOT auto-sign PAT-authored commits without Vigilant mode + a registered key | Real local signing is required; the REST API does not sign commits for you. Sign locally and push |
| Push a correctly-signed commit authored with the private gmail email | `git push` of a commit that was already correctly SSH-signed | `push declined due to email privacy restrictions` — the account blocks command-line pushes that expose the real email, independent of signing correctness | Author with the GitHub noreply email (`<id>+<login>@users.noreply.github.com`); it bypasses the email-privacy push block and still verifies |
| Register the signing key via the API with the current token | `gh api --method POST user/ssh_signing_keys` (and equivalently `gh ssh-key add` without the scope) | HTTP 404 — the token lacked the `admin:ssh_signing_key` scope | Grant the scope interactively with `gh auth refresh -h github.com -s admin:ssh_signing_key`; it requires a human to approve the device-code/browser flow and cannot be done headlessly |
| Register the key without `--type signing` | `gh ssh-key add ~/.ssh/id_signing_ed25519.pub --title host-key` (no type) | The key registered as an **auth** key, so GitHub had no signing key to verify against and commits stayed **Unverified** | `--type signing` is mandatory; an auth-only key does not make commits verify |

## Results & Parameters

**Exact git config (global) for SSH commit signing on a remote host:**

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub
git config --global commit.gpgsign true
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
git config --global user.email "<numeric-id>+<login>@users.noreply.github.com"
```

**allowed_signers line format** (`~/.config/git/allowed_signers`):

```text
<numeric-id>+<login>@users.noreply.github.com ssh-ed25519 AAAA...<pubkey-body>
```

**GitHub noreply email derivation:**

```text
<numeric-id>+<login>@users.noreply.github.com
# numeric-id from:  gh api user --jq '.id'      (e.g. 4211002)
# login from:       gh api user --jq '.login'   (e.g. mvillmow)
# result:           4211002+mvillmow@users.noreply.github.com
```

**Key-registration commands (the scope grant is interactive):**

```bash
gh auth refresh -h github.com -s admin:ssh_signing_key   # human approves browser/device flow
gh ssh-key add ~/.ssh/id_signing_ed25519.pub --type signing --title "<host>-signing"
```

**End-to-end verification (works even if a push is otherwise rejected):**

```bash
gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified
# Expected output: true
```

> Note: signature validity (`verification.verified`) is checkable via the REST API even when a *push* is rejected, because GitHub validates the commit object against the registered signing key **independently** of the push (email-privacy) policy. Use this to confirm signing is correct before debugging push rejections.

**Two orthogonal gates** that BOTH must pass — debug them separately:

| Gate | Controlled by | Symptom when failing | Fix |
|------|---------------|----------------------|-----|
| Signature verification | Key registered with `--type signing` + author email matches a registered identity | Commit shows **Unverified** on GitHub | Add key with `--type signing`; author with the noreply email |
| Push acceptance (email privacy) | "Block command-line pushes that expose my email" account setting | `push declined due to email privacy restrictions` | Author with `<id>+<login>@users.noreply.github.com` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence mesh (remote host `aeolus`) | 2026-05-31 — first-time signing setup on a headless build host | Generated ed25519 SSH signing key, registered with `gh ssh-key add --type signing` (after `gh auth refresh -s admin:ssh_signing_key`), authored with `<id>+<login>@users.noreply.github.com`; scratch commit pushed and `gh api repos/<owner>/<repo>/commits/<sha> --jq .commit.verification.verified` returned `true` |
