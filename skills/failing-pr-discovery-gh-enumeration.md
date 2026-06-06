---
name: failing-pr-discovery-gh-enumeration
description: "Discover failing open PRs via gh CLI using `gh pr list --json number,isDraft,statusCheckRollup,mergeStateStatus`. Filter by check conclusions (FAILURE/CANCELLED/TIMED_OUT) and mergeStateStatus==BLOCKED. Use synthetic-issue-key pattern (pr_num==issue_num) for consistency with issue-driven discovery. Use when: (1) automating PRs without relying on Closes #N issue mapping, (2) need to enumerate BLOCKED PRs from CI failures, (3) discovering work via PR-enumeration instead of issue-enumeration."
category: ci-cd
date: 2026-06-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - gh-pr-list
  - statusCheckRollup
  - mergeStateStatus
  - pr-discovery
  - check-failures
  - BLOCKED-state
  - synthetic-issue-key
  - gh-json
  - automation-loop
  - drive-green-pattern
---

# Discover Failing Open PRs via gh pr list With Synthetic Issue Keys

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Document the `gh pr list --json` pattern for discovering open PRs that are BLOCKED on failed CI checks, suitable for PR-driven automation loops that don't rely on issue→PR mapping. Use synthetic-issue-key pattern (pr_num==issue_num) for downstream consistency. |
| **Outcome** | Shipped in ProjectHephaestus issue #819 / PR #852 (feat: Implement #819). All 1143 automation tests pass, including 25 new tests for `_discover_failing_prs` enumeration and synthetic-key handling. |
| **Verification** | verified-ci (full automation test suite passes; deployed in drive-green-ecosystem loop) |
| **History** | New skill — no amendments yet. |

## When to Use

- You are building an automation driver (CI driver, drive-green loop, batch-merge bot) that enumerates work by **PR**, not by issue.
- You need to discover PRs that are BLOCKED on failed CI checks (FAILURE/CANCELLED/TIMED_OUT conclusions) to attempt automatic remediation.
- Your driver does NOT rely on parsing `Closes #N` from PR bodies — it treats PR numbers as the primary work unit.
- You want to filter open PRs by their merge state and check status, not by issue keywords or labels.
- You need a consistent discovery pattern that works with bot PRs (which have no originating issue) and human PRs alike.
- You are tempted to use `gh pr list --limit 100 --state OPEN` and want to know why `--json` with `statusCheckRollup` is the correct approach for failing PRs.

## Verified Workflow

### Quick Reference

```bash
# Enumerate all open PRs with their check status and merge state
gh pr list --limit 1000 --json number,isDraft,statusCheckRollup,mergeStateStatus

# Filter by BLOCKED state and check failures (in Python)
for pr in prs:
    if pr["mergeStateStatus"] == "BLOCKED" and \
       any(c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT") 
           for c in pr.get("statusCheckRollup", [])):
        failing_prs[pr["number"]] = pr["number"]  # synthetic key: pr_num==pr_num
```

### Detailed Steps

#### Why `gh pr list --json` is the right tool

The `gh pr list` command with `--json` output is designed for filtering and enumeration:

1. **Returns structured JSON** — each PR is a complete object with all fields needed for decision-making.
2. **Honors `--limit` and pagination** — `--limit 1000` ensures you get all PRs up to 1000; for larger repos use `--paginate` to walk all pages.
3. **Fields available**: `number`, `title`, `state`, `isDraft`, `statusCheckRollup`, `mergeStateStatus`, `author`, `labels`, `milestone`, `body` and more.
4. **No silent truncation** — unlike `gh pr list` with text output (which caps at 30 items by default), `--json` respects `--limit`.

#### The filter: `statusCheckRollup` and `mergeStateStatus`

```python
# REST shape (what gh pr list --json returns)
{
  "number": 852,
  "title": "feat: Implement #819",
  "isDraft": false,
  "statusCheckRollup": [
    {
      "context": "test (unit)",
      "description": "Tests passed",
      "state": "SUCCESS",
      "conclusion": "SUCCESS",
      "url": "https://..."
    },
    {
      "context": "lint",
      "description": "Found 5 issues",
      "state": "FAILURE",
      "conclusion": "FAILURE",
      "url": "https://..."
    }
  ],
  "mergeStateStatus": "BLOCKED",
  "author": {"login": "claude-haiku", "type": "Bot"}
}
```

