---
name: architecture-bot-pr-discovery-synthetic-issue-key
description: "When an automation tool resolves work via the issue→PR direction ('for each open issue, find its closing PR'), Dependabot PRs and other bot-authored PRs are architecturally invisible — they have no `Closes #N` link, so the resolver returns nothing. The fix is to union the issue-driven set with every open `user.type == 'Bot'` PR from `gh api --paginate /repos/.../pulls`, using the PR number as a synthetic issue key (same int in both positions of the dedup map). Downstream code that would call `gh issue view <issue_number>` must then short-circuit: a tiny helper `_is_bot_pr_mode(issue_number, pr_number)` returns `True` iff `issue_number == pr_number`, which is the synthetic-key invariant. The discriminator is `user.type == 'Bot'` (REST snake_case), NOT the login string `app/dependabot` — new bot apps continually appear, and login-based detection ages out. Use when: (1) building a driver that enumerates work by issue and discovers PRs through `Closes #N` parsing, (2) Dependabot or Renovate PRs are open but the driver reports 'nothing to do', (3) an `--all` flag changes the AUTHOR filter but not the discovery DIRECTION and bot PRs are still missed, (4) you're tempted to pass PR numbers as `--issues <pr-number>` and the downstream `gh issue view` 404s on you, (5) you're tempted to add a second pass (`--bot-prs-only`) and want to know why a unioned single pass is cleaner, (6) reviewing automation that calls human-only steps (advise / planning / Mnemosyne lookup) and needs to short-circuit them for synthetic-key bot PRs."
category: architecture
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - dependabot
  - bot-pr
  - issue-driven-discovery
  - synthetic-issue-key
  - ci-driver
  - automation-loop
  - user-type-bot
  - gh-api-paginate
  - closes-link
  - include-bot-prs
  - short-circuit-guard
  - hephaestus-automation
---

# Bot PRs Are Invisible to Issue-Driven Drivers — Union a `user.type=='Bot'` Sweep and Use the PR Number as a Synthetic Issue Key

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Stop the silent blind spot where a driver that resolves work as "for each open issue, find its closing PR via `Closes #N`" never touches Dependabot/Renovate/Lychee PRs that have no originating issue. Prescribe the three-helper pattern: (a) `_discover_bot_prs()` enumerates every open `user.type=='Bot'` PR via `gh api --paginate`, (b) union it into the issue-driven dedup map using the PR number as both key AND value (the synthetic-key invariant), (c) `_is_bot_pr_mode(issue, pr)` short-circuits any downstream step that would call `gh issue view <issue>` and 404 on the synthetic key. |
| **Outcome** | Replaces the issue→PR-only discovery in CI drivers with an issue-driven ∪ bot-driven union. Ship behind an `include_bot_prs` flag that defaults to `True`, with `--no-include-bot-prs` for the rare case the operator wants only human-authored work. Bot PRs flow through the rest of the driver with the synthetic-issue guard preventing 404s on advise / planning / Mnemosyne-lookup paths. |
| **Verification** | verified-ci — landed in ProjectHephaestus PR #849 (closes #848). 25 new unit tests including `TestBotPrDiscovery` and `TestIsBotPrMode` prove the union, the `issue==pr` rule, the advise short-circuit, and the gh-failure resilience; plus 6 bats tests pin the shell-script paginate/bot-count invariants. 3017 unit pass + 47 shell pass. |
| **History** | New skill — no amendments yet. |

## When to Use

