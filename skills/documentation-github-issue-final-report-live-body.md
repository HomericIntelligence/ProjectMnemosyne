---
name: documentation-github-issue-final-report-live-body
description: "Rewrite GitHub issues into coherent final reports without overwriting live edits. Use when: (1) an issue has accumulated investigation notes, follow-up phrasing, or stale detours, (2) the user asks for a final report-style issue body, (3) sensitive or model-specific details must be removed before publishing."
category: documentation
date: 2026-06-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, issues, final-report, live-body, redaction, documentation]
---

# GitHub Issue Final Report Live Body

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Convert a GitHub issue body from an incremental investigation transcript into one coherent final report while preserving user edits and removing stale or sensitive detours. |
| **Outcome** | Successful. The safe workflow reads the current live issue body, checks for concurrent edits, rewrites locally, publishes once, then verifies required content and removed phrasing. |
| **Verification** | verified-local - workflow executed against a live GitHub issue; CI validation not applicable. |

## When to Use

- A GitHub issue body contains chronological debugging notes, follow-up language, or obsolete side investigations.
- The user asks for the issue to read as a final report rather than an activity log.
- You need to avoid overwriting edits that may have happened since your last local draft.
- The issue should preserve technical evidence while removing user-error detours, stale checklists, or unnecessary operational specifics.
- The report must protect model-specific, endpoint-specific, host-specific, path-specific, or other internal identifiers.

## Verified Workflow

### Quick Reference

```bash
# 1. Fetch the current live body. Treat this as source of truth.
gh issue view <issue-number> --repo <owner>/<repo> \
  --json body --jq '.body' > /tmp/issue-live.md

# 2. Capture metadata for a concurrent-edit guard.
gh issue view <issue-number> --repo <owner>/<repo> \
  --json number,title,state,url,updatedAt --jq '.'

# 3. Draft the replacement body locally.
$EDITOR /tmp/issue-final.md

# 4. Re-check updatedAt immediately before editing.
gh issue view <issue-number> --repo <owner>/<repo> \
  --json updatedAt --jq '.updatedAt'

# 5. Publish only if updatedAt is unchanged or the newer body has been merged.
gh issue edit <issue-number> --repo <owner>/<repo> \
  --body-file /tmp/issue-final.md

# 6. Fetch and verify the live final body.
gh issue view <issue-number> --repo <owner>/<repo> \
  --json body --jq '.body' > /tmp/issue-live-final.md

rg -n "## Summary|## Final Finding|## Evidence|## Acceptance Criteria" /tmp/issue-live-final.md
rg -n "follow-up|previously unchecked|remaining|still untested|intermediate detour" /tmp/issue-live-final.md
```

### Detailed Steps

1. **Read the live issue body first.** Do not reuse an older local draft as the source of truth after the user says they edited or wants to avoid overwrites.
2. **Capture `updatedAt`.** Use it as a simple guard against concurrent edits between read and write.
3. **Identify the final report structure.** Prefer sections like Summary, Final Finding, Environment, Evidence, Reproduction Matrix, Controls, Logs, Bad Behavior, Expected Behavior, Reproduction Steps, Acceptance Criteria, and Validation.
4. **Convert chronology into conclusions.** Replace "follow-up testing" and "still unchecked" phrasing with final-state statements such as "tested", "observed", "not observed", or "inconclusive".
5. **Remove stale detours.** If an intermediate problem was unrelated to the final diagnosis, omit it unless it materially changes the conclusion.
6. **Protect sensitive details.** Replace model IDs, endpoint addresses, hostnames, job IDs, absolute paths, internal repo names, usernames, and proprietary payloads with placeholders or generic descriptions unless the user explicitly asks to retain them.
7. **Keep enough evidence to reproduce.** Preserve response shape, request shape, relevant flags, logs, control results, and acceptance criteria, but sanitize identifiers.
8. **Re-check `updatedAt` before publishing.** If the timestamp changed, fetch the body again and merge the user edits before editing.
9. **Verify the live result, not the local file.** Fetch the GitHub body after editing and check both required sections and forbidden stale phrasing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Editing from an old local draft | Reused a body file after additional live edits may have occurred | Risked overwriting user changes or resurrecting stale language | Always re-read the live issue body before a rewrite |
| Leaving chronological investigation language | Kept phrases like "follow-up", "previously unchecked", or intermediate detours | The issue read like a work log instead of a final bug report | Rewrite in final-state language once the investigation is complete |
| Over-preserving raw evidence | Included raw identifiers and detailed operational paths | Durable issue bodies can leak unnecessary internal information | Keep response shapes and conclusions; redact identifiers and proprietary payloads |
| Publishing without absence checks | Verified only that new sections existed | Old misleading phrases can remain and undermine the final report | Check both presence of required sections and absence of stale wording |

## Results & Parameters

### Final Report Section Order

```text
## Summary
## Final Finding
## Date And Environment
## Runtime Context
## Template Or Parser Evidence
## Request Shape
## Response Evidence
## Reproduction Matrix
## Control Results
## Endpoint Checks
## Log Evidence
## Bad Behavior
## Expected Behavior
## Reproduction Steps
## Acceptance Criteria
## Validation
```

### Concurrent Edit Guard

```text
1. Fetch live body.
2. Record updatedAt.
3. Draft local replacement.
4. Re-fetch updatedAt immediately before `gh issue edit`.
5. If changed, stop and merge live edits before publishing.
```

### Redaction Checklist

- No model IDs or model-family names unless explicitly approved.
- No endpoint IPs, hostnames, ports, or internal URLs unless explicitly approved.
- No job IDs, process IDs, usernames, cluster names, or allocation identifiers.
- No absolute paths or checkpoint paths.
- No full raw reasoning output unless explicitly approved and clearly truncated.
- No obsolete auth/user-error detours unless they are part of the final diagnosis.

### Live Verification Checklist

```bash
# Required content should exist.
rg -n "## Summary|## Final Finding|## Acceptance Criteria|## Validation" /tmp/issue-live-final.md

# Stale wording should be absent.
rg -n "follow-up|previously unchecked|remaining|still untested|intermediate detour" /tmp/issue-live-final.md
# Expected: no output, exit code 1.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| GitHub issue tracker | Final report rewrite after operational debugging | Sanitized workflow only; no issue number, model IDs, endpoints, paths, jobs, or raw proprietary payloads retained |
