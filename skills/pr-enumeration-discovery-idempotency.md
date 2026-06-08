---
name: pr-enumeration-discovery-idempotency
description: "Use when: (1) gh pr list silently truncates results because the default limit is 30 and a repo has more open PRs, (2) gh label list or gh issue list silently drops entries past the default pagination limit, (3) Dependabot or other bot-authored PRs are invisible to issue-driven automation because they have no Closes #N link — use synthetic issue-key union pattern, (4) an automation tool creates duplicate PRs for the same issue because it lacks an idempotency check before calling gh pr create, (5) GitHub API reports a PR as merged but the remote ref and local working tree have not yet synced — merged state is not proof of remote sync, (6) a bulk PR-sync tool times out (HTTP 504) because gh pr list with statusCheckRollup at 50+ PRs is too heavy — fetch statusCheckRollup per-PR instead, (7) a bulk driver silently skips the whole PR queue by returning an empty list on a gh error instead of raising, (8) stale CI classification marks BEHIND/BLOCKED PRs as FAILING and skips them when they should be rebased"
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: pr-enumeration-discovery-idempotency.history
tags:
  - gh-pr-list
  - gh-api-paginate
  - pagination
  - silent-truncation
  - bot-pr
  - synthetic-issue-key
  - dependabot
  - duplicate-pr
  - idempotency
  - statusCheckRollup
  - 504-gateway-timeout
  - mergeStateStatus
  - stale-ci
  - merged-state-sync
  - pr-discovery
  - bulk-pr-sync
---

# PR Enumeration, Discovery, and Idempotency

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Canonical reference for correctly *finding* PRs (pagination, bot PRs, limit caps), filing them idempotently, reasoning about state divergence between the GitHub API and the remote, and classifying a bulk PR queue for routing. |
| **Outcome** | Consolidated from 8 verified skills covering gh enumeration, synthetic-issue-key bot discovery, duplicate-PR prevention, merged-state sync verification, and bulk PR-sync classification. |
| **Verification** | verified-ci |
| **History** | [changelog](./pr-enumeration-discovery-idempotency.history) |

**Scope.** IN: listing and finding PRs (pagination, bot PRs, limit caps, `gh api --paginate`), idempotency guards against duplicate PR creation, stale state divergence between the GitHub API and the remote, bulk classification of PR queues for routing. OUT: what to do once PRs are found — review, rebase, merge, CI triage, multi-repo swarm drivers.

## When to Use

- `gh pr list` (or `gh issue list`, `gh label list`, `gh release list`) silently truncates because the default limit is **30** and the repo has more rows.
- You raised `--limit` "just to be safe" and want to know why a hard cap is still wrong for "enumerate everything".
- Dependabot/Renovate/other bot PRs are invisible to issue-driven automation (no `Closes #N` link) — use the synthetic-issue-key union pattern.
- An automation tool creates duplicate PRs for one issue because `gh pr create` runs without an existing-PR check, or a worktree manager rebuilds a branch from base and discards remote history.
- You are about to report "PR is merged" from `gh pr view` alone, or about to push a local branch to a PR a parallel process may also own — merged/named state is not proof of remote sync or matching content.
- A bulk PR-sync tool times out (HTTP 504) on `gh pr list` with `statusCheckRollup` at 50+ PRs, silently returns `[]` on a gh error, or skips every BEHIND/BLOCKED PR as FAILING after a fix lands on main.

## Verified Workflow

### Quick Reference