- You are building or auditing an automation driver (CI driver, drive-green loop, batch-merge bot) that enumerates work by **issue** and then looks up the closing PR via `Closes #N` parsing of the PR body.
- An ecosystem-wide run reports "Driven: N repos" but live `gh pr list` per repo shows open Dependabot/Renovate/Lychee PRs the driver never touched.
- A repo has zero open human-filed issues, but multiple open bot-filed PRs — the driver reports "nothing to do" and silently exits clean.
- You are tempted to "just pass the PR numbers as `--issues <pr-number>`" and the downstream `gh issue view <pr-number>` is 404-ing. (PR and issue numbers share GitHub's numbering space — a matching int does NOT mean the entities match.)
- You are tempted to write a second invocation (`--bot-prs-only`) and want to know why a unioned single pass keeps the "is this repo done?" gate honest.
- An `--all` flag exists on the driver and you noticed it changes the **author filter** but not the **discovery direction** — bot PRs are still missed.
- Reviewing downstream automation steps (`advise`, `planning`, `Mnemosyne lookup`, `human reviewer ping`) and asking "what should this step do for a Dependabot PR?" — the answer is **short-circuit via `_is_bot_pr_mode`**, not "run anyway and let the 404 surface".
- A new bot app appeared (e.g. `app/sweep`, `app/socket-security`, `app/whitesource`) and your login-string detection (`if author == "dependabot[bot]"`) stopped catching it. Switch to `user.type == "Bot"`.

## Verified Workflow

### Quick Reference

```python
# 1. The bot-PR enumerator — single REST round-trip per repo via gh api --paginate.
def _discover_bot_prs(self) -> dict[int, int]:
    """Enumerate every open user.type=='Bot' PR on the repo.

    Returns {pr_number: pr_number} — the synthetic-key invariant:
    PR number is BOTH the dedup key AND the value.
    """
    owner, repo = get_repo_info(self.repo_root)
    result = _gh_call(
        ["api", "--paginate",
         f"/repos/{owner}/{repo}/pulls?state=open&per_page=100"],
        check=False,
    )
    raw_pulls = json.loads(result.stdout or "[]")
    bot_prs: dict[int, int] = {}
    for pr in raw_pulls:
        user = pr.get("user") or {}
        if user.get("type") != "Bot":  # REST snake_case, NOT login string
            continue
        number = pr.get("number")
        if isinstance(number, int):
            bot_prs[number] = number  # synthetic-key invariant
    return bot_prs

# 2. The downstream guard — one rule, used everywhere we'd call gh issue view.
def _is_bot_pr_mode(self, issue_number: int, pr_number: int) -> bool:
    """True iff issue == pr (the synthetic-key invariant from _discover_bot_prs)."""
    return issue_number == pr_number

# 3. The union — bolt onto the existing issue-driven dedup map.
# In _discover_prs, AFTER the issue-driven dedup map is built:
if self.options.include_bot_prs:
    bot_prs = self._discover_bot_prs()
    for pr_num in bot_prs:
        if pr_num in deduped.values():
            continue  # already covered via an issue Closes link — keep human path
        deduped[pr_num] = pr_num
        self.shared_pr_issues.setdefault(pr_num, [pr_num])

# 4. Short-circuit every downstream step that needs a human issue body.
# In _attempt_ci_fixes, before calling _run_advise (and planning, Mnemosyne, etc.):
if self.options.enable_advise and not self._is_bot_pr_mode(issue_number, pr_number):
    advise_findings = self._run_advise(issue_number)
# else: skip advise — bot PRs have no human-authored issue body to learn from
```

### Detailed Steps

#### The blind spot, exactly as it surfaced

The audit that triggered this skill: run `20260531T190615Z` of `drive-prs-green-ecosystem.sh` reported **"Driven: 8 repos"**. Live `gh pr list` per repo showed 7 of those 8 had a combined **16+ open Dependabot PRs** the driver never touched. The breakdown:

| Repo | Open Dependabot PRs the driver missed |
| ------ | ------------------------------------- |
| ProjectOdysseus | 5 |
| ProjectAchaeanFleet | 11 |
| ProjectAgamemnon | 1 |
| ProjectProteus | 4 |
| ProjectArgus | 3 |
| ProjectCharybdis | 5 |
| ProjectHermes | 5 |

The driver's own header line 12 even acknowledged it: **"issue-driven discovery only: PRs without `Closes #<open-issue>` are invisible"**. The whole point of #848/#849 was making that statement false.

#### Why "issue-driven" can't see bot PRs

The driver's `_find_pr_for_issue(N)` works like:

```python
# For each open issue, look up its closing PR by scanning PR bodies for "Closes #N".
prs_for_issue_N = gh_api(
    f"/search/issues?q=is:pr+is:open+repo:{owner}/{repo}+'Closes #{N}'"
)
```

This is the issue→PR direction. It cannot, by construction, see a PR that has no originating issue. Dependabot PRs are filed straight from the GitHub Actions/Dependabot machinery — there is **no issue body**, **no `Closes #N` line**, **no human author**. The same goes for Renovate, Lychee (link-checker bot), Sweep, Socket Security, WhiteSource, and any future bot app.

You cannot fix this by raising a limit, changing a filter, or adding a `--bot-author` flag to the existing search. The discovery **direction** is wrong — you must add a complementary PR→PR enumeration that doesn't go through issues at all.

#### The synthetic-key invariant: PR number is both key AND value

The cleanest union strategy uses the **PR number as a synthetic issue key**. In Python:

```python
deduped: dict[int, int] = {}    # {issue_number_or_synthetic_key: pr_number}

# Existing issue-driven pass — issue → its closing PR
for issue_num in open_issues:
    pr_num = self._find_pr_for_issue(issue_num)
    if pr_num is not None:
        deduped[issue_num] = pr_num    # issue 42 → PR 123

# NEW union pass — bot PRs, using PR num as both sides of the map
if self.options.include_bot_prs:
    bot_prs = self._discover_bot_prs()       # {127: 127, 130: 130, ...}
    for pr_num in bot_prs:
        if pr_num in deduped.values():
            continue                          # PR already covered via Closes link
        deduped[pr_num] = pr_num              # synthetic key: PR 127 → PR 127
        self.shared_pr_issues.setdefault(pr_num, [pr_num])
```

After this loop, `deduped` mixes two kinds of entries:

| Entry | Meaning | `key == value`? |
| ----- | ------- | --------------- |
| `{42: 123}` | Issue 42, closed by PR 123 (human path) | No |
| `{127: 127}` | Bot PR 127, no originating issue (synthetic key) | **Yes** |

The downstream code consumes `(issue_number, pr_number)` pairs. The synthetic-key invariant — `issue_number == pr_number` — is what lets every downstream step detect bot-PR mode without a separate `is_bot` flag stored anywhere.

#### The downstream guard: `_is_bot_pr_mode`

Every step that would normally do something with the issue (read its body, post a comment on it, run `advise` on its description, look up its Mnemosyne history) needs a guard:

```python
def _is_bot_pr_mode(self, issue_number: int, pr_number: int) -> bool:
    return issue_number == pr_number
```

Why this signature instead of `is_bot_pr(pr_number)`? Because the synthetic-key invariant is a property of the **pair**, not of the PR alone. A PR number `127` might be:

- A human PR that closes issue `42` → pair `(42, 127)` → not bot mode.
- A bot PR with no issue → pair `(127, 127)` → bot mode.

The two-arg helper makes the rule self-documenting: **the issue field is synthetic iff it equals the PR field.**

Call sites that must short-circuit:

```python
# advise (asks Mnemosyne for prior learnings about the issue's topic)
if self.options.enable_advise and not self._is_bot_pr_mode(issue_number, pr_number):
    advise_findings = self._run_advise(issue_number)

# planning (decomposes the issue body into a task plan)
if self.options.enable_planning and not self._is_bot_pr_mode(issue_number, pr_number):
    plan = self._run_planning(issue_number)

# learn-on-merge (writes a Mnemosyne skill referencing the closed issue)
if not self._is_bot_pr_mode(issue_number, pr_number):
    self._run_learn(issue_number, pr_number)

# gh issue view (would 404 on synthetic key)
if not self._is_bot_pr_mode(issue_number, pr_number):
    body = subprocess.check_output(["gh", "issue", "view", str(issue_number), "--json", "body"])
```

If you forget one, the `gh issue view 127` call 404s on a synthetic-key PR — the error message is `not found` with no hint that the cause was a synthetic key. That is the failure-to-watch-for; add a unit test (`TestIsBotPrMode`) that covers every call site so a future refactor cannot drop the guard.

#### Why `user.type == 'Bot'`, not `author == 'dependabot[bot]'`

The REST `/pulls` response includes a `user` object per PR:

```json
{
  "number": 127,
  "title": "chore(deps): bump foo from 1.2.3 to 1.2.4",
  "user": {
    "login": "dependabot[bot]",
    "type": "Bot",            ← THE DISCRIMINATOR
    "site_admin": false
  },
  "body": "Bumps [foo] from 1.2.3 to 1.2.4."   ← no "Closes #N"
}
```

The discriminator is `user.type == "Bot"`, not the login string `"dependabot[bot]"`. Reasons:

1. **New bot apps continually appear.** Today it's `dependabot[bot]`, `renovate[bot]`, `lychee[bot]`. Tomorrow it's `sweep[bot]`, `socket-security[bot]`, `whitesource[bot]`. A login-string allowlist ages out the moment an org installs a new bot. `user.type == "Bot"` is set by GitHub at account-creation time for any app-backed account and catches all of them.
2. **`user.type` is part of the public REST contract.** The login string is not stable (an org can rename or replace a bot account). The type is.
3. **One-line check vs. growing allowlist.** Compare `if user.get("type") == "Bot"` against `if user.get("login") in {"dependabot[bot]", "renovate[bot]", "lychee[bot]", "sweep[bot]", ...}` — the second one is a maintenance burden every PR review must remember to update.

If you need to **distinguish** bot apps (e.g. only Dependabot, not Renovate), filter on login AFTER the `type == 'Bot'` predicate, not as the primary discriminator.

#### REST snake_case ↔ gh-CLI camelCase normalisation

`gh api /repos/.../pulls` returns REST shape; `gh pr list --json` returns camelCase. This skill uses REST throughout because `--paginate` requires `gh api`. The fields that matter for this skill:

| Concept | REST shape (`gh api`) | gh-CLI shape (`gh pr list --json`) |
| ------- | --------------------- | ----------------------------------- |
| PR number | `number` (int) | `number` (int) — same |
| Author user object | `user` (object) | `author` (object) — different key name |
| Author login | `user.login` (str) | `author.login` (str) |
| **Author type discriminator** | **`user.type` (str: `"User"` or `"Bot"`)** | **`author.is_bot` (bool)** |
| PR body (for `Closes #N` parsing) | `body` (str) | `body` (str) — same |

If you ever rewrite to `gh pr list --json author,number,body`, the discriminator changes from `user.type == "Bot"` to `author.is_bot == True`. Same logic, different field name. Pick one path and normalise at the boundary; don't mix shapes in the same call site.

#### Cost: one `gh api --paginate` call per repo

The cost added by the bot-PR sweep is exactly **one** `gh api --paginate /repos/.../pulls?state=open&per_page=100` call per repo per driver run. For repos under 100 PRs that is a single HTTP round-trip; for the largest dependabot-flooded repos in this ecosystem (ProjectAchaeanFleet at 11 + the human-authored PRs) it is still one paginate sweep, identical in cost to the `gh api --paginate` call already used by `tooling-gh-pr-list-limit-cap-use-api-paginate.md`'s "is repo done?" check. There is no per-PR cost — the entire sweep is the existing paginate response, filtered in-memory.

#### `include_bot_prs=True` default, with explicit opt-out

The flag default matters. If the user has to remember to pass `--include-bot-prs`, the bug recurs (drivers shipped before the flag existed still miss bot PRs by default). Make it opt-OUT:

```python
@dataclass
class CIDriverOptions:
    include_bot_prs: bool = True   # opt-OUT, not opt-IN
    # ... rest

# argparse:
parser.add_argument(
    "--no-include-bot-prs",
    dest="include_bot_prs",
    action="store_false",
    help="Skip bot-authored PRs (Dependabot, Renovate, etc.). "
         "Default is to INCLUDE them via the user.type=='Bot' sweep.",
)
```

Reasons to opt-out (`--no-include-bot-prs`) are narrow: an operator who explicitly wants to drive only human-authored work, e.g. for a release-candidate dry-run before bot churn lands. The default for every automation invocation is "see everything".

#### Why a single union beats a second pass

A reasonable-sounding alternative is "do two driver invocations per repo: one issue-driven, one bot-PR-only". That fails for three reasons:

1. **Cold-start cost doubles.** Every driver invocation re-opens the gh CLI session, re-reads config, re-enumerates the repo. Two passes is two cold-starts per repo. Across 8 repos in the ecosystem that's 16 cold-starts instead of 8.
2. **The done-gate fragments.** The "is this repo done?" gate consumes the deduped set after BOTH passes complete. With two invocations you have to externally sequence "driver-A done → driver-B done → check repo done", which is fragile (what if B fails after A succeeded?). Single union: one driver run, one gate evaluation.
3. **Operator UX.** Two invocations means two log files per repo, two exit codes to interpret, two failure modes ("which one failed?"). One invocation with the union means one log, one exit code, one clear failure mode.

The single-union pattern is also where the `_is_bot_pr_mode` short-circuit naturally lives — it's a method on the same driver class, called at every downstream branch.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Issue-driven only via `_find_pr_for_issue(N)` for every open issue | For each issue, search for a PR whose body has `Closes #N` | Dependabot PRs have NO `Closes #N` line — they're filed straight from the GitHub Actions / Dependabot machinery without an originating issue. Same for Renovate, Lychee, Sweep, Socket Security. The issue→PR direction cannot, by construction, see them. | The issue→PR direction CAN'T see PRs that have no issue. Add a complementary PR→PR enumeration; do not try to fix this in the search query. |
| Stuff Dependabot PR numbers into `--issues <pr-number>` and hope downstream tolerates them | Pass PR numbers on the CLI as if they were issue numbers | The driver calls `gh issue view <pr-number>` during the advise step. That 404s on PR numbers because PRs and issues share the GitHub numbering space — a matching int does NOT mean the entities match. The error message is `not found` with no hint that the cause was a synthetic key, so the symptom looks like "the issue was deleted" rather than "this isn't an issue". | Synthetic keys require explicit downstream guards (`_is_bot_pr_mode`) everywhere `gh issue view`, `gh issue comment`, or any other `gh issue *` call appears. Don't rely on the int alone; check the invariant. |
| Run with `--all` and assume it would broaden discovery | The driver had an `--all` flag; expectation was that it widened the search direction | `--all` toggles "include non-bot author PRs in issue-driven discovery" — it changes the AUTHOR FILTER, not the discovery DIRECTION. Issue-driven still misses bot PRs that have no Closes link. The flag was orthogonal to the actual blind spot. | The discovery DIRECTION must change, not the filter on top of an existing direction. If your `--all` flag still loses items, the data flow is the bug, not the filter. |
| Write a separate `--bot-prs-only` second invocation per repo | Two passes per repo: pass A enumerates issue-driven, pass B enumerates bot-only | (a) Doubles cold-start cost (CLI re-init, config reload, gh session). (b) Requires external sequencing — what if A finishes and B fails? (c) Fragments the "is this repo done?" gate so it cannot be evaluated atomically. (d) Doubles log files and exit codes per repo, hurting operator UX. The same code path is cleaner. | A single discovery function that unions both streams keeps the done-gate honest, the operator UX clean, and the cold-start cost halved. Bolt the union onto the existing dedup map; don't fork the driver. |
| Detect bots by login string allowlist: `if author.login in {"dependabot[bot]", "renovate[bot]"}` | Hard-code the known bot logins as a set | (a) Ages out the moment an org installs a new bot app. (b) Maintenance burden: every PR review must remember to update the set. (c) Login strings are not stable — an org can rename a bot account. (d) Misses `lychee[bot]` (link-checker), `sweep[bot]`, `socket-security[bot]`, `whitesource[bot]` and every future app. | Discriminate on `user.type == "Bot"` (REST contract field, set at account creation by GitHub). One-line check that catches every app-backed account, present and future. |
| Use `gh pr list --author "app/dependabot" --json number` to enumerate bot PRs | Sub-bug of the login-string attempt: rely on `--author` filter | (a) Filter accepts only one author at a time; doesn't union across bots. (b) Repeats the `gh pr list --limit` silent-cap trap (see `tooling-gh-pr-list-limit-cap-use-api-paginate`) — a repo with 100+ Dependabot PRs is silently truncated. (c) Same login-ages-out problem. | Use `gh api --paginate /repos/.../pulls?state=open&per_page=100` for the sweep — one call, unbounded, type-filterable in-memory. |

## Results & Parameters

### The three-helper pattern (copy-paste ready)

```python
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _discover_bot_prs(self) -> dict[int, int]:
    """Enumerate every open user.type=='Bot' PR on the repo.

    Uses gh api --paginate to walk Link: rel="next" headers — no cap, no
    silent truncation. Returns {pr_number: pr_number} (the synthetic-key
    invariant: PR number is BOTH key AND value).

    Conservative on failure: returns {} so the issue-driven pass remains
    authoritative when gh is unavailable. Logs the error for the operator.
    """
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
        logger.error("Could not enumerate bot PRs for %s/%s: %s", owner, repo, exc)
        return {}

    bot_prs: dict[int, int] = {}
    for pr in raw_pulls:
        user = pr.get("user") or {}
        if user.get("type") != "Bot":   # REST snake_case discriminator
            continue
        number = pr.get("number")
        if isinstance(number, int):
            bot_prs[number] = number    # synthetic-key invariant
    return bot_prs


def _is_bot_pr_mode(self, issue_number: int, pr_number: int) -> bool:
    """Single-rule detector: True iff issue == pr (the synthetic-key invariant).

    Use this as a guard anywhere the driver would otherwise call:
    - gh issue view <issue_number>   (would 404 on synthetic key)
    - gh issue comment <issue_number>
    - advise(issue_number)           (no human body to learn from)
    - planning(issue_number)         (no body to decompose)
    - learn(issue_number, pr_number) (Mnemosyne entry would reference a non-issue)
    """
    return issue_number == pr_number


# Patch into the existing _discover_prs(self) AFTER the issue-driven dedup map
# is built and BEFORE the function returns:
def _discover_prs(self) -> dict[int, int]:
    deduped: dict[int, int] = {}

    # ... existing issue-driven discovery populates `deduped` ...

    if self.options.include_bot_prs:
        bot_prs = self._discover_bot_prs()
        for pr_num in bot_prs:
            if pr_num in deduped.values():
                continue   # already covered via an issue Closes link
            deduped[pr_num] = pr_num
            self.shared_pr_issues.setdefault(pr_num, [pr_num])

    return deduped
```

### REST `/pulls` shape — every field this skill touches

```json
{
  "number": 127,
  "title": "chore(deps): bump anthropic from 0.42.0 to 0.43.0",
  "state": "open",
  "user": {
    "login": "dependabot[bot]",
    "type": "Bot",
    "id": 49699333,
    "site_admin": false
  },
  "body": "Bumps [anthropic](https://github.com/anthropics/...) from 0.42.0 to 0.43.0.\n<details><summary>Release notes</summary>...",
  "labels": [{"name": "dependencies"}, {"name": "python"}],
  "head": {"ref": "dependabot/pip/anthropic-0.43.0", "sha": "abc..."},
  "base": {"ref": "main", "sha": "def..."},
  "auto_merge": null,
  "draft": false
}
```

The only field needed for the discovery decision is `user.type`. The PR number, title, head ref, etc. flow through the existing pipeline unchanged.

### Configuration: `include_bot_prs` default and opt-out

```python
@dataclass
class CIDriverOptions:
    include_bot_prs: bool = True   # default ON — opt-out, not opt-in
    enable_advise: bool = True
    enable_planning: bool = True
    # ...

# CLI plumbing
parser.add_argument(
    "--no-include-bot-prs",
    dest="include_bot_prs",
    action="store_false",
    help="Skip bot-authored PRs (Dependabot, Renovate, Lychee, etc.). "
         "Default is to include them via the user.type=='Bot' sweep.",
)
```

Default ON because: the silent-truncation failure mode (driver reports "done" while bot PRs remain) is far worse than the false-positive failure mode (driver does extra work on a bot PR). If you flip the default to OFF, every driver shipped before someone remembers `--include-bot-prs` reverts to the old blind spot.

### Downstream short-circuit checklist

Every call site that consumes the `(issue_number, pr_number)` pair MUST guard with `_is_bot_pr_mode`. Audit your driver for these patterns:

| Pattern in code | Reason to guard | Guarded form |
| --------------- | --------------- | ------------ |
| `gh issue view <issue_number>` | Would 404 on synthetic key | `if not _is_bot_pr_mode(...): gh issue view ...` |
| `gh issue comment <issue_number>` | Posts to a PR number's issue slot — may post to a real but unrelated issue! | `if not _is_bot_pr_mode(...): gh issue comment ...` |
| `_run_advise(issue_number)` | No human body to learn from | `if not _is_bot_pr_mode(...): advise(...)` |
| `_run_planning(issue_number)` | No body to decompose into tasks | `if not _is_bot_pr_mode(...): plan(...)` |
| `_run_learn(issue_number, pr_number)` | Mnemosyne entry would reference a non-issue | `if not _is_bot_pr_mode(...): learn(...)` |
| `mnemosyne.search(issue_topic)` | Topic is the dependency name, not a feature | Often safe to keep; verify your search treats bot PRs gracefully |

Pin each call site with a unit test that asserts the short-circuit fires when `issue_number == pr_number`. A future refactor that adds a new downstream step but forgets the guard will be caught by the test suite, not by a 404 in production.

### Verification evidence

PR #849 in ProjectHephaestus landed this change. The test suite:

- **`TestBotPrDiscovery`** (in `tests/unit/automation/test_ci_driver.py`): proves the `gh api --paginate` call shape, the `user.type == 'Bot'` filter, the synthetic-key invariant (`bot_prs[pr_num] == pr_num`), and resilience when gh returns non-zero or non-JSON.
- **`TestIsBotPrMode`**: proves the `issue == pr` rule, the inequality cases (human PRs), and that the helper is used as a guard at every advise / planning / learn call site.
- **Six bats tests** in `tests/integration/shell/test_drive_prs_green_bot_prs.bats`: pin the shell-script paginate path and the bot-count invariants visible to operators in the run log.
- **3017 unit pass + 47 shell pass** in CI on the PR.

The audit that triggered the work: run `20260531T190615Z` of `drive-prs-green-ecosystem.sh` reported "Driven: 8 repos" while 16+ Dependabot PRs were open across 7 of those 8 repos. After #849 lands, the same script enumerates those PRs in the next run.

### Related skills

- `tooling-gh-pr-list-limit-cap-use-api-paginate.md` — same "use `gh api --paginate` for unbounded enumeration" pattern at the gh-CLI level. This skill builds on it: the `_discover_bot_prs` helper uses exactly the paginate call documented there. If you find yourself reaching for `gh pr list --limit 100 --author dependabot[bot]`, read that skill first to learn why the limit cap silently truncates.
- `tooling-hephaestus-automation-loop-drive-green-broken-design.md` — the broader audit of the drive-green loop's design bugs. The bot-PR blind spot documented in THIS skill is one of the four layered issues; the loop-drive-green skill covers the others (phase-model bugs, HEPH_LOOP_INDEX gate, `--issues required` argparse failure). Cross-reference when scoping fixes to the loop runner.
- `automation-loop-early-exit-zero-work-convergence.md` — when the loop's "zero-work convergence" check appears to fire but failing PRs remain, suspect a discovery blind spot first. The bot-PR sweep documented here was the missing piece for that early-exit logic to be honest.
- `workflow-github-issues-individual-per-fix-for-automation-loop.md` — companion skill on how to scope automation work as issues (not as PRs). The corollary documented here: when work CAN'T be scoped as an issue (bot PRs), you need the synthetic-key escape hatch instead of forcing the work into the issue model.

### Quick audit recipe — find drivers in your ecosystem that have this blind spot

```bash
# Find every Python file that resolves PRs via _find_pr_for_issue or "Closes #N" parsing
grep -rln "_find_pr_for_issue\|Closes #" --include="*.py" .

# For each one, check whether _discover_bot_prs (or equivalent) exists alongside
for f in $(grep -rln "_find_pr_for_issue" --include="*.py" .); do
  if ! grep -q "user.type.*Bot\|_discover_bot_prs\|include_bot_prs" "$f"; then
    echo "BLIND SPOT: $f resolves PRs via issues but has no bot-PR sweep"
  fi
done

# Confirm on a known-flooded repo: how many bot PRs would the driver miss?
gh api --paginate /repos/OWNER/REPO/pulls?state=open\&per_page=100 \
  | jq '[.[] | select(.user.type == "Bot")] | length'
```

If the audit prints "BLIND SPOT" for a driver, apply the three-helper pattern from "Quick Reference" above.
