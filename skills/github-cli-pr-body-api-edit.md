---
name: github-cli-pr-body-api-edit
description: "Update a GitHub PR body from automation when gh pr edit --body-file fails on missing read:project scope and gh auth refresh cannot complete headlessly. Use when: (1) gh pr edit only needs to change the PR body but reports missing read:project, (2) gh auth refresh starts a browser or device-code flow, (3) existing repo auth can still call gh api."
category: tooling
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github-cli, gh-api, pull-request, pr-body, auth-scope, read-project, automation]
---

# GitHub CLI PR Body API Edit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Update a GitHub pull request body from Codex automation when `gh pr edit --body-file` fails because the token lacks `read:project` and interactive scope refresh is not available |
| **Outcome** | Successful: the PR body was updated through the lower-level GitHub REST API `PATCH /repos/{owner}/{repo}/pulls/{pull_number}` path |
| **Verification** | verified-local |

## When to Use

- `gh pr edit <PR_NUMBER> --body-file <BODY_FILE>` fails with `error: your authentication token is missing required scopes [read:project]`.
- You only need to replace the PR body, not change projects, milestones, labels, reviewers, or other metadata.
- `gh auth refresh -s read:project` is not automation-safe because it requires `--hostname` or starts an interactive browser/device-code flow.
- Existing `gh` repo authentication can still perform `gh api` calls against the repository.

## Verified Workflow

### Quick Reference

```bash
# Normal path first.
gh pr edit <PR_NUMBER> --body-file <BODY_FILE>

# Fallback when gh pr edit fails on missing read:project and auth refresh is interactive.
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER> -X PATCH -F body=@<BODY_FILE> --jq .html_url
```

### Detailed Steps

1. Prepare the replacement PR body in a temporary markdown file, such as `.tmp/pr-body.md`.
2. Try the high-level GitHub CLI command first:
   ```bash
   gh pr edit <PR_NUMBER> --body-file .tmp/pr-body.md
   ```
3. If it fails with `error: your authentication token is missing required scopes [read:project]`, do not block automation on scope refresh.
4. Treat `gh auth refresh -s read:project` as diagnostic only in a headless agent. It may fail with `--hostname required`; `gh auth refresh -h github.com -s read:project` may launch a browser/device-code flow that the agent cannot complete.
5. Use the pull request REST API endpoint directly to update only the body:
   ```bash
   gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER> -X PATCH -F body=@.tmp/pr-body.md --jq .html_url
   ```
6. Confirm the command prints the PR URL.
7. Remove the temporary body file after the update succeeds.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| High-level PR edit | `gh pr edit <PR_NUMBER> --body-file <BODY_FILE>` | The command attempted a project-related lookup and failed because the token lacked `read:project`, even though the intended change was body-only | `gh pr edit` can require project read scope for operations that appear unrelated to projects |
| Scope refresh without hostname | `gh auth refresh -s read:project` | Failed with `--hostname required` in the agent session | Include `-h github.com` if a human is going to complete auth refresh, but do not expect this to work headlessly |
| Scope refresh with hostname | `gh auth refresh -h github.com -s read:project` | Started a browser/device-code flow that the agent could not complete non-interactively | Do not let automation wait on a human auth flow when a narrower API call can do the job |

## Results & Parameters

### Copy-paste fallback command

```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER> -X PATCH -F body=@<BODY_FILE> --jq .html_url
```

Expected output is the pull request URL, for example:

```text
https://github.com/<OWNER>/<REPO>/pull/<PR_NUMBER>
```

### Verified session

In `LLM360/Inference360` PR `#339`:

- `gh pr edit 339 --body-file .tmp/pr-339-body.md` failed with missing `read:project` scope.
- `gh auth refresh -s read:project` failed because `--hostname` was required.
- `gh auth refresh -h github.com -s read:project` produced a browser/device-code flow and was cancelled because it was non-interactive.
- `gh api repos/LLM360/Inference360/pulls/339 -X PATCH -F body=@.tmp/pr-339-body.md --jq .html_url` succeeded and printed `https://github.com/LLM360/Inference360/pull/339`.
- The temporary body file was deleted afterwards.

### Safety notes

- This workaround is for body-only PR updates. Keep using higher-level `gh pr edit` commands when changing metadata that benefits from CLI validation.
- Store replacement bodies in a temporary file to avoid shell quoting failures and accidental prompt/log expansion.
- Do not commit temporary body files.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | 2026-07-04, PR #339 body update from a Codex agent session | Verified locally with existing repo auth; CI validation was not involved because this is an operator CLI workflow |
