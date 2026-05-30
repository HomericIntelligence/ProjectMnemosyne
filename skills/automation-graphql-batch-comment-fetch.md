---
name: automation-graphql-batch-comment-fetch
description: "Fetch GitHub issue comments for N issues in one aliased GraphQL call instead of N sequential round-trips (N+1 anti-pattern). Use when: (1) a pipeline checks comment state per issue before or after a worker pool starts, (2) the per-issue comment check uses `gh issue view --comments` or single-issue GraphQL, (3) you already batch-fetch issue states with `prefetch_issue_states()` and want to apply the same pattern to comments, (4) profiling shows comment fetches dominate pipeline wall-clock time, (5) adding a cache layer to `has_existing_plan()` or similar per-issue gates."
category: optimization
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - graphql
  - batch-fetch
  - github-api
  - aliased-query
  - n-plus-one
  - comment-fetch
  - automation-pipeline
  - planner-state
  - round-trip-reduction
---

# Automation: GraphQL Batch Comment Fetch

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Replace N sequential `gh issue view --comments` (or per-issue GraphQL) calls with one aliased GraphQL query that fetches `comments` for all issues at once, matching the pattern already used by `prefetch_issue_states()` for issue states. |
| **Outcome** | SUCCESS — `fetch_all_issue_comments_graphql()` in `hephaestus/automation/review_state.py` + `PlannerStateManager.prefetch_comments()` cache path in `planner_state.py` shipped in PR #670. Round-trips cut from O(N) to O(1) per pipeline pass. |
| **Verification** | verified-ci — PR #670 passed all pre-commit hooks and CI. |

## When to Use

- A pipeline fetches per-issue comment state before or inside a worker pool (N+1 pattern).
- Individual fetches use `gh issue view --comments --json comments` or a per-issue GraphQL call with `_fetch_issue_comments_graphql(issue_number)`.
- You already have `prefetch_issue_states()` for issue open/closed state and want the same treatment for comment content.
- You want to share the fetched comments between two pipeline phases (plan-detection AND review-gate) without double-fetching.
- Adding a cache layer to `has_existing_plan()`, `is_plan_review_approved()`, or similar per-issue gates.

## Verified Workflow

### Quick Reference

```python
# review_state.py — one aliased GraphQL call for N issues
def fetch_all_issue_comments_graphql(
    issue_numbers: list[int],
) -> dict[int, list[dict[str, Any]]]:
    if not issue_numbers:
        return {}

    owner, name = get_repo_info(get_repo_root())

    # One aliased fragment per issue: issue0: issue(number: <n>) { comments { nodes { ... } } }
    fragments = [
        (
            f"issue{idx}: issue(number: {int(num)}){{"
            "comments(last: 100, orderBy: {field: UPDATED_AT, direction: DESC})"
            "{nodes{body updatedAt url}}"
            "}}"
        )
        for idx, num in enumerate(issue_numbers)
    ]
    query = f"query{{repository(owner:{owner!r},name:{name!r}){{{' '.join(fragments)}}}}}"

    idx_to_num = dict(enumerate(issue_numbers))
    result_map: dict[int, list[dict[str, Any]]] = {num: [] for num in issue_numbers}

    try:
        result = _gh_call(["api", "graphql", "-f", f"query={query}"])
        data = json.loads(result.stdout)
        repo_data = data.get("data", {}).get("repository", {})
        for alias, issue_data in repo_data.items():
            if not alias.startswith("issue"):
                continue
            try:
                idx = int(alias[len("issue"):])
            except ValueError:
                continue
            num = idx_to_num.get(idx)
            if num is None or issue_data is None:
                continue
            nodes = issue_data.get("comments", {}).get("nodes", []) or []
            # GraphQL returns newest-first; reverse to chronological order
            result_map[num] = list(reversed(nodes))
    except Exception as exc:
        logger.warning("Failed to batch-fetch comments for issues %s: %s", issue_numbers, exc)

    return result_map


# planner_state.py — cache + fallback in PlannerStateManager
class PlannerStateManager:
    def __init__(self, options):
        self.options = options
        self._comments_cache: dict[int, list[dict]] | None = None  # None = not yet fetched

    def prefetch_comments(self, issue_numbers: list[int]) -> None:
        """One aliased GraphQL call for all issues. Call before the worker pool starts."""
        self._comments_cache = fetch_all_issue_comments_graphql(issue_numbers)

    def get_cached_comments(self, issue_number: int) -> list[dict] | None:
        """Return cached comments, or None if prefetch_comments was not called."""
        if self._comments_cache is None:
            return None
        return self._comments_cache.get(issue_number, [])

    def has_existing_plan(self, issue_number: int) -> bool:
        cached = self.get_cached_comments(issue_number)
        if cached is not None:
            return any(
                any(marker in c.get("body", "") for marker in PLAN_COMMENT_MARKERS)
                for c in cached
            )
        # Fallback: individual gh CLI call (pre-batch behaviour)
        result = _gh_call(["issue", "view", str(issue_number), "--comments", "--json", "comments"])
        return any(
            any(marker in c.get("body", "") for marker in PLAN_COMMENT_MARKERS)
            for c in json.loads(result.stdout).get("comments", [])
        )
```

### Detailed Steps

