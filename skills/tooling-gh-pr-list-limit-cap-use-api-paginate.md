---
name: tooling-gh-pr-list-limit-cap-use-api-paginate
description: "`gh pr list --limit N` (and `gh issue list`, `gh repo list`, etc.) is a hard cap, not a page size: pass `--limit 100` and you get at most 100 rows, period. A repo with 200 dependabot PRs silently passes a `gh pr list --limit 100 --json number | jq length == 0` 'no remaining PRs' check after looking at only the first 100. There is no `--no-limit` form, and `gh pr list` does NOT accept `--paginate` — only `gh api` does. The fix is to call the REST endpoint directly: `gh api --paginate /repos/<owner>/<name>/pulls?state=open&per_page=100`, which walks the `Link: rel=\"next\"` header and emits a single concatenated JSON array with NO upper bound. Same pattern works for issues, branches, releases, runs, etc. Note: REST responses use snake_case nested shapes (`head.ref`, `auto_merge`) while `gh pr list --json` returns camelCase flat fields (`headRefName`, `autoMergeRequest`) — normalise at the boundary so downstream consumers don't need to know which path produced the data. Use when: (1) building a 'repo is done / clean / quiescent' check that lists ALL remaining open PRs or issues, (2) a repo has hundreds of dependabot PRs and a `--limit 100` check would silently truncate, (3) you tried `--paginate` on `gh pr list` and got 'unknown flag', (4) you want a true 'enumerate every open PR' query for org-wide automation, (5) migrating from `gh pr list --json` to `gh api` and need the field-name mapping."
category: tooling
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - gh-cli
  - gh-pr-list
  - gh-api
  - paginate
  - pagination
  - hard-cap
  - silent-truncation
  - rest-api
  - dependabot-flood
  - repo-done-check
  - field-name-mapping
  - snake-case
  - camel-case
---

# `gh pr list --limit` Is a Hard Cap — Use `gh api --paginate` for True Enumeration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Stop silent truncation in "list ALL open PRs / issues / branches" scripts where `gh <noun> list --limit N` caps at exactly `N` rows. Prescribe `gh api --paginate /repos/.../pulls?state=open&per_page=100` as the only true unbounded enumeration. |
| **Outcome** | Replaces `gh pr list --limit 100` (or any fixed cap) with `gh api --paginate` whenever the script's correctness depends on seeing _every_ row. Documents the REST snake_case ↔ gh-CLI camelCase field-name mapping so downstream consumers don't break. |
| **Verification** | verified-ci — landed in ProjectHephaestus PR #839 (closes #838). The "repo is done" check that triggered this skill ran against a repo with 200+ open dependabot PRs and was silently passing while items remained; switching to `gh api --paginate` made the count correct. |

## When to Use

- Building a "repo is done / clean / quiescent" check whose correctness depends on enumerating EVERY open PR or issue (not just the first page).
- The repo has, or could plausibly have, hundreds of open dependabot/security PRs that a fixed `--limit` would silently miss.
- You tried `gh pr list --paginate` and got `unknown flag: --paginate` (only `gh api` accepts it; the noun-list subcommands do not).
- You raised `--limit 100` to `--limit 10000` "just to be safe" and want to know why that is still wrong (it is — see Failed Attempts).
- You are migrating from `gh pr list --json number,title,headRefName,autoMergeRequest` to `gh api /repos/.../pulls` and need the field-name mapping (REST snake_case nested vs. gh-CLI camelCase flat).
- You are writing org-wide automation (Myrmidon swarm, CI gate, batch close, label sweep) that loops over every PR or issue and must not silently truncate.
- A `wait until repo is empty` poll loop appears to converge but the repo never empties — suspect a silent cap on the listing query first.

## Verified Workflow

### Quick Reference

```bash
# WRONG — --limit is a hard cap, not a page size. Caps at exactly 100 rows, silently.
gh pr list --state open --limit 100 --json number,title

# WRONG — still a hard cap. Bigger number, same trap, plus a wasted round-trip if there really are >10000 PRs.
gh pr list --state open --limit 10000 --json number,title

# WRONG — `gh pr list` does NOT accept --paginate. Only `gh api` does.
# Produces: "unknown flag: --paginate"
gh pr list --state open --paginate

# RIGHT — walks Link: rel="next" headers across all pages. NO upper bound.
gh api --paginate /repos/OWNER/NAME/pulls?state=open&per_page=100
gh api --paginate /repos/OWNER/NAME/issues?state=open&per_page=100
gh api --paginate /repos/OWNER/NAME/branches?per_page=100
gh api --paginate /repos/OWNER/NAME/releases?per_page=100
```

