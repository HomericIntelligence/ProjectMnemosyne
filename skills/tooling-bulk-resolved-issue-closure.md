---
name: tooling-bulk-resolved-issue-closure
description: "Efficiently close multiple GitHub issues that are already resolved. Use when: (1) auditing open issues reveals items already addressed, (2) batch-closing stale issues after a cleanup sprint, (3) verifying file existence before closing file-related issues."
category: tooling
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: [github, issues, cleanup, batch-operations, gh-cli]
---

# Bulk Closure of Already-Resolved GitHub Issues

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Close multiple GitHub issues that were already resolved by prior work (file removals, config additions) without requiring new code changes. |
| **Outcome** | Successfully closed 3 issues (#1524, #1531, #1533) with explanatory comments and rate-limited API calls. |

## When to Use

- Open issue backlog contains items already addressed by merged PRs or prior cleanup
- Audit reveals files requested by issues already exist in the repository (e.g., CODEOWNERS, dependabot.yml)
- Batch-closing issues after verifying their deliverables are present in the codebase
- Issue references a file that was already removed (cleanup issues)

## Verified Workflow

### Quick Reference

```bash
# Pattern: comment + close with rate limiting between API calls
gh issue comment <NUMBER> --repo <OWNER>/<REPO> --body "<explanation>"
sleep 1
gh issue close <NUMBER> --repo <OWNER>/<REPO>
sleep 1
# Repeat for next issue...
```

### Detailed Steps

1. **Verify resolution** before commenting: confirm the file exists or was removed as claimed
   ```bash
   # For "file should exist" issues:
   ls -la .github/CODEOWNERS .github/dependabot.yml
   # For "file should be removed" issues:
   ls retry_dryrun3.sh  # Should return "No such file"
   ```

2. **Post explanatory comment** with evidence of resolution
   ```bash
   gh issue comment 1524 --repo HomericIntelligence/ProjectScylla \
     --body "This file has already been removed from the repository. Closing as resolved."
   ```

3. **Rate-limit between API calls** with `sleep 1` to avoid GitHub throttling

4. **Close the issue** after the comment is posted
   ```bash
   gh issue close 1524 --repo HomericIntelligence/ProjectScylla
   ```

5. **Repeat** for each issue, maintaining the comment-then-close order

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | No failed attempts in this session | Process was straightforward | For simple closures, the comment+close pattern works reliably on first try |

## Results & Parameters

### Comment Templates by Issue Type

**File already removed:**
```
This file has already been removed from the repository. Closing as resolved.
```

**File/config already exists:**
```
`<filepath>` already exists with <brief description of contents>. Closing as resolved.
```

### Rate Limiting

- `sleep 1` between each `gh` API call (comment and close count as separate calls)
- For large batches (10+ issues), consider `sleep 2` to stay well within GitHub's rate limits

### Verification Checklist

- [ ] Verify each issue's deliverable is present (or absent, for removal issues) before closing
- [ ] Include specific evidence in the comment (file path, what it contains)
- [ ] Use `--repo` flag when operating from a different repository context

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Closing 3 audit issues (#1524, #1531, #1533) | Issues from codebase audit already resolved by prior work |
