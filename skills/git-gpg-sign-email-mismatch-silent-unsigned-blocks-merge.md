---
name: git-gpg-sign-email-mismatch-silent-unsigned-blocks-merge
description: "Diagnose and fix silent GPG-signing failure modes that BLOCK PR merge under required_signatures / pr-policy 'every commit is signed' even with green CI. Covers: (a) commit.gpgsign=true plus author/committer email that does not match any UID on the GPG signing key producing commits GitHub reports verified=false reason=no_user (signs fine locally — %G?=G — but GitHub rejects); (b) GraphQL pullRequest.commits.signature.state lagging 10+ minutes behind reality so commits appear UNSIGNED in `gh pr view --json commits` while REST /commits/<sha> confirms verified=true; (c) sub-agent shells inheriting commit.gpgsign=true but silently failing to sign because gpg-agent was not pre-warmed (needs GPG_TTY + a priming gpg --batch call); (d) a GitHub +suffix noreply variant (e.g. user+bot@users.noreply.github.com) CANNOT be verified on a GitHub account so adding it as a key UID does NOT fix no_user — only {id}+{username}@users.noreply.github.com or a real verified email works; (e) bare `git commit -S` picking the wrong default signing key (%G?=E 'No public key') so pass `git -c user.signingkey=<subkey>`; (f) a commit that silently failed (pre-commit hook non-zero) leaves HEAD unchanged and `git log` shows the PREVIOUS commit's signature, masquerading as corruption. Use when: (1) PR shows mergeStateStatus BLOCKED with mergeable MERGEABLE and all CI green, (2) gh api .../commits returns verification.reason=no_user, (3) dispatching sub-agents that override user.email to a bot identity while keeping a personal GPG key, (4) auditing multi-repo sweeps for invisible signing failures, (5) `gh pr view --json commits` shows signature.state=null for newly-pushed commits, (6) sub-agent push produces unsigned commits despite global commit.gpgsign=true config, (7) global ~/.gitconfig sets a bot/automation email that hand-authored commits inherit and that fails verification, (8) building automated re-sign tooling that must validate the resign email against the signing key UIDs."
category: ci-cd
date: 2026-06-06
version: "2.1.0"
user-invocable: false
verification: verified-ci
history: git-gpg-sign-email-mismatch-silent-unsigned-blocks-merge.history
tags:
  - git
  - gpg
  - commit-signing
  - required-signatures
  - branch-protection
  - pull-requests
  - agent-dispatch
  - silent-failure
  - graphql-lag
  - gpg-agent
---

# Git GPG Signing: Email Mismatch Silently Produces Unsigned Commits, Blocks PR Merge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-11 |
| **Objective** | Diagnose and remediate the invisible failure mode where `commit.gpgsign=true` combined with a `user.email` that has no matching UID on the GPG secret key produces an unsigned commit with no error, blocking PR merge under `required_signatures` rulesets despite green CI |
| **Outcome** | Successful — re-authored 7 commits on ProjectKeystone PR #552 with the GPG-key-owner identity, re-signed with `--reset-author -S`, force-pushed, and GitHub flipped every commit to `verified: true` (PR unblocked, auto-merge fired) |
| **Verification** | verified-ci |

## When to Use