```bash
# ── ENUMERATION: --limit is a hard cap (default 30). For a true "all rows" query
#    use gh api --paginate (gh pr list does NOT accept --paginate). ──────────────
gh pr list --limit 200 --json number,title,mergeStateStatus          # bounded view, explicit cap
gh api --paginate /repos/OWNER/NAME/pulls?state=open&per_page=100     # unbounded, walks Link rel=next
gh label list --repo "$repo" --limit 200 --json name                 # always pass --limit in scripts

# ── BOT-PR SWEEP: discriminate on user.type=='Bot' (REST), NOT login string ──────
gh api --paginate /repos/OWNER/NAME/pulls?state=open\&per_page=100 \
  | jq '[.[] | select(.user.type == "Bot")] | length'

# ── IDEMPOTENCY: check for an existing open PR before gh pr create ───────────────
gh pr list --head "$BRANCH" --json number,state          # reuse first OPEN; do not duplicate
git ls-remote --heads origin "$BRANCH"                   # remote-only branch? extend, don't rebuild

# ── MERGED-STATE SYNC: gh pr view MERGED proves only API state; fetch first ──────
git fetch origin --quiet && git log origin/main --oneline -10
git show origin/main:path/to/file 2>/dev/null && echo PRESENT || echo DELETED

# ── BULK SYNC: drop statusCheckRollup from the bulk list (504s at 50+ PRs) ───────
gh pr list --state open --limit 100 \
  --json number,title,headRefName,baseRefName,headRefOid,mergeable,mergeStateStatus
gh pr view <n> --json statusCheckRollup                  # fetch CI per-PR (never 504s)
```

### Detailed Steps

#### `gh pr list` pagination: default-30 truncation AND the hard-cap trap

Two layered failures bite list enumeration:

1. **Omitting `--limit`** — every `gh <noun> list` subcommand defaults to **30** rows (`gh run list` is 20, `gh workflow list` is 50). With `--json`, the visual truncation cue is gone, so a validation query returns `0` matches even when the rows exist (e.g. `state:*` labels that sort late alphabetically fall off page one). No error, no warning, no exit-code signal.
2. **Passing `--limit N`** — `--limit` is a **hard cap, not a page size**. `--limit 100` returns at most 100 rows, full stop. A repo with 200 dependabot PRs silently passes a `jq length == 0` "no remaining PRs" check after looking at only the first 100. Raising it to `--limit 10000` just turns the bug into a magic-number game (what about 10001?) plus a wasted round-trip.

The trap, as it surfaced — a `_list_open_prs_remaining` helper for a "is this repo done?" gate:

```python
def _list_open_prs_remaining(self) -> list[dict[str, Any]]:
    result = _gh_call(["pr", "list", "--repo", f"{owner}/{repo}",
                       "--state", "open", "--limit", "100",
                       "--json", "number,title,headRefName,autoMergeRequest"], check=False)
    return json.loads(result.stdout or "[]")   # silently caps at 100 → false "done"
```

**The fix for true enumeration: `gh api --paginate`.** Only `gh api` exposes the REST `Link: rel="next"` walker (`gh pr list --paginate` errors with `unknown flag: --paginate`):

```python
def _list_open_prs_remaining(self) -> list[dict[str, Any]]:
    owner, repo = get_repo_info(self.repo_root)
    try:
        result = _gh_call(["api", "--paginate",
            f"/repos/{owner}/{repo}/pulls?state=open&per_page=100"], check=False)
        raw_pulls = json.loads(result.stdout or "[]")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        logger.error("Could not list open PRs: %s", exc)
        return [{"number": -1, "title": "(unknown: gh api pulls failed)"}]  # NOT done → investigate
    # Normalise REST snake_case → gh-CLI camelCase so callers don't break (see table below)
    return [{"number": pr.get("number"), "title": pr.get("title", ""),
             "headRefName": (pr.get("head") or {}).get("ref", ""),
             "autoMergeRequest": pr.get("auto_merge")} for pr in raw_pulls]
```

`per_page=100` is the REST maximum; `--paginate` keeps fetching until no `next` link. No caller-visible cap.

**Decision rule.** Use `gh pr list --limit N` only for a *bounded* view (the N most recent, interactive inspection, provably small sets). Use `gh api --paginate /repos/.../<resource>?...&per_page=100` whenever the correctness of a downstream gate, count, or idempotency check depends on seeing **every** row, or the count is unbounded/growing (dependabot floods, issue backlogs). For scripts that must stay on `gh <noun> list`, always pass an explicit `--limit` well above the expected count (labels 200; issues/PRs 500, 1000 for huge repos) and assert the count is not exactly the limit.

**REST → gh-CLI field-name mapping** (normalise at the boundary when migrating from `gh pr list --json` to `gh api`):

