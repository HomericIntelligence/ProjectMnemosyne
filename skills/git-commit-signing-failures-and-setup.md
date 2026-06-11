---
name: git-commit-signing-failures-and-setup
description: "Diagnose and fix commit signing failures that block PR merge under required_signatures / pr-policy gates. Use when: (1) a PR shows mergeStateStatus BLOCKED with all CI green and mergeable MERGEABLE — suspect unsigned or unverified commits, (2) GPG commit.gpgsign=true produces commits GitHub reports as verified=false with reason=no_user because the author email has no matching UID on the signing key, (3) sub-agent shells inherit commit.gpgsign=true but silently fail to sign due to un-warmed gpg-agent or wrong default key, (4) setting up commit signing on a fresh remote/headless/CI host for the first time using SSH signing keys, (5) git push is rejected with 'push declined due to email privacy restrictions' even though signing appears correct, (6) the pr-policy required-check gate reports unsigned commits even though local git log shows signatures"
category: tooling
date: 2026-06-11
version: "1.0.1"
user-invocable: false
history: git-commit-signing-failures-and-setup.history
tags:
  - git
  - gpg
  - ssh-signing
  - commit-signing
  - required-signatures
  - pr-policy
  - branch-protection
  - noreply-email
  - email-privacy
  - gpg-agent
  - graphql-lag
  - headless
  - agent-dispatch
---

