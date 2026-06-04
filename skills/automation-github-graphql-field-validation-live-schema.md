---
name: automation-github-graphql-field-validation-live-schema
description: "A GitHub GraphQL mutation/query that selects a field which does NOT exist on the returned type fails on EVERY call with `Field 'X' doesn't exist on type 'Y'`, and a code path with no direct unit test can ship such a broken query indefinitely. Validate every field selection against the LIVE schema via introspection before shipping. Use when: (1) writing or editing a raw `gh api graphql` query/mutation string (especially `addPullRequestReview`, `reviewThreads`, or any PR-review traversal), (2) a runtime log shows `gh: Field '<field>' doesn't exist on type '<Type>'` or repeated identical mutation failures, (3) you need to read a parent object off a child node (e.g. a comment's thread or review) and are assuming a reverse edge exists, (4) a function that builds a GraphQL query has no direct unit test and is only mocked out by higher-level callers, (5) an automation loop treats a PR as NOGO/re-runs forever because an in-loop review/comment never posts."
category: tooling
date: 2026-06-03
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - graphql
  - github-api
  - schema-introspection
  - field-validation
  - addPullRequestReview
  - reviewThreads
  - pull-request-review
  - silent-broken-query
  - missing-unit-test
  - child-to-parent-edge
  - gh-api-graphql
  - automation-pipeline
---

# Automation: Validate GitHub GraphQL Field Selections Against the Live Schema

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Objective** | Stop a GitHub GraphQL mutation/query from selecting a field that does not exist on the returned type (which fails on EVERY call), by validating every field selection against the live schema via introspection before shipping, and by giving every raw-query function a direct unit test. |
| **Outcome** | SUCCESS — `gh_pr_review_post` in `hephaestus/automation/github_api.py` was selecting `pullRequestReviewThread { id isResolved }` on a `PullRequestReviewComment` node; that field does not exist, so the `addPullRequestReview` mutation failed on every call and NO in-loop PR review ever posted. Fixed by returning only `pullRequestReview { id }` from the mutation and resolving threads via a separate `pullRequest.reviewThreads` query that uses fields that actually exist. Shipped in PR #906 (closes #905). |
| **Verification** | verified-ci — fix merged this session; every field selection validated against the live GitHub schema via `gh api graphql` introspection. |

## When to Use

- You are writing or editing a raw `gh api graphql` query/mutation string, especially `addPullRequestReview`, `reviewThreads`, or any pull-request-review traversal.
- A runtime log shows `gh: Field '<field>' doesn't exist on type '<Type>'`, or you see many identical mutation failures in one automation run (this case produced 219 identical failures).
- You need to read a parent object from a child node (e.g. a comment's thread, or a comment's review) and are assuming a reverse edge exists on the child.
- A function that builds a GraphQL query/mutation has NO direct unit test and is only mocked out by higher-level callers.
- An automation loop treats a PR as NOGO and re-runs forever because an in-loop review or comment never actually posts.

## Verified Workflow

### Quick Reference

Validate any field selection against the LIVE schema BEFORE shipping. There is no
compile-time check — an invalid selection ships silently and fails at runtime:

```bash
# List every field that actually exists on a type:
gh api graphql -f query='{ __type(name: "PullRequestReviewComment") { fields { name } } }'

# Inspect a connection's node fields (e.g. what a reviewThread exposes):
gh api graphql -f query='{ __type(name: "PullRequestReviewThread") { fields { name } } }'
gh api graphql -f query='{ __type(name: "PullRequestReview") { fields { name } } }'
```

Correct PR-review post + foreign-thread-safe resolve (fields that ACTUALLY exist):

```graphql
# 1. Mutation: select ONLY pullRequestReview { id } (NOT a comment's thread).
mutation {
  addPullRequestReview(input: {
    pullRequestId: "<PR_NODE_ID>",
    event: COMMENT,
    body: "<review body>",
    comments: [{ path: "<file>", line: <n>, body: "<comment>" }]
  }) {
    pullRequestReview { id }   # PullRequestReview has `id`, NOT `databaseId`
  }
}

# 2. Follow-up query: read threads off the PARENT (pullRequest.reviewThreads),
#    and read each thread's first comment's parent review id (child -> parent).
query {
  repository(owner: "<owner>", name: "<name>") {
    pullRequest(number: <pr>) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes { pullRequestReview { id } }   # comment -> its parent review
          }
        }
      }
    }
  }
}
```

```python
# 3. Keep only unresolved threads created by THE review we just posted
#    ("foreign thread" guarantee — excludes pre-existing human-reviewer threads):
own_thread_ids = [
    t["id"]
    for t in review_threads
    if not t["isResolved"]
    and (t["comments"]["nodes"] or [{}])[0]
        .get("pullRequestReview", {})
        .get("id") == created_review_id
]
```

### Detailed Steps

1. **Before writing the selection set, introspect the type.** For every object whose
   fields you select, run `gh api graphql -f query='{ __type(name: "TYPE") { fields { name } } }'`
   and confirm each selected field name is in the returned list. Do this for the
   mutation payload type AND every nested node type.

