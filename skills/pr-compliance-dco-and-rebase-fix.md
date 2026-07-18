---
name: pr-compliance-dco-and-rebase-fix
description: "Repair a failing Hephaestus pr-policy gate by rewriting every offending PR commit with a verified cryptographic signature, DCO trailer, and Conventional Commit subject. Use when: (1) pr-policy reports unsigned, invalidly signed, or DCO-missing commits, (2) one or more historical PR commits have non-conventional subjects, (3) a final compliance commit would leave invalid commits in the PR range, or (4) a rebase requires conflict resolution."
category: ci-cd
date: 2026-07-18
version: "1.1.0"
user-invocable: false
verification: unverified
history: pr-compliance-dco-and-rebase-fix.history
tags: [dco-signoff, pr-policy, merge-conflict, ci-fix, commit-signing, conventional-commits, rebase]
---

# PR Policy: Rewrite and Re-sign the Whole PR Range

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-18 |
| **Objective** | Repair a PR-policy failure without leaving earlier non-compliant commits hidden beneath a later fix commit |
| **Outcome** | Procedure expanded from a last-commit DCO fix to a whole-range rewrite; the PR #2280 application remains unverified until its new `pr-policy` check succeeds |
| **Verification** | unverified for the PR #2280 extension; v1.0.0's last-commit/rebase procedure was previously verified in CI |
| **History** | [changelog](./pr-compliance-dco-and-rebase-fix.history) |
| **Context** | HomericIntelligence/Hephaestus PR #2280, whose required `pr-policy` check failed at 2026-07-18T17:01:14Z |

> **Warning:** The procedure below is the exact remediation directed by the live
> `pr-policy` workflow, but its PR #2280 application has not yet passed CI.
> The GitHub `pr-policy` result, not a local approximation, is the final verdict.

## When to Use

- The required `pr-policy` check fails and the workflow identifies any unsigned or invalidly signed commit.
- One or more commits lack a well-formed `Signed-off-by: Name <email>` trailer.
- A historical commit subject, such as `f511311c` on PR #2280, is not a Conventional Commit.
- A PR has several invalid commits: adding one final signed commit would leave the earlier commits in the PR range non-compliant.
- A range rewrite must be rebased onto the current target branch and safely force-pushed.

## Verified Workflow

### Quick Reference

```bash
# Treat the required CI check as the source of truth.
PR=2280
REPO=HomericIntelligence/Hephaestus
gh pr checks "$PR" --repo "$REPO" --required

# Fetch the PR's current base and rewrite *the complete PR range*.
git fetch origin main
BASE=origin/main
git rebase -i --rebase-merges --exec 'git commit --amend --no-edit -S -s' "$BASE"

# In the interactive todo, change each bad-subject commit from `pick` to `reword`.
# Give it an accurate allowed subject, for example: fix(scope): concise description
# Resolve conflicts, then safely publish the rewritten range.
git push --force-with-lease origin HEAD

# A local preflight is useful, but only the refreshed GitHub pr-policy check is final.
gh pr checks "$PR" --repo "$REPO" --required
```

### Detailed Steps

1. Read the current required check before changing history. Do not infer compliance from a newly created final commit:

   ```bash
   gh pr checks "$PR" --repo "$REPO" --required
   gh pr view "$PR" --repo "$REPO" --json headRefOid,statusCheckRollup \
     --jq '{headRefOid, prPolicy: [.statusCheckRollup[] | select(.name == "pr-policy")]}'
   ```

   On PR #2280, `pr-policy` failed while the rest of the required run was still
   pending. The failure was therefore a merge blocker, not a harmless advisory.

2. Read the CI implementation to identify what it enforces. The required
   `.github/workflows/_required.yml` job checks, independently and for **every
   PR commit**:

   - GitHub GraphQL `commit.signature.isValid == true` (cryptographic signature),
   - an allowed Conventional Commit subject,
   - a valid DCO `Signed-off-by: Name <email>` trailer, and
   - the separate PR-body `Closes #N` requirement.

   `git commit -S` and `git commit -s` are orthogonal. `-S` makes a cryptographic
   signature; `-s` adds the DCO trailer. Neither one repairs earlier commits.

3. Capture the immutable current range, fetch the target branch, and inspect all
   commits before rewriting. Keep the hash list in the incident record; never
   guess from `HEAD~1`.

   ```bash
   git fetch origin main
   BASE=$(git merge-base origin/main HEAD)
   git log --reverse --format='%H%n%s%n%B%n---' "$BASE..HEAD"
   ```

   For PR #2280 the failed CI evidence identified missing DCO trailers on
   `2f4a24da`, `c68df607`, `f133622c`, `a66c25ee`, `5993d392`, `ecf25567`, and
   `698fa09e`; `f511311c` also needed a Conventional Commit subject. Re-check
   the current check output and hashes immediately before rewriting because a
   force-push changes every commit ID.