### Detailed Steps

#### The trap, exactly as it surfaced

A `_list_open_prs_remaining` helper was added to a "is this repo done?" check. First draft:

```python
def _list_open_prs_remaining(self) -> list[dict[str, Any]]:
    result = _gh_call(
        [
            "pr", "list",
            "--repo", f"{owner}/{repo}",
            "--state", "open",
            "--limit", "100",
            "--json", "number,title,headRefName,autoMergeRequest",
        ],
        check=False,
    )
    return json.loads(result.stdout or "[]")
```

The user reviewed it and said, verbatim: **"don't limit PR's to 100, get all of them"**. The instinct to "just raise the limit" is wrong (see Failed Attempts row 2). The correct fix is to stop using `gh pr list` entirely and go straight to the REST endpoint with `--paginate`.

#### Why `--limit` is the wrong tool for this job

`--limit N` on `gh pr list` is documented as "maximum number of items to fetch" — it is a hard cap, not a page size. gh internally paginates the REST endpoint up to that many rows and then stops. There is:

- No `--limit 0` "no cap" form.
- No `--all` flag.
- No `--paginate` flag (that is `gh api` only).

The default is 30. The maximum the user can supply is whatever number they pick — but that number is always a cap. Pick too low and you silently truncate. Pick too high and you waste an HTTP round trip in the rare case the repo actually has that many rows; pick high enough to cover the worst case ever ("--limit 1000000") and you've turned the bug into a performance pessimisation while still depending on a magic number being above the unknowable max.

#### The fix: `gh api --paginate`

`gh api` is the only `gh` subcommand that exposes the REST `Link: rel="next"` walker. With `--paginate` it follows every next-page link and concatenates the JSON arrays into one stdout blob — no cap, no magic number, correct for any repo size:

```python
def _list_open_prs_remaining(self) -> list[dict[str, Any]]:
    owner, repo = get_repo_info(self.repo_root)
    try:
        result = _gh_call(
            [
                "api",
                "--paginate",
                f"/repos/{owner}/{repo}/pulls?state=open&per_page=100",
            ],
            check=False,
        )
        raw_pulls: list[dict[str, Any]] = json.loads(result.stdout or "[]")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        # Conservative default: assume NOT done so operators investigate.
        logger.error("Could not list open PRs: %s", exc)
        return [{"number": -1, "title": "(unknown: gh api pulls failed)"}]

    # Normalise REST snake_case shape → gh-CLI camelCase shape:
    normalised: list[dict[str, Any]] = []
    for pr in raw_pulls:
        normalised.append({
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "headRefName": (pr.get("head") or {}).get("ref", ""),
            "autoMergeRequest": pr.get("auto_merge"),
        })
    return normalised
```

The `per_page=100` is the REST endpoint's per-request page size (100 is the GitHub REST API maximum). `--paginate` keeps fetching until `Link: rel="next"` is gone. There is no caller-visible cap.

#### The field-name shape mismatch you MUST normalise

This is the non-obvious second half of the migration. `gh pr list --json` and `gh api /repos/.../pulls` return DIFFERENT shapes for the same data:

| Field meaning | `gh pr list --json` shape | `gh api /repos/.../pulls` shape |
| --------------- | --------------------------- | --------------------------------- |
| PR number | `number` (int, top-level) | `number` (int, top-level) — same |
| PR title | `title` (str, top-level) | `title` (str, top-level) — same |
| Head branch name | `headRefName` (str, top-level, camelCase, FLAT) | `head.ref` (str, NESTED under `head`, snake_case-y) |
| Auto-merge request | `autoMergeRequest` (object or null, top-level, camelCase) | `auto_merge` (object or null, top-level, snake_case) |
| Author login | `author.login` (object) | `user.login` (different key name!) |
| Mergeable state | `mergeStateStatus` (str) | `mergeable_state` (str) |
| Merge commit SHA | `mergeCommit.oid` | `merge_commit_sha` (flat snake_case) |
| Body | `body` (str) | `body` (str) — same |
| Draft? | `isDraft` (bool, camelCase) | `draft` (bool) — different name! |
| Labels | `labels` (array of `{name}`) | `labels` (array of `{name}`) — same shape |

