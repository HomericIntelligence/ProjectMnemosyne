---
name: pr-enumeration-discovery-idempotency
description: "Use when: (1) gh pr list silently truncates results because the default limit is 30 and a repo has more open PRs, (2) gh label list or gh issue list silently drops entries past the default pagination limit, (3) Dependabot or other bot-authored PRs are invisible to issue-driven automation because they have no Closes #N link — use synthetic issue-key union pattern, (4) an automation tool creates duplicate PRs for the same issue because it lacks an idempotency check before calling gh pr create, (5) GitHub API reports a PR as merged but the remote ref and local working tree have not yet synced — merged state is not proof of remote sync, (6) a bulk PR-sync tool times out (HTTP 504) because gh pr list with statusCheckRollup at 50+ PRs is too heavy — fetch statusCheckRollup per-PR instead, (7) a bulk driver silently skips the whole PR queue by returning an empty list on a gh error instead of raising, (8) stale CI classification marks BEHIND/BLOCKED PRs as FAILING and skips them when they should be rebased, (9) a docstring promises a soft-fail (Empty dict on any lookup failure — discovery must never abort) but the except tuple catches only a subset of subprocess failure modes — a gh-CLI hang (subprocess.TimeoutExpired) or missing binary (OSError/FileNotFoundError) propagates uncaught, violating the contract, (10) the PLANNER phase re-plans an issue that already has an open closing PR — add a skip-gate that calls find_pr_for_issue before planning so plan and implement share identical skip semantics, (11) a MERGED closing-PR is not detected because discovery only searches open PRs — use find_merged_closing_pr to search merged PRs too, and close the issue if it is still open, (12) you are handed 'open issues to solve' as a human/agent — verify each on origin/main FIRST; an issue can be a ZOMBIE whose closing PR already merged (GitHub didn't auto-close or it was a duplicate), and re-implementing it is the duplicate-PR anti-pattern; gh issue list is a point-in-time snapshot, re-check gh issue view N before acting, (13) a local <issue>-auto-impl branch looks like it holds the right commits but has a SHA mismatch vs origin and a revert-shaped multi-file diff — it is built on a stale pre-merge base; an add/add cherry-pick conflict proves the file already exists on main"
category: ci-cd
date: 2026-06-15
version: "1.3.0"
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
  - subprocess-except
  - TimeoutExpired
  - soft-fail
  - symmetric-failure-modes
  - planner-skip-gate
  - merged-closing-pr
  - find-merged-closing-pr
  - real-head-branch
  - assumed-branch-name
  - zombie-issue
  - verify-on-main-first
  - gh-issue-list-snapshot-stale
  - stale-branch-base
  - add-add-cherry-pick-conflict
---

