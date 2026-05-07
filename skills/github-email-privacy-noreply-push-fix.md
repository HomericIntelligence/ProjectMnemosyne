---
name: github-email-privacy-noreply-push-fix
description: "Fix GitHub push rejections caused by email-privacy settings when an agent commits with the user's real email. Use when: (1) a push is rejected with 'push declined due to email privacy restrictions', (2) dispatching sub-agents that will commit and push on the user's behalf, (3) configuring orchestrator/swarm prompts that need to override git author email."
category: tooling
date: 2026-05-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - push
  - email-privacy
  - noreply
  - agent-dispatch
  - swarm
  - commit
---

# GitHub Email Privacy: Use Noreply Form for Agent Pushes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-07 |
| **Objective** | Prevent GitHub from rejecting pushes when an orchestrator or sub-agent commits on behalf of a user whose GitHub account has email-privacy enabled |
| **Outcome** | Successful — overriding `user.email` to the GitHub noreply form (`<USER_ID>+<USERNAME>@users.noreply.github.com`) and amending the commit lets the push succeed |
| **Verification** | verified-local |

## When to Use

- A `git push` is rejected with `push declined due to email privacy restrictions`
- The remote message references `https://github.com/settings/emails`
- You are about to dispatch a sub-agent (Myrmidon swarm worker, code-review fixer, etc.) that will commit and push on the user's behalf
- You are writing or editing an orchestrator prompt template that controls agent commit author identity
- Local commits work fine but the first push from a fresh agent dispatch fails

## Verified Workflow

### Quick Reference

```bash
# 1. Discover the GitHub user ID once (cache for the session)
USER_ID=$(gh api users/<USERNAME> --jq .id)
NOREPLY="${USER_ID}+<USERNAME>@users.noreply.github.com"

# 2. Re-author the offending commit with the noreply email
git -c user.email="$NOREPLY" \
    -c user.name="<Display Name>" \
    commit --amend --reset-author --no-edit

# 3. Push (force-with-lease because we amended)
git push --force-with-lease origin HEAD:<branch>
```

### Detailed Steps

1. Confirm the failure mode. The rejected push prints a message that looks like:
   ```text
   remote: You can make your email public or disable this protection by visiting:
   remote: https://github.com/settings/emails
   To https://github.com/HomericIntelligence/<repo>.git
    ! [remote rejected] HEAD -> <branch> (push declined due to email privacy restrictions)
   error: failed to push some refs
   ```
   The `email privacy restrictions` phrase is the unique signal — do not retry naively.

2. Look up the user's numeric GitHub ID. Two reliable sources:
   ```bash
   # Preferred: the GitHub API
   gh api users/<USERNAME> --jq .id

   # Fallback: any prior squash-merged commit on the repo's default branch
   git log --pretty='%aN <%aE>' main | grep noreply | head -1
   ```
   Record the result as `<USER_ID>` and build the noreply email:
   `<USER_ID>+<USERNAME>@users.noreply.github.com`

3. Re-author the rejected commit using the per-invocation `-c` flags so the
   change is local to this commit (does **not** mutate the user's global git
   config):
   ```bash
   git -c user.email="<USER_ID>+<USERNAME>@users.noreply.github.com" \
       -c user.name="<Display Name>" \
       commit --amend --reset-author --no-edit
   ```
   `--reset-author` is required — without it, `--amend` keeps the original
   author identity even though the committer changes.

4. Push with `--force-with-lease` because the SHA changed:
   ```bash
   git push --force-with-lease origin HEAD:<branch>
   ```

5. When **dispatching sub-agents**, embed the email override into the prompt
   so the agent uses the right identity from its first commit and never
   needs to amend:
   ```text
   Use email `<USER_ID>+<USERNAME>@users.noreply.github.com` for all git
   commits (the GitHub noreply form is required by the user's email-privacy
   settings). Set both author name and email when staging commits.
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `git push` with the user's real email (e.g. `villmow.products@gmail.com`) inherited from local git config | GitHub's email-privacy setting on the user's account rejects any push whose author email is the user's real address | Local commits to private repos succeed with the real email, so agents never observe the failure until they push. Always probe identity before dispatch. |
| 2 | Retry the same push without changes after the rejection | Server-side check is deterministic — same email, same rejection | Email-privacy is not a transient error; do not retry without re-authoring. |
| 3 | `git commit --amend --no-edit` (without `--reset-author`) after changing the email | Amend kept the original author identity; only the committer changed, so the push was rejected again | `--reset-author` is mandatory when fixing the author email on an existing commit. |
| 4 | Adding the noreply email to a sub-agent's prompt without the numeric `<USER_ID>` prefix (e.g. `mvillmow@users.noreply.github.com`) | GitHub rejects noreply pushes that omit the user-ID prefix because they are ambiguous and not bound to a verified account | Always include `<USER_ID>+` — the numeric ID is what proves account ownership. |

## Results & Parameters

**Verified evidence:** Observed in 2026-05-07 Myrmidons session when the
orchestrator manually fixed PR #481's lint issue:

- First push attempt with `villmow.products@gmail.com` → rejected with
  `push declined due to email privacy restrictions`
- Second push attempt with `4211002+mvillmow@users.noreply.github.com`
  → succeeded; PR updated cleanly

**Copy-paste prompt fragment for orchestrators / swarm dispatchers:**

```text
When you commit, use:

  git -c user.email="<USER_ID>+<USERNAME>@users.noreply.github.com" \
      -c user.name="<Display Name>" \
      commit ...

The GitHub noreply form is required by the user's email-privacy settings —
pushing with the real email will be rejected by the remote.
```

**Operator checklist (one-time per repo/user pair):**

| Step | Command | Expected output |
|------|---------|-----------------|
| Resolve USER_ID | `gh api users/<USERNAME> --jq .id` | Numeric ID, e.g. `4211002` |
| Build noreply | `echo "${USER_ID}+<USERNAME>@users.noreply.github.com"` | `4211002+mvillmow@users.noreply.github.com` |
| Smoke-test push | `git -c user.email="$NOREPLY" commit --amend --reset-author --no-edit && git push --force-with-lease` | Push accepted; PR head SHA updates |

**Why agents fail without this:** Sub-agents inherit `user.email` from
git config. Some local configs hold the real email (because local commits to
private repos work fine that way) but GitHub's email-privacy setting rejects
pushes from that email. Agents that don't override the email field will hit
this every time they try to push.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Myrmidons | 2026-05-07 orchestrator session fixing PR #481 lint failure | First push rejected with real email; second push with `4211002+mvillmow@users.noreply.github.com` succeeded |