2. **Never assume a reverse (child→parent) edge.** A GraphQL connection edge often
   exists in only ONE direction. Here, a `PullRequestReviewComment` has NO thread
   field, and a `PullRequestReviewThread` has NO direct `review` field. The available
   edges are: `PullRequestReview.comments` (parent→child), `PullRequest.reviewThreads`
   (parent→child), and a thread comment's `pullRequestReview { id }` (child→parent).
   If `Child.parent` doesn't exist, fetch via `Parent.children` and filter.

3. **Treat HTTP 200 with an `errors` array as a FAILURE.** `gh api graphql` can return
   exit code 0 with a top-level `errors` array. A bare exit-code check misses it.
   Parse the JSON and surface `data.errors` (or the `errors` key) explicitly.

4. **Give every raw-query function a direct unit test.** Mock `_gh_call` / the
   subprocess, assert the exact query string AND the parsing of a sample response.
   A cheap durable guard: assert the sent query string does NOT contain the
   known-bad field name (e.g. `assert "pullRequestReviewThread" not in sent_query`).
   Mocking the whole function out in higher-level tests is what let the broken
   query ship for a long time.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | `addPullRequestReview` mutation selected `pullRequestReviewThread { id isResolved }` on each `PullRequestReviewComment` node | That field does NOT exist on `PullRequestReviewComment` — `gh: Field 'pullRequestReviewThread' doesn't exist on type 'PullRequestReviewComment'`; the mutation failed on EVERY call so NO in-loop review ever posted (219 identical failures in one run) | A field selection has no compile-time check; introspect every type with `__type { fields { name } }` against the LIVE schema before shipping |
| 2 | `gh_pr_review_post` had no direct unit test — coverage only mocked it out via `pr_reviewer` tests | The structurally-broken query passed CI indefinitely because nothing exercised the real query string | Any function that builds a raw GraphQL query/mutation MUST have a direct unit test asserting the query string and the parsing; add a guard asserting the known-bad field name is absent |
| 3 | Assumed a comment could report its own thread (read thread off the comment / child) | The reverse edge does not exist; you cannot read a comment's thread off the comment | Child→parent edges often don't exist; fetch threads via `pullRequest.reviewThreads` (parent→child) and filter |
| 4 | Tried selecting `databaseId` on `PullRequestReview` to correlate threads to the review | `PullRequestReview` exposes `id`, not `databaseId`, in the path needed here; correlation must use the node `id` | Confirm the exact identifier field name via introspection; don't assume `databaseId` exists everywhere |
| 5 | (Risk) relied on `gh api graphql` exit code alone to detect success | `gh api graphql` can return HTTP 200 with a top-level `errors` array and still have FAILED | Surface the `errors` array from the JSON response; a bare exit-code check can miss a failed operation |

## Results & Parameters

**Schema relationships (verified via live introspection, 2026-06-03):**

- `PullRequestReviewComment` has **no** thread field at all (verified:
  `gh api graphql -f query='{ __type(name: "PullRequestReviewComment") { fields { name } } }'`).
- `PullRequestReview` exposes `id` and `comments` (NOT `databaseId` in this path).
- `PullRequestReviewThread` exposes `comments` (no direct `review` field).
- A thread's comment exposes `pullRequestReview { id }` (child→parent), which is how
  you correlate a thread back to the review that created it.

**Corrected mutation (returns only an existing field):**

```graphql
mutation {
  addPullRequestReview(input: {
    pullRequestId: $prId, event: COMMENT, body: $body, comments: $comments
  }) {
    pullRequestReview { id }
  }
}
```

**Corrected follow-up resolve query + foreign-thread filter:**

```graphql
query {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) { nodes { pullRequestReview { id } } }
        }
      }
    }
  }
}
```

Keep unresolved threads whose first comment's `pullRequestReview.id` equals the
review id you just created — this excludes pre-existing human-reviewer threads
(the "foreign thread" guarantee) using fields that actually exist.

**Generalizable lessons (the heart of this skill):**

1. Validate every GraphQL field selection against the LIVE schema via introspection
   BEFORE shipping: `gh api graphql -f query='{ __type(name: "TYPE") { fields { name } } }'`.
   There is no compile-time check; an invalid selection ships silently and the
   `gh` CLI prints `Field 'X' doesn't exist on type 'Y'` only at runtime.
2. `gh api graphql` returning HTTP 200 with an `errors` array still means the
   operation FAILED — surface the `errors` array, don't trust the exit code alone.
3. Any function that builds a raw GraphQL query/mutation MUST have a direct unit
   test (mock `_gh_call`/subprocess, assert the query string and the parsing). A
   cheap durable guard is a unit test asserting the sent query string does NOT
   contain the known-bad field name.
4. Child→parent vs parent→child: a connection edge often exists in only ONE
   direction. If `Child.parent` doesn't exist, fetch via `Parent.children` and filter.

## Verified On

| Project | File / Issue | Notes |
|---|---|---|
| ProjectHephaestus | `hephaestus/automation/github_api.py` (`gh_pr_review_post`) | Removed non-existent `pullRequestReviewThread` selection; mutation now returns `pullRequestReview { id }` |
| ProjectHephaestus | Issue #905 / PR #906 | Fix merged 2026-06-03; thread resolution moved to `pullRequest.reviewThreads` follow-up query |
| GitHub GraphQL API | live schema introspection | `__type(name: "PullRequestReviewComment" / "PullRequestReviewThread" / "PullRequestReview")` confirmed the available fields |