4. Rewrite the entire offending range. Start interactive rebase at the current
   base, leave the topology intact with `--rebase-merges` when applicable, and
   add an `exec` that amends **each** rewritten commit with both required forms
   of attestation:

   ```bash
   git rebase -i --rebase-merges \
     --exec 'git commit --amend --no-edit -S -s' "$BASE"
   ```

   In the generated todo, change every non-conventional commit from `pick` to
   `reword`. At the stop, choose an accurate subject with an allowed type:

   ```text
   fix(scope): concise, accurate description
   ```

   Do not invent a scope or use a generic compliance subject; inspect that
   commit's diff before rewording it. The allowed types are `feat`, `fix`,
   `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `style`, and
   `revert` (optional non-empty scope; a non-empty description is required).

5. Resolve rebase conflicts manually, preserving both the target branch and PR
   changes. Then stage and continue:

   ```bash
   git status
   git add <resolved-path>
   GIT_EDITOR=true git rebase --continue
   ```

   If an already-landed patch becomes empty, inspect it before using
   `git rebase --skip`; do not skip a commit just to make the rebase finish.

6. Run a local preflight across the final range. This detects malformed subjects,
   missing trailers, and locally unverifiable signatures early, but it cannot
   prove GitHub's `signature.isValid` result:

   ```bash
   set -euo pipefail
   git log --format=%s "$BASE..HEAD" | python3 scripts/check_conventional_commit.py -
   git log -z --format=%B "$BASE..HEAD" | python3 scripts/check_dco_signoff.py -
   git rev-list "$BASE..HEAD" | while read -r oid; do
     git verify-commit "$oid"
   done
   ```

7. Publish the rewritten history with a lease and wait for CI. A successful push
   is not evidence of compliance:

   ```bash
   git push --force-with-lease origin HEAD
   gh pr checks "$PR" --repo "$REPO" --required --watch
   ```

   The remediation is verified-ci only when the new-head `pr-policy` check is
   `pass` and all other required checks are complete and passing. If it still
   fails, read the **new** check output and repeat from the actual current range.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add one final signed commit | Added a compliant follow-up without rewriting previous commits | `pr-policy` evaluates every commit in the PR range, so earlier invalid commits still fail | Rewrite every offending commit; a final fix commit cannot mask history-policy violations |
| Use `git commit -S` only | Added a cryptographic signature but no DCO trailer | The DCO checker validates a separate text trailer on every message | Re-sign with both flags: `git commit --amend --no-edit -S -s` |
| Add DCO only to `HEAD` | Used `git commit --amend -s` on the newest commit | PR #2280 had seven earlier commits missing sign-offs | Rebase the entire `$BASE..HEAD` range with an amend exec, then verify the final range |
| Treat local signature verification as final | Used `git verify-commit` as proof of GitHub acceptance | CI uses GitHub's GraphQL `signature.isValid`, which can differ from local trust configuration | Use local checks as preflight and the new-head required `pr-policy` result as the source of truth |
| Leave an old non-conventional subject untouched | Re-signed commits but did not reword `f511311c` | Signatures and DCO do not change the commit subject | Mark each bad subject `reword` during interactive rebase and validate subjects across the final range |
| Force-push without a lease | Used `git push --force` after rewriting history | It can overwrite unseen remote work | Use `git push --force-with-lease`; fetch and re-evaluate if the lease is stale |

## Results & Parameters

```text
Required PR-policy contract (non-Dependabot PRs):
  1. PR body has a standalone `Closes #N` line.
  2. Every PR commit has GitHub `signature.isValid == true`.
  3. Every PR commit subject is a Conventional Commit.
  4. Every PR commit has `Signed-off-by: Name <email>`.

PR #2280 initial evidence (2026-07-18):
  - required `pr-policy`: fail
  - DCO-missing commits: 2f4a24da, c68df607, f133622c, a66c25ee,
    5993d392, ecf25567, 698fa09e
  - non-conventional subject: f511311c
  - validation status: unverified until the rewritten branch's new `pr-policy` run passes
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1638, issue #1412 | v1.0.0 last-commit DCO/signature + rebase workflow passed all CI gates (verified-ci) |
| ProjectHephaestus | PR #2280 | Expanded whole-range remediation derived from the live failed required `pr-policy` check; rewrite and CI confirmation pending (unverified) |

## References

- `.github/workflows/_required.yml` — authoritative four-part `pr-policy` implementation
- `scripts/check_conventional_commit.py` — accepted commit types and subject grammar
- `scripts/check_dco_signoff.py` — exact DCO trailer requirements and CI-provided re-sign command
- `CONTRIBUTING.md` — Developer Certificate of Origin requirement