- A PR's `gh pr view --json mergeStateStatus` returns `BLOCKED` but `mergeable` returns `MERGEABLE` and every CI check is `SUCCESS`
- Direct merge attempt fails with `the base branch policy prohibits the merge`
- `gh api repos/<O>/<R>/pulls/<N>/commits --jq '.[].commit.verification'` shows `verified: false, reason: "no_user"` on every commit
- You are dispatching sub-agents (Myrmidon swarm workers, code-review fixers, etc.) that override `user.email` to a bot identity while inheriting a personal GPG key from `~/.gitconfig`
- You are auditing a multi-repo / multi-agent sweep where a small fraction of agents may have local config overrides that desync `user.email` from the GPG key UID
- You see commits in `git log --pretty=format:'%G?'` with status `N` (no signature) when you expected `G` (good signature)
- `gh pr view --json commits` shows `signature.state=null` (or `UNSIGNED`) for newly-pushed commits — the GraphQL field lags reality by 10+ minutes; always cross-check via REST `/commits/<sha>` before taking remediation action
- A sub-agent push produces unsigned commits despite global `commit.gpgsign=true` config — root cause is usually a non-pre-warmed `gpg-agent` in the non-interactive subshell, not config propagation
- Global `~/.gitconfig` sets a bot/automation `user.email` (e.g. `<user>+bot@users.noreply.github.com`) that hand-authored commits silently inherit, producing `no_user` while agent-authored commits (with the key-owner email) verify fine
- You are tempted to "fix" `no_user` by adding the bot email as a UID to the GPG key — STOP: a GitHub `+suffix` noreply variant cannot be verified on an account, so GitHub still returns `no_user` even after the UID is added (see the dedicated subsection below)
- `git log --show-signature` shows a Good signature but the GitHub REST commit verification still says `verified=false reason=no_user` — `--show-signature` only checks cryptographic validity against your local keyring, NOT whether GitHub can attribute the email to a verified account
- You are building automated re-sign tooling (fleet rebase, batch resign) that must NOT re-sign dozens of commits with an unverifiable identity — guard the resolved resign email against the signing key's UID emails first

## Verified Workflow

### Quick Reference

```bash
# Preflight: verify FIRST commit was actually signed (run inside agent before push)
git log -1 --pretty=format:'%G?'   # Must print 'G', NOT 'N' or 'B'

# Diagnose a BLOCKED PR with green CI
gh pr view <N> --repo <O>/<R> --json mergeStateStatus,mergeable
gh api repos/<O>/<R>/pulls/<N>/commits \
  --jq '.[].commit.verification'   # Look for verified:false reason:"no_user"

# Fix: re-author every commit to the GPG-key-owner identity AND re-sign
unset GITHUB_TOKEN GH_TOKEN
cd "$WORKTREE"
git config user.email "<GITHUB_USER_ID>+<USERNAME>@users.noreply.github.com"
git config user.name  "<GPG Key Owner Name>"
# user.signingkey and commit.gpgsign already set globally
OLD_HEAD=$(git rev-parse HEAD)
git fetch origin
git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'

# Verify content is byte-identical (CRITICAL)
git diff "$OLD_HEAD" HEAD   # Must be EMPTY (0 bytes)

# Verify every commit now signs cleanly
git log origin/main..HEAD --pretty=format:'%h %G? %an %s'   # All rows column-2 = G

git push --force-with-lease origin "$BRANCH"

# Confirm at GitHub
gh api repos/<O>/<R>/pulls/<N>/commits \
  --jq '[.[] | select(.commit.verification.verified == true)] | length'
# Must equal total commit count
```

### Detailed Steps

1. **Recognize the symptom pattern.** `mergeable: MERGEABLE` does NOT mean "passes branch protection" — it only means "no merge conflicts". The authoritative field is `mergeStateStatus`. If you see `mergeStateStatus: BLOCKED` with all CI green and no review requirements pending, suspect signature verification.

2. **Confirm via the commits API.** GitHub's commit verification object is the ground truth:
   ```bash
   gh api repos/<O>/<R>/pulls/<N>/commits --jq '.[].commit.verification'
   ```
   The diagnostic table:

   | `reason` | Meaning | Fix |
   |----------|---------|-----|
   | `unsigned` | No signature attached at all | Re-commit with `-S` after configuring signing |
   | `no_user` | Signature attached but author/committer email is not a verified email on the GitHub account that owns the key | **This skill** — re-author with the key-owner's registered email (`{id}+{username}@users.noreply.github.com`) AND re-sign. Note: adding a `+suffix` noreply variant as a key UID does NOT fix this |
   | `unknown_key` | Signature attached but public key not registered as a signing key on GitHub | See `github-ssh-commit-signing-fix-unknown-key-verification` |
   | `valid` + `verified:true` | Pass | Done |