The two key fields:

| Field | Meaning | Values | When to filter |
|-------|---------|--------|-----------------|
| **`mergeStateStatus`** | Can this PR be merged as-is? | BLOCKED, CLEAN, DIRTY, UNSTABLE, HAS_HOOKS, UNKNOWN | Filter by `== "BLOCKED"` to find PRs unable to merge due to required checks |
| **`statusCheckRollup`** | List of all CI checks run on the PR | Array of check objects with `conclusion` | Filter each check's `conclusion` for FAILURE/CANCELLED/TIMED_OUT |

A PR is "failing" if:
- `mergeStateStatus == "BLOCKED"` (repo rules say it can't merge), AND
- At least one check in `statusCheckRollup` has `conclusion` in {FAILURE, CANCELLED, TIMED_OUT}

#### The synthetic-issue-key invariant: `pr_number == pr_number`

The discovery pattern mirrors the synthetic-key approach from `architecture-bot-pr-discovery-synthetic-issue-key.md`:

```python
def _discover_failing_prs(self, repo_root: str) -> dict[int, int]:
    """Discover all open BLOCKED PRs with failed checks.
    
    Returns {pr_number: pr_number} — the synthetic-key invariant.
    For consistency with downstream code expecting (issue_number, pr_number) pairs,
    we use pr_number in both positions. This makes the code path identical whether
    work came from an issue or a PR.
    """
    owner, repo = get_repo_info(repo_root)
    
    # Fetch all open PRs with check status
    result = _gh_call(
        [
            "pr", "list",
            "--limit", "1000",
            "--json", "number,isDraft,statusCheckRollup,mergeStateStatus"
        ],
        cwd=repo_root,
        check=False,
    )
    
    if result.returncode != 0:
        logger.error("Failed to list PRs: %s", result.stderr)
        return {}
    
    prs = json.loads(result.stdout or "[]")
    failing_prs: dict[int, int] = {}
    
    for pr in prs:
        # Skip drafts (not ready for automation)
        if pr.get("isDraft", False):
            continue
        
        # Check if PR is BLOCKED
        if pr.get("mergeStateStatus") != "BLOCKED":
            continue
        
        # Check if any required check has failed
        status_checks = pr.get("statusCheckRollup", [])
        has_failure = any(
            check.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT")
            for check in status_checks
        )
        
        if has_failure:
            pr_num = pr.get("number")
            if isinstance(pr_num, int):
                failing_prs[pr_num] = pr_num  # synthetic-key invariant
    
    return failing_prs
```

#### Why synthetic keys for PR-driven discovery

When the driver uses PR enumeration as the primary discovery path (not issue enumeration), the code pipeline still expects `(issue_number, pr_number)` pairs downstream:

- Existing patterns in automation loops assume: "for each (issue, pr) pair, attempt fixes"
- Bot PRs have no issue, so `issue_number` would be None
- Using `pr_number` in both positions — the synthetic key — keeps the code path identical
- Downstream guards (like `_is_bot_pr_mode(issue_num, pr_num)` returning `True` when they're equal) work automatically

Result: PR-driven discovery flows through the same pipeline as issue-driven discovery, with no special-case handling.

#### Filtering out drafts

Always skip `isDraft==True` PRs:

```python
if pr.get("isDraft", False):
    continue
```

Draft PRs are:
- Still under author development — operator hasn't explicitly opened them for review
- Not intended for automation — the author may be force-pushing or rewriting history
- Likely to have flaky CI results — not a stable target for fixes

The only exception is if your automation is specifically designed for drafts (e.g., a bot that prepares drafts for human review). For general-purpose "find PRs to fix" discovery, skip drafts.

#### The `--limit 1000` choice

- `--limit 1000` covers repos up to 1000 open PRs, which is well beyond typical repos (the ecosystem's largest has ~16 open PRs).
- For repos larger than 1000, use `gh pr list --paginate --json ...` to walk all pages.
- Always use `--json` (not text output) — text output silently caps at 30 items.

#### Cost: one `gh pr list` call per repo

The cost of this discovery is exactly **one** `gh pr list --limit 1000 --json ...` call per repo per driver run. It is a single API call that returns all PRs with full metadata — no per-PR round-trips. For repos under 1000 PRs it is one HTTP round-trip; larger repos use `--paginate` for one continuous stream of paginated results.

### Integrating with downstream automation

After `_discover_failing_prs` returns a dict like `{852: 852, 857: 857}`, the automation loop processes each pair:

```python
# Example: attempt fixes for each discovered PR
failing_prs = self._discover_failing_prs(repo_root)

for issue_num, pr_num in failing_prs.items():
    # For PR-driven discovery, issue_num == pr_num (synthetic key)
    
    # Short-circuit steps that need a human issue body
    if not self._is_bot_pr_mode(issue_num, pr_num):
        advise_findings = self._run_advise(issue_num)  # has an issue to learn from
        plan = self._run_planning(issue_num)  # has a body to decompose
    
    # Always run the fixing step — it works on (issue, pr) regardless
    self._attempt_ci_fixes(issue_num, pr_num)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh pr list --state OPEN` with text output | Default gh pr list without `--json` | Text output silently caps at 30 items (hardcoded `defaultPageSize`), regardless of `--limit` flag. A repo with 100 open PRs returns only 30. Same as the `gh pr list --limit silent-cap trap` documented in `tooling-gh-pr-list-limit-cap-use-api-paginate.md`. | Always use `--json` for `gh pr list` to bypass the output-format cap. Text output is for human terminals only — never for automation. |
| Filter by `pr.state == "OPEN"` and check for status using `--jq` filter | Attempt to do filtering on the CLI side with `jq` | `statusCheckRollup` is a complex nested array — `jq` one-liners become unmaintainable. Also, `mergeStateStatus` information requires querying the PR after its checks run, which happens asynchronously. Filtering in-memory is cleaner and more resilient. | Fetch the full PR objects and filter in code — the JSON response is small enough that in-memory filtering is cleaner than shell piping. |
| Use `gh pr list` without a limit | Assume the default behavior is "all PRs" | Default is 30 items. Without `--limit`, you only see the 30 most recent open PRs. For a repo with 100 open PRs, you miss 70. | Always explicitly set `--limit` (or use `--paginate` for unbounded enumeration). Never rely on default limits in automation. |
| Use issue-driven discovery only: `gh issue list --state OPEN` | Assume issue enumeration works for PR work | (a) Issues and PRs are different entities — an issue without an associated PR is not actionable for "fix failing PR" workflows. (b) A PR without an originating issue (bot PRs) is invisible to issue-driven discovery. (c) A PR closed by a different unrelated issue still shows up in issue-driven results. | PR-driven discovery (`gh pr list`) is the correct primary source when work is scoped by PR, not by issue. Use issue-driven discovery for issue-workflow automation; use PR-driven discovery for PR-workflow automation. |

## Results & Parameters

### Discovery function (copy-paste ready)

```python
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _discover_failing_prs(repo_root: str) -> dict[int, int]:
    """Discover all open BLOCKED PRs with failed CI checks.
    
    Uses `gh pr list --limit 1000 --json` to enumerate PR state and check status.
    
    Args:
        repo_root: Path to the repo root (for cwd context of gh cli calls)
    
    Returns:
        dict[int, int]: Mapping of {pr_number: pr_number} (synthetic-key invariant).
                        Ready to pass to downstream automation loops expecting
                        (issue_number, pr_number) pairs.
    
    Resilience: Returns {} (empty dict) on gh CLI failure, logs the error for the
               operator. This allows the automation to gracefully degrade.
    """
    try:
        result = _gh_call(
            [
                "pr", "list",
                "--limit", "1000",
                "--json", "number,isDraft,statusCheckRollup,mergeStateStatus"
            ],
            cwd=repo_root,
            check=False,
        )
        
        if result.returncode != 0:
            logger.error("Failed to enumerate PRs in %s: %s", repo_root, result.stderr)
            return {}
        
        prs: list[dict[str, Any]] = json.loads(result.stdout or "[]")
    except (json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        logger.error("Error processing PR list for %s: %s", repo_root, exc)
        return {}
    
    failing_prs: dict[int, int] = {}
    
    for pr in prs:
        # Skip drafts — not ready for automation
        if pr.get("isDraft", False):
            continue
        
        # Require BLOCKED merge state
        if pr.get("mergeStateStatus") != "BLOCKED":
            continue
        
        # Require at least one failed check
        status_checks = pr.get("statusCheckRollup", [])
        has_failure = any(
            check.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT")
            for check in status_checks
        )
        
        if not has_failure:
            continue
        
        pr_num = pr.get("number")
        if isinstance(pr_num, int):
            failing_prs[pr_num] = pr_num  # synthetic-key invariant
    
    logger.info("Discovered %d failing PRs in %s", len(failing_prs), repo_root)
    return failing_prs


def _is_bot_pr_mode(issue_number: int, pr_number: int) -> bool:
    """Detect synthetic-key PR-driven discovery: True iff issue_number == pr_number.
    
    Use this guard before calling steps that need a human issue body:
    - _run_advise(issue_number)
    - _run_planning(issue_number)
    - gh issue view <issue_number>
    """
    return issue_number == pr_number
```

### Raw `gh pr list --json` output shape

```json
[
  {
    "number": 852,
    "title": "feat: Implement #819",
    "isDraft": false,
    "statusCheckRollup": [
      {
        "context": "test (unit)",
        "description": "Tests passed",
        "state": "SUCCESS",
        "conclusion": "SUCCESS",
        "startedAt": "2026-06-06T12:34:56Z",
        "completedAt": "2026-06-06T12:45:30Z",
        "url": "https://github.com/.../runs/12345"
      },
      {
        "context": "pr-policy",
        "description": "PR policy check failed",
        "state": "FAILURE",
        "conclusion": "FAILURE",
        "startedAt": "2026-06-06T12:34:56Z",
        "completedAt": "2026-06-06T12:37:15Z",
        "url": "https://github.com/.../runs/12346"
      }
    ],
    "mergeStateStatus": "BLOCKED"
  },
  {
    "number": 857,
    "title": "fix: Address review feedback",
    "isDraft": false,
    "statusCheckRollup": [
      {
        "context": "test (unit)",
        "description": "Tests passed",
        "state": "SUCCESS",
        "conclusion": "SUCCESS",
        "startedAt": "2026-06-06T12:00:00Z",
        "completedAt": "2026-06-06T12:15:00Z",
        "url": "https://github.com/.../runs/12340"
      },
      {
        "context": "required-reviewer",
        "description": "Awaiting review",
        "state": "PENDING",
        "conclusion": null,
        "startedAt": "2026-06-06T12:00:00Z",
        "completedAt": null,
        "url": "https://github.com/.../pulls/857"
      }
    ],
    "mergeStateStatus": "BLOCKED"
  }
]
```

### Verification evidence

- **PR #852 in ProjectHephaestus** (issue #819): Implements this discovery pattern for the drive-green-ecosystem loop.
- **Test coverage**: 25 new unit tests in `tests/unit/automation/test_drive_pr_discovery.py`:
  - `TestDiscoverFailingPrs`: Proves the `gh pr list --json` shape, the filtering by `mergeStateStatus` and check conclusions, synthetic-key invariant
  - `TestIsBotPrMode`: Proves the helper works for both human PRs and synthetic-key bot PRs
  - Edge cases: drafts, repos with no failing PRs, gh CLI timeouts, malformed JSON
- **Integration tests**: 6 bats tests verify the shell invocation shape and the output format
- **CI result**: All 1143 automation tests pass

### Related skills

- `architecture-bot-pr-discovery-synthetic-issue-key.md` — the broader synthetic-key pattern when discovering bot PRs. This skill focuses on the gh CLI pattern for PR enumeration; that skill covers the downstream architectural usage (short-circuit guards, union with issue-driven discovery).
- `tooling-gh-pr-list-limit-cap-use-api-paginate.md` — explains why `--json` is necessary and why `--limit` silent-cap is a pitfall. This skill builds on it.
- `automation-loop-early-exit-zero-work-convergence.md` — when the loop's "zero-work convergence" reports no PRs to fix but failing PRs remain, suspect a discovery blind spot. This skill's pattern is the remedy.

### Quick audit recipe — find reporters using the wrong discovery

```bash
# Find automation code that claims "no PRs to fix" but failing PRs exist
gh pr list --state OPEN --json number,mergeStateStatus,statusCheckRollup | \
  jq '[.[] | select(.mergeStateStatus == "BLOCKED" and 
       any(.statusCheckRollup[]; .conclusion == ("FAILURE", "CANCELLED", "TIMED_OUT")))] | length'

# If that count > 0 but your automation reports 0, you're using the wrong discovery.
```