If you swap `gh pr list --json` for `gh api /repos/.../pulls` without a normalisation layer, every downstream consumer that reads `pr["headRefName"]` or `pr["autoMergeRequest"]` will silently see `None` / `KeyError`. The fix is to normalise at the boundary (see the loop in the snippet above) so callers see the camelCase shape they already know.

#### Why this fix is `verified-ci`

PR #839 in ProjectHephaestus landed this change for the `automation.is_repo_done` workflow. The "is the repo done?" check is the gate that lets the automation loop exit. Before the fix, a repo with >100 open PRs would falsely report "done" and the loop would exit while items remained. After the fix, the count is correct for repos of any size, and CI on the PR validated the helper end-to-end. PR #839 closes #838.

#### Generalising the pattern

The same `--limit` hard-cap exists for every `gh <noun> list` subcommand. The same `gh api --paginate /repos/.../<resource>?state=...&per_page=100` fix works for:

```bash
gh api --paginate /repos/OWNER/NAME/issues?state=open&per_page=100
gh api --paginate /repos/OWNER/NAME/branches?per_page=100
gh api --paginate /repos/OWNER/NAME/releases?per_page=100
gh api --paginate /repos/OWNER/NAME/labels?per_page=100
gh api --paginate /repos/OWNER/NAME/actions/runs?status=in_progress&per_page=100
gh api --paginate /orgs/ORGNAME/repos?per_page=100
```

Each of those returns a snake_case REST shape that may need normalisation if you previously consumed the corresponding `gh <noun> list --json` shape.

#### When `gh pr list --limit N` is still fine

Not every call needs `--paginate`. Use `gh pr list --limit N` when:

- You explicitly want only the first N (e.g. "show me the 10 most recent merge attempts").
- Interactive ad-hoc inspection where you'll notice truncation by eye.
- The hard upper bound on items is provably small (e.g. release tags in a tiny repo).

Use `gh api --paginate` when:

- Correctness of a downstream check (gate, count comparison, idempotency assertion) depends on seeing every row.
- The item count is unbounded or grows over time (dependabot PRs, issue backlog, branch list).
- You're writing org-wide automation that runs across N repos with unknown sizes each.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh pr list --limit 100 --json number,title` for a "no remaining PRs" check | Reasoned that 100 PRs would surely cover the worst case for a repo we own | The `--limit` flag is a hard cap, not a page size. A repo with 200 dependabot PRs returns exactly 100 rows and the `jq length == 0` check falsely reports "done" with 100+ items still open. No warning, no error, no truncation signal. | `--limit` answers "give me at most N rows", never "give me all rows". If your decision depends on counting all rows, the wrong tool was chosen. |
| `gh pr list --limit 10000 --json number,title` "just to be safe" | Picked a number obviously above any realistic dependabot flood | Still a hard cap, just a bigger one. (a) For repos under the cap: one extra HTTP round trip wasted. (b) For repos at the cap: you've turned the silent-truncation bug into a magic-number game where you have to keep guessing higher than the unknowable max. (c) Code review will rightly object: "what happens when there are 10001 PRs?" | Raising a hard cap is never the right fix when the requirement is "enumerate everything". The fix is to stop using a capped API and use a paginated one. |
| `gh pr list --paginate --json number,title` | Reasoned: "I know `gh api --paginate` exists, so the noun-list subcommands probably accept it too" | `gh pr list` returns `unknown flag: --paginate`. Only `gh api` supports `--paginate`. The noun-list subcommands (`gh pr list`, `gh issue list`, `gh repo list`, `gh release list`, etc.) do NOT — they only expose `--limit`. | `--paginate` is a property of the raw REST passthrough (`gh api`), not of the friendly noun-verb subcommands. To get unbounded enumeration, you must drop down to `gh api`. |

## Results & Parameters

### Decision table — which gh form to use

