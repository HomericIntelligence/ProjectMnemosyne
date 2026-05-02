---
name: ci-cd-github-api-rate-limit-ci-monitoring
description: "Avoid and recover from GitHub API rate limit exhaustion (5000/hr) during
  intensive CI diagnostic loops using gh CLI. Use when: (1) running batch PR investigation
  across many open PRs, (2) fetching CI job logs in a loop, (3) hitting HTTP 403 rate
  limit errors from gh CLI during CI monitoring sessions."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-api
  - rate-limit
  - gh-cli
  - ci-monitoring
  - pr-investigation
  - loop
---

# GitHub API Rate Limit — CI Diagnostic Loops

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Diagnose and fix 13 open PRs across AchaeanFleet without exhausting GitHub API rate limit |
| **Outcome** | Rate limit exhausted within ~2 hours of intensive `gh run list` + job log fetching |
| **Verification** | verified-local — observed in AchaeanFleet session 2026-04-24 |

## When to Use

- Starting a batch PR investigation session (>5 open PRs to review)
- About to run a loop that fetches CI run logs per PR
- Encountering `HTTP 403: API rate limit exceeded for user ID XXXXXXX`
- Using `ScheduleWakeup` to poll CI status — need to budget API calls per wake cycle
- Before running intensive `gh api`, `gh run list`, or `gh pr list` loops

## Verified Workflow

### Quick Reference

```bash
# 1. Check remaining rate limit before any batch operation
gh api rate_limit --jq '.resources.core | "used: \(.used)/\(.limit), resets at: \(.reset | todate)"'

# 2. Bulk PR status — ONE call instead of N calls
gh pr list --json number,title,mergeStateStatus,statusCheckRollup --limit 50

# 3. All check statuses for a single PR — ONE call
gh pr view <NUMBER> --json statusCheckRollup

# 4. Calculate sleep until reset (when rate limit is exhausted)
RESET=$(gh api rate_limit --jq '.resources.core.reset')
NOW=$(date +%s)
DELAY=$(( RESET - NOW + 60 ))
echo "Sleep ${DELAY}s until reset"
```

### Detailed Steps

1. **Always check rate limit first** before starting any batch investigation session. The core limit is 5000 requests/hr; intensive sessions can exhaust it in under 2 hours.

2. **Prefer bulk endpoints over per-item calls**:
   - `gh pr list --json number,title,mergeStateStatus,statusCheckRollup` returns all PRs with check statuses in a single API call
   - `gh pr view <N> --json statusCheckRollup` returns all check statuses for one PR in one call — use this over querying individual run IDs

3. **Gate log fetching**: Each `gh api /repos/.../actions/jobs/<ID>/logs` call counts against the rate limit. Only fetch logs for failed jobs, and only after confirming which jobs failed via `statusCheckRollup`.

4. **Use `ScheduleWakeup` for rate limit recovery** — when exhausted, calculate seconds until reset and call `ScheduleWakeup` with that delay. Never busy-wait or poll in a tight loop.

5. **Log fetching batching**: If you must fetch multiple job logs, check rate limit after every 20 fetches and pause if under 200 remaining.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Per-PR `gh pr view` loop | Called `gh pr view <N>` for each of 13 PRs sequentially | 13 API calls instead of 1 bulk call | Use `gh pr list --json` to get all PR statuses at once |
| Per-failure log fetch loop | Fetched job logs for every failed run without rate limit checks | Job log endpoints are expensive; exhausted limit before all PRs investigated | Check rate limit every ~20 log fetches; only fetch logs for actionable failures |
| Ignoring rate limit until 403 | Did not check `gh api rate_limit` at session start | Had no budget awareness; couldn't predict when limit would exhaust | Always check remaining quota at session start and at each loop iteration |
| Sleeping fixed intervals | Used fixed `sleep 60` between retries after 403 | Woke up before reset; hit 403 again immediately | Calculate exact reset time with `gh api rate_limit --jq '.resources.core.reset'` and sleep to that timestamp |

## Results & Parameters

### Rate Limit Budget Reference

| Operation | Approximate Cost | Notes |
| ----------- | ----------------- | ------- |
| `gh api rate_limit` | 1 call | Always cheap — check freely |
| `gh pr list --json ...` (50 PRs) | 1 call | Bulk — always prefer this |
| `gh pr view <N> --json statusCheckRollup` | 1 call | Gets all checks for 1 PR |
| `gh pr view <N>` (no JSON) | 1 call | Same cost, less structured |
| `gh run list --limit 10` | 1 call | Lists recent runs |
| `gh api /repos/.../actions/jobs/<ID>/logs` | 1+ calls | Expensive if logs are large; avoid in bulk |
| `gh run view <RUN_ID> --log-failed` | 2-5 calls | Better than raw job log API |

**Limit**: 5000 requests/hr for authenticated users. Resets on the hour boundary (not rolling).

### Rate Limit Check Commands

```bash
# Full status
gh api rate_limit --jq '.resources.core | "used: \(.used)/\(.limit), resets at: \(.reset | todate)"'

# Just remaining
gh api rate_limit --jq '.resources.core.remaining'

# Calculate delay until reset (seconds)
RESET=$(gh api rate_limit --jq '.resources.core.reset')
NOW=$(date +%s)
echo "Seconds until reset: $(( RESET - NOW ))"
```

### ScheduleWakeup Pattern for Rate Limit Recovery

When rate limit is exhausted during a `/loop` or monitoring session:

```python
# Get reset time, add 90s buffer
RESET=$(gh api rate_limit --jq '.resources.core.reset')
NOW=$(date +%s)
DELAY=$(( RESET - NOW + 90 ))
# Pass DELAY as delaySeconds to ScheduleWakeup
# reason: "waiting for GitHub API rate limit reset"
```

### Session Budget Planning

For a session investigating N PRs with CI failures:
- **Minimum calls**: N + 1 (1 bulk list + 1 statusCheckRollup per PR)
- **With log fetching**: N + 1 + (failed_jobs * log_pages)
- **Safe threshold**: Stop log fetching when `remaining < 500`; stop all non-essential calls when `remaining < 100`

### Error Signature

```
Error: HTTP 403: API rate limit exceeded for user ID XXXXXXX
(https://api.github.com/repos/...)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | Batch investigation of 13 open PRs with CI failures, session 2026-04-24 | Rate limit exhausted within ~2 hours of intensive `gh run list` and job log fetching |
