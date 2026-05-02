---
name: ci-cd-pixi-lock-stale-multi-pr-triage
description: "Use when: (1) multiple PR branches failing CI with 'lock-file not up-to-date' or pixi.lock stale errors, (2) CI runs show failures but on an old commit SHA (not current HEAD) — pixi.lock was pushed but CI ran on old commit, (3) need to re-trigger CI on a PR branch without making a real code change (gh run rerun --failed is the only reliable method), (4) pixi platform added (e.g. linux-aarch64) but a dependency (e.g. bats-core) isn't available for that platform in conda-forge, (5) Security Scan failing with 'missing gitleaks license' (infrastructure issue — GITLEAKS_LICENSE secret missing from org, skip these), (6) LRU-cached FastAPI settings mutation in tests causes wrong HTTP status codes, (7) Protocol method missing from async client implementation."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pixi, pixi.lock, stale-lock, ci-triage, multi-pr, gh-run-rerun, sha-mismatch, bats-core, gitleaks, lru-cache, protocol, platform-dependency]
---

# Cross-Repo CI Triage and Stale pixi.lock Remediation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Triage and fix CI failures across 7 repositories (42 open PRs) where most failures were stale pixi.lock files, with several distinct code/infra failure patterns |
| **Outcome** | Successful — pixi.lock regenerated and pushed for failing PRs; Scylla PRs went green; Myrmidons reruns triggered |
| **Verification** | verified-local — remediation executed against live repos, CI reruns triggered |

## When to Use

- Multiple PR branches failing CI with "lock-file not up-to-date" or pixi.lock stale errors
- CI runs show failures but on an old commit SHA (not current HEAD) after a fix was pushed
- Need to re-trigger CI without making a real code change (pushing empty commits does NOT work)
- A new pixi platform (e.g. `linux-aarch64`) was added but a dependency is unavailable for it
- Security Scan fails with "missing gitleaks license" — this is an infra issue, not a code fix
- FastAPI test assertions return wrong HTTP status codes because `get_settings` uses `@lru_cache()`
- An async client class is missing a method required by its Protocol interface

## Verified Workflow

### Quick Reference

```bash
# Step 1: Find all open PRs across org
gh repo list HomericIntelligence --json name,isArchived --limit 50 \
  --jq '[.[] | select(.isArchived == false) | .name] | sort[]'

# Step 2: Get CI status for all PRs in each repo
gh pr list --repo HomericIntelligence/$repo \
  --json number,title,statusCheckRollup --limit 50 \
  --jq '.[] | "#\(.number) [\(
    if (.statusCheckRollup | map(select(.conclusion == "FAILURE")) | length) > 0 then "FAILING"
    elif (.statusCheckRollup | map(select(.status == "IN_PROGRESS")) | length) > 0 then "pending"
    elif (.statusCheckRollup | map(select(.conclusion == "SUCCESS")) | length) > 0 then "green"
    else "no-checks" end)] \(.title[0:60])"'

# Step 3: Get specific failure logs
gh run view <run_id> --repo HomericIntelligence/$repo --job <job_id> --log 2>&1 | \
  grep -E "FAILED|ERROR|error::" | head -20

# Step 4: Fix stale pixi.lock
git checkout <branch>
pixi install   # regenerates pixi.lock
git add pixi.lock
git commit -m "chore: regenerate pixi.lock"
git push

# Step 5: Verify CI runs on NEW commit SHA (detect SHA mismatch)
remote_sha=$(git ls-remote origin <branch> | awk '{print $1}' | head -c8)
latest_run=$(gh run list --repo HomericIntelligence/<repo> --branch <branch> --limit 1 \
  --json headSha --jq '.[0].headSha[0:8]')
# If remote_sha != latest_run → CI ran on old commit; rerun needed

# Step 6: Re-trigger CI when SHA mismatch or empty commit didn't work
gh run list --repo HomericIntelligence/<repo> \
  --limit 5 --json databaseId,headSha,status,conclusion \
  --jq '.[] | select(.conclusion == "failure") | .databaseId' \
  --branch <branch> | while read run_id; do
  gh run rerun $run_id --repo HomericIntelligence/<repo> --failed
done
```

