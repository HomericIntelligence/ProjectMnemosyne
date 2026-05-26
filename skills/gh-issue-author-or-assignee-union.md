---
name: gh-issue-author-or-assignee-union
description: "Combine `gh issue list` filters with OR semantics via two calls + Python set union. Use when: (1) you want issues authored-by OR assigned-to a user (not both), (2) automation that should only touch the operator's own issues."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, gh-cli, issues, automation]
---

# gh issue list -- Author OR Assignee Union

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Document how to get issues authored-by OR assigned-to a user using gh CLI |
| **Outcome** | Pattern shipped in hephaestus-automation-loop; restricts automation to the operator's own issues |
| **Verification** | verified-local (unit tests verify both queries + union; CI still running) |

## When to Use

- You want issues authored by OR assigned to a user (set union, not intersection)
- Automation that should only touch issues the operator created or is responsible for
- Building a personalized issue queue from `gh` CLI without writing GraphQL

## Verified Workflow

### Quick Reference

```bash
# Author-OR-assignee for the current user, given a repo slug:
{ gh issue list --repo $ORG/$REPO --author @me --state open --json number --jq '.[].number'
  gh issue list --repo $ORG/$REPO --assignee @me --state open --json number --jq '.[].number'
} | sort -u
```

### Detailed Steps

`gh issue list --author X --assignee Y` ANDs the two filters (issues authored by X AND assigned to Y). The CLI has no native OR. Workaround: run two separate calls and union the result sets in Python.

```python
def _gh_issue_numbers_for(org: str, repo: str, filter_flag: str) -> set[int]:
    out = subprocess.run(
        ["gh", "issue", "list", "--repo", f"{org}/{repo}",
         "--state", "open", filter_flag, "@me",
         "--limit", "200", "--json", "number", "--jq", ".[].number"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        return set()
    return {int(x) for x in out.stdout.split() if x.strip().isdigit()}

def list_open_issue_numbers(org: str, repo: str) -> list[int]:
    union = (
        _gh_issue_numbers_for(org, repo, "--author")
        | _gh_issue_numbers_for(org, repo, "--assignee")
    )
    return sorted(union)
```

`@me` is the gh-CLI shorthand for the authenticated user -- works with both `--author` and `--assignee`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh issue list --author @me --assignee @me` | Single call with both filters | gh ANDs the filters -- returns only issues that are BOTH authored by AND assigned to me | gh CLI filters are AND-only; OR requires two calls + set union |
| `gh search issues "author:@me OR assignee:@me"` | Use `gh search` with raw query syntax | `gh search issues` has different output JSON, and `OR` in the search-issue syntax doesn't combine these fields reliably | Two `gh issue list` calls + Python union is simpler and predictable |
| Filter via `--json` + `--jq` post-processing | Fetch all issues, filter client-side | Wastes bandwidth + pagination on repos with many open issues; `--limit 200` may still truncate | Push the filter to gh; only union in client |

## Results & Parameters

Tested in `hephaestus/automation/loop_runner.py` -- `_gh_issue_numbers_for` and `_list_open_issue_numbers` helpers. Coverage in `tests/unit/automation/test_loop_runner.py` verifies both queries are called and their results are unioned. PR HomericIntelligence/ProjectHephaestus#591.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Automation loop scoping (PR #591) | Restrict 6-phase automation to issues the operator created OR was assigned to |
