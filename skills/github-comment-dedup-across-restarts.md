---
name: github-comment-dedup-across-restarts
description: "Prevent duplicate GitHub issue comments when a pipeline worker restarts by lazily loading existing comment IDs from the GitHub API. Use when: (1) a long-running pipeline posts stage-progress comments to GitHub issues, (2) an in-memory comment-ID cache is lost on process restart causing duplicate comments, (3) you need idempotent PATCH-or-POST logic for issue comments keyed by stage name and iteration number, (4) using gh CLI to paginate issue comments efficiently."
category: tooling
date: 2026-04-05
version: "1.0.0"
user-invocable: false
tags:
  - github
  - api
  - comment
  - deduplication
  - nats
  - pipeline
  - myrmidon
  - gh-cli
  - idempotent
---

# GitHub Comment Dedup Across Restarts

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Prevent duplicate GitHub issue comments when claude-myrmidon pipeline worker restarts |
| **Outcome** | Successful -- `_load_existing_comment_ids()` repopulates in-memory cache from GitHub API on first use per issue, enabling idempotent PATCH-or-POST |
| **Verification** | verified-local (syntax checked, no runtime test) |

## When to Use

- A long-running pipeline worker posts `## Stage: <name>` comments to GitHub issues and uses an in-memory dict to track comment IDs for PATCH updates
- Process restarts cause the in-memory `_comment_ids` dict to be empty, resulting in duplicate comments instead of updating existing ones
- You need to lazily hydrate a comment-ID cache from the GitHub API on first access per issue
- You want to minimize API payload by fetching only the first 80 characters of each comment body (enough to capture the `## Stage:` header)

## Verified Workflow

### Quick Reference

| Step | What to do |
| ------ | ----------- |
| 1 | Add `_comment_ids: dict[str, int]` and `_comment_ids_loaded: set[int]` instance attributes |
| 2 | Implement `_load_existing_comment_ids(issue_number)` to paginate issue comments via `gh api` |
| 3 | Parse each comment body prefix with `## Stage: (\w+)(?:\s+\(iteration (\d+)\))?` regex |
| 4 | Populate `_comment_ids` with `"stage-iteration"` -> `comment_id` mappings |
| 5 | Call `_load_existing_comment_ids()` lazily on first `post_issue_comment()` per issue |
| 6 | Use loaded mappings to decide PATCH (update) vs POST (create) |

### Detailed Steps

#### Step 1 -- Instance attributes

```python
import re
import subprocess

class PipelineReporter:
    STAGE_RE = re.compile(r"## Stage: (\w+)(?:\s+\(iteration (\d+)\))?")

    def __init__(self, repo: str):
        self._repo = repo
        self._comment_ids: dict[str, int] = {}
        self._comment_ids_loaded: set[int] = set()
```

#### Step 2 -- Load existing comment IDs from GitHub API

```python
    def _load_existing_comment_ids(self, issue_number: int) -> None:
        """Fetch existing stage comments for an issue to avoid duplicates on restart."""
        if issue_number in self._comment_ids_loaded:
            return
        self._comment_ids_loaded.add(issue_number)

        jq_filter = r'.[] | "\(.id)\t\(.body[0:80])"'
        result = subprocess.run(
            [
                "gh", "api", "--paginate",
                f"repos/{self._repo}/issues/{issue_number}/comments",
                "--jq", jq_filter,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return  # non-fatal: worst case we create a duplicate

        for line in result.stdout.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            comment_id_str, body_prefix = parts
            match = self.STAGE_RE.search(body_prefix)
            if match:
                stage = match.group(1).lower()
                iteration = int(match.group(2)) if match.group(2) else 0
                key = f"{stage}-{iteration}"
                self._comment_ids[key] = int(comment_id_str)
```

**Key detail:** The `--jq` filter uses `r'...'` (raw string) to avoid Python escape sequence warnings with jq's `\(` interpolation syntax.

#### Step 3 -- Integrate into post_issue_comment()