### Detailed Steps

#### Phase 1: Org-Wide CI Triage

List all repos, then scan PRs per repo:

```bash
# Get all non-archived repos
gh repo list HomericIntelligence --json name,isArchived --limit 50 \
  --jq '[.[] | select(.isArchived == false) | .name] | sort[]'

# For each repo, summarize PR CI health
REPO=HomericIntelligence/Myrmidons
gh pr list --repo $REPO --json number,title,statusCheckRollup --limit 50 \
  --jq '.[] | "#\(.number) [\(
    if (.statusCheckRollup | map(select(.conclusion == "FAILURE")) | length) > 0 then "FAILING"
    elif (.statusCheckRollup | map(select(.status == "IN_PROGRESS")) | length) > 0 then "pending"
    elif (.statusCheckRollup | map(select(.conclusion == "SUCCESS")) | length) > 0 then "green"
    else "no-checks" end)] \(.title[0:60])"'
```

#### Phase 2: Identify Root Cause Per Failure

```bash
# Get run ID for a failing PR
gh pr checks <pr_number> --repo $REPO

# Drill into logs for the failing job
gh run view <run_id> --repo $REPO --log 2>&1 | grep -E "FAILED|ERROR|error::" | head -30

# Common root cause signatures:
# "lock-file not up-to-date"  → stale pixi.lock
# "missing gitleaks license"  → GITLEAKS_LICENSE secret missing from org (SKIP)
# "bats: command not found"   → bats-core not in conda-forge for new platform
# "has no attribute 'get_diagnostics'" → protocol method missing
# "assert response.status_code == 429" fails → LRU cached settings in tests
```

#### Phase 3: Stale pixi.lock Fix

```bash
git checkout <branch>
pixi install          # regenerates pixi.lock from pixi.toml
git add pixi.lock
git commit -m "chore: regenerate pixi.lock"
git push origin <branch>

# Wait ~30 seconds, then verify CI fired on new SHA
remote_sha=$(git ls-remote origin <branch> | awk '{print $1}' | head -c8)
latest_run_sha=$(gh run list --repo $REPO --branch <branch> --limit 1 \
  --json headSha --jq '.[0].headSha[0:8]')
echo "Remote: $remote_sha  |  CI run: $latest_run_sha"
# If they match → CI is running on the correct commit
# If they differ → use gh run rerun (see below)
```

#### Phase 4: Re-trigger CI (SHA Mismatch or Empty Commit Didn't Work)

**Critical**: Pushing empty commits does NOT reliably trigger CI when:
- Workflows use `concurrency: cancel-in-progress: true`
- Workflow trigger is `pull_request: branches: [main]` (deduplicates same SHA)

Use `gh run rerun --failed` instead:

```bash
gh run list --repo $REPO --branch <branch> --limit 5 \
  --json databaseId,conclusion \
  --jq '.[] | select(.conclusion == "failure") | .databaseId' | \
while read run_id; do
  gh run rerun $run_id --repo $REPO --failed
  echo "Rerun triggered for run $run_id"
done
```

#### Phase 5: Fix bats-core Missing for New Platform

When `linux-aarch64` (or other non-standard platform) is added and `bats-core` isn't in conda-forge for it:

```toml
# BEFORE (broken — bats-core unavailable for linux-aarch64)
[dependencies]
bats-core = "*"

# AFTER (fixed — only install where available)
[target.linux-64.dependencies]
bats-core = "*"

[target.osx-arm64.dependencies]
bats-core = "*"

[target.osx-64.dependencies]
bats-core = "*"
# Do NOT add bats-core to linux-aarch64 dependencies
```

#### Phase 6: Fix LRU-Cached Settings in FastAPI Tests

When `get_settings` uses `@lru_cache()` and tests mutate attributes directly:

```python
# BROKEN — direct mutation ignored because lru_cache returns same instance
def test_rate_limit(client):
    app.state.settings.rate_limit = 0  # lru_cache ignores this

# FIX option 1 — use env vars + cache_clear
def test_rate_limit(monkeypatch, client):
    monkeypatch.setenv("RATE_LIMIT", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

# FIX option 2 — use FastAPI dependency_overrides
def test_rate_limit(client):
    app.dependency_overrides[get_settings] = lambda: Settings(rate_limit=0)
    yield
    app.dependency_overrides.clear()
```

