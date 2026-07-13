---
name: github-issue-stale-plan-comment-cleanup
description: "Clean up stale GitHub issue plan/review/task comments after revalidating the issue against the current architecture. Use when: (1) issue bodies are current but older authored plan comments contradict them, (2) a user asks to remove existing plans or stale planning artifacts, (3) issue comments have headings like '# Implementation Plan', '## Plan Review', '# Task #', or older superseded notes, (4) an issue is superseded by a newer architecture path and needs a disposition comment plus closure."
category: tooling
date: 2026-07-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - issue-comments
  - stale-plan
  - comment-cleanup
  - architecture-review
  - gh-cli
  - issue-disposition
  - viewerDidAuthor
  - inference360
---

# GitHub Issue Stale Plan Comment Cleanup

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Reconcile GitHub issues whose body still matches the current architecture but whose older plan/review/task comments describe stale work, then remove only obsolete authored comments after posting a current canonical disposition. |
| **Outcome** | Successful against live LLM360/Inference360 issues #83 through #89: #83 and #85-#88 kept architecture-aligned issue bodies but obsolete June plan/review/task comments were removed; #84 was already closed and aligned; #89 was closed as superseded by the current digest-verified Enroot/SquashFS WardenRuntime validation path. |
| **Verification** | verified-local - live GitHub issue workflow was executed and read back; no CI was involved. |

## When to Use

- A GitHub issue body has been updated to match the current architecture, but older comments still contain stale implementation plans, plan reviews, task breakdowns, or superseded notes.
- The user explicitly says to remove existing plans, stale plan comments, or obsolete planning artifacts from issues.
- A plan comment is durable enough to mislead downstream implementers even when a newer comment says it is superseded.
- You need to decide whether an issue should stay open with a canonical disposition comment or close because the premise no longer matches the current architecture.
- You need a narrow, auditable cleanup that deletes only comments authored by the current user or bot identity and leaves issue bodies, unrelated comments, and the latest architecture-aligned comment intact.

## Verified Workflow

### Quick Reference

```bash
REPO=LLM360/Inference360

# 1. Read current issue state before changing anything.
gh issue view 83 --repo "$REPO" \
  --json number,title,state,url,body,comments \
  --jq '{number,title,state,url,comment_count:(.comments|length)}'

# 2. List comments simply per issue for explicit ID review.
gh issue view 83 --repo "$REPO" --json comments \
  --jq '.comments[] | {id,author:.author.login,viewerDidAuthor,createdAt,firstLine:(.body|split("\n")[0])}'

# If REST numeric issue-comment IDs are needed for deletion:
gh api "repos/${REPO}/issues/83/comments" --paginate \
  --jq '.[] | {id,author:.user.login,created_at,firstLine:(.body|split("\n")[0])}'

# 3. Post the current canonical architecture-aligned disposition first.
gh issue comment 83 --repo "$REPO" --body-file /tmp/issue-83-current-disposition.md

# 4. Delete only reviewed obsolete authored comments by numeric issuecomment ID.
gh api -X DELETE "repos/${REPO}/issues/comments/<numeric-comment-id>"

# 5. Close only issues whose premise is superseded by the current architecture.
gh issue close 89 --repo "$REPO" --comment "Closing as superseded: <current architecture rationale>."

# 6. Verify live state after cleanup.
gh issue view 83 --repo "$REPO" --json number,title,state,comments \
  --jq '{number,title,state,comment_count:(.comments|length),comments:[.comments[].body]}'
```

### Detailed Steps

1. **Read the repo contract and live issue state first.** In Inference360, the safe order was `AGENTS.md`, `README.md`, `docs/inference360-design.md`, then live `gh issue view` readback for each issue. Treat both the architecture doc and the current GitHub issue state as live inputs; do not modify comments from an old local snapshot.

2. **Classify each issue before touching comments.** Decide whether the issue body is still architecture-aligned, already closed and aligned, or superseded by the current architecture. In the verified Inference360 run, #83 and #85-#88 were aligned but had stale June plan/review/task comments; #84 was closed and aligned; #89 was superseded by the digest-verified Enroot/SquashFS WardenRuntime validation path.

3. **Post one canonical current comment before deletion.** If the issue remains open, add a concise architecture-aligned disposition comment first. If the issue should close, post the rationale in the close comment. This preserves an audit trail before removing obsolete planning artifacts.

4. **Delete narrowly and only after explicit ID review.** List comments per issue, inspect the author and first heading/body, and delete only comments that are both authored by the current identity (`viewerDidAuthor` or the known author) and clearly obsolete plan artifacts. Good deletion candidates are headings beginning `# Implementation Plan`, `## Plan Review`, `# Task #`, or an older superseded note. Keep the issue body, unrelated comments, comments by other authors, and the newest architecture-aligned disposition comment.