| `gh pr list --json` key | REST `/pulls` key | Note |
| ----------------------- | ----------------- | ---- |
| `headRefName` / `headRefOid` | `head.ref` / `head.sha` | REST nested |
| `baseRefName` / `baseRefOid` | `base.ref` / `base.sha` | REST nested |
| `autoMergeRequest` | `auto_merge` | object or null |
| `mergeStateStatus` | `mergeable_state` | str |
| `mergeCommit.oid` | `merge_commit_sha` | flat snake_case |
| `isDraft` | `draft` | different name |
| `author.login` / author type | `user.login` / `user.type` | different key name |

Same in both shapes: `number`, `title`, `body`, `state`, `labels[*].name`.

#### Discovering failing PRs via `gh pr list --json`

For PR-driven automation (enumerate by PR, not by issue), filter on two fields. A PR is "failing" if `mergeStateStatus == "BLOCKED"` AND at least one `statusCheckRollup` check has `conclusion` in {FAILURE, CANCELLED, TIMED_OUT}. Skip `isDraft` PRs.

```python
def _discover_failing_prs(repo_root: str) -> dict[int, int]:
    """Returns {pr_number: pr_number} — the synthetic-key invariant."""
    try:
        result = _gh_call(["pr", "list", "--limit", "1000",
            "--json", "number,isDraft,statusCheckRollup,mergeStateStatus"],
            cwd=repo_root, check=False)
        if result.returncode != 0:
            logger.error("Failed to enumerate PRs: %s", result.stderr)
            return {}
        prs = json.loads(result.stdout or "[]")
    except (json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        logger.error("Error processing PR list: %s", exc); return {}
    failing: dict[int, int] = {}
    for pr in prs:
        if pr.get("isDraft", False):                      continue
        if pr.get("mergeStateStatus") != "BLOCKED":       continue
        if not any(c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT")
                   for c in pr.get("statusCheckRollup", [])):  continue
        n = pr.get("number")
        if isinstance(n, int):
            failing[n] = n   # synthetic-key invariant: pr_num in both positions
    return failing
```

Always use `--json` (text output silently caps at 30 regardless of `--limit`). Cost is one `gh pr list` call per repo; for repos over 1000 PRs use `--paginate` via `gh api`.

#### Bot-PR discovery: union a `user.type=='Bot'` sweep with a synthetic issue key

An issue→PR resolver ("for each open issue, find its closing `Closes #N` PR") **cannot by construction** see a PR that has no originating issue. Dependabot/Renovate/Lychee/Sweep PRs have no issue body and no `Closes #N` line, so the driver reports "nothing to do" while bot PRs pile up. You cannot fix this by raising a limit or adding an `--author` filter — the discovery **direction** is wrong. Add a complementary PR→PR sweep:

```python
def _discover_bot_prs(self) -> dict[int, int]:
    """Enumerate every open user.type=='Bot' PR. Returns {pr_number: pr_number}."""
    owner, repo = get_repo_info(self.repo_root)
    try:
        result = _gh_call(["api", "--paginate",
            f"/repos/{owner}/{repo}/pulls?state=open&per_page=100"], check=False)
        raw = json.loads(result.stdout or "[]")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        logger.error("Could not enumerate bot PRs: %s", exc); return {}
    bots: dict[int, int] = {}
    for pr in raw:
        if (pr.get("user") or {}).get("type") != "Bot":   # REST discriminator
            continue
        n = pr.get("number")
        if isinstance(n, int):
            bots[n] = n   # synthetic-key invariant
    return bots
```

**Discriminate on `user.type == "Bot"`, NOT the login string** `dependabot[bot]`. A login allowlist ages out the moment an org installs a new bot app; `user.type` is a stable REST-contract field set by GitHub for every app-backed account.

**Union it onto the existing dedup map**, using the PR number as both key and value (the synthetic issue key):

```python
deduped: dict[int, int] = {}          # {issue_or_synthetic_key: pr_number}
# ... issue-driven pass fills deduped[issue_num] = pr_num (key != value) ...
if self.options.include_bot_prs:
    for pr_num in self._discover_bot_prs():
        if pr_num in deduped.values():     # already covered via a Closes link
            continue
        deduped[pr_num] = pr_num           # synthetic key: key == value
        self.shared_pr_issues.setdefault(pr_num, [pr_num])
```

