---
name: tooling-wave-b-pr-fix-mesh-playbook
description: "Wave-B autonomous fix-mesh playbook: green 20+ failing PRs across multiple HomericIntelligence repos by applying mechanical autofixes (markdownlint, clang-format, pixi lock, pre-commit autofixes) with signed/verified commits. Use when: (1) running an autonomous PR-sweep where many fully-auto PRs are red on the same mechanical checks, (2) re-signing previously unsigned commits to satisfy branch-protection signature policies, (3) applying a single shared-doc fix across N PRs that all inherit the same defect from main."
category: tooling
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Wave-B PR Fix-Mesh Playbook

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-31 |
| **Objective** | Turn red CI green on 22 fully-auto PRs across 7 HomericIntelligence repos using purely mechanical autofixes with signed commits. |
| **Outcome** | All 22 target PRs green; signed commits verified by GitHub API; auto-merge eligible. |
| **Verification** | verified-ci — every check observed `conclusion=success` in real CI on host `aeolus`. |
| **Host** | `aeolus` (account uses GitHub email-privacy noreply identity for pushes). |
| **Cross-links** | [Odysseus#299](https://github.com/HomericIntelligence/Odysseus/pull/299) · `/home/mvillmow/pr-mesh-run/report.md` |

## When to Use

- A Myrmidon swarm or autonomous run has produced 10+ PRs that are all red on the same mechanical checks (markdownlint, clang-format, pixi-lock, pre-commit autofixes).
- You need to re-sign a previously-pushed unsigned commit without rewriting history beyond the tip.
- A shared doc on `main` has a defect that N open PRs all inherit (none of them touched it) and you want to fix it once and propagate.
- You are running on host `aeolus` or any environment where GitHub email-privacy blocks pushes that author with the gmail address.

## Verified Workflow

### Quick Reference

```bash
# 1. Shallow clone but ALSO fetch all PR heads into origin/*
gh repo clone HomericIntelligence/REPO -- --depth=50
cd REPO
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --depth=50

# 2. Force noreply identity on aeolus (email-privacy is enabled)
git config user.email '4211002+mvillmow@users.noreply.github.com'
git config user.name 'mvillmow'
# Signing is global: gpg.format=ssh, signingkey=~/.ssh/id_signing_ed25519.pub, commit.gpgsign=true

# 3. Shared-doc fan-out fix across N PRs (one base worktree, loop branches)
cp path/to/FIXED-FILE /tmp/fixed-file
for BR in pr-branch-1 pr-branch-2 pr-branch-N; do
  git checkout -B "$BR" "origin/$BR"
  cp /tmp/fixed-file path/to/FIXED-FILE
  git add path/to/FIXED-FILE
  git commit -S -m "fix: apply shared-doc autofix"
  git push origin "HEAD:$BR"
done

# 4. Targeted single-hook pre-commit (skips heavy hooks like mojo-format)
pre-commit run markdownlint-cli2 --files docs/foo.md
pre-commit run trailing-whitespace --files docs/foo.md
pre-commit run end-of-file-fixer  --files docs/foo.md

# 5. Re-sign an unsigned commit already on origin
git fetch && git checkout -B local "origin/$BR"
git commit --amend -S --no-edit
git push --force-with-lease origin "HEAD:$BR"

# 6. Definitive CI status (gh pr checks lies; check-runs API does not)
SHA=$(gh pr view N --repo ORG/REPO --json headRefOid --jq .headRefOid)
gh api "repos/ORG/REPO/commits/$SHA/check-runs" \
  --jq '.check_runs[] | "\(.name)\t\(.conclusion)"'

# 7. Confirm signature verifies on GitHub side
gh api "repos/ORG/REPO/commits/$SHA" --jq .commit.verification.verified  # → true
```

### Detailed Steps

#### Step 1 — Shallow-clone refspec (avoid the "not a commit" trap)

`gh repo clone … -- --depth=N` only writes the default branch into `origin/main`. PR branches are NOT fetched. To unlock `git checkout -B prN origin/BRANCH` you MUST widen the refspec FIRST and re-fetch:

```bash
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --depth=50
```

Without this, every `git checkout -B prN origin/BRANCH` fails with `fatal: 'origin/BRANCH' is not a commit`.

#### Step 2 — Multi-PR shared-doc fan-out (one worktree, N branches)

When N PRs all fail the same check due to a defect in a shared doc on `main` that none of them touched, do NOT clone N worktrees. Instead:

1. In ONE worktree, fix the file on a scratch branch.
2. Copy the fixed file to `/tmp/fixed-file`.
3. Loop: `git checkout -B prN origin/BRANCH && cp /tmp/fixed-file path/to/file && git add … && git commit -S && git push origin HEAD:BRANCH`.

This is ~10x faster than N clones and keeps the fix byte-identical across PRs.

#### Step 3 — markdownlint-cli2 `--fix` is incomplete

`markdownlint-cli2 --fix` does NOT reliably fix:

- **MD013** (line-length) — requires manual rewrapping. The autofix never wraps long lines.
- **MD007** (unordered-list-indent) — leaves nested lists at wrong indent.
- **MD031 / MD032** (blanks-around-fences / blanks-around-lists) — partial in mixed contexts.
- **MD034** (bare URLs) — misses URLs inside table cells and footnotes.

Always re-lint after `--fix`:

```bash
pre-commit run markdownlint-cli2 --files <file>
# If still red → hand-rewrap to 100 cols, hand-fix bare URLs to <URL>, re-run.
```

#### Step 4 — Single-hook pre-commit invocation

`pre-commit run --all-files` triggers heavy hooks (mojo-format, clang-format-full, …) that take minutes. For autofix-class hooks, target one hook on one file:

```bash
pre-commit run <hook-id> --files X Y
```

Hooks proven safe to run in isolation: `trailing-whitespace`, `end-of-file-fixer`, `markdownlint-cli2`, `yamllint`, `check-merge-conflict`.

#### Step 5 — Re-sign an already-pushed unsigned commit

A Wave-A run pushed an unsigned commit on `ProjectMnemosyne#2071`. The repo's branch protection requires `Verified` signatures, so the PR was blocked despite green tests. Recovery:

```bash
git fetch && git checkout -B local "origin/$BR"
git commit --amend -S --no-edit
git push --force-with-lease origin "HEAD:$BR"
gh api "repos/ORG/REPO/commits/$(git rev-parse HEAD)" --jq .commit.verification.verified
# → true
```

`--force-with-lease` is SAFE here because we hold the exact `origin/$BR` SHA from the immediately-prior fetch. Do NOT use plain `--force`.

#### Step 6 — `gh pr checks` lies; the check-runs API does not

`gh pr checks N --repo ORG/REPO` caches and can return stale states for 30-60s after a push. For decision-grade status (pass/fail gating auto-merge), always use:

```bash
SHA=$(gh pr view N --repo ORG/REPO --json headRefOid --jq .headRefOid)
gh api "repos/ORG/REPO/commits/$SHA/check-runs" \
  --jq '.check_runs[] | select(.name=="<check-name>") | .conclusion'
```

AchaeanFleet workflows run 15-30 minutes wall-clock. Bound polls to once-per-90s and cap total at 35 min before paging a human.

#### Step 7 — Aeolus noreply email is mandatory

The account has GitHub's email-privacy "Block command line pushes that expose my email" enabled. Pushes that author with `villmow.products@gmail.com` are rejected with:

```text
remote: error: GH007: Your push would publish a private email address.
```

Mitigation (set per-clone OR globally):

```bash
git config user.email '4211002+mvillmow@users.noreply.github.com'
```

The SSH signing key (`~/.ssh/id_signing_ed25519.pub`) is registered on GitHub under that noreply identity, so signatures verify only when the author email matches. Setting `user.email` to anything else simultaneously breaks pushes AND signature verification.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial shallow clone | `gh repo clone REPO -- --depth=50` then `git checkout -B prN origin/BRANCH` | Default refspec only fetches `refs/heads/main`; `origin/BRANCH` did not exist. `fatal: 'origin/BRANCH' is not a commit`. | Widen refspec to `+refs/heads/*:refs/remotes/origin/*` and re-fetch BEFORE checking out any PR branch on a shallow clone. |
| Markdownlint autofix-only | Ran `markdownlint-cli2 --fix` expecting it to green MD013 (line-length) violations | `--fix` does not rewrap long lines; the check stayed red on every long-line offense. | Treat `--fix` as a partial preprocessor. Always re-lint and hand-rewrap MD013/MD007/MD034 residue. |
| Wave-A unsigned push | Wave-A predecessor pushed a normal (unsigned) commit to `ProjectMnemosyne#2071` | Repo branch protection requires `Verified` signatures; PR blocked from auto-merge despite green CI. | Always pass `-S` on commit. Recovery: `git commit --amend -S --no-edit && git push --force-with-lease`, then confirm via `gh api …/commits/$sha --jq .commit.verification.verified` returns `true`. |

## Results & Parameters

### Scoreboard

| Metric | Value |
|--------|-------|
| Target PRs | 22 fully-auto PRs |
| Repos touched | 7 (HomericIntelligence/*) |
| Final state | All 22 green on every required check |
| Host | `aeolus` |
| Date | 2026-05-31 |
| Signature verification | 100% of new commits return `verified=true` |

### Required git config (per clone, on aeolus)

```ini
[user]
    email = 4211002+mvillmow@users.noreply.github.com
    name  = mvillmow
# Inherited from global:
# [gpg]      format     = ssh
# [user]     signingkey = ~/.ssh/id_signing_ed25519.pub
# [commit]   gpgsign    = true
```

### Polling discipline

| Stage | Cadence | Cap |
|-------|---------|-----|
| Post-push CI poll | every 90s | 35 min wall-clock |
| Re-sign verification | once, immediately after force-push | n/a — synchronous via API |
| `gh pr checks` | DO NOT rely on for gating; informational only | n/a |
| `gh api …/check-runs` | authoritative source | n/a |

### Hooks safe to run as single-hook autofix

`trailing-whitespace` · `end-of-file-fixer` · `markdownlint-cli2` · `yamllint` · `check-merge-conflict` · `clang-format` (if `--files` is scoped)

### Cross-links

- PR: [HomericIntelligence/Odysseus#299](https://github.com/HomericIntelligence/Odysseus/pull/299)
- Run report: `/home/mvillmow/pr-mesh-run/report.md` on `aeolus`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/* (7 repos) | Wave-B autonomous fix-mesh, host `aeolus`, 2026-05-31 | 22/22 PRs green; signatures verified by GitHub API. |
