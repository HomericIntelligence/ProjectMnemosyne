---
name: github-bulk-issue-filing-rate-limit-recovery
description: "Patterns for filing 40+ GitHub issues reliably across multiple repos: handling secondary rate limits (403 BCE2), org monthly API usage limits, duplicate detection/cleanup, and pagination truncation in verification. Use when: (1) filing 200+ issues across 10+ repos in a single session, (2) hitting GitHub 403 errors mid-batch, (3) verifying issue counts after multi-wave filing with retry runs."
category: tooling
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, issues, rate-limit, bulk-filing, epic, deduplication, pagination]
---

# GitHub Bulk Issue Filing: Rate Limit Recovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | File 680 GitHub issues across 15 repos (one Epic + per-finding child issues per repo) reliably without duplicates |
| **Outcome** | Successful — 15 Epics + 680 child issues filed; required one org-limit recovery cycle and a duplicate cleanup pass |
| **Verification** | verified-local |

## When to Use

- Filing 40+ issues per repo, or 200+ issues across a session
- Using multiple retry agents that may overlap with previous filing runs
- Verifying issue counts after a multi-wave, multi-retry session
- Recovering from GitHub secondary rate limits (403 BCE2) or org monthly usage limits

## Verified Workflow

### Quick Reference

```bash
# Test org limit before dispatching batch
gh api repos/$ORG/$REPO/issues --method POST \
  -f title="[TEST] Rate limit check" -f body="test" 2>&1 | grep -q '"number"' \
  && echo "OK" || echo "BLOCKED"
# Close test issue immediately
gh issue close $TEST_ISSUE_NUM --repo $ORG/$REPO --reason "not planned"

# File issues with rate-limit guards
for finding in "${findings[@]}"; do
  echo "$body" > /tmp/issue_body.txt
  gh issue create --repo "$REPO" \
    --title "$title" \
    --label "audit-finding,severity:$sev" \
    --body-file /tmp/issue_body.txt
  sleep 3  # between issues
  # On 403: sleep 60 and retry up to 3 times
done

# Count issues correctly (avoid pagination truncation)
gh issue list --repo "$REPO" --label "audit-finding" \
  --state open --json number --limit 200 --jq 'length'

# Find duplicates by title
gh issue list --repo "$REPO" --label "audit-finding" \
  --state open --json number,title --limit 200 \
  --jq 'group_by(.title) | map(select(length > 1)) | .[] | "DUPE: #\([.[].number | tostring] | join(", #")) — \(.[0].title)"'

# Close duplicates (keep lower-numbered, close higher-numbered)
# Exception: if child bodies say "Part of #N" with a higher number, keep that one
gh issue close $DUPE_NUM --repo "$REPO" \
  --reason "not planned" \
  --comment "Duplicate — closing in favour of #$CANONICAL_NUM"
```

### Detailed Steps

1. **Pre-flight org limit test** — Before dispatching any batch of filer agents, POST one test issue to a representative repo. If it succeeds, close it immediately and proceed. If it returns the org limit error, stop and wait (limit resets daily).

2. **Use `--body-file` always** — Write issue bodies to a temp file first (`/tmp/repo_issue_body.txt`), then pass `--body-file`. Direct `--body` with multi-line markdown causes shell escaping failures.

3. **Sequential filing with sleep** — File issues sequentially (not parallel) within a repo: `sleep 3` between each. On 403, `sleep 60` and retry up to 3 times before marking as error.

4. **Idempotency before filing** — Check if issues already exist before starting: `gh issue list --label "audit-finding" --limit 200 --jq 'length'`. If count >= expected, skip.

5. **One filer agent per repo** — Never run two filer agents against the same repo concurrently. Parallel agents create exact-title duplicates that require a cleanup pass.

6. **Count verification with `--limit 200`** — GitHub defaults to 30 results. Always pass `--limit 200` when counting issues. Without it, repos with 31+ issues always appear as mismatches.