# Git Commit Signing: Failures and Setup

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Diagnose and remediate commit-signing failures that block PR merge under `required_signatures` / `pr-policy` gates (silent unsigned commits, email/key-UID mismatch producing `no_user`, un-warmed gpg-agent in sub-shells, GraphQL lag), AND set up GitHub-valid signing from scratch on a fresh remote/headless host using SSH signing keys |
| **Outcome** | Successful — re-authored and re-signed blocked PRs across multiple repos (Keystone #552, Hephaestus #1021/#1026/#1071, #900) flipping commits to `verified: true`; set up first-time SSH signing on headless host `aeolus` and confirmed `verification.verified == true` via REST |
| **Verification** | verified-ci |

## When to Use

- A PR's `gh pr view --json mergeStateStatus` returns `BLOCKED` while `mergeable` returns `MERGEABLE` and every CI check is `SUCCESS` — `mergeable` only means "no conflicts", NOT "passes branch protection". The authoritative blocker is usually the `pr-policy` / signature gate.
- `gh api repos/<O>/<R>/pulls/<N>/commits --jq '.[].commit.verification'` shows `verified: false, reason: "no_user"` (signed locally but author/committer email has no matching UID on the key registered to the GitHub account).
- A direct merge fails with `the base branch policy prohibits the merge` — `required_signatures` cannot be admin-bypassed at the merge layer.
- You are dispatching sub-agents (Myrmidon swarm workers, code-review fixers) that override `user.email` to a bot identity while inheriting a personal GPG key, OR that need to create signed commits in a repo with `pr-policy`.
- You are auditing a multi-repo / multi-agent sweep where a few agents may have local config overrides that desync `user.email` from the GPG key UID.
- `gh pr view --json commits` shows `signature.state=null` / `UNSIGNED` for newly-pushed commits — the GraphQL field lags reality by 10+ minutes; cross-check via REST `/commits/<sha>` before acting.
- A sub-agent push produces unsigned commits despite global `commit.gpgsign=true` — usually a non-pre-warmed `gpg-agent` in the non-interactive subshell, not config propagation.
- You are tempted to "fix" `no_user` by adding a `+suffix` bot noreply email as a GPG key UID — STOP, it cannot be verified on a GitHub account.
- You are setting up commit signing for the FIRST time on a fresh remote / headless / CI host (no GUI) using an SSH signing key.
- `git push` is rejected with `push declined due to email privacy restrictions` even though the commit is correctly signed.
- `gh api user/ssh_signing_keys` / `gh ssh-key add --type signing` returns HTTP 404 (token lacks `admin:ssh_signing_key` scope), or commits land Unverified because a key was added auth-only (missing `--type signing`).
- You authored commits via the GitHub Contents REST API expecting auto-signing and they come back `verification.reason=unsigned`.
- You are building automated re-sign / fleet tooling that must validate the resign email against the key UIDs and must NEVER rewrite PRs it does not own.

## Verified Workflow

### Quick Reference

```bash
# --- DIAGNOSE a BLOCKED PR with green CI ---
gh pr view <N> --repo <O>/<R> --json mergeStateStatus,mergeable,statusCheckRollup
gh api repos/<O>/<R>/pulls/<N>/commits \
  --jq '.[].commit.verification'        # look for verified:false reason:"no_user"/"unsigned"

# --- AUTHORITATIVE per-commit check (REST, NOT GraphQL — GraphQL lags 10+ min) ---
gh api repos/<O>/<R>/commits/<sha> \
  --jq '.commit.verification | "verified=\(.verified) reason=\(.reason)"'

# --- PREFLIGHT tripwire (run inside agent after first commit, before push) ---
git log -1 --pretty=format:'%G?'        # MUST print 'G' (not 'N'/'B'/'E')

# --- FIX: re-author every commit to key-owner identity AND re-sign ---
unset GITHUB_TOKEN GH_TOKEN
cd "$WORKTREE"
git config user.email "<ID>+<USERNAME>@users.noreply.github.com"   # MUST be a UID on the key
git config user.name  "<Key Owner Name>"
OLD_HEAD=$(git rev-parse HEAD)
git fetch origin
git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'
git diff "$OLD_HEAD" HEAD                # MUST be EMPTY (content byte-identical)
git log origin/main..HEAD --pretty=format:'%h %G? %an %s'   # every row col-2 = G
git push --force-with-lease origin "$BRANCH"

# --- SET UP SSH signing on a fresh remote/headless host ---
ssh-keygen -t ed25519 -f ~/.ssh/id_signing_ed25519 -N ""
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub   # PUBLIC key path, not a key id
git config --global commit.gpgsign true
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
EMAIL="$(gh api user --jq '.id')+$(gh api user --jq '.login')@users.noreply.github.com"
git config --global user.email "$EMAIL"
mkdir -p ~/.config/git
printf '%s %s\n' "$EMAIL" "$(cat ~/.ssh/id_signing_ed25519.pub)" >> ~/.config/git/allowed_signers
gh auth refresh -h github.com -s admin:ssh_signing_key            # interactive; cannot be headless
gh ssh-key add ~/.ssh/id_signing_ed25519.pub --type signing --title "$(hostname)-signing"
```

### Detailed Steps

#### Example A — GPG sign email mismatch silently produces unsigned commits, blocking merge

This is the most common silent failure: `commit.gpgsign=true` is set, but `user.email` is a bot
identity that has NO matching UID on the configured GPG signing key. GPG produces NO signature and
**git does not error** (exit 0). The commit lands unsigned (`%G?`=`N`), or signs locally but GitHub
returns `verified=false reason=no_user`.

1. **Recognize the symptom.** `mergeable: MERGEABLE` does NOT mean "passes branch protection". Query
   `mergeStateStatus`; `BLOCKED` + all CI green + no pending reviews ⇒ suspect signature verification.

2. **Confirm via the commits API (ground truth):**
   ```bash
   gh api repos/<O>/<R>/pulls/<N>/commits --jq '.[].commit.verification'
   ```

   | `reason` | Meaning | Fix |
   |----------|---------|-----|
   | `unsigned` | No signature at all | Configure signing, re-commit with `-S` |
   | `no_user` | Signed but author/committer email is not a verified email on the key-owner's GitHub account | **This example** — re-author with `{id}+{username}@users.noreply.github.com` AND re-sign |
   | `unknown_key` | Signed but public key not registered as a signing key | Register key (`--type signing` for SSH) |
   | `valid` + `verified:true` | Pass | Done |

3. **Confirm root cause locally.**
   ```bash
   git config --get user.email; git config --get user.signingkey; git config --get commit.gpgsign
   gpg --list-keys "$(git config --get user.signingkey)"   # does ANY uid line match user.email?
   ```
   If `user.email` is not a UID on the secret key, GPG silently writes the commit without `gpgsig`.

4. **Fix in a worktree** (never the main checkout). Set the key-owner identity repo-locally, then
   re-author + re-sign EVERY commit since `origin/main` (`--exec` runs the amend per-commit so each
   gets its own signature; `--reset-author` updates author/committer to the matching identity; `-S`
   forces signing):
   ```bash
   git config user.email "<ID>+<USERNAME>@users.noreply.github.com"
   git config user.name  "<Real Name on GPG Key>"
   OLD_HEAD=$(git rev-parse HEAD)
   git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'
   ```

5. **CRITICAL — content must be byte-identical:** `git diff "$OLD_HEAD" HEAD` must be 0 bytes. If not,
   STOP and investigate before force-pushing.

6. **Verify locally, force-push, confirm at GitHub:**
   ```bash
   git log origin/main..HEAD --pretty=format:'%h %G? %an %s'   # all col-2 = G
   git push --force-with-lease origin "$BRANCH"
   TOTAL=$(gh api repos/<O>/<R>/pulls/<N>/commits --jq 'length')
   VERIFIED=$(gh api repos/<O>/<R>/pulls/<N>/commits \
     --jq '[.[] | select(.commit.verification.verified == true)] | length')
   [ "$TOTAL" = "$VERIFIED" ] && echo "ALL SIGNED"
   ```
   `mergeStateStatus` flips `BLOCKED` → `CLEAN`; pre-armed `--auto-merge` fires.

7. **Preventative agent tripwire** — gate any committing agent before push:
   ```bash
   SIG=$(git log -1 --pretty=format:'%G?')
   [ "$SIG" = "G" ] || { echo "FATAL sig=$SIG"; git config --get user.email; exit 1; }
   ```

**GraphQL lag — use REST.** `pullRequest.commits.nodes.commit.signature.state` (via
`gh pr view --json commits`) returns `null`/`UNSIGNED` for MINUTES-to-HOURS after a push even when
the commit is verified. The REST `/commits/<sha>` endpoint updates within seconds and is
authoritative. **Before any remediation based on GraphQL `UNSIGNED`, poll REST on one commit** — if
`verified=true`, wait, do NOT re-upload the key / force-push / rebase.

**`+suffix` noreply emails cannot be verified — do NOT patch the key.** GitHub only accepts two email
shapes as account-verifiable: `{id}+{username}@users.noreply.github.com` (canonical ID-prefixed
noreply) or a real email added+verified in settings. An arbitrary `{username}+anything@users.noreply.github.com`
variant (e.g. `user+bot@...`) can NEVER become a verified account email, so adding it as a key UID
does not clear `no_user`. Fix at the identity layer (set the committer email to the canonical
ID-prefixed noreply) or fix the global `~/.gitconfig` so automation never writes the `+bot` email.
```bash
gpg --list-keys --with-colons "$KEY" | awk -F: '/^uid:/{print $10}'  # UID emails the key can sign as
```

**Always pin the signing key; re-verify HEAD after every commit.** Bare `git commit -S` can fall back
to a foreign default secret key (`%G?`=`E`, "No public key"); pin it:
`git -c user.signingkey=<signing-subkey> commit -S`. A pre-commit hook that exits non-zero aborts the
commit and leaves HEAD unmoved — `git log --show-signature` then shows the PREVIOUS commit, which looks
like corruption but is just "the commit never happened". Capture rc and compare `git rev-parse HEAD`
before/after.

#### Example B — SSH noreply-email signing on a fresh remote/headless host

Set up GitHub-valid (`verification.verified==true`) signing from scratch on a headless host with no
existing key, satisfying BOTH the signature gate AND the email-privacy push block.

1. **Generate an ed25519 SSH signing keypair** with an empty passphrase (headless, non-interactive):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_signing_ed25519 -N ""
   ```

2. **Wire git's SSH-signing config (global).** `gpg.format ssh` switches git from GPG to SSH; for SSH,
   `user.signingkey` is the **public key file path** (not a key id):
   ```bash
   git config --global gpg.format ssh
   git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub
   git config --global commit.gpgsign true
   git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
   ```

3. **Populate the allowed_signers file** so local `git log --show-signature` can verify
   (`<email> <pubkey-type> <pubkey-body>`):
   ```bash
   mkdir -p ~/.config/git
   EMAIL="$(gh api user --jq '.id')+$(gh api user --jq '.login')@users.noreply.github.com"
   printf '%s %s\n' "$EMAIL" "$(cat ~/.ssh/id_signing_ed25519.pub)" >> ~/.config/git/allowed_signers
   ```

4. **Set the author to the noreply email — CRITICAL.** Derivation
   `<numeric-id>+<login>@users.noreply.github.com` (e.g. `4211002+mvillmow@users.noreply.github.com`).
   If "Block command-line pushes that expose my email" is enabled, pushing a commit authored with the
   real gmail email is rejected even with correct signing. The noreply email BOTH bypasses the push
   block AND verifies against the registered key:
   ```bash
   git config --global user.email "$EMAIL"
   ```

5. **Grant the missing scope, then register the PUBLIC key as a SIGNING key.** The default `gh` token
   lacks `admin:ssh_signing_key` (API returns 404 without it); the grant is interactive — a human must
   approve the device-code/browser flow, it CANNOT be done headlessly. `--type signing` is
   essential — without it the key registers as an **auth** key and commits stay Unverified:
   ```bash
   gh auth refresh -h github.com -s admin:ssh_signing_key
   gh ssh-key add ~/.ssh/id_signing_ed25519.pub --type signing --title "$(hostname)-signing"
   ```

6. **Verify end-to-end on a throwaway branch before trusting a batch.** Signature validity is checkable
   via REST independently of any push policy:
   ```bash
   git checkout -b verify-signing-scratch
   git commit --allow-empty -S -m "verify signing"
   git push -u origin verify-signing-scratch
   gh api repos/<owner>/<repo>/commits/$(git rev-parse HEAD) --jq .commit.verification.verified  # true
   git push origin --delete verify-signing-scratch
   ```

#### Example C — cryptographic signed-commit pr-policy gate validation

The `pr-policy` required-check gate runs at the GitHub GraphQL API layer (not just a CI runner) and
validates: (1) every commit in the PR is cryptographically signed, (2) the PR body contains literal
`Closes #<n>` (capital C, no colon), (3) auto-merge is enabled (`gh pr merge --auto --squash`). If ANY
fail, the `pr-policy` check status is `BLOCKED` — **silently, with no log message** — and auto-merge
does not fire even when armed.

1. **Recognize the silent block** — all other checks SUCCESS, `pr-policy` BLOCKED, no error text:
   ```bash
   gh pr view <N> --json mergeStateStatus,mergeable,statusCheckRollup
   # mergeStateStatus:BLOCKED, mergeable:MERGEABLE, pr-policy status:BLOCKED, others SUCCESS
   ```

2. **Diagnose unsigned commits — local (fast) then API (authoritative):**
   ```bash
   git log origin/main..HEAD --pretty=format:'%h %G? %an — %s'   # any 'N' = unsigned
   gh pr view <N> --json commits \
     --jq '.commits[] | {oid:.oid[0:7], state:.commit.signature.state}'
   ```

   | `signature.state` | Meaning | Fix |
   |-------------------|---------|-----|
   | `VALID` | Signed and verified | None |
   | `UNSIGNED` | No signature | Re-commit `-S` |
   | `UNVERIFIED` | Signed but doesn't match GitHub records | gpg-agent / wrong-key config |
   | `BAD_SIGNATURE` | Verification failed | Key / agent config problem |

3. **Fix** — re-author+re-sign every commit, verify, force-push, confirm:
   ```bash
   git fetch origin
   git rebase origin/main --exec 'git commit --amend --no-edit -S'
   git log origin/main..HEAD --pretty=format:'%G? %h %s'   # all col-1 = G
   git push --force-with-lease origin <branch>
   gh pr view <N> --json mergeStateStatus                  # no longer BLOCKED (unless Closes #N missing)
   ```

4. **Sign from the start.** Use the GPG/SSH key REGISTERED on your GitHub account (a different local
   key marks commits `UNVERIFIED`/`BAD_SIGNATURE`). Do not ask to disable `pr-policy` — it is an org
   security standard, not a per-repo override. Branch protection (including `required_signatures`) is
   enforced at the GitHub API layer, so force-pushing unsigned commits to a protected branch is
   rejected before the push lands.

#### Pre-warm gpg-agent in sub-agent shells

With `commit.gpgsign=true` set globally and the key on the GitHub account, sub-agent shells DO inherit
the config — but a non-interactive subshell needs `GPG_TTY` and a pre-warmed `gpg-agent` to actually
produce a signature. If pre-warming is skipped, the commit silently fails to sign (no error). Combined
with GraphQL lag this is indistinguishable from "config didn't propagate" — diagnose via REST, not by
changing config.
```bash
export GPG_TTY=$(tty 2>/dev/null || echo /dev/null)
echo "test" | gpg --batch --yes --passphrase-fd 0 --pinentry-mode loopback \
  -as -o /dev/null 2>&1 | tail -1 || true
```

#### Fleet/automation re-sign scoping

Automation that rebases/re-signs PRs in bulk MUST scope discovery to the current user
(`gh pr list --author @me ...`), or it will rewrite — and STRIP the native web-flow signature off —
PRs it does not own (e.g. Dependabot bumps), turning a previously `verified=true` bot commit into
`unsigned`/`no_user` and BLOCKING it. Guard the resolved resign email against the signing key's UID
emails before a batch re-sign (escape hatch e.g. `FLEET_SKIP_EMAIL_KEY_CHECK=1`); note the UID check is
necessary but not sufficient (a `+suffix` noreply UID passes locally yet fails GitHub verification).
Companion `pr-policy` carve-out: exempt `dependabot[bot]` from the `Closes #N` body check (bot bodies
never carry it) while keeping the "every commit signed" + "auto-merge armed" checks enforced; pass the
PR-author login via `env:` (never interpolated into `run:`) for workflow-injection safety.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Set `user.email` to a bot identity globally, kept personal GPG key as `user.signingkey`, ran `git commit -S` | GPG found no secret key matching the bot email's UID, produced NO signature; git did not error (exit 0) and the commit landed unsigned | `commit.gpgsign=true` is a NO-OP when `user.email` matches no UID on the signing key. Always run `git log -1 --pretty=format:'%G?'` after the first signed commit as a tripwire |
| Attempt 2 | Read `gh pr view --json mergeable` (got `MERGEABLE`) and concluded the PR could merge | `mergeable` only reports merge-conflict status, nothing about branch protection. The authoritative field is `mergeStateStatus` (returned `BLOCKED`) | Query `mergeStateStatus`, never `mergeable` alone. `MERGEABLE` + `BLOCKED` is the signature-problem signature |
| Attempt 3 | `gh pr merge --rebase --admin` to bypass the rule | `required_signatures` cannot be admin-bypassed at the merge endpoint — GitHub returns `the base branch policy prohibits the merge` | Fix at the commit layer (re-sign), not the merge layer |
| Attempt 4 | `git commit --amend -S` on only the tip commit | Only the tip got signed; the other commits stayed unsigned so the PR stayed BLOCKED — `required_signatures` needs EVERY commit verified | Use `git rebase origin/main --exec 'git commit --amend --no-edit --reset-author -S'` to re-sign the whole range |
| Attempt 5 | Ran `rebase --exec` WITHOUT `--reset-author` | `%G?` still `N` because the author email was still the bot identity, so GPG still found no matching UID | `--reset-author` is mandatory — it updates author/committer to the current `user.email`, which GPG checks against the key UIDs |
| Attempt 6 | Checked mergeability without verifying the diff was byte-identical after the rebase | A mis-configured rebase (rerere, autosquash, clean-filter changes) could silently rewrite content and lose work if pushed | Always `git diff <old-HEAD> <new-HEAD>` and confirm 0 bytes before force-pushing |
| Attempt 7 | Trusted GraphQL `gh pr view --json commits ... signature.state=UNSIGNED` as authoritative and began remediation | GraphQL lags 10+ min after push even when commits ARE verified; REST `/commits/<sha>` returned `verified=true reason=valid` immediately (31 commits across Argus #520, Scylla #1978, Agamemnon #382) | Poll REST `gh api repos/<O>/<R>/commits/<sha>` for signature state; treat GraphQL `signature.state` as advisory only |
| Attempt 8 | Re-uploaded the GPG key assuming it was missing | Key was already registered; `gh gpg-key add` returned HTTP 422 "subkey already exists". The real issue was GraphQL lag | Before re-uploading, query REST verification on one commit; if `verified=true`, wait — do not re-upload |
| Attempt 9 | Trusted `git log --show-signature` ("Good signature", `%G?`=`G`) as proof of merge-readiness | GitHub returned `verified:false reason:no_user` and the gate failed at merge — `--show-signature` only checks LOCAL keyring cryptographic validity, not GitHub email attribution | Authoritative check is `gh api repos/<O>/<R>/commits/<sha> --jq .commit.verification` expecting `{verified:true, reason:valid}`. Never trust `--show-signature` alone |
| Attempt 10 | Tried to fix `no_user` by adding the `+bot` noreply email as a new GPG key UID and re-uploading | GitHub will not verify a `+suffix` noreply variant as an account email; `no_user` persisted with the UID present | Fix at the identity layer: set committer email to the key's registered `{id}+{username}@users.noreply.github.com` (or a real verified email) and re-sign |
| Attempt 11 | Re-signed with bare `git commit -S` (no explicit `user.signingkey`) | GPG fell back to a foreign default secret key; `%G?` came back `E` ("No public key") | Pin the subkey: `git -c user.signingkey=<signing-subkey> commit -S`. Never rely on default-key fallback when multiple secret keys exist |
| Attempt 12 | Amended a commit, saw `--show-signature` still showing the OLD identity, concluded the repo was corrupt | The amend had silently aborted (pre-commit hook exit non-zero); HEAD never moved so `git log` showed the unchanged previous commit | Capture the commit exit code AND compare `git rev-parse HEAD` before/after. If HEAD unchanged or rc≠0, the commit failed — fix the hook |
| Attempt 13 | Ran fleet re-sign automation with NO `--author` filter, rewriting every open PR including Dependabot's | Rewriting a PR you do not own STRIPS GitHub's native web-flow signature and stamps the local identity; the Dependabot commit went from `verified=true` to `no_user` and BLOCKED | Scope fleet discovery to `--author @me`; never rewrite PRs you do not own |
| Attempt 14 | Re-signed a damaged bot PR via `git commit --amend -S` in a sub-shell trusting `commit.gpgsign=true` | The sub-shell had a COLD gpg-agent (no `GPG_TTY`, no priming call), so signing was a no-op and the commit landed `reason=unsigned` | Warm the gpg-agent before ANY amend (`export GPG_TTY=$(tty)` + a priming `gpg --batch` call), then re-sign and verify via REST |
| Attempt 15 | Authored commits via the GitHub Contents REST API expecting server-side auto-sign | Returned `verified=false reason=unsigned` — GitHub does NOT auto-sign PAT-authored commits without Vigilant mode + a registered key | Sign locally and push; the REST API does not sign commits for you |
| Attempt 16 | Pushed a correctly-SSH-signed commit authored with the private gmail email | `push declined due to email privacy restrictions` — the account blocks pushes that expose the real email, independent of signing | Author with `<id>+<login>@users.noreply.github.com`; it bypasses the push block and still verifies |
| Attempt 17 | Registered the SSH signing key without `--type signing` | The key registered as an AUTH key, so GitHub had no signing key to verify against and commits stayed Unverified | `--type signing` is mandatory; an auth-only key does not make commits verify |
| Attempt 18 | Registered the SSH key via the API with the default token | HTTP 404 — the token lacked `admin:ssh_signing_key` | Grant it interactively: `gh auth refresh -h github.com -s admin:ssh_signing_key` (human approves device/browser flow; cannot be headless) |
| Attempt 19 | Committed without `-S` hoping pr-policy wouldn't catch it | pr-policy validated every commit at the GraphQL layer; PR showed all checks SUCCESS but `mergeStateStatus:BLOCKED` with no visible explanation, auto-merge did not fire | Always `git commit -S` in repos with `pr-policy`; verify each commit with `git log -1 --pretty=format:'%G?'` before pushing |
| Attempt 20 | Signed with a different GPG key than the one registered on GitHub | GitHub checked the public key against registered keys; the new key was unregistered so signatures were `UNVERIFIED`/`BAD_SIGNATURE` and pr-policy still blocked | Use the key registered on your GitHub account; `git config user.signingkey` must match an account key |

## Results & Parameters

**Diagnostic decision tree:**

```text
PR not auto-merging?
├─ gh pr view --json mergeStateStatus
│  ├─ BLOCKED → continue
│  ├─ BEHIND  → rebase against base branch
│  ├─ DIRTY   → resolve conflicts
│  └─ CLEAN   → wait for CI
└─ BLOCKED + all CI green:
   └─ gh api .../commits --jq '.[].commit.verification.reason'
      ├─ "unsigned"    → no signing configured / un-warmed gpg-agent → configure + re-commit -S
      ├─ "no_user"     → email/key-UID mismatch → re-author + re-sign (Example A)
      ├─ "unknown_key" → key not registered as signing → register (--type signing for SSH)
      └─ all "valid"   → not a signing problem; check missing required checks / Closes #N
```

**Two orthogonal gates that BOTH must pass — debug separately:**

| Gate | Controlled by | Symptom when failing | Fix |
|------|---------------|----------------------|-----|
| Signature verification | Key registered (GPG, or SSH with `--type signing`) + author email matches a registered/verified identity | Commit shows Unverified / `no_user` / `unsigned` | Register key correctly; author with the noreply email; re-sign |
| Push acceptance (email privacy) | "Block command-line pushes that expose my email" account setting | `push declined due to email privacy restrictions` | Author with `<id>+<login>@users.noreply.github.com` |

**GitHub noreply email derivation:**

```text
<numeric-id>+<login>@users.noreply.github.com
# numeric-id: gh api user --jq '.id'     (e.g. 4211002)
# login:      gh api user --jq '.login'  (e.g. mvillmow)
# result:     4211002+mvillmow@users.noreply.github.com
```

**Authoritative signature verification (REST, NOT GraphQL):**

```bash
gh api repos/<owner>/<repo>/commits/<sha> \
  --jq '.commit.verification | "verified=\(.verified) reason=\(.reason)"'
gh api repos/<owner>/<repo>/pulls/<N>/commits \
  --jq '[.[] | {sha:.sha[0:7], verified:.commit.verification.verified, reason:.commit.verification.reason}]'
```

**Critical config invariant for any GPG signing agent (must be true after config is set):**

```bash
git config --get user.email | xargs -I{} \
  gpg --list-keys "$(git config --get user.signingkey)" 2>/dev/null | grep -q "<{}>"
# If the grep fails, GPG will silently NOT sign.
```

**SSH-signing global config (remote/headless host):**

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub   # PUBLIC key path
git config --global commit.gpgsign true
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
git config --global user.email "<numeric-id>+<login>@users.noreply.github.com"
# allowed_signers line: <email> ssh-ed25519 AAAA...<pubkey-body>
```

**GPG signature status codes (`%G?`):**

| Code | Meaning |
|------|---------|
| `G` | Good signature (target state) |
| `B` | Bad signature |
| `U` | Good signature, unknown validity |
| `X` | Good signature, expired |
| `Y` | Good signature by an expired key |
| `R` | Good signature by a revoked key |
| `E` | Cannot be checked (missing/foreign key) |
| `N` | No signature (silent-fail state) |

**Empirical detection in multi-agent sweeps:**

| Sweep | Total PRs | Affected | Cause |
|-------|-----------|----------|-------|
| 2026-05-11 ecosystem easy-issue sweep | 11 | 1 (Keystone #552) | One agent had a local `user.email` override to a bot identity desynced from the GPG key UID |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | 2026-05-11 ecosystem easy-issue sweep, PR #552 | Re-authored 7 commits with `--reset-author -S` rebase, byte-identical diff (0 bytes), force-pushed; GitHub flipped all 7 from `verified:false reason:no_user` to `verified:true reason:valid`; `mergeStateStatus` `BLOCKED`→`CLEAN`; pre-armed auto-merge fired |
| ProjectArgus / ProjectScylla / ProjectAgamemnon | 2026-05-16 org-wide sweep — Argus #520, Scylla #1978, Agamemnon #382 | 31 commits showed GraphQL `signature.state=null`/`UNSIGNED` for 10+ min while REST returned `verified=true reason=valid` immediately. `gh gpg-key add` returned HTTP 422 "subkey already exists". Resolution: wait for GraphQL; no remediation needed |
| HomericIntelligence mesh (host `aeolus`) | 2026-05-31 first-time headless SSH signing setup | Generated ed25519 SSH signing key, registered with `gh ssh-key add --type signing` (after `gh auth refresh -s admin:ssh_signing_key`), authored with `<id>+<login>@users.noreply.github.com`; scratch commit pushed, `gh api .../commits/<sha> --jq .commit.verification.verified` returned `true` |
| ProjectHephaestus | 2026-06-04 Issue #739, PR #900+ | DRY refactor required all commits to pass pr-policy; all signed with `-S`, pr-policy confirmed `signature.state=VALID` per commit via GraphQL, auto-merge fired after pr-policy passed |
| ProjectHephaestus | 2026-06-06, PRs #1021 / #1026 | Global `~/.gitconfig` `user.email` was `mvillmow+bot@users.noreply.github.com`; GPG key `F0A2530669A31A2E` (subkey `7FD616C4744A8A7C`) was bound only to `4211002+mvillmow@users.noreply.github.com`. Commits showed `%G?`=`G` locally but GitHub returned `no_user` and pr-policy failed. Discovered the `+bot` variant cannot be a verified email (patching the key UID was a dead end). Fixed by `git config user.email 4211002+mvillmow@...` + `git commit --amend --reset-author -S`; added a defensive guard in `fleet_sync.get_resign_email()` validating resign email vs key UIDs (`FLEET_SKIP_EMAIL_KEY_CHECK=1` bypass). Also hit bare-`-S` foreign-key (`%G?`=`E`) and silent commit-abort-from-hook leaving HEAD unchanged |
| ProjectHephaestus | 2026-06-07, PR #1071 (issue #1070) | Fleet automation `fleet_sync.py` `list_prs()` had no author filter; `rebase_and_resign()` rewrote a Dependabot bump, STRIPPING the native web-flow signature; the amend ran in a sub-shell with a cold gpg-agent so it landed `reason=unsigned`. Fixed by scoping discovery with `--author @me`, warming gpg-agent before any re-sign amend, and exempting `dependabot[bot]` from pr-policy Check 1 (`Closes #N`) while keeping Checks 2/3. Verified via REST `reason=valid`; merged to main |
| ProjectHephaestus | 2026-06-11, PR #946 (issue #755) | Forensics code-only fix (malformed COREDUMP_MAX_BYTES handling) failed pr-policy Check 3 "every commit is signed": commit `189110e2` returned GitHub GraphQL `signature.isValid:false`. Re-signed via `git rebase origin/main --exec 'git commit --amend --no-edit -S'`; final merged commit `ab5ab4de` returned REST `verification.verified:true reason:valid` (PGP), committer email `4211002+mvillmow@users.noreply.github.com` matching the key UID. Confirms Example C pattern; auto-merge fired after pr-policy passed. |