# PR Enumeration, Discovery, and Idempotency

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-15 |
| **Objective** | Canonical reference for correctly *finding* PRs (pagination, bot PRs, limit caps), filing them idempotently, reasoning about state divergence between the GitHub API and the remote, classifying a bulk PR queue for routing, using the canonical 4-tuple of subprocess failure modes when a soft-fail contract is in force, and gating the PLANNER phase against re-planning issues that already have open or merged closing PRs. |
| **Outcome** | Consolidated from 8 verified skills covering gh enumeration, synthetic-issue-key bot discovery, duplicate-PR prevention, merged-state sync verification, bulk PR-sync classification, (v1.1.0) symmetric subprocess except-tuple coverage for soft-fail discovery helpers, (v1.2.0) planner skip-gate + merged-closing-PR detection to prevent 5.5h zombie-PR churn, and (v1.3.0) the operator/agent-side complement — verify each "open issue" on `origin/main` FIRST (it may be a zombie whose closing PR already merged or a duplicate), treat `gh issue list` as a point-in-time snapshot, and reject a stale `<issue>-auto-impl` branch whose revert-shaped diff / `add/add` cherry-pick conflict proves the work is already merged. |
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
- The **PLANNER** phase of an automation loop re-plans an issue that already has an open closing PR — the implementer phase skips it, but the planner ran first and consumed an agent call (and hit 529 retries). Add a skip-gate calling `_review_utils.find_pr_for_issue(issue)` before planning: plan and implement must use identical skip semantics.
- An issue stays open forever even after a PR with a valid `Closes #N` line merges — because discovery only searched `--state open` and never found the merged PR. Call `find_merged_closing_pr(issue)` against `--state merged` too; if a merged closing PR exists and the issue is still open, close the issue with `gh issue close N --comment "Closed by merged PR #M"`.
- You (a human or agent) are handed a list of "open issues to solve" — verify each on `origin/main` FIRST before implementing. An issue can be a ZOMBIE: its closing PR already merged (GitHub didn't auto-close, or the issue was reopened/duplicated). Grep the acceptance criteria against `git show origin/main:<file>`, and check `gh pr list --state all --search "<issue> in:body"` for a merged `Closes #N`. Re-implementing a zombie is the duplicate-PR anti-pattern. Also: `gh issue list` is a point-in-time snapshot — re-check `gh issue view N --json state` before acting, since a parallel merge can close an issue mid-session.
- A local branch named `<issue>-auto-impl` (or similar) appears to hold the relevant commits, but `git rev-parse <branch> origin/<branch>` shows a SHA mismatch and `git diff --stat origin/main..<branch>` is a huge multi-file diff that REVERTS already-merged work — the branch is built on a stale pre-merge base. Do NOT reuse it. A cherry-pick `add/add` conflict on a file is itself evidence that the file (and the work) already exists on main.
- A `git fetch origin <branch>` fails with exit 128 because the branch was resolved by assuming `{issue}-auto-impl` instead of calling `gh pr view <pr> --json headRefName` — the PR's real head branch may have been filed from a differently-named branch.

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

```python
# ── SOFT-FAIL DISCOVERY: the canonical 4-tuple for ANY gh-wrapped helper whose
#    docstring promises "Empty dict / [] on any lookup failure — never abort." ──
except (
    subprocess.CalledProcessError,   # gh exited non-zero
    subprocess.TimeoutExpired,       # gh hung past the timeout
    OSError,                         # missing binary / FileNotFoundError / permission
    json.JSONDecodeError,            # malformed stdout from --json
) as exc:
    logger.info("<helper> skipped: gh ... failed (%s)", exc)   # POLA: keep observable
    return {}
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
    """Returns {pr_number: pr_number} — the synthetic-key invariant.

    Empty dict on any lookup failure — discovery must never abort the drive.
    """
    try:
        result = _gh_call(["pr", "list", "--limit", "1000",
            "--json", "number,isDraft,statusCheckRollup,mergeStateStatus"],
            cwd=repo_root)
        prs = json.loads(result.stdout or "[]")
    except (
        subprocess.CalledProcessError,   # gh exited non-zero
        subprocess.TimeoutExpired,       # gh hung past its timeout
        OSError,                         # gh binary missing / permission denied
        json.JSONDecodeError,            # malformed --json stdout
    ) as exc:
        logger.info("Failing-PR discovery skipped: gh pr list failed (%s)", exc)
        return {}
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

#### Symmetric subprocess failure-mode handling: the canonical 4-tuple

A discovery helper whose docstring promises a soft-fail ("**Empty dict on any lookup failure — discovery must never abort the drive**") MUST catch every transient failure mode the wrapped binary can raise. Catching only 2 of the 4 canonical `subprocess`-wrapped CLI failure modes is a latent bug: the uncaught modes propagate out of the helper, get caught by an outer worker-thread exception handler, and mark the entire work item failed — directly violating the docstring contract. The bug is invisible until the rare failure mode fires in production.

The **canonical except 4-tuple** for any helper that wraps an external CLI (here, `gh`):

| Exception | Trigger | Realistic scenario |
| --------- | ------- | ------------------ |
| `subprocess.CalledProcessError` | Non-zero exit code (only when `check=True` or you raise it yourself) | gh reports auth error, rate limit, repo-not-found |
| `subprocess.TimeoutExpired` | Process hung past the `timeout=` argument | gh CLI hang on a slow API response; the canonical gh-CLI hang signal |
| `OSError` (incl. `FileNotFoundError`) | Binary missing, permission denied, broken pipe | gh not on PATH (CI without gh installed); EACCES on the binary; tmpfs full |
| `json.JSONDecodeError` | `--json` stdout was empty/truncated/garbled | gh wrote a banner before the JSON (auth migration warning); HTTP body returned as HTML |

`OSError` is the parent class of `FileNotFoundError`, so catching `OSError` covers the missing-binary case without naming it separately. Do **not** broaden to bare `except Exception` — that masks programmer errors (AttributeError from a malformed Mock, TypeError from a refactor that broke the signature) which you DO want to surface as bugs.

##### The cross-module symmetric check

When the same binary is wrapped by multiple helpers in the same module/package, their except tuples should **converge** on the same canonical set. An asymmetry is a code smell: either one helper is over-catching (masking a real bug class) or the other is under-catching (latent uncaught path). Worked example from `hephaestus.automation`:

```text
ci_driver.py:_discover_failing_prs   ← wraps `gh pr list`, soft-fails to {}
loop_runner.py:_count_failing_prs    ← wraps `gh pr list`, soft-fails to 0
```

Both wrap `gh pr list` against the SAME failure modes. They MUST converge on the same except tuple. The original `_discover_failing_prs` shipped with `(CalledProcessError, JSONDecodeError)` while `_count_failing_prs` shipped with `(TimeoutExpired, OSError)` — disjoint sets, no single helper covered the full 4-tuple. A 60-second `gh` hang in `_discover_failing_prs` propagated; the operator saw the whole multi-repo drive crash because two sister functions disagreed about what "transient" meant. The fix (PR #1097) was to widen both to the canonical 4-tuple.

##### Procedure to apply

1. **Grep the module for every wrapper of the same binary.**
   ```bash
   rg -n 'subprocess\.run.*"gh"' hephaestus/automation/
   rg -n '_gh_call' hephaestus/automation/
   ```
2. **Compare each helper's except tuple.** Are they catching the same set? If not, that's the bug.
3. **Widen each to the union** — for `gh`-wrapped soft-fail helpers, the canonical 4-tuple above.
4. **Preserve the observability log.** Demote `logger.error` to `logger.info` when the soft-fail is *expected* on the unhappy path (transient gh failure shouldn't trigger pages); a silent fallback with NO log line violates POLA and turns a 10-second debug into a multi-hour log archaeology project. Pattern:
   ```python
   logger.info("<helper> skipped: gh ... failed (%s)", exc)
   return {}   # or [] or 0 — match the soft-fail contract
   ```
5. **Add regression tests for each newly-caught exception.** Pattern after the existing `_returns_empty_on_gh_error` test:
   ```python
   def test_returns_empty_when_gh_times_out(monkeypatch):
       def fake_gh(*args, **kwargs):
           raise subprocess.TimeoutExpired(cmd=["gh", "pr", "list"], timeout=60.0)
       monkeypatch.setattr(ci_driver, "_gh_call", fake_gh)
       assert driver._discover_failing_prs() == {}

   def test_returns_empty_when_gh_binary_missing(monkeypatch):
       def fake_gh(*args, **kwargs):
           raise FileNotFoundError(2, "No such file or directory: 'gh'")
       monkeypatch.setattr(ci_driver, "_gh_call", fake_gh)
       assert driver._discover_failing_prs() == {}
   ```
   One regression test per exception type; the test name should encode the failure mode so a future reader sees "ah, the TimeoutExpired path is covered."

##### Why NOT broaden to `except Exception`

Catching the canonical 4-tuple keeps the soft-fail surface **precise**. Bare `except Exception` swallows the bug classes you want to surface:

- `AttributeError` from a malformed `Mock(spec=...)` in a unit test — silent test failure
- `TypeError` from a refactor that changed `_gh_call`'s signature — silent regression
- `KeyError` / `IndexError` from a JSON-shape change after the schema evolves — silent data corruption

If the codebase has a true "fail-safe orchestrator" need for `except Exception`, use the classification pattern from `silent-boundary-observability-exception-classification` (route expected to WARNING, unexpected to ERROR with `exc_info=True`). For a *discovery helper* with a tight, well-defined contract, stay with the explicit 4-tuple.

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
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        logger.info("Bot-PR discovery skipped: gh api failed (%s)", exc); return {}
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

#### Planner skip-gate: call find_pr_for_issue before planning

The IMPLEMENTER phase already skipped issues that had an existing open closing PR via
`_review_utils.find_pr_for_issue(issue)`. The PLANNER phase ran first with no such gate,
which let it re-plan an issue that already had an open closing PR — consuming an agent
call and repeatedly failing with 529 throttle errors during the churn window. The fix
(PR #1373) is to add the SAME skip-gate at the top of the planning routine:

```python
# In the planner (before calling the planning agent):
existing_pr = _review_utils.find_pr_for_issue(issue_number)
if existing_pr is not None:
    logger.info(
        "Planner skip: issue #%d already has open PR #%d", issue_number, existing_pr
    )
    return  # do not re-plan

# Continue with normal planning...
```

**Rule:** plan and implement MUST share identical skip semantics. If `find_pr_for_issue`
governs the implementer's skip, it MUST govern the planner's skip too — they are the
same guard applied at two consecutive phases of the same pipeline.

#### Merged closing-PR detection: find_merged_closing_pr

An open issue stays open forever if its closing PR was filed via `Closes #N` in the body
but the discovery routine only queries `--state open`. The issue never receives the
closing signal (GitHub auto-closes on merge only for the DEFAULT branch target). Fix
(PR #1373): add `find_merged_closing_pr(issue) -> int | None` that searches merged PRs:

```python
def find_merged_closing_pr(issue_number: int, repo: str) -> int | None:
    """Search merged PRs for one that closes this issue.

    Uses the SAME exact-line regex as find_pr_for_issue to avoid false matches:
    - ^Closes #1234\\b  matches "Closes #1234" at line start
    - Cannot match "Closes #12" when searching for #1234 (\\b stops at digit boundary)
    - Cannot match "Closes #12, #18" false-matching #1 (digit boundary guard)
    """
    pattern = re.compile(rf"^Closes #{issue_number}\b", re.MULTILINE)
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--repo", repo,
             "--search", f"Closes #{issue_number} in:body",
             "--json", "number,body"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        prs = json.loads(result.stdout or "[]")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            OSError, json.JSONDecodeError):
        return None
    for pr in prs:
        if pattern.search(pr.get("body") or ""):
            return pr["number"]
    return None
```

When `find_merged_closing_pr(issue)` returns a PR number and the issue is still open,
close the issue — do NOT re-plan:

```python
merged_pr = find_merged_closing_pr(issue_number, repo)
if merged_pr is not None:
    subprocess.run(
        ["gh", "issue", "close", str(issue_number), "--repo", repo,
         "--comment", f"Closed by merged PR #{merged_pr}"],
        check=True,
    )
    logger.info("Closed issue #%d via merged PR #%d", issue_number, merged_pr)
    return
```

**Search query note:** `gh pr list --search "Closes #N in:body"` is a pre-filter hint
to GitHub's search index; it is NOT a guarantee. Always apply the regex post-filter
(`pattern.search(body)`) to confirm the exact line match. The `--search` hint reduces
the candidate set from "all merged PRs" to a manageable handful; the regex removes
false positives from the candidate set.

#### Real head-branch resolution: always use get_pr_head_branch

Assuming a PR's head branch is named `{issue}-auto-impl` is wrong whenever the PR was
filed from a branch with a different name (e.g. a bundle branch named `1179-auto-impl`
that closes multiple issues including #1360). The log message is:

```
head branch is '1179-auto-impl' (not the assumed '1360-auto-impl')
git fetch origin 1360-auto-impl  → exit 128: couldn't find remote ref
```

Fix: always resolve the real head branch via `gh pr view`:

```python
def get_pr_head_branch(pr_number: int, repo: str) -> str:
    """Resolve the REAL head branch of a PR — never assume {issue}-auto-impl."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--repo", repo,
         "--json", "headRefName", "--jq", ".headRefName"],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return result.stdout.strip()
```

Every call site that previously constructed `f"{issue_number}-auto-impl"` to fetch or
check out a PR branch MUST be replaced with `get_pr_head_branch(pr_number, repo)`.
The assumed name is cheap to construct but wrong ~100% of the time when the filing
convention changes or multiple issues share one branch.

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
| Narrow-tuple soft-fail in a `gh`-wrapped discovery helper | Caught only `(subprocess.CalledProcessError, json.JSONDecodeError)` in `_discover_failing_prs` despite a docstring promising "Empty dict on any lookup failure — discovery must never abort" | A `gh` CLI hang (`subprocess.TimeoutExpired`) and a missing binary (`OSError` / `FileNotFoundError`) propagated uncaught, got swallowed by the outer worker-thread exception handler, and marked the entire work item failed — silently violating the soft-fail contract. The sister helper `_count_failing_prs` in the same package caught a disjoint subset `(TimeoutExpired, OSError)`, so neither covered the full failure surface. | A soft-fail helper wrapping an external CLI MUST catch the canonical 4-tuple `(subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError)`. Sister helpers wrapping the same binary must converge on the same tuple — an asymmetry IS the bug. Keep the precise tuple (do not broaden to `except Exception` — that masks `AttributeError`/`TypeError` from refactors and Mocks). Preserve a `logger.info(...)` line on the soft-fail path so it stays observable (POLA — a silent fallback with no log is a multi-hour debug). |
| Bare `except Exception` "to be safe" in a discovery helper | Replaced the narrow tuple with `except Exception` after one TimeoutExpired escape | Swallowed `AttributeError` from a malformed `Mock(spec=...)` in a unit test (silent test pass on a broken refactor) and `KeyError` from a JSON-schema drift after the `gh --json` field set changed (silent data corruption — discovery returned `{}` because the dict access blew up, not because gh failed). | The broad boundary is the wrong tool for a discovery helper with a tight contract. Stay with the explicit 4-tuple; use the classification pattern (`silent-boundary-observability-exception-classification`) only when fail-safe orchestrator semantics genuinely require `except Exception` AND you want unexpected types to log at ERROR. |
| Silent fallback to `{}` with NO log line | Caught the right exceptions but stripped the log call "to reduce log noise" | Operator saw "all repos clean" while every `gh pr list` was actually timing out. Debug took multiple hours of log archaeology before the timeout pattern was visible. | A soft-fail path is *expected*, not silent. Keep `logger.info("<helper> skipped: gh ... failed (%s)", exc)` — `INFO` (not `ERROR`) so it doesn't page on-call, but never *absent*. POLA: every fallback branch must be observable in logs. |
| Re-plan issue without checking for an existing open or merged closing PR | Planner ran unconditionally for every open issue; only the implementer had the `find_pr_for_issue` skip-gate | Automation-loop burned ~5.5h opening duplicate/zombie PRs for issue #1357 while PR #1358 already closed it; planner re-planned the issue on each iteration and the implementer tried to open more PRs, each failing with 529 throttle errors | Plan and implement MUST share identical skip semantics. Add `find_pr_for_issue(issue)` at the top of the planning routine; if it returns a PR, SKIP — do not call the planning agent. |
| Search only `--state open` PRs when checking for a closing PR | `find_pr_for_issue` queried `gh pr list --state open --search "Closes #N in:body"` | A merged PR with `Closes #N` was invisible; the issue stayed open and was re-implemented on every automation-loop iteration indefinitely | Also call `find_merged_closing_pr(issue)` against `--state merged`; if a merged closing PR exists and the issue is still open, close the issue with `gh issue close N --comment "Closed by merged PR #M"` — do not re-plan. |
| Match a PR to an issue by the assumed `{issue}-auto-impl` branch name | Constructed `f"{issue_number}-auto-impl"` to identify the PR's head branch, then ran `git fetch origin {issue}-auto-impl` | Fails exit 128 when the PR was filed from a differently-named branch (e.g. bundle branch `1179-auto-impl` that closes multiple issues including #1360); the assumed branch does not exist on the remote | Always resolve the real head via `get_pr_head_branch(pr_number, repo)` which calls `gh pr view <pr> --json headRefName`; never construct the branch name from the issue number. |
| Started implementing an "open" issue without checking if it was already merged | Took a list of open issues at face value and began planning/implementing each (a swarm of worktree agents was nearly spawned to re-implement #1367 and #1193) | #1367 was a duplicate of already-fixed #1368 (PR #1372 merged); #1193 was already merged via #1282 + #1376. Both fixes were live on `origin/main`. Re-implementing would have produced no-op duplicate PRs — the exact FM1 duplicate-PR-churn pattern. | Before implementing ANY "open" issue, verify ground truth on `origin/main`: grep the acceptance criteria against `git show origin/main:<file>`, and run `gh pr list --state all --search "<N> in:body"` for a merged `Closes #N`. If the work is live, close the zombie issue with a comment instead of opening a PR. |
| Trusted the initial `gh issue list` snapshot for the whole session | Reported "#1193 is still open, needs work" from a `gh issue list` taken at session start | PR #1376 (Closes #1193) merged mid-session and auto-closed the issue; the stale snapshot still showed it open. The "open issue" had become closed minutes earlier. | `gh issue list` is point-in-time. Re-check `gh issue view N --json state,stateReason` immediately before acting on any individual issue — concurrent merges (or your own just-merged PR) flip state mid-session. |
| Tried to reuse a local `1193-auto-impl` branch that appeared to hold the right 2 commits | Saw `git log origin/main..1193-auto-impl` list `feat: ReviewerProtocol` + `fix: ABC contract` and planned to cherry-pick them onto main | The branch's full `git diff --stat origin/main..1193-auto-impl` was 28 files that REVERTED the merged ci_driver decomposition (#1358/#1361) — it was built on a stale pre-decomposition base. Local and `origin/1193-auto-impl` had different SHAs. The cherry-pick hit an `add/add` conflict on `test_interfaces.py`, proving the file already existed on main (work already merged). | A branch whose NAME matches the issue is not proof of usable CONTENT (same lesson as the `512-impl` row, extended). Check `git rev-parse <branch> origin/<branch>` for SHA drift and `git diff --stat origin/main..<branch>` for a revert-shaped diff before reusing. An `add/add` cherry-pick conflict means the target already exists on main — stop and verify the work is already merged. |

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
| HomericIntelligence/ProjectHephaestus | Symmetric 4-tuple soft-fail in `_discover_failing_prs` (issue #1096 → PR #1097, merged via PR #1151, 2026-06-10) | Widened narrow `(CalledProcessError, JSONDecodeError)` except to canonical `(CalledProcessError, TimeoutExpired, OSError, JSONDecodeError)` in `hephaestus/automation/ci_driver.py:491-498`; aligned with sister helper `loop_runner._count_failing_prs:684`; added 2 regression tests in `tests/unit/automation/test_ci_driver_failing_pr_discovery.py` (gh timeout + missing-binary). All checks passed first try (pre-commit, unit/integration tests on Python 3.10–3.13, pr-policy, auto-merge, CodeQL). |
| HomericIntelligence/ProjectHephaestus | Planner skip-gate + merged-closing-PR detection + real-head-branch resolution (issue #1370 → PR #1373, 2026-06-15) | Fixed 3 root causes of ~5.5h zombie-PR churn against issues #1357/#1289/#1179: added `find_pr_for_issue` skip-gate to planner phase; added `find_merged_closing_pr` searching `--state merged` with exact-line `^Closes #N\b` regex; replaced assumed `{issue}-auto-impl` branch construction with `get_pr_head_branch(pr, repo)` via `gh pr view headRefName`. All CI checks passed (pr-policy, unit/integration, CodeQL). |
| HomericIntelligence/ProjectHephaestus | Operator-side zombie-issue triage of "3 open issues" #1367/#1199/#1193 (2026-06-15) | 2 of 3 were zombies: #1367 was a duplicate of #1368 (fix PR #1372 already merged to `main` — verified `log_on_error` param in `github/client.py` + 2 regression tests live), closed as duplicate with no PR; #1193 was already merged via #1282 + #1376 (ReviewerProtocol + abstract `BaseReviewer.run` live on `main`; #1376 auto-closed it mid-session though the initial `gh issue list` snapshot still showed OPEN), no work. A local `1193-auto-impl` branch looked like it held the 2 good commits but its 28-file diff REVERTED the merged #1358/#1361 decomposition (stale base; SHA mismatch vs `origin/1193-auto-impl`); a cherry-pick `add/add` conflict on `test_interfaces.py` proved the work was already on `main`. Only #1199 (markdownlint duplicate-job consolidation) was real → one signed PR #1377, merged green through required-checks-gate. |
