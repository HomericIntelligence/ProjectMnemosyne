---
name: gh-review-pr
description: "Comprehensively review a GitHub pull request, post inline review comments, and handle self-authored PR review limitations. Use when: (1) asked to review a PR, (2) adding review comments with gh api, (3) a strict review needs Go/No-Go output, (4) GitHub rejects request-changes on the authenticated user's own PR."
category: tooling
date: 2026-05-13
version: "1.1.0"
user-invocable: false
verification: verified-local
history: gh-review-pr.history
tags: [github, pull-request, review, gh-cli, review-comments]
---

# GitHub PR Review Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-13 |
| **Objective** | Evaluate PR quality, provide structured findings, and post review comments through GitHub. |
| **Outcome** | Operational. A self-authored PR cannot receive a `REQUEST_CHANGES` review from the same authenticated user, but a `COMMENT` review can still carry inline comments plus an explicit No-Go verdict in the body. |
| **Verification** | verified-local. Executed against Eval360-V2 PR #268 with live GitHub API calls; CI validation is not applicable to this operational workflow. |
| **History** | [changelog](./gh-review-pr.history) |

## When to Use

- Reviewing a PR before merge.
- Evaluating code quality, tests, CI status, documentation, or security risk.
- Posting inline review comments with exact file and line anchors.
- Adding per-file grading and a Go/No-Go review summary.
- Reviewing a PR authored by the authenticated GitHub user, where `REQUEST_CHANGES` may be rejected by GitHub.

## Verified Workflow

Verified locally only - CI validation is pending/not applicable because this is a GitHub CLI/API operating procedure.

### Quick Reference

```bash
# Inspect PR context.
gh pr view <pr> --repo OWNER/REPO --json author,baseRefName,headRefName,headRefOid,state,url
gh pr diff <pr> --repo OWNER/REPO --patch
gh pr checks <pr> --repo OWNER/REPO

# Confirm whether this is a self-authored PR.
gh api user --jq .login
gh pr view <pr> --repo OWNER/REPO --json author,headRefOid --jq '{author:.author.login, head:.headRefOid}'

# Submit a review with inline comments.
# Use event=COMMENT when the authenticated user is also the PR author.
gh api -X POST repos/OWNER/REPO/pulls/<pr>/reviews --input review.json

# Verify inline comments landed on the review.
gh api repos/OWNER/REPO/pulls/<pr>/comments \
  --jq '.[] | select(.pull_request_review_id==<review_id>) | {path,line,body,url:.html_url}'
```

### Detailed Steps

1. Gather the PR metadata, diff, checks, and existing review state. Prefer `gh pr diff`; if it fails transiently and the branch is checked out locally, use `git diff <base>...HEAD` as the evidence source.

2. Identify the authenticated account and PR author before choosing the review event:

   ```bash
   gh api user --jq .login
   gh pr view <pr> --repo OWNER/REPO --json author,headRefOid
   ```

3. Write the review body with findings first. For strict reviews, include per-file grades and an explicit Go/No-Go verdict in the summary.

4. Choose the review event:

   - Use `REQUEST_CHANGES` only when reviewing someone else's PR and the findings block merge.
   - Use `COMMENT` when the authenticated user owns the PR. GitHub rejects self-request-changes reviews with HTTP 422.
   - Use `APPROVE` only when the review is genuinely approving and the account is allowed to approve the PR.

5. Submit inline comments and the summary in one review payload:

   ```json
   {
     "commit_id": "<headRefOid>",
     "event": "COMMENT",
     "body": "## Review Summary\n\nPer-file grading...\n\nGo/No-Go: **NO-GO**",
     "comments": [
       {
         "path": "scripts/example.sh",
         "line": 109,
         "side": "RIGHT",
         "body": "[major] Explain the specific blocking issue and requested fix."
       }
     ]
   }
   ```

   ```bash
   gh api -X POST repos/OWNER/REPO/pulls/<pr>/reviews --input review.json
   ```

6. Verify the posted review and inline comments:

   ```bash
   gh api repos/OWNER/REPO/pulls/<pr>/comments \
     --jq '.[] | select(.pull_request_review_id==<review_id>) | {path,line,body,url:.html_url}'
   ```

## Review Checklist

- Code follows repository standards and local contributor instructions.
- Changed behavior is covered by tests proportional to risk.
- CI status is understood and any unavailable checks are called out.
- Security and destructive-operation risks are explicitly reviewed.
- Documentation updates match the user-facing behavior.
- Inline comments are anchored to changed lines and include severity.
- The summary includes the merge verdict: Approve, Comment, Request Changes, Go, or No-Go.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Self-authored request-changes review | Submitted `gh api -X POST repos/OWNER/REPO/pulls/<pr>/reviews` with `"event": "REQUEST_CHANGES"` while authenticated as the PR author | GitHub returned HTTP 422: `Review Can not request changes on your own pull request` | Detect self-authored PRs before posting. Use `"event": "COMMENT"` and put the strict No-Go verdict in the review body. |
| PR diff via GitHub during transient network issue | Ran `gh pr diff <pr> --patch` | The API call failed with a connection error to `api.github.com` | If the PR branch is checked out locally, use `git diff <base>...HEAD` for evidence, then still use GitHub API for posting once connectivity returns. |

## Results & Parameters

Observed parameters from the verified session:

| Field | Value |
|-------|-------|
| Project | Eval360-V2 |
| PR | #268 |
| Authenticated user | `mvillmow` |
| PR author | `mvillmow` |
| Head commit | `0432fe73a993208f6b38ec8aad39331f7b5afe08` |
| Rejected event | `REQUEST_CHANGES` |
| Working event | `COMMENT` |
| Review ID | `4284354764` |
| Review verdict in body | `NO-GO` |
| Inline anchors | `scripts/tools/rebuild_vllm_serving_env.sh:109`, `README.md:108` |

For strict reviews, use the summary body to preserve enforcement semantics when GitHub permissions prevent a formal request-changes review:

```markdown
## Strict Review Summary

Per-file grading:
- `README.md`: B- (82/100)
- `scripts/tools/rebuild_vllm_serving_env.sh`: C (74/100)

Go/No-Go: **NO-GO** for merge under strict review.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Eval360-V2 | PR #268 strict review posting | Self-authored PR rejected `REQUEST_CHANGES`; `COMMENT` review successfully posted summary and inline comments. |