7. **Duplicate detection** — After any multi-wave session with retries, run the jq `group_by(.title)` check to find exact-title duplicates. Close the higher-numbered duplicates (lower = filed earlier = canonical), UNLESS child bodies reference the higher number in "Part of #N" — in that case, keep the higher-numbered one.

8. **Semantic duplicates** — When two batches cover overlapping finding indices (e.g., first 30 then re-filed first 30), detect via issue number ranges rather than titles. Issues with different title formats (lowercase vs uppercase severity) are still semantic duplicates.

9. **Label application** — If issues were filed without the `audit-finding` label (e.g., due to label creation failure), apply retroactively: `gh issue edit $N --repo $REPO --add-label "audit-finding"`. Batch with `sleep 1` between edits.

10. **Duplicate Epic cleanup** — When two Epics exist: check which one child issues reference via "Part of #N" in their bodies, keep that one, close the other with a duplicate comment.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Haiku filer for 40+ issues | Used Haiku agents to file issues per repo | Hit GitHub secondary rate limits (403 BCE2) — smaller models issue requests faster, hitting burst limits | Use Sonnet agents for large filing batches; they pace naturally and are more resilient |
| Retry via parallel agents | Dispatched 5 parallel retry filer agents for blocked repos | All hit the org monthly usage limit simultaneously; no issues filed | Test the limit with a single API call first; wait for daily reset before any retry |
| `gh issue list` without `--limit` | Used `gh issue list --label audit-finding --jq length` for verification | GitHub defaults to 30 results — repos with 31+ issues always showed as MISMATCH | Always use `--limit 200` (or `--limit 500` for very large repos) |
| Closing lower-numbered duplicate Epics unconditionally | Assumed lower issue number = canonical Epic | Some child issues said "Part of #N" where N was the higher Epic number | Before closing, grep child bodies for "Part of #" to find which Epic number they reference |
| Concurrent filers on same repo | Two retry agents for the same repo ran simultaneously | Created ~49 exact-title duplicate issues per repo | Enforce one-agent-per-repo rule; use a serial outer loop for repo batches |

## Results & Parameters

### Filing Parameters

| Parameter | Value |
|-----------|-------|
| Sleep between issues | 3 seconds |
| Sleep on 403 | 60 seconds |
| Max retries on 403 | 3 |
| `--limit` for `gh issue list` | 200 (never omit) |
| Agents per repo | 1 (never concurrent) |
| Preferred agent tier | Sonnet (rate-limit resilient) |
| Body delivery | `--body-file /tmp/body.txt` (never `--body` for multi-line) |

### Org Limit Test Template

```bash
TEST_RESULT=$(gh api repos/$ORG/$REPO/issues --method POST \
  -f title="[TEST] Rate limit probe" -f body="probe" 2>&1)
if echo "$TEST_RESULT" | grep -q '"number"'; then
  TEST_NUM=$(echo "$TEST_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['number'])")
  gh issue close "$TEST_NUM" --repo "$ORG/$REPO" --reason "not planned" 2>/dev/null
  echo "CLEAR — proceed with batch"
else
  echo "BLOCKED — wait for daily reset"
  exit 1
fi
```

### Duplicate Cleanup Script Template

```python
import subprocess, json

def find_and_close_dupes(org_repo, expected_count):
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", org_repo,
         "--label", "audit-finding", "--state", "open",
         "--json", "number,title", "--limit", "200"],
        capture_output=True, text=True)
    issues = json.loads(result.stdout)
    seen = {}
    dupes = []
    for issue in sorted(issues, key=lambda x: x["number"]):
        title = issue["title"]
        if title in seen:
            dupes.append(issue["number"])
        else:
            seen[title] = issue["number"]
    print(f"{org_repo}: {len(issues)} total, {len(dupes)} dupes: {dupes}")
    return dupes
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus (15 repos) | 2026-04-28 ecosystem-wide strict audit | 680 findings, 15 Epics, ~119 duplicates closed, org limit hit once |