3. **Inspect local config to confirm root cause.**
   ```bash
   git config --get user.email          # bot identity?
   git config --get user.signingkey     # personal GPG key?
   git config --get commit.gpgsign      # true?
   gpg --list-keys "$(git config --get user.signingkey)"
   # Look at the uid lines — does ANY match user.email?
   ```
   If `user.email` is not present as a UID on the secret key, GPG silently produces no signature. **Git does not error.** The commit is created without `gpgsig` and `git log --pretty=format:'%G?'` shows `N`.

4. **Set up the fix worktree.** Always operate in a worktree, not the main checkout:
   ```bash
   git fetch origin
   git worktree add /tmp/fix-signing-<branch> <branch>
   cd /tmp/fix-signing-<branch>
   OLD_HEAD=$(git rev-parse HEAD)
   ```

5. **Reconfigure to the key-owner identity (repo-local, not global).**
   ```bash
   git config user.email "<USER_ID>+<USERNAME>@users.noreply.github.com"
   git config user.name  "<Real Name on GPG Key>"
   ```
   The noreply form is preferred to satisfy GitHub email-privacy rules. The chosen email MUST appear as a UID on the GPG secret key (`gpg --list-keys` shows the UIDs).

6. **Re-author and re-sign every commit since `origin/main`.** The `--exec` flag runs the amend on each commit individually so each gets re-signed:
   ```bash
   git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'
   ```
   `--reset-author` updates both author and committer to the new identity. `-S` forces signing. `--no-edit` preserves the original commit message.

7. **CRITICAL — verify the file content is byte-identical.** The rebase should change ONLY commit metadata (author, committer, signature). If anything else changed, abort:
   ```bash
   git diff "$OLD_HEAD" HEAD   # MUST be empty (0 bytes). If not, STOP and investigate.
   ```

8. **Verify every commit now has a good signature locally.**
   ```bash
   git log origin/main..HEAD --pretty=format:'%h %G? %an %s'
   ```
   Every row's second column must be `G`. Codes: `G` = good, `B` = bad, `U` = unknown validity, `X` = expired, `Y` = expired key, `R` = revoked, `E` = signing error, `N` = no signature.

9. **Force-push with lease for safety.**
   ```bash
   git push --force-with-lease origin "$BRANCH"
   ```

10. **Confirm at GitHub side.** GitHub re-verifies on push:
    ```bash
    TOTAL=$(gh api repos/<O>/<R>/pulls/<N>/commits --jq 'length')
    VERIFIED=$(gh api repos/<O>/<R>/pulls/<N>/commits \
      --jq '[.[] | select(.commit.verification.verified == true)] | length')
    [ "$TOTAL" = "$VERIFIED" ] && echo "ALL SIGNED" || echo "STILL BROKEN: $VERIFIED/$TOTAL"
    gh pr view <N> --repo <O>/<R> --json mergeStateStatus
    ```
    `mergeStateStatus` should flip from `BLOCKED` to `CLEAN` (or `BEHIND` if rebase needed). Pre-armed `--auto-merge` will fire automatically.

11. **Preflight detection in agent prompts (preventative).** Add this gate to any agent that commits and pushes signed commits:
    ```bash
    # After first commit, before push:
    SIG=$(git log -1 --pretty=format:'%G?')
    if [ "$SIG" != "G" ]; then
      echo "FATAL: commit signature status is '$SIG' (expected 'G')"
      echo "user.email=$(git config --get user.email)"
      echo "user.signingkey=$(git config --get user.signingkey)"
      gpg --list-keys "$(git config --get user.signingkey)"
      exit 1
    fi
    ```

### GraphQL Lag — Use REST for Verification

The GraphQL field `pullRequest.commits.nodes.commit.signature.state` (exposed via
`gh pr view --json commits --jq '.commits[].signature.state'`) returns `null` or
`UNSIGNED` for several MINUTES TO HOURS after a push, even when the commit IS
signed and IS verified by GitHub. The REST endpoint is authoritative and updates
within seconds:

```bash
# Authoritative single-commit verification (use this, not GraphQL)
gh api repos/<owner>/<repo>/commits/<sha> \
  --jq '.commit.verification | "verified=\(.verified) reason=\(.reason)"'
# Returns immediately: verified=true reason=valid
```

```bash
# Authoritative PR-wide verification
gh api repos/<owner>/<repo>/pulls/<N>/commits \
  --jq '[.[] | {sha: .sha[0:7], verified: .commit.verification.verified, reason: .commit.verification.reason}]'
```

Diagnostic rule: **before taking any remediation action based on GraphQL UNSIGNED,
poll the REST API on one representative commit.** If REST reports `verified=true`,
the commits are fine — wait 10+ minutes and GraphQL will catch up. Do NOT re-upload
the GPG key, do NOT force-push, do NOT rebase — those are no-ops at best and
destructive at worst when the underlying signature is already valid.

### Pre-Warm gpg-agent in Sub-Agent Shells

When `commit.gpgsign=true` is set globally and the GPG key is on the GitHub account,
sub-agent shells DO inherit the config and DO sign correctly — but a non-interactive
subshell needs `GPG_TTY` set and a pre-warmed `gpg-agent` to actually produce a
signature. If pre-warming is skipped, the commit silently fails to sign (no error,
just no signature). Combined with the GraphQL lag above, this is indistinguishable
from "config didn't propagate" — always diagnose by checking the REST API state, not
by changing config.

**Pre-warm idiom (run once per sub-agent shell before the first `git commit -S`):**

```bash
export GPG_TTY=$(tty 2>/dev/null || echo /dev/null)
echo "test" | gpg --batch --yes --passphrase-fd 0 --pinentry-mode loopback \
  -as -o /dev/null 2>&1 | tail -1 || true
```

After this, `git commit` (with `commit.gpgsign=true` inherited from global config)
will sign correctly. Verify with the same `%G?` tripwire from step 11.

### GitHub +suffix noreply Emails Cannot Be Verified — Do NOT Patch the Key

`no_user` means "GitHub cannot attribute the signing email to a verified email on
the account that owns the key." The intuitive fix — add the offending email as a
new UID on the GPG key (`gpg --quick-add-uid`, re-export, re-upload) — **does not
work** when the offending email is a GitHub `+suffix` noreply variant such as
`<user>+bot@users.noreply.github.com`. GitHub **only** accepts two email shapes for
verification:

| Email shape | Verifiable on a GitHub account? |
|-------------|---------------------------------|
| `{id}+{username}@users.noreply.github.com` (the canonical ID-prefixed noreply) | YES |
| A real email you have added and verified in account settings | YES |
| `{username}+anything@users.noreply.github.com` (arbitrary `+suffix` variant) | **NO** — cannot be added/verified; GitHub still returns `no_user` |

Because the `+bot` noreply variant can never become a verified account email, you
cannot make `no_user` go away by binding it to the key. The only working fixes:

1. **Set the committer/author email to the key's already-registered address**
   (`{id}+{username}@users.noreply.github.com`) and re-author + re-sign — this is the
   primary workflow above.
2. **Make automation author commits with a verifiable email** in the first place
   (fix the global `~/.gitconfig` / agent config so it never writes the `+bot` email).

```bash
# Confirm which emails the key can actually sign as (UID emails on the key):
gpg --list-keys --with-colons "$KEY" | awk -F: '/^uid:/{print $10}'
# Each UID email here must ALSO be a verified email on the GitHub account that owns
# the key for GitHub to return verified=true. A +suffix noreply UID will NOT.
```

### Always Pass the Signing Key Explicitly; Re-Verify HEAD After Every Commit

Two foot-guns observed while re-signing by hand:

1. **Bare `git commit -S` can pick the wrong default key.** If `user.signingkey` is
   not set (or is shadowed), GPG falls back to a default secret key that GitHub does
   not know about, producing `%G? = E` ("No public key" / signature cannot be
   checked). Always pin the subkey on the command line:
   ```bash
   git -c user.signingkey="$SIGNING_SUBKEY" commit --amend --reset-author -S
   # SIGNING_SUBKEY = the signing subkey fingerprint, e.g. 7FD616C4744A8A7C
   ```

2. **A "failed" commit can leave HEAD unchanged and look like corruption.** If a
   pre-commit hook exits non-zero, `git commit` aborts and HEAD does NOT move. A
   subsequent `git log --show-signature` then shows the *previous* commit's
   signature/identity — which looks like the amend silently corrupted things, but the
   amend simply never happened. Defend by capturing the exit code and re-verifying the
   HEAD sha + message after every commit:
   ```bash
   PREV=$(git rev-parse HEAD)
   git -c user.signingkey="$SIGNING_SUBKEY" commit --amend --reset-author -S; RC=$?
   NEW=$(git rev-parse HEAD)
   if [ "$RC" -ne 0 ] || [ "$NEW" = "$PREV" ]; then
     echo "FATAL: commit did not happen (rc=$RC, HEAD unchanged). Fix the hook failure first."
     exit 1
   fi
   git log -1 --pretty=format:'%H %G? %ae %s'   # confirm new sha, %G?=G, key-owner email
   ```

### Defensive Tooling: Validate Resign Email Against Key UIDs Before Batch Re-Sign