#### Phase 7: Fix Missing Protocol Method

When an async client implementation is missing a method required by its Protocol:

```python
# Protocol requires:
class AsyncAgamemnonClientProtocol(Protocol):
    async def get_diagnostics(self, agent_id: str) -> dict: ...

# Fix: add matching method to the implementation
class AsyncAgamemnonClient:
    async def get_diagnostics(self, agent_id: str) -> dict:
        """Retrieve diagnostics for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Diagnostics dictionary from the API.
        """
        response = await self._client.get(f"/v1/agents/{agent_id}/diagnostics")
        response.raise_for_status()
        return response.json()
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | --------------- | --------------- | ---------------- |
| Push empty commits to re-trigger CI | `git commit --allow-empty -m "ci: re-trigger"` | Myrmidons workflows use `concurrency: cancel-in-progress: true` + `pull_request` trigger deduplicates same SHA | Use `gh run rerun --failed` instead of empty commits |
| `gh workflow run` to re-trigger | `gh workflow run ci.yml --ref <branch>` | Returns HTTP 422 — workflow has no `workflow_dispatch` trigger | Only works if `on: workflow_dispatch` is in the workflow YAML |
| Fix gitleaks "missing license" by editing workflow | Attempted to add `GITLEAKS_LICENSE` to workflow env | Secret doesn't exist in the GitHub org — org admin must create it | This is a pure infra issue; skip and don't waste time on code changes |
| Fix one PR's pixi.lock while another PR was stacked on top | Checked out base branch and pushed pixi.lock | Agent accidentally included changes from a stacked branch | Always verify branch isolation before pushing pixi.lock fix |

## Results & Parameters

### Expected CI Timeline After pixi.lock Push

```
0s   — git push completes
10s  — GitHub detects push, queues CI run
30s  — CI run appears in gh run list
90s  — pixi install step completes (lock validated)
3-5m — full CI run completes
```

### Triage Status Classification

| Status | Meaning | Action |
| -------- | --------- | -------- |
| `FAILING` + "lock-file not up-to-date" | stale pixi.lock | `pixi install && git add pixi.lock && git commit && git push` |
| `FAILING` + "missing gitleaks license" | org secret missing | Skip — infra issue |
| `FAILING` + "bats: command not found" on new platform | platform missing bats-core | Move bats-core to platform-specific deps |
| `FAILING` + old SHA in CI run | SHA mismatch | `gh run rerun --failed` |
| `pending` | CI in progress | Wait |
| `green` | All checks pass | Enable auto-merge if not already enabled |
| `no-checks` | No CI configured or branch not triggered | Check workflow triggers |

### Complexity Refactoring (Ruff C901)

When a method exceeds complexity 10 (C901), extract helper methods:

```python
# BEFORE — _subscribe_loop has complexity > 10
async def _subscribe_loop(self): ...  # monolithic

# AFTER — extract helpers
async def _import_nats(self): ...
async def _create_subscriptions(self): ...
async def _cleanup_subscriptions(self): ...
async def _run_message_loop(self): ...
async def _handle_task_result(self, msg): ...
async def _subscribe_loop(self):
    """Orchestrate the subscription lifecycle."""
    await self._import_nats()
    await self._create_subscriptions()
    try:
        await self._run_message_loop()
    finally:
        await self._cleanup_subscriptions()
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Myrmidons | 42 open PRs, concurrency-cancel workflows | pixi.lock regeneration + gh run rerun pattern |
| ProjectHermes | LRU cache test failures | dependency_overrides / cache_clear pattern |
| ProjectScylla | C901 complexity + missing protocol method | helper extraction + protocol compliance |
| ProjectKeystone | stale pixi.lock | pixi install + push |
| ProjectAgamemnon | stale pixi.lock | pixi install + push |
| ProjectArgus | stale pixi.lock | pixi install + push |
| ProjectMnemosyne | stale pixi.lock | pixi install + push |