1. **Identify the N+1 site.** Look for `_gh_call(["issue", "view", str(n), "--comments", ...])` or `_fetch_issue_comments_graphql(n)` inside a loop or per-issue worker function.

2. **Add `fetch_all_issue_comments_graphql(issue_numbers)` to `review_state.py`** (or the module that already owns per-issue comment fetching). It is the shared primitive: both the planner (plan-detection) and the reviewer (review-gate) call it.

3. **Add `prefetch_comments(issue_numbers)` to `PlannerStateManager`** (or equivalent state manager). Call it once, before the worker pool starts, with the full issue list returned by `filter()`.

4. **Add `get_cached_comments(issue_number)` accessor.** Returns `None` when the cache has not been populated (so callers can fall back to the individual fetch). Returns `[]` for issues present in the cache but with no comments.

5. **Update `has_existing_plan()` and any `is_plan_review_approved()` caller** to pass `get_cached_comments(n)` as the `comments` argument. Both already accept a pre-fetched `comments` list; the batch just populates it.

6. **Keep the individual-fetch fallback** in `has_existing_plan()` for callers that do not call `prefetch_comments()` first. This preserves backward-compatibility — workers that run before the prefetch is populated still work correctly.

7. **Add tests:**
   - `prefetch_comments([])` sets `_comments_cache = {}`.
   - `get_cached_comments(n)` returns `None` before `prefetch_comments()`.
   - `get_cached_comments(n)` returns `[]` for a missing key after `prefetch_comments()`.
   - `has_existing_plan()` uses cache and does NOT call `_gh_call` when cache is populated.
   - `has_existing_plan()` falls back to `_gh_call` when `_comments_cache is None`.
   - `fetch_all_issue_comments_graphql([301, 302])` makes exactly ONE `_gh_call`.
   - Single and multi-issue payloads parse correctly in chronological order.
   - `fetch_all_issue_comments_graphql` returns `{n: []}` on `_gh_call` failure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | N sequential `gh issue view --comments --json comments` calls (original `has_existing_plan`) | One `gh` subprocess per issue; 20 issues = 20 round-trips before the first worker starts | The `gh` CLI call is a subprocess + HTTP round-trip; never put it in a per-issue loop |
| 2 | N sequential single-issue GraphQL calls (`_fetch_issue_comments_graphql` called per issue) | Same O(N) round-trip problem; GraphQL is still one HTTP call per issue | The per-issue GraphQL function (`last: 100, orderBy: UPDATED_AT`) is a useful building block — but alias it, don't call it N times |
| 3 | Putting the batch fetch inside the worker pool (called `fetch_all_issue_comments_graphql` from within each worker) | Race condition on the result dict; workers started before batch result arrived | Call batch fetch before the pool starts (in `filter()` or an explicit `prefetch_comments()` step) |
| 4 | dict comprehension `{idx: num for idx, num in enumerate(issue_numbers)}` (passed ruff check initially) | ruff C416: unnecessary dict comprehension — rewrite using `dict()` | Use `dict(enumerate(issue_numbers))`; ruff C416 fires on `{k: v for k, v in iterable}` |

## Results & Parameters

**GraphQL query shape (aliased fragments):**

```graphql
query {
  repository(owner: "HomericIntelligence", name: "ProjectHephaestus") {
    issue0: issue(number: 615) {
      comments(last: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { body updatedAt url }
      }
    }
    issue1: issue(number: 616) {
      comments(last: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { body updatedAt url }
      }
    }
  }
}
```

**Key design decisions:**

- `last: 100` + `orderBy: UPDATED_AT DESC`: matches the existing `_fetch_issue_comments_graphql` per-issue contract (so both single and batch paths see the same comment slice).
- Reverse nodes to chronological order: downstream "walk forward, last-match-wins" semantics (e.g. `latest_verdict()`) require oldest-first ordering.
- Return `{num: []}` on failure: callers already handle empty-list gracefully (`has_existing_plan` returns False, `is_plan_review_approved` returns False).
- `_comments_cache is None` vs `{}`: distinguishes "not yet fetched" from "fetched, no issues had comments". `get_cached_comments` returns `None` for the former so callers know to fall back.

**Existing parallel in codebase (model to follow):**

```python
# github_api.py — aliased batch for issue states (the exact same pattern)
def _fetch_batch_states(batch: list[int], owner: str, repo: str) -> dict[int, IssueState]:
    fragments = [
        f"issue{idx}: issue(number: {int(num)}) {{ number state }}"
        for idx, num in enumerate(batch)
    ]
    query = f"""query {{ repository(owner: "{owner}", name: "{repo}") {{ {" ".join(fragments)} }} }}"""
    result = _gh_call(["api", "graphql", "-f", f"query={query}"])
    ...
```

## Verified On

| Project | File / Issue | Notes |
|---|---|---|
| ProjectHephaestus | `hephaestus/automation/review_state.py` | `fetch_all_issue_comments_graphql()` |
| ProjectHephaestus | `hephaestus/automation/planner_state.py` | `PlannerStateManager.prefetch_comments()`, `get_cached_comments()`, updated `has_existing_plan()` |
| ProjectHephaestus | Issues #615, #616 / PR #670 | Part of the verdict-loop + batch-fetch fixes |