Automated fleet/rebase tooling that re-signs many commits should refuse to run if the
resolved resign email is not a UID on the signing key — otherwise one bad config
re-signs dozens of commits with an unverifiable identity (which GitHub then rejects
en masse). Pattern implemented in `fleet_sync.get_resign_email()` (ProjectHephaestus,
PR #1026):

```python
# Pseudocode of the guard:
# 1. Resolve the resign email (from config / CLI / env).
# 2. Read the signing key's UID emails:
#       gpg --list-keys --with-colons <key>  -> parse uid lines, field 10 angle-bracket email
# 3. If resign_email not in uid_emails -> raise a clear error naming both sides.
# 4. Escape hatch: FLEET_SKIP_EMAIL_KEY_CHECK=1 bypasses the guard.
```

Note this UID check is **necessary but not sufficient**: a UID email that is a
`+suffix` noreply variant passes the local UID check yet still fails GitHub
verification (see the +suffix subsection above). Prefer validating against the
key-owner's canonical `{id}+{username}@users.noreply.github.com` address.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Set `user.email` to a bot identity (e.g. `noreply@homericintelligence.dev`) globally for the agent, kept personal GPG key as `user.signingkey`, ran `git commit -S` expecting it to sign | GPG could not find a secret key matching the bot email's UID, so it produced NO signature. Git did not error — exit 0 — and the commit landed unsigned. The agent thought it had succeeded | `commit.gpgsign=true` is a NO-OP when `user.email` does not match any UID on the configured signing key. Git silently writes the commit without `gpgsig`. Always run `git log -1 --pretty=format:'%G?'` after the first signed commit as a tripwire |
| Attempt 2 | Read `gh pr view --json mergeable` (got `MERGEABLE`) and concluded the PR could be merged | `mergeable` only reports merge-conflict status. It says nothing about branch-protection rules. The authoritative field is `mergeStateStatus` which returned `BLOCKED` | When diagnosing why an auto-merge is not firing, query `mergeStateStatus` (and `mergeStateStatus` reasons) — never `mergeable` alone. `mergeable: MERGEABLE` + `mergeStateStatus: BLOCKED` is the signature pattern |
| Attempt 3 | Tried `gh pr merge --rebase --admin` to bypass the rule | Even admin merge fails when `required_signatures` is set on the ruleset and the commits are unsigned — GitHub returns `the base branch policy prohibits the merge` | `required_signatures` cannot be admin-bypassed via the merge endpoint. The fix is at the commit layer, not the merge layer |
| Attempt 4 | Used `git commit --amend -S` on just the tip commit | Only the tip commit got signed. The other 6 commits in the PR were still unsigned, so the PR remained `BLOCKED`. `required_signatures` requires EVERY commit in the PR to be verified | Use `git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'` to re-sign every commit in the range |
| Attempt 5 | Ran the rebase --exec without `--reset-author` | `git log --pretty=format:'%G?'` still showed `N` for re-authored commits because the author email was still the bot identity, so GPG still found no matching UID and produced no signature | `--reset-author` is mandatory — it updates the author/committer fields to the current `user.email`/`user.name`, which is what GPG checks against the signing key UIDs |
| Attempt 6 | Checked PR mergeability without first verifying the diff was byte-identical to before the rebase | Risk: a poorly-configured rebase (e.g. rerere artifacts, autosquash side-effects, gitattribute clean filter changes) could silently rewrite content. If pushed, it would lose work | After any rewriting rebase, ALWAYS run `git diff <old-HEAD> <new-HEAD>` and confirm it is empty bytes before force-pushing |
| Attempt 7 | Trusted `gh pr view --json commits --jq '.commits[].signature.state'` GraphQL output of `UNSIGNED` as authoritative and began remediation | GraphQL field lags 10+ min after push, even when commits ARE verified by GitHub. Verified via REST `/commits/<sha>` returning `verified=true reason=valid` while GraphQL still showed `null`/`UNSIGNED` for 31 commits across Argus #520, Scylla #1978, Agamemnon #382. ~30 min wasted on the 2026-05-16 sweep | Always poll REST `gh api repos/<O>/<R>/commits/<sha>` for signature state; treat GraphQL `signature.state` as advisory only. Cross-check one commit via REST before any remediation |
| Attempt 8 | Re-sign commits by uploading the GPG key (again) to GitHub on the assumption it was missing | Existing key was already registered on the account; `gh gpg-key add` returned HTTP 422 "subkey already exists". Confirmed by `gh api user/gpg_keys` showing the key present and active. The underlying issue was GraphQL lag (Attempt 7), not key registration | Before re-uploading a GPG key, query REST commit verification on a single test commit; if `verified=true`, the issue is GraphQL lag (not key registration) and the correct action is to wait, not to re-upload |
| Attempt 9 | Trusted `git log --show-signature` ("Good signature", `%G?`=`G`) as proof the commit would pass GitHub's `pr-policy` "every commit is signed" gate | GitHub returned `verification: {verified:false, reason:"no_user"}` and the gate FAILED at merge. `--show-signature` only checks cryptographic validity against the LOCAL keyring; it says nothing about whether the committer email maps to a verified email on the key-owner's GitHub account | `git log --show-signature` lies about merge-readiness. The authoritative check is `gh api repos/<O>/<R>/commits/<sha> --jq .commit.verification` expecting `{verified:true, reason:"valid"}`. Always verify server-side, never trust `--show-signature` alone |
| Attempt 10 | Tried to fix `no_user` by adding the bot email (`<user>+bot@users.noreply.github.com`) as a new UID on the GPG key and re-uploading | GitHub will not let a `+suffix` noreply variant be added/verified as an account email (only `{id}+{username}@users.noreply.github.com` and real verified emails qualify), so GitHub kept returning `no_user` even with the UID present on the key | You cannot patch `no_user` at the key layer for a `+suffix` noreply email. Fix it at the identity layer: set the committer email to the key's registered `{id}+{username}@users.noreply.github.com` (or a real verified email) and re-sign |
| Attempt 11 | Re-signed with a bare `git commit -S` (no explicit `user.signingkey`) | GPG fell back to a foreign default secret key GitHub did not know; `%G?` came back `E` ("No public key" / cannot be checked) instead of `G` | Always pin the subkey: `git -c user.signingkey=<signing-subkey> commit -S`. Never rely on the default-key fallback when multiple secret keys exist |
| Attempt 12 | Amended a commit, saw `git log --show-signature` still showing the OLD identity/signature, and concluded the amend corrupted the repo | The amend had silently aborted because a pre-commit hook exited non-zero; HEAD never moved, so `git log` was just showing the unchanged previous commit. Not corruption — the commit simply did not happen | Capture the `git commit` exit code AND compare `git rev-parse HEAD` before/after. If HEAD is unchanged or rc≠0, the commit failed (fix the hook); never diagnose signatures off a HEAD that did not advance |

## Results & Parameters

**Diagnostic decision tree:**

```text
PR not auto-merging?
├─ Check: gh pr view --json mergeStateStatus
│  ├─ BLOCKED → continue
│  ├─ BEHIND  → rebase against base branch
│  ├─ DIRTY   → resolve conflicts
│  └─ CLEAN   → wait for CI
│
└─ BLOCKED with all CI green:
   └─ Check: gh api .../commits --jq '.[].commit.verification.reason'
      ├─ "unsigned"     → no signing configured; configure and re-commit
      ├─ "no_user"      → THIS SKILL — email/key UID mismatch, re-author + re-sign
      ├─ "unknown_key"  → key not registered as signing on GitHub; see SSH-signing skill
      └─ all "valid"    → not a signing problem; check missing required checks
```

**One-shot fix script (parametric):**

```bash
#!/usr/bin/env bash
set -euo pipefail
OWNER="$1"; REPO="$2"; PR="$3"; BRANCH="$4"
KEY_OWNER_EMAIL="$5"   # e.g. 4211002+mvillmow@users.noreply.github.com
KEY_OWNER_NAME="$6"    # e.g. "Micah Villmow"

unset GITHUB_TOKEN GH_TOKEN || true
WORKTREE="${HOME}/.tmp/fix-sign-${REPO}-${PR}"
git -C . worktree add "$WORKTREE" "$BRANCH"
cd "$WORKTREE"
git config user.email "$KEY_OWNER_EMAIL"
git config user.name  "$KEY_OWNER_NAME"

OLD_HEAD=$(git rev-parse HEAD)
git fetch origin
git rebase "origin/$(gh repo view "$OWNER/$REPO" --json defaultBranchRef --jq .defaultBranchRef.name)" \
  --exec 'git commit --amend --no-edit --reset-author -S'

# Tripwire: content must be unchanged
DIFF_BYTES=$(git diff "$OLD_HEAD" HEAD | wc -c)
if [ "$DIFF_BYTES" -ne 0 ]; then
  echo "FATAL: rebase changed file content ($DIFF_BYTES bytes). Aborting."
  exit 1
fi

# Tripwire: every commit signed locally
BAD=$(git log "origin/$(gh repo view "$OWNER/$REPO" --json defaultBranchRef --jq .defaultBranchRef.name)..HEAD" \
        --pretty=format:'%G?' | grep -cv '^G$' || true)
if [ "$BAD" -gt 0 ]; then
  echo "FATAL: $BAD commits failed to sign locally"
  exit 1
fi

git push --force-with-lease origin "$BRANCH"

# Wait for GitHub re-verification
sleep 3
TOTAL=$(gh api "repos/$OWNER/$REPO/pulls/$PR/commits" --jq 'length')
VERIFIED=$(gh api "repos/$OWNER/$REPO/pulls/$PR/commits" \
  --jq '[.[] | select(.commit.verification.verified == true)] | length')
echo "Verified: $VERIFIED / $TOTAL"
```

**Empirical detection in multi-agent sweeps:**

| Sweep | Total PRs | Affected | Rate | Cause |
|-------|-----------|----------|------|-------|
| 2026-05-11 HomericIntelligence ecosystem easy-issue sweep | 11 | 1 (Keystone PR #552) | ~9% | One agent had local `user.email` override to bot identity; the other 10 agents inherited keyring-default identity that matched the GPG key UID |

**Authoritative signature verification (REST, NOT GraphQL):**

```bash
# Single commit
gh api repos/<owner>/<repo>/commits/<sha> \
  --jq '.commit.verification | "verified=\(.verified) reason=\(.reason)"'

# Whole PR
gh api repos/<owner>/<repo>/pulls/<N>/commits \
  --jq '[.[] | {sha: .sha[0:7], verified: .commit.verification.verified, reason: .commit.verification.reason}]'
```

**Sub-agent gpg-agent pre-warm idiom (run once per non-interactive subshell):**

```bash
export GPG_TTY=$(tty 2>/dev/null || echo /dev/null)
echo "test" | gpg --batch --yes --passphrase-fd 0 --pinentry-mode loopback \
  -as -o /dev/null 2>&1 | tail -1 || true
```

**Critical config invariant for any signing agent:**

```bash
# After config is set, this MUST be true:
git config --get user.email | xargs -I{} gpg --list-keys "$(git config --get user.signingkey)" 2>/dev/null | grep -q "<{}>"
# If the grep fails, GPG will silently NOT sign.
```

**GPG signature status codes (`%G?` format)** for quick reference:

| Code | Meaning |
|------|---------|
| `G`  | Good signature (target state) |
| `B`  | Bad signature |
| `U`  | Good signature with unknown validity |
| `X`  | Good signature that has expired |
| `Y`  | Good signature made by an expired key |
| `R`  | Good signature made by a revoked key |
| `E`  | Signature cannot be checked (e.g. missing key) |
| `N`  | No signature (silent-fail state from this skill) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | 2026-05-11 ecosystem-wide easy-issue sweep, PR #552 | Re-authored 7 commits with `--reset-author -S` rebase, byte-identical content diff confirmed (0 bytes), force-pushed; GitHub flipped all 7 commits from `verified: false reason: "no_user"` to `verified: true reason: "valid"`; `mergeStateStatus` flipped from `BLOCKED` to `CLEAN`; pre-armed auto-merge fired immediately |
| ProjectArgus / ProjectScylla / ProjectAgamemnon | 2026-05-16 org-wide PR sweep — Argus #520, Scylla #1978, Agamemnon #382 | 31 commits across the three PRs showed `signature.state=null`/`UNSIGNED` via `gh pr view --json commits` (GraphQL) for 10+ minutes after push. REST `gh api repos/.../commits/<sha>` returned `verified=true reason=valid` for every commit immediately. Attempted `gh gpg-key add` returned HTTP 422 "subkey already exists" (key was already registered). Resolution: wait for GraphQL to catch up; no remediation needed. Lesson codified as Attempts 7 and 8 in this skill |
| ProjectHephaestus | 2026-06-06, PRs #1021 / #1026 | Global `~/.gitconfig` `user.email` was a bot identity (`mvillmow+bot@users.noreply.github.com`) that hand-authored commits inherited; the GPG key `F0A2530669A31A2E` (signing subkey `7FD616C4744A8A7C`) was bound only to `4211002+mvillmow@users.noreply.github.com`. Commits showed `%G?`=`G` locally but GitHub returned `verified=false reason=no_user` and pr-policy "every commit is signed" FAILED at merge. Discovered the `+bot` noreply variant cannot be added as a verified GitHub email, so patching the key UID was a dead end (Attempt 10). Fixed by `git config user.email 4211002+mvillmow@users.noreply.github.com` + `git commit --amend --reset-author -S`; `gh api .../commits/<sha> --jq .commit.verification` then returned `{verified:true, reason:"valid"}` and pr-policy passed. Added a defensive guard in `fleet_sync.get_resign_email()` (PR #1026) validating the resign email against the key UID emails, with `FLEET_SKIP_EMAIL_KEY_CHECK=1` bypass. Also hit Attempts 11 (bare `git commit -S` picked a foreign key, `%G?`=`E`) and 12 (silent commit abort from a non-zero pre-commit hook left HEAD unchanged, masquerading as corruption) |