```python
    def post_issue_comment(
        self, issue_number: int, stage: str, iteration: int, body: str
    ) -> None:
        """Post or update a stage comment. PATCHes if comment already exists."""
        self._load_existing_comment_ids(issue_number)

        key = f"{stage.lower()}-{iteration}"
        existing_id = self._comment_ids.get(key)

        if existing_id:
            # PATCH existing comment
            subprocess.run(
                [
                    "gh", "api", "--method", "PATCH",
                    f"repos/{self._repo}/issues/comments/{existing_id}",
                    "-f", f"body={body}",
                ],
                capture_output=True,
                text=True,
            )
        else:
            # POST new comment and cache its ID
            result = subprocess.run(
                [
                    "gh", "api", "--method", "POST",
                    f"repos/{self._repo}/issues/{issue_number}/comments",
                    "-f", f"body={body}",
                    "--jq", ".id",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._comment_ids[key] = int(result.stdout.strip())
```

### Root Cause Analysis

The claude-myrmidon pipeline had an in-memory `_comment_ids` dict mapping `"stage-iteration"` keys to GitHub comment IDs. This allowed it to PATCH existing comments instead of creating duplicates within a single process run. But on process restart, the dict was empty and every stage comment was created as a new POST, resulting in duplicate comments on the issue.

The fix adds a lazy-loading step that queries the GitHub API for existing comments on first access per issue, parses their `## Stage:` headers, and repopulates the in-memory cache. This makes the PATCH-or-POST logic idempotent across restarts.

### Key Implementation Details

- **`--jq` filter fetches only first 80 chars**: `.[] | "\(.id)\t\(.body[0:80])"` minimizes API payload -- the `## Stage:` header is always within the first 80 characters
- **Raw string for jq filter**: `r'.[] | "\(.id)\t\(.body[0:80])"'` avoids Python escape sequence warnings from jq's `\(` interpolation syntax
- **Regex pattern**: `re.compile(r"## Stage: (\w+)(?:\s+\(iteration (\d+)\))?")` handles both `## Stage: PLAN` (iteration defaults to 0) and `## Stage: TEST (iteration 2)` formats
- **Stage names are lowercased**: Ensures consistent key matching regardless of case in the comment header
- **`_comment_ids_loaded: set[int]`**: Tracks which issues have been fetched to avoid redundant API calls
- **Non-fatal on API failure**: If `gh api` fails, the method returns silently -- worst case is a duplicate comment, not a crash

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| In-memory `_comment_ids` dict only | Cached comment IDs in a dict during process lifetime for PATCH-or-POST logic | Dict is empty after process restart; every stage comment creates a new POST, producing duplicates on re-run | In-memory caches for idempotency must be hydrated from the source of truth (GitHub API) on startup or first access |
| Fetching full comment bodies | Called `gh api` without `--jq` body truncation to get complete comment content | Wasteful -- full comment bodies can be large (multi-KB markdown) but the `## Stage:` header is always in the first line | Use `--jq` with `.body[0:80]` to fetch only what's needed for pattern matching, reducing API payload |

## Results & Parameters

### Comment Header Format

The dedup logic relies on comments following this header convention:

```markdown
## Stage: PLAN

## Stage: TEST (iteration 2)

## Stage: BUILD (iteration 3)
```

### Key Mapping

| Comment Header | Dict Key |
| ---------------- | ---------- |
| `## Stage: PLAN` | `plan-0` |
| `## Stage: TEST (iteration 2)` | `test-2` |
| `## Stage: BUILD (iteration 3)` | `build-3` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | claude-myrmidon pipeline worker | Pipeline posts stage-progress comments to GitHub issues; verified syntax and logic flow locally |

## References

- [gh-post-issue-update](gh-post-issue-update.md) -- Structured GitHub issue comment posting patterns (related skill)
- [nats-py-connection-resilience-patterns](nats-py-connection-resilience-patterns.md) -- NATS connection resilience for the same pipeline (related skill)
- [GitHub REST API: Issue Comments](https://docs.github.com/en/rest/issues/comments) -- Official API docs for listing, creating, and updating issue comments