| Goal | Use | Why |
| ------ | ----- | ----- |
| Show me the N most recent PRs (interactive) | `gh pr list --limit N` | `--limit` is exactly right when you want a bounded view |
| Show me ALL open PRs (gated correctness) | `gh api --paginate /repos/.../pulls?state=open&per_page=100` | `--paginate` walks every page, no cap |
| Show me all PRs matching a label, may be > 100 | `gh api --paginate /repos/.../pulls?state=open&per_page=100` then filter in `jq`; OR `gh search prs --owner X --label Y` (also caps but has its own search semantics) | Server-side label filter on the REST endpoint requires the search API; for simplicity, paginate-then-filter is robust |
| Show me ALL open issues across an org | Loop repos via `gh api --paginate /orgs/X/repos`, then per-repo `gh api --paginate /repos/X/Y/issues?state=open&per_page=100` | Both layers need pagination |
| Show me all dependabot PRs in this repo | `gh api --paginate /repos/.../pulls?state=open&per_page=100` then `jq 'map(select(.user.login == "dependabot[bot]"))'` | Same root call; `user.login` is REST shape (snake-ish nested) |

### REST → gh-CLI field-name mapping (full)

If you migrate from `gh pr list --json A,B,C` to `gh api /repos/.../pulls` and need to translate at the boundary, here is the mapping for fields that DIFFER:

| `gh pr list --json` key | REST `/pulls` key | Type |
| ----------------------- | ------------------ | ------ |
| `headRefName` | `head.ref` | str (REST nested) |
| `headRefOid` | `head.sha` | str (REST nested) |
| `baseRefName` | `base.ref` | str (REST nested) |
| `baseRefOid` | `base.sha` | str (REST nested) |
| `autoMergeRequest` | `auto_merge` | object or null |
| `mergeStateStatus` | `mergeable_state` | str |
| `mergeCommit.oid` | `merge_commit_sha` | str |
| `isDraft` | `draft` | bool |
| `isCrossRepository` | `head.repo.id != base.repo.id` (derive) | bool (REST does not expose flag) |
| `author.login` | `user.login` | str (different key name) |
| `latestReviews` | (not in REST list; requires `/reviews` subresource) | — |
| `closingIssuesReferences` | (not in REST list; requires GraphQL) | — |

Fields that are the SAME in both shapes: `number`, `title`, `body`, `state`, `labels[*].name`, `assignees[*].login`, `requested_reviewers[*].login`, `created_at`, `updated_at`, `merged_at`, `closed_at`.

### Sanity-check pattern for any unbounded enumeration

```bash
# If you have to enumerate without a cap, the pattern is always:
#   gh api --paginate /repos/OWNER/NAME/<resource>?<filters>&per_page=100 | jq <work>
# Assert that the count is plausible; if zero, the call probably failed (auth, repo name, filter typo).
result=$(gh api --paginate /repos/OWNER/NAME/pulls?state=open&per_page=100)
count=$(echo "$result" | jq length)
if [ "$count" -eq 0 ]; then
  # Confirm with an interactive sanity check
  gh pr list --state open --limit 5  # if this shows PRs, your --paginate call has a bug
fi
```

### Cost comparison

| Approach | HTTP calls (200 PRs) | HTTP calls (10 PRs) | Silent-truncation risk |
| ---------- | ---------------------- | --------------------- | ------------------------ |
| `gh pr list --limit 30` (default) | 1 | 1 | HIGH — silently caps at 30 |
| `gh pr list --limit 100` | 1 | 1 | HIGH — silently caps at 100 |
| `gh pr list --limit 10000` | 2 (100 + 100) | 1 | LOW until count > 10000, then HIGH |
| `gh api --paginate ...&per_page=100` | 2 (100 + 100) | 1 | NONE — correct for any size |

`--paginate` has the same HTTP cost as a generous `--limit` when items exceed one page, and the same cost (one call) when they don't. The only reason to prefer `--limit` is interactive ergonomics.

### Related skills

- `tooling-gh-label-list-default-limit-truncation.md` — covers the default-30 truncation that bites `gh label list --json` and other noun-list subcommands when `--limit` is omitted entirely. This skill (`tooling-gh-pr-list-limit-cap-use-api-paginate`) is the next layer: even when you DO pass `--limit`, it is still a hard cap, and the only true fix is `gh api --paginate`.
- `gh-create-pr-linked.md` — companion `gh` workflow skill.
- `gh-check-ci-status.md` — companion `gh` workflow skill.