5. **Use simple per-issue listings, not clever candidate predicates.** A complex jq filter failed with `expected an object but got: boolean (false)` on #84/#89. The safer workflow is one issue at a time: list comments, review IDs, delete the reviewed obsolete IDs, then read back.

6. **Verify the live GitHub result.** Read each issue after cleanup. In the verified run, issues #83-#89 each had `comment_count` 1 after cleanup, and #89 read back as `CLOSED` after the close call. Also confirm the local source repo remains clean if the work was purely GitHub metadata.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Supersede without deleting obsolete plan comments | Posted current architecture-aligned comments but left old plan/review/task comments visible | The older comments remained durable plan contracts and could still mislead downstream implementers despite a newer superseding note | If the user says remove existing plans, post the current canonical comment first, then delete obsolete authored plan artifacts |
| Delete broadly by topic | Considered removing all comments touching the stale plan area | This risks deleting issue bodies, unrelated comments, comments by other authors, or the newest disposition comment | Deletion must be narrow and auditable: authored by the current identity plus clearly obsolete headings/content |
| Use a complex jq candidate predicate | Tried to discover cleanup candidates with a compound jq predicate | It produced `expected an object but got: boolean (false)` on issues with different comment shapes (#84/#89) | Prefer simple per-issue comment listing and explicit ID review before deletion |
| Leave a stale plan comment because a newer comment supersedes it | Treated supersession as enough cleanup | Old issue plan comments are still plan contracts; if they contradict the architecture doc or issue body, keeping them visible can misdirect implementers | Remove obsolete authored plan comments after preserving a canonical current disposition |
| Close a superseded issue without rationale | Would have marked the issue closed but not explained the architectural replacement | Readers would not know whether the issue was completed, invalid, or superseded | Close with a reasoning comment that names the current architecture path and why the old premise no longer applies |

## Results & Parameters

### Deletion Candidate Rule

Delete a comment only when all of these are true:

- The comment is authored by the current account or known automation identity (`viewerDidAuthor` is true, or the REST/GraphQL author is the expected user).
- The comment is clearly an obsolete plan artifact, such as a heading beginning `# Implementation Plan`, `## Plan Review`, `# Task #`, or an older superseded note.
- A newer canonical architecture-aligned disposition comment is already present, or the close comment will preserve the current rationale.
- The numeric issuecomment ID was reviewed explicitly before the `gh api -X DELETE` call.

Keep the comment when any of these are true:

- It is the issue body or the latest current disposition comment.
- It was authored by someone else.
- It contains unrelated discussion, live evidence, or unresolved questions.
- You are not certain it is obsolete.

### Commands That Worked

```bash
# Readback before and after cleanup.
gh issue view <n> --repo LLM360/Inference360 \
  --json number,title,state,url,comments --jq '<simple per-issue jq>'

# Post superseding/current comment.
gh issue comment <n> --repo LLM360/Inference360 --body-file /tmp/<issue-comment>.md

# Delete reviewed obsolete comment by numeric issuecomment id.
gh api -X DELETE repos/LLM360/Inference360/issues/comments/<id>

# Close the superseded issue with rationale.
gh issue close 89 --repo LLM360/Inference360 --comment "<reasoning comment>"
```

### Verified Inference360 Disposition

- #83 and #85-#88: issue bodies were architecture-aligned; obsolete June plan/review/task comments were removed after posting a current architecture-aligned comment.
- #84: already closed and architecture-aligned; cleanup readback confirmed the remaining comment state.
- #89: Podman development-image cache plan was superseded by the digest-verified Enroot/SquashFS WardenRuntime validation path; closed with rationale.
- Verification readback: comment count was 1 for issues #83-#89 after cleanup; #89 state was `CLOSED`; the Inference360 worktree had clean `git status`.

### Related Skills

- `planning-check-already-shipped-before-planning` - verify whether issue premises are stale before planning implementation work.
- `verify-issue-premise-against-code-before-planning` - grep live code and enumerate all matching sites before trusting issue narration.
- `documentation-github-issue-final-report-live-body` - rewrite public GitHub bodies/comments into coherent final reports and sanitize durable public artifacts.
- `stale-plan-already-resolved` - verify stale point-in-time plan artifacts against current `origin/main` before applying them.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | Issues #83-#89 architecture cleanup | Verified-local/live GitHub workflow. Used current AGENTS/README/design-doc context plus live `gh issue view`; posted canonical comments, deleted only obsolete authored plan artifacts, closed #89 as superseded, and confirmed comment counts/state by readback. |
