---
name: github-issues-semantic-branch-rename-gh-edit-graphql-verify
description: "Semantically rename default-branch references across GitHub issue titles, bodies, and authored comments using gh. Use when: (1) a repository default branch changed and existing issues still mention the old branch, (2) search results include ambiguous English uses that must not be blindly replaced, (3) you need to edit an existing issue comment you authored."
category: tooling
date: 2026-04-03
version: "1.0.1"
user-invocable: false
verification: verified-local
tags:
  - github
  - gh
  - issues
  - graphql
  - branch-rename
---

# GitHub Issues: Semantic Branch Rename via gh

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-03 |
| **Objective** | Rename stale branch-name references in GitHub issues without corrupting unrelated natural-language uses of the same word |
| **Outcome** | Successful — updated live issue titles, bodies, and one authored comment in a real repository while leaving ordinary-English `main` references untouched |
| **Verification** | verified-local |

## When to Use

- A repository default branch changed, for example `main` to `master`, and issue text still references the old branch
- `gh search issues <term> --match title,body,comments` returns both true branch references and false positives like "main roadmap" or "main shell"
- You need to update an existing issue comment you authored, not just an issue title/body

## Verified Workflow

### Quick Reference

```bash
gh repo view --repo <OWNER>/<REPO> --json nameWithOwner,defaultBranchRef,url

gh search issues <OLD_BRANCH> --repo <OWNER>/<REPO> \
  --match title,body,comments --limit 100 --json number,title,url

gh issue view <ISSUE_NUMBER> --json number,title,body,comments,url

gh issue edit <ISSUE_NUMBER> \
  --title "<UPDATED_TITLE>" \
  --body-file /tmp/<issue>-body.md

BODY="$(cat /tmp/<comment>.md)"
gh api graphql \
  -f query='mutation($id:ID!, $body:String!) { updateIssueComment(input:{id:$id, body:$body}) { issueComment { id url } } }' \
  -f id='<COMMENT_NODE_ID>' \
  -f body="$BODY"

gh search issues <OLD_BRANCH> --repo <OWNER>/<REPO> \
  --match title,body,comments --limit 100 --json number,title,url
```

### Detailed Steps

1. Confirm the repo's real default branch before touching any issue text:
   ```bash
   gh repo view --repo <OWNER>/<REPO> --json nameWithOwner,defaultBranchRef,url
   ```
   Do not assume the repo still uses the old branch name.

2. Enumerate candidate hits, then classify them semantically instead of doing a blind literal replace:
   ```bash
   gh search issues <OLD_BRANCH> --repo <OWNER>/<REPO> \
     --match title,body,comments --limit 100 --json number,title,url
   ```
   Separate:
   - true branch references such as `protected-branch policy for main`
   - false positives such as `main roadmap`, `main ingestion path`, or `main shell`

3. Read each target issue with comments before editing anything:
   ```bash
   gh issue view <ISSUE_NUMBER> --json number,title,body,comments,url
   ```
   Capture:
   - the exact title/body text to preserve formatting
   - authored comment IDs for any comments that must be edited
   - nearby context proving the term refers to the branch name

4. Update issue titles and bodies with `gh issue edit`, using `--body-file` for multi-line bodies:
   ```bash
   gh issue edit <ISSUE_NUMBER> \
     --title "<UPDATED_TITLE>" \
     --body-file /tmp/<issue>-body.md
   ```
   Write the replacement body explicitly so lists, backticks, and section structure stay intact.

5. Update existing authored issue comments with GraphQL, because `gh issue edit` cannot mutate comments:
   ```bash
   BODY="$(cat /tmp/<comment>.md)"
   gh api graphql \
     -f query='mutation($id:ID!, $body:String!) { updateIssueComment(input:{id:$id, body:$body}) { issueComment { id url } } }' \
     -f id='<COMMENT_NODE_ID>' \
     -f body="$BODY"
   ```
   This requires:
   - the comment node ID, not just the issue number
   - an authenticated user who authored the comment

6. Re-run the search and manually inspect the remaining hits:
   ```bash
   gh search issues <OLD_BRANCH> --repo <OWNER>/<REPO> \
     --match title,body,comments --limit 100 --json number,title,url
   gh issue view <ISSUE_NUMBER> --comments --json number,title,body,comments,url
   ```
   Stop only when the remaining matches are known false positives or deliberately retained English text.

7. If the harness blocks outbound GitHub traffic and `gh` returns `error connecting to api.github.com`, rerun the same command with network-enabled or escalated permissions. The issue-edit workflow itself may be correct; the failure can be sandbox policy rather than GitHub auth.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Treated every `gh search issues main` hit as an edit target | Search results also surfaced ordinary-English uses like `main roadmap` and `main ingestion path` | Always classify hits semantically before changing issue text |
| Attempt 2 | Ran `gh issue edit` from a network-restricted sandbox | The command returned `error connecting to api.github.com` even though the edit payload was valid | When `gh` fails on connectivity inside a harness, retry with approved network or escalated access before redesigning the workflow |
| Attempt 3 | Looked for a single `gh issue edit` flow to update both issue metadata and existing comments | `gh issue edit` updates issue title/body only; it does not mutate existing comments | Use `gh api graphql` with `updateIssueComment` and the authored comment node ID for comment edits |

## Results & Parameters

**Live parameters that worked**:

```text
Repository: <OWNER>/<REPO>
Confirmed default branch: <NEW_BRANCH>
Old branch text: <OLD_BRANCH>
New branch text: <NEW_BRANCH>
Edited issue title/body: one target issue
Edited issue body cross-reference: one related issue
Edited comment node: one authored issue-comment node ID
```

**Verification commands**:

```bash
gh search issues <OLD_BRANCH> --repo <OWNER>/<REPO> \
  --match title,body,comments --limit 100 --json number,title,url

gh issue view <PRIMARY_ISSUE> --comments --json number,title,body,comments,url
gh issue view <RELATED_ISSUE> --json number,title,body,url
```

**Expected remaining hits after a correct semantic cleanup**:

- issue bodies or comments where `main` is ordinary English, not the branch name
- examples observed in the live verification run:
  - `main roadmap`
  - `main ingestion path`
  - `main shell`
  - `main product shell`

**Important constraint**:

- Existing issue comments are only editable if the authenticated GitHub user authored them

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| GitHub repository | Semantic issue cleanup after confirming the repo default branch had changed | Updated one issue title/body, one related issue body, and one authored issue comment via `updateIssueComment`, then verified that the remaining matches were ordinary-English false positives |