**Short-circuit downstream steps with `_is_bot_pr_mode`.** Any step that consumes the `(issue, pr)` pair and would call `gh issue view <issue>` (or advise/planning/learn on the issue body) must guard, because `gh issue view 127` 404s on a synthetic key — and `gh issue comment 127` could post to a real but unrelated issue:

```python
def _is_bot_pr_mode(self, issue_number: int, pr_number: int) -> bool:
    return issue_number == pr_number   # the synthetic-key invariant
# guard every call site:
if self.options.enable_advise and not self._is_bot_pr_mode(issue_number, pr_number):
    advise_findings = self._run_advise(issue_number)
```

Ship behind `include_bot_prs: bool = True` (opt-OUT via `--no-include-bot-prs`), because the silent blind-spot failure (driver reports "done" while bot PRs remain) is worse than doing extra work on a bot PR. Pin each guarded call site with a unit test so a future refactor can't drop the guard. A single union beats two passes: half the cold-start cost, one atomic done-gate, one log/exit code.

#### Idempotency: guard every PR-creation chokepoint

Duplicate PRs for one issue arise from three independent gaps; fixing one leaves the others able to duplicate (real case: issue #768 → PRs #942 CLOSED, #962 MERGED, #967 OPEN, two on the same branch with divergent history).

| Chokepoint | Guard | Mechanism |
| ---------- | ----- | --------- |
| Worktree creation | `_remote_branch_exists` | `git ls-remote --heads origin <branch>`; if present, extend remote history (`git fetch origin <branch>` + `git worktree add <path> -b <branch> origin/<branch>`) instead of rebuilding from base |
| PR creation | `_find_open_pr_for_head` | `gh pr list --head <branch> --json number,state`; return the existing OPEN PR instead of creating |
| Agent prompt | reuse instruction | tell the agent to run `gh pr list --head <branch>` FIRST and reuse an open PR |

Root causes: (1) the worktree manager checked branch existence **locally only** (`git rev-parse --verify`), so a remote-only `<issue>-auto-impl` branch pushed by another machine was rebuilt from base and its commits discarded → divergent PR. (2) `gh_pr_create` ran `gh pr create` unconditionally. (3) the prompt never told the agent to reuse.

**KISS tradeoff:** keep the open-PR lookup **OPEN-only** (`--state open`). Do NOT broaden it to skip on closed/merged PRs — a closed/merged prior PR legitimately means the issue may need fresh work; broadening trades a duplicate bug for a false-skip bug. **Testing note:** prepending a pre-flight `ls-remote`/`pr list` call breaks tests asserting `mock.call_count == N` or ordered `side_effect`; update counts and mind lazy attributes (the remote-extend path never accesses `base_branch`, so it triggers no detect call).

#### Merged state is not proof of remote sync (read AND write directions)

Three state surfaces diverge until `git fetch` reconciles the local view: (1) **GitHub API state** (`gh pr view --json state,mergedAt` — authoritative for "did GitHub accept the merge"), (2) **local remote-tracking ref** `origin/main` / `origin/<branch>` (updates only on `git fetch`, can be hours stale), (3) **working tree / local branch** (the checked-out branch's files, not main's).

**READ:** `gh pr view` returning MERGED proves only (1). Before reporting "merged to main" or auditing what's in main: `git fetch origin && git log origin/main --oneline -10`; for deletion audits use `git show origin/main:<path>` (non-zero exit = absent), never `ls`/`find` on the working tree. For broad audits, clone fresh (`git clone --depth 5 --branch main`) so the audit surface is guaranteed to be main. Pin every audit sub-agent to an explicit ref in its prompt — sub-agents default to scanning the checked-out branch and confidently report "Wave 2 didn't execute" against a feature branch's files.

**WRITE (symmetric trap):** a matching branch **NAME** does not imply matching **CONTENT**. When a parallel process (e.g. `.issue_implementer`) pushes a different implementation to `origin/<issue>-impl`, your local `<issue>-impl` is stale relative to the real PR head; merging main and pushing would fast-forward-clobber the wrong implementation. Before pushing to a PR branch you did not author end-to-end:

```bash
git fetch origin --quiet
git rev-parse HEAD; git rev-parse origin/<pr-branch>   # differ? local is NOT the PR head — STOP
git worktree add /tmp/sync-<branch> --detach origin/<pr-branch>   # --detach pins REMOTE head
( cd /tmp/sync-<branch> && git switch -c sync-<branch> && git merge origin/main )
git merge-base --is-ancestor origin/<pr-branch> HEAD \
  && echo "FF-safe" || { echo "would clobber the PR — STOP"; exit 1; }
unset GH_TOKEN GITHUB_TOKEN; git push origin HEAD:<pr-branch>
```

`git worktree add <dir> <branch>` checks out the **local** ref; use `--detach origin/<branch>` to pin the remote head.

#### Bulk PR-sync: statusCheckRollup 504, silent no-op, stale-failing misclassification

Three compounding bugs each silently neuter a bulk PR-sync tool (`hephaestus.github.fleet_sync`); any one makes it "succeed" while rebasing nothing.

1. **`statusCheckRollup` 504.** `gh pr list --json ...,statusCheckRollup --limit 100` returns **HTTP 504 Gateway Timeout** at ~50+ open PRs because the rollup aggregates every check on every PR. Request only cheap fields in the bulk list and fetch CI **per-PR** with `gh pr view <n> --json statusCheckRollup` (one PR per call never 504s). A flaky per-PR fetch downgrades *that* PR to `CI = UNKNOWN` (falls through to rebase) — never abort the whole run.
2. **Silent no-op on list failure.** Code that catches the gh error and `return []` logs "No open PRs" and exits SUCCESS while skipping the whole queue. Distinguish "no PRs" (return `[]`) from "list failed" (**raise**) so the run's exit status reflects the unprocessed queue.
3. **Stale-failing misclassification.** Marking ANY `CI = FAILURE` PR as FAILING strands the queue: after a fix lands on main, every BEHIND PR shows its OLD failing run. Gate FAILING on `mergeStateStatus == CLEAN`; a BEHIND/BLOCKED + MERGEABLE red PR must classify as **OUTDATED** so it gets rebased (re-running CI fresh). CONFLICTING stays CONFLICTED.

| mergeable | mergeStateStatus | CI state | Classification | Action |
| --------- | ---------------- | -------- | -------------- | ------ |
| MERGEABLE | CLEAN | FAILURE | FAILING | skip (genuine PR-specific failure) |
| MERGEABLE | BEHIND / BLOCKED | FAILURE (stale) | OUTDATED | rebase (re-runs CI fresh) |
| MERGEABLE | BEHIND / BLOCKED | SUCCESS / UNKNOWN | OUTDATED | rebase |
| CONFLICTING | DIRTY | any | CONFLICTED | per-PR conflict resolution |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| `gh pr list` without `--limit` (or with text output) | Relied on default behaviour for a count/validation query | Default caps at 30 rows; `--json` removes the visual truncation cue, so the query returns 0 matches even when rows exist (e.g. late-sorting `state:*` labels fall off page one). No error or exit-code signal. | Always pass an explicit `--limit` in scripts; never use text output for automation. When a writer reports success and a reader reports zero, suspect the reader. |
| `gh pr list --limit 100` (or `10000` "to be safe") for a "no remaining PRs" check | Assumed a generous cap covers the worst case | `--limit` is a hard cap, not a page size; a repo with 200 dependabot PRs returns exactly 100 and falsely reports "done". Raising it is a magic-number game (what about 10001?) plus a wasted round-trip. | If correctness depends on counting all rows, a capped API is the wrong tool — use `gh api --paginate`. |
| `gh pr list --paginate` | Assumed the noun-list subcommands accept `--paginate` like `gh api` | `unknown flag: --paginate`; only `gh api` exposes the `Link: rel="next"` walker. | Drop to `gh api --paginate /repos/.../<resource>?...&per_page=100` for unbounded enumeration. |
| Migrate `gh pr list --json` → `gh api /pulls` without a normalisation layer | Swapped the call, kept downstream consumers | REST returns snake_case nested shapes (`head.ref`, `auto_merge`, `user.type`); consumers reading `pr["headRefName"]` silently get `None`/`KeyError`. | Normalise REST → camelCase at the boundary so callers don't need to know which path produced the data. |
| Issue-driven discovery only (`_find_pr_for_issue` via `Closes #N`) | For each open issue, search for its closing PR | Dependabot/Renovate PRs have no `Closes #N` line and no originating issue; the issue→PR direction cannot see them. | Add a complementary PR→PR `user.type=='Bot'` sweep; do not try to fix it in the search query. |
| Detect bots by login allowlist (`author.login in {"dependabot[bot]", ...}`) | Hard-code known bot logins | Ages out when a new bot app appears; login strings are not stable; maintenance burden every review. | Discriminate on `user.type == "Bot"` — a stable REST-contract field that catches every app-backed account. |
| Stuff bot PR numbers into `--issues <pr-number>` | Pass PR numbers as if they were issue numbers | `gh issue view <pr-number>` 404s — PRs and issues share the numbering space, so a matching int does not mean the entities match; the error reads `not found` with no hint. | Synthetic keys require `_is_bot_pr_mode` guards everywhere a `gh issue *` call appears. |
| Local-only branch existence check in the worktree manager | `git rev-parse --verify <branch>` only | A remote-only `<issue>-auto-impl` branch (pushed by another machine) was invisible, so it was rebuilt from base and the remote commits discarded → divergent duplicate PR. | Consult `git ls-remote --heads origin <branch>` before rebuilding; extend remote history with `git fetch` + `worktree add -b <branch> origin/<branch>`. |
| Unconditional `gh pr create` | Always ran `gh pr create` | A re-run opened a second PR on the same head branch. | Guard the single creation chokepoint with `gh pr list --head <branch>` and return the existing OPEN PR. |
| Broaden `find_pr_for_issue` to skip on closed/merged PRs | Make the lookup also skip when a closed PR exists | False skips when an issue legitimately needs fresh work after an abandoned PR; trades a duplicate bug for a false-skip bug. | Keep the lookup OPEN-only; enforce idempotency at the creation/worktree boundaries instead. |
| Trusted `gh pr view <N> --json state` MERGED as proof commits are in main | Reported "all merged" without `git fetch`; audit sub-agents scanned the stale feature-branch working tree | API state and remote-ref state diverge — local `origin/main` refreshes only on `git fetch`; working-tree scans show the checked-out branch, not main. | Always `git fetch && git log origin/main --oneline` before claiming a merge propagated; for deletion audits use `git show origin/main:<path>` or a fresh shallow clone; pin sub-agents to an explicit ref. |
| Trusted a local branch named `512-impl` as the PR's content and merged main into it | About to push a local `<issue>-impl` to update a PR a parallel process also targeted | A matching branch NAME does not mean matching CONTENT; the OPEN PR head lived on `origin/512-impl` with a different implementation — pushing would have clobbered it. | Before pushing, compare `git rev-parse HEAD` vs `origin/<branch>` and commit subjects; re-derive from `origin/<branch>` via `--detach` and gate the push on `merge-base --is-ancestor`. |
| Bulk `gh pr list --json ...,statusCheckRollup --limit 100` | Fetch CI state for the whole queue in one call | HTTP 504 at ~50+ PRs — the rollup aggregates every check on every PR. | Never request `statusCheckRollup` in a bulk list; fetch CI per-PR via `gh pr view <n>`. |
| Catch the bulk `gh` list error and `return []` | Treat a failed list as an empty list | Tool logged "No open PRs" and exited SUCCESS while silently skipping the entire queue. | A list failure is fatal — raise so the exit status reflects the unprocessed queue; only a true empty result returns `[]`. |
| Classify ANY `CI=FAILURE` PR as FAILING (skip) | Skip every red PR | After a fix lands on main, every BEHIND PR shows its old failing run, so the tool skips all of them and rebases nothing. | Gate FAILING on `mergeStateStatus == CLEAN`; a BEHIND/BLOCKED + MERGEABLE red PR is OUTDATED → rebase (re-runs CI fresh). |
| Abort the whole run when one per-PR `gh pr view` is flaky | One transient fetch error blocks the queue | A single flaky fetch would strand every remaining PR. | Downgrade the flaky PR to `CI=UNKNOWN` (falls through to rebase); never abort the run for one PR. |

## Results & Parameters

### Recommended `--limit` per gh list subcommand (when staying on `gh <noun> list`)

| Subcommand | Default | Scripted limit | Subcommand | Default | Scripted limit |
| ---------- | ------- | -------------- | ---------- | ------- | -------------- |
| `gh label list` | 30 | 200 | `gh release list` | 30 | 200 |
| `gh issue list` | 30 | 500 | `gh run list` | 20 | 200 |
| `gh pr list` | 30 | 500 (1000 large) | `gh repo list <org>` | 30 | 1000 |

Assert the count is not exactly the limit (which implies more rows exist); otherwise raise the limit. For correctness-gated enumeration, prefer `gh api --paginate ...&per_page=100` (no cap, same HTTP cost as a generous `--limit` when items exceed one page).

### Idempotency guard helpers

| Helper | Mechanism | File (example) |
| ------ | --------- | -------------- |
| `_remote_branch_exists` | `git ls-remote --heads origin <branch>` → extend, don't rebuild | `worktree_manager.py` |
| `_find_open_pr_for_head` | `gh pr list --head <branch> --json number,state` → return OPEN PR | `github_api.py` |
| reuse instruction | `gh pr list --head <branch>` first, reuse open PR | `prompts/implementation.py` |

### Merged-state verification one-liners

```bash
# READ — before claiming "PR N merged to main":
git fetch origin --quiet && \
  COMMIT=$(gh pr view "$N" --json mergeCommit --jq '.mergeCommit.oid') && \
  git log origin/main --oneline | grep -q "${COMMIT:0:8}" && \
  echo "VERIFIED in origin/main" || echo "NOT YET — wait and re-fetch"

# WRITE — before pushing a local branch B to update a PR you didn't author end-to-end:
git fetch origin --quiet && \
  if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/$B)" ]; then echo "IN SYNC"
  elif git merge-base --is-ancestor "origin/$B" HEAD; then echo "FF-safe"
  else echo "DIVERGED — pushing would clobber the PR. STOP."; fi
```

### Bulk PR-sync invariants

- Bulk list field set (cheap, no 504): `number,title,headRefName,baseRefName,headRefOid,mergeable,mergeStateStatus`.
- `mergeStateStatus == CLEAN` is the *only* state in which a red PR is a genuine PR-specific failure (skip). Every other red state on a MERGEABLE PR is stale → rebase.
- A `gh` list failure must change the run's exit status; a true empty result must not.
- A per-PR CI fetch failure affects only that PR (→ UNKNOWN), never the whole run.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/ProjectHephaestus | `_discover_failing_prs` enumeration + synthetic-key handling (issue #819 / PR #852) | 1143 automation tests pass incl. 25 new discovery tests |
| HomericIntelligence/ProjectHephaestus | "is repo done?" check migrated to `gh api --paginate` (PR #839, closes #838) | Ran against a repo with 200+ dependabot PRs that was silently passing |
| HomericIntelligence (15 repos) | Org-wide label provisioning `gh label list` default-30 truncation (2026-05-29) | Validation reported 0/3 per repo; `--limit 200` returned correct counts |
| HomericIntelligence/ProjectHephaestus | Bot-PR `user.type=='Bot'` union + `_is_bot_pr_mode` (PR #849, closes #848) | 3017 unit + 47 shell pass; 16+ missed dependabot PRs across 7 repos |
| HomericIntelligence/ProjectHephaestus | Duplicate-PR idempotency guards (PR #1022, closes #1018) | Full automation suite (1091 tests) green; root case issue #768 → 3 PRs |
| HomericIntelligence/ProjectOdyssey | Merged-state read-direction false positives (PRs #5458/#5459/#5460, 2026-05-26) | Audit swarm on stale feature-branch working tree hallucinated "Wave 2 didn't execute" |
| ProjectKeystone | Merged-state write-direction divergence (PR #571 / branch `512-impl`, 2026-05-29) | Parallel `.issue_implementer` pushed a different implementation; caught before a clobbering push |
| HomericIntelligence/ProjectHephaestus | Bulk PR-sync 504 + silent no-op + stale-classify (`fleet_sync`, PRs #1028/#1030, 2026-06-06) | Run listed 56 PRs and rebased 49 (7 genuine conflicts) |
